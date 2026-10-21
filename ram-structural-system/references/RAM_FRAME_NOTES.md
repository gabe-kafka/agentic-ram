# RAM Frame notes

Verified GUI lessons for Bentley RAM Frame. Keep job kips, stories, and
coordinates in the matching `eng-agent` project. Do not apply these to RAM
Concept.

Code background for a full lateral run (drift, torsion, P-delta, wind cases,
Drift Control, concrete wall crack factors) is in
`RAM_FRAME_LATERAL_VIDEO_NOTES.md`, from two Bentley webinars plus the manual.

## Wall layout is not in Frame

A Frame warning of the form `No Lateral Member found for Diaphragm N on Story X`
means that diaphragm has mass but no lateral walls.

Close Frame. In RAM Modeler use `Layout > Walls > Change` and set the concrete
walls to Lateral. Gravity columns and footings do not count. Reopen Frame only
after that change.

## Simplified user-defined story forces

Until upper-level shear-wall locations exist, do not run program seismic or
wind. Use spreadsheet ELF base shear as user-defined story forces:

`Loads > Load Cases` → Seismic → User Defined Story Forces

- Label `EQX` and `EQY`.
- Put the story force in **Force (kips)**. **Rigid Diaph. X** is a length, not
  kips.
- `EQX` direction = `0°`. `EQY` direction = `90°`. The two cases must differ by
  `90°`. The same angle applies the same load twice.
- Apply the force at the podium/first-floor story that receives the transfer.

After both cases exist, that is the Frame setup for this pass. Skip omega
cases, generated load combinations, frame-number assignment, and reaction
envelopes until a later, sparser-wall review.

## Criteria

Leave general criteria at defaults unless a later check needs them.

- Diaphragm: semi-rigid is the usual office default and the program default.
  Rigid is acceptable when a first-pass story-force run should skip shell
  meshing.
- Ground level: leave default unless there is a basement and the analysis base
  must be raised.

## Analyze dialog

Green icons mean the cases exist. **OK stays grey until cases are highlighted.**
Click **Select All**, then **OK**. Leave **Write Results to Data Extractor
database** and **Generate ADINA Input file** unchecked.

## Distorted diaphragm shells

Semi-rigid meshing may report:

`Very distorted shell element found on diaphragm at one or more levels. That
element will not be included in the analysis.`

The dropped-element list is:

`%ProgramData%\Bentley\Engineering\RAM Structural System\Reports\<model>_MeshWarningReport.log`

A few discarded sliver shells on one diaphragm is not an EQ-angle error. Click
**OK** and let the run finish. Treat it as a Modeler geometry/mesh issue only if
story shears look wrong.

## After a clean Frame run

Close Frame. Open RAM Concrete. Before wall or column design:

`Criteria > Column Forces` → Use RAM Concept Forces → all applicable floors →
green status → `Process > Analyze`

Do not design walls until that Concrete analyze is green. Frame lateral forces
and Concept gravity forces meet in the Concrete wall module, not in Frame.

## Full ASCE 7-16 run, 2612_08 Lateral copy (*seen* 2026-10-19, RAM 26.00.00.222)

- **Check RAM Manager `Criteria > Self-Weight` before any seismic run.** On
  2612_08, Slabs/Deck was unticked under both Member Dead Loads and Story
  Masses, which leaves the slab (most of the weight) out of W. Tick both.
- RAM Frame runs inside `RAMContainer.exe` (grant that for computer use).
- `Criteria > General` on this model already had P-Delta Yes, Use Gravity
  Loads, Dead 1.2 / Live 1.6. `Criteria > Diaphragm` had every story Rigid;
  **All Semirigid**, OK. `Loads > Masses` shows story weights and the 5%
  eccentricity.
- `Loads > Load Cases`: Label, Seismic → "ASCE 7-16 Equivalent Lateral
  Force", Add. Dialog: Provisions for, Direction X/Y, Eccentricity "+ And -",
  R per direction, Risk Category, Ie, TL, Site Class, Ss/S1 or "Use:"
  SDS/SD1 (the SDS box is too narrow to show its first digit; the report
  echoes it), Ct dropdown (0.030/0.028/0.020/0.016), T options (Calculated,
  Use T, T = Ta). Wind → "ASCE 7-16", Add: Exposure, Kzt, Ke, Kd, gust
  factor, basic wind speed; 12 cases generated.
- Clicking in the Label box does not select it; typed text appends. Use End
  and Backspace.
- `Process > Analyze`, Select All, OK: about 3 minutes with semi-rigid
  meshing (10 stories, 22,563 sq ft floor).
- Reports: tick `Reports > Text File`, then a report asks for a `.csv` name
  (saved in `%ProgramData%\Bentley\Engineering\RAM Structural System\Reports`).
  The file name box ignored clipboard paste; type it key by key.
- `Loads and Applied Forces` prints SDS/SD1, SDC, Ta, Cu, T-used, Cs
  (eqs 12.8-2/3/5), k, total W, story forces per case, and the wind
  pressures with Kz, G and natural frequency.

## Drift at control points (*seen* 2026-10-20, 2612_08 Lateral, RAM 26)

- `Process > Results > Drift > At Control Points`: a grid of **10** points
  (the manual says 4). Double-click a cell, type, Enter (Tab does not commit
  the next cell). View Results.
- With `Reports > Text File` ticked, View Results asks for a CSV name; with
  Screen ticked it opens a "Preview" window (DevExpress, 21 pages here).
  Preview `Export To` (PDF icon) → PDF options OK → Save As (default name
  `Drift`) writes `%ProgramData%\...\Reports\Drift.pdf`; pymupdf reads it.
