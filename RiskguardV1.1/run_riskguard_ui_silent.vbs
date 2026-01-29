Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir
ps = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " & Chr(34) & fso.BuildPath(scriptDir, "run_riskguard_ui.ps1") & Chr(34)
shell.Run ps, 0, False
