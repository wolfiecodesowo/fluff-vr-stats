@echo off
rem signs the GitHub release for the version in VERSION, so apps accept the update
title Fluff VR Stats - sign the release
cd /d "%~dp0\.."
set /p TAG=<VERSION
echo   signing %TAG% ...
python tools\sign_release.py %TAG%
echo.
echo   now drag fluff-manifest.json (in this folder) into the %TAG% release on GitHub (Edit release, then Update release)
pause
