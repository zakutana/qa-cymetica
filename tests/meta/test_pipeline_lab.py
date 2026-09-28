"""The laboratory's brakes, in code rather than in the skill's prose.

A limit written in a skill is a limit the next session talks itself out of at
three in the morning. These are the ones that matter, each with the incident
behind it:

  * **paper only.** CLAUDE.md: Nexus's advice may not spend without `paper`. On
    2026-09-11 it asked us to send `mode=live` to prove the server would force
    paper back, and the answer was no.
  * **nothing while a deep pass is running.** The pass measures #85, #86 and
    #87 -- the newest Nexus answer, the last five questions, the newest trade.
    A question asked mid-run changes the subject the pass is verifying, and the
    verdict it sends the vendor is then about something else.
  * **a missing number is missing.** `get_strategy_returns` promises "a
    strategy with no runs returns a note, never a fabricated number". Ranking
    it as a zero would be us fabricating what they refused to.
  * **their pace, and the book's ceiling.** Nexus's own guide: an open-ended
    night "drifts, burns calls, and gives you no way to judge what it found".
    Our own caps on questions and rooms held that until V5 (2026-09-23); their
    hourly limit, their bound on outstanding jobs, their backoff and 60% of
    the book hold it now.

The tools the ground-truth lane calls are checked against components.yaml
rather than by calling them: a test that reaches the vendor to prove a
classification would be the thing the classification exists to stop.
"""

from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.safety import EndpointRegistry

REPO = Path(__file__).resolve().parent.parent.parent

