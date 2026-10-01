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
- Temporary one-way shear: user bars, full-width strips, do not save.
- Warnings list line-load numbers are one-based; saved indices are zero-based.

## Live API attach

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
