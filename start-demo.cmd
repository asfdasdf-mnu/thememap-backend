@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m app.migrate
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m app.seed
if errorlevel 1 goto fail
echo Open http://127.0.0.1:8000/docs in your browser.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto end
:fail
echo Setup failed. See error above. Python 3.11 and internet access are required.
pause
:end
