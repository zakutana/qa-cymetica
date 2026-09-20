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


def _check():
    import importlib.util
    from pathlib import Path

    path = (Path(__file__).resolve().parents[1] / "rest"
            / "test_build_it_better_board.py")
    spec = importlib.util.spec_from_file_location("bb_board", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    # And the needle: the key file is a saved RESPONSE, so a scan that used
    # the whole file could never match. It reads the field or reports none.
    held = bb._our_token()
    assert held == "" or 8 <= len(held) <= 64, (
        f"the needle is not token-shaped: {len(held)} chars -- this is the "
        f"comparison that reported 'no leak' without ever being able to match")
