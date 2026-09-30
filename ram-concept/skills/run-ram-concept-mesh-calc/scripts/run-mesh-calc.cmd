@echo off
rem Canonical launcher for the run-ram-concept-mesh-calc skill.
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-mesh-calc.ps1" %*
pause
endlocal
