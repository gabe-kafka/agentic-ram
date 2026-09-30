param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [string]$DataCheck,

    [switch]$AsJson,

    [switch]$ListColumns,

    [switch]$ListWalls,

    [switch]$ListLoads,

    [double]$CoordinateToleranceFt = 0.02,

    [string]$PythonPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pythonArgs = @()
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $runtimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes"
    $bundledPython = if (Test-Path -LiteralPath $runtimeRoot -PathType Container) {
        Get-ChildItem -LiteralPath $runtimeRoot -Filter "python.exe" -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\dependencies\\python\\python\.exe$" } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
    }

    if ($null -ne $bundledPython) {
        $PythonPath = $bundledPython.FullName
    }
    else {
        $pythonCommand = Get-Command "python.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $pythonCommand) {
            $PythonPath = $pythonCommand.Source
        }
        else {
            $pyCommand = Get-Command "py.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($null -ne $pyCommand) {
                $PythonPath = $pyCommand.Source
                $pythonArgs = @("-3")
            }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Python 3 was not found. Pass its executable path with -PythonPath."
}

$scriptPath = Join-Path $PSScriptRoot "inspect-ram-rss.py"
$arguments = @($scriptPath, $Source, "--coordinate-tolerance-ft", $CoordinateToleranceFt)
if (-not [string]::IsNullOrWhiteSpace($DataCheck)) {
    $arguments += @("--data-check", $DataCheck)
}
if ($AsJson) {
    $arguments += "--json"
}
if ($ListColumns) {
    $arguments += "--list-columns"
}
if ($ListWalls) {
    $arguments += "--list-walls"
}
if ($ListLoads) {
    $arguments += "--list-loads"
}

& $PythonPath @pythonArgs @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
