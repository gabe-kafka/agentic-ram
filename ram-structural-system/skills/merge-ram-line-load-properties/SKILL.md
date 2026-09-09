---
name: merge-ram-line-load-properties
description: Line Load Merge Skill for safely bulk-adding unassigned Bentley RAM Structural System line-load property definitions from a CSV manifest to an RSS archive that currently has zero line-load properties. Use when a user asks to import, add, create, or merge RAM Modeler line-load definitions while preserving existing surface/point properties and the source RSS.
---

# Line Load Merge Skill

Add line-load property definitions only. Do not create geometric assignments.
Always write a new RSS output; never overwrite the source.

## Input

Create a CSV with exactly these columns:

```csv
Label,DeadKlf,LiveKlf
EW1,2.195,1.150
```

Values are k/ft. Labels must be unique 1–20 byte ASCII strings. The script
creates Unreducible properties with zero construction dead, construction live,
partition, and mass dead load.

## Workflow

1. Confirm the source is a saved, closed copy—not the live production model.
2. Confirm the model currently has zero line-load properties. This guarded
   workflow refuses existing line properties.
3. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/merge-ram-line-load-properties.ps1 `
  -Source SOURCE.rss -Output OUTPUT.rss -LoadsCsv LINE_LOADS.csv
```

The wrapper locates Python from the Codex bundled runtime, `python`, or `py`.
Pass `-PythonPath` if none is discoverable.

4. Review the built-in validation output. The tool must report:
   - a valid source and output ZIP;
   - unchanged source SHA-256;
   - the expected line-property count;
   - unchanged existing surface and point properties;
   - only `.lpt` and `.ram` payload changes.
5. Open only the output in RAM Modeler. Verify **PropTable → Loads → Line**
   shows every label and exact value, all other components are zero, and the
   reduction type is Unreducible.
6. Keep the output provisional until it opens without crashing and RAM Data
   Check completes. Unrelated pre-existing Data Check errors may remain.

## Safety

- Stop if the output exists or equals the source.
- Stop on ZIP corruption, inconsistent `.ram`/`.lpt` counts, duplicate labels,
  invalid units, or any existing line-load property.
- Preserve all archive members, member order, ZIP comment, and all payloads
  except `.lpt` and the `NumLLoadProps` field in `.ram`.
- Preserve existing surface/point property records byte-for-byte.
- Do not infer or add line-load locations; require a separate marked plan or
  coordinate manifest for assignments.
- Keep generated RSS files and project load manifests out of version control.
