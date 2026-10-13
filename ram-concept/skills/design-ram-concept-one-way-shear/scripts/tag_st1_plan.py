#!/usr/bin/env python3
"""2636 Building 2: put the one-way shear stirrup regions on the F&F sheets (S101A/B/C) as the engineer's Bluebeam
markup set: an orange 50% rectangle (subject Rectangle), an 'ST1' text box, and two red length measurements
(width and length, Bluebeam LineDimension with a Measure dict at 1/8 in = 1 ft), one set per zone.

  python tag_st1_plan.py <sheets.pdf> <zones.json> <out.pdf> --model <saved.cpt> [--fits plans] [--author NAME]
                         [--drop-sample] [--report out.json]

<zones.json> from the tag table (st1-tags-1008.json): id, line (x0,y0)-(x1,y1) ft, width_ft (strip width rounded
DOWN), length_ft (zone length rounded UP). The rectangle is width_ft across the zone's line, centred on the line,
and length_ft along it from the support-face end (the end nearer a column, wall or beam); a zone that runs through
its support keeps its own centre. Fits per page are read from <fits>/fit-S101<X>.txt: scale pt/ft, offset x,
offset y, page height. The source PDF is not touched; --drop-sample leaves the engineer's own sample set out.
"""
import argparse, json, math, sys
from pathlib import Path
import pymupdf
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shear_regions as sr

ORANGE, RED, WHITE, BLACK = (1, 0.5019608, 0), (1, 0, 0), (1, 1, 1), (0, 0, 0)
MEASURE = ("<</Type/Measure/Subtype/RL/R(0.125 in = 1 ft' in\")"
           "/X[<</Type/NumberFormat/U(')/C .1111111/F/F/D 4/FD true/SS()>>]"
           "/D[<</Type/NumberFormat/U(')/C 1/F/F/D 4/FD true/PS()/SS(-)>><</Type/NumberFormat/U(\")/C 12/F/F/D 4/FD true/PS()/SS()>>]"
           "/A[<</Type/NumberFormat/U(sf)/C 1/D 100/FD true/SS()>>]/T[<</Type/NumberFormat/U<B0>/C 1/D 100/FD true/PS()/SS()>>]"
           "/V[<</Type/NumberFormat/U(cu ft)/C 1/D 100/FD true/SS()>>]>>")


def ftin(ft):
    return "%d'-%d\"" % (int(ft), int(round((ft - int(ft)) * 12)))


def to_support_fn(model):
    db = sr.cr.connect(model)
    cols, walls, beams = sr.columns(db), sr.segments(db, "Wall"), sr.segments(db, "Beam")

    def f(x, y):
        best = min((max(abs(x - cx) - b / 24, 0) ** 2 + max(abs(y - cy) - d / 24, 0) ** 2) ** 0.5 for cx, cy, b, d in cols)
        for x0, y0, x1, y1, w in walls + beams:
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy or 1e-9
            t = min(1.0, max(0.0, ((x - x0) * dx + (y - y0) * dy) / L2))
            best = min(best, max(math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)) - w / 24, 0))
        return best
    return f


def add_square(page, rect, author):
    a = page.add_rect_annot(rect)
    a.set_colors(stroke=ORANGE, fill=ORANGE)
    a.set_border(width=1)
    a.set_opacity(0.5)
    a.set_info(title=author, subject="Rectangle")
    a.update()
    return a


def add_text(page, rect, text, author):
    a = page.add_freetext_annot(rect, text, fontsize=12, fontname="helv", text_color=BLACK, fill_color=WHITE, border_width=0)
    a.set_info(title=author, subject="Text Box")
    a.update()
    doc = page.parent
    doc.xref_set_key(a.xref, "DS", "(font: Helvetica 12pt; text-align:left; margin:3pt; line-height:13.8pt; color:#000000)")
    doc.xref_set_key(a.xref, "C", "[1 1 1]")
    return a


