# Slab Reinforcement Optimization (RAM Concept): Architecture

Read this first when picking up slab rebar work in a new session or on
another machine. It is the durable record of how the pieces fit, which rules
are settled, and what is not built yet. Skill `SKILL.md` files hold the
run-level detail; job numbers and results live in `eng-agent`.

Last updated 2026-10-02, after the first full pass on one transfer slab
(job 2636). Everything here is proven on that one model only.

## Goal

Turn RAM Concept's program (yellow) concentrated rebar into the fewest
constructible user (orange) bar groups, calc until the program adds nothing
real, and hand the engineer a layout they can read by strip.

Principles, in the engineer's words:

- **Fewest groups; less efficient steel is acceptable.** Always show the
  groups-vs-tons table and let the engineer pick the row.
- **One callout per zone, at most.** A zone is a column strip or a middle
  strip, over the column line (top bars) or at midspan (bottom bars). Two
  bar sections in one zone is wrong unless a stated exception needs it.
- **Capture stray single bars** into the group beside them wherever that can
  be done. A yellow 1#9 sitting on an orange 4#9 must become 5#9.
- **Overrides are engineering decisions**, recorded with a reason and shown
  in every report with the count the program wanted.
- **The source model is never written.** Work on an API copy; results reach
  the production model by an archive swap the engineer approves.

## Pipeline

```text
0  strips        design spans settled; spans along beams set as T or L beams
1  transitions   mats-only copy -> Span Section Analysis export -> verdicts.json
2  bottom        bot-long, bot-lat: baseline -> options -> pick -> run
3  top columns   base (no user top bars) -> options -> typical counts -> run
4  top general   band-options -> bands -> run-bands (captures leftovers)
5  beams         t_beam_cleanup.py status -> overrides -> nothing open
6  review        bar_plan.py images, Concept plans, engineer review
7  sync          swap the finished .cpt into a copy of the .rss, archive, replace
```

Steps 2 to 4 each change demand elsewhere. After any of them, rerun `status`
(step 5) and check the other layers' leftovers from the newest saved model
before calling a layer finished.

## Classes of bars

Each class has its own rule. A program bar is assigned to exactly one class.

| Class | Rule | Lives in | State |
|---|---|---|---|
| Bottom bands | Bands by spacing; greedy merge under a budget; knee row suggested | `simplify-ram-concept-rebar` (`rebar_groups.py`) | proven |
| Top column groups | One group by count per column per direction; typical counts (e.g. 10 and 15) plus own counts | `simplify-ram-concept-top-rebar` (`top_columns.py`) | proven, locked in |
| Top general bands | Program top bars over no column, banded by spacing after the column groups are in | top tool: `band-options`, `bands`, `run-bands` | proven; zone rule not applied yet |
| Peaking | 2 bars or fewer and 5 ft or shorter: captured by the group beside it, else listed | `rg.is_peak`, `rg.absorb_peaks`, `tc.capture` | capture is partial, see Gaps |
| Waived at a mat notch | Bar sits only on a "notch only" mat boundary: not required | `check-ram-concept-slab-transitions` + `sr.split_waived` | script proven; no SKILL.md |
| Real mat transition | Band crossing a "real" mat boundary is drawn as two sets anchored at the boundary | bottom tool `apply` | proven |
| Beam: strips | Spans along beams set as T or L beams first | `set-ram-concept-beam-strips` | proven (T only) |
| Beam: top, runs through column | No top bar called out; recorded as an override | `clean-up-ram-concept-t-beams` | proven |
| Beam: top, ends at column | Column keeps its own count and length | same | proven |
| Beam: bottom, mid-span | The beam's own bars by count; mid-span leftovers add to the count | same + bottom tool `absorb` | proven |
| Beam: bottom, at beam end | Engineer's call; never added automatically | same | proven |
| Override | "No bar called out here", with reason, source and date | `beam_rules.py`, `decisions.json` | proven |

## The zone rule (target architecture, not built)

Today the bands are grouped by cost: neighbours merge when the added steel
is under a budget. That ignores how an engineer reads a plan. The target is
grouping by zone.

- Concept's own strips are in the saved `.cpt`: table `SpanSegmentStrip`
  (`StripType`, `Point0`, `Point1`, left and right boundaries, parent
  `SpanSegment`), 664 rows on 2636. Use these, not a guessed L/4.
