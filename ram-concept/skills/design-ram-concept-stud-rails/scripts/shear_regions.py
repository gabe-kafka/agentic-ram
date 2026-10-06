#!/usr/bin/env python3
"""One-way shear screening: sort the program's shear (stirrup) regions in a saved RAM Concept model by the office rule.

  python shear_regions.py <model.cpt> [--plan out.png] [--pieces]

Concept draws one stirrup zone as several short regions end to end, each with its own spacing. They are first
joined into chains: one chain is one location. Then each chain gets a class:

  BEAM      on a beam's centreline between its ends: the beam's own stirrups, not a slab zone
  SSR       the chain starts at a column that has stud rails: set aside, checked through the rails
  OK by d   the WHOLE chain ends within about d of the support face it starts from. Shear is checked at d from
            the face, so stirrups that exist only inside that distance are not required. The office judgement
            is 18 in of stirrups in a 16 in slab: 1.125 x the slab thickness.
  REQUIRED  the chain reaches further. The whole chain is then required, from the support face out: the d rule
            decides whether a location needs stirrups, it never trims the part of a required zone inside d.

A support is something the chain's own line runs into: a column on the line, a wall or beam crossing it, or
the end of a wall or beam lying along it. A wall or beam off to the side is not a support for that line.

Known limit (2636, 2026-10-06): on a full-width screening copy the program draws its regions at the middle of
the wide strip, off the column lines, so the support search misses and such zones come out REQUIRED with "no
support on its line". The by-zone count is too high there (41 against 22 by eye). Trust it on the real model
(code-slab strips); on the screening copy treat "no support" zones as unsorted.

Read-only. On the real model it describes what the program draws today. Heuristics for the engineer to judge from, not a
design check. --pieces lists the single regions instead of chains.
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
D_FACTOR = 1.125          # a chain is "within d" when it ends within this x slab thickness of the face (18 in for 16 in)


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


def regions(db, designed_by=2):
    """Transverse rebar regions drawn by the program (2) or the user (1)."""
    out = []
    for p0, p1, sdir, by, legs, spacing in db.execute(
            "select Point0, Point1, SpanDirection, DesignedBy, StirrupLegs, StirrupSpacing from TransverseRebarRegion"):
        if by != designed_by:
            continue
        (x0, y0), (x1, y1) = pts(p0)[0], pts(p1)[0]
        along = "x" if abs(x1 - x0) >= abs(y1 - y0) else "y"
        lo, hi = (min(x0, x1), max(x0, x1)) if along == "x" else (min(y0, y1), max(y0, y1))
        out.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, along=along, lo=lo, hi=hi,
                        across=(y0 + y1) / 2 if along == "x" else (x0 + x1) / 2,
                        mx=(x0 + x1) / 2, my=(y0 + y1) / 2, length=math.hypot(x1 - x0, y1 - y0),
                        legs=legs, spacing=spacing / IN, sdir=sdir))
    return out


def on_beam(beams, px, py, slack_ft=0.3):
    """True when the point lies in a beam's web between the beam's ends (not past an end)."""
    for x0, y0, x1, y1, w in beams:
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if not L2:
            continue
        t = ((px - x0) * dx + (py - y0) * dy) / L2
        if 0.0 <= t <= 1.0 and math.hypot(px - (x0 + t * dx), py - (y0 + t * dy)) <= w / 24 + slack_ft:
            return True
    return False


def chains(pieces, gap_ft=0.75, across_tol_ft=1.0):
    """Join regions that continue one another along the same line into chains (one chain = one stirrup zone)."""
    out = []
    for along in ("x", "y"):
        open_chains = []
        for r in sorted((p for p in pieces if p["along"] == along), key=lambda p: p["lo"]):
            for ch in open_chains:
                if abs(r["across"] - ch["across"]) <= across_tol_ft and r["lo"] <= ch["hi"] + gap_ft:
                    total = ch["length"] + r["length"]
                    ch["across"] = (ch["across"] * ch["length"] + r["across"] * r["length"]) / total if total else ch["across"]
                    ch["hi"] = max(ch["hi"], r["hi"])
                    ch["length"] = ch["hi"] - ch["lo"]
                    ch["pieces"].append(r)
                    break
            else:
                open_chains.append(dict(along=along, lo=r["lo"], hi=r["hi"], across=r["across"], length=r["hi"] - r["lo"], pieces=[r]))
        out += open_chains
    for ch in out:
        if ch["along"] == "x":
            ch.update(x0=ch["lo"], x1=ch["hi"], y0=ch["across"], y1=ch["across"])
        else:
            ch.update(x0=ch["across"], x1=ch["across"], y0=ch["lo"], y1=ch["hi"])
        ch.update(mx=(ch["x0"] + ch["x1"]) / 2, my=(ch["y0"] + ch["y1"]) / 2, sdir=ch["pieces"][0]["sdir"],
                  legs=max(p["legs"] for p in ch["pieces"]), spacing=min(p["spacing"] for p in ch["pieces"]))
    return out


def nearest_support(ch, cols, rails, walls, beams, across_tol_ft=1.5, reach_ft=8.0):
    """(reach past the face ft, kind, label) for the support on the chain's line that it reaches least far past."""
    along, lo, hi, c = ch["along"], ch["lo"], ch["hi"], ch["across"]
    best = None

    def consider(f_lo, f_hi, kind, label):
        nonlocal best
        if f_hi < lo - reach_ft or f_lo > hi + reach_ft:
            return
        if hi <= f_lo:
            ext = f_lo - lo
        elif lo >= f_hi:
            ext = hi - f_hi
        else:
            ext = max(f_lo - lo, hi - f_hi, 0.0)
        if best is None or ext < best[0]:
            best = (ext, kind, label)

    for cx, cy, b, d in cols:
        a_c, x_c = (cx, cy) if along == "x" else (cy, cx)
        half_a, half_x = ((b, d) if along == "x" else (d, b))
        if abs(x_c - c) <= half_x / 24 + across_tol_ft:
            has = any(math.hypot(cx - qx, cy - qy) < 1.0 for qx, qy in rails)
            consider(a_c - half_a / 24, a_c + half_a / 24, "column with stud rails" if has else "column, no stud rails", f"({cx:.0f},{cy:.0f})")
    for kind, segs in (("wall", walls), ("beam", beams)):
        for x0, y0, x1, y1, w in segs:
            a0, a1, q0, q1 = (x0, x1, y0, y1) if along == "x" else (y0, y1, x0, x1)       # along and across coordinates
            label = f"{kind} ({(x0 + x1) / 2:.0f},{(y0 + y1) / 2:.0f})"
            if abs(a1 - a0) >= abs(q1 - q0):                       # lies along the chain's line: its ends are the faces
                if abs((q0 + q1) / 2 - c) <= w / 24 + across_tol_ft:
                    consider(min(a0, a1), max(a0, a1), kind + " end", label)
            elif min(q0, q1) - across_tol_ft <= c <= max(q0, q1) + across_tol_ft:           # crosses the chain's line
                t = min(1.0, max(0.0, (c - q0) / (q1 - q0)))
                a_at = a0 + t * (a1 - a0)
                consider(a_at - w / 24, a_at + w / 24, kind, label)
    return best


