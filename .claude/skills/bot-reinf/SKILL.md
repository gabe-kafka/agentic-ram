---
name: bot-reinf
description: Simplify RAM Concept bottom reinforcement - replace program bottom bars (longitude then latitude) with a few user bar groups, showing the groups-vs-tonnage table for the engineer to pick. Use when the user says bot reinf, bottom reinf, bottom bars, or simplify bottom rebar.
---

# Bottom Reinf (RAM Concept)

Follow `ram-concept/skills/simplify-ram-concept-bottom-rebar/SKILL.md`, which
builds on `ram-concept/skills/simplify-ram-concept-rebar/SKILL.md`.

- Needs an API-enabled Concept on a copy of the model; Resume the Scripting
  Server before each run and Pause it when the engineer needs to look.
- Run each layer in the background and show the options table before
  applying. The engineer picks the row.
- Start the `rebar-dashboard` preview so the Browser pane shows Working or
  Ready for human review.
- Report groups, tons, real leftovers and peaking bars per layer.
