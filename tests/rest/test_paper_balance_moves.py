"""A paper balance that never moves is not a balance, it is a label.

The platform advertises a 100,000 USDC paper balance and an event-card book
that accepts `paper: true`. Both work in isolation: the order is accepted, the
position is created, `is_paper` is true, the notional and entry index are
right. What does not happen is the debit.

Measured 2026-09-10, twice, in both account modes:

    simulation_mode false   1.00 USDC bought   paper_balance 100000.00 -> 100000.00
    simulation_mode true    1.00 USDC bought   paper_balance 100000.00 -> 100000.00

`sim_balance.total_trades` stayed 0 across both, and `total_pnl` stayed 0.00
while the positions endpoint reported unrealized P&L on the open rows. No
published balance decreased by anything, in either mode.

That is what makes it worth a check rather than a shrug: an agent running a
paper campaign has nothing to score itself against. The positions endpoint
tells it what it holds; no surface tells it what it has left, so it cannot
size the next order, cannot know whether it is up or down, and cannot tell a
profitable run from a ruinous one.

**This check places no order.** It reads what `scripts/paper.py` recorded --
their own before-and-after responses, each with the evidence id of the capture
-- and re-reads the balance live, so a debit that merely settles late is not
reported as a debit that never came. Only trades opened since the paper
account's current `started_at` are counted: switching the account into
simulation_mode resets that pool, and holding it to trades from before the
reset would be our arithmetic, not their defect.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
ACCOUNT = "/api/v1/account/me"
POSITIONS = "/api/v1/event-cards/positions"


def _paper():
    spec = importlib.util.spec_from_file_location(
        "paper_log", REPO / "scripts" / "paper.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _moment(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_paper_buy_debits_the_paper_balance(rest_trusted):
    """Opening a position costs something, or the balance means nothing."""
    paper = _paper()
    rows = paper.load()
    chains: dict[str, dict] = {}
    for row in rows:
        chains.setdefault(row["id"], {})[row.get("type")] = row

    account = rest_trusted.get(ACCOUNT)
    if account.status_code != 200:
        raise Inconclusive(
            f"the account read answered HTTP {account.status_code}; a failed "
            f"read is not an unchanged balance")
    sim = (account.json() or {}).get("sim_balance") or {}
    started = _moment(sim.get("started_at"))
    try:
        balance_now = float(sim.get("usdc"))
    except (TypeError, ValueError):
        raise Inconclusive(
            f"sim_balance.usdc did not read as a number ({sim.get('usdc')!r})")

    # Only what this pool could have paid for. The pool is reset when the
    # account's mode is switched, and charging it for trades that predate its
    # own start would be a defect of ours.
    counted, opened = [], 0.0
    for trade_id, chain in sorted(chains.items()):
        intent, outcome = chain.get("intent") or {}, chain.get("outcome") or {}
        if outcome.get("outcome") != "accepted":
            continue
        when = _moment(outcome.get("at"))
        if started and when and when < started:
            continue
        counted.append(trade_id)
        opened += float(intent.get("usdc") or 0)

    if not counted:
        raise Inconclusive(
            "no accepted paper trade has been recorded since this paper "
            "balance was opened, so whether a buy debits it cannot be read; "
            "`python scripts/paper.py buy --card <id> --usdc 1 --confirm` "
            "records one")

    before = (chains[counted[0]].get("intent") or {}).get("before") or {}
    try:
        balance_before = float(before.get("sim_balance_usdc"))
    except (TypeError, ValueError):
        raise Inconclusive("the balance before the first counted trade was "
                           "not recorded as a number")

    moved = round(balance_before - balance_now, 2)
    expected = round(opened, 2)
    trades_counter = sim.get("total_trades")

    problems = []
    if abs(moved - expected) > 0.01:
        problems.append(
            f"{len(counted)} accepted paper buy(s) opened {expected:.2f} USDC "
            f"of notional and the paper balance moved {moved:.2f} "
            f"({balance_before:.2f} -> {balance_now:.2f})")
    if isinstance(trades_counter, (int, float)) and trades_counter < len(counted):
        problems.append(
            f"sim_balance.total_trades reads {trades_counter} after "
            f"{len(counted)} accepted trade(s)")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) + ": an agent running a paper campaign has "
                "no published number to score itself against, so it cannot "
                "size its next order or tell a winning run from a losing one"
                if problems else
                f"{len(counted)} paper buy(s) worth {expected:.2f} USDC "
                f"debited the paper balance by {moved:.2f}"),
        left=balance_now, right=round(balance_before - expected, 2),
        population={"trades": len(counted), "notional_usdc": expected,
                    "total_trades": trades_counter,
                    "pool_opened_at": sim.get("started_at")},
        sources={"balance": ACCOUNT, "positions": POSITIONS,
                 "our_record": str(paper.path().name)},
    ))
