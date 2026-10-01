---
name: simplify-ram-concept-top-rebar
description: Replace RAM Concept program top bars over columns with one count-based user bar group per column per direction, using one or two typical callouts (e.g. 10#9 x 12') plus own counts for the few heavy columns. Use when a user asks to simplify, rationalize, or convert top reinforcement, top bars over columns, or "top reinf" in a Concept slab.
---

# Simplify Top Rebar (RAM Concept)

Top bars are column bars. The program already puts one group over almost
every column, by count, straight, centred on the column. So do not merge
across columns: keep one group per column per direction and standardize the
count. The trade-off is **number of typical callouts vs tons**.

Setup, guards and the live-session rules are the engine's:
`../simplify-ram-concept-rebar/SKILL.md`. Read it first.

```text
base.cpt (no user top bars, calculated)
  -> options: 1 to 4 callouts per direction, with tons
  -> engineer picks typical counts (e.g. 10 and 15)
  -> run: one group per column, both directions -> calc
  -> report what the program still adds
```

## Check first: beams

Columns on a concrete beam are T or L beam sections, not slab. Until the
design spans along each beam are set up as beams, the program spreads a
large count of bars across the slab strip (2636: 20 to 27 #9 at beam columns
against 10 typical). `options` and `plan` warn when spans along beams still
use slab settings. Fix that with `../set-ram-concept-beam-strips` and recalc
before picking typical counts; design strips are not in the API.

Office setup for a span along a beam (R. Darling, 2026-09-23):

- Strip generation: unchanged.
- Column strip: width calc to the code T-beam option, cross section to
  **T or L**, torsion design to **beam**, and any other setting that offers
  "beam" to beam. Covers stay 2 in.
- Middle strip: untick "use column strip properties" and give it the typical
  slab strip properties.
- Shear bars: hold until reviewed.

Effect: the bars concentrate over the beam and the count drops. The same
note covers the rest of the top steel: continuous runs over walls, and group
the top bars over columns as much as possible.

## Run (from this skill's `scripts/`)

One work folder for both directions, e.g. `rebar-simplify/top-columns/`.
`base.cpt` is a calculated model with no user top bars in either direction.

```powershell
python simplify_top_rebar.py options --work <dir>
python simplify_top_rebar.py run     --work <dir> --typical 10 15
```

`plan`, `apply` and `verify` run single steps. `run` without `--typical`
applies the newest plan.

## How groups are made

- A program top bar belongs to a column when the column sits under its
  footprint (2 ft reach). Two bars at one column add up.
- Each column gets the smallest typical count that covers it. A column
  needing more than the largest typical keeps its own count and length.
- A typical callout's length is the longest demand among its columns, in
  whole feet. About an inch over does not earn another foot.
- Each group keeps the program bar's centre, extent width and depth, so it
  sits in the same strip and layer. The two directions are at different
  depths (2636: longitude -2.56 in, latitude -1.56 in).
- Where a longer typical bar would run off the slab, it keeps the program
  bar's end on that side.
- Bars are by count (`count`), straight both ends.
- Columns with no top demand get no group.

## Presenting options

Write callouts as count then size: `10#9 x 12' at 52 columns`. Show the 1 to
4 callout table per direction, then recommend. One callout for every column
is never the answer when a few columns need two to three times the rest; on
2636 that row cost 45 tons against 17.

2636, picked by the engineer (program-only over columns about 11 tons each
way):

| Direction | Schedule | Tons |
|---|---|---|
| Longitude | 10#9 x 12' at 52, 15#9 x 13' at 13, five heavy columns at 17#9 to 27#9 | 17.3 |
| Latitude | 10#9 x 15' at 58, 15#9 x 14' at 8, three heavy columns at 20#9, 21#9, 27#9 | 19.3 |

First calc: no real program demand left over any column in either direction.

## What it leaves

Program top bars that are not over a column stay as program bars: over
walls, at wall ends and around cores. On 2636 that was 70 groups (2.0 tons)
in longitude and 46 (1.7 tons) in latitude. Report them; the engineer decides
whether to band them with the engine (`simplify_rebar.py`, layer `top-long`
or `top-lat`) or detail them by hand. Running the engine on a top layer
replaces that layer's column groups, so that path is not wired up yet.

Flag the heavy columns on their own. Check first whether they sit on a
beam (see above). Otherwise more than about 15 #9 bars over one column
usually means a transfer load, a thin slab or a punching problem, not a
detailing question.

## Report

Per direction: the schedule with column counts, tons, real program demand
left over columns (must be 0), and the count and tons of program bars not
over a column.

## Validation

`python -m unittest ram-concept/tests/test_top_column_bars.py`. Live-proven
on 2636 only, one run; check bar depth and placement in the `Top Long` and
`Top Lat` plans on a new model.

## Bundled scripts

- `scripts/simplify_top_rebar.py`: CLI against the live API session.
- `scripts/top_columns.py`: column assignment, typical counts, schedules
  (pure, tested).
