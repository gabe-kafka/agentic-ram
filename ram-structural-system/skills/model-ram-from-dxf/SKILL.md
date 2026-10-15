---
name: model-ram-from-dxf
description: The first RAM Structural System model of a job from the architect's DXF. The workflow lives in the JT-ENG connector (jt-eng-connector, skills/model-from-dxf); this folder holds the script its tools run. Use the connector's skill and the ram_dxf_inventory tool; read scripts/dxf_inventory.py only to change what the inventory reports.
---

# New RAM model from the architect's DXF

The workflow is the connector's `jt-eng:model-from-dxf` skill. What the
program accepted and how the engineer built the model by hand is in
`../../references/RAM_MODELER_DXF_IMPORT_NOTES.md`, which ships with the
connector too.

```text
qcad.exe -no-gui -autostart scripts/dwg2dxf.js <in.dwg> <out.dxf>     the architect's DWG as a DXF (QCAD, ~20 s)
python scripts/dxf_inventory.py <floor.dxf> [--plan <out.png>]        what the DXF holds, as the import reads it
python scripts/dxf_prepare.py <floor.dxf> [--out <floor_RAM.dxf>]     one insert per column, drawing near 0,0
```

`dxf_inventory.py`: units and extent, each layer and the role its name says,
the columns (inserts, blocks, angles, doubled points), the slab edge (loops,
open ends, junctions, columns left outside), openings, walls, grids.
Read-only. `dxf_prepare.py` writes a new file beside the source and never
touches it. Both need `ezdxf`. `dwg2dxf.js` runs in QCAD's script engine
(`RSettings.getOriginalArguments`); run it from the QCAD folder.
