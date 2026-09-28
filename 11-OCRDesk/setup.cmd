@echo off
cd /d "%~dp0"
set "PROJECT_PYTHON=python"
if not "%~1"=="" set "PROJECT_PYTHON=%~1"
"%PROJECT_PYTHON%" -m venv .venv
if errorlevel 1 goto failed
"%~dp0.venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 goto failed
echo Setup complete. Run start.cmd. Tested with Python 3.13 on Windows.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.13 and retry. See README.md.
pause
exit /b 1
