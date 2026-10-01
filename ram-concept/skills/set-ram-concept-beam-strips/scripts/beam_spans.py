#!/usr/bin/env python3
"""Find the design spans that run along concrete beams and check their T or L beam strip setup.

Read-only on a saved .cpt. Lists each span with the midpoint to select it by,
whether it is a T beam (slab both sides) or an L beam (slab one side), and
what still differs from the office setup. Exit code 1 while any span is TODO.

  python beam_spans.py <model.cpt>
"""

from __future__ import annotations

import math
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

FT = 3048.0          # internal length units per foot
IN = 254.0
BAR_NAMES = {24: "#3", 25: "#4", 26: "#5", 27: "#6", 28: "#7", 29: "#8", 30: "#9", 31: "#10", 32: "#11"}
COLUMN_STRIP = {"ColumnStripCrossSectionAutoTrim": "T or L", "ColumnStripTorsionDesign": "beam",
                "ColumnStripDesignSystem": "beam"}
WIDTH_CALC = {"T": "code-beam", "L": "code-l-beam"}       # L value not seen yet; see SKILL.md
# middle strip takes the model's typical slab column-strip values for these
MIDDLE_FROM_COLUMN = {"MiddleStripCrossSectionAutoTrim": "ColumnStripCrossSectionAutoTrim",
                      "MiddleStripTopBar": "ColumnStripTopBar", "MiddleStripBottomBar": "ColumnStripBottomBar",
                      "MiddleStripTopCover": "ColumnStripTopCover", "MiddleStripBottomCover": "ColumnStripBottomCover",
                      "MiddleStripTorsionDesign": "ColumnStripTorsionDesign",
                      "MiddleStripDesignSystem": "ColumnStripDesignSystem"}


def point(text: str) -> tuple[float, float]:
    x, y = (float(v) / FT for v in re.findall(r"\[([-\d.eE+]+)\]", text))
    return x, y


def beam_along(span, beams, reach: float = 1.5):
    """The beam a span runs along: its midpoint sits on the beam line and the two are parallel."""
    (x0, y0), (x1, y1) = span
    mx, my, length = (x0 + x1) / 2, (y0 + y1) / 2, math.hypot(x1 - x0, y1 - y0)
    for beam in beams:
        (a, b), (c, d) = beam[0], beam[1]
        run = math.hypot(c - a, d - b)
        if not run or not length:
            continue
        s = max(0.0, min(1.0, ((mx - a) * (c - a) + (my - b) * (d - b)) / run ** 2))
        off = math.hypot(mx - a - s * (c - a), my - b - s * (d - b))
        if off <= reach and abs((x1 - x0) * (c - a) + (y1 - y0) * (d - b)) / (length * run) > 0.95:
            return beam
    return None


def beam_kind(span, beam, slab_at, clear: float = 3.0) -> str:
    """'T' when there is slab on both sides of the beam at the span midpoint, else 'L'."""
    (x0, y0), (x1, y1) = span
    (a, b), (c, d), width = beam
    run = math.hypot(c - a, d - b)
    nx, ny = -(d - b) / run, (c - a) / run
    mx, my, off = (x0 + x1) / 2, (y0 + y1) / 2, width / 2 + clear
    return "T" if slab_at(mx + nx * off, my + ny * off) and slab_at(mx - nx * off, my - ny * off) else "L"


