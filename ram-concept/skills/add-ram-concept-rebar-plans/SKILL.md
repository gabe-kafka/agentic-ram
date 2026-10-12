---
name: add-ram-concept-rebar-plans
description: Add the office's four rebar review plans (Top Long, Top Lat, Bot Long, Bot Lat) to a saved RAM Concept model, set up as on 2636 building 2 - one face and one direction per plan, user and program concentrated bars with descriptions and extents, walls, columns and slab elements. Use when a model lacks the Top Long / Bot Lat plans, when asked to set up the rebar views, plan views or review plans, or before the first rebar pass on a new model.
---

# Add Rebar Review Plans (RAM Concept)

The office reviews rebar in four custom plans under `Layers > Reinforcement`,
one per face and direction (`references/RAM_CONCEPT_GUI_NOTES.md`, "Rebar
review plans"). The published API cannot create plans, so `rebar_plans.py`
writes them into a copy of the saved file: each one is a copy of the model's
own standard `Top Bars` plan with the visible objects set to the convention,
exactly as the plans were set up on 2636 building 2.

| Plan | Reinforcement layer shows |
|---|---|
| `Top Long` | Longitude user + program concentrated bars, top face |
| `Top Lat` | Latitude user + program concentrated bars, top face |
| `Bot Long` | Longitude user + program concentrated bars, bottom face |
| `Bot Lat` | Latitude user + program concentrated bars, bottom face |

Every plan also shows concentrated bar descriptions and extents, and on the
Element layer walls above and below (outline only), columns above and below,
slab elements and their edges. Nothing on any other layer.

## Run

```powershell
python rebar_plans.py list <model.cpt>
python rebar_plans.py add  <model.cpt> <out.cpt> [--only "Bot Long" "Bot Lat"]
```

1. Save the model (the plans go into the saved file, not the open window).
2. `add` into a new file name. Plans already there are left alone; the
   output says when one of them does not show the office set-up.
3. Open the new file in Concept. The plans are the last four under
   `Layers > Reinforcement` in the report tree.

## Rules

- Never the model itself: `out` must be a new file. A model open in Concept
  is not read from disk again, so open the new file.
- Check the face filter, not the name: `list` reads what each plan shows.
- The Bentley file format is not documented. The script copies only what a
  plan is made of (PlanData, PlotSpecData, FilterKeyShowFilter, StdReportLeaf)
  and takes new UIDs above the model's largest. Proven on 2636 building 1
  (RAM Concept 2025) on 2026-10-12; check the first run on a new Concept
  version by opening the file and the four plans.
