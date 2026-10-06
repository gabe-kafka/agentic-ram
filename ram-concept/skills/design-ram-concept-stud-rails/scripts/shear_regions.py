#!/usr/bin/env python3
"""One-way shear screening: sort the program's shear (stirrup) regions in a saved RAM Concept model by the office rule.

  python shear_regions.py <model.cpt> [--plan out.png] [--d-margin 2.5]

For every program stirrup region: where it is, its direction, length, legs and spacing, the nearest support
(column, wall or beam) and how far past that support's face the region reaches. Then the class:

  SSR       nearest support is a column with stud rails: set aside, checked through the rails
  OK by d   the region ends within about d of the support face (d = slab thickness - --d-margin, in inches)
  REQUIRED  everything else: stirrups to be provided in the real model (expect beam ends and wall corners)

Read-only. Meant for a model whose design strips were set to full width (the office screening copy); on the
real model it only describes what the program draws today. The support search and the d rule are
heuristics for the engineer to judge from, not a design check.
"""
from __future__ import annotations

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
    v = [float(x) for x in re.findall(r"\[(-?[\d.eE+]+)\]", text or "")]
    return [(a / FT, b / FT) for a, b in zip(v[0::2], v[1::2])]


def columns(db):
    return [(pts(p)[0][0], pts(p)[0][1], b / IN, d / IN) for p, b, d in db.execute("select Point0, B, D from Column")]


def rail_columns(db):
    return [pts(loc)[0] for (loc,) in db.execute("select LocationPoint from SsrSet")]


def segments(db, table):
    """(x0, y0, x1, y1, width in) for every wall or beam."""
    width = "WallThickness" if table == "Wall" else "Width"
    out = []
    for p0, p1, w in db.execute(f"select Point0, Point1, [{width}] from [{table}]"):
        (x0, y0), (x1, y1) = pts(p0)[0], pts(p1)[0]
        out.append((x0, y0, x1, y1, w / IN))
    return out


def regions(db):
    out = []
    for p0, p1, sdir, by, legs, spacing in db.execute(
            "select Point0, Point1, SpanDirection, DesignedBy, StirrupLegs, StirrupSpacing from TransverseRebarRegion"):
        if by != 2:                                  # user regions are the answer, not the question
            continue
        (x0, y0), (x1, y1) = pts(p0)[0], pts(p1)[0]
        out.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, along="x" if abs(x1 - x0) >= abs(y1 - y0) else "y",
                        length=math.hypot(x1 - x0, y1 - y0), legs=legs, spacing=spacing / IN,
                        by="user" if by == 1 else "program", sdir=sdir))
    return out


def seg_point_distance(x0, y0, x1, y1, px, py):
    dx, dy = x1 - x0, y1 - y0
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def span_interval(x0, y0, x1, y1, w, along):
    """The interval a wall or beam occupies along the span axis: its length if it runs that way, else its width."""
    runs_along = (abs(x1 - x0) > abs(y1 - y0)) == (along == "x")
    if runs_along:
        return (min(x0, x1), max(x0, x1)) if along == "x" else (min(y0, y1), max(y0, y1))
    c = (x0 + x1) / 2 if along == "x" else (y0 + y1) / 2
    return c - w / 24, c + w / 24


