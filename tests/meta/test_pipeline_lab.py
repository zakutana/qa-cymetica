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
  * **a cap on questions and rooms.** Nexus's own guide: an open-ended night
    "drifts, burns calls, and gives you no way to judge what it found".

The tools the ground-truth lane calls are checked against components.yaml
rather than by calling them: a test that reaches the vendor to prove a
classification would be the thing the classification exists to stop.
"""

from __future__ import annotations

import json
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
    conversation that happened in a browser. The day's CAP is the other way
    round and stays -- `asked_within` counts "whoever asked them", which is
    deliberate and documented, because the cap is about how much of their
    time we take in a day and the operator's questions take some of it.

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

    # The cap is the other half and it still counts it.
    assert lab.asked_within(recorded, now) == 1, (
        "the day's cap is about how much of their time we take, and a "
        "question the operator put to them takes some of it")

    # A question of OURS at the same moment still holds the floor shut --
    # answered, so it is the FLOOR refusing and not the in-flight rule, which
    # fires one step earlier and would have hidden this.
    ours = [{"type": "question", "id": "NEX-0101", "at": now.isoformat()},
            {"type": "answer", "id": "NEX-0101", "at": now.isoformat(),
             "text": "..."}]
    may, why = lab.may_ask_now(ours, now)
    assert not may and "floor" in why, why


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
    # it learned. The same pattern as `running_experiments == 50` above.
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
    may, why = lab.may_ask(asked=0, pass_running=True)
    assert not may and "deep pass" in why.lower(), why

    may, why = lab.may_ask(asked=lab.CAPS["questions_per_day"],
                           pass_running=False)
    assert not may and str(lab.CAPS["questions_per_day"]) in why, why

    may, _ = lab.may_ask(asked=1, pass_running=False)
    assert may


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

    ok, why = lab.affordable(1_000, free_cash=free,
                             running=lab.CAPS["running_experiments"])
    assert not ok and "running" in why.lower(), why
    assert lab.CAPS["running_experiments"] == 50

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

    Both ends are checked: the `close` subcommand and the night's own close.
    The night matters more -- it runs unattended for hours and writes the most.

    The archive is stubbed here so the assertion is about the CALL. That it
    writes beside the state it archives, rather than into this repository, is
    test_the_archive_follows_the_state_it_archives below -- which is the bug
    this very call introduced: the suite ran, night() archived a tmp_path, and
    the committed audits/lab/lab.jsonl came back modified.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
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
    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 23, 30, tzinfo=zone))
    scripts_lab.night(
        "23:45", clock=clock, sleep=clock.sleep,
        actions={"pass": lambda: False, "backoff": lambda: None,
                 "cycle": lambda: {"polled": []}, "truth": lambda: [],
                 "ask": lambda concept, question: {"id": "NEX-1"}},
        out=lambda *a: None)
    assert calls == ["snapshot"], (
        "a night wrote all night and archived none of it")


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
    paper.buy = lambda *a, **k: sent.append(a) or {"stub": True}
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

    # The question floor is no longer two hours: their side sets the pace when
    # it is down, and when it is up we should not be throttling ourselves.
    assert lab.NIGHT["ask_seconds"] <= 20 * 60
    soon = lab.night_tick({**state, "last_ask": now - timedelta(minutes=25)}, now)
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
    # was right and the expectation was not.
    assert round(said["return_pct"], 2) == 4.0, said
    assert said["max_drawdown_pct"] <= 5.0
    assert said["formula"], "a verdict records the formula that produced it"


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
    is positive. A card that rose 1% while the benchmark rose 4% is refuted."""
    now = "2026-09-07T01:00:00+00:00"
    series = {
        "card-a": _series("2026-09-05T00:00:00+00:00",
                          [100, 100.25, 100.5, 100.75, 101], hours=12),
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
    assert all(abs(r - 10.0) < 1e-6 for r in returns["STR-0001"]), returns

    # A bear leg's return is flipped, and a two-leg room is share-weighted.
    rows.append({"type": "plan", "room": "STR-0001", "at": "t3",
                "legs": [{"card": "c1", "side": "bear", "share": 0.5},
                         {"card": "c2", "side": "bull", "share": 0.5}]})
    (tmp_path / "rooms.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    history["c2"] = history["c1"]  # identical series, opposite leg side
    mixed = scripts_lab.open_book_returns(
        now=now, history=lambda card: history.get(card, []))
    assert all(abs(r) < 1e-6 for r in mixed["STR-0001"]), (
        f"+10% bull and -10% (flipped bear) at equal share should cancel: "
        f"{mixed}")


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


class _Clock:
    """Wall time the test moves. A night paced by a fake clock runs in
    milliseconds; a night paced by the real one could not be tested at all."""

    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_night_and_the_loop_share_one_cap_per_day():
    """There were two caps until 2026-09-19 -- eight a session, twelve a
    night -- because a night was long and a session had a person waiting
    through it. A loop that ticks all day is neither, and the arithmetic of a
    rolling day covers both: whatever asked a question in the last 24 hours,
    it counts."""
    cap = lab.CAPS["questions_per_day"]
    may, why = lab.may_ask(asked=cap - 1, pass_running=False)
    assert may, why

    may, why = lab.may_ask(asked=cap, pass_running=False)
    assert not may and str(cap) in why, why

    may, why = lab.may_ask(asked=0, pass_running=True)
    assert not may and "deep pass" in why.lower(), why


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

    # Inside every floor: five minutes since the last question (the floor came
    # down to twenty on 2026-09-12), five since the last cycle, an hour since
    # the ranking, and nothing left to walk.
    fresh = {**state, "last_cycle": now - timedelta(minutes=5),
             "last_truth": now - timedelta(hours=1),
             "last_ask": now - timedelta(minutes=5)}
    plan = lab.night_tick(fresh, now)
    assert plan["do"] == [] and plan["skipped"] == "too soon"

    plan = lab.night_tick({**fresh, "last_ask": now - timedelta(hours=3)}, now)
    assert plan["do"] == ["ask"]

    plan = lab.night_tick({**fresh, "last_ask": now - timedelta(hours=3),
                           "asked": lab.CAPS["questions_per_day"]}, now)
    assert plan["do"] == [] and plan["skipped"] == "cap"

    plan = lab.night_tick({**fresh, "last_ask": now - timedelta(hours=3),
                           "candidates": []}, now)
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
    assert one == now + timedelta(seconds=lab.NIGHT["ask_seconds"]) - timedelta(minutes=10)

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

    held = lab.night_tick({"asked": 0, "candidates": ["bt-x"],
                           "hold_until": now + timedelta(hours=1)}, now)
    assert "ask" not in held["do"] and held["skipped"] == "backoff", (
        "a backoff holds the question, not the whole tick -- answers already "
        "in flight are still picked up while their side is down")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_night_ends_at_its_deadline_paced_and_counted(tmp_path, monkeypatch):
    """The whole of F7 in one run: it stops by itself, it asks at their pace,
    it never exceeds the night's cap, and what it did is on the record for the
    morning."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 23, 30, tzinfo=zone))
    asked, cycles, truths = [], [], []

    def _truth():
        truths.append(clock())
        # MORE concepts than the cap allows. Six was the fixture until
        # 2026-09-12 and `_candidates` drops anything already asked, so the
        # night ran out of subjects at six against a cap of twelve -- both cap
        # assertions below were satisfied by the fixture rather than by the
        # cap, and three readers each deleted the cap branch from `night_tick`
        # and watched this stay green.
        return [{"strategy": f"bt-{n}", "sharpe": 5 - n, "max_drawdown": 1.0 + n,
                 "total_return": 12.0, "over": "48h"} for n in range(30)]

    def _ask(concept, question):
        asked.append((clock(), concept, question))
        return {"id": f"NEX-{len(asked)}", "status": "queued"}

    # The cap is per rolling day since 2026-09-19, and a day's questions asked
    # BEFORE the night count against it -- so the day arrives with all but
    # eight spent, and eight is what the night may still ask. Without the
    # preload a 7.5-hour night at the 20-minute floor asks 23 against 24 and
    # the cap is never what stops it.
    already = lab.CAPS["questions_per_day"] - 8
    did = scripts_lab.night(
        "07:00", clock=clock, sleep=clock.sleep,
        actions={"pass": lambda: False, "backoff": lambda: None,
                 "cycle": lambda: cycles.append(clock()) or {"polled": []},
                 "truth": _truth, "ask": _ask,
                 "asked_today": lambda: already},
        out=lambda *a: None)

    assert clock() >= datetime(2026, 9, 13, 7, 0, tzinfo=zone), "it stopped early"
    assert clock() < datetime(2026, 9, 13, 7, 30, tzinfo=zone), (
        "it ran past the hour they named")
    assert len(asked) == lab.CAPS["questions_per_day"] - already, (
        f"{len(asked)} questions on top of {already} already asked today, "
        f"against a cap of {lab.CAPS['questions_per_day']}: with thirty "
        f"concepts on offer the cap is the only thing that can stop it, so "
        f"this is the cap measured rather than the fixture running dry")
    assert did["skipped"]["cap"] > 0, (
        "the night never once refused a question for the cap, so the branch "
        "that enforces it was never reached")
    gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(asked, asked[1:])]
    assert all(gap >= 20 * 60 for gap in gaps), gaps
    # One ask per ten ticks at the very most: 20 minutes against a 2-minute
    # tick. Stated as a RATIO rather than a count, because the count is now
    # the cap's and this assertion is the pace's -- two different claims that
    # were sharing one number before.
    assert did["ticks"] > 200, did["ticks"]
    assert len(asked) * 10 <= did["ticks"], (
        f"{len(asked)} questions over {did['ticks']} ticks: the pace is the "
        f"question clock, not the tick")
    assert len({concept for _, concept, _ in asked}) == len(asked), (
        "it asked about the same concept twice")
    assert all(q.strip().endswith("?") or "?" in q for _, _, q in asked)
    assert len(cycles) > len(asked), "answers are picked up between questions"
    assert 1 <= len(truths) <= 3, truths

    assert did["asked"] == len(asked) and did["ticks"] > 0
    assert did["skipped"]["pass"] == 0
    assert lab.open_sessions() == [], "the night left its session open"
    closed = lab.last_close()
    assert closed["mode"] == "night"
    assert closed["did"]["asked"] == len(asked)
    assert 0 < len(closed["lessons"]) <= lab.MAX_LESSONS
    assert closed["next"], "the morning needs the ids worth a room"
    assert any("NEX-" in item for item in closed["next"])

    summary = scripts_lab.status()
    assert "night" in summary.lower() and str(len(asked)) in summary, summary


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_night_with_nexus_dead_still_searches_all_night(tmp_path, monkeypatch):
    """The acceptance for the rebuilt night: their side being down stops the
    questions and nothing else. Backtests are reads, they cost only their rate
    limit, and a night that stops walking because Nexus is quiet is the night
    the operator went after."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 23, 30, tzinfo=zone))
    walked, asked = [], []
    moves = [{"legs": [], "period": 30, "why": f"m{n}"} for n in range(400)]

    def _search(bite):
        walked.extend(bite)
        return {"asked": len(bite), "known": 0, "failed": 0}

    did = scripts_lab.night(
        "07:00", clock=clock, sleep=clock.sleep,
        actions={"pass": lambda: False,
                 # Their side down, and it never comes back tonight.
                 "backoff": lambda: clock() + timedelta(hours=9),
                 "cycle": lambda: {}, "truth": lambda: [],
                 "ask": lambda slug, question: asked.append(slug),
                 "search": _search, "moves": lambda: list(moves)},
        out=lambda *a: None)

    assert asked == [], "it asked while their own failure said to wait"
    assert did["skipped"]["backoff"] > 0, did["skipped"]
    assert len(walked) == len(moves), (
        f"only {len(walked)} of {len(moves)} moves were walked in eight hours")
    assert did["backtests"] == len(moves)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_interrupted_night_still_closes_its_session(tmp_path, monkeypatch):
    """Ctrl-C is how the operator stops it. A session left open makes the next
    laboratory inherit an unfinished night, and the reminder rule then nags
    about a night that is long over."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 23, 30, tzinfo=zone))

    def _stop():
        raise KeyboardInterrupt

    did = scripts_lab.night(
        "07:00", clock=clock, sleep=clock.sleep,
        actions={"pass": lambda: False, "backoff": lambda: None,
                 "cycle": _stop, "truth": lambda: [], "ask": lambda c, q: {}},
        out=lambda *a: None)

    assert did["stopped"] == "interrupted"
    assert lab.open_sessions() == []
    assert lab.last_close()["did"]["stopped"] == "interrupted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_night_that_crashes_still_closes_its_session(tmp_path, monkeypatch):
    """Ctrl-C is not the only way a night ends early. Every tick reads files
    another process writes -- the deep pass's own notebook, nexus.jsonl -- and
    one half-written line at three in the morning is a raised exception, not a
    keyboard. Left open, the morning's `status` says OPEN, the reminder nags
    about a night that is long over, and `lab.py night` refuses to start the
    next one. The traceback still reaches their terminal; the session does not
    stay open to buy it.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 23, 30, tzinfo=zone))
    looks = {"n": 0}

    def _pass():
        looks["n"] += 1
        if looks["n"] >= 3:
            raise RuntimeError("deep-pass-progress.json was half written")
        return False

    with pytest.raises(RuntimeError):
        scripts_lab.night(
            "07:00", clock=clock, sleep=clock.sleep,
            actions={"pass": _pass, "backoff": lambda: None,
                     "cycle": lambda: {}, "truth": lambda: [],
                     "ask": lambda slug, question: {}},
            out=lambda *a: None)

    assert lab.open_sessions() == [], "the crash left the night open"
    closed = lab.last_close()
    assert closed["did"]["stopped"].startswith("crashed"), closed["did"]
    assert "half written" in closed["did"]["stopped"]


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
    assert "def night(" in night and len(night) > 2000, "the slice moved"

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

    # [operator 2026-09-12] *"Jasne ze v noci muze spoustet."* So this stopped
    # being "no hand at all" and became "only the braked one". Filing and
    # committing are still out: the night finds, the morning tells the vendor.
    for hand in ("submit", "findings", "subprocess", "withdraw", "prereg"):
        assert hand not in reached, (
            f"the night can reach {hand!r}: it researches and launches on "
            f"paper, it does not talk to the vendor")

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

    def _gate_then_spend(node) -> bool:
        for block in [b for n in ast.walk(node)
                      for b in (getattr(n, "body", []), getattr(n, "orelse", []))
                      if isinstance(b, list)]:
            gate = next((i for i, s in enumerate(block)
                         if _calls(s, "affordable")), None)
            spend = next((i for i, s in enumerate(block)
                          if _calls(s, "buy")), None)
            if gate is not None and spend is not None and gate < spend:
                return True
        return False

    spenders = [node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and _calls(node, "buy")]
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
def test_the_nights_own_doors_are_the_real_ones(tmp_path, monkeypatch):
    """The loop above is driven with fakes, which leaves the wiring untested --
    and a mistyped default would surface at three in the morning on their
    machine, hours into a night that then does nothing. A clock already past
    the deadline builds the real doors and runs no tick, so this reaches
    nothing over the network."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    zone = timezone(timedelta(hours=2))
    start = datetime(2026, 9, 12, 23, 30, tzinfo=zone)
    readings = iter([start, start + timedelta(hours=9)])

    did = scripts_lab.night("07:00", clock=lambda: next(readings),
                            sleep=lambda seconds: None, out=lambda *a: None)

    assert did["ticks"] == 0, "a tick ran and would have called their API"
    assert lab.open_sessions() == []
    assert lab.last_close()["mode"] == "night"


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
def test_the_night_keeps_searching_after_the_first_queue_runs_out(
        tmp_path, monkeypatch):
    """[operator] *"celou noc budete delat backtesty nonstop"* — and it did not.

    `night_moves()` is built ONCE and only ever sliced. Measured on the real
    repository: 168 moves, 30 a tick, a tick every two minutes — **six ticks,
    twelve minutes** of a fourteen-hour night, and then `pending` sits at 0 and
    `night_tick` stops scheduling `search` until dawn. The second night is
    worse: the walk is deterministic, so it rebuilds the same 168 and the
    register answers "already measured" for nearly all of them.

    An independent reviewer found it; two others read "search runs every tick"
    and called it delivered. The tick is uncapped, the SUPPLY was not, and the
    queue length is what settles it.

    The refill is also the better search. The first queue is the neighbourhood
    of THEIR cards; a refill is the neighbourhood of whatever has actually
    scored best so far, so each round climbs instead of restarting.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 20, 0, tzinfo=zone))
    walked, refills = [], []

    searched_at = []

    def _search(bite):
        searched_at.append(clock.now)
        walked.extend(bite)
        return {"asked": len(bite), "known": 0}

    def _refill():
        refills.append(len(refills))
        return [{"kind": "window", "period": 30, "legs": [], "why": f"r{n}"}
                for n in range(40)]

    did = scripts_lab.night(
        "06:00", clock=clock, sleep=clock.sleep,
        actions={"pass": lambda: False, "backoff": lambda: None,
                 "cycle": lambda: {"polled": []}, "truth": lambda: [],
                 "ask": lambda concept, question: {"id": "NEX-1"},
                 "search": _search, "refill": _refill,
                 "moves": lambda: [{"kind": "window", "period": 30,
                                    "legs": [], "why": f"seed{n}"}
                                   for n in range(30)]},
        out=lambda *a: None)

    assert refills, "the queue emptied and the night stopped searching"
    assert len(walked) > 30 * 4, (
        f"only {len(walked)} move(s) walked in a ten-hour night")
    assert did["backtests"] == len(walked)

    # WHEN, not only how many. `len(walked) > 120` is satisfied by a night that
    # refills three times and then stops: 30 + 3x40 = 150 over about seven
    # ticks, and nothing for the remaining ten hours. All three assertions above
    # stay green on exactly the defect this docstring quantifies -- "twelve
    # minutes of a fourteen-hour night". So the last search has to land near the
    # end of the night, which is the property, and it is the one a cap on
    # refills breaks. 3/3, deep pass of 2026-09-13.
    assert searched_at, "the night never searched at all"
    started, ended = searched_at[0], clock.now
    span = (ended - started).total_seconds()
    idle = (ended - searched_at[-1]).total_seconds()
    assert span > 0 and idle <= span * 0.1, (
        f"the night's last search was {idle / 3600:.1f} h before dawn, out of "
        f"{span / 3600:.1f} h -- it walked {len(walked)} moves and then waited")


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
def test_the_night_reaches_the_launch_step_at_all(tmp_path, monkeypatch):
    """[operator 2026-09-12] *"Jasne ze v noci muze spoustet."*

    The night researched all night and placed nothing, which was a narrowing I
    put in a plan they do not read. This is the wiring: `night()` reaches the
    promote step and counts what it returns.

    **Renamed 2026-09-13 (3/3), and the old name is the finding.** It read
    `..._on_paper_from_a_nexus_answer_and_nothing_else`, claiming the road (a
    room opens from a whole Nexus answer, never from a basket of ours) and the
    brakes (`affordable`, paper only, nothing while a deep pass runs) -- and
    `promote` here is a stub that returns `{"rooms": 1, "orders": 1}` whatever
    it is handed. A `night_promote` that opened a room from our own basket,
    skipped `affordable` and posted live would have kept every assertion below
    green. The road and the brakes are really held by
    tests/meta/test_pipeline_night_spend.py, which drives the real function;
    this name was borrowing their credit. Same shape as A04 of the 2026-09-12
    pass, which was ruled real and fixed by a rename.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    bought, rooms_opened = [], []

    def _promote():
        rooms_opened.append("STR-0001")
        bought.append({"card": "c1", "usdc": 1700.0})
        return {"rooms": 1, "orders": 1, "held": []}

    zone = timezone(timedelta(hours=2))
    clock = _Clock(datetime(2026, 9, 12, 22, 0, tzinfo=zone))
    did = scripts_lab.night(
        "23:00", clock=clock, sleep=clock.sleep,
        actions={"pass": lambda: False, "backoff": lambda: None,
                 "cycle": lambda: {"polled": []}, "truth": lambda: [],
                 "ask": lambda concept, question: {"id": "NEX-1"},
                 "search": lambda bite: {"asked": len(bite), "known": 0},
                 "refill": list, "moves": list, "promote": _promote},
        out=lambda *a: None)

    assert did["orders"] >= 1, "the night launched nothing"
    assert did["rooms"] >= 1
    assert bought, "no paper order was placed"


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
