#!/usr/bin/env python3
"""Stitch the tiled pages of Concept's Report > Export Window to PDF into one full-extent image.

  python stitch-concept-pdf.py <in.pdf> <out.png> [dpi]

Concept prints a plan at its plot scale across several pages; every page
holds the whole drawing, shifted and clipped to that page's window. Needs
pymupdf and Pillow.
"""
import sys
import pymupdf
from PIL import Image, ImageChops

src, out = sys.argv[1], sys.argv[2]
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 300
doc = pymupdf.open(src)
clips = [d.get("scissor") or d["rect"] for d in doc[0].get_drawings(extended=True) if d.get("type") == "clip"]
win = max(clips, key=lambda r: (r.y1 - r.y0) * (r.x1 - r.x0) if r.y0 > 60 else 0)      # the plan window, below the header
offsets = []
for pg in doc:
    boxes = [d["rect"] for d in pg.get_drawings()]
    offsets.append((min(b.x0 for b in boxes), min(b.y0 for b in boxes)))
xs = sorted({round(x) for x, _ in offsets}, reverse=True)
ys = sorted({round(y) for _, y in offsets}, reverse=True)
k = dpi / 72
w, h = round(win.width * k), round(win.height * k)
sheet = Image.new("RGB", (w * len(xs), h * len(ys)), "white")
for pg, (x, y) in zip(doc, offsets):
    pix = pg.get_pixmap(dpi=dpi, clip=win)
    tile = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).resize((w, h))
    sheet.paste(tile, (xs.index(round(x)) * w, ys.index(round(y)) * h))
box = ImageChops.difference(sheet, Image.new("RGB", sheet.size, "white")).getbbox()
pad = round(0.3 * dpi)
sheet = sheet.crop((max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, sheet.width), min(box[3] + pad, sheet.height)))
sheet.save(out)
print(out, sheet.size, f"{len(xs)}x{len(ys)} pages")
