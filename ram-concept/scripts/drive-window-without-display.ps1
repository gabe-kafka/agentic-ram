# Drive a window with posted messages and capture it with PrintWindow.
# Works when the session is locked or disconnected, where SendKeys, mouse_event and CopyFromScreen all fail.
#
#   drive-window-without-display.ps1 -Hwnd <h> -Actions "click:440,126;wait:500;type:10,25;enter;shot:name.png"
#
# Actions: click:x,y  move:x,y  target:x,y  type:text  enter  esc  wait:ms  shot:file  crop:file,x,y,w,h  children
# Coordinates are pixels in the PrintWindow image of the window (window-rect origin).
# Clicks go to the deepest child window under the point; keys go to the last click or target.
#
# Limits seen on RAM Concept 2025 (Qt):
# - The OpenGL plan canvas does not redraw without a display; captures show the last frame drawn.
#   Use Report > Export Window to PDF for a plan instead, then stitch-concept-pdf.py.
# - Popup menus ignore posted mouse clicks. Open the menu with a click on the menu bar, then post
#   Down-arrow keys (extended-key flag set) and Enter to the popup window.
# - In the native Save dialog, WM_SETTEXT on the file name box is ignored; post WM_CHAR per character.
param([long]$Hwnd, [string]$Actions)
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class PM {
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X,Y; }
 public delegate bool P(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
 [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
 [DllImport("user32.dll")] public static extern short VkKeyScan(char c);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h, P p, IntPtr l);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 public static List<string> Children(IntPtr h) { var r = new List<string>(); EnumChildWindows(h, (c,l)=>{ var s=new StringBuilder(256); GetClassName(c,s,256); RECT q; GetWindowRect(c,out q); r.Add(c+" "+s+" visible="+IsWindowVisible(c)+" rect="+q.L+","+q.T+","+q.R+","+q.B); return true; }, IntPtr.Zero); return r; }
 [DllImport("user32.dll")] public static extern IntPtr ChildWindowFromPointEx(IntPtr h, POINT p, uint f);
 [DllImport("user32.dll")] public static extern bool ScreenToClient(IntPtr h, ref POINT p);
 // deepest visible child under a screen point, and the point in its client coordinates
 public static IntPtr Deepest(IntPtr top, int sx, int sy, out int cx, out int cy) {
   IntPtr cur = top;
   while (true) { POINT p; p.X = sx; p.Y = sy; ScreenToClient(cur, ref p);
     IntPtr c = ChildWindowFromPointEx(cur, p, 1);
     if (c == IntPtr.Zero || c == cur) { cx = p.X; cy = p.Y; return cur; }
     cur = c; } }
 public static IntPtr L(int x, int y) { return (IntPtr)((y << 16) | (x & 0xFFFF)); }
 public static void Key(IntPtr h, uint vk) { uint sc = MapVirtualKey(vk, 0); PostMessage(h, 0x100, (IntPtr)vk, (IntPtr)(1 | (sc << 16))); PostMessage(h, 0x101, (IntPtr)vk, (IntPtr)(int)(1 | (sc << 16) | 0xC0000000)); }
}
'@
[PM]::SetProcessDPIAware() | Out-Null
$h = [IntPtr]$Hwnd
$script:target = $h
$r = New-Object PM+RECT; [PM]::GetWindowRect($h, [ref]$r) | Out-Null
$o = New-Object PM+POINT; [PM]::ClientToScreen($h, [ref]$o) | Out-Null
$dx = $o.X - $r.L; $dy = $o.Y - $r.T                       # image pixel -> client pixel
function Shot($path) {
  $bmp = New-Object Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T); $g = [Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc()
  [PM]::PrintWindow($h, $dc, 2) | Out-Null; $g.ReleaseHdc($dc); $g.Dispose(); return $bmp
}
foreach ($a in ($Actions -split ';')) {
  $verb, $arg = $a -split ':', 2
  switch ($verb) {
    'click' { $x, $y = $arg -split ','; $cx = 0; $cy = 0
              $t = [PM]::Deepest($h, [int]$x + $r.L, [int]$y + $r.T, [ref]$cx, [ref]$cy); $l = [PM]::L($cx, $cy)
              "click -> hwnd $t at $cx,$cy"; $script:target = $t
              [PM]::PostMessage($t, 0x200, [IntPtr]0, $l) | Out-Null; Start-Sleep -Milliseconds 120
              [PM]::PostMessage($t, 0x201, [IntPtr]1, $l) | Out-Null; Start-Sleep -Milliseconds 60
              [PM]::PostMessage($t, 0x202, [IntPtr]0, $l) | Out-Null; Start-Sleep -Milliseconds 250 }
    'target' { $x, $y = $arg -split ','; $cx = 0; $cy = 0; $script:target = [PM]::Deepest($h, [int]$x + $r.L, [int]$y + $r.T, [ref]$cx, [ref]$cy); "target hwnd $($script:target)" }
    'move'  { $x, $y = $arg -split ','; [PM]::PostMessage($h, 0x200, [IntPtr]0, [PM]::L([int]$x - $dx, [int]$y - $dy)) | Out-Null; Start-Sleep -Milliseconds 200 }
    'type'  { foreach ($c in $arg.ToCharArray()) { [PM]::Key($script:target, [uint32]([PM]::VkKeyScan($c) -band 0xFF)); Start-Sleep -Milliseconds 40 } }
    'enter' { [PM]::Key($script:target, 0x0D); Start-Sleep -Milliseconds 300 }
    'esc'   { [PM]::Key($script:target, 0x1B); Start-Sleep -Milliseconds 300 }
    'wait'  { Start-Sleep -Milliseconds ([int]$arg) }
    'shot'  { $b = Shot; $b.Save((Join-Path $PSScriptRoot $arg)); $b.Dispose(); "saved $arg" }
    'crop'  { $n, $cx, $cy, $cw, $ch = $arg -split ','; $b = Shot
              $c = $b.Clone((New-Object Drawing.Rectangle ([int]$cx), ([int]$cy), ([int]$cw), ([int]$ch)), $b.PixelFormat)
              $p = if ([IO.Path]::IsPathRooted($n)) { $n } else { Join-Path $PSScriptRoot $n }; $c.Save($p); $c.Dispose(); $b.Dispose(); "saved $n" }
    'children' { "offset $dx,$dy"; [PM]::Children($h) }
  }
}
