param(
    [Parameter(Mandatory = $true)]
    [string]$ModelPath,

    [string]$RamExePath = "C:\Program Files\Bentley\Engineering\RAM Structural System\Prog\RamManager.exe",

    [int]$WaitSeconds = 3,

    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$resolvedModelPath = [System.IO.Path]::GetFullPath($ModelPath)
if (-not (Test-Path -LiteralPath $resolvedModelPath -PathType Leaf)) {
    throw "RAM model not found: $resolvedModelPath"
}
if ([System.IO.Path]::GetExtension($resolvedModelPath) -ne ".rss") {
    throw "RAM model must use the .rss extension: $resolvedModelPath"
}
if (-not (Test-Path -LiteralPath $RamExePath -PathType Leaf)) {
    throw "RAM Manager executable not found: $RamExePath"
}

$process = Start-Process -FilePath $RamExePath -ArgumentList @($resolvedModelPath) -PassThru
if ($WaitSeconds -gt 0) {
    Start-Sleep -Seconds $WaitSeconds
}

$result = [pscustomobject]@{
    Message = "RAM model launch requested"
    ModelPath = $resolvedModelPath
    RamExePath = $RamExePath
    RequestedProcessId = $process.Id
    ProcessRunning = $null -ne (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 4
}
else {
    $result
}
