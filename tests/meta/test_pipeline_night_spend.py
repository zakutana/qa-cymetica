"""The one path in this repository that spends money with nobody watching.

[operator 2026-09-12] said the night may launch. Every other brake in
`test_pipeline_lab.py` guards a night that only read; this file guards the
night that buys, and it drives the REAL `night_promote` rather than the stub
the loop test uses. It is separate from its siblings for that reason: those
hold the laboratory's brakes in general, these hold the one function where a
mistake costs money, and the fixtures they need — a book, a diary of answers,
a stubbed sender — are its own.

Every defect below was found by a reviewer on the night the feature landed,
and every one of them was live in the committed code:

  * the stake was rounded UP past the cap it is computed from, so on the real
    balance the night refused every order it ever tried to place;
  * the room was opened BEFORE the money check, so a refusal consumed the
    answer for the morning as well;
  * a room was opened with no acceptance criterion, which no verdict can ever
    reach and no experiment count can ever see;
  * `new_rooms_per_session` was enforced nowhere in the repository;
  * one card named in three answers was bought three times;
  * an uncaught RoomError discarded the return value, so orders that WERE
    placed were reported as none.

The sender is always stubbed. A test that proves a brake by letting the order
through is the defect it exists to stop.
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
CARD = "30408a4b-8717-4fc7-a91a-9a6724cadd7e"


def _scripts_lab(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)
    import qa.rooms

    importlib.reload(qa.rooms)
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_spend", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _answers(tmp_path, rows):
    (tmp_path / "nexus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _book(tmp_path, free):
    (tmp_path / "paper.jsonl").write_text(
        json.dumps({"type": "after", "id": "TRD-0001",
                    "sim_balance_usdc": str(free)}) + "\n", encoding="utf-8")


def _whole(card):
    return "Buy " + card + " bull, sized small. " + ("reasoning. " * 40)


def _wire(scripts_lab, monkeypatch, cards):
    """A night that can see those cards, with the sender stubbed.

    Since 2026-09-19 a card is read from their API and backtested before a
    room opens (`_card_live`, `_gate`), so both are stubbed here to a card
    that exists and a basket that measured well -- the brakes this file holds
    are the ones AFTER the gate. The gate itself is tests/meta/
    test_pipeline_lab_loop.py's.
    """
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)
    monkeypatch.setattr(scripts_lab, "card_baskets",
                        lambda: [{"card": c, "legs": []} for c in cards])
    basket = {"legs": [{"symbol": "BTC", "weight": 0.5},
                       {"symbol": "ETH", "weight": 0.5}],
              "tradeable": True, "title": "a card"}
    monkeypatch.setattr(scripts_lab, "_card_live",
                        lambda card: basket if card in cards else None)
    monkeypatch.setattr(scripts_lab, "backtest",
                        lambda legs, period_days=30, **_: {
                            "cached": True, "p": period_days, "r": 6.0,
                            "s": 1.2, "d": 2.0})
    sent = []
    real = scripts_lab._sibling
    paper = real("paper")
    paper.buy = lambda *a, **k: sent.append(a[0]) or {"stub": True}
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda n: paper if n == "paper" else real(n))
    return sent


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stake_never_exceeds_the_ceiling_it_is_computed_from(
        tmp_path, monkeypatch):
    """`round(free * 0.02, 2)` rounds UP past the unrounded ceiling.

    Measured on the balance actually in state/paper.jsonl: free 89000.96,
    stake 1780.02, ceiling 1780.0192 — refused, with a message reading "1780 is
    more than 2% of the 89001 free (1780)" because both sides round for
    display. `_free_cash` does not move while nothing is bought, so it is every
    order of every night. Only a balance whose 2% lands exactly on a cent
    passes, and 100000.00 does, which is why no fixture caught it.

    A stake is money: floor it.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)

    for free in (100000.00, 99000.96, 92236.82, 89000.96, 1.0, 0.0):
        stake = scripts_lab._stake(free)
        assert stake <= free * lab.CAPS["share_of_free_cash"] + 1e-9, (
            f"a stake of {stake} is over its own ceiling on {free} free")
        if stake > 0:
            ok, why = lab.affordable(stake, free, 0, deployed=0.0)
            assert ok, f"the cap refused the stake the cap itself computed: {why}"

    assert scripts_lab._stake(None) == 0.0, "an unreadable book is not a stake"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refused_answer_is_left_for_the_morning_and_not_spent(
        tmp_path, monkeypatch):
    """The compounding half, and the worse one.

    `open_strategy` ran BEFORE the money check, so a refusal opened a room,
    logged "the morning reads it", and broke. That row puts the origin in
    `linked` for every later cycle AND makes `open_strategy` raise for the
    morning too. The answer is not held, it is spent — and a night that could
    afford nothing would have consumed every answer it touched.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _answers(tmp_path, [{"type": "answer", "id": "NEX-0001",
                         "at": "2026-09-12T22:00:00+00:00",
                         "text": _whole(CARD)}])
    # No book at all: `_free_cash()` reads None and `affordable` refuses with
    # "the book could not be read" -- rule 8, and the case where spending
    # anyway would be worst. With the stake floored the per-experiment cap can
    # no longer refuse a stake it computed itself, so the unreadable book is
    # the honest refusal to test here.
    sent = _wire(scripts_lab, monkeypatch, [CARD])

    did = scripts_lab.night_promote()

    assert sent == [] and did["orders"] == 0
    assert did["rooms"] == 0, "a refusal opened a room and spent the answer"
    assert did["held"], "it refused and said nothing about why"

    import qa.rooms as qa_rooms
    assert not qa_rooms.strategies(qa_rooms.load()), (
        "the answer is linked to a room now and the morning cannot promote it")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_night_room_carries_a_criterion_and_the_room_cap_holds(
        tmp_path, monkeypatch):
    """A room with no criterion is never graded and never closes.

    `verdicts()` skips any room whose acceptance is None, and
    `_running_experiments()` counts only `running` — so rooms opened without
    either left positions no verdict could reach, while the 50-experiment cap
    counted none of them and `_deployed` ratcheted up for every later session.

    `new_rooms_per_session` was enforced nowhere: its own definition was the
    only reference to it in the repository. It became `new_rooms_per_day` on
    2026-09-19, and the fixture offers MORE answers than the cap, or the cap
    is never what stops it.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    count = lab.CAPS["new_rooms_per_day"] + 2
    cards = [f"3040{n:04x}-8717-4fc7-a91a-9a6724cadd7e" for n in range(count)]
    _answers(tmp_path, [
        {"type": "answer", "id": f"NEX-{n:04d}",
         "at": "2026-09-12T22:00:00+00:00", "text": _whole(cards[n])}
        for n in range(count)])
    _book(tmp_path, 100000.0)
    _wire(scripts_lab, monkeypatch, cards)

    did = scripts_lab.night_promote()

    import qa.rooms as qa_rooms
    rows = qa_rooms.load()
    opened = qa_rooms.strategies(rows)
    assert len(opened) == lab.CAPS["new_rooms_per_day"], (
        f"{len(opened)} rooms against a cap of "
        f"{lab.CAPS['new_rooms_per_day']} a day")
    assert did["rooms"] == len(opened)
    assert opened, "nothing launched on a book that can clearly afford it"
    for room in opened:
        assert qa_rooms.acceptance_of(rows, room["id"]), (
            f"{room['id']} holds a position no verdict can ever reach")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_card_is_not_bought_once_per_answer_that_mentions_it(
        tmp_path, monkeypatch):
    """Nexus repeats its favourite card across answers. "Fifty experiments at
    2% each" assumed fifty different things, not one thing fifty times.

    **Bought ONCE, not "at most once".** `len(sent) == len(set(sent))` alone is
    satisfied by `sent == []`, so anything that stops the night buying at all
    turns this green while saying nothing about the defect the file records --
    a reader reintroduced the round-up at the inner call site
    (`stake = _stake(free) + 0.01`), `affordable` then refused every buy, and
    the whole of tests/meta stayed green with Nexus's most-repeated pick bought
    zero times. The sibling above anchors itself with `assert opened`; this had
    no anchor. M07, triage 2/3, deep pass of 2026-09-13.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _answers(tmp_path, [
        {"type": "answer", "id": f"NEX-000{n}",
         "at": "2026-09-12T22:00:00+00:00", "text": _whole(CARD)}
        for n in range(3)])
    _book(tmp_path, 100000.0)
    sent = _wire(scripts_lab, monkeypatch, [CARD])

    scripts_lab.night_promote()

    assert sent, (
        "nothing was bought at all on a book of 100 000 USDC and three answers "
        "naming a real card: the dedup cannot be measured on an empty list")
    assert len(sent) == len(set(sent)), (
        f"{CARD[:8]} was bought {len(sent)} times in one call")
    assert sent == [CARD], (
        f"expected exactly one order for {CARD[:8]}, got {sent}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_that_cannot_trade_does_not_park_the_cards_that_can_for_ever(
        tmp_path, monkeypatch):
    """NEX-0052 named its recommendation beside two counterexamples, one of
    them `pw_live: false`, and the untradeable one parked the whole answer
    for 27 ticks. A fresh answer still waits whole -- the plan keeps its legs
    together while there is a chance they all open -- but past
    WAIT_FOR_LEGS_HOURS the cards that pass open their room, and the one that
    cannot trade is named rather than waited for."""
    other = "7764668a-0000-4000-8000-000000000000"
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _book(tmp_path, 100000.0)
    sent = _wire(scripts_lab, monkeypatch, [CARD])
    basket = {"legs": [{"symbol": "BTC", "weight": 1.0}], "tradeable": True,
              "title": "a card"}
    monkeypatch.setattr(scripts_lab, "_card_live", lambda card: (
        basket if card == CARD else {**basket, "tradeable": False}))
    text = "Buy " + CARD + " bull. Not " + other + ". " + ("reasoning. " * 40)

    fresh = datetime.now(timezone.utc).isoformat()
    _answers(tmp_path, [{"type": "answer", "id": "NEX-0001", "at": fresh,
                         "text": text}])
    said = scripts_lab.night_promote()
    assert not sent and said["rooms"] == 0, "a fresh answer waits whole"

    old = (datetime.now(timezone.utc) - timedelta(
        hours=scripts_lab.WAIT_FOR_LEGS_HOURS + 1)).isoformat()
    _answers(tmp_path, [{"type": "answer", "id": "NEX-0001", "at": old,
                         "text": text}])
    said = scripts_lab.night_promote()
    assert sent == [CARD] and said["rooms"] == 1
    assert any(other[:8] in line for line in said["held"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_that_cannot_open_does_not_discard_what_was_already_placed(
        tmp_path, monkeypatch):
    """A short answer naming a real card passes `proposed_cards` and fails
    `open_strategy`'s whole-answer rule.

    The RoomError was uncaught, so the function exited before `return`: a probe
    placed seven orders worth 14 000 USDC and the night reported zero, every
    cycle, because the offending answer never became `linked`. state/nexus.jsonl
    already holds such an answer — NEX-0009, 168 characters. Reporting a spend
    as nothing is the failure this repository cares about most.
    """
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    cards = [f"3040{n}04b-8717-4fc7-a91a-9a6724cadd7e" for n in range(2)]
    _answers(tmp_path, [
        {"type": "answer", "id": "NEX-0001", "at": "2026-09-12T22:00:00+00:00",
         "text": _whole(cards[0])},
        {"type": "answer", "id": "NEX-0002", "at": "2026-09-12T22:01:00+00:00",
         "text": "Buy " + cards[1] + "."},
    ])
    _book(tmp_path, 100000.0)
    sent = _wire(scripts_lab, monkeypatch, cards)

    did = scripts_lab.night_promote()

    # `assert sent` FIRST, because without it the whole judgement is
    # `0 == 0`: reintroduce anything that stops the night buying -- an
    # unreadable book, a stake of zero, a brake at the inner call site -- and
    # both assertions below hold while the check says nothing about the
    # discard it is named for. The sibling above carries this line; this one
    # was left without it. M07 again, found by three readers on 2026-09-20.
    assert sent, (
        "nothing was bought at all, so 'what was already placed' is the "
        "empty set and this check cannot see the defect it exists for")
    assert did["orders"] == len(sent), (
        f"{len(sent)} order(s) placed and {did['orders']} reported")
    assert any("NEX-0002" in line for line in did["held"]), did["held"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_is_launched_while_a_deep_pass_is_running(tmp_path, monkeypatch):
    """The interlock, on the path that spends rather than on the pure function
    that only claims to cover it."""
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _answers(tmp_path, [{"type": "answer", "id": "NEX-0001",
                         "at": "2026-09-12T22:00:00+00:00",
                         "text": _whole(CARD)}])
    _book(tmp_path, 100000.0)
    sent = _wire(scripts_lab, monkeypatch, [CARD])
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: True)

    did = scripts_lab.night_promote()

    assert sent == [] and did["orders"] == 0 and did["rooms"] == 0
    assert any("deep pass" in line for line in did["held"]), did["held"]
