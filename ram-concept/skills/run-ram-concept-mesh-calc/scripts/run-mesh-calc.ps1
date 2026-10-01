# Canonical implementation for the run-ram-concept-mesh-calc skill.
#
# Drives the open RAM Concept window through Process > Generate Mesh and
# Process > Calc All, pressing through the dialogs those commands raise.
# Each dismissed dialog is logged and screenshotted. Progress dialogs and
# unreadable dialogs are never pressed.
#
# Concept's Qt accessibility stops answering while a UI Automation Invoke
# call is inside a modal loop, so commands and buttons are pressed with real
# mouse clicks. UI Automation is only read, on a worker with a timeout.
param(
    [switch]$MeshOnly,
    [switch]$CalcOnly,
    [switch]$WatchOnly,
    [switch]$ValidateOnly,
    [int]$TimeoutMinutes = 60,
    [string]$OutDir
)

$ErrorActionPreference = 'Stop'

$formsAssembly = [Reflection.Assembly]::LoadWithPartialName(
    'System.Windows.Forms')
$drawingAssembly = [Reflection.Assembly]::LoadWithPartialName(
    'System.Drawing')
$automationClientAssembly = [Reflection.Assembly]::LoadWithPartialName(
    'UIAutomationClient')
$automationTypesAssembly = [Reflection.Assembly]::LoadWithPartialName(
    'UIAutomationTypes')
$windowsBaseAssembly = [Reflection.Assembly]::LoadWithPartialName(
    'WindowsBase')

$source = @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Automation;

public static class RamConceptMeshCalc
{
    // Buttons pressed to move a dialog forward, in preference order. The
    // title-bar close button is never pressed; it acts as Stop/Cancel.
    private static readonly string[] AcceptButtons =
    {
        "Generate", "Calc All", "Calc", "Continue", "OK",
        "Yes", "Yes to All", "Ignore", "Done", "Close"
    };

    // Checkboxes ticked before pressing, so Concept stops repeating a warning.
    private static readonly string[] SuppressCheckboxes =
    {
        "don't show", "do not show", "don't display", "do not display",
        "repeat selected option", "all warnings of this type", "this type of warning"
    };

    // Dialog text that must never be answered automatically.
    private static readonly string[] GuardedWords =
    {
        "save", "delete", "overwrite", "rebuild"
    };

    private const int QuietMilliseconds = 3000;
    private const int StableMilliseconds = 700;
    private const int UnreadableLimitSeconds = 30;
    private const int StartLimitSeconds = 15;
    private const int PressCooldownMilliseconds = 4000;
    private const uint SMTO_ABORTIFHUNG = 0x0002;
    private const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    private const uint MOUSEEVENTF_LEFTUP = 0x0004;
    private const byte VK_MENU = 0x12;
    private const uint KEYEVENTF_KEYUP = 0x0002;

    private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT
    {
        public int X;
        public int Y;
    }

