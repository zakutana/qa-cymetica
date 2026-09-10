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

**This check places no order.** It reads what `scripts/paper.py` recorded:
for each accepted order, the account as they reported it seconds before the
POST and seconds after, each read carrying the evidence id of its capture. One
trade, two reads, their own numbers.

It used to compare the live balance against the bankroll and count only trades
since the pool's `started_at`. That went INCONCLUSIVE within the hour, because
`started_at` moves -- the pool is reset when the account's mode is switched,
and possibly at other times -- so no trade was ever "since" it. A check keyed
on something that moves measures nothing, which is the same defect as pinning
a fingerprint that is not stable. A pair of reads around one order cannot
drift: whatever the pool did before or after, those two numbers were taken
either side of one POST.
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

    measured = []
    for trade_id, chain in sorted(chains.items()):
        intent, outcome, after = (chain.get("intent") or {},
                                  chain.get("outcome") or {},
                                  chain.get("after") or {})
        if outcome.get("outcome") != "accepted":
            continue
        before = intent.get("before") or {}
        try:
            was, now = (float(before.get("sim_balance_usdc")),
                        float(after.get("sim_balance_usdc")))
        except (TypeError, ValueError):
            continue
        measured.append({
            "id": trade_id, "usdc": float(intent.get("usdc") or 0),
            "moved": round(was - now, 6),
            "positions_grew": (after.get("positions") or 0) - (before.get("positions") or 0),
            "trades_counter": (before.get("sim_total_trades"),
                               after.get("sim_total_trades")),
        })

    if not measured:
        raise Inconclusive(
            "no accepted paper trade carries a balance read on both sides of "
            "it, so whether a buy debits anything cannot be read; `python "
            "scripts/paper.py buy --card <id> --usdc 1 --confirm` records one")

    silent = [m for m in measured if abs(m["moved"] - m["usdc"]) > 0.01]
    landed = [m for m in measured if m["positions_grew"] >= 1]

    # A buy that did not create a position is a different fault and not this
    # one. What is asserted here is a position opening and nothing paying.
    subject = [m for m in silent if m in landed]

    conclude(Measurement(
        verdict="failed" if subject else "passed",
        reason=(f"{len(subject)} paper buy(s) opened a position and moved the "
                f"paper balance by nothing: "
                + "; ".join(f"{m['id']} bought {m['usdc']:.2f} and the balance "
                            f"moved {m['moved']:.2f}" for m in subject[:3])
                + ". An agent running a paper campaign has no published number "
                  "to score itself against, so it cannot size its next order "
                  "or tell a winning run from a losing one"
                if subject else
                f"each of the {len(measured)} recorded paper buy(s) debited "
                f"the paper balance by its own notional"),
        left=[m["moved"] for m in measured],
        right=[m["usdc"] for m in measured],
        population={"accepted": len(measured), "opened_a_position": len(landed),
                    "debited_nothing": len(subject),
                    "trades_counter": measured[-1]["trades_counter"]},
        sources={"balance": ACCOUNT, "positions": POSITIONS,
                 "our_record": str(paper.path().name)},
    ))
