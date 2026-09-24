"""A paper buy is not refused for money the paper book holds.

The contract is the card's own `tradeability` block, on every
`GET /api/v1/event-cards/{id}`:

    tradeable_now: "True when a position can be opened on this card RIGHT NOW
    via POST /buy, /sell or /short (paper or live per your account mode);
    False carries trading_blocked_reason. This is the only trade gate."

and `GET /api/v1/account/me`, which says which mode that is: our account
reads `simulation_mode: true` with a paper book in `sim_balance.usdc`. A buy
sent with `"paper": true` from that account is a paper buy. If it is refused
for want of money, the money it lacks has to be the paper book's.

**What was seen when this was written** (2026-09-23): card
5d91bf43-a597-47b0-9abe-5c7f52618bbd ("AIB-Privacy — Privacy Crypto Index
Basket", `evcdx_symbol: AIB-PRIVACY`, `pw_live: false`) read `status: live`,
`tradeable_now: true`, `trading_blocked_reason: null` at the buy. A paper
`POST /api/v1/event-cards/{id}/buy` of 480.36 USDC, `"paper": true`, from an
account in simulation_mode holding 88,598.91 paper USDC answered HTTP 409
`{"detail": "Insufficient USDC balance: you have 7.650006."}` twice --
TRD-0039 at 05:59:13 and TRD-0040 at 06:00:24 UTC -- and a paper buy of 5 USDC
on another card (30015006, no EVCDX symbol, `pw_live: true`) was accepted at
06:01:16. 7.650006 is neither the paper book nor `/account/me`'s
`balance_usdc` (0.00). Which balance it is, is theirs to say; that it is not
the paper one is the claim.

**This check places no order.** It reads what `scripts/paper.py` recorded:
the intent (the body sent, the card's gate and the account's paper book, both
read just before the buy) and the outcome (status and their body, with an
evidence id). Its subjects are EVERY card a buy of which was ever refused as
"insufficient ... balance", each judged by its NEWEST buy: the same refusal,
from simulation_mode, sent as paper, on a card that read tradeable_now true,
with a paper book that covered the amount, fails; an accepted buy of that card
passes it; anything else -- the book really short, the card shut at the buy, a
live account or a live order, nothing recorded before the buy, a different
refusal -- is unmeasured. Another card's accepted buy is not the fix: a card
nobody tries again stays failed (#117's A01).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
SHORT = re.compile(r"insufficient\s+\w*\s*balance", re.I)
HAVE = re.compile(r"you have\s+([0-9][0-9,]*(?:\.[0-9]+)?)", re.I)


def _paper():
    spec = importlib.util.spec_from_file_location(
        "paper_book_buys", REPO / "scripts" / "paper.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def buys(rows) -> list[dict]:
    """Every buy we attempted, intent and outcome side by side, oldest first."""
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
                    "body": intent.get("body") or {},
                    "before": intent.get("before"),
                    "card_before": intent.get("card_before"),
                    "status": outcome.get("http_status"),
                    "outcome": outcome.get("outcome"),
                    "response": str(outcome.get("response") or "")[:300],
                    "evidence_id": outcome.get("evidence_id")})
    return sorted(out, key=lambda b: (b["at"], b["id"]))


def _short(buy: dict) -> bool:
    status = buy["status"]
    return (isinstance(status, int) and 400 <= status < 500
            and bool(SHORT.search(buy["response"])))


def _accepted(buy: dict) -> bool:
    status = buy["status"]
    return (isinstance(status, int) and 200 <= status < 300
            and buy["outcome"] == "accepted")


QUOTED = re.compile(r"you have\s+([\d.,]+)", re.I)


def _quoted_balance(refusals: list[dict]) -> float | None:
    """The balance the newest refusal said we had ("you have 7.650006")."""
    for buy in reversed(refusals):
        found = QUOTED.search(buy["response"])
        if found:
            return _number(found.group(1).rstrip("."))
    return None


def _number(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def why_unmeasured(buy: dict) -> str | None:
    """None when this refusal is the defect; otherwise why it cannot be."""
    before, gate = buy["before"], buy["card_before"]
    if not isinstance(before, dict):
        return "no paper book was recorded before the buy"
    if before.get("simulation_mode") is not True:
        return "the account was not in simulation_mode"
    if buy["body"].get("paper") is not True:
        return "the order was not sent as paper"
    if not isinstance(gate, dict) or gate.get("tradeable_now") is not True:
        return (f"the card did not read tradeable_now true at the buy "
                f"({(gate or {}).get('trading_blocked_reason')})")
    book, amount = _number(before.get("sim_balance_usdc")), _number(buy["usdc"])
    if book is None or amount is None:
        return "the paper book or the amount could not be read"
    if book < amount:
        return (f"the paper book, {book}, really was short of {amount} -- the "
                f"refusal is true")
    return None


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_paper_buy_is_not_refused_for_money_the_paper_book_holds():
    """Every card refused for balance, by its newest buy, against the paper book."""
    attempts = buys(_paper().load())
    newest: dict[str, dict] = {}
    for buy in attempts:
        newest[buy["card"]] = buy
    struck = [card for card in newest
              if any(_short(b) for b in attempts if b["card"] == card)]
    if not struck:
        raise Inconclusive("no paper buy has been refused for balance")

    breaches, unmeasured, fixed = [], [], []
    for card_id in struck:
        latest = newest[card_id]
        if _accepted(latest):
            # The fix only when the buy is one the wrong balance could NOT
            # cover (A04, deep pass of 2026-09-24): a 5 USDC buy lands under
            # the 7.65 the refusal quoted whether or not anything was fixed.
            quoted = _quoted_balance([b for b in attempts
                                      if b["card"] == card_id and _short(b)])
            amount = _number(latest["usdc"])
            if quoted is not None and (amount is None or amount <= quoted):
                unmeasured.append(
                    f"{card_id}: its newest buy {latest['id']} of {amount} was "
                    f"accepted, which the {quoted} the refusal quoted also "
                    f"covers -- it proves nothing about the paper book")
                continue
            fixed.append(card_id)
            continue
        if not _short(latest):
            unmeasured.append(f"{card_id}: its newest buy {latest['id']} came "
                              f"back {latest['status']} {latest['response']}")
            continue
        why = why_unmeasured(latest)
        if why:
            unmeasured.append(f"{card_id}: {latest['id']} -- {why}")
            continue
        breaches.append(latest)

    if breaches:
        latest = breaches[0]
        same = [b for b in attempts if b["card"] == latest["card"] and _short(b)]
        have = HAVE.search(latest["response"])
        conclude(Measurement(
            verdict="failed",
            reason=(f"card {latest['card']} read tradeable_now true at the buy, "
                    f"the account was in simulation_mode with a paper book of "
                    f"{latest['before'].get('sim_balance_usdc')} USDC, and a "
                    f"paper buy of {latest['usdc']} USDC sent with paper: true "
                    f"answered HTTP {latest['status']} {latest['response']} "
                    f"({len(same)} time(s): "
                    f"{', '.join(b['id'] + ' ' + b['at'][11:19] for b in same)})"
                    + (f"; {len(breaches) - 1} other card(s) the same"
                       if len(breaches) > 1 else "")),
            left=_number(have.group(1)) if have else latest["response"],
            right=_number(latest["before"].get("sim_balance_usdc")),
            population={"refused_on_card": same,
                        "other_cards": [b["card"] for b in breaches[1:]],
                        "accepted_elsewhere": [
                            {"id": b["id"], "card": b["card"], "at": b["at"]}
                            for b in attempts
                            if _accepted(b) and b["at"] > same[0]["at"]][:5]},
            sources={"contract": "GET /api/v1/event-cards/{id} tradeability."
                                 "tradeable_now: 'paper or live per your "
                                 "account mode ... the only trade gate'",
                     "mode": "GET /api/v1/account/me simulation_mode, "
                             "sim_balance.usdc (recorded before the buy)",
                     "log": "state/paper.jsonl (TRD intent / outcome, with "
                            "evidence ids)"}))
        return
    if unmeasured:
        raise Inconclusive("; ".join(unmeasured))
    conclude(Measurement(
        verdict="passed",
        reason=("every card refused for balance on a paper buy has since taken "
                "one: " + ", ".join(f"{c} ({newest[c]['id']})" for c in fixed)),
        left=[newest[c]["status"] for c in fixed], right="2xx",
        population={"newest_on_struck_cards": [newest[c] for c in fixed]},
        sources={"log": "state/paper.jsonl"}))
