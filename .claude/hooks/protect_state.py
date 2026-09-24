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


MSYS_DRIVE = re.compile(r"^/([a-zA-Z])/")


def _drive(text: str) -> str:
    """Git Bash spells C:\\ as /c/ -- an absolute path the shell writes to and
    Path() would read as \\c\\ on the current drive (A6)."""
    return MSYS_DRIVE.sub(lambda m: f"{m.group(1)}:/", text)


def under_state(raw: str, cwd: Path | None = None) -> bool:
    if not raw:
        return False
    try:
        target = Path(_drive(os.path.expandvars(raw.strip().strip("\"'")))).expanduser()
        if not target.is_absolute():
            # Against REPO (or a `cd` this command made), not the hook's own
            # cwd, which is not ours to assume.
            target = (cwd or REPO) / target
        target = Path(os.path.normpath(str(target)))
    except (OSError, ValueError):
        return False
    try:
        target.relative_to(STATE)
    except ValueError:
        return False
    return True


# A6 of the review of 2026-09-23 (3/3): the forms above read the command as
# text and missed an absolute-path redirect, `cd state; > x`, Path.write_text,
# a raw-string open(..., 'a') and shutil.copy. So the command is also walked
# segment by segment with its working directory, and every redirect target,
# and every string a Python write could be aimed at, is RESOLVED.
SEGMENT = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
CD = re.compile(r"^\s*(?:cd|Set-Location|pushd)\s+(\"[^\"]*\"|'[^']*'|\S+)\s*$", re.I)
# Any stream: `2>`, `1>`, `&>` write a file as surely as `>` (R07, deep pass of
# 2026-09-24, 3/3 -- a lookbehind that spared `2>&1` spared `2> state/x` too).
# `2>&1` and `>&2` name a stream, not a file: the target may not begin with &.
# `>|` is the noclobber override -- a write like any other.
REDIRECT = re.compile(r">(?:>|\|)?\s*(\"[^\"]*\"|'[^']*'|[^\s;|&<>]+)")
# The pattern before R07, still read beside the new one, so the new reading
# can only ADD refusals to what it replaced.
OLD_REDIRECT = re.compile(r"(?<![0-9&])>>?\s*(\"[^\"]*\"|'[^']*'|[^\s;|&<>]+)")
NOCLOBBER = re.compile(r">\|")
PY_WRITE = re.compile(
    r"\.write_text\(|\.write_bytes\(|\.unlink\(|\.rename\(|\.touch\("
    r"|\bshutil\.(?:copy\w*|move)\(|\bos\.(?:replace|rename|remove|unlink)\("
    r"|\bopen\([^)]*,\s*r?[\"'][rbt+]*[wax]", re.I)
# Single- and double-quoted strings searched apart: `python -c "..."` wraps
# the code in one, and the path inside it sits in the other.
LITERALS = (re.compile(r"(?:\b[rRbB])?'([^'\n]*)'"),
            re.compile(r"(?:\b[rRbB])?\"([^\"\n]*)\""))


QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")


def _blank_arguments(segment: str) -> str:
    """The segment with every quoted ARGUMENT blanked and every quoted
    redirect TARGET kept. A `>` inside quotes is text, not a redirect: read
    as one it swallowed the real redirect after it (`echo "2>" > .../state/x`,
    a 1c reader, 2026-09-24) and refused reads like `python -c "print(1>0)"`
    run from inside state/."""
    out, last = [], 0
    for found in QUOTED.finditer(segment):
        before = segment[:found.start()].rstrip()
        kept = before.endswith(">") or before.endswith(">|")
        out.append(segment[last:found.start()])
        out.append(found.group(0) if kept else " " * len(found.group(0)))
        last = found.end()
    out.append(segment[last:])
    return "".join(out)


def _head_writes_under_state(command: str) -> bool:
    """The reading this hook made before R07, kept VERBATIM and asked first,
    so every refusal it made is still made (1c readers, 2026-09-24: each
    round of the new reading lost some refusal of the old one, often an
    accident of how it split, and a union of patterns inside a changed loop
    did not preserve them)."""
    cwd = REPO
    for segment in SEGMENT.split(command):
        moved = CD.match(segment)
        if moved:
            path = Path(_drive(moved.group(1).strip("\"'")))
            cwd = Path(os.path.normpath(str(path if path.is_absolute() else cwd / path)))
            continue
        for found in OLD_REDIRECT.finditer(segment):
            if under_state(found.group(1), cwd):
                return True
        if PY_WRITE.search(segment):
            for literal in (m for form in LITERALS for m in form.finditer(segment)):
                if under_state(literal.group(1), cwd):
                    return True
    return False


