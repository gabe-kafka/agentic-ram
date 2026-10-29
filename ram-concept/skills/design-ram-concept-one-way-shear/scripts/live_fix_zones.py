#!/usr/bin/env python3
"""2636 one-way shear, live API session: replace several user stirrup zones in one go (each found by its current
endpoints), save, check collisions, Calc All, save.

  python live_fix_zones.py --port N --fixes fixes.json --save <file.cpt> [--no-calc]

fixes.json: list of {"label", "old": [x0,y0,x1,y1], "new": [x0,y0,x1,y1], "legs": L}. Span set, bar, shape and
spacing are kept from the old zone. Endpoints must match within 0.15 ft.
"""
import argparse, json, math, subprocess, sys, time
from pathlib import Path

TOOLS = Path(Path(__file__).resolve().parents[2])
sys.path.insert(0, str(TOOLS / "simplify-ram-concept-rebar" / "scripts"))
sys.path.insert(1, str(TOOLS / "attach-ram-concept-api" / "scripts" / "api_vendor"))
sys.path.insert(2, str(sorted(Path(r"C:\Program Files\Bentley\Engineering\RAM Concept").glob("RAM Concept */python"))[-1]))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
p = argparse.ArgumentParser()
p.add_argument("--port", type=int, required=True)
p.add_argument("--fixes", type=Path, required=True)
p.add_argument("--save", type=Path, required=True)
p.add_argument("--no-calc", action="store_true")
a = p.parse_args()
fixes = json.loads(a.fixes.read_text(encoding="utf-8"))

import simplify_rebar as srb
from ram_concept.enums import DesignedBy, SpanSet
from ram_concept.line_segment_2D import LineSegment2D
from ram_concept.point_2D import Point2D

model = srb.live_model(a.port)
layer = model.cad_manager.rebar_layer
user = lambda: [t for sset in SpanSet for t in layer.transverse_rebar(DesignedBy.USER, sset)]
before = len(user())
log(f"attached on port {a.port}: {before} user stirrup regions")
near = lambda q, x, y: math.hypot(q.x - x, q.y - y) <= 0.15
for f in fixes:
    o = f["old"]
    hit = [t for t in user() if (near(t.location.start_point, o[0], o[1]) and near(t.location.end_point, o[2], o[3]))
           or (near(t.location.start_point, o[2], o[3]) and near(t.location.end_point, o[0], o[1]))]
    if len(hit) != 1:
        raise SystemExit(f"{f['label']}: {len(hit)} zones match {o}; nothing more changed")
    t = hit[0]
    span_set, bar, shape, spacing, legs0 = t.span_set, t.bar_type, t.shape, t.stirrup_spacing, t.number_of_legs
    t.delete()
    n = f["new"]
    z = layer.add_transverse_rebar(LineSegment2D(Point2D(n[0], n[1]), Point2D(n[2], n[3])))
    z.span_set, z.designed_by, z.bar_type, z.shape = span_set, DesignedBy.USER, bar, shape
    z.number_of_legs, z.fixed_spacing, z.stirrup_spacing = f.get("legs", legs0), True, spacing
    log(f"{f['label']}: ({o[0]},{o[1]})-({o[2]},{o[3]}) {legs0}L -> ({n[0]},{n[1]})-({n[2]},{n[3]}) {z.number_of_legs}L, {math.hypot(n[2]-n[0], n[3]-n[1]):.1f} ft, {round(math.hypot(n[2]-n[0], n[3]-n[1]) * 12 / spacing) + 1} rows @{spacing:g} in")
assert len(user()) == before
model.calc_options.check_capacity_only = False
model.save_file(str(a.save))
log(f"saved {a.save.name}")
r = subprocess.run([sys.executable, str(TOOLS / "design-ram-concept-one-way-shear" / "scripts" / "stirrup_collisions.py"), str(a.save)], capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode:
    log("COLLISION: not calculating"); sys.exit(5)
if a.no_calc:
    sys.exit(0)
log("calc all ..."); start = time.time()
from ram_concept.model import CalcLevel
model.calc_partial(CalcLevel.DETAIL, skip_warnings=True, calc_only_out_of_date=True,
                   warnings_invalidate_calcs=False, timeout_seconds=3600)   # the engineer's bar-change calc: no analysis, no mesh
log(f"calc returned in {time.time() - start:.0f} s")
model.save_file(str(a.save))
log("saved", a.save.name, "after the calc")
