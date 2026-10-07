@echo off
title Fluff VR Stats :3 (desktop)
cd /d "%~dp0"
call "%~dp0find_python.bat"
if not defined PY exit /b 1
%PY% -c "import openvr, PIL" >nul 2>&1
if errorlevel 1 (
  echo   first time? installing what the app needs...
  %PY% -m pip install -r "%~dp0requirements.txt"
)
%PY% main.py --desktop
if errorlevel 1 pause
