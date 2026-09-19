"""A backtest that says 365 days should not be 119 days wearing the label.

`backtest_event_card_idea` echoes the `period_days` it was asked for. Where a
leg's history is shorter than that, the window is truncated to what exists --
which is correct and unavoidable -- but the answer still reports the window as
requested, and two different requests come back byte-identical.

Measured 2026-09-12, the laboratory's first search:

    WIF+PNUT+GOAT+ACT+DOGS   180 d -> 119 points, -4.62%, sharpe 0.1365
                             365 d -> 119 points, -4.62%, sharpe 0.1365
    BCH+OKB+HBAR             180 d -> 177 points, -52.42%
                             365 d -> 362 points, -61.93%

The second basket is the control: where the history exists, the two windows
genuinely differ, so this is not a tool that ignores `period_days`.

The harm is #97's, on the tool they did not fix. Their own guidance is to rank
strategies by Sharpe; an agent ranking a "365-day Sharpe" puts a real one
(362 points) beside a 119-day figure labelled 365 and cannot tell. `n_points`
is in the payload and is how this check sees it, so the repair is small: say
the window that was actually covered.

Two readings of the same basket at two windows, and nothing is traded: four
calls, read-only, at SAFE.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOOL = "backtest_event_card_idea"
LONG, LONGER = 180, 365

# A key that would say what window the answer actually covers. Anchored, not a
# substring search: the first version of this check asked whether any key
# contained "start", matched `starting_capital_usdc`, and passed green while
# the defect was in front of it. A loose match on a field NAME is the same
# mistake as reading a number without its units.
NAMES_THE_WINDOW = re.compile(
    r"^(actual|covered|effective|real)?_?(period|window|days|span|range)"
    r"(_days|_hours)?$|^(first|last|earliest|latest)_(point|date|day)$"
    r"|^(from|to|since|until|start|end)_(date|time|day)$"
    # The word order the other way round, `days_covered` (V02, 2026-09-19).
    r"|^(days|hours|window|period|span)_(covered|actual|effective)$",
    re.IGNORECASE)

# A span in words, the way their own surfaces write one: "119 days", "48h",
# "6 months". Months are read as 30.44 days -- a label this check compares
# against the points with 25% of slack, not a calendar.
IN_WORDS = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(d|days?|h|hrs?|hours?|w|wks?|weeks?|mo|months?)"
    r"\s*$", re.IGNORECASE)
_UNIT_DAYS = {"d": 1.0, "h": 1 / 24, "w": 7.0, "m": 30.44}


# How far a label may sit from the window the points support before it stops
# being a reading of them. Their sampling is not exactly daily and a boundary
# point can go either way, so this is generous -- the defect it must catch is
# 180 against 120, not 122 against 120.
LABEL_SLACK = 0.25


def _implied_days(value) -> float | None:
    """What a label claims, in days: a number as it stands, a date as the span
    back to today, a span in words ("119 days", "48h"), or a block carrying
    one of those ({start, end}, {days}, {hours}, {label}). Anything else is
    unreadable, which is not a claim.

    Numbers and dates only until V02 (deep pass of 2026-09-19, 3/3): their own
    house style is words and blocks, so a correct repair of #99 written the
    way #97's was -- `period: {start, end, hours, label: "19.8 days"}` -- read
    None and the check FAILED on a fixed defect.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    from datetime import date, datetime

    def when(text):
        try:
            return datetime.fromisoformat(
                str(text).replace("Z", "+00:00")).date()
        except (TypeError, ValueError):
            return None

    if isinstance(value, dict):
        start, end = when(value.get("start")), when(value.get("end"))
        if start is not None:
            return float(((end or date.today()) - start).days)
        for key, per in (("days", 1.0), ("hours", 1 / 24)):
            number = value.get(key)
            if isinstance(number, (int, float)) and not isinstance(number, bool):
                return float(number) * per
        return _implied_days(value.get("label"))
    words = IN_WORDS.match(str(value))
    if words:
        return float(words.group(1)) * _UNIT_DAYS[words.group(2)[0].lower()]
    start = when(value)
    return None if start is None else float((date.today() - start).days)


def says_covered(answer, requested, per_day: float | None = None) -> list[str]:
    """Keys that say what window the answer ACTUALLY covered.

    The comment above was already right and this function was not: it collected
    key names and never read what they carried. Two values satisfy a name and
    answer nothing.

    `covered_days: null` is the absence with a label on it. And
    `effective_period_days: 365`, returned for a 365-day request that produced
    119 points, is the argument echoed under a second name -- the filed defect
    restated, which would have read here as the fix to it. So a number equal to
    what we asked for is not a reading of what we got; 119, or a date the
    points begin at, is.

    B04, deep pass of 2026-09-12, triage 3/3, the same hour as the same defect
    in tests/rest/test_backtest_metrics_agree.py.
    """
    out = []
    for key, value in answer.items():
        if key == "period_days" or not NAMES_THE_WINDOW.match(str(key)):
            # `period_days` itself is excluded: echoing the argument is the
            # claim under question, not an answer to it.
            continue
        if value is None or value == "" or value == [] or value == {}:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and abs(float(value) - requested) < 1e-9:
            continue

        # And the value has to AGREE with the points it arrived with. B04
        # stopped the echoed argument; any OTHER number still passed, and a
        # date was exempt from the value test entirely -- so `covered_days:
        # 180` beside 120 points, and the requested range echoed as
        # `start_date`, both read as "the window it actually covered". V03,
        # deep pass of 2026-09-13, triage 3/3. The control basket gives the
        # points-per-day, so this is checkable rather than assumed.
        claimed = _implied_days(value)
        if claimed is None:
            continue
        points = answer.get("n_points")
        if per_day and isinstance(points, (int, float)) and per_day > 0:
            supported = float(points) / per_day
            if abs(claimed - supported) > max(1.0, supported * LABEL_SLACK):
                continue
        # With no control there is nothing to check the label against, and a
        # claim we cannot refute is not a claim we may call false -- rule 8 in
        # its own shape. The live check always HAS a control (it raises
        # Inconclusive when the two windows cannot be told apart), so this
        # branch is the offline callers only.
        out.append(str(key))
    return sorted(out)

