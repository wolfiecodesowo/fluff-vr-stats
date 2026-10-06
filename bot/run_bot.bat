@echo off
title Fluff Bot :3
cd /d "%~dp0"
call "%~dp0..\find_python.bat"
if not defined PY exit /b 1
%PY% fluffbot.py
pause
