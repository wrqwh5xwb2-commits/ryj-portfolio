@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m app.evaluate
if errorlevel 1 goto failed
echo Checks complete. See docs/benchmark.json.
pause
exit /b 0
:failed
echo Check failed. See the error above.
pause
exit /b 1
