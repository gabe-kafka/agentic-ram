#Requires AutoHotkey v2.0
#SingleInstance Force

; RAM Modeler only:
; Ctrl+G opens Layout > Grids > Construction Grids.
; Ctrl+L opens Layout > Loads > Line Loads.
#HotIf WinActive("ahk_exe RamModeler.exe")
$^g::
{
    try
        OpenRamConstructionGrids()
    catch Error as err
        MsgBox("Could not open RAM Construction Grids.`n`n" err.Message,
            "RAM Hotkeys")
}

$^l::
{
    try
        OpenRamLineLoads()
    catch Error as err
        MsgBox("Could not open RAM Line Loads.`n`n" err.Message, "RAM Hotkeys")
}
#HotIf

OpenRamConstructionGrids()
{
    modelerWindow := WinExist("A")

    ; The Grids submenu positions are Create/Edit, Select, separator, then
    ; Construction Grids. MenuSelect's positional syntax counts separators.
    try
    {
        MenuSelect("ahk_id " . modelerWindow, "", "Layout", "Grids", "4&")
        return
    }
    catch Error as menuErr
    {
        ; RAM can invalidate its menu while opening a modal child. Treat a
        ; different active RAM Modeler window as success.
        activeWindow := WinExist("A")
        if (activeWindow != modelerWindow
            && WinGetProcessName("ahk_id " . activeWindow) = "RamModeler.exe")
            return

        throw Error("RAM did not open Construction Grids.`n"
            . "Menu error: " . menuErr.Message)
    }
}

OpenRamLineLoads()
{
    ; RAM's menu is not always exposed as a standard Windows menu. Use the
    ; direct menu call when available, then fall back to its keyboard mnemonics.
    try
    {
        MenuSelect("A", "", "Layout", "Loads", "Line Loads")
        return
    }
    catch Error as menuErr
    {
        ; RAM can open the dialog and then invalidate its menu while
        ; WinMenuSelectItem is still returning. Treat that as success.
        if WinWaitActive("Line Load", "", 0.5)
            return

        KeyWait("Ctrl")
        WinActivate("A")
        SetKeyDelay(80, 30)
        SendEvent("{Alt down}l{Alt up}")
        Sleep(150)
        SendEvent("l")
        Sleep(150)
        SendEvent("l")

        if !WinWaitActive("Line Load", "", 2)
            throw Error("RAM did not open the Line Loads dialog.`n"
                . "Direct menu error: " . menuErr.Message)
    }
}
