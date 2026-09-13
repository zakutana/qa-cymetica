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
