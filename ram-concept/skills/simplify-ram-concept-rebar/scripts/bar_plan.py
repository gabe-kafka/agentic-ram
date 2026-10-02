#!/usr/bin/env python3
"""Draw one layer's bar layout from a saved .cpt, with callouts as the office writes them.

  python bar_plan.py <model.cpt> <layer> <out.png> [job folder]

layer is bot-long, bot-lat, top-long or top-lat. The job folder holds
decisions.json (default: two levels above the model). Read-only; needs no
Concept session and no display, so it works when the PC is locked.
Needs matplotlib.
"""
import math
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

SKILLS = Path(__file__).resolve().parents[2]
for d in ("set-ram-concept-beam-strips", "clean-up-ram-concept-t-beams"):
    sys.path.insert(0, str(SKILLS / d / "scripts"))
import beam_rules as br          # noqa: E402
import cpt_reader as cr          # noqa: E402
import t_beam_cleanup as tb      # noqa: E402

model, name, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
job = Path(sys.argv[4]) if len(sys.argv) > 4 else model.parent.parent
layer = cr.Layer.parse(name)
db = cr.connect(model)
mesh = cr.Mesh(model)

fig, ax = plt.subplots(figsize=(24, 26), dpi=140)
shade = {th: c for th, c in zip(sorted({th for th, _ in mesh.elements}), ("#f1f1f1", "#e4e4e4", "#d6d6d6", "#c8c8c8", "#bababa"))}
for th in shade:
    ax.add_collection(PolyCollection([poly for t, poly in mesh.elements if t == th], facecolors=shade[th], edgecolors="none"))

wall_cols = [r[1] for r in db.execute("pragma table_info(Wall)")]
where = next((c for c in wall_cols if db.execute(f"select count(*) from Wall where [{c}] in ('below','above')").fetchone()[0]), None)
for p0, p1, pos in db.execute(f"select Point0, Point1, {where or chr(39) + 'below' + chr(39)} from Wall"):
    (x0, y0), (x1, y1) = cr._points(p0 + p1)
    if pos == "below":
        ax.plot([x0, x1], [y0, y1], color="#555555", lw=2.6, solid_capstyle="butt", zorder=2)
for (a, b), (c, d), w in tb.beams(model):
    run = math.hypot(c - a, d - b)
    nx, ny = -(d - b) / run * w / 2, (c - a) / run * w / 2
    ax.add_patch(plt.Polygon([(a + nx, b + ny), (c + nx, d + ny), (c - nx, d - ny), (a - nx, b - ny)],
                             facecolor="#9ec9f5", edgecolor="#2f6fb0", lw=0.8, zorder=2))
cols = tb.columns(model)
for x, y in cols:
    ax.add_patch(Rectangle((x - 1, y - 1), 2, 2, facecolor="black", zorder=8))
placed = list(cols)                                           # label positions and columns to keep clear of


def rect(d):
    (x0, y0), (x1, y1) = layer.to_plan(d.a0, d.b0), layer.to_plan(d.a1, d.b1)
    return min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)


def draw(d, colour, text, fill=0.22, size=7.5, lw=1.3, z=4, at=0.5):
    x, y, w, h = rect(d)
    ax.add_patch(Rectangle((x, y), w, h, facecolor=colour, alpha=fill, edgecolor="none", zorder=z))
    ax.add_patch(Rectangle((x, y), w, h, facecolor="none", edgecolor=colour, lw=lw, zorder=z + 1))
    mid = (d.a0 + d.a1) / 2                                   # the bar itself, along its length
    (bx0, by0), (bx1, by1) = layer.to_plan(mid, d.b0), layer.to_plan(mid, d.b1)
    ax.plot([bx0, bx1], [by0, by1], color=colour, lw=lw + 0.6, zorder=z + 1)
    if text:
        turn = 90 if h > w * 1.3 and len(text) > 5 else 0
        if at is None:                                        # the spot inside the group farthest from other labels
            spots = [layer.to_plan(d.a0 + (d.a1 - d.a0) * i / 6, d.b0 + (d.b1 - d.b0) * j / 12)
                     for i in range(1, 6) for j in range(1, 12)]
            tx, ty = max(spots, key=lambda s: min(math.dist(s, q) for q in placed))
        else:
            tx, ty = layer.to_plan(mid, d.b0 + (d.b1 - d.b0) * at)
        placed.append((tx, ty))
        ax.text(tx, ty, text, ha="center", va="center", fontsize=size, rotation=turn, color="black",
                zorder=9, bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.8))


spacing = {}
for p0, p1, sp, uses in db.execute("select Point0, Point1, BarSpacing, BarUsesSpacing from ConcentratedRebar"):
    spacing[tuple(round(v, 2) for pt in cr._points(p0 + p1) for v in pt)] = sp / cr.IN