- A zone = one strip, at the support (top) or at midspan (bottom).
- Column strip over a column: only the count group. A program bar inside
  that strip adds to the count.
- Middle strip: one band, at the tightest spacing needed in that strip.
- A band that runs through a column strip is cut out of it, and the column
  count goes up to cover what the band was carrying there.
- A wide band may still cover several middle strips with one callout; the
  rule limits callouts per zone, it does not force one band per strip.

Until this is built, two stopgaps exist: `tc.capture` (a column group takes
bars inside its own extent) and `merge-bands` (neighbouring bands up to two
spacing steps apart merge when it costs under 500 lb).

**Never widen a column group's extent to reach a bar.** A bar beside the
extent is the next strip's bar. Widening thins the column bars where they
are needed and the program asks for more every round (2636: a 15#9 group
ran to 25#9 in four rounds before this was caught).

## Where things live

Repo `agentic-ram` (reusable, checked in):

```text
ram-concept/skills/
  simplify-ram-concept-rebar/         engine: live session, bands, reader, status page
    scripts/simplify_rebar.py           baseline | options | apply | verify | absorb | run
    scripts/rebar_groups.py             pure grouping rules (tested)
    scripts/cpt_reader.py               read-only .cpt reader (SQLite)
    scripts/bar_plan.py                 draw one layer's layout to PNG, no Concept needed
    scripts/dashboard.py, .html         status page: Working / Ready for human review
  simplify-ram-concept-bottom-rebar/  bottom workflow (doc only; uses the engine)
  simplify-ram-concept-top-rebar/     top columns + general bands
    scripts/simplify_top_rebar.py       options | plan | run | band-options | bands |
                                        run-bands | merge-bands | report
    scripts/top_columns.py              pure column rules (tested)
  clean-up-ram-concept-t-beams/       all beam conditions + override record
    scripts/t_beam_cleanup.py           status | override
    scripts/beam_rules.py               pure beam rules and decisions (tested)
  set-ram-concept-beam-strips/        T or L beam strip setup (GUI-driven)
  check-ram-concept-slab-transitions/ transition_check.py (no SKILL.md yet)
ram-concept/scripts/
  drive-window-without-display.ps1    post input and capture when the PC is locked
  stitch-concept-pdf.py               stitch Export Window to PDF pages into one image
ram-structural-system/scripts/
  swap-concept-into-rss.py            build an .rss copy with the Concept member replaced
ram-concept/tests/                    test_simplify_rebar_groups, test_top_column_bars,
                                      test_t_beam_cleanup, test_beam_spans
.claude/skills/                       /bot-reinf /top-reinf /t-beam /t-beam-cleanup /calc-all
.agents/skills/                       discovery shims for the canonical skills
```

Job folder (in `eng-agent`, not this repo):

```text
eng-agent/projects/<job>/ram-concept/rebar-simplify/
  STATUS.md             where the job stands: newest model, picks, open items
  decisions.json        overrides: layer, x, y, reach, reason, source, date
  <layer work folder>/  base.cpt, plan-N.json, round-N.cpt, peaks.json, waived.json
  <top work folder>/    base.cpt, columns-plan-N.json, round-N.cpt, plans/*.png
  transitions/          mats-only.cpt, exported table, verdicts.json
```

Two facts about work folders that cause confusion:

- **The newest model is wherever the last run saved it.** `save_file`
  retargets the open API model, so a bottom run leaves the newest state in
  the bottom folder and a top run in the top folder. `STATUS.md` names it.
  `simplify_rebar.py absorb --from-model <cpt>` reads leftovers from it.
- **Plan numbers and round numbers can skip.** `round-N.cpt` is the calc of
  `plan-N`. A plan with no round was written but not applied.

## Code shape

The split that matters for reuse, and for a future tool aimed at less
technical users:

- **Pure rules** (`rebar_groups.py`, `top_columns.py`, `beam_rules.py`):
  geometry and bookkeeping, no Concept, fully unit-tested. New rules go here.
- **Reader** (`cpt_reader.py`): read-only SQLite access to a saved `.cpt`.
  Units are 0.1 mm (FT = 3048, IN = 254).
- **Drivers** (`simplify_rebar.py`, `simplify_top_rebar.py`): the only code
  that talks to the live API. apply, calc, save, then read the saved file.
- **Conditions as modules.** Beam handling was pulled out of the top and
  bottom tools into one skill that both import. Do the same for the next
  cross-cutting condition (zones, transitions) rather than growing the
  drivers.

A published tool would wrap this as: read model -> classify every program
bar into a class and zone -> show the options table -> apply -> verify ->
report, with `decisions.json` as the engineer's record. The pieces exist;
the missing part is the zone classifier and one driver for all four layers.

## Live session rules

- Concept's API only works on a session started with `-apiServerWithGui`
  on a separately named copy. The Scripting Server window's **Pause** blocks
  every API call; the GUI is only usable while paused. The agent may Pause
  and Resume it without asking (standing permission from the user), and must
  leave it paused when handing back for review.
- Resume and Pause through UI Automation `InvokePattern`, then confirm with
  an API call. Mouse clicks miss.
- While a run is active the user must keep hands off Concept. Each calc is
  about 2 minutes.
- Design strips are not in the API. Strip edits are GUI-driven and proved
  from the saved file.
- **Locked or disconnected session** (state `Disc` in `quser`): screen
  capture and keyboard or mouse injection fail, and Concept's plan canvas
  stops redrawing. Use `bar_plan.py` for layouts. For Concept's own plan,
  `Report > Export Window to PDF` driven by
  `drive-window-without-display.ps1`, then `stitch-concept-pdf.py`.
- Never send keys before focusing Concept; an Escape sent to the agent's own
  window cancels the running command.

## Getting results into the RAM model

The `.rss` is a zip; the elevated-slab Concept file is the member ending
`.cpt<story>E` (`...M` is the mat). Route, proven and adopted on 2636:

1. RAM Manager closed (it holds a working copy and a `.usr` lock).
2. `swap-concept-into-rss.py <production.rss> <finished.cpt> <new.rss> <suffix>`
   builds a new archive; the source is never written.
3. Copy the production `.rss` into its `Archive` folder with a timestamp.
4. Put the new `.rss` in place and compare hashes.

Protocol set by the user: **save and sync every 2 hours** of Concept work,
and say at every report whether results are in the production model or only
in the job folder. Overwriting RAM's working `.cpt` directly is not
permitted.

## How to present results

- Callouts: by count `15#7 x 26'`; by spacing `#7 @12"`. Never Concept's
  `(15)#9x13T` form in chat or reports.
- Options: the whole groups-vs-tons table, knee row marked, then a
  recommendation. The engineer picks.
- Per layer: groups, tons, real leftovers (must be 0), peaking left with
  locations, overrides with the program's count.
- Keep replies short: the next action, in a few bullets.

## Gaps, in the order to take them

1. **Zone rule** (above). Rebuild the top general bands by strip, then apply
   the same rule to bottom midspan. Biggest open item.
2. **Stray singles not yet captured**: bars just outside a column group's
   extent and bars inside a band. The zone rule decides both.
3. **Transition skill**: `transition_check.py` works and its verdicts are
   wired into both tools, but there is no `SKILL.md`, the yellow notch bars
   still show in Concept, and the senior reviewer has not seen the verdicts.
4. **One driver for all four layers** with one work folder and one newest
   model, replacing the per-layer folders.
5. **Beam bar size**: counts by #7 do not fit one layer in a 20 in web;
   the tool does not propose a larger bar.
6. **L beams**: strip setup and checker only proven for T beams.
7. **Callout format in the model**: Concept still prints `(10)#9x15T`;
   the callout format strings on each bar are not set by the tools.
8. Pre-existing failing test:
   `test_attach_live_concept.test_parses_rss_launched_cpt_path`.

## Picking this up elsewhere

1. Clone `agentic-ram`, check out the working branch, read `AGENTS.md`,
   `ram-concept/AGENTS.md`, then this file.
2. `python -m unittest discover -s ram-concept/tests` (one known failure,
   item 8 above). `bar_plan.py` needs matplotlib; the PDF stitcher needs
   pymupdf and Pillow.
3. Read the job's `STATUS.md` in `eng-agent` for the newest model and open
   items. Job models are not in git; they are on the machine that ran them
   and, after a sync, inside the production `.rss`.
4. To continue on a model: extract or copy the Concept file, start an API
   session on the copy, and follow the pipeline from the first step whose
   output is missing.
5. Claude Code's local memory does not travel between machines. Anything
   that must persist goes here, in a skill, or in the job's `STATUS.md`.
