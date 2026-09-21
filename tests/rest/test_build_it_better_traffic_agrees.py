"""The traffic and likes published for every rebuilt app, held against
themselves.

Shipped 2026-09-20 and announced the same day: every app rebuilt on Build it
Better now carries public traffic, no account needed. Three surfaces serve the
same figures -- `/build-it-better/stats`, a strip at the foot of each app's
page, and two documented GETs on `/build-it-better/api#traffic`:

    GET /api/v1/build-it-better/apps/leaderboard?sort=&days=   every app ranked
    GET /api/v1/build-it-better/apps/stats?path=/finviz        one app in full

Their announcement makes four claims this check can read off those two calls,
and one it deliberately does not.

WHAT IT ASSERTS.

  1. *The same numbers.* "The same numbers are on /build-it-better/stats and at
     the foot of each app's page." A leaderboard row over `days=30` must be the
     app's own `last_30d`, and its `likes` the app's own `likes`.
  2. *A range is the sum of its days.* Their own definition: "A range is the
     sum of its days, so one person on three days counts three times." So
     `daily[]` must sum to `last_30d`, metric by metric.
  3. *The windows nest.* `last_7d` <= `last_30d` <= `all_time`, and within any
     window `uses` <= `views`: uses are "page loads where the visitor
     interacted", a subset of the loads by their own words. Not `visitors` <=
     `views`, which is our inference and not their sentence -- their
     definitions say where views come from (a JavaScript beacon) and do not
     say where visitors do, and a figure whose unit we are guessing at is the
     shape that made us call a card self-contradicting once already.
  4. *Nothing earlier was recorded.* "Counting started 2026-09-20; nothing
     earlier was recorded." No day before `first_counted` may carry a figure,
     and no app's `first_counted` may fall before the board's
     `counting_since`. A LATER one is an app first visited after counting
     began, not a contradiction -- until 2026-09-21 this said "must be", our
     clause and not their sentence, and read 8 apps as defects.

WHAT IT DOES NOT ASSERT, AND WHY. Not that `uses` is ever smaller than
`views`. It is the one figure whose defect would be silent -- a `uses` that is
merely an alias for `views` would satisfy every invariant above -- but on the
day counting started two apps of 113 carry a single view each, and a rule over
two rows that have never been clicked is a coin flip, not a measurement (rule
10, and the check on a rotating population that passed, failed and passed with
the same defect throughout). It needs a population and is recorded in NEXT.md
as waiting for one.

Neither does it read the ranked page, the per-app footer strip or the chart:
those are markup, and the numbers behind them are what this reads.

VACUITY IS NAMED, NOT HIDDEN. Counting began today, so most of these
invariants hold over zeros. Every verdict says how many apps carried a figure
at all and which comparisons were therefore vacuous -- the shape the deep pass
of 2026-09-20 found judging `0 == 0` and calling it a pass.

THE RACE IS BRACKETED, NOT IGNORED. The two calls are seconds apart and the
counters move underneath them, so a plain comparison would call a real visit a
contradiction. Each app is read BEFORE and AFTER the leaderboard, and the
leaderboard figure must lie between the two. Counters only grow within a day,
so a figure outside that bracket is theirs disagreeing with itself, not
someone arriving. Only the leaderboard read taken INSIDE an app's bracket is
judged: the first ranking, read before any app, chooses which apps to read
and nothing more (deep pass of 2026-09-21 -- held against the bracket, one
visit in the minutes between read as a contradiction).

SAFE. Three GETs per app and no key: "No key, no account" is the claim under
test. Views are counted by an in-page JavaScript beacon, so these reads do not
move the numbers they measure, and the like button -- the one write on the
surface -- is never touched.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

BOARD = "/api/v1/build-it-better/apps/leaderboard"
STATS = "/api/v1/build-it-better/apps/stats"
WINDOW = 30
# The app their own documentation uses as its example, so it is read even when
# it carries nothing: a check that reads only the apps with traffic would have
# nothing at all to say on the day counting starts.
DOCUMENTED_EXAMPLE = "/finviz"
METRICS = ("views", "visitors", "uses")


def _number(value):
    """A figure, or None. A missing field is not a zero (rule 8)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _window(body: dict, name: str) -> dict:
    node = body.get(name)
    return node if isinstance(node, dict) else {}


def _carries_anything(row: dict) -> bool:
    return any((_number(row.get(key)) or 0) > 0
               for key in METRICS + ("likes",))


