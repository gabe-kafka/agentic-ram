# punch-export.ps1 -Out <file.txt> [-ProcId N] [-KeepPaused]
# Export Design Status > Tables > Punching Check Analysis from the API Concept session, with no hand on the mouse.
# Drives Concept through UI Automation by element name: the Layers menu (Design Status > Tables > Punching Check
# Analysis), the table's Export... button and the Export Entity Table dialog. Nothing is clicked by screen
# position and no keystrokes are sent, so the engineer can keep working beside it. It pauses the Scripting
# Server first (Concept's GUI ignores menus while the server is live) and resumes it after, unless -KeepPaused.
# Needs a calculated model in the API session (concept.exe started with -apiServerWithGui). With more than one
# Concept open (say, one launched from RAM Manager) it acts only on the API session, or on -ProcId.
# Then run punch_status.py on the file.
param([Parameter(Mandatory = $true)][string]$Out, [int]$ProcId = 0, [switch]$KeepPaused, [int]$Wait = 20)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class Win {
 public delegate bool P(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumWindows(P p, IntPtr l);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
 [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint msg, IntPtr w, string l);
 [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "SendMessageW")] public static extern IntPtr GetText(IntPtr h, uint msg, IntPtr w, StringBuilder l);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
 public static string Text(IntPtr h) { var s = new StringBuilder(512); GetWindowText(h, s, 512); return s.ToString(); }
 public static string Cls(IntPtr h) { var s = new StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }
 // Visible top-level windows of a process as "handle|class|title".
 public static List<string> Tops(uint pid) { var r = new List<string>(); EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p);
   if (p == pid && IsWindowVisible(h)) r.Add(h + "|" + Cls(h) + "|" + Text(h)); return true; }, IntPtr.Zero); return r; }
}
'@
$A = [System.Windows.Automation.AutomationElement]
$Scope = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]
function Cond($prop, $value) { New-Object System.Windows.Automation.PropertyCondition($prop, $value) }
function And-Cond { param([System.Windows.Automation.Condition[]]$c) New-Object System.Windows.Automation.AndCondition($c) }

if (Test-Path -LiteralPath $Out) { throw "$Out exists" }
$outDir = Split-Path -Parent $Out
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) { throw "folder $outDir does not exist" }
if (-not $ProcId) {
    $api = @(Get-CimInstance Win32_Process -Filter "Name='Concept.exe'" | Where-Object { $_.CommandLine -match '-apiServer' })
    if ($api.Count -ne 1) { throw "need exactly one API Concept session, found $($api.Count); pass -ProcId" }
    $ProcId = $api[0].ProcessId
}
$root = $A::RootElement
$byPid = Cond $A::ProcessIdProperty ([int]$ProcId)

function TopWindows { $root.FindAll($Scope::Children, $byPid) }
function Window($pattern) {
    foreach ($w in (TopWindows)) { if ($w.Current.Name -like $pattern) { return $w } }
    return $null
}
# The Export Entity Table dialog is the Windows file dialog; it is not always listed under Concept's
# process id, and UI Automation does not always list it at all. It is found with EnumWindows instead: a
# visible #32770 window of the process with that title (Windows keeps a closed file dialog around hidden
# for reuse, so only a visible one counts), and its controls come from the handle.
function Tops { foreach ($line in [Win]::Tops([uint32]$ProcId)) { $h, $cls, $text = $line.Split([char]124, 3); [pscustomobject]@{ Handle = [IntPtr][long]$h; Class = $cls; Title = $text } } }
function Dialog($title) {
    foreach ($w in (Tops)) {
        if ($w.Class -eq '#32770' -and $w.Title -eq $title) { return [System.Windows.Automation.AutomationElement]::FromHandle($w.Handle) }
    }
    return $null
}
# Dialogs left from an earlier run are cancelled first: a new Export... click stacks another file dialog
# on top of them and nothing gets written. The file dialogs go first (Cancel is dialog item 2); the
# "replace the file?" prompt under them is Concept's own Qt box, titled "Save As...", and takes its No.
function Cancel-Stale {
    foreach ($w in (Tops)) {
        if ($w.Class -eq '#32770' -and $w.Title -eq 'Export Entity Table') {
            $cancel = [Win]::GetDlgItem($w.Handle, 2)
            if ($cancel -ne [IntPtr]::Zero) { [Win]::SendMessage($cancel, 0x00F5, [IntPtr]::Zero, $null) | Out-Null; Write-Output 'cancelled a stale export dialog'; Start-Sleep -Milliseconds 800 }
        }
    }
    foreach ($w in (Tops)) {
        if ($w.Title -eq 'Save As...' -and [Win]::IsWindowEnabled($w.Handle)) {
            $box = [System.Windows.Automation.AutomationElement]::FromHandle($w.Handle)
            foreach ($b in $box.FindAll($Scope::Descendants, (Cond $A::ControlTypeProperty $CT::Button))) {
                if ($b.Current.Name -match '^&?(No|Cancel)$') { Invoke-Element $b $b.Current.Name; Write-Output 'dismissed a stale replace-file prompt'; Start-Sleep -Milliseconds 800; break }
            }
        }
    }
}
function WaitFor($what, [scriptblock]$find, $seconds = $Wait) {
    $deadline = (Get-Date).AddSeconds($seconds)
    do { $e = & $find; if ($e) { return $e }; Start-Sleep -Milliseconds 250 } while ((Get-Date) -lt $deadline)
    throw "did not find $what within $seconds s"
}
function FindIn($scopeElement, $type, $name) {
    $scopeElement.FindFirst($Scope::Descendants, (And-Cond @((Cond $A::ControlTypeProperty $type), (Cond $A::NameProperty $name))))
}
function FindAnywhere($type, $name) {
    foreach ($w in (TopWindows)) { $e = FindIn $w $type $name; if ($e) { return $e } }
    return $null
}
function Invoke-Element($e, $what) {
    $patterns = $e.GetSupportedPatterns() | ForEach-Object { $_.ProgrammaticName }
    if ($patterns -contains 'InvokePatternIdentifiers.Pattern') { $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return }
    if ($patterns -contains 'SelectionItemPatternIdentifiers.Pattern') { $e.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); return }
    if ($patterns -contains 'LegacyIAccessiblePatternIdentifiers.Pattern') { $e.GetCurrentPattern([System.Windows.Automation.LegacyIAccessiblePattern]::Pattern).DoDefaultAction(); return }
    throw "$what offers no way to activate it (patterns: $($patterns -join ', '))"
}
function Expand-Element($e, $what) {
    $patterns = $e.GetSupportedPatterns() | ForEach-Object { $_.ProgrammaticName }
    if ($patterns -notcontains 'ExpandCollapsePatternIdentifiers.Pattern') { throw "$what is not a menu that opens (patterns: $($patterns -join ', '))" }
    $e.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
}
# A menu's items exist in the automation tree only while it is open, as children of its item. Open each
# level in turn and look for the next one under it; the last item is activated.
function Menu-Path([string[]]$names) {
    $parent = $main
    $opened = @()
    try {
        for ($i = 0; $i -lt $names.Count; $i++) {
            $name = $names[$i]
            $item = WaitFor "menu item '$name'" { FindIn $parent $CT::MenuItem $name } 10
            if ($i -lt $names.Count - 1) { Expand-Element $item "menu '$name'"; $opened += $item; Start-Sleep -Milliseconds 400; $parent = $item }
            else { Invoke-Element $item "menu item '$name'" }
        }
    }
    catch {
        foreach ($m in $opened) { try { $m.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse() } catch {} }
        throw
    }
}

