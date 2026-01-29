Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir
pythonw = fso.BuildPath(scriptDir, "venv\\Scripts\\pythonw.exe")
app = fso.BuildPath(scriptDir, "riskguard_ui.py")
q = Chr(34)
shell.Run q & pythonw & q & " " & q & app & q, 0, False