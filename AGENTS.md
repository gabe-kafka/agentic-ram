# Agentic RAM Workspace

This repository holds reusable Bentley RAM product knowledge and GUI
workflows so an agent can guide hand work. Automation skills are a subset.
Job kips, stories, soil values, and model paths stay in `eng-agent`.

This repository is organized by Bentley product.

## Response conciseness

- Default response verbosity is 3/10.
- Give only the immediate next action, using no more than five bullets unless
  additional detail is required for safety or correctness.
- Add background or extended explanation only when explicitly requested.
- A request for detail applies only to that response; return to 3/10 afterward.

## Product routing

- **RAM Structural System** owns generic RAM Manager, RAM Modeler, RAM Frame,
  RAM Concrete, RAM Foundation, DataAccess, RSS-inspection, scripts, skills,
  references, and tests. Read `ram-structural-system/AGENTS.md` before acting
  there. Live GUI guidance uses `references/` notes and
  `skills/guide-ram-podium-concrete`.
- **RAM Concept** owns generic Concept tutorials, model-building workflows,
  automation, file research, GUI notes, and Concept skills. Read
  `ram-concept/AGENTS.md` before acting there. Live GUI work uses
  `ram-concept/references/` plus `skills/attach-ram-concept-api` and the
  official API only.
- **Engineering project context** lives in the separate `eng-agent` repository.
  Project 2636 context is under
  `C:\Users\GabrielKafka-Gibbons\Documents\eng-agent\projects\2636-mt-pleasant-building-2`.
  Read that repository's `AGENTS.md` before acting there.
- **Shared** contains only product-neutral utilities or explicit interchange
  contracts. Do not put code there merely because both products may eventually
  use it.

Keep reusable product capabilities inside their generic product directory.
Keep project evidence in the matching `eng-agent` project directory. Do not
recreate root-level `scripts/`, `skills/`, `references/`, `tests/`, `models/`,
`out/`, or `projects/` directories. `.agents/skills/` contains discovery shims
only; canonical skill instructions and scripts remain under their owning
generic product.

Never apply RSS archive assumptions, record layouts, API calls, or RAM Modeler
hotkeys to a RAM Concept model.
