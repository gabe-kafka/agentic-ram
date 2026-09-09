# RAM Frame notes

Verified GUI lessons for Bentley RAM Frame. Keep job kips, stories, and
coordinates in the matching `eng-agent` project. Do not apply these to RAM
Concept.

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
