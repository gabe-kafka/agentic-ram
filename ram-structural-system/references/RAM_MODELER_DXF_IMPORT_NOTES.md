# RAM Modeler DXF import notes

Written 2026-10-15 and 2026-10-16 on 2612_08 (1300 Manhattan Ave, 10th floor
SL1), RAM Structural System 2026 (Modeler 26.00.00.222). On 10-15 the
engineer built by hand with Claude reading the manual (`RAMModeler.pdf`); on
10-16 Claude drove Modeler by computer use with the engineer watching.
*seen* = confirmed on screen; *manual* = from the manual, not yet seen.

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
| `WALL` | lines | Beams, as placeholders for drawing walls (see Walls) |
| `GRID` | lines (+ text) | Grids, Grid Labels |

Columns must be blocks (polylines are not read; *manual*). The block is
named in the dialog under a steel shape: `HSS-SECTION-RAM` (David
Pruscino's 6 x 6 square) goes under **Rectangular HS** (*seen*).

Prepare the file before importing (`scripts/dxf_prepare.py` does all three):

- **Purge unused blocks.** The dialog's block lists hold only the first 100
  block definitions in file order (*seen* 2026-10-16; that is what the
  "Over a 100 Blocks in DXF file." notice means), and they are pick-lists,
  no typing. The QCAD-saved Revit export carried about 980 definitions with
  the column block past the 460th, so Rectangular HS offered nothing useful;
  picking a long Revit name by accident gives "Enter no more than 24
  characters". With the unused blocks deleted (ezdxf 1.4.2 has no
  `purge()`: `delete_block(name, safe=True)` on each block with no INSERT)
  the file had 24 and the column block was 8th.
- **One insert per column.** 2612_08 had 147 inserts on 103 points, 44
  points with two identical inserts; the import makes a column for each.
- **Near 0,0.** The manual refuses coordinates "excessively large" (2,000 ft
  off); 2612_08 sat 1,190 ft, 621 ft off in Revit shared coordinates. The
  script moves the lower-left corner to whole feet from the origin.

## Order of work (*seen* end to end on 2612_08, 2026-10-16)

1. **New model.** RAM Manager `File > New`. The model lives in the job's
   `03_RAM Structural` folder; Manager writes a `.usr` beside it while open.
2. **Layout type.** Modeler `Layout > Type > Select`: name in Floor Type ID,
   Add, Select; the plan goes empty and the title bar names the type. The
   import goes only into an **empty** layout type (`Import from DXF...` is
   greyed otherwise). To redo an import: Select, pick the type, Delete
   ("All data for Floor Type ... will be destroyed!", OK; only while no
   story uses it), Add the same name, Select.
3. **Material Steel.** The import's column blocks are steel shapes and the
   columns come in steel; the WALL placeholders come in as steel beams.
4. **Import.** `Layout > Type > Import from DXF`, pick the file, OK the
   blocks notice if it shows. Slab Edges `EDGE`, Columns `COL`, Beams `WALL`,
   all others `*None`; Rectangular HS `HSS-SECTION-RAM`, Round HS `*None`
   (defaults to `*As Circle Entity`), Grid Label Symbol `*None` (defaults to
   `*As Text Entity`), Cantilever `*None`; Save Settings; OK. The dialog
   remembers the layer names, not a block that is missing from its list.
   Columns land at every insert, turned ones at their insert angle.
5. **Columns of another building.** 2612_08 has an expansion joint; Ryan:
   ignore the east wing. Material Steel, `Layout > Columns > Delete`, Fence
   (a drag) around them. The east `EDGE` line was already the joint line.
6. **Walls on the placeholder beams.** See Walls below.
7. **Slab edge clean-up.** See Slab edge below. Keep edges straight across
   shafts and stairs and model those as Slab Openings (Ryan: an edge that
   detours round a shaft cuts the walls out of the diaphragm).
8. **Deck, before any DataCheck is trusted.** `PropTable > Decking`,
   Concrete Slab System tab: label, Concrete Slab Thickness, f'c, Add, OK
   (2612_08: `SLAB 9`, 9 in, 4 ksi, defaults otherwise). `Layout > Slab >
   Deck Assign`: Two-Way, Concrete, the property, Whole Floor. Changing the
   thickness later: PropTable > Decking, select the row, edit, Change; the
   assignment follows the property.
