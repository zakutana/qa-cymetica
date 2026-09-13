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

# The heredoc itself: `<<EOF`, `<<'EOF'`, `<<-"EOF"`, and its body. The rest
# of the line after the terminator belongs to the command, NOT to the body --
# `cat <<'EOF' > f` is the POSIX-canonical order and the first version of this
# pattern demanded a newline straight after the word, so it did not recognise
# that as a heredoc at all. A03, deep pass of 2026-09-13: the guard caught one
# shape of five, and the one it caught was the one its author happened to type.
HEREDOC = re.compile(r"<<-?\s*[\"']?(\w+)[\"']?([^\n]*)\n(.*?)\n\1\b", re.DOTALL)

# A redirect into a path, or a tee, on the same command as the heredoc.
REDIRECT = re.compile(r">>?\s*[\"']?([^\s\"'|;&<>]+)")
TEE = re.compile(r"\btee\b(?:\s+-\w+)*\s+[\"']?([^\s\"'|;&<>]+)")

# A python body that writes a file. Both spellings, and the path may sit on
# either side of the call: `open(p, "w")` carries it inside the parentheses,
# `Path(p).write_text(s)` carries it before them -- the first version scanned
# only forward and so missed `write_text`, which its own docstring named.
OPENS_FOR_WRITING = re.compile(
    r"open\(\s*[^)]*?[\"'][arwx+b]*[aw][arwx+b]*[\"']"
    r"|[\w.]*\([^)]*\)\s*\.\s*write_(?:text|bytes)\s*\("
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
        after, body = match.group(2), match.group(3)
        # The segment of the command line that carries this heredoc -- what
        # comes BEFORE the `<<` up to the operator that starts the command,
        # and what comes AFTER the terminator word on the same line. A
        # redirect may sit on either side: `cat > f <<EOF` and `cat <<EOF > f`
        # are the same command, and only the first was seen until 2026-09-13.
        head = command[:match.start()].rsplit("|", 1)[-1]
        head = head.rsplit(";", 1)[-1].rsplit("&&", 1)[-1]
        for segment in (head, after):
            for target in REDIRECT.findall(segment):
                if target != "-" and _ours(target):
                    return True
            for target in TEE.findall(segment):
                if _ours(target):
                    return True
        # A python body that writes a repository path. Read the whole
        # statement the call sits in, not only what follows it -- `Path(p)
        # .write_text(s)` carries its path in front of the call.
        for opened in OPENS_FOR_WRITING.finditer(body):
            line_start = body.rfind("\n", 0, opened.start()) + 1
            around = body[line_start:opened.end() + 300]
            for quoted in re.findall(r"[\"']([^\"']{2,200})[\"']", around):
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
