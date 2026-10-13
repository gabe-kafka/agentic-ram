#!/usr/bin/env python3
"""The working SVG for one-way shear stirrup zones: what is in the full-width design model now, numbered, so the
engineer can say which zones go and where zones are added.

  python zones_svg.py <full-width calc .cpt> <main model .cpt> <out.svg> [--annots annots.json --ignore-left-of PT]
                      [--out X0,Y0,X1,Y1 ...]

  Z1, Z2, ...   user slab stirrup zones in the full-width model, drawn at the width they have in the main model
                (its column strip: where the stirrups really go), with legs @ spacing. Red outline: the program
                still draws stirrups in that zone's full-width strip sections.
  P1, P2, ...   what the program still draws in the full-width model (not on beams), by the office sort:
                at a stud rail column, OK by d, required, or not sorted (no support on its line).
  --out         a zone that was left out, by its line: drawn dashed grey.
  --annots      the engineer's PDF markup (read_markup.py): his magenta boxes, green strokes and check marks.

Writes <out.svg> and a list beside it (<out>.txt) so Z and P numbers can be turned back into coordinates.
Read-only on the models. One-off for 2636; the fit and the sort come from the skill's markup_plan.py and
shear_regions.py.
"""
import argparse, json, math, re, sys
from pathlib import Path

SKILL = Path(str(Path(__file__).resolve().parent))
sys.path.insert(0, str(SKILL))
import markup_plan as mp        # noqa: E402
import shear_regions as sr      # noqa: E402

FT = 3048.0
pts = lambda t: [(float(a) / FT, float(b) / FT) for a, b in re.findall(r"\[(-?[\d.]+)\]\[(-?[\d.]+)\]", t or "")]
SET = {1: "latitude", 2: "longitude"}


def crosses(a, b, c, d):
    o = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) <= 0 and o(c, d, a) * o(c, d, b) <= 0


