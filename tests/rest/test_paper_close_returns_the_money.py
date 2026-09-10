"""The other half of the book: a close gives the money back.

#87 established that a paper buy DEBITS the balance, and stopped there. That
is half an accounting identity. A book that takes money on the way in and
never returns it on the way out reads every strategy as losing, and it would
take weeks of campaign before anybody noticed the arithmetic rather than the
strategy.

Nothing had ever called `/sell`. `scripts/paper.py` carried the SELL constant
and no command, so whether a close credits rested entirely on the vendor's
telegram message of 2026-09-10 18:06: *"a paper close returns the proceeds
and books total_pnl."* A vendor claim nobody has measured is exactly what
this repository exists to measure.

Measured on TRD-0005, closing a 1.00 USDC position held since 2026-09-08:

    paper balance   100000.00 -> 100000.96    credited 0.96
    total_pnl            0.00 -> -0.04        booked

0.96 is the notional back minus the 0.044 the position had lost. Both halves
of their claim hold, and this check is here so they keep holding.

WHY THE PNL HALF IS CONDITIONAL. `sim_balance.total_pnl` is published to two
decimals, so a position whose realised result is smaller than a cent cannot
move it. TRD-0004 closed for +0.0022 and total_pnl stayed 0.00 -- correctly.
Reading that as a defect would have been a false report, so the pnl assertion
runs only when the result is large enough to be visible, and says so
otherwise rather than passing quietly.

THE NEWEST CLOSE, not every close. The lesson of the 2026-09-10 sweep: a
check that judges an append-only log of ours answers "has this ever failed",
which no fix can change the answer to. The history stays in `population`.

**This check places no order.** It reads what `scripts/paper.py` recorded --
their account either side of one close, each read carrying its evidence id.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
ACCOUNT = "/api/v1/account/me"

# Their published precision. A result below this cannot move the field, and a
# check that demands it anyway reports arithmetic as a defect.
VISIBLE = 0.01


def _paper():
    spec = importlib.util.spec_from_file_location(
        "paper_log_close", REPO / "scripts" / "paper.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def closes(rows):
    """Every recorded close that carries a balance read on both sides."""
    chains: dict[str, dict] = {}
    for row in rows:
        chains.setdefault(row["id"], {})[row.get("type")] = row

    out = []
    for trade_id, chain in chains.items():
        intent = chain.get("intent") or {}
        outcome = chain.get("outcome") or {}
        after = chain.get("after") or {}
        if intent.get("kind") != "close":
            continue
        if outcome.get("outcome") != "accepted":
            continue
        try:
            was, now = (float(intent["before"]["sim_balance_usdc"]),
                        float(after["sim_balance_usdc"]))
        except (KeyError, TypeError, ValueError):
            continue
        try:
            pnl_was, pnl_now = (float(intent["before"]["sim_total_pnl"]),
                                float(after["sim_total_pnl"]))
        except (KeyError, TypeError, ValueError):
            pnl_was = pnl_now = None
        out.append({
            "id": trade_id,
            "at": intent.get("at") or "",
            "notional": float(intent.get("notional_usdc") or 0),
            "expected_pnl": intent.get("unrealized_pnl_usdc"),
            "credited": round(now - was, 6),
            "pnl_booked": (None if pnl_was is None
                           else round(pnl_now - pnl_was, 6)),
        })
    out.sort(key=lambda c: (c["at"], c["id"]))
    return out


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_closing_a_paper_position_returns_its_money(rest_trusted):
    """Money out on the way in, money back on the way out."""
    paper = _paper()
    recorded = closes(paper.load())
    if not recorded:
        raise Inconclusive(
            "no accepted close carries a balance read on both sides of it, so "
            "whether closing returns anything cannot be read; `python "
            "scripts/paper.py close --position-id <id> --confirm` records one")

    subject = recorded[-1]
    if subject["notional"] <= 0:
        raise Inconclusive(
            f"the newest close {subject['id']} records no notional, so what "
            f"should have come back cannot be established")

    # The proceeds are the notional adjusted by what the position made or
    # lost. Their published balance is 2dp, so the comparison is too: this
    # asserts the money came back, not that it came back to the microcent.
    expected = subject["notional"] + float(subject["expected_pnl"] or 0)
    off_by = round(subject["credited"] - expected, 2)
    returned = subject["credited"] > 0 and abs(off_by) <= VISIBLE

    # Only judged where their own precision could show it. TRD-0004 closed
    # for +0.0022 and total_pnl stayed 0.00, which is right.
    measurable = (subject["pnl_booked"] is not None
                  and abs(float(subject["expected_pnl"] or 0)) >= VISIBLE)
    booked = (not measurable) or abs(subject["pnl_booked"]) >= VISIBLE

    conclude(Measurement(
        verdict="passed" if returned and booked else "failed",
        reason=(
            f"the newest close {subject['id']} ({subject['at']}) returned "
            f"{subject['credited']:.2f} on a {subject['notional']:.2f} "
            f"position"
            + (f" and booked {subject['pnl_booked']:.2f} to total_pnl"
               if measurable else
               "; its result was under a cent, which their 2dp total_pnl "
               "cannot show, so that half was not judged")
            if returned and booked else
            f"the newest close {subject['id']} ({subject['at']}) returned "
            f"{subject['credited']:.2f} where {expected:.2f} was due on a "
            f"{subject['notional']:.2f} position"
            + (f", and total_pnl moved {subject['pnl_booked']} against a "
               f"result of {subject['expected_pnl']}" if measurable else "")
            + ". A book that debits on the way in and does not credit on the "
              "way out reads every strategy as losing money"),
        left=[subject["credited"]],
        right=[round(expected, 2)],
        population={"closes_recorded": len(recorded),
                    "subject": subject["id"],
                    "pnl_judged": measurable,
                    "pnl_booked": subject["pnl_booked"]},
        sources={"balance": ACCOUNT,
                 "our_record": str(paper.path().name)},
    ))
