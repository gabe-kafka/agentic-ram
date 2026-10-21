# RAM Structural System Workspace

These instructions apply to all work under `ram-structural-system/`.

## Product boundary

RAM Structural System owns RAM Manager, RAM Modeler, RAM Frame, RAM Concrete,
RAM Foundation, `.rss` archives, DataAccess integration, and the tools in
`scripts/`, `skills/`, `references/`, and `tests/`.

When the user is at the live GUI, read the matching `references/` notes and
guide the next command path. Do not invent clicks. Keep job numbers in
`eng-agent`.

Never apply these RSS archive assumptions, record layouts, API calls, or
hotkeys to a RAM Concept model.

Keep reusable tools and verified notes here. Put job-specific RSS models,
inspection archives, screenshots, candidates, and output under
the matching `eng-agent` project's `ram-structural-system/` folder.

## Proven tools

- `scripts/open-blank-ram.ps1`
- `scripts/open-ram-model.ps1`
- `scripts/test-ram-api-hook.ps1`
- `scripts/ram-modeler-hotkeys.ahk`
- `scripts/inspect-ram-rss.ps1`
- `scripts/frame_drift_compare.py`: RAM Frame Drift PDFs side by side, ratio
  to limit and torsion per story.
- `scripts/frame_member_forces.py`: RAM Frame `Member Forces > All` PDF to
  per-wall JSON.
- `scripts/bluebeam_markup.py`: Highlight and Text Box markups on RAM report
  PDFs in the office Bluebeam style, editable in Revu.

## Product skills

- Use **Wall Integration Skill** (`skills/merge-ram-layout-walls`) when asked to
  move a validated complete wall block from one RAM floor/layout type into an
  earlier empty layout. Run its bundled script and preserve the source `.rss`.
- Use **Column Integration Skill** (`skills/merge-ram-layout-columns`) when
  asked to move a validated complete steel gravity-column block into an earlier
  empty layout. Run its bundled script and preserve the source `.rss`.
- Use **Line Load Merge Skill** (`skills/merge-ram-line-load-properties`) when
  asked to bulk-add line-load property definitions from a CSV to an RSS model
  with zero existing line properties. It does not create geometric assignments.
- Use **RAM Concrete Footing Design Skill**
  (`skills/concrete-footing-design-ram`) when asked to carry verified RAM
  Concept reactions through RAM Concrete, model spread footings, configure RAM
  Foundation, design or review footings, or troubleshoot force, status, and
  design gates.
- Use **Guide RAM Podium Concrete** (`skills/guide-ram-podium-concrete`) when
  asked to walk Modeler lateral walls, user-defined Frame story forces, or
  Concrete wall/column design by hand. Read its notes; do not mutate the
  production model.
- Use **Sync RAM Concept into RSS** (`skills/sync-ram-concept-into-rss`) for
  every swap of a saved Concept file into a job's `.rss`: it refuses while
  RAM Manager has the model open or when the member hash is not the one the
  change was built on, archives the replaced file and proves the result.
  `scripts/rss_member.py` there lists, hashes and extracts the member.
- Read the selected skill's `SKILL.md` before operating on an RSS archive, and
  open only the generated output model in RAM for visual validation.

## RAM Modeler foundation lessons

- Read `references/RAM_MODELER_FOUNDATION_NOTES.md` before a Frame story-force
  pass.
- Concrete walls become Lateral in Modeler (`Layout > Walls > Change`), not
  Frame.
- Spreads under columns. Mats under walls. Do not use RAM continuous/strip
  footings.
- RAM will not analyze a concentrated footing that shares a support with
  another foundation member. Tuck nearby columns into the wall mat instead of
  overlapping a spread.

## RAM Frame lessons

- Read `references/RAM_FRAME_NOTES.md` before guiding a live Frame run, and
  `references/RAM_FRAME_LATERAL_VIDEO_NOTES.md` for a full seismic/wind lateral
  run of a concrete shear wall building (drift, torsion, P-delta).
- Wall gravity vs lateral is set in RAM Modeler (`Layout > Walls > Change`),
  not in Frame. A `No Lateral Member` diaphragm warning means walls are still
  gravity. Close Frame, change the walls, then reopen Frame.
- For a first two-stage podium pass, use Seismic → User Defined Story Forces.
  Do not run program seismic or wind until upper shear-wall transfer loads
  exist.
- Story force goes in Force (kips). Rigid Diaph. X is length, not kips.
- `EQX` = `0°`, `EQY` = `90°`. Same angle = the same load twice.
- Analyze OK stays grey until cases are highlighted. Use Select All. Leave
  Data Extractor and ADINA unchecked.
- Semi-rigid diaphragm meshing may drop a few distorted shells. The list is
  `%ProgramData%\Bentley\Engineering\RAM Structural System\Reports\<model>_MeshWarningReport.log`.
  Click OK and continue unless story shears look wrong.
