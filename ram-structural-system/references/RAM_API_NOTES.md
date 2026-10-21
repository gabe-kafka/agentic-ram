# RAM DataAccess notes

## Installed components

- RAM Manager: `C:\Program Files\Bentley\Engineering\RAM Structural System\Prog\RamManager.exe`
- Native COM server: `C:\Program Files\Common Files\Bentley\Engineering\RAMDataAccess_2_0\RamDataAccess.dll`
- Managed interop metadata: `C:\Program Files\Bentley\Engineering\RAM Structural System\Prog\Interop.RAMDATAACCESSLib.dll`
- Official developer guide: `C:\Program Files\Bentley\Engineering\RAM Structural System\manuals\RAM DataAccess Developers Guide.pdf`

## Proven hookup

1. Create `RAMDataAccess.RamDataAccess1`.
2. Call `GetDispInterfacePointerByEnum(10)` to obtain the database interface.
3. Use `iTAS_GetLoadedModelPath([ref]status, [ref]path)` to confirm the current model.

The loaded API path is normally a working `.ram` file under:

`C:\ProgramData\Bentley\Engineering\RAM Structural System\Working\`

The user's durable model is the `.rss` file supplied to RAM Manager.

## Confirmed safe calls

- `CreateNewDatabase2(path, units, jobName)`
- `LoadDataBase2(path, userId)`
- `iTAS_GetLoadedModelPath([ref]status, [ref]path)`
- `CloseDatabase()`

## Unsafe PowerShell boundary

Generic PowerShell COM calls to model interface enum `32` caused an access violation. A PowerShell wrapper around `Interop.RAMDATAACCESSLib.dll` also fell back to dynamic COM dispatch and crashed. Future model geometry work should use a compiled, strongly typed client and be tested one call at a time in a separate process.

See `ram-wall-api.md` for mapped wall interfaces. That mapping is documentation, not proof that live mutation is safe.

## Saving from a standalone process crashes (RAM SS 26.00.00.222, 2026-10-19)

`scripts/RamLateralLoads.cs` (built to `out/RamLateralLoads.exe`, x64, csc
Framework64) loads an `.rss` copy with `LoadDataBase2`, reads it and makes
in-memory edits without error: surface/line load properties, `IStory.
IsolateFloorType()` (the isolated story gets the NEW floor type UID),
surface and line load sets. `IDBIO1.SaveDatabase()` then raises an
AccessViolationException, even with no edits at all; `GetLastError` returns
code 0 and no text, and the process ends with heap corruption (0xC0000374).
`CloseDatabase()` after a read can crash the same way, which is why the
exporters close on a background thread.

Ruled out: RAM Manager open or closed; DLL version mismatch (COM server,
Prog copy and interop all 26.00.00.222); RAM's SQLite/zip DLLs copied beside
the exe; RAM Manager's `useLegacyV2RuntimeActivationPolicy` config; long vs
short paths; working directory and PATH set to `Prog`.

Each crashed load leaves `<model>.usr` (the user and PC) beside the `.rss`;
delete it before the next load of that file, or `LoadDataBase2` returns 25673.

Until a save works, the API is read-only in practice: model edits go through
Modeler.