def stirrup_regions(path):
    """Every transverse rebar region with its strip cross sections and its drawn corners."""
    db = sr.cr.connect(path)
    span_set = dict(db.execute("select Name, SpanSet from SpanDesign"))
    strips = [(n, span_set.get(n), list(zip(pts(l), pts(r)))) for n, l, r in db.execute("select Name, ResistanceLeftBoundary, ResistanceRightBoundary from SpanSegmentStrip")]
    out = []
    for p0, p1, sd, by, legs, s, shape, a0, a1, b0, b1 in db.execute(
            "select Point0, Point1, SpanDirection, DesignedBy, StirrupLegs, StirrupSpacing, StirrupShape, FirstStirrupEnd0, FirstStirrupEnd1, LastStirrupEnd0, LastStirrupEnd1 from TransverseRebarRegion"):
        a, b = pts(p0)[0], pts(p1)[0]
        corners = [q[0] for q in (pts(a0), pts(a1), pts(b1), pts(b0)) if q]
        out.append(dict(a=a, b=b, set=SET[sd], by=by, legs=legs, sp=s / 254, shape=shape, corners=corners if len(corners) == 4 else None,
                        key=tuple(round(v, 2) for v in a + b), mx=(a[0] + b[0]) / 2, my=(a[1] + b[1]) / 2, len=math.hypot(a[0] - b[0], a[1] - b[1]),
                        secs={(n, k) for n, ss, lines in strips if ss == SET[sd] for k, (l, r) in enumerate(lines) if crosses(l, r, a, b)}))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("full", type=Path)
    p.add_argument("main", type=Path)
    p.add_argument("svg", type=Path)
    p.add_argument("--annots", type=Path)
    p.add_argument("--ignore-left-of", type=float, default=0.0)
    p.add_argument("--out", action="append", default=[], metavar="X0,Y0,X1,Y1")
    p.add_argument("--title", default="")
    p.add_argument("--ids", type=Path, help="JSON that keeps Z numbers stable between runs: a zone keeps its number, a new zone gets the next one")
    p.add_argument("--annots-old", type=Path, help="the previous reading of the PDF: marks not in it are drawn as new (B boxes, C checks) and listed")
    p.add_argument("--propose", type=Path, help='JSON list of zones not placed yet: {"label", "x0", "y0", "x1", "y1", "legs", "spacing", "width"}; drawn dashed blue')
    a = p.parse_args(argv)

    db = sr.cr.connect(a.full)
    cols, rails = sr.columns(db), sr.rail_columns(db)
    full = stirrup_regions(a.full)
    main_width = {r["key"]: r["corners"] for r in stirrup_regions(a.main) if r["by"] == 1}
    near = lambda u, q: any(n == n2 and abs(k - k2) <= 1 for n, k in u["secs"] for n2, k2 in q["secs"])
    prog_raw = [r for r in full if r["by"] == 2]
    zones = sorted((r for r in full if r["by"] == 1 and r["shape"] == 0), key=lambda r: (-round(r["my"] / 8), r["mx"]))
    beams_user = [r for r in full if r["by"] == 1 and r["shape"] == 1]
    ids = json.loads(a.ids.read_text(encoding="utf-8")) if a.ids and a.ids.exists() else {}
    nxt = max([int(v[1:]) for v in ids.values()] + [0]) + 1
    for z in zones:
        name = ",".join(f"{v:.2f}" for v in z["key"])
        if name not in ids:
            ids[name] = f"Z{nxt}"
            nxt += 1
        z["id"] = ids[name]
    if a.ids:
        a.ids.write_text(json.dumps(ids, indent=1), encoding="utf-8")
    for z in zones:
        z["left"] = [q for q in prog_raw if near(z, q)]
        z["draw"] = main_width.get(z["key"]) or z["corners"]
    prog = sorted((z for z in sr.classify(a.full) if z["klass"] != "BEAM"), key=lambda z: (-round(z["my"] / 8), z["mx"]))
    for i, q in enumerate(prog, 1):
        q["id"], q["class"] = f"P{i}", mp.zone_class(q)

    marks, to_model = None, None
    if a.annots:
        pages = json.loads(a.annots.read_text(encoding="utf-8"))
        page = max(pages, key=lambda q: len(q["annots"]))
        marks = mp.read_marks(page, a.ignore_left_of)
        s, ox, oy, matched, worst = mp.fit(marks["ssr"], rails)
        if matched < 0.8 * len(marks["ssr"]):
            raise SystemExit(f"only {matched} of {len(marks['ssr'])} red column marks fit; check --ignore-left-of")
        to_model = lambda px, py: (ox + s * px, oy - s * py)      # noqa: E731
        print(f"markup: {matched} of {len(marks['ssr'])} column marks matched, worst {worst:.2f} ft; {len(marks['boxes'])} magenta boxes, "
              f"{len(marks['checks'])} check marks, {len(marks['green'])} green strokes")
        old = None
        if a.annots_old:
            old_pages = json.loads(a.annots_old.read_text(encoding="utf-8"))
            old = mp.read_marks(max(old_pages, key=lambda q: len(q["annots"])), a.ignore_left_of)
        is_new = lambda pt, olds: old is not None and all(math.hypot(pt[0] - q[0], pt[1] - q[1]) > 2 for q in olds)      # noqa: E731
        marks["new_boxes"] = [r for r in marks["boxes"] if is_new(mp.centre(r), [mp.centre(q) for q in old["boxes"]] if old else [])]
        marks["new_checks"] = [c for c in marks["checks"] if is_new(c, old["checks"] if old else [])]
        marks["new_green"] = [g for g in marks["green"] if is_new(g[0], [q[0] for q in old["green"]] if old else [])]

    slab = [sr.pts(m) for (m,) in db.execute("select MultiPoint from SlabArea")]
    xs, ys = [q[0] for poly in slab for q in poly], [q[1] for poly in slab for q in poly]
    minx, maxx, miny, maxy = min(xs) - 6, max(xs) + 6, min(ys) - 6, max(ys) + 6
    W = 2400.0
    k = W / (maxx - minx)
    H = (maxy - miny) * k
    sx, sy = (lambda x: (x - minx) * k), (lambda y: (maxy - y) * k)
    poly = lambda q: " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in q)      # noqa: E731
    C = dict(mp.COLOR)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H + 150:.0f}" font-family="Segoe UI, Arial" font-size="11">',
         f'<rect width="{W:.0f}" height="{H + 150:.0f}" fill="white"/>']
    for q in slab:
        o.append(f'<polygon points="{poly(q)}" fill="#eef2f6" stroke="#8aa0b4" stroke-width="0.8"/>')
    for (m,) in db.execute("select MultiPoint from SlabOpening"):
        o.append(f'<polygon points="{poly(sr.pts(m))}" fill="white" stroke="#8aa0b4" stroke-width="0.8"/>')
    for gx in range(int(minx // 50 + 1) * 50, int(maxx), 50):
        o.append(f'<line x1="{sx(gx):.1f}" y1="0" x2="{sx(gx):.1f}" y2="{H:.1f}" stroke="#c9d3dc" stroke-width="0.5" stroke-dasharray="2,6"/><text x="{sx(gx) + 3:.1f}" y="12" fill="#8896a3" font-size="10">x {gx}</text>')
    for gy in range(int(miny // 50 + 1) * 50, int(maxy), 50):
        o.append(f'<line x1="0" y1="{sy(gy):.1f}" x2="{W:.0f}" y2="{sy(gy):.1f}" stroke="#c9d3dc" stroke-width="0.5" stroke-dasharray="2,6"/><text x="3" y="{sy(gy) - 3:.1f}" fill="#8896a3" font-size="10">y {gy}</text>')
    for table, colour, width, alpha in (("Wall", "#5c6770", 4, 1.0), ("Beam", "#b36b00", 7, 0.45)):
        for x0, y0, x1, y1, _ in sr.segments(db, table):
            o.append(f'<line x1="{sx(x0):.1f}" y1="{sy(y0):.1f}" x2="{sx(x1):.1f}" y2="{sy(y1):.1f}" stroke="{colour}" stroke-width="{width}" opacity="{alpha}"/>')
    for r in beams_user:
        o.append(f'<line x1="{sx(r["a"][0]):.1f}" y1="{sy(r["a"][1]):.1f}" x2="{sx(r["b"][0]):.1f}" y2="{sy(r["b"][1]):.1f}" stroke="#7a4a00" stroke-width="2" stroke-dasharray="3,2"/>')
    for cx, cy, b, d in cols:
        has = any(math.hypot(cx - qx, cy - qy) < 1 for qx, qy in rails)
        o.append(f'<rect x="{sx(cx - b / 24):.1f}" y="{sy(cy + d / 24):.1f}" width="{b / 12 * k:.1f}" height="{d / 12 * k:.1f}" fill="{"#e03131" if has else "#343a40"}"/>')
    if marks:
        for rect in marks["boxes"]:
            X0, X1, Y0, Y1 = mp.model_box(rect, to_model)
            if rect in marks["new_boxes"]:
                n = marks["new_boxes"].index(rect) + 1
                o.append(f'<rect x="{sx(X0):.1f}" y="{sy(Y1):.1f}" width="{(X1 - X0) * k:.1f}" height="{(Y1 - Y0) * k:.1f}" fill="#1971c2" fill-opacity="0.10" stroke="#1971c2" stroke-width="3"/>')
                o.append(f'<text x="{sx(X0):.1f}" y="{sy(Y1) - 5:.1f}" fill="#1971c2" font-size="14" font-weight="bold">B{n} new box</text>')
            else:
                o.append(f'<rect x="{sx(X0):.1f}" y="{sy(Y1):.1f}" width="{(X1 - X0) * k:.1f}" height="{(Y1 - Y0) * k:.1f}" fill="none" stroke="#d6336c" stroke-width="1.5" stroke-dasharray="8,5" opacity="0.7"/>')
        for vs in marks["green"]:
            new = vs in marks["new_green"]
            o.append('<polyline points="' + poly([to_model(*v) for v in vs]) + f'" fill="none" stroke="{"#099268" if new else "#51cf66"}" stroke-width="{8 if new else 5}" opacity="0.6"/>')
        for px, py in marks["checks"]:
            X, Y = to_model(px, py)
            if (px, py) in marks["new_checks"]:
                n = marks["new_checks"].index((px, py)) + 1
                o.append(f'<circle cx="{sx(X):.1f}" cy="{sy(Y):.1f}" r="13" fill="none" stroke="#1971c2" stroke-width="2.5"/>')
                o.append(f'<text x="{sx(X) + 16:.1f}" y="{sy(Y) - 8:.1f}" fill="#1971c2" font-size="14" font-weight="bold">C{n}</text>')
            o.append(f'<text x="{sx(X):.1f}" y="{sy(Y) + 6:.1f}" fill="#c92a2a" font-size="20" font-weight="bold" text-anchor="middle">&#10003;</text>')
    for q in prog:
        c = C[q["class"]]
        x0, y1, w, h = (q["lo"], q["across"] + 0.6, q["length"], 1.2) if q["along"] == "x" else (q["across"] - 0.6, q["hi"], 1.2, q["length"])
        o.append(f'<rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{w * k:.1f}" height="{h * k:.1f}" fill="{c}" opacity="0.85"/>')
        o.append(f'<text x="{sx(q["mx"]) + 6:.1f}" y="{sy(q["my"]) + 14:.1f}" fill="{c}" font-size="10" font-weight="bold">{q["id"]}</text>')
    for spec in a.out:
        x0, y0, x1, y1 = (float(v) for v in spec.split(","))
        o.append(f'<line x1="{sx(x0):.1f}" y1="{sy(y0):.1f}" x2="{sx(x1):.1f}" y2="{sy(y1):.1f}" stroke="#868e96" stroke-width="6" stroke-dasharray="5,4"/>')
        o.append(f'<text x="{sx(x0) - 4:.1f}" y="{sy(max(y0, y1)) - 5:.1f}" fill="#868e96" font-size="10" text-anchor="end">left out</text>')
    for z in zones:
        dirty = bool(z["left"])
        colour = "#c92a2a" if dirty else "#d6336c"
        if z["draw"]:
            o.append(f'<polygon points="{poly(z["draw"])}" fill="#d6336c" fill-opacity="0.16" stroke="{colour}" stroke-width="{3 if dirty else 2}"/>')
        o.append(f'<line x1="{sx(z["a"][0]):.1f}" y1="{sy(z["a"][1]):.1f}" x2="{sx(z["b"][0]):.1f}" y2="{sy(z["b"][1]):.1f}" stroke="{colour}" stroke-width="2.5"/>')
        o.append(f'<text x="{sx(z["mx"]) + 5:.1f}" y="{sy(z["my"]) - 5:.1f}" fill="#a61e4d" font-size="13" font-weight="bold" stroke="white" stroke-width="3" paint-order="stroke">{z["id"]}</text>')
        o.append(f'<text x="{sx(z["mx"]) + 5:.1f}" y="{sy(z["my"]) + 8:.1f}" fill="#a61e4d" font-size="9" stroke="white" stroke-width="2.5" paint-order="stroke">{z["legs"]}L @{z["sp"]:g}"</text>')
    for q in (json.loads(a.propose.read_text(encoding="utf-8")) if a.propose else []):
        along_x = abs(q["x1"] - q["x0"]) >= abs(q["y1"] - q["y0"])
        h = q["width"] / 2
        x0, x1, y0, y1 = min(q["x0"], q["x1"]), max(q["x0"], q["x1"]), min(q["y0"], q["y1"]), max(q["y0"], q["y1"])
        X0, X1, Y0, Y1 = (x0, x1, y0 - h, y1 + h) if along_x else (x0 - h, x1 + h, y0, y1)
        o.append(f'<rect x="{sx(X0):.1f}" y="{sy(Y1):.1f}" width="{(X1 - X0) * k:.1f}" height="{(Y1 - Y0) * k:.1f}" fill="#ffd43b" fill-opacity="0.45" stroke="#e67700" stroke-width="3" stroke-dasharray="9,5"/>')
        o.append(f'<line x1="{sx(q["x0"]):.1f}" y1="{sy(q["y0"]):.1f}" x2="{sx(q["x1"]):.1f}" y2="{sy(q["y1"]):.1f}" stroke="#e67700" stroke-width="3"/>')
        o.append(f'<text x="{sx(X1) + 6:.1f}" y="{sy(Y1) + 14:.1f}" fill="#e67700" font-size="16" font-weight="bold" stroke="white" stroke-width="3" paint-order="stroke">{q["label"]}  {q["legs"]}L @{q["spacing"]:g}"</text>')
        if q.get("note"):
            o.append(f'<text x="{sx(X1) + 6:.1f}" y="{sy(Y1) + 30:.1f}" fill="#e67700" font-size="12" stroke="white" stroke-width="3" paint-order="stroke">{q["note"]}</text>')
    legend = [("#ffd43b", "YELLOW: change proposed, not in Concept yet")] if a.propose else []
    legend += [("#d6336c", "Z: user stirrup zone, at its real (column strip) width"), ("#c92a2a", "Z with red outline: program still draws stirrups in its strip"),
              ("#868e96", "dashed grey: zone left out (shares a full-width section)"), (C["REQUIRED"], "P: program zone, required by the d rule"),
              (C["UNSORTED"], "P: program zone, not sorted (no support on its line)"), (C["SSR"], "P: program zone at a stud rail column"),
              (C["OK by d"], "P: program zone, OK by d"), ("#e03131", "column with stud rails"), ("#7a4a00", "beam stirrups (closed, by the beam design)")]
    if marks:
        legend.append(("#d6336c", "dashed magenta box / green stroke / check: the 10/6 PDF markup"))
    for i, (c, t) in enumerate(legend):
        x, y = 20 + (i % 4) * 590, H + 22 + (i // 4) * 26
        o.append(f'<rect x="{x}" y="{y}" width="26" height="14" fill="{c}"/><text x="{x + 34}" y="{y + 12}" font-size="14">{t}</text>')
    o.append(f'<text x="20" y="{H + 118}" font-size="15" font-weight="bold">{a.title or a.full.name}</text>')
    o.append(f'<text x="20" y="{H + 138}" font-size="13">Say which Z zones go and where zones are added (a P number, or a column and a direction). Nothing changes in Concept until you say so.</text>')
    o.append("</svg>")
    a.svg.parent.mkdir(parents=True, exist_ok=True)
    a.svg.write_text("\n".join(o), encoding="utf-8")

    lines = [f"{a.title or a.full.name}", "", "USER ZONES"]
    for z in zones:
        w = math.hypot(z["draw"][0][0] - z["draw"][1][0], z["draw"][0][1] - z["draw"][1][1]) if z["draw"] else 0
        left = "; ".join(f"{q['legs']}L @{q['sp']:.1f} in x {q['len']:.1f} ft" for q in z["left"])
        lines.append(f"  {z['id']:4s} ({z['a'][0]:.2f},{z['a'][1]:.2f}) to ({z['b'][0]:.2f},{z['b'][1]:.2f})  {z['set']:9s} {z['len']:4.1f} ft  {z['legs']:2d}L @{z['sp']:g} in  "
                     f"{w:4.1f} ft wide in the main model  {'PROGRAM STILL DRAWS ' + left if left else 'clean'}")
    lines.append("")
    lines.append("PROGRAM ZONES STILL DRAWN (full-width model)")
    for q in prog:
        lines.append(f"  {q['id']:4s} ({q['mx']:.1f},{q['my']:.1f}) along {q['along']} {q['lo']:.1f}-{q['hi']:.1f} at {q['across']:.1f}  {q['length']:4.1f} ft  {q['legs']}L @{q['spacing']:.2f} in  "
                     f"slab {q['t_in']:.0f} in  {q['class']}: {q['why']}")
    if marks and (marks["new_boxes"] or marks["new_checks"] or marks["new_green"]):
        def col_near(X, Y):
            c = min(cols, key=lambda c: math.hypot(c[0] - X, c[1] - Y))
            has = any(math.hypot(c[0] - qx, c[1] - qy) < 1 for qx, qy in rails)
            return f"column ({c[0]:.0f},{c[1]:.0f}) {math.hypot(c[0] - X, c[1] - Y):.1f} ft away, {'stud rails' if has else 'no stud rails'}"

        lines += ["", "NEW IN THE PDF SINCE THE LAST READING"]
        for n, rect in enumerate(marks["new_boxes"], 1):
            X0, X1, Y0, Y1 = mp.model_box(rect, to_model)
            zin = [z["id"] for z in zones if X0 - 1 <= z["mx"] <= X1 + 1 and Y0 - 1 <= z["my"] <= Y1 + 1]
            pin = [f"{q['id']} {q['class']} {q['length']:.1f} ft along {q['along']} {q['legs']}L @{q['spacing']:.1f} in" for q in prog if X0 - 1 <= q["mx"] <= X1 + 1 and Y0 - 1 <= q["my"] <= Y1 + 1]
            lines.append(f"  B{n} box x {X0:.1f}..{X1:.1f}, y {Y0:.1f}..{Y1:.1f} ({X1 - X0:.1f} x {Y1 - Y0:.1f} ft); {col_near((X0 + X1) / 2, (Y0 + Y1) / 2)}; "
                         f"zones inside: {', '.join(zin) or 'none'}; program inside: {'; '.join(pin) or 'none'}")
        for n, (px, py) in enumerate(marks["new_checks"], 1):
            X, Y = to_model(px, py)
            zn = min(zones, key=lambda z: math.hypot(z["mx"] - X, z["my"] - Y))
            pn = min(prog, key=lambda q: math.hypot(q["mx"] - X, q["my"] - Y)) if prog else None
            lines.append(f"  C{n} check at ({X:.1f},{Y:.1f}); {col_near(X, Y)}; nearest zone {zn['id']} {math.hypot(zn['mx'] - X, zn['my'] - Y):.1f} ft; "
                         + (f"nearest program {pn['id']} {pn['class']} {math.hypot(pn['mx'] - X, pn['my'] - Y):.1f} ft, {pn['length']:.1f} ft along {pn['along']} {pn['legs']}L @{pn['spacing']:.1f} in" if pn else "no program zones"))
        for vs in marks["new_green"]:
            (X0, Y0), (X1, Y1) = to_model(*vs[0]), to_model(*vs[-1])
            lines.append(f"  green stroke from ({X0:.1f},{Y0:.1f}) to ({X1:.1f},{Y1:.1f})")
        print("\n".join(lines[lines.index("NEW IN THE PDF SINCE THE LAST READING"):]))
    txt = a.svg.with_suffix(".txt")
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    counts = {}
    for q in prog:
        counts[q["class"]] = counts.get(q["class"], 0) + 1
    print(f"{len(zones)} user zones ({sum(1 for z in zones if z['left'])} with program stirrups left), {len(prog)} program zones {counts}")
    print("svg:", a.svg)
    print("list:", txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
