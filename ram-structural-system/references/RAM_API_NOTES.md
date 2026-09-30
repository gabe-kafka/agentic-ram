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
