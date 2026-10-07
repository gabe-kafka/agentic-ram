# Slab Reinforcement Optimization (RAM Concept): Architecture

Read this first when picking up slab rebar work in a new session or on
another machine. It is the durable record of how the pieces fit, which rules
are settled, and what is not built yet. Skill `SKILL.md` files hold the
run-level detail; job numbers and results live in `eng-agent`.

Last updated 2026-10-05, after the first full pass on one transfer slab
(job 2636) and the senior engineer's review of it. Everything here is
proven on that one model only, and the review changes several rules.

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

## Stack

Four pieces, each with one job. Adopted 2026-10-02.

| Piece | Where | Holds |
|---|---|---|
| `agentic-ram` | GitHub, private | The tools and rules. The same for every project. No job files. |
| `eng-agent` | GitHub, private | One folder per job: meetings, decisions, actions, and the rebar record (`STATUS.md`, `decisions.json`, plans, layout images). No models. |
| Production folder | Office server (S:) | The RAM model `.rss` and its `Archive`. The authoritative engineering file. |
| Work PC | Local | RAM Concept and RAM Structural System, and the large working copies of the model. Never in git. |

The two repos stay separate on purpose: the tools may be published one day,
and `eng-agent` holds client meeting records. Do not move job files into
`agentic-ram`. Model files never go in either repo: check what is staged
before every commit (two Concept snapshots were committed here by a blanket
`git add` on 2026-10-05 and had to be removed).

Anything that calculates needs the work PC. From any other machine the
status, decisions, plans and layout images can be read, and rules or code
can be changed.

## Starting a new project

1. Make the job folder in `eng-agent/projects/<job>/` and copy
   `REBAR_STATUS_TEMPLATE.md` (beside this file) to
   `ram-concept/rebar-simplify/STATUS.md`. Add a `.gitignore` there with
   `*.cpt`, `*.cpt.*` and `.working`.
2. With RAM Manager closed, take the Concept file out of the production
   `.rss` (the member ending `.cpt<story>E`) or have the engineer
   `File > Save As` a copy, and start an API session on that copy.
3. Run the pipeline below. The engineer picks the row at each options table
   and states any overrides.
4. Review from `bar_plan.py` images or in Concept.
5. Sync into the production model every 2 hours.
6. End of every session: update `STATUS.md`, then commit and push both
   repos.

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
| Top general bands | Program top bars over no column, banded by spacing after the column groups are in | top tool: `band-options`, `bands`, `run-bands` | runs, but **contradicts the 2026-10-05 review** (top bars in middle strips); see Reviewer rules |
| Peaking | 2 bars or fewer and 5 ft or shorter: captured by the group beside it, else listed | `rg.is_peak`, `rg.absorb_peaks`, `tc.capture` | capture is partial, see Gaps |
| Waived at a mat notch | Bar sits only on a "notch only" mat boundary: not required | `check-ram-concept-slab-transitions` + `sr.split_waived` | script proven; no SKILL.md |
| Real mat transition | Band crossing a "real" mat boundary is drawn as two sets anchored at the boundary | bottom tool `apply` | proven |
| Beam: strips | Spans along beams set as T or L beams first | `set-ram-concept-beam-strips` | proven (T only) |
| Beam: top, runs through column | No top bar called out; recorded as an override | `clean-up-ram-concept-t-beams` | proven |
| Beam: top, ends at column | Column keeps its own count and length | same | proven |
| Beam: bottom, mid-span | The beam's own bars by count; mid-span leftovers add to the count | same + bottom tool `absorb` | runs, but bar size, layers, length and cover are to change per the review |
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

## Reviewer rules (senior review of the first pass, 2026-10-05)

The first pass was reviewed sheet by sheet. The reviewer agreed with where
program bars were left out, and asked for the layout to be refined. These
rules outrank what the tools do today; the Gaps list says what is not built.

**Design strips come first.** Most odd bars are strip problems, not demand.

- A sliver middle strip makes the program add bars, because a mat bar may
  not physically fall inside the section. Fix the strip: a boundary strip
  set to manual, or two adjacent strips merged into one.
- Strip width stays on `code slab`, never full width.
- Add the strips at column faces where they are missing.
- At a step-down, segment the strip so each part is checked at its depth. A
  middle strip partly over a lower slab is checked entirely at the lower
  depth; pull it back to the face with a boundary segment.
- A column strip split by a step beside a column is still one column strip:
  add the two parts' demands and capacities and reinforce it as one.
- **Do not delete the strips over exterior walls.** Bars then show as needed
  beside the wall and nothing shows where the strip is missing. (The first
  pass deleted them; the reviewer flagged the result.)
- An end support set as free when it is not a true cantilever puts top bars
  in the middle strip; setting it to none usually clears them.

**Where bars go.**

- **Avoid top bars in the middle strip and at mid-span.** They are sometimes
  needed where two columns are close and share the negative moment, but the
  final reviewer questions every one. Widen the column strips to line up
  across adjacent spans instead.
