' Mutsuki silent launcher - no CMD window when double-clicked.
Option Explicit

Dim shell, fso, root, ps1, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = root & "\start.ps1"

If Not fso.FileExists(ps1) Then
    MsgBox "start.ps1 not found:" & vbCrLf & ps1, vbCritical, "Mutsuki"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
cmd = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File " _
    & Chr(34) & ps1 & Chr(34) & " -Hidden"
shell.Run cmd, 0, False
