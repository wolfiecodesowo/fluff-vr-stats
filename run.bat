@echo off
title Fluff VR Stats :3
cd /d "%~dp0"
python main.py
if errorlevel 1 pause
