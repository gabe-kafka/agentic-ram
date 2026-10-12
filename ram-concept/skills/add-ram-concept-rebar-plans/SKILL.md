---
name: add-ram-concept-rebar-plans
description: Add the office's four rebar review plans (Top Long, Top Lat, Bot Long, Bot Lat) to a saved RAM Concept model, set up as on 2636 building 2 - one face and one direction per plan, user and program concentrated bars with descriptions and extents, walls, columns and slab elements. Use when a model lacks the Top Long / Bot Lat plans, when asked to set up the rebar views, plan views or review plans, or before the first rebar pass on a new model.
---

# Add Rebar Review Plans (RAM Concept)

**Shipped.** The team runs this through the JT-ENG connector: skill
`rebar-plans`, tools `concept_rebar_plans_*`. The order of the steps, the office rules and
what the engineer decides live there (`jt-eng-connector/skills/rebar-plans/SKILL.md`),
and lessons from jobs go there first.

What stays here is canonical and vendored into the connector by
`tools/vendor.py`: rebar_plans.py. Change scripts here, commit, then run the
vendor script in the connector.

## Developer run, from `scripts/`

```powershell
python rebar_plans.py list <model.cpt>
python rebar_plans.py add  <model.cpt> <out.cpt> [--only "Bot Long" "Bot Lat"]
```
