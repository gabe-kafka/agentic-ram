---
name: concrete-footing-design-ram
description: Guide and verify the end-to-end Bentley RAM Structural System spread-footing workflow from RAM Concept reactions through RAM Concrete Analysis, RAM Modeler foundation placement, and RAM Foundation design. Use when asked to load or troubleshoot Concept column forces, confirm story-force mapping, model single-column spread footings, assign verified soil capacity, generate concrete and soil combinations, optimize/design footings, review failed footing checks, or prepare a footing-design checklist or handoff.
---

# RAM Concrete Footing Design

Guide the user through the live RAM workflow. Do not mutate a production model
unless the user explicitly asks and a proven guarded tool exists. Prefer short,
immediate command sequences; expand only when the user asks for detail.

## Establish the design basis

Before design reliance, identify:

- the authoritative RSS and linked Concept model;
- the Concept source story and RAM story receiving the reactions;
- the governing building-code and load-combination editions;
- verified net allowable soil bearing pressure and applicable bearing stratum;
- concrete strength, reinforcement grade, cover, and optimization limits; and
- whether each foundation is a spread footing, continuous footing, pile cap, or
  mat.

Label transcript, preliminary-report, or reviewer values as provisional until
verified. Never carry a project-specific soil value or code edition into another
project.

## 1. Prepare RAM Concept reactions

1. Open the Concept model linked to the current RSS and confirm the correct
   story/model identity.
2. Run `Process > Calc All` and resolve errors that interrupt the load vector,
   mesh, or analysis.
3. Run `File > Save`, then return to RAM Manager so the current reactions are
   available to RAM Concrete.
4. Record two or three identifiable support reactions for a later spot-check.

Stop if the Concept model is a stale backup, the calculation is incomplete, or
the reactions are not from the controlling floor.

## 2. Load and analyze forces in RAM Concrete

1. Open RAM Concrete in `Concrete Analysis` mode.
2. Select `Criteria > Column Forces`.
3. Choose `Use RAM Concept Analysis Forces at selected levels`, check `Use` for
   the applicable story, and confirm the source-story mapping and Concept file.
4. Require a green status indicator. Red means the reactions are unavailable;
   yellow means they may be stale.
5. If graphical results are needed, select
   `Criteria > Analysis > Save Results for Display`.
6. Run `Process > Analyze` and resolve `No Concept forces`, stale-result, or
   story-mapping warnings.

### Force spot-check

1. Use `Process > Results > Member Forces` for matching, unfactored load cases.
2. At two or three transfer columns, record the axial force at the column top
   immediately below the slab.
3. Compare absolute magnitudes with the matching Concept vertical reactions.
   Account for opposite sign conventions, live-load patterning/reduction, and
   any explicitly included member self-weight.
4. Use `Reports > Column Design Forces > Single` to confirm the forces used for
   design, but do not compare factored or magnified design values directly with
   Concept service reactions.

Investigate material discrepancies rather than accepting them under an
arbitrary percentage tolerance.

## 3. Model the footings in RAM Modeler

1. Open RAM Modeler and select the lowest framed level where the columns or
   walls stop. Do not create a separate foundation story solely for footings.
2. Select `Layout > Foundations > Single Column > Add`.
3. Choose `Spread Footing`, enter verified material properties, and use
   `Single` or `Fence` to place footings beneath the applicable columns.
4. Confirm every intended column has one footing and that no footing was added
   unintentionally beneath a wall pilaster or a column already supported by a
   continuous foundation.

Footings must exist in Modeler before RAM Foundation can design them.

## 4. Configure RAM Foundation

Open `RAM Manager > Design > RAM Foundation`, then complete these gates:

1. `Criteria > Forces`: use RAM Concrete forces for concrete gravity members.
2. `Criteria > Design`: select the verified code. When the project workflow
   calls for optimized spread footings, select design based on applied forces
   and optimum design for each column.
3. `Criteria > Optimize`: enter office/project minimum edge distances,
   dimension increments, minimum thickness, thickness increments, uplift
   criteria, and reinforcement limits. Do not copy tutorial defaults blindly.
4. `Assign > Soil`: enter the verified allowable bearing pressure and assign it
   to every applicable footing. Confirm units and whether the value is net or
   gross.
5. `Assign > Geometry > Spread`: assign and optimize both plan dimensions and
   thickness unless a project constraint requires a fixed dimension or
   eccentric footing.
6. Add verified surcharge, base-plate, pedestal, or fixed-geometry assignments
   when applicable.
7. `Combinations > Generate for Concrete`: generate the verified strength
   combinations and check each required combination `Use`.
8. `Combinations > Generate for Soil`: generate the verified service/soil
   combinations and check each required combination `Use`.

Do not design until at least one active concrete combination and one active soil
combination exist.

## 5. Design and review

1. Run `Process > Design > All Footings`.
2. Interpret yellow as ready to design, green as successfully designed, and red
   as unresolved or unsuccessful.
3. Select `Process > View/Update`, choose each governing footing, and review the
   design and full results report.
4. Check soil pressure, uplift/stability, one-way shear, punching shear,
   flexure, column/pedestal bearing, footing self-weight and surcharge,
   dimensions, reinforcement, development/cover, and constructability.
5. Review perimeter, property-line, adjacent-footing, wall, and utility
   conflicts before accepting an optimized centered footing.

Resolve the governing check; do not merely enlarge a footing until the status
turns green. Keep user overrides visible and rerun affected designs after any
load, criterion, soil, or geometry change.

## Troubleshooting map

- **Red Concept-force status**: recalculate and save the linked Concept model;
  confirm the source story and file; then reload the criteria.
- **Yellow Concept-force status**: refresh the saved reactions and rerun RAM
  Concrete Analysis.
- **Results commands disabled**: run `Process > Analyze`.
- **No results saved for display**: enable
  `Criteria > Analysis > Save Results for Display`, then analyze again.
- **Nonzero but implausible forces**: compare the same unfactored load cases at
  the column top; check story mapping, units, sign convention, and live-load
  category.
- **Footings absent in RAM Foundation**: add them in RAM Modeler at the lowest
  framed level.
- **Footings not ready/yellow**: verify force source, soil assignment, geometry,
  and both combination sets.
- **Red footing**: open `Process > View/Update` and read the governing failure
  before changing geometry, material, or reinforcement.

## Completion gate

Do not describe the footing design as complete until:

- the linked Concept model and story are confirmed and current;
- RAM Concrete shows green Concept-force status and a clean analysis;
- sampled forces have been reconciled;
- every intended footing is modeled at the correct level;
- governing code, soil, materials, criteria, and combination editions are
  verified;
- every required footing has been designed and reviewed with no unexplained red
  status; and
- governing sizes, reinforcement, reports, assumptions, and unresolved
  coordination constraints are captured for the project handoff.

Treat RAM output as engineering-analysis evidence, not approval. Preserve the
authoritative model and report any unverified criterion explicitly.
