#!/usr/bin/env python3
"""Fit the engineer's PDF markup to the model, say what each mark covers, and draw the reading as an SVG.

  python markup_plan.py <annots.json> <screening.cpt> <out.svg> [--page N] [--ignore-left-of PT]
                        [--boxes-out boxes.json] [--extra extra.json]

<annots.json> comes from read_markup.py. <screening.cpt> is the saved model the marked-up plan was printed from
(the full-width copy). The SVG is what goes back to the engineer: he checks that his intent was read correctly
BEFORE any bar is drawn in Concept, and it shows which boxes he still has to add to his PDF.

The markup convention read here (the engineer's, first used on 2636):
  red square about the size of a column   a stud rail column: set aside, checked through the rails. These marks
                                          also fix the page: they are matched to the stud rail columns in the model
  green freehand stroke                   stirrups there are OK by d: nothing to place
  magenta square                          user stirrups wanted in this box
  red polygon (a check mark)              a required location
A legend drawn with the same marks at the left of the page is skipped with --ignore-left-of (page points).

--boxes-out writes the magenta boxes in model feet (to the nearest foot; place_stirrups.py adds a 1 ft
margin) for `place_stirrups.py --boxes`. --extra is a JSON list of [x0, x1, y0, y1, label, "placed" | "candidate"]: boxes the
agent proposes on top of the markup, drawn dashed and labelled so the engineer can add or reject them.

Program stirrup zones are drawn from shear_regions.classify. On a full-width copy a zone with no support on its
line is drawn as unsorted, not as required (see the known limit in shear_regions.py).
Read-only on the model.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shear_regions as sr      # noqa: E402

cr = sr.cr


def is_red(a):
    s = a.get("stroke") or []
    return len(s) == 3 and s[0] > 0.8 and s[1] < 0.3 and s[2] < 0.3


def is_magenta(a):
    s = a.get("stroke") or []
    return len(s) == 3 and s[0] > 0.8 and s[1] < 0.3 and s[2] > 0.8


def centre(r):
    return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def read_marks(page, ignore_left_of=0.0):
    A = [a for a in page["annots"] if a["rect"][0] >= ignore_left_of]
    red_sq = [a for a in A if a["type"] == "Square" and is_red(a)]
    if red_sq:                                                    # drop a page frame or a cloud: keep column-size squares
        med = statistics.median(a["rect"][2] - a["rect"][0] for a in red_sq)
        red_sq = [a for a in red_sq if med / 2 <= a["rect"][2] - a["rect"][0] <= med * 2]
    return dict(ssr=[centre(a["rect"]) for a in red_sq],
                boxes=[a["rect"] for a in A if a["type"] == "Square" and is_magenta(a)],
                checks=[(sum(v[0] for v in a["vertices"]) / len(a["vertices"]), sum(v[1] for v in a["vertices"]) / len(a["vertices"]))
                        for a in A if a["type"] == "Polygon" and is_red(a) and a.get("vertices")],
                green=[a["vertices"] for a in A if a["type"] == "Ink" and len(a.get("vertices") or []) >= 3])


def fit(marks, targets, tol_ft=6.0):
    """Page points to model feet: X = ox + s px, Y = oy - s py (uniform scale, page y runs down).
    Returns (s, ox, oy, matched, worst residual ft)."""
    mx, my = [m[0] for m in marks], [m[1] for m in marks]
    tx, ty = [t[0] for t in targets], [t[1] for t in targets]
    s = ((max(tx) - min(tx)) / (max(mx) - min(mx)) + (max(ty) - min(ty)) / (max(my) - min(my))) / 2
    ox, oy = min(tx) - s * min(mx), max(ty) + s * min(my)
    pairs = []
    for _ in range(8):
        pairs = []
        for px, py in marks:
            X, Y = ox + s * px, oy - s * py
            t = min(targets, key=lambda q: math.hypot(q[0] - X, q[1] - Y))
            if math.hypot(t[0] - X, t[1] - Y) < tol_ft:
                pairs.append(((px, -py), t))
        if len(pairs) < 4:
            break
        n = len(pairs)
        ub, vb = sum(p[0] for p, _ in pairs) / n, sum(p[1] for p, _ in pairs) / n
        Xb, Yb = sum(t[0] for _, t in pairs) / n, sum(t[1] for _, t in pairs) / n
        s = (sum((p[0] - ub) * (t[0] - Xb) + (p[1] - vb) * (t[1] - Yb) for p, t in pairs)
             / sum((p[0] - ub) ** 2 + (p[1] - vb) ** 2 for p, _ in pairs))
        ox, oy = Xb - s * ub, Yb - s * vb
    resid = [math.hypot(ox + s * p[0] - t[0], oy + s * p[1] - t[1]) for p, t in pairs]
    return s, ox, oy, len(pairs), (max(resid) if resid else None)


def model_box(rect, to_model):
    X0, Y1 = to_model(rect[0], rect[1])
    X1, Y0 = to_model(rect[2], rect[3])
    return X0, X1, Y0, Y1


def zone_class(z):
    return "UNSORTED" if z["klass"] == "REQUIRED" and not z["support"] else z["klass"]


COLOR = {"REQUIRED": "#c92a2a", "UNSORTED": "#7048e8", "OK by d": "#2b8a3e", "SSR": "#e8590c", "BEAM": "#868e96"}


def svg(db, zones, cols, rails, marks, to_model, extra, note, out: Path):
    slab = [sr.pts(mp) for (mp,) in db.execute("select MultiPoint from SlabArea")]
    xs = [p[0] for poly in slab for p in poly]
    ys = [p[1] for poly in slab for p in poly]
    minx, maxx, miny, maxy = min(xs) - 5, max(xs) + 5, min(ys) - 5, max(ys) + 5
    W = 1400.0
    k = W / (maxx - minx)
    H = (maxy - miny) * k
    sx = lambda x: (x - minx) * k               # noqa: E731
    sy = lambda y: (maxy - y) * k               # noqa: E731
    poly = lambda p: " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in p)      # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H + 170:.0f}" font-family="Segoe UI, Arial" font-size="11">',
         f'<rect width="{W:.0f}" height="{H + 170:.0f}" fill="white"/>']
    for p in slab:
        o.append(f'<polygon points="{poly(p)}" fill="#e9eff4" stroke="#8aa0b4" stroke-width="0.7"/>')
    for (mp,) in db.execute("select MultiPoint from SlabOpening"):
        o.append(f'<polygon points="{poly(sr.pts(mp))}" fill="white" stroke="#8aa0b4" stroke-width="0.7"/>')
    for table, colour, width, alpha in (("Wall", "#5c6770", 3, 1.0), ("Beam", "#b36b00", 5, 0.6)):
        for x0, y0, x1, y1, _ in sr.segments(db, table):
            o.append(f'<line x1="{sx(x0):.1f}" y1="{sy(y0):.1f}" x2="{sx(x1):.1f}" y2="{sy(y1):.1f}" stroke="{colour}" stroke-width="{width}" opacity="{alpha}"/>')
    for cx, cy, b, d in cols:
        has = any(math.hypot(cx - qx, cy - qy) < 1 for qx, qy in rails)
        o.append(f'<rect x="{sx(cx - b / 24):.1f}" y="{sy(cy + d / 24):.1f}" width="{b / 12 * k:.1f}" height="{d / 12 * k:.1f}" fill="{"#e03131" if has else "#343a40"}"/>')
    for z in zones:
        c = zone_class(z)
        x0, y1, w, h = (z["lo"], z["across"] + 0.5, z["length"], 1.0) if z["along"] == "x" else (z["across"] - 0.5, z["hi"], 1.0, z["length"])
        o.append(f'<rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{w * k:.1f}" height="{h * k:.1f}" fill="{COLOR[c]}" opacity="0.8"/>')
        if c in ("REQUIRED", "UNSORTED"):
            o.append(f'<text x="{sx(z["mx"]) + 4:.1f}" y="{sy(z["my"]) - 3:.1f}" fill="{COLOR[c]}" font-size="9">{z["legs"]}L @{z["spacing"]:.1f}" {z["length"]:.0f}\'</text>')
    for rect in marks["boxes"]:
        X0, X1, Y0, Y1 = model_box(rect, to_model)
        o.append(f'<rect x="{sx(X0):.1f}" y="{sy(Y1):.1f}" width="{(X1 - X0) * k:.1f}" height="{(Y1 - Y0) * k:.1f}" fill="none" stroke="#d6336c" stroke-width="2.5"/>')
    for px, py in marks["checks"]:
        X, Y = to_model(px, py)
        o.append(f'<text x="{sx(X):.1f}" y="{sy(Y) + 6:.1f}" fill="#c92a2a" font-size="20" font-weight="bold" text-anchor="middle">&#10003;</text>')
    for X0, X1, Y0, Y1, label, style in extra:
        colour = "#d6336c" if style == "placed" else "#868e96"
        o.append(f'<rect x="{sx(X0):.1f}" y="{sy(Y1):.1f}" width="{(X1 - X0) * k:.1f}" height="{(Y1 - Y0) * k:.1f}" fill="none" stroke="{colour}" stroke-width="2.5" stroke-dasharray="6,4"/>')
        o.append(f'<text x="{sx(X0):.1f}" y="{sy(Y1) - 4:.1f}" fill="{colour}" font-size="11" font-weight="bold">{label}</text>')
    for vs in marks["green"]:
        o.append('<polyline points="' + poly([to_model(*v) for v in vs]) + '" fill="none" stroke="#51cf66" stroke-width="5" opacity="0.8"/>')
    legend = [(COLOR["REQUIRED"], "program zone, required"), (COLOR["OK by d"], "program zone, OK by d"), (COLOR["SSR"], "program zone at a stud rail column"),
              (COLOR["UNSORTED"], "program zone, not sorted (no support on its line)"), (COLOR["BEAM"], "a beam's own stirrups"), ("#e03131", "column with stud rails"),
              ("#d6336c", "magenta box from the markup; dashed = added here, to add to the PDF"), ("#51cf66", "green stroke from the markup: OK by d"),
              ("#868e96", "grey dashed: flagged, not placed")]
    for i, (c, t) in enumerate(legend):
        x, y = 20 + (i % 3) * 460, H + 20 + (i // 3) * 26
        o.append(f'<rect x="{x}" y="{y}" width="26" height="14" fill="{c}"/><text x="{x + 34}" y="{y + 12}" font-size="13">{t}</text>')
    o.append(f'<text x="20" y="{H + 115}" font-size="13">Red check: a check mark from the markup. {note}</text>')
    o.append("</svg>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(o), encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("annots", type=Path)
    p.add_argument("model", type=Path)
    p.add_argument("svg", type=Path)
    p.add_argument("--page", type=int, help="page number; default the page with the most annotations")
    p.add_argument("--ignore-left-of", type=float, default=0.0, metavar="PT", help="skip marks left of this page x (a legend)")
    p.add_argument("--boxes-out", type=Path)
    p.add_argument("--extra", type=Path)
    a = p.parse_args(argv)

    pages = json.loads(a.annots.read_text(encoding="utf-8"))
    page = next(q for q in pages if q["page"] == a.page) if a.page else max(pages, key=lambda q: len(q["annots"]))
    marks = read_marks(page, a.ignore_left_of)
    db = cr.connect(a.model)
    cols, rails = sr.columns(db), sr.rail_columns(db)
    if len(marks["ssr"]) < 4 or len(rails) < 4:
        raise SystemExit(f"{len(marks['ssr'])} red column marks and {len(rails)} stud rail columns: too few to fix the page to the model")
    s, ox, oy, matched, worst = fit(marks["ssr"], rails)
    if matched < 0.8 * len(marks["ssr"]):
        raise SystemExit(f"only {matched} of {len(marks['ssr'])} red column marks land on a stud rail column: check --page and --ignore-left-of")
    to_model = lambda px, py: (ox + s * px, oy - s * py)        # noqa: E731
    print(f"page {page['page']}: 1 pt = {s:.4f} ft; {matched} of {len(marks['ssr'])} red column marks matched to stud rail columns, worst {worst:.2f} ft")
    unmarked = [q for q in rails if all(math.hypot(q[0] - to_model(*m)[0], q[1] - to_model(*m)[1]) > 3 for m in marks["ssr"])]
    if unmarked:
        print("stud rail columns with no red mark: " + ", ".join(f"({x:.0f},{y:.0f})" for x, y in sorted(unmarked)))

    zones = [z for z in sr.classify(a.model)]
    counts = {c: sum(1 for z in zones if zone_class(z) == c) for c in COLOR}
    print(f"{len(zones)} program stirrup zones in {a.model.name}: " + ", ".join(f"{n} {c}" for c, n in counts.items() if n))

    def nearest_col(X, Y):
        c = min(cols, key=lambda c: math.hypot(c[0] - X, c[1] - Y))
        has = any(math.hypot(c[0] - qx, c[1] - qy) < 1 for qx, qy in rails)
        return f"({c[0]:.0f},{c[1]:.0f}) {math.hypot(c[0] - X, c[1] - Y):.1f} ft, {'stud rails' if has else 'no stud rails'}"

    boxes = []
    print(f"\n{len(marks['boxes'])} MAGENTA BOXES (user stirrups wanted)")
    for rect in marks["boxes"]:
        X0, X1, Y0, Y1 = model_box(rect, to_model)
        box = [round(X0), round(X1), round(Y0), round(Y1)]
        boxes.append(box)
        inside = [z for z in zones if any(X0 - 1 <= q["mx"] <= X1 + 1 and Y0 - 1 <= q["my"] <= Y1 + 1 for q in z["pieces"]) and z["klass"] != "BEAM"]
        desc = "; ".join(f"{zone_class(z)} {z['legs']}L @{z['spacing']:.1f} in, {z['length']:.1f} ft along {z['along']}" for z in inside) or "NO program zone inside"
        print(f"  x {box[0]}..{box[1]}, y {box[2]}..{box[3]} ({X1 - X0:.1f} x {Y1 - Y0:.1f} ft): {desc}; nearest column {nearest_col((X0 + X1) / 2, (Y0 + Y1) / 2)}")
    print(f"\n{len(marks['checks'])} CHECK MARKS (required)")
    for px, py in marks["checks"]:
        X, Y = to_model(px, py)
        z = min(zones, key=lambda z: math.hypot(z["mx"] - X, z["my"] - Y)) if zones else None
        near = f"nearest zone ({z['mx']:.0f},{z['my']:.0f}) {zone_class(z)} {z['legs']}L @{z['spacing']:.1f} in, {z['length']:.1f} ft" if z else "no zones"
        boxed = any(b[0] - 1 <= X <= b[1] + 1 and b[2] - 1 <= Y <= b[3] + 1 for b in boxes)
        print(f"  ({X:.0f},{Y:.0f}): {near}; nearest column {nearest_col(X, Y)}{'' if boxed else '; NOT inside a magenta box'}")
    print(f"\n{len(marks['green'])} GREEN STROKES (OK by d)")
    for vs in marks["green"]:
        (X0, Y0), (X1, Y1) = to_model(*vs[0]), to_model(*vs[-1])
        print(f"  from ({X0:.0f},{Y0:.0f}) to ({X1:.0f},{Y1:.0f}), {math.hypot(X1 - X0, Y1 - Y0):.1f} ft")

    covered = lambda z: any(b[0] - 1 <= q["mx"] <= b[1] + 1 and b[2] - 1 <= q["my"] <= b[3] + 1 for b in boxes for q in z["pieces"])     # noqa: E731
    loose = [z for z in zones if zone_class(z) == "REQUIRED" and not covered(z)]
    if loose:
        print(f"\n{len(loose)} REQUIRED zones outside every magenta box (ask the engineer):")
        for z in sorted(loose, key=lambda z: (round(z["my"]), z["mx"])):
            print(f"  ({z['mx']:.0f},{z['my']:.0f}) along {z['along']} {z['length']:.1f} ft, {z['legs']}L @{z['spacing']:.1f} in: {z['why']}")

    extra = json.loads(a.extra.read_text(encoding="utf-8")) if a.extra else []
    note = f"{a.model.name}: {len(zones)} program zones. Page fit: {matched} column marks matched, worst {worst:.1f} ft."
    svg(db, zones, cols, rails, marks, to_model, extra, note, a.svg)
    print("\nsvg:", a.svg)
    if a.boxes_out:
        a.boxes_out.write_text(json.dumps(boxes + [list(e[:4]) for e in extra if e[5] == "placed"]), encoding="utf-8")
        print("boxes:", a.boxes_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
