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
    """An empty history is not mistakable for "you have never traded".

    Repaired 2026-09-08 after Cymetica answered #81. The first version demanded
    a non-empty list whenever the account held positions, and their fix showed
    why that was the wrong demand: the endpoint covers filled order-book orders
    only, we have never placed one, and zero is the truthful answer. What was
    actually wrong was that nothing said so -- an empty 200 read exactly like
    "no trading has happened here".

    They closed it by publishing a `scope` block on every response: the
    identity, what it covers, what it does not, and the endpoints that do. So
    the contract to hold is that one. An empty list with a scope beside it is
    honest; an empty list on its own is the defect.

    Third repair of this shape today. A check written against a defect tends to
    encode the fix its author imagined, and the vendor is entitled to a better
    one.
    """
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

    reported = int(body.get("total") or len(rows))
    scope = body.get("scope") or {}
    # What an agent needs from an empty answer: whose trades these are, which
    # products the number spans, and where the rest of its activity lives.
    stated = [field for field in ("identity", "covers", "does_not_cover", "see_also")
              if scope.get(field)]
    explained = len(stated) >= 3

    conclude(Measurement(
        verdict="passed" if reported > 0 or explained else "failed",
        reason=(f"trade history reports {reported} trade(s) and says what that "
                f"number spans: {', '.join(stated)}"
                if reported > 0 or explained else
                f"\"Trade history\" reports {reported} trades and does not say "
                f"what it covers, so an empty answer is indistinguishable from "
                f"an account that has never traded"),
        left=sorted(stated), right=["identity", "covers", "does_not_cover"],
        population={"trades_reported": reported, "scope_fields": len(stated)},
        sources={"trades": TRADES}))
