# Agentic RAM

Local tools for Bentley RAM Structural System 2025.

## What works

- Create and launch a blank RAM `.rss` model.
- Open an existing `.rss` model in RAM Manager.
- Confirm the safe RAM DataAccess COM hook and print the loaded working model path.
- Move a validated complete steel gravity-column block into an earlier empty layout without overwriting the source RSS.
- Move a validated complete wall block into an earlier empty layout without overwriting the source RSS.
- Bulk-add validated line-load property definitions from CSV without overwriting the source RSS.
- Use RAM-specific keyboard shortcuts through the shared AutoHotkey v2 helper.
- Read and cross-check known RSS floor, story, wall, column, section, and load records without modifying the model.

## Included skills

- **Wall Integration Skill** (`skills/merge-ram-layout-walls`) packages the proven wall-layout reassignment workflow.
- **Column Integration Skill** (`skills/merge-ram-layout-columns`) packages the guarded column-layout migration workflow.
- **Line Load Merge Skill** (`skills/merge-ram-line-load-properties`) packages the validated unassigned line-load property import workflow.

All skills validate their supported RAM metadata before editing and always create a separate output model.

## Quick start

Open an existing model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\open-ram-model.ps1 -ModelPath ".\models\ram\your-model.rss"
```

Check the live API hook:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-ram-api-hook.ps1 -AsJson
```

Create and open a blank model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\open-blank-ram.ps1 -AsJson
```

Inspect a saved RSS and correlate an optional RAM Data Check report:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\inspect-ram-rss.ps1 `
  -Source ".\models\ram\your-model.rss" -DataCheck ".\Data Check.prnx" -ListLoads
```

The evidence-based archive map and confidence levels are documented in
`references/RSS_ARCHIVE_FORMAT.md`.

## RAM Modeler hotkeys

The shared helper is `scripts/ram-modeler-hotkeys.ahk`. The proven first mapping
is `Ctrl+L` for `Layout > Loads > Line Loads`. Implementation lessons and the
pattern for adding future shortcuts are documented in
`references/RAM_HOTKEY_NOTES.md`.

## Safety boundary

The reliable API surface is intentionally narrow. Use `RAMDataAccess.RamDataAccess1`, database interface enum `10`, and the calls documented in `references/RAM_API_NOTES.md`. Do not use broad COM discovery against a live model.

Do not probe RAM's live `IModel` dynamically from PowerShell. The archive-based merge tools intentionally support only validated contiguous element blocks and refuse broader cases.

Use `scripts/inspect-ram-rss.ps1` for read-only RSS debugging. Unknown or
version-specific records must remain uninterpreted until isolated by a
controlled one-change model diff and validated in RAM.