def classify(path: Path, d_factor: float = D_FACTOR, chained: bool = True):
    """Program stirrup zones (chains, or single regions with chained=False) with klass, why, support and slab thickness."""
    db = cr.connect(path)
    cols, rails = columns(db), rail_columns(db)
    walls, beams = segments(db, "Wall"), segments(db, "Beam")
    mesh = cr.Mesh(path)
    pieces = regions(db)
    for p in pieces:
        p["web"] = on_beam(beams, p["mx"], p["my"])
    groups = chains([p for p in pieces if not p["web"]]) + chains([p for p in pieces if p["web"]])
    if not chained:
        groups = [dict(p, pieces=[p]) for p in pieces]
    out = []
    for ch in groups:
        thick = []
        for p in ch["pieces"]:
            t = mesh.thickness(p["mx"], p["my"])
            thick.append((t / IN if t and t > 100 else t) or 16.0)       # the mesh helper may hold 0.1 mm or inches
        t_in = min(thick)
        limit_ft = d_factor * t_in / 12
        best = nearest_support(ch, cols, rails, walls, beams)
        if all(p["web"] for p in ch["pieces"]):
            klass, why = "BEAM", "on a beam between its ends"
        elif best is None:
            klass, why = "REQUIRED", "no support on its line within reach"
        elif best[1] == "column with stud rails":
            klass, why = "SSR", f"starts at {best[2]}"
        elif best[0] <= limit_ft + 0.02:
            klass, why = "OK by d", f"ends {best[0] * 12:.0f} in past {best[1]} {best[2]}; limit {limit_ft * 12:.0f} in"
        else:
            klass, why = "REQUIRED", f"reaches {best[0] * 12:.0f} in past {best[1]} {best[2]}; limit {limit_ft * 12:.0f} in"
        out.append(dict(ch, klass=klass, why=why, support=best[1] if best else "", t_in=t_in, reach=best[0] if best else None))
    return out


