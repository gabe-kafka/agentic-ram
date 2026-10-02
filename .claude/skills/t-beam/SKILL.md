---
name: t-beam
description: Set RAM Concept design spans along concrete beams to the T or L beam strip setup and prove it from the saved file. Use when the user says t-beam, T beam, L beam, beam strips, or when bars pile up over beam columns.
---

# T-Beam Strips (RAM Concept)

Follow `ram-concept/skills/set-ram-concept-beam-strips/SKILL.md`. This is
step 1 of `/t-beam-cleanup`, which owns the rest of the beam conditions.

- Run `beam_spans.py` on a saved copy first; it lists the beam spans and
  prints the command for each direction.
- The edit is GUI-driven: the right Design Spans plan must be active, the
  Scripting Server paused, and the user off the mouse and keyboard.
- Proof is the saved file: rerun `beam_spans.py` and show every span DONE.
- Then Generate Strips and Calc All, and rerun `/top-reinf` and `/bot-reinf`
  because the demand at beam columns changes.
