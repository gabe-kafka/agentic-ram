# Agentic RAM

A product-separated workspace for Bentley RAM knowledge, GUI workflows, and
automation. An agent should be able to guide hand work from the notes here
even when no script exists.

## Repository structure

```text
agentic-ram/
|-- .agents/skills/         Codex discovery shims for repository skills
|-- ram-structural-system/  Generic RSS tooling, skills, references, and tests
|-- ram-concept/            Generic Concept workflows, skills, and tests
|-- shared/                 Product-neutral contracts and utilities only
|-- AGENTS.md               Repository routing rules
`-- README.md
```

## Product boundaries

- **RAM Structural System:** RAM Manager, RAM Modeler, RAM Frame, RAM Concrete,
  RAM Foundation, RSS archives, Story Data, layouts, members, gravity loads,
  Data Check, and RAM DataAccess.
- **RAM Concept:** Concept model setup, meshing, loading, criteria, analysis,
  design, result review, tutorial capture, and future Concept automation.
- **Shared:** only genuinely product-neutral utilities or explicit interchange
  contracts.

See `ram-structural-system/README.md` for proven RSS tools and GUI notes, and
`ram-concept/README.md` for Concept workflows.

## Project context

Job-specific context lives in the separate `eng-agent` repository. Project
2636 is located at:

```text
C:\Users\GabrielKafka-Gibbons\Documents\eng-agent\projects\
2636-mt-pleasant-building-2
```
