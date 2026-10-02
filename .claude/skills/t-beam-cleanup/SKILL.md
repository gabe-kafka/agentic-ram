---
name: t-beam-cleanup
description: Check and clean up every place a concrete beam changes RAM Concept slab rebar - beam strips, top bars where a beam runs through or ends at a column, beam bottom bars, beam-end bottom bars - and record "no bar called out" overrides. Use when the user says t-beam cleanup, beam conditions, beam override, or "the beam will handle that".
---

# T-Beam Cleanup (RAM Concept)

Follow `ram-concept/skills/clean-up-ram-concept-t-beams/SKILL.md`.

- Run `t_beam_cleanup.py status --model <newest round-N.cpt>` first; it is
  read-only and needs no Concept session.
- Show the five blocks and the open count. Callouts as `15#7 x 26'`.
- Record an override only when the engineer says so; give the reason in
  their words. Beam-through columns are recorded by rule.
- Strips not set: `/t-beam`. Top or bottom leftovers: `/top-reinf`,
  `/bot-reinf`.
