---
name: merge-ram-layout-walls
description: Safely reassign a complete contiguous Bentley RAM Structural System wall block from one floor/layout type to an earlier empty target layout in an RSS archive. Use when a user asks to move or merge RAM walls between layouts without overwriting the source model.
---

# Merge RAM Layout Walls

Operate only on a new output copy. Never overwrite the source `.rss` file.

## Workflow

1. Inspect the RSS floor-type records and identify the numeric indices and labels for the source and target layouts.
2. Confirm the target is earlier than the source, contains zero walls, and the source owns the complete `.w3d` wall array.
3. Run:

```powershell
python scripts/merge-ram-layout-walls.py SOURCE.rss OUTPUT.rss --source-floor SOURCE_INDEX --target-floor TARGET_INDEX
```

4. Verify the output ZIP integrity and re-read the `.flt` wall counts before delivery.
5. Open only the output model in RAM for visual confirmation.

## Safety

- Stop if the output already exists.
- Do not splice partial, interleaved, or noncontiguous wall blocks.
- Preserve every archive member except the validated `.flt` floor metadata.
- This workflow moves the wall block: the target receives all walls and the source becomes empty.
- Keep backups and generated RSS files out of version control.
