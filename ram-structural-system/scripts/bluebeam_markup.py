"""Bluebeam-editable markups on RAM report PDFs (pymupdf), in the office markup style.

Office style (engineer, 2026-10-21):
- Highlights are standard PDF Highlight markups: subject "Highlight", 50% opacity, multiply blend.
- Notes are Bluebeam "Text Box" markups: Helvetica 12 pt, red #FF0000, no border, no fill.
  The only styling allowed is bold (**text**) and underline (__text__).
- Wording is terse engineer shorthand, e.g. "V = 934.5k = RAM. OK", "H/893 < H/600 OK".
- With no fill, a note must sit in clear white space: `note()` finds the nearest clear spot.

Use:
    import pymupdf, bluebeam_markup as bm
    doc = pymupdf.open("report.pdf"); page = doc[0]
    bm.highlight(page, page.search_for("934.45", quads=True)[0], bm.YELLOW)
    bm.note(page, (330, 40), "__GOV. DRIFT__: W END, LVL 8\\n1.0E: 0.0019 < 0.005 OK")
    doc.save("report - marked up.pdf", garbage=3, deflate=True)

pymupdf traps this works around (pymupdf 1.28):
- A rich-text FreeText appearance is laid out in a box 24 pt taller than the annotation and
  flipped by the annotation height, so text lands 24 pt low: `text_box` patches the flip.
- `set_info(content=...)` followed by `update()` redraws from plain text and drops bold and
  underline: `text_box` writes /T, /Subj, /Contents directly and never calls update().
- The rich-text `style` argument takes CSS declarations only (it is wrapped in body{...}).
"""
import html
import re

import numpy as np
import pymupdf

AUTHOR = "Claude"
FS, LH, PAD = 12, 13.8, 3
STYLE = f"font:Helvetica {FS}pt; text-align:left; margin:{PAD}pt; line-height:{LH}pt; color:#FF0000"
DS = f"font: Helvetica {FS}pt; text-align:left; margin:{PAD}pt; line-height:{LH}pt; color:#FF0000"
CSS = f"font-family: sans-serif; font-size: {FS}pt; color: #FF0000; line-height: 1.15;"
YELLOW, GREEN, BLUE, ORANGE = (1, 0.93, 0.2), (0.55, 0.9, 0.45), (0.55, 0.8, 1), (0.93, 0.45, 0.05)
MARK = re.compile(r"(\*\*.+?\*\*|__.+?__)")


def highlight(page, area, color, note=""):
    """A standard Highlight markup over a Rect or Quad: 50% opacity, multiply blend."""
    a = page.add_highlight_annot(area)
    a.set_colors(stroke=color)
    a.set_opacity(0.5)
    a.set_blendmode(pymupdf.PDF_BM_Multiply)
    a.set_info(title=AUTHOR, subject="Highlight", content=note)
    a.update()
    return a


def plain(text):
    return MARK.sub(lambda m: m.group(0)[2:-2], text)


def _spans(line, bold, underline):
    out = []
    for part in MARK.split(line):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(bold(html.escape(part[2:-2], quote=False)))
        elif part.startswith("__") and part.endswith("__"):
            out.append(underline(html.escape(part[2:-2], quote=False)))
        else:
            out.append(html.escape(part, quote=False))
    return "".join(out) or "&#160;"


def _rc(text):
    """Bluebeam's /RC rich text, so the box stays editable in Revu."""
    paras = "".join("<p>" + _spans(line, lambda s: f'<span style="font-weight:bold">{s}</span>',
                                   lambda s: f'<span style="text-decoration:underline">{s}</span>') + "</p>"
                    for line in text.split("\n"))
    return ('<?xml version="1.0"?><body xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/" '
            'xfa:contentType="text/html" xfa:APIVersion="BluebeamPDFRevu:2018" xfa:spec="2.2.0" '
            f'style="{STYLE}" xmlns="http://www.w3.org/1999/xhtml">{paras}</body>')


def _appearance(text):
    return "".join("<p>" + _spans(line, lambda s: f"<b>{s}</b>", lambda s: f"<u>{s}</u>") + "</p>"
                   for line in text.split("\n"))


