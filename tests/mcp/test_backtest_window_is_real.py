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
    r"|^(from|to|since|until|start|end)_(date|time|day)$", re.IGNORECASE)

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
                # wrong, so it is read rather than assumed absent -- and
                # `period_days` itself is excluded, because echoing the
                # argument is the claim under question, not an answer to it.
                "says_covered": sorted(
                    key for key in answer
                    if key != "period_days" and NAMES_THE_WINDOW.match(key)),
            }

    control = readings[("long", LONG)], readings[("long", LONGER)]
    if control[0]["n_points"] == control[1]["n_points"]:
        raise Inconclusive(
            "both windows returned the same number of points for the control "
            "basket too, so this run cannot tell a truncated window from a "
            "tool that ignores period_days")

    short = readings[("short", LONG)], readings[("short", LONGER)]
    truncated = short[0]["n_points"] == short[1]["n_points"]
    named = bool(short[1]["says_covered"])

    conclude(Measurement(
        verdict="failed" if truncated and not named else "passed",
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
            if truncated and not named else
            f"the {LONGER}-day answer names the window it covered "
            f"({', '.join(short[1]['says_covered'])})" if named else
            f"{LONG} and {LONGER} days returned different readings "
            f"({short[0]['n_points']:.0f} vs {short[1]['n_points']:.0f} points)"),
        left={"asked_365": short[1], "asked_180": short[0]},
        right={"control_365": control[1], "control_180": control[0]},
        population={"basket": [leg["symbol"] for leg in SHORT_HISTORY],
                    "control": [leg["symbol"] for leg in LONG_HISTORY]},
        sources={"tool": f"POST /mcp/v1 tools/call {TOOL}",
                 "their_fix_on_the_sibling": "#97, fixed 2026-09-12"}))
