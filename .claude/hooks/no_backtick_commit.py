"""PreToolUse guard: a commit message may not carry a live backtick.

Inside double quotes a backtick is a COMMAND SUBSTITUTION, not quoting. The
shell runs what is between the pair and puts its output -- usually nothing,
plus an error on stderr -- into the message. Three times on 2026-09-20:

    /usr/bin/bash: line 1: waived: command not found
    /usr/bin/bash: line 1: unmeasured: command not found

The commit lands. Only the sentence is wrong, and only in the place nobody
re-reads: the history, which is what the deep pass's own retrospective is
built from.

Why a hook and not a reminder. This is already a memory --
`a-rule-i-keep-breaking-needs-a-hook-not-a-reminder`, 2026-09-14, written
about the heredocs -- and its whole point is that a rule broken this often
needs a mechanism rather than restating. Same reasoning as protect_state.py
for rule 4 and no_heredoc_writes.py for the workspace: the failure is quiet,
so a person cannot be the control.

WHAT IS REFUSED: a `git commit` (or `--amend`) whose command line carries a
backtick that the shell would act on -- that is, one NOT inside single
quotes. Single quotes make it literal and the message survives, so refusing
those would be refusing correct usage.

The remedy is what this repository already does everywhere else: write the
message to a file and `git commit -F <file>`. That path is left open on
purpose; a guard that also blocked the way out of itself would just be
turned off.
"""

from __future__ import annotations

import json
import re
import sys

REMEDY = (
    "Inside double quotes a backtick runs a command and drops its OUTPUT into\n"
    "the message, so the phrase between them disappears and git still exits 0.\n"
    "This happened three times on 2026-09-20.\n\n"
    "Write the message to a file and use -F:\n"
    "  (Write tool) -> <scratchpad>/msg.txt\n"
    "  git commit -F <scratchpad>/msg.txt\n\n"
    "Single quotes are fine if the message really needs a backtick:\n"
    "  git commit -m 'reads `waived` first'"
)

COMMIT = re.compile(r"(^|[;&|]|\s)git\s+(-[^\s]+\s+)*commit\b")


def substitutes(command: str) -> bool:
    """Is there a backtick the shell would act on?

    Walks the string once, tracking quote state, because the question is not
    "is there a backtick" but "is there one outside single quotes". A
    backslash escapes the next character in double quotes and in no quotes;
    inside single quotes nothing escapes, which is the whole reason single
    quotes are the safe form.
    """
    single = double = False
    index = 0
    while index < len(command):
        char = command[index]
        if char == "\\" and not single:
            index += 2
            continue
        if char == "'" and not double:
            single = not single
        elif char == '"' and not single:
            double = not double
        elif char == "`" and not single:
            return True
        index += 1
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not COMMIT.search(command) or not substitutes(command):
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason":
            "A commit message carries a backtick the shell will run.\n" + REMEDY,
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
