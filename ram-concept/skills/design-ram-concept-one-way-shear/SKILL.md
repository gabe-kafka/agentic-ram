---
name: design-ram-concept-one-way-shear
description: Design a RAM Concept two-way slab for one-way shear by the office two-model method - a full-width screening copy, the engineer's marked-up PDF read back to him as an SVG before any bar is drawn, then user stirrup zones in the real model (#4 open stirrups, 6 in along the span, one leg per mat bar, from the support face) and a check that the program adds nothing more. Use when a user asks for one-way shear, slab shear reinforcement, stirrups in the slab, the full width model, the shear reinforcement plan, or hands over a one-way shear markup PDF.
---

# One-Way Shear Design with a PDF Markup (RAM Concept)

The office method is in `../../references/RAM_CONCEPT_GUI_NOTES.md`,
"One-way shear in a two-way slab". Read it first; this skill automates the
reading of the markup and the placing of the stirrups. Run end to end on one
model (2636, 2026-10-06): 36 user stirrup zones, 35 clean after the calc.

It comes after the bending bars (one-way concrete shear capacity depends on
the flexural steel) and after two-way punching passes (stud rail columns are
set aside here).

```text
screening copy by hand: Save As "<model> - Full Width", every slab strip to Full Width, Calc All
  -> print the Shear Reinforcement Plan to PDF -> the engineer marks it up
  -> read_markup.py -> markup_plan.py -> SVG back to the engineer
     -> he corrects the PDF or confirms; repeat until the reading is his intent
  -> place_stirrups.py --boxes on the REAL model (API session on a copy) -> Calc All
  -> zones_check.py -> sync into the production model
  -> by hand: average the legs, the stud rail columns through the rails
```

The full-width copy answers one question only: **where**. How much (rows,
legs, pass) is decided in the main model on its column and middle strips.
Settled with the engineer on 2026-10-07 after a day spent the other way.

## The back and forth

Nothing is drawn in Concept until the engineer has seen the SVG and agreed.
He asked for exactly that on the first job.

1. `read_markup.py <marked-up.pdf> <dir>`: every annotation and a picture of
   each page.
2. `markup_plan.py <dir>/annots.json <screening.cpt> <reading.svg>
   --boxes-out boxes.json`: fits the page to the model from the red column
   marks, lists what each mark covers, and draws the reading.
3. Send the SVG. Say which required zones sit outside every box and which
   boxes hold no program zone; the script prints both lists.
4. Boxes the agent proposes go in `--extra` (dashed, labelled A, B, ...).
   The engineer adds the ones he accepts to his PDF; the PDF stays the
   record.
5. Read the PDF again after he changes it.

