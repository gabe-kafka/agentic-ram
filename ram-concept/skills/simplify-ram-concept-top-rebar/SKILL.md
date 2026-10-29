---
name: simplify-ram-concept-top-rebar
description: Replace RAM Concept program top bars with user bar groups by count - one group per column per direction from one shared list of typical counts (e.g. 5, 7, 10, 15, 20 #8, picked from five priced rows), then one group over each cluster of program bars away from the columns, one length per direction. Use when a user asks for top bending reinforcement, or to simplify, rationalize, or convert top reinforcement, top bars over columns, or "top reinf" in a Concept slab.
---

# Simplify Top Rebar (RAM Concept)

Top bars are column bars. The program already puts one group over almost
every column, by count, straight, centred on the column. So do not merge
across columns: keep one group per column per direction and standardize the
count. The trade-off is **number of typical callouts vs tons**. The top bars
away from the columns (over walls, between columns, at wall ends) are count
groups too, one over each cluster of program bars, the way the engineer
finished 2636 building 1 by hand (2026-10-28).

Setup, guards and the live-session rules are the engine's:
`../simplify-ram-concept-rebar/SKILL.md`. Read it first.

```text
base.cpt (no user top bars, calculated)
  -> options: one count list for both directions, 1 to 5 counts, each row priced
  -> engineer picks a row (2636 building 1: 5, 7, 10, 15, 20)
  -> run: one group per column, both directions -> calc
  -> run-clusters: strays beside a column group widen it once; one count group over
     each cluster of program bars away from the columns -> calc -> repeat while real demand is left
  -> report: schedules, tons, what the program still adds (real vs noise)
```

## Check first: beams

Every beam rule lives in `../clean-up-ram-concept-t-beams`; read it when the
slab has concrete beams. What matters here:

- Until the design spans along each beam are set up as beams, the program
  spreads a large count of bars across the slab strip (2636: 20 to 27 #9 at
  beam columns against 10 typical). `options` and `plan` warn when spans
  along beams still use slab settings. Fix that and recalc before picking
  typical counts.
- Beam runs through the column, parallel to the bars: no top bar called out.
- Beam ends at the column: the column keeps its own count and length.
- **The engine's own bars at beam columns.** User bars inside a concrete
  beam are the engineer's and are never deleted. Groups the engine draws at
  beam columns sit inside the beam too, so each `apply` must recognise them
  as its own: it does, by the footprints in this work folder's plans
  (`owned_footprints`). Before that (2636 building 1, 2026-10-28) four rounds
  stacked the eight latitude groups on the beam lines four deep, and the
  stack went into the production model. Every report now ends with any
  `STACKED: n copies of ... at (x,y)` it finds in the saved round; `dedupe`
  deletes the extra copies in the live session (same footprint, count and
  depth keep one, the engineer's beam bars included since their rows differ
  in depth), and `--calc` verifies after. Run it on any model that was
  worked before 2026-10-29.

Ryan's note also covers the rest of the top steel: continuous runs over
walls, and group the top bars over columns as much as possible.

## Run (from this skill's `scripts/`)

One work folder for both directions, e.g. `rebar-simplify/top-columns/`.
`base.cpt` is a calculated model with no user top bars in either direction.

```powershell
python simplify_top_rebar.py options      --work <dir>                      # 1 to 5 shared counts, priced
python simplify_top_rebar.py run          --work <dir> --typical 5 7 10 15 20
python simplify_top_rebar.py run-clusters --work <dir> --cluster-length 14 12   # long, lat; even feet
python simplify_top_rebar.py report       --work <dir>
python simplify_top_rebar.py dedupe       --work <dir> [--calc]                  # when a report says STACKED
```

`plan`, `apply`, `verify` and `clusters` run single steps. `run` without
`--typical` applies the newest plan. `report` prints the last round again
without a calc, for example after a new override. Each calc is the
engineer's bar-change calc (extent "+ Detailing", out-of-date items only, no
mesh): about 2.5 minutes on 2636 building 1.

## How column groups are made

- A program top bar belongs to a column when the column sits under its
  footprint (2 ft reach). Two bars at one column add up.
- Each column gets the smallest typical count that covers it. A column
  needing more than the largest typical keeps its own count and length.
- **Every bar length is an even number of feet**, rounded up (office rule,
  2026-10-12). A typical callout's length is the longest demand among its
  columns. About an inch over does not earn more. The engineer trims by
  hand where that stretches a callout: on 2636 building 1 he turned a
  `15#8 x 18'` into `16#8 x 14'` and lengthened two `5#8 x 12'` to `14'` to
  sit with their neighbours.
- Each group keeps the program bar's centre, extent width and depth, so it
  sits in the same strip and layer. The two directions are at different
  depths (2636 building 1: longitude -1.50 in, latitude -2.25 in).
- Where a longer typical bar would run off the slab, it keeps the program
  bar's end on that side.
