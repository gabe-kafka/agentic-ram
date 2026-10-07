---
name: design-ram-concept-stud-rails
description: Design a RAM Concept slab for two-way punching shear with stud rails (also called shear studs, shear rails or SSR) - assumed 6 in penetration at each stud rail column, pass/fail status from Concept's own table, search radius for cutoff-section errors, moving the assumed opening back for stress failures, until every punching check passes. Use when a user asks to design for two-way punching or two-way shear, or about shear studs, shear rails, stud rails, SSR, punching checks, punching openings, cutoff section errors or the search radius. The schedule is the next skill, schedule-ram-concept-stud-rails; setting the rails to User is not built.
---

# Two-Way Punching Design with Stud Rails (RAM Concept)

The engineer calls this designing for two-way punching, shear studs or
shear rails. Concept calls the rails SSR. It is all this workflow.

The office method is in `../../references/RAM_CONCEPT_GUI_NOTES.md`,
"Two-way shear: stud rails". Read it first; this skill automates parts of
it. Run end to end on one model (2636, 2026-10-05): 56 punching checks, all
passing, 51 with stud rails. The schedule is the next skill,
`schedule-ram-concept-stud-rails`; rails to `User` are not built.

```text
settings by hand -> stud_openings.py add --all -> calc
  -> punch-export.ps1 (the Punching Check Analysis table) -> punch_status.py
  -> cutoff errors: punch-radius.ps1 (10, then 12 ft) -> calc --no-mesh -> status again
  -> stress failures, and errors left at 12 ft: stud_openings.py move --back 1 into a TRIAL file
     -> calc -> status -> the engineer accepts or not, against the floor plan
  -> schedule: schedule-ram-concept-stud-rails; rails to User: by hand (not built)
```

## What is automated

| Step | Tool | How it is proved |
|---|---|---|
| List stud rail columns and their rails | `stud_openings.py list <saved.cpt>` | read-only |
| Add the assumed 6 in x 6 in opening | `stud_openings.py add <saved.cpt> <out.cpt> --at X Y` or `--all --existing <cpt>` | openings counted in the saved file |
| Move an assumed opening back from the face | `stud_openings.py move <saved.cpt> <trial.cpt> --back 1 --at X Y` | openings compared in the saved files. The command was run on 2636 as a scratch script; this copy of it is compile-checked only |
| Mesh, calc, save | `stud_openings.py calc <any.cpt> <out.cpt>` | API; about 7 minutes on 2636 at a 2 ft mesh |
| Calc, save (radius changes) | `stud_openings.py calc <any.cpt> <out.cpt> --no-mesh` | about 5 minutes on 2636 |
| Before and after rails | `stud_openings.py compare <before.cpt> <after.cpt>` | read-only |
| Export the status table | `punch-export.ps1 -Out <export.txt>` | file written; positions are for the 2636 tree, check them first. Run on 2636 as a scratch script; this copy is parse-checked only |
| Status of every check | `punch_status.py <model.cpt> <export.txt>` | from Concept's own table |
| Set a check's search radius | `punch-radius.ps1 -Points "x,y;..." -Radius 10` | `-ReadOnly` reads it back; then confirm from a saved file |
| Plan of checks and openings | `punch_plan.py <model.cpt> <out.png>` | openings drawn 5x so they show |

Openings are in the Concept API. Punching checks and stud rail sets are not:
radius changes go through the GUI, and deleting a check or setting rails to
`User` is done by hand.

## The opening rule

- 6 in x 6 in, at the long face of the column and **1 in clear of it**, its
  centre 4.5 in off the middle of that face. The position along the face
  was confirmed by the engineer and the senior reviewer on 2636.
- Why 1 in clear (engineer, 2026-10-06): an opening touching the face makes
  Concept add a third rail on that face (2636: 35 columns went from 8 rails
  to 9, and back to 8 at 1 in). The opening is an assumption, so the gap
  costs nothing. `add` draws it with the gap; the script was changed after
  the 2636 run and `add` has not been rerun since.
