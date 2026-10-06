@echo off
title Fluff VR Stats - install
echo.
echo   installing Fluff VR Stats :3 ...
echo.
python -m pip install --upgrade -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo   ^>w^< couldn't install. Is Python installed? Get Python 3.10+ from python.org
  echo   and tick "Add python.exe to PATH" during setup, then run this again.
  pause
  exit /b 1
)
echo.
echo   music support: song info, album art + controls for every music app
python -m pip install --upgrade winrt-runtime winrt-Windows.Foundation winrt-Windows.Media.Control winrt-Windows.Storage.Streams >nul 2>&1
if errorlevel 1 (echo   skipped - Spotify still works) else (echo   ok!)
echo.
echo   all done!! start SteamVR, then double-click run.bat  :3
pause
