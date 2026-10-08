@echo off
rem Builds the Quest Edition on YOUR PC and puts it on the website so every Quest app updates to it.
rem It has to be built here: the APK is signed with ur PC's Android debug key, and the Quest app only
rem accepts updates signed with that same key.
rem
rem Before the first keyed build (v0.8.0): run tools\make_keys.bat and push trust.json.
title Fluff VR Stats - publish Quest Edition
cd /d "%~dp0"

findstr /c:"\"bot\"" "..\trust.json" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   no Fluff Bot key in ..\trust.json yet ~ run tools\make_keys.bat first, then try again
  pause
  exit /b 1
)

echo.
echo   building the Quest Edition...
call gradlew.bat assembleRelease
if errorlevel 1 (
  echo   ^>w^< build failed, see above
  pause
  exit /b 1
)

for /f "tokens=2 delims==" %%a in ('findstr /r /c:"versionCode = " app\build.gradle.kts') do set CODE=%%a
for /f "tokens=2 delims==" %%a in ('findstr /r /c:"versionName = " app\build.gradle.kts') do set NAME=%%a
set CODE=%CODE: =%
set NAME=%NAME: =%
set NAME=%NAME:"=%
set NAME=%NAME:-quest=%

copy /y app\build\outputs\apk\release\app-release.apk "..\docs\quest\FluffVRStats-Quest-%NAME%.apk" >nul
copy /y app\build\outputs\apk\release\app-release.apk "..\docs\quest\FluffVRStats-Quest.apk" >nul

rem minCode/minAfter: Quest apps older than v0.8.0 (code 13) must update after Nov 1 2026
> "..\docs\quest\version.json" echo {"versionCode": %CODE%, "versionName": "%NAME%", "apk": "https://wolfiecodesowo.github.io/fluff-vr-stats/quest/FluffVRStats-Quest-%NAME%.apk", "minCode": 13, "minAfter": 1793512800, "minMsg": "this Quest version is too old ~ update to keep using Fluff VR Stats. ur settings stay :3"}

echo.
echo   done!! v%NAME% (code %CODE%) is in docs\quest\
echo   install it on ur Quest + test chat and ur key, THEN commit + push docs\quest to send it to everyone :3
pause
