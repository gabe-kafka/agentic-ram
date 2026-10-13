#!/usr/bin/env python3
"""Fit plan sheets to the Concept model from the column bubble numbers (SSR workbook 'Plan Col.' -> Concept (x, y)).
Scale from bubble pairs (mode of page/model distance ratios), translation by vote, bubble block offset removed
(about +32, +35 pt up-right of the column). Writes <fits>/fit-<sheet>.txt: scale, ox, oy, page height.

  python fit_sheets.py <sheets.pdf> <SSR.xlsx> <fits dir> [--sheets S101A,S101B,...]   (sheet names read from the page text)
"""
import math, re, statistics, sys
from collections import Counter
from pathlib import Path
import openpyxl, pymupdf

pdf, xlsx, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
wb = openpyxl.load_workbook(xlsx, data_only=True)
ws = wb["SSR Input"] if "SSR Input" in wb.sheetnames else wb[wb.sheetnames[0]]
for row in ws.iter_rows(min_row=1, max_row=15):
    vals = [str(c.value) if c.value is not None else "" for c in row]
    if any("Plan Col" in v for v in vals):
        hdr = {v: i for i, v in enumerate(vals)}; hrow = row[0].row; break
ci = next(i for v, i in hdr.items() if "Plan Col" in v); xi = next(i for v, i in hdr.items() if "Column at" in v)
bub = {}
for row in ws.iter_rows(min_row=hrow + 1, values_only=True):
    if row[ci] is None or row[xi] is None: continue
    m = re.findall(r"-?\d+\.?\d*", str(row[xi]))
    if len(m) >= 2 and str(row[ci]).strip().isdigit(): bub[int(str(row[ci]).strip())] = (float(m[0]), float(m[1]))
d = pymupdf.open(pdf)
BX, BY = 32.0, 35.0
for i, p in enumerate(d):
    H = p.rect.height
    t = p.get_text()
    sheet = ([w.strip() for w in t.split("\n") if re.fullmatch(r"S\d{3}[A-Z]?", w.strip())] or [f"page{i + 1}"])[-1]
    ints = [(int(w[4]), (w[0] + w[2]) / 2, H - (w[1] + w[3]) / 2) for w in p.get_text("words") if re.fullmatch(r"\d{1,2}", w[4]) and int(w[4]) in bub]
    ratios = []
    for a in range(len(ints)):
        for b in range(a + 1, len(ints)):
            na, pxa, pya = ints[a]; nb, pxb, pyb = ints[b]
            if na == nb: continue
            dm = math.hypot(bub[na][0] - bub[nb][0], bub[na][1] - bub[nb][1])
            if dm >= 15: ratios.append(math.hypot(pxa - pxb, pya - pyb) / dm)
    if len(ratios) < 5:
        print(f"page {i + 1} {sheet}: {len(ints)} bubble numbers, too few to fit"); continue
    S = Counter(round(r, 1) for r in ratios).most_common(1)[0][0]
    votes = Counter((round((px - S * bub[n][0]) / 15) * 15, round((py - S * bub[n][1]) / 15) * 15) for n, px, py in ints)
    (ox, oy), nv = votes.most_common(1)[0]
    hits = [(n, px - S * bub[n][0] - ox, py - S * bub[n][1] - oy) for n, px, py in ints if abs(px - S * bub[n][0] - ox) < 20 and abs(py - S * bub[n][1] - oy) < 20]
    ox += statistics.mean(h[1] for h in hits); oy += statistics.mean(h[2] for h in hits)
    ox, oy = ox - BX, oy - BY
    spread = max(math.hypot(h[1] - statistics.mean(x[1] for x in hits), h[2] - statistics.mean(x[2] for x in hits)) for h in hits) / S
    print(f"page {i + 1} {sheet}: {p.rect.width:.0f}x{H:.0f} pt, scale {S} pt/ft, {len(hits)} of {len(ints)} bubbles consistent (spread {spread:.2f} ft), offset ({ox:.1f},{oy:.1f}); "
          f"model window x {(-ox) / S:.0f}..{(p.rect.width - ox) / S:.0f}, y {(-oy) / S:.0f}..{(H - oy) / S:.0f} ft; bubbles {sorted(h[0] for h in hits)}")
    (out / f"fit-{sheet}.txt").write_text(f"{S} {ox:.3f} {oy:.3f} {H} {len(hits)} bubbles spread {spread:.3f}\n")
