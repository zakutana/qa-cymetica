"""The laboratory as a /loop: one tick every twenty minutes, all day.

[operator 2026-09-19] *"jak zadam /loop 20m jdi do laborky tak ty budes
pracovat samostatne, a komunikovat s nexusem strategie sam"* -- said after the
loop that existed had run dry. It never asked Nexus at all, and the two paths
that did ask were capped per SESSION: eight questions and three rooms, then
nothing, and a fresh session reset the count. Five rooms in six days, none
running, against their own fifty.

What this file holds is the arithmetic of a laboratory that runs all day:

  * the caps are per rolling day, so a loop cannot exhaust them in the first
    three hours and a new session cannot reset them;
  * fifty rooms fit under the 60% ceiling, which the old per-card stake made
    impossible -- a three-card room took six per cent of the book.

The sender is always stubbed, as in test_pipeline_night_spend.py: a test that
proves a brake by letting the order through is the defect it exists to stop.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
NOW = datetime(2026, 9, 19, 14, 0, tzinfo=timezone.utc)


def _scripts_lab(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)
    import qa.rooms

    importlib.reload(qa.rooms)
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_loop", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(tmp_path, name, rows):
    (tmp_path / name).write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _question(ident, when):
    return {"type": "question", "id": ident, "at": when.isoformat()}


def _whole(card):
    return "Buy " + card + " bull, sized small. " + ("reasoning. " * 40)


def _card(n):
    return f"{n:08x}-8717-4fc7-a91a-9a6724cadd7e"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_questions_are_paced_by_their_hour_not_a_count_of_ours():
    """Twenty-four a day until V5 (2026-09-23), eight a session before that.

    Per session it was eight, and a session is whatever was opened last: a
    loop ticking every twenty minutes reached eight before lunch, and opening
    a new session to get past it would have been the reset nobody meant. The
    day's count then never bound anything their own hourly limit did not --
    so it went, and the day's figure is only said, never a refusal.
    """
    rows = [_question("NEX-1", NOW - timedelta(hours=30)),
            _question("NEX-2", NOW - timedelta(hours=23)),
            _question("NEX-3", NOW - timedelta(minutes=5)),
            {"type": "answer", "id": "NEX-3", "at": NOW.isoformat()}]
    assert lab.asked_within(rows, NOW) == 2, (
        "a question thirty hours old still counted against today")

    may, why = lab.may_ask(pass_running=False)
    assert may, why
    may, why = lab.may_ask(pass_running=True)
    assert not may and "deep pass" in why.lower(), why

    for gone in ("questions_per_session", "questions_per_night",
                 "new_rooms_per_session", "questions_per_day",
                 "new_rooms_per_day", "running_experiments"):
        assert gone not in lab.CAPS, (
            f"{gone} is still a cap of ours: V5 left only their pace and the "
            f"book's ceiling")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_waits_for_their_hour_their_bound_and_their_backoff():
    """The night kept its pace in memory; a tick is a new process every twenty
    minutes, so the pace is read off the diary -- or `lab.py ask` from a loop
    would ask on every tick.

    Since V5 (2026-09-23) the pace is theirs alone. One question in flight
    and the twenty-minute floor were ours, and both went: a question five
    minutes after the last, with that one still being answered, may go --
    until their hour or their bound says otherwise."""
    def q(ident, minutes):
        return _question(ident, NOW - timedelta(minutes=minutes))

    def a(ident, minutes, kind="answer", **extra):
        return {"type": kind, "id": ident,
                "at": (NOW - timedelta(minutes=minutes)).isoformat(), **extra}

    # In flight, and five minutes old: not a brake of ours any more.
    may, why = lab.may_ask_now([q("NEX-1", 5)], NOW)
    assert may, why
    may, why = lab.may_ask_now([q("NEX-1", 15), a("NEX-1", 2)], NOW)
    assert may, why

    # Their hour: the fourth inside it waits.
    may, why = lab.may_ask_now([q("NEX-1", 50), q("NEX-2", 30), q("NEX-3", 5)],
                               NOW)
    assert not may and "hour" in why, why

    may, why = lab.may_ask_now(
        [q("NEX-1", 60), a("NEX-1", 30, kind="gave_up", status="failed",
                           retry_after_s=3600)], NOW)
    assert not may and "wait" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_their_side_turned_away_does_not_hold_our_floor():
    """NEX-0029, 2026-09-19 14:30: their deep lane answered "at capacity,
    retry after 30 s" in no time at all, and our twenty-minute floor then
    held the same question for eighteen minutes more. [operator 2026-09-19]
    *"Tak to ke trapny ne? Zbytecne cekame 20 min."* A question they refused
    outright took nothing from them, so their wait replaces ours."""
    asked = NOW - timedelta(minutes=2)
    refused = {"type": "gave_up", "id": "NEX-1", "status": "failed",
               "retry_after_s": 30,
               "at": (asked + timedelta(seconds=5)).isoformat()}

    may, why = lab.may_ask_now([_question("NEX-1", asked), refused], NOW)
    assert may, why

    longer = {**refused, "retry_after_s": 600}
    may, why = lab.may_ask_now([_question("NEX-1", asked), longer], NOW)
    assert not may and "wait" in why, why

    # And since V5 (2026-09-23) an ANSWERED one holds no floor either: the
    # floor itself went, and their hourly limit is the pace.
    answered = {"type": "answer", "id": "NEX-1",
                "at": (asked + timedelta(minutes=1)).isoformat()}
    may, why = lab.may_ask_now([_question("NEX-1", asked), answered], NOW)
    assert may, why


def _refused(ident, asked, retry):
    return [_question(ident, asked),
            {"type": "gave_up", "id": ident, "status": "failed",
             "retry_after_s": retry,
             "at": (asked + timedelta(seconds=30)).isoformat()}]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_while_the_deep_lane_is_full_the_question_goes_the_shallow_way(
        tmp_path, monkeypatch):
    """[operator 2026-09-19] said yes to the fallback Cymetica advised in
    REPLY-0018: when the deep lane is at capacity, the question goes through
    POST /api/v1/bounty/qa-agent/ask at once instead of stalling the loop --
    under the same hourly limit and bound. Without the backoff, the deep
    lane; asked for the deep lane by name, it still waits."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    sent = []

    class _Nexus:
        @staticmethod
        def ask(question, wait=True):
            sent.append(("deep", question))
            return {"id": "NEX-9"}

        @staticmethod
        def ask_shallow(question):
            sent.append(("shallow", question))
            return {"id": "NEX-9"}

    real = scripts_lab._sibling
    _Nexus.load = staticmethod(lambda: real("nexus").load())
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: _Nexus if n == "nexus" else real(n))
    real_now = datetime.now(timezone.utc)

    _write(tmp_path, "nexus.jsonl",
           _refused("NEX-0031", real_now - timedelta(minutes=2), 877))
    scripts_lab.ask("five cards?", wait=False)
    assert sent == [("shallow", "five cards?")], sent

    with __import__("pytest").raises(SystemExit) as held:
        scripts_lab.ask("five cards?", wait=False, lane="deep")
    assert "wait" in str(held.value), held.value

    _write(tmp_path, "nexus.jsonl",
           _refused("NEX-0031", real_now - timedelta(hours=2), 30))
    scripts_lab.ask("five cards?", wait=False)
    assert sent[-1] == ("deep", "five cards?"), sent

    # Their hourly limit still holds on the shallow lane (the twenty-minute
    # floor that held it before V5 went; the hour covers what it paced).
    _write(tmp_path, "nexus.jsonl",
           [*_refused("NEX-0031", real_now - timedelta(minutes=9), 877),
            _question("NEX-0032", real_now - timedelta(minutes=6)),
            {"type": "answer", "id": "NEX-0032", "lane": "shallow",
             "at": (real_now - timedelta(minutes=6)).isoformat()},
            _question("NEX-0033", real_now - timedelta(minutes=3)),
            {"type": "answer", "id": "NEX-0033", "lane": "shallow",
             "at": (real_now - timedelta(minutes=3)).isoformat()}])
    with __import__("pytest").raises(SystemExit) as paced:
        scripts_lab.ask("again?", wait=False)
    assert "hour" in str(paced.value), paced.value


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tick_says_the_shallow_way_is_open_while_the_deep_one_waits(
        tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    _write(tmp_path, "nexus.jsonl",
           _refused("NEX-0031", real_now - timedelta(minutes=2), 877))
    doors, _ = _doors()

    did = _tick(scripts_lab, real_now, doors)

    assert did["may_ask"] is True and "shallow" in did["why"], did


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_shallow_answer_is_written_where_every_answer_is(tmp_path,
                                                           monkeypatch):
    """Their sync door answers in seconds, so the question and the answer are
    both on the diary before the call returns -- the launch, the board and
    the brief then read it like any answer of his, and the row says which
    lane and what confidence it came with. A door that fails is a give-up,
    never an empty answer (rule 8)."""
    import importlib.util as util

    import httpx

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state
    importlib.reload(qa.state)
    spec = util.spec_from_file_location("nexus_shallow",
                                        REPO / "scripts" / "nexus.py")
    nexus = util.module_from_spec(spec)
    spec.loader.exec_module(nexus)
    from qa.client import build_mock_client

    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={
            "answer": "Buy " + _card(0xA) + " bull. " + "why. " * 60,
            "confidence": 0.8, "sources": ["x"]})
    monkeypatch.setattr(nexus, "_rest_client",
                        lambda: build_mock_client(handler, timeout=5.0))

    said = nexus.ask_shallow("five cards?")

    # Its own diary: #85 and #86 measure the DEEP channel off nexus.jsonl,
    # and a sync answer counted there would pass #86 on a door it is not
    # about -- a false verdict on its way to the vendor.
    assert nexus.load() == [], "a shallow row landed in the deep channel's diary"
    rows = nexus.load_shallow()
    assert [r["id"] for r in nexus.load_all()] == [r["id"] for r in rows]
    assert bodies == [{"question": "five cards?"}]
    assert [r["type"] for r in rows] == ["question", "answer"]
    assert rows[1]["id"] == said["id"] == rows[0]["id"]
    assert rows[1]["lane"] == "shallow" and rows[1]["confidence"] == 0.8
    assert _card(0xA) in rows[1]["text"]

    monkeypatch.setattr(nexus, "_rest_client", lambda: build_mock_client(
        lambda r: httpx.Response(503, json={}), timeout=5.0))
    nexus.ask_shallow("again?")
    last = nexus.load_shallow()[-1]
    assert last["type"] == "gave_up" and "503" in last["status"], last
    assert last["id"] != said["id"], "one NEX sequence across both diaries"

    # R03 (3/3): the question row is written before the call, so a failure
    # that is not a transport error must still close it -- or lab.outstanding
    # reads it as in flight and nothing may be asked for a day.
    def _broken():
        raise RuntimeError("the registry refused the door")
    monkeypatch.setattr(nexus, "_rest_client", _broken)
    with __import__("pytest").raises(RuntimeError):
        nexus.ask_shallow("third?")
    closed = nexus.load_shallow()[-1]
    assert closed["type"] == "gave_up" and closed["status"].startswith("error"), (
        closed)
    assert lab.outstanding(nexus.load_all()) == [], (
        "a question our own side failed to send is still 'being answered'")

    # And a room can open from a shallow answer: the room checks for a whole
    # answer across both diaries.
    import qa.rooms as qa_rooms
    importlib.reload(qa_rooms)
    room = qa_rooms.open_strategy(said["id"], "from the sync door")
    assert room["origin"] == said["id"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_queued_deep_job_is_still_in_flight_after_our_give_up():
    """REPLY-0019: at capacity their deep lane now QUEUES a job and runs it
    when the window frees, instead of failing it. `nexus.py answer` still
    writes a give-up at fifteen minutes -- #86 measures their published
    window with it -- but a job that is queued or running then is theirs
    still working, and the answer that lands later must be picked up. A
    failed one is finished."""
    asked = NOW - timedelta(minutes=40)
    rows = [_question("NEX-1", asked),
            {"type": "gave_up", "id": "NEX-1", "status": "queued",
             "at": (asked + timedelta(minutes=15)).isoformat()},
            _question("NEX-2", asked),
            {"type": "gave_up", "id": "NEX-2", "status": "failed",
             "at": (asked + timedelta(minutes=1)).isoformat()},
            _question("NEX-3", asked),
            {"type": "gave_up", "id": "NEX-3", "status": "running",
             "at": (asked + timedelta(minutes=15)).isoformat()},
            {"type": "answer", "id": "NEX-3",
             "at": (asked + timedelta(minutes=30)).isoformat()}]

    assert lab.outstanding(rows, NOW) == ["NEX-1"]
    # Since V5 (2026-09-23) one job in flight holds nothing back by itself:
    # REPLY-0037 bounds us at six, not one. What stops this one is their hour
    # -- three asks inside it.
    may, why = lab.may_ask_now(rows, NOW)
    assert not may and "hour" in why, why
    may, why = lab.may_ask_now(rows[:2] + rows[6:], NOW)
    assert may, why

    # R04 (3/3): and not for a day. A job their side lost -- or one whose
    # every poll errors -- is still polled for a late answer over
    # POLLABLE_HOURS; it takes one of their six slots, never the lane.
    old = NOW - timedelta(hours=2, minutes=10)
    stale = [_question("NEX-1", old),
             {"type": "gave_up", "id": "NEX-1", "status": "queued",
              "at": (old + timedelta(minutes=15)).isoformat()},
             _question("NEX-2", old - timedelta(minutes=30))]
    assert lab.outstanding(stale, NOW) == ["NEX-1", "NEX-2"], (
        "a late answer to either must still be picked up")
    may, why = lab.may_ask_now(stale, NOW)
    assert may, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_turned_away_at_the_door_is_not_in_flight():
    """NEX-0074, 2026-09-22 17:28 UTC: their wording filter answered
    QUERY_RESTRICTED before any job existed, and `nexus.py ask` wrote the
    question row with `accepted: false` and no `job_id`. `outstanding` read
    that row as a job still being answered, so the reworded question a minute
    later was refused by OUR brake -- "NEX-0074 is still being answered" --
    for the two hours of IN_FLIGHT_HOURS, over a job that never existed and
    that nothing could ever poll.

    It still counts as an ask against the hour (the test below): the filter
    ran on their side. What it cannot be is in flight."""
    asked = NOW - timedelta(minutes=1)
    refused = {**_question("NEX-1", asked), "accepted": False,
               "error": "tool error: {'error': 'QUERY_RESTRICTED'}"}
    taken = {**_question("NEX-2", asked), "accepted": True, "job_id": "j-2"}

    assert lab.outstanding([refused], NOW) == [], (
        "a question with no job on their side has nothing left to answer")
    assert lab.outstanding([refused, taken], NOW) == ["NEX-2"], (
        "one they took on is still in flight until it is answered")
    may, why = lab.may_ask_now([refused], NOW)
    assert may, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refused_question_still_counts_against_the_hour():
    """2026-09-21, 01:25 UTC: "Hourly deep-answer limit reached."

    The twenty-minute floor runs from the last question their side TOOK ON,
    because a refusal at capacity "spent nothing of theirs" and their own
    retry_after replaces our wait -- NEX-0029's reasoning, and right as far as
    it went. Four questions went inside one hour that night: one answered,
    then three that failed at 7, 6 and 2 minutes, each resetting the floor to
    their 30-second retry_after. The fourth came back saying we had reached an
    hourly limit nobody had published, and which REPLY-0037 had implied we
    could not reach at one question every twenty minutes.

    So a refusal costs them something after all. The floor keeps its reading
    -- their wait replaces ours when they ask for one -- and a second brake
    counts ASKS, refused or not, over a rolling hour. At the twenty-minute
    cadence the operator's loop runs, three fit and the fourth waits, which
    is exactly the cadence that was never supposed to reach a bound.
    """
    asked = NOW - timedelta(minutes=50)
    rows = []
    for n in range(lab.ASKS_PER_HOUR):
        ident = f"NEX-90{n}"
        at = asked + timedelta(minutes=n * 10)
        rows.append(_question(ident, at))
        rows.append({"type": "gave_up", "id": ident, "status": "failed",
                     "retry_after_s": 30,
                     "at": (at + timedelta(minutes=2)).isoformat()})

    may, why = lab.may_ask_now(rows, NOW)
    assert not may, (
        "every one of these was refused, so the floor lets the next go at "
        "once -- and their hourly limit is what stops it instead of us")
    assert "hour" in why.lower(), why

    # One fewer inside the hour, and the newest refusal old enough that their
    # own retry_after has passed: it goes.
    may, why = lab.may_ask_now(rows[:-2], NOW)
    assert may, why

    # An ask that fell out of the window does not count against it.
    old = [r for r in rows]
    old[0] = _question("NEX-900", NOW - timedelta(minutes=75))
    old[1] = {"type": "gave_up", "id": "NEX-900", "status": "failed",
              "retry_after_s": 30,
              "at": (NOW - timedelta(minutes=73)).isoformat()}
    may, why = lab.may_ask_now(old, NOW)
    assert may, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_our_own_outstanding_jobs_stay_under_their_reserved_bound():
    """REPLY-0037: the deep lane now holds a slot for us, and with it a bound
    of SIX outstanding jobs of our own. The same answer says a queued job of
    ours keeps its place for twenty-four hours instead of the one that ended
    be99d6d8 at sixty-seven minutes.

    Those two together broke a brake that used to be safe by accident. The
    in-flight window is two hours (R04, 2026-09-19): a job older than that
    stops holding the next question back, because their side had lost it. It
    HAD lost it -- an unanswered job was dead at an hour, so two hours always
    covered everything they still held. Now it does not: a job of ours can sit
    queued for a day while our pacing forgets it after two, which is one new
    question every two hours against jobs that never finish -- twelve of our
    own in a day, against their six.

    So the pacing window stays at two hours, and the BOUND is counted over
    the window their side actually keeps: POLLABLE_HOURS, the same twenty-four
    they now promise. It is not a pace, so `ignore_backoff` does not lift it.
    """
    # Since V5 (2026-09-23) there is no in-flight window of ours at all, so
    # this bound is the ONLY thing between the loop and a seventh job.
    old = NOW - timedelta(hours=2, minutes=10)
    stale = []
    for n in range(lab.OUTSTANDING_BOUND):
        stale.append(_question(f"NEX-{n}", old - timedelta(minutes=n)))

    assert len(lab.outstanding(stale, NOW)) == lab.OUTSTANDING_BOUND, (
        "every one is still pollable: none carries an answer or a give-up")
    may, why = lab.may_ask_now(stale, NOW)
    assert not may, (
        "the six are past the in-flight window, so only the bound can stop a "
        "seventh -- and without it the loop asks one every two hours for ever")
    assert str(lab.OUTSTANDING_BOUND) in why, why
    may, why = lab.may_ask_now(stale, NOW, ignore_backoff=True)
    assert not may, "their bound is not a pace and is not ours to skip"

    # One short of it goes, or the reserved slot buys us nothing.
    may, why = lab.may_ask_now(stale[:-1], NOW)
    assert may, why

    # And a finished job does not count against it, however old.
    answered = stale + [{"type": "answer", "id": "NEX-0",
                         "at": (old + timedelta(minutes=5)).isoformat()}]
    may, why = lab.may_ask_now(answered, NOW)
    assert may, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_cycle_looks_once_and_does_not_wait_on_a_queued_job(
        tmp_path, monkeypatch):
    """A queued job can sit for as long as their window stays hot; the cycle
    polling it through `nexus.answer` blocked for fifteen minutes each, past
    the ten a tick's command may take. It looks once per tick instead."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    _write(tmp_path, "nexus.jsonl", [
        _question("NEX-0035", real_now - timedelta(minutes=5))])
    looked, waited = [], []

    class _Nexus:
        @staticmethod
        def load():
            return real("nexus").load()

        @staticmethod
        def poll_once(question_id):
            looked.append(question_id)
            return {"status": "queued"}

        @staticmethod
        def answer(question_id):
            waited.append(question_id)
            return {"status": "done"}

    real = scripts_lab._sibling
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: _Nexus if n == "nexus" else
                        type("_", (), {"main": staticmethod(lambda a: 0)})
                        if n == "sampler" else real(n))
    monkeypatch.setattr(scripts_lab, "surface", lambda: {})
    monkeypatch.setattr(scripts_lab, "book_correlation", lambda: {})

    did = scripts_lab.cycle()

    assert looked == ["NEX-0035"] and waited == [], (looked, waited)
    assert did["polled"] == [{"NEX-0035": "queued"}]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_picks_up_a_question_in_flight_whatever_the_clock_says(
        tmp_path, monkeypatch):
    """The answers were picked up every half hour, so an answer that took
    three minutes waited up to thirty more before anything could launch from
    it. A question in flight is polled on every tick, and the launch is
    looked at on every tick: an answer that came back through a poll of its
    own is launched by the next tick, not the next half hour."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    doors, calls = _doors()
    real_now = datetime.now(timezone.utc)

    _tick(scripts_lab, real_now, doors)
    _write(tmp_path, "nexus.jsonl", [
        _question("NEX-0031", real_now + timedelta(minutes=1))])
    _tick(scripts_lab, real_now + timedelta(minutes=5), doors)

    assert len(calls["cycle"]) == 2, (
        "a question in flight waited for the half-hour clock")
    _tick(scripts_lab, real_now + timedelta(minutes=10), doors)
    assert len(calls["promote"]) == 3, "the launch is looked at every tick"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_new_session_does_not_reset_what_was_asked_today(tmp_path, monkeypatch):
    """The reset, through the real reader. `_asked_this_session` counted from
    the moment the open session began, so a question at nine and a session
    opened at ten read as zero asked."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    _write(tmp_path, "nexus.jsonl", [
        _question("NEX-1", real_now - timedelta(hours=2)),
        _question("NEX-2", real_now - timedelta(hours=30))])
    lab.open_session(mode="loop")

    assert scripts_lab._asked_today() == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rooms_of_a_day_are_bounded_by_the_book_not_by_a_count(
        tmp_path, monkeypatch):
    """A day's cap of new rooms (25 since 2026-09-21; ten and fifty before)
    went in V5 (2026-09-23). It was "a ceiling, not a quota" behind the gate;
    the gate stays the bar, and MONEY is the ceiling: `affordable` refuses a
    room past 60% of the book, however few opened today.

    Both halves, so the test cannot pass by the launch simply stopping: thirty
    passing cards on a roomy book all open -- past the old 25 -- and on a book
    already 60% out, none does and the refusal names the ceiling.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    cards = [_card(n) for n in range(30)]
    answers = [{"type": "answer", "id": f"NEX-{n:04d}",
                "at": (NOW - timedelta(hours=1)).isoformat(),
                "text": _whole(cards[n])} for n in range(len(cards))]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={c: _basket("BTC", "ETH") for c in cards},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    import qa.rooms as qa_rooms

    did = scripts_lab.night_promote()

    opened = qa_rooms.strategies(qa_rooms.load())
    assert did["rooms"] == len(cards) == len(opened), (did["rooms"], did["held"])
    assert not any("a day" in line for line in did["held"]), did["held"]

    # New answers on the same cards' twins, on a book already at the ceiling.
    # (The first answers are read now -- V5 reads an answer once.)
    more = [_card(0x200 + n) for n in range(5)]
    _write(tmp_path, "nexus.jsonl", answers + [
        {"type": "answer", "id": f"NEX-{n + 100:04d}", "at": answers[0]["at"],
         "text": _whole(more[n])} for n in range(len(more))])
    monkeypatch.setattr(scripts_lab, "_card_live",
                        lambda card: _basket("BTC", "ETH"))
    monkeypatch.setattr(scripts_lab, "_deployed", lambda: 150000.0)
    did = scripts_lab.night_promote()
    assert did["rooms"] == 0, did
    assert any("60%" in line for line in did["held"]), did["held"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_is_read_once_unless_something_of_it_waits(
        tmp_path, monkeypatch):
    """V5 (2026-09-23): "answers are read once; only answers with pending
    legs are re-read". Plan v1 measured 242 re-reads of answers that named
    nothing: every tick for a day walked the same answer, wrote the same
    "names no card" line, and pushed the reason that mattered off the screen.

    An answer whose every pick was decided is marked read in the notebook
    and skipped from then on. One with a pick still waiting -- a card that
    could not be read, a catalogue that did not answer, money not there yet
    -- is read again next tick, and marked read once nothing of it waits."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    waiting = _card(0x51)
    at = (NOW - timedelta(hours=1)).isoformat()
    answers = [{"type": "answer", "id": "NEX-0001", "at": at,
                "text": "Nothing worth running today. " + "why. " * 60},
               {"type": "answer", "id": "NEX-0002", "at": at,
                "text": _whole(waiting)}]
    live = {waiting: RuntimeError("HTTP 502 from their card door")}
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers, live=live,
               readings={("BTC", "ETH"): (6.5, 1.3)})
    looked = []
    real_live = scripts_lab._card_live
    monkeypatch.setattr(scripts_lab, "_card_live",
                        lambda card: looked.append(card) or real_live(card))

    first = scripts_lab.night_promote()
    assert any("NEX-0001" in h and "names no" in h for h in first["held"]), first
    assert "NEX-0001" in lab.answers_read(), "an answer that names nothing was not marked read"
    assert "NEX-0002" not in lab.answers_read(), "a pick still waiting was marked read"

    second = scripts_lab.night_promote()
    assert not any("NEX-0001" in h for h in second["held"]), (
        f"an answer read once was read again: {second['held']}")
    assert looked.count(waiting) == 2, "the waiting card was not tried again"

    # The card can be read now: its room opens, and the answer is done.
    live[waiting] = _basket("BTC", "ETH")
    third = scripts_lab.night_promote()
    assert third["rooms"] == 1, third
    assert "NEX-0002" in lab.answers_read()

    # A catalogue that did not answer is not an answer that named nothing.
    _write(tmp_path, "nexus.jsonl", answers + [
        {"type": "answer", "id": "NEX-0003", "at": at,
         "text": "Clone MACD Hunter on paper. " + "why. " * 60}])

    def unread():
        raise RuntimeError("their catalogue did not answer")
    monkeypatch.setattr(scripts_lab, "_bot_catalogue", unread)
    scripts_lab.night_promote()
    assert "NEX-0003" not in lab.answers_read(), (
        "an answer read against an unreadable catalogue was marked read")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_he_names_only_to_rule_out_opens_no_room(tmp_path, monkeypatch):
    """NEX-0064 recommended one card and listed three more under "Why the
    other three ... are out". The launch read every UUID in the text as a
    proposal and opened STR-0011 and STR-0012 on two of the rejected ones,
    with a paper order each. A card is his proposal, not his mention."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    pick, out_a, out_b, spare = _card(1), _card(2), _card(3), _card(4)
    text = (
        "**Answer: one card fits, not three.** Naming it:\n\n"
        f"**`{pick}`** -- \"NEAR Protocol Price Surges\"\n"
        "- **Side: trade UP (bull).**\n"
        "- **Take-profit +15% / stop -9%.**\n\n"
        "**Why the other two candidates are out:**\n"
        f"- **`{out_a}`** (WIF): downtrend, no up-momentum to ride long.\n"
        f"- **`{out_b}`**: fails your own gate at 7d.\n\n"
        # NEX-0065 opened STR-0016 on a card it kept only as a spare.
        f"Passed but not selected (kept as your alternate): `{spare}`, "
        "+4.17% / Sharpe 1.70.\n\n"
        "**Reader next step (allied MCP):** open the position with "
        f"`trade_event_card` (`card_id: {pick}`, `direction: \"bull\"`).\n"
        + ("reasoning. " * 40))
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(hours=1)).isoformat(), "text": text}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={c: _basket("BTC", "ETH")
                     for c in (pick, out_a, out_b, spare)},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    import qa.rooms as qa_rooms

    did = scripts_lab.night_promote()

    cards = [row.get("card") for row in qa_rooms.strategies(qa_rooms.load())]
    assert cards == [pick], (cards, did["held"])
    assert any(out_a[:8] in line and "rule" in line for line in did["held"]), (
        did["held"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_basket_their_backtest_cannot_price_is_untested_not_unread(
        tmp_path, monkeypatch):
    """NEX-0063's stock card: their backtest prices crypto legs only and said
    so -- "only 47.0% of requested basket weight could be priced". That is an
    answer, not a silence, and read as "unread" it was retried every tick for
    good. It is the absence of a test, which the gate already has a word for."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)

    def refused(*args, **kwargs):
        raise RuntimeError(
            "tool error: {'error': \"Can't backtest this basket: only 47.0% of "
            "requested basket weight could be priced (need >= 80%)\", "
            "'success': False, 'code': 'TOOL_FAILED'}")
    monkeypatch.setattr(scripts_lab, "backtest", refused)

    said = scripts_lab._gate(_card(7), [{"symbol": "META", "weight": 0.5},
                                        {"symbol": "BTC", "weight": 0.5}])
    assert said["verdict"] == "unbacktestable", said

    def down(*args, **kwargs):
        raise RuntimeError("HTTP 502 from /mcp/v1")
    monkeypatch.setattr(scripts_lab, "backtest", down)
    assert scripts_lab._gate(_card(8), [{"symbol": "BTC", "weight": 0.5},
                                        {"symbol": "ETH", "weight": 0.5}]
                             )["verdict"] == "unread", "a failed read is unread"


def _fill(stakes_for, rooms_wanted=70, book=100000.0):
    """Open rooms one after another the way the loop would, until the brakes
    stop it. Returns (rooms placed whole, deployed)."""
    free, deployed, running = book, 0.0, 0
    for n in range(rooms_wanted):
        legs = 1 + n % 3
        stakes = stakes_for(free, deployed, legs)
        placed = 0
        for stake in stakes:
            ok, _ = lab.affordable(stake, free, running, deployed=deployed)
            if not ok or stake <= 0:
                break
            free -= stake
            deployed += stake
            placed += 1
        if placed < legs:
            return running, deployed
        running += 1
    return running, deployed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_running_room_fits_under_the_ceiling(tmp_path, monkeypatch):
    """[operator 2026-09-12] fifty at once. The ceiling is 60% of the book, so a
    room may take 1.2% of it, split across its cards.

    Fifty was their floor; the count cap was 125 from 2026-09-21 (RC1) and
    went in V5 (2026-09-23). A room now takes a FIXED share of the book,
    CAPS["stake_share_of_book"], so the 60% ceiling alone is what stops the
    count -- at total_exposure / stake_share_of_book rooms, never below the
    operator's fifty. `_fill` asks for far more than that, and `affordable`
    is given no count to refuse on: the ceiling has to be what stops it.

    The negative control is the stake it replaces: 2% of what is free for EACH
    card, which runs a mix of one-, two- and three-card rooms into the 60%
    ceiling well before twenty -- and the laboratory would have read that as
    "the book is full" with thirty experiments still owed.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)

    fits = round(lab.CAPS["total_exposure"] / lab.CAPS["stake_share_of_book"])
    placed, deployed = _fill(scripts_lab._leg_stakes, rooms_wanted=fits * 3)
    assert placed >= 50, (
        f"{placed} rooms fit, against the fifty the operator asked for")
    assert fits - 1 <= placed <= fits, (
        f"{placed} rooms fit where the ceiling allows {fits}: something other "
        f"than 60% of the book stopped the count")
    assert deployed <= 100000.0 * lab.CAPS["total_exposure"] + 1e-6

    old, _ = _fill(lambda free, deployed, legs:
                   [scripts_lab._stake(free)] * legs)
    assert old < 30, (
        f"the per-card stake fitted {old} rooms: this control no longer shows "
        f"the ceiling binding, so the test above proves nothing by contrast")

    for free, out in ((100000.0, 0.0), (41000.0, 59000.0), (89000.96, 0.0)):
        for legs in (1, 2, 3, 5):
            for stake in scripts_lab._leg_stakes(free, out, legs):
                assert round(stake, 2) == stake, f"{stake} is not whole cents"
                assert stake <= free * lab.CAPS["share_of_free_cash"] + 1e-9, (
                    f"a leg of {stake} is over the per-order ceiling on {free}")

    half = scripts_lab._leg_stakes(100000.0, 0.0, 2, half=True)
    whole = scripts_lab._leg_stakes(100000.0, 0.0, 2)
    assert sum(half) <= sum(whole) / 2 + 0.01 and sum(half) > 0
    assert scripts_lab._leg_stakes(None, 0.0, 2) == [0.0, 0.0], (
        "an unreadable book is not a stake")


# --- the tick: one step, and where it stopped --------------------------------

def _doors(**over):
    """Every door a tick reaches, stubbed and counted. Nothing here touches
    their API; the real doors are named in `_tick_doors` and checked apart."""
    calls = {k: [] for k in ("fomo", "sample", "cycle", "promote", "truth",
                             "search", "verdicts", "variants", "refill", "moves",
                             "fomo_reading", "hot", "hot_reading",
                             "surface_drift")}

    def door(name, value):
        return lambda *a: calls[name].append(a) or value

    doors = {
        "pass": lambda: False, "night": lambda: False,
        # No console collecting: the tick does its own rounds.
        "console": lambda: set(),
        # And no morning report due.
        "morning": lambda: False,
        "fomo": door("fomo", {"added": 2}),
        "sample": door("sample", {"rows": 3}),
        "cycle": door("cycle", {"polled": []}),
        "promote": door("promote", {"rooms": 0, "orders": 0, "held": []}),
        "truth": door("truth", []),
        "verdicts": door("verdicts", []),
        "variants": door("variants", {"rooms": 0, "orders": 0, "held": []}),
        "moves": door("moves", [{"legs": [], "period": 30, "why": f"m{n}"}
                                for n in range(150)]),
        "refill": door("refill", [{"legs": [], "period": 90, "why": f"r{n}"}
                                  for n in range(10)]),
        "fomo_reading": door("fomo_reading", {"readouts": [], "claims": {}}),
        "hot": door("hot", {"ok": True, "hot": 100, "headlines": 3, "cards": 0}),
        "hot_reading": door("hot_reading", {"rounds": 0}),
        "surface_drift": door("surface_drift", []),
    }

    def search(bite):
        calls["search"].append([move["why"] for move in bite])
        return {"asked": len(bite), "known": 0}
    doors["search"] = search
    doors.update(over)
    return doors, calls


def _tick(scripts_lab, when, doors):
    return scripts_lab.tick(now=when, actions=doors, out=lambda *a: None)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_shows_the_newest_reasons_it_held(tmp_path, monkeypatch):
    """The launch lists its reasons oldest answer first, and the tick kept the
    first six: NEX-0049..0052 filled every line all night, and NEX-0063's
    backtest refusal -- the one that mattered -- was never on screen."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    reasons = [f"NEX-{n:04d}: old reason" for n in range(40, 49)]
    reasons.append("NEX-0063/5e25b255: the one that matters")
    doors, _ = _doors(promote=lambda: {"rooms": 0, "orders": 0,
                                       "held": reasons})

    said = _tick(scripts_lab, NOW, doors)

    assert "NEX-0063/5e25b255: the one that matters" in said["held"], said["held"]
    assert len(said["held"]) <= 6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_says_how_many_reasons_it_left_off_screen(tmp_path, monkeypatch):
    """The newest six hid the rest without a word: on 2026-09-23 NEX-0078's
    stock card fell off the screen as newer answers arrived, still retried
    every tick, and a session spent an hour looking for why the launch had
    dropped it. A cut that is not said reads as an absence."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    reasons = [f"NEX-{n:04d}: reason" for n in range(40, 50)]
    doors, _ = _doors(promote=lambda: {"rooms": 0, "orders": 0,
                                       "held": reasons})
    printed = []

    scripts_lab.tick(now=NOW, actions=doors, out=printed.append)

    assert any("4 older" in line for line in printed), printed

    printed.clear()
    doors, _ = _doors(promote=lambda: {"rooms": 0, "orders": 0,
                                       "held": reasons[:6]})
    scripts_lab.tick(now=NOW + timedelta(minutes=20), actions=doors,
                     out=printed.append)
    assert not any("older" in line for line in printed), printed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_carries_on_the_walk_where_the_last_one_stopped(
        tmp_path, monkeypatch):
    """A tick is a fresh process every twenty minutes. The night held its
    queue in memory for fourteen hours; a tick that started the walk again
    each time would re-read the same first bite forever and call it work."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    doors, calls = _doors()
    bite = scripts_lab.TICK["search_bite"]

    _tick(scripts_lab, NOW, doors)
    _tick(scripts_lab, NOW + timedelta(minutes=20), doors)

    assert len(calls["moves"]) == 1, "the walk was seeded twice"
    assert calls["search"][0][0] == "m0"
    assert calls["search"][1][0] == f"m{bite}", (
        f"the second tick began at {calls['search'][1][0]}, not where the "
        f"first stopped")

    for n in range(2, 6):
        _tick(scripts_lab, NOW + timedelta(minutes=20 * n), doors)
    assert calls["refill"], "the first queue ran out and nothing refilled it"
    walked = [why for bite_ in calls["search"] for why in bite_]
    assert walked[:150] == [f"m{n}" for n in range(150)], "a move was skipped"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_keeps_the_nights_clocks(tmp_path, monkeypatch):
    """Answers are picked up every half hour and the ranking every six --
    the night's own pace, carried between processes."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    doors, calls = _doors()

    for n in range(4):  # 0, 20, 40, 60 minutes
        _tick(scripts_lab, NOW + timedelta(minutes=20 * n), doors)

    assert len(calls["cycle"]) == 2, calls["cycle"]
    assert len(calls["promote"]) == 4, (
        "the launch is looked at on every tick -- an answer can come back "
        "through its own poll between two cycles")
    assert len(calls["truth"]) == 1
    assert len(calls["fomo"]) == 4, "a memecoin checkpoint is perishable"
    assert len(calls["verdicts"]) == 4

    # Hot against control is written into the diary every six hours: often
    # enough to watch it move, rarely enough that the diary stays readable.
    assert len(calls["fomo_reading"]) == 1
    assert len(calls["hot"]) == 4, "Hot has no history; every tick is a round"
    assert len(calls["hot_reading"]) == 1
    _tick(scripts_lab, NOW + timedelta(hours=6, minutes=10), doors)
    assert len(calls["fomo_reading"]) == 2
    assert len(calls["hot_reading"]) == 2
    kept = [r for r in lab.load() if r.get("type") == "fomo_reading"]
    assert len(kept) == 2 and "readouts" in kept[0]
    assert len([r for r in lab.load() if r.get("type") == "hot_reading"]) == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_that_finds_another_one_running_does_nothing(tmp_path, monkeypatch):
    """A /loop at ten minutes fires again while a tick that caught up after a
    pause is still inside its launch. Two ticks walking the same answers is
    two paper orders for one proposal. The second one steps aside -- unless
    the first has been gone so long it must have died."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    doors, calls = _doors()
    marker = scripts_lab._tick_marker()
    marker.write_text(json.dumps({"pid": 1, "at": NOW.isoformat()}), encoding="utf-8")

    printed = []
    said = scripts_lab.tick_exclusive(now=NOW + timedelta(minutes=10),
                                      actions=doors, out=printed.append)
    assert said["busy"] and not any(calls.values()), "the running tick owns the work"
    assert marker.exists(), "and its marker is left for it to remove"
    assert printed[-1] == "decide: none", (
        "V6: the firing that stepped aside has nothing to wake the manager for")

    said = scripts_lab.tick_exclusive(
        now=NOW + timedelta(minutes=scripts_lab.TICK_STALE_MINUTES + 1),
        actions=doors, out=lambda *a: None)
    assert not said.get("busy") and calls["fomo"], "a stale marker is taken over"
    assert not marker.exists(), "and removed when this tick ends"

    # C01, deep pass of 2026-09-21: everything above ran against a marker this
    # test wrote, so a tick that never wrote its own passed. The marker has to
    # be there WHILE a tick runs, and the command a /loop runs has to be the
    # exclusive one.
    seen = []
    doors["fomo"] = lambda *a: seen.append(marker.exists()) or {"added": 0}
    scripts_lab.tick_exclusive(now=NOW + timedelta(hours=2), actions=doors,
                               out=lambda *a: None)
    assert seen == [True], "a running tick holds its own marker"
    assert not marker.exists()

    routed = []
    monkeypatch.setattr(scripts_lab, "tick_exclusive",
                        lambda **kw: routed.append("exclusive") or {})
    monkeypatch.setattr(scripts_lab, "tick",
                        lambda **kw: routed.append("bare") or {})
    scripts_lab.main(["tick"])
    assert routed == ["exclusive"], "`lab.py tick` is the exclusive tick"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_first_tick_of_a_day_closes_yesterday_and_opens_today(
        tmp_path, monkeypatch):
    """A loop has no last tick to close a session with, so the day is the
    session: the first tick after midnight UTC closes yesterday's with what
    it counted and what was written as a lesson, and opens today's. LAB-0004
    was opened by hand on 2026-09-13 and left open for six days."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    yesterday = NOW - timedelta(days=1)
    lab._append({"type": "session", "state": "open", "session": "LAB-0004",
                 "mode": "session", "at": yesterday.isoformat()})
    lab.note_entry("LAB-0004", "Nexus names SOL cards when asked for crypto",
                   kind="lesson")
    lab.note_entry("LAB-0004", "retry STR-0005 at the US open", kind="next")
    doors, _ = _doors()

    did = _tick(scripts_lab, NOW, doors)
    again = _tick(scripts_lab, NOW + timedelta(minutes=20), doors)

    closed = lab.last_close()
    assert closed["session"] == "LAB-0004"
    assert any("SOL" in lesson for lesson in closed["lessons"]), closed
    assert len(closed["lessons"]) <= lab.MAX_LESSONS
    assert closed["next"] == ["retry STR-0005 at the US open"]
    (today,) = lab.open_sessions()
    assert today != "LAB-0004" and did["session"] == today
    assert again["session"] == today, "a second tick opened a second session"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_during_a_deep_pass_or_a_night_only_reads_memecoins_and_hot(
        tmp_path, monkeypatch):
    """The pass verifies #85-#87 over the very answers and trades a tick
    would write, and a night is another process walking the same queue. The
    memecoin checkpoints and the Hot round are neither -- read-only, each into
    its own diary -- and they are what is gone for good if a tick skips them
    (the Hot round since 2026-09-21, RC3)."""
    for blocker in ("pass", "night"):
        (tmp_path / blocker).mkdir()
        scripts_lab = _scripts_lab(tmp_path / blocker, monkeypatch)
        doors, calls = _doors(**{blocker: lambda: True})

        did = _tick(scripts_lab, NOW, doors)

        assert did["skipped"] == blocker
        assert len(calls["fomo"]) == 1
        # EVERY door but the memecoin one, read off `calls` rather than from
        # a list written by hand. The list named five of ten, so `truth` -- a
        # live read of their ground-truth tools -- and `moves`, `refill` and
        # `fomo_reading` could all have run under a name that says "only
        # reads the memecoins". Enumerating what you expect is how a check
        # stops covering what you did not think of; found by three readers on
        # 2026-09-20.
        #
        # The Hot round is the second exemption (2026-09-21), for the same
        # two reasons as the memecoins, each one refutable: it reads only
        # their headlines and card histories -- no Nexus answer, no trade, so
        # nothing #85-#87 verify -- and Hot has no history, so a round a
        # pass skips is a moment nobody can read again. Its six-hourly
        # READING is not exempt; it waits like everything else.
        assert len(calls["hot"]) == 1
        for door, made in sorted(calls.items()):
            if door in ("fomo", "hot"):
                continue
            assert not made, f"{door} ran while a {blocker} was on"
        assert did["may_ask"] is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_first_tick_from_six_forty_says_the_morning_report_is_due(
        tmp_path, monkeypatch):
    """Plan v2, V11 -- no scheduler: the overnight loop's own tick says the
    report is due and how to make it, even while a deep pass holds the rest
    (the report is read-only and the pass's own notebook is one of its
    inputs)."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    for blocker in (False, True):
        doors, _ = _doors(morning=lambda: True, **{"pass": lambda: blocker})
        printed = []
        said = scripts_lab.tick(now=NOW, actions=doors, out=printed.append)
        assert said["morning_due"] is True
        assert any("lab.py morning" in line for line in printed), printed
    doors, _ = _doors()
    printed = []
    said = scripts_lab.tick(now=NOW + timedelta(minutes=20), actions=doors,
                            out=printed.append)
    assert not said["morning_due"]
    assert not any("lab.py morning" in line for line in printed), printed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_leaves_a_round_to_the_console_that_is_collecting_it(
        tmp_path, monkeypatch):
    """Plan v2, V4: one writer per diary. The console's timers (serve.py
    --fomo, --hot, --sample) and the tick both went round the same diaries --
    two readers of their API writing the same rows. The console does it now
    when it runs; a tick skips exactly the rounds the console says it is
    doing and still does the rest, so a console closed overnight loses no
    checkpoint (they cannot be read again later)."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    doors, calls = _doors(console=lambda: {"fomo", "hot", "sample"})
    printed = []
    said = scripts_lab.tick(now=NOW, actions=doors, out=printed.append)
    assert not calls["fomo"] and not calls["hot"] and not calls["sample"], calls
    assert said["fomo"] == said["hot"] == said["sample"] == {"by": "console"}
    assert any("by the console" in line for line in printed), printed

    doors, calls = _doors(console=lambda: {"fomo"})
    _tick(scripts_lab, NOW + timedelta(minutes=20), doors)
    assert not calls["fomo"], "the console collects the memecoins"
    assert calls["hot"] and calls["sample"], "the rest is still the tick's"

    def down():
        raise OSError("connection refused")
    doors, calls = _doors(console=down)
    said = _tick(scripts_lab, NOW + timedelta(minutes=40), doors)
    assert calls["fomo"] and calls["hot"] and calls["sample"], (
        "a console that does not answer collects nothing")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_writes_down_what_it_did_and_whether_a_question_may_go(
        tmp_path, monkeypatch):
    """The diary is what tells the next tick where this one stopped, and the
    question is the agent's to write -- so the tick says whether one may go
    and why not, and asks nothing itself."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    # Their bound (V5 left only their pace): six of ours outstanding.
    _write(tmp_path, "nexus.jsonl", [
        _question(f"NEX-003{n}", real_now - timedelta(hours=2, minutes=n))
        for n in range(lab.OUTSTANDING_BOUND)])
    doors, _ = _doors()

    did = _tick(scripts_lab, real_now, doors)

    assert did["may_ask"] is False and "NEX-0030" in did["why"], did
    ticks = [r for r in lab.load() if r.get("type") == "tick"]
    assert len(ticks) == 1 and ticks[0]["session"] == did["session"]
    assert ticks[0]["backtests"] == scripts_lab.TICK["search_bite"]
    assert "ask" not in scripts_lab._tick_doors(), (
        "the tick holds a door that asks Nexus; the question is composed "
        "from the diary by whoever runs the tick")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_that_may_ask_still_sends_nothing(tmp_path, monkeypatch):
    """The key name above is a name. L07 (2/3): a door under another name, or
    a direct call inside tick(), would have asked and stayed green -- and in
    that test a question could not go anyway. Here one may, and every way
    into Nexus the tick could reach is watched."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    sent = []
    real = scripts_lab._sibling

    class _Nexus:
        @staticmethod
        def load():
            return []

        @staticmethod
        def load_all():
            return []

        @staticmethod
        def ask(*a, **k):
            sent.append(("ask", a))

        @staticmethod
        def ask_shallow(*a, **k):
            sent.append(("ask_shallow", a))

        @staticmethod
        def poll_once(*a, **k):
            return {"status": "done"}

    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: _Nexus if n == "nexus" else real(n))
    doors, _ = _doors()

    did = _tick(scripts_lab, datetime.now(timezone.utc), doors)

    assert did["may_ask"] is True, did
    assert sent == [], f"the tick asked Nexus by itself: {sent}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_position_that_resolved_without_us_is_written_down_once(
        tmp_path, monkeypatch):
    """`resolved_without_us` reported the same position on every status and
    wrote nothing -- 85.76 USDC on e579581b, 2026-09-19 12:40, printed on
    every tick. A tick records it once, and the book of what the laboratory
    earned can then count it."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _write(tmp_path, "paper.jsonl", [
        {"type": "intent", "id": "TRD-1", "card_id": "c1", "usdc": 10.0},
        {"type": "outcome", "id": "TRD-1", "outcome": "accepted",
         "position_id": "p1"}])
    _write(tmp_path, "samples.jsonl", [
        {"type": "sample", "kind": "position", "at": "2026-09-19T12:40:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "closed",
         "realized_pnl_usdc": 85.76}])
    doors, _ = _doors()

    first = _tick(scripts_lab, NOW, doors)
    second = _tick(scripts_lab, NOW + timedelta(minutes=20), doors)

    written = [r for r in lab.load() if r.get("type") == "resolved"]
    assert [r["position_id"] for r in written] == ["p1"]
    assert written[0]["realized_pnl_usdc"] == 85.76
    assert first["resolved"] == 1 and second["resolved"] == 0


# --- the board and the brief: what earned, and what to ask next -------------

def _intent(ident, card, usdc, origin):
    return {"type": "intent", "id": ident, "card_id": card, "usdc": usdc,
            "nexus": {"id": origin}}


def _accepted(ident, position):
    return {"type": "outcome", "id": ident, "outcome": "accepted",
            "position_id": position}


def _position(position, card, status, pnl, at="2026-09-19T12:00:00+00:00"):
    key = "realized_pnl_usdc" if status == "closed" else "unrealized_pnl_usdc"
    return {"type": "sample", "kind": "position", "at": at,
            "position_id": position, "card_id": card, "status": status,
            key: pnl}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_board_ranks_his_proposals_by_what_they_earned():
    """[operator 2026-09-19] the goal is the strategies that earn the most. So
    every proposal is followed to the money: the stake our orders credited to
    his answer, the newest reading of each position, realised once closed --
    and a proposal the backtest turned away is on the board too, with its
    numbers, because "what has been tested" is half of what they asked for."""
    # Since C2 (2026-09-23) a position counts for an answer only on a card
    # the answer picked, so each names the cards its orders bought.
    c1, c1b, c2, c3 = _card(0xC1), _card(0xC1B), _card(0xC2), _card(0xC3)
    texts = {1: f"Buy {c1} and {c1b}.", 2: f"Buy {c2}.", 3: f"Buy {c3}.",
             4: "..."}
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": f"2026-09-19T0{n}:00:00+00:00", "text": texts[n]}
               for n in range(1, 5)]
    notebook = [
        {"type": "gate", "origin": "NEX-0001", "card": c1, "verdict": "pass",
         "why": "+6.5% at Sharpe 1.30 over 90 days after fees"},
        {"type": "gate", "origin": "NEX-0003", "card": c3,
         "verdict": "reject", "why": "-4.0% over 90 days after fees"}]
    room_rows = [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-0001",
         "title": "Fed cut", "at": "2026-09-19T01:10:00+00:00"},
        {"type": "status", "room": "STR-0001", "status": "running"},
        {"type": "strategy", "id": "STR-0002", "origin": "NEX-0002",
         "title": "SOL memes", "at": "2026-09-19T02:10:00+00:00"},
        {"type": "status", "room": "STR-0002", "status": "running"}]
    paper_rows = [
        _intent("TRD-1", c1, 600.0, "NEX-0001"), _accepted("TRD-1", "p1"),
        _intent("TRD-2", c1b, 600.0, "NEX-0001"), _accepted("TRD-2", "p2"),
        _intent("TRD-3", c2, 1200.0, "NEX-0002"), _accepted("TRD-3", "p3")]
    samples = [
        _position("p1", c1, "open", 10.0, at="2026-09-19T10:00:00+00:00"),
        _position("p1", c1, "open", 40.0, at="2026-09-19T12:00:00+00:00"),
        _position("p2", c1b, "closed", 20.0),
        _position("p3", c2, "open", -30.0)]

    # Handed newest first, so the order that comes out is the board's own:
    # in file order the best earner was also the earliest, and a board that
    # never sorted passed (L01, deep pass of 2026-09-19, 3/3).
    rows = lab.board(list(reversed(answers)), notebook, room_rows,
                     paper_rows, samples)

    assert [r["origin"] for r in rows] == ["NEX-0001", "NEX-0002", "NEX-0003"], rows
    best = rows[0]
    assert best["room"] == "STR-0001" and best["stake_usdc"] == 1200.0
    assert best["pnl_usdc"] == 60.0, "the newest reading, realised once closed"
    assert round(best["pnl_pct"], 6) == 5.0
    assert rows[1]["pnl_pct"] < 0
    assert rows[2]["room"] is None and "-4.0" in rows[2]["gates"][0]["why"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_board_shows_every_room_an_answer_opened(tmp_path, monkeypatch):
    """R05, deep pass of 2026-09-21 (3/3): with one room per card an answer
    opens several, and the board kept only the last -- a refuted room hidden
    behind a running one of the same answer. Every room is named, with its
    own status and verdict; the row's status says they differ."""
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": "2026-09-19T01:00:00+00:00", "text": "..."}]
    room_rows = [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-0001",
         "card": "c1", "title": "A", "at": "2026-09-19T01:10:00+00:00"},
        {"type": "status", "room": "STR-0001", "status": "stopped"},
        {"type": "verdict", "room": "STR-0001", "verdict": "refuted",
         "early": True},
        {"type": "strategy", "id": "STR-0002", "origin": "NEX-0001",
         "card": "c2", "title": "B", "at": "2026-09-19T01:11:00+00:00"},
        {"type": "status", "room": "STR-0002", "status": "running"}]

    (row,) = lab.board(answers, [], room_rows, [], [])

    assert [r["id"] for r in row["rooms"]] == ["STR-0001", "STR-0002"]
    assert [r["verdict"] for r in row["rooms"]] == ["refuted", None]
    assert row["status"] != "running", "a refuted room read as running"
    assert "refuted" in str(row["verdict"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_board_credits_what_he_picked_with_what_it_made():
    """C2 of the 2026-09-23 review (3/3, reworded). NEX-0064 picked one card
    and ruled three out; the launch opened rooms on two of those by mistake,
    bought them and sold them a minute later. The board then credited his
    answer with the stake of all three buys and the P&L of the one position
    the sampler had read -- 19.82 on 1426.83, +1.39% -- where his pick made
    +4.17% on its 475.61. And a P&L realised on OUR close record counted for
    nothing when the sampler never saw the position closed.

    So an answer is credited only with what it picked (`lab.picked_cards`;
    the same reading for a bot); a position's money is our own close record
    when we sold it, the sampler's newest reading otherwise; the return is
    over the stake of the positions priced, and the row says how many were.
    A paper bot he picked counts on what went into it and what it made."""
    fixture = json.loads((REPO / "tests" / "meta" / "fixtures"
                          / "nexus_answers.json").read_text(encoding="utf-8"))
    pick = "9f9433ef-75ec-4637-a743-64d9110545bf"
    out_a = "db54ed55-851d-40ac-a775-a43e43604a28"
    out_b = "0a35dd76-0929-4d64-8f79-18e677e2c758"
    sold, unread = _card(0x5), _card(0x6)
    answers = [
        {"type": "answer", "id": "NEX-0064", "at": "2026-09-21T23:50:00+00:00",
         "text": fixture["answers"]["NEX-0064"]["text"]},
        {"type": "answer", "id": "NEX-0002", "at": "2026-09-19T02:00:00+00:00",
         "text": f"Buy {sold} and {unread}."},
        {"type": "answer", "id": "NEX-0003", "at": "2026-09-19T03:00:00+00:00",
         "text": "**Pick: MACD Hunter.**\n\nIt beats Trend Titan on trades."}]
    room_rows = [
        {"type": "strategy", "id": "STR-0003", "origin": "NEX-0003",
         "title": "MACD Hunter", "kind": "bot", "ref": "sp-macd"},
        {"type": "acceptance", "room": "STR-0003", "window_days": 5.0,
         "legs": [{"kind": "bot", "ref": "inst-macd", "share": 1.0}]},
        {"type": "strategy", "id": "STR-0004", "origin": "NEX-0003",
         "title": "Trend Titan", "kind": "bot", "ref": "sp-titan"},
        {"type": "acceptance", "room": "STR-0004", "window_days": 5.0,
         "legs": [{"kind": "bot", "ref": "inst-titan", "share": 1.0}]}]

    def close(ident, position, realized):
        return [{"type": "intent", "id": ident, "kind": "close",
                 "position_id": position},
                {"type": "outcome", "id": ident, "kind": "close",
                 "outcome": "accepted", "realized_pnl_usdc": realized}]
    paper_rows = [
        _intent("TRD-0013", pick, 475.61, "NEX-0064"), _accepted("TRD-0013", "P-13"),
        _intent("TRD-0014", out_a, 475.61, "NEX-0064"), _accepted("TRD-0014", "P-14"),
        _intent("TRD-0015", out_b, 475.61, "NEX-0064"), _accepted("TRD-0015", "P-15"),
        *close("TRD-0016", "P-14", 0.582433), *close("TRD-0017", "P-15", 0.268275),
        _intent("TRD-0005", sold, 100.0, "NEX-0002"), _accepted("TRD-0005", "P-5"),
        _intent("TRD-0006", unread, 100.0, "NEX-0002"), _accepted("TRD-0006", "P-6"),
        *close("TRD-0007", "P-5", 5.0)]
    samples = [
        _position("P-13", pick, "open", 19.817763558441584),
        {"type": "sample", "kind": "bot", "at": "2026-09-23T07:05:46+00:00",
         "instance_id": "inst-macd", "total_profit_usdc": 7.1},
        {"type": "sample", "kind": "bot", "at": "2026-09-23T07:05:46+00:00",
         "instance_id": "inst-titan", "total_profit_usdc": -50.0}]
    clone_rows = []
    for ident, instance, amount in (("CLN-1", "inst-macd", 240.0),
                                    ("CLN-2", "inst-titan", 100.0)):
        clone_rows += [{"type": "intent", "id": ident, "kind": "fund",
                        "instance_id": instance, "amount": amount},
                       {"type": "outcome", "id": ident, "outcome": "accepted"}]

    rows = {r["origin"]: r for r in lab.board(
        answers, [], room_rows, paper_rows, samples, clone_rows)}

    his = rows["NEX-0064"]
    assert his["stake_usdc"] == pytest.approx(475.61), his
    assert round(his["pnl_pct"], 2) == 4.17, his

    both = rows["NEX-0002"]
    assert both["pnl_usdc"] == pytest.approx(5.0), (
        "a sale on our own record counted for nothing", both)
    assert both["pnl_pct"] == pytest.approx(5.0), (
        "the return is over the stake that was priced", both)
    assert (both["priced"], both["positions"]) == (1, 2), both

    bot = rows["NEX-0003"]
    assert bot["stake_usdc"] == pytest.approx(240.0), bot
    assert bot["pnl_pct"] == pytest.approx(7.1 / 240 * 100), bot


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_brief_carries_his_track_record_into_the_next_question(
        tmp_path, monkeypatch):
    """Nexus remembers nothing between questions; the brief is his memory.
    It has to say what the day may still spend, how his last proposals did --
    including the ones the gate turned away, with the numbers -- and what
    measured well on our side, as a question for him and never a proposal."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    _write(tmp_path, "nexus.jsonl", [
        _question("NEX-0001", real_now - timedelta(hours=3)),
        {"type": "answer", "id": "NEX-0001",
         "at": (real_now - timedelta(hours=2)).isoformat(), "text": "..."}])
    _write(tmp_path, "paper.jsonl", [{"type": "after", "id": "TRD-0001",
                                      "sim_balance_usdc": "98800"}])
    lab.note_gate("NEX-0001", _card(0xC), {
        "verdict": "reject", "why": "-4.0% over 90 days after fees"})
    from qa import backtests as qa_backtests
    qa_backtests.record(
        [{"symbol": "SOL", "weight": 0.5}, {"symbol": "ZEC", "weight": 0.5}],
        30, {"total_return_pct": 91.98, "sharpe_ratio": 9.05,
             "max_drawdown_pct": 12.0, "n_points": 30}, why="search")

    text = scripts_lab.brief()

    # Since V5 (2026-09-23) the day's figure is said without a cap of ours,
    # and the only limit named is the book's.
    assert "1 in the last 24 h" in text and "of 24" not in text, text
    assert "the only limit" in text, text
    assert "NEX-0001" in text and "-4.0%" in text, text
    # The section's CONTENT, not its header: the register was empty, so the
    # header was all there was to find, and a brief that listed our baskets
    # as buy calls under it passed (L06, deep pass of 2026-09-19, 3/3).
    lines = text.splitlines()
    header = next(n for n, line in enumerate(lines)
                  if "never a proposal" in line.lower())
    section = []
    for line in lines[header + 1:]:
        if not line.startswith("  "):
            break
        section.append(line)
    assert any("SOL 50%" in line and "ZEC 50%" in line and "sharpe" in line
               for line in section), section
    assert not any(word in line.lower() for line in section
                   for word in ("buy", "trade this", "go long")), section


# --- the gate: a backtest before a room ------------------------------------

def _reading(period, r, s, d=3.0, lost=None):
    row = {"p": period, "r": r, "s": s, "d": d, "fees": True}
    if lost:
        row["lost"] = lost
    return row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_gate_reads_the_longest_window_their_backtest_priced_whole():
    """"Slibná" in numbers: their own backtest of the card's basket, after
    fees, positive and at a Sharpe of at least half -- over the LONGEST window
    it answered. A good month inside a bad quarter is the quarter's result.

    A reading that lost a leg is a different basket (qa/backtests.py::record)
    and does not count; nothing priced at all is "unbacktestable", which is not
    a rejection -- it is the absence of a test, and it goes to paper small.
    """
    passed = lab.gate([_reading(30, 2.0, 0.9), _reading(90, 6.5, 1.2)])
    assert passed["verdict"] == "pass" and passed["period"] == 90, passed

    quarter = lab.gate([_reading(30, 9.0, 2.5), _reading(90, -3.0, -0.4)])
    assert quarter["verdict"] == "reject" and "-3.0" in quarter["why"], quarter

    flat = lab.gate([_reading(90, 1.0, 0.2)])
    assert flat["verdict"] == "reject" and "0.20" in flat["why"], flat

    lost = lab.gate([_reading(90, 20.0, 3.0, lost=["XYZ"]),
                     _reading(30, -1.0, -0.1)])
    assert lost["verdict"] == "reject" and lost["period"] == 30, (
        "a reading that lost a leg measured some other basket")

    assert lab.gate([])["verdict"] == "unbacktestable"
    assert lab.gate([{"p": 90, "r": None, "s": None}])["verdict"] == "unbacktestable"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_gate_charges_what_a_trade_costs_not_their_stress_test():
    """REPLY-0047, 2026-09-22, verified live: their backtest's fee toggle is
    2% + 0.5% PER SIDE, 5% a round trip, "a deliberately conservative stress
    estimate, not the live fee schedule" -- the live event-card taker fee is
    0.2% a fill. The gate asked for "positive after fees" through that
    toggle, so a card up 3% gross over a quarter was refused for a cost it
    would never pay. The gate now reads the GROSS return and charges the live
    round trip: two fills of 0.2% and 0.5% of slippage each side."""
    gross = {"p": 90, "r": 3.0, "s": 1.1, "d": 2.0}
    said = lab.gate([gross])
    assert said["verdict"] == "pass", said
    cost = lab.GATE["round_trip_cost_pct"]
    assert cost == 1.4
    assert round(said["return_pct"], 4) == round(((1.03) * (1 - cost / 100) - 1) * 100, 4)
    # Under the live cost, still a loss.
    assert lab.gate([dict(gross, r=1.0)])["verdict"] == "reject"
    # A reading their toggle already charged is not charged twice.
    stressed = lab.gate([_reading(90, 2.0, 1.1)])
    assert stressed["verdict"] == "pass" and stressed["return_pct"] == 2.0, stressed


def _launchpad(scripts_lab, tmp_path, monkeypatch, answers, live, readings,
               refuse=()):
    """night_promote with their card door and their backtest stubbed, the
    sender stubbed, and everything else real. A card in `refuse` is refused
    by the sender the way paper.py refuses: SystemExit."""
    _write(tmp_path, "nexus.jsonl", answers)
    _write(tmp_path, "paper.jsonl", [{"type": "after", "id": "TRD-0001",
                                      "sim_balance_usdc": "100000"}])
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    monkeypatch.setattr(scripts_lab, "card_baskets", lambda: [])
    # Their bot and fund catalogues (2026-09-22), empty unless a test says so.
    monkeypatch.setattr(scripts_lab, "_bot_catalogue", lambda: [])
    monkeypatch.setattr(scripts_lab, "_fund_catalogue", lambda: [])

    def _live(card):
        said = live[card]
        if isinstance(said, Exception):
            raise said
        return said
    monkeypatch.setattr(scripts_lab, "_card_live", _live)

    calls = []

    def _backtest(legs, period_days=30, *, why="", include_fees=False, **_):
        calls.append((tuple(leg["symbol"] for leg in legs), period_days,
                      include_fees))
        key = tuple(sorted(leg["symbol"] for leg in legs))
        r, s = readings[key]
        return {"cached": False, **_reading(period_days, r, s)}
    monkeypatch.setattr(scripts_lab, "backtest", _backtest)

    sent = []
    real = scripts_lab._sibling
    paper = real("paper")

    def _buy(card, usdc, *a, **k):
        if card in refuse:
            raise SystemExit("the money in our paper bots could not be read")
        sent.append((card, usdc))
        return {"outcome": "accepted", "http_status": 200,
                "position_id": f"pos-{card[:8]}"}
    paper.buy = _buy
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: paper if n == "paper" else real(n))
    return sent, calls


def _basket(*symbols):
    return {"legs": [{"symbol": s, "weight": 1.0 / len(symbols)}
                     for s in symbols], "tradeable": True, "title": "t"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_cards_question_names_what_we_hold_and_what_the_gate_refused(
        tmp_path, monkeypatch):
    """The question that feeds one-room-per-card: up to five cards, each with
    its thesis -- fewer if fewer are worth it, because the operator said a
    room is for a promising theory, not a quota. It carries the WHOLE ids of
    the cards we hold (NEX-0058 could not find two cards we named by their
    first eight characters) and why the gate refused his last ones."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    held, refused = _card(0x21), _card(0x22)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": "Buy " + held + " and " + refused + ". " + "why. " * 60}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={held: _basket("BTC", "ETH"), refused: _basket("SOL", "DOGE")},
               readings={("BTC", "ETH"): (6.5, 1.3), ("DOGE", "SOL"): (-3.0, -0.4)})
    scripts_lab.night_promote()

    text = scripts_lab.cards_question()

    assert held in text, "the held card is named whole"
    assert refused[:8] in text and "backtest" in text.lower()
    assert "up to five" in text.lower() and "fewer" in text.lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_past_its_stop_is_stopped_early_and_its_position_closed(
        tmp_path, monkeypatch):
    """2026-09-21: a room that fails is dropped, not carried to the end of its
    window. verdicts() reads a running room's index once an hour; a crossing
    of its stop records the verdict (early), stops the room and closes the
    paper position it holds, so its money comes back under the ceiling.
    A room still inside its stop is left running, and is not read again
    inside the hour."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    card = _card(0xE)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={card: _basket("BTC", "ETH")},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    (room,) = qa_rooms.strategies(qa_rooms.load())
    opened = qa_rooms.acceptance_of(qa_rooms.load(), room["id"])["at"]
    _write(tmp_path, "paper.jsonl", [
        {"id": "TRD-0001", "type": "intent", "at": opened, "card_id": card,
         "usdc": 480.0, "paper": True, "nexus": {"id": "NEX-0001"}},
        {"id": "TRD-0001", "type": "outcome", "at": opened, "outcome": "accepted",
         "http_status": 200, "position_id": "P-1"}])
    closed = []
    paper = scripts_lab._sibling("paper")
    paper.close = lambda position, confirm: closed.append(position) or {}

    start = datetime.fromisoformat(opened)
    points = lambda values: [{"t": (start + timedelta(hours=h)).isoformat(),
                              "index": v} for h, v in enumerate(values)]
    path = {"now": points([100, 99, 97])}
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: path["now"] if c == card else [])

    later = start + timedelta(hours=3)
    assert scripts_lab.verdicts(now=later) == []
    rows = qa_rooms.load()
    assert qa_rooms.status_of(rows, room["id"]) == "running"

    path["now"] = points([100, 99, 97, 88])
    assert scripts_lab.verdicts(now=later + timedelta(minutes=30)) == [], (
        "read again inside the hour")
    said = scripts_lab.verdicts(now=later + timedelta(hours=2))
    assert [s["verdict"] for s in said] == ["refuted"] and said[0]["early"], said
    rows = qa_rooms.load()
    assert qa_rooms.status_of(rows, room["id"]) == "stopped"
    assert closed == ["P-1"], "the position the room held was not closed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_whose_card_closed_inside_the_window_gets_a_verdict(
        tmp_path, monkeypatch):
    """Every crypto card the laboratory bought on the night of 2026-09-21
    closes on 2026-09-24, inside its five-day window. verdicts() has to hand
    the formula each card's close, or all of them come back inconclusive."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    card = _card(0x24)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={card: _basket("BTC", "ETH")},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    (room,) = qa_rooms.strategies(qa_rooms.load())
    acceptance = qa_rooms.acceptance_of(qa_rooms.load(), room["id"])
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    close = start + timedelta(days=days / 2)
    hours = int((close - start).total_seconds() // 3600)
    points = [{"t": (start + timedelta(hours=h)).isoformat(),
               "index": 100 + h * 0.05} for h in range(hours + 1)]
    # A flat benchmark: since C1 (2026-09-23) a room accepted against one is
    # not survived on its return alone.
    flat = [{"t": p["t"], "index": 100.0} for p in points]
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: points if c == card else flat)
    monkeypatch.setattr(scripts_lab, "_closes_at",
                        lambda client, c: close.isoformat() if c == card else None)

    said = scripts_lab.verdicts(now=start + timedelta(days=days, hours=1))

    assert [s["verdict"] for s in said] == ["survived"], said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_benchmark_read_does_not_turn_refuted_into_survived(
        tmp_path, monkeypatch):
    """C1 of the 2026-09-23 review (3/3). `_history` answered `[]` for any
    status but 200, so a benchmark read that failed looked like a benchmark
    with no marks, the verdict judged the room on its return alone, and a
    room that lost to BTC was written down as survived -- once, for good.

    A failed read is not an empty one (rule 8). The real reader is driven
    here, through a client that answers 502: the room stays running with no
    verdict, the tick says it waits, and the next call -- the read answering
    this time -- refutes it against the benchmark. A failed read of the
    room's own card waits the same way instead of coming back inconclusive.
    And a benchmark that answered with nothing over the window does not let
    a positive return survive either: that is inconclusive."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    card = _card(0xC1)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={card: _basket("BTC", "ETH")},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    (room,) = qa_rooms.strategies(qa_rooms.load())
    acceptance = qa_rooms.acceptance_of(qa_rooms.load(), room["id"])
    bench = acceptance["benchmark_card"]
    assert bench, "the room was accepted without a benchmark"
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    hours = int(days * 24)

    def rising(pct):
        return [{"t": (start + timedelta(hours=h)).isoformat(),
                 "index": 100 * (1 + pct / 100 * h / hours)}
                for h in range(hours + 1)]
    failing = {bench}

    class Response:
        def __init__(self, c):
            self.status_code = 502 if c in failing else 200
            self.body = {"points": rising(3.0 if c == card else 10.0)}

        def json(self):
            return self.body

    class Client:
        def get(self, path, **kwargs):
            return Response(path.split("/event-cards/")[1].split("/")[0])

    real = scripts_lab._history
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: real(Client(), c))
    monkeypatch.setattr(scripts_lab, "_closes_at", lambda client, c: None)
    after = start + timedelta(days=days, hours=1)

    said = scripts_lab.verdicts(now=after)
    assert [s["verdict"] for s in said] == ["waiting"], said
    assert "502" in said[0]["why"], said
    rows = qa_rooms.load()
    assert qa_rooms.verdict_of(rows, room["id"]) is None, "written without its benchmark"
    assert qa_rooms.status_of(rows, room["id"]) == "running"

    failing.clear()
    failing.add(card)
    said = scripts_lab.verdicts(now=after + timedelta(minutes=20))
    assert [s["verdict"] for s in said] == ["waiting"], (
        "a failed read of the room's own card was judged, not waited on", said)

    failing.clear()
    said = scripts_lab.verdicts(now=after + timedelta(minutes=40))
    assert [s["verdict"] for s in said] == ["refuted"], said
    assert "benchmark" in said[0]["why"], said

    # A benchmark that ANSWERED with nothing over the window: no survival.
    from qa import lab
    points = {card: rising(3.0), bench: []}
    judged = lab.verdict(acceptance, points, after)
    assert judged["verdict"] == "inconclusive", judged
    points[bench] = rising(1.0)
    assert lab.verdict(acceptance, points, after)["verdict"] == "survived"

    # The tick does not count a waiting verdict as one, and says why it waits.
    doors, _ = _doors(verdicts=lambda: [
        {"room": "STR-0001", "verdict": "waiting",
         "why": "index-history of a4a5b71e answered HTTP 502"},
        {"room": "STR-0002", "verdict": "refuted", "why": "it returned -1%"}])
    printed = []
    said = scripts_lab.tick(now=after, actions=doors, out=printed.append)
    assert said["verdicts"] == 1, said
    assert any("STR-0001" in line and "502" in line for line in printed), printed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_that_closes_normally_sells_the_rooms_card_position(
        tmp_path, monkeypatch):
    """C3 of the 2026-09-23 review (3/3), already fired once: only an EARLY
    verdict closed a room's card positions. STR-0003 was judged at the end
    of its window on 2026-09-18 and TRD-0006 stayed open under it until the
    card resolved on its own the next day, counted against the ceiling the
    whole time. The next room to close normally is STR-0006, 2026-09-26.

    Any verdict now sells what the room holds. A sale that fails is owed and
    tried again on the next call, as the early path's is. And a position
    their own record already shows closed -- TRD-0006's, resolved without us
    -- is not sold a second time: that is a close retried every tick
    forever."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    cards = [_card(0xC3), _card(0xC4)]
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)} for n, card in enumerate(cards, 1)]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={c: _basket("BTC", "ETH") for c in cards},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    rows = qa_rooms.load()
    first, second = qa_rooms.strategies(rows)
    acceptance = qa_rooms.acceptance_of(rows, first["id"])
    opened = acceptance["at"]
    start = datetime.fromisoformat(opened)
    days = float(acceptance["window_days"])
    buys = []
    for n, card in enumerate(cards, 1):
        buys += [
            {"id": f"TRD-000{n}", "type": "intent", "at": opened, "card_id": card,
             "usdc": 480.0, "paper": True, "nexus": {"id": f"NEX-000{n}"}},
            {"id": f"TRD-000{n}", "type": "outcome", "at": opened,
             "outcome": "accepted", "http_status": 200, "position_id": f"P-{n}"}]
    _write(tmp_path, "paper.jsonl", buys)
    # P-2's card resolved on their side: the sampler saw it closed.
    _write(tmp_path, "samples.jsonl", [
        {"type": "sample", "kind": "position", "at": opened,
         "position_id": "P-2", "status": "open"},
        {"type": "sample", "kind": "position",
         "at": (start + timedelta(days=1)).isoformat(),
         "position_id": "P-2", "status": "closed", "realized_pnl_usdc": 85.76}])
    attempts = []

    def close(position, confirm):
        """Fails once, then writes what paper.close writes on a sale."""
        attempts.append(position)
        if len(attempts) == 1:
            raise SystemExit("their /sell answered 500")
        sale = f"TRD-01{len(attempts):02d}"
        with open(tmp_path / "paper.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": sale, "type": "intent", "kind": "close",
                                 "position_id": position, "paper": True}) + "\n")
            fh.write(json.dumps({"id": sale, "type": "outcome",
                                 "outcome": "accepted", "http_status": 200}) + "\n")
        return {}
    scripts_lab._sibling("paper").close = close

    hours = int(days * 24)
    points = [{"t": (start + timedelta(hours=h)).isoformat(),
               "index": 100 + h * 0.05} for h in range(hours + 1)]
    flat = [{"t": p["t"], "index": 100.0} for p in points]
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: points if c in cards else flat)
    monkeypatch.setattr(scripts_lab, "_closes_at", lambda client, c: None)
    after = start + timedelta(days=days, hours=1)

    said = scripts_lab.verdicts(now=after)
    assert sorted(s["verdict"] for s in said) == ["survived", "survived"], said
    assert not any(s.get("early") for s in said), said
    assert attempts == ["P-1"], (
        "a normal verdict left the room's position open" if not attempts
        else f"sold {attempts}: P-2 was already closed on their side")
    assert any(s.get("close_failed") for s in said), said

    scripts_lab.verdicts(now=after + timedelta(minutes=20))
    assert attempts == ["P-1", "P-1"], "the failed sale was not tried again"

    scripts_lab.verdicts(now=after + timedelta(minutes=40))
    assert attempts == ["P-1", "P-1"], "a sold position was sold again"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_room_is_judged_on_our_position_net_of_the_round_trip(
        tmp_path, monkeypatch):
    """The plan's V2 (review of 2026-09-23): the verdict read their index
    from its first point inside the window, not what OUR position did, and
    charged nothing for getting in and out. A card that had already moved
    before our order filled was credited with the move we never had, and a
    position we sold on day two was judged as if held to the end.

    Our book: 100 at our fill (`entry_index`, from the buy's own response),
    their index rebased on it while we hold (a paper position is worth units
    x index), and the realised value from our sale on, frozen to the end.
    The live round trip (1.4%) is charged once on the leg's return. Their
    index-only reading rides beside as the cross-check."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    held, sold = _card(0xB0), _card(0xB1)
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)} for n, card in enumerate((held, sold), 1)]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={c: _basket("BTC", "ETH") for c in (held, sold)},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    rows = qa_rooms.load()
    first, second = qa_rooms.strategies(rows)
    acceptance = qa_rooms.acceptance_of(rows, first["id"])
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    end = start + timedelta(days=days)
    filled = start + timedelta(minutes=2)

    def buy(ident, card, origin, position, entry):
        return [{"id": ident, "type": "intent", "card_id": card, "usdc": 100.0,
                 "paper": True, "nexus": {"id": origin},
                 "at": filled.isoformat()},
                {"id": ident, "type": "outcome", "outcome": "accepted",
                 "position_id": position, "at": filled.isoformat(),
                 "response": json.dumps({"position_id": position,
                                         "entry_index": entry,
                                         "notional_usdc": 100.0})}]
    sale_at = start + timedelta(days=2)
    _write(tmp_path, "paper.jsonl", [
        *buy("TRD-0001", held, "NEX-0001", "P-1", 200.0),
        *buy("TRD-0002", sold, "NEX-0002", "P-2", 50.0),
        {"id": "TRD-0003", "type": "intent", "kind": "close",
         "position_id": "P-2", "at": sale_at.isoformat()},
        {"id": "TRD-0003", "type": "outcome", "kind": "close",
         "outcome": "accepted", "realized_pnl_usdc": 2.0,
         "proceeds_usdc": 102.0, "at": sale_at.isoformat()}])
    scripts_lab._sibling("paper").close = lambda position, confirm: {}

    hours = int(days * 24)
    # The held card had moved 190 -> 200 before our order filled, and goes
    # on to 210. The sold card goes on to 60 after we sold it at 51.
    index = {held: [{"t": start.isoformat(), "index": 190.0}]
             + [{"t": (filled + timedelta(hours=h)).isoformat(),
                 "index": 200.0 + 10.0 * h / hours} for h in range(hours)],
             sold: [{"t": (filled + timedelta(hours=h)).isoformat(),
                     "index": 50.0 + 10.0 * h / hours} for h in range(hours)]}
    flat = [{"t": (start + timedelta(hours=h)).isoformat(), "index": 100.0}
            for h in range(hours + 1)]
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: index.get(c, flat))
    monkeypatch.setattr(scripts_lab, "_closes_at", lambda client, c: None)

    said = {s["room"]: s for s in scripts_lab.verdicts(now=end + timedelta(hours=1))}

    net = lambda gross: ((1 + gross / 100) * (1 - 0.014) - 1) * 100  # noqa: E731
    mine = said[first["id"]]
    last = 200.0 + 10.0 * (hours - 1) / hours
    assert mine["return_pct"] == pytest.approx(net((last / 200.0 - 1) * 100)), mine
    assert mine["index_return_pct"] == pytest.approx(net((last / 190.0 - 1) * 100)), (
        "the cross-check is their index alone, net the same way")
    assert said[second["id"]]["return_pct"] == pytest.approx(net(2.0)), (
        "a position we sold is worth what we sold it for, to the end")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_his_exits_are_on_the_leg_the_criterion_judges(tmp_path, monkeypatch):
    """Every room the launch opened from 2026-09-21 on carries tp None and
    sl None, while nearly every answer named both ("TP +8%, stop -4%"). The
    criterion judged his idea without his exits. They are read per card and
    written onto the leg before the criterion is -- forward only."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    card = _card(0xE1)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": (f"**PICK 1 — `{card}`** — side: UP (bull). "
                         f"TP +8%, stop −4%.\n" + "reasoning. " * 40)}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={card: _basket("BTC", "ETH")},
               readings={("BTC", "ETH"): (6.5, 1.3)})

    scripts_lab.night_promote()

    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    (leg,) = qa_rooms.acceptance_of(rows, room["id"])["legs"]
    assert (leg["tp"], leg["sl"]) == (8.0, -4.0), leg


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_benchmark_card_is_not_an_experiment(tmp_path, monkeypatch):
    """STR-0008: NEX-0059 picked a4a5b71e, the BTC card every room is judged
    against, and the launch opened a room on it -- one that could only ever
    tie its own benchmark. It is refused at the launch now, and said."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    bench = scripts_lab.BTC_PROXY
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(bench)}]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={bench: _basket("BTC", "ETH")},
               readings={("BTC", "ETH"): (6.5, 1.3)})

    said = scripts_lab.night_promote()

    assert said["rooms"] == 0, said
    assert any("benchmark" in line for line in said["held"]), said["held"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stopped_room_is_archived_or_judged_up_to_its_stop(
        tmp_path, monkeypatch):
    """Review of 2026-09-23 (the plan's V2): `verdicts()` never read a room's
    status. A room stopped because its order never landed (STR-0027,
    STR-0042) was still judged "on the index" at the end of its window -- a
    verdict on an experiment nobody ran -- and one opened by mistake on a
    card he had ruled out (STR-0011, STR-0012) was his to lose. And a room
    stopped by hand while it held a position waited for a window that no
    longer meant anything.

    Status first. Stopped, never having held anything, or not his pick: the
    room is archived -- derived, not written, and never given a verdict.
    Stopped holding his pick: judged now, over the window up to the stop."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    pick, ruled, never = _card(0xA1), _card(0xA2), _card(0xA3)
    text = (f"**Pick: `{pick}`** and a second, `{never}`.\n\n"
            f"**Why the others are out:**\n- `{ruled}` is ruled out.\n")
    _write(tmp_path, "nexus.jsonl", _answer(text))
    start = datetime.now(timezone.utc) - timedelta(days=2)
    rooms_rows, paper_rows = [], []
    for n, card in enumerate((pick, ruled, never), 1):
        room = f"STR-000{n}"
        rooms_rows += [
            {"type": "strategy", "id": room, "origin": "NEX-0001",
             "title": card[:8], "card": card, "at": start.isoformat()},
            {"type": "acceptance", "room": room, "window_days": 5.0,
             "stop_pct": 10.0, "benchmark_card": scripts_lab.BTC_PROXY,
             "legs": [{"card": card, "side": "bull", "share": 1.0}],
             "adopted": True, "why": "test", "at": start.isoformat()}]
        if card != never:
            paper_rows += [
                {"id": f"TRD-000{n}", "type": "intent", "card_id": card,
                 "usdc": 100.0, "paper": True, "nexus": {"id": "NEX-0001"},
                 "at": start.isoformat()},
                {"id": f"TRD-000{n}", "type": "outcome", "outcome": "accepted",
                 "position_id": f"P-{n}", "at": start.isoformat()}]
    stopped_at = start + timedelta(days=1)
    for n in (1, 2, 3):
        rooms_rows.append({"type": "status", "room": f"STR-000{n}",
                           "status": "stopped", "why": "by hand",
                           "at": stopped_at.isoformat()})
    _write(tmp_path, "rooms.jsonl", rooms_rows)
    _write(tmp_path, "paper.jsonl", paper_rows)
    scripts_lab._sibling("paper").close = lambda position, confirm: {}

    hours = 48
    rising = [{"t": (start + timedelta(hours=h)).isoformat(),
               "index": 100 + h * 0.1} for h in range(hours + 1)]
    flat = [{"t": p["t"], "index": 100.0} for p in rising]
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: rising if c != scripts_lab.BTC_PROXY
                        else flat)
    monkeypatch.setattr(scripts_lab, "_closes_at", lambda client, c: None)

    said = scripts_lab.verdicts(now=start + timedelta(days=2))

    assert [s["room"] for s in said if s.get("verdict")] == ["STR-0001"], said
    (judged,) = [s for s in said if s["room"] == "STR-0001"]
    assert judged["window"]["to"] == stopped_at.isoformat(), judged
    assert judged["return_pct"] == pytest.approx((1.024 * 0.986 - 1) * 100), (
        "judged over the window up to the stop, 24 hours at +0.1 an hour, "
        "after the round trip")
    rows = qa_rooms.load()
    assert qa_rooms.verdict_of(rows, "STR-0002") is None
    assert qa_rooms.verdict_of(rows, "STR-0003") is None
    assert lab.archived_rooms(rows, qa_rooms.nexus_answers(), paper_rows) == {
        "STR-0002", "STR-0003"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_early_close_that_failed_is_tried_again_and_the_benchmark_read_once(
        tmp_path, monkeypatch):
    """R06 and R08, deep pass of 2026-09-21 (3/3 each). The verdict is written
    and the room stopped BEFORE the close, so a close that failed was never
    tried again and the stake stayed out under the ceiling. And every room
    fetched the same benchmark history for itself. A stopped room with an
    early verdict and a position still ours is closed on the next call; a
    card's history is read once per call."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    cards = [_card(0x31), _card(0x32)]
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)} for n, card in enumerate(cards, 1)]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={c: _basket("BTC", "ETH") for c in cards},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    rows = qa_rooms.load()
    opened = qa_rooms.acceptance_of(rows, qa_rooms.strategies(rows)[0]["id"])["at"]
    _write(tmp_path, "paper.jsonl", [
        {"id": "TRD-0001", "type": "intent", "at": opened, "card_id": cards[0],
         "usdc": 480.0, "paper": True, "nexus": {"id": "NEX-0001"}},
        {"id": "TRD-0001", "type": "outcome", "at": opened, "outcome": "accepted",
         "http_status": 200, "position_id": "P-1"}])
    attempts = []

    def close(position, confirm):
        """What paper.close does (RL02, deep pass of 2026-09-24): a /sell
        that answers non-2xx is written as outcome `unknown` and RETURNS; it
        raises only when the POST itself fails. Refused twice, then sold."""
        attempts.append(position)
        sale = f"TRD-01{len(attempts):02d}"
        status = 500 if len(attempts) <= 2 else 200
        with open(tmp_path / "paper.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": sale, "type": "intent", "kind": "close",
                                 "position_id": position, "paper": True}) + "\n")
            fh.write(json.dumps({"id": sale, "type": "outcome", "kind": "close",
                                 "outcome": "accepted" if status == 200 else "unknown",
                                 "http_status": status}) + "\n")
        return {"id": sale}
    paper = scripts_lab._sibling("paper")
    paper.close = close

    start = datetime.fromisoformat(opened)
    fetched = []

    def history(client, card):
        fetched.append(card)
        # The first room's card falls through its stop; the second's is flat,
        # so that room stays open and is looked at again an hour later.
        values = [100, 99, 85] if card == cards[0] else [100, 100, 100]
        return [{"t": (start + timedelta(hours=h)).isoformat(), "index": v}
                for h, v in enumerate(values)]
    monkeypatch.setattr(scripts_lab, "_history", history)

    said = scripts_lab.verdicts(now=start + timedelta(hours=3))
    assert len(said) == 1 and said[0]["early"], said
    assert len(fetched) == len(set(fetched)), f"a card was read twice: {fetched}"
    assert attempts == ["P-1"], attempts
    assert any("500" in line for line in said[0].get("close_failed") or []), (
        "a /sell their side refused was taken for a sale", said)

    # RL01: the next call owes the close AND looks at the open room again. The
    # retry that failed a second time is in what it returns -- it was dropped
    # whenever anything else came due -- and it is no verdict.
    again = scripts_lab.verdicts(now=start + timedelta(hours=4, minutes=1))
    assert attempts == ["P-1", "P-1"], "the failed close was not tried again"
    retry = [row for row in again if row.get("retry")]
    assert retry and retry[0].get("close_failed"), again
    tally = scripts_lab._tally_verdicts(again)
    assert tally["verdicts"] == 0, tally
    assert tally["close_failed"] and "500" in tally["close_failed"][0], tally
    real = scripts_lab.verdicts
    monkeypatch.setattr(scripts_lab, "verdicts", lambda now=None: again)
    assert scripts_lab.main(["verdicts"]) == 0, "a retry row crashed `lab.py verdicts`"

    real(now=start + timedelta(hours=4, minutes=10))
    assert attempts == ["P-1", "P-1", "P-1"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_opens_only_from_a_card_their_backtest_rates(
        tmp_path, monkeypatch):
    """Three answers, three fates, and each written down once.

    A: exists, backtests well after fees -> a room with a plan and a
       criterion a verdict can reach, and one paper order.
    B: exists, backtests badly -> no room, no order, the numbers on the record
       so the next question can tell Nexus how his idea measured.
    C: their API does not know it -> #91, not bought.

    The second call is the loop's next tick: nothing is backtested again and
    nothing is bought twice.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    a, b, c = _card(0xA), _card(0xB), _card(0xC)
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)} for n, card in enumerate((a, b, c), 1)]
    sent, calls = _launchpad(
        scripts_lab, tmp_path, monkeypatch, answers,
        live={a: _basket("BTC", "ETH"), b: _basket("SOL", "DOGE"), c: None},
        readings={("BTC", "ETH"): (6.5, 1.3), ("DOGE", "SOL"): (-4.0, -0.6)})

    did = scripts_lab.night_promote()

    assert [card for card, _ in sent] == [a], sent
    # Gross since 2026-09-22 (REPLY-0047): their fee toggle is a 5% stress
    # estimate, and the gate charges the live round trip itself
    # (test_the_gate_charges_what_a_trade_costs_not_their_stress_test).
    assert not any(fees for _, _, fees in calls), (
        "the gate asked their stress-test toggle, which charges 5% a trade")
    assert did["rooms"] == 1 and did["orders"] == 1, did
    held = " | ".join(did["held"])
    assert "NEX-0002" in held and "-4.0" in held, held
    assert "NEX-0003" in held and "#91" in held, held

    import qa.rooms as qa_rooms
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    assert room["origin"] == "NEX-0001"
    criterion = qa_rooms.acceptance_of(rows, room["id"])
    assert [leg["card"] for leg in criterion["legs"]] == [a], (
        "a criterion with no legs is one no verdict can ever score")
    assert criterion["benchmark_card"], "their guide asks whether it beats BTC"

    # And a verdict can actually be reached from it: a card that rose 5% while
    # the benchmark stood still survives. The night's stop was -10.0 until
    # 2026-09-19 -- a drawdown is positive, so every room was refuted by it.
    start = datetime.fromisoformat(criterion["at"])
    hours = int(criterion["window_days"] * 24) + 1
    rising = [{"t": (start + timedelta(hours=h)).isoformat(),
               "index": 100.0 + 5.0 * h / hours} for h in range(hours + 1)]
    flat = [{"t": p["t"], "index": 100.0} for p in rising]
    said = lab.verdict(criterion, {a: rising, criterion["benchmark_card"]: flat},
                       start + timedelta(hours=hours + 1))
    assert said["verdict"] == "survived", said

    gates = [r for r in lab.load() if r.get("type") == "gate"]
    assert {(g["origin"], g["verdict"]) for g in gates} == {
        ("NEX-0001", "pass"), ("NEX-0002", "reject"),
        ("NEX-0003", "unknown_card")}, gates

    before = len(calls)
    again = scripts_lab.night_promote()
    assert len(calls) == before, "the next tick backtested a decided card again"
    assert len(sent) == 1 and again["orders"] == 0
    assert len([r for r in lab.load() if r.get("type") == "gate"]) == len(gates)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_that_could_not_be_read_or_traded_waits_for_the_next_tick(
        tmp_path, monkeypatch):
    """Rule 8 on the launch path: a failed read of the card is not "the card
    does not exist", and a market that is shut is not a bad idea. Neither
    consumes the answer; the next tick tries again."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    a, b = _card(0xA), _card(0xB)
    shut = {**_basket("BTC", "ETH"), "tradeable": False}
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)} for n, card in enumerate((a, b), 1)]
    live = {a: RuntimeError("HTTP 502"), b: shut}
    sent, calls = _launchpad(
        scripts_lab, tmp_path, monkeypatch, answers, live=live,
        readings={("BTC", "ETH"): (6.5, 1.3)})

    did = scripts_lab.night_promote()

    assert sent == [] and did["rooms"] == 0
    held = " | ".join(did["held"])
    assert "NEX-0001" in held and "could not be read" in held, held
    assert "NEX-0002" in held and "not tradeable" in held, held
    assert not [r for r in lab.load() if r.get("type") == "gate"], (
        "a card nobody could read was decided anyway")

    live[a] = _basket("BTC", "ETH")
    live[b] = _basket("BTC", "ETH")
    scripts_lab.night_promote()
    assert sorted(card for card, _ in sent) == sorted([a, b]), sent


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_their_backtest_cannot_price_goes_to_paper_at_half(
        tmp_path, monkeypatch):
    """A one-coin card is outside their backtest tool (two legs at least), and
    so is a bot. Refusing those would refuse Nexus on a technicality of our
    test bench, so they go to paper -- at half the stake, and the room says it
    was never backtested."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    a = _card(0xA)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(a)}]
    sent, calls = _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
                             live={a: _basket("BTC")}, readings={})

    did = scripts_lab.night_promote()

    assert calls == [], "a one-leg basket was sent to a tool that takes two"
    assert did["rooms"] == 1 and len(sent) == 1, did
    # EXACTLY half, not "at most half": an upper bound was satisfied by a
    # quarter stake or by one cent (L05, deep pass of 2026-09-19, 3/3).
    #
    # And half OF THE WHOLE, which is the half L05's fix missed: comparing
    # the order against `_leg_stakes(..., half=True)` pins the call site to
    # the function and leaves the function free to mean anything. Changing
    # `each /= 2` to `each /= 4` kept this green and kept the only other
    # reference green too, that one being an upper bound. So the definition
    # is pinned here, against the full stake, and the call site against the
    # definition. Found by three readers on 2026-09-20.
    whole = scripts_lab._leg_stakes(100000.0, 0.0, 1)[0]
    half = scripts_lab._leg_stakes(100000.0, 0.0, 1, half=True)[0]
    assert abs(half - whole / 2) <= 0.01, (
        f"half is {half} against a whole stake of {whole}: 'half' has to mean "
        f"half, or the word in the docstring is the only thing that says so")
    assert sent[0][1] == half and half > 0, (sent, half)
    import qa.rooms as qa_rooms
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    criterion = qa_rooms.acceptance_of(rows, room["id"])
    # The clause that says so, not the word "backtest" -- that one is in every
    # room's why ("Backtest: ..."), so removing the clause stayed green.
    assert "not backtested" in criterion["why"].lower(), criterion["why"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refused_paper_order_does_not_stop_the_launch_or_strand_the_room(
        tmp_path, monkeypatch):
    """R01, deep pass of 2026-09-19 (3/3). paper.py refuses with SystemExit
    -- the money in the bots unreadable, their book not answering -- AFTER the
    room was opened with its criterion. The exception escaped night_promote:
    every later answer in the call was skipped, and the room sat with no
    position and no word on it. The refusal is held, the room says it holds
    nothing, and the next answer is launched."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    a, b = _card(0xA), _card(0xB)
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(card)} for n, card in enumerate((a, b), 1)]
    sent, _ = _launchpad(
        scripts_lab, tmp_path, monkeypatch, answers,
        live={a: _basket("BTC", "ETH"), b: _basket("SOL", "DOGE")},
        readings={("BTC", "ETH"): (6.5, 1.3), ("DOGE", "SOL"): (5.0, 1.1)},
        refuse={a})

    did = scripts_lab.night_promote()

    assert [card for card, _ in sent] == [b], (
        "the refusal on the first answer stopped the second one")
    assert any("NEX-0001" in h and "refused" in h for h in did["held"]), did
    import qa.rooms as qa_rooms
    rows = qa_rooms.load()
    first = next(r for r in qa_rooms.strategies(rows)
                 if r["origin"] == "NEX-0001")
    assert qa_rooms.status_of(rows, first["id"]) == "stopped", (
        "a room with no position reads as an experiment in flight")
    # RL07 (deep pass of 2026-09-24): its reason promised "the criterion
    # still judges his idea on the index", and since V2 a stopped room that
    # held nothing is archived and never judged. The reason says so.
    why = [r.get("why") for r in rows if r.get("type") == "status"
           and r.get("room") == first["id"]][-1]
    assert "still judges" not in why and "not judged" in why, why
    assert first["id"] in lab.archived_rooms(rows, [], [], [])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_naming_many_cards_opens_a_room_for_each_under_the_ceiling(
        tmp_path, monkeypatch):
    """2026-09-21: one room per card. An answer naming nine cards used to open
    ONE room of MAX_LEGS legs (R02 kept it from being stranded); now every card
    that passes the gate is its own strategy -- its own plan of one leg, its
    own criterion, its own order -- until the book's 60% ceiling, which says
    what it left for later. (Until V5, 2026-09-23, a day cap of 25 rooms
    stopped it first; the fixture's book is sized so the ceiling binds.)"""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    cap = 12
    cards = [_card(0x100 + n) for n in range(cap + 2)]
    text = "Buy " + ", ".join(cards) + " bull. " + "why. " * 60
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(), "text": text}]
    sent, _ = _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
                         live={c: _basket("BTC", "ETH") for c in cards},
                         readings={("BTC", "ETH"): (6.5, 1.3)})
    # A book of 217 391.30 with 117 391.30 already out: 60% of it leaves
    # 13 043.48, and a room takes 0.48% of the book (1 043.47) -- room for
    # twelve and a half, so twelve. Every accepted order moves money from
    # free to out, as the real book does.
    monkeypatch.setattr(scripts_lab, "_free_cash",
                        lambda: 100000.0 - sum(u for _, u in sent))
    monkeypatch.setattr(scripts_lab, "_deployed",
                        lambda: 117391.30 + sum(u for _, u in sent))

    did = scripts_lab.night_promote()

    rows = qa_rooms.load()
    opened = qa_rooms.strategies(rows)
    assert len(opened) == cap and did["rooms"] == cap, did
    assert [r["card"] for r in opened] == cards[:cap]
    for room in opened:
        criterion = qa_rooms.acceptance_of(rows, room["id"])
        assert criterion and [leg["card"] for leg in criterion["legs"]] == [room["card"]]
    assert [card for card, _ in sent] == cards[:cap]
    assert any("60%" in h for h in did["held"]), did["held"]
    # V6: the answer that opened them is the one the manager is woken for.
    assert did["answered"] == ["NEX-0001"], did


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_already_held_is_not_launched_again_by_a_later_answer(
        tmp_path, monkeypatch):
    """R09 (3/3): `bought` lasted one call, so the next tick bought a card a
    running room already held -- two experiments that are one, and double the
    exposure to one card. Nexus repeats his favourites across answers."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    a = _card(0xA)
    answers = [{"type": "answer", "id": f"NEX-000{n}",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(a)} for n in (1, 2)]
    sent, _ = _launchpad(scripts_lab, tmp_path, monkeypatch, answers[:1],
                         live={a: _basket("BTC", "ETH")},
                         readings={("BTC", "ETH"): (6.5, 1.3)})
    scripts_lab.night_promote()
    _write(tmp_path, "nexus.jsonl", answers)

    again = scripts_lab.night_promote()

    assert [card for card, _ in sent] == [a], sent
    assert len(qa_rooms.strategies(qa_rooms.load())) == 1
    assert any("NEX-0002" in h and "STR-0001" in h for h in again["held"]), (
        again["held"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_id_their_api_does_not_know_is_not_called_an_invented_card(
        tmp_path, monkeypatch):
    """R06 (2/3): every UUID in an answer is read as a card, and his answers
    also carry run ids and species ids (NEX-0010, NEX-0015). A 404 on one of
    those was written down as a card Nexus invented -- #91 -- and the brief
    reads the gate back to him as his record. The 404 still means nothing is
    bought; what it may not do is claim which of the two it was."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    c = _card(0xC)
    answers = [{"type": "answer", "id": "NEX-0001",
                "at": (NOW - timedelta(minutes=30)).isoformat(),
                "text": _whole(c)}]
    sent, _ = _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
                         live={c: None}, readings={})

    did = scripts_lab.night_promote()

    assert sent == []
    (gate,) = [r for r in lab.load() if r.get("type") == "gate"]
    for said in (gate["why"], " ".join(did["held"])):
        assert "no card" in said and "not a card" in said, said
        # B02, deep pass of 2026-09-22: `"or" in said` found "or" inside
        # order and record, so a plain accusation passed. Each "invented"
        # has to be one side of a whole-word "or" that follows it.
        for hit in re.finditer(r"invented", said):
            assert re.search(r"\bor\b", said[hit.end():hit.end() + 40]), said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_he_gave_elsewhere_is_his_guidance_not_his_latency(
        tmp_path, monkeypatch):
    """The operator talks to Nexus on their website, and had nowhere to put it.

    What he says there is guidance like any other: the brief should hold it,
    the board should be able to score it, the next tick should not ask it
    again. Until `record` there was nowhere to write it down, so it lived in a
    conversation that ends at the next /clear -- the same loss as ET-22498.

    It must NOT reach `load()`. #85 and #86 measure their channel from that
    file, and a row we typed in has no poll behind it and no latency to read:
    counting it would be a verdict about their availability drawn from our own
    keyboard. That is `a-read-that-writes-is-a-writer`, and `lane: shallow`
    already exists for exactly this separation.
    """
    import importlib
    import importlib.util as util

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state
    importlib.reload(qa.state)
    spec = util.spec_from_file_location("nexus_record",
                                        REPO / "scripts" / "nexus.py")
    nexus = util.module_from_spec(spec)
    spec.loader.exec_module(nexus)

    said = nexus.record_answer("what breaks stockbull-blue?",
                               "  Treat 24 hours as one regime-day.  ",
                               at="2026-09-19T21:00:00+00:00")

    assert nexus.load() == [], (
        "a pasted answer landed in the diary the channel checks measure")
    rows = nexus.load_shallow()
    assert [r["type"] for r in rows] == ["question", "answer"]
    assert rows[0]["id"] == rows[1]["id"] == said["id"]
    assert said["text"] == "Treat 24 hours as one regime-day."
    assert said["at"] == "2026-09-19T21:00:00+00:00", (
        "the diary is a timeline: it records when HE said it")
    assert said["via"] == "web chat" and said["lane"] == "operator"
    assert [r["id"] for r in nexus.load_all()] == [r["id"] for r in rows], (
        "the laboratory reads load_all, and his guidance is not in it")

    # An id is never reused across the two diaries.
    again = nexus.record_answer("and the drawdown?", "watch N_eff")
    assert again["id"] != said["id"]

    try:
        nexus.record_answer("nothing", "   ")
    except SystemExit as refused:
        assert "not an answer" in str(refused), str(refused)
    else:  # pragma: no cover -- the assertion is the point
        raise AssertionError("an empty answer was written down as one")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_picking_up_a_refused_question_says_it_was_refused(tmp_path, monkeypatch):
    """NEX-0087, 2026-09-23 05:26 UTC: QUERY_RESTRICTED at the door, so the
    row has no job_id, and `nexus.py answer NEX-0087` died in a KeyError
    traceback. There is nothing to poll; the refusal is the answer."""
    import importlib
    import importlib.util as util

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state
    importlib.reload(qa.state)
    spec = util.spec_from_file_location("nexus_refused",
                                        REPO / "scripts" / "nexus.py")
    nexus = util.module_from_spec(spec)
    spec.loader.exec_module(nexus)
    nexus._append({"id": "NEX-0087", "type": "question",
                   "at": "2026-09-23T05:26:04+00:00", "tool": "ask_nexus_deep",
                   "question": "which card?", "accepted": False,
                   "error": "tool error: {'error': 'QUERY_RESTRICTED'}"})

    def no_door():
        raise AssertionError("a refused question was polled")
    monkeypatch.setattr(nexus, "_client", no_door)

    try:
        nexus.answer("NEX-0087")
    except SystemExit as said:
        assert "refused" in str(said) and "QUERY_RESTRICTED" in str(said), str(said)
    else:  # pragma: no cover -- the assertion is the point
        raise AssertionError("a refused question was picked up as outstanding")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verdict_reads_the_whole_index_history_not_the_last_five_days(
        tmp_path, monkeypatch):
    """`index-history` with no `interval` answers the last five days only.

    A verdict is read after its window closes, so five days back from then
    starts inside the window, or past it: STR-0005 (a 7-day window read 10 h
    after it closed) came back inconclusive at 65% coverage with its entry
    taken two days late. The operator was told the holes were in their
    history; that one was in our request.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    asked = []

    class Response:
        status_code = 200

        def json(self):
            return {"interval": "all", "points": []}

    class Client:
        def get(self, path, **kwargs):
            asked.append((path, kwargs))
            return Response()

    scripts_lab._history(Client(), "2a6f5562-01f2-4522-ae8a-eb355e74be94")
    ((path, kwargs),) = asked
    interval = (kwargs.get("params") or {}).get("interval")
    if interval is None and "interval=" in path:
        interval = path.split("interval=", 1)[1].split("&", 1)[0]
    assert interval == "all", (path, kwargs)


# ---------------------------------------------------------------------------
# 2026-09-22: bots cloned on paper and funds marked, not only cards
# ---------------------------------------------------------------------------
#
# The operator: "proč běží jen samé karty, proč nezkouší boty... papírově jde
# spustit plno věcí kromě karet". Their catalogue as GET
# /api/v1/cloned-bots/available answered it (evidence 1287ecda), in part.

MACD = {"id": "dd206f68-048f-4325-9f33-4ca77e40bbeb", "name": "MACD Hunter",
        "source_type": "wta_species"}
TITAN = {"id": "86de496c-a5df-49e7-91e2-b0dc96cfd783", "name": "Trend Titan",
         "source_type": "wta_species"}
DOOM = {"id": "80ec35bf-a03e-45e0-9c5c-6053f5c69076", "name": "Doom & Gloom",
        "source_type": "perpetual_agent"}
LIQ = {"id": "e1251539-3494-4993-9568-42bf35c757fa", "name": "Liquidation Hunter",
       "source_type": "perpetual_agent"}
CATALOGUE = [MACD, TITAN, DOOM, LIQ]
FUNDS = ["AIB-SPACE", "AIB-AI", "FTA-STOCKS"]


def _clonepad(scripts_lab, tmp_path, monkeypatch, answers, fund_points=None,
              clone_outcome="accepted"):
    """night_promote with the bot catalogue, the fund roster and clone.py's
    three writes stubbed -- each stub writes the rows the real one writes, so
    the record downstream is the real record. Nothing reaches their side."""
    sent, _ = _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
                         live={}, readings={})
    monkeypatch.setattr(scripts_lab, "_bot_catalogue", lambda: list(CATALOGUE))
    monkeypatch.setattr(scripts_lab, "_fund_catalogue", lambda: list(FUNDS))
    monkeypatch.setattr(scripts_lab, "_fund_points",
                        lambda symbol: (fund_points or {}).get(symbol, []))
    pinned = scripts_lab._sibling
    clone = pinned("clone")
    calls = []

    def _clone(source_type, source_id, name, nexus_id, confirm):
        calls.append(("clone", source_type, source_id, nexus_id, confirm))
        cid = clone._next_id(clone.load())
        clone._append({"id": cid, "type": "intent", "at": NOW.isoformat(),
                       "source_type": source_type, "source_id": source_id,
                       "custom_name": name, "paper": True,
                       "nexus": {"id": nexus_id}})
        out = {"id": cid, "type": "outcome", "at": NOW.isoformat(),
               "outcome": clone_outcome, "http_status": 200,
               "clone_instance_id": f"inst-{len(calls)}", "is_paper": True,
               "is_trading": False}
        clone._append(out)
        return out

    def _fund(instance_id, amount, confirm):
        calls.append(("fund", instance_id, amount, confirm))
        cid = clone._next_id(clone.load())
        # The real clock, as clone.fund writes it: a bot enters at its
        # funding, which comes after the criterion the launch just wrote.
        funded_at = datetime.now(timezone.utc).isoformat()
        clone._append({"id": cid, "type": "intent", "at": funded_at,
                       "kind": "fund", "instance_id": instance_id,
                       "amount": float(amount)})
        clone._append({"id": cid, "type": "outcome", "at": funded_at,
                       "kind": "fund", "outcome": "accepted",
                       "http_status": 200})
        return {"bot_balance": amount}

    def _enable(instance_id, confirm, enabled=True):
        calls.append(("enable" if enabled else "pause", instance_id, confirm))
        cid = clone._next_id(clone.load())
        kind = "enable" if enabled else "disable"
        # The real clock, as clone.enable writes it: a variant's restart is
        # found AFTER its room's criterion (V5), which is written on it too.
        at = datetime.now(timezone.utc).isoformat()
        clone._append({"id": cid, "type": "intent", "at": at, "kind": kind,
                       "instance_id": instance_id,
                       "bot_profit_usdc": _enable.profit})
        clone._append({"id": cid, "type": "outcome", "at": at,
                       "kind": kind, "outcome": "accepted", "http_status": 200})
        return {"is_trading": enabled}
    # What their row says the bot has made, as the real enable() records it.
    _enable.profit = None

    def _settings(instance_id, changes, confirm):
        calls.append(("settings", instance_id, dict(changes), confirm))
        cid = clone._next_id(clone.load())
        at = datetime.now(timezone.utc).isoformat()
        clone._append({"id": cid, "type": "intent", "at": at, "kind": "settings",
                       "instance_id": instance_id, "body": dict(changes)})
        clone._append({"id": cid, "type": "outcome", "at": at, "kind": "settings",
                       "outcome": _settings.outcome, "http_status": 200})
        return {"id": cid, "outcome": _settings.outcome}
    _settings.outcome = "accepted"

    clone.clone, clone.fund, clone.enable = _clone, _fund, _enable
    clone.settings = _settings
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: clone if n == "clone" else pinned(n))
    return sent, calls


def _answer(text, ident="NEX-0001"):
    return [{"type": "answer", "id": ident,
             "at": (NOW - timedelta(minutes=30)).isoformat(),
             "text": text + " " + ("reasoning. " * 40)}]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_catalogue_readers_take_whole_names_and_respect_what_he_ruled_out():
    """A bot is proposed by its exact species name from their catalogue, a
    fund by its exact symbol from list_funds. A name inside a longer word is
    not a mention, and a name that sits only under a ruling-out heading is
    not a proposal -- the same reading ruled_out_cards gives a card."""
    text = ("**Clone MACD Hunter on paper.** It fits the regime.\n"
            "Mark `AIB-SPACE` as the fund to watch.\n\n"
            "**Why the others are out:**\n"
            "- Trend Titan: chops in this range.\n"
            "- AIB-AI: too concentrated.\n\n"
            "MACD Hunters in general lag; Doom & Gloom has no edge here, "
            "skip it.\n")
    bots = [b["name"] for b in lab.proposed_bots(text, CATALOGUE)]
    assert bots == ["MACD Hunter"], bots
    assert lab.proposed_funds(text, FUNDS) == ["AIB-SPACE"]
    assert lab.proposed_bots("Moon Hunter looks good", CATALOGUE) == []
    # B02, deep pass of 2026-09-22 evening (3/3): the only longer word above
    # named a bot already proposed, so plain substring matching stayed green.
    # Unproposed and inside longer words, it must not be read as a mention.
    assert lab.proposed_bots("The Trend Titans of this cycle are all "
                             "MACD Hunters.", CATALOGUE) == []
    assert lab.proposed_funds("The AIB-SPACEX basket is not ours.", FUNDS) == []
    assert lab.proposed_funds("aib-space, lower case, is not the symbol",
                              FUNDS) == []
    # R02, deep pass of 2026-09-22: a bot he measures his pick against, in
    # plain prose and under no ruling heading, is not a second pick. When he
    # says which he picks, only the bots on that line are proposals.
    compared = ("**Pick: MACD Hunter** (momentum).\n\n"
                "It beats RSI Sniper and Trend Titan on trend days.\n")
    assert [b["name"] for b in lab.proposed_bots(compared, CATALOGUE)] == [
        "MACD Hunter"]
    both = "MACD Hunter and Trend Titan both look fine here.\n"
    assert [b["name"] for b in lab.proposed_bots(both, CATALOGUE)] == [
        "MACD Hunter", "Trend Titan"]
    # 2026-09-23 02:15 UTC, NEX-0081: asked for ONE fund, he answered "## Pick:
    # **AIB-MOLECULAR**" and ranked it ahead of five others in prose -- and
    # the fund reader, which never got R02's rule, opened six rooms. The same
    # rule for funds: when a line says which he picks, only those are picks.
    ranked = ("## Pick: **AIB-SPACE** -- mark it, watch 5 days.\n"
              "It sits at the top, ahead of AIB-AI (+9.8%) and FTA-STOCKS.\n")
    assert lab.proposed_funds(ranked, FUNDS) == ["AIB-SPACE"]
    assert lab.proposed_funds("AIB-SPACE and AIB-AI both look fine.\n",
                              FUNDS) == ["AIB-SPACE", "AIB-AI"]
    # The card reader keeps its own behaviour through the shared section logic.
    card = _card(0x77)
    assert lab.ruled_out_cards(f"**These are out:**\n- `{card}`\n") == {card}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_markdown_section_that_rules_out_holds_its_prose_and_a_qualifier_rules_nothing():
    """NEX-0086, 2026-09-23 04:56 UTC, in its shape: one fund picked under
    "# ONE PICK", its sub-heading qualified "(... a watch, not a buy)", and
    every bot named in a PARAGRAPH under "# BOTS — RULED OUT". The paragraph,
    a non-bullet line, closed the ruling section, so all six bots read as
    proposals -- the next tick would have cloned two he called noise -- and
    the qualifier's "not a buy" ruled out the one fund he did pick."""
    card = _card(0x86)
    text = (
        "Verified. Here is the result of running the gate myself.\n\n"
        "# ONE PICK THAT CLEARS THE BAR\n\n"
        "**FUND — AIB-SPACE — mark/watch (no side; long-only NAV sleeve, so "
        "this is a watch, not a buy)**\n"
        "- Watch-up trigger: +8% from current.\n"
        "- Rests on: the strongest live sleeve, ahead of AIB-AI at 99.96.\n"
        "- Reader's next step: GET /api/v1/aib/AIB-SPACE/quote.\n\n"
        "That is the only slot I will spend. Everything below is ruled out "
        "on purpose — none of these is a pick.\n\n"
        "# CARDS — RULED OUT (do NOT read any id below as a pick)\n\n"
        f"- {card} — unbacktestable.\n\n"
        "# BOTS — RULED OUT (do NOT read any species name below as a pick)\n\n"
        "Full roster from /api/v1/cloned-bots/available. Every species with "
        "a real sample is net-negative: MACD Hunter -$52.1, Trend Titan "
        "-$284.6, least-bad Doom & Gloom at 50.9%. The only positive PnL is "
        "Liquidation Hunter at +$0.05 over 5 trades — noise, not evidence.\n\n"
        "If you want a bot to add signal, clone a fresh one and point it at "
        "a set.\n\n"
        "**Summary: 1 pick (mark AIB-SPACE). 0 cards, 0 bots — withheld "
        "because none cleared the bar.**\n")

    assert lab.proposed_bots(text, CATALOGUE) == []
    assert lab.proposed_funds(text, FUNDS) == ["AIB-SPACE"]
    assert lab.ruled_out_cards(text) == {card}
    # A markdown heading that does not rule out keeps the old reading below
    # it: a bold heading that rules out still opens a section of its own.
    mixed = ("# Recommendation\n\n**Clone MACD Hunter.**\n\n"
             "**Why the others are out:**\n- Trend Titan: chops.\n")
    assert [b["name"] for b in lab.proposed_bots(mixed, CATALOGUE)] == [
        "MACD Hunter"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_he_names_is_cloned_funded_and_started_on_paper_in_its_own_room(
        tmp_path, monkeypatch):
    """clone (paper) -> fund with the stake -> enable, through clone.py's own
    functions, so its paper floors and its CLN record are the ones used. A
    bot has no backtest, so it goes at half the stake, like an untested card.
    Its room holds one leg -- the bot's instance -- a criterion of the same
    window, stop and benchmark as a card, and a link to its clone."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch,
                            _answer("Clone MACD Hunter on paper, it suits the tape."))

    did = scripts_lab.night_promote()

    half = scripts_lab._leg_stakes(100000.0, 0.0, 1, half=True)[0]
    assert [c[0] for c in calls] == ["clone", "fund", "enable"], calls
    assert calls[0][1:] == ("wta_species", MACD["id"], "NEX-0001", True)
    assert calls[1] == ("fund", "inst-1", half, True) and half > 0
    assert sent == [], "a bot room placed a card order"
    assert did["rooms"] == 1, did
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    assert (room["kind"], room["ref"]) == ("bot", MACD["id"])
    criterion = qa_rooms.acceptance_of(rows, room["id"])
    assert [(qa_rooms.leg_kind(g), qa_rooms.leg_ref(g))
            for g in criterion["legs"]] == [("bot", "inst-1")]
    assert (criterion["window_days"], criterion["stop_pct"]) == (
        scripts_lab.NIGHT_WINDOW_DAYS, scripts_lab.NIGHT_STOP_PCT)
    assert criterion["benchmark_card"] == scripts_lab.BTC_PROXY
    assert "not backtested" in criterion["why"].lower()
    assert qa_rooms.status_of(rows, room["id"]) == "running"
    assert any(r.get("type") == "link" and r.get("room") == room["id"]
               and str(r.get("ref")).startswith("CLN-") for r in rows)

    again = scripts_lab.night_promote()
    assert [c[0] for c in calls] == ["clone", "fund", "enable"], (
        "the next tick cloned the same bot again")
    assert again["rooms"] == 0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_nobody_lists_or_he_ruled_out_opens_nothing(tmp_path, monkeypatch):
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    text = ("Moon Hunter is my pick.\n\n**Why the others are out:**\n"
            "- Trend Titan: chops.\n")
    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch, _answer(text))

    scripts_lab.night_promote()

    assert calls == [] and sent == []
    assert qa_rooms.strategies(qa_rooms.load()) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_alternatives_he_weighed_against_his_pick_are_not_picks(
        tmp_path, monkeypatch):
    """NEX-0073, 2026-09-22: asked for ONE bot, he answered "**Pick: MACD
    Hunter**" and then "**Why it edges the alternatives:** Fibonacci Phoenix
    ... and RSI Sniper ... and Perceptron Oracle ...". The launch cloned all
    four; two were stopped and paused by hand."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    text = ("**Pick: MACD Hunter** (momentum).\n\n"
            "**Why it edges the alternatives:** Fibonacci Phoenix (40%) and "
            "Trend Titan (35%) need a higher hit-rate.\n")
    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch, _answer(text))

    scripts_lab.night_promote()

    titles = [r["title"] for r in qa_rooms.strategies(qa_rooms.load())]
    assert titles == ["MACD Hunter"], titles


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clone_they_did_not_accept_is_never_funded(tmp_path, monkeypatch):
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch,
                            _answer("Clone MACD Hunter."), clone_outcome="rejected")

    did = scripts_lab.night_promote()

    assert [c[0] for c in calls] == ["clone"], calls
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    assert qa_rooms.status_of(rows, room["id"]) == "stopped"
    assert any("MACD Hunter" in h for h in did["held"]), did


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_species_we_already_own_a_clone_of_is_not_cloned_again(
        tmp_path, monkeypatch):
    """R01, deep pass of 2026-09-22: STR-0001's Perceptron clone (CLN-0002)
    had no room the launch could see, so NEX-0073 cloned Perceptron Oracle a
    second time -- their API refused it with a 400 (CLN-0017), after a room
    and a cap slot were already spent. A clone we own is held, whoever
    opened it and whether or not it is paused."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch,
                            _answer("Clone MACD Hunter on paper."))
    _write(tmp_path, "clones.jsonl", [
        {"id": "CLN-0002", "type": "intent", "source_type": "wta_species",
         "source_id": MACD["id"], "paper": True},
        {"id": "CLN-0002", "type": "outcome", "outcome": "accepted",
         "http_status": 200, "clone_instance_id": "inst-old"},
        # B05, deep pass of 2026-09-22 evening: "whether or not it is
        # paused" -- and the fixture had no pause, so a reader that dropped
        # paused instances stayed green. Paused here, the way close_positions
        # pauses one: an accepted disable.
        {"id": "CLN-0003", "type": "intent", "kind": "disable",
         "instance_id": "inst-old"},
        {"id": "CLN-0003", "type": "outcome", "kind": "disable",
         "outcome": "accepted", "http_status": 200}])

    did = scripts_lab.night_promote()

    assert calls == [], calls
    assert qa_rooms.strategies(qa_rooms.load()) == []
    assert did["rooms"] == 0
    assert any("CLN-0002" in h for h in did["held"]), did["held"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_species_their_api_refused_to_clone_is_not_tried_on_every_answer(
        tmp_path, monkeypatch):
    """R06, deep pass of 2026-09-22: a refused clone left a stopped room and
    nothing against the species, so every later answer naming it opened
    another room, spent another slot and got the same refusal."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    answers = (_answer("Clone MACD Hunter.", "NEX-0001")
               + _answer("MACD Hunter again, it suits the tape.", "NEX-0002"))
    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch, answers,
                            clone_outcome="rejected")

    first = scripts_lab.night_promote()
    # A LATER answer naming it (the first two are read once since V5).
    _write(tmp_path, "nexus.jsonl",
           answers + _answer("And MACD Hunter once more.", "NEX-0003"))
    second = scripts_lab.night_promote()

    assert [c[0] for c in calls] == ["clone"], calls
    assert len(qa_rooms.strategies(qa_rooms.load())) == 1
    assert first["rooms"] + second["rooms"] == 1
    assert any("NEX-0003" in h and "refused" in h and "MACD Hunter" in h
               for h in second["held"]), second["held"]


