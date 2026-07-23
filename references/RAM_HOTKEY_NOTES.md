# RAM Modeler hotkey notes

The shared AutoHotkey v2 script is:

`scripts/ram-modeler-hotkeys.ahk`

The installed interpreter is normally:

`%LOCALAPPDATA%\Programs\AutoHotkey\v2\AutoHotkey64.exe`

The Windows Startup shortcut is:

`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RAM Modeler Hotkeys.lnk`

## Proven Ctrl+L command

`Ctrl+L` opens the RAM Modeler geometric line-load assignment tool:

`Layout > Loads > Line Loads`

This is distinct from the line-load property-definition table:

`PropTable > Loads > Line`

## Reliable implementation pattern

1. Restrict the hotkey to `RamModeler.exe`.
2. First attempt `WinMenuSelectItem` using menu captions.
3. Pass an explicit empty string for `WinText`; do not leave the argument unset.
4. If the menu call throws, first test whether the expected RAM dialog already
   opened. RAM can invalidate its menu during a successful command and make the
   Windows menu call report a false failure.
5. Only then use keyboard menu mnemonics as a fallback.
6. Release the triggering modifier with `KeyWait` before sending mnemonics.
7. Validate using a stable window-title prefix because RAM's layout and property
   dialogs do not share one exact title.

## Failure history

- `WinMenuSelectItem("A", , ...)` failed in AutoHotkey v2 because the omitted
  argument was treated as an unset local variable. Use
  `WinMenuSelectItem("A", "", ...)`.
- The direct menu command opened Line Loads but then threw while RAM replaced
  the menu with its modal dialog. The fallback ran unnecessarily and displayed
  an error. Checking for an active `Line Load` window immediately inside the
  catch block fixed the false error.
- Repeated launches left duplicate helper processes during testing. Stop the
  duplicates and restart one clean process after script changes.

## Adding future shortcuts

Keep all mappings in the shared script. Avoid coordinate-based clicking because
RAM toolbar positions vary with resolution, scaling, and workspace layout.
Prefer menu paths, then mnemonic fallbacks, and give each shortcut a narrow
success check for the dialog or mode it is expected to open.