user, program = cr.bars(model, layer, cr.USER), cr.bars(model, layer, cr.PROGRAM)
counts = [d for d in user if d.by_count]
bands = [d for d in user if not d.by_count]
typical = [n for n, _ in Counter(d.count for d in counts).most_common(2)]
palette = dict(zip(sorted(typical), ("#e8590c", "#c2255c")))
OWN, BAND, PROGRAM, NONE = "#7b2cbf", "#087f5b", "#c9a400", "#d00000"
feet = lambda d: math.ceil(d.length - 0.1)

for d in program:
    draw(d, PROGRAM, f"{d.count}{d.size}", fill=0.45, size=6, lw=0.8, z=3, at=0.15)
schedule = Counter()
for d in counts:
    callout = f"{d.count}{d.size} x {feet(d)}'"
    schedule[(d.count in palette, d.count, callout)] += 1
    draw(d, palette.get(d.count, OWN), f"{d.count}{d.size}" if d.count in palette else callout, at=0.8)
band_text = Counter()
for d in sorted(bands, key=lambda d: (d.a1 - d.a0) * d.length):
    (x0, y0), (x1, y1) = layer.to_plan((d.a0 + d.a1) / 2, d.b0), layer.to_plan((d.a0 + d.a1) / 2, d.b1)
    key = min(spacing, key=lambda k: min(math.dist(k[:2], (x0, y0)) + math.dist(k[2:], (x1, y1)),
                                         math.dist(k[:2], (x1, y1)) + math.dist(k[2:], (x0, y0))))
    callout = f'{d.size} @{spacing[key]:.0f}"'
    band_text[callout] += 1
    draw(d, BAND, f"{callout} x {feet(d)}'", at=None)

through = [cols[i] for i in sorted(tb.through_columns(model, layer))] if layer.face == "top" else []
marks = [(x, y, tb.THROUGH) for x, y in through]
marks += [(o["x"], o["y"], o["reason"]) for o in br.overrides(job, layer.name)
          if not any(math.hypot(o["x"] - x, o["y"] - y) < 1 for x, y, _ in marks)]
for x, y, reason in marks:
    ax.plot(x, y, marker="X", color=NONE, markersize=17, markeredgecolor="white", zorder=10)
    ax.text(x + 3, y + 3, f"no {layer.face} bar called out:\n{reason}", fontsize=7.5, color=NONE, zorder=10, weight="bold",
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor=NONE, alpha=0.9))

xs = [p[0] for _, poly in mesh.elements for p in poly]
ys = [p[1] for _, poly in mesh.elements for p in poly]
ax.set_xlim(min(xs) - 8, max(xs) + 8)
ax.set_ylim(min(ys) - 8, max(ys) + 8)
ax.set_aspect("equal")
ax.set_xticks(range(int(min(xs) // 20 * 20), int(max(xs)) + 20, 20))
ax.set_yticks(range(int(min(ys) // 20 * 20), int(max(ys)) + 20, 20))
ax.grid(color="#999999", lw=0.3, alpha=0.5)
ax.tick_params(labelsize=9)
ax.set_xlabel("x (ft)")
ax.set_ylabel("y (ft)")
run = "bars run north-south" if layer.direction == "long" else "bars run east-west"
face = "Top" if layer.face == "top" else "Bottom"
ax.set_title(f"{face} bars, {'longitude' if layer.direction == 'long' else 'latitude'} ({run})\n"
             f"{model.parent.name}/{model.name}: {len(counts)} groups by count, {len(bands)} bands by spacing, "
             f"{len(program)} program bars left", fontsize=15)

legend = []
for (is_typical, n, callout), k in sorted(schedule.items(), key=lambda kv: (not kv[0][0], kv[0][1])):
    if is_typical:
        legend.append(Patch(facecolor=palette[n], alpha=0.5, label=f"{callout}: {k}"))
own = sum(k for (is_typical, _, _), k in schedule.items() if not is_typical)
if own:
    legend.append(Patch(facecolor=OWN, alpha=0.5, label=f"own count (labelled): {own}"))
if bands:
    legend.append(Patch(facecolor=BAND, alpha=0.5, label="bands by spacing: " + ", ".join(
        f"{c} at {k}" for c, k in sorted(band_text.items(), key=lambda kv: -float(kv[0].split("@")[1][:-1])))))
legend.append(Patch(facecolor=PROGRAM, alpha=0.6, label=f"program bars left (yellow in Concept): {len(program)}"))
if marks:
    legend.append(Line2D([], [], marker="X", color=NONE, lw=0, markersize=11, label="override: no bar called out"))
legend += [Patch(facecolor="#9ec9f5", edgecolor="#2f6fb0", label="concrete beam"),
           Line2D([], [], color="#555555", lw=2.6, label="wall below"),
           Line2D([], [], marker="s", color="black", lw=0, label="column")]
ax.legend(handles=legend, loc="upper left", fontsize=10, framealpha=0.95, title="Callouts", title_fontsize=11)
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, bbox_inches="tight")
print(out, f"{len(counts)} count groups, {len(bands)} bands, {len(program)} program, {len(marks)} overrides")
