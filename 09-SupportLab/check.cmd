@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m app.evaluation
if errorlevel 1 goto failed
echo All checks completed.
pause
exit /b 0
:failed
echo Check failed. Read the error above.
pause
exit /b 1
