"""The account summary against the positions the same platform reports.

Measured 2026-09-08, either side of one $1 paper trade:

    before   total_predictions 0     total_volume 0
    after    total_predictions 142   total_volume 3582.146846

The account held 38 event-card positions and $2,900 of historical notional
throughout. Nothing about that dollar created 142 predictions or $3,582 of
volume — those figures were true before the trade and the endpoint was
reporting zeros. A write appears to have forced a recompute.

So an agent reading its own summary would have concluded it had never traded,
on an account with 38 positions in it, and no other surface would have
contradicted that: /event-cards/positions is a different endpoint and an agent
has no reason to cross-read it against the summary.

**This guard cannot reproduce the zero state.** The write that revealed it also
repaired it, and we will not file a report we cannot reproduce — that is the
whole reason the vendor takes our filings seriously. What this does is notice
if it comes back, with the evidence attached, on any account that has traded.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

SUMMARY = "/api/v1/portfolio/summary"
POSITIONS = "/api/v1/event-cards/positions"


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest")
def test_the_summary_does_not_report_a_history_the_positions_contradict(rest_trusted):
    """Zero traded, beside positions that were traded.

    Deliberately weak as an equality and strong as a contradiction: the two
    endpoints count different populations -- 142 predictions against 39
    event-card positions, so the summary spans instruments this one does not --
    and demanding they match would be a check that fails on a truth. What
    cannot both be true is "you have never traded" and "here are your
    positions".
    """
    summary = rest_trusted.get(SUMMARY)
    positions = rest_trusted.get(POSITIONS)
    if summary.status_code != 200 or positions.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"summary answered HTTP {summary.status_code} and positions "
                   f"HTTP {positions.status_code}; a failed read is not an "
                   f"empty account",
            sources={"summary": SUMMARY, "positions": POSITIONS}))
        return

    body = summary.json() or {}
    held = (positions.json() or {}).get("positions") or []
    if not held:
        conclude(Measurement(
            verdict="inconclusive",
            reason="this account holds no event-card position, so an empty "
                   "summary is not a contradiction and this establishes nothing",
            sources={"summary": SUMMARY, "positions": POSITIONS}))
        return

    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    predictions = number(body.get("total_predictions"))
    volume = number(body.get("total_volume"))
    notional = sum(number(p.get("notional_usdc")) or 0.0 for p in held)
    silent = [name for name, value in (("total_predictions", predictions),
                                       ("total_volume", volume))
              if value == 0]

    conclude(Measurement(
        verdict="failed" if silent else "passed",
        reason=(f"the summary reports {', '.join(silent)} as zero while "
                f"{len(held)} position(s) worth {notional:.2f} USDC of notional "
                f"are listed on the same account: an agent reading its own "
                f"summary would conclude it had never traded"
                if silent else
                f"the summary's counters are non-zero beside {len(held)} "
                f"position(s), so it does not contradict what the account holds"),
        left=silent, right=[],
        population={"positions": len(held), "notional_usdc": round(notional, 2),
                    "total_predictions": predictions, "total_volume": volume},
        sources={"summary": SUMMARY, "positions": POSITIONS}))
