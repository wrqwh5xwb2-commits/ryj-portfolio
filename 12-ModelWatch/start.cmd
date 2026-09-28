@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  call setup.cmd
  if errorlevel 1 exit /b 1
)
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" launch.py
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
