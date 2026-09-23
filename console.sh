#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  Cymetica QA Console -- the same launcher for Git Bash / WSL.
#
#    ./console.sh              start and open the page
#    ./console.sh --port 8788  if something else holds the default port
#
#  Leave it running; Ctrl-C stops the server. Starting it twice is harmless:
#  serve.py recognises its own instance and just opens the tab.
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")"

# The Windows console codepage is cp1250, and a decode error there does not
# announce itself -- it silently yields empty output three layers away. Every
# entry point in this repo pins utf-8 for the same reason.
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

if command -v py >/dev/null 2>&1; then
  PY="py -3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "Python was not found on PATH." >&2
  exit 1
fi

echo
echo "  Starting the QA console. Ctrl-C stops it."
echo

# --ask 15 is on; see the comment block in console.cmd for why, and for what
# it costs. A later --ask on the command line wins, so `./console.sh --ask 0`
# turns it off. --sample 10 reads their API for the Nexus tab into the
# gitignored state/samples.jsonl; `./console.sh --sample 0` turns that off.
#
# --fomo 20 feeds the memecoin measurement: one capture-and-resolve round
# every twenty minutes, which is well inside the 45-minute window a checkpoint
# may still be taken in. Added 2026-09-13 because the hourly curve shipped
# unfed -- the flag defaults to 0 and neither launcher passed it, so the
# hours went by, each one past its tolerance by the time anything looked, and
# the measurement filled only when a round was run by hand. Three of the
# first day's twenty-four hours were captured. `./console.sh --fomo 0` turns
# it off.
exec $PY scripts/serve.py --open --ask 15 --sample 10 --fomo 20 --hot 20 "$@"
