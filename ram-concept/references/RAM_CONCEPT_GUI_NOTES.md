# RAM Concept GUI notes

Verified live-GUI lessons. Keep job thicknesses, mixes, and model paths in the
matching `eng-agent` project. Direct mutation of an existing design model is
not a proven repository skill; guide the user and preserve a checkpoint.

## Checkpoint first

Work from a separately named `.cpt`. `File > Save As` before edits.

`Process > Calc All` and `Generate Mesh` commit pending edits. Undo will not
restore the pre-command state. Do not calc until the setup review is done.

Do not remesh merely to inspect the existing mesh
(`Layers > Element > Standard Plan`).

## Criteria

- `Criteria > Calc Options`, `Materials`, `Loadings`, `Load Combos`: review
  before changing.
- Do not use `Criteria > Rebuild Load Combos` without reviewer direction. It
  can replace project-specific combinations.
- Concept includes slab-mesh self-weight. Do not also draw a duplicate
  self-weight area load.

## Plans

- Mesh input: `Layers > Mesh Input > Standard Plan`
- Slab properties: select area → `Edit > Selection Properties`
- Loads: `Layers > Loadings > <name> > All Loads Plan`
- Design strips: latitude and longitude span plans
- Punching checks: `Layers > Design Strips > Punching Checks Plan`
- To trace imported area-load outlines without reimporting from Modeler:
  `View > Visible Objects > Static Loadings` on Mesh Input

### Rebar review plans (office convention)

Four custom plans under `Layers > Reinforcement`, one per face and direction.
Name them by face, then direction:

| Plan | Reinforcement layer visible objects |
|---|---|
| `Top Long` | Longitude User + Program Concentrated Bars, Top Face |
| `Top Lat` | Latitude User + Program Concentrated Bars, Top Face |
| `Bot Long` | Longitude User + Program Concentrated Bars, Bottom Face |
| `Bot Lat` | Latitude User + Program Concentrated Bars, Bottom Face |

Every plan also shows Concentrated Bar Descriptions and Extents, and on the
Element layer: walls and columns above/below (outline only), slab elements,
and slab element edges.

`Layers > New Plan...` (name without "Plan", layer Reinforcement) opens
`Visible Objects` for the new plan. Click `Show Nothing on Any Layer`, then:

- `Reinf.` tab, concentrated group (left column): Lat/Long Concentrated User
  and Program Reinf., Top or Bottom Face, Description, Extent. The transverse
  group below repeats the Description/Extent labels; do not tick those.
- `Element` tab: Wall Elements Above/Below + their Outline Only, Column
  Elements Above/Below, Slab Elements + its Outline Only (stored as
  `SlabElementEdges`).

Check the face filter, not the name. A plan named `Top Long` that filters
`BottomFaceConcentratedBars` shows bottom bars. Callouts ending in `B` are
bottom bars. Typical gravity slab: top bars #9 over supports, bottom #7.
Rename a plan with `Layers > Rename...`; it acts on the active plan window, not
the tree selection. Double-click the plan in the report tree first, and confirm
the dialog's `Old name` before typing. Create plans with `Layers > New Plan...`.
The published API cannot create or rename plans. The report tree is not
exposed to UI Automation, so automation must click it by screen position.
Saved checkpoints store each plan's filter in `PlanData` /
`FilterKeyShowFilter.FilterString`; `ConcentratedRebar.BarFace` is 1 = top,
2 = bottom.

## Line loads

The Warnings list uses one-based load numbers. Saved checkpoint indices are
zero-based. A "line load is not on the slab" warning is often a slab-edge or
stale-mesh problem, not a reason to delete a transfer load.

## Thickness changes

Separate slab-property regions at terraces, balconies, and step-downs. Put
reinforcement in matching regions so cover follows the correct elevation.
Confirm generated stud rails do not run through a modeled step.

## Two-way shear: stud rails (office path)

From a senior reviewer's walkthrough, 2026-10-02. Not yet run end to end by
this workspace; guide it by hand and checkpoint first.

Settings before reading results:

- Punching checks: search radius 8 ft to start, `Design SSR if necessary` on.
- SSR size 3/4 in. `Criteria > Materials > SSR Systems > Stud Spacing` on
  that system: `Auto Calc`, not the default `Code Max`. `Code Max` holds the
  widest stud spacing and piles on rails.

The generated rails are a minimum design with no MEP penetrations in it.
Penetrations are not located reliably before construction, so assume one:

1. Add a 6 in x 6 in slab opening at the face of every column that has stud
   rails. Use the long face and shift it off the centre of the face; an
   opening at mid-face blocks the rail the program may need there.
2. Calc. The program removes the critical perimeter inside the opening's
   projection on its own.
3. Review every rail set for failures, calc errors, and rails from
   neighbouring columns that overlap. Each column is checked alone, so
   overlapping rails are not analysed together; avoid them.
4. Where rails stop generating, raise that check's search radius. About 10
   to 12 ft is the most; a 20 ft rail is not acceptable.
5. Still failing: overlay the architectural plan above. Bathrooms and
   washer/dryers near the column mean the opening stays. With nothing
   nearby, move the opening back a foot or two at a time.
6. Nothing works: a beam is the next option.

Then group the rails into a short schedule in the office stud rail
spreadsheet: number of rails, studs per rail, typical stud spacing; rail
length follows. Group by rail length in steps of about 1 to 1.5 ft, then by
stud spacing (light about 5 to 6 in, heavy about 3 to 4 in; the same length
at two spacings stays two types). Concept can export the stud rail table to
a text file; rows come out unordered. Last, select each stud rail set in
the model, change it to `User`, and set its properties to its schedule type.
Exterior columns need configurations for four, three and two sides.

`scripts/inspect-punching-checks.py` reads the saved checks, search radii
and generated rail geometry from a checkpoint without opening Concept.

## Mat / lateral foundation design (office path)

RAM Foundation is weak for wall foundations. Design lateral/wall mats in
Concept on a separate mat level imported from Modeler mats.

1. Modeler: crude mats under walls/columns that belong in the Concept design.
2. Concept import (lowest level, mat type): slab/mat areas, columns above,
   walls above, direct transfer lateral loads, and usually RSS cracked
   factors. Reimport column/wall geometry only if Modeler changed after the
   last Concept import.
3. `Criteria > Loadings`: delete seismic **overstrength** cases before design;
   they inflate footings. Keep wind + standard EQ.
4. Delete the Modeler mat outlines in Mesh Input. Redraw:
   - walls → beams as strip footings (start ~SF 3.0; Mesh as slab off)
   - columns / hot corners → Drop Cap under Slab Area (start ~F 6.0)
5. Place an area spring under the whole foundation (soil). Subgrade modulus
   from the geo report; set small R/S side constants so the mat does not
   slide. Hide the spring after placing.
6. Rule Set Designs → Soil Bearing Design → Max Soil Bearing Pressure plan.
   Use a finer mesh (~2 ft). Size until bearing is at/under the project
   allowable; tiny corner red chips may be OK, large over-bearing zones are
   not.
7. Export Mesh Input drawing for docs, or screenshot-markup the foundation
   plan.

Keep job soil values, SF/F schedule names, and model paths in `eng-agent`.

## Live API

A Start-menu or RAM Manager Concept window has no API. Attach only after
`-apiServer` / `-apiServerWithGui`. See
`../skills/attach-ram-concept-api/SKILL.md`.
