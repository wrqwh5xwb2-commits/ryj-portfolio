@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto failed
"%~dp0.venv\Scripts\python.exe" -m app.evaluate
if errorlevel 1 goto failed
echo Tests and evaluation complete. See docs/benchmark.json.
pause
exit /b 0
:failed
echo Checks failed. Read the error above.
pause
exit /b 1
