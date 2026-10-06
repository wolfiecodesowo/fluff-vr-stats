@echo off
rem Finds a working Python 3.10+ and puts the command in %PY%.
rem If there isn't one, offers to install Python automatically (winget), no PATH fiddling needed.
set "PY="
call :try py -3
if defined PY goto :eof
call :try python
if defined PY goto :eof
call :try python3
if defined PY goto :eof
for %%V in (314 313 312 311 310) do (
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" call :try "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
  if not defined PY if exist "%ProgramFiles%\Python%%V\python.exe" call :try "%ProgramFiles%\Python%%V\python.exe"
)
if defined PY goto :eof

echo.
echo   ^>w^< Python isn't installed yet (Fluff VR Stats needs it to run).
echo.
where winget >nul 2>&1
if errorlevel 1 goto :manual
choice /c YN /m "  Install Python 3.12 for you now? (free, from python.org via Windows)"
if errorlevel 2 goto :manual
echo.
echo   installing Python... this takes a minute or two :3
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY call :try py -3
if defined PY (
  echo.
  echo   Python is installed!! continuing...
  goto :eof
)
:manual
echo.
echo   please install Python 3.12 from the page that just opened:
echo     1. click the yellow "Download Python" button and run it
echo     2. IMPORTANT: tick "Add python.exe to PATH" at the bottom of the first screen
echo     3. click "Install Now", then run this file again
start "" "https://www.python.org/downloads/"
echo.
pause
exit /b 1

:try
%* -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=%*"
goto :eof
