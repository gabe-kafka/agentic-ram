---
name: design-ram-concept-one-way-shear
description: Design a RAM Concept two-way slab for one-way shear by the office two-model method - a full-width screening copy, the engineer's marked-up PDF read back to him as an SVG before any bar is drawn, then user stirrup zones in the real model (#4 open stirrups, 6 in along the span, one leg per mat bar, from the support face) and a check that the program adds nothing more. Use when a user asks for one-way shear, slab shear reinforcement, stirrups in the slab, the full width model, the shear reinforcement plan, or hands over a one-way shear markup PDF.
---

# One-Way Shear Design with a PDF Markup (RAM Concept)

**Shipped.** The team runs this through the JT-ENG connector: skill
`one-way-shear`, tools `one_way_shear_*` and `concept_calc`. The order of the
steps, the markup convention, the office rules and what the engineer decides
live there (`jt-eng-connector/skills/one-way-shear/SKILL.md`), and lessons from
jobs go there first. The building 2 and 3 record (hand-off to drafting, what the
job taught) is in this file's history (git log) and in the connector skill.

What stays here is canonical and vendored into the connector by
`tools/vendor.py`: read_markup.py, markup_plan.py, shear_regions.py,
place_stirrups.py, zones_check.py, stirrup_collisions.py, live_set_rows.py.
Not shipped (lab): zones_svg.py, beside.py, demand_main.py, live_fix_zones.py,
fit_sheets.py, tag_st1_plan.py (the drafting hand-off), full-width-strips.ps1.
Change scripts here, commit, then run the vendor script in the connector.

## Developer run, from `scripts/`

```text

```
