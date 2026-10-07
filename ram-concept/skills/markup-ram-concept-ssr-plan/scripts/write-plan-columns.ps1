# write-plan-columns.ps1 -Workbook <SSR.xlsx> -Report <placements.json> [-Sheet 'B2 SSR Input'] [-Header 'Plan Col. (S101D)']
#
# Put the drawing's column number beside each stud rail row of the SSR workbook, from the plan markup's report
# (markup_ssr_plan.py --report): each placement has the Concept (x, y) and the bubble number it was tagged at.
# A column headed -Header is inserted right after the 'Column at (x, y) ft' column (or reused if it exists) and
# filled by matching "(x, y)". Rows with no placement are left blank and listed.
#
# Works on the workbook as the engineer has it: if it is open in a running Excel, that session is used and the
# workbook saved there (he sees the column appear); otherwise a hidden Excel opens and closes it. Through Excel,
# not openpyxl, so the images, formats, names and formulas survive.
param(
    [Parameter(Mandatory = $true)][string]$Workbook,
    [Parameter(Mandatory = $true)][string]$Report,
    [string]$Sheet = '',
    [string]$Header = 'Plan Col. (S101D)'
)
$ErrorActionPreference = 'Stop'
$Workbook = (Resolve-Path $Workbook).Path
$rep = Get-Content $Report -Raw | ConvertFrom-Json
$map = @{}
foreach ($p in $rep.placements) { if ($p.bubble -and $p.bubble -ne '?') { $map["($([int]$p.x), $([int]$p.y))"] = [string]$p.bubble } }
"$($map.Count) columns mapped from $Report"

$attached = $false; $xl = $null; $wb = $null
try { $xl = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application') } catch { }
if ($xl) {
    foreach ($w in $xl.Workbooks) { if ($w.FullName -ieq $Workbook) { $wb = $w; $attached = $true } }
}
if (-not $wb) {
    if (Test-Path (Join-Path (Split-Path $Workbook) ('~$' + (Split-Path $Workbook -Leaf)))) { throw "$Workbook is open elsewhere (lock file) and not in a reachable Excel" }
    $xl = New-Object -ComObject Excel.Application
    $xl.Visible = $false; $xl.DisplayAlerts = $false
    $wb = $xl.Workbooks.Open($Workbook)
}
try {
    if ($wb.ReadOnly) { throw "$Workbook is open read-only" }
    $ws = $null
    foreach ($s in $wb.Worksheets) { if (($Sheet -and $s.Name -eq $Sheet) -or (-not $Sheet -and $s.Name -like '*SSR Input*' -and -not $ws)) { $ws = $s } }
    if (-not $ws) { throw "no sheet $($Sheet) / '*SSR Input*' in $Workbook" }
    $last = $ws.Cells.Item($ws.Rows.Count, 2).End(-4162).Row            # last Mk
    $xyCol = 0; $planCol = 0
    for ($c = 1; $c -le 40; $c++) {
        $h = [string]$ws.Cells.Item(3, $c).Text
        if ($h -like 'Column at*') { $xyCol = $c }
        if ($h -eq $Header) { $planCol = $c }
    }
    if (-not $xyCol) { throw "no 'Column at (x, y) ft' header in row 3 of $($ws.Name)" }
    if (-not $planCol) {
        $planCol = $xyCol + 1
        [void]$ws.Columns.Item($planCol).Insert(-4161)                  # shift right; the type table formulas follow their cells
        $ws.Cells.Item(3, $planCol).Value2 = $Header
        $ws.Cells.Item(3, $xyCol).Copy() | Out-Null
        $ws.Cells.Item(3, $planCol).PasteSpecial(-4122) | Out-Null       # formats only
        $xl.CutCopyMode = $false
        $ws.Cells.Item(3, $planCol).Value2 = $Header
        $ws.Columns.Item($planCol).ColumnWidth = 9
        "inserted column $planCol headed '$Header'"
    }
    $missing = @(); $n = 0
    for ($r = 5; $r -le $last; $r++) {
        $key = ([string]$ws.Cells.Item($r, $xyCol).Text).Trim() -replace '\s+', ' '
        if (-not $key) { continue }
        if ($map.ContainsKey($key)) { $ws.Cells.Item($r, $planCol).Value2 = [double]$map[$key]; $n++ }
        else { $missing += "row $r $key" }
    }
    $ws.Range($ws.Cells.Item(5, $planCol), $ws.Cells.Item($last, $planCol)).HorizontalAlignment = -4108
    if ($ws.AutoFilterMode) { $ws.AutoFilterMode = $false }
    [void]$ws.Range($ws.Cells.Item(3, 2), $ws.Cells.Item($last, $planCol)).AutoFilter()
    $wb.Save()
    "$n rows filled in '$($ws.Name)' column $planCol; saved $Workbook" + $(if ($attached) { ' (in the running Excel)' } else { '' })
    if ($missing) { "no plan column for: " + ($missing -join '; ') }
}
finally {
    if (-not $attached) {
        $wb.Close($false); $xl.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
        [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    }
}
