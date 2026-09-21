"""The build-stats totals, held against the period they are published under.

`/build-stats` is their AI-native proof page: "Claude Code session metrics &
git commit analytics". A visitor reads, in one strip,

    SINCE 2025-11-23
    SESSIONS    315      301 days active
    MESSAGES    608.2K   1.9K/session
    TOOL CALLS  60.5K    0.10/msg
    COMMITS     23.1K    76.7/day

and, under RECORDS, "First Session 2025-11-23".

Every one of those figures comes from `GET /api/v1/build-stats`, and the
arithmetic inside the response is right: the commit series really does span
301 days and sum to 23 100, the rates divide out, and `ai_commits` sums to
`ai_coauthored_commits` exactly.

What does not hold is the WINDOW of the first three. Measured 2026-09-20:

    daily_commits    301 rows, 2025-11-23 -> 2026-09-20   (to today)
    daily_activity    17 rows, 2026-01-31 -> 2026-02-16   (seven months ago)
    totals.sessions   315 == the sum of those 17 days
    totals.messages   608 185 == the sum of those 17 days
    totals.tool_calls  60 519 == the sum of those 17 days
    first_session     2025-11-23 -- before the first of those 17 days

So the totals are exactly one seventeen-day window of February, and the
session they themselves call the first is outside it. Whatever the figures
are, they are not "sessions since 2025-11-23": either the session feed
stopped on 2026-02-16 and the page still labels it as the whole history, or
the history is there and the totals leave most of it out.

WHAT THIS CHECK ASSERTS. Only what the response says about itself, with no
expectation of ours mixed in:

  * a total that equals the sum of its own series is that series and nothing
    more -- their own framing on the sibling traffic surface, "a range is the
    sum of its days";
  * and `first_session` must then fall inside the range that series covers.
    A `first_session` that is absent, renamed or not a day was never read,
    so the verdict is inconclusive -- never a pass on "(None) falls inside".

It does NOT assert that the series must reach today. A feed may legitimately
stop; that is their operational business. The defect is a total published
under a date the total does not reach, which is a contradiction inside one
response and visible to any reader of the page.

Whichever they correct -- the label, the window, or the feed -- the check
goes green, which is the shape a report on this repository is allowed to
make.

SAFE. One GET and no key.
"""

from __future__ import annotations

import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

STATS = "/api/v1/build-stats"
# The one shape a date is compared in: an ISO day, perhaps with a time after.
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}(?![\d])")
# The three totals that have a daily series of their own underneath them.
SERIES = {"sessions": "sessions", "messages": "messages",
          "tool_calls": "tool_calls"}


def _number(value):
    """A figure, or None. A missing field is not a zero (rule 8)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _days(rows) -> list[str]:
    return sorted(str(r.get("date")) for r in rows
                  if isinstance(r, dict) and r.get("date"))


def window_problems(body: dict) -> tuple[list[str], dict]:
    """The contradiction, computed on its own so it can be refuted by a
    fixture rather than only by whatever the live platform happens to serve
    on the day."""
    activity = body.get("daily_activity")
    totals = body.get("totals")
    if not isinstance(activity, list) or not activity or not isinstance(totals, dict):
        return [], {"measured": False}

    days = _days(activity)
    if not days:
        return [], {"measured": False}
    first, last = days[0], days[-1]

    # Which totals ARE their own series, exactly. One that is larger holds
    # something the series does not, and this check has nothing to say about
    # it -- that is the honest half of the same reading.
    equal = []
    for key, field in SERIES.items():
        total = _number(totals.get(key))
        summed = sum(_number(r.get(field)) or 0 for r in activity
                     if isinstance(r, dict))
        if total is not None and total == summed:
            equal.append(key)

    facts = {"measured": True, "series_days": len(days),
             "series_from": first, "series_to": last,
             "totals_equal_to_the_series": equal,
             "first_session": body.get("first_session")}
    if not equal:
        return [], facts

    first_session = body.get("first_session")
    # Absent, renamed or not a day, it is the date nothing was read from
    # (rule 8). Until the deep pass of 2026-09-21 (A18) this returned no
    # problem with `measured` still True, and the verdict passed on "the
    # first session they record (None) falls inside that window".
    if not isinstance(first_session, str) or not ISO_DAY.match(first_session):
        return [], {**facts, "measured": False,
                    "why": f"first_session reads {first_session!r}, not a day"}
    # Their own dates, compared as their own strings: both are ISO days.
    if first_session[:10] >= first:
        return [], facts

    return ([f"{', '.join(equal)} are exactly the sum of the "
             f"{len(days)} day(s) from {first} to {last}, and so hold nothing "
             f"outside that window -- while the same response dates the first "
             f"session to {first_session[:10]}, before it. The page publishes "
             f"those totals under SINCE {first_session[:10]}"], facts)


@qa(component="platform.ai_native_proof", tier=SafetyTier.SAFE, surface="rest")
def test_the_build_totals_reach_back_to_the_date_they_are_published_under(
        rest_anon):
    """One read of their own proof page's numbers."""
    response = rest_anon.get(STATS)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{STATS} answered HTTP {response.status_code}, so the "
                   f"figures behind the page could not be read",
            sources={"build stats": STATS}))
        return

    body = response.json()
    problems, facts = window_problems(body)
    if not facts.get("measured") and "why" in facts:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"{', '.join(facts['totals_equal_to_the_series'])} sum "
                    f"the {facts['series_days']} day(s) from "
                    f"{facts['series_from']} to {facts['series_to']}, but "
                    f"{facts['why']}, so the date the page publishes them "
                    f"under could not be read"),
            sources={"build stats": STATS},
            population=facts))
        return
    if not facts.get("measured"):
        conclude(Measurement(
            verdict="inconclusive",
            reason="the response carries no daily_activity series, so the "
                   "totals cannot be held against the days they are made of",
            sources={"build stats": STATS}))
        return

    if not facts["totals_equal_to_the_series"]:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"none of {', '.join(SERIES)} equals the sum of the "
                    f"{facts['series_days']} day(s) the response carries, so "
                    f"the totals hold something the series does not and this "
                    f"check cannot say what period they cover"),
            sources={"build stats": STATS},
            population=facts))
        return

    commits = _days(body.get("daily_commits") or [])
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"{', '.join(facts['totals_equal_to_the_series'])} sum the "
                f"{facts['series_days']} day(s) from {facts['series_from']} "
                f"to {facts['series_to']}, and the first session they record "
                f"({facts['first_session']}) falls inside that window"),
        left={"totals": body.get("totals"),
              "first_session": body.get("first_session")},
        right={"daily_activity": {"days": facts["series_days"],
                                  "from": facts["series_from"],
                                  "to": facts["series_to"]},
               "daily_commits": {"days": len(commits),
                                 "from": commits[0] if commits else None,
                                 "to": commits[-1] if commits else None}},
        sources={"build stats": STATS},
        population=facts))
