# RAM Concrete notes

Verified GUI lessons after a RAM Frame story-force run. Keep job SDS, bar
patterns, and story names in the matching `eng-agent` project.

## Force handoff

Before any wall or column design:

`Criteria > Column Forces` → Use RAM Concept Forces → all applicable floors →
green → `Process > Analyze`

- Green: Concept and RSS are in sync; reactions are current.
- Yellow (Not Current): RSS had a **minor** change after Concept last
  imported that story (reframe, slab edge, loads, member size, mats, etc.).
  Calc All alone does not clear yellow. Either (a) re-import that story from
  RSS into Concept, then Calc All, Save, and export reactions, or (b) for a
  first design pass Bentley still allows integrating yellow forces — accept
  the popup, check Use, Analyze, and tighten later.
- Red: forces not available or a major story change. Stop.

Frame supplies lateral. Concept supplies gravity. They meet here.

## Walls

`Criteria > Column Forces` is a force-source gate for walls and columns, not
column design. After Analyze, switch the module dropdown to **Walls**. Do not
open column design yet.

Frame analysis groups (story shears) are not Concrete wall design groups.

`Assign > Wall Design Groups…`

- The dialog lists group numbers. `(new)` is the next unused number.
- Select the number, then **Single** to click walls one-by-one, or **Add > Fence** for a whole line.
- Clicking a wall already in another group moves it to the current number.
- The selected group highlights in the 3D view.

Group like this:

- One group per straight collinear line (close-enough-to-straight is OK).
- A small plan jog (for example 15 ft, 1 ft return, 15 ft) is one group for
  the two 15 ft legs. A ~1 ft stub is detailing, not a pier: leave it
  unassigned rather than its own group. It is not a 30 ft planar wall. Each
  assigned panel still designs at its own length. If a stub is left in the
  group, expect red on it and accept it unless a 15 ft leg fails flexure.
- Isolated walls get their own group.
- An elevator/stair core (the 3–4 walls around it) is one group.
- Walls in one group share combined lateral distribution. Do not group walls
  that do not act together.

Then:

1. `Assign > Section Cuts` → Add automatically. Keep horizontal top, horizontal
   bottom, vertical ends, and openings. Skip mid-height cuts (tilt-up).
2. Openings: elevation view → `Assign > Coupling Beam` so the lintel designs as
   a beam, not only as a wall around the hole.
3. Bar-pattern templates: start with one curtain of `#5@12`. Use two curtains
   for walls 10 in. and thicker. Name patterns without special characters
   (`1512`, not `#5@12` if the build mishandles symbols).
4. Do not enable min/max bar-size or spacing ranges unless a project truly
   needs mixed patterns. Variety slows the run and creates coordination noise.
5. `Combinations > Generate` with the verified design code and SDS.
   Code = None greys Generate. Set ACI / ASCE (or the project editions) and
   SDS first. Design-criteria fields that stay grey with a code selected are
   intentional — leave them.
6. `Process > Design All`.

Light-blue section marks mean a missing assign/combo step. `Process > View
Design` names what is missing. Groups skipped for missing cuts or bar
patterns need `Assign` → All/Fence, then redesign.

Red on very short return walls from spacing/length checks is often accepted
by judgment. Investigate any red that is not an obvious stub, especially
flexure.

## Columns

1. Bar patterns: office start is `#8` bars near 2% As (often 10-`#8` on a
   standard rectangular column). Assign all, then design. Design All stays
   grey until combinations exist.
2. Combinations already generated for walls should still be present.
3. Read the View/Update failure mode before changing anything:
   - **Axial / interaction strength** (e.g. Ld/Cap ≈ 1.07 compression): As
     can help. For a few mild fails, bump bars first (e.g. 12-`#8`). Widen
     ~2 in on the weak side if already near max As, congestion, or many
     columns fail the same way.
   - **Slenderness / magnification** (red with utilization under 1.0): do
     **not** raise As. The program's hard magnification cap is 1.4. About
     1.42–1.43 is commonly accepted; 1.45 and above needs a change. Prefer
     enlarging the weak dimension, or raise `f'c` only when the problem is
     widespread.

## Do not skip

Prefer green Concept-force status before design reliance. For a first podium
pass, Bentley still allows yellow — analyze and design, then tighten Concept
sync later.
