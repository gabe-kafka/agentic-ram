---
name: run-ram-concept-mesh-calc
description: Run Process > Generate Mesh and Process > Calc All in the one open RAM Concept window and press through the dialogs they raise, logging and screenshotting each one. Use when a user wants Concept meshed and calculated without clicking Enter through every prompt or warning box.
---

# Run RAM Concept Mesh and Calc

Drives the live Concept GUI with real clicks. Works on RSS-launched windows
(no API needed).

```text
Process > Generate Mesh -> Generate, then answer warnings
Process > Calc All      -> answer warnings until Concept is idle
```

Each warning: tick "Don't show this again" / "Do not display this type of
warning during this calc" / "Repeat selected option for all
warnings of this type", then press Continue/OK. Never the title-bar X; on a
Fixable Analysis Warning it acts as Stop.

## Run

Leave exactly one Concept model open with no dialog showing, then:

```powershell
.\ram-concept\skills\run-ram-concept-mesh-calc\scripts\run-mesh-calc.cmd
```

Options: `-MeshOnly`, `-CalcOnly`, `-WatchOnly` (answer dialogs for a mesh
or calc already started by hand), `-TimeoutMinutes 60`, `-OutDir <path>`.
`/calc-all` (`.claude/skills/calc-all`) runs this for Claude Code; a local
PreToolUse hook (`.claude/hooks/allow_mesh_calc.py`) auto-approves it.
Do not use the mouse until it prints `Finished`.

Output goes to `ram-concept/out/mesh-calc-<stamp>/`: `run.log` plus one
`dialog-NN.png` per pressed dialog. Review them and
`Process > Display Warnings` before trusting results.

## Guards

- Mesh and Calc All commit edits; Undo will not restore them. Checkpoint
  first when the model state matters.
- Never presses a dialog with a progress bar, or one whose only buttons are
  Cancel-type.
- Stops on dialogs mentioning save, delete, overwrite, or rebuild.
- Stops if a dialog stays unreadable to UI Automation for 30 s.
- Stops if Concept never goes busy within 15 s of the menu click.
- Never uses UI Automation Invoke: in Concept 2025 an Invoke that opens a
  modal dialog wedges Qt accessibility until that dialog closes.

## Validate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\ram-concept\skills\run-ram-concept-mesh-calc\scripts\run-mesh-calc.ps1 -ValidateOnly
```

Not yet proven end to end on a live model; confirm the log and screenshots
after the first runs.
