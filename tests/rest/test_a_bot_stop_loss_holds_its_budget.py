"""A paper bot paused by its stop-loss has not lost more than the stop allows.

The contract is their own settings page for a cloned bot (/clone/{id}, the
"Stop Loss %" field, read 2026-09-28):

    "Max capital drawdown from your resume baseline. Trading pauses when
    total P&L falls below this %, and each trade's stake is auto-capped so a
    single loss cannot exceed the remaining stop-loss budget."

**What was seen when this was written** (2026-09-28, four paper clones of
ours started 07:28-07:32 UTC, 477 USDC each): three perpetual agents with
`stop_loss_pct` 5 (Corr Catcher, Sent Surfer, Delta Hunter) each opened a BTC
and an ETH position of 23.85 at once, lost both whole, and stand at -47.70:
-10.0% of what went in. Their own pause event for each says
`stop_loss_triggered`, `pnl_pct: -5.0`, `threshold_pct: 5.0`. Divergence
Dragon, stop 6, paused at -10.48% by its own event. Each stake fit the
budget alone; two at once spent it twice.

**The claim:** for every paper clone of ours whose trading was paused by
`stop_loss`, the loss from its resume baseline is within its own
`threshold_pct` (plus half a point for rounding). Measured from their fields
only:

  * the threshold is the one their `stop_loss_triggered` event carries;
  * the baseline is `current_balance_usdc - total_profit_usdc`, which is the
    resume balance only when the bot resumed once and holds no position --
    so a bot resumed more than once, or with a position open, is left out
    rather than guessed at.

Not in scope: the trailing profit floor and what happens after a pause, which
their P2T2 forward test covered (owner pass, 2026-09-28).

**After their fix only.** Filed as #134; their record reads `fixed_at`
2026-09-28T11:34:44 ("open stakes now count against the same budget",
ET-28099). A bot paused before that is history and stays as it paused, so
judging it would keep this red for good: only a stop-loss pause after
`FIXED_AT` is judged, and until one happens there is nothing to judge.

SAFE: GETs only.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/cloned-bots"
ROUNDING_PP = 0.5
# Their `fixed_at` on #134, from GET /api/v1/bounty/my-reports.
FIXED_AT = "2026-09-28T11:34:44"


def judged(row: dict, events: dict, profile: dict) -> dict | None:
    """One bot's reading, or None when its baseline cannot be read off."""
    if row.get("auto_pause_reason") != "stop_loss":
        return None
    items = events.get("events") or []
    stops = [e for e in items if e.get("event_type") == "stop_loss_triggered"]
    resumes = [e for e in items if e.get("event_type") == "trading_resumed"]
    if len(stops) != 1 or len(resumes) != 1 or profile.get("current_position_side"):
        return None
    try:
        threshold = float(stops[0]["threshold_pct"])
        balance = float(row["current_balance_usdc"])
        profit = float(row["total_profit_usdc"])
    except (KeyError, TypeError, ValueError):
        return None
    baseline = balance - profit
    if baseline <= 0:
        return None
    loss = -profit / baseline * 100.0
    return {"name": row.get("name"), "id": row.get("id"), "threshold": threshold,
            "loss": round(loss, 2), "recorded": stops[0].get("pnl_pct"),
            "breach": loss > threshold + ROUNDING_PP}


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_a_bot_paused_by_its_stop_loss_lost_no_more_than_the_stop(rest_trusted):
    """Every stop-paused paper clone of ours, its loss against its own stop."""
    mine = rest_trusted.get(f"{PREFIX}/my-clones", params={"mode": "paper"})
    if mine.status_code != 200 or not isinstance(mine.json(), list):
        raise Inconclusive(f"my-clones answered HTTP {mine.status_code}")
    readings, unread, before_fix = [], 0, 0
    for row in mine.json():
        if row.get("auto_pause_reason") != "stop_loss":
            continue
        if str(row.get("auto_pause_at") or "")[:19] < FIXED_AT:
            before_fix += 1
            continue
        bid = row.get("id")
        events = rest_trusted.get(f"/api/v1/agents/instances/{bid}/events")
        profile = rest_trusted.get(f"{PREFIX}/{bid}/profile")
        if events.status_code != 200 or profile.status_code != 200:
            unread += 1
            continue
        reading = judged(row, events.json() or {}, profile.json() or {})
        if reading:
            readings.append(reading)
    if not readings:
        raise Inconclusive(
            f"no stop-loss pause of ours since their fix of #134 at "
            f"{FIXED_AT} UTC with a readable baseline ({before_fix} before it, "
            f"history; {unread} unread); nothing to judge")

    breaches = [r for r in readings if r["breach"]]
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(
            f"{len(breaches)} of {len(readings)} paper bot(s) paused by their "
            f"stop-loss lost more than the stop: "
            + "; ".join(f"{r['name']} lost {r['loss']}% against a "
                        f"{r['threshold']:g}% stop, its own pause event "
                        f"recording {r['recorded']}%" for r in breaches)
            if breaches else
            f"all {len(readings)} stop-paused paper bot(s) stayed within "
            f"their stop"),
        left={"breaches": len(breaches), "judged": len(readings)},
        right={"breaches": 0},
    ))