- Dropping that rail makes the others run longer: expect a few checks back
  in cutoff-section error at 8 ft, cured at 10 ft.
- One per column that generates stud rails. Columns that pass without rails
  get none.
- **Edge columns: the inside face.** `--face auto` (the default) picks the
  long face away from a slab edge or opening within 10 ft. Only north/south
  or east/west long faces are handled; rotated columns stop the script.

## Rules learned the hard way

- **Status comes from the exported table, not from the saved file.** A
  column that lost its rails is not the same as a check in cutoff-section
  error. On 2636 the radius was first raised on four columns with no rails;
  they were failing on stress (ratio above 2), and 15 real cutoff errors
  went unnoticed until the table was exported.
- A check with no row in the analysis table is in cutoff-section error.
- Re-export the table after any change to the mesh, the openings or the
  checks. On 2636 the list of cutoff errors went from 15 to 16 and changed
  members after a mesh change.
- Unreinforced stress ratio above about 2.2 with stud rail design on: no
  rails at any radius. Do not raise the radius. On 2636 a check at 2.14
  passed with rails and checks at 2.23 to 2.33 failed.
- On 2636, 10 ft cleared 15 of 16 cutoff errors; none needed 12 ft. The one
  left sat beside a stair opening and stayed in error at 12 ft.
- Moving the assumed opening 1 ft back from the face cleared all four
  stress failures (ratio down by about 0.15) and that last cutoff error.
  This is a design assumption, not cleanup: it only stands if the floor
  plan above shows no plumbing at the column, and that is the engineer's
  call. Keep it in a trial file, out of the production model, until the
  engineer accepts it.
- Delete the checks at columns on beams before judging anything.
- **A rail set with rails of two lengths is not finished** (engineer,
  2026-10-07: different-length rails around a column are non-typical). Read
  the stud counts in every `SsrSet`; where some rails are shorter because an
  opening or slab edge sits inside the rail length (2636: the two north rails
  at the stair column (157,307), 15 studs against 36), or where the rails
  cross a slab step (2636 column 59, (157,262)), the column needs a different
  answer, chosen by the engineer: drop cap or drop panel, a beam, or the
  opening moved. A short rail that nothing physical forces is a program
  artefact; the schedule type covers it with full rails. Settle this before
  the schedule, which refuses to type a non-typical column.
- Regenerating the mesh after adding openings moves the rebar results a
  little. Recheck the bars afterwards.
- `punch-radius.ps1` reads the command prompt from the status bar. The
  older pixel test in `set-ram-concept-beam-strips` failed over Remote
  Desktop; this one tests where the white edit box starts.
- Concept's plan canvas does not redraw without a display. Use
  `punch_plan.py` for a picture when the PC is locked.

## Run

1. API session on a copy of the model; Scripting Server running.
2. `stud_openings.py list`, then `add` on one column and check it on plan,
   then `add --all --existing <that file>`, then `calc`.
3. Pause the Scripting Server. `punch-export.ps1`, or by hand: `Design
   Status > Tables > Punching Check Analysis`, `Export...`, save beside the
   model.
4. `punch_status.py`. For the cutoff errors, open `Design Strip > Punching
   Checks Plan` and run `punch-radius.ps1`; resume, `calc --no-mesh`,
   export, status.
5. Sync the result into the production model.
6. What is left: `move --back 1` into a trial file, `calc`, export, status.
   Report the trial; sync it only when the engineer accepts it.

## Not built

- The schedule is its own skill, `schedule-ram-concept-stud-rails` (rows
  from the saved model, proposed types, the office workbook).
- Setting rail sets to `User` to match the schedule.
- Deleting checks.
- Checking the floor plan above for plumbing at a column.
- Tests. Nothing here is covered by `ram-concept/tests` yet.

## Bundled scripts

- `scripts/stud_openings.py`, `scripts/punch_status.py`,
  `scripts/punch_plan.py` (needs matplotlib), `scripts/punch-radius.ps1`,
  `scripts/punch-export.ps1`.
