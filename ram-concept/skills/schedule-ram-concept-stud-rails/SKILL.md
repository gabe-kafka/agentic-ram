---
name: schedule-ram-concept-stud-rails
description: Create the shear stud schedule (stud rail or SSR schedule) from a calculated RAM Concept model - one row per stud rail column as the program designed it, types proposed by rail length and stud spacing with a real controlling row for each, a types-against-studs table for the engineer to pick from, and the office SSR workbook filled for CAD. Use after two-way punching passes, when a user asks for the shear stud schedule, stud rail schedule, SSR schedule or SSR spreadsheet, or to group stud rails into types. Setting the rails to User in the model is not built.
---

# Shear Stud Schedule (RAM Concept)

The office method is in `../../references/RAM_CONCEPT_GUI_NOTES.md`,
"Two-way shear: stud rails", last part. It follows
`design-ram-concept-stud-rails`: every punching check passes first.

```text
calculated model, all punching checks passing (status from the exported table)
  -> stud_rail_schedule.py --options      types against studs, the engineer picks a step
  -> stud_rail_schedule.py <rows.json>    rows, proposed types, one controlling row per type
  -> the engineer reviews the types
  -> build-ssr-workbook.ps1               the office workbook: input rows and the FOR CAD table
  -> markup-ram-concept-ssr-plan          the column location plan with an SR-n Bluebeam tag at every stud rail column
  -> by hand: each rail set to User with its type's values, calc, every check still passes
```

The handoff to the documentation team is two files, as on 2636_03: the workbook's `FOR CAD` tab (the schedule
table, from here) and the column location plan (sheet S101D) with a blue text-box markup `SR-n` beside each stud
rail column's bubble (the next skill, `markup-ram-concept-ssr-plan`).

## What is automated

| Step | Tool | How it is proved |
|---|---|---|
| Rows as designed | `stud_rail_schedule.py <calc.cpt> <rows.json>` | 2636: 51 rows, identical to the rows the job's workbook was built from |
| Non-typical columns | same run, `NON-TYPICAL` list | 2636: exactly the two the senior reviewer found by eye, (157,262) rails across the 12 to 16 in step and (157,307) north rails stopped by the stair; (176,277) classed a program artefact |
| Types against studs | `stud_rail_schedule.py <calc.cpt> --options` | 2636: 6 to 9 types, +17 to +36 percent studs |
| Proposed types | same, `--step 1.25 --tight 4.0` | 2636: 8 types, +17 percent; the grouping picked by hand on that job was 7 types, +15 percent |
| Workbook | `build-ssr-workbook.ps1 -Source <previous SSR.xlsx> -RowsJson rows.json -Out <new.xlsx> -Tag B2 -SourceTag B3` | the job's copy built the 2636 workbook; this copy is parse-checked only |

Read-only on the model. No API session is needed. The `Column at (x, y) ft` column added to `SSR Input` on 2636_02
is what the plan markup reads; keep it.

## The grouping rule

Senior reviewer, 2026-10-02: group by rail length in steps of about 1 to
1.5 ft, then by stud spacing (light about 5 to 6 in, heavy about 3 to 4 in).
The same length at two spacings stays two types.

- Rows are split by number of rails first. On 2636 the 16 in slab gave 8
  rails and the 12 in slab gave 10.
- A type is a rail set the program designed: its controlling row has the
  tightest spacing and the longest rail of the type, so no column gets less
  than the program gave it. The script does not invent a row.
- Rail length = first spacing + (studs - 1) x typical spacing.
- Fewer types cost studs. Show the `--options` table and let the engineer
  pick, as with bar groups against tons.
- The types are a proposal until the engineer accepts them. He may move a
  column between types in the workbook; the workbook's own check column
  says whether each controlling row still covers its type.

## Rules

- **Pass or fail is not in the saved file.** Have a `Punching Check
  Analysis` export for the same model state before calling the schedule
  final (`design-ram-concept-stud-rails`).
- Any change to the mesh, the openings, a radius or the bars changes the
  rails. Read the rows again.
- **Every rail around a column is the same type and length** (engineer,
  2026-10-07). The comment column stays blank, as the Building 3 schedule
  shipped. A program design with some rails shorter than the rest is handled
  two ways, and the script tells them apart by geometry: if nothing physical
  lies on the short rail's line within the longest rail's length, it is a
  program artefact and the standard type covers the column with full rails
  (2636 column 62, (176,277), E/W rails one stud short); if an opening or the
  slab edge lies on that line, the column is **NON-TYPICAL**: it gets no type,
  is listed for the engineer, and needs another solution (drop cap, beam,
  moved opening) before the schedule is final (2636 column 67, (157,307), two
  north rails stopped by the stair). "Go up to the next category if needed",
  never a note.
- A model that already holds user rail sets stops the script.
- One-way shear at the stud rail columns is checked through the rails
  (`design-ram-concept-one-way-shear`). It rarely changes them; if it does,
  redo the schedule.
- The workbook builder starts a hidden Excel. Do not run it while the
  engineer has that workbook open.

## Not built

- Setting each rail set to `User` with its type's values, and the calc
  that proves the types. Stud rail sets are not in the Concept API.
- Exterior columns with rails on three or two sides (configurations B, C).
  Everything so far was configuration A.
- A workbook template of its own: the builder copies the previous job's.

## Bundled scripts

- `scripts/stud_rail_schedule.py`, `scripts/build-ssr-workbook.ps1`.
- Tests: `ram-concept/tests/test_stud_rail_schedule.py` (the grouping).
