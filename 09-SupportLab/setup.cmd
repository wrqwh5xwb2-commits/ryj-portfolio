@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 goto failed
echo Setup complete. Double-click start.cmd to launch.
pause
exit /b 0
:failed
echo Setup failed. Read the error above. Python 3.14 is the tested version.
pause
exit /b 1
