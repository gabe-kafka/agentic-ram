# Agentic RAM Workspace

This repository contains local Bentley RAM Structural System API tools.

## Proven tools

- `scripts/open-blank-ram.ps1`
- `scripts/open-ram-model.ps1`
- `scripts/test-ram-api-hook.ps1`
- `scripts/ram-modeler-hotkeys.ahk`
- `scripts/inspect-ram-rss.ps1`

## Repository skills

- Use **Wall Integration Skill** (`skills/merge-ram-layout-walls`) when asked to move a validated complete wall block from one RAM floor/layout type into an earlier empty layout. Run its bundled script and preserve the source `.rss`.
- Use **Column Integration Skill** (`skills/merge-ram-layout-columns`) when asked to move a validated complete steel gravity-column block into an earlier empty layout. Run its bundled script and preserve the source `.rss`.
- Use **Line Load Merge Skill** (`skills/merge-ram-line-load-properties`) when asked to bulk-add line-load property definitions from a CSV to an RSS model with zero existing line properties. It does not create geometric assignments.
- Read the selected skill's `SKILL.md` before operating on an RSS archive, and open only the generated output model in RAM for visual validation.

## RAM API lessons

- Hook RAM through the native COM component `RAMDataAccess.RamDataAccess1`.
- Use `GetDispInterfacePointerByEnum(10)` for the stable database gateway.
- Confirmed safe calls are `CreateNewDatabase2`, `iTAS_GetLoadedModelPath`, `LoadDataBase2`, `CloseDatabase`, and narrow method listing on interface 10.
- Do not run broad or speculative RAM COM probes against a live model.
- Do not call `GetDatabaseVersion`, `GetJobName`, `GetCompanyName`, `GetModelNameWithPath`, or `GetModelNameWithOutPath` from generic PowerShell COM code.
- Do not call `GetDispInterfacePointerByEnum(32)` dynamically from PowerShell.
- Loading `Interop.RAMDATAACCESSLib.dll` does not make live `IModel` calls safe from PowerShell; typed casts still reached PowerShell's dynamic COM marshaler and caused an access violation.
- Use a separately compiled, typed client for future `IModel` work. Keep each new API probe isolated in its own process.
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
- Prefer `WinMenuSelectItem` over screen coordinates and keep a keyboard-menu
  fallback for RAM menus that are not consistently exposed to Windows.
- In AutoHotkey v2, pass `""` for an intentionally blank `WinText` argument.
  An omitted argument caused an unassigned-local-variable error.
- RAM may successfully open a modal command and invalidate its menu before
  `WinMenuSelectItem` returns, causing a false exception. In the catch block,
  check whether the expected dialog is already active before using the fallback
  or reporting failure.
- Match stable title prefixes such as `Line Load`, not one assumed full dialog
  title. RAM uses different titles for property and layout modes.
- Use `KeyWait("Ctrl")` before sending fallback menu mnemonics so the triggering
  modifier does not alter the fallback sequence.
- After editing the script, stop duplicate AutoHotkey instances and launch one
  clean instance. The Windows Startup shortcut is named `RAM Modeler Hotkeys`.
- Proven mapping: `Ctrl+L` opens `Layout > Loads > Line Loads`, the geometric
  line-load assignment tool.
