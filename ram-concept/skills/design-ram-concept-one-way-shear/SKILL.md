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

## Not built

- The screening copy itself (Save As, full width, calc) and the PDF print.
- Averaging the legs to a few counts (the written process, step 6b).
- The stud rail columns: bar `SSR one-way` as the column strip shear bar,
  and the office `SSR for One-way` spreadsheet.
- Middle strips along long walls.
- Writing the agent's proposed boxes into the PDF.

## Bundled scripts

- `scripts/read_markup.py` (needs pymupdf), `scripts/markup_plan.py`,
  `scripts/shear_regions.py` (plan needs matplotlib),
  `scripts/place_stirrups.py`, `scripts/zones_check.py`,
  `scripts/stirrup_collisions.py`, `scripts/full-width-strips.ps1`.
- Tests: `ram-concept/tests/test_one_way_shear.py` (joining regions into
  zones, the page fit).
