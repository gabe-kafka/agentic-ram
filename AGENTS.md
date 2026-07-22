# Agentic RAM Workspace

This repository contains local Bentley RAM Structural System API tools.

## Proven tools

- `scripts/open-blank-ram.ps1`
- `scripts/open-ram-model.ps1`
- `scripts/test-ram-api-hook.ps1`

## RAM API lessons

- Hook RAM through the native COM component `RAMDataAccess.RamDataAccess1`.
- Use `GetDispInterfacePointerByEnum(10)` for the stable database gateway.
- Confirmed safe calls are `CreateNewDatabase2`, `iTAS_GetLoadedModelPath`, `LoadDataBase2`, `CloseDatabase`, and narrow method listing on interface 10.
- Do not run broad or speculative RAM COM probes against a live model.
- Do not call `GetDatabaseVersion`, `GetJobName`, `GetCompanyName`, `GetModelNameWithPath`, or `GetModelNameWithOutPath` from generic PowerShell COM code.
- Do not call `GetDispInterfacePointerByEnum(32)` dynamically from PowerShell.
- Loading `Interop.RAMDATAACCESSLib.dll` does not make live `IModel` calls safe from PowerShell; typed casts still reached PowerShell's dynamic COM marshaler and caused an access violation.
- Use a separately compiled, typed client for future `IModel` work. Keep each new API probe isolated in its own process.
- Never overwrite source `.rss` files. Generate a separate output copy.
