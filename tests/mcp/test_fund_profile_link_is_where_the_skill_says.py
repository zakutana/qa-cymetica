"""The link their advisor skill tells an assistant to cite is on every fund.

The advisor connector's skill
(https://cymetica.com/static/plugins/eventtrader-funds/skills/fund-research/SKILL.md)
ends with "Links to cite", and its line for a single fund is, verbatim:

    - One fund: `profile_url` from `get_fund`

An assistant briefing a client follows that line. So the measurable promise is
narrow: for every symbol `list_funds` hands out, `get_fund` carries a
`profile_url`.

**What was seen when this was written.** Twenty of twenty-four funds carry it.
The four that do not are the non-AIB sleeves -- MA-RIPPLE, FTA-STOCKS,
FTA-CRYPTOS and EVENT-CARD -- which come back with a different field set
altogether: a `url` instead (https://cymetica.com/ma-fund, /fta-fund, an event
page), and no `inception_index_price_usd`. The link exists, under another
name; an assistant told to read `profile_url` finds nothing, and the fund it
cannot link is the one holding real USDC.

**A fund that carries `url` and not `profile_url` is counted, and the reason
says so**, because the fix is theirs to pick: add `profile_url` to those
sleeves, or change that line of the skill. Either satisfies this check. A
symbol whose `get_fund` read fails is unmeasured for that fund, never a
defect (rule 8).

Deliberately NOT asserted: that the link resolves, or which URL it should be.
Fetching each one would make this a slow check about their web tier, and the
claim being measured is about the field an assistant is told to read.
"""

from __future__ import annotations

import time

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PAUSE_S = 4.0
SKILL = ("https://cymetica.com/static/plugins/eventtrader-funds/skills/"
         "fund-research/SKILL.md")


def _body(answer):
    """Their tools wrap the payload in {success, tool, result}."""
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="mcp",
    claim="fund-profile-link-where-the-skill-says")
def test_every_listed_fund_carries_the_profile_link_the_skill_names(mcp_anon):
    """list_funds -> get_fund: is `profile_url` there, for every symbol?"""
    try:
        roster = _body(mcp_anon.call("list_funds", {"limit": 100})).get("funds") or []
    except McpError as exc:
        raise Inconclusive(f"list_funds failed, so there is no roster: {exc}")
    if not roster:
        raise Inconclusive("list_funds returned no funds")

    missing, present, unmeasured = [], [], []
    for row in roster:
        symbol = row.get("symbol")
        if not symbol:
            continue
        try:
            time.sleep(PAUSE_S)
            fund = _body(mcp_anon.call("get_fund", {"symbol": symbol})).get("fund")
        except McpError as exc:
            unmeasured.append(f"{symbol}: read failed ({str(exc)[:80]})")
            continue
        if not isinstance(fund, dict):
            unmeasured.append(f"{symbol}: get_fund carried no fund")
            continue
        if fund.get("profile_url"):
            present.append(symbol)
        else:
            missing.append({"symbol": symbol, "status": fund.get("status"),
                            "sleeve": row.get("sleeve"),
                            "url_instead": fund.get("url"),
                            "fields": sorted(fund)})

    measured = len(missing) + len(present)
    if not measured:
        raise Inconclusive(f"no fund could be read: {'; '.join(unmeasured)}")

    named = ", ".join(f"{m['symbol']}"
                      + (f" (carries url {m['url_instead']})" if m["url_instead"] else "")
                      for m in missing)
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} of {measured} funds carry no profile_url, the "
                f"field their advisor skill tells an assistant to cite for one "
                f"fund: {named}"
                if missing else
                f"all {measured} listed funds carry profile_url"),
        left=sorted(m["symbol"] for m in missing), right="profile_url on every fund",
        population={"missing": missing, "present": present,
                    "unmeasured": unmeasured, "roster": len(roster)},
        sources={"contract": f"{SKILL}, 'Links to cite': One fund: profile_url "
                             f"from get_fund",
                 "roster": "list_funds(limit=100)", "fund": "get_fund(symbol)"},
        claim_id="fund-profile-link-where-the-skill-says"))
