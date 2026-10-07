#!/usr/bin/env python3
"""Tag every stud rail column on the column location plan with its SSR mark, as Bluebeam text-box markups.

  python markup_ssr_plan.py <SSR.xlsx> <plan.pdf> <out.pdf> [--page N] [--sheet NAME] [--author NAME]
                            [--report placements.json] [--dry-run]

<SSR.xlsx> is the office stud rail workbook (schedule-ram-concept-stud-rails): one row per stud rail column with its
Mk and the column's Concept (x, y) in feet. <plan.pdf> is the drawing set or a single sheet; the page used is the
column location plan (the one with the most "X:ff'-ii"" labels), or --page. <out.pdf> gets that one page with a
FreeText annotation "SR-n" beside each stud rail column's bubble, the way the 2636_03 handoff was marked by hand:
blue text in a blue box, transparent fill, subject "Text Box", so the drafter can move or retype any tag in Bluebeam.

How the columns are found: the plan prints "X:" and "Y:" from its work point beside each column. The Concept origin
is not the work point, so the shift between them is taken from the data (the most common whole-foot (x - X, y - Y)
over every pairing, refined to the median). Each workbook column is then matched to the label within 1 ft; the
bubble is the standalone integer nearest above that label. Columns that do not match, or whose bubble is not
found, are reported and, unless --dry-run, tagged at the label with a "?" so nothing is silently dropped.

A column whose Mk is NON-TYPICAL (the engineer's equal-length rule) is tagged in red with the fix written in its
COMMENTS cell (for example "DROP CAP 5'x5'x18 1/4" DP"), or "NON-TYPICAL" if the cell is blank.
<plan.pdf> may be a previous run's output: this author's earlier tags are removed from the page first, other
markups (a signature stamp, the drafter's notes) are kept, and <out.pdf> may be that same file.
Read-only on the workbook; the source PDF is read, and rewritten only when it is also the output.
"""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

import openpyxl
import pymupdf

TAG_W, TAG_H = 30.0, 14.0          # "SR-n" in Helvetica 10 pt with 1 pt padding; the 2636_03 hand tags were 35.8 x 14
TAG_DX, TAG_DY = 21.0, -4.0        # fallback only: tag's top-left from the bubble centre, when no column symbol is found
GAP = 0.5                          # the tag's border touches the column symbol's edge
BUBBLE_R = 9.0                     # column bubble circle, pt
BLUE = (0, 0, 1)
RED = (1, 0, 0)


def feet(text):
    m = re.match(r"[XY]:\s*(-?\d+)'(?:-(\d+)(?:\s+(\d+)/(\d+))?)?", text)
    if not m:
        return None
    f, i = int(m.group(1)), int(m.group(2) or 0)
    frac = int(m.group(3)) / int(m.group(4)) if m.group(3) else 0.0
    return f + (i + frac) / 12 * (1 if f >= 0 else -1)


