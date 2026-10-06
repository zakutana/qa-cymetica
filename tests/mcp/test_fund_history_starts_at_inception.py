"""A fund's history, fetched the way their advisor skill says, starts at inception.

Cymetica published an advisor connector on 2026-09-19 (`/.well-known/mcp.json`
-> `advisor_connector`): four read-only tools on /mcp/v1, no key, and a skill
for financial-advisor assistants at
https://cymetica.com/static/plugins/eventtrader-funds/skills/fund-research/SKILL.md.
Its workflow step 4, verbatim:

    For a chart or a trend question, call `get_fund_history` with the symbol.

and the tool's own description says the AIB series is "hourly since
inception"; `get_fund_methodology` says returns are "measured since the fund's
own inception". So what an advisor charts, following their instructions, is
the history as `get_fund_history(symbol)` returns it -- and that series should
begin where the fund began.

**What was seen when this was written.** The tool's `points` parameter is
"last N points (default 80, max 400)". Their stored AIB series ran to 81
points, so the default dropped exactly one -- the oldest, which is the
inception point. AIB-SPACE: inception 64.162 on 2026-08-14, first point
returned 59.3413 on 2026-08-25, so the chart an advisor draws rises about 5%
beside a `return_since_inception_pct` of -5.17. With `points: 200` the same
call starts at 64.162. The public page's own chart starts at inception too.

**Anchored on the first point against `inception_index_price_usd`**, both from
their own tools, because that comparison reads nothing time-sensitive. The
alternative -- history-implied return against `return_since_inception_pct` --
mixes the last history point with a fresher NAV and gaps by up to a point on
time skew alone, which would make the check flap.

**Tolerance 2%.** A legitimately late first sample (the first stored point
some minutes after inception) sits under half a percent in today's data; the
clipped ones were 2.6-15% off. Funds clipped by only hours sit at 0.5-1.1%
-- they cannot be told apart from a late first sample by this comparison, so
they are listed in `population` as unseparated rather than counted either
way. A fund with no published inception price (MA-RIPPLE, the
FTA sleeves, EVENT-CARD) or whose history call fails is unmeasured for that
fund, never a defect: a failed read is not an empty read (rule 8).

Deliberately NOT asserted: the number of points, the sampling, or that the
default must be any particular value. Raising the default, returning the whole
series, or telling advisors in the skill to pass `points` would each fix what
an advisor sees, and which one is theirs to choose
(`a-check-encodes-the-fix-its-author-imagined`).
"""

from __future__ import annotations

import time

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOLERANCE_PCT = 2.0
# Below this a first point is a late first sample, not a clipped series.
UNSEPARATED_PCT = 0.3
# Their surface answered 429 at about one call a second on 2026-09-19.
PAUSE_S = 4.0
SKILL = ("https://cymetica.com/static/plugins/eventtrader-funds/skills/"
         "fund-research/SKILL.md")


def _body(answer):
    """Their tools wrap the payload in {success, tool, result}."""
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="mcp",
    claim="fund-history-starts-at-inception")
