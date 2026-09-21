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

So the skill is READ, with one GET through the client the check already
holds, and the field(s) its "One fund" item names in backticks -- the line and
anything indented under it, less the tool after "from" -- are what a fund has
to carry. Until the deep pass of 2026-09-21 (A11) it was only a string in
`sources`, and the skill fix our own report offered would have gone on
failing. A skill that no longer has that item leaves nothing to hold a fund
to: Inconclusive. A skill that cannot be read falls back to the line quoted
above, and is Inconclusive if any fund lacks `profile_url` -- the unread
half is then the half that decides.

Deliberately NOT asserted: that the link resolves, or which URL it should be.
Fetching each one would make this a slow check about their web tier, and the
claim being measured is about the field an assistant is told to read.
"""

from __future__ import annotations

import re
import time

import httpx

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PAUSE_S = 4.0
SKILL = ("https://cymetica.com/static/plugins/eventtrader-funds/skills/"
         "fund-research/SKILL.md")
# The field that line named when this check was written, and the one held to
# when the skill cannot be read.
QUOTED = ["profile_url"]


def _body(answer):
    """Their tools wrap the payload in {success, tool, result}."""
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


def cited_fields(skill: str) -> list[str]:
    """The field(s) the skill's 'Links to cite' item for one fund names.

    The item is its own line and anything indented under it, so a sleeve
    exception written as a sub-bullet is read with it. Backticked names only,
    less the one after "from" -- that is the tool, not the field. Empty when
    the section or the item is gone.
    """
    lines = (skill or "").splitlines()
    start = next((i for i, line in enumerate(lines)
                  if "links to cite" in line.lower()), None)
    if start is None:
        return []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.lstrip().startswith("#"):
            return []
        if not re.match(r"\s*(?:[-*+]\s+|\d+[.)]\s+)?one fund\b", line, re.I):
            continue
        indent = len(line) - len(line.lstrip())
        item = [line]
        for more in lines[i + 1:]:
            if not more.strip() or len(more) - len(more.lstrip()) <= indent:
                break
            item.append(more)
        return sorted(set(re.findall(r"(?<!from )`([A-Za-z_][A-Za-z0-9_]*)`",
                                     " ".join(item))))
    return []


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="mcp",
    claim="fund-profile-link-where-the-skill-says")
def test_every_listed_fund_carries_the_profile_link_the_skill_names(mcp_anon):
    """list_funds -> get_fund: is the field the skill names there, for every
    symbol?"""
    # The skill first: a skill that names no field ends this before 24 paced
    # reads are spent on it.
    try:
        answer = mcp_anon.http.get(SKILL)
        skill_status = answer.status_code
        skill = answer.text if skill_status == 200 else None
    except httpx.HTTPError as exc:
        skill_status, skill = f"{type(exc).__name__}", None
    if skill is None:
        fields = QUOTED
    else:
        fields = cited_fields(skill)
        if not fields:
            raise Inconclusive(
                f"{SKILL} no longer has a 'Links to cite' item for one fund "
                f"naming a field, so there is no published link to hold the "
                f"funds to")
    wanted = " or ".join(fields)

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
        if any(fund.get(field) for field in fields):
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
    contract = (f"{SKILL}, 'Links to cite': One fund: {wanted}"
                + ("" if skill is not None else
                   f" (as quoted when written; this read got {skill_status})"))
    sources = {"contract": contract, "roster": "list_funds(limit=100)",
               "fund": "get_fund(symbol)"}
    population = {"missing": missing, "present": present,
                  "unmeasured": unmeasured, "roster": len(roster),
                  "skill": {"read": skill is not None, "status": skill_status,
                            "fields": fields}}
    if missing and skill is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"{len(missing)} of {measured} funds carry no {wanted} "
                    f"({named}), but the skill that says which field to cite "
                    f"could not be read ({skill_status}), and its line decides: "
                    f"a skill that now names the field these carry is the fix "
                    f"our report offered"),
            left=sorted(m["symbol"] for m in missing),
            right=f"{wanted} on every fund", population=population,
            sources=sources, claim_id="fund-profile-link-where-the-skill-says"))
        return
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} of {measured} funds carry no {wanted}, the "
                f"field their advisor skill tells an assistant to cite for one "
                f"fund: {named}"
                if missing else
                f"all {measured} listed funds carry {wanted}"
                + ("" if skill is not None else
                   f", the field the skill named when this check was written; "
                   f"the skill itself could not be read ({skill_status})")),
        left=sorted(m["symbol"] for m in missing), right=f"{wanted} on every fund",
        population=population, sources=sources,
        claim_id="fund-profile-link-where-the-skill-says"))
