"""A round still open on day N prices a pick at day 0, so day N is free.

Their rules, verbatim from `/api/v1/universe/movers/tournament`:

    "Each pick locks the stored close on the round day and is scored a week
     later on its real 7-day return. Ranked by average return; the NEXUS
     screen competes as a row."

We entered on 2026-09-13 into the round anchored **2026-09-11** and the five
picks came back priced at the 2026-09-11 closes (AAPL 335.80, GOOGL 341.51,
PLTR 166.64, SPCX 146.95, COIN 181.01). Two of the seven days had already
happened. Entering on day six would leave one.

So the later an entry is made, the more of the return it is scored on is
already observable when it is made, at a price that does not move. The
leaderboard that ranks entrants by `avg_pct` has no way to tell a pick
committed on the anchor day from one committed the day before scoring.

It matters most for the row this tournament exists to be measured against.
The NEXUS screen's `/movers/potential` is stamped `as_of` the anchor, so the
house commits on day 0 while a human need not -- and `avg_pct` puts the two
in the same column.

WHAT THIS CHECK ASSERTS, AND WHY IT IS NOT A DATE COMPARISON DRESSED UP. Two
things, both read from their side: that the round is still accepting entries
(their own `round` is open and `scores_after` has not passed), and that the
anchor those entries price at is already in the past. Either alone is normal.
Together they are the finding, because the pricing rule is theirs and quoted
above.

WHAT MAKES IT PASS. Any of the three repairs: entries closing at the anchor
day, a late entry priced at the day it was made, or the payload naming an
entry deadline so the window is at least declared. The last is the weakest
and it still passes -- a check that demands the fix its author imagined
reports a fixed defect as broken, which has happened here repeatedly.

WHAT MAKES IT INCONCLUSIVE. A round whose anchor IS today: nothing to see,
and on that day the tournament behaves exactly as it should.

SAFE. One keyless GET. It never enters a round -- the entry that produced the
evidence was made once, on purpose, and is recorded in `state/lab.jsonl`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOURNAMENT = "/api/v1/universe/movers/tournament"

# A field naming when entries stop being accepted. Any of these present means
# the window is declared, which is the weakest of the three honest repairs.
DEADLINE_FIELDS = ("entries_close", "entries_close_at", "closes_at",
                   "entry_deadline", "locks_at", "entries_closed")


def _day(value) -> date | None:
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        try:
            return date.fromisoformat(str(value)[:10])
        except (TypeError, ValueError):
            return None


def declares_a_deadline(round_: dict, rules: dict) -> bool:
    for source in (round_ or {}), (rules or {}):
        for field in DEADLINE_FIELDS:
            if source.get(field) is not None:
                return True
    return False


def decide(round_: dict, rules: dict, today: date) -> tuple[str, str]:
    """Verdict and reason, pure, from their round state and today's date."""
    anchor = _day((round_ or {}).get("round_anchor"))
    scores_after = _day((round_ or {}).get("scores_after"))
    if anchor is None:
        return ("inconclusive",
                "their round names no round_anchor, so there is no pricing "
                "day here to be stale")

    if declares_a_deadline(round_, rules):
        return ("passed",
                "the round declares when entries stop being accepted, so the "
                "window a late entry could exploit is at least stated")

    if anchor >= today:
        return ("inconclusive",
                f"the round is anchored {anchor}, which is not in the past, "
                f"so an entry made now prices at a close that has only just "
                f"been struck -- nothing to report today")

    if scores_after is not None and scores_after <= today:
        return ("inconclusive",
                f"the round anchored {anchor} is already past its "
                f"scores_after of {scores_after}, so it is not open to be "
                f"entered late")

    elapsed = (today - anchor).days
    window = (rules or {}).get("window_days")
    fraction = (f"{elapsed} of its {window} days" if window
                else f"{elapsed} day(s)")
    return ("failed",
            f"the round anchored {anchor} is still open -- it does not score "
            f"until {scores_after} and nothing in its payload names a cutoff "
            f"for entries -- while their own rules price every pick at 'the "
            f"stored close on the round day'. An entry made today is "
            f"therefore scored over a window of which {fraction} have already "
            f"happened, at a price that cannot move. We entered this round on "
            f"2026-09-13 and were given the {anchor} closes, which is how "
            f"this was found. The leaderboard ranks by avg_pct and carries "
            f"nothing to tell a pick committed on the anchor day from one "
            f"committed the day before scoring -- including the NEXUS screen "
            f"row, whose own /movers/potential is stamped as_of the anchor")


@qa(component="rest.movers", tier=SafetyTier.SAFE, surface="rest")
def test_a_round_open_after_its_anchor_says_when_entries_close(rest_anon):
    """Read-only. The entry that evidences the pricing was made once, on
    purpose, and lives in state/lab.jsonl -- this check never enters."""
    response = rest_anon.get(TOURNAMENT)
    if response.status_code != 200:
        raise Inconclusive(
            f"{TOURNAMENT} answered HTTP {response.status_code}; a failed "
            f"read is not an open round")
    try:
        state = response.json() or {}
    except ValueError as exc:
        raise Inconclusive(f"{TOURNAMENT} did not answer JSON: {exc}")

    round_ = state.get("round") or {}
    rules = state.get("rules") or {}
    today = datetime.now(timezone.utc).date()

    verdict, reason = decide(round_, rules, today)
    if verdict == "inconclusive":
        raise Inconclusive(reason)

    anchor = _day(round_.get("round_anchor"))
    conclude(Measurement(
        verdict=verdict,
        reason=reason,
        left=[{"round_anchor": round_.get("round_anchor"),
               "scores_after": round_.get("scores_after"),
               "read_on": today.isoformat()}],
        right=[{"rules_text": rules.get("text"),
                "window_days": rules.get("window_days")}],
        population={
            "days_already_elapsed": (today - anchor).days if anchor else None,
            "window_days": rules.get("window_days"),
            "declares_a_deadline": declares_a_deadline(round_, rules),
            "round_fields": sorted(round_),
            "rules_fields": sorted(rules),
            "our_entry_prices_are_anchor_dated": True,
        },
        sources={"tournament": TOURNAMENT,
                 "our_entry": "state/lab.jsonl type=tournament"},
    ))
