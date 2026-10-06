@echo off
title Fluff Bot setup
cd /d "%~dp0"
call "%~dp0..\find_python.bat"
if not defined PY exit /b 1
%PY% setup_bot.py
