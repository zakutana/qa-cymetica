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
    # A6 of the review of 2026-09-23 (3/3): five shapes that went through.
    f"echo x > {(REPO / 'state' / 'ledger.json').as_posix()}",
    "echo x > /c/Users/adamz/Documents/Projects/cymetica-qa-agent/qa-cymetica/state/ledger.json",
    "cd state; echo x > ledger.json",
    "cd state && echo '{}' >> journal/events.jsonl",
    "python -c \"from pathlib import Path; Path('state/ledger.json').write_text('{}')\"",
    "python -c \"open(r'state\\journal\\events.jsonl','a').write('x')\"",
    "python -c \"import shutil; shutil.copy('/tmp/x.json', 'state/ledger.json')\"",
    # R07 (deep pass of 2026-09-24, 3/3): a stream prefix kept the absolute
    # and the cd forms of A6 open -- the lookbehind that spares `2>&1` spared
    # these too.
    f"echo x 2> {(REPO / 'state' / 'ledger.json').as_posix()}",
    "echo x &> /c/Users/adamz/Documents/Projects/cymetica-qa-agent/qa-cymetica/state/ledger.json",
    "cd state; ls 2> x.json",
    "cd state; ls &> x.json",
    "echo x 1> state/ledger.json",
    # Two more a 1c reader named: a write hidden in a command substitution
    # inside a quoted target, and the noclobber override `>|`.
    "echo x 2>\"$(echo > /c/Users/adamz/Documents/Projects/cymetica-qa-agent/"
    "qa-cymetica/state/ledger.json)\"",
    f"echo x >| {(REPO / 'state' / 'ledger.json').as_posix()}",
    # A `2>` inside a quoted ARGUMENT started a match whose quoted target
    # swallowed the real redirect after it (a 1c reader, second round).
    f"echo \"2>\" > {(REPO / 'state' / 'ledger.json').as_posix()} \"z\"",
    f"echo '&>' > {(REPO / 'state' / 'ledger.json').as_posix()} 'z'",
    # ...and a quoted argument that is itself a command still writes.
    f"bash -c \"echo x > {(REPO / 'state' / 'ledger.json').as_posix()}\"",
    f"eval 'echo x >> {(REPO / 'state' / 'ledger.json').as_posix()}'",
    "python -c \"import os; os.system('echo x > "
    f"{(REPO / 'state' / 'ledger.json').as_posix()}')\"",
    "bash -c \"echo x > qa/../state/ledger.json\"",
    "cd state; bash -c \"echo x > ledger.json\"",
    # An escaped quote fooled the pairing (a 1c reader, third round).
    "printf \"%s\" \"a\\\"b\" > "
    f"\"{(REPO / 'state' / 'ledger.json').as_posix()}\"",
    "cd state; echo \\\" > \"ledger.json\"",
    "cd state; echo it\\'s > 'ledger.json'",
    # A `cd` carrying a redirect writes before it moves (a 1c reader, fourth
    # round, through `>|`; the plain form was open at HEAD too).
    "cd /tmp>|x>/c/Users/adamz/Documents/Projects/cymetica-qa-agent/qa-cymetica"
    "/state/ledger.json",
    "cd /tmp>/c/Users/adamz/Documents/Projects/cymetica-qa-agent/qa-cymetica"
    "/state/ledger.json",
    # A reading that raised crashed the hook before the fixed forms were
    # asked, and a crashed hook does not block (a 1c reader, seventh round).
    "sed -i s/a/b/ state/ledger.json; echo x 2>~~:",
    "echo x >~~: ; cd state; echo y > ledger.json",
    # The shell joins `''ledger.json` into one word (a 1c reader, fourth round).
    "cd state; echo x >''ledger.json",
    "cd state; echo x > \"\"ledger.json",
    "cd state && eval \"echo x > ledger.json\"",
    "powershell -Command \"Get-Date > "
    f"{(REPO / 'state' / 'ledger.json').as_posix()}\"",
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
    # A read of state/ whose OUTPUT goes elsewhere is a read.
    "cat state/ledger.json > /tmp/ledger-copy.json",
    "python -c \"print(open('state/ledger.json').read()[:200])\"",
    "cd state && ls -la",
    # A stream sent to another stream, or to nowhere, writes nothing (R07).
    "cd state && ls 2>&1 | head",
    "ls state 2>/dev/null",
    # A `>` inside a quoted argument that names nothing under state/ writes
    # nothing there.
    "python -c \"print(1>0)\"",
    "awk '$1>0' state/ledger.json",
    "grep -c \"2>\" state/journal/events.jsonl",
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
    #
    # And the list comes from the GUARD, not from four names typed here. It was
    # four -- Write, Edit, MultiEdit, Bash -- while protect_state.py handled
    # six, so deleting `PowerShell|` from the matcher left this green, left
    # `test_shell_write_under_state_is_refused` green too (decide() calls the
    # guard directly and never reads settings.json), and left
    # `Set-Content state\ledger.json` reaching disk unhooked on the machine
    # where PowerShell is the primary shell. Rule 4 unenforced with every guard
    # green. Deep pass, 2026-09-08, 3/3.
    guard = _load()
    handled = set(guard.FILE_TOOLS) | set(guard.SHELL_TOOLS)
    assert handled, "the guard names no tools at all, so this asserts nothing"

    covered = {token.strip() for token in matcher.split("|")}
    for tool in sorted(handled):
        assert tool in covered, (
            f"{tool} is handled by protect_state.py but is not one of the "
            f"alternatives in the matcher ({sorted(covered)}), so the hook "
            f"never runs for it; a substring of another entry does not count"
        )
