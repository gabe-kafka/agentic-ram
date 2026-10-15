# RAM Modeler DXF import notes

Written 2026-10-15 on 2612_08 (1300 Manhattan Ave, 10th floor SL1), the
engineer building the model by hand with Claude reading the manual
(`RAMModeler.pdf` 2.6-2.7, 2.17, 3.1-3.3, p.146) and the screen. *seen* =
confirmed on screen that day; *manual* = from the manual, not yet seen.

## Getting a DXF from the architect's DWG

QCAD 3.33 on the office PC (`%LOCALAPPDATA%\Programs\QCAD`, with the DWG
plugin `qcaddwg.dll`) converts headlessly, about 20 s a drawing (15 s of it
the add-on's trial pause):

```text
qcad.exe -no-gui -autostart <repo>\ram-structural-system\skills\model-ram-from-dxf\scripts\dwg2dxf.js <in.dwg> <out.dxf>
```

Run from the QCAD folder. Writes DXF 2013 (*seen*: opens clean in ezdxf,
inches, every entity). Dead ends: DWG TrueView's `accoreconsole.exe` refuses
`DXFOUT`, `SAVEAS` and `-EXPORT` ("Unknown command"); QCAD's `dwg2dwg.bat`
wants `qcadcmd.com` and a Pro script that are not installed; ezdxf cannot
read DWG at all.

## What the DXF must carry

One layer per role, model space, inches, near 0,0. The import takes
(*seen*, the Import DXF dialog): Grids, Grid Labels, Slab Edges, Slab
Openings, Columns, Frame Columns, Hanging Columns, Frame Hang. Cols., Beams,
Frame Beams, Joists. **Walls are not on the list** and never import.

| Layer (office name) | Entities | Role |
|---|---|---|
| `COL` | block inserts; insert point = column centre, insert rotation = column angle | Columns |
| `EDGE` | lines end to end | Slab Edges |
| `FLR_OPNG` | lines, closed loops | Slab Openings |
| `WALL` | lines | not imported; see the workaround below |
| `GRID` | lines (+ text) | Grids, Grid Labels |

Columns must be blocks (polylines are not read; *manual*). The block is
named in the dialog under a steel shape: `HSS-SECTION-RAM` (David
Pruscino's 6 x 6 square) goes under **Rectangular HS** (*seen*).

Prepare the file before importing (`scripts/dxf_prepare.py` does both):

- **One insert per column.** 2612_08 had 147 inserts on 103 points, 44
  points with two identical inserts; the import makes a column for each.
- **Near 0,0.** The manual refuses coordinates "excessively large" (2,000 ft
  off); 2612_08 sat 1,190 ft, 621 ft off in Revit shared coordinates. The
  script moves the lower-left corner to whole feet from the origin.

## Order of work

1. RAM Manager `File > New` (*seen*; defaults from `Tools > RAM Defaults
   Utility`, *manual*). The model lives in the job's `03_RAM Structural`
   folder; Manager writes a `.usr` beside it while open.
2. Modeler `Layout > Type > Select`: name in Floor Type ID, Add, Select
   (*seen*). The import only goes into an **empty** layout type; if it comes
   in wrong, delete the layout type (not yet in Story Data), add it again,
   import again (*manual*, p.42).
3. `Material` menu → Concrete, before the import.
4. `Layout > Type > Import from DXF` (*seen*): pick the file; Slab Edges
   `EDGE`, Columns `COL`, other layers `*None`; Rectangular HS
   `HSS-SECTION-RAM`, Round HS `*None` (it defaults to `*As Circle Entity`),
   Grid Label Symbol `*None` (defaults to `*As Text Entity`), Cantilever
   `*None`; Save Settings; OK.
5. What the import made (*seen*):
   - Columns at every insert, **turned columns at their insert angle**
     (the squares on the curved wing came in tilted). No orientation pass
     needed.
   - The columns come in as **steel** (the dialog's block list is steel
     shapes). Make them concrete: `Material` → Concrete, `Layout > Columns >
     Change Materials`, set f'c, **Fence** the plan (*manual* p.146, done
     on 2612_08).
   - Size: `PropTable > Column Sections` (Concrete mode) → add `14x24`;
     `Layout > Columns > Assign Size` → `14x24` → Fence. The DXF block
     carries no size and the import stamps the default.
   - Slab edge in as segments with 0.0 overhang; the DXF's open ends and
     balcony junctions are now gaps and crossings: `Layout > Slab > Slab
     Edge`.
6. Walls, not imported. Workaround (proposed, not yet seen): on a fresh
   layout type map the `WALL` layer to **Grids** so each wall line becomes a
   grid line to snap on, then `Layout > Walls > Add On-Grid`, concrete,
   thickness; delete the wall grids after. Otherwise `Add Off-Grid` with the
   endpoints typed in (`dxf_inventory.py` does not list them; a one-off
   script printed them in feet on 2612_08).
7. Slab edge where the DXF has none, by hand. `PropTable > Decking` →
   `Layout > Slab > Deck Assign` (*manual*).
8. `Story`: level number, floor type, floor-to-floor height, label; the same
   floor type only on adjacent levels (*manual*).
9. `Integrity > DataCheck`, Integrated for a model going to Concrete
   (*manual*).

## 2612_08 input as received (26-10-13)

`...\03_RAM Structural\DXF Inputs\26-10-13\FloorPlan-10TH(SL1)FLOORPLAN(ELEV179-5').dxf`
(inches, Revit export reworked by David Pruscino). `COL` 147 inserts on 103
points, 60 turned to odd angles along the curved wing; `EDGE` 106 lines, the
curved west wing and the middle box only, 47 columns of the east wing with no
edge, 14 open ends, 14 T-junctions; `WALL` 20 lines (two shaft boxes, a
double box, five single lines); nothing else. The prepared file is
`FloorPlan-10TH(SL1)_RAM.dxf` beside it (103 columns, moved to 0..507 ft by
0..177 ft), which the engineer then touched up in QCAD before importing: the
notch in the north-west corner of the edge squared off (four lines became
one; 122 edge lines in the file on S:, 126 from the script).
`scripts/dxf_inventory.py` reports all of this.

## Open

- Whether the import honours Concrete material mode at import time (step 3
  was set after the first import on 2612_08).
- The wall-grid workaround, step 6.
- Which side of a turned 14 x 24 is the long one: the block was square, so
  the angle is right but the long side must be checked against the
  architect's plan.