$main = Window '*RAM Concept*'
if (-not $main) { throw "no RAM Concept main window in process $ProcId" }
$server = Window 'Scripting Server'
$paused = $false
if ($server) {
    $pause = FindIn $server $CT::Button 'Pause'
    if ($pause -and $pause.Current.IsEnabled) { Invoke-Element $pause 'Pause'; $paused = $true; Start-Sleep -Milliseconds 500; Write-Output 'scripting server paused' }
    else { Write-Output 'scripting server was already paused' }
}
try {
    Cancel-Stale
    Menu-Path @('Layers', 'Design Status', 'Tables', 'Punching Check Analysis Table')
    Start-Sleep -Milliseconds 800
    $export = WaitFor "the table's Export... button" { FindIn $main $CT::Button 'Export...' }
    Invoke-Element $export 'Export...'
    $dialog = WaitFor 'the Export Entity Table dialog' { Dialog 'Export Entity Table' }
    $hDialog = [IntPtr]$dialog.Current.NativeWindowHandle
    # The file dialog's own controls show up as panes: the file name box is the Edit with id 1001 and Save the
    # Button with id 1. Never fall back to any edit box: the dialog's search box is one too.
    # The file name box is a plain Edit window with no automation pattern: it gets the name by window message.
    $hEdit = WaitFor 'the file name box' {
        $e = $dialog.FindFirst($Scope::Descendants, (And-Cond @((Cond $A::AutomationIdProperty '1001'), (Cond $A::ClassNameProperty 'Edit'))))
        if ($e -and [IntPtr]$e.Current.NativeWindowHandle -ne [IntPtr]::Zero) { [IntPtr]$e.Current.NativeWindowHandle } else { $null }
    }
    Start-Sleep -Milliseconds 1000                                              # let a fresh dialog settle
    [Win]::SendMessage($hEdit, 0x000C, [IntPtr]::Zero, $Out) | Out-Null       # WM_SETTEXT
    Start-Sleep -Milliseconds 500
    $typed = New-Object System.Text.StringBuilder 1024
    [Win]::GetText($hEdit, 0x000D, [IntPtr]1024, $typed) | Out-Null          # WM_GETTEXT: GetWindowText cannot read another process's edit box
    if ($typed.ToString() -ne $Out) { throw "the file name box reads '$typed', not the name given" }
    Start-Sleep -Milliseconds 300
    $hSave = [Win]::GetDlgItem($hDialog, 1)                                     # dialog item 1 is Save
    if ($hSave -eq [IntPtr]::Zero) { throw 'the dialog has no Save button' }
    [Win]::SendMessage($hSave, 0x00F5, [IntPtr]::Zero, $null) | Out-Null       # BM_CLICK
    # Concept creates the file at once and fills it a moment later.
    try { $null = WaitFor 'the export file' { if ((Test-Path -LiteralPath $Out) -and (Get-Item -LiteralPath $Out).Length -gt 0) { $true } else { $null } } 90 }
    catch {
        $left = @((Tops) | Where-Object { $_.Class -eq '#32770' -or $_.Title -eq 'Save As...' } | ForEach-Object { $_.Title })
        if ($left) { throw "Save did not finish; still open: $($left -join ', ')" }
        throw
    }
    $size = 0
    foreach ($i in 1..20) { Start-Sleep -Milliseconds 500; $now = (Get-Item -LiteralPath $Out).Length; if ($now -eq $size) { break }; $size = $now }
    Write-Output "exported $size bytes to $Out"
}
finally {
    if ($paused -and -not $KeepPaused -and $server) {
        $resume = FindIn $server $CT::Button 'Resume'
        if ($resume -and $resume.Current.IsEnabled) { Invoke-Element $resume 'Resume'; Write-Output 'scripting server resumed' }
    }
}
