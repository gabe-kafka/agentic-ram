---
name: attach-ram-concept-api
description: Discover and attach to a running Bentley RAM Concept GUI through the official localhost HTTP API. Use when a user wants to hook into an open Concept window, check whether Concept.exe is serving -apiServerWithGui, print a read-only live-model snapshot, or start a new API-enabled Concept GUI. Do not use this to mutate design strips, uncheck Consider as Post-Tensioned, calc, mesh, save, or close a live design model.
---

# Attach RAM Concept API

Hook the official RAM Concept Python API to a live GUI. Attach is read-only.

## What the API can do here

```text
running Concept.exe
  -> find -apiServer / -apiServerWithGui listener
  -> Concept.attach_to_concept(port)
  -> wrap the already-open Model
  -> read-only snapshot
```

Do not call `open_file`, `new_model`, `save_file`, `close_model`, `shut_down`,
`generate_mesh`, `calc_all`, or unit resets on an attached session. Those
close or rewrite the user's live file.

The published API does **not** expose design strips or
`Consider as Post-Tensioned`. Uncheck that in the UI:

```text
Layers -> Design Strip -> Latitude/Longitude Design Spans Plan
  -> span properties -> General -> uncheck Consider as Post-Tensioned
```

## Run

From the repository root, outside the sandbox:

```powershell
python .\ram-concept\scripts\attach-live-concept.py
```

That probes, then attaches if an API port answers `PONG`.

```powershell
python .\ram-concept\scripts\attach-live-concept.py --probe --format markdown
python .\ram-concept\scripts\attach-live-concept.py --attach --port 1999
```

If the open window was started from the Start menu or RAM Manager
(`-updateRSS`), it has no API listener. Do not inject into that process and
do not open a second Concept on the live RSS working `.cpt`. Close the
RSS-launched window first, copy the checkpoint, then start an API-enabled
GUI:

```powershell
.\ram-concept\scripts\start-ram-concept-api.cmd
python .\ram-concept\scripts\attach-live-concept.py --start-gui --file "C:\path\model.cpt"
```

`--start-gui` starts a **new** Concept process. It does not inject the API
into an already-running window.

## Guards

- Preserve the live model. Snapshot only unless the user later asks for a
  separately named copy.
- Match the Python API folder to the running `Concept.exe` version.
- If several API sessions are running, require `--port`.
- Never kill `Concept.exe`.

## Bundled scripts

- `scripts/attach_live_concept.py`: probe, attach, optional API GUI start.
- `scripts/api_vendor/requests.py`: localhost POST adapter required by the
  installed Concept Python package.
