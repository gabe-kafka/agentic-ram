# RAM Concept skills: what is what

This folder is the workshop. The product the team installs is the JT-ENG
connector (`jt-eng-connector`, a Claude Code plugin): a chosen, built-out set
of tools and skills. Every skill here is in one of four boxes.

## Shipped: in the connector

The rules live in the connector's skill; the `SKILL.md` here is a pointer.
The scripts stay here and are canonical: change them here, then
`python tools/vendor.py` in the connector copies the committed files.

| Skill here | Connector skill | Tools |
|---|---|---|
| `design-ram-concept-stud-rails` | `stud-rails` | `stud_rails_*` |
| `simplify-ram-concept-bottom-rebar` | `bottom-bars` | `bottom_bars_*`, `bars_draw` |
| `simplify-ram-concept-top-rebar` | `top-bars` | `top_bars_*`, `bars_draw` |
| `add-ram-concept-rebar-plans` | `rebar-plans` | `concept_rebar_plans_*` |
| `design-ram-concept-one-way-shear` | `one-way-shear` | `one_way_shear_*`, `concept_calc` |

## Engine: scripts the shipped tools run

Not workflows of their own. Do not rename or move them; the shipped scripts
import them by folder name, and the connector vendors them file by file.

| Skill | Used for |
|---|---|
| `simplify-ram-concept-rebar` | the rebar engine: `simplify_rebar.py`, `rebar_groups.py`, `cpt_reader.py`, `bar_plan.py` |
| `attach-ram-concept-api` | finding, starting, resuming the Concept API session |
| `clean-up-ram-concept-t-beams` | `beam_rules.py`, `t_beam_cleanup.py`: bars inside beams, overrides |
| `set-ram-concept-beam-strips` | `beam_spans.py`, imported by `t_beam_cleanup.py` |

## Lab: in development, run from here

One job at a time, by the person developing them. A lab skill moves to
shipped once it has run on a job and its office rules are settled; it then
gets a connector skill and tools, and the `SKILL.md` here becomes a pointer.

- `compare-ram-concept-models`
- `check-ram-concept-slab-transitions`
- `schedule-ram-concept-stud-rails`
- `markup-ram-concept-ssr-plan`

## By hand: GUI drivers and one-offs

Scripts that drive the Concept window with the mouse, or fixed one problem
once. Not for the connector unless a workflow needs them as a step.

- `manage-ram-concept-hotkeys`
- `run-ram-concept-mesh-calc`
- `repair-ram-concept-slab-edge`

## Elsewhere in this repo

- `.claude/skills/`: wrappers for running the lab skills from this checkout
  in Claude Code. Wrappers of shipped workflows are in `.claude/skills-retired/`.
- `.agents/skills/`: one-file pointers for other agents (Codex).
- `references/RAM_CONCEPT_GUI_NOTES.md`: the office method; the connector
  vendors it too.
