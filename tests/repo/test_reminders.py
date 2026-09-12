"""What is due, said once, in the words that start it.

[operator 2026-09-12] refused a scheduler: they launch every run, as they have
all along, and what they want instead is to be told what is on the table. So
the mechanism is a sentence, not a timer -- and a sentence has the failure mode
a timer does not: it can be wrong, it can nag, and it can go quiet exactly when
it matters.

Each test here is one rule, and each rule has both directions: it fires when it
should, and it is silent when it should not. The silence half is the one worth
writing down, because a reminder that appears every evening is a reminder they
stop reading -- and they run the deep pass every evening already.

`messages` is here rather than in the deep pass's own tests because it is the
same defect in the other direction: step 1 looked for the operator's messages
by TODAY's date while the transcripts are stamped in UTC, so a pass that starts
after midnight local reads an hour of the new day and calls it "what they said
today". Nothing goes red; the pass simply learns nothing.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "processes", REPO / "scripts" / "processes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NOW = datetime(2026, 9, 12, 20, 0, tzinfo=timezone.utc)


def _ago(hours=0, days=0) -> str:
    return (NOW - timedelta(hours=hours, days=days)).isoformat()


def _facts(**over):
    base = {
        "unpushed": 0,
        "last_pass": _ago(hours=6),
        "week_last": _ago(days=1),
        "open_next": [],
        "plan_phases": [],
    }
    base.update(over)
    return base


def _says(lines, *words):
    return [line for line in lines if all(w in line for w in words)]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_deep_pass_is_named_only_when_a_night_was_missed():
    mod = _module()

    missed = mod.reminders(_facts(unpushed=12, last_pass=_ago(hours=40)), NOW)
    assert _says(missed, "jdu spat") or _says(missed, "jdu spát"), missed

    # They ran it last night and have worked since: that is the normal evening,
    # and saying anything here is the nag that gets the whole line ignored.
    quiet = mod.reminders(_facts(unpushed=12, last_pass=_ago(hours=6)), NOW)
    assert not _says(quiet, "deep pass"), quiet

    # Nothing to review is nothing to say, however long it has been.
    idle = mod.reminders(_facts(unpushed=0, last_pass=_ago(days=4)), NOW)
    assert not _says(idle, "deep pass"), idle


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_week_is_named_when_it_is_due_even_with_nothing_to_review():
    """The week rides on the deep pass, and the pass only runs when they say so.
    With `unpushed == 0` nothing else would mention it, so a quiet week is
    exactly when the retrospective would be lost."""
    mod = _module()

    due = mod.reminders(_facts(unpushed=0, week_last=_ago(days=8)), NOW)
    assert _says(due, "ýden") or _says(due, "yden"), due

    fresh = mod.reminders(_facts(week_last=_ago(days=2)), NOW)
    assert not (_says(fresh, "ýden") or _says(fresh, "yden")), fresh


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_plan_phase_with_neither_a_commit_nor_a_line_is_named():
    """The incident this rule is named for: `docs/UPGRADE-PLAN.md` decided on
    2026-09-09 to stop committing captures, nobody built it, and the store grew
    by 273 MB before anyone noticed on 2026-09-12."""
    mod = _module()

    orphan = mod.reminders(_facts(plan_phases=[
        {"plan": "docs/lab-plan.md", "id": "F5", "open": True}]), NOW)
    assert _says(orphan, "F5", "lab-plan"), orphan

    carried = mod.reminders(_facts(
        plan_phases=[{"plan": "docs/lab-plan.md", "id": "F5", "open": True}],
        open_next=["F5 z `docs/lab-plan.md`: experimenty"]), NOW)
    assert not _says(carried, "F5", "lab-plan"), carried


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_operator_s_messages_are_read_from_the_last_pass_not_from_today():
    """23:30Z yesterday and 00:30Z today are one evening to everybody except a
    date comparison."""
    mod = _module()
    rows = [
        {"type": "user", "timestamp": "2026-09-11T23:30:00.000Z",
         "message": {"content": "pockej, tohle je spatne"}},
        {"type": "user", "timestamp": "2026-09-12T00:30:00.000Z",
         "message": {"content": "a jeste jedna vec"}},
        {"type": "user", "timestamp": "2026-09-10T10:00:00.000Z",
         "message": {"content": "stara zprava"}},
        {"type": "assistant", "timestamp": "2026-09-12T00:31:00.000Z",
         "message": {"content": "not theirs"}},
    ]
    found = mod.messages(rows, since="2026-09-11T18:00:00+00:00")
    texts = [text for _, text in found]
    assert "pockej, tohle je spatne" in texts, found
    assert "a jeste jedna vec" in texts, found
    assert "stara zprava" not in texts, "older than the last pass"
    assert "not theirs" not in texts, "only what the operator said"

    # The old behaviour, kept as the failing case: today's date alone loses the
    # evening that produced the work the pass is about to review.
    by_date = [text for stamp, text in found if stamp.startswith("2026-09-12")]
    assert len(by_date) < len(texts), (
        "if every message is on today's date the fixture no longer covers the "
        "midnight case this test exists for")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_silent_when_nothing_is_due_and_never_fails(tmp_path,
                                                                monkeypatch):
    """It runs at the start of every session, so it may not be the reason one
    does not start -- and it may not reach the network: the operator's Nexus
    channel is measured by checks that count questions, and a hook that asked
    the vendor anything would be counted as one."""
    import os
    import socket
    import subprocess
    import sys

    hook = REPO / ".claude" / "hooks" / "reminders.py"
    assert hook.is_file(), "the reminder hook is the whole mechanism"

    source = hook.read_text(encoding="utf-8")
    for forbidden in ("httpx", "requests", "urllib", "socket"):
        assert forbidden not in source, (
            f"{forbidden} in a SessionStart hook: it must answer from files")

    # Nothing due, in an empty repository: it must print nothing and exit 0.
    # QA_REPO_ROOT is how the hooks here are pointed at a fixture, the same
    # way next_step.py takes QA_NEXT_FILE.
    env = {**os.environ, "QA_REPO_ROOT": str(tmp_path)}
    quiet = subprocess.run([sys.executable, str(hook)], cwd=tmp_path, env=env,
                           capture_output=True, text=True, timeout=30)
    assert quiet.returncode == 0, quiet.stderr
    assert quiet.stdout.strip() == "", quiet.stdout

    # And with the files it reads broken rather than missing.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "processes.py").write_text(
        (REPO / "scripts" / "processes.py").read_text(encoding="utf-8"),
        encoding="utf-8")
    (tmp_path / "NEXT.md").write_text("- [ ] not a date\n", encoding="utf-8")
    (tmp_path / "audits").mkdir()
    (tmp_path / "audits" / "deep-pass-progress.json").write_text(
        "{not json", encoding="utf-8")
    broken = subprocess.run([sys.executable, str(hook)], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert broken.returncode == 0, broken.stderr
    assert socket is not None  # the import above is the guard's own subject
