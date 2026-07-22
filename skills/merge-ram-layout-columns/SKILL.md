---
name: merge-ram-layout-columns
description: Safely merge a complete contiguous block of Bentley RAM Structural System layout columns from a source layout into an earlier target layout inside an RSS archive. Use when a user asks to move, combine, or merge column locations between RAM floor/layout types and the source RSS must remain unchanged.
---

# Merge RAM Layout Columns

Operate only on a new output copy. Never overwrite the source `.rss` file.

## Workflow

1. Confirm the source and target layout labels.
2. Inspect the RSS before editing. The bundled script validates that:
   - the target precedes the source in the floor-type array;
   - both layouts contain columns;
   - together they own the complete contiguous column block;
   - the target block starts at zero and the source immediately follows it.
3. Run:

```powershell
python scripts/merge-ram-layout-columns.py SOURCE.rss OUTPUT.rss --source-layout SOURCE_LABEL --target-layout TARGET_LABEL
```

4. Verify the output ZIP integrity and report the resulting counts.
5. Open the output in RAM only after validation. If RAM reports an abnormal prior termination, remove only the same-named `.usr` marker beside the output, then reopen it.

## Safety

- Stop if the output already exists.
- Do not use this binary-layout workflow when the source and target do not own the complete contiguous column array.
- Preserve every archive member except the validated `.flt` floor metadata.
- Explain that existing target columns remain in the merged target; the source layout becomes empty.
- Keep backups and generated RSS files out of version control.
