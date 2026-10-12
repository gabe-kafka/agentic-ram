---
name: simplify-ram-concept-bottom-rebar
description: Replace RAM Concept program bottom bars in both directions with a few constructible user bar groups. Shows the groups-vs-tonnage table for the engineer to pick a row, then absorbs leftovers and peaking bars until the program adds nothing real. Use when a user asks for bottom bending reinforcement, or to simplify, rationalize, or convert bottom reinforcement, bottom additional bars, or "bot reinf" in a Concept slab.
---

# Simplify Bottom Rebar (RAM Concept)

**Shipped.** The team runs this through the JT-ENG connector: skill
`bottom-bars`, tools `bottom_bars_*`. The order of the steps, the office rules and
what the engineer decides live there (`jt-eng-connector/skills/bottom-bars/SKILL.md`),
and lessons from jobs go there first.

What stays here is canonical and vendored into the connector by
`tools/vendor.py`: none of its own: the engine in ../simplify-ram-concept-rebar (simplify_rebar.py bot-long / bot-lat). Change scripts here, commit, then run the
vendor script in the connector.

## Developer run, from `scripts/`

```powershell
python simplify_rebar.py baseline --layer bot-long --work <dir>
python simplify_rebar.py options  --layer bot-long --work <dir> --pick knee
python simplify_rebar.py options  --layer bot-long --work <dir> --option N
python simplify_rebar.py run      --layer bot-long --work <dir> --absorb-peaks
```
