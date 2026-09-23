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
    """Case-INSENSITIVELY, which is the whole of a fix from 2026-09-12.

    It was case-sensitive, and every silence assertion in this file is written
    in lower case while `reminders()` starts its sentences with a capital. So
    `not _says(quiet, "deep pass")` could never fail: three readers each set
    MISSED_NIGHT_HOURS to 0 -- the nag firing at every single session start,
    which the module docstring calls the thing that must not happen -- and the
    assertion still held. The half this file says is the one worth writing
    down was guarding nothing.
    """
    low = [w.lower() for w in words]
    return [line for line in lines if all(w in line.lower() for w in low)]


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
def test_a_missing_morning_report_is_named_so_the_session_makes_it():
    """Plan v2, V11: the report is ready at 7:00 because the overnight loop's
    tick makes it. When no tick ran, the next session start says so -- and a
    command in a reminder is run, not repeated (CLAUDE.md)."""
    mod = _module()
    missing = mod.reminders(_facts(morning_missing=True), NOW)
    assert _says(missing, "ranní přehled", "lab.py morning"), missing
    made = mod.reminders(_facts(morning_missing=False), NOW)
    assert not _says(made, "ranní přehled"), made


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_loop_on_opus_is_named_with_the_words_that_move_it_to_sonnet():
    """Plan v2, V6. The laboratory's frontmatter says `model: sonnet`, and on
    2026-09-20 its loop still made 533 calls on Opus and none on Sonnet. A
    session cannot change its own model; `/model` is the operator's, so the
    reminder names what THEY type, in the session the loop runs in."""
    mod = _module()
    opus = mod.reminders(_facts(loop_models={"claude-opus-5-5": 20,
                                             "claude-sonnet-5": 1}), NOW)
    assert _says(opus, "laborka", "/model sonnet"), opus
    sonnet = mod.reminders(_facts(loop_models={"claude-sonnet-5": 20,
                                               "claude-opus-5-5": 1}), NOW)
    assert not _says(sonnet, "/model"), sonnet
    # Two firings are the operator trying it by hand, not a loop running.
    tried = mod.reminders(_facts(loop_models={"claude-opus-5-5": 2}), NOW)
    assert not _says(tried, "/model"), tried
    assert not _says(mod.reminders(_facts(), NOW), "/model")


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
def test_the_archive_is_named_once_there_is_a_bundle_s_worth_to_carry():
    """`keep.py archive` had no trigger at all.

    The deep pass calls `keep.py track` and `keep.py snapshot`; nothing has
    ever called `archive`. So the bundle stayed the snapshot of the day it was
    first built -- 2026-09-12 -- while the manifest went on adding rows with
    `archive: ""`, and 1 145 bodies sat on disk that nothing would ever let go
    of. That is the half of the data plan that governs the disk, quietly not
    running.

    Both directions. Rebuilding the month's xz costs minutes, so a line at
    every session start over a handful of new captures is the nag that gets
    the whole reminder ignored -- and this one would fire every single day,
    because a sweep writes captures every time.
    """
    mod = _module()

    due = mod.reminders(_facts(evidence_unarchived=1145), NOW)
    assert _says(due, "keep.py archive"), due
    assert _says(due, "2026-09"), "the line has to name the month it would bundle"

    quiet = mod.reminders(_facts(evidence_unarchived=40), NOW)
    assert not _says(quiet, "archiv"), quiet
    assert not _says(mod.reminders(_facts(), NOW), "archiv")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_night_still_inside_its_own_hours_is_not_a_forgotten_session():
    """The open-session rule was written before the night existed, and a night
    is an open session on purpose -- for up to fourteen hours, by their own
    command. Nagging "close it" at every session start while the thing is
    doing exactly what it was told is how a reminder stops being read.

    C05, deep pass of 2026-09-12, triage 3/3: the two assertions below hand
    `lab_open` in ready-made, and `lab_open` without the night in it IS the
    decision under test. The clause that takes it out lives in
    `_lab_facts`, which nothing here called -- delete that line and the hook
    nags about the night's own session every session start, all night, while
    this test stays green. So the exclusion is now asserted where it is made.
    """
    mod = _module()

    assert mod.sessions_to_close(["LAB-0006", "LAB-0007"], "LAB-0007") == [
        "LAB-0006"], "the night's own session is not a session to close"
    assert mod.sessions_to_close(["LAB-0006"], None) == ["LAB-0006"]
    assert mod.sessions_to_close([], "LAB-0007") == []

    running = mod.reminders(_facts(lab_open=[], night_running="LAB-0007",
                                   night_until=_ago(hours=-8)), NOW)
    assert not _says(running, "zavře"), running
    assert _says(running, "LAB-0007"), (
        "say it is running, so a night nobody remembers starting is visible")

    forgotten = mod.reminders(_facts(lab_open=["LAB-0006"]), NOW)
    assert _says(forgotten, "LAB-0006", "laborato"), forgotten


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
def test_a_phase_is_read_whatever_letter_it_was_numbered_with():
    """The rule read `F\\d+` because the plan it was written for used F. The
    second plan of the same day numbered its phases N0..N5, and every one of
    them was invisible -- a watcher that sees only what it was written for."""
    mod = _module()

    rows = [line for line in [
        "| **N0** | Hlídka nad jejich stranou | ... | **hotovo `deadbeef`** |",
        "| N1 | Rejstřík | ... | otevřeno |",
        "| **F7** | Noc | ... | otevřeno |",
        "| not a phase | x | y | z |",
    ]]
    seen = [mod.PHASE_ROW.match(line) for line in rows]
    assert [m.group(1) if m else None for m in seen] == ["N0", "N1", "F7", None]


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

    # S01, deep pass of 2026-09-12: the window above was right and the FLOOR
    # handed to it was this pass's own start. Step 0 opens the notebook by
    # writing `at`, step 1 read it back, and the window was "since a few
    # minutes ago" -- 0 messages on an evening of a dozen, with nothing red,
    # because an empty window and a quiet evening are the same shape from
    # here. Reproduced by the pass itself, on itself.
    now = datetime(2026, 9, 12, 20, 0, tzinfo=timezone.utc)
    since, whose = mod.messages_floor(
        {"at": "2026-09-12T19:10:00+00:00",
         "previous_at": "2026-09-11T17:43:00+00:00"}, now)
    assert since == "2026-09-11T17:43:00+00:00" and whose == "the previous pass"

    since, whose = mod.messages_floor({"at": "2026-09-12T19:10:00+00:00"}, now)
    assert since == "2026-09-11T20:00:00+00:00", (
        "with no previous pass named, a day back is a poor floor and this "
        "pass's own start is no floor at all")
    assert "no previous pass" in whose, (
        "and it has to say which floor it used: wrong in this direction is "
        "silent by construction")

    since, whose = mod.messages_floor({}, now)
    assert since == "2026-09-11T20:00:00+00:00" and "no pass" in whose

    # S02, found by step 1 the first time the floor above let it see anything:
    # a compaction summary arrives in the transcript with the operator's own
    # role, and the filter that promises to drop "the harness's own blocks"
    # only dropped ones opening with `<`. Three of the 23 messages read that
    # night were walls of text I wrote myself, in the reader whose whole job
    # is to find their short corrections.
    injected = ("This session is being continued from a previous conversation "
                "that ran out of context. The summary below covers ...")
    mixed = [
        {"type": "user", "timestamp": "2026-09-12T07:57:00.000Z",
         "message": {"content": injected}},
        {"type": "user", "timestamp": "2026-09-12T08:49:00.000Z",
         "message": {"content": "takze jak to ted vypada?"}},
        {"type": "user", "timestamp": "2026-09-12T09:00:00.000Z",
         "message": {"content": "<command-name>/deep-pass</command-name>"}},
    ]
    said = [text for _, text in mod.messages(mixed, since=None)]
    assert said == ["takze jak to ted vypada?"], said


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

    # SILENCE, from the mechanism rather than from its absence. This ran the
    # hook against an empty tmp_path, where `reminders.py` returns 0 at line 37
    # because `scripts/processes.py` is not there -- so the empty stdout proved
    # the early return and nothing about whether a day with nothing due is
    # quiet. Inserting an unconditional print after the load left all seven
    # tests in this file green while the hook spoke at every session start.
    # 3/3, deep pass of 2026-09-13.
    #
    # `reminders()` is pure over its facts, so the day with nothing due can be
    # stated exactly: every rule satisfied, and not one line out.
    mod = _module()
    now = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
    settled = {
        "surface_drift": [],
        "unpushed": 0,
        "last_pass": (now - timedelta(hours=1)).isoformat(),
        "week_last": (now - timedelta(days=1)).isoformat(),
        "lab_open": [],
        "night_running": None,
        "nexus_down": 0,
        "nexus_last_try": (now - timedelta(minutes=10)).isoformat(),
        "open_next": [],
        "plan_phases": [],
    }
    assert mod.reminders(settled, now) == [], (
        f"a day with every rule satisfied still spoke: "
        f"{mod.reminders(settled, now)} -- a line printed every evening is one "
        f"the operator stops reading, which is the mechanism this replaced")

    # And each rule still fires on its own, or the silence above is silence
    # about nothing.
    # Unpushed commits alone are not a reminder -- a pass an hour ago is
    # SUPPOSED to leave some. It is unpushed work plus a pass that has not run.
    assert mod.reminders({**settled, "unpushed": 9}, now) == [], (
        "commits waiting an hour after a pass are the normal state")
    assert mod.reminders({**settled, "unpushed": 9, "last_pass": None}, now), \
        "unpushed"
    assert mod.reminders({**settled, "week_last": None}, now), "the week"
    assert mod.reminders({**settled, "lab_open": ["LAB-0003"]}, now), "lab"
    assert mod.reminders({**settled, "surface_drift": ["x moved"]}, now), "drift"

    # The hook itself must still never be the reason a session does not start,
    # in an empty repository and with the files it reads broken.
    env = {**os.environ, "QA_REPO_ROOT": str(tmp_path)}
    quiet = subprocess.run([sys.executable, str(hook)], cwd=tmp_path, env=env,
                           capture_output=True, text=True, timeout=30)
    assert quiet.returncode == 0, quiet.stderr

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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_lab_facts_counts_only_their_side_of_the_streak(tmp_path, monkeypatch):
    """`_lab_facts()` had its own looser streak: any `gave_up` counted,
    including our own read failures (`unread: ReadTimeout`, `unknown`). A
    session that failed to read three answers in a row would have reported
    Nexus as down when nothing was wrong with their channel. Now it calls
    `qa.lab.their_down_streak`, the same distinction #86's own check makes.

    One seam, not two. Until 2026-09-20 this function read the questions
    behind its own `REPO_ROOT` while the three lab readings beside it followed
    `qa.state.state_dir()`, so the test had to set both and write its fixture
    into `<tmp>/state/`. The architecture audit called that what it was -- one
    function answering from two state directories -- and the fixture now goes
    where `state_dir()` points, which is the whole of the isolation.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    mod = _module()
    mod.REPO_ROOT = tmp_path
    rows = [
        {"type": "question", "id": "NEX-1", "at": _ago(hours=3)},
        {"type": "gave_up", "id": "NEX-1", "status": "failed"},
        {"type": "question", "id": "NEX-2", "at": _ago(hours=2)},
        {"type": "gave_up", "id": "NEX-2", "status": "running"},
        {"type": "question", "id": "NEX-3", "at": _ago(hours=1)},
        {"type": "gave_up", "id": "NEX-3", "status": "unknown: ReadTimeout"},
    ]
    (tmp_path / "nexus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    facts = mod._lab_facts()
    assert facts["nexus_down"] == 0, (
        f"the newest give-up is OUR read failure, not their channel, and it "
        f"is below the 3-streak floor either way: {facts}")

    # Three of THEIRS in a row is the real thing this exists to catch.
    theirs_only = rows[:4] + [
        {"type": "question", "id": "NEX-3", "at": _ago(hours=1)},
        {"type": "gave_up", "id": "NEX-3", "status": "queued"}]
    (tmp_path / "nexus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in theirs_only), encoding="utf-8")
    assert mod._lab_facts()["nexus_down"] == 3


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_n_eff_is_named_only_past_nexus_own_collapse_threshold():
    """"when average pairwise correlation crosses ~0.6-0.7 the breadth
    collapses" -- Nexus's own words, 2026-09-12, about its own top strategy.
    Below that, a correlated pair of positions is the ordinary state of a
    small book and not worth a line every session."""
    mod = _module()

    # Words the line actually carries. The silence was asserted with
    # "koreluje" and "korelac", which "Kniha je moc korelovaná" contains
    # neither of, so the threshold set to 0 printed the nag and stayed green
    # (C04, deep pass of 2026-09-19, 3/3). The positive case below proves the
    # words match the real line before the negatives lean on them.
    collapsing = mod.reminders(_facts(n_eff={"n": 4, "rho": 0.7, "n_eff": 1.3}),
                               NOW)
    assert _says(collapsing, "1.3") and _says(collapsing, "4"), collapsing
    assert _says(collapsing, "N_eff", "korelovan"), collapsing

    calm = mod.reminders(_facts(n_eff={"n": 3, "rho": 0.2, "n_eff": 2.5}), NOW)
    assert not _says(calm, "N_eff"), calm
    assert not _says(calm, "korelovan"), calm

    # No reading at all (never run, or the book was too thin to correlate) is
    # silence, not a nag about a number nobody has.
    assert not _says(mod.reminders(_facts(n_eff=None), NOW), "N_eff")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_archive_reminder_counts_only_what_an_archive_run_could_take(
        tmp_path, monkeypatch):
    """2026-09-21: `keep.py archive` bundled everything it could and the
    reminder still said 392 -- bodies `prune_runs.py` had already let go of,
    uncited, that no archive run can ever take. A count that can never reach
    zero is a line the operator learns to skip."""
    from qa import keepset, manifest

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    here, gone = "a" * 64, "b" * 64
    body = keepset.evidence_path(here)
    body.parent.mkdir(parents=True, exist_ok=True)
    body.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(manifest, "read", lambda *a, **k: {
        here: {"id": here, "archive": ""},
        gone: {"id": gone, "archive": ""},
        "c" * 64: {"id": "c" * 64, "archive": "evidence-2026-09"}})

    assert _module()._unarchived() == 1
