@echo off
rem ---------------------------------------------------------------------------
rem  Cymetica QA Console -- double-click this.
rem
rem  Starts the local server and opens the page. Leave the window open; closing
rem  it stops the server. Running it a second time does not fail: serve.py sees
rem  its own instance on the port and just opens the tab.
rem ---------------------------------------------------------------------------
setlocal
title Cymetica QA Console

rem Run from this file's own directory, whatever the working directory was.
cd /d "%~dp0"

rem The console codepage is cp1250 here, which mangles anything non-ASCII the
rem page or the logs contain. This is the same fix every entry point needs.
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

rem Prefer the launcher, fall back to python on PATH.
where py >nul 2>&1 && (set PY=py -3) || (set PY=python)

%PY% -c "import sys; sys.exit(0)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   Python was not found on PATH.
  echo   Install it, or edit this file and set PY to the full python.exe path.
  echo.
  pause
  exit /b 1
)

echo.
echo   Starting the QA console. Keep this window open.
echo   Close it, or press Ctrl-C, to stop the server.
echo.

%PY% scripts\serve.py --open %*

rem Only pause on a failure; a clean Ctrl-C should just close.
if errorlevel 1 (
  echo.
  echo   The server exited with an error. The message above says why.
  pause
)
endlocal