def writes_under_state(command: str, cwd: Path | None = None) -> bool:
    """Whether any segment of `command` writes to a path under state/, with
    each `cd` followed. Reads -- cat, grep, a redirect of their output
    elsewhere, a Python read -- resolve to no write target and pass.

    The old reading first, whole; the new one only adds to it."""
    try:
        if cwd is None and _head_writes_under_state(command):
            return True
    except (RecursionError, RuntimeError, OSError, ValueError, TypeError):
        # HEAD's reading crashed the hook on the same input (`echo x >~~:`),
        # and a crashed hook does not block. Refused instead.
        return True
    try:
        return _new_writes_under_state(command, cwd or REPO)
    except (RecursionError, RuntimeError, OSError, ValueError, TypeError):
        # A reading that cannot finish cannot say the command is safe: `2>~~:`
        # made Path.expanduser raise (a 1c reader, seventh round). Refused.
        return True


def _new_writes_under_state(command: str, cwd: Path) -> bool:
    """The readings R07 added, each of which can only add a refusal."""
    # `>|` is the noclobber override, a write like `>`; read as one BEFORE the
    # split, so its `|` is not taken for a pipe -- and the split itself stays
    # HEAD's (a 1c reader, fourth round: not splitting there let `cd` swallow
    # `cd /tmp>|x>/abs/state/ledger.json` whole).
    for segment in SEGMENT.split(NOCLOBBER.sub("> ", command)):
        moved = CD.match(segment)
        if moved:
            path = Path(_drive(moved.group(1).strip("\"'")))
            after = Path(os.path.normpath(str(path if path.is_absolute() else cwd / path)))
            # A `cd` carrying a redirect -- `cd /tmp>/abs/state/x`, one word to
            # the CD pattern -- writes before it moves, against the directory
            # it starts in.
            if ">" in moved.group(1):
                target_part = moved.group(1)[moved.group(1).index(">"):]
                if writes_under_state("x " + target_part, cwd):
                    return True
            cwd = after
            continue
        # A quoted argument may be a command of its own -- `bash -c "..."`,
        # `eval '...'`, `python -c "os.system('...')"` -- so it is read as one
        # too (a 1c reader, third round: blanking alone let those through).
        for quoted in QUOTED.finditer(segment):
            inner = quoted.group(0)[1:-1]
            if ">" in inner and writes_under_state(inner, cwd):
                return True
        # A UNION of readings, so no refusal the earlier hook made can be
        # lost: its own pattern over the raw text, the new one over the raw
        # text, and the new one with quoted arguments blanked. Quote pairing
        # by regex is fooled by an escaped quote (`printf "a\"b" > "…"`, a 1c
        # reader, third round); the raw readings are not.
        readings = [m.group(1) for m in OLD_REDIRECT.finditer(segment)]
        for text in (segment, _blank_arguments(segment)):
            readings += [m.group(1) for m in REDIRECT.finditer(text)]
        for target in readings:
            # Every reading, even a bare `''`: the shell joins `''ledger.json`
            # into one word, so a quote-only target inside state/ may be a
            # write (a 1c reader, fourth round).
            if under_state(target, cwd):
                return True
            # A command run to NAME the target runs, and may write itself:
            # `2>"$(echo > .../state/x)"` (a 1c reader, 2026-09-24).
            inner = target.strip("\"'")
            if ("$(" in inner or "`" in inner) and writes_under_state(
                    inner.replace("$(", " ; ").replace("`", " ; "), cwd):
                return True
        if PY_WRITE.search(segment):
            for literal in (m for form in LITERALS for m in form.finditer(segment)):
                if under_state(literal.group(1), cwd):
                    return True
    return False


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
        # The fixed forms first: a reading that raises must not take them
        # down with it (a 1c reader, 2026-09-24 -- a hook that exits 1 is a
        # non-blocking error, so the write went ahead).
        if any(re.search(form, command, re.IGNORECASE) for form in WRITE_FORMS) \
                or writes_under_state(command):
            deny(
                "This command writes under state/, which is written only by "
                f"qa/state.py.\n\n{REMEDY}\n\nReading state/ is fine -- cat, "
                "grep, ls and git status are not matched."
            )
        return


if __name__ == "__main__":
    main()