    [DllImport("user32.dll")]
    private static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool IsWindowEnabled(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(IntPtr window, out RECT rectangle);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(IntPtr window, StringBuilder name, int count);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);

    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out POINT point);

    [DllImport("user32.dll")]
    private static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    private static extern void mouse_event(
        uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);

    [DllImport("user32.dll")]
    private static extern void keybd_event(
        byte key, byte scan, uint flags, UIntPtr extraInfo);

    [DllImport("user32.dll")]
    private static extern IntPtr SendMessageTimeout(
        IntPtr window, uint message, IntPtr wParam, IntPtr lParam,
        uint flags, uint timeout, out IntPtr result);

    // Titles already seen with a progress bar. Concept is too busy to answer
    // UI Automation while these run, so an unreadable one is still progress.
    private static readonly HashSet<string> ProgressTitles = new HashSet<string>
    {
        "Mesh Generation", "Calculating"
    };

    private static StreamWriter log;
    private static string outDir;
    private static int shotNumber;

    public static void Validate()
    {
        // Successful type compilation is the validation.
    }

    public static int Run(
        bool mesh, bool calc, bool watch, int timeoutMinutes, string runDir)
    {
        SetProcessDPIAware();
        outDir = runDir;
        Directory.CreateDirectory(outDir);

        using (log = new StreamWriter(Path.Combine(outDir, "run.log"), true, Encoding.UTF8))
        {
            try
            {
                Log("Output: " + outDir);
                IntPtr main = FindMainWindow();
                int processId = ProcessIdOf(main);
                Log("Concept: " + Title(main).Trim());

                TimeSpan timeout = TimeSpan.FromMinutes(timeoutMinutes);
                int dismissed = 0;
                if (watch)
                    dismissed += RunCommand(main, processId, null, timeout);
                else if (!IsWindowEnabled(main))
                    throw new InvalidOperationException(
                        "A Concept dialog is already open. Close it, or rerun with -WatchOnly.");
                if (!watch && mesh)
                    dismissed += RunCommand(main, processId, "Generate Mesh", timeout);
                if (!watch && calc)
                    dismissed += RunCommand(main, processId, "Calc All", timeout);

                Log(String.Format("Finished. Dialogs pressed: {0}.", dismissed));
                Log("Review Process > Display Warnings before trusting results.");
                return 0;
            }
            catch (Exception exception)
            {
                Log("STOPPED: " + exception.Message);
                return 1;
            }
        }
    }

    private static int RunCommand(
        IntPtr main, int processId, string command, TimeSpan timeout)
    {
        // A null command watches a mesh or calc already started by hand.
        if (command == null)
        {
            command = "Watch";
            Log("== Watch (answering dialogs until Concept is idle)");
        }
        else
        {
            Log("== " + command);
            ClickProcessMenuItem(main, command);
        }

        Stopwatch clock = Stopwatch.StartNew();
        Stopwatch quiet = Stopwatch.StartNew();
        Dictionary<IntPtr, Stopwatch> firstSeen = new Dictionary<IntPtr, Stopwatch>();
        Dictionary<IntPtr, Stopwatch> unreadableSince = new Dictionary<IntPtr, Stopwatch>();
        Dictionary<IntPtr, Stopwatch> pressedAt = new Dictionary<IntPtr, Stopwatch>();
        HashSet<string> reported = new HashSet<string>();
        int pressed = 0;
        bool started = false;

        while (true)
        {
            if (clock.Elapsed > timeout)
                throw new TimeoutException(command + " did not finish in time.");

            Thread.Sleep(300);
            bool busy = !IsWindowEnabled(main) || !IsResponsive(main);

            foreach (IntPtr dialog in FindDialogs(processId, main))
            {
                busy = true;
                if (!firstSeen.ContainsKey(dialog))
                    firstSeen[dialog] = Stopwatch.StartNew();
                if (firstSeen[dialog].ElapsedMilliseconds < StableMilliseconds ||
                    !IsResponsive(dialog))
                    continue;

                // A busy Concept can leave a pressed dialog on screen briefly;
                // give it time to close instead of clicking it again.
                if (pressedAt.ContainsKey(dialog) &&
                    pressedAt[dialog].ElapsedMilliseconds < PressCooldownMilliseconds)
                    continue;

                DialogInfo info = TryDescribe(dialog);
                string title = Title(dialog);

                if (info == null && ProgressTitles.Contains(title))
                    continue;

                if (info == null)
                {
                    if (!unreadableSince.ContainsKey(dialog))
                        unreadableSince[dialog] = Stopwatch.StartNew();
                    if (reported.Add("unreadable:" + dialog))
                        Log(String.Format(
                            "   unreadable dialog \"{0}\" ({1})", title, Screenshot(dialog)));
                    if (unreadableSince[dialog].Elapsed.TotalSeconds > UnreadableLimitSeconds)
                        throw new InvalidOperationException(
                            "Dialog \"" + title + "\" is unreadable; answer it by hand.");
                    continue;
                }

                if (info.HasProgress)
                    ProgressTitles.Add(title);

                if (info.HasProgress || info.Accept == null)
                {
                    if (reported.Add(info.Summary()))
                        Log("   waiting on: " + info.Summary());
                    continue;
                }

                if (info.IsGuarded())
                    throw new InvalidOperationException(
                        "Guarded dialog; answer it by hand: " + info.Summary());

                string shot = Screenshot(dialog);
                if (info.HasSuppress && !info.SuppressChecked)
                {
                    ClickCenter(dialog, info.SuppressRect);
                    Log("   tick [" + info.SuppressName + "]");
                }
                Log(String.Format(
                    "   press [{0}] {1} ({2})", info.Accept, info.Summary(), shot));
                ClickCenter(dialog, info.AcceptRect);
                firstSeen.Remove(dialog);
                pressedAt[dialog] = Stopwatch.StartNew();
                pressed++;
            }

            if (busy)
            {
                started = true;
                quiet.Restart();
            }
            else if (!started)
            {
                if (command == "Watch")
                {
                    Log("   Concept is idle; nothing to answer.");
                    return pressed;
                }
                if (clock.Elapsed.TotalSeconds < StartLimitSeconds)
                    quiet.Restart();
                else
                    throw new InvalidOperationException(
                        command + " never started; Concept stayed idle after the menu click.");
            }
            if (quiet.ElapsedMilliseconds >= QuietMilliseconds)
                break;
        }

        Log(String.Format("   {0} done in {1:0}s.", command, clock.Elapsed.TotalSeconds));
        return pressed;
    }

    private static IntPtr FindMainWindow()
    {
        List<IntPtr> found = new List<IntPtr>();
        HashSet<int> conceptIds = new HashSet<int>();
        foreach (Process process in Process.GetProcessesByName("Concept"))
            conceptIds.Add(process.Id);

        EnumWindows(delegate(IntPtr window, IntPtr parameter)
        {
            if (conceptIds.Contains(ProcessIdOf(window)) &&
                IsWindowVisible(window) &&
                Title(window).IndexOf(
                    "RAM Concept", StringComparison.OrdinalIgnoreCase) >= 0)
                found.Add(window);
            return true;
        }, IntPtr.Zero);

        if (found.Count == 0)
            throw new InvalidOperationException("No open RAM Concept model window.");
        if (found.Count > 1)
            throw new InvalidOperationException(
                "Several RAM Concept windows are open. Leave only one open.");
        return found[0];
    }

    private static void ClickProcessMenuItem(IntPtr main, string command)
    {
        BringToFront(main);
        AutomationElement root = AutomationElement.FromHandle(main);
        AutomationElement processMenu = root.FindFirst(
            TreeScope.Descendants,
            new AndCondition(
                new PropertyCondition(
                    AutomationElement.ControlTypeProperty, ControlType.MenuItem),
                new PropertyCondition(AutomationElement.NameProperty, "Process")));
        if (processMenu == null)
            throw new InvalidOperationException("Process menu not found.");

        // Expanding only opens the popup; it does not run a command.
        ((ExpandCollapsePattern)processMenu.GetCurrentPattern(
            ExpandCollapsePattern.Pattern)).Expand();

        for (int attempt = 0; attempt < 20; attempt++)
        {
            Thread.Sleep(100);
            AutomationElement item = processMenu.FindFirst(
                TreeScope.Descendants,
                new AndCondition(
                    new PropertyCondition(
                        AutomationElement.ControlTypeProperty, ControlType.MenuItem),
                    new PropertyCondition(AutomationElement.NameProperty, command)));
            if (item == null || item.Current.BoundingRectangle.IsEmpty)
                continue;
            if (!item.Current.IsEnabled)
                throw new InvalidOperationException(
                    "Process > " + command + " is disabled.");

            ClickCenter(IntPtr.Zero, item.Current.BoundingRectangle);
            return;
        }

        throw new InvalidOperationException("Process > " + command + " not found.");
    }

    // Visible, enabled Concept windows other than the main window, shown only
    // while a modal dialog has disabled the main window.
    private static List<IntPtr> FindDialogs(int processId, IntPtr main)
    {
        List<IntPtr> dialogs = new List<IntPtr>();
        if (IsWindowEnabled(main))
            return dialogs;

        EnumWindows(delegate(IntPtr window, IntPtr parameter)
        {
            if (window == main || ProcessIdOf(window) != processId ||
                !IsWindowVisible(window) || !IsWindowEnabled(window))
                return true;

            string className = ClassName(window);
            if (className == "SysShadow" ||
                className.IndexOf("Popup", StringComparison.OrdinalIgnoreCase) >= 0 ||
                className.IndexOf("ToolTip", StringComparison.OrdinalIgnoreCase) >= 0)
                return true;

            // Qt keeps small untitled helper windows; they are not dialogs.
            RECT rect;
            if (!GetWindowRect(window, out rect) ||
                rect.Right - rect.Left < 60 || rect.Bottom - rect.Top < 40)
                return true;

            dialogs.Add(window);
            return true;
        }, IntPtr.Zero);

        return dialogs;
    }

    private static DialogInfo TryDescribe(IntPtr dialog)
    {
        DialogInfo result = null;
        Thread reader = new Thread(delegate()
        {
            try
            {
                result = Describe(AutomationElement.FromHandle(dialog));
            }
            catch
            {
                result = null;
            }
        });
        reader.IsBackground = true;
        reader.Start();
        if (!reader.Join(3000))
            return null;
        if (result != null && result.Buttons.Count == 0 && !result.HasProgress)
            return null;
        return result;
    }

    private static DialogInfo Describe(AutomationElement dialog)
    {
        DialogInfo info = new DialogInfo();
        info.Title = dialog.Current.Name ?? "";
        System.Windows.Rect frame = dialog.Current.BoundingRectangle;

        foreach (AutomationElement child in dialog.FindAll(
            TreeScope.Descendants, Condition.TrueCondition))
        {
            try
            {
                ControlType type = child.Current.ControlType;
                string name = (child.Current.Name ?? "").Trim();
                if (type == ControlType.ProgressBar)
                    info.HasProgress = true;
                else if (type == ControlType.Button && name.Length > 0 &&
                         child.Current.IsEnabled && !child.Current.IsOffscreen &&
                         !IsTitleBarButton(frame, child.Current.BoundingRectangle))
                    info.Buttons.Add(new KeyValuePair<string, System.Windows.Rect>(
                        name.Replace("&", ""), child.Current.BoundingRectangle));
                else if (type == ControlType.CheckBox && IsSuppressCheckbox(name) &&
                         child.Current.IsEnabled && !child.Current.IsOffscreen)
                {
                    info.HasSuppress = true;
                    info.SuppressName = name;
                    info.SuppressRect = child.Current.BoundingRectangle;
                    object toggle;
                    info.SuppressChecked =
                        child.TryGetCurrentPattern(TogglePattern.Pattern, out toggle) &&
                        ((TogglePattern)toggle).Current.ToggleState == ToggleState.On;
                }
                else if ((type == ControlType.Text || type == ControlType.Document ||
                          type == ControlType.Edit) && name.Length > 0)
                    info.Text.Add(name);
            }
            catch (ElementNotAvailableException)
            {
            }
        }

        foreach (string accept in AcceptButtons)
        {
            foreach (KeyValuePair<string, System.Windows.Rect> button in info.Buttons)
            {
                if (button.Key.Equals(accept, StringComparison.OrdinalIgnoreCase) &&
                    !button.Value.IsEmpty)
                {
                    info.Accept = button.Key;
                    info.AcceptRect = button.Value;
                    return info;
                }
            }
        }

        return info;
    }

    private static void BringToFront(IntPtr window)
    {
        // A tapped Alt key lets a background process take the foreground.
        keybd_event(VK_MENU, 0, 0, UIntPtr.Zero);
        keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
        SetForegroundWindow(window);
        Thread.Sleep(150);
    }

    private static void ClickCenter(IntPtr window, System.Windows.Rect rect)
    {
        if (window != IntPtr.Zero)
            BringToFront(window);

        POINT original;
        GetCursorPos(out original);
        try
        {
            SetCursorPos(
                (int)(rect.Left + rect.Width / 2),
                (int)(rect.Top + rect.Height / 2));
            Thread.Sleep(50);
            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
            Thread.Sleep(100);
        }
        finally
        {
            SetCursorPos(original.X, original.Y);
        }
    }

    private static string Screenshot(IntPtr window)
    {
        try
        {
            RECT rect;
            GetWindowRect(window, out rect);
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;
            if (width <= 0 || height <= 0)
                return "no screenshot";

            string path = Path.Combine(
                outDir, String.Format("dialog-{0:00}.png", ++shotNumber));
            using (Bitmap bitmap = new Bitmap(width, height))
            {
                using (Graphics graphics = Graphics.FromImage(bitmap))
                    graphics.CopyFromScreen(rect.Left, rect.Top, 0, 0, bitmap.Size);
                bitmap.Save(path, ImageFormat.Png);
            }
            return Path.GetFileName(path);
        }
        catch (Exception exception)
        {
            return "no screenshot: " + exception.Message;
        }
    }

    private static bool IsSuppressCheckbox(string name)
    {
        foreach (string phrase in SuppressCheckboxes)
        {
            if (name.IndexOf(phrase, StringComparison.OrdinalIgnoreCase) >= 0)
                return true;
        }
        return false;
    }

    // Caption buttons sit in the top strip of the frame; dialog buttons do not.
    private static bool IsTitleBarButton(System.Windows.Rect frame, System.Windows.Rect button)
    {
        if (frame.IsEmpty || button.IsEmpty)
            return false;
        return button.Top - frame.Top < 48 && frame.Right - button.Right < 160;
    }

    private static bool IsResponsive(IntPtr window)
    {
        IntPtr result;
        return SendMessageTimeout(
            window, 0, IntPtr.Zero, IntPtr.Zero,
            SMTO_ABORTIFHUNG, 1000, out result) != IntPtr.Zero;
    }

    private static int ProcessIdOf(IntPtr window)
    {
        uint processId;
        GetWindowThreadProcessId(window, out processId);
        return (int)processId;
    }

    private static string Title(IntPtr window)
    {
        StringBuilder text = new StringBuilder(512);
        GetWindowText(window, text, text.Capacity);
        return text.ToString();
    }

    private static string ClassName(IntPtr window)
    {
        StringBuilder name = new StringBuilder(256);
        GetClassName(window, name, name.Capacity);
        return name.ToString();
    }

    private static void Log(string message)
    {
        string line = DateTime.Now.ToString("HH:mm:ss") + "  " + message;
        Console.WriteLine(line);
        if (log != null)
        {
            log.WriteLine(line);
            log.Flush();
        }
    }

    private sealed class DialogInfo
    {
        public string Title = "";
        public bool HasProgress;
        public List<string> Text = new List<string>();
        public List<KeyValuePair<string, System.Windows.Rect>> Buttons =
            new List<KeyValuePair<string, System.Windows.Rect>>();
        public string Accept;
        public System.Windows.Rect AcceptRect;
        public bool HasSuppress;
        public bool SuppressChecked;
        public string SuppressName;
        public System.Windows.Rect SuppressRect;

        public bool IsGuarded()
        {
            string all = (Title + " " + String.Join(" ", Text.ToArray()))
                .ToLowerInvariant();
            foreach (string word in GuardedWords)
            {
                if (all.Contains(word))
                    return true;
            }
            return false;
        }

        public string Summary()
        {
            List<string> names = new List<string>();
            foreach (KeyValuePair<string, System.Windows.Rect> button in Buttons)
                names.Add(button.Key);
            return String.Format(
                "\"{0}\" {1} buttons=[{2}]",
                Title,
                String.Join(" | ", Text.ToArray()),
                String.Join(", ", names.ToArray()));
        }
    }
}
'@

$references = @(
    $formsAssembly.Location
    $drawingAssembly.Location
    $automationClientAssembly.Location
    $automationTypesAssembly.Location
    $windowsBaseAssembly.Location
) | Select-Object -Unique

Add-Type -TypeDefinition $source -ReferencedAssemblies $references

if ($ValidateOnly) {
    [RamConceptMeshCalc]::Validate()
    Write-Output 'RAM Concept mesh/calc helper compiled successfully.'
    exit 0
}

if ($MeshOnly -and $CalcOnly) {
    throw 'Use -MeshOnly or -CalcOnly, not both.'
}

if (-not $OutDir) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutDir = Join-Path $PSScriptRoot "..\..\..\out\mesh-calc-$stamp"
}
$OutDir = [IO.Path]::GetFullPath($OutDir)

exit [RamConceptMeshCalc]::Run(
    -not $CalcOnly,
    -not $MeshOnly,
    [bool]$WatchOnly,
    $TimeoutMinutes,
    $OutDir)
