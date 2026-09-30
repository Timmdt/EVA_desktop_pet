Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

folder = fso.GetParentFolderName(WScript.ScriptFullName)

pythonw = folder & "\.venv\Scripts\pythonw.exe"
script = folder & "\eva_pet.py"

shell.Run """" & pythonw & """ """ & script & """", 0, False