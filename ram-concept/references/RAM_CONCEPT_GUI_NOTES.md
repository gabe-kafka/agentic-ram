# RAM Concept GUI notes

Verified live-GUI lessons. Keep job thicknesses, mixes, and model paths in the
matching `eng-agent` project. Direct mutation of an existing design model is
not a proven repository skill; guide the user and preserve a checkpoint.

## Checkpoint first

Work from a separately named `.cpt`. `File > Save As` before edits.

`Process > Calc All` and `Generate Mesh` commit pending edits. Undo will not
restore the pre-command state. Do not calc until the setup review is done.

Do not remesh merely to inspect the existing mesh
(`Layers > Element > Standard Plan`).

## Criteria

- `Criteria > Calc Options`, `Materials`, `Loadings`, `Load Combos`: review
  before changing.
- Do not use `Criteria > Rebuild Load Combos` without reviewer direction. It
  can replace project-specific combinations.
- Concept includes slab-mesh self-weight. Do not also draw a duplicate
  self-weight area load.

## Plans

- Mesh input: `Layers > Mesh Input > Standard Plan`
- Slab properties: select area → `Edit > Selection Properties`
- Loads: `Layers > Loadings > <name> > All Loads Plan`
- Design strips: latitude and longitude span plans
- Punching checks: `Layers > Design Strips > Punching Checks Plan`
- To trace imported area-load outlines without reimporting from Modeler:
  `View > Visible Objects > Static Loadings` on Mesh Input

## Line loads

The Warnings list uses one-based load numbers. Saved checkpoint indices are
zero-based. A "line load is not on the slab" warning is often a slab-edge or
stale-mesh problem, not a reason to delete a transfer load.

## Thickness changes

Separate slab-property regions at terraces, balconies, and step-downs. Put
reinforcement in matching regions so cover follows the correct elevation.
Confirm generated stud rails do not run through a modeled step.

## Live API

A Start-menu or RAM Manager Concept window has no API. Attach only after
`-apiServer` / `-apiServerWithGui`. See
`../skills/attach-ram-concept-api/SKILL.md`.
