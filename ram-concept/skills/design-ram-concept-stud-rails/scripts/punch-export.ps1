# punch-export.ps1 -Out <file.txt> [-Tree "x,y"] [-Export "x,y"]: export Design Status > Tables > Punching Check Analysis.
# Double-clicks the table in the Report Sections tree, presses Export... and types the file name into the
# "Export Entity Table" dialog. Then run punch_status.py on the file.
# Needs an attached display, Concept 2025 maximized at 100% scaling, the Scripting Server paused, a calculated
# model, and nobody else on the mouse or keyboard. -Tree and -Export are window positions of the tree item and
# the Export... button; the defaults are for the tree with Design Status and its Tables expanded and the
# Design Strip, Reinforcement and prestressing folders above it as on 2636. Check them on a screenshot first.
# With more than one Concept open (say, one launched from RAM Manager) it acts only on the API session, or on -ProcId.
param([Parameter(Mandatory = $true)][string]$Out, [string]$Tree = '210,583', [string]$Export = '1130,165', [int]$ProcId = 0)
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public static class PX {
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
     if (t.ToString().Contains(contains)) { RECT r; GetWindowRect(h,out r); found = h + "|" + r.L + "|" + r.T; } } return true; }, IntPtr.Zero); return found; }
 public static void Front(IntPtr h) { keybd_event(0x12,0,0,UIntPtr.Zero); keybd_event(0x12,0,2,UIntPtr.Zero); SetForegroundWindow(h); System.Threading.Thread.Sleep(300); }
 public static void Click(int x, int y, bool twice) { SetCursorPos(x, y); System.Threading.Thread.Sleep(90); mouse_event(2,0,0,0,UIntPtr.Zero); mouse_event(4,0,0,0,UIntPtr.Zero);
   if (twice) { System.Threading.Thread.Sleep(60); mouse_event(2,0,0,0,UIntPtr.Zero); mouse_event(4,0,0,0,UIntPtr.Zero); } }
}
'@
[PX]::SetProcessDPIAware() | Out-Null
if (Test-Path $Out) { throw "$Out exists" }
if (-not $ProcId) {
    $api = @(Get-CimInstance Win32_Process -Filter "Name='Concept.exe'" | Where-Object { $_.CommandLine -match '-apiServer' })
    if ($api.Count -ne 1) { throw "need exactly one API Concept session, found $($api.Count); pass -ProcId" }
    $ProcId = $api[0].ProcessId
}
$procId = [uint32]$ProcId
$main = [PX]::Find($procId, 'RAM Concept') -split '\|'
if ($main.Count -lt 3) { throw 'RAM Concept main window not found' }
$OX = [int]$main[1]; $OY = [int]$main[2]
$t = $Tree -split ',' | ForEach-Object { [int]$_ }; $e = $Export -split ',' | ForEach-Object { [int]$_ }
[PX]::Front([IntPtr][long]$main[0])
[PX]::Click($OX + $t[0], $OY + $t[1], $true); Start-Sleep -Seconds 3
[PX]::Click($OX + $e[0], $OY + $e[1], $false)
$dlg = @(); foreach ($try in 1..20) { Start-Sleep -Milliseconds 500; $dlg = [PX]::Find($procId, 'Export Entity Table') -split '\|'; if ($dlg.Count -ge 3) { break } }
if ($dlg.Count -lt 3) { throw 'the Export Entity Table dialog did not open; check -Tree and -Export on a screenshot' }
[PX]::Front([IntPtr][long]$dlg[0])
foreach ($k in '%n', '^a', $Out, '{ENTER}') { [System.Windows.Forms.SendKeys]::SendWait($k); Start-Sleep -Milliseconds 300 }
foreach ($try in 1..20) { Start-Sleep -Milliseconds 500; if (Test-Path $Out) { break } }
if (-not (Test-Path $Out)) { throw 'export file not written' }
"exported $((Get-Item $Out).Length) bytes to $Out"