def _nests(body: dict, path: str) -> list[str]:
    """Claims 3: the windows nest and the metrics nest inside them."""
    problems = []
    for metric in METRICS:
        seven = _number(_window(body, "last_7d").get(metric))
        thirty = _number(_window(body, f"last_{WINDOW}d").get(metric))
        ever = _number(_window(body, "all_time").get(metric))
        if None in (seven, thirty):
            continue
        if seven > thirty:
            problems.append(f"{path} reports last_7d {metric} {seven} above "
                            f"its own last_{WINDOW}d {thirty}")
        if ever is not None and thirty > ever:
            problems.append(f"{path} reports last_{WINDOW}d {metric} {thirty} "
                            f"above its own all_time {ever}")
    for name in ("all_time", "last_7d", f"last_{WINDOW}d"):
        node = _window(body, name)
        views, uses = _number(node.get("views")), _number(node.get("uses"))
        if views is None or uses is None:
            continue
        if uses > views:
            problems.append(
                f"{path} reports {name} uses {uses} above its own views "
                f"{views}, and uses are page loads where the visitor "
                f"interacted, by their own definition")
    return problems


def _series(body: dict, path: str, counting_since) -> tuple[list, bool]:
    """Claims 2 and 4, over `daily[]`. Returns the problems and whether the
    series carried any figure at all -- an all-zero series makes the sum
    comparison vacuous, and the caller says so rather than counting it."""
    problems: list[str] = []
    daily = body.get("daily")
    if not isinstance(daily, list) or not daily:
        return ([f"{path} serves no daily[] series, so the "
                 f"last_{WINDOW}d figures cannot be held against their own "
                 f"days"], False)

    moved = False
    first = body.get("first_counted") or counting_since
    for day in daily:
        if not isinstance(day, dict):
            continue
        stamp = str(day.get("day") or "")
        figures = {m: _number(day.get(m)) for m in METRICS}
        if any((v or 0) > 0 for v in figures.values()):
            moved = True
            if first and stamp and stamp < str(first):
                problems.append(
                    f"{path} carries {figures} on {stamp}, before the "
                    f"{first} they say counting started on -- their "
                    f"announcement says nothing earlier was recorded")
    # Earlier only. An app first visited after counting began says so -- 8 of
    # 14 apps read as defects in PRE-0145 for a first_counted of the 21st,
    # while the 6 first visited on the 20th said the 20th (deep pass of
    # 2026-09-21). "Nothing earlier was recorded" bounds it from below.
    if body.get("first_counted") and counting_since and \
            str(body["first_counted"]) < str(counting_since):
        problems.append(
            f"{path} says counting started {body['first_counted']}, before the "
            f"{counting_since} the board says counting started for every app "
            f"-- their announcement says nothing earlier was recorded")

    for metric in METRICS:
        summed = sum(_number(d.get(metric)) or 0 for d in daily
                     if isinstance(d, dict))
        ranged = _number(_window(body, f"last_{WINDOW}d").get(metric))
        if ranged is None:
            continue
        if summed != ranged:
            problems.append(
                f"{path} sums {summed} {metric} over its {len(daily)} daily "
                f"rows while its own last_{WINDOW}d says {ranged}, and they "
                f"define a range as the sum of its days")
    return problems, moved


