# full-width-strips.ps1 [-ProcId N] [-Box "-100,-100;600,600"] : on the ACTIVE Design Spans plan, select everything
# with one typed selection box, keep only the span segments (right-click > Selection Filter), open Selection
# Properties from the same context menu and set Column Strip Width Calc to Full Width.
# Run once per direction (Latitude plan, then Longitude plan). Beam spans get Full Width too: restore them
# afterwards with ../../set-ram-concept-beam-strips/scripts/apply-beam-strips.ps1. Prove the result from the
# saved file (SpanSegment.ColumnStripWidthCalc), not from this script's output.
# Needs an attached display, Concept 2025 maximized at 100% scaling, the Scripting Server paused, and nobody
# else on the mouse or keyboard. With more than one Concept open it acts only on the API session, or -ProcId.
# Status 2026-10-06: the box selection and the Full Width edit were proven on 2636 (the saved file showed 219 spans
# at full width); the Selection Filter step by position has not been run end to end. Check the dialog title it
# prints: "Edit <span count> Selected Items" means the filter worked.
# The command line is found by scanning the status bar row (RowY pixels above the window's bottom edge) for the
# white edit box. The box starts about 35 px further right while the prompt reads "Enter opposite corner point:",
# so a start at or left of -OneStartMax means "Enter one corner point:". Main monitor on the 2636 PC: box at 440
# or 475, OneStartMax 457; the upper monitor: 345 or 380, OneStartMax 362. Check once with a screenshot.
# -Blank is a window point on the plan canvas with nothing under it, for the right-click.
param([int]$ProcId = 0, [string]$Box = "-100,-100;600,600", [int]$MinItems = 50, [int]$RowY = 23, [int]$OneStartMax = 457,
      [string]$Blank = "700,600", [int]$SpanRow = 2)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing, UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public static class FW {
 public delegate bool P(IntPtr h, IntPtr l);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 [DllImport("user32.dll")] static extern bool EnumWindows(P p, IntPtr l);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f, int x, int y, uint d, UIntPtr e);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, UIntPtr e);
 public static string Find(uint pid, string contains) { string found = ""; EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
   if (p==pid && IsWindowVisible(h) && found=="") { var t=new StringBuilder(256); GetWindowText(h,t,256);
     if (t.ToString().Contains(contains)) { RECT r; GetWindowRect(h,out r); found = h + "|" + t + "|" + r.L + "|" + r.T + "|" + r.R + "|" + r.B; } } return true; }, IntPtr.Zero); return found; }
 public static void Click(int x, int y, bool right) { SetCursorPos(x, y); System.Threading.Thread.Sleep(90);
   if (right) { mouse_event(8,0,0,0,UIntPtr.Zero); mouse_event(16,0,0,0,UIntPtr.Zero); } else { mouse_event(2,0,0,0,UIntPtr.Zero); mouse_event(4,0,0,0,UIntPtr.Zero); } }
}
'@
[FW]::SetProcessDPIAware() | Out-Null
if (-not $ProcId) {
    $api = @(Get-CimInstance Win32_Process -Filter "Name='Concept.exe'" | Where-Object { $_.CommandLine -match '-apiServer' })
    if ($api.Count -ne 1) { throw "need exactly one API Concept session, found $($api.Count); pass -ProcId" }
    $ProcId = $api[0].ProcessId
}
$procId = [uint32]$ProcId
$main = [FW]::Find($procId, 'RAM Concept') -split '\|'
if ($main.Count -lt 6) { throw 'RAM Concept main window not found' }
[FW]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [FW]::keybd_event(0x12,0,2,[UIntPtr]::Zero)
[FW]::SetForegroundWindow([IntPtr][long]$main[0]) | Out-Null; Start-Sleep -Milliseconds 500
$OX = [int]$main[2]; $OY = [int]$main[3]; $H = [int]$main[5] - $OY
$RowAbs = $OY + $H - $RowY
$bx, $by = $Blank -split ',' | ForEach-Object { [int]$_ }
function Keys($k) { [System.Windows.Forms.SendKeys]::SendWait($k); Start-Sleep -Milliseconds 300 }
function BoxStart {
    # x (window offset) where the white command-line edit box starts in the status bar row, or -1
    $b = New-Object Drawing.Bitmap 700, 1; $g = [Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($OX + 200, $RowAbs, 0, 0, $b.Size); $g.Dispose()
    $start = -1; $run = 0                                   # the first white run at least 20 px wide (panel separators are 1 px)
    for ($x = 0; $x -lt 700; $x++) {
        $c = $b.GetPixel($x, 0)
        if ($c.R -ge 250 -and $c.G -ge 250 -and $c.B -ge 250) { $run++; if ($run -ge 20) { $start = 200 + $x - $run + 1; break } } else { $run = 0 }
    }
    $b.Dispose(); $start
}
function Prompt { $s = BoxStart; if ($s -lt 0) { 'none' } elseif ($s -le $OneStartMax) { 'one' } else { 'opposite' } }
function CmdLine { $s = BoxStart; if ($s -lt 0) { throw 'no command line box in the status bar; is a plan active?' }; [FW]::Click($OX + $s + 40, $RowAbs, $false); Start-Sleep -Milliseconds 350 }
function Win($title) { [FW]::Find($procId, $title) -split '\|' }
function WaitWin($title) { $d = @(); foreach ($try in 1..20) { Start-Sleep -Milliseconds 400; $d = Win $title; if ($d.Count -ge 6) { return $d } }; return @() }
function ContextItem($dx, $dy) {
    # right-click the blank canvas point, then click the menu item at this offset from it
    [FW]::Click($OX + $bx, $OY + $by, $true); Start-Sleep -Milliseconds 900
    [FW]::Click($OX + $bx + $dx, $OY + $by + $dy, $false); Start-Sleep -Milliseconds 900
}

# 1. box-select everything on the active plan
$c0, $c1 = $Box -split ';'
$selected = $false
foreach ($attempt in 1..3) {
    CmdLine
    if ((Prompt) -eq 'opposite') { Keys '-60,-60{ENTER}'; Keys '{ESC}'; Start-Sleep -Milliseconds 400; CmdLine }
    if ((Prompt) -ne 'one') { continue }
    Keys "$c0{ENTER}"; Start-Sleep -Milliseconds 300
    if ((Prompt) -ne 'opposite') { continue }
    Keys "$c1{ENTER}"; Start-Sleep -Milliseconds 800
    if ((Prompt) -eq 'one') { $selected = $true; break }
}
if (-not $selected) { throw 'could not place the selection box' }

# 2. keep only the span segments: right-click > Selection Filter..., Clear All, tick the Span Segment row, OK.
#    The list's check boxes are not exposed to UI Automation (tried 2026-10-06), so this goes by position: the list is
#    alphabetical, and on a Design Spans plan it reads Span Boundary, Span Segment, Strip Boundary, so Span Segment is
#    row 2 (-SpanRow). A picture of the dialog is saved beside this script as filter-last.png for the record.
ContextItem 77 38
$f = WaitWin 'Selection Filter'
if ($f.Count -lt 6) { throw 'the Selection Filter dialog did not open' }
$FL = [int]$f[2]; $FT = [int]$f[3]
[FW]::Click($FL + 55, $FT + 84, $false); Start-Sleep -Milliseconds 350                 # Clear All (Check All is the button above it)
[FW]::Click($FL + 111, $FT + 52 + 20 * ($SpanRow - 1), $false); Start-Sleep -Milliseconds 350   # the Span Segment row's box
$shot = New-Object Drawing.Bitmap ([int]$f[4] - $FL), ([int]$f[5] - $FT); $g = [Drawing.Graphics]::FromImage($shot)
$g.CopyFromScreen($FL, $FT, 0, 0, $shot.Size); $shot.Save("$PSScriptRoot\filter-last.png"); $g.Dispose(); $shot.Dispose()
[FW]::Click($FL + 237, $FT + 252, $false); Start-Sleep -Milliseconds 900                # OK

# 3. Selection Properties from the context menu
ContextItem 92 15
$d = WaitWin 'Selected Items'
if ($d.Count -lt 6) { throw 'Selection Properties dialog did not open' }
$n = 0; if ($d[1] -match 'Edit (\d+) Selected Items') { $n = [int]$Matches[1] }
if ($n -lt $MinItems) { Keys '{ESC}'; throw "dialog '$($d[1])': fewer than $MinItems items selected; is the Design Spans plan active?" }
Start-Sleep -Milliseconds 700
$L = [int]$d[2]; $T = [int]$d[3]
[FW]::Click($L + 131, $T + 48, $false); Start-Sleep -Milliseconds 450          # Strip Generation tab
[FW]::Click($L + 258, $T + 135, $false); Start-Sleep -Milliseconds 450         #   Column Strip Width Calc dropdown
Keys 'Full'; Keys '{ENTER}'                                                     #   -> Full Width
[FW]::Click($L + 380, $T + 612, $false)                                         # OK
$open = $d; foreach ($try in 1..20) { Start-Sleep -Milliseconds 400; $open = Win 'Selected Items'; if ($open.Count -lt 6) { break } }
Start-Sleep -Milliseconds 800
"$n spans set to Full Width" + $(if ($open.Count -ge 6) { " WARNING dialog still open: $($open[1])" } else { '' })
