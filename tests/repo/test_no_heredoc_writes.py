"""A heredoc may not write a file in this repository.

CLAUDE.md has said it since 2026-09-09: *"Writing UTF-8 through bash heredocs
silently corrupts files (truncation, embedded null bytes). Use the Write and
Edit tools for file content; bash is fine for running things."*

[operator 2026-09-13] *"Ten heredoc ti porad dela problemy uz tak 50x proc ho
porad pouzivas?"*

Because appending a test with `cat >> file <<'EOF'` feels like running
something rather than writing content, and because `Edit` wants the file read
first. Both are convenience, and the rule already covers both. On 2026-09-13
alone it cost four broken files: a `\\n\\n` that became a real newline inside
a string literal, two `SyntaxWarning: invalid escape sequence` runs whose
replacement then silently did nothing, and a `print("` left unterminated.

The last of those is the one that matters. A heredoc failure is not loud: the
shell reports success, the file is wrong, and the next reader finds it. That
is why this is a hook and not a note -- a rule I have to remember is one I
demonstrably do not.

WHAT IS STILL ALLOWED. Feeding a heredoc to a program that CONSUMES it --
`git commit -F -`, `python - <<EOF` that only reads or prints. The refusal is
about a heredoc that lands in a file: a redirect into a path, or a python body
that opens one for writing.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
HOOK = REPO / ".claude" / "hooks" / "no_heredoc_writes.py"


def _hook():
    spec = importlib.util.spec_from_file_location("no_heredoc", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(command: str, tool: str = "Bash") -> dict:
    payload = {"tool_name": tool, "tool_input": {"command": command}}
    result = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else {}


def _denied(out: dict) -> bool:
    return ((out.get("hookSpecificOutput") or {}).get("permissionDecision")
            == "deny")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_two_shapes_that_actually_broke_files_are_refused():
    """Both are from 2026-09-13, verbatim in shape."""
    mod = _hook()
    # Appending a test -- the one I reached for most.
    assert mod.writes_a_file(
        "cd /repo; cat >> tests/meta/test_x.py <<'PYEOF'\ndef t(): pass\nPYEOF")
    # String surgery on a source file.
    assert mod.writes_a_file(
        "python - <<'PYEOF'\nimport io\n"
        "io.open('scripts/render.py','w').write(s)\nPYEOF")
    # And a plain truncating redirect.
    assert mod.writes_a_file("cat > qa/fomo.py <<EOF\nx = 1\nEOF")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_four_shapes_the_first_guard_let_straight_through():
    """A03, deep pass of 2026-09-13, triage 3/3. It caught one of five.

    Measured against the hook as first written: `cat >> f <<EOF` refused, and
    then `cat <<EOF > f`, `cat <<EOF >> f`, `cat <<EOF | tee f` and a heredoc
    whose python body calls `Path(p).write_text(s)` all ALLOWED. The first two
    are the POSIX-canonical order and were not even recognised as heredocs --
    the pattern demanded a newline straight after the terminator word. The
    write_text one is named in the hook's own docstring and missed because the
    scan ran forward from the call while the path sat behind it.

    A guard written because a rule was broken four times in one day was one
    keyboard habit from not applying.
    """
    mod = _hook()
    for command, what in (
        ("cat <<'EOF' > tests/meta/test_x.py\ndef t(): pass\nEOF",
         "heredoc first, then the redirect -- the canonical order"),
        ("cat <<'EOF' >> tests/meta/test_x.py\ndef t(): pass\nEOF",
         "the same, appending"),
        ("cat <<'EOF' | tee tests/meta/test_x.py\ndef t(): pass\nEOF",
         "piped into tee"),
        ("python - <<'EOF'\nfrom pathlib import Path\n"
         "Path('scripts/render.py').write_text(s)\nEOF",
         "write_text, which the hook's own docstring names"),
        ("python - <<'EOF'\nimport io\n"
         "io.open('qa/lab.py', 'w').write(s)\nEOF",
         "open(path, 'w') with the path before the call"),
    ):
        assert mod.writes_a_file(command), what


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_path_may_be_bound_to_a_name_lines_before_the_write():
    """The shape that walked straight past the widened guard, hours later.

    The session that built this hook on the afternoon of 2026-09-13 ran this
    at 21:4x, during the same deep pass, to mutate a production file:

        cp scripts/movers.py /tmp/movers.bak && python - <<'PY'
        from pathlib import Path
        p = Path("scripts/movers.py")
        s = p.read_text(encoding="utf-8")
        p.write_text(s.replace(old, new), encoding="utf-8")
        PY

    `OPENS_FOR_WRITING` matched `.write_text(` exactly as intended. What failed
    is what the hook then read for a path: the line the call sits on and 300
    characters after it, which hold only `"utf-8"`. The path is four lines up,
    bound to `p`.

    So the guard passed, the file was mutated through a heredoc, and the
    operator's *"proc ho porad pouzivas?"* had been answered with a mechanism
    that did not cover the author's own next keystroke -- for the second time
    in one day, A03 being the first.

    Tracing `p` back would fix this spelling and not the next one (a dict of
    paths, an f-string, a loop). The question asked now is the blunt one: does
    the body write, and does it name a path of ours anywhere.
    """
    mod = _hook()
    assert mod.writes_a_file(
        "cp scripts/movers.py /tmp/movers.bak && python - <<'PY'\n"
        "from pathlib import Path\n"
        "p = Path(\"scripts/movers.py\")\n"
        "s = p.read_text(encoding=\"utf-8\")\n"
        "p.write_text(s.replace(old, new), encoding=\"utf-8\")\n"
        "print(\"mutated\")\n"
        "PY"), "the path was bound to a name above the write call"

    # The same distance, through open() rather than a Path method.
    assert mod.writes_a_file(
        "python - <<'EOF'\n"
        "target = 'qa/fomo.py'\n"
        "body = compute()\n"
        "handle = open(target, 'w')\n"
        "handle.write(body)\n"
        "EOF"), "the path was a bare name in open()"

    # And a body that writes only outside the repository still passes, because
    # it names nothing of ours.
    assert not mod.writes_a_file(
        "python - <<'EOF'\n"
        "from pathlib import Path\n"
        "Path('/tmp/out.json').write_text(data)\n"
        "EOF"), "a write confined to /tmp is not ours to refuse"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_widening_the_scan_did_not_drop_what_the_narrow_one_caught():
    """One apostrophe, and the whole-body scan goes blind.

    The fix above was first written as a REPLACEMENT: the line-local scan out,
    a whole-body scan in. A reader drove both versions over the 1 502 heredoc
    commands in this project's own transcripts and found 497 newly refused --
    and three going the other way, caught by the old scan and allowed by the
    new one. Two of those three wrote `audits/_scope.json` through a heredoc,
    which is precisely what this hook exists to stop.

    The cause is `re.findall` over quote pairs. An apostrophe earlier in the
    body -- in a comment, in English prose -- pairs with the next quote
    character rather than with itself, and every pair after it is shifted, so
    the real path is never produced as a token. The line-local window started
    after that apostrophe and was unaffected.

    So the two scans are OR-ed, not swapped, and a third reading by shape
    (`_paths`) does not depend on quoting at all. A guard whose repair silently
    drops three true positives to gain 497 is not a repair.
    """
    mod = _hook()

    apostrophe = ("python - <<'EOF'\n"
                  "# fix the operator's path\n"
                  "open(\"qa/fomo.py\",\"w\").write(s)\n"
                  "EOF")
    assert mod.writes_a_file(apostrophe), (
        "an apostrophe in a comment shifted the quote pairing and the write "
        "to qa/fomo.py went unseen")

    scope = ("python - <<'PY'\n"
             "import io, json\n"
             "# the nodeids come back with '::' in them, and a '\\\\' on windows\n"
             "io.open(\"audits/_scope.json\", \"w\", encoding=\"utf-8\", "
             "newline=\"\\n\").write(json.dumps(rows))\n"
             "PY")
    assert mod.writes_a_file(scope), (
        "the real command from this project's transcripts that the widened "
        "scan let through")

    # AND the other direction, which is what makes the `or` testable at all.
    #
    # Both cases above are found by `_paths` on its own, so deleting the
    # line-local scan left every assertion here green while the docstring
    # claimed the two may not replace each other -- the assertion weaker than
    # the contract it names, in a test written tonight to pin exactly that
    # class of defect. Found by the third reader of the reworked change, who
    # was asked to mutate rather than read. These two are what line-local
    # uniquely holds: an extension `SUFFIXES` does not list, and a path with
    # no extension at all.
    assert mod.writes_a_file(
        "python - <<'EOF'\n"
        "from pathlib import Path\n"
        "Path('audits/report.log').write_text(x)\n"
        "EOF"), "`.log` is not in SUFFIXES; only the line-local scan sees this"
    assert mod.writes_a_file(
        "python - <<'EOF'\n"
        "open('.githooks/pre-commit', 'w').write(body)\n"
        "EOF"), "a path with no extension at all; line-local only"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_ways_round_it_the_three_readers_found():
    """Each one walked straight past the hook, and each is one keystroke.

    Found by the third reader of the 2026-09-13 rule change, who was asked
    whether the NEXT failure was already visible in the code rather than
    whether this one had been fixed. All four were.
    """
    mod = _hook()

    # A backslash-quoted delimiter is POSIX and means exactly what the quoted
    # form means. The pattern did not recognise it as a heredoc at all, so it
    # bypassed every branch at once -- one character.
    assert mod.writes_a_file(
        "cat > scripts/x.py <<\\EOF\nprint(1)\nEOF"), \
        "<<\\EOF is the same heredoc as <<'EOF'"

    # A bare filename has no slash. The redirect branch refused it and the
    # python branch allowed it -- two answers about the same file.
    assert mod.writes_a_file(
        "python - <<'EOF'\n"
        "from pathlib import Path\n"
        "Path(\"NEXT.md\").write_text(body)\n"
        "EOF"), "a repository file at the root still has no slash in its name"

    # A shell heredoc carries its redirects inside the body, where the old
    # scan never looked.
    assert mod.writes_a_file(
        "bash <<'EOF'\necho 'x = 1' > scripts/new_thing.py\nEOF"), \
        "the redirect was in the body, not on the command line"

    # A patch writes every file it names.
    assert mod.writes_a_file(
        "git apply <<'EOF'\n--- a/qa/fold.py\n+++ b/qa/fold.py\n"
        "@@ -1 +1 @@\n-x\n+y\nEOF"), "git apply writes what the diff names"

    # And the redirect scan must stay gated on the head invoking a shell,
    # because a python comparison looks exactly like a redirect.
    #
    # This was written as `if n > 0:` and was green for a reason it did not
    # name: REDIRECT captures `0:` there, with the colon, and `_ours("0:")`
    # is false on Windows because that is not a path. So the assertion passed
    # whether or not the gate existed. The comparison that discriminates has
    # something after it -- REDIRECT then captures a bare `0`, which resolves
    # under the repository root and IS `_ours`. Found by the third reader of
    # the reworked change, by widening SHELL_FED to match `python` and
    # noticing this test stayed green.
    assert not mod.writes_a_file(
        "python - <<'EOF'\nn = count()\nif n > 0 and n < 5:\n    print(n)\nEOF"), \
        "a greater-than in python is not a redirect: the body-redirect scan " \
        "must only run when the heredoc feeds a shell"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_heredoc_that_is_consumed_rather_than_stored_is_fine():
    """The refusal is about content landing in a file, not about heredocs.

    A commit message is the shape this must never block: it is how every
    commit in this repository is written, and a guard that stopped them would
    be turned off within the hour.
    """
    mod = _hook()
    assert not mod.writes_a_file(
        "git add -A; git commit -q -F - <<'EOF'\na message\nEOF")
    assert not mod.writes_a_file(
        "python - <<'PYEOF'\nimport json\nprint(json.load(open('x.json')))\nPYEOF")
    assert not mod.writes_a_file("python -m pytest tests/meta -q")
    assert not mod.writes_a_file(
        "python - <<'EOF'\nfor line in open('state/x.jsonl'):\n    pass\nEOF")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_file_outside_the_repository_is_not_ours_to_police():
    """The scratchpad is where a throwaway script belongs, and writing one
    there with a heredoc breaks nothing this repository reads."""
    mod = _hook()
    assert not mod.writes_a_file(
        "cat > /tmp/probe.py <<'EOF'\nprint(1)\nEOF")
    assert not mod.writes_a_file(
        "cat > \"C:/Users/adamz/AppData/Local/Temp/claude/x/probe.py\" "
        "<<'EOF'\nprint(1)\nEOF")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_denies_end_to_end_and_names_the_tool_to_use_instead():
    """Driven through the real hook, the way the harness calls it -- a guard
    asserted about in the abstract is one that can be green while never
    actually firing."""
    out = _run("cat >> tests/meta/test_x.py <<'EOF'\ndef t(): pass\nEOF")
    assert _denied(out), out
    reason = (out["hookSpecificOutput"]["permissionDecisionReason"]).lower()
    assert "write" in reason and "edit" in reason, reason

    assert not _denied(_run("git commit -F - <<'EOF'\nmsg\nEOF"))
    assert not _denied(_run("python -m pytest tests/meta -q"))