def _agrees(row: dict, before: dict, after: dict, path: str) -> list[str]:
    """Claim 1, bracketed against the counters moving between the two calls."""
    problems = []
    for metric in METRICS:
        listed = _number(row.get(metric))
        low = _number(_window(before, f"last_{WINDOW}d").get(metric))
        high = _number(_window(after, f"last_{WINDOW}d").get(metric))
        if listed is None or low is None or high is None:
            continue
        floor, ceiling = min(low, high), max(low, high)
        if not floor <= listed <= ceiling:
            problems.append(
                f"the board ranks {path} at {listed} {metric} over "
                f"{WINDOW} days while the app's own stats read {low} just "
                f"before and {high} just after, so the difference is not the "
                f"counter moving")
    listed, low, high = (_number(row.get("likes")), _number(before.get("likes")),
                         _number(after.get("likes")))
    if None not in (listed, low, high) and not min(low, high) <= listed <= max(low, high):
        problems.append(f"the board gives {path} {listed} like(s) while the "
                        f"app itself reads {low} then {high}")
    return problems


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_traffic_figures_agree_with_the_days_they_are_made_of(rest_anon):
    """One board, and each app's own record of the same thirty days."""
    board = rest_anon.get(BOARD, params={"sort": "views", "days": WINDOW})
    if board.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the app leaderboard answered HTTP {board.status_code}, "
                   f"so there is no ranking to hold the apps against",
            sources={"leaderboard": BOARD}))
        return

    listing = board.json()
    apps = listing.get("apps")
    if not isinstance(apps, list) or not apps:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the leaderboard ranks no apps, so there is nothing to "
                   "reconcile",
            sources={"leaderboard": BOARD}))
        return

    counting_since = listing.get("counting_since")
    carrying = [a for a in apps if isinstance(a, dict) and _carries_anything(a)]
    chosen = list(carrying)
    if not any(a.get("path") == DOCUMENTED_EXAMPLE for a in chosen):
        example = [a for a in apps
                   if isinstance(a, dict) and a.get("path") == DOCUMENTED_EXAMPLE]
        chosen += example

    problems: list[str] = []
    read, moved_apps, unreadable = [], [], []
    bracketed, unbracketed = [], []
    for row in chosen:
        path = str(row.get("path") or "")
        if not path:
            continue
        before = rest_anon.get(STATS, params={"path": path})
        fresh = rest_anon.get(BOARD, params={"sort": "views", "days": WINDOW})
        after = rest_anon.get(STATS, params={"path": path})
        if before.status_code != 200 or after.status_code != 200:
            # Rule 8: a read that failed is not an app with no traffic.
            unreadable.append(f"{path} ({before.status_code}/{after.status_code})")
            continue
        one, two = before.json(), after.json()
        read.append(path)

        # Only the row re-read INSIDE the bracket is judged. The original
        # ranking was read before the first app's `before`, minutes earlier
        # for the last app, so a real visit in between put it below the
        # floor and read as their board disagreeing with itself -- deep pass
        # of 2026-09-21, A07. A board that could not be re-read, or no longer
        # lists the app, leaves claim 1 unmeasured for it (rule 8), never
        # judged against the stale row.
        rows = []
        if fresh.status_code == 200:
            try:
                rows = [r for r in (fresh.json() or {}).get("apps") or []
                        if isinstance(r, dict) and r.get("path") == path]
            except (ValueError, AttributeError):
                rows = []
        if rows:
            bracketed.append(path)
        else:
            unbracketed.append(f"{path} (HTTP {fresh.status_code})"
                               if fresh.status_code != 200 else
                               f"{path} (not on the board re-read)")
        for candidate in rows:
            problems += _agrees(candidate, one, two, path)
        problems += _nests(one, path)
        series_problems, moved = _series(one, path, counting_since)
        problems += series_problems
        if moved:
            moved_apps.append(path)

    if not read:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"none of the {len(chosen)} app(s) chosen off the board "
                   f"could be read one by one: {', '.join(unreadable)}",
            sources={"leaderboard": BOARD, "one app": STATS},
            population={"apps_listed": len(apps)}))
        return

    # What was compared over zeros is said out loud. On the day counting
    # started this is nearly all of it, and a pass that did not say so would
    # be the `0 == 0` verdict the deep pass found the same morning.
    held = [f"{len(read)} app(s) of the {len(apps)} on the board were read "
            f"one by one"
            + (f", and for {len(bracketed)} of them every figure on the "
               f"board re-read between the app's two reads is the app's own"
               if bracketed else "")]
    if unbracketed:
        held.append(f"NOT measured against the board for "
                    f"{len(unbracketed)} app(s), whose row could not be "
                    f"re-read inside the bracket: {', '.join(unbracketed)}")
    if moved_apps:
        held.append(f"the daily series sums to last_{WINDOW}d for "
                    f"{len(moved_apps)} app(s) that have moved at all "
                    f"({', '.join(moved_apps)})")
    else:
        held.append(f"NOT measured on real figures: not one of the {len(read)} "
                    f"app(s) read carries a non-zero day, so the sum and the "
                    f"nesting hold over zeros only -- counting began "
                    f"{counting_since}")
    if unreadable:
        held.append(f"not read: {', '.join(unreadable)}")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason="; ".join(problems) if problems else "; ".join(held),
        left={"board": [{k: r.get(k) for k in ("path",) + METRICS + ("likes",)}
                        for r in chosen]},
        right={"counting_since": counting_since,
               "apps_read": read},
        sources={"leaderboard": BOARD, "one app": STATS},
        population={"apps_listed": len(apps),
                    "apps_carrying_a_figure": len(carrying),
                    "apps_read": len(read),
                    "apps_bracketed": len(bracketed),
                    "apps_with_a_non_zero_day": len(moved_apps)}))
