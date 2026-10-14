@echo off
title Fluff dev panel
cd /d "%~dp0.."
call "%~dp0..\find_python.bat"
if not defined PY exit /b 1
%PY% -c "import cryptography" >nul 2>&1
if errorlevel 1 %PY% -m pip install -q cryptography
%PY% devpanel.py
if errorlevel 1 pause