def workbook_rows(path: Path, sheet):
    wb = openpyxl.load_workbook(path, data_only=True)
    names = [n for n in wb.sheetnames if (sheet and n == sheet) or (not sheet and "SSR Input" in n)]
    if not names:
        raise SystemExit(f"no sheet {sheet or 'named like SSR Input'} in {path.name}: {wb.sheetnames}")
    ws = wb[names[0]]
    head = {str(c.value).strip(): c.column for c in ws[3] if c.value}
    mk_col = head.get("Mk")
    xy_col = next((c for h, c in head.items() if h.startswith("Column at")), None)
    note_col = head.get("COMMENTS")
    if not mk_col or not xy_col:
        raise SystemExit(f"{names[0]}: need 'Mk' and 'Column at (x, y) ft' in row 3; found {list(head)}")
    rows = []
    for r in range(4, ws.max_row + 1):
        mk, xy = ws.cell(r, mk_col).value, ws.cell(r, xy_col).value
        if mk and xy:
            x, y = (float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", str(xy))[:2])
            note = str(ws.cell(r, note_col).value or "").strip() if note_col else ""
            mk = str(mk).strip()
            # a NON-TYPICAL column (the engineer's equal-length rule) is tagged with its fix from the comment, in red
            text = (note or mk) if mk.upper().startswith("NON-TYP") else mk
            rows.append(dict(row=r, mk=mk, x=x, y=y, label=text, red=mk.upper().startswith("NON-TYP")))
    return names[0], rows


def plan_labels(page):
    words = page.get_text("words")
    lines = {}
    for w in words:
        lines.setdefault((w[5], w[6]), []).append(w)
    labs = []
    for ws in lines.values():
        ws.sort(key=lambda w: w[0])
        s = " ".join(w[4] for w in ws)
        if s[:2] in ("X:", "Y:") and feet(s) is not None:
            labs.append(dict(axis=s[0], val=feet(s), x=(ws[0][0] + ws[-1][2]) / 2, y=(ws[0][1] + ws[-1][3]) / 2))
    X = [l for l in labs if l["axis"] == "X"]
    Y = [l for l in labs if l["axis"] == "Y"]
    cols = []
    for xl in X:
        yl = min(Y, key=lambda l: math.hypot(l["x"] - xl["x"], l["y"] - xl["y"]), default=None)
        if yl and math.hypot(yl["x"] - xl["x"], yl["y"] - xl["y"]) < 30:
            cols.append(dict(X=xl["val"], Y=yl["val"], px=xl["x"], py=xl["y"]))
    ints = [((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, w[4]) for w in words if re.fullmatch(r"\d{1,3}", w[4])]
    find_bubbles(cols, ints)
    return cols


def similarity(pairs):
    """Least-squares plan feet -> page points: px = ox + s X, py = oy - s Y. pairs: [((X, Y), (px, py)), ...]"""
    n = len(pairs)
    Xb, Yb = sum(a[0] for a, _ in pairs) / n, sum(a[1] for a, _ in pairs) / n
    pxb, pyb = sum(b[0] for _, b in pairs) / n, sum(b[1] for _, b in pairs) / n
    s = (sum((a[0] - Xb) * (b[0] - pxb) - (a[1] - Yb) * (b[1] - pyb) for a, b in pairs)
         / sum((a[0] - Xb) ** 2 + (a[1] - Yb) ** 2 for a, _ in pairs))
    return lambda X, Y: (pxb + s * (X - Xb), pyb - s * (Y - Yb))


def find_bubbles(cols, ints):
    """The bubble (column number) is a block attribute at a fixed offset from the column, so: fit the page from the
    labels, take the dominant offset of integers from the fitted column positions, refit on those bubbles, then
    give every column the nearest unused integer within 30 pt of its predicted bubble spot. A column whose bubble
    was moved by hand keeps the predicted spot (bubble None) so the tag still lands near it."""
    T = similarity([((c["X"], c["Y"]), (c["px"], c["py"])) for c in cols])
    offs = Counter()
    for c in cols:
        px, py = T(c["X"], c["Y"])
        for ix, iy, _ in ints:
            if math.hypot(ix - px, iy - py) < 120:
                offs[(round((ix - px) / 8) * 8, round((iy - py) / 8) * 8)] += 1
    (ux, uy), _ = offs.most_common(1)[0]
    for _ in range(2):
        pairs = []
        for c in cols:
            px, py = T(c["X"], c["Y"])
            b = min(ints, key=lambda w: math.hypot(w[0] - px - ux, w[1] - py - uy))
            if math.hypot(b[0] - px - ux, b[1] - py - uy) < 25:
                pairs.append(((c["X"], c["Y"]), (b[0], b[1])))
        T, ux, uy = similarity(pairs), 0.0, 0.0
    used = set()
    for c in cols:
        c["bx"], c["by"] = T(c["X"], c["Y"])
        c["gx"], c["gy"] = c["bx"], c["by"]          # the block's bubble spot from the fit, kept even when the drafter moved the bubble
        c["bubble"] = None
    for reach in (30, 60):          # first every bubble at its block offset, then the ones the drafter nudged aside
        for c in sorted(cols, key=lambda c: (c["Y"], c["X"])):
            if c["bubble"]:
                continue
            b = min((w for w in ints if w not in used), key=lambda w: math.hypot(w[0] - c["bx"], w[1] - c["by"]), default=None)
            if b and math.hypot(b[0] - c["bx"], b[1] - c["by"]) < reach:
                used.add(b)
                c["bubble"], c["bx"], c["by"] = b[2], b[0], b[1]


def column_symbols(page):
    """The column symbols: small stroked rectangles (a 24 x 16 in column is 9 x 6 pt at 1/16 in = 1 ft).
    Returns their rects; the caller takes the one nearest each bubble."""
    out = []
    for g in page.get_drawings():
        r = g["rect"]
        if g.get("type") == "s" and len(g["items"]) == 1 and 3 <= r.width <= 14 and 3 <= r.height <= 14:
            out.append(r)
    return out


def attach_symbols(cols, symbols, reach=35.0):
    """Give each labelled column the symbol nearest the block's fitted bubble spot, else nearest its actual bubble,
    within `reach` pt. The symbol sits at a fixed offset from the block, so the fitted spot finds it even where the
    drafter moved the bubble. Neighbouring columns are 60 pt or more apart at 15 ft, so the nearest is the column's own."""
    for c in cols:
        c["sym"] = None
        for ax, ay in ((c["gx"], c["gy"]), (c["bx"], c["by"])):
            r = min(symbols, key=lambda r: math.hypot((r.x0 + r.x1) / 2 - ax, (r.y0 + r.y1) / 2 - ay), default=None)
            if r and math.hypot((r.x0 + r.x1) / 2 - ax, (r.y0 + r.y1) / 2 - ay) < reach:
                c["sym"] = tuple(r)
                break


def datum_shift(rows, cols):
    cnt = Counter((round(r["x"] - c["X"]), round(r["y"] - c["Y"])) for r in rows for c in cols)
    (dx0, dy0), n = cnt.most_common(1)[0]
    pairs = [(r["x"] - c["X"], r["y"] - c["Y"]) for r in rows for c in cols
             if abs(r["x"] - c["X"] - dx0) < 1.5 and abs(r["y"] - c["Y"] - dy0) < 1.5]
    dx = sorted(p[0] for p in pairs)[len(pairs) // 2]
    dy = sorted(p[1] for p in pairs)[len(pairs) // 2]
    return dx, dy, n


def tag_width(text):
    """30 pt fits "SR-n"; a longer Mk such as "DROP CAP 5'x5'x18 1/4"" gets a box to fit, 3 pt padding each side."""
    return max(TAG_W, pymupdf.get_text_length(text, fontname="helv", fontsize=10) + 6.0)


def spots(q):
    """Candidate tag rects for one column, in order. With a column symbol: touching its right edge, centred on it
    (the engineer's rule, 2026-10-07: the tag must read as that column's); then touching its left edge; then
    hanging under it. Without a symbol: right of the bubble, then below, then above, as the 2636_03 drafter did."""
    w = q["w"]
    if q.get("sym"):
        x0, y0, x1, y1 = q["sym"]
        top = y1 - TAG_H                   # bottom edge level with the symbol's bottom: up out of the X:/Y: text below
        bx, by = q["bx"], q["by"]          # the column's own bubble, usually up-right of the symbol in the block
        if x1 + GAP - BUBBLE_R < bx < x1 + GAP + w + BUBBLE_R:
            top = max(top, by + BUBBLE_R + GAP)                 # slide down just enough to clear the bubble's circle
        top = min(top, y0)                                      # but never below top-aligned with the symbol
        return [(x1 + GAP, top), (x0 - GAP - w, top), ((x0 + x1) / 2 - w / 2, y1 + GAP)]   # right, left, under
    bx, by = q["bx"], q["by"]
    return [(bx + TAG_DX, by + TAG_DY), (bx + TAG_DX - 8.0, by + TAG_DY + 16.0), (bx + TAG_DX - 8.0, by + TAG_DY - 16.0)]


def settle(placed, bubbles, symbols):
    """Place each tag at its first candidate spot clear of every bubble, every column symbol and every earlier tag.
    Returns the count that did not get their first spot."""
    taken, moved = [], 0
    for q in placed:
        q["w"] = tag_width(q["text"])
        if not q["ok"]:
            taken.append((q["x0"], q["y0"], q["x0"] + q["w"], q["y0"] + TAG_H))
            continue
        own = q.get("sym")

        def circle_hits(r, x, y):        # bubble circle against the tag rect
            cx, cy = min(max(x, r[0]), r[2]), min(max(y, r[1]), r[3])
            return math.hypot(x - cx, y - cy) < BUBBLE_R

        for i, (x0, y0) in enumerate(spots(q)):
            r = (x0, y0, x0 + q["w"], y0 + TAG_H)
            hit = any(circle_hits(r, x, y) for x, y in bubbles if (x, y) != (q["bx"], q["by"]))   # own bubble is handled in spots()
            hit = hit or any(r[0] < s[2] and s[0] < r[2] and r[1] < s[3] and s[1] < r[3] for s in symbols if s != own)
            hit = hit or any(r[0] < t[2] and t[0] < r[2] and r[1] < t[3] and t[1] < r[3] for t in taken)
            if not hit:
                break
        q["x0"], q["y0"] = r[0], r[1]
        moved += i > 0
        taken.append(r)
    return moved


STYLE = "font: Helvetica 10pt; text-align:left; margin:0pt; line-height:11.5pt; color:#0000FF"


def add_tag(page, rect, text, author, red=False):
    """A Bluebeam-style text box: Helvetica 10 pt, 1 pt border drawn in the text colour, no fill. Blue for an SR
    mark; red for a non-typical column's fix, so it reads as something still to resolve."""
    colour = RED if red else BLUE
    style = STYLE.replace("#0000FF", "#FF0000") if red else STYLE
    a = page.add_freetext_annot(rect, text, fontsize=10, fontname="helv", text_color=colour, fill_color=None, border_width=1)
    a.set_info(title=author, subject="Text Box", content=text)
    a.update()
    doc = page.parent
    doc.xref_set_key(a.xref, "DS", f"({style})")
    rc = ('<?xml version="1.0"?><body xmlns="http://www.w3.org/1999/xhtml" xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/" '
          f'xfa:contentType="text/html" xfa:spec="2.2.0" style="{style}"><p>{text}</p></body>')
    doc.xref_set_key(a.xref, "RC", f"({rc})")
    return a


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("workbook", type=Path)
    p.add_argument("plan", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--page", type=int, help="1-based page of the column location plan; default: most X: labels")
    p.add_argument("--sheet", help="workbook sheet; default: the first named like 'SSR Input'")
    p.add_argument("--author", default="GKG", help="Bluebeam author on every tag")
    p.add_argument("--report", type=Path, help="JSON of every placement, for the job record")
    p.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    a = p.parse_args(argv)

    sheet, rows = workbook_rows(a.workbook, a.sheet)
    src = pymupdf.open(a.plan)
    pno = (a.page - 1) if a.page else max(range(len(src)), key=lambda i: src[i].get_text().count("X:"))
    page = src[pno]
    cols = plan_labels(page)
    if len(cols) < 4 or len(rows) < 1:
        raise SystemExit(f"{len(cols)} labelled columns on page {pno + 1}, {len(rows)} workbook rows: nothing to fit")
    symbols = column_symbols(page)
    attach_symbols(cols, symbols)
    dx, dy, n = datum_shift(rows, cols)
    print(f"{sheet}: {len(rows)} stud rail columns. {a.plan.name} page {pno + 1}: {len(cols)} labelled columns, "
          f"{sum(1 for c in cols if c['bubble'])} with a bubble found, {sum(1 for c in cols if c['sym'])} with a column symbol.")
    print(f"Concept origin to plan work point: x + {dx:.2f} ft, y + {dy:.2f} ft ({n} of {len(rows)} columns agree to the foot)")

    placed, problems, used = [], [], {}
    for r in rows:
        c = min(cols, key=lambda c: math.hypot(c["X"] + dx - r["x"], c["Y"] + dy - r["y"]))
        resid = math.hypot(c["X"] + dx - r["x"], c["Y"] + dy - r["y"])
        key = (round(c["px"]), round(c["py"]))
        where = f"({r['x']:.0f},{r['y']:.0f}) {r['mk']}"
        if resid > 1.0:
            problems.append(f"{where}: no plan label within 1 ft (nearest {resid:.1f} ft, bubble {c['bubble']})")
            placed.append(dict(r, bubble=None, text=r["label"] + "?", x0=c["px"] + 10, y0=c["py"] - 7, resid=resid, ok=False))
            continue
        if key in used:
            problems.append(f"{where}: same plan column as {used[key]}")
        used[key] = r["mk"]
        if c["bubble"] is None and c["sym"] is None:
            problems.append(f"{where}: label matched but no bubble or column symbol near it; tagged at the label")
            placed.append(dict(r, bubble=None, sym=None, text=r["label"] + "?", x0=c["px"] + 10, y0=c["py"] - 7, resid=resid, ok=False))
            continue
        if c["sym"] is None:
            problems.append(f"{where}: no column symbol near bubble {c['bubble']}; tagged beside the bubble instead")
        placed.append(dict(r, bubble=c["bubble"] or "?", sym=c["sym"], bx=c["bx"], by=c["by"], text=r["label"],
                           x0=c["bx"] + TAG_DX, y0=c["by"] + TAG_DY, resid=resid, ok=True))

    moved = settle(placed, [(c["bx"], c["by"]) for c in cols if c["bubble"]], [tuple(s) for s in symbols])
    good = [q for q in placed if q["ok"]]
    worst = max((q["resid"] for q in good), default=0.0)
    if moved:
        print(f"{moved} tags could not sit on the right side of their column and went left of it or under it")
    print(f"{len(good)} of {len(rows)} columns tagged at their bubble; worst match {worst:.2f} ft")
    for q in sorted(good, key=lambda q: int(q["bubble"]) if q["bubble"].isdigit() else 999):
        print(f"  col {q['bubble']:>3}  {q['text']:5}  concept ({q['x']:.0f},{q['y']:.0f})")
    if problems:
        print(f"{len(problems)} PROBLEMS:")
        for s in problems:
            print("  " + s)
    by_mk = Counter(q["mk"] for q in rows)
    print("per mark: " + ", ".join(f"{k} x{v}" for k, v in sorted(by_mk.items())))

    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(dict(workbook=str(a.workbook), sheet=sheet, plan=str(a.plan), page=pno + 1,
                                            dx=dx, dy=dy, placements=placed, problems=problems), indent=1), encoding="utf-8")
        print("report:", a.report)
    if a.dry_run:
        return 0
    out = pymupdf.open()
    out.insert_pdf(src, from_page=pno, to_page=pno)
    pg = out[0]
    old = [an for an in pg.annots() if an.type[1] == "FreeText" and an.info.get("title") == a.author]
    for an in old:                      # a rerun on a previous markup: this author's earlier tags go, other markups stay
        pg.delete_annot(an)
    if old:
        print(f"removed {len(old)} earlier tags by {a.author} from the source page; other markups kept")
    for q in placed:
        add_tag(pg, pymupdf.Rect(q["x0"], q["y0"], q["x0"] + q["w"], q["y0"] + TAG_H), q["text"], a.author, red=q.get("red", False))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if a.out.resolve() == a.plan.resolve():       # writing over the source: finish the file first, then swap it in
        tmp = a.out.with_name(a.out.stem + ".new.pdf")
        out.save(tmp, garbage=3, deflate=True)
        out.close(); src.close()
        tmp.replace(a.out)
    else:
        out.save(a.out, garbage=3, deflate=True)
    print(f"wrote {a.out} ({len(placed)} tags, page {pno + 1} of {a.plan.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
