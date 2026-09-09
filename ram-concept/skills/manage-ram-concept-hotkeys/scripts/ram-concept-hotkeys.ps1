# Canonical implementation for the manage-ram-concept-hotkeys skill.
param(
    [switch]$ValidateOnly,
    [switch]$Inspect
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
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Automation;
using System.Windows.Forms;
using System.Drawing;

public static class RamConceptHotkeys
{
    private const int WH_KEYBOARD_LL = 13;
    private const int WM_KEYDOWN = 0x0100;
    private const int WM_KEYUP = 0x0101;
    private const int WM_SYSKEYDOWN = 0x0104;
    private const int WM_SYSKEYUP = 0x0105;
    private const int VK_ESCAPE = 0x1B;
    private const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    private const uint MOUSEEVENTF_LEFTUP = 0x0004;

    private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

    private static readonly LowLevelKeyboardProc HookCallback = KeyboardHook;
    private static IntPtr hookHandle = IntPtr.Zero;
    private static NotifyIcon trayIcon;
    private static int selectActionRunning;

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT
    {
        public int X;
        public int Y;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SetWindowsHookEx(
        int idHook,
        LowLevelKeyboardProc callback,
        IntPtr moduleHandle,
        uint threadId);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnhookWindowsHookEx(IntPtr hook);

    [DllImport("user32.dll")]
    private static extern IntPtr CallNextHookEx(
        IntPtr hook,
        int code,
        IntPtr wParam,
        IntPtr lParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    private static extern IntPtr GetModuleHandle(string moduleName);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr window);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);

    [DllImport("user32.dll")]
    private static extern int GetWindowTextLength(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(IntPtr window, out RECT rectangle);

    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out POINT point);

    [DllImport("user32.dll")]
    private static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    private static extern void mouse_event(
        uint flags,
        uint dx,
        uint dy,
        uint data,
        UIntPtr extraInfo);

    [DllImport("user32.dll")]
    private static extern uint GetDpiForWindow(IntPtr window);

    public static void Validate()
    {
        // Successful type compilation is the validation.
    }

    public static void Run()
    {
        bool ownsMutex;
        using (Mutex mutex = new Mutex(
            true,
            @"Local\AgenticRam.RamConceptHotkeys",
            out ownsMutex))
        {
            if (!ownsMutex)
            {
                MessageBox.Show(
                    "RAM Concept hotkeys are already running.",
                    "RAM Concept hotkeys",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
                return;
            }

            Application.EnableVisualStyles();
            CreateTrayIcon();

            hookHandle = SetWindowsHookEx(
                WH_KEYBOARD_LL,
                HookCallback,
                GetModuleHandle(null),
                0);

            if (hookHandle == IntPtr.Zero)
            {
                trayIcon.Dispose();
                throw new System.ComponentModel.Win32Exception(
                    Marshal.GetLastWin32Error(),
                    "Could not install the Esc hotkey.");
            }

            try
            {
                trayIcon.ShowBalloonTip(
                    2000,
                    "RAM Concept hotkeys",
                    "Esc now returns the main RAM Concept window to Selection.",
                    ToolTipIcon.Info);
                Application.Run();
            }
            finally
            {
                UnhookWindowsHookEx(hookHandle);
                hookHandle = IntPtr.Zero;
                trayIcon.Visible = false;
                trayIcon.Dispose();
            }
        }
    }

    public static string InspectForegroundToolbar()
    {
        IntPtr window = GetForegroundWindow();
        if (window == IntPtr.Zero)
            return "There is no foreground window.";

        StringBuilder output = new StringBuilder();
        output.AppendLine("Window: " + GetTitle(window));

        try
        {
            AutomationElement root = AutomationElement.FromHandle(window);
            System.Windows.Rect rootRect = root.Current.BoundingRectangle;
            AutomationElementCollection elements =
                root.FindAll(TreeScope.Descendants, Condition.TrueCondition);

            foreach (AutomationElement element in elements)
            {
                try
                {
                    System.Windows.Rect rect = element.Current.BoundingRectangle;
                    if (rect.IsEmpty || element.Current.IsOffscreen)
                        continue;
                    if (rect.Top > rootRect.Top + 180)
                        continue;

                    string name = element.Current.Name;
                    string automationId = element.Current.AutomationId;
                    ControlType type = element.Current.ControlType;
                    if (String.IsNullOrEmpty(name) && String.IsNullOrEmpty(automationId))
                        continue;

                    output.AppendFormat(
                        "{0,-12} Name=\"{1}\" Id=\"{2}\" Rect={3:0},{4:0},{5:0},{6:0}\r\n",
                        type.ProgrammaticName.Replace("ControlType.", ""),
                        name,
                        automationId,
                        rect.Left,
                        rect.Top,
                        rect.Width,
                        rect.Height);
                }
                catch (ElementNotAvailableException)
                {
                }
            }
        }
        catch (Exception exception)
        {
            output.AppendLine("Inspection failed: " + exception.Message);
        }

        return output.ToString();
    }

    private static void CreateTrayIcon()
    {
        trayIcon = new NotifyIcon();
        trayIcon.Icon = SystemIcons.Application;
        trayIcon.Text = "RAM Concept: Esc to Selection";
        trayIcon.Visible = true;

        ContextMenuStrip menu = new ContextMenuStrip();
        ToolStripMenuItem exitItem = new ToolStripMenuItem("Exit");
        exitItem.Click += delegate
        {
            Application.ExitThread();
        };
        menu.Items.Add(exitItem);
        trayIcon.ContextMenuStrip = menu;
    }

    private static IntPtr KeyboardHook(
        int code,
        IntPtr wParam,
        IntPtr lParam)
    {
        if (code >= 0)
        {
            int virtualKey = Marshal.ReadInt32(lParam);
            int message = wParam.ToInt32();
            bool isEscapeMessage =
                virtualKey == VK_ESCAPE &&
                (message == WM_KEYDOWN ||
                 message == WM_KEYUP ||
                 message == WM_SYSKEYDOWN ||
                 message == WM_SYSKEYUP);

            if (isEscapeMessage && IsMainConceptWindow(GetForegroundWindow()))
            {
                if ((message == WM_KEYDOWN || message == WM_SYSKEYDOWN) &&
                    Interlocked.Exchange(ref selectActionRunning, 1) == 0)
                {
                    Thread worker = new Thread(delegate()
                    {
                        try
                        {
                            ActivateSelectionTool();
                        }
                        finally
                        {
                            Interlocked.Exchange(ref selectActionRunning, 0);
                        }
                    });
                    worker.IsBackground = true;
                    worker.SetApartmentState(ApartmentState.STA);
                    worker.Start();
                }

                // Suppress Esc only in the main model window. Concept dialogs
                // keep their normal Esc-to-cancel behavior.
                return new IntPtr(1);
            }
        }

        return CallNextHookEx(hookHandle, code, wParam, lParam);
    }

    private static bool IsMainConceptWindow(IntPtr window)
    {
        if (window == IntPtr.Zero)
            return false;

        uint processId;
        GetWindowThreadProcessId(window, out processId);
        if (processId == 0)
            return false;

        try
        {
            using (Process process = Process.GetProcessById((int)processId))
            {
                if (!process.ProcessName.Equals(
                    "Concept",
                    StringComparison.OrdinalIgnoreCase))
                    return false;
            }
        }
        catch
        {
            return false;
        }

        // The model window title includes "RAM Concept". Property dialogs do
        // not, so Esc continues to close or cancel those dialogs normally.
        return GetTitle(window).IndexOf(
            "RAM Concept",
            StringComparison.OrdinalIgnoreCase) >= 0;
    }

    private static string GetTitle(IntPtr window)
    {
        int length = GetWindowTextLength(window);
        StringBuilder text = new StringBuilder(Math.Max(length + 1, 256));
        GetWindowText(window, text, text.Capacity);
        return text.ToString();
    }

    private static void ActivateSelectionTool()
    {
        IntPtr window = GetForegroundWindow();
        if (!IsMainConceptWindow(window))
            return;

        // RAM Concept 2024 exposes this command through:
        // Tools > Selection > Selection.
        //
        // The menu path is more stable than toolbar accessibility metadata:
        // Alt+T opens Tools, Home selects Snaps, Down selects Selection,
        // Right opens its submenu, and Home/Enter activates Selection.
        if (ActivateSelectionFromMenu(window))
            return;

        AutomationElement root = null;
        try
        {
            root = AutomationElement.FromHandle(window);
        }
        catch
        {
        }

        AutomationElement selection = FindToolbarElement(root, true);
        if (selection != null && InvokeElement(selection))
            return;

        AutomationElement toolGroup = FindToolbarElement(root, false);
        if (toolGroup != null)
        {
            if (ExpandElement(toolGroup))
            {
                Thread.Sleep(120);
                selection = FindVisibleSelectionChoice(window, toolGroup);
                if (selection != null && InvokeElement(selection))
                    return;
            }

            System.Windows.Rect groupRect = SafeRectangle(toolGroup);
            if (!groupRect.IsEmpty &&
                OpenToolPaletteAndChooseSelection(window, groupRect))
                return;
        }

        // RAM Concept 2024 default toolbar fallback. Coordinates are relative
        // to the model window and DPI-scaled. The long press opens the
        // Selection/Utility palette; the actual Selection item is then found
        // through Windows accessibility.
        RECT windowRect;
        if (GetWindowRect(window, out windowRect))
        {
            uint dpi = GetDpiForWindow(window);
            double scale = dpi == 0 ? 1.0 : dpi / 96.0;
            System.Windows.Rect fallback = new System.Windows.Rect(
                windowRect.Left + (310 * scale),
                windowRect.Top + (50 * scale),
                28 * scale,
                28 * scale);

            if (OpenToolPaletteAndChooseSelection(window, fallback))
                return;
        }

        ShowFailure();
    }

    private static bool ActivateSelectionFromMenu(IntPtr window)
    {
        try
        {
            SetForegroundWindow(window);
            SendKeys.SendWait("%t");
            Thread.Sleep(100);
            SendKeys.SendWait("{HOME}{DOWN}{RIGHT}");
            Thread.Sleep(100);
            SendKeys.SendWait("{HOME}{ENTER}");
            return true;
        }
        catch
        {
            // Retain the accessibility/toolbar fallbacks below.
            return false;
        }
    }

    private static AutomationElement FindToolbarElement(
        AutomationElement root,
        bool selectionOnly)
    {
        if (root == null)
            return null;

        try
        {
            System.Windows.Rect rootRect = root.Current.BoundingRectangle;
            AutomationElementCollection elements =
                root.FindAll(TreeScope.Descendants, Condition.TrueCondition);

            AutomationElement best = null;
            int bestScore = Int32.MinValue;

            foreach (AutomationElement element in elements)
            {
                try
                {
                    System.Windows.Rect rect = element.Current.BoundingRectangle;
                    if (rect.IsEmpty || element.Current.IsOffscreen)
                        continue;
                    if (rect.Top > rootRect.Top + 180)
                        continue;

                    string name = element.Current.Name ?? "";
                    string automationId = element.Current.AutomationId ?? "";
                    bool isSelection =
                        name.Equals("Selection", StringComparison.OrdinalIgnoreCase) ||
                        name.StartsWith(
                            "Selection (",
                            StringComparison.OrdinalIgnoreCase);
                    bool isGroup =
                        automationId.Equals(
                            "SelectionTool",
                            StringComparison.OrdinalIgnoreCase) ||
                        name.Equals("Utility", StringComparison.OrdinalIgnoreCase) ||
                        isSelection;

                    if (selectionOnly && !isSelection)
                        continue;
                    if (!selectionOnly && !isGroup)
                        continue;

                    int score = 0;
                    if (automationId.Equals(
                        "SelectionTool",
                        StringComparison.OrdinalIgnoreCase))
                        score += 20;
                    if (isSelection)
                        score += 15;
                    if (element.Current.ControlType == ControlType.Button)
                        score += 5;

                    if (score > bestScore)
                    {
                        best = element;
                        bestScore = score;
                    }
                }
                catch (ElementNotAvailableException)
                {
                }
            }

            return best;
        }
        catch
        {
            return null;
        }
    }

    private static AutomationElement FindVisibleSelectionChoice(
        IntPtr conceptWindow,
        AutomationElement excludedElement)
    {
        System.Windows.Rect excluded = SafeRectangle(excludedElement);
        uint conceptProcessId;
        GetWindowThreadProcessId(conceptWindow, out conceptProcessId);

        try
        {
            PropertyCondition nameCondition = new PropertyCondition(
                AutomationElement.NameProperty,
                "Selection");
            AutomationElementCollection elements =
                AutomationElement.RootElement.FindAll(
                    TreeScope.Descendants,
                    nameCondition);

            foreach (AutomationElement element in elements)
            {
                try
                {
                    if (element.Current.ProcessId != (int)conceptProcessId ||
                        element.Current.IsOffscreen)
                        continue;

                    System.Windows.Rect rect = element.Current.BoundingRectangle;
                    if (rect.IsEmpty || RectanglesMatch(rect, excluded))
                        continue;

                    return element;
                }
                catch (ElementNotAvailableException)
                {
                }
            }
        }
        catch
        {
        }

        return null;
    }

    private static bool ExpandElement(AutomationElement element)
    {
        try
        {
            object pattern;
            if (element.TryGetCurrentPattern(
                ExpandCollapsePattern.Pattern,
                out pattern))
            {
                ((ExpandCollapsePattern)pattern).Expand();
                return true;
            }
        }
        catch
        {
        }

        return false;
    }

    private static bool InvokeElement(AutomationElement element)
    {
        try
        {
            object pattern;
            if (element.TryGetCurrentPattern(InvokePattern.Pattern, out pattern))
            {
                ((InvokePattern)pattern).Invoke();
                return true;
            }

            System.Windows.Rect rect = element.Current.BoundingRectangle;
            if (!rect.IsEmpty)
                return ClickAt(
                    (int)(rect.Left + rect.Width / 2),
                    (int)(rect.Top + rect.Height / 2));
        }
        catch
        {
        }

        return false;
    }

    private static bool OpenToolPaletteAndChooseSelection(
        IntPtr conceptWindow,
        System.Windows.Rect groupRect)
    {
        POINT original;
        GetCursorPos(out original);

        try
        {
            int x = (int)(groupRect.Left + groupRect.Width / 2);
            int y = (int)(groupRect.Top + groupRect.Height / 2);
            SetCursorPos(x, y);
            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
            Thread.Sleep(650);
            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
            Thread.Sleep(150);

            AutomationElement choice =
                FindVisibleSelectionChoice(conceptWindow, null);
            if (choice != null && InvokeElement(choice))
                return true;

            return false;
        }
        finally
        {
            SetCursorPos(original.X, original.Y);
        }
    }

    private static bool ClickAt(int x, int y)
    {
        POINT original;
        GetCursorPos(out original);
        try
        {
            SetCursorPos(x, y);
            mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
            mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
            return true;
        }
        finally
        {
            SetCursorPos(original.X, original.Y);
        }
    }

    private static System.Windows.Rect SafeRectangle(
        AutomationElement element)
    {
        if (element == null)
            return System.Windows.Rect.Empty;

        try
        {
            return element.Current.BoundingRectangle;
        }
        catch
        {
            return System.Windows.Rect.Empty;
        }
    }

    private static bool RectanglesMatch(
        System.Windows.Rect first,
        System.Windows.Rect second)
    {
        if (first.IsEmpty || second.IsEmpty)
            return false;

        return Math.Abs(first.Left - second.Left) < 2 &&
               Math.Abs(first.Top - second.Top) < 2 &&
               Math.Abs(first.Width - second.Width) < 2 &&
               Math.Abs(first.Height - second.Height) < 2;
    }

    private static void ShowFailure()
    {
        if (trayIcon == null)
            return;

        trayIcon.ShowBalloonTip(
            3000,
            "RAM Concept hotkeys",
            "Selection tool was not found. Run the launcher with -Inspect while the model window is active.",
            ToolTipIcon.Warning);
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
    [RamConceptHotkeys]::Validate()
    Write-Output 'RAM Concept hotkey helper compiled successfully.'
    exit 0
}

if ($Inspect) {
    Write-Output ([RamConceptHotkeys]::InspectForegroundToolbar())
    exit 0
}

[RamConceptHotkeys]::Run()
