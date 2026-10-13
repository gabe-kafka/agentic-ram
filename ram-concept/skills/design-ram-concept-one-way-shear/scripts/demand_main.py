#!/usr/bin/env python3
"""2636 one-way shear, main model: for each locked zone, the program's own demand on its line (from the baseline calc
with no slab zones), the zone as it is now, and the rows it needs. Read-only.

  python demand_main.py <zones.cpt> <baseline-nozones.cpt> [--ids zone-ids.json] [--json out.json]

Demand = the furthest point from the zone's support-face end that the baseline program draws stirrups on the zone's
line (within 1.5 ft across), chaining regions with gaps up to 1 ft. Rows = ceil(demand / spacing) + 1.
"""
import json, math, sys
from pathlib import Path
S = Path(str(Path(__file__).resolve().parent))
sys.path.insert(0, str(S))
import shear_regions as sr

zones_path, base_path = Path(sys.argv[1]), Path(sys.argv[2])
ids = json.loads(Path(sys.argv[sys.argv.index("--ids") + 1]).read_text(encoding="utf-8")) if "--ids" in sys.argv else {}
db = sr.cr.connect(zones_path)
cols, walls, beams = sr.columns(db), sr.segments(db, "Wall"), sr.segments(db, "Beam")
mesh = sr.cr.Mesh(zones_path)
users = [u for u in sr.regions(db, designed_by=1)]
shapes = [s for (s,) in db.execute("select StirrupShape from TransverseRebarRegion where DesignedBy=1")]
users = [u for u, s in zip(users, shapes) if s == 0]
db.close()
bdb = sr.cr.connect(base_path)
prog = [p for p in sr.regions(bdb, designed_by=2) if not sr.on_beam(beams, p["mx"], p["my"])]
bdb.close()


def to_support(x, y):
    best = min((max(abs(x - cx) - b / 24, 0) ** 2 + max(abs(y - cy) - d / 24, 0) ** 2) ** 0.5 for cx, cy, b, d in cols)
    for x0, y0, x1, y1, w in walls + beams:
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1e-9
        t = min(1.0, max(0.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        best = min(best, max(math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)) - w / 24, 0))
    return best


out = []
print(" zone   dir        now     legs @in  face end           demand (baseline)   rows now -> needed")
for u in sorted(users, key=lambda u: (round(u["my"] / 8), u["mx"])):
    key = ",".join(f"{v:.2f}" for v in (u["x0"], u["y0"], u["x1"], u["y1"]))
    zid = ids.get(key, "?")
    a, b = (u["x0"], u["y0"]), (u["x1"], u["y1"])
    face, far = (a, b) if to_support(*a) <= to_support(*b) else (b, a)
    ux, uy = ((far[0] - face[0]) / u["length"], (far[1] - face[1]) / u["length"]) if u["length"] else (0, 1)
    # baseline program regions on the line, projected onto the zone's direction from the face
    along = []
    for p in prog:
        if p["along"] != u["along"] or abs(p["across"] - u["across"]) > 1.5:
            continue
        for q in ((p["x0"], p["y0"]), (p["x1"], p["y1"])):
            along.append((((q[0] - face[0]) * ux + (q[1] - face[1]) * uy), p))
    # chain outward from the face: pieces whose near end is within 1 ft of the covered extent so far
    pieces = sorted({id(p): p for s, p in along}.values(), key=lambda p: min(((q[0] - face[0]) * ux + (q[1] - face[1]) * uy) for q in ((p["x0"], p["y0"]), (p["x1"], p["y1"]))))
    reach, used = 0.0, []
    for p in pieces:
        s0, s1 = sorted(((q[0] - face[0]) * ux + (q[1] - face[1]) * uy) for q in ((p["x0"], p["y0"]), (p["x1"], p["y1"])))
        if s1 < -1.0:
            continue                       # behind the face
        if s0 <= reach + 1.0:
            reach = max(reach, s1); used.append(p)
    t = mesh.thickness(u["mx"], u["my"]); t_in = (t / 254 if t and t > 100 else t) or 16.0
    sp = u["spacing"]
    rows_now = round(u["length"] * 12 / sp) + 1
    rows_need = math.ceil(reach * 12 / sp) + 1 if reach > 0 else 0
    heaviest = max((p["spacing"] for p in used), default=None)
    heavy = min((p["spacing"] for p in used), default=None)
    print(f"  {zid:4s} {('x' if u['along'] == 'x' else 'y'):3s} {u['length']:5.1f} ft  {u['legs']:3d} @{sp:g}  ({face[0]:6.1f},{face[1]:6.1f})  "
          f"{reach:5.1f} ft in {len(used)} piece(s){(' heaviest 2L @%.1f in' % heavy) if heavy else ''}   {rows_now:3d} -> {rows_need:3d}"
          + ("   SHORT" if rows_need > rows_now else ("   over by %d rows" % (rows_now - rows_need) if rows_now > rows_need else "")))
    out.append(dict(id=zid, x0=u["x0"], y0=u["y0"], x1=u["x1"], y1=u["y1"], along=u["along"], legs=u["legs"], spacing=sp, face=face, far=far,
                    length=u["length"], demand=reach, rows_now=rows_now, rows_need=rows_need, t_in=t_in))
if "--json" in sys.argv:
    Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
tot_now = sum(r["legs"] * r["rows_now"] for r in out)
tot_need = sum(r["legs"] * max(r["rows_need"], 2) for r in out)
print(f"\n#4 stirrup legs: now {tot_now}, at the main-model demand {tot_need}")
