@echo off
setlocal
cd /d "%~dp0.."
if not exist "backend\.venv\Scripts\python.exe" (
  py -3 -m venv backend\.venv
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
)
if not exist "frontend\node_modules" (
  cd frontend
  call npm install
  cd ..
)
if not exist "backend\.env" copy backend\.env.example backend\.env
start "AI Agent Studio API" cmd /k "cd /d %CD%\backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 >nul
start "AI Agent Studio UI" cmd /k "cd /d %CD%\frontend && npm run dev"
timeout /t 5 >nul
start http://localhost:3000
endlocal
