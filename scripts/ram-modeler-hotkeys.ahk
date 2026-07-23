#Requires AutoHotkey v2.0
#SingleInstance Force

; RAM Modeler only: Ctrl+L opens Layout > Loads > Line Loads.
#HotIf WinActive("ahk_exe RamModeler.exe")
$^l::
{
    try
        OpenRamLineLoads()
    catch Error as err
        MsgBox("Could not open RAM Line Loads.`n`n" err.Message, "RAM Hotkeys")
}
#HotIf

OpenRamLineLoads()
{
    ; RAM's menu is not always exposed as a standard Windows menu. Use the
    ; direct menu call when available, then fall back to its keyboard mnemonics.
    try
    {
        WinMenuSelectItem("A", "", "Layout", "Loads", "Line Loads")
        return
    }
    catch Error as menuErr
    {
        ; RAM can open the dialog and then invalidate its menu while
        ; WinMenuSelectItem is still returning. Treat that as success.
        if WinWaitActive("Line Load",, 0.5)
            return

        KeyWait("Ctrl")
        WinActivate("A")
        SetKeyDelay(80, 30)
        SendEvent("{Alt down}l{Alt up}")
        Sleep(150)
        SendEvent("l")
        Sleep(150)
        SendEvent("l")

        if !WinWaitActive("Line Load",, 2)
            throw Error("RAM did not open the Line Loads dialog.`n"
                . "Direct menu error: " . menuErr.Message)
    }
}
