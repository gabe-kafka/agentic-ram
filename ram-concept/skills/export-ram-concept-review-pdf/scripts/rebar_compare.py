#!/usr/bin/env python3
"""Required bending bars, BEFORE vs AFTER, on Concept's own plan exports, marked up for Bluebeam.

  python rebar_compare.py <exports> <out.pdf> <before.cpt> [<after.cpt>] [--title TEXT] [--names B A]

<exports> holds Concept's Report > Export Window to PDF of the four review plans of each model, one
page each: before-top-long.pdf, before-top-lat.pdf, before-bot-long.pdf, before-bot-lat.pdf, and the
same with after-. Export at a print scale that fits one sheet (1:175 on A1 for 2636 building 3).
The .cpt files are the saved, calculated models the pages were exported from, read immutable.

Each AFTER program bar group is matched to the BEFORE group at its place (same size, centre within
NEAR ft): new (none there), more (more bar-feet), less (fewer), moved (same steel, shifted), or the
same (within TOL ft); BEFORE groups no AFTER group matched are gone.
Out: a summary page (groups, bars and bar-feet per plan, the counts above, and the new and more
groups listed), then one A1 sheet per plan: the BEFORE plan on the left and the AFTER plan on the
right, as Concept printed them, at one scale, each under a big red label (BEFORE LONG TOP, ...).
On the AFTER plan each new or more group gets a red Highlight markup, and the new loads (area and
point loads in AFTER, not in BEFORE) a green outline; a red Text Box under each label names the model
and the count. All markups stay editable in Bluebeam. With one model: the summary and its four plans,
labelled, no other markups.
Plan feet are fitted to page points from the slab outline: the colour whose drawn extents match the
mesh extents at one scale in x and y.
"""
import argparse
import math
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "simplify-ram-concept-rebar" / "scripts"))
sys.path.insert(0, str(HERE.parents[3] / "ram-structural-system" / "scripts"))
import bluebeam_markup as bm   # noqa: E402
import cpt_reader as cr        # noqa: E402

PSF = 4.788026e-7                # internal N per (0.1 mm)^2 per psf
KIP = 4448.222
PLANS = [("top-long", "Top Long"), ("top-lat", "Top Lat"), ("bot-long", "Bot Long"), ("bot-lat", "Bot Lat")]
RED, GREEN = (1, 0, 0), (0.17, 0.54, 0.24)
PAD = 1.0                        # ft around a highlighted bar group
NEAR = 1.5                       # ft between centres for an AFTER group to be the BEFORE group at its place
TOL = 0.05                       # ft (and bar-ft) below which a difference is no change
RED_FOR = ("new", "more")
SHEET = (2384, 1684)             # A1 landscape, pt
MARGIN, GAP = 40, 60             # pt round the sheet and between the plans
LABEL = 100                      # pt, the red plan label (as the engineer marks the set by hand)
BAND = 230                       # pt above the plans for the label and the model note


def centre(d):
    return (d.a0 + d.a1) / 2, (d.b0 + d.b1) / 2


def match(before, after):
    """Each AFTER group with its status and the BEFORE group it replaces; and the BEFORE groups gone."""
    left, out = list(before), []
    for d in after:
        c = centre(d)
        near = [b for b in left if b.size == d.size and all(abs(p - q) <= NEAR for p, q in zip(centre(b), c))]
        if not near:
            out.append((d, "new", None))
            continue
        b = min(near, key=lambda b: math.dist(centre(b), c))
        left.remove(b)
        grow = d.count * d.length - b.count * b.length
        same = d.count == b.count and all(abs(p - q) <= TOL for p, q in zip((d.a0, d.a1, d.b0, d.b1), (b.a0, b.a1, b.b0, b.b1)))
        out.append((d, "same" if same else "more" if grow > TOL else "less" if grow < -TOL else "moved", b))
    return out, left


def bar_ft(bars):
    return round(sum(d.count * d.length for d in bars))


def callout(d):
    return f"({d.count}){d.size}x{d.length:g}'"


def new_loads(before, after):
    """Area and point loads in AFTER whose geometry and value are not in BEFORE."""
    def area(p):
        return {(mp, round(z / PSF, 1)) for mp, z in cr.connect(p).execute("select MultiPoint, ALFz0 from AreaLoad")}

    def point(p):
        return {(pt, round(z / KIP, 2)) for pt, z in cr.connect(p).execute("select Point0, PLFz from PointLoad")}
    areas = [(cr._points(mp), psf) for mp, psf in area(after) - area(before)]
    points = [(cr._points(pt)[0], k) for pt, k in point(after) - point(before)]
    return areas, points