def text_width(s):
    return pymupdf.get_text_length(s, fontname="hebo", fontsize=FS)   # bold width covers both


def height(text, w):
    n = 0
    for para in plain(text).split("\n"):
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if text_width(trial) <= w - 2 * PAD - 10 or not line:
                line = trial
            else:
                n += 1
                line = word
        n += 1
    return n * 14.4 + 10


def text_box(page, x0, y0, w, text):
    """A Bluebeam Text Box at (x0, y0), width w, height fitted to the text."""
    rect = pymupdf.Rect(x0, y0, x0 + w, y0 + height(text, w))
    a = page.add_freetext_annot(rect, _appearance(text), richtext=True, style=CSS, border_width=0)
    doc = page.parent
    ap = int(doc.xref_get_key(a.xref, "AP/N")[1].split()[0])
    s = doc.xref_stream(ap).decode("latin-1")
    m = re.search(r"1 0 0 -1 -?0 ([\d.]+) cm\nq\n0 0 ([\d.]+) ([\d.]+) re", s)
    if m:   # flip by the layout box height, not the annotation height (24 pt offset)
        fixed = m.group(0).replace(f"-1 -0 {m.group(1)} cm", f"-1 -0 {m.group(3)} cm").replace(
            f"-1 0 {m.group(1)} cm", f"-1 0 {m.group(3)} cm")
        doc.update_stream(ap, s.replace(m.group(0), fixed, 1).encode("latin-1"))
    for key, val in (("T", pymupdf.get_pdf_str(AUTHOR)), ("Subj", pymupdf.get_pdf_str("Text Box")),
                     ("Contents", pymupdf.get_pdf_str(plain(text))),
                     ("DA", pymupdf.get_pdf_str(f"0 0 0 rg /Helv {FS} Tf")), ("DS", pymupdf.get_pdf_str(DS)),
                     ("RC", pymupdf.get_pdf_str(_rc(text))), ("BS", "<</W 0/S/S/Type/Border>>"),
                     ("C", "[]"), ("CL", "null"), ("IC", "null")):
        doc.xref_set_key(a.xref, key, val)
    return rect


INK_DPI = 36


def _ink(page):
    """Integral image of inked pixels of the printed page (markups left out)."""
    pix = page.get_pixmap(dpi=INK_DPI, annots=False, colorspace=pymupdf.csGRAY)
    ink = (np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 235).astype(np.int32)
    return np.pad(ink.cumsum(0).cumsum(1), ((1, 0), (1, 0)))


def _inked(integral, r):
    k = INK_DPI / 72
    x0, y0 = max(int(r.x0 * k), 0), max(int(r.y0 * k), 0)
    x1, y1 = min(int(r.x1 * k) + 1, integral.shape[1] - 1), min(int(r.y1 * k) + 1, integral.shape[0] - 1)
    return integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0] > 0


def free_spot(page, w, text, near):
    """Top-left and width of the clear rectangle nearest `near` that fits the text.
    Pixels catch everything printed (text, lines, frames, raster); existing markups are avoided too."""
    obs = [pymupdf.Rect(a.rect) + (-3, -3, 3, 3) for a in page.annots()]
    integral = _ink(page)
    near = pymupdf.Point(near)
    for width in (w, 260, 220, 180):
        h = height(text, width)
        best = None
        y = 18
        while y + h <= page.rect.height - 18:
            x = 18
            while x + width <= page.rect.width - 18:
                r = pymupdf.Rect(x, y, x + width, y + h)
                if not _inked(integral, r + (-3, -3, 3, 3)) and not any(r.intersects(o) for o in obs):
                    d = (x - near.x) ** 2 + (y - near.y) ** 2
                    if best is None or d < best[0]:
                        best = (d, x, y)
                x += 6
            y += 6
        if best:
            return best[1], best[2], width
    return near.x, near.y, w


def note(page, near, text, width=None):
    """A Text Box in the clear space nearest `near`, as narrow as its longest line allows."""
    widest = max(text_width(s) for s in plain(text).split("\n")) + 2 * PAD + 16
    x, y, w = free_spot(page, min(width or widest, widest), text, near)
    return text_box(page, x, y, w, text)
