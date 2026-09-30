---
name: calc-all
description: Generate Mesh then Calc All in the open RAM Concept window, accepting every warning and error dialog along the way (ticks "don't show again" / "repeat for all warnings", then Continue/OK). Use when the user says calc all, mesh and calc, or run Concept.
---

# Calc All (RAM Concept)

Run, from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ram-concept\skills\run-ram-concept-mesh-calc\scripts\run-mesh-calc.ps1
```

- If the user already started mesh or calc by hand, add `-WatchOnly`.
- `-MeshOnly` / `-CalcOnly` run one step.
- Run it in the background; tell the user to keep off the mouse until
  `Finished`.
- Report every `press` / `tick` line from the output and the `STOPPED` reason
  if any. Screenshots are in the printed output folder.

Full behavior and guards: `ram-concept/skills/run-ram-concept-mesh-calc/SKILL.md`.
