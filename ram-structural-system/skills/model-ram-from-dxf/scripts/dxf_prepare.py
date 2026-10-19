#!/usr/bin/env python3
"""Prepare an architect's DXF for RAM Modeler's import: one insert per column, the drawing near 0,0, unused blocks out.

  python dxf_prepare.py <floor.dxf> [--out <floor_RAM.dxf>] [--column-layer COL]

Deletes inserts that sit on a point another insert of the same angle already holds (Revit exports
carry doubles), then moves every model-space entity so the drawing's lower-left corner lands within
a foot of the origin, on whole feet (the Modeler manual refuses coordinates far from 0,0). Writes a
new file beside the source (`<name>_RAM.dxf` unless --out) and never touches the source. Blocks
nothing inserts or names as a dimension arrow are deleted, so the import dialog's 100-block list
reaches the column block; layers and everything else are left as they are. Proven on 2612_08,
2026-10-15 and 2026-10-19. Needs ezdxf.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import ezdxf

TOL = 0.05        # inches: inserts closer than this are on one point


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dxf", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--column-layer", default="COL")
    p.add_argument("--overwrite", action="store_true")
    a = p.parse_args()
    out = a.out or a.dxf.with_name(a.dxf.stem.split("FLOORPLAN")[0].rstrip("_- ") + "_RAM.dxf")
    if out.resolve() == a.dxf.resolve():
        print("the output would overwrite the source; give --out a new name")
        return 2
    if out.exists() and not a.overwrite:
        print(f"{out} exists; pass --overwrite or --out")
        return 2
    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()

    seen, doubles = set(), []
    for e in msp.query("INSERT"):
        if e.dxf.layer != a.column_layer:
            continue
        k = (round(e.dxf.insert.x / TOL), round(e.dxf.insert.y / TOL), round(e.dxf.rotation % 360, 1))
        if k in seen:
            doubles.append(e)
        else:
            seen.add(k)
    for e in doubles:
        msp.delete_entity(e)

    pts = []
    for e in msp:
        if e.dxftype() == "LINE":
            pts += [e.dxf.start, e.dxf.end]
        elif e.dxftype() == "INSERT":
            pts.append(e.dxf.insert)
        elif e.dxftype() == "LWPOLYLINE":
            pts += [ezdxf.math.Vec3(q[0], q[1]) for q in e.get_points()]
    if not pts:
        print("nothing to move: no lines, polylines or inserts in model space")
        return 2
    minx, miny = min(q.x for q in pts), min(q.y for q in pts)
    dx, dy = -math.floor(minx / 12) * 12, -math.floor(miny / 12) * 12
    for e in msp:
        try:
            e.translate(dx, dy, 0)
        except (AttributeError, NotImplementedError):
            print(f"  not moved: {e.dxftype()} on {e.dxf.layer}")
    doc.header["$EXTMIN"] = (minx + dx, miny + dy, 0)
    doc.header["$EXTMAX"] = (max(q.x for q in pts) + dx, max(q.y for q in pts) + dy, 0)

    # RAM's Import DXF dialog lists only the first 100 block names; a Revit export carries hundreds
    # (984 on 2612_08, the column block at 463), so the column block never shows. Keep only the used ones.
    used = set()
    for layout in doc.layouts:
        used |= {e.dxf.name for e in layout.query("INSERT")}
    for style in doc.dimstyles:        # arrow blocks are named by the dimension styles, not inserted (TICK1 on 2612_08)
        for attr in ("dimblk", "dimblk1", "dimblk2", "dimldrblk"):
            name = style.dxf.get(attr)                       # by name (the Revit export) or by handle (QCAD)
            if name:
                used.add(name)
            handle = style.dxf.get(attr + "_handle")         # often empty; get_arrow_block_name raises then
            record = doc.entitydb.get(handle) if handle else None
            if record is not None:
                used.add(record.dxf.name)
    purged, again = 0, True
    while again:                       # a block nested in a deleted block frees up on the next pass
        again = False
        for block in list(doc.blocks):
            if block.name.startswith("*") or block.name in used:
                continue
            try:
                doc.blocks.delete_block(block.name, safe=True)
                purged, again = purged + 1, True
            except ezdxf.DXFBlockInUseError:
                pass
    try:
        doc.saveas(out)
    except Exception:
        out.unlink(missing_ok=True)    # never leave a half-written DXF for the import to read
        raise
    print(f"{len(seen)} columns ({len(doubles)} doubled inserts deleted); moved by ({dx / 12:.0f} ft, {dy / 12:.0f} ft); "
          f"{purged} unused blocks purged; wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
