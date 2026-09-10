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

**It judges the NEWEST trade, and only that one.** Until the 2026-09-10 sweep
it judged every trade in the log, which is a different question -- "has a buy
ever failed to debit" rather than "does a buy debit" -- and one no fix the
vendor ships can change the answer to. The two trades on file are from 11:41
and 11:59 that day; the fix was claimed live at 18:06. Frozen rows cannot be
repaired, so the check could not have gone green again, and a red that cannot
turn green is not a measurement. The history stays in `population`, where it
is a record rather than a verdict.

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


def measurements(rows):
    """Every accepted trade that carries a balance read on both sides.

    The population, and deliberately not the verdict. Judging all of it is
    what made this check unable to ever pass: TRD-0001 and TRD-0002 were
    recorded at 11:41 and 11:59 on 2026-09-10 and the vendor claimed the fix
    live at 18:06, so those two rows are frozen evidence of the old behaviour
    and no fix they ship can reach them. Sorted oldest first.
    """
    chains: dict[str, dict] = {}
    for row in rows:
        chains.setdefault(row["id"], {})[row.get("type")] = row

    measured = []
    for trade_id, chain in sorted(chains.items()):
        # A close lives in this same log and wears the same three row types.
        # It credits rather than debits and its position count falls, so
        # reading one as a buy answers the opposite question. Rows written
        # before closes existed carry no `kind`, so absent means buy.
        if (chain.get("intent") or {}).get("kind") == "close":
            continue
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
        # `positions` is written by _snapshot ONLY on a 200. Absent means the
        # read failed, and `(x or 0)` turned that into 0 -- so a failed read
        # gave 0 - 39 = -39, the trade fell out of `landed`, the subject list
        # emptied and the verdict was PASSED with the reason "each buy debited
        # the balance by its own notional" while nothing had moved. Rule 8
        # inverted, on the row that would flip #87 to VERIFIED FIXED. Found by
        # a check-auditor 2026-09-10, confirmed 3/3.
        unread = [side for side, snap in (("before", before), ("after", after))
                  if snap.get("positions") is None]
        measured.append({
            "id": trade_id, "usdc": float(intent.get("usdc") or 0),
            "at": intent.get("at") or outcome.get("at") or "",
            "moved": round(was - now, 6),
            "unread": unread,
            "positions_grew": (None if unread else
                               after["positions"] - before["positions"]),
            "trades_counter": (before.get("sim_total_trades"),
                               after.get("sim_total_trades")),
        })

    measured.sort(key=lambda m: (m["at"], m["id"]))
    return measured


def newest(measured):
    """The one trade this check has an opinion about: the last one placed.

    By time, and NOT by "the last one we could read". The fallback is the
    trap: a fresh trade whose account read failed would hand the verdict back
    to a trade from before the fix, and the check would report the vendor's
    old defect with today's date on it. A newest trade that cannot be read is
    Inconclusive -- rule 8, on the row that decides #87.
    """
    return measured[-1] if measured else None


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_paper_buy_debits_the_paper_balance(rest_trusted):
    """Opening a position costs something, or the balance means nothing."""
    paper = _paper()
    measured = measurements(paper.load())

    if not measured:
        raise Inconclusive(
            "no accepted paper trade carries a balance read on both sides of "
            "it, so whether a buy debits anything cannot be read; `python "
            "scripts/paper.py buy --card <id> --usdc 1 --confirm` records one")

    subject = newest(measured)
    if subject["unread"]:
        raise Inconclusive(
            f"the newest trade {subject['id']} is missing a positions read on "
            f"the {', '.join(subject['unread'])} side, so whether a position "
            f"opened cannot be established -- and judging the trade before it "
            f"instead would report a pre-fix trade with today's date on it")

    # A buy that did not create a position is a different fault and not this
    # one. What is asserted here is a position opening and nothing paying, so
    # with a single subject there is nothing left to compare and the honest
    # answer is that this check could not measure -- not "passed".
    if subject["positions_grew"] < 1:
        raise Inconclusive(
            f"the newest trade {subject['id']} was accepted but opened no "
            f"position ({subject['positions_grew']:+d}), which is a different "
            f"fault from the one this check reads: there is no position whose "
            f"cost could have been debited")

    # "Costs something", which is the contract this check's own docstring
    # states. It demanded EXACTLY the notional, so a 1.00 buy debited 0.97 --
    # a fee, a rounding, a partial fill -- was filed under the headline "moved
    # the paper balance by nothing" while the same sentence quoted 0.97. A
    # false claim to the vendor, from the strictness rather than from the data.
    silent = subject["moved"] <= 0.01

    history = [m for m in measured if not m["unread"]]
    conclude(Measurement(
        verdict="failed" if silent else "passed",
        reason=(f"the newest paper buy {subject['id']} ({subject['at']}) "
                f"opened a position and moved the paper balance by nothing: "
                f"bought {subject['usdc']:.2f}, balance moved "
                f"{subject['moved']:.2f}. An agent running a paper campaign "
                f"has no published number to score itself against, so it "
                f"cannot size its next order or tell a winning run from a "
                f"losing one"
                if silent else
                f"the newest paper buy {subject['id']} ({subject['at']}) "
                f"bought {subject['usdc']:.2f} and debited "
                f"{subject['moved']:.2f} from the paper balance"),
        # The subject, not the log. The history stays in population, where it
        # is a record rather than a verdict -- judging all of it is what kept
        # this check red no matter what the vendor shipped.
        left=[subject["moved"]],
        right=[subject["usdc"]],
        population={"accepted": len(measured),
                    "readable": len(history),
                    "unreadable": len(measured) - len(history),
                    "subject": subject["id"],
                    "ever_debited_nothing": sum(
                        1 for m in history
                        if m["moved"] <= 0.01 and m["positions_grew"] >= 1),
                    "trades_counter": subject["trades_counter"]},
        sources={"balance": ACCOUNT, "positions": POSITIONS,
                 "our_record": str(paper.path().name)},
    ))
