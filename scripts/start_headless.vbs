' Headless silent launcher using pythonw.exe (0 focus stealing, 0 window flash)
Set WinScriptHost = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)

pythonwPath = projectDir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonwPath) Then
    pythonwPath = "pythonw.exe"
End If

' Pass arguments or default to daemon
args = ""
If WScript.Arguments.Count > 0 Then
    For i = 0 To WScript.Arguments.Count - 1
        args = args & " " & WScript.Arguments(i)
    Next
Else
    args = "-m src.cli daemon"
End If

cmd = Chr(34) & pythonwPath & Chr(34) & " " & args
WinScriptHost.CurrentDirectory = projectDir
WinScriptHost.Run cmd, 0, False
Set WinScriptHost = Nothing