COLOR = {"REQUIRED": "#c92a2a", "OK by d": "#2b8a3e", "SSR": "#e8590c", "BEAM": "#868e96"}


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
    for u in regions(db, designed_by=1):                             # user regions: magenta outline with the callout
        w = 1.4
        rect = (u["lo"], u["across"] - w / 2, u["length"], w) if u["along"] == "x" else (u["across"] - w / 2, u["lo"], w, u["length"])
        ax.add_patch(plt.Rectangle(rect[:2], rect[2], rect[3], facecolor="none", edgecolor="#d6336c", lw=1.8, zorder=6))
        ax.annotate(f"{u['legs']}L @{u['spacing']:.0f}\"", (u["mx"], u["my"]), fontsize=6, color="#d6336c", xytext=(3, -9), textcoords="offset points", zorder=7)
    for r in found:
        w = 1.0
        rect = (r["lo"], r["across"] - w / 2, r["length"], w) if r["along"] == "x" else (r["across"] - w / 2, r["lo"], w, r["length"])
        ax.add_patch(plt.Rectangle(rect[:2], rect[2], rect[3], facecolor=COLOR[r["klass"]], alpha=0.75, zorder=4))
        if r["klass"] == "REQUIRED":
            ax.annotate(f"{r['legs']}L @{r['spacing']:.1f}\"  {r['length']:.0f}'", (r["mx"], r["my"]), fontsize=6, color="#c92a2a",
                        xytext=(3, 3), textcoords="offset points", zorder=5)
    for k, c in COLOR.items():
        ax.plot([], [], color=c, lw=6, label=k)
    ax.plot([], [], "s", color="#e03131", label="column with stud rails")
    ax.plot([], [], color="#d6336c", lw=2, label="user stirrup region (legs @ spacing)")
    ax.legend(loc="lower left", fontsize=9)
    ax.set_aspect("equal")
    ax.autoscale()
    ax.set_title(f"{path.name}: program stirrup zones by the office one-way rule", fontsize=11)
    ax.set_xlabel("x (ft)")
    ax.set_ylabel("y (ft)")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print("plan:", out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("model", type=Path)
    p.add_argument("--plan", type=Path)
    p.add_argument("--pieces", action="store_true", help="classify the single regions instead of chains")
    a = p.parse_args(argv)
    found = classify(a.model, chained=not a.pieces)
    counts = {k: sum(1 for r in found if r["klass"] == k) for k in COLOR}
    unit = "regions" if a.pieces else "zones"
    print(f"{len(found)} program stirrup {unit}: {counts['REQUIRED']} required, {counts['OK by d']} OK by d, "
          f"{counts['SSR']} at stud rail columns, {counts['BEAM']} on beams")
    for k in ("REQUIRED", "SSR", "OK by d", "BEAM"):
        rows = sorted((r for r in found if r["klass"] == k), key=lambda r: (round(r["my"]), r["mx"]))
        if k != "REQUIRED" and len(rows) > 25:
            print(f"  {k}: {len(rows)} {unit} (not listed)")
            continue
        for r in rows:
            print(f"  {k:8s} ({r['mx']:5.0f},{r['my']:5.0f}) along {r['along']} {r['length']:4.1f} ft in {len(r['pieces'])} piece(s)  "
                  f"{r['legs']}L @ {r['spacing']:.2f} in  slab {r['t_in']:.0f} in  {r['why']}")
    if a.plan:
        plan(found, a.model, a.plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
