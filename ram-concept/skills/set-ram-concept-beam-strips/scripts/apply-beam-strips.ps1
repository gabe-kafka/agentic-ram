# apply-beam-strips.ps1 -Points "x,y;x,y" [-Kind T|L] -TopBar "#9" -BottomBar "#7" -TopCover 2 -BottomCover 2
#
# Drives the RAM Concept GUI: for each design span (picked by a typed selection box at its midpoint in the
# ACTIVE Design Spans plan) it opens Edit > Selection Properties and applies the office beam strip setup.
# Get the points and the typical slab values from beam_spans.py, and re-run beam_spans.py on a saved copy
# afterwards: that file check is the proof, not this script's "applied" lines.
#
# Needs: the Concept window maximized as calibrated below, the Scripting Server paused if it is an API
# session, the right Design Spans plan active, and nobody else using the mouse or keyboard.
param(
    [Parameter(Mandatory = $true)][string]$Points,
    [ValidateSet('T', 'L')][string]$Kind = 'T',
    [string]$TopBar = '#9', [string]$BottomBar = '#7',
    [double]$TopCover = 2, [double]$BottomCover = 2
)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing, UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public static class BeamStrip {
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
 // "handle|title|left|top|right|bottom" of the first visible window of the process whose title contains the text
 public static string Find(uint pid, string contains) { string found = ""; EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
   if (p==pid && IsWindowVisible(h) && found=="") { var t=new StringBuilder(256); GetWindowText(h,t,256);
     if (t.ToString().Contains(contains)) { RECT r; GetWindowRect(h,out r); found = h + "|" + t + "|" + r.L + "|" + r.T + "|" + r.R + "|" + r.B; } } return true; }, IntPtr.Zero); return found; }
 public static void Click(int x, int y) { SetCursorPos(x, y); System.Threading.Thread.Sleep(90); mouse_event(2,0,0,0,UIntPtr.Zero); mouse_event(4,0,0,0,UIntPtr.Zero); }
}
'@
[BeamStrip]::SetProcessDPIAware() | Out-Null
$procId = (Get-Process Concept | Select-Object -First 1).Id
$main = [BeamStrip]::Find($procId, 'RAM Concept') -split '\|'
if ($main.Count -lt 6) { throw 'RAM Concept main window not found' }
$OX = [int]$main[2]; $OY = [int]$main[3]; $H = [int]$main[5] - $OY

# Calibration (Concept 2025, maximized, 100% scaling): offsets from the main window's top-left corner.
$EditMenu = @(60, 43); $SelectionProperties = @(133, 250)
$CommandLine = @(440, ($H - 21)); $PromptPixel = @(365, ($H - 28))

function Keys($k) { [System.Windows.Forms.SendKeys]::SendWait($k); Start-Sleep -Milliseconds 300 }
function Red($x, $y) { $b = New-Object Drawing.Bitmap 1, 1; $g = [Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($x, $y, 0, 0, $b.Size); $r = $b.GetPixel(0, 0).R; $g.Dispose(); $b.Dispose(); $r }
# The command-line edit box is white at this pixel only while the prompt reads "Enter one corner point:".
function Prompt { if ((Red ($OX + $PromptPixel[0]) ($OY + $PromptPixel[1])) -eq 255) { 'one' } else { 'opposite' } }
function CmdLine { [BeamStrip]::Click($OX + $CommandLine[0], $OY + $CommandLine[1]); Start-Sleep -Milliseconds 350 }
function SelectAt($x, $y) {
    foreach ($attempt in 1..3) {
        CmdLine
        if ((Prompt) -eq 'opposite') { Keys '-60,-60{ENTER}'; Keys '{ESC}'; Start-Sleep -Milliseconds 400; CmdLine }   # finish a stray box, unselect
        if ((Prompt) -ne 'one') { continue }
        Keys ('{0:0.00},{1:0.00}{{ENTER}}' -f ($x - 0.2), ($y - 0.2)); Start-Sleep -Milliseconds 300
        if ((Prompt) -ne 'opposite') { continue }
        Keys ('{0:0.00},{1:0.00}{{ENTER}}' -f ($x + 0.2), ($y + 0.2)); Start-Sleep -Milliseconds 500
        if ((Prompt) -eq 'one') { return $true }
    }
    return $false
}
function Dialog { [BeamStrip]::Find($procId, 'Selected Items') -split '\|' }

foreach ($pt in ($Points -split ';')) {
    $x, $y = $pt -split ',' | ForEach-Object { [double]$_ }
    if (-not (SelectAt $x $y)) { "$pt SKIPPED could not place the selection box"; continue }
    [BeamStrip]::Click($OX + $EditMenu[0], $OY + $EditMenu[1]); Start-Sleep -Milliseconds 700
    [BeamStrip]::Click($OX + $SelectionProperties[0], $OY + $SelectionProperties[1])
    $d = @(); foreach ($try in 1..15) { Start-Sleep -Milliseconds 400; $d = Dialog; if ($d.Count -ge 6) { break } }
    if ($d.Count -lt 6 -or $d[1] -ne 'Edit 1 Selected Items') { "$pt SKIPPED dialog='$($d[1])'"; Keys '{ESC}'; Start-Sleep -Milliseconds 500; continue }
    Start-Sleep -Milliseconds 700
    $L = [int]$d[2]; $T = [int]$d[3]
    function At($dx, $dy) { [BeamStrip]::Click($L + $dx, $T + $dy); Start-Sleep -Milliseconds 450 }
    function Combo($dx, $dy, $text) { At $dx $dy; Keys $text; Keys '{ENTER}' }       # typing jumps to the matching item
    function Field($dx, $dy, $text) { At $dx $dy; Keys '^a'; Keys $text; Keys '{TAB}' }

    At 131 48                                        # Strip Generation tab
    Combo 258 135 "Code $Kind"                       #   Column Strip Width Calc -> Code T-beam / Code L-beam
    At 233 48                                        # Column Strip tab
    Combo 339 83 'T'                                 #   CS Cross Section Trimming -> T or L
    Combo 339 353 'B'                                #   CS Torsion Design -> Beam
    Combo 339 380 'B'                                #   CS Design System -> Beam
    At 324 48                                        # Middle Strip tab
    $box = [Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$d[0]).FindFirst('Descendants',
        (New-Object Windows.Automation.PropertyCondition ([Windows.Automation.AutomationElement]::ControlTypeProperty), ([Windows.Automation.ControlType]::CheckBox)))
    $ticked = $box -and $box.GetCurrentPattern([Windows.Automation.TogglePattern]::Pattern).Current.ToggleState -eq 'On'
    if ($ticked) { At 34 82 }                        #   untick "Middle Strip uses Column Strip Properties"
    Combo 342 108 'S'                                #   MS Cross Section Trimming -> Slab Rectangle
    Combo 342 162 $TopBar                            #   MS Top Bar
    Combo 342 189 $BottomBar                         #   MS Bottom Bar
    Field 340 243 "$TopCover"                        #   MS Top Cover
    Field 340 270 "$BottomCover"                     #   MS Bottom Cover
    Combo 342 378 'W'                                #   MS Torsion Design -> Wood-Armer
    Combo 342 432 'N'                                #   MS Span Detailer -> None
    At 380 612                                       # OK
    $open = $d; foreach ($try in 1..15) { Start-Sleep -Milliseconds 400; $open = Dialog; if ($open.Count -lt 6) { break } }
    Start-Sleep -Milliseconds 800
    "$pt applied" + $(if ($open.Count -ge 6) { " WARNING dialog still open: $($open[1])" } else { '' })
}
