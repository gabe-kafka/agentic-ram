#!/usr/bin/env python3
"""Main model: program stirrup regions drawn BESIDE a user zone (parallel, 1 to 6 ft across, overlapping along), with
the span strip each one sits in. zones_check looks only on the zone's own line; this is the rest of the picture.

  python beside.py <calc.cpt> [--ids zone-ids.json]
"""
import json, math, re, sys
from pathlib import Path
S = Path(str(Path(__file__).resolve().parent))
sys.path.insert(0, str(S))
import shear_regions as sr

path = Path(sys.argv[1])
ids = json.loads(Path(sys.argv[sys.argv.index("--ids") + 1]).read_text(encoding="utf-8")) if "--ids" in sys.argv else {}
db = sr.cr.connect(path)
beams, cols, rails = sr.segments(db, "Beam"), sr.columns(db), sr.rail_columns(db)
pts = lambda t: [(float(a) / 3048, float(b) / 3048) for a, b in re.findall(r"\[(-?[\d.]+)\]\[(-?[\d.]+)\]", t or "")]
span_set = dict(db.execute("select Name, SpanSet from SpanDesign"))
strips = [(n, t, span_set.get(n), list(zip(pts(l), pts(r)))) for n, t, l, r in db.execute("select Name, StripType, ResistanceLeftBoundary, ResistanceRightBoundary from SpanSegmentStrip")]
SET = {1: "latitude", 2: "longitude"}


def crosses(a, b, c, d):
    o = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) <= 0 and o(c, d, a) * o(c, d, b) <= 0


def strip_of(r):
    a, b = (r["x0"], r["y0"]), (r["x1"], r["y1"])
    hits = {(n, t, round(math.hypot(l[0] - q[0], l[1] - q[1]), 1)) for n, t, ss, lines in strips if ss == SET[r["sdir"]] for l, q in lines if crosses(l, q, a, b)}
    return sorted(hits)


shapes = [s for (s,) in db.execute("select StirrupShape from TransverseRebarRegion where DesignedBy=1")]
users = [u for u, s in zip(sr.regions(db, designed_by=1), shapes) if s == 0]
prog = [p for p in sr.regions(db, designed_by=2) if not sr.on_beam(beams, p["mx"], p["my"])]
ssr = lambda p: any(math.hypot(p["mx"] - qx, p["my"] - qy) < 4 for qx, qy in rails)
n = 0
for u in sorted(users, key=lambda u: (round(u["my"] / 8), u["mx"])):
    key = ",".join(f"{v:.2f}" for v in (u["x0"], u["y0"], u["x1"], u["y1"]))
    zid = ids.get(key, "?")
    near = [p for p in prog if p["along"] == u["along"] and 1.0 < abs(p["across"] - u["across"]) <= 6.0 and p["lo"] <= u["hi"] + 3 and p["hi"] >= u["lo"] - 3]
    if not near:
        continue
    n += 1
    us = strip_of(u)
    print(f"{zid:4s} ({u['mx']:.1f},{u['my']:.1f}) along {u['along']} {u['lo']:.1f}-{u['hi']:.1f} at {u['across']:.2f}, {u['legs']}L @{u['spacing']:g}  in strip(s) {[(s[0], s[1], s[2]) for s in us]}")
    for p in sorted(near, key=lambda p: p["across"]):
        print(f"      program at {p['across']:.2f} ({p['across'] - u['across']:+.1f} ft across): {p['lo']:.1f}-{p['hi']:.1f} ({p['length']:.1f} ft) {p['legs']}L @{p['spacing']:.2f} in"
              f"{'  [stud rail column nearby]' if ssr(p) else ''}  strip(s) {strip_of(p)}")
print(f"\n{n} of {len(users)} zones have program stirrups beside them")
