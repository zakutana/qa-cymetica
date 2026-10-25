"""/traffic: "AI-agent visits" and the agents' requests by area are both "every request", and differ by a quarter.

https://cymetica.com/traffic defines its two agent figures in the same words. The tile "AI-agent visits"
(`id="k-agents"`, filled from `GET /api/v1/traffic/public` -> `ai_agents.total`) is, in the AI Agents panel:

    Visits = every request an agent makes (one crawler reading 300 pages is 300 visits).

and the list "AI agents requests" under "What visitors do" (`id="tl-do-agent"`, filled from
`GET /api/v1/traffic/activity` -> `requests.ai_agent.range` when "Selected range" is chosen) is:

    Every request, landings AND the pages and API calls after them, grouped by product area.

The list ends in an "Everything else" row, so it is the whole and not a top ten. Read on 2026-10-26 around
23:17 UTC (2026-10-25), both endpoints with `days=14` and the same `since` (2026-10-11T07:00Z), four seconds
apart: the tile 115,359, the list 89,770 -- 25,589 requests (22 %) in one figure and not in the other. At
`days=7` 67,113 against 59,030 (12 %), at `days=30` 195,354 against 133,871 (31 %): the older the days, the
wider the gap, so it is not the few minutes the two caches can lie apart.

**The rule.** While the page defines both figures as every request (or all requests) and neither definition
says what it leaves out, the two totals over the same range agree within 2 % (the endpoints are cached a few
minutes apart; 2 % of the smallest real total is over a thousand requests). Either fix passes: the numbers
made to agree, or the page saying what one of them excludes (a definition that names an exception, or one
that stops claiming every request). The second is a fix of the words, and it is theirs to choose.

VERDICTS. failed: both definitions claim every request, neither names an exception, the two ranges are the
same, the list has a remainder row, and the totals differ by more than 2 %. passed: the totals agree within
2 % (a whole list then, remainder row or not); or the tile and the list are on the page and the two
definitions no longer both claim every request without an exception. inconclusive: the page, either
endpoint or a field unreadable; the tile or the list gone from the page; different `since` or `days`;
the two snapshots generated more than 30 minutes apart; an empty list; no remainder row while the totals
disagree (the list may be a top ten).

NOT asserted: which of the two figures is right; the human figures (humans' "Visits" are landings, a
different measure the page names as such); the 24-hour list, which has no tile to agree with; the daily
lines in the chart.
SAFE: three anonymous GETs.
"""

from __future__ import annotations

import re
from datetime import datetime
from html import unescape

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

CLAIM = "traffic-agent-visits-are-the-agents-requests"
PAGE = "/traffic"
DAYS = 14
PUBLIC = f"/api/v1/traffic/public?days={DAYS}"
ACTIVITY = f"/api/v1/traffic/activity?days={DAYS}"
TOLERANCE = 0.02
FLOOR = 50
MAX_SKEW_S = 30 * 60

# Anchored on their markup: the tile's id, the list's id, and the <strong>Visits</strong> = definition.
TILE_ID = re.compile(r'\bid="k-agents"')
LIST_ID = re.compile(r'\bid="tl-do-agent"')
PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
VISITS_DEF = re.compile(r"<strong>\s*Visits\s*</strong>\s*=(.*?)(?:<strong>|$)", re.S | re.I)
EVERY = re.compile(r"\b(?:every|all|each)\b[^.<]{0,40}?\brequests?\b", re.I)
EXCEPT = re.compile(r"\b(?:except\w*|exclud\w*|only|apart from|other than|leaves? out|left out|omit\w*"
                    r"|not (?:counted|included|in (?:it|this|the list|these)))\b", re.I)
REMAINDER = re.compile(r"everything else|\ball other\b|\bthe rest\b|\bremainder\b", re.I)