- Semi-rigid diaphragm: the report says displacements are "based on nodal
  displacements near to selected point", so control points do differ.
- The last page, TORSIONAL IRREGULARITY DATA, picks the worst pair of
  control points per story and case and prints Max/Min and Max/Ave.
- `scripts/frame_drift_compare.py` reads these PDFs, gives each run's worst
  ratio to the 1.0E and 0.6W limits and recomputes the torsion ratio per story
  from the extreme control points (it reproduced RAM's own table).
- Computer use: `open_application("Ramcontainer")` launches a **new, empty**
  RAMContainer that pops an Open `.rss` dialog. Bring RAM Frame forward from
  its taskbar button instead (File Explorer click grant).

## Per-wall outputs (*seen* 2026-10-20, 2612_08 Lateral, RAM 26)

- With every wall at Frame Number 0 (the Modeler default), `Reports > Frame
  Story Shear` offers only frame 0, and `Wall-Group Forces > All` puts all 20
  walls in one group 0: both give the building total, not a wall's share.
- `Reports > Member Force Summary` (frame 0) is the compact per-wall output:
  one block per level, a row per wall per combination with P, Mmajor and
  Vmajor. A wall's first row prints wall number and combination run together
  (`211` = wall 21, combination 1). 87 pages for 20 walls x 10 levels x 16
  combinations; Level 1 is the last 9.
- `Member Forces > All` gives each wall's thickness, length, f'c, cracking
  factors and end coordinates (`Column Line (x1,y1)-(x2,y2)`): 400 pages, the
  key to which wall number is where. `scripts/frame_member_forces.py` turns it
  into per-wall JSON.
- At Level 1 the in-plane Vmajor of the walls summed to 932 k in Y against
  the 934 k story shear: the check that the parse and the wall directions are
  right.
- `View > Members`, wall tab, `Labels > Wall Number` drew no labels in Plan
  View on this model (meshed floors on or off, text scale 1.0). The plan
  sheet overlaid RAM's wall numbers by coordinate instead.
- Each report opens its own Preview window; closing one can bring RAM
  Manager forward. Go back to RAM Frame by its taskbar button.

## Taking a wall out of the lateral system for a study (*seen* 2026-10-21, 2612_08)

- Work on copies and leave the original alone. Each step is its own file in a study folder (`S1 - no W19.rss`, `S2 - no W19 W20.rss`, ...) with its `Drift S1.pdf`, so the progression can be shown.
- RAM Manager `File > Save As` makes the next step's copy and switches to it.
  - Type the file name in chunks of 15 characters or fewer: a clipboard paste into that box came up empty.
- In Modeler, `Layout > Walls > Change Properties` changes only the ticked properties. Tick **Framing**, choose **Gravity**, then Single and click the wall.
  - Do this on every layout type that has the wall (here TYP and ROOF).
  - `Layout > Walls > Show` then reads "Member Type: Gravity" and gives the wall number, which matches the Member Force Summary numbering.
- Gravity walls keep their weight and drop out of RAM Frame. DataCheck stays clean.
- Start RAM Frame from the RAM Manager left toolbar ("Frame Design" icon). The status list entries are not launchers.
- Frame's `File > Save` (about 1 minute for 110 MB) packs the results into the .rss. Check the file time before exiting.
- Preview `Export To` needs the Preview window focused first. The first click after it opens is often swallowed.

## Wind on semirigid diaphragms is larger than the story forces (*seen* 2026-10-21, 2612_08)

- `Loads and Applied Forces` prints two wind totals per case:
  - **APPLIED STORY FORCES** is the code calculation: W1 X 417.73 k, W1 Y 898.99 k. Tedds agrees to within 2-5%.
  - **Applied Loads for Pseudo-Flexible or Semirigid Diaphragms** is what the analysis applies: 706.64 k (X) and 1,027.95 k (Y).
- `Building Story Shears` confirms the analysis uses the second set: 0.6 W1 = 423.98 k and 0.6 W2 = 616.77 k at Level 1.
- That is +69% in X and +14% in Y. The cause: with a semirigid diaphragm RAM puts wind on every slab edge that faces the wind (RAMFrame manual 7.12.3.3), so each step of a jagged perimeter adds width and the projected width is overcounted.
- EQ is unaffected: the semirigid sum = story forces = 934.45 k.
- Before quoting "RAM wind = Tedds", compare the semirigid total, not the story-force table.
- Not yet resolved: how to make RAM apply only the projected-width wind. Options are the exposure settings, a rigid copy, or a simplified slab edge.

## Drift load combinations: 1.0E and 0.6W (*seen* 2026-10-20, 2612_08)

- RAM's ELF seismic load cases are E (= Eh) with no rho: rho enters only
  through the load combination generators (manual 3.1.4). Drift uses Eh
  without rho (ASCE 7-16 12.3.4.1), so the E cases are the drift cases.
- Mode box `Load Cases` → `Load Combinations`; `Combinations > Custom
  Combinations`. Type each row as `1.0 E1` … `0.6 W12` (symbols from the
  load case list). Double-click the cell, type, Enter. The grid does not
  scroll with the wheel: select the last visible row and press Down. Check
  the row is empty before typing; a row that did not scroll got overwritten
  once. Tick all Use, click the "Click to Validate" header: all green. OK.
- `Process > Results > Drift > At Control Points` in this mode reports the
  combinations (numbered 1..n). Results matched the factored load-case drifts
  to 0.0001 in, since the analysis is linear.