TRUTH_TOOLS = ("list_backtest_surfaces", "get_backtest_models",
               "get_strategy_returns")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_ground_truth_tools_are_read_and_an_unknown_one_is_refused():
    """The lane Nexus's guide starts with, and the floor under it.

    Two of the three were absent from every list in components.yaml until
    2026-09-12, which means the transport refused them: 0 calls in the whole
    evidence store, to the first step of the loop the vendor themselves told us
    to run.
    """
    registry = EndpointRegistry.load()
    missing = [tool for tool in TRUTH_TOOLS
               if registry.tool_class(tool) != "read"]
    unknown_allowed = registry.tool_class("definitely_not_a_tool") != "unknown"

    conclude(Measurement(
        verdict="failed" if missing or unknown_allowed else "passed",
        reason=(f"{', '.join(missing)} is not classified read, so the "
                f"transport refuses it" if missing else
                "a tool nobody classified is served at SAFE"
                if unknown_allowed else
                "all three ground-truth tools are read, and an unlisted tool "
                "is not"),
        left={"tools": list(TRUTH_TOOLS)}, right={"missing": missing},
        sources={"floor": "components.yaml: mcp_tools.read"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_missing_sharpe_is_not_a_zero():
    ranked = lab.rank([
        {"strategy": "bt-cryptobull-blue", "sharpe": 5.16, "max_drawdown": 1.8},
        {"strategy": "bt-nothing-ran"},
        {"strategy": "bt-hybrid2-red", "sharpe": 2.81, "max_drawdown": 3.7},
        {"strategy": "bt-hybrid2-blue", "sharpe": 2.81, "max_drawdown": 1.7},
    ])
    assert [r["strategy"] for r in ranked[:3]] == [
        "bt-cryptobull-blue", "bt-hybrid2-blue", "bt-hybrid2-red"], ranked
    assert ranked[-1]["strategy"] == "bt-nothing-ran"
    assert "unranked" in ranked[-1], "a strategy with no runs is not a zero"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stamp_we_cannot_read_is_counted_against_the_cap():
    """Rule 8, on the side that spends.

    Both caps read `(_at(row["at"]) or since) > since`, so a row whose
    timestamp will not parse falls back to `since`, compares false, and is
    NOT counted -- an unreadable stamp quietly admitted a 25th question and
    an 11th room. `nexus.py record --at` takes the operator's free text
    straight into the diary, so producing one needs no bug at all.

    The safe direction here is the opposite of `_closed_on_their_side`: there
    a reading we did not take leaves money counted, and here it must leave a
    question counted. Both keep the brake on when we cannot see.
    """
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    rows = [{"type": "question", "at": (now - timedelta(hours=1)).isoformat()},
            {"type": "question", "at": "not a timestamp"},
            {"type": "question", "at": None},
            {"type": "question"}]
    assert lab.asked_within(rows, now) == 4, (
        "three of these carry no readable moment, and a cap that cannot see "
        "a question must assume it was asked inside the window")

    # A stamp that IS readable and outside the window still does not count.
    old = [{"type": "question", "at": (now - timedelta(hours=30)).isoformat()}]
    assert lab.asked_within(old, now) == 0

    rooms = [{"type": "strategy", "at": "nope"},
             {"type": "strategy", "at": (now - timedelta(hours=30)).isoformat()},
             {"type": "strategy", "at": (now - timedelta(hours=2)).isoformat()}]
    assert lab.rooms_within(rooms, now) == 2, (
        "the unreadable one and the recent one; the 30-hour-old one is out")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_they_gave_the_operator_does_not_pace_our_door():
    """Writing down what he said elsewhere must not arm a brake about them.

    `nexus.py record` exists so an answer the operator got on their website
    survives the next /clear. It writes a `question` row, and both the
    twenty-minute floor and the in-flight rule read every question row in the
    diary -- so recording one at 14:00 silently stopped the laboratory asking
    anything until 14:20, for a question that never used their door.

    The floor is about THEIR side: one question in flight so the pick-up is
    not split, and a pace their rate limit can carry. Neither is true of a
    conversation that happened in a browser. (Since V5, 2026-09-23, the floor
    and the in-flight rule are gone and the pace is their hourly limit; it
    reads our door the same way. The day's count went too; `asked_within`
    still counts "whoever asked them", for the brief.)

    Found by three readers on 2026-09-20, the day the command was written.
    """
    now = datetime(2026, 9, 20, 14, 0, tzinfo=timezone.utc)
    recorded = [{"type": "question", "id": "NEX-0100", "lane": "operator",
                 "at": now.isoformat()},
                {"type": "answer", "id": "NEX-0100", "lane": "operator",
                 "at": now.isoformat(), "text": "..."}]

    may, why = lab.may_ask_now(recorded, now)
    assert may, (
        f"an answer the operator pasted in put our own door behind a "
        f"twenty-minute floor: {why}")

    # The day's figure still counts it (said in the brief, no longer a cap).
    assert lab.asked_within(recorded, now) == 1, (
        "a question the operator put to them takes some of their time")

    # The floor and the in-flight rule went in V5 (2026-09-23); the pace that
    # holds now is their hour, and it too is about OUR door. Three recorded
    # from a browser inside the hour do not shut it; three of ours do --
    # answered, so it is the HOUR refusing and nothing else.
    browser = [{**row, "id": f"NEX-01{n}{row['type'][0]}"} for n in range(
        lab.ASKS_PER_HOUR) for row in recorded]
    browser = [{**row, "id": row["id"][:-1]} for row in browser]
    may, why = lab.may_ask_now(browser, now)
    assert may, why
    ours = []
    for n in range(lab.ASKS_PER_HOUR):
        ours += [{"type": "question", "id": f"NEX-020{n}", "at": now.isoformat()},
                 {"type": "answer", "id": f"NEX-020{n}", "at": now.isoformat(),
                  "text": "..."}]
    may, why = lab.may_ask_now(ours, now)
    assert not may and "hour" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_n_eff_collapses_toward_one_as_the_book_correlates():
    """Nexus's own leading indicator (2026-09-12, unprompted): "N_eff = N /
    (1 + (N-1)*rho) over the open book -- when average pairwise correlation
    crosses ~0.6-0.7 the breadth collapses and that precedes the drawdown."
    It is the only thing Nexus has told us about risk in the whole BOOK rather
    than in one card, and nothing built it. This is the pure formula; the
    laboratory's own wiring reads it off real index-history separately.
    """
    identical = {"a": [1.0, 2.0, 3.0, 4.0, 5.0],
                "b": [2.0, 4.0, 6.0, 8.0, 10.0]}
    said = lab.n_eff(identical)
    assert said["n"] == 2
    assert abs(said["rho"] - 1.0) < 1e-9
    assert abs(said["n_eff"] - 1.0) < 1e-9, (
        "two perfectly correlated positions are one position's worth of risk")

    orthogonal = {"a": [1.0, -1.0, 1.0, -1.0, 1.0],
                 "b": [1.0, 1.0, -1.0, -1.0, 1.0]}
    said = lab.n_eff(orthogonal)
    assert said["n"] == 2
    assert abs(said["rho"]) < 0.3, said
    assert said["n_eff"] > 1.7, (
        "near-uncorrelated positions should read as close to their own count")

    # Nexus's stated collapse zone, and this fixture was NOT in it: five
    # series, three rising and two falling, average pairwise rho -0.1966 and
    # n_eff 23.43 -- twenty-three independent bets out of five positions,
    # which is not a reading of anything. And `expected` was computed from
    # the function's OWN returned rho, so a rho that is not the average
    # pairwise correlation (the first pair only, say) passed unchanged.
    # Found by three readers on 2026-09-20.
    #
    # So: rho is computed here, independently, from the pairs; and a fixture
    # that really is in the zone is the one the collapse is read off.
    from itertools import combinations
    from statistics import correlation

    together = {"a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "b": [1.1, 2.2, 2.9, 4.3, 4.8, 6.4],
                "c": [1.2, 1.9, 3.3, 3.8, 5.2, 5.9],
                "d": [0.9, 2.1, 3.1, 3.9, 5.1, 6.1],
                "e": [1.3, 2.0, 3.2, 4.1, 4.9, 6.2]}
    said = lab.n_eff(together)
    assert said["n"] == 5

    pairs = [correlation(together[x], together[y])
             for x, y in combinations(sorted(together), 2)]
    mine = sum(pairs) / len(pairs)
    assert abs(said["rho"] - mine) < 1e-9, (
        f"rho has to be the AVERAGE PAIRWISE correlation Nexus named: the "
        f"ten pairs here average {mine:.4f} and the function said "
        f"{said['rho']:.4f}")
    assert mine > 0.6, (
        f"this fixture is supposed to sit in the collapse zone Nexus quoted, "
        f"and its average pairwise correlation is {mine:.4f}")
    assert said["n_eff"] < 2.0, (
        f"five positions correlated at {mine:.2f} are worth fewer than two "
        f"independent bets, which is the whole of what the indicator says; "
        f"n_eff read {said['n_eff']:.2f}")
    assert abs(said["n_eff"] - 5 / (1 + 4 * mine)) < 1e-9, "the formula"

    # And the other direction, computed the same way: a book that is not
    # correlated must not read as collapsed.
    apart = lab.n_eff(orthogonal)
    assert apart["n_eff"] > 1.7 > apart["rho"]

    # A gap is not a loss: fewer than two rooms, or a series too short to
    # correlate, is inconclusive -- never a fabricated 1.0 or a crash.
    assert lab.n_eff({}) == {
        "verdict": "inconclusive", "why": "fewer than two open positions"}
    assert lab.n_eff({"a": [1.0, 2.0, 3.0, 4.0, 5.0]}) == {
        "verdict": "inconclusive", "why": "fewer than two open positions"}
    short = lab.n_eff({"a": [1.0, 2.0], "b": [2.0, 4.0]})
    assert short["verdict"] == "inconclusive"
    assert "short" in short["why"] or "point" in short["why"], short

    # A perfectly flat series has no correlation to compute -- not an error,
    # not a fabricated 1.0 either.
    flat = lab.n_eff({"a": [3.0, 3.0, 3.0, 3.0, 3.0], "b": [1.0, 2.0, 3.0, 4.0, 5.0]})
    assert flat["verdict"] == "inconclusive", flat


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_position_resolved_without_us_is_read_from_the_samples(tmp_path):
    """The last unmeasured link: 'bet -> resolves -> paid'. A close WE sent is
    already measured (#87, TRD-0005); a card that resolves on its own has
    never been caught, because nothing compared what our book says is open
    against what their own sampled position status says.
    """
    paper_rows = [
        {"type": "intent", "id": "TRD-1", "card_id": "c1", "usdc": 10.0},
        {"type": "outcome", "id": "TRD-1", "outcome": "accepted",
         "position_id": "p1"},
        # p2 we closed ourselves -- must NOT be reported as resolved without us.
        {"type": "intent", "id": "TRD-2", "card_id": "c2", "usdc": 10.0},
        {"type": "outcome", "id": "TRD-2", "outcome": "accepted",
         "position_id": "p2"},
        {"type": "intent", "id": "TRD-3", "kind": "close", "position_id": "p2"},
        {"type": "outcome", "id": "TRD-3", "kind": "close", "outcome": "accepted"},
    ]
    sample_rows = [
        {"kind": "position", "at": "2026-09-13T10:00:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "open"},
        {"kind": "position", "at": "2026-09-13T10:00:00+00:00",
         "position_id": "p2", "card_id": "c2", "status": "open"},
        # p1 flips to closed with realised P&L and NO close event of ours.
        {"kind": "position", "at": "2026-09-13T16:00:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "closed",
         "realized_pnl_usdc": 4.2},
        {"kind": "position", "at": "2026-09-13T16:00:00+00:00",
         "position_id": "p2", "card_id": "c2", "status": "closed",
         "realized_pnl_usdc": -1.0},
    ]
    found = lab.resolved_without_us(paper_rows, sample_rows)
    assert [r["position_id"] for r in found] == ["p1"], found
    assert found[0]["card_id"] == "c1"
    assert found[0]["realized_pnl_usdc"] == 4.2
    assert found[0]["resolved_at"] == "2026-09-13T16:00:00+00:00"

    # Nothing yet closed: nothing to report, not an error.
    assert lab.resolved_without_us(paper_rows, sample_rows[:2]) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_down_streak_counts_only_their_side_breaking():
    """Duplicated from -- not sharing -- #86's own classifier
    (tests/mcp/test_nexus_channel.py::did_not_answer), on purpose: that
    function's fingerprint must not move for a reminder-side refactor (rule
    5). Same distinction, independent fixtures.
    """
    rows = [
        {"type": "question", "id": "NEX-1", "at": "2026-09-13T10:00:00+00:00"},
        {"type": "gave_up", "id": "NEX-1", "status": "failed"},
        {"type": "question", "id": "NEX-2", "at": "2026-09-13T11:00:00+00:00"},
        {"type": "gave_up", "id": "NEX-2", "status": "running"},
        {"type": "question", "id": "NEX-3", "at": "2026-09-13T12:00:00+00:00"},
        {"type": "gave_up", "id": "NEX-3", "status": "unknown: ReadTimeout"},
    ]
    assert lab.their_down_streak(rows) == 2, (
        "the newest give-up is OURS (a read failure), not theirs -- the "
        "streak is read from the tail and must not count it")

    rows[-1] = {"type": "gave_up", "id": "NEX-3", "status": "queued"}
    assert lab.their_down_streak(rows) == 3, (
        "a still-queued give-up at their own ceiling is their channel, not ours")

    answered = rows + [
        {"type": "question", "id": "NEX-4", "at": "2026-09-13T13:00:00+00:00"},
        {"type": "answer", "id": "NEX-4"}]
    assert lab.their_down_streak(answered) == 0, "one answer resets the streak"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_notebook_keeps_at_most_three_lessons_and_knows_an_open_session(
        tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import importlib

    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)

    # The number, not just "fewer than four". A07, deep pass of 2026-09-12,
    # triage 3/3: two of the three readers wrote MAX_LESSONS = 2 to disk and
    # watched this test pass. Everything else reads the constant --
    # scripts/lab.py truncates a night's lessons by it, and the assertion
    # further down this file says `<= lab.MAX_LESSONS` -- so a silent drop to
    # two was invisible while the name, close_session's docstring and
    # CLAUDE.md all said three, and a night would have lost a third of what
    # it learned. The same pattern as `stake_share_of_book == 0.0048` above.
    assert lab.MAX_LESSONS == 3

    opened = lab.open_session(mode="session")
    assert lab.open_sessions() == [opened["session"]]

    with pytest.raises(lab.LabError):
        lab.close_session(opened["session"],
                          lessons=["one", "two", "three", "four"], nextup=[])
    with pytest.raises(lab.LabError):
        lab.close_session("LAB-9999", lessons=[], nextup=[])

    # THREE is the boundary and the boundary is what a cap is. `> MAX_LESSONS`
    # read as `>=` refuses a night that produced exactly three, with a message
    # that contradicts itself -- "at most 3 lessons per session, not 3" -- and
    # the session stays open. Only four-raises and one-passes were asserted.
    lab.close_session(opened["session"], lessons=["one", "two", "three"],
                      nextup=["ask Nexus about STR-0001"])
    assert lab.open_sessions() == []
    assert lab.last_close()["next"] == ["ask Nexus about STR-0001"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_is_asked_while_a_deep_pass_is_running():
    """The asking half, and it says so in its name.

    It was `..._asked_or_bought_...` and exercised only `may_ask`. All three
    readers of 2026-09-12 deleted the buy interlock in `scripts/lab.py` and
    watched this stay green. No behaviour was unguarded -- the buying half is
    held by `test_the_buy_path_reads_what_is_already_deployed` below, by the
    AST guard that requires every spender to name `pass_in_flight`, and by
    `test_pipeline_night_spend.py::test_nothing_is_launched_while_a_deep_pass_is_running`
    -- so this is renamed rather than widened. A second assertion of the same
    interlock buys nothing; a name that claims one it does not make costs a
    reader their trust in every other name here. A04, triage 3/3.
    """
    may, why = lab.may_ask(pass_running=True)
    assert not may and "deep pass" in why.lower(), why

    may, _ = lab.may_ask(pass_running=False)
    assert may

    # V5 (2026-09-23): the day's count of 24 went, and what it protected --
    # an open-ended loop burning their calls -- is held by THEIR pace. Thirty
    # answered questions over the last day do not stop the next one; three
    # inside the hour do.
    now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    day = []
    for n in range(30):
        at = (now - timedelta(minutes=45 * (n + 2))).isoformat()
        day += [{"type": "question", "id": f"NEX-D{n}", "at": at},
                {"type": "answer", "id": f"NEX-D{n}", "at": at}]
    assert "questions_per_day" not in lab.CAPS
    may, why = lab.may_ask_now(day, now)
    assert may, why
    hour = day + [{"type": "question", "id": f"NEX-H{n}",
                   "at": (now - timedelta(minutes=10 * (n + 1))).isoformat()}
                  for n in range(lab.ASKS_PER_HOUR)]
    may, why = lab.may_ask_now(hour, now)
    assert not may and "hour" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_is_capped_at_a_share_of_what_is_free():
    """Raised 2026-09-12 from 6 experiments at 15% each to 50 at 2%.

    [operator 2026-09-12] *"musime testvoat aspon 50 strategii najednou"*. The
    reason is theirs and it is right for a reason they did not give: a verdict
    takes a five-to-seven-day window, so six at a time is six verdicts a week,
    and knowing which of Nexus's ideas pay needs dozens.

    The count is the weaker brake. Fifty at 2% is 100% of the book on paper, so
    a ceiling on what may be deployed AT ONCE is what actually holds -- there is
    always dry powder, and one bad night cannot take the whole book.
    """
    free = 89_000.0
    ok, why = lab.affordable(1_500, free_cash=free, running=2)
    assert ok, why

    ok, why = lab.affordable(10_000, free_cash=free, running=2)
    assert not ok and "2" in why, why

    # V5 (2026-09-23): the count caps went -- 125 running, 25 new a day. A
    # running count is no refusal now; what holds is the 60% ceiling below,
    # and it binds on the book, not on a number of rooms.
    ok, why = lab.affordable(1_000, free_cash=free, running=10_000)
    assert ok, why
    for gone in ("running_experiments", "new_rooms_per_day"):
        assert gone not in lab.CAPS, f"{gone} is still a cap of ours"
    # The stake that replaced the count, pinned by value like the others: a
    # FIXED 0.48% of the book, so the ceiling alone stops the count at 125 --
    # "aspoň 50" is the operator's floor and 125 keeps it. `>= 50`-style pins
    # survived 10**6 once (reader 1 of the deep pass of 2026-09-21), so the
    # value itself, and moving it is an edit HERE too.
    assert lab.CAPS["stake_share_of_book"] == 0.0048
    assert round(lab.CAPS["total_exposure"] / lab.CAPS["stake_share_of_book"]) >= 50

    # THE CAP ITSELF, by name and by boundary. L04, deep pass of 2026-09-13,
    # triage 3/3: this test used to pin only the rendering. Three readers set
    # `share_of_free_cash` to 0.03, 0.07 and 0.08 in turn and every test in
    # this file stayed green, because `"2" in why` is satisfied by the digit
    # inside "(7120)" -- at 0.08 a night would stake 7 120 USDC of 89 000 free
    # where the operator agreed to 1 780. The file already pins MAX_LESSONS
    # and running_experiments by name for exactly this reason; this was the
    # one cap of the four that moves money and it was the one left loose.
    assert lab.CAPS["share_of_free_cash"] == 0.02, (
        "the per-experiment share is the operator's own number (2% of what is "
        "free); changing it is a conversation, not an edit")

    # And the boundary is measured, not inferred from the constant: 2% of
    # 89 000 is 1 780, so 1 780 is affordable and one cent more is not.
    assert lab.affordable(1_780.0, free_cash=free, running=2)[0]
    assert not lab.affordable(1_780.01, free_cash=free, running=2)[0]

    ok, why = lab.affordable(1_000, free_cash=free, running=5,
                             deployed=free * 2.0)
    assert not ok and "60" in why, why
    ok, why = lab.affordable(1_000, free_cash=free, running=5,
                             deployed=free * 0.30)
    assert ok, why

    ok, why = lab.affordable(1_000, free_cash=None, running=0)
    assert not ok and "could not" in why.lower(), (
        "an unreadable book is not an empty one -- rule 8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_exposure_ceiling_is_a_share_of_the_book_not_of_the_remainder():
    """60% of total exposure is 60% of the book, not 60% of what is left.

    Measured against what is still free, the ceiling walks down as we deploy:
    `d <= 0.6*(free)` with `free = B - d` solves to `d <= 0.375*B`, so a limit
    written as 60% bound at 37.5% and the refusal said "60% of the 89000 free"
    while meaning something else. The plan the operator approved says *max 60 %
    celkove expozice* -- exposure is what is out over the whole book.

    The case below separates the two: 55k out of a 100k book is under the
    ceiling and over 60% of the 45k that remains.
    """
    book, deployed = 100_000.0, 55_000.0
    ok, why = lab.affordable(500, free_cash=book - deployed, running=2,
                             deployed=deployed)
    assert ok, why
    assert "100000" in why.replace(",", ""), (
        f"the reason has to name the book it measured against: {why}")

    deployed = 59_800.0
    ok, why = lab.affordable(500, free_cash=book - deployed, running=2,
                             deployed=deployed)
    assert not ok and "60" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_closing_a_session_puts_the_diaries_where_git_can_hold_them(
        tmp_path, monkeypatch):
    """The laboratory's five diaries are gitignored, so the copy in audits/lab/
    is the only one that survives this machine.

    `keep.py snapshot` was written 2026-09-12 08:19 and its only caller was the
    deep pass, whose trigger is the operator saying "jdu spat". So a whole day
    of laboratory work -- on 2026-09-12, every row the laboratory had -- sat on
    one untracked disk until they happened to go to bed. That is not a broken
    mechanism; it is a mechanism with one trigger, in the wrong place for data
    that finalises at the end of a session.

    Both ends are checked: the `close` subcommand and the close a tick makes
    of yesterday's session. The tick's matters more -- since `lab.py night`
    was removed (2026-09-21) it is the only close nobody is watching, at the
    end of a day the loop wrote all of.

    The archive is stubbed here so the assertion is about the CALL. That it
    writes beside the state it archives, rather than into this repository, is
    test_the_archive_follows_the_state_it_archives below -- which is the bug
    this very call introduced: the suite ran, night() archived a tmp_path, and
    the committed audits/lab/lab.jsonl came back modified.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    # No pass running: the notebook read is REPO_ROOT/audits, and a real
    # pass in flight holds the archive back (RL03) -- tested in
    # test_the_buy_path_reads_what_is_already_deployed.
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    calls = []
    real_sibling = scripts_lab._sibling

    class _Keep:
        @staticmethod
        def snapshot():
            calls.append("snapshot")
            return ["lab.jsonl"]

    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda name: _Keep if name == "keep"
                        else real_sibling(name))

    lab.open_session(mode="session")
    scripts_lab.main(["close", "--lesson", "one", "--next", "two"])
    assert calls == ["snapshot"], (
        "the session closed and its diaries stayed on a single disk")

    calls.clear()
    now = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
    lab._append({"type": "session", "state": "open", "session": "LAB-0901",
                 "mode": "loop", "day": "2026-09-12",
                 "at": (now - timedelta(days=1)).isoformat()})
    stub = lambda *a: {}  # noqa: E731 -- every door a tick reaches, inert
    doors = {name: stub for name in scripts_lab._tick_doors()}
    doors.update({"pass": lambda: False, "night": lambda: False,
                  "asked_today": lambda: 0, "moves": lambda: [],
                  "refill": lambda: [], "truth": lambda: [],
                  "verdicts": lambda: []})
    monkeypatch.setattr(scripts_lab, "_record_resolved", lambda: [])
    scripts_lab.tick(now=now, actions=doors, out=lambda *a: None)
    assert lab.last_close()["session"] == "LAB-0901", "yesterday stayed open"
    assert calls == ["snapshot"], (
        "the loop wrote all day, closed the day, and archived none of it")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_archive_follows_the_state_it_archives(tmp_path, monkeypatch):
    """A test run must never be able to overwrite the committed archive.

    `SNAPSHOT_DIR` was `REPO_ROOT / "audits" / "lab"`, fixed at import, while
    the source was `state_dir()`, which every test redirects. The hour a caller
    was added to `lab.py close`, the suite ran, the night test closed its
    session, and the repository's own audits/lab/lab.jsonl came back holding a
    tmp_path's rows. The archive of the laboratory's whole history is exactly
    the file that must not be writable by a passing test.

    So it is derived from the state it copies: the real state dir's parent IS
    the repository, and anything else lands beside itself.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import importlib
    import importlib.util

    import qa.state
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "scripts_keep_under_test", REPO / "scripts" / "keep.py")
    keep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(keep)

    (tmp_path / "lab.jsonl").write_text('{"type":"open"}\n', encoding="utf-8")
    copied = keep.snapshot()

    assert copied == ["lab.jsonl"], copied
    target = keep.snapshot_dir()
    assert target == tmp_path.parent / "audits" / "lab", (
        f"the archive went to {target}, not beside the state it archives")
    assert REPO not in target.parents and target != REPO / "audits" / "lab", (
        "a test just wrote into the repository's committed archive")
    assert (target / "lab.jsonl").read_text(encoding="utf-8").strip() == \
        '{"type":"open"}'


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_free_cash_reader_takes_their_decimal_strings(tmp_path, monkeypatch):
    """Their balances arrive as strings, and this reader demanded numbers.

    `sim_balance_usdc` is `"89000.96"` -- a string -- in every `after` row we
    have ever written, while `_free_cash` accepted only int or float. So it
    returned None every time, `affordable` refused with "the book could not be
    read", and `lab.py buy` has never once placed an order. The trades on the
    book came through `paper.py` directly, before the lab existed.

    Failing closed is why nobody noticed, and no test of the caps ever read a
    real row: they all called the pure function with a float. `paper.py` has
    coerced this same field with `float()` since it was written.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    book = tmp_path / "paper.jsonl"

    book.write_text(json.dumps(
        {"type": "after", "id": "TRD-0001",
         "sim_balance_usdc": "89000.96"}) + "\n", encoding="utf-8")
    assert scripts_lab._free_cash() == pytest.approx(89_000.96)

    book.write_text(json.dumps(
        {"type": "after", "id": "TRD-0001",
         "sim_balance_usdc": "not a number"}) + "\n", encoding="utf-8")
    assert scripts_lab._free_cash() is None, (
        "an unparseable balance is unreadable, never a zero -- rule 8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_buy_path_reads_what_is_already_deployed(tmp_path, monkeypatch):
    """The ceiling has to hold where the order actually goes out.

    `deployed` reached `affordable` only from the unit test: `buy()` left it at
    its default of zero, so the brake N4's commit called the one that actually
    holds was dead on the single path that spends. Review found it after the
    commit; nothing in the suite could, because every test of the ceiling called
    the pure function directly.

    The order is stubbed rather than allowed to go out: a negative control that
    needs the refusal to work is not a control.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    rows = [
        {"type": "intent", "id": "TRD-0001", "card_id": "c1", "usdc": 29_900.0},
        {"type": "outcome", "id": "TRD-0001", "outcome": "accepted",
         "position_id": "p1"},
        {"type": "intent", "id": "TRD-0002", "card_id": "c2", "usdc": 29_900.0},
        {"type": "outcome", "id": "TRD-0002", "outcome": "accepted",
         "position_id": "p2"},
        {"type": "intent", "id": "TRD-0003", "card_id": "c3", "usdc": 5_000.0},
        {"type": "outcome", "id": "TRD-0003", "outcome": "refused"},
        {"type": "after", "id": "TRD-0003", "sim_balance_usdc": "40200.00"},
    ]
    book = tmp_path / "paper.jsonl"
    book.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    assert scripts_lab._deployed() == 29_900.0 * 2, (
        "a refused order was never out; two accepted ones are")

    sent = []
    real_sibling = scripts_lab._sibling
    paper = real_sibling("paper")
    paper.buy = lambda *a, **k: sent.append(a) or {
        "outcome": "accepted", "http_status": 200, "position_id": "pos-stub"}
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda name: paper if name == "paper"
                        else real_sibling(name))

    # The pass notebook is REPO_ROOT/audits, not state_dir, so without this the
    # money assertions below would read a real deep pass and get its refusal
    # instead -- turning tests/meta red mid-pass, which aborts the pass. The
    # interlock gets its own assertion at the end rather than being lost here.
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)

    with pytest.raises(SystemExit) as refused:
        scripts_lab.buy("c4", 500.0, nexus_id=None, confirm=True)
    assert "60" in str(refused.value), str(refused.value)
    assert sent == [], "it refused and sent the order anyway"

    with book.open("a", encoding="utf-8") as handle:
        for row in ({"type": "intent", "id": "TRD-0004", "kind": "close",
                     "position_id": "p2", "notional_usdc": 29_900.0},
                    {"type": "outcome", "id": "TRD-0004", "kind": "close",
                     "outcome": "accepted"},
                    {"type": "after", "id": "TRD-0004",
                     "sim_balance_usdc": "70100.00"}):
            handle.write(json.dumps(row) + "\n")

    assert scripts_lab._deployed() == 29_900.0, "a closed position is not out"
    scripts_lab.buy("c4", 500.0, nexus_id=None, confirm=True)
    assert len(sent) == 1, "room under the ceiling and it still refused"

    # The same defect this test exists for, one line up the same function:
    # `may_ask(pass_running=...)` is tested as a pure function and nothing
    # checked that `buy` consults the interlock at all.
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: True)
    with pytest.raises(SystemExit) as held:
        scripts_lab.buy("c4", 500.0, nexus_id=None, confirm=True)
    assert "deep pass" in str(held.value), str(held.value)
    assert len(sent) == 1, "a deep pass was running and the order went anyway"

    # RL03 (deep pass of 2026-09-24): the first tick after midnight UTC
    # closes the day, and closing it copied the diaries into the TRACKED
    # audits/lab/ -- before the tick's pass guard. A dirty tree mid-pass is
    # one its preregistration refuses; the pass's step 8 archives them.
    snapped = []
    keep = real_sibling("keep")
    keep.snapshot = lambda: snapped.append(1) or ["audits/lab/lab.jsonl"]
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda name: keep if name == "keep"
                        else paper if name == "paper" else real_sibling(name))
    assert scripts_lab._archive_diaries() == [] and snapped == [], (
        "the day's close wrote tracked files while a deep pass was running")
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    assert scripts_lab._archive_diaries() and snapped == [1]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_position_they_say_is_closed_is_not_still_deployed(tmp_path,
                                                             monkeypatch):
    """Our book is not the only way a position closes.

    2026-09-12: the operator closed a paper card on their website by hand -- a
    10 000 USDC position, +85.76 realised. Nothing wrote that to `paper.jsonl`,
    because `paper.jsonl` records OUR orders, so `_deployed` went on counting
    10 000 USDC as out and the 60% ceiling was measured against money that had
    already come home. The memory is
    `the-journal-records-our-pipeline-not-the-operator`; this is the same
    sentence about the book.

    The sampler already reads their side every ten minutes and writes the
    answer down, so the closure is on this machine -- it was simply never read.

    Both directions, because the safe one is not obvious: an explicit `closed`
    from them releases the money, and NO row at all does not. A position they
    have not described is one we know nothing new about, and rule 8 says a
    reading we did not take is not a reading of zero -- keeping it counted
    understates our headroom, which is the direction that cannot overspend.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    rows = [
        {"type": "intent", "id": "TRD-0001", "card_id": "c1", "usdc": 10_000.0},
        {"type": "outcome", "id": "TRD-0001", "outcome": "accepted",
         "position_id": "p1"},
        {"type": "intent", "id": "TRD-0002", "card_id": "c2", "usdc": 1_000.0},
        {"type": "outcome", "id": "TRD-0002", "outcome": "accepted",
         "position_id": "p2"},
    ]
    (tmp_path / "paper.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    assert scripts_lab._deployed() == 11_000.0, (
        "with nothing read from their side, both positions are still out")

    samples = [
        # Their first look: both open. Then p1 closes on the website.
        {"type": "sample", "kind": "position", "at": "2026-09-12T20:00:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "open"},
        {"type": "sample", "kind": "position", "at": "2026-09-12T20:00:00+00:00",
         "position_id": "p2", "card_id": "c2", "status": "open"},
        {"type": "sample", "kind": "position", "at": "2026-09-12T22:00:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "closed",
         "realized_pnl_usdc": 85.75958},
    ]
    (tmp_path / "samples.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in samples), encoding="utf-8")

    assert scripts_lab._deployed() == 1_000.0, (
        "their own record says p1 is closed and ours never heard about it")

    # The newest row wins, not any row: a position that closed and was opened
    # again is out again, and reading "closed" anywhere in the history would
    # release money that is genuinely at risk.
    with (tmp_path / "samples.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(
            {"type": "sample", "kind": "position",
             "at": "2026-09-12T23:00:00+00:00", "position_id": "p1",
             "card_id": "c1", "status": "open"}) + "\n")
    assert scripts_lab._deployed() == 11_000.0, (
        "the newest reading of a position is the one that counts")

    # A buy that timed out is written `unknown`, and it may have landed: the
    # sampler then reads a position of its card that no accepted order of
    # ours claims. That money is out, under the ceiling like the rest; it was
    # left out of `_deployed` (deep pass 2026-09-27, L01, 3/3). A 4xx is their
    # refusal and nothing landed.
    with (tmp_path / "paper.jsonl").open("a", encoding="utf-8") as handle:
        for row in ({"type": "intent", "id": "TRD-0003", "card_id": "C3", "usdc": 700.0},
                    {"type": "outcome", "id": "TRD-0003", "outcome": "unknown",
                     "error": "ReadTimeout"},
                    {"type": "intent", "id": "TRD-0004", "card_id": "c4", "usdc": 900.0},
                    {"type": "outcome", "id": "TRD-0004", "outcome": "unknown",
                     "http_status": 409}):
            handle.write(json.dumps(row) + "\n")
    assert scripts_lab._deployed() == 11_000.0, "nothing of c3 is listed yet"
    with (tmp_path / "samples.jsonl").open("a", encoding="utf-8") as handle:
        for pid, card in (("p3", "c3"), ("p4", "c4")):
            handle.write(json.dumps(
                {"type": "sample", "kind": "position", "at": "2026-09-13T01:00:00+00:00",
                 "position_id": pid, "card_id": card, "status": "open"}) + "\n")
    assert scripts_lab._deployed() == 11_700.0, (
        "an unknown buy whose position they list is money out; a 409 is not")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_simulation_reset_takes_our_older_positions_with_it(tmp_path,
                                                             monkeypatch):
    """Their simulation can be restarted, and a restart is not a close.

    `sim_balance.started_at` moved to 13:31:55 on 2026-09-10, after TRD-0001
    (11:41) and TRD-0002 (11:59) were accepted. Their own `total_trades` read
    4 where our book held 6: the two older orders do not exist on their side
    any more. Nothing ever closes them -- no close of ours, no `closed` row
    from the sampler, because the positions are gone rather than closed -- so
    they sit in `_deployed()` for ever and every later reset adds two more.
    Today that is 2 USDC of a 99 000 book; the defect is that it only grows,
    and it inflates the numerator of the 60% exposure ceiling.

    The safe direction is the opposite one from `_closed_on_their_side`: there,
    silence keeps money counted. Here we have a POSITIVE reading from their
    side -- a start time after the order -- so dropping it is reading what they
    said, not assuming. With no `sim_started_at` anywhere, nothing is dropped.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    rows = [
        {"type": "intent", "id": "TRD-0001", "card_id": "c1", "usdc": 1.0,
         "at": "2026-09-10T11:41:45+00:00"},
        {"type": "outcome", "id": "TRD-0001", "outcome": "accepted",
         "position_id": "p1", "at": "2026-09-10T11:41:48+00:00"},
        {"type": "intent", "id": "TRD-0002", "card_id": "c2", "usdc": 1.0,
         "at": "2026-09-10T11:59:32+00:00"},
        {"type": "outcome", "id": "TRD-0002", "outcome": "accepted",
         "position_id": "p2", "at": "2026-09-10T11:59:35+00:00"},
        {"type": "intent", "id": "TRD-0003", "card_id": "c3", "usdc": 500.0,
         "at": "2026-09-10T20:06:05+00:00"},
        {"type": "outcome", "id": "TRD-0003", "outcome": "accepted",
         "position_id": "p3", "at": "2026-09-10T20:06:08+00:00"},
    ]
    book = tmp_path / "paper.jsonl"
    book.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    assert scripts_lab._deployed() == 502.0, (
        "with no start time read from them, every accepted order is still out")

    with book.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(
            {"type": "after", "id": "TRD-0003",
             "at": "2026-09-10T20:06:11+00:00",
             "sim_started_at": "2026-09-10T13:31:55.163793+00:00"}) + "\n")

    assert scripts_lab._deployed() == 500.0, (
        "the two orders older than their own simulation are ghosts")

    # An unreadable start time is not a start time. It must not release
    # anything, the way an unreadable sample does not.
    book.write_text("".join(json.dumps(r) + "\n" for r in rows)
                    + json.dumps({"type": "after", "id": "TRD-0003",
                                  "sim_started_at": "not a date"}) + "\n",
                    encoding="utf-8")
    assert scripts_lab._deployed() == 502.0, (
        "a start time we could not read released money anyway")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_night_searches_on_its_own_clock_not_the_question_clock():
    """Two clocks, because a backtest is free and a question is not.

    The night ran backtests every six hours -- twice a night -- and asked every
    two. That is the timidity the operator went after: *"celou noc budete delat
    backtesty nonstop"*. A search tick is bounded by their 30/min and by
    nothing else; only a deep pass stops it, for the reason every other tick
    stops.
    """
    now = datetime(2026, 9, 13, 2, 0, tzinfo=timezone.utc)
    state = {"asked": 0, "candidates": ["bt-x"], "pending": 40,
             "last_cycle": now, "last_truth": now, "last_ask": now}

    plan = lab.night_tick(state, now)
    assert "search" in plan["do"], (
        "nothing else was due and the search sat idle anyway")

    held = lab.night_tick({**state, "hold_until": now + timedelta(hours=3)}, now)
    assert "search" in held["do"], "their backoff is about questions, not reads"

    passing = lab.night_tick({**state, "pass_running": True}, now)
    assert passing["do"] == [] and passing["skipped"] == "pass"

    done = lab.night_tick({**state, "pending": 0}, now)
    assert "search" not in done["do"], "nothing left to walk"

    # The question floor is gone altogether (V5, 2026-09-23; two hours, then
    # twenty minutes): their side sets the pace -- ASKS_PER_HOUR, read off the
    # diary by may_ask_now -- so a question five minutes after the last is
    # not held here.
    assert "ask_seconds" not in lab.NIGHT
    soon = lab.night_tick({**state, "last_ask": now - timedelta(minutes=5)}, now)
    assert "ask" in soon["do"], soon


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_with_no_answer_is_what_the_next_cycle_finishes():
    """A foreground ask is killed at ten minutes by the tool that runs it,
    while nexus.py waits fifteen. The question is on their server either way;
    what is missing is our end of it, and the cycle is what closes that."""
    from datetime import datetime, timezone

    now = datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc)
    rows = [
        {"type": "question", "id": "NEX-0030", "at": "2026-09-12T06:00:00+00:00"},
        {"type": "answer", "id": "NEX-0030", "at": "2026-09-12T06:03:00+00:00"},
        {"type": "question", "id": "NEX-0031", "at": "2026-09-12T07:00:00+00:00"},
        {"type": "poll", "id": "NEX-0031", "at": "2026-09-12T07:01:00+00:00",
         "status": "running"},
        # Asked with --no-wait on the 10th and never picked up. Their
        # investigations take one to five minutes; this job id is gone, and a
        # cycle that polls it for ever is a loop that cannot finish.
        {"type": "question", "id": "NEX-0013", "at": "2026-09-10T21:50:00+00:00"},
    ]
    assert lab.outstanding(rows, now=now) == ["NEX-0031"]