def _plain(fragment: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def page_facts(html: str) -> dict:
    """What the page says the two agent figures are, read from its own markup."""
    tile_def = list_def = None
    for body in PARAGRAPH.findall(html):
        m = VISITS_DEF.search(body)
        if m and tile_def is None:
            tile_def = _plain(m.group(1))
        elif list_def is None and re.search(r"grouped by product area", _plain(body), re.I):
            list_def = _plain(body)
    def claims_every(definition: str | None) -> bool:
        return bool(definition) and bool(EVERY.search(definition)) and not EXCEPT.search(definition)

    return {
        "sections": bool(TILE_ID.search(html)) and bool(LIST_ID.search(html)),
        "tile_definition": tile_def,
        "list_definition": list_def,
        "promise": claims_every(tile_def) and claims_every(list_def),
    }


def _when(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _count(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def judge(facts: dict, public: dict, activity: dict) -> tuple[str | None, str, dict]:
    """(verdict or None for inconclusive, why, the numbers it rests on)."""
    numbers: dict = {}
    if not facts.get("sections"):
        return None, f"{PAGE} no longer has the AI-agent visits tile and the AI agents requests list", numbers
    visits = _count((public.get("ai_agents") or {}).get("total")) if isinstance(public, dict) else None
    rows = ((activity.get("requests") or {}).get("ai_agent") or {}).get("range") if isinstance(activity, dict) else None
    if visits is None:
        return None, "the public endpoint gave no whole-number ai_agents.total", numbers
    if not isinstance(rows, list) or not rows:
        return None, "the activity endpoint gave no requests.ai_agent.range rows", numbers
    counts = [_count(r.get("requests")) if isinstance(r, dict) else None for r in rows]
    if any(c is None for c in counts):
        return None, "a requests.ai_agent.range row has no whole-number requests", numbers
    requests = sum(counts)
    remainder = next((r.get("area") for r in rows if REMAINDER.search(str(r.get("area") or ""))), None)
    numbers = {"agent_visits": visits, "agent_requests_by_area": requests, "gap": visits - requests,
               "gap_share": round(abs(visits - requests) / max(visits, requests), 4) if max(visits, requests) else 0.0,
               "remainder_row": remainder, "rows": len(rows),
               "since": [public.get("since"), activity.get("since")],
               "days": [public.get("days"), activity.get("days")],
               "generated_at": [public.get("generated_at"), activity.get("generated_at")]}
    if public.get("since") != activity.get("since") or public.get("days") != activity.get("days"):
        return None, (f"the two endpoints cover different ranges (since {public.get('since')} / "
                      f"{activity.get('since')}, days {public.get('days')} / {activity.get('days')})"), numbers
    a, b = _when(public.get("generated_at")), _when(activity.get("generated_at"))
    if a and b and abs((a - b).total_seconds()) > MAX_SKEW_S:
        return None, f"the two snapshots were generated {abs((a - b).total_seconds()) / 60:.0f} minutes apart", numbers
    if abs(visits - requests) <= max(TOLERANCE * max(visits, requests), FLOOR):
        return "passed", (f"AI-agent visits {visits:,} and the agents' requests by area {requests:,} agree "
                          f"over the same range"), numbers
    if not facts.get("promise"):
        return "passed", ("the page no longer defines both figures as every request without naming an "
                          "exception, so it no longer says they are the same count"), numbers
    if remainder is None:
        return None, (f"the agents' list has no remainder row and adds up to {requests:,} against "
                      f"{visits:,}: it may be a top list, not a whole"), numbers
    return "failed", (f"{PAGE} defines AI-agent visits as \"{facts['tile_definition']}\" and the AI agents "
                      f"requests list as \"{facts['list_definition']}\", but over the same {public.get('days')} "
                      f"days (since {public.get('since')}) the tile reads {visits:,} and the list, "
                      f"{len(rows)} rows ending in \"{remainder}\", adds up to {requests:,}: "
                      f"{abs(visits - requests):,} requests ({numbers['gap_share']:.0%}) are in one figure "
                      f"and not in the other"), numbers


def _json(client, url: str) -> dict:
    try:
        got = get_patiently(client, url)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{url} could not be read: {type(exc).__name__}")
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    try:
        body = got.json()
    except ValueError:
        raise Inconclusive(f"{url} answered 200 without JSON")
    if not isinstance(body, dict):
        raise Inconclusive(f"{url} answered JSON that is not an object")
    return body


@qa(component="rest.traffic", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_traffic_agent_visits_are_the_agents_requests(rest_anon):
    """The tile and the list the page defines as the same count, over the same range."""
    try:
        page = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{PAGE} could not be read: {type(exc).__name__}")
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    facts = page_facts(page.text)
    public = _json(rest_anon, PUBLIC)
    activity = _json(rest_anon, ACTIVITY)
    verdict, why, numbers = judge(facts, public, activity)
    if verdict is None:
        raise Inconclusive(why)
    conclude(Measurement(
        verdict=verdict,
        reason=why,
        left={"ai_agent_visits": numbers.get("agent_visits")},
        right={"ai_agent_requests_by_area": numbers.get("agent_requests_by_area")},
        population={**numbers, "tile_definition": facts["tile_definition"],
                    "list_definition": facts["list_definition"],
                    "area_rows": [{"area": r.get("area"), "requests": r.get("requests")}
                                  for r in ((activity.get("requests") or {}).get("ai_agent") or {}).get("range") or []]},
        sources={"page": f"{PAGE} (#k-agents, #tl-do-agent, the <strong>Visits</strong> = paragraph and the "
                         f"'grouped by product area' paragraph)",
                 "tile": f"{PUBLIC} -> ai_agents.total",
                 "list": f"{ACTIVITY} -> requests.ai_agent.range"},
        claim_id=CLAIM))
