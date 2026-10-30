# RAM Concept slab-options notes

Office GUI workflow for a transfer-slab option review. The shared-drive PDF
controls if this summary conflicts. Keep project option thickness, mix, and
report counts in `eng-agent`.

Prerequisite: initial RAM Concept review, loading, geometry, and design-info
import are complete and approved.

## Review order

Office PDF default:

1. Deflection, then adjust the slab option.
2. Two-way punching, then radius, drop caps, beams, walls, or thickness.
3. Temporary full-width one-way shear.
4. Quantities into the comparison spreadsheet.
5. PDF report.

A project meeting may override that order (for example punching before
deflection). Follow the project sequence when one is recorded.

Office standard since the 2026-10-06 team meeting: design **one** option
fully, the one the office expects to recommend (the architect rarely picks
another). Document it, then change only the thickness (16 in to 14 in in
the example) and do a visual review of the results: a rough count and the
general locations of beams needed for deflection and punching, without
modelling them or iterating. The comparison schedule is reduced and carries
little reinforcement detail for the secondary option. A true 50/50 case
still gets two full options.

Batch a reasonable set of geometry changes, then `Calc All`. Recheck punching,
deflection, and reinforcement after each meaningful iteration.

## Deflection (office PDF)

The limits are the JTE standard (`shared/JTE_DEFLECTION_LIMITS.md`, from
`S:\02_Design\01_JTE Standards\Design Standards\Loads and Deflections\Deflections.pdf`).
The load history steps are the ones in the slab options workflow:
Construction, DL Attachment, Immediate LL, Sustained Loads, Sustained +
Immediate LL.

| Plan to read | Limit |
|---|---|
| Sustained + Immediate LL (total long-term, nothing subtracted) | 2 in max, regardless of the initial DL deflection |
| Sustained + Immediate LL minus DL Attachment | L/240; L/480 on perimeter spans |
| Immediate LL | L/360, and 3/4 in max at exterior conditions |
| Immediate total load, where the slab supports brick or CMU | L/600 or 0.5 in, whichever is less |

- Cantilevers: twice the allowable deflection (the limits assume simple spans).
- Calc with the extent at `+ Load History Δ`; Calc All skips long-term
  deflection. Read the plots under `Layers > Load History Deflections`.
- The brick `L/600` plot in some examples is the brick/CMU row above: it
  applies where the slab carries brick or CMU, as an immediate total load check.

If a span fails, consider beams, higher `f'c`, thickness, columns, or walls.

Difference plots must subtract the correct attachment loading. Wrong
attachment layer = wrong difference.

## Punching

- Review the status plan and the checks plan.
- Interior fail with USR `< 2.0`: try a larger maximum search radius.
- Interior fail with USR `>= 2.0`: drop cap is the usual next move.
- Punching audit: if the larger perimeter governs, widen the drop cap; if the
  smaller governs, thicken the slab.
- `Criteria > Materials > SSR Systems > Stud Spacing`: use `Auto Calc` for
  transfer-slab constructability review. Default `Code Max` can place many
  widely spaced rails on short column faces.
- `No cutoff section`: increase search radius in about 2 ft steps. About 12 ft
  is a practical troubleshooting ceiling, not a code limit. A larger radius
  still needs a reasonable rail layout.
- Nearby openings or the slab edge inside the search circle can create a bad
  critical section. Check those before raising the radius.
- After a beam is added, Concept may still show a punching fail because it
  does not fully credit beam reinforcement. Office uses a separate final
  punching check.
- Coordinate drop caps with the reviewer before locking them in.

Saved-checkpoint inspection cannot tell "SSR not required" from "SSR failed
before layout." Export Warnings and Errors or a Punching Audit for the exact
failing checks. See `../AGENTS.md` punching diagnostics.

## Temporary one-way shear

1. Change top and bottom reinforcement to user bars so span-segment calcs stay
   locked.
2. Set column-strip width to full width.
3. Review the shear-bars plan: extent `< d` → stirrups not required; `>= d` →
   required.
4. Do not save the Concept model after this temporary setup.

## Report set (office PDF)

Mesh-input, SSR plan, four deflection plans, top bars, bottom bars, shear
bars, punching, beam/drop-cap notes, SSR count, comparison-spreadsheet image
on page 1. Reconcile if a meeting asked for a different deflection-plan count.