def _bot_room(scripts_lab, tmp_path, monkeypatch):
    import qa.rooms as qa_rooms

    sent, calls = _clonepad(scripts_lab, tmp_path, monkeypatch,
                            _answer("Clone MACD Hunter on paper."))
    scripts_lab.night_promote()
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    acceptance = qa_rooms.acceptance_of(rows, room["id"])
    funded = calls[1][2]
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: [
                            {"t": (datetime.fromisoformat(acceptance["at"])
                                   + timedelta(hours=h)).isoformat(),
                             "index": 100.0} for h in range(0, 24 * 6)])
    return room, acceptance, funded, calls


def _bot_samples(tmp_path, start, funded, profits, balances=None, hours=6):
    rows = []
    for n, profit in enumerate(profits):
        rows.append({"type": "sample", "kind": "bot", "instance_id": "inst-1",
                     "at": (start + timedelta(hours=hours * n)).isoformat(),
                     "balance_usdc": str((balances or {}).get(n, funded + profit)),
                     "total_profit_usdc": str(profit), "is_paper": True})
    _write(tmp_path, "samples.jsonl", rows)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_room_is_judged_on_what_it_made_and_paused_at_the_close(
        tmp_path, monkeypatch):
    """The series is the bot's own, from the sampler's rows, rebased to 100 at
    entry: what went in plus what it made (`total_profit_usdc`), the reading
    paper.capital_in_bots uses. NOT `balance_usdc` alone: since their fix of
    #94 a stake is debited from it on entry, so a bot that opens a position
    reads as a loss it has not taken. At the close the bot is paused."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, acceptance, funded, calls = _bot_room(scripts_lab, tmp_path, monkeypatch)
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    count = int(days * 24 / 6) + 1

    # Mid-window: half its balance in a trade, nothing lost. Not refuted.
    _bot_samples(tmp_path, start, funded, [0.0] * 4,
                 balances={2: funded * 0.5, 3: funded * 0.5})
    assert scripts_lab.verdicts(now=start + timedelta(hours=20)) == []
    assert qa_rooms.status_of(qa_rooms.load(), room["id"]) == "running"

    # The close: +5% on what went in, the benchmark flat. Survived, paused.
    _bot_samples(tmp_path, start, funded,
                 [funded * 0.05 * n / (count - 1) for n in range(count)])
    said = scripts_lab.verdicts(now=start + timedelta(days=days, hours=1))
    assert [s["verdict"] for s in said] == ["survived"], said
    assert said[0]["return_pct"] == pytest.approx(5.0)
    assert calls[-1] == ("pause", "inst-1", True), calls
    assert qa_rooms.status_of(qa_rooms.load(), room["id"]) == "stopped"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_is_judged_from_what_went_in_not_from_its_first_reading(
        tmp_path, monkeypatch):
    """Bollinger Bandit, STR-0034: 240 USDC in, and by the sampler's first
    reading it had already made +33.6; it gave most of that back and stood at
    +7.1. The verdict took the FIRST READING as the entry, so a bot that made
    +2.96% on what went in read -9.7% -- rebased on a peak it reached before
    anyone looked. A bot enters at 100 when it is funded; a room that took
    over a bot funded before its window still starts from the first reading
    inside it."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, acceptance, funded, calls = _bot_room(scripts_lab, tmp_path, monkeypatch)
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    first = start + timedelta(hours=1)
    count = int((days * 24 - 5) / 6) + 1
    profits = [33.6 / 240 * funded] * (count - 1) + [7.1 / 240 * funded]
    _bot_samples(tmp_path, first, funded, profits)

    said = scripts_lab.verdicts(now=start + timedelta(days=days, hours=1))

    assert [s["verdict"] for s in said] == ["survived"], said
    assert said[0]["return_pct"] == pytest.approx(7.1 / 240 * 100), said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_past_its_stop_is_refuted_early_and_paused(tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, acceptance, funded, calls = _bot_room(scripts_lab, tmp_path, monkeypatch)
    start = datetime.fromisoformat(acceptance["at"])
    _bot_samples(tmp_path, start, funded, [0.0, -0.05 * funded, -0.15 * funded])

    said = scripts_lab.verdicts(now=start + timedelta(hours=13))

    assert [s["verdict"] for s in said] == ["refuted"] and said[0]["early"], said
    assert calls[-1] == ("pause", "inst-1", True), calls


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_with_too_few_samples_is_inconclusive_not_a_loss(tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, acceptance, funded, calls = _bot_room(scripts_lab, tmp_path, monkeypatch)
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    _bot_samples(tmp_path, start, funded, [0.0])

    said = scripts_lab.verdicts(now=start + timedelta(days=days, hours=1))

    assert [s["verdict"] for s in said] == ["inconclusive"], said


def _flat_then(start, values, hours=6):
    return [{"t": (start + timedelta(hours=hours * n)).isoformat(), "v": v}
            for n, v in enumerate(values)]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fund_is_marked_not_bought_and_judged_on_its_own_series(
        tmp_path, monkeypatch):
    """create_aib_fund costs real money and has no paper switch, so a fund
    Nexus picks is WATCHED: a room, a leg, a criterion, and no order of any
    kind. Its notional stake is written down and counts toward no ceiling.
    The verdict reads get_fund_history the way it reads a card's index. A
    fund whose history is empty has nothing to judge and opens no room."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    start = NOW - timedelta(hours=1)
    series = {"AIB-SPACE": _flat_then(start, [64.0] * 3)}
    sent, calls = _clonepad(
        scripts_lab, tmp_path, monkeypatch,
        _answer("Mark AIB-SPACE, and FTA-STOCKS if you want a second."),
        fund_points=series)
    deployed = scripts_lab._deployed()

    did = scripts_lab.night_promote()

    assert sent == [] and calls == [], "a fund was bought or cloned"
    assert scripts_lab._deployed() == deployed, "a marked fund counted as deployed"
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    assert (room["kind"], room["ref"]) == ("fund", "AIB-SPACE"), did
    assert any("FTA-STOCKS" in h for h in did["held"]), did
    criterion = qa_rooms.acceptance_of(rows, room["id"])
    assert [(qa_rooms.leg_kind(g), qa_rooms.leg_ref(g))
            for g in criterion["legs"]] == [("fund", "AIB-SPACE")]
    moved = [r for r in rows if r.get("type") == "status"]
    assert moved[-1]["status"] == "running"
    assert "marked, not bought" in moved[-1]["why"]

    opened = datetime.fromisoformat(criterion["at"])
    days = float(criterion["window_days"])
    count = int(days * 24 / 6) + 2
    series["AIB-SPACE"] = _flat_then(
        opened, [64.0 * (1 + 0.04 * n / count) for n in range(count)])
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, c: [{"t": p["t"], "index": 100.0}
                                           for p in series["AIB-SPACE"]])
    said = scripts_lab.verdicts(now=opened + timedelta(days=days, hours=13))
    assert [s["verdict"] for s in said] == ["survived"], said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_arena_leg_is_a_gap_until_something_reads_its_series(
        tmp_path, monkeypatch):
    """An arena leg (2026-09-22) names a team, BLUE or RED, and nothing here
    reads a team's price yet: how a share settles is NEX-0076's question. Any
    kind series_of does not know fell through to a CARD's index-history, so
    an arena leg would have been judged on /event-cards/BLUE. Until a reader
    exists it is a gap -- inconclusive, never a loss and never a pass."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _write(tmp_path, "nexus.jsonl", _answer("Hold BLUE through the next epoch."))
    room = qa_rooms.open_strategy("NEX-0001", "Arena BLUE", kind="arena",
                                  ref="BLUE")
    qa_rooms.set_plan(room["id"], [
        {"kind": "arena", "ref": "BLUE", "side": "bull", "share": 0.1}])
    qa_rooms.set_acceptance(room["id"], 1.0, 10.0, "an arena room under test")
    qa_rooms.set_status(room["id"], "running", "an arena room under test")

    read = []
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, card: read.append(card) or [])
    said = scripts_lab.verdicts(now=datetime.now(timezone.utc) + timedelta(days=2))

    assert "BLUE" not in read, f"a team was read as a card: {read}"
    assert [s["verdict"] for s in said] == ["inconclusive"], said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_board_the_brief_and_resume_read_bot_and_fund_rooms(
        tmp_path, monkeypatch, capsys):
    """The plan's own check: `lab.py board` and `resume` over the new rooms.
    A bot's gate row names `bot:<species>` where every earlier row named a
    card (a fund writes one, `fund:<symbol>`, only when its history is empty
    -- see the fund test) -- and resume is the first thing a tick after a
    /clear runs."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _clonepad(scripts_lab, tmp_path, monkeypatch,
              _answer("Clone MACD Hunter, and mark AIB-SPACE."),
              fund_points={"AIB-SPACE": _flat_then(NOW, [64.0, 64.0])})
    scripts_lab.night_promote()

    # The board is one line per ANSWER: both of its rooms, the bot's gate.
    (line,) = [scripts_lab._board_line(row) for row in scripts_lab.board_rows()]
    assert "STR-0001" in line and "STR-0002" in line, line
    assert "MACD Hunter" in line, line
    # B08, deep pass of 2026-09-22 evening: the gate keys the docstring names
    # were asserted nowhere, and brief() only for being non-empty -- its
    # first line is fixed, so it always is.
    keys = {key for _, key in lab.gates()}
    assert "bot:MACD Hunter" in keys, keys
    said = scripts_lab.brief()
    # The brief counts them rather than naming them: both rooms, the bot's
    # and the fund's, are running experiments on its book line.
    assert re.search(r"\b2 experiment\(s\) running", said), said[:600]
    assert scripts_lab.cmd_resume() == 0
    capsys.readouterr()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_room_does_not_spend_the_rest_of_its_answer(tmp_path, monkeypatch):
    """B03, deep pass of 2026-09-22 evening (3/3). A room with no `card` used
    to mean a WHOLE-ANSWER room in three places -- open_strategy, the launcher
    and the page -- and only open_strategy was driven. In the launcher,
    reading a bot room as whole-answer marks its answer spent, so a card of
    the same answer held back on one tick never opens on a later one."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    a = _card(0xA)
    sent, _ = _launchpad(
        scripts_lab, tmp_path, monkeypatch,
        _answer(f"Clone MACD Hunter on paper. Buy {a} bull, sized small."),
        live={a: _basket("BTC", "ETH")},
        readings={("BTC", "ETH"): (6.5, 1.3)})
    # The bot's room stands already, from an earlier tick.
    qa_rooms.open_strategy("NEX-0001", "MACD Hunter", kind="bot", ref=MACD["id"])

    did = scripts_lab.night_promote()

    assert [card for card, _ in sent] == [a], (sent, did)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_money_in_a_clone_is_out_and_a_paused_clone_holds_it_parked(
        tmp_path, monkeypatch):
    """A clone funded with practice money holds it until somebody moves it
    back -- pausing the bot does not -- so an accepted transfer is out of the
    free cash, and a refused one never was.

    But out is not exposed. The plan's V2 (review of 2026-09-23): 1 960 USDC
    sat in paused bots and counted against the 60% ceiling as if it traded.
    Money in a clone that is not trading -- paused by us, or stopped by
    itself, which the sampler sees as `is_trading: false` after our start --
    is PARKED: it stays in the book and out of free cash, and only what
    trades counts against the ceiling."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)

    def fund(ident, instance, amount, outcome="accepted"):
        return [{"id": ident, "type": "intent", "kind": "fund",
                 "instance_id": instance, "amount": amount},
                {"id": ident, "type": "outcome", "kind": "fund",
                 "outcome": outcome, "http_status": 200}]

    def switch(ident, instance, kind, at):
        return [{"id": ident, "type": "intent", "kind": kind,
                 "instance_id": instance, "at": at},
                {"id": ident, "type": "outcome", "kind": kind,
                 "outcome": "accepted", "http_status": 200, "at": at}]
    _write(tmp_path, "clones.jsonl", [
        *fund("CLN-0002", "inst-1", 500.0),
        *fund("CLN-0003", "inst-1", 700.0, outcome="rejected"),
        # B06, deep pass of 2026-09-22 evening: "pausing the bot does not"
        # release the money -- a reader that dropped a paused instance's
        # transfers has to go red.
        *switch("CLN-0004", "inst-1", "disable", "2026-09-22T10:00:00+00:00"),
        *fund("CLN-0005", "inst-2", 240.0),
        *switch("CLN-0006", "inst-2", "enable", "2026-09-22T10:00:00+00:00"),
        *fund("CLN-0007", "inst-3", 100.0),
        *switch("CLN-0008", "inst-3", "enable", "2026-09-22T10:00:00+00:00")])
    _write(tmp_path, "samples.jsonl", [
        {"type": "sample", "kind": "bot", "instance_id": "inst-2",
         "at": "2026-09-22T09:00:00+00:00", "is_trading": False},
        {"type": "sample", "kind": "bot", "instance_id": "inst-2",
         "at": "2026-09-22T12:00:00+00:00", "is_trading": True},
        # inst-3 stopped by itself after we started it.
        {"type": "sample", "kind": "bot", "instance_id": "inst-3",
         "at": "2026-09-22T12:00:00+00:00", "is_trading": False}])

    assert scripts_lab._deployed() == 240.0, "only the bot that trades is exposed"
    assert scripts_lab._parked() == 600.0, (
        "a paused or self-stopped clone still holds its money")

    # 6 050 out on a 10 000 book passes 60%; with the 600 parked in the book
    # (10 600) it does not -- parked money is book, not exposure.
    ok, why = lab.affordable(50.0, 4_000.0, 0, deployed=6_000.0, parked=600.0)
    assert ok and "10600" in why, (
        "the book counts parked money, the exposure does not", why)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_bot_stop_is_ours_their_guard_or_unexplained():
    """The plan's V2 (review of 2026-09-23): two bots stopped by themselves
    and nobody noticed. Every stop now has one of three causes: OURS (our
    accepted pause came first), THEIR GUARD (it stopped at a cumulative loss,
    where their halt is documented to fire -- NEX-0049), or UNEXPLAINED. The
    real three of 2026-09-22/23: Fibonacci Phoenix paused by us a minute
    after its start, MACD Hunter halted at -24.02 on 240.21, and Bollinger
    Bandit halted between 01:43 and 02:05 while +7.11 up -- which nothing in
    their documentation explains, and which is a check and a report."""
    def fund(ident, instance, amount, at):
        return [{"id": ident, "type": "intent", "kind": "fund",
                 "instance_id": instance, "amount": amount, "at": at},
                {"id": ident, "type": "outcome", "outcome": "accepted", "at": at}]

    def switch(ident, instance, kind, at):
        return [{"id": ident, "type": "intent", "kind": kind,
                 "instance_id": instance, "at": at},
                {"id": ident, "type": "outcome", "outcome": "accepted", "at": at}]

    def sample(instance, at, trading, profit):
        return {"type": "sample", "kind": "bot", "instance_id": instance,
                "at": at, "is_trading": trading, "total_profit_usdc": profit}
    clones = [
        *fund("CLN-0009", "macd", 240.21, "2026-09-22T13:38:17+00:00"),
        *switch("CLN-0010", "macd", "enable", "2026-09-22T13:38:30+00:00"),
        *fund("CLN-0012", "fib", 240.21, "2026-09-22T13:38:38+00:00"),
        *switch("CLN-0013", "fib", "enable", "2026-09-22T13:38:41+00:00"),
        *switch("CLN-0018", "fib", "disable", "2026-09-22T13:39:55+00:00"),
        *fund("CLN-0022", "boll", 240.18, "2026-09-23T01:31:41+00:00"),
        *switch("CLN-0023", "boll", "enable", "2026-09-23T01:32:23+00:00")]
    samples = [
        sample("macd", "2026-09-22T20:00:00+00:00", False, "-24.02"),
        sample("fib", "2026-09-22T20:00:00+00:00", False, "0.0"),
        sample("boll", "2026-09-23T01:43:18+00:00", True, "33.6252"),
        sample("boll", "2026-09-23T02:05:44+00:00", False, "7.109328"),
        sample("boll", "2026-09-23T07:05:46+00:00", False, "7.109328")]

    stops = {s["instance"]: s for s in lab.bot_stops(clones, samples)}

    assert {k: v["cause"] for k, v in stops.items()} == {
        "fib": "ours", "macd": "their_guard", "boll": "unexplained"}, stops
    boll = stops["boll"]
    assert (boll["after"], boll["before"]) == (
        "2026-09-23T01:43:18+00:00", "2026-09-23T02:05:44+00:00"), boll
    assert boll["profit_usdc"] == pytest.approx(7.109328)
    assert stops["macd"]["after"] == "2026-09-22T13:38:30+00:00", (
        "a stop the sampler never saw trading is bounded by our start")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_free_cash_is_the_newest_account_read_whichever_script_took_it(
        tmp_path, monkeypatch):
    """clone.py snapshots the account either side of every transfer, as
    paper.py does of every order. Read from paper.jsonl alone, the free cash
    stayed at its pre-transfer figure while `_deployed` counted the transfer
    -- the same money on both sides of the book, which raises the ceiling."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _write(tmp_path, "paper.jsonl", [
        {"id": "TRD-0001", "type": "after", "at": "2026-09-22T10:00:00+00:00",
         "sim_balance_usdc": "100000"}])
    _write(tmp_path, "clones.jsonl", [
        {"id": "CLN-0002", "type": "after", "at": "2026-09-22T11:00:00+00:00",
         "sim_balance_usdc": "99500.00"}])
    assert scripts_lab._free_cash() == 99500.0
    _write(tmp_path, "paper.jsonl", [
        {"id": "TRD-0002", "type": "after", "at": "2026-09-22T12:00:00+00:00",
         "sim_balance_usdc": "99000"}])
    assert scripts_lab._free_cash() == 99000.0
    # RL08 (deep pass of 2026-09-24): a transfer whose after-read of the
    # account FAILED left the older, pre-transfer balance to win while
    # `_deployed` already counted the transfer. The newest read is unknown,
    # so the free cash is unknown -- the same refusal paper.py makes.
    _write(tmp_path, "clones.jsonl", [
        {"id": "CLN-0003", "type": "after", "at": "2026-09-22T13:00:00+00:00",
         "error": "account read: HTTP 503"}])
    assert scripts_lab._free_cash() is None, (
        "a failed read after a transfer fell back to the balance before it")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_verdict_is_the_same_number_with_or_without_a_kind():
    """A leg written before 2026-09-22 has only `card`; one written after has
    `kind` and `ref` beside it. The formula keys its series by ref, so both
    must give the identical verdict -- a card room judged differently after
    this change would be the past rewritten."""
    start = NOW - timedelta(days=6)
    card = _card(0x55)
    rising = [{"t": (start + timedelta(hours=h)).isoformat(),
               "index": 100.0 + h * 0.05} for h in range(24 * 5 + 2)]
    old = {"at": start.isoformat(), "window_days": 5.0, "stop_pct": 10.0,
           "legs": [{"card": card, "side": "bull", "share": 1.0,
                     "tp": None, "sl": None}]}
    new = {**old, "legs": [{**old["legs"][0], "kind": "card", "ref": card}]}
    was, now = lab.verdict(old, {card: rising}, NOW), lab.verdict(new, {card: rising}, NOW)
    assert was["verdict"] == now["verdict"] == "survived"
    assert (was["return_pct"], was["max_drawdown_pct"], was["coverage"]) == (
        now["return_pct"], now["max_drawdown_pct"], now["coverage"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_question_offers_a_card_a_bot_or_a_fund_and_names_all_we_hold(
        tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _clonepad(scripts_lab, tmp_path, monkeypatch,
              _answer("Clone MACD Hunter, and mark AIB-SPACE."),
              fund_points={"AIB-SPACE": _flat_then(NOW, [64.0, 64.0])})
    scripts_lab.night_promote()

    text = scripts_lab.cards_question()

    assert "/api/v1/cloned-bots/available" in text and "list_funds" in text
    assert "whole" in text.lower() and "uuid" in text.lower()
    assert "MACD Hunter" in text and "AIB-SPACE" in text, text


# ---------------------------------------------------------------------------
# V5: the tick walks a paper bot's settings in time, on its one clone
# ---------------------------------------------------------------------------

def _judged_bot(scripts_lab, tmp_path, monkeypatch, made_pct=0.05):
    """His pick's bot room, run to its verdict and paused by the close."""
    room, acceptance, funded, calls = _bot_room(scripts_lab, tmp_path, monkeypatch)
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    count = int(days * 24 / 6) + 1
    _bot_samples(tmp_path, start, funded,
                 [funded * made_pct * n / (count - 1) for n in range(count)])
    scripts_lab.verdicts(now=start + timedelta(days=days, hours=1))
    assert calls[-1] == ("pause", "inst-1", True), calls
    return room, funded, calls, scripts_lab._sibling("clone")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_starts_the_next_setting_of_a_judged_bot_on_its_one_clone(
        tmp_path, monkeypatch):
    """The phase's done-when: the tick starts a variant of a bot with other
    settings, through the paper floor, under 60% of the book alone.

    REPLY-0049: one paper clone per species, so the grid is walked in TIME on
    it: when a variant's room has its verdict (and the close paused the bot),
    the next setting opens a NEW room of ours (OUR-...), goes through
    clone.settings() -- the floor that refuses while a room runs, and the new
    room is not running yet -- and the bot starts again through
    clone.enable(). One at a time: nothing moves while a room runs on it. And
    the variant is judged from its restart, not from the clone's funding."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, acceptance, funded, calls = _bot_room(scripts_lab, tmp_path, monkeypatch)
    # His room runs: nothing to vary yet.
    assert scripts_lab.bot_variants()["rooms"] == 0
    assert "settings" not in [c[0] for c in calls]
    start = datetime.fromisoformat(acceptance["at"])
    days = float(acceptance["window_days"])
    count = int(days * 24 / 6) + 1
    _bot_samples(tmp_path, start, funded,
                 [funded * 0.05 * n / (count - 1) for n in range(count)])
    scripts_lab.verdicts(now=start + timedelta(days=days, hours=1))
    clone = scripts_lab._sibling("clone")

    clone.enable.profit = str(funded * 0.05)
    did = scripts_lab.bot_variants()

    assert [c[0] for c in calls[-2:]] == ["settings", "enable"], calls
    assert calls[-2][1:] == ("inst-1", lab.variants()[0]["settings"], True)
    assert did["rooms"] == 1 and did["orders"] == 1, did
    rows = qa_rooms.load()
    (variant,) = [s for s in qa_rooms.strategies(rows)
                  if str(s["origin"]).startswith("OUR-")]
    assert (variant["origin"], variant["kind"], variant["ref"]) == (
        "OUR-0001", "bot", MACD["id"]), variant
    assert "reference" in variant["title"] and "MACD Hunter" in variant["title"]
    assert qa_rooms.status_of(rows, variant["id"]) == "running"
    criterion = qa_rooms.acceptance_of(rows, variant["id"])
    assert [(qa_rooms.leg_kind(g), qa_rooms.leg_ref(g))
            for g in criterion["legs"]] == [("bot", "inst-1")]

    # One at a time: a room runs on the clone, so nothing moves.
    before = len(calls)
    assert scripts_lab.bot_variants()["rooms"] == 0 and len(calls) == before
    # And the next tick's verdicts leave it alone: his settled room no longer
    # owns the clone, so it is owed no pause -- the newest start is the
    # variant's, not his bot "still trading after its verdict".
    scripts_lab.verdicts(now=datetime.fromisoformat(criterion["at"])
                         + timedelta(hours=1))
    assert calls[before:] == [], ("a settled room paused the variant running "
                                  "on its clone", calls[before:])

    # Its verdict starts at its restart: +2% on what the bot held then
    # (240 in + 12 made), not +7% on the 240 that went in at the funding.
    vstart = datetime.fromisoformat(criterion["at"])
    held = funded * 1.05
    _write(tmp_path, "samples.jsonl", [
        {"type": "sample", "kind": "bot", "instance_id": "inst-1",
         "at": (vstart + timedelta(hours=6 * n)).isoformat(),
         "total_profit_usdc": str(funded * 0.05 + held * 0.02 * n / (count - 1)),
         "is_paper": True} for n in range(count)])
    said = scripts_lab.verdicts(now=vstart + timedelta(days=days, hours=1))
    assert [s["room"] for s in said] == [variant["id"]], said
    assert said[0]["return_pct"] == pytest.approx(2.0), said
    assert calls[-1] == ("pause", "inst-1", True), calls

    # And the walk goes on: the next setting, in the next room.
    scripts_lab.bot_variants()
    assert calls[-2][:3] == ("settings", "inst-1", lab.variants()[1]["settings"])
    assert calls[-1][0] == "enable"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_variant_that_cannot_run_starts_nothing_and_says_why(tmp_path, monkeypatch):
    """The refusals, each before anything is started: a settings PATCH their
    side did not accept leaves the bot paused and its room stopped with the
    reason (the variant is not proposed again every tick); a bot that
    stopped by itself before our pause is never started again (V2, a
    finding); and a book nobody can read starts nothing."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, funded, calls, clone = _judged_bot(scripts_lab, tmp_path, monkeypatch)

    real = scripts_lab._free_cash
    scripts_lab._free_cash = lambda: None
    did = scripts_lab.bot_variants()
    scripts_lab._free_cash = real
    assert did["rooms"] == 0 and any("unreadable" in h for h in did["held"]), did
    assert calls[-1][0] == "pause", calls

    clone.settings.outcome = "rejected"
    did = scripts_lab.bot_variants()
    assert calls[-1][0] == "settings", ("started after a refused PATCH", calls)
    rows = qa_rooms.load()
    (ours,) = [s for s in qa_rooms.strategies(rows)
               if str(s["origin"]).startswith("OUR-")]
    assert qa_rooms.status_of(rows, ours["id"]) == "stopped"
    assert any("settings" in h for h in did["held"]), did
    # The refused variant is spent; the next tick proposes the next one.
    clone.settings.outcome = "accepted"
    scripts_lab.bot_variants()
    assert calls[-2][2] == lab.variants()[1]["settings"], calls[-2]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_their_side_halted_is_never_varied(tmp_path, monkeypatch):
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, funded, calls, clone = _judged_bot(scripts_lab, tmp_path, monkeypatch)
    rows = clone.load()
    started = next(r["at"] for r in rows if r.get("kind") == "enable")
    paused = next(r["at"] for r in rows if r.get("kind") == "disable")
    halted = datetime.fromisoformat(started) + (
        datetime.fromisoformat(paused) - datetime.fromisoformat(started)) / 2
    _write(tmp_path, "samples.jsonl", [
        {"type": "sample", "kind": "bot", "instance_id": "inst-1",
         "at": halted.isoformat(), "is_trading": False,
         "total_profit_usdc": str(-0.1 * funded)}])
    before = len(calls)

    did = scripts_lab.bot_variants()

    assert len(calls) == before and did["rooms"] == 0, calls[before:]
    assert any("by itself" in h for h in did["held"]), did
    assert not [s for s in qa_rooms.strategies(qa_rooms.load())
                if str(s["origin"]).startswith("OUR-")]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_our_rooms_rank_after_his_and_are_put_to_him_as_questions(
        tmp_path, monkeypatch):
    """The own lane's two rules the board and the brief keep: a room of ours
    is never ranked above his picks, whatever it earned, and each one running
    is listed as a QUESTION for him -- never a proposal."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, funded, calls, clone = _judged_bot(scripts_lab, tmp_path, monkeypatch,
                                             made_pct=-0.02)
    clone.enable.profit = str(-0.02 * funded)
    scripts_lab.bot_variants()
    vstart = datetime.now(timezone.utc)
    _write(tmp_path, "samples.jsonl", [
        {"type": "sample", "kind": "bot", "instance_id": "inst-1",
         "at": (vstart + timedelta(hours=1)).isoformat(),
         "total_profit_usdc": str(-0.02 * funded + 30.0), "is_paper": True}])

    board = scripts_lab.board_rows()
    assert [r["origin"] for r in board] == ["NEX-0001", "OUR-0001"], board
    assert board[1]["pnl_pct"] > (board[0]["pnl_pct"] or -1e9), (
        "the fixture must have ours earning more, or the order proves nothing")
    said = scripts_lab.brief()
    assert "OUR-0001" in said and "question for him" in said, said


# --- V6: the manager wakes only when there is something to decide ----------

def _said(**over):
    base = {"at": NOW.isoformat(), "skipped": "", "morning_due": False,
            "errors": [], "held": [], "answered": [], "verdicts": 0,
            "resolved": 0, "may_ask": True, "why": ""}
    base.update(over)
    return base


def _tick_row(when, **over):
    return {"type": "tick", "at": when.isoformat(), "errors": [], "held": [],
            "verdicts": 0, "resolved": 0, "decide": [], **over}


def _decide(said, earlier=(), last_question=None, hour=14):
    return lab.decide(said, list(earlier), last_question, NOW, local_hour=hour)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_quiet_tick_decides_nothing_and_says_so_in_its_last_line(
        tmp_path, monkeypatch):
    """Plan v2, V6. The loop ran 35 firings a day at a median of 11 model
    calls each, every one on Opus (transcript 655b6244, 2026-09-20/21),
    because every firing read the brief, wrote the diary and composed a
    reply whatever the tick had found. The tick now says what, if anything,
    needs the manager -- and a firing that reads `decide: none` stops."""
    hour_ago = NOW - timedelta(hours=1)
    earlier = [_tick_row(hour_ago, decide=["hunt bugs"])]
    items = _decide(_said(), earlier, last_question=NOW - timedelta(minutes=30))
    assert items == [], items
    assert lab.decide_line(items) == "decide: none"

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    _write(tmp_path, "nexus.jsonl", [
        _question("NEX-0001", real_now - timedelta(minutes=30)),
        {"type": "answer", "id": "NEX-0001",
         "at": (real_now - timedelta(minutes=25)).isoformat(), "text": "..."}])
    lab.note_tick({"at": (real_now - timedelta(hours=1)).isoformat(),
                   "decide": ["hunt bugs"], "errors": [], "held": []})
    doors, _ = _doors()
    printed = []
    said = scripts_lab.tick(now=real_now, actions=doors, out=printed.append)
    assert printed[-1] == "decide: none", printed
    assert said["decide"] == [], said
    stored = [r for r in lab.load() if r.get("type") == "tick"][-1]
    assert stored["decide"] == [], "the next tick reads what this one decided"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_is_due_on_news_or_after_its_hours_not_on_every_tick():
    """Replayed over the 160 stored ticks, `may_ask` alone woke the manager
    on 97 of them -- and V5 took away the floor that had held it that low.
    A question is his memory of what happened (he remembers nothing), so it
    is due when something happened that he has not heard -- a verdict, a
    position that resolved -- or when QUESTION_HOURS passed without one."""
    asked = NOW - timedelta(minutes=40)
    # A hunt an hour ago, so an idle tick has nothing else to wake him for.
    hunted = _tick_row(NOW - timedelta(hours=1), decide=["hunt bugs"])
    assert _decide(_said(), [hunted], asked) == []
    later = NOW - timedelta(hours=lab.QUESTION_HOURS, minutes=1)
    assert _decide(_said(), [hunted], later) == ["question"]
    assert _decide(_said(), [hunted], None) == ["question"], (
        "never asked is due")
    # News since the last question, in this tick or an earlier one.
    assert _decide(_said(verdicts=1), [hunted], asked) == ["question"]
    verdict_after = _tick_row(NOW - timedelta(minutes=20), verdicts=2)
    assert _decide(_said(), [hunted, verdict_after], asked) == ["question"]
    verdict_before = _tick_row(NOW - timedelta(hours=1), resolved=1,
                               decide=["hunt bugs"])
    assert _decide(_said(), [verdict_before], asked) == [], (
        "news he already carried in the last question is not news")
    # Their pace still decides whether one may go at all.
    assert _decide(_said(may_ask=False, verdicts=1), [hunted], later) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_a_gap_and_the_report_wake_the_manager_in_that_order():
    """One line, every item that needs him, most urgent first: the morning
    report (V11 -- the 06:40 tick returns it), a gap to say to the operator,
    an answer that opened a room, a question."""
    items = _decide(_said(morning_due=True, answered=["NEX-0090"],
                          errors=["cycle: HTTP 502 from their side"]),
                    last_question=None)
    assert items == ["report", "gap", "answer NEX-0090", "question"], items
    assert lab.decide_line(items) == (
        "decide: report + gap + answer NEX-0090 + question")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_gap_is_what_went_wrong_for_the_first_time_not_every_tick():
    """A held reason is retried every tick and shown every tick, so "a gap"
    means first seen: a door that did not fail on the tick before, or a
    reason of the HTTP-error class no earlier tick carried. Replayed, that
    woke the manager 4 times in 160 ticks."""
    asked = NOW - timedelta(minutes=30)
    failing = _said(errors=["cycle: HTTP 502 from their side"])
    before = _tick_row(NOW - timedelta(minutes=20), decide=["hunt bugs"])
    assert _decide(failing, [before], asked) == ["gap"]
    still = _tick_row(NOW - timedelta(minutes=20), decide=["hunt bugs"],
                      errors=["cycle: HTTP 503 again"])
    assert _decide(failing, [still], asked) == [], "the same door, still down"

    refused = ("NEX-0088/5d91bf43: the paper order was not accepted "
               "(HTTP 409, no position returned)")
    assert _decide(_said(held=[refused]), [before], asked) == ["gap"]
    seen = _tick_row(NOW - timedelta(hours=3), held=[refused])
    assert _decide(_said(held=[refused]), [seen, before], asked) == []
    ordinary = "NEX-0083: names no card, bot or fund we can act on"
    assert _decide(_said(held=[ordinary]), [before], asked) == [], (
        "a proposal that names nothing is the morning's to read, not a gap")

    # RL04 (deep pass of 2026-09-24): the tick shows the newest six held lines,
    # and a gap line older than those six was never read -- while the gate
    # marks an unknown card spent, so it is written once and only once.
    unknown = "NEX-0091/9ef04dc6: their API knows no card 9ef04dc6"
    shown = [f"NEX-00{n}: variant held" for n in range(60, 66)]
    assert _decide(_said(held=shown, gap_held=[unknown]), [before], asked) == ["gap"]
    # RL01: a close their side refused is news the first time, and a close
    # that only waits for a deep pass is not news at all.
    refused_close = "STR-0009: P-1: the sell answered HTTP 500"
    assert _decide(_said(close_failed=[refused_close]), [before], asked) == ["gap"]
    told = _tick_row(NOW - timedelta(hours=1), close_failed=[refused_close])
    assert _decide(_said(close_failed=[refused_close]), [told, before], asked) == []
    waits = "STR-0009: a deep pass is running; the close waits for the next call"
    assert _decide(_said(close_failed=[waits]), [before], asked) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_idle_hunt_comes_every_few_hours_and_the_sweep_once_a_night():
    """The 2026-09-19 and 2026-09-20 decisions in laborator/SKILL.md: an idle
    tick hunts for bugs, and may run the sweep. Every idle tick doing that
    was most of the loop's cost; so a hunt is due HUNT_HOURS after the last
    one the tick asked for, the sweep is the first hunt of a local night, and
    nothing else due means nothing else."""
    asked = NOW - timedelta(minutes=30)
    assert _decide(_said(), [], asked, hour=14) == ["hunt bugs"]
    recent = _tick_row(NOW - timedelta(hours=3), decide=["hunt bugs"])
    assert _decide(_said(), [recent], asked, hour=14) == []
    old = _tick_row(NOW - timedelta(hours=lab.HUNT_HOURS, minutes=1),
                    decide=["hunt bugs"])
    assert _decide(_said(), [old], asked, hour=14) == ["hunt bugs"]
    assert _decide(_said(), [old], asked, hour=2) == ["hunt sweep"]
    swept = _tick_row(NOW - timedelta(hours=12), decide=["hunt sweep"])
    assert _decide(_said(), [swept, old], asked, hour=2) == ["hunt bugs"]
    # Anything else due, and the hunt waits: the manager is awake anyway.
    assert _decide(_said(), [old], None, hour=14) == ["question"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_while_a_deep_pass_runs_only_the_report_can_wake_the_manager():
    """The pass verifies #85-#87 over these very answers and trades; the
    tick that yields to it has nothing for the manager to decide but the
    report, which is read-only."""
    held = _said(skipped="pass", may_ask=False, answered=["NEX-0090"])
    assert _decide(held, last_question=None) == []
    assert _decide({**held, "morning_due": True}, last_question=None) == ["report"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_that_opened_a_room_is_named_by_the_tick(tmp_path, monkeypatch):
    """`answer NEX-...` comes from the launch itself: the answers that
    opened a room on THIS tick. One that named nothing is the morning's."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    real_now = datetime.now(timezone.utc)
    _write(tmp_path, "nexus.jsonl", [
        _question("NEX-0090", real_now - timedelta(minutes=10))])
    doors, _ = _doors(promote=lambda: {"rooms": 1, "orders": 1, "held": [],
                                       "answered": ["NEX-0090"]})
    printed = []
    said = scripts_lab.tick(now=real_now, actions=doors, out=printed.append)
    assert "answer NEX-0090" in said["decide"], said["decide"]
    assert printed[-1].startswith("decide: ") and "NEX-0090" in printed[-1]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_budget_decides_whether_an_idle_hunt_spends_an_agent():
    """V6: a hunt runs one Sonnet agent in the normal budget mode and none
    otherwise. The line is V7's: at 85 % of the week the deep pass goes
    minimal too, and the 5-hour window is held to the same number so a hunt
    does not take the operator's own afternoon."""
    assert lab.budget_mode(5, 35) == "normal"
    assert lab.budget_mode(lab.BUDGET_CEILING_PCT, 10) == "minimal"
    assert lab.budget_mode(10, lab.BUDGET_CEILING_PCT) == "minimal"
    assert lab.budget_mode(None, 10) == "minimal", (
        "a usage nobody could read is not room to spend")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tick_scans_their_surface_every_few_hours_for_the_session_start(
        tmp_path, monkeypatch):
    """Plan v2, V7 (E1): the session start reads the drift from a cache, and
    by day the loop's tick is what refreshes it -- once per surface_hours."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    doors, calls = _doors()
    _tick(scripts_lab, NOW, doors)
    _tick(scripts_lab, NOW + timedelta(minutes=20), doors)
    assert len(calls["surface_drift"]) == 1, calls["surface_drift"]
    later = NOW + timedelta(hours=scripts_lab.TICK["surface_hours"], minutes=1)
    _tick(scripts_lab, later, doors)
    assert len(calls["surface_drift"]) == 2
    assert "surface_drift" in scripts_lab._tick_doors()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_brief_carries_what_we_know_about_nexus(tmp_path, monkeypatch):
    """It lived in laborator/SKILL.md, loaded on every firing of the loop,
    while only a question needs it. V6 moved it here, into the one read
    every question makes."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    text = scripts_lab.brief()
    for known in ("QUERY_RESTRICTED", "#85", "#91", "#92",
                  "get_strategy_returns", "movers tournament"):
        assert known in text, (known, text[-2000:])