def fit(page, path):
    """Plan ft -> page points, from the slab outline: (x, y) -> (x0 + k(x - xmin), y0 - k(y - ymin))."""
    mesh = cr.Mesh(path)
    xs = [p[0] for _, poly in mesh.elements for p in poly]
    ys = [p[1] for _, poly in mesh.elements for p in poly]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    ext = defaultdict(lambda: [math.inf, math.inf, -math.inf, -math.inf])
    for p in page.get_drawings():
        if not p.get("color"):
            continue
        e = ext[tuple(round(v, 2) for v in p["color"])]
        for item in p["items"]:
            for q in item[1:]:
                pts = [q] if isinstance(q, pymupdf.Point) else [q.tl, q.br] if isinstance(q, pymupdf.Rect) else []
                for pt in pts:
                    e[0], e[1], e[2], e[3] = min(e[0], pt.x), min(e[1], pt.y), max(e[2], pt.x), max(e[3], pt.y)
    best = None
    for x0, y0, x1, y1 in ext.values():
        kx, ky = (x1 - x0) / w, (y1 - y0) / h
        if kx > 0 and ky > 0 and abs(kx - ky) / kx < 0.01 and (best is None or abs(kx - ky) < best[0]):
            best = (abs(kx - ky), (kx + ky) / 2, x0, y1)
    if best is None:
        raise SystemExit(f"{path.name}: no drawn outline matches the slab extents; is the page one plan on one sheet?")
    _, k, x0, y1 = best
    return lambda x, y: pymupdf.Point(x0 + k * (x - min(xs)), y1 - k * (y - min(ys))), k


class Model:
    def __init__(self, path):
        self.path = Path(path)
        self.user, self.prog = {}, {}
        for name, _ in PLANS:
            layer = cr.Layer.parse(name)
            self.user[name] = cr.bars(self.path, layer, cr.USER)
            self.prog[name] = cr.bars(self.path, layer, cr.PROGRAM)


def plan_area(page):
    """The printed plan with its title block: the inked extent of the page, less the file-name header
    and the page footer, which Concept right-aligns at the sheet edge."""
    pix = page.get_pixmap(dpi=36, annots=False, colorspace=pymupdf.csGRAY)
    ink = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 245
    k = 36 / 72
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            x0, y0, x1, y1 = line["bbox"]
            if x1 >= page.rect.width - 60:
                ink[max(int(y0 * k) - 1, 0):int(y1 * k) + 2, max(int(x0 * k) - 1, 0):int(x1 * k) + 2] = False
    ys, xs = np.nonzero(ink)
    r = pymupdf.Rect(xs.min() / k, ys.min() / k, (xs.max() + 1) / k, (ys.max() + 1) / k)
    return (r + (-8, -8, 8, 8)) & page.rect


def label(page, rect, text):
    """A big red Text Box, Helvetica, no border, no fill."""
    a = page.add_freetext_annot(rect, text, fontsize=LABEL, fontname="helv", text_color=RED, border_width=0)
    a.set_info(title=bm.AUTHOR, subject="Text Box", content=text)
    a.update()


def mark(page, place, src, model, name, new, loads):
    """Red highlights on the new program bars, green outlines on the new loads, on the sheet.
    `place` takes a point of the source page `src` to the sheet."""
    fitted, k = fit(src, model.path)

    def to_page(x, y):
        return place(fitted(x, y))
    layer = cr.Layer.parse(name)
    for d in new:
        a = layer.to_plan(d.a0 - PAD, d.b0 - PAD)
        b = layer.to_plan(d.a1 + PAD, d.b1 + PAD)
        rect = pymupdf.Rect(to_page(*a), to_page(*b)).normalize()
        bm.highlight(page, rect, RED, f"NEW OR MORE vs BEFORE: {callout(d)}")
    areas, points = loads
    for poly, psf in areas:
        a = page.add_polygon_annot([to_page(x, y) for x, y in poly + poly[:1]])
        a.set_colors(stroke=GREEN)
        a.set_border(width=1.5, dashes=[6, 3])
        a.set_info(title=bm.AUTHOR, subject="Polygon", content=f"NEW LOAD {-psf:g} PSF")
        a.update(opacity=0.8)
    for (x, y), kips in points:
        c = to_page(x, y)
        a = page.add_circle_annot(pymupdf.Rect(c.x - 6, c.y - 6, c.x + 6, c.y + 6))
        a.set_colors(stroke=GREEN)
        a.set_border(width=1.5)
        a.set_info(title=bm.AUTHOR, subject="Ellipse", content=f"NEW PT LOAD {-kips:g}k")
        a.update(opacity=0.8)


