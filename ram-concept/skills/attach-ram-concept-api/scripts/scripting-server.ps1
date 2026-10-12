# scripting-server.ps1 [-Resume | -Pause] [-ProcId N]
#
# The state of RAM Concept's Scripting Server window, and resuming or pausing it, through UI Automation
# (the button's Invoke pattern). No mouse, no focus change: a click on Resume can miss when another
# window covers it, and every API call then times out. Prints one line: running | paused | no window,
# and what was done. Exit code 0 when the server is in the state asked for, 1 otherwise.
param([switch]$Resume, [switch]$Pause, [int]$ProcId = 0)
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$CT = [System.Windows.Automation.ControlType]
$Scope = [System.Windows.Automation.TreeScope]

function Cond($prop, $value) { New-Object System.Windows.Automation.PropertyCondition($prop, $value) }
$cond = Cond $A::NameProperty 'Scripting Server'
if ($ProcId) { $cond = New-Object System.Windows.Automation.AndCondition(@($cond, (Cond $A::ProcessIdProperty $ProcId))) }
$server = $A::RootElement.FindFirst($Scope::Children, $cond)
if (-not $server) { Write-Output 'no window: no Scripting Server window (Concept was not started with the API, or no model is open)'; exit 1 }
function Button($name) {
    $server.FindFirst($Scope::Descendants, (New-Object System.Windows.Automation.AndCondition(@((Cond $A::ControlTypeProperty $CT::Button), (Cond $A::NameProperty $name)))))
}
function Press($e) { $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
function State() {
    $p = Button 'Pause'
    if ($p -and $p.Current.IsEnabled) { return 'running' }
    $r = Button 'Resume'
    if ($r -and $r.Current.IsEnabled) { return 'paused' }
    return 'unknown (neither Pause nor Resume is enabled)'
}
$before = State
$done = ''
if ($Resume -and $before -eq 'paused') { Press (Button 'Resume'); Start-Sleep -Milliseconds 700; $done = '; Resume pressed' }
if ($Pause -and $before -eq 'running') { Press (Button 'Pause'); Start-Sleep -Milliseconds 700; $done = '; Pause pressed' }
$after = State
Write-Output ("{0} (pid {1}){2}{3}" -f $after, $server.Current.ProcessId, $done, $(if ($done) { ", was $before" } else { '' }))
if (($Resume -and $after -ne 'running') -or ($Pause -and $after -ne 'paused')) { exit 1 }
exit 0
