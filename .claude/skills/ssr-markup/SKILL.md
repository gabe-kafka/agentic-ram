---
name: ssr-markup
description: Tag the column location plan with the stud rail marks (SR-1, SR-2, ...) as Bluebeam text boxes for the documentation team, from the SSR workbook and the engineer's plot of S101D. Use when the user says SSR markup, SSR plan, SSR labels, Bluebeam labels, stud rail plan, tag the columns, or label the plan.
---

# SSR Plan Markup (RAM Concept, Bluebeam)

Follow `ram-concept/skills/markup-ram-concept-ssr-plan/SKILL.md`.

- Input: the job's `SSR.xlsx` (`SSR Input` tab) and the engineer's own plot of
  S101D in `Calculations\03_RAM Structural\2-Way Reinf Export\`. Never write
  over his plot; the tagged file gets its own name.
- First prove the workbook rows against the rail sets in the model he is in.
- Run `scripts/markup_ssr_plan.py <SSR.xlsx> <plot.pdf> <out.pdf> --report
  <placements.json>`; the problem list must be empty and the render checked.
- Tags are real Bluebeam `Text Box` markups (blue 10 pt, no fill, author GKG),
  so the drafter can move or retype any of them.
- Open the result in Bluebeam Revu for him when done.
