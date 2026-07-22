---
name: merge-ram-layout-columns
description: Column Integration Skill for safely moving a complete Bentley RAM Structural System steel gravity-column block from one layout into an earlier empty layout inside an RSS archive. Use when a user asks to integrate, migrate, or reassign all steel gravity columns between RAM floor/layout types while preserving the source RSS.
---

# Column Integration Skill

Operate only on a new output copy. Never overwrite the source `.rss` file.

## Workflow

1. Confirm the source and target layout labels and that the source block contains steel gravity columns. Do not use this workflow for concrete or lateral columns.
2. Inspect the RSS before editing. The bundled script validates that:
   - the target precedes the source in the floor-type array;
   - the target is empty and the source owns the complete column block;
   - the `.flt` metadata count agrees with the fixed-size `.c3d` column array;
   - the source column block starts at index zero;
   - the target has matching `.sty` Story Data and the source is not referenced
     by Story Data;
   - the `.ram` gravity-column total agrees with `.sty` before editing.
3. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/merge-ram-layout-columns.ps1 `
  -Source SOURCE.rss -Output OUTPUT.rss `
  -SourceLayout SOURCE_LABEL -TargetLayout TARGET_LABEL
```

The wrapper locates Python from the Codex bundled runtime, `python`, or `py`.
Pass `-PythonPath` when none of those are available.

4. Verify ZIP integrity, the preserved archive comment, the unchanged `.c3d`
   payload, and matching `.flt`/`.sty`/`.ram` column totals.
5. Open only the output in RAM Modeler. Confirm columns appear on the target,
   the source is empty, and Integrity > Data Check reports zero errors.

## Safety

- Stop if the output already exists.
- Refuse nonempty targets, partial source blocks, or inconsistent metadata.
- Do not use this proven workflow for concrete or lateral columns.
- Preserve every archive member and the ZIP archive comment. Change only the
  validated `.flt` layout pointers, `.sty` Story Data pointers, and `.ram`
  gravity-column summary; never rewrite `.c3d` geometry.
- Keep the generated output provisional until RAM Modeler and Data Check pass.
- Keep backups and generated RSS files out of version control.
