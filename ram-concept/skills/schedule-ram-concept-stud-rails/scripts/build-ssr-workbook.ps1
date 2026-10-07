# build-ssr-workbook.ps1 -Source <previous job's SSR.xlsx> -RowsJson <rows.json> -Out <new.xlsx> -Tag B2 -SourceTag B3
# Copies the office stud rail workbook from the previous building or job, keeps its two sheets as "<SourceTag> ..."
# reference copies, and fills the original two sheets ("<Tag> SSR Input", "<Tag> FOR CAD") from stud_rail_schedule.py.
# Hidden Excel instance; no clipboard, no keystrokes. Refuses to overwrite -Out.
# The source must be laid out like the 2636 Building 3 workbook: sheets "SSR Input" (rows from 5, formats to row 41,
# type table at P:X) and "FOR CAD" (8 formatted type rows). A workbook this script already built has renamed sheets:
# start from the original template, or rename its sheets back first.
# Status: the 2636 Building 2 workbook was built with the job's copy of this script (2026-10-06). This copy differs
# only in -Tag, -SourceTag and -StudSize and is parse-checked, not rerun.
param([Parameter(Mandatory = $true)][string]$Source, [Parameter(Mandatory = $true)][string]$RowsJson, [Parameter(Mandatory = $true)][string]$Out,
      [Parameter(Mandatory = $true)][string]$Tag, [Parameter(Mandatory = $true)][string]$SourceTag, [string]$StudSize = '3/4"')
