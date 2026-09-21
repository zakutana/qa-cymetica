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
Its subject is the card of our newest 5xx buy, and the verdict is the NEWEST
attempt on THAT card: accepted passes, a 5xx while it still reads
`tradeable_now: true` fails, a 4xx with a reason is the gate working and is
inconclusive. Until the deep pass of 2026-09-21 it judged the newest buy of
ANY card, so an accepted buy of another card -- two were accepted the day
this was found -- would have passed #117 with a4a5b71e still answering 500
(R03/A01, 3/3). A card nobody tries again stays failed: a fix is shown by a
buy of the card that failed, not by the calendar.
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
                    "evidence_id": outcome.get("evidence_id")})
    return sorted(out, key=lambda a: (a["at"], a["id"]))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_that_reads_tradeable_now_takes_a_paper_buy(rest_trusted):
    """Our newest paper buy against the card's own tradeable_now."""
    attempts = buy_attempts(_paper().load())
    if not attempts:
        raise Inconclusive("no paper buy has been attempted")
    failed = [a for a in attempts
              if isinstance(a["status"], int) and a["status"] >= 500]
    subject = failed[-1]["card"] if failed else attempts[-1]["card"]
    latest = [a for a in attempts if a["card"] == subject][-1]
    status = latest["status"]
    if isinstance(status, int) and 200 <= status < 300 and latest["outcome"] == "accepted":
        conclude(Measurement(
            verdict="passed",
            reason=(f"the newest paper buy of card {latest['card']}, {latest['id']}, "
                    f"was accepted" + (" -- the card whose buy last got a 5xx"
                                       if failed else "")),
            left=status, right="2xx",
            population={"newest_on_card": latest, "subject": subject},
            sources={"log": "state/paper.jsonl"}))
        return
    if not (isinstance(status, int) and status >= 500):
        raise Inconclusive(f"the newest paper buy of card {subject}, {latest['id']}, "
                           f"came back {status} {latest['response']} -- a stated "
                           f"refusal or an unread outcome, not this defect")

    response = rest_trusted.get(CARD.format(card=latest["card"]))
    if response.status_code != 200:
        raise Inconclusive(f"the card could not be read: HTTP {response.status_code}")
    card = response.json() or {}
    if card.get("tradeable_now") is not True:
        raise Inconclusive(f"the card no longer reads tradeable_now true "
                           f"({card.get('tradeable_now')}, "
                           f"{card.get('trading_blocked_reason')})")
    same = [a for a in attempts if a["card"] == latest["card"]
            and isinstance(a["status"], int) and a["status"] >= 500]
    conclude(Measurement(
        verdict="failed",
        reason=(f"card {latest['card']} reads status {card.get('status')}, "
                f"tradeable_now true, trading_blocked_reason "
                f"{card.get('trading_blocked_reason')}, and our paper buy of it "
                f"answered HTTP {status} {latest['response']} "
                f"({len(same)} time(s): {', '.join(a['id'] + ' ' + a['at'][11:19] for a in same)})"),
        left=status, right="2xx, or a 4xx naming its reason",
        population={"attempts_on_card": same,
                    "card": {k: card.get(k) for k in (
                        "status", "tradeable_now", "trading_blocked_reason",
                        "pw_live", "current_index", "share_price_usd")},
                    "legs": [(b.get("symbol"), b.get("weight"))
                             for b in card.get("basket") or []]},
        sources={"contract": "GET /api/v1/event-cards/{id} tradeability.tradeable_now: "
                             "'the only trade gate'",
                 "log": "state/paper.jsonl (TRD intent / outcome, with evidence ids)"}))
