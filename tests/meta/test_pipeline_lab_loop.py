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
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
def test_the_question_cap_is_a_rolling_day_not_a_session():
    """Twenty-four a day, counted over the last twenty-four hours.

    Per session it was eight, and a session is whatever was opened last: a
    loop ticking every twenty minutes reached eight before lunch, and opening
    a new session to get past it would have been the reset nobody meant.
    """
    rows = [_question("NEX-1", NOW - timedelta(hours=30)),
            _question("NEX-2", NOW - timedelta(hours=23)),
            _question("NEX-3", NOW - timedelta(minutes=5)),
            {"type": "answer", "id": "NEX-3", "at": NOW.isoformat()}]
    assert lab.asked_within(rows, NOW) == 2, (
        "a question thirty hours old still counted against today")

    cap = lab.CAPS["questions_per_day"]
    may, why = lab.may_ask(asked=cap - 1, pass_running=False)
    assert may, why
    may, why = lab.may_ask(asked=cap, pass_running=False)
    assert not may and str(cap) in why and "24 h" in why, why
    may, why = lab.may_ask(asked=0, pass_running=True)
    assert not may and "deep pass" in why.lower(), why

    for gone in ("questions_per_session", "questions_per_night",
                 "new_rooms_per_session"):
        assert gone not in lab.CAPS, (
            f"{gone} is still a cap: a per-session count is the one the loop "
            f"exhausts or resets")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_waits_for_the_last_one_the_floor_and_their_backoff():
    """The night kept its pace in memory; a tick is a new process every twenty
    minutes, so the pace is read off the diary -- or `lab.py ask` from a loop
    would ask on every tick, over an answer still in flight."""
    def q(ident, minutes):
        return _question(ident, NOW - timedelta(minutes=minutes))

    def a(ident, minutes, kind="answer", **extra):
        return {"type": kind, "id": ident,
                "at": (NOW - timedelta(minutes=minutes)).isoformat(), **extra}

    may, why = lab.may_ask_now([q("NEX-1", 5)], NOW)
    assert not may and "NEX-1" in why, why

    may, why = lab.may_ask_now([q("NEX-1", 15), a("NEX-1", 2)], NOW)
    assert not may and "20" in why, why

    may, why = lab.may_ask_now([q("NEX-1", 30), a("NEX-1", 22)], NOW)
    assert may, why

    may, why = lab.may_ask_now(
        [q("NEX-1", 60), a("NEX-1", 30, kind="gave_up", status="failed",
                           retry_after_s=3600)], NOW)
    assert not may and "wait" in why, why


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
def test_the_room_cap_is_a_rolling_day_and_counts_rooms_opened_earlier(
        tmp_path, monkeypatch):
    """Ten new rooms a day: fifty running over a five-day window is ten a day.

    The rooms opened earlier TODAY count, or every tick would get ten of its
    own -- the per-session cap's reset, one level down.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    cap = lab.CAPS["new_rooms_per_day"]
    earlier = cap - 2
    cards = [_card(n) for n in range(earlier + 6)]
    answers = [{"type": "answer", "id": f"NEX-{n:04d}",
                "at": (NOW - timedelta(hours=1)).isoformat(),
                "text": _whole(cards[n])} for n in range(len(cards))]
    _launchpad(scripts_lab, tmp_path, monkeypatch, answers,
               live={c: _basket("BTC", "ETH") for c in cards},
               readings={("BTC", "ETH"): (6.5, 1.3)})
    import qa.rooms as qa_rooms
    for n in range(earlier):
        qa_rooms.open_strategy(f"NEX-{n:04d}", f"earlier {n}")

    did = scripts_lab.night_promote()

    opened = qa_rooms.strategies(qa_rooms.load())
    assert did["rooms"] == cap - earlier, (
        f"{did['rooms']} opened on top of {earlier} earlier today, against a "
        f"cap of {cap} a day")
    assert len(opened) == cap
    assert any("a day" in line for line in did["held"]), did["held"]


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
def test_fifty_rooms_fit_under_the_ceiling(tmp_path, monkeypatch):
    """[operator 2026-09-12] fifty at once. The ceiling is 60% of the book, so a
    room may take 1.2% of it, split across its cards.

    The negative control is the stake it replaces: 2% of what is free for EACH
    card, which runs a mix of one-, two- and three-card rooms into the 60%
    ceiling well before twenty -- and the laboratory would have read that as
    "the book is full" with thirty experiments still owed.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)

    placed, deployed = _fill(scripts_lab._leg_stakes)
    assert placed == lab.CAPS["running_experiments"], (
        f"{placed} rooms fit, against the {lab.CAPS['running_experiments']} "
        f"the operator asked for")
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


def _launchpad(scripts_lab, tmp_path, monkeypatch, answers, live, readings):
    """night_promote with their card door and their backtest stubbed, the
    sender stubbed, and everything else real."""
    _write(tmp_path, "nexus.jsonl", answers)
    _write(tmp_path, "paper.jsonl", [{"type": "after", "id": "TRD-0001",
                                      "sim_balance_usdc": "100000"}])
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    monkeypatch.setattr(scripts_lab, "card_baskets", lambda: [])

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
    paper.buy = lambda card, usdc, *a, **k: sent.append((card, usdc)) or {}
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: paper if n == "paper" else real(n))
    return sent, calls


def _basket(*symbols):
    return {"legs": [{"symbol": s, "weight": 1.0 / len(symbols)}
                     for s in symbols], "tradeable": True, "title": "t"}


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
    assert all(fees for _, _, fees in calls), "a gate that ignores fees"
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
    full = scripts_lab._leg_stakes(100000.0, 0.0, 1)[0]
    assert sent[0][1] <= full / 2 + 0.01, sent
    import qa.rooms as qa_rooms
    rows = qa_rooms.load()
    (room,) = qa_rooms.strategies(rows)
    criterion = qa_rooms.acceptance_of(rows, room["id"])
    assert "backtest" in criterion["why"].lower(), criterion["why"]
