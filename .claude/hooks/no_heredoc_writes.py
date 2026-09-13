"""PreToolUse guard: a heredoc may not write a file in this repository.

CLAUDE.md, since 2026-09-09: *"The bash sandbox is Linux, the workspace is
Windows. Writing UTF-8 through bash heredocs silently corrupts files
(truncation, embedded null bytes). Use the Write and Edit tools for file
content; bash is fine for running things."*

[operator 2026-09-13] *"Ten heredoc ti porad dela problemy uz tak 50x proc ho
porad pouzivas?"* -- asked after the fourth broken file of one day: a `\n\n`
inside a replacement string that became a real newline in the middle of a
Python literal, two runs whose `SyntaxWarning: invalid escape sequence` meant
the replacement silently matched nothing, and a `print("` left unterminated.

Why a hook and not a reminder. A heredoc failure is QUIET: the shell exits 0,
the file is wrong, and the cost lands on whoever reads it next. A rule that
has been in the always-loaded file for four days and was broken four times in
one afternoon is not a rule that needs restating -- it needs a mechanism, the
same reasoning that put rule 4 behind protect_state.py rather than behind the
hash chain alone.

WHAT IS REFUSED: a heredoc whose content ends up in a file inside this
repository -- `cat > f <<EOF`, `cat >> f <<EOF`, or a `python - <<EOF` body
that opens a repository path for writing.

WHAT IS NOT: a heredoc CONSUMED by the program it feeds. `git commit -F -` is
how every commit here is written; a `python - <<EOF` that reads, measures or
prints is the right tool for a one-off probe. Files outside the repository --
the scratchpad, /tmp -- are not ours to police, and a throwaway script belongs
there anyway.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

REMEDY = (
    "Use the Write tool for a new file and the Edit tool to change one. "
    "A heredoc writes through the Linux sandbox onto a Windows workspace and "
    "corrupts UTF-8 silently -- the shell still exits 0. See CLAUDE.md, "
    "\"File writes on this workspace\".\n"
    "Heredocs that are CONSUMED are fine: git commit -F -, or python - <<EOF "
    "that only reads and prints."
)

# The heredoc itself: `<<EOF`, `<<'EOF'`, `<<-"EOF"`, and its body.
HEREDOC = re.compile(r"<<-?\s*[\"']?(\w+)[\"']?\n(.*?)\n\1\b", re.DOTALL)

# A redirect into a path, on the same command as the heredoc. The gap stops
# at a pipe or a newline so a later command's redirect is not attributed here.
REDIRECT = re.compile(r">>?\s*[\"']?([^\s\"'|;&<>]+)")

# A python body that opens something for writing. `open(p, "w")`,
# `io.open(p, "w")`, `Path(p).write_text(...)`, `.write_bytes(`.
OPENS_FOR_WRITING = re.compile(
    r"open\(\s*[^)]*?[\"'][arwx+b]*[aw][arwx+b]*[\"']"
    r"|\.write_(?:text|bytes)\s*\(")

# A path we are responsible for: inside the repository, and not the temp
# areas a throwaway script belongs in.
OUTSIDE = ("/tmp/", "\\temp\\", "/temp/", "appdata", "scratchpad")


def _ours(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    if any(mark in lowered for mark in OUTSIDE):
        return False
    try:
        resolved = (REPO / path).resolve() if not Path(path).is_absolute() \
            else Path(path).resolve()
    except (OSError, ValueError):
        return False
    try:
        resolved.relative_to(REPO.resolve())
    except ValueError:
        return False
    return True


def writes_a_file(command: str) -> bool:
    """Whether this command lands heredoc content in a repository file."""
    if not command:
        return False
    for match in HEREDOC.finditer(command):
        body = match.group(2)
        # The segment of the command line that carries this heredoc, up to
        # the operator that starts it -- that is where its redirect lives.
        head = command[:match.start()].rsplit("|", 1)[-1]
        head = head.rsplit(";", 1)[-1].rsplit("&&", 1)[-1]
        for target in REDIRECT.findall(head):
            if target != "-" and _ours(target):
                return True
        # A python body that opens a repository path for writing.
        for opened in OPENS_FOR_WRITING.finditer(body):
            tail = body[opened.start():opened.start() + 300]
            for quoted in re.findall(r"[\"']([^\"']{2,200})[\"']", tail):
                if ("/" in quoted or "\\" in quoted) and _ours(quoted):
                    return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not writes_a_file(command):
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason":
            "A heredoc is writing a file inside this repository.\n" + REMEDY,
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
