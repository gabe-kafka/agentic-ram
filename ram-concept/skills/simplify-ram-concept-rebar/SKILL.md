---
name: simplify-ram-concept-rebar
description: Replace RAM Concept program (yellow) concentrated rebar with a few constructible user (orange) bar groups, one layer at a time (top/bottom x lat/long), and present the groups-vs-tonnage trade-off for the engineer to choose. Use when a user wants to simplify, rationalize, or convert program reinforcement to user-defined reinforcement, cut callout count, or stop chasing program bars by hand.
---

# Simplify RAM Concept Rebar

Turn Concept's program bars into the fewest sensible user bar groups, then
calc until the program adds nothing real. One layer per run:
`bot-long`, `bot-lat`, `top-long`, `top-lat`.

```text
copy model -> API session -> baseline (no user bars, calc)
  -> options table (groups vs tons) -> engineer picks
  -> apply -> calc -> absorb real leftovers -> repeat
  -> report groups, tons, peaking bars for review
```

## Present the trade-off, then let the engineer choose

Always show the options table before applying. Fewer groups means simpler
drawings and placing; more tons means less efficient steel. Program-only
tonnage is the floor. Example (2636 bottom longitude):

| Option | Groups | Tons |
|---|---|---|
| 1 | 100 | 13.0 |
| 3 | 54 | 14.6 |
| 5 | 37 | 18.6 |
| 7 | 26 | 30.4 |

Ask for a target such as "about 50 groups, under 15 tons". Default picks the
closest group count within the tonnage cap.

## Setup

1. The user saves a separately named copy (`File > Save As`) into the job's
   `eng-agent/projects/<job>/ram-concept/models/` and closes the RAM-linked
   window.
2. Start an API GUI on the copy:
   `python ram-concept\scripts\attach-live-concept.py --start-gui --file <copy.cpt>`
3. The Scripting Server window must show **Pause** enabled (running). If the
   user clicks Pause to look around, every call times out until **Resume**.
4. Work folder per layer, in the job folder, e.g.
   `eng-agent/projects/<job>/ram-concept/rebar-simplify/bot-long/`.

## Run

From `scripts/`:

```powershell
python simplify_rebar.py baseline --layer bot-long --work <dir>
python simplify_rebar.py options  --layer bot-long --work <dir> --target-groups 50 --max-tons 15
python simplify_rebar.py run      --layer bot-long --work <dir> --rounds 4
```

`options --option N` picks a table row directly. `apply`, `verify` and
`absorb` run single steps. Each calc takes about 2 minutes; Calc All through
the API raises no dialogs.

`save_file` re-targets the open model, so after `baseline` the API session is
working on `<dir>/base.cpt`, then `round-N.cpt`. The source copy is not
written again.

## Rules learned the hard way

- **Bar depth follows the thinnest slab under the group.** Concept places
  each concentrated group at one elevation: the one that fits the thinnest
  slab anywhere in its footprint (84 of 87 program groups on 2636). A band
  set to 16 in depth that crosses 12 in slab puts bars below the soffit; they
  get no credit ("rebar out of cross section") and the program keeps adding
  bars. Hand-tightening spacing never fixes it. The skill learns the
  thickness -> elevation table from the baseline program bars.
- **Do not split groups at slab steps.** It is correct but multiplies
  callouts; use the thinnest-slab depth instead.
- **Start from a no-user-bar baseline.** Program bars then show the full
  demand. Mixing old user bars with program deficits overstates demand.
- **Absorb leftovers into an existing group; never add small groups.** Pick
  the group that covers the leftover with the least extra steel, tighten one
  menu step if needed, and lengthen 2 ft past the leftover so bars develop.
  Leftovers at bar ends are a length problem, not a spacing problem.
- **Peaking:** demand of 1-2 bars no longer than 5 ft is listed, not chased
  (`peaks.json`, verify output). Engineer judgment, e.g. a bar inside an
  elevator pit, is usually that it is not needed. Tags flag ones near
  openings or off the slab.
- Spacing menu 18/12/9/6/4 in, lengths and extents in whole feet, bar size =
  the layer's dominant program size.
- Demand above #7 at 4 in (about 1.8 in^2/ft) is an engineering flag, not a
  simplification problem: check loads, depth, or a bigger bar.

## Outputs (work folder)

- `base.cpt`: no-user-bar calc; demand source and mesh for depths
- `plan-N.json`: settings, depth rule, groups
- `round-N.cpt`: calc after applying `plan-N`
- `peaks.json`: peaking demand left for review

## Guards

- API copy only. Never run on the RAM-linked model; the published API cannot
  attach to a RAM Manager window anyway.
- Only the chosen layer's user bars are deleted and rewritten.
- Report real leftovers and peaking bars; do not claim "no program bars"
  unless verify shows none.
- Getting the result into the RAM-linked model is not automated yet.

## Validation

`python -m unittest ram-concept/tests/test_simplify_rebar_groups.py`.
Live-proven on 2636 bottom longitude only; check each new layer's first run
in the plan views (`Top Long`, `Top Lat`, `Bot Long`, `Bot Lat`; see
`references/RAM_CONCEPT_GUI_NOTES.md`).

## Bundled scripts

- `scripts/simplify_rebar.py`: CLI against the live API session.
- `scripts/rebar_groups.py`: grouping, options, peaking, absorb (pure, tested).
- `scripts/cpt_reader.py`: read-only `.cpt` reader: bars, mesh thickness,
  openings, depth rule.
