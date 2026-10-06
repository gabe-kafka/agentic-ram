# punch-radius.ps1 -Points "x,y;x,y" -Radius 10: on the ACTIVE Punching Checks plan, select the check at each point
# (typed selection box), open Selection Properties (Ctrl+E) and set Maximum Search Radius. Prove it from a saved file.
# -ReadOnly reopens each check, saves a picture of the radius field beside this script and cancels.
# Needs an attached display, Concept 2025 maximized at 100% scaling, the Scripting Server paused, and
# nobody else on the mouse or keyboard. The prompt test reads the status bar: the command-line edit box
# starts further right while the prompt says 'Enter opposite corner point:'.
# With more than one Concept open (say, one launched from RAM Manager) it acts only on the API session, or on -ProcId.
param([Parameter(Mandatory = $true)][string]$Points, [double]$Radius = 0, [double]$Half = 0.2, [switch]$ReadOnly, [int]$ProcId = 0)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public static class PS1 {
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
[PS1]::SetProcessDPIAware() | Out-Null
if (-not $ProcId) {
    $api = @(Get-CimInstance Win32_Process -Filter "Name='Concept.exe'" | Where-Object { $_.CommandLine -match '-apiServer' })
    if ($api.Count -ne 1) { throw "need exactly one API Concept session, found $($api.Count); pass -ProcId" }
    $ProcId = $api[0].ProcessId
}
$procId = [uint32]$ProcId
$main = [PS1]::Find($procId, 'RAM Concept') -split '\|'
if ($main.Count -lt 6) { throw 'RAM Concept main window not found' }
[PS1]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [PS1]::keybd_event(0x12,0,2,[UIntPtr]::Zero)
[PS1]::SetForegroundWindow([IntPtr][long]$main[0]) | Out-Null; Start-Sleep -Milliseconds 500
$OX = [int]$main[2]; $OY = [int]$main[3]; $H = [int]$main[5] - $OY
$EditMenu = @(60, 43); $SelectionProperties = @(133, 250)
# the edit box (white) starts at x 440 for 'Enter one corner point:' and at x 475 for 'Enter opposite corner point:'
$CommandLine = @(520, ($H - 21)); $PromptPixel = @(454, ($H - 37))
function Keys($k) { [System.Windows.Forms.SendKeys]::SendWait($k); Start-Sleep -Milliseconds 300 }
function Red($x, $y) { $b = New-Object Drawing.Bitmap 1, 1; $g = [Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($x, $y, 0, 0, $b.Size); $r = $b.GetPixel(0, 0).R; $g.Dispose(); $b.Dispose(); $r }
function Prompt { if ((Red ($OX + $PromptPixel[0]) ($OY + $PromptPixel[1])) -eq 255) { 'one' } else { 'opposite' } }
function CmdLine { [PS1]::Click($OX + $CommandLine[0], $OY + $CommandLine[1]); Start-Sleep -Milliseconds 350 }
function SelectAt($x, $y) {
    foreach ($attempt in 1..3) {
        CmdLine
        if ((Prompt) -eq 'opposite') { Keys '-60,-60{ENTER}'; Keys '{ESC}'; Start-Sleep -Milliseconds 400; CmdLine }
        if ((Prompt) -ne 'one') { continue }
        Keys ('{0:0.00},{1:0.00}{{ENTER}}' -f ($x - $Half), ($y - $Half)); Start-Sleep -Milliseconds 300
        if ((Prompt) -ne 'opposite') { continue }
        Keys ('{0:0.00},{1:0.00}{{ENTER}}' -f ($x + $Half), ($y + $Half)); Start-Sleep -Milliseconds 500
        if ((Prompt) -eq 'one') { return $true }
    }
    return $false
}
function Dialog { [PS1]::Find($procId, 'Selected Items') -split '\|' }
foreach ($pt in ($Points -split ';')) {
    $x, $y = $pt -split ',' | ForEach-Object { [double]$_ }
    if (-not (SelectAt $x $y)) { "$pt SKIPPED could not place the selection box"; continue }
    Keys '^e'
    $d = @(); foreach ($try in 1..15) { Start-Sleep -Milliseconds 400; $d = Dialog; if ($d.Count -ge 6) { break } }
    if ($d.Count -lt 6 -or $d[1] -ne 'Edit 1 Selected Items') { "$pt SKIPPED dialog='$($d[1])'"; if ($d.Count -ge 6) { Keys '{ESC}' }; Start-Sleep -Milliseconds 500; continue }
    Start-Sleep -Milliseconds 700
    $L = [int]$d[2]; $T = [int]$d[3]
    if ($ReadOnly) { $b = New-Object Drawing.Bitmap 520, 30; $g = [Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($L + 60, $T + 88, 0, 0, $b.Size); $b.Save("$PSScriptRoot\radius-$($pt -replace ',','_').png"); $g.Dispose(); $b.Dispose(); [PS1]::Click($L + 708, $T + 735); Start-Sleep -Milliseconds 900; "$pt read"; continue }
    [PS1]::Click($L + 398, $T + 103); Start-Sleep -Milliseconds 400       # Maximum Search Radius (General tab)
    Keys '^a'; Keys "$Radius"; Keys '{TAB}'
    [PS1]::Click($L + 608, $T + 735)                                      # OK
    $open = $d; foreach ($try in 1..15) { Start-Sleep -Milliseconds 400; $open = Dialog; if ($open.Count -lt 6) { break } }
    Start-Sleep -Milliseconds 800
    "$pt radius set to $Radius" + $(if ($open.Count -ge 6) { " WARNING dialog still open: $($open[1])" } else { '' })
}
