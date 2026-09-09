# RAM Concrete notes

Verified GUI lessons after a RAM Frame story-force run. Keep job SDS, bar
patterns, and story names in the matching `eng-agent` project.

## Force handoff

Before any wall or column design:

`Criteria > Column Forces` → Use RAM Concept Forces → all applicable floors →
green → `Process > Analyze`

- Green: Concept reactions are current.
- Yellow: stale. Recalc and save Concept, then reload.
- Red: forces not available. Stop.

Frame supplies lateral. Concept supplies gravity. They meet here.

## Walls

Frame analysis groups (story shears) are not Concrete wall design groups.

1. Assign wall design groups: collinear walls together; isolated walls alone;
   elevator/stair cores as one group.
2. `Assign > Section Cuts` → Add automatically. Keep horizontal top, horizontal
   bottom, vertical ends, and openings. Skip mid-height cuts (tilt-up).
3. Openings: elevation view → `Assign > Coupling Beam` so the lintel designs as
   a beam, not only as a wall around the hole.
4. Bar-pattern templates: start with one curtain of `#5@12`. Use two curtains
   for walls 10 in. and thicker. Name patterns without special characters
   (`1512`, not `#5@12` if the build mishandles symbols).
5. Do not enable min/max bar-size or spacing ranges unless a project truly
   needs mixed patterns. Variety slows the run and creates coordination noise.
6. `Combinations > Generate` with the verified design code and SDS.
7. `Process > Design All`.

Light-blue section marks mean a missing assign/combo step. `Process > View
Design` names what is missing.

Red on very short return walls from spacing/length checks is often accepted
by judgment. Investigate any red that is not an obvious stub, especially
flexure.

## Columns

1. Bar patterns: office start is `#8` bars near 2% As (often 10-`#8` on a
   standard rectangular column). Assign all, then design.
2. Combinations already generated for walls should still be present.
3. Slenderness: red with utilization under 1.0 is usually moment
   magnification, not strength. The program's hard magnification cap is 1.4.
   About 1.42–1.43 is commonly accepted; 1.45 and above needs a change.
4. Increasing As does not fix magnification. Change the section (prefer the
   weak dimension) or raise `f'c` if many columns fail. Change `f'c` globally
   only when the problem is widespread; otherwise enlarge the local section.

## Do not skip

Do not design walls or columns until the Concept-force analyze is green.