- Report Frame results on RAM's own report pages, highlighted and noted with
  `scripts/bluebeam_markup.py`, not in a written report of our own.
- Studies that change the lateral system leave the original `.rss` alone and
  save each step as its own file, with its Drift PDF, so the original-then-
  optimized progression can be shown.
- After Frame finishes: RAM Concrete → `Criteria > Column Forces` → Use RAM
  Concept Forces → all floors green → `Process > Analyze`. Do not design walls
  before that.

## RAM Concrete lessons

- Read `references/RAM_CONCRETE_NOTES.md` before guiding wall or column
  design.
- Frame analysis groups are not Concrete wall design groups.
- Yellow Concept-force status: Calc All alone does not clear it. First design
  pass may proceed on yellow; re-import later for green.
- Combinations need a real code + SDS; Code = None greys Generate. Design All
  for columns stays grey until combos exist.
- Start walls at `#5@12` (two curtains at 10 in. and thicker). Do not enable
  mixed bar-size ranges unless the project needs them.
- Column fails: axial/interaction strength → bars or local size; magnification
  red with util < 1.0 → enlarge section / `f'c`, do not raise As.

## RAM API lessons

- Hook RAM through the native COM component `RAMDataAccess.RamDataAccess1`.
- Use `GetDispInterfacePointerByEnum(10)` for the stable database gateway.
- Confirmed safe calls are `CreateNewDatabase2`, `iTAS_GetLoadedModelPath`,
  `LoadDataBase2`, `CloseDatabase`, and narrow method listing on interface 10.
- Do not run broad or speculative RAM COM probes against a live model.
- Do not call `GetDatabaseVersion`, `GetJobName`, `GetCompanyName`,
  `GetModelNameWithPath`, or `GetModelNameWithOutPath` from generic PowerShell
  COM code.
- Do not call `GetDispInterfacePointerByEnum(32)` dynamically from PowerShell.
- Loading `Interop.RAMDATAACCESSLib.dll` does not make live `IModel` calls safe
  from PowerShell; typed casts still reached PowerShell's dynamic COM marshaler
  and caused an access violation.
- Use a separately compiled, typed client for future `IModel` work. Keep each
  new API probe isolated in its own process.
- Never overwrite source `.rss` files. Generate a separate output copy.

## RSS archive debugging lessons

- Read `references/RSS_ARCHIVE_FORMAT.md` before interpreting or editing RSS
  binary members.
- Use `scripts/inspect-ram-rss.ps1` for read-only archive checks and Data Check
  coordinate correlation.
- Confirmed fixed record sizes are `.flt` 472, `.sty` 336, `.c3d` 1072,
  `.w3d` 584, `.sec` 184, `.lpt` 72, `.lod` 20, and `.pol` 16 bytes.
- `.lod` stores `<point count, zero-based .pol start, local property index,
  placement id, placement uid>`. Surface, line, and point placement blocks
  follow the corresponding `.lpt` property-category order.
- A property's assignment count at `.lpt + 44` must reconcile with its
  occurrences in the matching `.lod` category block.
- Data Check `.prnx` reports are gzip-compressed XML. Correlate their
  coordinates to `.lod` placements and nearby `.w3d` wall centerlines.
- Treat undocumented offsets as version-specific. Promote a field to
  "confirmed" only after a controlled one-change diff, UI/report validation,
  successful reopen, and RAM Data Check.

## RAM Modeler hotkey lessons

- Add future RAM shortcuts to `scripts/ram-modeler-hotkeys.ahk` rather than
  creating separate AutoHotkey processes.
- Scope shortcuts with `#HotIf WinActive("ahk_exe RamModeler.exe")`.
- Prefer AutoHotkey v2 `MenuSelect` over screen coordinates and keep a keyboard-menu
  fallback for RAM menus that are not consistently exposed to Windows.
- In AutoHotkey v2, pass `""` for an intentionally blank `WinText` argument.
  An omitted argument caused an unassigned-local-variable error.
- RAM may successfully open a modal command and invalidate its menu before
  `MenuSelect` returns, causing a false exception. In the catch block,
  check whether the expected dialog is already active before using the fallback
  or reporting failure.
- Match stable title prefixes such as `Line Load`, not one assumed full dialog
  title. RAM uses different titles for property and layout modes.
- Use `KeyWait("Ctrl")` before sending fallback menu mnemonics so the triggering
  modifier does not alter the fallback sequence.
- After editing the script, stop duplicate AutoHotkey instances and launch one
  clean instance. The Windows Startup shortcut is named `RAM Modeler Hotkeys`.
- Proven mappings:
  - `Ctrl+G` opens `Layout > Grids > Construction Grids`.
  - `Ctrl+L` opens `Layout > Loads > Line Loads`, the geometric line-load
    assignment tool.
