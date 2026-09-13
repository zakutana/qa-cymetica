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

rem --ask 15 is ON here, and that is a decision rather than a default.
rem
rem Without it the console is a viewer: it redraws when a file on this machine
rem changes and never touches the network, so the bell can only ever show what
rem a sweep already fetched. The operator ran it that way for two days
rem believing the bell was live, which it was not.
rem
rem With it, the server asks their tracker and the a2a inbox every 15 minutes
rem and the bell lights on its own. The cost is real: it writes, so after a
rem change the tree is dirty until it is committed, and a run started in that
rem window cannot reach level V. That cost falls on the agent running sweeps,
rem not on the person watching the page -- which is why it is on.
rem
rem Pass --ask 0 to turn it off:  console.cmd --ask 0
rem
rem --sample 10 is on too: every ten minutes the server reads their API for the
rem Nexus tab -- our bot and our card positions, GET only -- into
rem state/samples.jsonl. That file is gitignored, so unlike --ask it never
rem dirties the tree. Pass --sample 0 to turn it off.
%PY% scripts\serve.py --open --ask 15 --sample 10 --fomo 20 %*

rem Only pause on a failure; a clean Ctrl-C should just close.
if errorlevel 1 (
  echo.
  echo   The server exited with an error. The message above says why.
  pause
)
endlocal