def add_dim(page, p1, p2, text, author, helv_xref, measure_xref):
    """A Bluebeam length measurement from p1 to p2 (page points, y down). The dimension line sits 34 pt outside:
    below a horizontal measure, left of a vertical one. The appearance is drawn the way Revu draws its own."""
    doc = page.parent
    a = page.add_line_annot(pymupdf.Point(*p1), pymupdf.Point(*p2))
    a.set_colors(stroke=RED, fill=RED)
    a.set_border(width=1)
    a.set_line_ends(pymupdf.PDF_ANNOT_LE_CLOSED_ARROW, pymupdf.PDF_ANNOT_LE_CLOSED_ARROW)
    a.set_info(title=author, subject="Length Measurement", content=text)
    a.update()
    x = a.xref
    H = page.rect.height
    (x1, y1), (x2, y2) = (p1[0], H - p1[1]), (p2[0], H - p2[1])        # PDF coordinates, y up
    horizontal = abs(y2 - y1) < abs(x2 - x1)
    LL = 33.90881
    if horizontal:
        dline = [(x1, y1 - LL), (x2, y2 - LL)]
        ext = [((x1, y1), (x1, y1 - LL - 2)), ((x2, y2), (x2, y2 - LL - 2))]
    else:
        dline = [(x1 - LL, y1), (x2 - LL, y2)]
        ext = [((x1, y1), (x1 - LL - 2, y1)), ((x2, y2), (x2 - LL - 2, y2))]
    (ax, ay), (bx, by) = dline
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    tw = 6.7 * len(text)                                                # Helvetica 12 pt, about 6.7 pt a character
    mx, my = (ax + bx) / 2, (ay + by) / 2
    gap = tw / 2 + 2
    s = ["1 0 0 RG 1 0 0 rg 1 w"]
    for (ex0, ey0), (ex1, ey1) in ext:
        s.append("%.3f %.3f m %.3f %.3f l S" % (ex0, ey0, ex1, ey1))
    s.append("%.3f %.3f m %.3f %.3f l S" % (ax + ux, ay + uy, mx - ux * gap, my - uy * gap))
    s.append("%.3f %.3f m %.3f %.3f l S" % (bx - ux, by - uy, mx + ux * gap, my + uy * gap))
    for (px, py, dx, dy) in ((ax, ay, ux, uy), (bx, by, -ux, -uy)):     # closed arrows, 7.8 long and 9 wide
        nx, ny = -dy, dx
        s.append("%.3f %.3f m %.3f %.3f l %.3f %.3f l b" % (px + dx * 7.8 + nx * 4.5, py + dy * 7.8 + ny * 4.5, px, py,
                                                           px + dx * 7.8 - nx * 4.5, py + dy * 7.8 - ny * 4.5))
    if horizontal:
        s.append("BT 1 0 0 rg /Helv 12 Tf 1 0 0 1 %.3f %.3f Tm (%s) Tj ET" % (mx - tw / 2, my - 4.3, text))
    else:
        s.append("BT 1 0 0 rg /Helv 12 Tf 0 1 -1 0 %.3f %.3f Tm (%s) Tj ET" % (mx + 4.3, my - tw / 2, text))
    xs = [x1, x2, ax, bx] + [e[1][0] for e in ext]
    ys = [y1, y2, ay, by] + [e[1][1] for e in ext]
    bbox = [min(xs) - 14, min(ys) - 14, max(xs) + 14, max(ys) + 14]
    ap = doc.get_new_xref()
    doc.update_object(ap, "<</Type/XObject/Subtype/Form/FormType 1/BBox[%.3f %.3f %.3f %.3f]/Matrix[1 0 0 1 %.3f %.3f]"
                          "/Resources<</ProcSet[/PDF/Text]/Font<</Helv %d 0 R>>>>>>" % (bbox[0], bbox[1], bbox[2], bbox[3], -bbox[0], -bbox[1], helv_xref))
    doc.update_stream(ap, "\n".join(s).encode())
    doc.xref_set_key(x, "AP", "<</N %d 0 R>>" % ap)
    doc.xref_set_key(x, "Rect", "[%.3f %.3f %.3f %.3f]" % tuple(bbox))
    doc.xref_set_key(x, "IT", "/LineDimension")
    doc.xref_set_key(x, "Cap", "true")
    doc.xref_set_key(x, "LL", "%.5f" % (-LL if horizontal and x2 > x1 else (LL if horizontal else (-LL if y2 > y1 else LL))))
    doc.xref_set_key(x, "LLE", "2")
    doc.xref_set_key(x, "Measure", "%d 0 R" % measure_xref)
    doc.xref_set_key(x, "MeasurementTypes", "130")
    doc.xref_set_key(x, "SlopeType", "0")
    doc.xref_set_key(x, "PitchRun", "12")
    doc.xref_set_key(x, "Label", "()")
    doc.xref_set_key(x, "DS", "(font: Helvetica 12pt; text-align:center; line-height:13.8pt; color:#FF0000)")
    doc.xref_set_key(x, "DepthUnit", "[<</Type/NumberFormat/U(')/C .001157407/D 100/FD true/SS()>>]")
    return a


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sheets", type=Path)
    p.add_argument("zones", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--model", type=Path, required=True, help="saved Concept model, for the supports (which end is the face)")
    p.add_argument("--fits", type=Path, default=Path("plans"))
    p.add_argument("--author", default="GKG")
    p.add_argument("--drop-sample", action="store_true", help="leave out the engineer's own sample set on the sheets")
    p.add_argument("--report", type=Path)
    a = p.parse_args(argv)
    zones = json.loads(a.zones.read_text(encoding="utf-8"))
    to_support = to_support_fn(a.model)
    doc = pymupdf.open(a.sheets)
    helv = doc.get_new_xref()
    doc.update_object(helv, "<</Type/Font/Subtype/Type1/BaseFont/Helvetica/Encoding/WinAnsiEncoding>>")
    meas = doc.get_new_xref()
    doc.update_object(meas, MEASURE)
    fits = {}
    import re as _re
    sheets = {}
    for i, page in enumerate(doc):
        names = [w.strip() for w in page.get_text().splitlines() if _re.fullmatch(r"S\d{3}[A-Z]?", w.strip())]
        sheets[i] = names[-1] if names else "S101%s" % "ABC"[i]
        f = a.fits / ("fit-%s.txt" % sheets[i])
        if f.exists():
            S, ox, oy, H = [float(v) for v in f.read_text().split()[:4]]
            fits[i] = (S, ox, oy, H)
        if a.drop_sample:
            for an in list(page.annots()):
                if an.info.get("title") != a.author and an.info.get("subject") in ("Rectangle", "Text Box", "Length Measurement"):
                    page.delete_annot(an)
    report, placed = [], 0
    for z in zones:
        a0, b0 = (z["x0"], z["y0"]), (z["x1"], z["y1"])
        face, far = (a0, b0) if to_support(*a0) <= to_support(*b0) else (b0, a0)
        L = math.hypot(far[0] - face[0], far[1] - face[1]) or 1.0
        ux, uy = (far[0] - face[0]) / L, (far[1] - face[1]) / L
        nx, ny = -uy, ux
        W, Lft = z["width_ft"], z["length_ft"]
        through = to_support(*a0) > 0.3 and to_support(*b0) > 0.3 and any(
            to_support(face[0] + ux * t, face[1] + uy * t) < 0.3 for t in (L * 0.25, L * 0.5, L * 0.75))
        if through:                                       # the zone runs through its support: keep its centre
            cx, cy = (a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2
            c = [(cx - ux * Lft / 2 + nx * W / 2, cy - uy * Lft / 2 + ny * W / 2), (cx + ux * Lft / 2 + nx * W / 2, cy + uy * Lft / 2 + ny * W / 2),
                 (cx + ux * Lft / 2 - nx * W / 2, cy + uy * Lft / 2 - ny * W / 2), (cx - ux * Lft / 2 - nx * W / 2, cy - uy * Lft / 2 - ny * W / 2)]
        else:
            c = [(face[0] + nx * W / 2, face[1] + ny * W / 2), (face[0] + ux * Lft + nx * W / 2, face[1] + uy * Lft + ny * W / 2),
                 (face[0] + ux * Lft - nx * W / 2, face[1] + uy * Lft - ny * W / 2), (face[0] - nx * W / 2, face[1] - ny * W / 2)]
        xs, ys = [q[0] for q in c], [q[1] for q in c]
        mx, my = sum(xs) / 4, sum(ys) / 4
        best = None
        for i, (S, ox, oy, H) in fits.items():
            px, py = ox + S * mx, oy + S * my
            m = min(px, 2592 - px, py, H - py)
            if m > 0 and (best is None or m > best[0]):
                best = (m, i)
        if best is None:
            report.append(dict(id=z["id"], page=None, note="centre on no sheet"))
            print("NOT ON A SHEET:", z["id"])
            continue
        i = best[1]
        S, ox, oy, H = fits[i]
        page = doc[i]
        P = lambda x, y: (ox + S * x, H - (oy + S * y))          # model ft -> page pt, y down
        pr = pymupdf.Rect(P(min(xs), max(ys)), P(max(xs), min(ys)))
        add_square(page, pr, a.author)
        tw, th = 30, 20
        add_text(page, pymupdf.Rect(pr.x0 + (pr.width - tw) / 2, pr.y0 + (pr.height - th) / 2,
                                    pr.x0 + (pr.width + tw) / 2, pr.y0 + (pr.height + th) / 2), "ST1", a.author)
        along_x = abs(ux) >= abs(uy)
        bottom = ((pr.x0, pr.y1), (pr.x1, pr.y1))
        left = ((pr.x0, pr.y0), (pr.x0, pr.y1))
        if along_x:
            add_dim(page, bottom[0], bottom[1], ftin(Lft), a.author, helv, meas)     # length runs with x: below
            add_dim(page, left[0], left[1], ftin(W), a.author, helv, meas)           # width across: left
        else:
            add_dim(page, bottom[0], bottom[1], ftin(W), a.author, helv, meas)
            add_dim(page, left[0], left[1], ftin(Lft), a.author, helv, meas)
        placed += 1
        report.append(dict(id=z["id"], page=sheets[i], width_ft=W, length_ft=Lft, face=list(face), through=through,
                           model_rect=[min(xs), min(ys), max(xs), max(ys)], page_rect=[pr.x0, pr.y0, pr.x1, pr.y1]))
        print("  %-4s %s %2d x %2d ft at model (%.1f,%.1f)-(%.1f,%.1f) -> page (%.0f,%.0f)-(%.0f,%.0f)%s" % (
            z["id"], sheets[i], W, Lft, min(xs), min(ys), max(xs), max(ys), pr.x0, pr.y0, pr.x1, pr.y1, "  through the support" if through else ""))
    doc.save(a.out, garbage=1, deflate=True)
    print("%d of %d zones tagged -> %s" % (placed, len(zones), a.out))
    if a.report:
        a.report.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
