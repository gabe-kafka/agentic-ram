# RAM Modeler foundation notes

Verified before a RAM Frame story-force pass. Do not use these on RAM Concept
geometry.

## Walls

`Layout > Walls > Change` → Lateral for concrete walls. Frame cannot do this.
Gravity columns and footings do not satisfy a lateral diaphragm.

## Column spreads vs wall mats

- Place concentrated spread footings under columns
  (`Layout > Foundations > Single Column > Add`).
- Place a mat under lateral walls so wall forces can later import into RAM
  Concept. Trace crude geometry that covers the full wall length. Assign any
  existing slab/mat property; Concept will redesign it.
- Do not use RAM continuous / strip footings. The program's own analysis of
  those members is not used in this office workflow.

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
