# RAM Concept Workspace

These instructions apply to all work under `ram-concept/`.

## Current status

RAM Concept support remains limited and guard-driven. Direct mutation of an
existing Concept design model is not proven. Guide the live GUI from
`references/RAM_CONCEPT_GUI_NOTES.md` and
`references/RAM_CONCEPT_SLAB_OPTIONS.md`. The proven
`skills/repair-ram-concept-slab-edge` workflow creates, meshes, reopens, and
visually validates a separate geometry-only proof model from read-only RSS
slab/wall geometry. Read-only inspection of saved punching-check inputs and
generated SSR geometry is available through `scripts/inspect-punching-checks.py`.
Live GUI attachment uses `skills/attach-ram-concept-api` and the official
localhost API only.

## Core slab design workflows

The engineer's five, in the order they are done on a slab, plus the plan
markup that hands the stud rails to the documentation team. Each is one
skill; read its `SKILL.md` before acting. Design strips come first (beam
strips: `skills/set-ram-concept-beam-strips`), and every step ends with the
newest calculated model synced into the production RAM model.

| # | Workflow | Skill | What the engineer decides |
|---|---|---|---|
| 1 | Bottom bending reinforcement | `skills/simplify-ram-concept-bottom-rebar` | the row of the groups-against-tons table |
| 2 | Top bending reinforcement | `skills/simplify-ram-concept-top-rebar` | typical column counts; the band row |
| 3 | Two-way punching reinforcement (stud rails, SSR) | `skills/design-ram-concept-stud-rails` | moving an assumed opening back, against the floor plan above |
| 4 | Shear stud schedule | `skills/schedule-ram-concept-stud-rails` | the types |
| 5 | One-way shear reinforcement | `skills/design-ram-concept-one-way-shear` | the marked-up PDF; the SVG reading goes back to him before any bar is drawn |
| 6 | SSR plan markup for the documentation team | `skills/markup-ram-concept-ssr-plan` | he plots S101D himself; the tagged PDF is checked in Bluebeam |

- 1 and 2 share `skills/simplify-ram-concept-rebar` (the engine) and
  `skills/clean-up-ram-concept-t-beams` (beam conditions).
- 5 needs 1 and 2 done (one-way concrete shear capacity depends on the
  flexural steel) and 3 passing (stud rail columns are set aside in 5).
- 5 checks the stud rail columns through the rails and rarely changes them;
  if it does, redo 4.
- Not built anywhere yet: rails to `User` after 4, the final check with
  program reinforcement off, beam reinforcement by the quick reference.

## Slab reinforcement optimization

For any work on simplifying, grouping or reviewing slab rebar, read
`references/SLAB_REBAR_OPTIMIZATION.md` first. It is the architecture and
handoff record: the pipeline, the bar classes and their rules, the
one-callout-per-zone rule, what is not built yet, and how to pick the work
up on another machine. Then read the job's
`eng-agent/projects/<job>/ram-concept/rebar-simplify/STATUS.md`.

Standing rules from the engineer, which apply in every session:

- Fewest bar groups; show the groups-vs-tons table and let the engineer pick.
- Office first-pass standards (team meeting 2026-10-06): additional bars at
  20 to 25 percent of the mat tonnage, one spacing per region, two to three
  column count conditions, beam top bars minimum + 1 and bottom bars
  single-layer maximum - 1, stirrups 3 in ends and 9 in middle. See
  `references/SLAB_REBAR_OPTIMIZATION.md`, "Office standards".
- One callout per zone at most (column strip or middle strip, over the
  column line or at midspan).
- Capture stray single program bars into the user group beside them.
- Callouts as `15#7 x 26'` (by count) and `#7 @12"` (by spacing).
- The agent may Pause and Resume the Scripting Server without asking, and
  leaves it paused when handing back for review.
- Save and sync into the production RAM model every 2 hours of Concept work;
  say at every report where the results live.
- **Never let the engineer pick up in an outdated model.** Sync the newest
  calculated Concept file into the production RAM model at every stopping
  point, not only at the 2-hour mark. If a sync cannot be done, say so in
  the first line, name the newest file, and say what the production model
  is missing. When a session resumes, first compare the model that is open
  with the newest saved file (hash the Concept member inside the `.rss`)
  and report the result before anything else. A Concept window launched
  from RAM Manager has no API; work continues only after it is closed and
  an API session is started on a copy.

## Hand-guide GUI lessons

- Read `references/RAM_CONCEPT_GUI_NOTES.md` before walking a live Concept
  window. Checkpoint with `File > Save As` first.
- `Calc All` and `Generate Mesh` commit edits; Undo will not restore the
  prior state.
- Do not `Rebuild Load Combos` without reviewer direction.
- Concept includes slab-mesh self-weight. Do not duplicate it as an area load.
- Transfer-slab SSR: `Criteria > Materials > SSR Systems > Stud Spacing` =
  `Auto Calc`, not default `Code Max`.
