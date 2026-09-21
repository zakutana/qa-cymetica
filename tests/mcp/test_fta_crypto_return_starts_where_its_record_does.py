"""FTA Fund -- Cryptos: its published return starts before its own record does.

The contract, `get_fund_methodology` (the advisor connector, no key):
"Return is measured since the fund's own inception from real market prices
with timestamped entries -- nothing backfilled, no backtest."

**What was seen when this was written** (2026-09-21):

* `get_fund FTA-CRYPTOS` publishes `inception_date: 2026-07-26` and
  `return_since_inception_pct: -19.05`, with `last_composition_change:
  2026-08-17`.
* The fund's own record, `GET /api/v1/fta-fund/history`, says `inception:
  2026-08-09`, and its first point is 2026-08-21.
* /fund-performance puts the same figure under "Return since inception
  (short)" and explains it in so many words: "Short return of the index since
  2026-07-26 (inception) -- today's composition applied across the full
  period, matching the chart." The page's own script says the period before
  the first held position "is pro-forma (today's composition applied to past
  closes) and must NOT feed the headline change" -- and the headline is
  exactly the figure that does.

So the headline return of a LIVE fund, one that takes real USDC, includes a
stretch before the fund held anything, priced with a basket it only settled on
later. That is a backfill, which the methodology says there is none of.

**What is measured.** The inception `get_fund` publishes against the
inception the fund's own history publishes, while the methodology still says
"nothing backfilled". Either fix satisfies it: start the published return
where the record starts, or stop telling advisors nothing is backfilled. A
read that fails is unmeasured, never a defect (rule 8).
"""

from __future__ import annotations

from datetime import date

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

HISTORY = "/api/v1/fta-fund/history"
SYMBOL = "FTA-CRYPTOS"
NO_BACKFILL = "nothing backfilled"


def _body(answer):
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


def _day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="mcp")
def test_the_fta_crypto_return_starts_where_its_own_record_does(mcp_anon, rest_anon):
    """get_fund's FTA-CRYPTOS inception against its own history's, under 'nothing backfilled'."""
    try:
        methodology = _body(mcp_anon.call("get_fund_methodology", {})).get("methodology") or {}
        fund = _body(mcp_anon.call("get_fund", {"symbol": SYMBOL})).get("fund") or {}
    except McpError as exc:
        raise Inconclusive(f"the connector could not be read: {exc}")
    returns_rule = str(methodology.get("returns") or "")
    # Rule 8. The first preregistered run read an empty methodology in the
    # same minute list_funds came back empty, and "the sentence is gone" was
    # scored a pass. An unreadable contract is not a withdrawn one.
    if not returns_rule.strip():
        raise Inconclusive("get_fund_methodology carried no `returns` text, so the "
                           "contract could not be read")
    published = _day(fund.get("inception_date") or fund.get("inception"))

    response = rest_anon.get(HISTORY)
    if response.status_code != 200:
        raise Inconclusive(f"{HISTORY} answered HTTP {response.status_code}")
    history = response.json() or {}
    recorded = _day(history.get("inception"))
    points = history.get("points") or []
    first_point = _day(points[0].get("t")) if points and isinstance(points[0], dict) else None
    if published is None or recorded is None:
        raise Inconclusive(f"an inception is missing: get_fund {published}, "
                           f"history {recorded}")

    claims_none = NO_BACKFILL in returns_rule.lower()
    early = published < recorded
    conclude(Measurement(
        verdict="failed" if (claims_none and early) else "passed",
        reason=(f"get_fund publishes {SYMBOL}'s return ({fund.get('return_since_inception_pct')} %) "
                f"since {published}, while the fund's own history says its inception "
                f"is {recorded} (first point {first_point}): the published return starts "
                f"{(recorded - published).days} days before the record does, with the "
                f"composition last changed "
                f"{fund.get('last_composition_change')}; the methodology still says "
                f"'{NO_BACKFILL}'"
                if (claims_none and early) else
                f"published inception {published}, recorded {recorded}; the methodology "
                f"{'says' if claims_none else 'no longer says'} '{NO_BACKFILL}'"),
        left=str(published), right=str(recorded),
        population={"get_fund": {k: fund.get(k) for k in (
                        "inception_date", "return_since_inception_pct",
                        "last_composition_change", "status", "index_price_usd")},
                    "history": {"inception": history.get("inception"),
                                "first_point": points[0] if points else None,
                                "points": len(points)},
                    "methodology_returns": returns_rule},
        sources={"contract": "get_fund_methodology.returns: 'nothing backfilled, no backtest'",
                 "published": f"get_fund {{symbol: {SYMBOL}}}",
                 "record": f"GET {HISTORY}"},
    ))
