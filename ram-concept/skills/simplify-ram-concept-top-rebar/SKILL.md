---
name: simplify-ram-concept-top-rebar
description: Replace RAM Concept program top bars over columns with one count-based user bar group per column per direction, using one or two typical callouts (e.g. 10#9 x 12') plus own counts for the few heavy columns. Use when a user asks for top bending reinforcement, or to simplify, rationalize, or convert top reinforcement, top bars over columns, or "top reinf" in a Concept slab.
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

Every beam rule lives in `../clean-up-ram-concept-t-beams`; read it when the
slab has concrete beams. What matters here:

- Until the design spans along each beam are set up as beams, the program
  spreads a large count of bars across the slab strip (2636: 20 to 27 #9 at
  beam columns against 10 typical). `options` and `plan` warn when spans
  along beams still use slab settings. Fix that and recalc before picking
  typical counts.
- Beam runs through the column, parallel to the bars: no top bar called out.
- Beam ends at the column: the column keeps its own count and length.

Ryan's note also covers the rest of the top steel: continuous runs over
walls, and group the top bars over columns as much as possible.

## Run (from this skill's `scripts/`)

One work folder for both directions, e.g. `rebar-simplify/top-columns/`.
`base.cpt` is a calculated model with no user top bars in either direction.

```powershell
python simplify_top_rebar.py options --work <dir>
python simplify_top_rebar.py run     --work <dir> --typical 10 15
```

`plan`, `apply` and `verify` run single steps. `run` without `--typical`
applies the newest plan. `report` prints the last round again without a
calc, for example after a new override.

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

## General top bars (away from columns)

The second class: program top bars over no column (over walls, at wall ends,
around cores). Treated like bottom bars, as bands by spacing, once the
column groups are in and calculated. The column groups are kept as they are.

```powershell
python simplify_top_rebar.py band-options --work <dir> --band-size "#7"
python simplify_top_rebar.py bands        --work <dir> --band-size "#7" --option LONG LAT
python simplify_top_rebar.py run-bands    --work <dir>
```

- `band-options` prints the bands-vs-tons table per direction with the knee
  row marked; the engineer picks. `bands` without `--option` takes the knee.
- Write spaced bars as `#7 @12"`.
- `run-bands` applies, calcs and captures what the program still adds,
  until nothing changes (3 rounds at most). Capturing adds steel; say so.
- `--verdicts` waives bars that sit only on a mat-boundary notch.
- 2636: the engineer went one row past the knee for fewer bands. Longitude
  20 bands, 8.3 tons; latitude 17 bands, 7.5 tons after absorbing (program
  only: 1.8 and 1.6 tons).

### Capturing leftovers

The engineer's rule: a stray program bar beside a user group is captured by
that group wherever it can be. `run-bands` does this each round, column
groups first, then bands.

- A leftover over a column goes to that column's group: alongside the group
  its bars add to the count (`4#9 x 10'` becomes `5#9 x 10'`); past the end
  of the group, within 5 ft, the group is lengthened and keeps its own
  callout. A typical group that now needs more moves to the next typical
  count (`10#9` to `15#9`).
- A column with a leftover and no group gets its own group by the usual
  typical rule.
- A peaking bar away from the columns goes to a column group only when at
  least half its width is inside that group's extent; otherwise the nearest
  band within 5 ft is stretched over it.
- **A column group's extent is never widened.** A bar beside the extent is
  the next strip's bar. Widening thins the column bars and the program asks
  for more every round; on 2636 one column ran from 15#9 to 25#9.
- Still listed, not captured: bars just outside a column group's extent and
  bars inside a band. The zone rule in
  `../../references/SLAB_REBAR_OPTIMIZATION.md` is the fix and is not built.

Office standard (2026-10-06): two to three count conditions for the slab,
copied to every column in a region; outliers keep their own count. The
typical counts here are those conditions.

### One callout per zone

Two bands stacked in one middle strip is wrong. Until bands are grouped by
strip, `merge-bands` merges neighbouring bands up to two spacing steps apart
at the tighter spacing when one merge adds no more than 500 lb
(`--class-jump`, `--merge-budget`). On 2636 it turned `#7 @12"` and `#7 @6"`
between two columns into one `#7 @6" x 14'`. A looser budget also merges a
70 ft band to `@6"` for one more ton; show that cost before doing it.

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
