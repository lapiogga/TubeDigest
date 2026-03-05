Set WshShell = CreateObject("WScript.Shell")

' 백엔드 (FastAPI) 실행
' .venv가상환경 활성화 후 uvicorn 실행. (0은 창 숨김, False는 대기하지 않음)
WshShell.Run "cmd /c cd backend && call .venv\Scripts\activate && uvicorn main:app --reload --port 8000", 0, False

' 프론트엔드 (Next.js) 실행
WshShell.Run "cmd /c cd frontend && npm run dev", 0, False