The markup convention (the engineer's, 2636):

| Mark | Meaning |
|---|---|
| red square the size of a column | stud rail column: set aside, checked through the rails |
| green freehand stroke | stirrups there are OK by d: nothing to place |
| magenta square | user stirrups wanted in this box |
| red check mark (polygon) | a required location |

A legend drawn with the same marks is skipped with `--ignore-left-of`.

## What is automated

| Step | Tool | How it is proved |
|---|---|---|
| Read the markup | `read_markup.py` | 2636: 77 annotations read |
| Fit it to the model, draw the reading | `markup_plan.py` | 2636: 49 of 49 column marks matched, worst 1.4 ft; boxes within 1 ft of the ones typed by hand |
| Sort the program's stirrup zones | `shear_regions.py <model.cpt> [--plan out.png]` | read-only; over-counts on a full-width copy (below) |
| Place user stirrup zones | `place_stirrups.py <saved.cpt> <out.cpt> --boxes boxes.json [--box X0 X1 Y0 Y1] [--around-beam-columns 10] [--replace] [--dry]` | 2636: 36 zones through the API, calc, checked. `--boxes` has only been run with `--dry` |
| After the calc | `zones_check.py <calculated.cpt>` | 2636: 35 of 36 clean, one leftover found |
| Before a calc on changed strips | `stirrup_collisions.py <saved.cpt>` | 2636: found the same two sections Concept stopped on; none in two clean files |
| All strips to full width | `full-width-strips.ps1` | not proven end to end; the engineer did it by hand faster |

`place_stirrups.py` needs an API session with the real model open, saved as
`<saved.cpt>` before any user stirrups are in it. Always `--dry` first and
compare the list with the SVG.

## The design rule

- Bar #4, open stirrups, 6 in on centre along the span.
- **One leg per mat bar across the column strip** (senior reviewer,
  2026-10-06): with a 12 in mat, legs = the strip width in feet.
- Spacing along the span no more than d/2, or the program does not count
  the stirrups: 6 in in a 16 in slab, 4 in in a 12 in slab.
- One user region per zone, **from the support face to the far end of the
  zone**.
- The engineer's marked box is placed as marked. The d rule is not applied
  inside it.
- Beam strips are skipped: a beam's own stirrups are beam design.

## Rules learned the hard way

- **The d rule screens a location in or out. It never trims one that is
  in.** Concept draws one zone as a short region at the face plus longer
  ones beyond. Join them first (`shear_regions.chains`), judge the zone by
  where it ends, and place from the face. Applied region by region, the rule
  left eight zones starting 1.5 to 2 ft off the support.
- The program's answer is an area: two legs at a spacing that shrinks, over
  the whole strip. Equivalent spacing at n legs = program spacing x n / 2.
  A wild-looking `2L @ 1.2 in` is about 10 legs at 6 in.
- On a full-width copy the program draws its regions at the middle of the
  wide strip, off the column lines, so `shear_regions.py` finds no support
  and calls them required. `markup_plan.py` draws those as not sorted. The
  engineer's markup decides on the screening copy; trust the sorter on the
  real model only.
- Never set the real model's strips to full width.
- Placing twice doubles the regions. Plan from the model state before any
  user stirrups, and use `--replace`.
- A user zone is good when the program draws nothing more on its line.
  A leftover right at the column face next to a full zone is a judgement
  call for the engineer, not a reason to add legs everywhere.
- **One design cross section holds one user stirrup region.** A second one
  stops the calc: `<strip> contains multiple user transverse reinforcement
  regions`. The zones belong to the strips they were placed on. When the
  strips change (2636: the reviewer widened a column strip to 13 and 15 ft
  and two neighbouring zones landed in it), run `stirrup_collisions.py`
  before the calc and let the engineer say which zone stays.
- Over the API a stopped calc still answers SUCCESS. Proof that it finished
  is in the saved file: detailed stirrups (`IndividualTransverseBar`) are
  there. None means it stopped; the reason is in Concept's log.
- With the engineer at the PC, or a second Concept open, no real keystrokes
  or mouse clicks. The strip edit is quicker by hand than by script.

## Hand-off to drafting (the office precedent, 2636 Building 3, June 2026)

Seen on 2026-10-07 in `S:\...\2636_03_(...Building 3)\Calculations\03_RAM Structural\One-way Shear\2636_03_One-way Shear.pdf`
(the engineer's markup, 2026-06-16) and the permit set of 2026-06-19 (`Structural Dwgs\PDF\26-06-19 (Permit)`).

- **The markup PDF is the hand-off.** On the full-width Shear Reinforcement Plan: red column-size squares = SSR
  columns (legend "= SSR REINF"), green strokes = "OK DUE TO d DISTANCE", a red check at each required location,
  and beside it two text boxes: red `13FT` (the stirrup region width: the column strip) and blue `(12) 12L`
  (rows of stirrups, legs per row). Building 3 had 14 locations, widths 8 to 13 ft, 8 to 17 rows, 7 to 12 legs.
- **What the drafters drew from it:** sheet S011 `SLAB STIRRUP SCHEDULE` with one mark, `ST1  #4  6" O.C.  TYPE 1`,
  a TYPE 1 detail (shaded region, "WIDTH REF: PLAN", "LENGTH REF: PLAN", "U-STIRRUP TO MATCH SPACING OF MAT
  REINFORCEMENT", spacing S), and five notes (single-leg stirrups allowed in lieu of U; single legs where regions
  overlap; at an opening the leg count is still required each side plus one extra row each side; at a drop cap the
  region narrows to the cap). On the framing plans (S102A, S102B) each region is a shaded rectangle tagged `ST1`
  with its width and length dimensioned, e.g. `11'-0"` x `7'-0"` at the column face. The typical placement detail is
  on S511 (stirrups hooked around top and bottom bars, full slab depth, "#5 bars along the length of the stirrup
  region" if hook bars are needed).
- So for a new job the drafter needs, per region: the column strip width, the length (rows x spacing), and the
  mark; the leg count is implied by the mat spacing. `zones_svg.py` in the job folder lists exactly that per zone.

- **Building 2 hand-off (2026-10-08):** the engineer's own Bluebeam set on the plan sheets (S101A/B/C), one per zone: orange
  rectangle at 50%, `ST1` text box, two red length measurements. Width = the column strip width in the main model
  rounded **down** to the foot (the drawn width at the 12 in mat spacing is the leg count), length = the zone length
  rounded **up**. Legs in the model are brought to the strip width first. Tool in the job folder:
  `eng-agent/projects/2636-mt-pleasant-building-2/ram-concept/one-way-shear/tag_st1_plan.py` (sheets fitted from the SSR
  workbook's plan column numbers at 9 pt/ft, verified by overlaying the model's walls and columns); output beside the
  engineer's file, never over it; open in Revu for him. To be promoted into this skill.

## What 2636 Building 2 taught (2026-10-07 and 08)

The method, as the engineer finally stated it:

1. **Full width decides WHERE only.** The full-width copy is a binary screen; his markup on it fixes the
   locations and they are then locked. Nothing is sized there: Concept draws a user zone across the whole strip
   it sits in (a zone has no width of its own), so in a full-width model the zones look twice as wide and a
   trim against the full-width demand left 8 of 28 zones short in the real model.
2. **The main model (code-slab strips) decides HOW MUCH.** Each zone one region from the support face to the end
   of what the program draws on its line; a zone is good when the program draws nothing more on its line
   (`zones_check.py`); program regions elsewhere, and middle-strip regions beside a zone (`beside.py`), are
   ignored. `demand_main.py` reads each zone's demand from a baseline calc of the main model with no slab zones.
3. **The grid is 6 in along x 12 in across**: #4 at 6 in (4 in in a 12 in slab), legs = the column strip width
   in feet (one per 12 in mat bar). Building 3's TYPE 1 detail is the same grid (a U-stirrup across two adjacent
   mat bars, one leg on every bar). Re-read the leg counts after any strip change: the senior reviewer widened
   strips the evening after the legs were counted and 11 zones were under. More legs never makes a passing zone
   fail; a zone that loses legs needs the recalc.
4. **The engineer works in the S: model in the mornings.** A redesign he has not locked is not the design: on
   the second morning his own save (8 zones lengthened by hand) was the base, diffed first, and the leg fix was
   applied on top of it. Check `Working\<model>.cpt1027E` and the `.rss` member hash before anything.
5. **Hand-off to drafting** is the ST1 markup on the framing plans (S102A/B/C), not a separate document:
   `tag_st1_plan.py` with `fit_sheets.py` (see the hand-off section). Confirm the sheet set is the framing plan
   before tagging; a first pass went onto the S101 foundation sheets.

Concept and API behaviour met on the way:

- The Scripting Server's Pause blocks every call ("Concept did not answer"); it was found paused three times.
  Resume it through the window (UI Automation `Invoke` on the Resume button), never with the mouse.
- An API GUI session started with `inactivityTimeout 3600` exits after an hour without calls; `attach` then
  refuses the connection. Check the process before assuming the session is there.
- `SAVE_FILE` fails while a Python sqlite handle is open on the target file: close read handles first.
- Concept snaps a zone's far end to a whole number of spacings (7.77 ft became 8.0 at 6 in); verify with that
  tolerance, not exact endpoints.
- Two user regions in one design cross section stop the calc; `stirrup_collisions.py` before every calc.
- Before every live batch keep a copy of the saved file so a "revert the last turn" is a file swap; the revert
  on 2026-10-07 had to be re-edited zone by zone.
- Swapping the S: model more than once per decision confused everyone: show the diff, swap once, on his word.

Job-folder prototypes of the live tools (`eng-agent/.../2636-mt-pleasant-building-2/ram-concept/one-way-shear/`):
`live_add_zones.py`, `live_change_zone.py`, `live_save_calc.py`, `build_full_width_from_merged.py`,
`merge_zones_into_main.py`, `build_full_width_screening.py`; generic copies of `zones_svg.py`, `beside.py`,
`demand_main.py`, `live_fix_zones.py`, `live_set_rows.py`, `fit_sheets.py`, `tag_st1_plan.py` are in `scripts/`.

## Lessons from 2636 Building 2, 2026-10-07 and 08

- **Full width is a binary WHERE check.** The engineer's words: "we use the
  full slab width model only as a binary check to determine where we will
  add shear one way reinf." Sizing the zones against the full-width demand
  left 8 of 28 short in the main model. Size in the main model, from a
  baseline calc with no slab zones (`demand_main.py` reads it per zone).
- **A zone has no width.** Concept draws a stirrup region across the whole
  strip it sits in; in a full-width model every zone looks twice as wide
  (legs read 24 in apart). Drawing only; the check is legs x bar area per row.
- **The grid is 6 in along by 12 in across**, and it lives in two inputs:
  spacing 6 in, legs = column strip width in feet (one per 12 in mat bar).
  Building 3's TYPE 1 detail is the same thing drawn: U-stirrups spanning
  adjacent mat bars, so one leg on every bar; the plan region's width at the
  mat spacing *is* the leg count, nothing else calls it out.
- **When the strips change, recount the legs.** The reviewer widened strips
  after the legs were counted; 11 of 28 zones were then under the mat rule
  (6 legs in an 11 ft strip). The drawn width is `FirstStirrupEnd0/1` in the
  calculated file; legs = that width in feet. More legs never un-passes a
  zone; fewer (one zone, 7 to 5) needs the recalc.
- **The engineer's save on S: is the design, not the agent's working copy.**
  He opened the merged model from RAM Manager the next morning and lengthened
  five zones by hand; the agent's live redesign of the previous evening had
  never been locked. Compare the two before doing anything (`gabe-main-*`
  snapshots), and tag the drawings from his file.
- Program stirrups beside a zone on the far side of its support belong to the
  next span. Running the zone through the support covers them, but the
  engineer reverted that the same hour: "dont add new zones ... add more rows
  or legs as makes sense", then "revert". Report them; let him lengthen.
- Two user zones in one full-width cross section stop the calc; 3 of 36 did.
  Only the real model's strips are narrow enough to hold them all.
- The API session's inactivity timeout (3600 s) closes it silently; a paused
  Scripting Server looks the same (no answer). Resume it through the window
  (UI Automation Invoke on the Resume button), never with the mouse. An open
  sqlite handle on the save target makes `SAVE_FILE` fail. Concept snaps a
  zone's far end to a whole number of spacings; compare with that tolerance.
- A Full Width screening copy can be built without the GUI: write
  `SpanSegment.ColumnStripWidthCalc = 'full'` into a copy of the saved file
  and Calc All regenerates the strips (329 centre strips, mean 18 ft).
- Keep zone numbers stable across edits (`plans/zone-ids.json`, re-keyed by
  line and overlap); he refers to zones by number across the day.
- Lengths were not standardized on Building 3 (8 to 17 rows, each region its
  own); the engineer kept his own 4.5 to 8.5 ft lengths here too.

## Not built

- The screening copy itself (Save As, full width, calc) and the PDF print.
- Averaging the legs to a few counts (the written process, step 6b).
- The stud rail columns: bar `SSR one-way` as the column strip shear bar,
  and the office `SSR for One-way` spreadsheet.
- Middle strips along long walls.
- Writing the agent's proposed boxes into the PDF.

## Bundled scripts

- `scripts/read_markup.py` (needs pymupdf), `scripts/markup_plan.py`, `scripts/zones_svg.py`, `scripts/beside.py`,
  `scripts/demand_main.py`, `scripts/live_fix_zones.py`, `scripts/live_set_rows.py`, `scripts/fit_sheets.py`,
  `scripts/tag_st1_plan.py` (needs openpyxl for the fit),
  `scripts/shear_regions.py` (plan needs matplotlib),
  `scripts/place_stirrups.py`, `scripts/zones_check.py`,
  `scripts/stirrup_collisions.py`, `scripts/full-width-strips.ps1`.
- Tests: `ram-concept/tests/test_one_way_shear.py` (joining regions into
  zones, the page fit).