- Bottom bars merge wherever needed. Top bars are merged with care, to stay
  out of middle strips.
- Additional bottom bars are needed only at column strips in most cases.
  That means one group per column strip, not one group across several
  (clarified 2026-10-06).
- Bar lengths are kept to similar round values (a bar was stretched to
  exactly 25 ft).
- Reinforce locally at corners and over walls, not one bar segment across a
  whole section.
- A callout is normally at most **30 ft** long. Do not stretch one past
  that to cover a bar needed in a single bay.
- Spacing looser where capacity is about double the demand: the review
  took bands from 9 in to 18 in and removed bands at 6 in.

**How bars are drawn**, because documentation copies the model's linework.

- Bars crossing a step-down: the anchored pair only at the step itself;
  full-length bars elsewhere.
- A bar ending at a slab edge or a large opening has that end `Anchored`.
  No split at a small bump-in.
- At a large opening, split into separate callouts each side, anchored or
  hooked at the face.

**Leftover program bars.**

- The end product is a design run with program reinforcement switched off:
  the check that the user bars alone pass. That removes every program bar.
  The setting is `Criteria > Calc Options`, `Check capacity of user
  reinforcement without designing` (named 2026-10-06).
- Until then small obvious ones are ignored. One-bar conditions: note the
  location and check demand without program bars; the slab may be 1% over.
- The reviewer's own method: remove bars that look excessive, rerun, and see
  what comes back.

**Beams** follow the office concrete quick reference (minimum and maximum
bars in one layer by beam width; see `RAM_CONCEPT_GUI_NOTES.md`).

- Top: the minimum number for the beam width over the full beam length, even
  where the design needs none; they carry the stirrups.
