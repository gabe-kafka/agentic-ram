#!/usr/bin/env python3
"""Place user stirrup zones for slab one-way shear, by the office rule.

  python place_stirrups.py <saved.cpt> <out.cpt> --box X0 X1 Y0 Y1 [--box ...] [--around-beam-columns R]
                           [--spacing 6] [--mat 12] [--bar "#4"] [--replace] [--dry]

The program's stirrup regions in <saved.cpt> are joined into zones (shear_regions.chains: Concept draws one zone
as several short regions end to end). For every zone picked, ONE user region is added in the live API session
over the whole zone, from the support face to its far end: bar --bar, open stirrups, --spacing in along the
span, legs = the span's column strip width / --mat (rounded, minimum 2). Then the model is saved to <out.cpt>.

Which zones are picked:
  --box X0 X1 Y0 Y1          the engineer's marked box (ft, 1 ft margin): every zone with a region inside it.
                             His mark stands; the d rule is not applied.
  --around-beam-columns R    a box of half-size R ft around every column that sits on a beam (engineer's rule,
                             2026-10-06: target beam columns in every direction). Here a zone is picked when the
                             screening classes it REQUIRED: it reaches past about d from the face it starts at.
                             Zones that end within d, and zones starting at a stud rail column, are listed and
                             left out.
  Never picked: zones on a beam's centreline between its ends (the beam's own stirrups).

The d rule decides whether a location needs stirrups at all. Where it does, the zone runs from the support face;
the part inside d is not trimmed off. (A first version skipped the short region next to the face and left the
zone starting 1 to 2 ft out; the engineer caught it.)

Legs (Ryan Darling, team meeting 2026-10-06, confirmed by the engineer): one leg per mat bar across the strip, so
--mat is the mat bar spacing, default 12 (a 10 ft strip gets 10 legs). The earlier 6 by 6 in grid (--mat 6) is
superseded. Spacing: --spacing, reduced to whole inches within d/2 where the slab is thinner (a 12 in slab gets
4 in): stirrups wider apart than d/2 are not counted by the program.

--replace deletes every existing user transverse region first. <saved.cpt> must be the model open in the
session (the real model, strips on code slab). --dry prints the plan. After the calc, anything the program still
draws inside a picked zone means the user region is not enough.
"""
import argparse
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "simplify-ram-concept-rebar" / "scripts"))
import cpt_reader as cr          # noqa: E402
import shear_regions as srg      # noqa: E402

FT, IN = 3048.0, 254.0
D_MARGIN_IN = 2.5                # slab thickness to d


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


def beam_columns(db, slack_ft=0.5):
    """Columns whose centre sits on a beam line."""
    beams = srg.segments(db, "Beam")
    out = []
    for cx, cy, b, d in srg.columns(db):
        if any(dist_to_segment(x0, y0, x1, y1, cx, cy) <= w / 24 + slack_ft for x0, y0, x1, y1, w in beams):
            out.append((cx, cy))
    return out


def inside(box, x, y, margin=1.0):
    return box[0] - margin <= x <= box[1] + margin and box[2] - margin <= y <= box[3] + margin


