@echo off
title Fluff VR Stats - AI setup
cd /d "%~dp0"
call "%~dp0find_python.bat"
if not defined PY exit /b 1
%PY% setup_ai.py