def sheet(out, srcs, titles, notes, marks):
    """One A1 sheet: the source pages' plans side by side at one scale, BEFORE left, each under its
    red label and model note. `marks[i]` adds markups for plan i given (sheet, place, source page)."""
    page = out.new_page(width=SHEET[0], height=SHEET[1])
    clip = pymupdf.Rect()
    for s in srcs:
        clip |= plan_area(s)
    n = len(srcs)
    col = (SHEET[0] - 2 * MARGIN - GAP * (n - 1)) / n
    k = min(col / clip.width, (SHEET[1] - 2 * MARGIN - BAND) / clip.height)
    w, h = clip.width * k, clip.height * k
    for i, s in enumerate(srcs):
        x0 = MARGIN + i * (col + GAP)
        px, py = x0 + (col - w) / 2, MARGIN + BAND
        page.show_pdf_page(pymupdf.Rect(px, py, px + w, py + h), s.parent, s.number, clip=clip)
        if i:
            page.draw_line((x0 - GAP / 2, MARGIN), (x0 - GAP / 2, SHEET[1] - MARGIN), color=(0.6, 0.6, 0.6), width=1)
        label(page, pymupdf.Rect(x0, MARGIN, x0 + col, MARGIN + LABEL * 1.25), titles[i])
        bm.text_box(page, x0, MARGIN + LABEL * 1.25 + 4, col, notes[i])
        if marks[i]:
            marks[i](page, lambda q, px=px, py=py: pymupdf.Point(px + (q.x - clip.x0) * k, py + (q.y - clip.y0) * k), s)
    return page


