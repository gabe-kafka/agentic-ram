---
name: stud-rails
description: Design for two-way punching shear with stud rails in RAM Concept (also called shear studs, shear rails, SSR) - assumed 6 in opening at each stud rail column, punching status from Concept's own table, search radius for cutoff errors, opening moved back for stress failures. Use when the user says two-way punching, two-way shear, shear studs, shear rails, stud rails, SSR, punching, punching openings, cutoff section or search radius.
---

# Two-Way Punching Design with Stud Rails (RAM Concept)

Follow `ram-concept/skills/design-ram-concept-stud-rails/SKILL.md` and
the office method in `ram-concept/references/RAM_CONCEPT_GUI_NOTES.md`.

- Status comes from the exported `Punching Check Analysis` table, never from
  whether rails exist in the saved file. Run `punch_status.py` first.
- Sort failing checks by cause first. Cutoff-section error: radius to 10,
  then 12 ft. Failed on stress (ratio above about 2.2): radius does nothing;
  move the assumed opening 1 ft back in a trial file and report it. The
  engineer accepts it before it goes in the production model.
- Export the status table again after every change to the model.
- Edge columns get the opening on the inside face.
- Sync the result into the production model before handing back.
