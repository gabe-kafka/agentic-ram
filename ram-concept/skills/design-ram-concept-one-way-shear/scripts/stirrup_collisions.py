#!/usr/bin/env python3
"""Design cross sections that hold more than one user stirrup region. Concept stops the calc on the first one
("<strip> contains multiple user transverse reinforcement regions"); this lists them all from a saved file.

  python stirrup_collisions.py <model.cpt>        read-only; exit 1 when any are found

A region is in a cross section when it runs the same way as the strip's span set and its line crosses the
section line (the strip's left to right resistance boundary at that station). Checked on 2636: no collisions
in Gabe's production file, and the two Concept reported in the merged file are both found.
"""
import re, sqlite3, sys
from collections import defaultdict
from pathlib import Path

FT = 3048.0
db = sqlite3.connect(f"file:{Path(sys.argv[1]).as_posix()}?immutable=1", uri=True)
pts = lambda t: [(float(a) / FT, float(b) / FT) for a, b in re.findall(r"\[(-?[\d.]+)\]\[(-?[\d.]+)\]", t or "")]
span_set = dict(db.execute("select Name, SpanSet from SpanDesign"))
SET = {1: "latitude", 2: "longitude"}
regions = [(pts(p0)[0], pts(p1)[0], SET[sd], legs, sp / 254, "closed" if shape else "open")
           for p0, p1, sd, legs, sp, shape in db.execute(
               "select Point0, Point1, SpanDirection, StirrupLegs, StirrupSpacing, StirrupShape from TransverseRebarRegion where DesignedBy=1")]


def crosses(a, b, c, d):
    o = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) <= 0 and o(c, d, a) * o(c, d, b) <= 0


found = defaultdict(list)                      # (strip, frozenset of region indices) -> section lines
for name, left, right in db.execute("select Name, ResistanceLeftBoundary, ResistanceRightBoundary from SpanSegmentStrip"):
    for l, r in zip(pts(left), pts(right)):
        inside = frozenset(i for i, q in enumerate(regions) if q[2] == span_set.get(name) and crosses(l, r, q[0], q[1]))
        if len(inside) > 1:
            found[(name, inside)].append((l, r))
print(f"{len(regions)} user stirrup regions; {len(found)} collisions")
for (name, inside), lines in sorted(found.items()):
    l, r = lines[0]
    print(f"  strip {name} ({span_set[name]}), {len(lines)} section(s), first ({l[0]:.1f},{l[1]:.1f}) to ({r[0]:.1f},{r[1]:.1f}), "
          f"strip width {((l[0] - r[0]) ** 2 + (l[1] - r[1]) ** 2) ** 0.5:.1f} ft")
    for i in sorted(inside):
        a, b, _, legs, sp, shape = regions[i]
        print(f"      ({a[0]:.2f},{a[1]:.2f}) to ({b[0]:.2f},{b[1]:.2f}), {((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5:.1f} ft, "
              f"{legs} legs @ {sp:g} in, {shape}; midpoint {(a[0] + b[0]) / 2:.2f},{(a[1] + b[1]) / 2:.2f}")
sys.exit(1 if found else 0)
