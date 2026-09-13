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
    """Every accepted close, and what could be read on it.

    A close whose balance could not be read stays, with `credited` None:
    until the deep pass of 2026-09-11 it was dropped, so a failed read on the
    newest close handed the verdict to the one before it (V06).
    """
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
            credited = round(float(after["sim_balance_usdc"])
                             - float(intent["before"]["sim_balance_usdc"]), 6)
        except (KeyError, TypeError, ValueError):
            credited = None
        try:
            pnl_was, pnl_now = (float(intent["before"]["sim_total_pnl"]),
                                float(after["sim_total_pnl"]))
        except (KeyError, TypeError, ValueError):
            pnl_was = pnl_now = None
        try:
            proceeds = float(outcome["proceeds_usdc"])
        except (KeyError, TypeError, ValueError):
            proceeds = None
        out.append({
            "id": trade_id,
            "at": intent.get("at") or "",
            "notional": float(intent.get("notional_usdc") or 0),
            "expected_pnl": intent.get("unrealized_pnl_usdc"),
            "proceeds": proceeds,
            "credited": credited,
            "pnl_booked": (None if pnl_was is None
                           else round(pnl_now - pnl_was, 6)),
        })
    out.sort(key=lambda c: (c["at"], c["id"]))
    return out


# Without their own figure for the proceeds, what was due is our estimate from
# the position row read BEFORE the close, and the index can move a cent or a
# fee be taken in between; a tenth of a percent of the notional (0.001), never
# less than their 2dp, is room for that and not for money that did not come
# back.
ESTIMATE_SLACK = 0.001


def judge(subject: dict) -> dict:
    """The verdict on one close, out of the check so it can be driven.

    Until the deep pass of 2026-09-11 this was inline, and the only meta test
    drove closes() -- dropping the sub-cent condition below turned TRD-0004
    into a false fail with every guard green (T05). And it held the credit to
    within a cent of our own pre-close estimate, so a two-cent fee failed as
    "does not credit", and counted a P&L booked with the wrong sign as booked
    (V06). Both triage 3/3.
    """
    # Both of these come off THEIR payloads -- `proceeds_usdc` from the close
    # response and `unrealized_pnl_usdc` from the position row -- and both were
    # read with a default. With the pnl absent the "estimate" became the bare
    # notional, so a CORRECT close of a position that lost 0.05 on a 1.00
    # notional credited 0.95 and read `failed`: "A book that debits on the way
    # in and does not credit on the way out reads every strategy as losing
    # money", sent as a new report. And the same None made `result` 0, so the
    # P&L half was silently waived in the same run. V08, deep pass of
    # 2026-09-13, triage 3/3 -- `qa/measure.py::required` exists for this.
    if subject.get("expected_pnl") is None and subject.get("proceeds") is None:
        raise Inconclusive(
            "their close response carries no proceeds_usdc and the position "
            "row no unrealized_pnl_usdc, so there is nothing to judge the "
            "credit against -- a missing field is not a zero result, and "
            "guessing one turns a correct close into an accusation")

    estimate = subject["notional"] + float(subject["expected_pnl"] or 0)
    if subject.get("proceeds") is not None:
        expected, slack, basis = subject["proceeds"], VISIBLE, "their proceeds"
    else:
        expected = estimate
        slack = max(VISIBLE, round(abs(subject["notional"]) * ESTIMATE_SLACK, 2))
        basis = "our estimate"
    off_by = round(subject["credited"] - expected, 2)
    returned = subject["credited"] > 0 and abs(off_by) <= slack

    # Only judged where their own precision could show it: TRD-0004 closed
    # for +0.0022 and total_pnl stayed 0.00, which is right. And the same
    # sign as the result -- a loss booked as a gain is not booked.
    result = float(subject["expected_pnl"] or 0)
    measurable = subject["pnl_booked"] is not None and abs(result) >= VISIBLE
    booked = (not measurable) or (abs(subject["pnl_booked"]) >= VISIBLE
                                  and (subject["pnl_booked"] > 0) == (result > 0))
    return {"expected": round(expected, 2), "slack": slack, "basis": basis,
            "returned": returned, "measurable": measurable, "booked": booked}


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

    if subject["credited"] is None:
        raise Inconclusive(
            f"the newest close {subject['id']} has no balance read on one side "
            f"of it, so what came back cannot be established -- and judging "
            f"the close before it instead would report an older close with "
            f"today's date on it")

    # The proceeds are the notional adjusted by what the position made or
    # lost, and judge() says against which figure: theirs when the close
    # recorded it, our pre-close estimate otherwise.
    verdict = judge(subject)
    expected, returned = verdict["expected"], verdict["returned"]
    measurable, booked = verdict["measurable"], verdict["booked"]

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