def _slab_lookup(path: Path):
    """Point-on-slab test from the meshed model, using the rebar engine's reader."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"))
    import cpt_reader
    mesh = cpt_reader.Mesh(Path(path))
    return lambda x, y: mesh.thickness(x, y) is not None


def read(path: Path) -> tuple[list[dict], dict]:
    db = sqlite3.connect(f"file:{Path(path).as_posix()}?immutable=1", uri=True)
    beams = [(point(a), point(b), w / FT) for a, b, w in db.execute("select Point0, Point1, Width from Beam")]
    keys = sorted(set(COLUMN_STRIP) | set(MIDDLE_FROM_COLUMN) | set(MIDDLE_FROM_COLUMN.values())
                  | {"ColumnStripWidthCalc", "MiddleStripUsesColumnStripProps"})
    rows = [dict(zip(["uid", "set", "p0", "p1"] + keys, r)) for r in
            db.execute("select UID, SpanSet, Point0, Point1, " + ", ".join(keys) + " from SpanSegment")]
    for r in rows:
        r["span"] = (point(r["p0"]), point(r["p1"]))
        r["beam"] = beam_along(r["span"], beams)
    # typical slab strip values per direction: covers differ between the two bar layers
    typical = {}
    for span_set in {r["set"] for r in rows}:
        slab = [r for r in rows if r["beam"] is None and r["set"] == span_set]
        typical[span_set] = {k: Counter(r[k] for r in slab).most_common(1)[0][0] for k in set(MIDDLE_FROM_COLUMN.values())}
    slab_at = _slab_lookup(path)
    out = []
    for r in rows:
        if r["beam"] is None:
            continue
        kind = beam_kind(r["span"], r["beam"], slab_at)
        want = dict(COLUMN_STRIP, MiddleStripUsesColumnStripProps=0,
                    **{m: typical[r["set"]][c] for m, c in MIDDLE_FROM_COLUMN.items()})
        diffs = {k: r[k] for k, v in want.items() if r[k] != v}
        if r["ColumnStripWidthCalc"] in ("code-slab", "manual", "full-width"):
            diffs["ColumnStripWidthCalc"] = r["ColumnStripWidthCalc"]
        (x0, y0), (x1, y1) = r["span"]
        out.append(dict(uid=r["uid"], set=r["set"], mid=((x0 + x1) / 2, (y0 + y1) / 2), kind=kind,
                        width_calc=r["ColumnStripWidthCalc"], diffs=diffs))
    return sorted(out, key=lambda o: (o["set"], o["mid"])), typical


def main(argv=None) -> int:
    path = Path((argv or sys.argv[1:])[0])
    spans, typical = read(path)
    for o in spans:
        state = "TODO" if o["diffs"] else "DONE"
        print(f"{state} {o['set']:9s} {o['kind']} beam  midpoint {o['mid'][0]:.2f},{o['mid'][1]:.2f}  uid {o['uid']}"
              + ("  differs: " + ", ".join(f"{k}={v}" for k, v in o["diffs"].items()) if o["diffs"] else ""))
    todo = [o for o in spans if o["diffs"]]
    print(f"{len(spans) - len(todo)} of {len(spans)} beam spans set as beams")
    for span_set in ("longitude", "latitude"):
        if span_set not in typical:
            continue
        ty = typical[span_set]
        top, bottom = BAR_NAMES.get(ty["ColumnStripTopBar"], "?"), BAR_NAMES.get(ty["ColumnStripBottomBar"], "?")
        tc, bc = ty["ColumnStripTopCover"] / IN, ty["ColumnStripBottomCover"] / IN
        print(f"typical {span_set} slab strip: top {top}, bottom {bottom}, covers {tc:g} / {bc:g} in, "
              f"{ty['ColumnStripCrossSectionAutoTrim']}, {ty['ColumnStripTorsionDesign']}, {ty['ColumnStripDesignSystem']}")
        points = ";".join(f"{o['mid'][0]:.2f},{o['mid'][1]:.2f}" for o in todo if o["set"] == span_set)
        if points:
            print(f"  with the {span_set.capitalize()} Design Spans Plan active:")
            print(f'  apply-beam-strips.ps1 -Points "{points}" -TopBar "{top}" -BottomBar "{bottom}" '
                  f"-TopCover {tc:g} -BottomCover {bc:g}")
    return 1 if todo else 0


if __name__ == "__main__":
    raise SystemExit(main())
