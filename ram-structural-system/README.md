# RAM Structural System

The generic product workspace for Bentley RAM Structural System knowledge and
automation.

## Structure

```text
ram-structural-system/
|-- AGENTS.md    Product-specific operating and safety rules
|-- models/ram/  Generic local fixtures only
|-- out/         Generic generated tooling artifacts
|-- references/  Verified API, hotkey, RSS format, and GUI workflow notes
|-- scripts/      Proven automation and inspection tools
|-- skills/       Agent-discoverable guarded workflows
`-- tests/        Automated tests
```

The repository's `.agents/skills/` entries forward Codex discovery to the
canonical skills in this directory.

## What works

- Create and launch a blank RAM `.rss` model.
- Open an existing `.rss` model in RAM Manager.
- Confirm the safe RAM DataAccess COM hook and print the loaded model path.
- Move complete validated steel gravity-column or wall blocks between layouts
  without overwriting the source RSS.
- Bulk-add validated line-load property definitions from CSV without
  overwriting the source RSS.
- Use RAM-specific keyboard shortcuts through the AutoHotkey v2 helper.
- Read and cross-check known RSS floor, story, wall, column, section, and load
  records without modifying the model.
- Run a first-pass RAM Frame user-defined story-force analysis after Modeler
  walls are Lateral, then hand off to RAM Concrete Concept forces.

## Skills

- **Wall Integration Skill** (`skills/merge-ram-layout-walls`)
- **Column Integration Skill** (`skills/merge-ram-layout-columns`)
- **Line Load Merge Skill** (`skills/merge-ram-line-load-properties`)
- **Guide RAM Podium Concrete** (`skills/guide-ram-podium-concrete`)
- **RAM Concrete Footing Design** (`skills/concrete-footing-design-ram`)

Archive-edit skills validate RAM metadata and always write a separate output
model. Guide skills walk the live GUI and do not mutate the production file.

## Quick start

Run these commands from the repository root.

Open an existing model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\ram-structural-system\scripts\open-ram-model.ps1 `
  -ModelPath ".\ram-structural-system\models\ram\your-model.rss"
```

Check the live API hook:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\ram-structural-system\scripts\test-ram-api-hook.ps1 -AsJson
```

Create and open a blank model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\ram-structural-system\scripts\open-blank-ram.ps1 -AsJson
```

Inspect a saved RSS and correlate an optional RAM Data Check report:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\ram-structural-system\scripts\inspect-ram-rss.ps1 `
  -Source ".\ram-structural-system\models\ram\your-model.rss" `
  -DataCheck ".\Data Check.prnx" -ListLoads
```

The evidence-based archive map is in `references/RSS_ARCHIVE_FORMAT.md`.
Hand-guide notes: `RAM_PODIUM_CONCRETE_WORKFLOW.md`, `RAM_FRAME_NOTES.md`,
`RAM_CONCRETE_NOTES.md`, and `RAM_MODELER_FOUNDATION_NOTES.md`.

## Hotkeys

The helper is `scripts/ram-modeler-hotkeys.ahk`. The proven first mapping is
`Ctrl+L` for `Layout > Loads > Line Loads`. See
`references/RAM_HOTKEY_NOTES.md` before adding shortcuts.

## Safety boundary

The reliable API surface is intentionally narrow. Use
`RAMDataAccess.RamDataAccess1`, database interface enum `10`, and only the calls
documented in `references/RAM_API_NOTES.md`. Do not use broad COM discovery
against a live model or probe RAM's live `IModel` dynamically from PowerShell.

The archive merge tools intentionally support only validated contiguous element
blocks and refuse broader cases. Use `scripts/inspect-ram-rss.ps1` for read-only
RSS debugging, and keep unknown records uninterpreted until controlled
one-change validation succeeds.

RSS binary layouts, RAM DataAccess COM behavior, and RAM Modeler hotkeys are
specific to RAM Structural System. They are not shared with RAM Concept.

Job-specific RSS models, inspection archives, screenshots, and candidates
belong in the matching `eng-agent` project's `ram-structural-system/` folder.
