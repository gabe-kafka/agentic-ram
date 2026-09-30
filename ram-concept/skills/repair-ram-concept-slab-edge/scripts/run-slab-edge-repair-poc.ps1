[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRss,

    [Parameter(Mandatory = $true)]
    [string]$ProjectDirectory,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]*$')]
    [string]$OutputName,

    [ValidateRange(0.001, 120.0)]
    [double]$ClearanceIn = 1.0,

    [string]$PythonExe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE."
    }
}

$repoRoot = [IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot '..\..\..\..')
)
$sourcePath = [IO.Path]::GetFullPath($SourceRss)
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Source RSS not found: $sourcePath"
}
if ([IO.Path]::GetExtension($sourcePath) -ine '.rss') {
    throw 'SourceRss must identify an .rss file.'
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $bundledPython = Join-Path $env:USERPROFILE (
        '.cache\codex-runtimes\codex-primary-runtime\' +
        'dependencies\python\python.exe'
    )
    if (Test-Path -LiteralPath $bundledPython -PathType Leaf) {
        $PythonExe = $bundledPython
    }
    else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) {
            throw 'Python was not found. Pass -PythonExe explicitly.'
        }
        $PythonExe = $pythonCommand.Source
    }
}
$PythonExe = [IO.Path]::GetFullPath($PythonExe)
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}

$conceptApi = (
    'C:\Program Files\Bentley\Engineering\RAM Concept\' +
    'RAM Concept 2024\python'
)
if (-not (Test-Path -LiteralPath $conceptApi -PathType Container)) {
    throw "RAM Concept 2024 Python API not found: $conceptApi"
}

$projectDirectory = [IO.Path]::GetFullPath($ProjectDirectory)
if (-not (Test-Path -LiteralPath $projectDirectory -PathType Container)) {
    throw "ProjectDirectory not found: $projectDirectory"
}
$rssModelDirectory = Join-Path $projectDirectory (
    'ram-structural-system\models'
)
$rssOutputDirectory = Join-Path $projectDirectory (
    "ram-structural-system\out\$OutputName"
)
$conceptModelDirectory = Join-Path $projectDirectory (
    'ram-concept\models'
)
$conceptOutputDirectory = Join-Path $projectDirectory (
    "ram-concept\out\$OutputName"
)

$sourceCopy = Join-Path $rssModelDirectory "$OutputName-source.rss"
$geometryTsv = Join-Path $rssOutputDirectory 'geometry.tsv'
$repairJson = Join-Path $conceptOutputDirectory 'repair-proposal.json'
$validationJson = Join-Path $conceptOutputDirectory 'validation.json'
$manifestJson = Join-Path $conceptOutputDirectory 'skill-run.json'
$outputCpt = Join-Path $conceptModelDirectory "$OutputName-repaired.cpt"

$allOutputs = @(
    $sourceCopy,
    $rssOutputDirectory,
    $conceptOutputDirectory,
    $outputCpt
)
$existingOutputs = @(
    $allOutputs | Where-Object { Test-Path -LiteralPath $_ }
)
if ($existingOutputs.Count -gt 0) {
    throw (
        "Refusing to overwrite an existing proof run:`n" +
        ($existingOutputs -join "`n")
    )
}

New-Item -ItemType Directory -Path $rssModelDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $rssOutputDirectory | Out-Null
New-Item -ItemType Directory -Path $conceptModelDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $conceptOutputDirectory | Out-Null

Copy-Item -LiteralPath $sourcePath -Destination $sourceCopy
$sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
$copyHash = (Get-FileHash -LiteralPath $sourceCopy -Algorithm SHA256).Hash
if ($sourceHash -ne $copyHash) {
    throw 'The ignored RSS inspection copy does not match the source.'
}

$exporterSource = Join-Path $repoRoot (
    'ram-structural-system\scripts\RamSlabGeometryExporter.cs'
)
$interopSource = (
    'C:\Program Files\Bentley\Engineering\RAM Structural System\' +
    'Prog\Interop.RAMDATAACCESSLib.dll'
)
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
foreach ($requiredPath in @($exporterSource, $interopSource, $compiler)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required dependency not found: $requiredPath"
    }
}

$exporterExe = Join-Path $rssOutputDirectory (
    'RamSlabGeometryExporter.exe'
)
$interopCopy = Join-Path $rssOutputDirectory (
    'Interop.RAMDATAACCESSLib.dll'
)
Copy-Item -LiteralPath $interopSource -Destination $interopCopy
Invoke-Checked -Executable $compiler -Arguments @(
    '/nologo',
    '/target:exe',
    '/platform:x64',
    "/reference:$interopSource",
    "/out:$exporterExe",
    $exporterSource
)
Invoke-Checked -Executable $exporterExe -Arguments @(
    $sourceCopy,
    $geometryTsv
)

$repairScript = Join-Path $PSScriptRoot (
    'repair_slab_boundary_from_geometry.py'
)
$buildScript = Join-Path $PSScriptRoot 'build_slab_edge_poc.py'
$validateScript = Join-Path $PSScriptRoot (
    'validate_slab_edge_poc.py'
)

Invoke-Checked -Executable $PythonExe -Arguments @(
    $repairScript,
    $geometryTsv,
    $repairJson,
    '--clearance-in',
    $ClearanceIn.ToString(
        [Globalization.CultureInfo]::InvariantCulture
    )
)
Invoke-Checked -Executable $PythonExe -Arguments @(
    $buildScript,
    $repairJson,
    $geometryTsv,
    $outputCpt,
    $validationJson
)
Invoke-Checked -Executable $PythonExe -Arguments @(
    $validateScript,
    $outputCpt,
    $repairJson,
    $validationJson
)

$validation = Get-Content -LiteralPath $validationJson -Raw |
    ConvertFrom-Json
$manifest = [ordered]@{
    skill = 'repair-ram-concept-slab-edge'
    status = 'passed'
    source_rss = $sourcePath
    source_sha256 = $sourceHash
    source_copy = $sourceCopy
    source_copy_sha256 = $copyHash
    clearance_past_wall_face_in = $ClearanceIn
    geometry_tsv = $geometryTsv
    repair_proposal = $repairJson
    output_cpt = $outputCpt
    validation = $validation
}
$manifest | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $manifestJson -Encoding UTF8

$manifest | ConvertTo-Json -Depth 10