$ErrorActionPreference = 'Stop'
if (Test-Path $Out) { throw "$Out exists" }
$rows = @(Get-Content $RowsJson -Raw | ConvertFrom-Json)
$n = $rows.Count
$last = 4 + $n
$marks = @($rows | Where-Object { $_.mk -ne 'NON-TYPICAL' } | ForEach-Object { $_.mk } | Sort-Object -Unique)   # a NON-TYPICAL row is listed but is no type
if ($marks.Count -gt 8) { throw 'more than 8 types: the FOR CAD sheet has 8 formatted rows' }
Copy-Item $Source $Out
$missing = [Type]::Missing
$before = @(Get-Process EXCEL -ErrorAction SilentlyContinue | ForEach-Object Id)
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($Out)
    $in = $wb.Worksheets.Item('SSR Input')
    $cad = $wb.Worksheets.Item('FOR CAD')

    # the source job stays as it was, on copies
    # the copy does not always land beside its source, so it is found by name; the order is set at the end
    function Copy-Sheet($sheet, $name) {
        $had = @(1..$wb.Worksheets.Count | ForEach-Object { $wb.Worksheets.Item($_).Name })
        $sheet.Copy($wb.Worksheets.Item(1))
        $new = @(1..$wb.Worksheets.Count | ForEach-Object { $wb.Worksheets.Item($_) } | Where-Object { $had -notcontains $_.Name })
        if ($new.Count -ne 1) { throw "copy of $($sheet.Name) not found" }
        $new[0].Name = $name
        $new[0]
    }
    $b3in = Copy-Sheet $in "$SourceTag SSR Input"
    $b3cad = Copy-Sheet $cad "$SourceTag FOR CAD"
    $b3cad.Range('A5').Formula2 = "=SORT(FILTER('$SourceTag SSR Input'!B5:I41,'$SourceTag SSR Input'!J5:J41=""Y"",""No matching data""),1,1)"
    foreach ($sheet in $b3in, $b3cad) { for ($i = $sheet.Names.Count; $i -ge 1; $i--) { $sheet.Names.Item($i).Delete() } }
    $in.Name = "$Tag SSR Input"
    $cad.Name = "$Tag FOR CAD"
    # ORDER is a hidden sheet in the 2636 Building 3 file and stays hidden; the four visible tabs go in this order
    $tabs = "$Tag SSR Input", "$SourceTag SSR Input", "$Tag FOR CAD", "$SourceTag FOR CAD"
    for ($i = $tabs.Count - 1; $i -ge 0; $i--) { $wb.Worksheets.Item($tabs[$i]).Move($wb.Worksheets.Item(1)) }
    $shown = @(1..$wb.Worksheets.Count | ForEach-Object { $wb.Worksheets.Item($_) } | Where-Object { $_.Visible -eq -1 } | ForEach-Object Name)
    if (($shown -join '|') -ne ($tabs -join '|')) { throw "tab order is $($shown -join ' | ')" }

    # this job's input rows
    foreach ($a in 'A5:J41', 'M5:N41', 'P5:S41', 'U3:X41') { [void]$in.Range($a).ClearContents() }
    [void]$in.Range('A38:N38').Copy($in.Range("A39:N$last"))                   # formats and the K, L formulas; row 38 is already cleared
    $in.Range("39:$last").RowHeight = $in.Range('38:38').RowHeight
    $cells = New-Object 'object[,]' $n, 10
    for ($i = 0; $i -lt $n; $i++) {
        $r = $rows[$i]
        $cells[$i, 0] = [double]($i + 1); $cells[$i, 1] = $r.mk; $cells[$i, 2] = $StudSize
        $cells[$i, 3] = [double]$r.rails; $cells[$i, 4] = [double]$r.studs; $cells[$i, 5] = 'A'
        $cells[$i, 6] = [double]$r.typical; $cells[$i, 7] = [double]$r.first; $cells[$i, 8] = [string]$r.comment
        $cells[$i, 9] = $(if ($r.controlling) { 'Y' } else { $null })
    }
    $in.Range("A5:J$last").Value2 = $cells
    $in.Range("J5:J$last").HorizontalAlignment = -4108
    $slab = New-Object 'object[,]' $n, 1
    $where = New-Object 'object[,]' $n, 1
    for ($i = 0; $i -lt $n; $i++) { $slab[$i, 0] = [double]$rows[$i].slab; $where[$i, 0] = "($($rows[$i].x), $($rows[$i].y))" }
    $in.Range("M5:M$last").Value2 = $slab
    $in.Range("M5:M$last").HorizontalAlignment = -4108
    $in.Range("N5:N$last").Formula = '=M5-2'
    $in.Range("N5:N$last").NumberFormat = '0.00'
    $in.Range("N5:N$last").HorizontalAlignment = -4108
    $in.Range("O5:O$last").NumberFormat = '@'
    $in.Range("O5:O$last").Value2 = $where
    $in.Range("O5:O$last").HorizontalAlignment = -4108
    $in.Range('O3:O4').Merge()
    $in.Range('O3').Value2 = 'Column at (x, y) ft'
    $in.Range('O3').Font.Bold = $true
    $in.Range('O3').WrapText = $true
    $in.Range('O3').HorizontalAlignment = -4108
    $in.Range('O3').VerticalAlignment = -4108
    $in.Columns.Item('O').ColumnWidth = 14
    $in.Range('B5').FormatConditions.Item(1).ModifyAppliesToRange($in.Range("B5:B$last"))
    if ($in.AutoFilterMode) { $in.AutoFilterMode = $false; [void]$in.Range("B3:O$last").AutoFilter() }   # the header filter stopped at row 41

    # type table beside the rows, as on the source sheet, by formula from the controlling rows
    $head = @{ U4 = 'Mk'; V4 = 'Columns'; W4 = 'L'; X4 = 'Covers type' }
    foreach ($k in $head.Keys) { $in.Range($k).Value2 = $head[$k]; $in.Range($k).HorizontalAlignment = -4108 }
    $pick = 'INDEX(${0}$5:${0}${1},MATCH(1,INDEX(($B$5:$B${1}=$U{2})*($J$5:$J${1}="Y"),0),0))'
    for ($i = 0; $i -lt $marks.Count; $i++) {
        $row = 5 + $i
        $in.Range("U$row").Value2 = $marks[$i]
        $in.Range("P$row").Formula = '=' + ($pick -f 'E', $last, $row)
        $in.Range("Q$row").Formula = '=' + ($pick -f 'F', $last, $row)
        $in.Range("R$row").Formula = '=' + ($pick -f 'G', $last, $row)
        $in.Range("S$row").Formula = '=' + ($pick -f 'H', $last, $row)
        $in.Range("V$row").Formula = "=COUNTIF(`$B`$5:`$B`$$last,`$U$row)"
        $in.Range("W$row").Formula = "=(S$row+(P$row-1)*R$row)/12"
        $g = "`$B`$5:`$B`$$last,`$U$row"
        $in.Range("X$row").Formula2 = "=IF(AND(R$row<=MINIFS(`$G`$5:`$G`$$last,$g),S$row<=MINIFS(`$H`$5:`$H`$$last,$g),W$row+0.005>=MAXIFS(`$L`$5:`$L`$$last,$g),MINIFS(`$D`$5:`$D`$$last,$g)=MAXIFS(`$D`$5:`$D`$$last,$g)),""OK"",""CHECK"")"
    }
    $in.Range("V5:X$(4 + $marks.Count)").HorizontalAlignment = -4108

    # this job's schedule for CAD
    $cad.Range('A5').Formula2 = "=SORT(FILTER('$Tag SSR Input'!B5:I$last,'$Tag SSR Input'!J5:J$last=""Y"",""No matching data""),1,1)"
    for ($i = $marks.Count; $i -lt 8; $i++) { [void]$cad.Rows.Item(5 + $marks.Count).Delete() }

    $xl.CalculateFull()
    $in.Activate()
    $wb.Save()
    "$n rows, $($marks.Count) types; tabs: " + ($shown -join ' | ')
    "names: " + (($wb.Names | ForEach-Object { $_.Name + ' ' + $_.RefersTo }) -join ' ; ')
    $wb.Close($false)
}
finally {
    $xl.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    Start-Sleep -Seconds 2
    Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | Stop-Process -Force
}
"built $Out"