# Two of their own cards' baskets, as the sampler recorded them. The first is
# expected to be short of history (2026 coins), the second to have it.
SHORT_HISTORY = [{"symbol": "WIF", "weight": 0.735}, {"symbol": "PNUT", "weight": 0.174},
                 {"symbol": "GOAT", "weight": 0.055}, {"symbol": "ACT", "weight": 0.036}]
LONG_HISTORY = [{"symbol": "BCH", "weight": 0.685}, {"symbol": "OKB", "weight": 0.315}]


def _read(mcp, legs, period):
    payload = mcp.call(TOOL, {"constituents": legs, "period_days": period,
                              "starting_capital": 1000})
    node = payload
    for _ in range(4):
        if isinstance(node, dict) and isinstance(node.get("result"), (dict, str)):
            node = node["result"]
        else:
            break
    if not isinstance(node, dict):
        raise Inconclusive(f"{TOOL} answered something that is not an object")
    return node


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_a_backtest_says_the_window_it_actually_covered(mcp_trusted):
    """Asked for a year, given four months, and told it was a year."""
    readings = {}
    for name, legs in (("short", SHORT_HISTORY), ("long", LONG_HISTORY)):
        for period in (LONG, LONGER):
            answer = _read(mcp_trusted, legs, period)
            points = answer.get("n_points")
            if not isinstance(points, (int, float)):
                raise Inconclusive(
                    f"{TOOL} returned no n_points for the {name} basket, so "
                    f"what window it covered cannot be read at all")
            readings[(name, period)] = {
                "n_points": points,
                "period_days": answer.get("period_days"),
                "total_return_pct": answer.get("total_return_pct"),
                "sharpe_ratio": answer.get("sharpe_ratio"),
                # Anything that already names the truth would make this check
                # wrong, so it is read rather than assumed absent -- for its
                # VALUE, which is where this went wrong until 2026-09-12.
                "answer": answer,
            }

    control = readings[("long", LONG)], readings[("long", LONGER)]
    if control[0]["n_points"] == control[1]["n_points"]:
        raise Inconclusive(
            "both windows returned the same number of points for the control "
            "basket too, so this run cannot tell a truncated window from a "
            "tool that ignores period_days")

    # The control basket is what makes a label checkable: it has the history,
    # so its points over its window are the sampling rate, and a label that
    # disagrees with the points is not a reading of them. V03, 2026-09-13.
    per_day = control[1]["n_points"] / float(LONGER)
    for reading in readings.values():
        reading["says_covered"] = says_covered(
            reading.pop("answer"), reading["period_days"] or LONGER, per_day)

    short = readings[("short", LONG)], readings[("short", LONGER)]
    truncated = short[0]["n_points"] == short[1]["n_points"]
    named = bool(short[1]["says_covered"])

    if not truncated:
        # The subject is a window that was truncated and labelled anyway. WIF,
        # PNUT, GOAT and ACT are 2026 coins: every day that passes lengthens
        # their history, and the day it reaches past 180 days the two requests
        # stop agreeing and there is no truncation here to mislabel. That is
        # the calendar moving, not their fix landing -- and this branch read
        # "passed" until 2026-09-12, which on a filed row is a verification
        # sent for something nobody repaired. Rule 10, inverted: what cannot be
        # measured is not a pass any more than it is a defect. B04, triage 3/3.
        raise Inconclusive(
            f"{LONG} and {LONGER} days now return different readings for the "
            f"short basket ({short[0]['n_points']:.0f} vs "
            f"{short[1]['n_points']:.0f} points), so its legs have grown the "
            f"history and there is no truncated window here to be mislabelled "
            f"-- pick a younger basket, or this run proves nothing either way")

    conclude(Measurement(
        verdict="failed" if not named else "passed",
        reason=(
            f"asked for {LONGER} days and given {short[1]['n_points']:.0f} "
            f"points -- the same reading as {LONG} days, to the decimal -- "
            f"while the answer reports period_days {short[1]['period_days']} "
            f"and nothing that names the window actually covered. The same "
            f"two requests on a basket whose legs have the history differ "
            f"({control[0]['n_points']:.0f} vs {control[1]['n_points']:.0f} "
            f"points), so the truncation is the data, not the tool ignoring "
            f"the argument. An agent ranking by Sharpe, which your guidance "
            f"asks for, compares a real {LONGER}-day figure with a "
            f"{short[1]['n_points']:.0f}-day one wearing the same label"
            if not named else
            f"the {LONGER}-day answer names the window it covered "
            f"({', '.join(short[1]['says_covered'])})"),
        left={"asked_365": short[1], "asked_180": short[0]},
        right={"control_365": control[1], "control_180": control[0]},
        population={"basket": [leg["symbol"] for leg in SHORT_HISTORY],
                    "control": [leg["symbol"] for leg in LONG_HISTORY]},
        sources={"tool": f"POST /mcp/v1 tools/call {TOOL}",
                 "their_fix_on_the_sibling": "#97, fixed 2026-09-12"}))
