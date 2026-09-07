"""The PreToolUse guard refuses writes under state/ and nothing else.

`.claude/hooks/protect_state.py` is rule 4 enforced before the write. It is
prose-adjacent by nature -- it reads shell commands with a regex -- so it has
exactly two ways to fail, and both are here:

  * it lets a hand-edit through, and the hash chain catches it a load later
  * it blocks legitimate work, and gets switched off

The second is the one that actually happened: the first commit message written
*about* this hook mentioned `rm`, `git checkout` and `state/` on separate
lines, and the guard blocked its own commit. Hence `strip_payload` and a gap
that does not span newlines, and hence the ALLOW half of this table, which is
the longer half on purpose.

Not in tests/meta: a regression here must not abort a sweep. It stops nobody
from filing a finding; it only stops the guard from guarding.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / ".claude" / "hooks" / "protect_state.py"


def _load():
    spec = importlib.util.spec_from_file_location("protect_state", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load()


def decide(payload: dict, capsys) -> str:
    """Run the guard over one hook payload; return "deny" or "allow"."""
    import io
    import sys

    stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps(payload))
    try:
        guard.main()
    except SystemExit:
        pass  # the guard exits 0 after printing its refusal
    finally:
        sys.stdin = stdin

    out = capsys.readouterr().out
    if not out.strip():
        return "allow"
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    return "deny"


DENIED_FILES = [
    "state/ledger.json",
    "state/journal/events.jsonl",
    "state/runs/run-1.json",
    "docs/../state/ledger.json",
    str(REPO / "state" / "ledger.json"),
]

ALLOWED_FILES = [
    "dashboard/index.html",
    "qa/state.py",
    "CLAUDE.md",
    "tests/repo/test_state_guard.py",
    "components.yaml",
]

DENIED_COMMANDS = [
    "echo x >> state/journal/events.jsonl",
    "echo x > state/ledger.json",
    "sed -i s/a/b/ state/ledger.json",
    "tee state/ledger.json",
    "rm state/ledger.json",
    "rm -rf state/runs",
    "mv state/ledger.json state/old.json",
    "git checkout -- state/ledger.json",
    "git restore state/journal/events.jsonl",
    "python -c \"open('state/ledger.json','w').write('{}')\"",
    "Set-Content state\\ledger.json -Value x",
    "Remove-Item state\\ledger.json",
]

# The sanctioned writers reach state/ through qa/state.py and never name the
# path, so they must pass. So must every read, and any prose that mentions the
# path without acting on it.
ALLOWED_COMMANDS = [
    "python scripts/ledger.py --run run-20260906T162414Z-a177e73",
    "python scripts/withdraw.py retract 68 --reason 'wrong tier'",
    "python scripts/render.py",
    "python -m pytest tests --prereg PRE-0039 -q",
    "python scripts/prereg.py new --selector tests --window 30 --tag",
    "cat state/ledger.json",
    "grep RAISED state/journal/events.jsonl",
    "ls -la state/runs",
    "git status --short",
    "git add state/ dashboard/index.html",
    "git diff --stat state/",
    # the commit message that blocked itself
    "git commit -m 'guard state/ before the write: refuses rm, sed -i and "
    "git checkout aimed under state/'",
    "git commit -F - <<'EOF'\nrule 4, before the write\n\nRefuses a redirect, "
    "sed -i, rm, mv or git checkout aimed under state/.\nReads are untouched: "
    "cat, grep and ls still reach state/ freely.\nEOF",
]


@pytest.mark.parametrize("path", DENIED_FILES)
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_editor_write_under_state_is_refused(path, capsys):
    assert decide({"tool_name": "Write", "tool_input": {"file_path": path}}, capsys) == "deny"
    assert decide({"tool_name": "Edit", "tool_input": {"file_path": path}}, capsys) == "deny"


@pytest.mark.parametrize("path", ALLOWED_FILES)
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_editor_write_elsewhere_passes(path, capsys):
    assert decide({"tool_name": "Write", "tool_input": {"file_path": path}}, capsys) == "allow"


@pytest.mark.parametrize("command", DENIED_COMMANDS)
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_shell_write_under_state_is_refused(command, capsys):
    tool = "PowerShell" if "-Item" in command or "-Content" in command else "Bash"
    assert decide({"tool_name": tool, "tool_input": {"command": command}}, capsys) == "deny"


@pytest.mark.parametrize("command", ALLOWED_COMMANDS)
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_reads_and_sanctioned_writers_pass(command, capsys):
    assert decide({"tool_name": "Bash", "tool_input": {"command": command}}, capsys) == "allow"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_unrelated_tools_are_not_touched(capsys):
    assert decide({"tool_name": "Read", "tool_input": {"file_path": "state/ledger.json"}}, capsys) == "allow"
    assert decide({"tool_name": "Grep", "tool_input": {"pattern": "state/"}}, capsys) == "allow"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_actually_wired_up():
    """A guard nobody invokes is a comment. Check settings.json still calls it."""
    settings = json.loads((REPO / ".claude" / "settings.json").read_text("utf-8"))
    entries = settings["hooks"]["PreToolUse"]
    wired = [
        h
        for entry in entries
        for h in entry["hooks"]
        if "protect_state.py" in " ".join(h.get("args", [])) + h.get("command", "")
    ]
    assert wired, "no PreToolUse hook runs protect_state.py"
    matcher = next(
        entry["matcher"]
        for entry in entries
        if any("protect_state.py" in " ".join(h.get("args", [])) for h in entry["hooks"])
    )
    # The matcher is an alternation, so split it and compare whole tokens.
    # `tool in matcher` was a substring test, and the collision was already in
    # the file: delete `Edit|` and "Edit" is still found inside "MultiEdit",
    # so the Edit tool would write under state/ with no hook in front of it
    # while this test stayed green. Found by the contract audit, 2026-09-07.
    covered = {token.strip() for token in matcher.split("|")}
    for tool in ("Write", "Edit", "MultiEdit", "Bash"):
        assert tool in covered, (
            f"{tool} is not one of the alternatives in the guard's matcher "
            f"({sorted(covered)}); a substring of another entry does not count"
        )
