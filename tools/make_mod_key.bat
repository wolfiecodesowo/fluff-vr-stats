@echo off
title Fluff VR Stats - make the dev panel key
cd /d "%~dp0.."
call "%~dp0..\find_python.bat"
if not defined PY exit /b 1
%PY% -m pip install -q cryptography
%PY% tools\make_mod_key.py %*
pause