def classify(path: Path, d_margin_in: float = 2.5, reach_ft: float = 8.0):
    db = cr.connect(path)
    cols, rails = columns(db), rail_columns(db)
    walls, beams = segments(db, "Wall"), segments(db, "Beam")
    mesh = cr.Mesh(path)
    out = []
    for r in regions(db):
        mx, my = (r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2
        a0, a1 = (r["x0"], r["x1"]) if r["along"] == "x" else (r["y0"], r["y1"])      # region ends along the span
        lo, hi = min(a0, a1), max(a0, a1)
        across = my if r["along"] == "x" else mx                                       # the region's line across the span
        best = None                                                                   # (extent past face ft, kind, label)

        def consider(face_lo, face_hi, kind, label):
            nonlocal best
            if hi <= face_lo:
                ext = face_lo - lo
            elif lo >= face_hi:
                ext = hi - face_hi
            else:
                ext = max(face_lo - lo, hi - face_hi, 0.0)
            if best is None or ext < best[0]:
                best = (ext, kind, label)

        for cx, cy, b, d in cols:
            along_c, across_c = (cx, cy) if r["along"] == "x" else (cy, cx)
            half = (b if r["along"] == "x" else d) / 24
            if abs(across_c - across) > reach_ft or min(abs(along_c - lo), abs(along_c - hi)) > reach_ft:
                continue
            has_rails = any(math.hypot(cx - qx, cy - qy) < 1.0 for qx, qy in rails)
            consider(along_c - half, along_c + half,
                     "column with stud rails" if has_rails else "column, no stud rails", f"({cx:.0f},{cy:.0f})")
        for kind, segs in (("wall", walls), ("beam", beams)):
            for x0, y0, x1, y1, w in segs:
                if seg_point_distance(x0, y0, x1, y1, mx, my) > reach_ft:
                    continue
                f_lo, f_hi = span_interval(x0, y0, x1, y1, w, r["along"])
                consider(f_lo, f_hi, kind, f"{kind} ({(x0 + x1) / 2:.0f},{(y0 + y1) / 2:.0f})")
        t = mesh.thickness(mx, my)
        t_in = (t / IN if t and t > 100 else t) or 16.0            # the mesh helper may hold 0.1 mm or inches
        d_ft = max(t_in - d_margin_in, 4.0) / 12
        if best is None:
            klass, why = "REQUIRED", "no support within reach"
        elif best[1] == "column with stud rails":
            klass, why = "SSR", best[2]
        elif best[0] <= d_ft + 0.05:
            klass, why = "OK by d", f"{best[0] * 12:.0f} in past {best[2]}, d about {d_ft * 12:.0f} in"
        else:
            klass, why = "REQUIRED", f"{best[0] * 12:.0f} in past {best[2]}, d about {d_ft * 12:.0f} in"
        out.append(dict(r, mx=mx, my=my, klass=klass, why=why, support=best[1] if best else "", t_in=t_in))
    return out


def plan(found, path: Path, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    db = cr.connect(path)
    fig, ax = plt.subplots(figsize=(16, 16), dpi=110)
    for (mp,) in db.execute("select MultiPoint from SlabArea"):
        ax.add_patch(plt.Polygon(pts(mp), facecolor="#dfe7ee", edgecolor="#8aa0b4", lw=0.6, zorder=0))
    for (mp,) in db.execute("select MultiPoint from SlabOpening"):
        ax.add_patch(plt.Polygon(pts(mp), facecolor="white", edgecolor="#8aa0b4", lw=0.6, zorder=1))
    for x0, y0, x1, y1, w in segments(db, "Wall"):
        ax.plot([x0, x1], [y0, y1], color="#5c6770", lw=3, solid_capstyle="butt", zorder=2)
    for x0, y0, x1, y1, w in segments(db, "Beam"):
        ax.plot([x0, x1], [y0, y1], color="#b36b00", lw=4, alpha=0.6, zorder=2)
    rails = rail_columns(db)
    for cx, cy, b, d in columns(db):
        has = any(math.hypot(cx - qx, cy - qy) < 1.0 for qx, qy in rails)
        ax.add_patch(plt.Rectangle((cx - b / 24, cy - d / 24), b / 12, d / 12, facecolor="#e03131" if has else "#343a40", zorder=3))
    color = {"REQUIRED": "#c92a2a", "OK by d": "#2b8a3e", "SSR": "#e8590c"}
    for p0, p1, legs, sp in db.execute("select Point0, Point1, StirrupLegs, StirrupSpacing from TransverseRebarRegion where DesignedBy = 1"):
        (x0, y0), (x1, y1) = pts(p0)[0], pts(p1)[0]                 # user regions: magenta outline with the callout
        along_x = abs(x1 - x0) >= abs(y1 - y0)
        w = 1.4
        rect = (min(x0, x1), (y0 + y1) / 2 - w / 2, abs(x1 - x0), w) if along_x else ((x0 + x1) / 2 - w / 2, min(y0, y1), w, abs(y1 - y0))
        ax.add_patch(plt.Rectangle(rect[:2], rect[2], rect[3], facecolor="none", edgecolor="#d6336c", lw=1.8, zorder=6))
        ax.annotate(f"{legs}L @{sp / IN:.0f}\"", ((x0 + x1) / 2, (y0 + y1) / 2), fontsize=6, color="#d6336c", xytext=(3, -9), textcoords="offset points", zorder=7)
    for r in found:
        w = 1.0
        if r["along"] == "x":
            ax.add_patch(plt.Rectangle((min(r["x0"], r["x1"]), r["my"] - w / 2), r["length"], w, facecolor=color[r["klass"]], alpha=0.75, zorder=4))
        else:
            ax.add_patch(plt.Rectangle((r["mx"] - w / 2, min(r["y0"], r["y1"])), w, r["length"], facecolor=color[r["klass"]], alpha=0.75, zorder=4))
        if r["klass"] == "REQUIRED":
            ax.annotate(f"{r['legs']}L @{r['spacing']:.1f}\"  {r['length']:.0f}'", (r["mx"], r["my"]), fontsize=6, color="#c92a2a",
                        xytext=(3, 3), textcoords="offset points", zorder=5)
    for k, c in color.items():
        ax.plot([], [], color=c, lw=6, label=k)
    ax.plot([], [], "s", color="#e03131", label="column with stud rails")
    ax.plot([], [], color="#d6336c", lw=2, label="user stirrup region (legs @ spacing)")
    ax.legend(loc="lower left", fontsize=9)
    ax.set_aspect("equal")
    ax.autoscale()
    ax.set_title(f"{path.name}: program shear regions by the office one-way rule", fontsize=11)
    ax.set_xlabel("x (ft)")
    ax.set_ylabel("y (ft)")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print("plan:", out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", type=Path)
    p.add_argument("--plan", type=Path)
    p.add_argument("--d-margin", type=float, default=2.5, help="inches from slab thickness to d (default 2.5)")
    a = p.parse_args(argv)
    found = classify(a.model, a.d_margin)
    counts = {k: sum(1 for r in found if r["klass"] == k) for k in ("REQUIRED", "OK by d", "SSR")}
    print(f"{len(found)} program shear regions: {counts['REQUIRED']} required, {counts['OK by d']} OK by d, {counts['SSR']} at stud rail columns")
    for k in ("REQUIRED", "SSR", "OK by d"):
        rows = sorted((r for r in found if r["klass"] == k), key=lambda r: (round(r["my"]), r["mx"]))
        if k != "REQUIRED" and len(rows) > 25:
            print(f"  {k}: {len(rows)} regions (not listed)")
            continue
        for r in rows:
            print(f"  {k:8s} ({r['mx']:5.0f},{r['my']:5.0f}) along {r['along']} {r['length']:4.1f} ft  "
                  f"{r['legs']}L @ {r['spacing']:.2f} in  slab {r['t_in']:.0f} in  {r['why']}")
    if a.plan:
        plan(found, a.model, a.plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
