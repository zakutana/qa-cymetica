"""A card that says it can be bought right now takes a paper buy.

The contract is the card's own `tradeability` block, on every
`GET /api/v1/event-cards/{id}`:

    tradeable_now: "True when a position can be opened on this card RIGHT NOW
    via POST /buy, /sell or /short (paper or live per your account mode);
    False carries trading_blocked_reason. This is the only trade gate."

**What was seen when this was written** (2026-09-21): card
a4a5b71e-de11-4805-b8a3-ed9c3f8f8161 (Nexus's NEX-0059 pick, "SpaceX IPO: Top
10 Crypto Plays") read `status: live`, `tradeable_now: true`,
`trading_blocked_reason: null`, `pw_live: true`, and a paper
`POST /api/v1/event-cards/{id}/buy` of 1,189.04 USDC answered HTTP 500
`{"detail": "Buy failed"}` twice -- TRD-0010 at 17:01:28 and TRD-0011 at
17:04:10 UTC -- with no position created and the account unchanged. The same
account's buys on other cards were accepted the same day (TRD-0008, TRD-0009).
Six of the card's ten legs carry weight 0.0 (NEO, CKB, BANANA, ANKR, FIL,
ONT); that is a guess at the cause, not part of the claim.

When the platform refuses for a reason it names, it says so: TRD-0007 got a
400 "This card's price is not currently available". A 500 with "Buy failed" is
not a stated gate.

**This check places no order.** It reads what `scripts/paper.py` recorded.
Its subjects are EVERY card one of our buys got a 5xx on, each judged by the
NEWEST attempt on that card: a 5xx while it still reads `tradeable_now: true`
fails; a pass needs every one of them since accepted; a 4xx with a reason is
the gate working, and a card no longer tradeable or unreadable is unmeasured
-- both inconclusive. Until the deep pass of 2026-09-21 it judged the newest
buy of ANY card, and then only the card of the newest 5xx, so an accepted buy
of another card would have passed #117 with a4a5b71e still answering 500
(R03 and A01, 3/3 each). A card nobody tries again stays failed: a fix is
shown by a buy of the card that failed, not by the calendar.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
CARD = "/api/v1/event-cards/{card}"


def _paper():
    spec = importlib.util.spec_from_file_location(
        "paper_buys", REPO / "scripts" / "paper.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def buy_attempts(rows) -> list[dict]:
    """Every buy we attempted, with how it came back, oldest first."""
    chains: dict[str, dict] = {}
    for row in rows:
        if row.get("id"):
            chains.setdefault(row["id"], {})[row.get("type")] = row
    out = []
    for trade_id, chain in chains.items():
        intent, outcome = chain.get("intent") or {}, chain.get("outcome") or {}
        if not intent or intent.get("kind") == "close" or not outcome:
            continue
        out.append({"id": trade_id, "at": intent.get("at") or "",
                    "card": intent.get("card_id"), "usdc": intent.get("usdc"),
                    "status": outcome.get("http_status"),
                    "outcome": outcome.get("outcome"),
                    "response": str(outcome.get("response") or "")[:200],
                    "evidence_id": outcome.get("evidence_id"),
                    "card_before": intent.get("card_before")})
    return sorted(out, key=lambda a: (a["at"], a["id"]))


def _is_5xx(attempt: dict) -> bool:
    return isinstance(attempt["status"], int) and attempt["status"] >= 500


def _accepted(attempt: dict) -> bool:
    status = attempt["status"]
    return (isinstance(status, int) and 200 <= status < 300
            and attempt["outcome"] == "accepted")


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_that_reads_tradeable_now_takes_a_paper_buy(rest_trusted):
    """Every card whose buy got a 5xx, by its newest attempt, against its own tradeable_now."""
    attempts = buy_attempts(_paper().load())
    if not attempts:
        raise Inconclusive("no paper buy has been attempted")
    newest: dict[str, dict] = {}
    for attempt in attempts:
        newest[attempt["card"]] = attempt
    # A01, deep pass of 2026-09-21 (3/3): judging only the card of the newest
    # 5xx let card A 500, card B 500, B accepted pass with A never tried
    # again. Every card that ever answered 5xx is a subject, each by its own
    # newest attempt.
    struck = [card for card in newest if any(
        _is_5xx(a) for a in attempts if a["card"] == card)]
    if not struck:
        latest = attempts[-1]
        if _accepted(latest):
            conclude(Measurement(
                verdict="passed",
                reason=(f"no paper buy has answered 5xx, and the newest, "
                        f"{latest['id']} of card {latest['card']}, was accepted"),
                left=latest["status"], right="2xx",
                population={"newest": latest},
                sources={"log": "state/paper.jsonl"}))
            return
        raise Inconclusive(f"the newest paper buy, {latest['id']}, came back "
                           f"{latest['status']} {latest['response']} -- a stated "
                           f"refusal or an unread outcome, not this defect")

    breaches, unmeasured = [], []
    for card_id in struck:
        latest = newest[card_id]
        if _accepted(latest):
            continue
        if not _is_5xx(latest):
            unmeasured.append(f"{card_id}: its newest buy {latest['id']} came back "
                              f"{latest['status']} {latest['response']} -- a stated "
                              f"refusal or an unread outcome")
            continue
        # A03, deep pass of 2026-09-22: the contract is tradeable_now AT the
        # buy. paper.py records the card's gate in the intent since then;
        # a buy from before that is judged on today's read, and says so.
        then = latest.get("card_before")
        if isinstance(then, dict) and isinstance(then.get("tradeable_now"), bool):
            if then["tradeable_now"] is not True:
                unmeasured.append(f"{card_id}: it read tradeable_now false when "
                                  f"{latest['id']} was placed "
                                  f"({then.get('trading_blocked_reason')})")
                continue
            breaches.append((card_id, latest, {**then, "read": "at the buy"}))
            continue
        # Recorded at the buy, and unreadable then: what the card said when it
        # was bought is unknown, and today's read is not it (C09, deep pass of
        # 2026-09-22 evening -- it fell through and said the buy predated
        # recording). Only a buy with no record at all is judged on today.
        if isinstance(then, dict):
            unmeasured.append(f"{card_id}: the card could not be read when "
                              f"{latest['id']} was placed (HTTP "
                              f"{then.get('http_status')})")
            continue
        response = rest_trusted.get(CARD.format(card=card_id))
        if response.status_code != 200:
            unmeasured.append(f"{card_id}: the card could not be read, HTTP "
                              f"{response.status_code}")
            continue
        card = response.json() or {}
        if card.get("tradeable_now") is not True:
            unmeasured.append(f"{card_id}: no longer reads tradeable_now true "
                              f"({card.get('tradeable_now')}, "
                              f"{card.get('trading_blocked_reason')})")
            continue
        breaches.append((card_id, latest, {**card, "read": (
            "today -- the buy predates recording the card at the buy")}))

    if breaches:
        card_id, latest, card = breaches[0]
        same = [a for a in attempts if a["card"] == card_id and _is_5xx(a)]
        conclude(Measurement(
            verdict="failed",
            reason=(f"card {card_id} reads (read {card.get('read')}) status "
                    f"{card.get('status')}, "
                    f"tradeable_now true, trading_blocked_reason "
                    f"{card.get('trading_blocked_reason')}, and our paper buy of it "
                    f"answered HTTP {latest['status']} {latest['response']} "
                    f"({len(same)} time(s): "
                    f"{', '.join(a['id'] + ' ' + a['at'][11:19] for a in same)})"
                    + (f"; {len(breaches) - 1} other tradeable card(s) the same"
                       if len(breaches) > 1 else "")),
            left=latest["status"], right="2xx, or a 4xx naming its reason",
            population={"attempts_on_card": same,
                        "other_cards": [c for c, _, _ in breaches[1:]],
                        "card": {k: card.get(k) for k in (
                            "read", "status", "tradeable_now",
                            "trading_blocked_reason",
                            "pw_live", "current_index", "share_price_usd")},
                        "legs": [(b.get("symbol"), b.get("weight"))
                                 for b in card.get("basket") or []]},
            sources={"contract": "GET /api/v1/event-cards/{id} tradeability.tradeable_now: "
                                 "'the only trade gate'",
                     "log": "state/paper.jsonl (TRD intent / outcome, with evidence ids)"}))
        return
    if unmeasured:
        raise Inconclusive("; ".join(unmeasured))
    conclude(Measurement(
        verdict="passed",
        reason=(f"every card whose paper buy answered 5xx has since taken one: "
                + ", ".join(f"{c} ({newest[c]['id']})" for c in struck)),
        left=[newest[c]["status"] for c in struck], right="2xx",
        population={"newest_on_struck_cards": [newest[c] for c in struck]},
        sources={"log": "state/paper.jsonl"}))
