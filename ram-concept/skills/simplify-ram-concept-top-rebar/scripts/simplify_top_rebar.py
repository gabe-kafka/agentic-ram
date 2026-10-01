#!/usr/bin/env python3
"""Replace RAM Concept program top bars over columns with typical count-based user groups.

Both directions in one work folder. Uses the engine in
``../simplify-ram-concept-rebar/scripts`` for the live session and .cpt reads.

  options  per direction, the cheapest schedules using 1 to 4 callouts (from base.cpt)
  plan     write the next plan:  --typical 10 15   (heavier columns keep their own count)
  apply    delete user top bars, draw one group per column per direction
  verify   calc, save round-N.cpt, report what the program still adds
  run      plan (when --typical is given) -> apply -> verify
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"
sys.path.insert(0, str(ENGINE))

import cpt_reader as cr          # noqa: E402
import rebar_groups as rg        # noqa: E402
import simplify_rebar as sr      # noqa: E402
import top_columns as tc         # noqa: E402

LAYERS = ("top-long", "top-lat")
FT = 3048.0


def columns_local(path: Path, layer: cr.Layer) -> list[tuple[float, float]]:
    out = []
    for (point,) in cr.connect(path).execute("select Point0 from Column"):
        x, y = (float(v) / FT for v in re.findall(r"\[([-\d.eE+]+)\]", point))
        out.append(layer.to_local(x, y))
    return out


def gather(path: Path, layer: cr.Layer):
    """Program top bars over each column, counted in the layer's dominant bar size."""
    demands = cr.bars(path, layer, cr.PROGRAM)
    size = cr.dominant_size(demands)
    for d in demands:
        if d.size != size:
            d.count = math.ceil(d.count * rg.BAR_AREA[d.size] / rg.BAR_AREA[size])
            d.size = size
    bars, loose = tc.assign(demands, columns_local(path, layer))
    return bars, loose, size


def _point(text: str) -> tuple[float, float]:
    x, y = (float(v) / FT for v in re.findall(r"\[([-\d.eE+]+)\]", text))
    return x, y


def beam_check(path: Path, reach: float = 1.5) -> tuple[int, int, list[tuple[float, float]]]:
    """Design spans along beams still on slab strip settings, all spans along beams, columns on beams."""
    db = cr.connect(path)
    beams = [(_point(a), _point(b)) for a, b in db.execute("select Point0, Point1 from Beam")]

    def beam_under(x, y):
        for (a, b), (c, d) in beams:
            length = math.hypot(c - a, d - b)
            if not length:
                continue
            s = max(0.0, min(1.0, ((x - a) * (c - a) + (y - b) * (d - b)) / length ** 2))
            if math.hypot(x - a - s * (c - a), y - b - s * (d - b)) <= reach:
                return (c - a) / length, (d - b) / length
        return None

    along = slab_set = 0
    for p0, p1, section in db.execute("select Point0, Point1, ColumnStripCrossSectionAutoTrim from SpanSegment"):
        (x0, y0), (x1, y1) = _point(p0), _point(p1)
        axis = beam_under((x0 + x1) / 2, (y0 + y1) / 2)
        span = math.hypot(x1 - x0, y1 - y0)
        if axis and span and abs((x1 - x0) * axis[0] + (y1 - y0) * axis[1]) / span > 0.95:
            along += 1
            slab_set += section == "slab rectangle"
    columns = [_point(p) for (p,) in db.execute("select Point0 from Column")]
    return slab_set, along, [c for c in columns if beam_under(*c)]


def warn_beams(path: Path) -> None:
    slab_set, along, columns = beam_check(path)
    if slab_set:
        print(f"WARNING: {slab_set} of {along} design spans along beams still use slab strip settings. "
              f"Set them to T or L beam and recalc first; the {len(columns)} columns on beams will change:")
        print("   " + ", ".join(f"({x:.0f},{y:.0f})" for x, y in columns))


def latest(work: Path, prefix: str, ext: str) -> int:
    nums = [int(m.group(1)) for p in work.glob(f"{prefix}-*.{ext}")
            if (m := re.fullmatch(rf"{prefix}-(\d+)\.{ext}", p.name))]
    return max(nums, default=0)


def loose_tons(loose) -> float:
    return sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in loose) / 2000


def cmd_options(a):
    base = a.work / "base.cpt"
    warn_beams(base)
    for name in LAYERS:
        bars, loose, size = gather(base, cr.Layer.parse(name))
        print(f"\n{name}: {len(bars)} columns with top demand, {size}; "
              f"{len(loose)} program groups not over a column ({loose_tons(loose):.1f} tons)")
        print(" types   tons   schedule")
        for row in tc.type_options(bars):
            text = "; ".join(f"{n}{size} x {length}' at {k}" for n, length, k in row["schedule"])
            print(f"   {row['types']}    {row['tons']:5.1f}   {text}")


