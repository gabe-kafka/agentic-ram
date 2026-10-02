---
name: simplify-ram-concept-bottom-rebar
description: Replace RAM Concept program bottom bars in both directions with a few constructible user bar groups. Shows the groups-vs-tonnage table for the engineer to pick a row, then absorbs leftovers and peaking bars until the program adds nothing real. Use when a user asks to simplify, rationalize, or convert bottom reinforcement, bottom additional bars, or "bot reinf" in a Concept slab.
---

# Simplify Bottom Rebar (RAM Concept)

Bottom bars are zone bars: wide bands that merge cheaply. The job is to pick
how many bands the engineer wants and what that costs in steel.

This skill is the bottom-face workflow. The engine (scripts, grouping rules,
setup, guards) is `../simplify-ram-concept-rebar`; read its `SKILL.md` first.

```text
bot-long: baseline -> options table -> engineer picks -> run
bot-lat:  baseline -> options table -> engineer picks -> run
```

## Check first

- Design spans drawn along walls and sliver strips at slab edges create
  bottom bars that are not real demand. Settle the strips before simplifying.
- Deleting a span that runs along a wall does **not** widen the neighbouring
  strip. Concept stops it halfway to the wall, so the half-bay beside the
  wall drops out of design in that direction. Compare strip coverage before
  and after, or set those strip widths by hand.

## Run (from the engine's `scripts/`)

One work folder per layer and per option tried, in the job folder, e.g.
`rebar-simplify/bot-long/`, `rebar-simplify/bot-lat-opt7/`.

```powershell
python simplify_rebar.py baseline --layer bot-long --work <dir>
python simplify_rebar.py options  --layer bot-long --work <dir> --pick knee
python simplify_rebar.py options  --layer bot-long --work <dir> --option N
python simplify_rebar.py run      --layer bot-long --work <dir> --absorb-peaks
```

Then the same for `bot-lat`.

- `baseline --reuse-calc` skips the calc when the layer has no user bars and
  the open model was just calculated (the usual case for the second layer).
- Trying another row: use a new work folder with a copy of `base.cpt`. `run`
  always applies the newest plan in its folder.

## Picking the row

Show the whole table every time; the engineer picks. The `<- knee` row is the
suggestion: the fewest groups before a step costs more than 0.5 tons per
group removed.

- Table tons are starting values. Absorbing leftovers and peaking bars adds
  about 2 to 5 tons; say so before the run.
- On 2636 the engineer went at or past the knee both times:

| Layer | Program only | Picked | Finished |
|---|---|---|---|
| bot-long | 130 groups, 7.2 t | option 5: 33 groups, 16.8 t | 30 groups, 19.3 t |
| bot-lat | 121 groups, 6.8 t | option 7: 21 groups, 22.7 t | 20 groups, 27.7 t |

## Bottom-specific rules

- Bar size is the layer's dominant program size (#7 on 2636).
- Depth follows the thinnest slab under each group. A band set for 16 in
  slab that crosses 12 in slab sits below the soffit and gets no credit.
- Bars inside a concrete beam are not banded. The rules are in
  `../clean-up-ram-concept-t-beams`: mid-span bars become the beam's own
  bars by count, and a mid-span leftover adds to that count on the next
  absorb. Bars reaching a beam end are listed as the engineer's call, or as
  `no bar called out (override: reason)` once the engineer overrides them.
- `--absorb-peaks` stretches the nearest group over 1 to 2 bar, 5 ft or
  shorter program bars. It never tightens spacing or adds a group for one.
  Peaks with no group within 5 ft, or already inside a group, stay listed
  for the engineer; most sit at slab edges or mesh spikes.

## Report

Per layer: program-only groups and tons, the row picked, finished groups and
tons, real leftovers (must be 0), and the peaking bars left with locations.
