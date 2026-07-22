# Agentic RAM

Local tools for Bentley RAM Structural System 2025.

## What works

- Create and launch a blank RAM `.rss` model.
- Open an existing `.rss` model in RAM Manager.
- Confirm the safe RAM DataAccess COM hook and print the loaded working model path.
- Move a validated complete steel gravity-column block into an earlier empty layout without overwriting the source RSS.
- Move a validated complete wall block into an earlier empty layout without overwriting the source RSS.

## Included skills

- **Wall Integration Skill** (`skills/merge-ram-layout-walls`) packages the proven wall-layout reassignment workflow.
- **Column Integration Skill** (`skills/merge-ram-layout-columns`) packages the guarded column-layout migration workflow.

Both skills validate RAM's floor metadata before editing and always create a separate output model.

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

## Safety boundary

The reliable API surface is intentionally narrow. Use `RAMDataAccess.RamDataAccess1`, database interface enum `10`, and the calls documented in `references/RAM_API_NOTES.md`. Do not use broad COM discovery against a live model.

Do not probe RAM's live `IModel` dynamically from PowerShell. The archive-based merge tools intentionally support only validated contiguous element blocks and refuse broader cases.
