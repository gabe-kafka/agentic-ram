---
name: stud-rails
description: Two-way shear stud rails in RAM Concept - assumed 6 in opening at each stud rail column, punching status from Concept's own table, search radius fixes. Use when the user says stud rails, SSR, punching, punching openings, cutoff section or search radius.
---

# Stud Rails (RAM Concept)

Follow `ram-concept/skills/design-ram-concept-stud-rails/SKILL.md` (draft) and
the office method in `ram-concept/references/RAM_CONCEPT_GUI_NOTES.md`.

- Status comes from the exported `Punching Check Analysis` table, never from
  whether rails exist in the saved file. Run `punch_status.py` first.
- Raise the radius only on checks in cutoff-section error. Stress failures
  are the engineer's call.
- Edge columns get the opening on the inside face.
- Sync the result into the production model before handing back.
