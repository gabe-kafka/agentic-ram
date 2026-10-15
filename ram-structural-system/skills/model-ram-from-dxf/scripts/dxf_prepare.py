#!/usr/bin/env python3
"""Prepare an architect's DXF for RAM Modeler's import: one insert per column, the drawing near 0,0.

  python dxf_prepare.py <floor.dxf> [--out <floor_RAM.dxf>] [--column-layer COL]

Deletes inserts that sit on a point another insert of the same angle already holds (Revit exports
carry doubles), then moves every model-space entity so the drawing's lower-left corner lands within
a foot of the origin, on whole feet (the Modeler manual refuses coordinates far from 0,0). Writes a
new file beside the source (`<name>_RAM.dxf` unless --out) and never touches the source. Layers,
blocks and everything else are left as they are. Proven on 2612_08, 2026-10-15. Needs ezdxf.
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
    doc.saveas(out)
    print(f"{len(seen)} columns ({len(doubles)} doubled inserts deleted); moved by ({dx / 12:.0f} ft, {dy / 12:.0f} ft); wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
