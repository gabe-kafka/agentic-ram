param(
    [string]$OutputDirectory,

    [string]$ModelPath,

    [string]$ModelName,

    [int]$Units = 0,

    [string]$JobName = "Agentic RAM Blank",

    [string]$RamExePath,

    [int]$WaitSeconds = 5,

    [switch]$NoLaunch,

    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-RamSuccess {
    param(
        [int]$ReturnCode,
        [string]$Operation
    )

    if ($ReturnCode -ne 0) {
        throw "$Operation failed with return code $ReturnCode."
    }
}

function Get-RamProcess {
    param(
        [int]$RequestedPid
    )

    $candidateNames = @(
        "RAMManager",
        "RamManager",
        "RAMModeler",
        "RamModeler",
        "RAMFrame",
        "RamFrame"
    )

    $all = foreach ($candidateName in $candidateNames) {
        Get-Process -Name $candidateName -ErrorAction SilentlyContinue
    }

    $seen = @{}
    foreach ($process in @($all)) {
        if ($null -eq $process) {
            continue
        }

        if (-not $seen.ContainsKey([string]$process.Id)) {
            $seen[[string]$process.Id] = $process
        }
    }

    $processes = @($seen.Values | Sort-Object Id)
    if ($RequestedPid) {
        return $processes | Where-Object { $_.Id -eq $RequestedPid } | Select-Object -First 1
    }

    $withWindow = $processes | Where-Object { $_.MainWindowHandle -ne 0 }
    if ($withWindow) {
        return $withWindow | Select-Object -First 1
    }

    return $processes | Select-Object -First 1
}

function Find-RamExecutablePath {
    param(
        [string]$PreferredExePath
    )

    if (-not [string]::IsNullOrWhiteSpace($PreferredExePath)) {
        if (Test-Path -LiteralPath $PreferredExePath -PathType Leaf) {
            return (Resolve-Path -LiteralPath $PreferredExePath).Path
        }

        throw "RAM executable path '$PreferredExePath' does not exist."
    }

    $roots = @(
        "C:\Program Files\Bentley\Engineering\RAM Structural System",
        "C:\Program Files\Bentley\Engineering\RAM Structural System\Prog",
        "C:\Program Files (x86)\Bentley\Engineering\RAM Structural System",
        "C:\Program Files (x86)\Bentley\Engineering\RAM Structural System\Prog"
    )

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            continue
        }

        foreach ($exeName in @("RamManager.exe", "RAMManager.exe")) {
            $direct = Join-Path -Path $root -ChildPath $exeName
            if (Test-Path -LiteralPath $direct -PathType Leaf) {
                return (Resolve-Path -LiteralPath $direct).Path
            }
        }
    }

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            continue
        }

        $match = Get-ChildItem -LiteralPath $root -Recurse -File -Filter "RamManager.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -ne $match) {
            return $match.FullName
        }
    }

    return $null
}

function Resolve-BlankRamModelPath {
    param(
        [string]$RequestedModelPath,
        [string]$RequestedOutputDirectory,
        [string]$RequestedModelName
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedModelPath)) {
        $fullPath = [System.IO.Path]::GetFullPath($RequestedModelPath)
        $directory = Split-Path -Parent $fullPath
        if (-not [string]::IsNullOrWhiteSpace($directory)) {
            New-Item -ItemType Directory -Force -Path $directory | Out-Null
        }

        return $fullPath
    }

    $outputDirectoryValue = if ([string]::IsNullOrWhiteSpace($RequestedOutputDirectory)) {
        Join-Path -Path (Get-Location) -ChildPath "out\ram-blank"
    }
    else {
        $RequestedOutputDirectory
    }

    New-Item -ItemType Directory -Force -Path $outputDirectoryValue | Out-Null
    $resolvedOutputDirectory = (Resolve-Path -LiteralPath $outputDirectoryValue).Path

    $fileName = if ([string]::IsNullOrWhiteSpace($RequestedModelName)) {
        "agentic-ram-blank-{0}.rss" -f (Get-Date -Format "yyyyMMdd-HHmmss")
    }
    else {
        $RequestedModelName
    }

    if ([System.IO.Path]::GetExtension($fileName) -eq "") {
        $fileName = "$fileName.rss"
    }

    return Join-Path -Path $resolvedOutputDirectory -ChildPath $fileName
}

function New-BlankRamDatabase {
    param(
        [string]$Path,
        [int]$UnitValue,
        [string]$Name
    )

    if (Test-Path -LiteralPath $Path) {
        throw "Blank RAM model path already exists: '$Path'. Pass a different -ModelPath or -ModelName."
    }

    $rda = New-Object -ComObject "RAMDataAccess.RamDataAccess1"
    $database = $rda.GetDispInterfacePointerByEnum(10)
    $returnCode = $database.CreateNewDatabase2($Path, $UnitValue, $Name)
    Assert-RamSuccess -ReturnCode $returnCode -Operation "CreateNewDatabase2"

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "CreateNewDatabase2 returned success, but no .rss file was found at '$Path'."
    }

    return [pscustomobject]@{
        Path = (Resolve-Path -LiteralPath $Path).Path
        Units = $UnitValue
        JobName = $Name
        ReturnCode = $returnCode
    }
}

function Open-RamManagerModel {
    param(
        [string]$Path,
        [string]$ExecutablePath,
        [int]$DelaySeconds
    )

    $resolvedExe = Find-RamExecutablePath -PreferredExePath $ExecutablePath
    if ([string]::IsNullOrWhiteSpace($resolvedExe)) {
        throw "No RAM Manager executable was found. Pass -RamExePath explicitly."
    }

    $beforeIds = @(Get-Process -Name "RamManager" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    $process = Start-Process -FilePath $resolvedExe -ArgumentList @($Path) -PassThru

    if ($DelaySeconds -gt 0) {
        Start-Sleep -Seconds $DelaySeconds
    }

    $after = @(Get-Process -Name "RamManager" -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending)
    $newProcess = $after | Where-Object { $_.Id -notin $beforeIds } | Select-Object -First 1
    $ramProcess = if ($null -ne $newProcess) { $newProcess } else { Get-RamProcess -RequestedPid $process.Id }
    if ($null -eq $ramProcess) {
        $ramProcess = Get-RamProcess -RequestedPid 0
    }

    return [pscustomobject]@{
        RequestedProcessId = $process.Id
        ProcessId = if ($null -ne $ramProcess) { $ramProcess.Id } else { $null }
        ProcessName = if ($null -ne $ramProcess) { $ramProcess.ProcessName } else { $null }
        MainWindowTitle = if ($null -ne $ramProcess) { $ramProcess.MainWindowTitle } else { $null }
        ExecutablePath = $resolvedExe
        NewProcessDetected = $null -ne $newProcess
    }
}

$resolvedModelPath = Resolve-BlankRamModelPath -RequestedModelPath $ModelPath -RequestedOutputDirectory $OutputDirectory -RequestedModelName $ModelName
$databaseResult = New-BlankRamDatabase -Path $resolvedModelPath -UnitValue $Units -Name $JobName

$launchResult = $null
if (-not $NoLaunch) {
    $launchResult = Open-RamManagerModel -Path $databaseResult.Path -ExecutablePath $RamExePath -DelaySeconds $WaitSeconds
}

$result = [pscustomobject]@{
    Message = "opened blank RAM model"
    ModelPath = $databaseResult.Path
    Units = $databaseResult.Units
    JobName = $databaseResult.JobName
    Created = $true
    Launched = -not [bool]$NoLaunch
    Launch = $launchResult
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 6
}
else {
    $result
}
