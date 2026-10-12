---
name: top-reinf
description: Simplify RAM Concept top reinforcement - one count-based user bar group over each column in each direction, from one or two typical callouts (e.g. 10#9 x 12') plus own counts for heavy columns. Use when the user says top reinf, top reinf refine, top bars, bars over columns, or simplify top rebar.
---

# Top Reinf (RAM Concept)

Follow `ram-concept/skills/simplify-ram-concept-top-rebar/SKILL.md`, which
builds on `ram-concept/skills/simplify-ram-concept-rebar/SKILL.md`.

- Needs an API-enabled Concept on a copy of the model; Resume the Scripting
  Server before each run and Pause it when the engineer needs to look.
- Show the typical-callout options per direction, written as count then
  size (`10#9 x 12' at 52 columns`). The engineer picks the typical counts.
- Do not group across columns. Heavy columns keep their own count; flag them.
- Start the `rebar-dashboard` preview so the Browser pane shows Working or
  Ready for human review.
- Report the schedule, tons, anything still needed over a column, and the
  program bars left that are not over a column.
