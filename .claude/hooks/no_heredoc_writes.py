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

WHAT IS REFUSED:

* a redirect or a tee into a repository path, on either side of the heredoc --
  `cat > f <<EOF`, `cat <<EOF > f`, `cat <<EOF | tee f`;
* a heredoc fed to a SHELL whose body redirects into one;
* a heredoc applied as a patch (`git apply`, `patch`) that names one;
* a `python - <<EOF` body that WRITES and names a repository path anywhere in
  itself.

The last of those is blunter than its one-line form sounds, and this paragraph
is wider than the sentence above it on purpose -- the docstring said something
narrower than the code twice on 2026-09-13, which is this repository's most
expensive recurring defect. Stated at full width:

* "writes" means the body CONTAINS a write call, anywhere, including inside a
  string literal. A read-only probe that happens to quote `write_text(` in a
  message is refused;
* "a path of ours" includes a BARE filename, because a bare name resolves under
  the repository root. A body writing `out.json` into a `tempfile.mkdtemp()` is
  refused, since nothing in the text says which directory it lands in;
* a body that reads `qa/fold.py` and writes only to /tmp is refused too.

Measured over the ~2 100 heredoc commands in this project's transcripts: about
9% of the refusals are of this over-broad kind, against roughly ten times as
many that are genuinely writing a repository source file. Tracing which name
holds which path works for one spelling and fails for the next (a dict of
paths, an f-string, a loop), and the cost of a false positive is one line:
move the script to the scratchpad and run it by path.

WHAT IS NOT: a heredoc CONSUMED by the program it feeds. `git commit -F -` is
how every commit here is written; a `python - <<EOF` that reads, measures or
prints is the right tool for a one-off probe. A file outside the repository is
not ours to police -- but a body that writes there and NAMES something of ours
is refused, per the paragraph above.
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
    "that only reads and prints.\n"
    "A throwaway script that has to write: put it in the scratchpad with the "
    "Write tool and run it with `python <path>`."
)

# The heredoc itself: `<<EOF`, `<<'EOF'`, `<<-"EOF"`, and its body. The rest
# of the line after the terminator belongs to the command, NOT to the body --
# `cat <<'EOF' > f` is the POSIX-canonical order and the first version of this
# pattern demanded a newline straight after the word, so it did not recognise
# that as a heredoc at all. A03, deep pass of 2026-09-13: the guard caught one
# shape of five, and the one it caught was the one its author happened to type.
#
# `\\?` is the POSIX third way of quoting the delimiter: `<<\EOF` means the
# same as `<<'EOF'`. Without it, one backslash walked past every branch of
# this hook at once -- `cat > scripts/x.py <<\EOF` was not recognised as a
# heredoc, while the identical `<<EOF` was refused. Found by the third reader
# of the 2026-09-13 rule change.
HEREDOC = re.compile(r"<<-?\s*\\?[\"']?(\w+)[\"']?([^\n]*)\n(.*?)\n\1\b",
                     re.DOTALL)

# A heredoc the SHELL itself consumes, so the writes are inside the body.
SHELL_FED = re.compile(r"(?:^|[|;&]|\s)(?:ba|z|k|da)?sh\b(?![\w.-])")
# A heredoc applied as a patch: every path it names is written.
PATCHES = re.compile(r"\bgit\s+(?:apply|am)\b|\bpatch\b")

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


# A path by its SHAPE, not by the quotes around it: something ending in a
# file extension this repository actually holds. Quote pairing is what the
# whole-body scan got wrong -- an apostrophe inside a comment shifts every
# pair after it -- and this does not depend on quoting at all. It also sees a
# bare `NEXT.md`, which has no slash: the redirect branch has always refused
# `cat > NEXT.md <<EOF` while the python branch allowed
# `Path("NEXT.md").write_text(s)`, two answers about the same file.
SUFFIXES = ("py", "md", "json", "jsonl", "ya?ml", "txt", "html", "cmd", "sh",
            "toml", "cfg", "ini", "csv", "js", "css", "lock")
PATH_SHAPED = re.compile(
    r"[A-Za-z0-9_.\-/\\]*[A-Za-z0-9_.\-]\.(?:" + "|".join(SUFFIXES) + r")\b")


def _paths(text: str) -> set[str]:
    """Every path-shaped token in `text`, however it is quoted."""
    return {m.group(0) for m in PATH_SHAPED.finditer(text)}


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
        # A heredoc fed to a SHELL carries its own redirects inside the body:
        # `bash <<'EOF'` with `echo x > scripts/thing.py` in it writes a
        # repository file while the command line itself shows nothing. Scanned
        # only for a shell, never for a python body -- `if n > 0:` would make
        # REDIRECT match `0`, and `_ours("0")` is true, so every comparison
        # would be a refusal.
        if SHELL_FED.search(head):
            for target in REDIRECT.findall(body) + TEE.findall(body):
                if target != "-" and _ours(target):
                    return True
        # A patch applied from a heredoc writes every file it names.
        if PATCHES.search(head) and any(_ours(p) for p in _paths(body)):
            return True
        # A python body that writes.
        #
        # TWO scans, and the `or` between them is load-bearing.
        #
        # The first is line-local: the statement the write call sits in, plus
        # 300 characters. The second reads the WHOLE body, because the ordinary
        # spelling binds the path to a name several lines earlier --
        #
        #     p = Path("scripts/movers.py")
        #     s = p.read_text(encoding="utf-8")
        #     p.write_text(s.replace(old, new), encoding="utf-8")
        #
        # -- where the only quoted strings near the write are "utf-8" and the
        # argument names. The hook passed exactly that on the night of
        # 2026-09-13 and a production file was mutated through a heredoc by the
        # session that had built this guard the same afternoon.
        #
        # The second scan REPLACED the first for about an hour, and a reader
        # drove both over the 1 502 heredoc commands in this project's own
        # transcripts: 497 newly refused, and **three that the old scan caught
        # and the new one let through**. One apostrophe inside a comment shifts
        # the quote pairing for the rest of the body, so `re.findall` never
        # produces the real path as a token at all. Whole-body coverage and
        # line-local coverage are each blind where the other sees; neither may
        # replace the other.
        #
        # `_paths` is there for the same reason at one level down: it finds a
        # path by its SHAPE rather than by a pair of quotes, so a token the
        # pairing skipped is still seen, and a bare `NEXT.md` -- refused by the
        # redirect branch and allowed by this one until now, on the same
        # file -- counts as a path.
        #
        # A body that reads a repository path and writes only to the scratchpad
        # is refused too. That is the intended trade: the remedy costs one line
        # and a throwaway script belongs in the scratchpad anyway.
        for opened in OPENS_FOR_WRITING.finditer(body):
            line_start = body.rfind("\n", 0, opened.start()) + 1
            around = body[line_start:opened.end() + 300]
            for quoted in re.findall(r"[\"']([^\"']{2,200})[\"']", around):
                if ("/" in quoted or "\\" in quoted) and _ours(quoted):
                    return True
        if OPENS_FOR_WRITING.search(body):
            if any(_ours(candidate) for candidate in _paths(body)):
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