- Bottom: never more than the single-layer maximum. Go up a bar size (#7 to
  #9) and add a second layer if needed. Extend to the beam ends, `Anchored`.
- Beam bars on `Bottom Cover` 2 in, not `Absolute`.
- Stirrups: #4 at 3 in to start; end, middle, end zones later.

**One-way shear** has its own office method (two models, stirrups only
where a full-width copy still needs them; see `RAM_CONCEPT_GUI_NOTES.md`).
Nothing here automates it.

**Punching.**

- Delete the punching checks at columns on beams.
- Read status from Concept's own tables, not from whether rails exist.

## Office standards for additional reinforcement (team meeting, 2026-10-06)

Set by the senior reviewer and the final reviewer on 2026-10-05, presented
to the team on 2026-10-06 and agreed. Source: eng-agent
`meeting-transcripts/26-10-06 - Team meeting additional reinforcement
process.txt`. These are first-pass standards. The aim is fewer calc
iterations and simpler drawings, accepting heavier steel.

**Targets.**

- Additional bars total **20 to 25 percent of the mat tonnage**. Transfer
  slabs have been running 30 to 35 percent. Usually that means the mat bar
  goes up one size. A bid note at 75 percent can then say "allow X percent
  additional bars" without a separate check. A before-and-after tonnage
  case study on 2636 is planned once its additional reinforcement is done.
- About **four to five calc iterations** for the whole additional
  reinforcement pass, on an uninterrupted day. A calc is 5 to 10 minutes on
  these models. Count them.
- One slab option designed fully; see `RAM_CONCEPT_SLAB_OPTIONS.md`.

**First pass, by hand.** Turn every program bar into a user bar while they
are all still program bars, and read the slab from the bar label (the
concentrated bar description format: `$S` spacing, `$Q` quantity, `$B`
size; see `RAM_CONCEPT_GUI_NOTES.md`, "Bar description labels").

| Bars | Read | Rule |
|---|---|---|
| Bottom | `$S` | One spacing per region, the average or the worst case, applied across the whole region. No 12 to 18 in transition inside a region: where the mat is at 12 in, the additional bars are at 12 in over the whole area |
| Top over columns | `$Q` | Two to three count conditions for the slab (by eye or an Excel average), outliers left out; the pattern copied to every column in the region, for example 10#9 at the same length and spacing at every column. Expect 50 to 75 percent of columns settled in that batch |
| Top over walls | `$S` | One spacing per wall; heavily loaded walls run 9 to 12 in |
| Beams | tables | Top bars = the width minimum + 1; bottom bars = the single-layer maximum - 1, more layers if needed; stirrups 3 in at the ends, 9 in in the middle; add legs before changing spacing; widen the beam when legs stop helping. One pattern for all beams of a width. See `RAM_CONCEPT_GUI_NOTES.md`, "Beam reinforcement" |

Then calc, fix the problem areas specifically, calc again.

**What this means for the tools here.**

- The bottom tool's bands by spacing fit the standard when one band covers
  a region. Prefer the tighter spacing over the whole region to splitting
  it into 12 and 18 in bands. The groups-versus-tons table stays; the
  standard favours fewer groups.
- The top tool's typical counts are the standard's two to three conditions.
- Not built: the mat percentage (additional user bar tons over mat tons) in
  the status report, and a mat-size what-if (the same slab with the mat one
  size up: mat tons plus additional tons). The engineer offered this at the
  meeting as the useful thing to code.
- Slab one-way shear legs: one leg per mat bar in the strip width (10 ft
  strip, 10 legs), the reviewer's rule, confirmed by the engineer the same
  afternoon. `place_stirrups.py --mat` defaults to 12.
- Next office topics: punching (a better way than an assumed opening at
  every column) and one-way shear stirrups. A colleague's tip: export
  Concept's SSR table as the basis for the stud rail spreadsheet; it goes
  by coordinates and gives rail lengths.

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
  design-ram-concept-stud-rails/      draft: assumed openings, search radius, punching status
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
  (or headless, `-apiServer`) on a separately named copy. The Scripting Server window's **Pause** blocks
  every API call; the GUI is only usable while paused. The agent may Pause
  and Resume it without asking (standing permission from the user), and must
  leave it paused when handing back for review.
- Resume and Pause through UI Automation `InvokePattern`, then confirm with
  an API call. Mouse clicks miss.
- Work that needs no GUI (bars, stirrup regions, bar materials, calc
  options, calc, save) runs headless: `Concept.start_concept(headless=True,
  log_file_path=...)`, then `open_file` on the copy and `shut_down` at the
  end. Nothing appears on the engineer's screen. Proven on 2636, 2026-10-07.
- `calc_all` answers SUCCESS even when the calc stopped on an analysis
  error. Always start with a log file and look for a line ending
  `ANALYSIS ERROR:` (not `OPTIONAL ANALYSIS ERROR IGNORED:`). Concept writes
  the log's tail as it exits. A stopped calc leaves no program reinforcement
  and no detailed stirrups in the saved file, which reads like a clean
  result if only the program bars are counted.
- **Merging two engineers' copies**: diff every table of both against the
  save they branch from (ignore the UID and sibling-link columns). Strips
  cannot be written, so the base is the copy with the strip changes, and the
  other engineer's change is replayed onto it through the API. Prove the
  result table by table from the saved file.
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

1. **Top general bands contradict the review.** The tool bands every top
   bar away from a column, including in middle strips, and goes past the
   knee for fewer bands. The review wants almost no top bars in middle
   strips. Rework: fix strips first, widen column strips, let the column
   groups take what falls in them, and band only what is left at walls and
   corners, locally.
2. **Zone rule** (above), using `SpanSegmentStrip`. It is the mechanism for
   item 1 and for bottom midspan. Stray singles are decided by it too.
3. **Callout length cap of 30 ft.** `max_length` is 40 ft and absorbing
   stretches groups further.
4. **Step-downs.** `apply` splits a whole band into two anchored sets at a
   real transition. Wanted: the anchored pair only at the step, continuous
   bars in the main slab.
5. **Ends and openings.** Bars are drawn straight-ended. Wanted: `Anchored`
   at slab edges and large openings, and split callouts around openings.
6. **Beam bars.** The tool copies the program's count in the program's bar
   size (2636: 17#7 in a 20 in web, whose single-layer maximum is 7#7 or
   6#9), on `Absolute` elevation, mid-span length only, no top bars, and
   leaves beam-end bars as the engineer's call. Wanted: the quick reference
   rules above and the office first-pass rules (top minimum + 1, bottom
   single-layer maximum - 1, stirrups 3 in ends and 9 in middle). Extending the bottom bars to the ends, anchored, replaces
   the beam-end class.
7. **Final check with program reinforcement off.** Not found in the API or
   driven through the GUI yet; today the tools only count leftover program
   bars.
8. **Exterior wall strips.** The bottom skill says to settle strips drawn
   along walls before simplifying; it must not suggest deleting them.
9. **Two-way punching (stud rails).** `skills/design-ram-concept-stud-rails`
   took 2636 to all punching checks passing: openings by API, radius and
   table export by GUI, status from the exported table. The schedule is
   `skills/schedule-ram-concept-stud-rails` (rows, proposed types, the
   office workbook); setting rails to `User` is not built. One-way shear
   is `skills/design-ram-concept-one-way-shear`. The five core workflows
   are indexed in `ram-concept/AGENTS.md`.
10. **Transition skill**: `transition_check.py` works and its verdicts are
    wired into both tools, but there is no `SKILL.md` and the yellow notch
    bars still show in Concept.
11. **One driver for all four layers** with one work folder and one newest
    model, replacing the per-layer folders.
12. **L beams**: strip setup and checker only proven for T beams.
13. **Callout format in the model**: Concept still prints `(10)#9x15T`.
14. Pre-existing failing test:
    `test_attach_live_concept.test_parses_rss_launched_cpt_path`.
15. **Mat percentage and mat-size what-if.** The office target is
    additional bars at 20 to 25 percent of the mat tonnage. Nothing here
    reports that ratio or compares the slab with the mat one size up.

## Picking this up elsewhere

1. Clone `agentic-ram` and `eng-agent` (both private under the same GitHub
   account), check out the working branches, read `AGENTS.md`,
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
