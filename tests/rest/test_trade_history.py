"""Can an agent read back the trades it made?

llms.txt publishes `GET /api/v1/trades` as "Trade history", unqualified. On
2026-09-08 it answered 200 with total 0, under six different query shapes, on
an account where the same platform reports 142 predictions, $3,582.15 of
volume and 39 event-card positions -- one of them opened eleven minutes
earlier by the API caller doing the reading.

This matters beyond tidiness. /build invites an agent to trade over HTTP, and
an agent that cannot read back what it did cannot compute its own position,
reconcile a fill, or stop itself repeating an order. It is also the endpoint a
human would reach for first: it is called "trade history" and there is no
second one.

Two readings fit the evidence and the report says both, because we cannot tell
them apart from outside: the endpoint is blind to this account's activity, or
it is scoped to an identity our API key is not -- the sibling
/api/v1/swap/history answers 401 "Valid JWT token required", so per-identity
scoping demonstrably exists here. Either way an agent holding the key /build
told it to save reads an empty history of its own trading.

The check is a contradiction between two of their own surfaces, not an
assertion about what the number should be. We do not know how many trades they
ought to report; we know it cannot be zero while they themselves report 142
predictions on the same account in the same minute.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

TRADES = "/api/v1/trades"
SUMMARY = "/api/v1/portfolio/summary"
POSITIONS = "/api/v1/event-cards/positions"


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest")
def test_trade_history_is_not_empty_for_an_account_that_has_traded(rest_trusted):
    """"Trade history" against the two surfaces that say there is history."""
    history = rest_trusted.get(TRADES)
    if history.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{TRADES} answered HTTP {history.status_code}; a failed "
                   f"read is not an empty history",
            sources={"trades": TRADES}))
        return

    body = history.json() or {}
    rows = body.get("trades")
    if rows is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{TRADES} answered 200 with no `trades` key, so the shape "
                   f"this check reads has changed: keys are {sorted(body)}",
            sources={"trades": TRADES}))
        return

    summary = rest_trusted.get(SUMMARY)
    positions = rest_trusted.get(POSITIONS)
    if summary.status_code != 200 or positions.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the surfaces this is held against could not be read, so "
                   "an empty history proves nothing on its own",
            sources={"trades": TRADES, "summary": SUMMARY}))
        return

    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    counters = summary.json() or {}
    predictions = number(counters.get("total_predictions"))
    volume = number(counters.get("total_volume"))
    held = len((positions.json() or {}).get("positions") or [])
    traded = predictions > 0 or volume > 0 or held > 0
    reported = int(body.get("total") or len(rows))

    conclude(Measurement(
        verdict="failed" if traded and reported == 0 else "passed",
        reason=(f"\"Trade history\" reports {reported} trades while the same "
                f"platform reports {predictions:.0f} predictions, "
                f"{volume:.2f} USDC of volume and {held} open-or-closed "
                f"event-card position(s) on this account: an agent cannot read "
                f"back what it did"
                if traded and reported == 0 else
                f"trade history reports {reported} trade(s) beside "
                f"{predictions:.0f} prediction(s) and {held} position(s)"),
        left=reported, right=[predictions, volume, held],
        population={"trades_reported": reported, "total_predictions": predictions,
                    "total_volume": volume, "event_card_positions": held},
        sources={"trades": TRADES, "summary": SUMMARY, "positions": POSITIONS}))
