#!/usr/bin/env python3
"""2636 one-way shear, live API session: set every user slab stirrup zone to a fixed number of rows along the span,
keeping its support-face end, legs, bar and spacing. Gabe, 2026-10-07: "trim it, 10 rows everywhere, 15 at Z32".

  python live_set_rows.py --port N --saved <live.cpt> --rows 10 [--rows-at X Y N ...] --save <live.cpt> [--dry]

Length = (rows - 1) x spacing. The face end is the end point nearer a support (column, wall or beam) in the saved
file; the other end moves. --rows-at X Y N gives a zone (by its midpoint, within 1 ft) its own row count.
Replaces each zone through the API (delete, add), saves, then checks the saved file for two user zones in one
cross section before the calc (exit 5 and the model is left saved with the new zones, no calc). Beam stirrup
regions (closed) are not touched. The session stays open.
"""
import argparse, math, sys, time
from pathlib import Path

TOOLS = Path(Path(__file__).resolve().parents[2])
sys.path.insert(0, str(TOOLS / "simplify-ram-concept-rebar" / "scripts"))
sys.path.insert(1, str(TOOLS / "attach-ram-concept-api" / "scripts" / "api_vendor"))
sys.path.insert(2, str(TOOLS / "design-ram-concept-one-way-shear" / "scripts"))
sys.path.insert(3, str(sorted(Path(r"C:\Program Files\Bentley\Engineering\RAM Concept").glob("RAM Concept */python"))[-1]))
import shear_regions as sr      # noqa: E402
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

p = argparse.ArgumentParser()
p.add_argument("--port", type=int, required=True)
p.add_argument("--saved", type=Path, required=True, help="the session's last save, for the support geometry")
p.add_argument("--rows", type=int, required=True)
p.add_argument("--rows-at", type=float, nargs=3, action="append", default=[], metavar=("X", "Y", "N"))
p.add_argument("--save", type=Path, required=True)
p.add_argument("--dry", action="store_true")
p.add_argument("--no-calc", action="store_true")
a = p.parse_args()

db = sr.cr.connect(a.saved)
cols, walls, beams = sr.columns(db), sr.segments(db, "Wall"), sr.segments(db, "Beam")
db.close()      # an open handle on the file blocks Concept's save over it (seen 2026-10-07: SAVE_FILE failed)


def to_support(x, y):
    """Distance from a point to the nearest support edge (column rectangle, wall or beam centreline less half its width)."""
    best = min((max(abs(x - cx) - b / 24, 0) ** 2 + max(abs(y - cy) - d / 24, 0) ** 2) ** 0.5 for cx, cy, b, d in cols)
    for x0, y0, x1, y1, w in walls + beams:
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1e-9
        t = min(1.0, max(0.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        best = min(best, max(math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)) - w / 24, 0))
    return best


import simplify_rebar as srb
from ram_concept.enums import DesignedBy, SpanSet, StirrupShape
from ram_concept.line_segment_2D import LineSegment2D
from ram_concept.point_2D import Point2D

model = srb.live_model(a.port)
layer = model.cad_manager.rebar_layer
user = lambda: [t for sset in SpanSet for t in layer.transverse_rebar(DesignedBy.USER, sset)]
zones = [t for t in user() if t.shape == StirrupShape.OPEN]
before = len(user())
log(f"attached on port {a.port}: {before} user stirrup regions, {len(zones)} open slab zones")
plan = []
for t in zones:
    s, e = t.location.start_point, t.location.end_point
    mx, my = (s.x + e.x) / 2, (s.y + e.y) / 2
    rows = next((int(n) for x, y, n in a.rows_at if math.hypot(mx - x, my - y) <= 1.0), a.rows)
    length = (rows - 1) * t.stirrup_spacing / 12
    face, far = ((s, e) if to_support(s.x, s.y) <= to_support(e.x, e.y) else (e, s))
    L = math.hypot(far.x - face.x, far.y - face.y) or 1.0
    ux, uy = (far.x - face.x) / L, (far.y - face.y) / L
    new = (face.x, face.y, face.x + ux * length, face.y + uy * length)
    plan.append((t, new, rows))
    log(f"  ({mx:6.1f},{my:6.1f}) {t.span_set.name.lower():9s} {math.hypot(e.x - s.x, e.y - s.y):4.1f} ft -> {length:4.1f} ft ({rows} rows @{t.stirrup_spacing:g} in), "
        f"{t.number_of_legs}L, face end ({face.x:.2f},{face.y:.2f}) kept")
if a.dry:
    sys.exit(0)
for t, (x0, y0, x1, y1), rows in plan:
    span_set, bar, shape, legs, spacing = t.span_set, t.bar_type, t.shape, t.number_of_legs, t.stirrup_spacing
    t.delete()
    n = layer.add_transverse_rebar(LineSegment2D(Point2D(x0, y0), Point2D(x1, y1)))
    n.span_set, n.designed_by, n.bar_type, n.shape = span_set, DesignedBy.USER, bar, shape
    n.number_of_legs, n.fixed_spacing, n.stirrup_spacing = legs, True, spacing
assert len(user()) == before
model.calc_options.check_capacity_only = False
model.save_file(str(a.save))
log(f"saved {a.save.name} with {before} user stirrup regions")
import subprocess
r = subprocess.run([sys.executable, str(TOOLS / "design-ram-concept-one-way-shear" / "scripts" / "stirrup_collisions.py"), str(a.save)], capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode:
    log("COLLISION: not calculating; fix the zone first")
    sys.exit(5)
if a.no_calc:
    sys.exit(0)
log("calc all ...")
start = time.time()
model.calc_all(timeout_seconds=3600)
log(f"calc returned in {time.time() - start:.0f} s")
model.save_file(str(a.save))
log("saved", a.save.name, "after the calc")
