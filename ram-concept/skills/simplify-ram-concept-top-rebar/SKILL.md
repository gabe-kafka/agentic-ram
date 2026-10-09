---
name: simplify-ram-concept-top-rebar
description: Replace RAM Concept program top bars over columns with one count-based user bar group per column per direction, using one or two typical callouts (e.g. 10#9 x 12') plus own counts for the few heavy columns. Use when a user asks for top bending reinforcement, or to simplify, rationalize, or convert top reinforcement, top bars over columns, or "top reinf" in a Concept slab.
---

# Simplify Top Rebar (RAM Concept)

Top bars are column bars. The program already puts one group over almost
every column, by count, straight, centred on the column. So do not merge
across columns: keep one group per column per direction and standardize the
count. The trade-off is **number of typical callouts vs tons**.

Three things the senior engineer does by hand to the result (call,
2026-10-09), which the tool now does:

- **Bars at 12 in on centre.** The program spreads a count over the whole
  column strip, so 10 bars in a 14 ft strip come out at an odd 17 in. He
  narrows the extent until the bars land at exactly 12 in (10#9 in a 10 ft
  zone). The aim is a layout that displays well and reads the same at every
  column.
- **Lengths in 5 ft steps** (15, 20, 25, 30 ft), so the slab has a few bar
  lengths instead of 12, 13.5 and 15 ft. He called this the tedious part
  best left to the API.
- **Nothing in the middle strip unless the moment plot asks for it** (see
  "Middle strips" below).

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
python simplify_top_rebar.py run     --work <dir> --typical 10 15 --spacing 9
```

`plan`, `apply` and `verify` run single steps. `run` without `--typical`
applies the newest plan. `report` prints the last round again without a
calc, for example after a new override. `--spacing` (inches, default 12)
sets the bar spacing over every column; `--length-step` (feet, default 5)
the length rounding. Plans written before 2026-10-09 have no spacing and
still spread the count over the strip.

## How groups are made

- A program top bar belongs to a column when the column sits under its
  footprint (2 ft reach). Two bars at one column add up.
- Each column gets the smallest typical count that covers it. A column
  needing more than the largest typical keeps its own count and length.
- A typical callout's length is the longest demand among its columns, in
  whole feet. About an inch over does not earn another foot.
- Each group keeps the program bar's centre along the span and its depth,
  so it sits in the same strip and layer. The two directions are at
  different depths (2636: longitude -2.56 in, latitude -1.56 in).
- **Across the span the bars sit at 12 in on centre: the extent zone width
  is count x 12 in** (`10#9` in a 10 ft zone, `15#9` in 15 ft), placed on
  the column and kept inside the program's strip, so an edge column's bars
  start at the edge. A count that does not fit the strip at 12 in is centred
  on the strip and overhangs a little each side. The program's strip is
  still remembered on the group; it decides which strays belong to it.
- Lengths are the longest demand among a callout's columns, rounded up to
  the next 5 ft. About an inch over does not earn the next step.
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

## Spacing: 12 in, then 9 in

The engineer's rule for a column where the program wants the bars tighter
than 12 in: draw them at 12 in anyway, calc, and read what the program adds
back at that column. Up to about 3 to 5 percent more (one bar on a 10 or 15
bar group) is accepted, top bars especially. More than that, go to 9 in
(`--spacing 9`) rather than odd spacings in between. The tool's `verify`
lists what each column still needs; apply the rule from that list.

## Middle strips

Top bars away from the column line are questioned by every reviewer. Where
the program wants them, in order:

1. **Read the moment plot first.** `Layers > Rule Set Designs > Strength
   Design`, the `Min Mx` and `Min My` plots at the bottom of the list. An
   isolated column shows contours centred on it. Where two columns are
   close, the contours merge into one shape between them: that shared
   negative moment is a real middle strip demand. Contours that stay on the
   columns mean the bar is a strip artefact.
2. **A middle strip only 1 to 2 ft wide** is merged into its neighbour
   (the strip is the problem, not the demand).
3. **Wider than that, with merged contours:** extend the column group's zone
   a little further, at the same 12 in spacing, so one or two more bars
   reach into the middle strip. That is what the engineer did on 2636
   instead of redrawing the strips. The tool's capture does this when the
   bar sits in the group's strip (the count goes up and the zone widens by
   one spacing per bar). It never thins the existing bars to reach it.
4. Only if that fails, a middle strip band of its own, or wider column
   strips lined up across the adjacent spans.

Middle strip top bars are most often legitimate over beams (stiffer
elements, see `../clean-up-ram-concept-t-beams`) and where columns are
tightly spaced.

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
- **A column group's bars are never spread thinner to reach a bar.** A bar
  beside the strip is the next strip's bar. On 2636, widening a group's
  extent while holding its count thinned the column bars and the program
  asked for more every round; one column ran from 15#9 to 25#9. Widening
  by adding bars at the same 12 in spacing (the engineer's "extend the
  region a little further") is the opposite case and is fine.
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
over a column. Say once that the bars are at 12 in on centre (or 9 in
where that was needed) and that lengths are in 5 ft steps.

## Validation

`python -m unittest ram-concept/tests/test_top_column_bars.py`. Live-proven
on 2636 only, one run, before the 12 in zone and 5 ft lengths were added
(2026-10-09; unit-tested, not yet run live). On the first live run check in
the `Top Long` and `Top Lat` plans, with the label set to `$S`, that a
`10#9` group reads 12 in; if Concept divides the zone width by the count
less one, the zone needs `(count - 1) x spacing` instead, and
`ColumnGroup.zone` is the one place to change it.

## Bundled scripts

- `scripts/simplify_top_rebar.py`: CLI against the live API session.
- `scripts/top_columns.py`: column assignment, typical counts, schedules
  (pure, tested).
