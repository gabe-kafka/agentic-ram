#!/usr/bin/env python3
"""Read the engineer's markup off a PDF: every annotation's type, colour, text and geometry, and a picture of each page.

  python read_markup.py <marked-up.pdf> <out_dir>

Writes <out_dir>/annots.json (one entry per page: size in points and its annotations) and page-N.png with the
markup drawn in. Read-only on the PDF. Needs pymupdf. Next: markup_plan.py fits the marks to the model.

Only annotations are read (Bluebeam or Acrobat markups: squares, polygons, ink, text boxes). Marks that were
flattened into the page are in the picture and not in annots.json.
"""
import json
import sys
from pathlib import Path


def flat(v):
    if isinstance(v, (list, tuple)):
        for w in v:
            yield from flat(w)
    else:
        yield round(float(v), 1)


def read(pdf: Path, out: Path, dpi: int = 110):
    import pymupdf
    out.mkdir(parents=True, exist_ok=True)
    pages = []
    for i, page in enumerate(pymupdf.open(pdf)):
        png = out / f"page-{i + 1}.png"
        page.get_pixmap(dpi=dpi, annots=True).save(png)
        info = dict(page=i + 1, width=page.rect.width, height=page.rect.height, annots=[])
        for a in page.annots() or []:
            d = dict(type=a.type[1], content=(a.info.get("content") or "").strip(), rect=[round(v, 1) for v in a.rect],
                     stroke=a.colors.get("stroke"), fill=a.colors.get("fill"))
            if a.vertices:
                v = list(flat(a.vertices))
                d["vertices"] = [v[k:k + 2] for k in range(0, len(v) - 1, 2)]
            info["annots"].append(d)
        pages.append(info)
    (out / "annots.json").write_text(json.dumps(pages, indent=1), encoding="utf-8")
    return pages


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    pdf, out = Path(argv[0]), Path(argv[1])
    for info in read(pdf, out):
        kinds = {}
        for a in info["annots"]:
            key = (a["type"], tuple(a["stroke"] or ()))
            kinds[key] = kinds.get(key, 0) + 1
        print(f"page {info['page']}: {info['width']:.0f} x {info['height']:.0f} pt, {len(info['annots'])} annotations -> page-{info['page']}.png")
        for (kind, stroke), n in sorted(kinds.items()):
            print(f"  {n:3d} {kind:9s} stroke {list(stroke)}")
    print("annotations:", out / "annots.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
