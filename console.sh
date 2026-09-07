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
# turns it off.
exec $PY scripts/serve.py --open --ask 15 "$@"