- Bars are by count (`count`), straight both ends.
- Columns with no top demand get no group.
- **A column with a beam running through it gets no group in the beam's
  direction.** `plan` records it as an override ("beam carries this
  moment") in `decisions.json`; the report then reads `no top bar called out
  (override): (269,111) ... [program would add 8#9]`. The program bar stays
  yellow in Concept and is not chased.
- A column at the end of a beam keeps its own count and length (kind "beam
  end") and does not stretch the typical callouts. Bars that cross a beam
  are treated like any other column.
- Any other location the engineer overrides (`t_beam_cleanup.py override`)
  is set aside the same way, over a column or not.

## Presenting options

Write callouts as count then size: `10#9 x 12' at 52 columns`. `options`
prints one table: the cheapest shared count list for 1, 2, 3, 4 and 5
counts, with the total tons and the schedule per direction. One list serves
both directions and goes on the drawings as is; the largest count is always
on it. Show all five rows in the chat and recommend; one count for every
column is never the answer when a few columns need two to three times the
rest (2636 building 2: 45 tons against 17). The engineer asked for five rows
and took the five-count row on building 1.

2636 building 1, picked by the engineer (program-only over columns 4.6 and
6.2 tons; the counts 5, 7, 10, 15, 20 #8):

| Direction | Schedule | Tons |
|---|---|---|
| Longitude | 5#8 x 12' at 13, 7#8 x 12' at 2, 10#8 x 14' at 3, 15#8 x 18' at 3; eight beam-end columns at 12 to 15#8 | 4.7 |
| Latitude | 5#8 x 10' at 6, 7#8 x 10' at 6, 10#8 x 12' at 6, 15#8 x 12' at 4, 20#8 x 14' at 8 | 5.9 |

2636 building 2 (two counts plus own, #9): longitude 10#9 x 12' at 52,
15#9 x 13' at 13, five heavy columns at 17#9 to 27#9, 17.3 tons; latitude
10#9 x 15' at 58, 15#9 x 14' at 8, three heavy columns, 19.3 tons.

Flag the heavy columns on their own. Check first whether they sit on a
beam. Otherwise more than about 15 #9 bars over one column usually means a
transfer load, a thin slab or a punching problem, not a detailing question.

## Top bars away from columns, by count

What the engineer drew by hand on 2636 building 1 after the column groups
(23 groups in latitude, 5 in longitude, about 50 minutes), now
`run-clusters`:

- **One group over each cluster of program bars.** Program bars that touch
  across (within 1.25 ft) and overlap along are one cluster; the group
  covers the cluster's footprint, the strip's width (7.5 or 15 ft on 2636).
  A chain wider than a strip (18 ft) is cut at its widest gaps; the
  engineer cut at the design strip boundary (an 8#8 middle-strip group
  beside a 20#8 column-strip group where one chain crossed both).
- **Count: the sum of the program bars under it, rounded up to the typical
  count that covers it;** under the smallest typical the sum stands
  (2#8, 3#8, 4#8). He wrote 7#8 nine times where the sums were 4 to 7.
- **One length per direction** (`--cluster-length`): 12' in latitude for
  every group but one, 14' in longitude, whatever the program bars'
  lengths were. Without the flag the commonest program length is used and
  printed; set it when his is different (on building 1 the default would
  have been 12' in longitude).
- **A run over a wall** (a wall across the bars under the whole cluster,
  demand fairly even along it) stays one group, at its densest program
  bar's spacing across the run. He went heavier: `46#8 x 14'` over 23 ft
  (about 6 in) and `31#8 x 14'` over 24 ft (about 9 in) where this rule
  gives 34 and 26. Runs are flagged in the output; he sets them.
- **Strays beside a column group first.** Before clustering, a leftover
  alongside a column group adds to its count; one beside the extent, within
  5 ft, widens the group once over it and moves it up a count (he widened
  two `10#8 x 14'` to `12#8` and `15#8`). A widened group takes no second
  stray across: that is the next strip's bar (building 2: a column ran from
  15#9 to 25#9 when widened round after round).
- **Noise is left.** A lone program bar up to 10 ft, a pair up to 7 ft, and
  slivers under 3 ft wide against the slab edge are not chased: he left 17
  in longitude and 14 in latitude. Noise beside a real bar joins its group.
  The report counts noise apart from real leftovers.
- Everything by count, straight, at the program bars' depth.

Checked against his model: of his 28 groups, 23 land where the rule puts
one and 20 of those within two bars of his count; the rule misses 3 small
groups he drew over noise, and splits one 7.5 ft cluster he drew as two.
Each `run-clusters` round regrows the clusters from the new leftovers
(earlier clusters are seeds, never dropped), 3 rounds at most.

### Bands by spacing (the older way)

`band-options`, `bands`, `run-bands` and `merge-bands` still draw the
scattered top bars as spaced bands like the bottom layers (2636 building 2:
longitude 20 bands, 8.3 tons; latitude 17 bands, 7.5 tons; write spaced bars
as `#7 @12"`). `run-bands` captures leftovers the same way, column groups
first (widen once), then the nearest band within 5 ft. Two bands stacked in
one middle strip is wrong: `merge-bands` merges neighbours up to two
spacing steps apart when one merge adds no more than 500 lb.

Office standard (2026-10-06): two to three count conditions for the slab,
copied to every column in a region; outliers keep their own count. The
typical counts here are those conditions.

## Report

Per direction: the column schedule with column counts and tons, the groups
away from columns with tons, and what the program still adds: real over
columns (must be 0), beside a column group (widen once or the next strip's
bar), real elsewhere (must be 0 when done), and noise (left).

## Validation

`python -m unittest ram-concept/tests/test_top_column_bars.py` (49 tests:
assignment, typing, capture, shared options, clusters, noise). Live-proven
on 2636 building 2 (column groups and bands) and building 1 (column groups
from a shared five-count list; the clusters rule checked offline against the
engineer's hand finish, not yet drawn live). Check bar depth and placement
in the `Top Long` and `Top Lat` plans on a new model, and that user bars at
beam columns are single.

## Bundled scripts

- `scripts/simplify_top_rebar.py`: CLI against the live API session.
- `scripts/top_columns.py`: column assignment, typical counts, shared
  options, capture, clusters, schedules (pure, tested).