def cmd_plan(a):
    base = a.work / "base.cpt"
    warn_beams(base)
    mesh = cr.Mesh(base)
    state = dict(typical=sorted(a.typical), layers={})
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        bars, loose, _ = gather(base, layer)
        on_slab = lambda p, q: mesh.thickness(*layer.to_plan(p, q)) is not None
        groups = tc.typed(bars, tuple(a.typical), on_slab)
        state["layers"][name] = [asdict(g) for g in groups]
        print(f"{name}: {len(groups)} columns, {tc.tons(groups):.1f} tons")
        for callout, k in tc.schedule(groups):
            print(f"   {callout} at {k}")
    n = latest(a.work, "columns-plan", "json") + 1
    (a.work / f"columns-plan-{n}.json").write_text(json.dumps(state, indent=1))
    sr.note(a.work, f"plan {n}: typical {state['typical']}")
    print(f"-> columns-plan-{n}.json")


def cmd_apply(a):
    model = sr.live_model(a.port)
    from ram_concept.line_segment_2D import LineSegment2D
    from ram_concept.point_2D import Point2D
    BarEnd, _, ElevationReference, SlabFace, SpanSet = sr.enums()
    n = latest(a.work, "columns-plan", "json")
    state = json.loads((a.work / f"columns-plan-{n}.json").read_text())
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        old = sr.user_bars(model, layer)
        for b in old:
            b.delete()
        groups = [tc.ColumnGroup(**g) for g in state["layers"][name]]
        for g in groups:
            mid = (g.a0 + g.a1) / 2
            b = model.cad_manager.rebar_layer.add_concentrated_rebar(
                LineSegment2D(Point2D(*layer.to_plan(mid, g.b1)), Point2D(*layer.to_plan(mid, g.b0))))
            b.span_set = SpanSet.LONGITUDE if layer.direction == "long" else SpanSet.LATITUDE
            b.slab_face = SlabFace.TOP
            b.bar_type = model.rebars.rebar(g.size)
            b.elevation_reference = ElevationReference.ABSOLUTE
            b.elevation_from_reference = g.elevation
            b.ending_anchorage_1 = BarEnd.STRAIGHT
            b.ending_anchorage_2 = BarEnd.STRAIGHT
            b.extent_zone_width = g.a1 - g.a0
            b.set_extent_zone_width_fractions(0.5)
            b.count = g.count
        print(f"{name}: replaced {len(old)} user groups with {len(groups)} column groups")
    sr.note(a.work, f"plan {n} applied")


def cmd_verify(a):
    model = sr.live_model(a.port)
    n = latest(a.work, "columns-plan", "json")
    state = json.loads((a.work / f"columns-plan-{n}.json").read_text())
    path = a.work / f"round-{n}.cpt"
    sr.note(a.work, f"round {n}: calc started")
    secs = sr.calc_and_save(model, path)
    print(f"round {n} (calc+save {secs:.0f}s)")
    for name in LAYERS:
        layer = cr.Layer.parse(name)
        groups = [tc.ColumnGroup(**g) for g in state["layers"][name]]
        bars, loose, size = gather(path, layer)
        s = rg.Settings(size=size)
        short = [c for c in bars if not (c.count <= s.peak_bars and c.length <= s.peak_length)]
        real_loose = [d for d in loose if not rg.is_peak(d, s)]
        left = len(bars) + len(loose)
        print(f"{name}: {len(groups)} column groups, {tc.tons(groups):.1f} tons; program left: {left} groups "
              f"({len(short)} real over columns, {len(real_loose)} real elsewhere, "
              f"{left - len(short) - len(real_loose)} peaking)")
        for c in short:
            x, y = layer.to_plan(c.a, c.b)
            print(f"   column at ({x:.1f},{y:.1f}) still needs {c.count}{size} x {c.length:.1f}'")
        for d in real_loose:
            print("   elsewhere", sr.describe(d, layer))
    sr.note(a.work, f"round {n} calc done in {secs:.0f}s")


def cmd_run(a):
    if a.typical:
        cmd_plan(a)
    cmd_apply(a)
    cmd_verify(a)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["options", "plan", "apply", "verify", "run"])
    p.add_argument("--work", required=True, type=Path, help="work folder holding base.cpt (no user top bars, calculated)")
    p.add_argument("--typical", type=int, nargs="+", help="typical bar counts, e.g. 10 15")
    p.add_argument("--port", type=int, help="API port (auto-detected when one session runs)")
    a = p.parse_args(argv)
    a.work = a.work.resolve()
    if a.command == "plan" and not a.typical:
        p.error("plan needs --typical")
    marker = a.work / ".working"
    marker.write_text(json.dumps(dict(pid=os.getpid(), t=time.time(), text=f"top columns {a.command}")))
    try:
        {"options": cmd_options, "plan": cmd_plan, "apply": cmd_apply, "verify": cmd_verify, "run": cmd_run}[a.command](a)
    finally:
        marker.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
