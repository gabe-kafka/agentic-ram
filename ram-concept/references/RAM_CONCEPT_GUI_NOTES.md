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

Also called designing for two-way punching, shear studs or shear rails;
Concept's name for the rails is SSR.

From a senior reviewer's walkthroughs, 2026-10-02 and 2026-10-05. Run on one
model until every punching check passed; grouping and setting rails to
`User` are not done yet. Checkpoint first.

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

Columns on beams: delete their punching checks entirely. Concept gives the
beam no credit, so those checks only ever fail.

Status comes from Concept's own tables, not from the saved file. The file
holds the checks and the generated rails; it does not hold pass or fail.

- `Layers > Design Status > Tables > Punching Check Analysis`: one row per
  section with `Max SR Status`, unreinforced and reinforced stress ratio.
- `... > Punching Check Design`: stud rail system, rail count, studs per
  rail, first and typical spacing. This is the data the schedule needs.
- Each table has an `Export...` button; the file is UTF-16 tab-separated
  text with no byte-order mark.
- `Layers > Design Status > Punching Shear Status Plan` shows the same on
  plan: green OK, red failed or in error.

Reading the status:

| Status | Meaning | Next step |
|---|---|---|
| `OK`, `OK with SSR` | passes | none |
| no row in the analysis table; plan shows `Error(s): Cutoff Sections` | rails generate but no cutoff section is found inside the search radius | raise that check's radius to 10, then 12 ft |
| `Failed`, stud rail design on, unreinforced ratio above about 2.2 | over the limit even with stud rails; no rails are generated at any radius | move the assumed opening back, or a beam |
| `Failed`, stud rail design off | usually a column on a beam | delete the check |

A column that has lost its rails is not the same as a check in cutoff
error. On the first run here the radius was raised on four columns that had
no rails; they were failing on stress and the 15 real cutoff errors were
missed until the table was exported.

What the finished run showed (one model, 16 in transfer slab, 24 x 16 in
columns):

- A 10 ft radius cleared 15 of 16 cutoff errors. None needed 12 ft.
- The stress ceiling with stud rails sat at about 2.2 times the
  unreinforced capacity: a check at 2.14 passed, checks at 2.23 to 2.33
  failed.
- All four stress failures had rails before the assumed opening went in.
  Moving the opening 1 ft straight back from the face dropped the ratio by
  about 0.15 and all four passed. The same move cleared the one cutoff
  error that 12 ft did not, beside a stair opening.
- Moving an opening changes what the design assumes about penetrations at
  that column. Try it in a separately named file; it goes in the working
  model when the engineer accepts it.
- The result tables go stale with the model. Export again after any change
  to the mesh, the openings, the checks or a radius.
- An opening touching the face adds a rail on that face, at mid-face beside
  the opening: all 35 two-rails-per-face columns went from 8 rails to 9.
  It is not load: a column at ratio 1.20 with studs at 9.25 in got it, and
  columns at 2.18 with the opening 1 ft back did not. Concept's help
  (`Punching Shear Design Notes > Step 5` and `SSR Maximum Transverse
  Spacing Checks`) says initial rails are placed to meet the 2d transverse
  spacing at the face and that an opening makes a dead sector from the
  column centre; the method is called proprietary.
- It is contact with the face that triggers the extra rail. Moving the 46
  openings 1 in off the face (engineer's instruction, 2026-10-06) took all
  35 columns back to 8 rails, two on that face. A first guess that the dead
  sector swallows the corner rail was wrong: the sector is nearly the same
  at 1 in. The opening is an assumption, so a 1 in gap costs nothing and
  avoids a lopsided 3-and-2 rail set.
- Fewer rails run longer: after that move 7 checks that had passed at an
  8 ft radius went into cutoff-section error. Expect to raise their radius
  to 10 ft again.
- With a second Concept open (one launched from RAM Manager), GUI scripts
  must be pointed at the API session's process, and real keystrokes
  (`SendKeys`) and mouse clicks collide with the engineer's own typing.
  While the engineer is at the PC, drive Concept with posted window
  messages instead: a posted click on `Export...`, `WM_CHAR` into the
  dialog's file name box, `BM_CLICK` on Save.

More from the reviewer:

- The search radius is only an outer limit on rail length. Overlapping
  radius circles are not a problem by themselves.
- A rail set split three and two is a design stopped part-way by a cutoff
  error; it evens out once the error clears.
- A cutoff error beside a stair or shaft is often geometry: a slab edge at
  or past the wall centreline leaves a sliver. In Mesh Input make the
  opening flush with the interior face of the wall. The leftmost snap icon
  adds nodes at intersections.
- A column close to a wall may not really be governed by punching, or the
  assumed penetration is not realistic there.
- `Process > Calc Partial` is `Calc All` with options, including skipping
  the warning pop-ups; quicker when only punching changed.
- A 2 ft mesh helps some conditions and roughly doubles the element count.
- After import from Modeler, review Mesh Input: openings and exterior slab
  edges.

`scripts/inspect-punching-checks.py` reads the saved checks, search radii
and generated rail geometry from a checkpoint without opening Concept.
Draft tools for the openings, radii and status are in
`skills/design-ram-concept-stud-rails`.

## Beam reinforcement (office path)

From the office concrete quick reference (ACI 318-14 based; tables 3.6 and
3.8), as walked through by a senior reviewer on 2026-10-05. Not yet applied
by any tool here.

| Beam width (in) | 12 | 14 | 16 | 18 | 20 | 22 | 24 | 26 | 28 | 30 | 36 | 42 | 48 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Minimum bars in one layer | 2 | 2 | 3 | 3 | 3 | 3 | 3 | 4 | 4 | 4 | 5 | 5 | 6 |
| Maximum #6 in one layer | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 14 | 17 | 20 | 23 |
| Maximum #7 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 15 | 18 | 21 |
| Maximum #8 | 3 | 4 | 5 | 6 | 7 | 7 | 8 | 9 | 10 | 11 | 14 | 16 | 19 |
| Maximum #9 | 3 | 4 | 4 | 5 | 6 | 7 | 8 | 8 | 9 | 10 | 12 | 15 | 17 |
| Maximum #10 | 2 | 3 | 4 | 5 | 5 | 6 | 7 | 7 | 8 | 9 | 11 | 13 | 15 |
| Maximum #11 | 2 | 3 | 3 | 4 | 5 | 5 | 6 | 7 | 7 | 8 | 10 | 11 | 13 |

The maximums assume 1.5 in clear cover to the stirrup, 3/4 in aggregate, and
#4 stirrups for #7 bars and larger.

- **Top bars:** draw the minimum number for the beam width over the full
  beam length, even where the design needs none; they carry the stirrups.
  Use #9, or the bottom bar size, or #7 where the top is light.
- **Bottom bars:** never more than the single-layer maximum. A program
  result such as 15#7 in a 16 or 20 in beam means go up to #9, start with
  the single-layer maximum, and add a second layer if needed. Extend the
  bars to the ends of the beam and set both ends `Anchored`.
- **Elevation:** set beam bars to `Bottom Cover` = 2 in, not `Absolute`.
  It reads directly and makes a second layer simple.
- **Stirrups:** #4 at 3 in on centre over the full length to start;
  normally split into end, middle and end zones.

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