def summary(path, rows, changes, title, names, loads, compare):
    """The front page, as a one-page PDF at A1 landscape."""
    doc = pymupdf.open()
    page = doc.new_page(width=2384, height=1684)
    head = (["Plan", "BEFORE groups / bars / bar-ft", "AFTER groups / bars / bar-ft", "New", "More", "Less", "Moved",
             "Gone"] if compare else ["Plan", "User groups", "Program groups", "Program bars", "Program bar-ft"])
    cells = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    lists = "".join(f"<td><b>{label}</b><br>" + ("<br>".join(new) or "none") + "</td>" for label, new in changes)
    files = (f"BEFORE: {names[0]}<br>AFTER: {names[1]}<br>New loads in AFTER: {len(loads[0])} area loads, "
             f"{len(loads[1])} point loads" if compare else f"Model: {names[0]}")
    html = f"""
      <h1>Required bending reinforcement{' - BEFORE vs AFTER' if compare else ''}</h1>
      <h2>{title}</h2>
      <p>{files}</p>
      <table class="t"><tr>{cells}</tr>{body}</table>
      <p>Plan pages: RAM Concept, Report &gt; Export Window to PDF, the office Top Long, Top Lat, Bot Long and
      Bot Lat plans. Program bars = reinforcement Concept still requires beyond the user bars (drawing set).</p>
      {'<p>Each AFTER program group against the BEFORE group at its place (same size, centre within 1.5 ft): New = none there; More / Less = more / fewer bar-ft; Moved = same steel shifted; Gone = BEFORE group with none in AFTER. Unchanged groups are not counted.</p><p><b>New and More in AFTER (plan ft), red highlights on the AFTER pages:</b></p><table class="l"><tr>' + lists + '</tr></table>' if compare else ''}"""
    css = """body {font-family: sans-serif; font-size: 20px;} h1 {font-size: 44px;} h2 {font-size: 30px; font-weight: normal;}
             table.t {border-collapse: collapse; width: 100%;} .t td, .t th {border: 1px solid #444; padding: 10px; text-align: center;}
             table.l {width: 100%;} .l td {vertical-align: top; font-family: monospace; font-size: 17px; padding-right: 24px;}"""
    page.insert_htmlbox(pymupdf.Rect(110, 110, 2274, 1600), html, css=css)
    doc.save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("exports", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("models", type=Path, nargs="+")
    p.add_argument("--title", default="")
    p.add_argument("--names", nargs="+", help="the model names to show, when the exports came from copies")
    a = p.parse_args()
    if len(a.models) > 2:
        p.error("one model, or a BEFORE and an AFTER model")
    if a.out.exists():
        p.error(f"{a.out} exists; give a new name")
    compare = len(a.models) == 2
    tags = ["before", "after"] if compare else ["before"]
    pages = {(t, n): a.exports / f"{t}-{n}.pdf" for t in tags for n, _ in PLANS}
    missing = [str(f) for f in pages.values() if not f.is_file()]
    if missing:
        p.error("missing exports: " + ", ".join(missing))
    names = a.names or [m.name for m in a.models]
    models = [Model(m) for m in a.models]
    loads = new_loads(*a.models) if compare else ([], [])
    rows, changes, news = [], [], {}
    for name, label in PLANS:
        first = models[0].prog[name]
        if not compare:
            rows.append((label, len(models[0].user[name]), len(first), sum(d.count for d in first), bar_ft(first)))
            continue
        layer = cr.Layer.parse(name)
        after = models[1].prog[name]
        matched, gone = match(first, after)
        n = {s: sum(1 for _, t, _ in matched if t == s) for s in ("new", "more", "less", "moved")}
        news[name] = [d for d, s, _ in matched if s in RED_FOR]
        rows.append((label, f"{len(first)} / {sum(d.count for d in first)} / {bar_ft(first)}",
                     f"{len(after)} / {sum(d.count for d in after)} / {bar_ft(after)}",
                     n["new"], n["more"], n["less"], n["moved"], len(gone)))
        changes.append((label, [f"{callout(d)} at ({x:.0f}, {y:.0f})" + (f", was {callout(b)}" if b else ", new")
                                for d, s, b in matched if s in RED_FOR
                                for x, y in [layer.to_plan(*centre(d))]]))
    work = Path(tempfile.mkdtemp(prefix="rebar-compare-"))        # made apart: a failed run leaves nothing beside the job
    try:
        summary(work / "summary.pdf", rows, changes, a.title, names, loads, compare)
        out = pymupdf.open(work / "summary.pdf")
        for name, plan in PLANS:
            srcs = []
            for tag in tags:
                src = pymupdf.open(pages[(tag, name)])
                if len(src) != 1:
                    raise SystemExit(f"{pages[(tag, name)].name}: {len(src)} pages; export at a scale that fits one sheet")
                srcs.append(src[0])
            words = " ".join(reversed(plan.split())).upper()            # Top Long -> LONG TOP
            titles = [f"{tag.upper()} {words}" if compare else words for tag in tags]
            notes = [f"**{tag.upper()}** - {names[i]}" if compare else names[i] for i, tag in enumerate(tags)]
            marks = [None] * len(tags)
            if compare:
                areas, points = loads
                notes[1] += f"\n{len(news[name])} PROG. BAR GROUPS NEW OR MORE vs BEFORE (RED)"
                if areas or points:
                    notes[1] += f"\nNEW LOADS (GREEN): {len(areas)} AREA, {len(points)} PT"
                marks[1] = lambda pg, place, src, name=name: mark(pg, place, src, models[1], name, news[name], loads)
            sheet(out, srcs, titles, notes, marks)
        out.save(work / "out.pdf", garbage=3, deflate=True)
        out.close()
        shutil.copyfile(work / "out.pdf", a.out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if compare:
        print("plan\tbefore groups/bars/bar-ft\tafter groups/bars/bar-ft\tnew\tmore\tless\tmoved\tgone")
    else:
        print("plan\tuser groups\tprogram groups\tprogram bars\tprogram bar-ft")
    for r in rows:
        print(*r, sep="\t")
    for label, new in changes:
        if new:
            print(f"{label} new or more: " + "; ".join(new))
    if compare:
        print(f"new loads in AFTER: {len(loads[0])} area, {len(loads[1])} point")
    print(f"saved {a.out} ({1 + len(PLANS)} pages)")


if __name__ == "__main__":
    main()
