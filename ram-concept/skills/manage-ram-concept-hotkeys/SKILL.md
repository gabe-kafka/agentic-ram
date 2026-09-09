---
name: manage-ram-concept-hotkeys
description: Install, start, stop, validate, troubleshoot, and extend Windows hotkeys scoped to Bentley RAM Concept 2024. Use when a user asks to enable or repair RAM Concept keyboard shortcuts, especially mapping Esc to the Tools, Selection, Selection command while preserving normal Esc behavior in dialogs.
---

# Manage RAM Concept Hotkeys

Use the bundled helper for RAM Concept-only keyboard automation. Keep all
implementation and tests inside this skill directory; keep the top-level
`ram-concept/scripts/` files as compatibility wrappers only.

## Esc to Selection

Treat this RAM Concept 2024 menu path as canonical:

```text
Tools > Selection > Selection
```

The helper intercepts `Esc` only when:

- the foreground process is `Concept.exe`; and
- the foreground title contains `RAM Concept`, identifying the main model
  window.

Do not intercept `Esc` in property or criteria dialogs. Those dialogs must
retain their native cancel/close behavior.

## Start and stop

Start the helper with:

```powershell
.\scripts\start-ram-concept-hotkeys.cmd
```

The helper uses a named mutex to prevent duplicate instances. Stop it by
right-clicking **RAM Concept: Esc to Selection** in the Windows notification
area and choosing **Exit**.

## Validate

Compile-check the canonical implementation after every edit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\ram-concept-hotkeys.ps1 -ValidateOnly
```

Then perform this controlled UI test:

1. Open a disposable or already-saved RAM Concept model.
2. Activate **Tools > Selection > Utility**.
3. Press `Esc` in the main model window.
4. Confirm **Tools > Selection > Selection** is active.
5. Open a harmless dialog and confirm `Esc` still closes or cancels it.

Do not claim the mapping works until both behaviors are observed.

## Troubleshoot

If `Esc` does nothing:

1. Exit the existing tray instance.
2. Run the compile check.
3. Start one clean instance.
4. Repeat the controlled UI test.

Use `-Inspect` only when diagnosing RAM Concept accessibility metadata:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\ram-concept-hotkeys.ps1 -Inspect
```

Prefer the verified keyboard-menu sequence over toolbar coordinates or
accessibility names. Retain toolbar detection only as a fallback.

## Extend safely

- Scope every mapping to `Concept.exe`.
- Prefer stable menu paths and keyboard navigation.
- Protect modal dialogs and text-entry controls from global remapping.
- Avoid RAM Modeler AutoHotkey assumptions; RAM Structural System hotkeys
  belong to that product.
- Do not mutate a Concept model merely to test a shortcut.
- Restart the helper after code changes and test the affected UI state.

## Bundled scripts

- `scripts/ram-concept-hotkeys.ps1`: canonical hook and menu automation.
- `scripts/start-ram-concept-hotkeys.cmd`: hidden notification-area launcher.