- `No cutoff section`: raise search radius in about 2 ft steps; about 12 ft is
  a practical troubleshooting ceiling. Check nearby openings and the slab
  edge first.
- After a beam is added, Concept may still show a punching fail; office uses a
  separate final punching check.
- One-way shear: the office method screens on a separately saved copy with
  every design strip at full width, then puts stirrups in the real model:
  6 in along the span, one leg per mat bar across the column strip.
  See `references/RAM_CONCEPT_GUI_NOTES.md`, "One-way shear in a two-way
  slab", and `skills/design-ram-concept-one-way-shear`. Never set the real
  model's strips to full width. Show the engineer the SVG reading of his
  markup before drawing any stirrup.
- With the engineer at the PC, or a second Concept open, do not send real
  keystrokes or mouse clicks; use window messages addressed to the API
  session's own windows.
- Warnings list line-load numbers are one-based; saved indices are zero-based.

## Live API attach

- **Design work goes through a live API session** (engineer's rule,
  2026-10-07): start `scripts/start-ram-concept-api.cmd --file <model.cpt>
  --port <N>` so the engineer sees the same window, make the changes through
  the API, calc there, save into the job folder, and swap the saved file into
  the production `.rss` at stopping points. Headless Concept is for builds
  and checks the engineer does not need to watch (screening copies, replays,
  batch verification), not for the back-and-forth of a design.
- Use `scripts/attach-live-concept.py` to probe `Concept.exe` and attach when
  the process was started with `-apiServer` or `-apiServerWithGui`.
- Wrap the already-open model. Do not call `open_file`, `save_file`,
  `close_model`, `shut_down`, mesh, calc, or unit resets on an attached
  session, except on a separately named API copy started for
  `skills/simplify-ram-concept-rebar`, which calcs and saves into its job
  work folder.
- The Scripting Server's Pause button blocks every API call (timeouts) until
  Resume is clicked.
- A Start-menu Concept window has no API. Do not kill it. Ask the user to
  close it, then start `scripts/start-ram-concept-api.cmd`.
- Design strips and `Consider as Post-Tensioned` are not in the published
  API. Change those in the Concept UI.

## Safety

- Preserve every source Concept model. Work from a separately named copy or
  checkpoint.
- Begin with documented UI workflows, screenshots, exported reports, and
  controlled one-change comparisons.
- Do not apply RAM Structural System `.rss` record layouts or archive-editing
  scripts to Concept files.
- Do not assume RAM DataAccess interfaces or RAM Modeler hotkeys work in RAM
  Concept.
- Do not perform broad COM discovery or speculative mutation against a live
  Concept model.
- Treat file formats and undocumented fields as version-specific until they
  have been isolated, reopened successfully, and validated in RAM Concept.

## Punching diagnostics

- Work from a hashed, separately named saved Concept checkpoint. If the
  checkpoint is embedded in an RSS archive, keep archive extraction in the RAM
  Structural System workflow and inspect only the extracted Concept copy here.
- Start with `scripts/inspect-punching-checks.py` to correlate `PunchCheck`
  inputs, generated `SsrSet` geometry, rail reach, and maximum search radius.
- Verify internal-to-displayed unit conversion through the official Concept API
  or UI. Do not infer units from raw values alone.
- Compare each check's search circle with nearby slab-opening and slab-boundary
  edges before recommending a larger radius. A distant opening or edge can
  create an inappropriate critical section.
- Do not classify a check as passed or failed solely because it lacks a
  generated `SsrSet`. The saved checkpoint does not distinguish “SSR not
  required” from “SSR design failed before layout generation.”
- Use an exported Warnings and Errors list or Punching Audit report for the
  exact failing-check list and failure message. Preserve the export beside the
  project checkpoint inspection.

## Tutorial capture

For each tutorial step, record:

- RAM Concept version
- model units
- design code and criteria
- slab system and geometry assumptions
- loads and combinations
- mesh settings
- analysis/design command
- expected visual or report result
- saved checkpoint name

## Folder use

Use these folders only for generic, reusable RAM Concept work:

- `tutorials/`: reproducible lesson sequences and checkpoints
- `scripts/`: Concept-only automation and inspection tools
- `skills/`: draft Concept workflows before promotion
- `references/`: product documentation and verified technical notes
- `tests/`: automated tests and controlled fixtures
- `models/`: local source/checkpoint models; ignored by Git
- `out/`: generated reports, screenshots, diffs, and experiments; ignored by Git

Put job-specific models, transcripts, screenshots, audits, tutorials, and
generated output under the matching `eng-agent` project's `ram-concept/`
folder.

## Promotion rule

A Concept workflow becomes a proven repository skill only after it has explicit
guards, preserves the source model, passes a controlled test, reopens
successfully, and is visually or report-validated in RAM Concept.
