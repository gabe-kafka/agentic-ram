param(
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-SafeRamCheck {
    param(
        [string]$Name,
        [scriptblock]$Body
    )

    try {
        $value = & $Body
        return [pscustomobject]@{
            Check = $Name
            Success = $true
            Value = $value
            Error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            Check = $Name
            Success = $false
            Value = $null
            Error = $_.Exception.Message
        }
    }
}

$checks = New-Object System.Collections.Generic.List[object]

$rda = New-Object -ComObject "RAMDataAccess.RamDataAccess1"
$checks.Add([pscustomobject]@{
        Check = "Create RAMDataAccess COM object"
        Success = $true
        Value = "RAMDataAccess.RamDataAccess1"
        Error = $null
    }) | Out-Null

$database = $rda.GetDispInterfacePointerByEnum(10)
$checks.Add([pscustomobject]@{
        Check = "Get database interface"
        Success = $true
        Value = "EINTERFACES enum 10"
        Error = $null
    }) | Out-Null

$checks.Add((Invoke-SafeRamCheck -Name "Get loaded model path" -Body {
            $status = 0
            $path = ""
            $database.iTAS_GetLoadedModelPath([ref]$status, [ref]$path)
            [pscustomobject]@{
                Status = $status
                Path = $path
            }
        })) | Out-Null

$checks.Add((Invoke-SafeRamCheck -Name "Get database interface methods" -Body {
            (($database | Get-Member -MemberType Method |
                    Select-Object -ExpandProperty Name |
                    Where-Object { $_ -in @("CreateNewDatabase2", "LoadDataBase2", "iTAS_GetLoadedModelPath", "CloseDatabase") }) -join ", ")
        })) | Out-Null

$result = [pscustomobject]@{
    Message = "RAM API hook check complete"
    Hooked = -not (@($checks.ToArray() | Where-Object { -not $_.Success }).Count -gt 0)
    ComProgId = "RAMDataAccess.RamDataAccess1"
    Checks = $checks.ToArray()
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 6
}
else {
    $result
}
