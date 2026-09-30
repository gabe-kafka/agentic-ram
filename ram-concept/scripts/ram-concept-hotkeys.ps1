param(
    [switch]$ValidateOnly,
    [switch]$Inspect
)

$canonicalScript = Join-Path $PSScriptRoot `
    '..\skills\manage-ram-concept-hotkeys\scripts\ram-concept-hotkeys.ps1'

$parameters = @{}
if ($ValidateOnly) {
    $parameters.ValidateOnly = $true
}
if ($Inspect) {
    $parameters.Inspect = $true
}

& $canonicalScript @parameters
exit $LASTEXITCODE
