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
where the record starts (and the return then follows from that record), or
tell advisors the pro-forma stretch is in it -- a sentence that mentions
pro-forma only to deny it ("no pro-forma") is not that disclosure. A read
that fails is unmeasured, never a defect (rule 8).
"""

from __future__ import annotations

import re
from datetime import date

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

HISTORY = "/api/v1/fta-fund/history"
SYMBOL = "FTA-CRYPTOS"
NO_BACKFILL = "nothing backfilled"
PRO_FORMA = re.compile(r"pro[\s-]?forma", re.IGNORECASE)
# A03, deep pass of 2026-09-21 (3/3): "nothing backfilled, no pro-forma, no
# backtest" DENIES the stretch, and was read as disclosing it. A mention with a
# negation in the few words before it, inside the same clause, is a denial --
# "No backfill. Pro-forma: ..." is a disclosure, and a false fail is a claim.
# A02, deep pass of 2026-09-22: "nothing backfilled or pro-forma" is a denial
# too, and "nothing", "none" and "neither" were not negations here.
DENIED = re.compile(r"\b(?:no|not|never|nor|neither|none|nothing|without|zero)\b"
                    r"(?:[\s,'-]+\w+){0,3}?"
                    r"[\s,'-]+pro[\s-]?forma", re.IGNORECASE)
# C07, deep pass of 2026-09-22 evening (3/3): the negation can come AFTER the
# word -- "pro-forma periods are excluded", "pro-forma figures are never used"
# -- inside the same clause, and read as a disclosure. And "exclude(s) any
# pro-forma" puts the verb first.
DENIED_AFTER = re.compile(r"^pro[\s-]?forma(?:[\s,'-]+\w+){0,4}?[\s,'-]+"
                          r"(?:excluded|never|not|omitted|removed|isn't|aren't)\b",
                          re.IGNORECASE)
EXCLUDES = re.compile(r"\bexclud(?:e|es|ing)\b(?:[\s,'-]+\w+){0,2}?[\s,'-]+"
                      r"pro[\s-]?forma", re.IGNORECASE)
RETURN_SLACK_PP = 5.0


def discloses_pro_forma(text: str) -> bool:
    """Whether the methodology says a pro-forma stretch is IN the return."""
    def denied(m) -> bool:
        before = text[:m.end()][-80:]
        clause = re.split(r"[.;]", text[m.start():m.start() + 120], 1)[0]
        return bool(DENIED.search(before) or EXCLUDES.search(before)
                    or DENIED_AFTER.search(clause))
    return any(not denied(m) for m in PRO_FORMA.finditer(text))


def _short_return(points) -> float | None:
    """The short book's return from its record's first point to its last."""
    values = [p.get("v") for p in points or [] if isinstance(p, dict)]
    values = [float(v) for v in values if isinstance(v, (int, float)) and v > 0]
    if len(values) < 2:
        return None
    return round(-(values[-1] / values[0] - 1.0) * 100.0, 4)


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

    # R09/A03, deep pass of 2026-09-21 (3/3): "the methodology no longer says
    # 'nothing backfilled'" passed on any rewording of an unchanged claim. The
    # fix the report offered is a DISCLOSURE, so that is what is looked for;
    # and dates that agree on paper while the return still spans the old start
    # are not taken as the fix either.
    disclosed = discloses_pro_forma(returns_rule)
    claims_none = not disclosed
    early = published < recorded
    if claims_none and not early:
        ret = fund.get("return_since_inception_pct")
        implied = _short_return(points)
        if (not isinstance(ret, (int, float)) or implied is None
                or abs(float(ret) - implied) > RETURN_SLACK_PP):
            raise Inconclusive(
                f"the inceptions now agree ({published}), but the published "
                f"return {ret} % does not follow from the record it names "
                f"({implied} % from its first point) -- a relabel is not the fix")
    conclude(Measurement(
        verdict="failed" if (claims_none and early) else "passed",
        reason=(f"get_fund publishes {SYMBOL}'s return ({fund.get('return_since_inception_pct')} %) "
                f"since {published}, while the fund's own history says its inception "
                f"is {recorded} (first point {first_point}): the published return starts "
                f"{(recorded - published).days} days before the record does, with the "
                f"composition last changed "
                f"{fund.get('last_composition_change')}; the methodology discloses "
                f"no pro-forma stretch"
                + (f" and says '{NO_BACKFILL}'" if NO_BACKFILL in returns_rule.lower()
                   else "")
                if (claims_none and early) else
                f"published inception {published}, recorded {recorded}; "
                + ("the methodology discloses the pro-forma stretch" if disclosed
                   else "the published return follows from the record")),
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
