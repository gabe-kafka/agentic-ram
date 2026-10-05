---
name: design-ram-concept-stud-rails
description: Draft workflow for two-way (punching) shear stud rails in a RAM Concept slab - assumed 6 in penetration at each stud rail column, search radius changes, pass/fail status from Concept's own table. Use when a user asks about stud rails, SSR, punching checks, punching openings, cutoff section errors or the search radius. Not finished - grouping into a schedule and setting rails to User are not built.
---

# Stud Rails (RAM Concept) — draft

The office method is in `../../references/RAM_CONCEPT_GUI_NOTES.md`,
"Two-way shear: stud rails". Read it first; this skill only automates parts
of it. Proven on one model (2636), as far as the status table.

```text
settings by hand -> stud_openings.py add --all -> calc
  -> export the Punching Check Analysis table -> punch_status.py
  -> cutoff errors: punch-radius.ps1 (10, then 12 ft) -> calc -> status again
  -> stress failures: engineer (move the opening, or a beam)
  -> schedule and rails to User: by hand (not built)
```

## What is automated

| Step | Tool | How it is proved |
|---|---|---|
| List stud rail columns and their rails | `stud_openings.py list <saved.cpt>` | read-only |
| Add the assumed 6 in x 6 in opening | `stud_openings.py add <saved.cpt> <out.cpt> --at X Y` or `--all --existing <cpt>` | openings counted in the saved file |
| Mesh, calc, save | `stud_openings.py calc <any.cpt> <out.cpt>` | API; about 4 minutes on 2636 |
| Before and after rails | `stud_openings.py compare <before.cpt> <after.cpt>` | read-only |
| Status of every check | `punch_status.py <model.cpt> <export.txt>` | from Concept's own table |
| Set a check's search radius | `punch-radius.ps1 -Points "x,y;..." -Radius 10` | `-ReadOnly` reads it back; then confirm from a saved file |
| Plan of checks and openings | `punch_plan.py <model.cpt> <out.png>` | openings drawn 5x so they show |

Openings are in the Concept API. Punching checks and stud rail sets are not:
radius changes go through the GUI, and deleting a check or setting rails to
`User` is done by hand.

## The opening rule

- 6 in x 6 in, touching the long face of the column, its centre 4.5 in off
  the middle of that face. That clears a rail at mid-face and the corner
  rails. Confirmed by the engineer and the senior reviewer on 2636.
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
- Unreinforced stress ratio above about 2 with stud rail design on: no
  rails at any radius. Do not raise the radius; it is the engineer's call.
- Delete the checks at columns on beams before judging anything.
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
3. Pause the Scripting Server. In Concept open `Design Status > Tables >
   Punching Check Analysis`, press `Export...`, save beside the model.
4. `punch_status.py`. For the cutoff errors, open `Design Strip > Punching
   Checks Plan` and run `punch-radius.ps1`; resume, `calc`, export, status.
5. Sync the result into the production model before handing back.

## Not built

- Reading the exported `Punching Check Design` table into the office stud
  rail spreadsheet and grouping by rail length (1 to 1.5 ft steps), then
  stud spacing.
- Setting rail sets to `User` to match the schedule.
- Deleting checks, and moving an opening back from the face.
- Tests. Nothing here is covered by `ram-concept/tests` yet.

## Bundled scripts

- `scripts/stud_openings.py`, `scripts/punch_status.py`,
  `scripts/punch_plan.py` (needs matplotlib), `scripts/punch-radius.ps1`.
