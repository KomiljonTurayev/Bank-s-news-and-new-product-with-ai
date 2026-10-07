' Yo'l skript manbasidan olinadi - repo boshqa joyga ko'chsa ham buzilmaydi.
Set objShell = CreateObject("WScript.Shell")
backendDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
objShell.CurrentDirectory = backendDir
objShell.Run """" & backendDir & "run_service.bat""", 0, False
