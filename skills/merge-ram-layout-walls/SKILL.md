---
name: merge-ram-layout-walls
description: Wall Integration Skill for safely reassigning a complete contiguous Bentley RAM Structural System wall block from one floor/layout type to an earlier empty target layout in an RSS archive. Use when a user asks to integrate, move, or merge RAM walls between layouts without overwriting the source model.
---

# Wall Integration Skill

Operate only on a new output copy. Never overwrite the source `.rss` file.

## Workflow

1. Inspect the RSS floor-type records and identify the numeric indices and labels for the source and target layouts.
2. Confirm the target is earlier than the source, contains zero walls, and the source owns the complete `.w3d` wall array.
3. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/merge-ram-layout-walls.ps1 `
  -Source SOURCE.rss -Output OUTPUT.rss `
  -SourceFloor SOURCE_INDEX -TargetFloor TARGET_INDEX
```

The wrapper locates Python from the Codex bundled runtime, `python`, or `py`.
Pass `-PythonPath` when none of those are available.

4. Verify the output ZIP integrity, preserved archive metadata, and re-read the `.flt` wall counts before delivery.
5. Open only the output model in RAM for visual confirmation.

## Safety

- Stop if the output already exists.
- Do not splice partial, interleaved, or noncontiguous wall blocks.
- Preserve every archive member and the ZIP archive metadata; change only the validated `.flt` floor metadata payload.
- This workflow moves the wall block: the target receives all walls and the source becomes empty.
- Keep backups and generated RSS files out of version control.
