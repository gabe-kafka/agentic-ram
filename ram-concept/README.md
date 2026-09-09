# RAM Concept

This is the generic home for reusable RAM Concept work. Job-specific models,
transcripts, screenshots, audits, and tutorials belong in the matching
`eng-agent` project directory.

## Local hotkeys

Run `scripts\start-ram-concept-hotkeys.cmd` to enable the RAM Concept-only
hotkey helper. While the main model window is active, `Esc` returns to the
Selection tool. RAM Concept dialogs retain their normal `Esc` behavior.

The canonical implementation and operating instructions live in
`skills\manage-ram-concept-hotkeys\`. The files in `scripts\` are stable
compatibility launchers.

The helper runs in the notification area. Right-click its icon and choose
**Exit** to stop it. To inspect the active Concept toolbar if the Selection
button is not detected, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\ram-concept\scripts\ram-concept-hotkeys.ps1 -Inspect
```

## Slab-option and live-GUI notes

Hand-guide Concept from `references/RAM_CONCEPT_GUI_NOTES.md` (checkpoint,
Calc All, combos, loads) and `references/RAM_CONCEPT_SLAB_OPTIONS.md`
(deflection, punching, SSR Auto Calc, temporary one-way shear). Job
thicknesses and mixes stay in `eng-agent`.

## Slab-boundary proof

The canonical workflow is
`skills\repair-ram-concept-slab-edge\`. It exports RSS geometry read-only,
creates a guarded slab-boundary proposal, builds and meshes a separately named
Concept proof model, and reopens it in a fresh process to verify the saved
geometry and mesh. The similarly named files in `scripts\` are compatibility
launchers.

The controlled 2636_02 result and its assumptions are recorded in
`C:\Users\GabrielKafka-Gibbons\Documents\eng-agent\projects\
2636-mt-pleasant-building-2\ram-concept\tutorials\
2636_02_slab_boundary_proof.md`.

## Live API attach

A normally started RAM Concept GUI does not listen for the API. Probe and
attach only when the process was started with `-apiServerWithGui`:

```powershell
python .\ram-concept\scripts\attach-live-concept.py --probe --format markdown
python .\ram-concept\scripts\attach-live-concept.py --attach
```

To start a new API-enabled GUI:

```powershell
.\ram-concept\scripts\start-ram-concept-api.cmd
```

Attach is read-only. It does not uncheck `Consider as Post-Tensioned`; that
flag lives on design-strip span segments, which the published API does not
expose.

## Saved punching-check inspection

Use the read-only checkpoint inspector to correlate punching-check inputs with
generated stud-rail geometry:

```powershell
python .\ram-concept\scripts\inspect-punching-checks.py `
  "C:\path\to\separate-model-copy.cpt" `
  --format markdown
```

The inspector opens the SQLite checkpoint with `mode=ro`, `immutable=1`, and
`PRAGMA query_only=ON`. It reports the maximum search radius, selected SSR
system, generated rail reach, checks whose generated rails approach the search
limit, checks with no generated SSR layout, and whether a slab opening or
exterior slab boundary lies inside each check's search radius.

This is diagnostic evidence, not an exact failure report. A check without an
`SsrSet` may either pass without SSR or fail before a layout is generated. Use
an exported Warnings and Errors list or Punching Audit report to identify the
exact failed checks. Verify displayed units through the official Concept API or
UI before relying on undocumented internal values.

```text
ram-concept/
|-- AGENTS.md     Product boundary and safety rules
|-- references/   Verified GUI and slab-option notes
|-- scripts/      Generic Concept automation and launchers
|-- skills/       Reusable guarded Concept workflows
|-- tests/        Generic automated tests
`-- README.md
```

Keep all RAM Structural System RSS tooling outside this folder. Keep project
evidence out of this generic product area.
