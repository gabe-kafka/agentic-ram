#!/usr/bin/env python3
"""Judge the additional bars RAM Concept asks for where two mats meet.

Where a mat patch ends (balcony or terrace meeting the main slab) the mat bars
terminate, the program's moment capacity notches down, and it adds bars. The
office check: ignore the notch and compare demand with the mat capacity on
either side. Demand within the side capacity means the bars are not required.

Inputs, both from a calculated mats-only copy of the model:
  <model.cpt>   the saved copy (geometry, mats, program bars)
  <table.txt>   Strength Design > Tables > Span Section Analysis, exported

  python transition_check.py <model.cpt> <table.txt> [--out verdicts.json]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"))
import cpt_reader as cr          # noqa: E402

FT = 3048.0
TOP_COVER, BOTTOM_COVER = 4, 5                    # DistributedRebar.ElevationReference
ZONE = 4.0                                        # ft either side of the boundary treated as the notch
SIDE = 10.0                                       # ft either side used for the side capacity


def points(text: str) -> list[tuple[float, float]]:
    v = [float(x) / FT for x in re.findall(r"\[([-\d.eE+]+)\]", text)]
    return list(zip(v[0::2], v[1::2]))


def read_table(path: Path) -> dict[str, list[dict]]:
    """Exported Span Section Analysis: strip id -> sections with bending demand and capacity (kip-ft)."""
    raw = path.read_bytes()
    text = raw.decode("utf-16-le") if b"\x00" in raw[:64] else raw.decode("utf-8", "replace")
    rows = [[c.strip() for c in line.split("\t")] for line in text.splitlines() if line.strip()]
    head = rows[0]
    col = {name: next(i for i, h in enumerate(head) if h.startswith(name)) for name in
           ("ID", "Section", "Min Capacity Bending", "Min Demand Bending", "Max Demand Bending", "Max Capacity Bending")}

    def number(value):
        try:
            return float(value)
        except ValueError:
            return None

    strips = defaultdict(list)
    for r in rows[1:]:
        strips[r[col["ID"]]].append(dict(
            section=int(r[col["Section"]]),
            top_capacity=number(r[col["Min Capacity Bending"]]), top_demand=number(r[col["Min Demand Bending"]]),
            bottom_demand=number(r[col["Max Demand Bending"]]), bottom_capacity=number(r[col["Max Capacity Bending"]])))
    for sections in strips.values():
        sections.sort(key=lambda s: s["section"])
    return strips


def crossing(p0, p1, a, b):
    """Parameter along p0->p1 (0..1) where it crosses segment a-b, or None."""
    (x0, y0), (x1, y1), (ax, ay), (bx, by) = p0, p1, a, b
    dx, dy, ex, ey = x1 - x0, y1 - y0, bx - ax, by - ay
    den = dx * ey - dy * ex
    if abs(den) < 1e-9:
        return None
    t = ((ax - x0) * ey - (ay - y0) * ex) / den
    u = ((ax - x0) * dy - (ay - y0) * dx) / den
    return t if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None


def judge(sections: list[dict], added: list[bool], length: float, t: float, face: str) -> dict | None:
    """Office check at one boundary crossing of one strip, for one face.

    ``sections`` run evenly from one end of the strip to the other; ``t`` is
    where the mat boundary crosses (0..1). ``added[i]`` says whether the
    program put additional bars over section i. The table's capacity includes
    those bars, so the mat's own capacity is read only from sections without
    them. Returns None when no section falls in the notch zone.

      covered     no additional bars at the notch: the mat carries it
      notch only  bars at the notch, none either side, and demand at the notch
                  is within the mat capacity either side: not required
      real        demand at the notch exceeds the mat either side, or the
                  additional bars carry on past the notch
    """
    n = len(sections)
    sign = 1.0 if face == "bottom" else -1.0
    place = [length * i / (n - 1) if n > 1 else 0.0 for i in range(n)]
    at = length * t
    demand = [max(0.0, sign * (s[f"{face}_demand"] or 0.0)) for s in sections]
    capacity = [abs(s[f"{face}_capacity"]) if s[f"{face}_capacity"] is not None else None for s in sections]
    if any(c is None for c in capacity):
        return None
    zone = [i for i in range(n) if abs(place[i] - at) <= ZONE]
    if not zone:
        return None
    before = [i for i in range(n) if ZONE < at - place[i] <= SIDE]
    after = [i for i in range(n) if ZONE < place[i] - at <= SIDE]
    worst = max(zone, key=lambda i: demand[i])
    out = dict(section=sections[worst]["section"], demand=round(demand[worst], 1), side_capacity=None)
    if not any(added[i] for i in zone):
        out["verdict"] = "covered"
        return out
    mat = []                                      # mat capacity on each side that has sections
    for side in (before, after):
        if not side:
            continue
        free = [capacity[i] for i in side if not added[i]]
        if not free:
            out["verdict"] = "real"               # additional bars carry on past the notch
            out["why"] = "bars continue past the notch"
            return out
        mat.append(max(free))
    if not mat:
        out["verdict"] = "no side to compare"
        return out
    out["side_capacity"] = round(min(mat), 1)
    out["verdict"] = "notch only" if demand[worst] <= min(mat) else "real"
    if out["verdict"] == "real":
        out["why"] = "demand above the mat either side"
    return out


def mat_edges(db, mesh, direction: int, reference: int) -> list:
    """Edges of mat patches that have slab on both sides: where one mat stops and another starts."""
    edges = []
    for (boundary,) in db.execute("select MultiPoint from DistributedRebar where SpanDirection=? and ElevationReference=?",
                                  (direction, reference)):
        polygon = points(boundary)
        for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
            run = math.hypot(bx - ax, by - ay)
            if run < 0.5:
                continue
            mx, my, nx, ny = (ax + bx) / 2, (ay + by) / 2, -(by - ay) / run, (bx - ax) / run
            if mesh.thickness(mx + nx * 1.5, my + ny * 1.5) is not None and mesh.thickness(mx - nx * 1.5, my - ny * 1.5) is not None:
                edges.append(((ax, ay), (bx, by)))
    return edges


def check(model: Path, table: Path) -> list[dict]:
    db = sqlite3.connect(f"file:{model.as_posix()}?immutable=1", uri=True)
    mesh = cr.Mesh(model)
    strips = read_table(table)
    lines = {name: (span_set, points(line)) for name, span_set, line in
             db.execute("select Name, SpanSet, MultiPoint from SpanDesign")}
    edges = {(d, face): mat_edges(db, mesh, d, ref)
             for d in (1, 2) for face, ref in (("top", TOP_COVER), ("bottom", BOTTOM_COVER))}
    program = {name: cr.bars(model, cr.Layer.parse(name), cr.PROGRAM) for name in ("bot-long", "bot-lat", "top-long", "top-lat")}
    found = []
    for name, sections in strips.items():
        if name not in lines or len(sections) < 3:
            continue
        span_set, line = lines[name]
        direction = 1 if span_set == "latitude" else 2
        p0, p1 = line[0], line[-1]
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        for face in ("bottom", "top"):
            layer_name = f"{'bot' if face == 'bottom' else 'top'}-{'lat' if direction == 1 else 'long'}"
            layer = cr.Layer.parse(layer_name)
            seen = []
            for a, b in edges[(direction, face)]:
                t = crossing(p0, p1, a, b)
                if t is None or any(abs(t - s) * length < 1.0 for s in seen):
                    continue
                seen.append(t)
                added = []
                for i in range(len(sections)):
                    f = i / (len(sections) - 1)
                    la, lb = layer.to_local(p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f)
                    added.append(any(d.a0 - 1 <= la <= d.a1 + 1 and d.b0 - 0.5 <= lb <= d.b1 + 0.5 for d in program[layer_name]))
                result = judge(sections, added, length, t, face)
                if result:
                    x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
                    found.append(dict(strip=name, direction=span_set, face=face, x=round(x, 1), y=round(y, 1),
                                      slab=(mesh.thickness(x, y)), **result))
    return found


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", type=Path)
    p.add_argument("table", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    found = check(a.model, a.table)
    print(f"{len(found)} strip crossings of a mat boundary checked")
    for face in ("bottom", "top"):
        for direction in ("longitude", "latitude"):
            rows = [f for f in found if f["face"] == face and f["direction"] == direction]
            count = lambda verdict: sum(1 for f in rows if f["verdict"] == verdict)
            print(f"{face:6s} {direction:9s}: {len(rows):3d} crossings | covered {count('covered'):3d} | "
                  f"notch only {count('notch only'):3d} | real {count('real'):3d} | no side {count('no side to compare'):3d}")
    for verdict in ("real", "notch only"):
        rows = sorted((f for f in found if f["verdict"] == verdict), key=lambda f: (f["direction"], f["face"], f["x"], f["y"]))
        print(f"\n{verdict}: {len(rows)}")
        for f in rows[:60]:
            side = f"mat capacity either side {f['side_capacity']:.0f} kip-ft" if f["side_capacity"] is not None else f.get("why", "")
            print(f"  {f['strip']:8s} {f['direction'][:4]} {f['face']:6s} at ({f['x']:.0f},{f['y']:.0f}), {f['slab']:g} in slab: "
                  f"demand {f['demand']:.0f} kip-ft, {side}")
    if a.out:
        a.out.write_text(json.dumps(found, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
