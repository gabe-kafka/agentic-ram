---
name: design-ram-concept-stud-rails
description: Design a RAM Concept slab for two-way punching shear with stud rails (also called shear studs, shear rails or SSR) - assumed 6 in penetration at each stud rail column, pass/fail status from Concept's own table, search radius for cutoff-section errors, moving the assumed opening back for stress failures, until every punching check passes. Use when a user asks to design for two-way punching or two-way shear, or about shear studs, shear rails, stud rails, SSR, punching checks, punching openings, cutoff section errors or the search radius. The schedule is the next skill, schedule-ram-concept-stud-rails; setting the rails to User is not built.
---

# Two-Way Punching Design with Stud Rails (RAM Concept)

**Shipped.** The team runs this through the JT-ENG connector: skill
`stud-rails`, tools `stud_rails_*`. The order of the steps, the office rules and
what the engineer decides live there (`jt-eng-connector/skills/stud-rails/SKILL.md`),
and lessons from jobs go there first.

What stays here is canonical and vendored into the connector by
`tools/vendor.py`: stud_openings.py, punch_status.py, punch_plan.py, punch-export.ps1, punch-radius.ps1. Change scripts here, commit, then run the
vendor script in the connector.
