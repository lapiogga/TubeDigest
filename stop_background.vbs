Set WshShell = CreateObject("WScript.Shell")

' 백엔드 프로세스 종료 (포트 8000 사용 프로세스)
WshShell.Run "cmd /c FOR /F ""tokens=5"" %a IN ('netstat -ano ^| findstr :8000') DO taskkill /F /PID %a", 0, True

' 프론트엔드 프로세스 종료 (포트 3000 사용 프로세스)
WshShell.Run "cmd /c FOR /F ""tokens=5"" %a IN ('netstat -ano ^| findstr :3000') DO taskkill /F /PID %a", 0, True