def test_a_fund_history_fetched_as_their_skill_says_starts_at_inception(mcp_anon):
    """Every fund's get_fund_history(symbol), first point vs its inception level."""
    try:
        roster = _body(mcp_anon.call("list_funds", {"limit": 100})).get("funds") or []
    except McpError as exc:
        raise Inconclusive(f"list_funds failed, so there is no roster: {exc}")
    if not roster:
        raise Inconclusive("list_funds returned no funds, so there is nothing "
                           "to hold against inception")

    clipped, unseparated, within, unmeasured = [], [], [], []
    for row in roster:
        symbol = row.get("symbol")
        if not symbol:
            continue
        try:
            time.sleep(PAUSE_S)
            answer = _body(mcp_anon.call("get_fund", {"symbol": symbol}))
            time.sleep(PAUSE_S)
            # No `points`: step 4 of their skill passes the symbol and nothing
            # else, and that call is what an advisor charts.
            history = _body(mcp_anon.call("get_fund_history", {"symbol": symbol}))
        except McpError as exc:
            unmeasured.append(f"{symbol}: read failed ({str(exc)[:80]})")
            continue
        fund = answer.get("fund")
        if not isinstance(fund, dict):
            # An answer with no fund in it is a read that failed -- a rate
            # limit came back this way on the first run -- not a fund that
            # publishes no inception level.
            unmeasured.append(f"{symbol}: get_fund carried no fund "
                              f"({answer.get('code') or answer.get('error') or sorted(answer)})")
            continue
        inception = fund.get("inception_index_price_usd")
        points = history.get("points") or []
        if not inception:
            unmeasured.append(f"{symbol}: no inception_index_price_usd")
            continue
        if not points or not isinstance(points[0], dict) or points[0].get("v") is None:
            unmeasured.append(f"{symbol}: history has no readable point "
                              f"({history.get('code') or history.get('error') or 'empty'})")
            continue
        first = points[0]
        off = round((float(first["v"]) / float(inception) - 1) * 100, 2)
        seen = {"symbol": symbol, "inception": inception, "first_t": first.get("t"),
                "first_v": first["v"], "off_pct": off, "returned": len(points),
                "return_since_inception_pct": fund.get("return_since_inception_pct")}
        if abs(off) > TOLERANCE_PCT:
            # A gap is a clip only if a longer read starts EARLIER. The first
            # sweep after their fix (2026-10-06) found AIB-DATA-CENTERS 3.27% off
            # with the same first point (2026-07-28T21:00, 146.181) at the default
            # and at points=400: nothing was clipped, the stored series simply
            # begins that far from inception -- a late first sample, which this
            # comparison cannot tell from a clip without the control. Their fix
            # keeps the oldest point whatever the limit, so the old reading of
            # every gap as a clip had become wrong.
            try:
                time.sleep(PAUSE_S)
                full = _body(mcp_anon.call("get_fund_history",
                                           {"symbol": symbol, "points": 400}))
            except McpError as exc:
                unmeasured.append(f"{symbol}: control read failed ({str(exc)[:80]})")
                continue
            full_points = full.get("points") or []
            if not full_points or not isinstance(full_points[0], dict):
                unmeasured.append(f"{symbol}: control read had no readable point")
                continue
            seen["full_first_t"], seen["full_returned"] = full_points[0].get("t"), len(full_points)
            if full_points[0].get("t") == first.get("t"):
                unseparated.append(seen)
            else:
                clipped.append(seen)
        elif abs(off) > UNSEPARATED_PCT:
            unseparated.append(seen)
        else:
            within.append(symbol)

    measured = len(clipped) + len(unseparated) + len(within)
    if not measured:
        raise Inconclusive(f"no fund could be measured: {'; '.join(unmeasured)}")

    clipped.sort(key=lambda s: -abs(s["off_pct"]))
    worst = clipped[0] if clipped else None
    conclude(Measurement(
        verdict="failed" if clipped else "passed",
        reason=(f"{len(clipped)} of {measured} fund histories, fetched as their "
                f"advisor skill says (symbol only), start more than "
                f"{TOLERANCE_PCT:g}% away from the fund's own inception level -- "
                f"worst {worst['symbol']}: first point {worst['first_v']} at "
                f"{worst['first_t']} against inception {worst['inception']} "
                f"({worst['off_pct']:+}%), while it reports "
                f"{worst['return_since_inception_pct']}% since inception"
                if clipped else
                f"all {measured} measurable fund histories start within "
                f"{TOLERANCE_PCT:g}% of inception"),
        left=[s["off_pct"] for s in clipped],
        right=TOLERANCE_PCT,
        population={"clipped": clipped, "unseparated": unseparated,
                    "within": within, "unmeasured": unmeasured,
                    "roster": len(roster)},
        sources={"contract": f"{SKILL} step 4, and get_fund_history's own "
                             f"description ('hourly since inception')",
                 "inception": "get_fund.inception_index_price_usd",
                 "history": "get_fund_history(symbol), no points argument"},
        claim_id="fund-history-starts-at-inception"))
