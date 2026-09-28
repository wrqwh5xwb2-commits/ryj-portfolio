@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pytest -q
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
