"""A round still open on day N prices a pick at day 0, so day N is free.

Their rules, verbatim from `/api/v1/universe/movers/tournament`:

    "Each pick locks the stored close on the round day and is scored a week
     later on its real 7-day return. Ranked by average return; the NEXUS
     screen competes as a row."

We entered on 2026-09-13 into the round anchored **2026-09-11** and the five
picks came back priced at the 2026-09-11 closes (AAPL 335.80, GOOGL 341.51,
PLTR 166.64, SPCX 146.95, COIN 181.01).

**Our own entry is the weakest possible instance of it, and the first version
of this check said otherwise.** The anchor was a Friday and we entered on the
Sunday, so between the close we were priced at and the moment we chose, US
equities held **no sessions at all** -- four of the five picks are
`asset_class: equity` and their listing was answering `us_market_open: false`.
The reason line called it "two of the seven days", that went to them in
report #100's sibling, and it claimed an advantage a shut market could not
give. Corrected to count sessions.

The defect is unchanged: an entry made on the Thursday of the round week is
priced at Friday's close with three sessions already run. So the later an
entry is made, the more of the return it is scored on is already observable,
at a price that does not move -- and the leaderboard that ranks entrants by
`avg_pct` has no way to tell a pick committed on the anchor day from one
committed the day before scoring.

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

import re
from datetime import date, datetime, timedelta, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOURNAMENT = "/api/v1/universe/movers/tournament"

# A field naming when entries stop being accepted. Any of these present means
# the window is declared, which is the weakest of the three honest repairs.
DEADLINE_FIELDS = ("entries_close", "entries_close_at", "closes_at",
                   "entry_deadline", "locks_at", "entries_closed")
# And any field that names a cutoff FOR ENTRIES in its own words. Six names
# were the whole of "whatever it is called", so `entry_cutoff` or
# `entries_close_time` FAILED a repair (V07, deep pass of 2026-09-19, 3/3).
# Anchored to entries/submissions/picks, so a market's `trading_closes_at` is
# not read as a deadline for entering the round.
DEADLINE_NAMED = re.compile(
    r"^(entr(y|ies)|submissions?|picks?)_?"
    r"(close[sd]?|closing|cutoff|deadline|locks?|locked)(_at|_time|_utc)?$",
    re.IGNORECASE)
# Their rule that a pick is priced at the ROUND DAY's close -- the defect. When
# the rules text stops saying so, a late entry may be priced at its own day,
# which is the second repair, and only an entry can show it.
PRICES_AT_THE_ROUND_DAY = re.compile(r"round day", re.IGNORECASE)


def _day(value) -> date | None:
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        try:
            return date.fromisoformat(str(value)[:10])
        except (TypeError, ValueError):
            return None


def trading_sessions(anchor: date, today: date) -> int:
    """US sessions that have CLOSED between the anchor's close and today.

    Counted rather than assumed, because assuming cost us a number in a filed
    report. The anchor price is that day's close, so the anchor day itself is
    already spent when the price is struck and does not count; nor does today,
    which has not closed. What is left is the weekdays strictly between them.

    Weekends only -- market holidays are not modelled, so this can overstate
    by a day around one, never understate. A number we send them should err
    towards claiming less. Their own event-card listing carries
    `us_market_open`, which is the live version of the same question.
    """
    if today <= anchor:
        return 0
    day, sessions = anchor + timedelta(days=1), 0
    while day < today:
        if day.weekday() < 5:
            sessions += 1
        day += timedelta(days=1)
    return sessions


def declares_a_deadline(round_: dict, rules: dict) -> bool:
    """Whether a cutoff for entries is actually STATED.

    Read for the value, not the presence. Until the deep pass of 2026-09-13
    this was `is not None`, and `entries_closed` is one of the fields it looks
    for -- so `{"entries_closed": false}`, which says in so many words that
    entries are still open, cleared the finding and would have sent the PASS
    verification on #101. A boolean is a deadline only when it is True; a
    timestamp or a sentence is one whenever it is not empty.
    """
    for source in (round_ or {}), (rules or {}):
        named = [key for key in source
                 if isinstance(key, str) and DEADLINE_NAMED.match(key)]
        for field in dict.fromkeys([*DEADLINE_FIELDS, *named]):
            value = source.get(field)
            if isinstance(value, bool):
                if value:                      # entries_closed: true
                    return True
                continue                       # entries_closed: false
            if value not in (None, ""):
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

    # Their own word that the round is shut. The docstring has always said
    # this check reads whether entries are still being accepted, and until the
    # deep pass of 2026-09-13 `decide` never touched the field -- so a round
    # they had closed still failed with the reason "the round is still open",
    # against their own payload saying otherwise.
    if (round_ or {}).get("entries_open") is False:
        return ("inconclusive",
                f"the round anchored {anchor} is no longer accepting entries "
                f"(entries_open is false), so there is no late entry to be "
                f"priced at a stale close")

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

    # The second repair: their rules stop pricing a pick at the round day's
    # close. That shows only in the rules text -- this check never enters a
    # round -- and the text was never read, so reworded rules still FAILED,
    # quoting the old rule back to them (V07, deep pass of 2026-09-19, 3/3).
    text = str((rules or {}).get("text") or "")
    if text and not PRICES_AT_THE_ROUND_DAY.search(text):
        return ("inconclusive",
                f"their rules no longer say a pick locks the close on the "
                f"round day ({text[:120]!r}), so a late entry may now be "
                f"priced at its own day -- which only an entry can show, and "
                f"our one entry (2026-09-13) predates the wording")

    sessions = trading_sessions(anchor, today)
    elapsed = (today - anchor).days
    return ("failed",
            f"the round anchored {anchor} is still open -- it does not score "
            f"until {scores_after} and nothing in its payload names a cutoff "
            f"for entries -- while their own rules price every pick at 'the "
            f"stored close on the round day'. By that rule an entry made "
            f"today is priced at the {anchor} close, which is how our own "
            f"entry of 2026-09-13 came back, with {sessions} trading "
            f"session(s) of the "
            f"window already run ({elapsed} calendar day(s)), so that much of "
            f"the return it will be scored on is already observable while the "
            f"price it is scored from cannot move. The leaderboard ranks by "
            f"avg_pct and carries nothing to tell a pick committed on the "
            f"anchor day from one committed the day before scoring -- "
            f"including the NEXUS screen row, whose own /movers/potential is "
            f"stamped as_of the anchor")


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
            # NOT a measurement of this run. Our own entry of 2026-09-13 came
            # back priced at the 2026-09-11 closes, which is what first showed
            # the pricing rule, and it lives in state/lab.jsonl as a
            # `tournament` row. It was a hardcoded `True` here until the deep
            # pass of 2026-09-13 and read as though this check had measured
            # it -- the same defect as a reason asserting what no branch ran.
            "our_entry_priced_at_anchor": "recorded once, state/lab.jsonl "
                                          "type=tournament 2026-09-13",
        },
        sources={"tournament": TOURNAMENT,
                 "our_entry": "state/lab.jsonl type=tournament"},
    ))
