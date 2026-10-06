@echo off
title Fluff VR Stats - install
cd /d "%~dp0"
echo.
echo   installing Fluff VR Stats :3 ...
call "%~dp0find_python.bat"
if not defined PY exit /b 1
echo   using Python: %PY%
echo.
%PY% -m pip install --upgrade pip >nul 2>&1
%PY% -m pip install --upgrade -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo   ^>w^< couldn't install the packages. check ur internet and run this again.
  echo   still stuck? ask in the Discord's #open-a-ticket with a screenshot of this window
  pause
  exit /b 1
)
echo.
echo   music support: song info, album art + controls for every music app
%PY% -m pip install --upgrade winrt-runtime winrt-Windows.Foundation winrt-Windows.Media.Control winrt-Windows.Storage.Streams >nul 2>&1
if errorlevel 1 (echo   skipped - Spotify still works) else (echo   ok!)
echo.
echo   all done!! start SteamVR, then double-click run.bat  :3
pause
