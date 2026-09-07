"""PreToolUse guard: nothing hand-writes state/.

Rule 4 in CLAUDE.md says state/*.json and the journal are never edited by
hand. Until now that was enforced *after* the fact -- the hash chain in
qa/state.py raises "chain mismatch (payload edited?)" at the next load, and
tests/repo notices a ledger that its inputs no longer fold to. Both are
detection: the bad write has already happened and the next reader pays for it.

This runs before the write and refuses it, so the incident never starts.

It sees two shapes of write:

  * Write / Edit / NotebookEdit -- the file_path is under state/
  * Bash / PowerShell          -- the command redirects, truncates, moves or
                                  deletes something under state/

The second is not paranoia: this workspace does most of its file work through
bash, so a guard that only watched the file tools would leave `sed -i` and
`>>` open. What it deliberately does NOT match is a command that merely names
state/ while reading it (cat, grep, ls, git status) or the sanctioned writers,
which reach state/ through qa/state.py and never spell the path on the command
line:

    python scripts/ledger.py --run <id>      composes a run into the ledger
    python scripts/withdraw.py ...           appends a correction event
    python scripts/render.py                 rewrites the dashboard

Those are the way to change a row. If this hook fires, the answer is one of
them -- not a smaller edit.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
STATE = REPO / "state"

FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

REMEDY = (
    "A row changes only through an admissible run or a journal event:\n"
    "  python scripts/ledger.py --run <run_id>    (CHECK axis)\n"
    "  python scripts/withdraw.py ... --reason    (FILING axis, corrections)\n"
    "  python scripts/render.py                   (dashboard)\n"
    "See CLAUDE.md rules 3 and 4. If the state looks wrong, fix the run or the "
    "event, not the file."
)

# A shell command counts as a write when one of these sits next to a state/
# path. The gap between verb and path excludes newlines: a verb on one line
# has no business claiming a path on another, and letting it span turned a
# commit message that merely *described* this hook into a blocked command.
GAP = r"[^|;&\n]*"
WRITE_FORMS = [
    # > state/x, >> state/x, 2> state/x
    r">>?\s*[\"']?(?:\./)?state[/\\]",
    # sed -i ... state/x, sed --in-place
    rf"\bsed\b{GAP}(?:-i\b|--in-place){GAP}\bstate[/\\]",
    # tee state/x, tee -a state/x
    rf"\btee\b{GAP}\bstate[/\\]",
    # rm / mv / cp / truncate / touch with a state/ target
    rf"\b(?:rm|mv|cp|truncate|touch|shred|dd)\b{GAP}\bstate[/\\]",
    # PowerShell equivalents
    rf"\b(?:Set-Content|Add-Content|Clear-Content|Out-File|Remove-Item|"
    rf"Move-Item|Copy-Item|New-Item)\b{GAP}\bstate[/\\]",
    # git restoring or removing tracked state files
    rf"\bgit\s+(?:checkout|restore|rm)\b{GAP}\bstate[/\\]",
    # python -c "... open('state/x', 'w') ..."
    r"open\(\s*[\"'][^\"']*state[/\\][^\"']*[\"']\s*,\s*[\"'][arw+xb]*[aw]",
]

# Text carried *by* a command is not the command. A heredoc body and a commit
# message are payload -- prose there may name state/ freely -- so they come out
# before the forms above are applied. Quoted arguments in general do not: a
# `python -c "open('state/x','w')"` body is executable and must stay visible.
HEREDOC = re.compile(r"<<-?\s*[\"']?(\w+)[\"']?\n.*?\n\1\b", re.DOTALL)
MESSAGE_ARG = re.compile(
    r"(?:-m|--message)\s+(\"(?:[^\"\\]|\\.)*\"|'[^']*')", re.DOTALL
)


def strip_payload(command: str) -> str:
    """Remove the parts of a command that are text rather than instruction."""
    command = HEREDOC.sub(" ", command)
    return MESSAGE_ARG.sub(" ", command)


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def under_state(raw: str) -> bool:
    if not raw:
        return False
    try:
        target = Path(os.path.expandvars(raw.strip().strip("\"'"))).expanduser()
        if not target.is_absolute():
            # Against REPO, not cwd: the hook's cwd is not ours to assume.
            target = REPO / target
        target = Path(os.path.normpath(str(target)))
    except (OSError, ValueError):
        return False
    try:
        target.relative_to(STATE)
    except ValueError:
        return False
    return True


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return  # not our business; let the tool run

    tool = payload.get("tool_name", "")
    args = payload.get("tool_input") or {}

    if tool in FILE_TOOLS:
        path = args.get("file_path") or args.get("notebook_path") or ""
        if under_state(str(path)):
            deny(
                f"{tool} refused: {path} is under state/, which is written only "
                f"by qa/state.py.\n\n{REMEDY}"
            )
        return

    if tool in SHELL_TOOLS:
        command = strip_payload(str(args.get("command") or ""))
        for form in WRITE_FORMS:
            if re.search(form, command, re.IGNORECASE):
                deny(
                    "This command writes under state/, which is written only by "
                    f"qa/state.py.\n\n{REMEDY}\n\nReading state/ is fine -- cat, "
                    "grep, ls and git status are not matched."
                )
        return


if __name__ == "__main__":
    main()
