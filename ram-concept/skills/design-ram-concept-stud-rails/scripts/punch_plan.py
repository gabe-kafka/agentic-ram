#!/usr/bin/env python3
"""Plan of punching checks: which columns have the assumed opening, which do not, which have no check. punch_plan.py <model.cpt> <out.png>"""
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
ENGINE = Path(__file__).resolve().parents[2] / "simplify-ram-concept-rebar" / "scripts"
sys.path.insert(0, str(ENGINE))
argv = sys.argv[:]
sys.argv = ["x"]
import cpt_reader as cr          # noqa: E402
import stud_openings as so       # noqa: E402

model, out = Path(argv[1]), Path(argv[2])
db = cr.connect(model)
mesh = cr.Mesh(model)
cols = so.columns(model)
sets = so.rail_sets(model)
checks = [tuple(float(v) / 3048 for v in re.findall(r"\[(-?[\d.]+)\]", p)) + (r / 3048,)
          for p, r in db.execute("select Point0, MaxRadius from PunchCheck")]
openings = [so.pts(mp) for (mp,) in db.execute("select MultiPoint from SlabOpening")]
small = [(sum(q[0] for q in o) / len(o) / 3048, sum(q[1] for q in o) / len(o) / 3048) for o in openings
         if len(o) == 4 and max(q[0] for q in o) - min(q[0] for q in o) < 1.1 * 6 * 254]
near = lambda pts, x, y, d: any(math.hypot(px - x, py - y) < d for px, py in pts)

fig, ax = plt.subplots(figsize=(17, 18), dpi=120)
ax.add_collection(PolyCollection([poly for _, poly in mesh.elements], facecolors="#ececec", edgecolors="none"))
for p0, p1, w in db.execute("select Point0, Point1, Width from Beam"):
    (a, b), (c, d) = so.pts(p0)[0], so.pts(p1)[0]
    ax.plot([a / 3048, c / 3048], [b / 3048, d / 3048], color="#74a9e8", lw=5, solid_capstyle="butt", zorder=2)
n = dict(opening=0, none=0, nocheck=0)
for x, y, b, d, _ in cols:
    has_check = near([(c[0], c[1]) for c in checks], x, y, 1.0)
    has_open = near(small, x, y, 2.0)
    has_rails = near([(s["x"], s["y"]) for s in sets], x, y, 1.0)
    if not has_check:
        colour, key = "#9a9a9a", "nocheck"
    elif has_open:
        colour, key = "#1b8a3a", "opening"
    else:
        colour, key = "#d00000", "none"
    n[key] += 1
    ax.add_patch(plt.Rectangle((x - b / 24, y - d / 24), b / 12, d / 12, facecolor=colour, zorder=5))
    if has_check:
        r = next(c[2] for c in checks if math.hypot(c[0] - x, c[1] - y) < 1.0)
        ax.add_patch(plt.Circle((x, y), r, fill=False, edgecolor=colour, lw=0.9, alpha=0.55, zorder=3))
    if key == "none":
        ax.text(x + 2.2, y + 2.2, f"({x:.0f},{y:.0f})\nno opening:\nno stud rails needed", fontsize=8, color="#d00000", weight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#d00000", alpha=0.9))
    if has_rails:
        ax.plot(x, y, marker="+", color="white", markersize=6, zorder=6)
for px, py in small:                                          # the 6 in openings, drawn 5x so they can be seen
    ax.add_patch(plt.Rectangle((px - 1.25, py - 1.25), 2.5, 2.5, facecolor="#ffd43b", edgecolor="#8a6d00", lw=0.8, zorder=7))
xs = [p[0] for _, poly in mesh.elements for p in poly]
ys = [p[1] for _, poly in mesh.elements for p in poly]
ax.set_xlim(min(xs) - 8, max(xs) + 8)
ax.set_ylim(min(ys) - 8, max(ys) + 8)
ax.set_aspect("equal")
ax.set_xticks(range(int(min(xs) // 20 * 20), int(max(xs)) + 20, 20))
ax.set_yticks(range(int(min(ys) // 20 * 20), int(max(ys)) + 20, 20))
ax.grid(color="#aaaaaa", lw=0.3, alpha=0.5)
ax.set_xlabel("x (ft)")
ax.set_ylabel("y (ft)")
ax.set_title(f"Punching checks and assumed openings: {model.name}\n{len(checks)} checks, {len(small)} assumed 6 in openings (drawn 5x size)", fontsize=14)
ax.legend(handles=[
    Line2D([], [], marker="s", color="#1b8a3a", lw=0, markersize=10, label=f"punching check with an assumed opening: {n['opening']}"),
    Line2D([], [], marker="s", color="#d00000", lw=0, markersize=10, label=f"punching check, no opening (needs no stud rails): {n['none']}"),
    Line2D([], [], marker="s", color="#9a9a9a", lw=0, markersize=10, label=f"column with no punching check (on a beam; check deleted): {n['nocheck']}"),
    Line2D([], [], marker="s", color="#ffd43b", markeredgecolor="#8a6d00", lw=0, markersize=10, label="assumed opening"),
    Line2D([], [], color="#74a9e8", lw=5, label="concrete beam"),
    Line2D([], [], color="#555555", lw=0.9, label="circle = search radius"),
], loc="upper left", fontsize=10, framealpha=0.95)
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, bbox_inches="tight")
print(out, n)