def plan(model: Path, boxes, spacing_in, mat_in, around_beam_columns=None):
    """(rows to place, notes on what was left out)."""
    db = cr.connect(model)
    strips = column_strips(db)
    beam_spans = {uid for uid, calc in db.execute("select UID, ColumnStripWidthCalc from SpanSegment") if calc == "code-beam"}
    slab_strips = [s for s in strips if s["seg"] not in beam_spans]
    marked = list(boxes or [])
    auto = []
    if around_beam_columns:
        R = around_beam_columns
        auto = [(cx - R, cx + R, cy - R, cy + R) for cx, cy in beam_columns(db)]
    rows, notes = [], []
    for z in srg.classify(model):
        if z["klass"] == "BEAM":
            continue
        mids = [(p["mx"], p["my"]) for p in z["pieces"]]
        in_marked = any(inside(b, x, y) for b in marked for x, y in mids)
        in_auto = any(inside(b, x, y) for b in auto for x, y in mids)
        if not in_marked and not in_auto:
            continue
        where = f"({z['mx']:5.1f},{z['my']:5.1f}) along {z['along']} {z['length']:4.1f} ft"
        if not in_marked and z["klass"] != "REQUIRED":
            notes.append(f"left out {where}: {z['klass']}, {z['why']}")
            continue
        widths = []
        for x, y in mids:
            found = strip_width(strips, x, y, z["along"])
            if found and found[2]["seg"] in beam_spans and found[0] > found[1] / 2 + 0.5:     # beside a beam, outside its strip
                found = strip_width(slab_strips, x, y, z["along"]) or found                   # no slab strip near: the beam strip's width
            if found:
                widths.append(found[1])
        width = max(widths) if widths else None
        if width is None and in_marked:                                                       # no strip at all: the marked box's width
            b = next(b for b in marked if any(inside(b, x, y) for x, y in mids))
            width = (b[1] - b[0]) if z["along"] == "y" else (b[3] - b[2])
        n = max(2, round(width / (mat_in / 12))) if width else 2
        d_in = z["t_in"] - D_MARGIN_IN
        s = min(spacing_in, float(math.floor(d_in / 2)))
        tight = min(z["pieces"], key=lambda p: p["spacing"] / p["legs"])                 # the program's heaviest region
        equiv = tight["spacing"] * n / tight["legs"]
        rows.append(dict(x0=z["x0"], y0=z["y0"], x1=z["x1"], y1=z["y1"], mx=z["mx"], my=z["my"], along=z["along"],
                         length=z["length"], pieces=len(z["pieces"]), width=width, legs=n, spacing=s, t_in=z["t_in"],
                         span_set="latitude" if z["sdir"] == 1 else "longitude", klass=z["klass"], why=z["why"],
                         marked=in_marked, prog=f"{tight['legs']}L @ {tight['spacing']:.2f} in", equiv=equiv))
    return rows, notes


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--box", type=float, nargs=4, action="append", metavar=("X0", "X1", "Y0", "Y1"))
    p.add_argument("--around-beam-columns", type=float, metavar="R", help="also a box of half-size R ft around every column on a beam")
    p.add_argument("--spacing", type=float, default=6.0, help="stirrup spacing along the span, in (default 6; less where d/2 is less)")
    p.add_argument("--mat", type=float, default=12.0, help="leg spacing across the strip = mat bar spacing, in (default 12: one leg per mat bar)")
    p.add_argument("--replace", action="store_true", help="delete the existing user transverse regions first")
    p.add_argument("--bar", default="#4")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--port", type=int)
    a = p.parse_args(argv)
    if not a.box and not a.around_beam_columns:
        p.error("give --box and/or --around-beam-columns")
    rows, notes = plan(a.model, a.box, a.spacing, a.mat, a.around_beam_columns)
    print(f"{len(rows)} zones -> one user region each, {a.bar}, from the support face:")
    for r in sorted(rows, key=lambda r: (round(r["my"]), r["mx"])):
        w = f"{r['width']:.1f} ft" if r["width"] else "no strip"
        flag = "" if r["equiv"] >= r["spacing"] else "  LIGHT by area: the program's heaviest region wants more"
        src = "marked" if r["marked"] else "beam column"
        print(f"  ({r['mx']:5.1f},{r['my']:5.1f}) {r['span_set']:9s} {r['length']:4.1f} ft in {r['pieces']} piece(s), slab {r['t_in']:.0f} in, strip {w:>8s}"
              f" -> {r['legs']:2d} legs @ {r['spacing']:g} in  [{src}; program's heaviest {r['prog']}, matched down to {r['equiv']:.1f} in]{flag}")
    for n in notes:
        print("  " + n)
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
    if a.replace:
        for s in SpanSet:
            for t in list(layer.transverse_rebar(DesignedBy.USER, s)):
                t.delete()
        print(f"deleted {before} user transverse regions")
        before = 0
    for r in rows:
        t = layer.add_transverse_rebar(LineSegment2D(Point2D(r["x0"], r["y0"]), Point2D(r["x1"], r["y1"])))
        t.span_set = SpanSet.LATITUDE if r["span_set"] == "latitude" else SpanSet.LONGITUDE
        t.designed_by = DesignedBy.USER
        t.bar_type = bar
        t.shape = StirrupShape.OPEN
        t.number_of_legs = r["legs"]
        t.fixed_spacing = True
        t.stirrup_spacing = r["spacing"]
    after = sum(len(layer.transverse_rebar(DesignedBy.USER, s)) for s in SpanSet)
    model.save_file(str(a.out))
    print(f"user transverse regions {before} -> {after}; saved {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
