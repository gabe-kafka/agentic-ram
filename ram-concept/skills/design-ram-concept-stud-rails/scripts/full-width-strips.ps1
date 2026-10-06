# full-width-strips.ps1 [-ProcId N] [-Box "-100,-100;600,600"] : on the ACTIVE Design Spans plan, select every span
# with one typed selection box, open Selection Properties (Ctrl+E) and set Column Strip Width Calc to Full Width.
# Run once per direction (Latitude plan, then Longitude plan). Beam spans get Full Width too: restore them
# afterwards with ../../set-ram-concept-beam-strips/scripts/apply-beam-strips.ps1. Prove the result from the
# saved file (SpanSegment.ColumnStripWidthCalc), not from this script's output.
# Needs an attached display, Concept 2025 maximized at 100% scaling, the Scripting Server paused, and nobody
# else on the mouse or keyboard. With more than one Concept open it acts only on the API session, or -ProcId.
param([int]$ProcId = 0, [string]$Box = "-100,-100;600,600", [int]$MinItems = 50)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
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
 public static void Click(int x, int y) { SetCursorPos(x, y); System.Threading.Thread.Sleep(90); mouse_event(2,0,0,0,UIntPtr.Zero); mouse_event(4,0,0,0,UIntPtr.Zero); }
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
$CommandLine = @(520, ($H - 21)); $PromptPixel = @(454, ($H - 37))    # same calibration as punch-radius.ps1
function Keys($k) { [System.Windows.Forms.SendKeys]::SendWait($k); Start-Sleep -Milliseconds 300 }
function Red($x, $y) { $b = New-Object Drawing.Bitmap 1, 1; $g = [Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($x, $y, 0, 0, $b.Size); $r = $b.GetPixel(0, 0).R; $g.Dispose(); $b.Dispose(); $r }
function Prompt { if ((Red ($OX + $PromptPixel[0]) ($OY + $PromptPixel[1])) -eq 255) { 'one' } else { 'opposite' } }
function CmdLine { [FW]::Click($OX + $CommandLine[0], $OY + $CommandLine[1]); Start-Sleep -Milliseconds 350 }
function Dialog { [FW]::Find($procId, 'Selected Items') -split '\|' }

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
Keys '^e'
$d = @(); foreach ($try in 1..20) { Start-Sleep -Milliseconds 400; $d = Dialog; if ($d.Count -ge 6) { break } }
if ($d.Count -lt 6) { throw 'Selection Properties dialog did not open' }
$n = 0; if ($d[1] -match 'Edit (\d+) Selected Items') { $n = [int]$Matches[1] }
if ($n -lt $MinItems) { Keys '{ESC}'; throw "dialog '$($d[1])': fewer than $MinItems items selected; is the Design Spans plan active?" }
Start-Sleep -Milliseconds 700
$L = [int]$d[2]; $T = [int]$d[3]
[FW]::Click($L + 131, $T + 48); Start-Sleep -Milliseconds 450          # Strip Generation tab
[FW]::Click($L + 258, $T + 135); Start-Sleep -Milliseconds 450         #   Column Strip Width Calc dropdown
Keys 'Full'; Keys '{ENTER}'                                             #   -> Full Width
[FW]::Click($L + 380, $T + 612)                                         # OK
$open = $d; foreach ($try in 1..20) { Start-Sleep -Milliseconds 400; $open = Dialog; if ($open.Count -lt 6) { break } }
Start-Sleep -Milliseconds 800
"$n spans set to Full Width" + $(if ($open.Count -ge 6) { " WARNING dialog still open: $($open[1])" } else { '' })
