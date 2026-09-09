@echo off
rem Canonical launcher for the manage-ram-concept-hotkeys skill.
setlocal
set "SCRIPT_DIR=%~dp0"
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT_DIR%ram-concept-hotkeys.ps1"
endlocal