9. **Columns concrete and sized.** Material Concrete, `Layout > Columns >
   Change Material` ("Change Concrete Column Material Mode": f'c, unit
   weights, fy), Fence the whole plan. `PropTable > Column Sections`: add
   `14X24` (H 24, B 14). `Layout > Columns > Assign Size`, pick it, Fence.
   The columns keep their insert angle (`Layout > Columns > Show` gives
   "Column orientation angle (measured from Global-X)").
10. **Stories.** `Story...`: the Generate radio shows a Level ... To range.
    Level 1 To 10, floor type, Flr to Flr Height, Style `1`, Prefix
    `Level `, Add, OK (2612_08: 10 stories at 10.5 ft). 3D View, Elevation
    Mode and Find stay greyed until a story uses the layout type. 3D View
    opens as its own process, `RAMContainer.exe`.
11. **DataCheck.** `Integrity > DataCheck`, Integrated, OK. The report opens
    in a Preview window (Close, top right), then a Data Check Status box
    (Close). "No Errors or Warnings Found" is the finish line.
12. **Save.** Modeler `File > Save` (Ctrl+S) writes only the working copy in
    `C:\ProgramData\Bentley\Engineering\RAM Structural System\Working\`.
    The `.rss` in the job folder is rewritten by RAM Manager when Modeler
    exits (`File > Exit`). Check the `.rss` time stamp, or read the archive.
    Manager keeps the previous save beside it as `.backup`.

## Walls from the WALL layer (*seen* 2026-10-16)

The 20 wall lines came in as steel beams whose ends are SnapTo points.

- **A wall cannot sit on a beam and a beam cannot be laid on a wall.**
  Refused four ways: wall drawn over a placeholder beam and beam drawn over
  a wall ("Unable to Add this Wall/Beam. Span crosses another member at
  (x, y)"); wall drawn over a beam added first (same message); `Layout >
  Beams > Add Off-Grid > Parallel-To-Beam` at zero offset from a wall ("No
  supporting member found for left end").
- What worked: `Layout > Grids > Construction Grids`, **Two Points**, click
  the two beam ends of every wall line (collinear box sides need one line);
  **Point-Angle**, Dist 0, Angle 90, click each end of a wall that stands
  alone, so it has an intersection. Then Material Steel, `Layout > Beams >
  Delete`, Fence the plan (only beams of the current material go).
  Material Concrete, `Layout > Walls > Add On-Grid` (Lateral, Cast-in-place,
  Normal Weight, Thickness, f'c), Single, click intersection to
  intersection. `Construction Grids > Delete - All` after. `Options > Set
  Snap Points` with Grids on. `Layout > Walls > Show` confirms each wall.
- Infinite construction grids make stray intersections; one sat 0.13 ft
  from a wall end. Hover a pixel off and read the status bar, or delete that
  grid first.
- A T between walls needs the flange wall split at the stem (*manual*
  3.13); the 2612_08 double shaft already was.
- Untried: Keyboard Mode Coordinate Entry in Add Wall (*manual*: "several
  commands"; *seen* in Slab Edge Add) would type the DXF end points
  directly and skip the beams and grids.

## Slab edge (*seen* 2026-10-16)

The DXF edge drawn for a view is not a slab outline. On 2612_08 it carried
both paths at every balcony and recess (the chord and the bump), stubs that
stopped an inch or two short of a vertex, and one piece that overshot a
corner.

- `Layout > Slab > Slab Edge`: Slab Overhang (in) defaults to 12; use 0 for
  free-form edges. Delete - Single: click on the segment. Delete - Fence:
  only segments wholly inside the fence go.
- Move: pick the segment, then the end to move (it snaps to that segment's
  own ends), then the new location (any snap point).
- Snap points on slab edges are each segment's **start** vertex only.
- Add: two clicks per segment. The **Keyboard Mode Coordinate Entry** panel
  (bottom right in Add mode) takes X, Y, Absolute, Add; two typed Adds make
  one segment and "Previous Point" shows the last vertex. A click and a
  typed Add do not pair. Type the DXF coordinates to four decimals: a typed
  end that met an existing vertex at rounding was flagged "Slab edges
  intersect"; stopping 0.0002 ft short of it passed.
- Edit > Undo undoes the last slab edge delete.

## DataCheck messages on 2612_08 and what fixed them

| Message | Cause | Fix |
|---|---|---|
| Slab edges intersect / Break or Extraneous Slab Edge | duplicate paths, near-miss stubs and an overshoot from the DXF edge | delete the inner path; Move the end onto the vertex; add the closing piece |
| Wall #n has free-standing end ... under decking | a single wall ending in open slab, checked **before a deck is assigned** | assign the two-way concrete slab deck; no stub beams needed |
| Steel Column #n lies under two-way deck | the imported columns are still steel | Change Material to concrete |
| Concrete Beam #n has no member size (warning) | stub beams tried for the wall ends | gone with the beams |

The free-standing wall end error looked like a modeling problem and cost an
hour of beam work. Mt Pleasant Building 2 never showed it because its
two-way slab deck was already on. Look at a working office model before
inventing a workaround.

## Driving Modeler by computer use (*seen*)

- Modeler runs as `RamModeler.exe`, apart from `RamManager.exe`; grant it
  after it starts. The 3D viewer is `RAMContainer.exe`.
- The screen lags clicks by 2 to 4 s on the office RDP session. Menus open
  reliably with Alt+L (Layout), Alt+F (File).
- The status bar shows the snapped X, Y while hovering; read it before every
  click. It can lag one hover behind; move twice and wait.
- Numeric boxes ignore Ctrl+A and triple-click; typing inserts at the caret
  ("12" into "10.00" made 10.1200). Clear with End and Backspace, then zoom
  on the box before going on.
- D recalls the current mode's dialog; Cancel in it ends the command. Esc
  ends Show and Zoom modes.
- `View > Zoom > Full` refits to what is left after deletions, so screen
  positions change. `View > Zoom > Fence` on a 16 px box gives about 85 px
  per foot.
- Construction Grids Point-Angle clicks in a zoomed view took the previous
  or a nearby snap point several times; Two Points and Parallel-To-Beam/Wall
  behaved.
- After the first click of a new kind of action, screenshot before batching
  more: a warning box swallows the rest of the batch.

## A reference model: Mt Pleasant Building 2

`S:\0_2026 Projects\2636_Blackbird Group Architects\2636_02_(Mt Pleasant
Active Adult - Building 2)\Calculations\03_RAM Structural\2636_02_gravity_slab_merged_10-7-26.rss`,
read from the archive (`RSS_ARCHIVE_FORMAT.md`): one layout type, 72
columns, 190 walls, 0 beams; 379 of 380 wall ends meet another wall, none
stands alone; one two-way concrete slab deck.

## 2612_08 input as received (26-10-13)

`...\03_RAM Structural\DXF Inputs\26-10-13\FloorPlan-10TH(SL1)FLOORPLAN(ELEV179-5').dxf`
(inches, Revit export reworked by David Pruscino). `COL` 147 inserts on 103
points, 60 turned to odd angles along the curved wing; `EDGE` 106 lines, the
curved west wing and the middle box only, 47 columns of the east wing with no
edge, 14 open ends, 14 T-junctions; `WALL` 20 lines (two shaft boxes, a
double box, five single lines); nothing else. The prepared file is
`FloorPlan-10TH(SL1)_RAM.dxf` beside it (103 columns, moved to 0..507 ft by
0..177 ft), touched up by the engineer in QCAD; `..._RAM_purged.dxf` is that
file with the unused blocks deleted (24 blocks, 102 EDGE lines), and is the
one imported on 10-16. `scripts/dxf_inventory.py` reports all of this.

State saved 2026-10-16 16:05 in `2612_08 - 1300 Manhattan Residential
Wing.rss`: layout `10TH SL1` with 63 concrete 14X24 columns at their DXF
angles, 20 walls 12 in 4 ksi Lateral, a 9 in two-way slab, the edge cleaned
and the 10th level transition cut back to the column row at y 120.76 ft,
stories Level 1 to 10 at 10.5 ft, DataCheck clean.

## Open

- Whether the import honours Concrete material mode at import time (both
  imports ran in Steel).
- Which side of a turned 14 x 24 is the long one: the block was square, so
  the angle is right but the long side must be checked against the BOD.
  Some may need 90 degrees more (Ryan).
- The closed `EDGE` loop around the box C shaft is a second edge loop; it
  should be a Slab Opening.
- Walls by Keyboard Mode Coordinate Entry, untried.
