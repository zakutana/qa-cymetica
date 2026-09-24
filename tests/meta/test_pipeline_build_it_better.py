"""The board check's reading, over the defect it was written for.

`test_a_spec_carries_every_line_of_the_request_it_answers` passes today, and a
check that has only ever passed is a check nobody has seen work. The pure half
is exercised here against the two shapes ET-26036 actually took on
2026-09-19 -- the truncated spec of 18:29:58 and the repaired one of 19:39:42
-- so the failing direction is driven without needing their server to be
broken again.

Verbatim from their own log, not paraphrased: a fixture that says roughly what
happened would agree with whatever the code does, which is the thing a test
written afterwards is for.
"""

from __future__ import annotations

import json

import pytest

from qa.marks import SafetyTier, qa

# The seven lines as filed, from the BB-REQUEST message of 18:29:58 UTC.
IMPROVEMENTS = "\n".join([
    "Free and clean: no paywall, no upsell, one plain page.",
    "CyMetica designs its own signal: a combination of technical analysis and "
    "classic indicators (e.g. Bollinger Bands, MACD, RSI). CyMetica chooses "
    "the combination and its parameters itself.",
    "Two versions of that signal, backtested on weekly charts: one "
    "historically successful 80%+ of the time, one 90%+.",
    "The page lists every crypto and stock whose weekly chart fires the "
    "signal right now.",
    "Two filters: 80%+ signal and 90%+ signal.",
    "For each listed asset show its own historical success rate, how many "
    "past signals that rate rests on, and the period tested.",
    "State on the page what counts as a success (how many weeks after the "
    "signal, and what price move), so the 80% and 90% can be checked.",
])

# What the generator produced first: eight sentences, so line 2 is cut at the
# full stop inside "(e.g. Bollinger Bands, MACD, RSI)" and line 7 never
# arrives at all.
TRUNCATED = """BB-SPEC for Tickeron

What we will build: a page on EventTrader that does the job you use Tickeron
for, with these changes. Each line is a check you can run on the live page:
  1. Free and clean: no paywall, no upsell, one plain page.
  2. CyMetica designs its own signal: a combination of technical analysis and
     classic indicators (e.g.
  3. Bollinger Bands, MACD, RSI).
  4. CyMetica chooses the combination and its parameters itself.
  5. Two versions of that signal, backtested on weekly charts: one historically successful 80%+ of the time, one 90%+.
  6. The page lists every crypto and stock whose weekly chart fires the signal right now.
  7. Two filters: 80%+ signal and 90%+ signal.
  8. For each listed asset show its own historical success rate, how many past signals that rate rests on, and the period tested.
"""

# And what it produces since the fix: a line is an item, nothing is cut, and
# the BB-CHANGE rides along as an addendum rather than replacing anything.
REPAIRED = """BB-SPEC for Tickeron

  1. Free and clean: no paywall, no upsell, one plain page.
  2. CyMetica designs its own signal: a combination of technical analysis and classic indicators (e.g. Bollinger Bands, MACD, RSI). CyMetica chooses the combination and its parameters itself.
  3. Two versions of that signal, backtested on weekly charts: one historically successful 80%+ of the time, one 90%+.
  4. The page lists every crypto and stock whose weekly chart fires the signal right now.
  5. Two filters: 80%+ signal and 90%+ signal.
  6. For each listed asset show its own historical success rate, how many past signals that rate rests on, and the period tested.
  7. State on the page what counts as a success (how many weeks after the signal, and what price move), so the 80% and 90% can be checked.

Your changes (BB-CHANGE) are part of the scope and override the list above:
  C2. Clicking an asset in the list opens its weekly chart with the signal's
  exact indicators and settings already drawn.
"""


def _load(filename: str, name: str):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "rest" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check():
    return _load("test_build_it_better_board.py", "bb_board")


class _Answer:
    """One response, as much of it as these checks read."""

    def __init__(self, status, body=None, text=None):
        self.status_code, self._body = status, body
        self.text = text if text is not None else json.dumps(body)

    def json(self):
        if self._body is None:
            raise ValueError("not JSON")
        return self._body


