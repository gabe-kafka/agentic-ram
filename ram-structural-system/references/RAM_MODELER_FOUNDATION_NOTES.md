# RAM Modeler foundation notes

Verified before a RAM Frame story-force pass. Do not use these on RAM Concept
geometry.

## Walls

`Layout > Walls > Change` → Lateral for concrete walls. Frame cannot do this.
Gravity columns and footings do not satisfy a lateral diaphragm.

## Column spreads vs wall mats

- Place concentrated spread footings under columns
  (`Layout > Foundations > Single Column > Add` → Spread → Fence gravity
  columns). Check the base plan first; many models already have spreads.
- Leave out wall-line / future-mat columns when fencing. Delete any spread
  that will later share a support with a wall mat.
- Place a mat under lateral walls so wall forces can later import into RAM
  Concept. Trace crude geometry that covers the full wall length. Assign any
  existing slab/mat property; Concept will redesign it.
- Do not use RAM continuous / strip footings. The program's own analysis of
  those members is not used in this office workflow.

## RAM Foundation (spreads)

Manager red on Foundation usually means not designed yet, not a member fail.

1. `Criteria > Forces` → RAM Concrete.
2. `Criteria > Design` / `Optimize` → verified code; optimize on applied
   forces unless the project locks sizes.
3. `Assign > Soil` → verified net allowable (project value) → all gravity
   spreads.
4. `Combinations > Generate for Concrete` + `Generate for Soil` → check Use.
5. `Process > Design > All Footings` → View/Update reds by governing check.

Wall mats stay next-week / Concept work unless the job says otherwise.

## Overlap rule

RAM will not analyze a concentrated footing that shares a support with another
foundation member. Do not put a spread and a mat under the same column.

If a nearby column spread would grow into the wall mat, omit the spread and
include that column centerline in the mat.

Do not draw one mat around the entire building perimeter just to save tracing.

## After Frame and Concrete

Column spreads are designed in RAM Foundation from Concrete forces. Wall mats
are designed in RAM Concept on a separate foundation level. See
`../skills/concrete-footing-design-ram/SKILL.md` for the spread-footing gates.