def _series(start: str, values, hours: float = 1.0):
    """A card's index history: their shape, `[{t, index}, ...]`."""
    from datetime import datetime, timedelta, timezone

    first = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    return [{"t": (first + timedelta(hours=hours * i)).isoformat(),
             "index": float(value)} for i, value in enumerate(values)]


def _acceptance(**over):
    base = {
        "at": "2026-09-05T00:00:00+00:00",
        "window_days": 2,
        "stop_pct": 5.0,
        "legs": [{"card": "card-a", "side": "bull", "share": 1.0,
                  "tp": 8.0, "sl": -5.0}],
        "benchmark_card": None,
    }
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_strategy_that_made_money_inside_its_stop_survives():
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 101, 102, 103, 104], hours=12)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "survived", said
    # Five points twelve hours apart over a two-day window: the last one falls
    # exactly on the closing edge and is inside it. This test said 3.0 first,
    # from counting four steps and assuming the edge was exclusive -- the code
    # was right and the expectation was not. Since V2 (2026-09-23) a card leg
    # pays the live round trip, 1.4%, on what it made.
    (leg,) = said["legs"]
    assert round(leg["gross_return_pct"], 2) == 4.0, said
    assert said["return_pct"] == pytest.approx((1.04 * 0.986 - 1) * 100), said
    assert said["max_drawdown_pct"] <= 5.0
    assert said["formula"], "a verdict records the formula that produced it"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_drawdown_is_measured_from_the_peak_not_in_points_of_return():
    """C8 of the 2026-09-23 review (3/3). The drawdown was the fall in
    PERCENTAGE POINTS of return -- +50% to +20% read as 30 -- where a holder
    at 150 who is now at 120 has lost 20% from the peak. Against a 25% stop
    the points reading refuted a room that never breached it, early and at
    the close alike."""
    legs = [{"card": "card-a", "side": "bull", "share": 1.0}]
    accepted = _acceptance(legs=legs, stop_pct=25.0)
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 150, 120, 120, 120], hours=12)}

    inside = lab.verdict(accepted, series, "2026-09-06T01:00:00+00:00")
    assert inside["verdict"] == "open", (
        "a 20% fall from the peak was read as past a 25% stop", inside)

    closed = lab.verdict(accepted, series, "2026-09-07T01:00:00+00:00")
    assert closed["verdict"] == "survived", closed
    assert closed["max_drawdown_pct"] == pytest.approx(20.0), closed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_strategy_that_lost_is_refuted_and_says_by_how_much():
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 99, 97, 96, 95], hours=12)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "refuted", said
    assert said["return_pct"] < 0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stop_nexus_named_is_taken_when_the_index_crosses_it():
    """His own exit rule, applied to his own proposal. A strategy that would
    have been stopped out on day one is not rescued by the index coming back
    -- reading only the last point is how a backtest flatters itself."""
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 94, 97, 103, 104], hours=12)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["legs"][0]["exit"] == "sl", said
    assert said["return_pct"] < 0, said
    assert said["verdict"] == "refuted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_that_closes_inside_the_window_is_judged_up_to_its_close():
    """Every crypto card tradeable on 2026-09-22 closed on 2026-09-24, inside
    the laboratory's five-day windows. After the close their index stops, and
    reading the rest of the window as a gap made every one of those rooms
    inconclusive before it opened. A card's close is where its window ends."""
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 101, 102, 103, 104], hours=6)}
    closes = {"card-a": "2026-09-06T00:00:00+00:00"}

    said = lab.verdict(_acceptance(), series, now, closes=closes)
    assert said["verdict"] == "survived", said
    assert said["coverage"] >= 0.8, said

    without = lab.verdict(_acceptance(), series, now)
    assert without["verdict"] == "inconclusive", (
        "with no close to go by, half a window is still a gap")

    # The benchmark over the same stretch: BTC flat until the close and up
    # 20% after it must not refute a leg that had already closed at +4%.
    series["btc"] = _series("2026-09-05T00:00:00+00:00",
                            [100, 100, 100, 100, 100, 110, 120], hours=6)
    benched = lab.verdict(_acceptance(benchmark_card="btc"), series, now,
                          closes=closes)
    assert benched["verdict"] == "survived", benched
    assert benched["benchmark_pct"] == 0.0, benched


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_flat_stretch_they_did_not_record_is_the_same_value_not_a_gap():
    """SPCX, 2026-09-11 17:14 to 09-15 05:46: no point for 85 hours and
    99.870362 at both ends. They record the index when it moves; a stretch
    with the same value on both sides is that value, and STR-0005 read it as
    a gap covering the first two days of its window."""
    now = "2026-09-07T01:00:00+00:00"
    before = _series("2026-09-04T12:00:00+00:00", [100])
    after = _series("2026-09-05T10:00:00+00:00",
                    [100, 99, 98, 97, 96, 95, 94, 93, 92], hours=4)
    said = lab.verdict(_acceptance(), {"card-a": before + after}, now)
    assert said["coverage"] >= 0.8, said
    assert said["verdict"] == "refuted", said

    moved = _series("2026-09-05T10:00:00+00:00",
                    [103, 99, 98, 97, 96, 95, 94, 93, 92], hours=4)
    unknown = lab.verdict(_acceptance(), {"card-a": before + moved}, now)
    assert unknown["verdict"] == "inconclusive", (
        "a value that moved across the gap moved at a time nobody knows")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_gap_in_the_data_is_inconclusive_and_never_a_loss():
    """Rule 8 in the laboratory: the console stopped sampling, so we do not
    know -- and "we do not know" may not be written into the record as a
    strategy that failed."""
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 101],
                                hours=1)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "inconclusive", said
    assert said["coverage"] < 0.8


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_inconclusive_verdict_is_still_writable_to_the_diary():
    """`verdict()` is never called for its own sake -- `record_verdict()`
    immediately `json.dumps`s whatever it returns into `state/rooms.jsonl`.
    Every test above calls `verdict()` and inspects the dict; none of them
    write it, which is the shape `driving-the-helper-is-not-running-the-check`
    names -- the helper was exercised, the path that actually runs in
    production was not.

    STR-0003 hit exactly this live on 2026-09-18: `lab.py verdicts` crashed
    inside `json.dumps` with "Object of type datetime is not JSON
    serializable". The final SURVIVED/REFUTED return already strips each
    leg's internal `curve` -- a list of `(datetime, float)` points used only
    to compute the portfolio drawdown -- but the earlier INCONCLUSIVE-on-
    coverage return, a few lines above it, does not: it returns `legs`
    exactly as the loop built them, curve included, for any leg that scored
    at all before the window's overall coverage came up short.
    """
    now = "2026-09-07T01:00:00+00:00"
    # Two legs: one long enough to score (and so build a `curve`), one too
    # short -- coverage is dragged under the floor by the second leg, and the
    # verdict comes back inconclusive with the first leg's curve still in it.
    series = {
        "card-a": _series("2026-09-05T00:00:00+00:00",
                          [100, 101, 102, 103, 104], hours=12),
        "card-b": _series("2026-09-05T00:00:00+00:00", [100, 101], hours=1),
    }
    acceptance = _acceptance(legs=[
        {"card": "card-a", "side": "bull", "share": 1.0, "tp": 8.0, "sl": -5.0},
        {"card": "card-b", "side": "bull", "share": 1.0, "tp": 8.0, "sl": -5.0},
    ])
    said = lab.verdict(acceptance, series, now)
    assert said["verdict"] == "inconclusive", said
    assert any(leg.get("card") == "card-a" and leg.get("return_pct") is not None
              for leg in said["legs"]), (
        "the fixture must exercise a SCORED leg, or this proves nothing")

    json.dumps(said)  # must not raise TypeError: Object of type datetime ...
    for leg in said["legs"]:
        assert "curve" not in leg, (
            "an internal field leaked into what gets written to the diary")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_beating_nothing_is_not_beating_the_benchmark():
    """Cymetica's own guide asks whether a strategy beats BTC, not whether it
    is positive. A card that rose 3% while the benchmark rose 4% is refuted.
    (It said 1% until V2: after the 1.4% round trip that is a loss, and the
    test would have been refuted for the wrong reason.)"""
    now = "2026-09-07T01:00:00+00:00"
    series = {
        "card-a": _series("2026-09-05T00:00:00+00:00",
                          [100, 100.75, 101.5, 102.25, 103], hours=12),
        "btc-card": _series("2026-09-05T00:00:00+00:00",
                            [100, 101, 102, 103, 104], hours=12),
    }
    said = lab.verdict(_acceptance(benchmark_card="btc-card"), series, now)
    assert said["benchmark_pct"] is not None and said["benchmark_pct"] > 3
    assert said["verdict"] == "refuted", said
    assert "benchmark" in said["why"].lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_that_has_not_closed_has_no_verdict_yet():
    now = "2026-09-05T06:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 101])}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "open", said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stop_crossed_inside_the_window_refutes_it_there_and_then():
    """2026-09-21, the operator: rooms that fail are dropped, not carried to
    the end of a five-day window. A crossing we have SEEN is a fact whatever
    the coverage of the rest of the window, so it needs none; a path that
    has not crossed stays open."""
    now = "2026-09-05T06:00:00+00:00"
    crossed = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 98, 94.5])}
    said = lab.verdict(_acceptance(), crossed, now)
    assert said["verdict"] == "refuted" and said["early"] is True, said
    assert "before the window closed" in said["why"]

    held = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 98, 97])}
    assert lab.verdict(_acceptance(), held, now)["verdict"] == "open"

    # Only the portfolio stop, no leg levels -- the laboratory's own rooms.
    bare = _acceptance(legs=[{"card": "card-a", "side": "bull", "share": 1.0}],
                       stop_pct=10.0)
    deep = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 104, 93])}
    said = lab.verdict(bare, deep, now)
    assert said["verdict"] == "refuted" and said["early"], said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_survives_early_only_failures_settle_before_the_close():
    """Deep pass of 2026-09-21, two rounds of rule-change readers. An early
    "survived" read survived at +6 h and refuted at the close on one path
    (the benchmark kept rising after the exit), and legs of +20 at TP and -4
    at SL read refuted early and survived at the close. Only what the close
    can no longer reverse settles early: a drawdown past the stop (it only
    grows), or every leg out at a net loss. A win waits for the window."""
    now = "2026-09-05T06:00:00+00:00"
    tp = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 103, 108.5])}
    assert lab.verdict(_acceptance(), tp, now)["verdict"] == "open"

    mixed = _acceptance(stop_pct=50.0, legs=[
        {"card": "card-a", "side": "bull", "share": 1.0, "tp": 20.0, "sl": -5.0},
        {"card": "card-b", "side": "bull", "share": 1.0, "tp": 8.0, "sl": -4.0}])
    series = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 110, 121]),
              "card-b": _series("2026-09-05T00:00:00+00:00", [100, 98, 95.5])}
    assert lab.verdict(mixed, series, now)["verdict"] == "open", (
        "a net win of mixed exits is the close's to call")

    losing = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 97, 94]),
              "card-b": _series("2026-09-05T00:00:00+00:00", [100, 98, 95.5])}
    said = lab.verdict(mixed, losing, now)
    assert said["verdict"] == "refuted" and said["early"] is True, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_goes_running_only_with_a_criterion_written_first(tmp_path,
                                                                 monkeypatch):
    """Preregistration, in the laboratory. A criterion written after the
    numbers are in is a criterion that fits them -- which is the whole reason
    this repository preregisters a run before it measures anything."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import importlib

    import qa.rooms
    import qa.state

    importlib.reload(qa.state)
    rooms = importlib.reload(qa.rooms)

    # Long enough that the tab would call it answered, which is the same bar a
    # room opens on (qa/rooms.py::ANSWERED_CHARS).
    answer = ("Buy card-a, bull, 20% of the bankroll, take profit at 8%, stop "
              "at -5%. Backtest Sharpe 5.16 over 90 days, with a max drawdown "
              "of 1.8% and 275 trades. The basket is dominated by one asset, "
              "so size it against the headline rather than the coins, and do "
              "not add to it while the index is inside the stop. Reassess when "
              "the card resolves or the window closes, whichever is first.")
    (tmp_path / "nexus.jsonl").write_text(json.dumps({
        "type": "answer", "id": "NEX-1", "at": "2026-09-05T00:00:00+00:00",
        "text": answer}) + "\n", encoding="utf-8")

    room = rooms.open_strategy("NEX-1", "Karta A")["id"]
    with pytest.raises(rooms.RoomError):
        rooms.set_status(room, "running", "bought it")

    # A claim may only carry numbers his answer actually says.
    with pytest.raises(rooms.RoomError):
        rooms.set_claim(room, {"sharpe": "7.77"})
    rooms.set_claim(room, {"sharpe": "5.16", "take_profit": "8%"})

    rooms.set_acceptance(room, window_days=7, stop_pct=5.0,
                         why="his own stop, over his own horizon")
    rooms.set_status(room, "running", "TRD-0001 placed")

    # And it cannot be moved while it runs.
    with pytest.raises(rooms.RoomError):
        rooms.set_acceptance(room, window_days=30, stop_pct=20.0,
                             why="it would look better over a month")

    rows = rooms.load()
    kinds = [r["type"] for r in rows]
    assert "claim" in kinds and "acceptance" in kinds
    claim = [r for r in rows if r["type"] == "claim"][-1]
    assert claim["quoted"]["sharpe"] == "5.16"
    assert claim["numbers"]["sharpe"] == 5.16


# --- N_eff -------------------------------------------------------------
#
# The wiring around the pure formula: turning running rooms into one aligned
# return series each, live-history injected so this needs no network.


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_open_book_returns_reads_only_running_rooms_weighted_by_leg(
        tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    rows = [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-1", "at": "t0"},
        {"type": "plan", "room": "STR-0001", "at": "t1",
         "legs": [{"card": "c1", "side": "bull", "share": 1.0}]},
        {"type": "status", "room": "STR-0001", "status": "running", "at": "t2"},
        # A second room, never set running -- must not appear at all.
        {"type": "strategy", "id": "STR-0002", "origin": "NEX-2", "at": "t0"},
        {"type": "plan", "room": "STR-0002", "at": "t1",
         "legs": [{"card": "c2", "side": "bull", "share": 1.0}]},
    ]
    (tmp_path / "rooms.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    history = {"c1": [{"t": (now - timedelta(days=d)).isoformat(), "index": v}
                      for d, v in [(3, 100.0), (2, 110.0), (1, 121.0), (0, 133.1)]][::-1]}
    returns = scripts_lab.open_book_returns(
        now=now, history=lambda card: history.get(card, []))

    assert list(returns) == ["STR-0001"], (
        "a room never set running is not part of the open book")
    assert all(abs(r - 10.0) < 1e-6 for r in returns["STR-0001"].values()), returns

    # A bear leg's return is flipped, and a two-leg room is share-weighted.
    rows.append({"type": "plan", "room": "STR-0001", "at": "t3",
                "legs": [{"card": "c1", "side": "bear", "share": 0.5},
                         {"card": "c2", "side": "bull", "share": 0.5}]})
    (tmp_path / "rooms.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    history["c2"] = history["c1"]  # identical series, opposite leg side
    mixed = scripts_lab.open_book_returns(
        now=now, history=lambda card: history.get(card, []))
    assert all(abs(r) < 1e-6 for r in mixed["STR-0001"].values()), (
        f"+10% bull and -10% (flipped bear) at equal share should cancel: "
        f"{mixed}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_open_book_correlates_returns_of_the_same_day(tmp_path, monkeypatch):
    """C4 of the 2026-09-23 review (3/3, narrower). Returns were paired by
    their position in each room's list, so a room whose card has five days of
    history was correlated against one with three by setting day one of the
    first beside day three of the second. Two rooms that moved identically
    every day they shared read ~0.8 and the book looked broader than it is.
    The returns are per UTC day now, and pairs are taken on the days both have
    -- a day with no point is a day the index did not move."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    rows = []
    for n, card in ((1, "a"), (2, "b")):
        rows += [{"type": "strategy", "id": f"STR-000{n}", "origin": f"NEX-{n}",
                  "at": "t0"},
                 {"type": "plan", "room": f"STR-000{n}", "at": "t1",
                  "legs": [{"card": card, "side": "bull", "share": 1.0}]},
                 {"type": "status", "room": f"STR-000{n}", "status": "running",
                  "at": "t2"}]
    (tmp_path / "rooms.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    moves = [2.0, -1.0, 3.0, -2.0, 1.0]           # days -4 .. 0, card a
    def path(start_value, days_back, steps):
        value = start_value
        out = [(now - timedelta(days=days_back), value)]
        for d, pct in zip(range(days_back - 1, -1, -1), steps):
            value *= 1 + pct / 100
            out.append((now - timedelta(days=d), value))
        return [{"t": t.isoformat(), "index": v} for t, v in out]
    history = {"a": path(100.0, 5, moves),
               "b": path(50.0, 3, moves[2:])}     # the last three days only

    returns = scripts_lab.open_book_returns(
        now=now, history=lambda card: history.get(card, []))
    said = lab.n_eff(returns)
    assert said["rho"] == pytest.approx(1.0), (
        f"identical days read as rho {said['rho']:.3f}", returns)
    assert said["n_eff"] == pytest.approx(1.0)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_book_correlation_writes_a_reading_only_when_one_was_taken(
        tmp_path, monkeypatch):
    """The wiring, not the formula: `book_correlation` calls `lab.n_eff` on
    whatever `open_book_returns` produced and only appends a notebook row when
    the result actually carries a reading -- an inconclusive book (fewer than
    two open positions, which is the ordinary daytime state) writes nothing."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    monkeypatch.setattr(scripts_lab, "open_book_returns", lambda **k: {})

    said = scripts_lab.book_correlation()
    assert said["verdict"] == "inconclusive"
    assert lab.last_n_eff() is None, "an inconclusive reading must not be logged"

    monkeypatch.setattr(
        scripts_lab, "open_book_returns",
        lambda **k: {"a": [1.0, 2.0, 3.0, 4.0, 5.0],
                    "b": [2.0, 4.0, 6.0, 8.0, 10.0]})
    said = scripts_lab.book_correlation()
    assert said["n_eff"] == pytest.approx(1.0)
    logged = lab.last_n_eff()
    assert logged is not None and logged["n_eff"] == pytest.approx(1.0)


# --- the night -------------------------------------------------------------
#
# One process the operator starts before going to bed, which ends by itself at
# an hour they name. Everything below is what keeps it from becoming a
# scheduler: it holds no hand that trades, it paces itself, and it stops.


def _scripts_lab(tmp_path, monkeypatch):
    """scripts/lab.py with its state under tmp_path. Imported by path because
    scripts/ is not a package; the same route tests/mcp uses."""
    import importlib
    import importlib.util

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_under_test", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hand_and_the_loop_share_their_hourly_limit(tmp_path, monkeypatch):
    """There were two caps until 2026-09-19 -- eight a session, twelve a
    night -- then one per rolling day (24), and since V5 (2026-09-23) none of
    ours: the brake is THEIR hourly limit, and it has to count whoever asked.

    Until the deep pass of 2026-09-21 (C09) the day's test called the pure
    `may_ask` three times, so a hand-asked question counting on its own would
    have stayed green. The same holds for the hour: one reader of the diary,
    over every session's questions, refusing `ask` itself. And the tick holds
    no door for a day's count any more -- a door nobody reads is a brake that
    looks present."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    now = datetime.now(timezone.utc)
    rows = ([{"type": "question", "id": f"NEX-N{n}", "session": "LAB-0009",
              "at": (now - timedelta(hours=n + 1)).isoformat()} for n in range(3)]
            + [{"type": "question", "id": f"NEX-T{n}", "session": "LAB-0010",
                "at": (now - timedelta(minutes=10 * n + 5)).isoformat()}
               for n in range(2)]
            + [{"type": "question", "id": f"NEX-O{n}", "session": "LAB-0008",
                "at": (now - timedelta(hours=30 + n)).isoformat()}
               for n in range(4)])
    monkeypatch.setattr(scripts_lab, "_nexus_rows", lambda: rows)
    assert scripts_lab._asked_today() == 5, "the night's three and the loop's two"
    assert "asked_today" not in scripts_lab._tick_doors()

    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    inside = []
    for n in range(lab.ASKS_PER_HOUR):
        at = (now - timedelta(minutes=15 * n + 1)).isoformat()
        inside += [{"type": "question", "id": f"NEX-{n}",
                    "session": f"LAB-{n % 3}", "at": at},
                   {"type": "answer", "id": f"NEX-{n}", "at": at}]
    monkeypatch.setattr(scripts_lab, "_nexus_rows", lambda: inside)
    # The limit's own refusal, by its words: "3" alone also matches minutes.
    with pytest.raises(SystemExit, match=f"the cap is {lab.ASKS_PER_HOUR}"):
        scripts_lab.ask("one more", wait=False)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_deadline_is_read_on_the_operators_own_clock():
    """They type the hour they will wake up, not a UTC offset. Everything else
    here is UTC, so the one place a local hour is meant has to say so -- and a
    mistyped one must not run the machine for a day."""
    zone = timezone(timedelta(hours=2))  # what their clock says in September
    night = datetime(2026, 9, 12, 23, 30, tzinfo=zone)

    due = lab.deadline("07:00", night)
    assert (due.hour, due.minute) == (7, 0)
    assert due.date() == datetime(2026, 9, 13).date()
    assert (due - night).total_seconds() == 7.5 * 3600

    with pytest.raises(lab.LabError) as refused:
        lab.deadline("07:00", datetime(2026, 9, 12, 7, 30, tzinfo=zone))
    assert "07:00" in str(refused.value) and "14" in str(refused.value), (
        "a refusal has to name what it resolved to, or it reads as a bug")
    for bad in ("7", "25:00", "07:60", "morning"):
        with pytest.raises(lab.LabError):
            lab.deadline(bad, night)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_while_a_deep_pass_runs_does_nothing_at_all():
    """Not just "asks nothing". A poll writes the answer down, and #86 counts
    the last five questions over exactly that file -- a read that writes is a
    writer. So the whole tick waits, and says which kind of wait it was, or a
    night that produced nothing looks the same as a night that was blocked."""
    now = datetime(2026, 9, 13, 2, 0, tzinfo=timezone.utc)
    state = {"asked": 0, "candidates": ["bt-cryptobull-blue"]}

    plan = lab.night_tick({**state, "pass_running": True}, now)
    assert plan["do"] == [] and plan["skipped"] == "pass"

    plan = lab.night_tick(state, now)
    assert plan["do"] == ["cycle", "truth", "ask"], (
        "the first tick of a night has never cycled, ranked or asked")

    # Five minutes since the last question, five since the last cycle, an hour
    # since the ranking, and nothing left to walk. The floor ("too soon") and
    # the day's count ("cap") went in V5 (2026-09-23): a question five
    # minutes after the last one, the day's hundredth, is theirs to pace --
    # may_ask_now's hourly limit and bound -- not this clock's.
    fresh = {**state, "last_cycle": now - timedelta(minutes=5),
             "last_truth": now - timedelta(hours=1),
             "last_ask": now - timedelta(minutes=5)}
    plan = lab.night_tick(fresh, now)
    assert plan["do"] == ["ask"], plan

    plan = lab.night_tick({**fresh, "asked": 100}, now)
    assert plan["do"] == ["ask"], plan

    # Their backoff still holds it.
    plan = lab.night_tick({**fresh, "hold_until": now + timedelta(minutes=30)},
                          now)
    assert plan["do"] == [] and plan["skipped"] == "backoff"

    plan = lab.night_tick({**fresh, "candidates": []}, now)
    assert plan["do"] == [] and plan["skipped"] == "nothing to ask about"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_night_waits_the_hour_their_own_failure_asked_for():
    """Their failed investigations carry `retry_after_s`. Six in a row on
    2026-09-11 said retryable; a night that ignored the number would have spent
    all twelve questions inside the outage."""
    now = datetime(2026, 9, 13, 2, 0, tzinfo=timezone.utc)
    said = [{"id": "NEX-1", "type": "gave_up", "status": "failed",
             "at": (now - timedelta(minutes=10)).isoformat(),
             "retryable": True, "retry_after_s": 900}]
    assert lab.backoff_until(said, now) == now + timedelta(minutes=5)

    # Without a number of theirs, the wait GROWS with the streak. Flat is wrong
    # both ways: twenty minutes would spend a whole night's cap inside an
    # outage like the one running on 2026-09-12 (six refusals, seventeen
    # hours), and two hours throttles a Nexus that is merely having a moment.
    def _failed(count, ago):
        return [{"id": f"NEX-{n}", "type": "gave_up", "status": "failed",
                 "at": (now - timedelta(minutes=ago)).isoformat()}
                for n in range(count)]

    one = lab.backoff_until(_failed(1, 10), now)
    assert one == now + timedelta(seconds=lab.NIGHT["backoff_base_seconds"]) - timedelta(minutes=10)

    three = lab.backoff_until(_failed(3, 10), now)
    assert three > one, "three refusals in a row is not one refusal"
    assert (three - now).total_seconds() <= lab.NIGHT["backoff_max_seconds"]

    many = lab.backoff_until(_failed(9, 10), now)
    assert (many - now).total_seconds() <= lab.NIGHT["backoff_max_seconds"], (
        "an outage cannot push the next try past the end of the night")

    answered = [*_failed(1, 10), {"id": "NEX-2", "type": "answer",
                         "at": (now - timedelta(minutes=1)).isoformat()}]
    assert lab.backoff_until(answered, now) is None, (
        "one answer since the failure means the lane is open again")

    # RL06 (deep pass of 2026-09-24): only the DEEP lane's own rows speak
    # about its capacity. An answer the operator pasted from the web chat is
    # no evidence the lane is open, and our own give-up -- a job still
    # `running` when our patience ran out -- is not a failure of theirs.
    pasted = [*_failed(1, 10), {"id": "NEX-3", "type": "answer", "lane": "operator",
                                "at": (now - timedelta(minutes=1)).isoformat()}]
    assert lab.backoff_until(pasted, now) == one, (
        "an answer pasted from their web chat cleared the deep lane's wait")
    impatient = [{"id": "NEX-4", "type": "gave_up", "status": "running",
                  "at": (now - timedelta(minutes=10)).isoformat()},
                 {"id": "NEX-5", "type": "gave_up", "status": "unread: ReadTimeout",
                  "at": (now - timedelta(minutes=9)).isoformat()}]
    assert lab.backoff_until(impatient, now) is None, (
        "our own give-ups were counted as their failures")

    # RL05: an answer whose time cannot be read is not a fresh one -- the
    # launch window reads it as old, not as now (rule 8, on the side that
    # spends).
    import importlib.util
    spec = importlib.util.spec_from_file_location("lab_rl05", REPO / "scripts" / "lab.py")
    scripts_lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scripts_lab)
    since = now - timedelta(hours=24)
    assert scripts_lab._fresh({"at": (now - timedelta(hours=1)).isoformat()}, since)
    assert not scripts_lab._fresh({"at": "včera 14:00"}, since), (
        "an answer with an unreadable time was launched as fresh")
    assert scripts_lab._fresh({"at": "anything"}, None)

    held = lab.night_tick({"asked": 0, "candidates": ["bt-x"],
                           "hold_until": now + timedelta(hours=1)}, now)
    assert "ask" not in held["do"] and held["skipped"] == "backoff", (
        "a backoff holds the question, not the whole tick -- answers already "
        "in flight are still picked up while their side is down")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_night_holds_no_hand_that_trades_files_or_commits():
    """A negative control that does not need the thing it tests: read off the
    source rather than performed.

    It said "buying, filing and committing are not among the night's doors"
    until 2026-09-12, when the operator said the night may launch. Buying is a
    door now; filing and committing are not, and the buying door has the day's
    brakes wired in front of it. An audit agent caught the docstring still
    claiming the old rule while the assertion below required the new one --
    the two halves of this check disagreeing about what it was for."""
    import ast

    source = (REPO / "scripts" / "lab.py").read_text(encoding="utf-8")
    night = source[source.index("\n# --- the night"):source.index("\ndef main(")]
    # `def night(` was the anchor until the command was removed on 2026-09-21;
    # the section still holds every door the tick spends through.
    assert "def night_promote(" in night and len(night) > 2000, "the slice moved"

    # The CODE, not the prose. A raw substring search read docstrings too, so
    # explaining in words that the night must not reach paper was itself a
    # failure -- and it fired that way on 2026-09-12. Reading identifiers and
    # non-docstring strings is also STRICTER: it sees a call split over lines,
    # which the substring never could.
    tree = ast.parse(textwrap.dedent(night))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Module)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:]

    def _names(node) -> set:
        out = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                out.add(child.id)
            elif isinstance(child, ast.Attribute):
                out.add(child.attr)
            elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                out.add(child.value)
        return out

    reached = _names(tree)

    # Deep pass 2026-09-25 (B03, 3/3): only the slice was read, while the
    # night calls lab.py functions defined outside it (`_archive_diaries`)
    # and, through `_sibling`, keep, processes, morning and clone. What those
    # reach is the night's hand too: walk them, function by function, from
    # what the night names -- not whole modules, whose other commands (keep
    # track's `git add`) the night never runs.
    def _module_defs(path):
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(module):   # the code, not the prose, as above
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = node.body
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    node.body = body[1:] or [ast.Pass()]
        return {n.name: n for n in module.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def _walk(defs, start):
        seen, todo, names = set(), [n for n in start if n in defs], set()
        while todo:
            name = todo.pop()
            if name in seen:
                continue
            seen.add(name)
            found = _names(defs[name])
            names |= found
            todo += [n for n in found if n in defs and n not in seen]
        return names

    lab_defs = _module_defs(REPO / "scripts" / "lab.py")
    in_slice = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    outside_defs = {k: v for k, v in lab_defs.items() if k not in in_slice}
    outside = [n for n in _walk(outside_defs, reached - in_slice) | (reached - in_slice)
               if n in outside_defs]
    reached |= _walk(outside_defs, outside)

    def _sibling_calls(nodes) -> dict:
        """(module -> attributes) the code calls on `_sibling("module")`,
        directly or through a name it was assigned to."""
        calls: dict = {}
        for fn in nodes:
            local = {}
            for child in ast.walk(fn):
                if (isinstance(child, ast.Assign) and isinstance(child.value, ast.Call)
                        and getattr(child.value.func, "id", None) == "_sibling"
                        and child.value.args
                        and isinstance(child.value.args[0], ast.Constant)):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            local[target.id] = child.value.args[0].value
            for child in ast.walk(fn):
                if not isinstance(child, ast.Attribute):
                    continue
                owner = child.value
                if isinstance(owner, ast.Name) and owner.id in local:
                    calls.setdefault(local[owner.id], set()).add(child.attr)
                elif (isinstance(owner, ast.Call)
                      and getattr(owner.func, "id", None) == "_sibling"
                      and owner.args and isinstance(owner.args[0], ast.Constant)):
                    calls.setdefault(owner.args[0].value, set()).add(child.attr)
        return calls

    night_fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    calls = _sibling_calls(night_fns + [lab_defs[n] for n in outside])
    walked = set()
    for sibling, attrs in sorted(calls.items()):
        path = REPO / "scripts" / f"{sibling}.py"
        if sibling == "bounty" or not path.exists():   # bounty is walked below
            continue
        defs = _module_defs(path)
        reached |= _walk(defs, attrs & set(defs))
        walked.add(sibling)
    assert {"keep", "clone"} <= walked, ("the walk no longer reaches the "
                                         "siblings it was written for", walked)

    # And qa/, which the tick calls on every round (lab.note_tick, rooms.*,
    # lab.decide): a git commit added to a qa function the night reaches
    # passed, because the walk stopped at scripts/ (deep pass 2026-09-27, B03,
    # 2/3). Walked the same way, function by function from what the night
    # names, over the qa modules scripts/lab.py imports, to a fixed point.
    #
    # Kept apart from `reached`: qa/state.py names "withdraw" and
    # "scripts/withdraw.py" as event types and in error text, which is prose,
    # not a hand. qa/ imports no script, so the only way it can file, commit or
    # run one is a shell -- and that is what is asserted of it below.
    qa_mods = ("lab", "rooms", "surface", "morning", "lab_report", "backtests",
               "state", "evidence", "client", "config", "console", "safety")
    qa_defs = {m: _module_defs(REPO / "qa" / f"{m}.py") for m in qa_mods}
    qa_reached = set(reached)
    while True:
        grown = set(qa_reached)
        for defs in qa_defs.values():
            grown |= _walk(defs, qa_reached & set(defs))
        if grown == qa_reached:
            break
        qa_reached = grown
    qa_reached -= reached
    assert len(qa_reached) > 100, f"the qa walk reads nothing: {len(qa_reached)}"
    for hand in ("subprocess", "system", "popen", "Popen", "execv", "execvp",
                 "spawnv", "startfile", "check_call", "check_output"):
        assert hand not in qa_reached, f"the night reaches a shell in qa/: {hand!r}"
    git = re.compile(r"\bgit\s+(?:commit|push|add|tag|reset)\b")
    assert not sorted(s for s in qa_reached if git.search(s)), "a git command in qa/"

    # [operator 2026-09-12] *"Jasne ze v noci muze spoustet."* So this stopped
    # being "no hand at all" and became "only the braked one". Filing and
    # committing are still out: the night finds, the morning tells the vendor.
    # C02 (deep pass of 2026-09-24): `_sibling("verify").main([...])` puts
    # only "verify" among the names read here, and verify.py POSTs verdicts
    # to their tracker -- as correspond, a2a and bounty talk to them too.
    for hand in ("submit", "findings", "subprocess", "withdraw", "prereg",
                 "verify", "correspond", "a2a"):
        assert hand not in reached, (
            f"the night can reach {hand!r}: it researches and launches on "
            f"paper, it does not talk to the vendor")
    # bounty.py, since 2026-09-25: the tick reads their tracker and inbox so
    # their answers are acted on within a tick (CLAUDE.md, How to work with
    # me). READS only: the one function that loads it may touch exactly the
    # two read functions, and neither they nor what they call may POST --
    # bounty.fetch() probes the filing endpoint with empty POSTs, and that
    # stays out of reach.
    holders = [node for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef) and "bounty" in _names(node)]
    assert [h.name for h in holders] == ["_tracker_round"], [h.name for h in holders]
    READS = {"refresh_our_reports", "fetch_inbox"}
    used = {child.attr for child in ast.walk(holders[0])
            if isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Name) and child.value.id == "bounty"}
    assert used and used <= READS, f"the tick reaches bounty.{used - READS}"
    bounty_tree = ast.parse((REPO / "scripts" / "bounty.py").read_text(encoding="utf-8"))
    defs = {n.name: n for n in bounty_tree.body if isinstance(n, ast.FunctionDef)}
    seen, todo = set(), list(READS)
    while todo:
        name = todo.pop()
        if name in seen or name not in defs:
            continue
        seen.add(name)
        for child in ast.walk(defs[name]):
            if isinstance(child, ast.Attribute) and child.attr in (
                    "post", "put", "patch", "delete"):
                raise AssertionError(f"bounty.{name} writes to them: .{child.attr}")
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                todo.append(child.func.id)
    assert {"fetch_our_reports", "record_inbox"} <= seen, seen
    # And the read works from a tick, which has not loaded .env: the first
    # live round read the wallet as unset and kept a stale snapshot.
    assert "load_dotenv" in _names(defs["fetch_our_reports"])
    # B01, deep pass of 2026-09-22 evening (3/3): five exact names, so
    # os.system("git commit -am night") in night_promote stayed green -- the
    # door the docstring says is shut, through a hand the list did not name.
    for hand in ("system", "popen", "Popen", "execv", "execvp", "spawnv",
                 "startfile", "check_call", "check_output"):
        assert hand not in reached, f"the night can reach a shell: {hand!r}"
    shell = re.compile(r"\bgit\s+(?:commit|push|add|tag|reset)\b"
                       r"|\b(?:submit|withdraw|prereg|verify|correspond|a2a"
                       r"|bounty)\.py\b")
    said = sorted(s for s in reached if shell.search(s))
    assert not said, f"the night carries a command it must not run: {said}"

    # Every function in the night that can spend must reach the caps BEFORE it
    # spends, and the interlock at all. Read as a tree, not as token presence:
    # an audit agent defeated the first version of this in one line by moving
    # `affordable` after `paper.buy`, which is the exact move the comment
    # claimed word-presence could not see. The idiom is
    # test_pipeline_book.py::test_the_cap_is_not_advisory's -- the gate and the
    # spend must be statements of ONE block, in that order, which a relocation
    # into another branch cannot preserve.
    def _calls(node, name: str) -> bool:
        return any(isinstance(c, ast.Call) and (
                   getattr(c.func, "id", None) == name
                   or getattr(c.func, "attr", None) == name)
                   for c in ast.walk(node))

    # Since 2026-09-22 a paper bot is funded from the same book (clone.py's
    # `fund`), so a transfer into a clone is a spend like a buy.
    spends = ("buy", "fund")

    def _gate_then_spend(node) -> bool:
        for block in [b for n in ast.walk(node)
                      for b in (getattr(n, "body", []), getattr(n, "orelse", []))
                      if isinstance(b, list)]:
            gate = next((i for i, s in enumerate(block)
                         if _calls(s, "affordable")), None)
            spend = next((i for i, s in enumerate(block)
                          if any(_calls(s, name) for name in spends)), None)
            if gate is not None and spend is not None and gate < spend:
                # C02, deep pass of 2026-09-22: calling the gate is not
                # obeying it. Dropping `not ok or` at both call sites kept
                # this green. Its verdict has to be bound, and a statement
                # between it and the spend has to leave on `not <verdict>`.
                verdict = _bound_verdict(block[gate])
                if verdict and any(_leaves_on_not(s, verdict)
                                   for s in block[gate + 1:spend]):
                    return True
        return False

    def _bound_verdict(stmt):
        targets = getattr(stmt, "targets", None) or []
        if targets and isinstance(targets[0], ast.Tuple) and targets[0].elts:
            first = targets[0].elts[0]
            return getattr(first, "id", None)
        return None

    def _leaves_on_not(stmt, name: str) -> bool:
        return (isinstance(stmt, ast.If)
                and any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not)
                        and getattr(n.operand, "id", None) == name
                        for n in ast.walk(stmt.test))
                and any(isinstance(n, (ast.Return, ast.Raise, ast.Continue,
                                       ast.Break)) for n in stmt.body))

    spenders = [node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and any(_calls(node, name) for name in spends)]
    assert any(_calls(node, "fund") for node in spenders), (
        "nothing in the night funds a paper bot; the operator asked for bots")
    assert spenders, "nothing in the night can launch; the operator asked for it"
    for node in spenders:
        assert _gate_then_spend(node), (
            f"{node.name} spends without the caps as an earlier statement of "
            f"the same block -- a gate in another branch is not a gate")
        assert "pass_in_flight" in _names(node), (
            f"{node.name} spends without checking for a running deep pass, "
            f"which is verifying #85/#86/#87 over these very trades")
        assert "open_strategy" in _names(node), (
            f"{node.name} spends without opening a room from a Nexus answer -- "
            f"CLAUDE.md: a strategy of ours never becomes a room")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_notebook_is_outside_git():
    """It is appended to while a run may be in flight, and a dirty tree is a
    tree no run can reach level V from -- the reason nexus.jsonl and
    paper.jsonl are outside git too. scripts/keep.py snapshot is what stops
    that meaning "one disk"."""
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "state/lab.jsonl" in ignored, (
        "the laboratory's notebook would dirty the tree mid-run")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refill_reaches_live_cards_it_has_not_walked_yet():
    """2026-09-21 21:43 onward, every tick: "0 backtest(s), 56 already known".
    The seeds were the cards our sampler happened to see and the best of our
    own readings, and both are deterministic -- once walked, the refill hands
    back the same questions and the register answers all of them. Their live
    crypto cards change every day; they are what a dry search refills from."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "lab_refill_live", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    live = [{"card": "c1", "title": "new today",
             "legs": [{"symbol": "NEAR", "weight": 0.5},
                      {"symbol": "TRUMP", "weight": 0.5}]}]
    assert module.night_refill(rows=[]) == [], "no readings, no live cards"
    moves = module.night_refill(rows=[], live=live)
    symbols = {leg["symbol"] for move in moves for leg in (move["legs"] or [])}
    assert {"NEAR", "TRUMP"} <= symbols, moves[:3]

    # The listing, crypto only and tradeable: a stock leg cannot be priced by
    # their backtest, and a card that cannot trade is not a question for now.
    listing = {"cards": [
        {"id": "a", "title": "ok", "tradeable_now": True, "has_stock_legs": False,
         "basket": [{"symbol": "NEAR", "weight": 0.52, "asset_type": "crypto"},
                    {"symbol": "XRP", "weight": 0.48, "asset_type": "crypto"}]},
        {"id": "b", "title": "stocks", "tradeable_now": True, "has_stock_legs": True,
         "basket": [{"symbol": "GNRC", "weight": 0.6, "asset_type": "stock"},
                    {"symbol": "BTC", "weight": 0.4, "asset_type": "crypto"}]},
        {"id": "c", "title": "shut", "tradeable_now": False, "has_stock_legs": False,
         "basket": [{"symbol": "SOL", "weight": 0.5, "asset_type": "crypto"},
                    {"symbol": "ETH", "weight": 0.5, "asset_type": "crypto"}]},
        {"id": "d", "title": "one coin", "tradeable_now": True,
         "has_stock_legs": False,
         "basket": [{"symbol": "WIF", "weight": 1.0, "asset_type": "crypto"}]}]}
    seeds = module.live_card_seeds(listing)
    assert [s["card"] for s in seeds] == ["a"], seeds


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refill_climbs_from_what_scored_rather_than_from_where_we_started():
    """Otherwise the night re-walks its own first queue for ever.

    The readings are stamped RELATIVE to now. They were absolute --
    2026-09-12T12:00Z -- and `night_refill` has no `now` seam, so
    `backtests.best()` reads the wall clock: `stale_after(30)` is 3.0 days, and
    on 2026-09-15 `best()` would have returned nothing, `moves` would have been
    empty and this test would have gone red in `tests/meta` with the refill
    entirely correct. A red there aborts every session, so it would have taken
    the vendor checks down with it three days after it was written. Every
    sibling in test_pipeline_backtests.py pins `now=NOW`; this one cannot, so
    the fixture moves with the clock instead.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "lab_refill", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = [{"fp": "a", "p": 30, "s": 9.0, "d": 1.0, "r": 5.0, "pts": 90,
             "at": fresh, "why": "the good one",
             "legs": [["BTC", 0.6], ["ETH", 0.4]]},
            {"fp": "b", "p": 30, "s": 0.1, "d": 40.0, "r": 0.2, "pts": 90,
             "at": fresh, "why": "the bad one",
             "legs": [["DOGE", 0.9], ["SHIB", 0.1]]}]

    moves = module.night_refill(rows=rows, limit=1, cap=8)

    assert moves, "a refill from real readings produced nothing"
    symbols = {leg["symbol"] for move in moves for leg in (move["legs"] or [])}
    assert "BTC" in symbols, "the refill did not climb from the best reading"
    assert "SHIB" not in symbols, (
        "the refill seeded from the worst reading as well as the best")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hand_run_search_refills_the_same_way_the_night_does():
    """`night` climbs; `lab.py search` did not, and went silently empty.

    The night refills its queue from what has actually scored the moment the
    first one runs out (test above). The hand-run `search` command had no such
    step: it walked `card_baskets()`' neighbourhood once and, from then on,
    every invocation asked for baskets the register already held. Measured
    2026-09-13 -- two consecutive sweeps, the second returning **0 asked, 32
    already known**, which reads exactly like a finished search rather than
    like a queue nobody refilled. The operator's question that afternoon was
    why so few backtests had been run.

    So `search_queue` is the one place both callers get their moves from, and
    what is asserted here is that it does NOT stop at the cards: when the
    register holds good readings, they are in the queue too.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "lab_search_queue", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    scored = [{"fp": "a", "p": 30, "s": 9.0, "d": 1.0, "r": 5.0, "pts": 90,
               "at": fresh, "why": "the good one",
               "legs": [["KSM", 0.6], ["ZEN", 0.4]]}]
    seeds = [{"card": "c1", "title": "a card the sampler saw",
              "legs": [{"symbol": "BTC", "weight": 0.6},
                       {"symbol": "ETH", "weight": 0.4}]}]

    queue = module.search_queue(seeds, rows=scored, cap=6)

    symbols = {leg["symbol"] for move in queue for leg in (move["legs"] or [])}
    assert "BTC" in symbols, "the card neighbourhood must still be walked"
    assert "KSM" in symbols, (
        "a hand-run search must also climb from what scored, or it goes empty "
        "after one pass and every later sweep asks only what is already known")

    # With nothing scored yet, it is still exactly the card neighbourhood --
    # a first run on an empty register must not be broken by the refill.
    first = module.search_queue(seeds, rows=[], cap=6)
    assert first, "an empty register must not empty the queue"
    assert {leg["symbol"] for move in first
            for leg in (move["legs"] or [])} <= {"BTC", "ETH"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_climb_can_reach_symbols_the_best_baskets_do_not_contain():
    """A refill that draws its pool from the winners only collapses onto them.

    Measured 2026-09-13, within an hour of the refill being wired into the
    hand-run search: **all 20 of the top 20 readings contained KSM**, and the
    share of new readings containing it went from 27 of 65 the day before to
    49 of 69 that day. 134 backtests across 21 distinct symbols.

    The mechanism was `night_refill` taking its substitution pool from the
    seeds it had just built out of the best rows -- so `add` and `drop` could
    only ever shuffle symbols that were already winning. The more baskets get
    tested around one symbol, the more surely the best observed Sharpe is that
    symbol's noise: the deflated-Sharpe point Nexus itself made to us about
    stockbull-blue, arriving on our own side of the glass.

    So the pool is an argument, and `search_queue` passes THEIR whole card
    universe. The climb still starts from what scored; what it may reach is no
    longer limited to what has already scored.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "lab_refill_pool", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    scored = [{"fp": "a", "p": 30, "s": 9.0, "d": 1.0, "r": 5.0, "pts": 90,
               "at": fresh, "why": "the winner",
               "legs": [["KSM", 0.6], ["ZEN", 0.4]]}]

    narrow = module.night_refill(rows=scored, limit=1, cap=24)
    assert {leg["symbol"] for move in narrow
            for leg in (move["legs"] or [])} <= {"KSM", "ZEN"}, (
        "without a pool the refill can only shuffle the winners -- this is "
        "the collapse, pinned so the fix below is visibly a fix")

    wide = module.night_refill(rows=scored, limit=1, cap=24,
                               pool=["KSM", "ZEN", "BCH", "SOL", "NEO"])
    reached = {leg["symbol"] for move in wide for leg in (move["legs"] or [])}
    assert "KSM" in reached, "it must still climb from what scored"
    assert reached - {"KSM", "ZEN"}, (
        "a refill given a wider pool never left the winners' own symbols")

    # And the hand-run queue supplies that pool from THEIR cards. The symbol
    # that proves it has to be reachable ONLY through the wide pool: BCH comes
    # from the card's own legs and KSM from the scored row's, so asserting
    # those two could not see the pool at all -- reverting search_queue to
    # `night_refill(rows, limit, cap)`, the exact collapse this test is named
    # for, left it green. L05, deep pass of 2026-09-13, triage 3/3.
    #
    # ACT is on one of their cards and in none of the winners, so it can only
    # enter a CLIMB move by being substituted in from the card universe. It is
    # chosen to sort early, because `neighbourhood` walks the pool in order and
    # a cap of 8 does not reach the end of it -- a symbol that sorts late would
    # make this test about the cap rather than about the pool.
    seeds = [{"card": "c1", "title": "theirs",
              "legs": [{"symbol": "BCH", "weight": 0.5},
                       {"symbol": "SOL", "weight": 0.5}]},
             {"card": "c2", "title": "theirs too",
              "legs": [{"symbol": "ACT", "weight": 0.5},
                       {"symbol": "BCH", "weight": 0.5}]}]
    queue = module.search_queue(seeds, rows=scored, cap=8)

    # A climb move is one seeded from a scored basket, so it carries KSM or
    # ZEN; the card neighbourhoods never do.
    climbs = [m for m in queue
              if {"KSM", "ZEN"} & {leg["symbol"] for leg in (m["legs"] or [])}]
    assert climbs, "the queue carries no climb at all"
    reached = {leg["symbol"] for m in climbs for leg in (m["legs"] or [])}
    assert "ACT" in reached, (
        f"no climb move reached a symbol outside the winners, so the wide "
        f"pool is not being used: {sorted(reached)}")

    narrow = module.search_queue(seeds, rows=scored, cap=8, pool_from_cards=False)
    narrow_climbs = {leg["symbol"] for m in narrow
                     for leg in (m["legs"] or [])
                     if {"KSM", "ZEN"} & {l["symbol"] for l in (m["legs"] or [])}}
    assert "ACT" not in narrow_climbs, (
        "the control failed: without the card pool the climb reaches ACT "
        "anyway, so the assertion above proves nothing")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unreadable_pass_notebook_is_not_an_absent_pass(tmp_path,
                                                           monkeypatch):
    """Rule 8, on the interlock that stops us talking to Nexus mid-pass.

    `_notebook()` mapped a half-read JSON to `{}`, and `pass_in_flight()` reads
    `{}` as "no pass running". The deep pass rewrites that file repeatedly as it
    goes, so a read landing mid-write turned the interlock OFF -- while the pass
    was verifying #85, #86 and #87 over the very answers and trades a question
    would then change.

    `prune_runs._load` gets this right twenty files away: a failed read is not
    an empty read.
    """
    import importlib.util

    monkeypatch.setenv("QA_REPO_ROOT", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "processes_rule8", REPO / "scripts" / "processes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    notebook = tmp_path / "audits" / "deep-pass-progress.json"
    notebook.parent.mkdir(parents=True, exist_ok=True)
    notebook.write_text('{"run": "deep-pass", "at": "2026-09-12T1',
                        encoding="utf-8")

    assert module.pass_in_flight() is True, (
        "a notebook we could not parse was read as no pass running, and the "
        "laboratory would have asked Nexus straight through a deep pass")

    notebook.unlink()
    assert module.pass_in_flight() is False, (
        "no notebook at all IS no pass; only an unreadable one is unknown")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_money_out_is_counted_even_when_they_name_it_oddly(tmp_path,
                                                           monkeypatch):
    """Understating what is deployed overstates the headroom under the ceiling.

    Two shapes dropped an accepted order to zero: no `position_id`, and a
    `usdc` given as one of their decimal strings. The second is the same defect
    `_free_cash` was fixed for the same hour, twenty lines above. Both inflate
    the room left under the 60% exposure cap, which is the brake that holds.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    rows = [
        {"type": "intent", "id": "TRD-0001", "usdc": 10_000.0},
        {"type": "outcome", "id": "TRD-0001", "outcome": "accepted",
         "position_id": "p1"},
        {"type": "intent", "id": "TRD-0002", "usdc": "20000.00"},
        {"type": "outcome", "id": "TRD-0002", "outcome": "accepted",
         "position_id": "p2"},
        {"type": "intent", "id": "TRD-0003", "usdc": 5_000.0},
        {"type": "outcome", "id": "TRD-0003", "outcome": "accepted"},
    ]
    (tmp_path / "paper.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    assert scripts_lab._deployed() == 35_000.0, (
        "a string amount or a missing position id was counted as nothing out")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_nexus_invented_is_not_bought():
    """#91: it named a card that does not exist, with a live-looking index and
    90-day metrics beside two cards whose numbers were right to six decimals.

    So a proposal is only actionable for cards we have actually seen come back
    from their API. Nexus naming one is not evidence it exists -- that is the
    finding, and this is the brake it earned.
    """
    known = {"30408a4b-8717-4fc7-a91a-9a6724cadd7e",
             "e579581b-0ad3-463f-8c3d-e80bd2624d40"}
    text = ("Buy 30408a4b-8717-4fc7-a91a-9a6724cadd7e bull, and also "
            "deadbeef-0000-0000-0000-000000000000 which looks strong.")

    found = lab.proposed_cards(text, known)

    assert found["actionable"] == ["30408a4b-8717-4fc7-a91a-9a6724cadd7e"]
    assert found["unknown"] == ["deadbeef-0000-0000-0000-000000000000"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_that_names_no_card_is_left_for_the_morning():
    """NEX-0018 and NEX-0026 named none. NEX-0026 was the best answer Nexus has
    given us -- it refused its own top-ranked strategy and handed us a leading
    indicator -- and it proposes nothing to buy. An answer is not a proposal."""
    assert lab.proposed_cards("treat that number as unmeasured", {"a"}) == {
        "actionable": [], "unknown": []}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_status_shows_the_cached_n_eff_and_a_resolve_nobody_caught(
        tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)

    (tmp_path / "lab.jsonl").write_text(json.dumps(
        {"type": "n_eff", "at": "2026-09-13T10:00:00+00:00",
         "n": 4, "rho": 0.72, "n_eff": 1.4}) + "\n", encoding="utf-8")

    paper = [
        {"type": "intent", "id": "TRD-1", "card_id": "c1", "usdc": 10.0},
        {"type": "outcome", "id": "TRD-1", "outcome": "accepted",
         "position_id": "p1"},
    ]
    (tmp_path / "paper.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in paper), encoding="utf-8")
    samples = [
        {"kind": "position", "at": "2026-09-13T09:00:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "open"},
        {"kind": "position", "at": "2026-09-13T15:00:00+00:00",
         "position_id": "p1", "card_id": "c1", "status": "closed",
         "realized_pnl_usdc": 7.5},
    ]
    (tmp_path / "samples.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in samples), encoding="utf-8")

    out = scripts_lab.status()
    assert "N_eff 1.4 of 4" in out, out
    assert "0.72" in out, out
    assert "RESOLVED WITHOUT US: p1 (c1), 7.5 USDC" in out, out

    # Written down once (a tick does it), it stops being news: the same line
    # on every status for ever was the defect the writer closed, 2026-09-19.
    lab.note_resolved(lab.resolved_without_us(paper, samples))
    out = scripts_lab.status()
    assert "RESOLVED WITHOUT US" not in out, out
    assert "written down: 1" in out, out


# --- V5: a paper bot's settings, walked in time on its one clone -----------

def _clone_module(tmp_path, monkeypatch):
    import importlib.util

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "clone_for_the_grid", REPO / "scripts" / "clone.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_settings_grid_is_walked_one_variant_at_a_time_and_each_body_is_whole(
        tmp_path, monkeypatch):
    """V5 of plan v2: a grid of settings per species, walked in time on its
    ONE paper clone (REPLY-0049), one factor at a time.

    A PATCH that sets a field cannot unset it -- a fresh clone's SL, TP,
    max_position and min_ai_confidence are null (CLN-0018's response) and
    clone.py's floor sends numbers only -- so a factor one variant moved would
    leak into every later one. Every body therefore carries the WHOLE grid:
    the reference with exactly one factor moved, determined by itself and not
    by what ran on the clone before. Every body is one clone.py's floor
    accepts, so the grid can never spend a variant on a 422."""
    clone = _clone_module(tmp_path, monkeypatch)
    grid = lab.variants()
    labels = [v["label"] for v in grid]
    assert labels[0] == "reference" and len(set(labels)) == len(labels), labels
    reference = grid[0]["settings"]
    # Their defaults wherever they have one (CLN-0018, 2026-09-22).
    assert (reference["max_open_positions"], reference["arena_trading_enabled"],
            reference["event_card_trading_enabled"],
            reference["tge_trading_enabled"],
            reference["catalog_trading_enabled"]) == (5, True, False, False, False)
    moved = set()
    # The market lists may only be switched off, for a bot meant for one
    # market; the grid does not walk them -- adding them to the reference
    # would move the control of every variant already run.
    walked = set(clone.SAFE_SETTINGS) - set(clone.MARKETS_OFF)
    for variant in grid:
        body = variant["settings"]
        assert set(body) == walked, sorted(set(body) ^ walked)
        assert clone.safe_settings(body) == body, variant["label"]
        diff = {k for k in body if body[k] != reference[k]}
        assert len(diff) == (0 if variant["label"] == "reference" else 1), variant
        moved |= diff
    # Every factor of the plan's grid is walked, except the catalog toggle,
    # which trades only a watchlist and the watchlist is not ours to set.
    assert moved == walked - {"catalog_trading_enabled"}, moved

    assert lab.next_variant([]) == grid[0]
    assert lab.next_variant(["reference"]) == grid[1]
    assert lab.next_variant(labels[:5]) == lab.next_variant(labels[:5]) == grid[5]
    assert lab.next_variant(labels) is None, "a walk that is done proposes nothing"


def _chain(ident, kind, at, instance="inst-1", **intent):
    return [{"id": ident, "type": "intent", "kind": kind, "instance_id": instance,
             "at": at, **intent},
            {"id": ident, "type": "outcome", "kind": kind, "outcome": "accepted",
             "at": at, "http_status": 200}]


def _t(days=0.0, minutes=0.0):
    return (datetime(2026, 9, 20, tzinfo=timezone.utc)
            + timedelta(days=days, minutes=minutes)).isoformat()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_variant_is_measured_from_its_restart_not_from_the_first_funding():
    """Item 5 of V5. `bot_series` measures from what went in, with their
    lifetime `total_profit_usdc` -- so a clone reused for a second setting
    would carry the first setting's P&L into the second verdict. A room on a
    RESTART enters at 100 at that restart, on what the bot held then (what
    went in plus what it had made), and moves only by what it made since.

    The past is not rewritten: a room on a clone's first run enters at its
    funding as before, and a room that took over a running bot (no start
    after its criterion) is read as it always was."""
    clones = [*_chain("CLN-0001", "fund", _t(0, 1), amount=240.0),
              *_chain("CLN-0002", "enable", _t(0, 2)),
              *_chain("CLN-0003", "disable", _t(5)),
              *_chain("CLN-0004", "settings", _t(5, 1)),
              *_chain("CLN-0005", "enable", _t(5, 2), bot_profit_usdc="20.0")]
    assert lab.bot_restart(clones, "inst-1", _t(0)) is None, "a first run"
    assert lab.bot_restart(clones, "inst-1", _t(1)) is None, "an adopted room"
    restart = lab.bot_restart(clones, "inst-1", _t(5, 0.5))
    assert restart == {"at": _t(5, 2), "profit": 20.0}, restart

    samples = [{"type": "sample", "kind": "bot", "instance_id": "inst-1",
                "at": at, "total_profit_usdc": profit}
               for at, profit in ((_t(4), "20.0"), (_t(5, 60), "20.0"),
                                  (_t(6), "32.6"))]
    series = lab.bot_series(samples, "inst-1", 240.0, entry_at=restart["at"],
                            entry_profit=restart["profit"])
    assert [p["t"] for p in series] == [_t(5, 2), _t(5, 60), _t(6)], series
    assert series[-1]["index"] == pytest.approx(100.0 * (1 + 12.6 / 260.0))
    # The first run, unchanged: from what went in, through every reading.
    first = lab.bot_series(samples, "inst-1", 240.0, entry_at=_t(0, 1))
    assert first[-1]["index"] == pytest.approx(100.0 * (1 + 32.6 / 240.0))

    # A restart that did not carry the figure takes the newest reading at or
    # before it; with none, the variant cannot be sized and is not judged.
    bare = [row if row.get("id") != "CLN-0005" or row["type"] != "intent"
            else {k: v for k, v in row.items() if k != "bot_profit_usdc"}
            for row in clones]
    assert lab.bot_restart(bare, "inst-1", _t(5, 0.5), samples)["profit"] == 20.0
    unsized = lab.bot_restart(bare, "inst-1", _t(5, 0.5), [])
    assert unsized["profit"] is None
    assert lab.bot_series(samples, "inst-1", 240.0, entry_at=unsized["at"],
                          entry_profit=unsized["profit"], restart=True) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_restart_turns_parked_money_into_exposure_under_the_same_ceiling():
    """A variant spends no new money: the clone's practice balance was moved
    in once and sits PARKED while the bot is paused (V2). Starting it again
    turns that parked money into exposure, so 60% of the book -- the only
    count limit since V5 -- is asked of it. The 2%-of-free per-order cap is
    not: it sizes a new stake, and a restart takes nothing from free cash."""
    ok, why = lab.restart_affordable(240.0, 10_000.0, deployed=5_700.0, parked=240.0)
    assert ok, why
    ok, why = lab.restart_affordable(240.0, 6_000.0, deployed=9_400.0, parked=240.0)
    assert not ok and "60%" in why, why
    # A case the AMOUNT decides (deep pass 2026-09-24, B02, 3/3): the one
    # above was already over 60% before the restart, so a check ignoring the
    # amount passed. Book 16 000, 9 400 out: 200 more fits, 300 does not.
    ok, why = lab.restart_affordable(200.0, 6_300.0, deployed=9_400.0, parked=300.0)
    assert ok, why
    ok, why = lab.restart_affordable(300.0, 6_300.0, deployed=9_400.0, parked=300.0)
    assert not ok and "60%" in why, why
    ok, why = lab.restart_affordable(5_000.0, 10_000.0, deployed=0.0, parked=5_000.0)
    assert ok, ("a restart is not a new order; the per-order cap does not apply", why)
    ok, why = lab.restart_affordable(240.0, None, deployed=0.0, parked=240.0)
    assert not ok and "unreadable" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_of_ours_is_judged_when_its_variant_ran_and_archived_when_not():
    """An OUR- room has no answer of his, so it is never among his picks
    (`picked_rooms` feeds "his picks" on /lab and must not grow by ours). The
    archive read "not his pick" as "archive", which would have archived every
    variant the moment it stopped. A room of ours is archived only when
    nothing ran in it -- its restart never accepted -- and judged otherwise."""
    clones = [*_chain("CLN-0001", "fund", _t(0, 1), amount=240.0),
              *_chain("CLN-0002", "enable", _t(0, 2)),
              *_chain("CLN-0003", "disable", _t(5)),
              *_chain("CLN-0004", "settings", _t(5, 1)),
              *_chain("CLN-0005", "enable", _t(5, 2), bot_profit_usdc="20.0")]
    leg = {"kind": "bot", "ref": "inst-1", "side": "bull", "share": 1.0}

    def room(ident, origin, opened):
        return [{"type": "strategy", "id": ident, "origin": origin, "title": "x",
                 "kind": "bot", "ref": "sp-1", "at": opened},
                {"type": "acceptance", "room": ident, "window_days": 5.0,
                 "stop_pct": 10.0, "legs": [leg], "at": opened},
                {"type": "status", "room": ident, "status": "stopped",
                 "why": "x", "at": _t(9)}]
    rows = room("STR-0002", "OUR-0001", _t(5, 0.5)) + room("STR-0003", "OUR-0002", _t(8))
    archived = lab.archived_rooms(rows, [], [], clones)
    assert archived == {"STR-0003"}, archived
    assert lab.picked_rooms(rows, []) == set(), "a room of ours is not his pick"

    # And what ours earned is not his record: the Nexus line on /lab
    # (questions -> picks -> gate -> survived) counts his rooms' verdicts only.
    from qa import lab_report
    judged = rows + [{"type": "verdict", "room": "STR-0002", "verdict": "survived",
                      "at": _t(10)}]
    said = lab_report._nexus([], [], judged)
    assert (said["survived"], said["refuted"]) == (0, 0), said
