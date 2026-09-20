"""A backtick inside `git commit -m` is a command substitution, not quoting.

Three times on 2026-09-20 a commit message written with `-m` lost a phrase,
because the shell ran what was between the backticks and put its output --
usually nothing, plus an error on stderr -- into the message:

    /usr/bin/bash: line 1: waived: command not found
    /usr/bin/bash: line 1: unmeasured: command not found

The commits landed. Only the sentence was wrong, and only in the place nobody
re-reads: the history. The first one claimed the check "now reads that key
FIRST" with the key name gone; the third lost the name of the bucket the whole
paragraph was about.

Why a hook rather than another reminder. This is already in a memory --
`a-rule-i-keep-breaking-needs-a-hook-not-a-reminder`, written on 2026-09-14
about the heredocs -- and the memory's own point is that a rule broken this
often needs a mechanism. The failure is quiet: git exits 0, the message is
wrong, and the cost lands on whoever reads the history next, which in this
repository is the deep pass's own retrospective.

The remedy is the one this repository already uses everywhere else: put the
message in a file and commit with `-F`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / ".claude" / "hooks" / "no_backtick_commit.py"


def _decide(command: str) -> str:
    """Run the hook exactly as the harness does: JSON in, JSON or nothing out."""
    said = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}}),
        capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert said.returncode == 0, said.stderr[:400]
    if not said.stdout.strip():
        return "allow"
    return (json.loads(said.stdout).get("hookSpecificOutput") or {}).get(
        "permissionDecision", "allow")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_three_messages_that_lost_a_word_today_are_refused():
    """The real commands, as they were typed."""
    assert _decide(
        'git commit -m "bb: the check now reads `waived` FIRST"') == "deny"
    assert _decide(
        "git commit -m 'fix' -m \"went to `unmeasured`, a bucket\"") == "deny"
    assert _decide(
        'git commit --amend -m "a `backtick` here"') == "deny"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_it_refuses_nothing_it_was_not_written_for():
    """A guard that fires on the ordinary case stops being read.

    Everything here either carries no backtick, is not a commit, or is the
    remedy itself -- and the remedy must never be refused, or the hook has
    taken away the only way out of it.
    """
    for allowed in (
            'git commit -m "no backticks in this one"',
            "git commit -F /tmp/message.txt",
            "git commit -F - < /tmp/message.txt",
            # The remedy, with a backtick in the FILE rather than the command.
            "git commit -F msg.txt && echo done",
            # Not a commit at all.
            'echo "`date`"',
            "grep -n '`waived`' tests/x.py",
            "python -c \"print('`x`')\"",
            # A backtick inside single quotes is literal to the shell, so the
            # message survives; refusing it would be refusing correct usage.
            "git commit -m 'reads `waived` first'",
    ):
        assert _decide(allowed) == "allow", allowed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_wired_and_cannot_block_by_crashing():
    """Wired into settings.json, and silent on anything it cannot parse."""
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(
        encoding="utf-8"))
    wired = json.dumps(settings)
    assert "no_backtick_commit.py" in wired, (
        "the hook exists and nothing runs it")

    said = subprocess.run([sys.executable, str(HOOK)], input="not json",
                          capture_output=True, text=True, timeout=20)
    assert said.returncode == 0 and not said.stdout.strip(), (
        "a hook that cannot read its input must get out of the way, not "
        "block every command in the session")

    spec = importlib.util.spec_from_file_location("nbc", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.substitutes("git commit -m \"a `x` b\"")
    assert not mod.substitutes("git commit -m 'a `x` b'")
