"""A card that says it can be bought right now is one whose basket can be priced.

The contract is the card's own `tradeability` block, on every
`GET /api/v1/event-cards/{id}`:

    tradeable_now: "True when a position can be opened on this card RIGHT NOW
    via POST /buy, /sell or /short (paper or live per your account mode);
    False carries trading_blocked_reason. This is the only trade gate."

**What was seen when this was written** (2026-10-12): card
8ffd61fa-f469-45be-a717-a4dcfe9f9508 ("Gem Screener L2", our own card) read
`status: live`, `tradeable_now: true`, `trading_blocked_reason: null` -- at
16:25:40 and again at 16:48:15 UTC, read just before each order -- and a paper
`POST /api/v1/event-cards/{id}/buy` of 593.63 USDC answered HTTP 400
`{"detail": "Basket is not fully priceable right now -- try again shortly"}`
twice, TRD-0113 at 16:25:45 and TRD-0115 at 16:48:39, 23 minutes apart, with no
position created and the account unchanged. TRD-0114, on another card, filled
200 in the same minute as the first.

This is not #117. That one was a 500 "Buy failed"; its report says a 4xx that
names its reason satisfies it, and the fix arrived as exactly that kind of
answer. What is left is the answer itself: the gate says true and carries no
reason, and the platform then refuses because it cannot price the basket.

**This check places no order.** It reads what `scripts/paper.py` recorded. A
subject is a buy whose card read `tradeable_now: true` with no blocked reason
at the buy, and which a 400 refused because the price or the basket's pricing
was unavailable (a 409, "not found" or any other 4xx is a different thing).
Each card is judged by its NEWEST attempt, as #117 is: a buy that landed since
is the fix; a card that no longer reads tradeable_now true, or cannot be read,
cannot show the defect or its fix and is unmeasured. A buy recorded before
2026-09-22 carries no card read, so it is never a subject -- the 400 "This
card's price is not currently available" of 2026-09-13 (TRD-0007) is cited in
the report only as the earlier wording of the same refusal.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
CARD = "/api/v1/event-cards/{card}"

# Both wordings seen, and nothing broader: a refusal of another kind (a stale
# card, a closed market, "not found") is the gate working or another defect.
_UNPRICED = ("not fully priceable", "price is not currently available")


def _paper():
    spec = importlib.util.spec_from_file_location(
        "paper_buys_priced", REPO / "scripts" / "paper.py")
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


def _accepted(attempt: dict) -> bool:
    status = attempt["status"]
    return (isinstance(status, int) and 200 <= status < 300
            and attempt["outcome"] == "accepted")


def _unpriced_refusal(attempt: dict) -> bool:
    return (attempt["status"] == 400
            and any(w in attempt["response"].lower() for w in _UNPRICED))


def _read_tradeable(attempt: dict) -> bool:
    """The card said tradeable_now true, with no reason, when the order went."""
    then = attempt.get("card_before")
    return (isinstance(then, dict) and then.get("tradeable_now") is True
            and not then.get("trading_blocked_reason"))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_that_reads_tradeable_now_can_be_priced(rest_trusted):
    """Every card refused as unpriceable while reading tradeable, by its newest buy."""
    attempts = buy_attempts(_paper().load())
    struck = []
    for attempt in attempts:
        if (_unpriced_refusal(attempt) and _read_tradeable(attempt)
                and attempt["card"] not in struck):
            struck.append(attempt["card"])
    if not struck:
        raise Inconclusive("no paper buy has been refused as unpriceable while "
                           "its card read tradeable_now true")

    breaches, unmeasured, fixed = [], [], []
    for card_id in struck:
        history = [a for a in attempts if a["card"] == card_id]
        latest = history[-1]
        if _accepted(latest):
            fixed.append(latest)
            continue
        if not (_unpriced_refusal(latest) and _read_tradeable(latest)):
            unmeasured.append(f"{card_id}: its newest buy {latest['id']} came back "
                              f"{latest['status']} {latest['response']}, "
                              f"not an unpriced refusal on a tradeable read")
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
        breaches.append((card_id, latest, card, [
            a for a in history if _unpriced_refusal(a) and _read_tradeable(a)]))

    if breaches:
        card_id, latest, card, same = breaches[0]
        conclude(Measurement(
            verdict="failed",
            reason=(f"card {card_id} reads status {card.get('status')}, "
                    f"tradeable_now true, trading_blocked_reason "
                    f"{card.get('trading_blocked_reason')} -- at the buy as well -- "
                    f"and our paper buy of it was refused HTTP {latest['status']} "
                    f"{latest['response']} ({len(same)} time(s): "
                    f"{', '.join(a['id'] + ' ' + a['at'][11:19] for a in same)}, "
                    f"newest {latest['id']})"
                    + (f"; {len(breaches) - 1} other card(s) the same"
                       if len(breaches) > 1 else "")),
            left=latest["status"], right="2xx",
            population={"refusals_on_card": same,
                        "other_cards": [c for c, _, _, _ in breaches[1:]],
                        "card": {k: card.get(k) for k in (
                            "status", "tradeable_now", "trading_blocked_reason",
                            "pw_live", "current_index", "share_price_usd")},
                        "legs": [(b.get("symbol"), b.get("weight"))
                                 for b in card.get("basket") or []]},
            sources={"contract": "GET /api/v1/event-cards/{id} tradeability.tradeable_now: "
                                 "'True when a position can be opened on this card RIGHT "
                                 "NOW ... This is the only trade gate.'",
                     "log": "state/paper.jsonl (TRD intent / outcome, with evidence ids)"}))
        return
    if unmeasured:
        raise Inconclusive("; ".join(unmeasured))
    conclude(Measurement(
        verdict="passed",
        reason=("every card refused as unpriceable while reading tradeable has "
                "since taken a paper buy: "
                + ", ".join(f"{a['card']} ({a['id']})" for a in fixed)),
        left=[a["status"] for a in fixed], right="2xx",
        population={"newest_on_struck_cards": fixed},
        sources={"log": "state/paper.jsonl"}))
