"""A stand-in for `claude -p`, so the company can be run without any model.

The supervisor starts it exactly as it starts the real executable (`QA_CREW_CLAUDE`
names the command) and reads what it prints the same way: one JSON result on stdout,
the shape `claude -p --output-format json` printed on 2026-10-11 (`is_error`,
`result`, `num_turns`, `total_cost_usd`, `usage`, `subtype`, `terminal_reason`).

What it does is set by `FAKE_CLAUDE_MODE`, or per department by a JSON file named in
`FAKE_CLAUDE_PLAN` ({"bugs": "ok", "desk": "bug-ticket", ...}, a department missing
from it does "ok"):

    ok            close the ticket it was given (`crew.py done`) and succeed
    silent        succeed without closing it (the supervisor must close it)
    fail          exit 1 with is_error, the work's own failure
    sleep         sleep far past any timeout (the supervisor must kill it)
    notloggedin   what an unauthenticated CLI says: an infrastructure failure
    bug-ticket    hand a bug to the Bugs department, then close its own ticket
    fail-ticket   close its ticket as failed (`crew.py fail`) and exit 0
    refused       succeed without closing, its `crew.py done` among the refused calls
    handover-refused  close its own ticket, its `crew.py ticket --to bugs` among the refused calls

Every start is appended to `FAKE_CLAUDE_LOG` (when set) with its argv, so a test can
read what the worker was allowed and denied.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _mode(argv: list[str]) -> str:
    plan = os.environ.get("FAKE_CLAUDE_PLAN")
    dept = os.environ.get("QA_CREW_DEPT", "")
    if plan and Path(plan).is_file():
        said = json.loads(Path(plan).read_text(encoding="utf-8"))
        return str(said.get(dept, said.get("*", "ok")))
    return os.environ.get("FAKE_CLAUDE_MODE", "ok")


def _crew(*args: str) -> None:
    subprocess.run([sys.executable, str(REPO / "scripts" / "crew.py"), *args],
                   cwd=str(REPO), env=os.environ.copy(), capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=60)


def _result(text: str, error: bool = False, reason: str = "completed") -> str:
    return json.dumps({
        "type": "result", "subtype": "success", "is_error": error, "result": text,
        "num_turns": 3, "total_cost_usd": 0.01, "terminal_reason": reason,
        "usage": {"input_tokens": 1200, "output_tokens": 300,
                  "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 0},
        "permission_denials": []})


def main(argv: list[str]) -> int:
    log = os.environ.get("FAKE_CLAUDE_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"argv": argv, "dept": os.environ.get("QA_CREW_DEPT"),
                                     "ticket": os.environ.get("QA_CREW_TICKET")}) + "\n")
    mode = _mode(argv)
    ticket = os.environ.get("QA_CREW_TICKET", "")
    prompt = argv[argv.index("-p") + 1] if "-p" in argv else ""
    if not ticket:
        found = re.search(r"\bT-\d{4,}\b", prompt)
        ticket = found.group(0) if found else ""
    if mode == "sleep":
        # A child of its own, as a real worker's bash or pytest would be, so a test can
        # see whether the timeout killed the tree or only the top of it.
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        marker = os.environ.get("FAKE_CLAUDE_CHILD")
        if marker:
            Path(marker).write_text(str(child.pid), encoding="utf-8")
        time.sleep(600)
        return 0
    if mode == "notloggedin":
        print(_result("Not logged in · Please run /login", error=True, reason="api_error"))
        return 1
    if mode == "fail":
        print(_result("the work failed", error=True, reason="error"))
        return 1
    if mode == "refused":
        said = json.loads(_result(f"closed {ticket}"))
        said["permission_denials"] = [{"tool_name": "Bash", "tool_input": {
            "command": f"python scripts/crew.py done {ticket} --note done"}}]
        print(json.dumps(said))
        return 0
    if mode == "handover-refused" and ticket:
        _crew("done", ticket, "--note", "handed a bug to bugs")
        said = json.loads(_result(f"handed the bug to Bugs and closed {ticket}"))
        said["permission_denials"] = [{"tool_name": "Bash", "tool_input": {
            "command": "python scripts/crew.py ticket --to bugs --kind bug --text found | tail -1"}}]
        print(json.dumps(said))
        return 0
    if mode == "bug-ticket" and ticket:
        _crew("ticket", "--to", "bugs", "--kind", "bug", "--key", f"fake-bug:{ticket}",
              "--text", f"a bug met while working {ticket}")
        _crew("done", ticket, "--note", "handed a bug to bugs")
    elif mode == "fail-ticket" and ticket:
        _crew("fail", ticket, "--why", "could not do it")
    elif mode == "ok" and ticket:
        _crew("done", ticket, "--note", "done by the fake")
    print(_result(f"fake {mode} on {ticket or 'no ticket'}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