class _Board:
    """A `rest_anon` that answers from a dict keyed by path and has no
    network behind it at all: a path it was not given is a 404, so a check
    driven through it can never reach their server."""

    def __init__(self, answers: dict):
        self.answers = answers

    def get(self, path, params=None):
        return self.answers.get(path) or _Answer(404, {"detail": "not here"})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_board_check_sees_the_defect_it_was_written_for():
    """Both directions over the two specs ET-26036 really had."""
    bb = _check()

    assert len(bb.lines_of(IMPROVEMENTS)) == 7, bb.lines_of(IMPROVEMENTS)
    assert bb.lines_of("") == [] and bb.lines_of(None) == []
    assert bb.lines_of("a\n\n  \nb") == ["a", "b"], "a blank line is not an item"

    lost = bb.dropped(IMPROVEMENTS, TRUNCATED)
    assert len(lost) == 2, [line[:40] for line in lost]
    assert any(line.startswith("State on the page") for line in lost), (
        "the definition of success is the line the cap dropped, and the one "
        "without which 80% and 90% cannot be checked at all")
    assert any(line.startswith("CyMetica designs its own signal") for line in lost), (
        "the line cut at the full stop inside \"(e.g.\" is no longer whole "
        "anywhere in the spec, which is the whole of the claim")

    assert bb.dropped(IMPROVEMENTS, REPAIRED) == [], (
        "the repaired generator keeps every line whole")

    # Adding is not the defect: the addendum, the numbering and the standard
    # paragraphs are all additions, and the repaired spec carries all three.
    assert "C2." in REPAIRED and bb.dropped(IMPROVEMENTS, REPAIRED) == []

    # A spec that says the same thing in other words has changed the scope,
    # and a requester diffing by eye would not see it either.
    reworded = REPAIRED.replace("no paywall, no upsell", "without a paywall")
    assert bb.dropped(IMPROVEMENTS, reworded), (
        "a paraphrase is a different requirement from the one that was filed")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_waived_gate_is_the_spec_working_as_written():
    """The case the first version of this check could not see, and #108.

    ET-26036 really does carry `funded: false` and `raised_usd: 0.0` with the
    clock running -- and, three keys further into the SAME funding block,
    `waived: true`, `waived_at` equal to `clock_started_at` to the microsecond,
    and `waiver_reason: "Build it Better: requester holds 100+ ET10"`. The
    spec says "filled (or waived)". The product did exactly what it documents.

    A reading that stopped at `funded` called that a contradiction and #108
    went to the vendor saying the gate was "neither filled nor waived". It was
    waived. The probe that produced the evidence printed the funding block cut
    to 200 characters, and the cut fell three keys before the word that
    settles it.

    So the waived case is the first fixture here, not an afterthought: the
    real record, whole, has to read as no finding at all.
    """
    bb = _check()
    # ET-26036 as their server actually answers it.
    real = {
        "ticket": "ET-26036",
        "spec_text": "... " + bb.GATE_SENTENCE,
        "funding": {"microfund_id": 786, "goal_usd": 100.0, "raised_usd": 0.0,
                    "pct": 0, "backers": 0, "funded": False, "status": "open",
                    "expired": False, "waived": True,
                    "waived_at": "2026-09-19T20:25:59.571403+00:00",
                    "waiver_reason":
                        "Build it Better: requester holds 100+ ET10"},
        "clock_started_at": "2026-09-19T20:25:59.571403+00:00",
        "stage": "funded", "ready_to_build": True,
    }
    assert bb.clock_runs_unfunded(real) is None, (
        "the gate was waived because we hold 100+ ET10, which is exactly what "
        "the spec's \"(or waived)\" allows -- this is #108, and it was wrong")

    # The defect the check is FOR: neither filled nor waived, clock running.
    neither = {**real, "funding": {**real["funding"], "waived": False,
                                   "waived_at": None, "waiver_reason": None}}
    said = bb.clock_runs_unfunded(neither)
    assert said and said["waived"] is False, said
    assert said["raised_usd"] == 0.0 and said["goal_usd"] == 100.0

    assert bb.clock_runs_unfunded({**neither, "spec_text": "no such promise"}) is None, (
        "a spec that never claims the clock waits cannot contradict itself")
    assert bb.clock_runs_unfunded({**neither, "clock_started_at": None}) is None, (
        "a clock that has not started is the spec working as written")
    assert bb.clock_runs_unfunded(
        {**neither, "funding": {**neither["funding"], "funded": True}}) is None, (
        "a gate that IS filled is the spec working as written")
    assert bb.clock_runs_unfunded({**neither, "funding": None}) is None, (
        "no funding block is no reading, not a reading of zero -- rule 8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_request_whose_gate_was_never_read_is_not_evidence_either_way():
    """Absence was read as compliance, and the sentence said otherwise.

    `clock_runs_unfunded` returns None when `waived` is absent or the funding
    block is missing entirely -- correct, rule 8 -- but the ticket was still
    counted into `read`, so the PASS sentence "on N request(s) the clock
    starts only once the gate is filled or waived" covered requests whose
    funding state had never been read. A key emitted only when a waiver
    exists is the natural shape, so this is not a hypothetical.

    And the docstring's own headline, "and NOT BEFORE", was never measured:
    the evidence it quotes is a TIMESTAMP -- waived_at equal to
    clock_started_at to the microsecond -- while only the booleans were read.
    A clock that started thirty minutes before the waiver passed.
    """
    bb = _check()
    base = {"ticket": "ET-1", "spec_text": "... " + bb.GATE_SENTENCE,
            "clock_started_at": "2026-09-19T20:25:59.571403+00:00",
            "stage": "funded", "ready_to_build": True}

    for missing in ({"goal_usd": 100.0, "raised_usd": 0.0, "funded": False},
                    None, {}, "not a block"):
        assert bb.gate_state({**base, "funding": missing}) == "unread", (
            f"a funding block that never says whether the gate was waived is "
            f"a reading we did not take: {missing}")

    waived = {"goal_usd": 100.0, "raised_usd": 0.0, "funded": False,
              "waived": True, "waived_at": "2026-09-19T20:25:59.571403+00:00"}
    assert bb.gate_state({**base, "funding": waived}) == "honoured"

    early = {**waived, "waived_at": "2026-09-19T20:55:59.571403+00:00"}
    assert bb.gate_state({**base, "funding": early}) == "clock_ran_early", (
        "the clock started thirty minutes before the gate opened, which is "
        "the 'and not before' half of the sentence they ask us to lock")

    neither = {**waived, "waived": False, "waived_at": None}
    assert bb.gate_state({**base, "funding": neither}) == "clock_ran_unopened"

    assert bb.gate_state({**base, "funding": waived,
                          "clock_started_at": None}) == "not_started"
    assert bb.gate_state({**base, "spec_text": "no promise"}) == "no_claim"

    # The same defect one field over (deep pass of 2026-09-21, A19). A gate
    # that says it opened and not WHEN, or a clock whose start cannot be
    # read, gave `opened_at` or `began` None -- and the comparison then fell
    # through to "honoured". A missing time is not a time that was not
    # before; "and not before" is exactly what nobody measured.
    for funding, clock in (
            ({**waived, "waived_at": None}, base["clock_started_at"]),
            ({k: v for k, v in waived.items() if k != "waived_at"},
             base["clock_started_at"]),
            ({**waived, "waived_at": "not a time"}, base["clock_started_at"]),
            ({**neither, "funded": True}, base["clock_started_at"]),
            ({**neither, "funded": True, "funded_at": ""},
             base["clock_started_at"]),
            (waived, "not a time")):
        assert bb.gate_state({**base, "funding": funding,
                              "clock_started_at": clock}) == "unread", (
            f"a gate that opened at no readable moment, or a clock that "
            f"started at none, read as honoured: {funding}, clock {clock}")

    # Filled rather than waived carries `funded_at`, and that one is read.
    filled = {**neither, "funded": True,
              "funded_at": "2026-09-19T20:00:00+00:00"}
    assert bb.gate_state({**base, "funding": filled}) == "honoured"
    assert bb.gate_state({**base, "funding": {
        **filled, "funded_at": "2026-09-19T21:00:00+00:00"}}) == \
        "clock_ran_early"

    # And through the check itself, because a state the helper returns is
    # only a claim until the verdict is seen to follow it: one request,
    # waived at no stated moment, has to leave the check with nothing to say.
    from qa.marks import Inconclusive

    record = {**base, "funding": {**waived, "waived_at": None}}
    board = _Board({bb.BOARD: _Answer(200, {"items": [{"ticket": "ET-1"}]}),
                    f"{bb.BOARD}/ET-1": _Answer(200, record)})
    with pytest.raises(Inconclusive, match="no reading"):
        bb.test_the_spec_s_funding_gate_is_the_one_the_build_actually_waits_on(
            board)

    # And the verdict the check exists for quotes what it read. The row for
    # an early clock came from clock_runs_unfunded(), which answers only for a
    # gate neither filled nor waived, so it rendered "clock from None, None of
    # None USD raised, waived None" about a request whose record says waived.
    record = {**base, "funding": early}
    board = _Board({bb.BOARD: _Answer(200, {"items": [{"ticket": "ET-1"}]}),
                    f"{bb.BOARD}/ET-1": _Answer(200, record)})
    with pytest.raises(AssertionError) as said:
        bb.test_the_spec_s_funding_gate_is_the_one_the_build_actually_waits_on(
            board)
    for read in ("clock_ran_early", "2026-09-19T20:25:59", "waived True",
                 "2026-09-19T20:55:59"):
        assert read in str(said.value), (read, str(said.value))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_token_scan_would_find_a_token_and_not_a_coin_address():
    """A guard over a boundary that currently holds has to be shown working.

    The public read of a build carries 47 keys and none is a credential, so
    the check passes and will go on passing until the day it matters. The two
    ways it could be useless are both driven here: a word that LOOKS like a
    credential and is not (`token_address`, a coin's contract address, which
    is in every one of these payloads), and a real one nested where a shallow
    scan would miss it.
    """
    bb = _check()

    real = {"ticket": "ET-26036", "coin": {"token_address": None},
            "messages": [{"kind": "BB-SPEC", "body": "..."}]}
    assert bb.token_fields(real) == [], (
        "token_address is a contract address; flagging it would make the "
        "check cry wolf on every single request")

    leaked = {"ticket": "ET-1", "messages": [{"kind": "BB-REQUEST",
                                              "request_token": "bb_abc123"}]}
    assert bb.token_fields(leaked) == ["messages[0].request_token"], (
        bb.token_fields(leaked))
    assert bb.token_fields({"secret": "x"}) == ["secret"]
    assert bb.token_fields({"a": {"b": {"token": "x"}}}) == ["a.b.token"]

    # A leak under another name. The docstring promised "the word standing
    # alone or ENDING the key" and the code implemented the suffix for
    # `_secret` alone, so all four of these passed the scan that exists to
    # catch them -- and the verbatim fallback it names as the backstop does
    # not run at all on a machine with no key file.
    for key in ("owner_token", "access_token", "api_key", "build_password",
                "auth_bearer"):
        assert bb.token_fields({key: "bb_live_x"}) == [key], (
            f"{key} is a credential by its own name and passed the scan")

    # And the one that is not, which must stay out or the check cries wolf on
    # every single request: a coin's contract address.
    assert bb.token_fields({"coin": {"token_address": None}}) == []
    assert bb.token_fields({"public_key": "0xabc"}) == []

    # And the needle: the key file is a saved RESPONSE, so a scan that used
    # the whole file could never match. It reads the field or reports none.
    held = bb._our_token()
    assert held == "" or 8 <= len(held) <= 64, (
        f"the needle is not token-shaped: {len(held)} chars -- this is the "
        f"comparison that reported 'no leak' without ever being able to match")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_counters_are_counted_from_the_stage_field():
    """One request, one stage, and a board that today has a single item.

    With one item every counter is trivially satisfiable, so the reading is
    driven over a board that does not exist yet: several requests across
    several stages, and one carrying no stage at all. A counter that agreed
    with the list by accident would be a guard that goes green for years and
    then says nothing on the day the numbers drift.
    """
    bb = _check()

    assert bb.stage_counts([]) == {}
    assert bb.stage_counts(None) == {}
    assert bb.stage_counts([{"stage": "funded"}]) == {"funded": 1}

    many = [{"stage": "funded"}, {"stage": "funded"}, {"stage": "shipped"},
            {"stage": "requested"}, {"stage": None}, {}]
    assert bb.stage_counts(many) == {"funded": 2, "shipped": 1,
                                     "requested": 1}, bb.stage_counts(many)
    # A request with no stage is counted in `total` and in no stage, which is
    # what the check compares: len(items) against total, stages separately.
    assert sum(bb.stage_counts(many).values()) == 4 and len(many) == 6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_late_means_past_the_deadline_with_nothing_shipped():
    """Written while the one live build is still inside its window.

    ET-26036's deadline is 2026-09-20T20:25:59Z and this was written that
    morning, so the live check can only pass today whatever it does. The
    reading therefore has to be driven here, at both a before and an after,
    or the guard is one nobody has seen work until the night it matters.

    One way a build stops being late: a resolution time at or before its
    deadline. Until #112 a shipped url or a posted verdict did it too, and
    ET-26036 read as on time four hours after it missed its window. Since
    then a url or a verdict with no readable finish time proves only that
    something arrived, never when, so it reads `unreadable` -- neither late
    nor on time -- and a resolution after the deadline is `shipped_late`.
    """
    from datetime import datetime, timedelta, timezone

    bb = _check()
    deadline = datetime(2026, 9, 20, 20, 25, 59, tzinfo=timezone.utc)
    live = {"ticket": "ET-26036", "deadline_at": deadline.isoformat(),
            "stage": "funded", "our_url": None, "resolved_at": None,
            "verdict": None}

    inside = deadline - timedelta(hours=9)
    assert bb.overdue(live, inside) is None, "nine hours early is not late"

    after = deadline + timedelta(hours=2, minutes=30)
    said = bb.overdue(live, after)
    assert said and said["ticket"] == "ET-26036", said
    assert said["over_by_hours"] == 2.5, said["over_by_hours"]

    # A resolution INSIDE the window is the only one of the three that proves
    # the promise was kept. Repaired 2026-09-21: until then any one of these
    # returned None, so ET-26036 -- filed as #112 for passing its deadline
    # with nothing built -- read as compliant four hours later when they
    # shipped it, and a pass verdict on that report was one command away.
    assert bb.overdue({**live, "resolved_at": "2026-09-20T19:00:00+00:00"},
                      after) is None, (
        "a build resolved an hour before its deadline is not late")

    # A link or a verdict with no readable finish time proves only that
    # something arrived, never when. Not a breach and not compliance: named,
    # and kept out of the verdict by the caller (rule 8).
    for key, value in (("our_url", "https://cymetica.com/tools/signal9"),
                       ("verdict", "pass")):
        said = bb.overdue({**live, key: value}, after)
        assert said and said.get("unreadable"), (
            f"{key} set with no resolution time reads as a build that met its "
            f"deadline, and nothing here says when it arrived")
        assert not said.get("shipped_late"), said

    # Resolved AFTER the deadline is the night this was written for.
    late = bb.overdue({**live, "our_url": "https://cymetica.com/weekly-signal",
                       "resolved_at": "2026-09-21T00:25:27+00:00"}, after)
    assert late and late.get("shipped_late") and late["over_by_hours"] == 4.0, late

    assert bb.overdue({**live, "deadline_at": None}, after) is None, (
        "no published deadline is no promise to hold them to")
    assert bb.overdue({**live, "deadline_at": "not a date"}, after) is None, (
        "a deadline we cannot read is not a deadline that passed -- rule 8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_build_that_shipped_late_once_does_not_hold_the_verdict_red_for_good():
    """A10, deep pass of 2026-09-21: the board is a log that only grows.

    The 24-hour check judged every dated request the board has ever held.
    ET-26036 shipped four hours late and its record says so for good, so the
    check could never pass again whatever they ship on time from now on --
    "has a build ever been late" answered under a docstring that asks "does a
    build ship inside 24 hours". The shape of the two logs repaired on
    2026-09-10 (a-check-over-a-growing-log-can-never-go-green).

    A build shipped late is a finished event; a build past its deadline with
    nothing shipped is a live one, and they can still change it. So the
    verdict judges what settled inside the last day, and every request that
    is still overdue however old; what shipped before that is history, named
    in the population and never the verdict. A window with nothing settled in
    it is nothing measured (rule 10), not a promise kept.

    Considered folding this into `test_late_means_past_the_deadline_with_
    nothing_shipped`: it drives `overdue()` over one request at a time, and
    this defect is in which requests the check function hands to it, so it
    needs a board and the function itself.
    """
    from datetime import datetime, timedelta, timezone

    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    bb = _check()
    now = datetime.now(timezone.utc)

    def at(hours):
        return (now + timedelta(hours=hours)).isoformat()

    def run(*items):
        bb.test_a_build_ships_inside_the_24_hours_it_publishes(
            _Board({bb.BOARD: _Answer(200, {"items": list(items)})}))
        return CURRENT_MEASUREMENT.get()

    # ET-26036 as it stands a day on: missed its deadline, shipped late, and
    # the shipping was over a day ago. Beside it a build that shipped on time
    # this morning -- the promise, kept, inside the window.
    old_late = {"ticket": "ET-26036", "deadline_at": at(-30), "stage": "shipped",
                "our_url": "/weekly-signal", "resolved_at": at(-26),
                "on_time": False}
    on_time = {"ticket": "ET-2", "deadline_at": at(10), "stage": "shipped",
               "our_url": "/x", "resolved_at": at(-2), "on_time": True}
    said = run(old_late, on_time)
    assert said.verdict == "passed", said.reason
    assert "ET-26036" in said.reason, (
        "the late build left the verdict without being named as history: "
        + said.reason)
    assert "ET-26036" in str(said.population), said.population

    # History alone is nothing measured about the promise now.
    with pytest.raises(Inconclusive):
        run(old_late)
    # Neither is a board where nothing has reached its deadline yet, nor a
    # deadline that cannot be read as a date (rule 8).
    with pytest.raises(Inconclusive):
        run({"ticket": "ET-3", "deadline_at": at(5), "stage": "funded"})
    with pytest.raises(Inconclusive):
        run({"ticket": "ET-6", "deadline_at": "not a date", "stage": "funded"})

    # A build that shipped late inside the window still fails ...
    with pytest.raises(AssertionError, match="ET-4"):
        run({"ticket": "ET-4", "deadline_at": at(-6), "stage": "shipped",
             "our_url": "/y", "resolved_at": at(-2), "on_time": False},
            on_time)
    # ... and one past its deadline with nothing shipped fails however old
    # it is: that breach is still happening, it is not history.
    with pytest.raises(AssertionError, match="ET-5"):
        run({"ticket": "ET-5", "deadline_at": at(-72), "stage": "funded"},
            old_late, on_time)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_building_tile_is_judged_by_the_arithmetic_behind_its_name():
    """A15, deep pass of 2026-09-21: `nb` has no stage in it.

    The tile check reads the expression handed to `text($('bs-building'),
    ...)` and fails when it names a stage other than `building`. Written as
    `const nb = s.funded + s.building; text($('bs-building'), nb);` -- the
    same arithmetic, one line up -- it captured `nb`, found no stage word in
    it, and PASSED, while its docstring promises a pass only when the tile is
    `s.building` alone.

    So a bare name is followed once to its assignment, and whatever still
    cannot be read -- a name with no assignment, a second name, a call --
    is inconclusive: a rewritten front end is not evidence of a fix (its own
    docstring, and rule 8). No meta test drove this check before; there was
    nothing to fold it into.
    """
    from qa.marks import Inconclusive

    tile = _load("test_the_build_board_counts_building_as_building.py",
                 "bb_tile")

    def run(script):
        page = f"<html><body><script>{script}</script></body></html>"
        tile.test_the_boards_building_tile_counts_only_what_is_building(_Board({
            tile.BOARD_PAGE: _Answer(200, text=page),
            tile.API: _Answer(200, {"stats": {"building": 0, "funded": 1}})}))

    # The defect as measured, and the fix it asks for.
    with pytest.raises(AssertionError, match="funded"):
        run("function paint(s){ text($('bs-building'), "
            "(s.funded || 0) + (s.building || 0)); }")
    run("function paint(s){ text($('bs-building'), s.building || 0); }")

    # The same two, one name removed.
    with pytest.raises(AssertionError, match="funded"):
        run("function paint(s){ const nb = s.funded + s.building; "
            "text($('bs-building'), nb); }")
    run("function paint(s){ const nb = (s.building || 0); "
        "text($('bs-building'), nb); }")

    # A14, deep pass of 2026-09-22: only five stage names were looked for,
    # so a tile adding a stage nobody listed -- pending, in_progress -- passed
    # as counting nothing but what is building. Any other field is added.
    for other in ("pending", "in_progress"):
        with pytest.raises(AssertionError, match=other):
            run(f"function paint(s){{ text($('bs-building'), "
                f"(s.building || 0) + (s['{other}'] || 0)); }}")
    run("function paint(s){ text($('bs-building'), "
        "(s.building || 0).toLocaleString()); }")

    # And what cannot be read is not a pass.
    for script in (
            "function paint(s){ text($('bs-building'), nb); }",
            "function paint(s){ const a = s.funded + s.building; "
            "const nb = a; text($('bs-building'), nb); }",
            "function paint(s){ text($('bs-building'), countOf(s)); }"):
        with pytest.raises(Inconclusive):
            run(script)

    # A01/C04, deep pass of 2026-09-22 evening (3/3): a name was followed
    # only when it was the WHOLE expression, so a stage hidden in a local
    # beside s.building passed, and so did a call beside it. Every free name
    # in the expression is followed; a call whose body is elsewhere, or a
    # name with no assignment, is not read.
    with pytest.raises(AssertionError, match="funded"):
        run("function paint(s){ const nf = (s.funded || 0); "
            "text($('bs-building'), (s.building || 0) + nf); }")
    for script in (
            "function paint(s){ text($('bs-building'), "
            "(s.building || 0) + countOf(s)); }",
            "function paint(s){ text($('bs-building'), (s.building || 0) + nf); }"):
        with pytest.raises(Inconclusive):
            run(script)
    run("function paint(s){ text($('bs-building'), Number(s.building || 0)); }")

    # B05 (deep pass of 2026-09-24): the argument was read up to the first
    # `)` followed by `;`, so a correct tile in minified or semicolon-less
    # script took in the NEXT tile's stage -- a false regression on a
    # PASSING, FIX_CLAIMED row. Read to the call's own closing parenthesis.
    for script in (
            "function paint(s){text($('bs-building'),s.building||0),"
            "text($('bs-shipped'),s.shipped||0);}",
            "function paint(s){ text($('bs-building'), s.building || 0)\n"
            " text($('bs-funded'), s.funded || 0) }"):
        run(script)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_socket_named_by_its_path_or_with_a_trailing_slash_is_named():
    """A12, deep pass of 2026-09-21. The socket check wanted the page's
    absolute URL as a substring of each document, so a page writing
    `wss://cymetica.com/ws/build-it-better/` or a document naming
    `/ws/build-it-better` relative to the server it is served from read as a
    channel named nowhere -- a failure sentence about their documents that
    their documents contradict. No meta test drove this check before; there
    was nothing to fold it into.
    """
    import httpx

    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    sock = _load("test_socket_is_discoverable.py", "bb_socket")
    check = sock.test_a_socket_a_page_advertises_is_named_where_a_machine_reads

    def run(page_url, llms="", mcp="{}", openapi="{}"):
        board = _Board({
            "/build-it-better/api": _Answer(
                200, text=f'<script>new WebSocket("{page_url}")</script>'),
            "/llms.txt": _Answer(200, text=llms),
            "/.well-known/mcp.json": _Answer(200, text=mcp),
            "/openapi-public.json": _Answer(200, text=openapi)})
        board.base_url = httpx.URL("https://cymetica.com")
        CURRENT_MEASUREMENT.set(None)
        try:
            check(board)
            return "passed"
        except AssertionError:
            return "failed"
        finally:
            CURRENT_MEASUREMENT.set(None)  # not this meta test's own record

    live = "wss://cymetica.com/ws/build-it-better"
    # Named relative to the server the document is served from.
    assert run(live, llms="- Live feed: `/ws/build-it-better` (websocket)") == "passed"
    assert run(live, openapi='{"paths": {"/ws/build-it-better": {}}}') == "passed"
    # A trailing slash on either side is the same channel.
    assert run(live + "/", llms=f"- Live feed: `{live}`") == "passed"
    assert run(live, llms=f"- Live feed: {live}/ (websocket)") == "passed"
    assert run(live, llms=f"- Live feed: {live}.") == "passed"

    # And what is not the same channel is still not it.
    assert run(live, llms="- `/ws/build-it-better-v2`") == "failed"
    assert run(live, llms="- `/ws/build-it-better/admin`") == "failed"
    assert run(live, llms="- wss://elsewhere.example/ws/build-it-better") == "failed"
    assert run(live, llms="nothing about sockets") == "failed"
    # A socket on another host is not named by a bare path on this one.
    assert run("wss://other.example/ws/build-it-better",
               llms="- `/ws/build-it-better`") == "failed"

    # Rule 8 still holds: an unread document is not an omission.
    board = _Board({"/build-it-better/api": _Answer(200, text=live)})
    board.base_url = httpx.URL("https://cymetica.com")
    with pytest.raises(Inconclusive):
        check(board)
