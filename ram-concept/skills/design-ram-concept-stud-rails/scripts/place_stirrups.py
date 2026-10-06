#!/usr/bin/env python3
"""Place user stirrup regions where the engineer marked them, by the office one-way shear rule.

  python place_stirrups.py <saved.cpt> <out.cpt> --box X0 X1 Y0 Y1 [--box ...] [--spacing 6] [--mat 12] [--bar "#4"] [--dry]

For every PROGRAM transverse rebar region in <saved.cpt> whose midpoint lies inside one of the boxes (ft, with a
1 ft margin): a USER region is added on the same line in the live API session, same span direction, bar --bar,
open stirrups, spacing --spacing in, legs = that span's column strip width / --mat spacing (rounded), minimum 2.
Then the model is saved to <out.cpt>. The program regions are left alone; the next calc regenerates them and
anything that is still drawn inside a box means the user region is not enough.

<saved.cpt> must be the model open in the session (the real model, strips on code slab). --dry prints the plan.
"""
import argparse
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "simplify-ram-concept-rebar" / "scripts"))
import cpt_reader as cr          # noqa: E402

FT, IN = 3048.0, 254.0


def pts(text):
    return [(float(a) / FT, float(b) / FT) for a, b in re.findall(r"\[(-?[\d.eE+]+)\]\[(-?[\d.eE+]+)\]", text or "")]


def dist_to_segment(x0, y0, x1, y1, px, py):
    dx, dy = x1 - x0, y1 - y0
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy))) if dx or dy else 0.0
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def nearest_on(poly, px, py):
    best = None
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy))) if dx or dy else 0.0
        q = (ax + t * dx, ay + t * dy)
        d = math.hypot(px - q[0], py - q[1])
        if best is None or d < best[0]:
            best = (d, q)
    return best[1] if best else None


def column_strips(db):
    out = []
    for p0, p1, lb, rb, seg in db.execute(
            "select Point0, Point1, ResistanceLeftBoundary, ResistanceRightBoundary, SpanSegment from SpanSegmentStrip where StripType = 'center'"):
        (x0, y0), (x1, y1) = pts(p0)[0], pts(p1)[0]
        out.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, left=pts(lb), right=pts(rb), seg=seg,
                        along="x" if abs(x1 - x0) >= abs(y1 - y0) else "y"))
    return out


def strip_width(strips, px, py, along):
    """Width of the nearest column strip running `along` at the point, and its distance."""
    best = None
    for s in strips:
        if s["along"] != along:
            continue
        d = dist_to_segment(s["x0"], s["y0"], s["x1"], s["y1"], px, py)
        if d > 9 or (best and d >= best[0]):
            continue
        l, r = nearest_on(s["left"], px, py), nearest_on(s["right"], px, py)
        if l and r:
            best = (d, math.hypot(l[0] - r[0], l[1] - r[1]), s)
    return best


def plan(model: Path, boxes, spacing_in, mat_in):
    db = cr.connect(model)
    strips = column_strips(db)
    spans = {uid: ss for uid, ss, _ in db.execute("select UID, SpanSet, ColumnStripWidthCalc from SpanSegment")}
    beam_spans = {uid for uid, _, calc in db.execute("select UID, SpanSet, ColumnStripWidthCalc from SpanSegment") if calc == "code-beam"}
    rows = []
    for p0, p1, sdir, by, legs, sp in db.execute(
            "select Point0, Point1, SpanDirection, DesignedBy, StirrupLegs, StirrupSpacing from TransverseRebarRegion"):
        if by != 2:
            continue
        (x0, y0), (x1, y1) = pts(p0)[0], pts(p1)[0]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        hit = next((b for b in boxes if b[0] - 1 <= mx <= b[1] + 1 and b[2] - 1 <= my <= b[3] + 1), None)
        if hit is None:
            continue
        along = "x" if abs(x1 - x0) >= abs(y1 - y0) else "y"
        found = strip_width(strips, mx, my, along)
        if found and found[2]["seg"] in beam_spans:
            print(f"  skipped ({mx:5.1f},{my:5.1f}): on a beam's own strip; the beam design covers it")
            continue
        width = found[1] if found else None
        n = max(2, round(width / (mat_in / 12))) if width else 2
        span_set = spans.get(found[2]["seg"], "latitude" if sdir == 1 else "longitude") if found else ("latitude" if sdir == 1 else "longitude")
        rows.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, mx=mx, my=my, along=along, length=math.hypot(x1 - x0, y1 - y0),
                         prog=f"{legs}L @ {sp / IN:.2f} in", width=width, legs=n, span_set=span_set, sdir=sdir, box=hit,
                         equiv=(sp / IN) * n / legs if legs else None))
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--box", type=float, nargs=4, action="append", metavar=("X0", "X1", "Y0", "Y1"), required=True)
    p.add_argument("--spacing", type=float, default=6.0, help="stirrup spacing along the span, in (default 6)")
    p.add_argument("--mat", type=float, default=12.0, help="mat bar spacing, in: one leg per mat bar (default 12)")
    p.add_argument("--bar", default="#4")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--port", type=int)
    a = p.parse_args(argv)
    rows = plan(a.model, a.box, a.spacing, a.mat)
    print(f"{len(rows)} program regions inside {len(a.box)} boxes -> user regions {a.bar}, {a.spacing:g} in o.c.:")
    for r in rows:
        w = f"{r['width']:.1f} ft" if r["width"] else "no strip found"
        eq = f", covers program up to {r['equiv']:.1f} in" if r["equiv"] else ""
        print(f"  ({r['mx']:5.1f},{r['my']:5.1f}) {r['span_set']:9s} along {r['along']} {r['length']:4.1f} ft  program {r['prog']:14s} strip {w:>14s} -> {r['legs']:2d} legs @ {a.spacing:g} in{eq}")
    if a.dry:
        return 0
    import simplify_rebar as sr
    model = sr.live_model(a.port)
    from ram_concept.enums import DesignedBy, SpanSet, StirrupShape
    from ram_concept.line_segment_2D import LineSegment2D
    from ram_concept.point_2D import Point2D
    layer = model.cad_manager.rebar_layer
    bar = next(b for b in model.rebars.rebars if b.name == a.bar)
    before = sum(len(layer.transverse_rebar(DesignedBy.USER, s)) for s in SpanSet)
    for r in rows:
        t = layer.add_transverse_rebar(LineSegment2D(Point2D(r["x0"], r["y0"]), Point2D(r["x1"], r["y1"])))
        t.span_set = SpanSet.LATITUDE if r["span_set"] == "latitude" else SpanSet.LONGITUDE
        t.designed_by = DesignedBy.USER
        t.bar_type = bar
        t.shape = StirrupShape.OPEN
        t.number_of_legs = r["legs"]
        t.fixed_spacing = True
        t.stirrup_spacing = a.spacing
    after = sum(len(layer.transverse_rebar(DesignedBy.USER, s)) for s in SpanSet)
    model.save_file(str(a.out))
    print(f"user transverse regions {before} -> {after}; saved {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
