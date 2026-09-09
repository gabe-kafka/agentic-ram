---
name: repair-ram-concept-slab-edge
description: Safely detect and repair deficient RAM Concept slab-edge geometry reconstructed from a Bentley RAM Structural System .rss model. Use when a user wants the slab to extend beyond exterior wall faces, asks to automate slab-corner cleanup after a RAM Structural System import, or requests a separate meshed and reopened RAM Concept proof model without modifying the source RSS or a live design model.
---

# Repair RAM Concept Slab Edge

Create a separate geometry-only RAM Concept proof model in which the slab
extends past every exported wall footprint. Preserve the source RSS and refuse
unsupported geometry.

## Scope

Use this skill only for the proven workflow:

```text
RSS inspection copy
  -> typed read-only slab/wall export
  -> guarded polygon repair
  -> separate Concept proof model
  -> mesh
  -> fresh-process reopen validation
  -> visual Standard Plan inspection
```

Do not use this workflow to edit an existing `.cpt`, a live Concept model,
loads, columns, openings, design strips, reinforcement, or analysis criteria.
The generated 10 in slab thickness and 120 in wall height are proof
placeholders, not design decisions.

## Run

Read the repository and both product `AGENTS.md` files first. From the
repository root, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\ram-concept\skills\repair-ram-concept-slab-edge\scripts\run-slab-edge-repair-poc.ps1 `
  -SourceRss "C:\path\model.rss" `
  -ProjectDirectory "C:\path\eng-agent\projects\project-name" `
  -OutputName "project-slab-edge-repair-poc" `
  -ClearanceIn 1.0
```

Choose a new `OutputName` for every run. The runner refuses to overwrite prior
proof artifacts. Run outside the sandbox when required because RAM DataAccess
and RAM Concept start installed Windows processes.

The runner:

1. Copies the RSS byte-for-byte into the ignored RSS models folder.
2. Compiles and runs the typed, read-only RSS geometry exporter.
3. Requires exactly one floor type and one slab perimeter.
4. Rejects zero-length walls, nonpositive wall thickness, nonzero wall
   eccentric distance, invalid polygons, self-intersections, and uncovered
   wall corners.
5. Enforces:

   ```text
   slab offset >= wall thickness / 2 + clearance
   ```

6. Builds and meshes a separately named Concept 2024 proof `.cpt`.
7. Closes Concept, starts a fresh process, reopens the saved model, and verifies
   its slab, walls, coordinates, wall coverage, and persisted mesh.

## Validate

Require all of these before reporting success:

- source and inspection-copy SHA-256 hashes match;
- repaired wall-footprint failures equal zero;
- fresh-process reopen equals `passed`;
- reopened wall-footprint failures equal zero;
- reopened mesh slab-element count is greater than zero;
- saved coordinate delta is within 0.004 in.

Then open only the generated `.cpt` visibly in RAM Concept. Inspect:

```text
Mesh Input > Standard Plan
```

Confirm the slab and wall plan renders normally and save a screenshot in the
run's ignored Concept output folder. Do not open or overwrite the source RSS.

## Outputs

For `OutputName = project-slab-edge-repair-poc`:

```text
<project-directory>/ram-structural-system/models/
  project-slab-edge-repair-poc-source.rss

<project-directory>/ram-structural-system/out/project-slab-edge-repair-poc/
  geometry.tsv
  RamSlabGeometryExporter.exe

<project-directory>/ram-concept/models/
  project-slab-edge-repair-poc-repaired.cpt

<project-directory>/ram-concept/out/project-slab-edge-repair-poc/
  repair-proposal.json
  validation.json
  skill-run.json
```

Treat these as local ignored artifacts. Record the proof assumptions and
checkpoint in `<project-directory>/ram-concept/tutorials/`.

## Bundled scripts

- `scripts/run-slab-edge-repair-poc.ps1`: guarded end-to-end runner.
- `scripts/repair_slab_boundary_from_geometry.py`: geometry repair and audit.
- `scripts/build_slab_edge_poc.py`: Concept proof-model builder and mesher.
- `scripts/validate_slab_edge_poc.py`: fresh-process reopen validator.
- `scripts/api_vendor/requests.py`: localhost-only adapter required by the
  installed Concept 2024 Python package.
