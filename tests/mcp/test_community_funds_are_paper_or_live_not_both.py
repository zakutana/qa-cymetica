"""A community fund is paper or it is live -- the pages do not say both.

Three of their own surfaces describe the same funds:

  * /fund-launcher, under "Before you start": *Community funds -- Paper
    trading only. The index, terminal and management are real-time. Buying in
    is simulated.* The builder says it again: *Community funds trade in paper
    mode (simulated) -- no real USDC is invested.*
  * /fund-performance, the legend over "All funds, ranked": *LIVE funds take
    real USDC; PAPER funds trade simulated and take no investment yet.* The
    table then marks every Community AIB fund `live`.
  * `list_funds` / `get_fund` on their MCP: Community AIB funds carry
    `status: live` and an `invest_url` (/fund/apply?invest=<symbol>); the
    fund's own profile page offers "Invest in <fund> now -- it's LIVE", and
    /fund/apply says "Every fund below is live ... shares are issued at each
    fund's live NAV".

**What was seen when this was written** (2026-09-25): 11 Community AIB funds,
every one `status: live`, among them AIB-8830DFE9 "Privacy" with
`invest_url` https://cymetica.com/fund/apply?invest=AIB-8830DFE9, while the
launcher says buying into a community fund is simulated. A stranger cannot
tell whether money put into one is real. Which statement is right is theirs
to say; that both are published is the defect.

**The claim, and what settles it.** Fails when the launcher still says
community funds are paper-only AND a Community AIB fund is `live` on their MCP
AND its profile page offers to invest in it as live. Passes when any one of
those stops being true -- the launcher corrected, the funds labelled paper, or
the live invest offer gone -- because each is a way of making the three agree,
and which is theirs (`a-check-encodes-the-fix-its-author-imagined`).

**Nothing is bought.** GETs of three public pages and two read-only MCP tools.
Up to PROFILES community profiles are read, spaced for their rate limit.
"""

from __future__ import annotations

import html
import re
import time

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SITE = "https://cymetica.com"
LAUNCHER = SITE + "/fund-launcher"
COMMUNITY = "Community AIB"
PROFILES = 3
PAUSE_S = 4.0

PAPER_ONLY = re.compile(r"Community funds\W+Paper trading only", re.I)
SIMULATED = re.compile(r"Buying in is simulated", re.I)
LIVE_INVEST = re.compile(r"Invest in [^<>]{1,80}? now\W+it'?s LIVE", re.I)


def visible_text(page: str) -> str:
    """What a reader sees: comments, scripts and styles out, tags to spaces."""
    page = re.sub(r"<!--.*?-->|<script.*?</script>|<style.*?</style>", " ",
                  str(page or ""), flags=re.S | re.I)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))


def launcher_says_paper_only(text: str) -> bool:
    return bool(PAPER_ONLY.search(text) and SIMULATED.search(text))


def offers_live_invest(text: str) -> str | None:
    found = LIVE_INVEST.search(text)
    return found.group(0) if found else None


def _body(answer):
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="mcp")
def test_a_community_fund_is_paper_or_live_not_both(mcp_anon):
    """The launcher's paper-only sentence against the funds' own live status."""
    launcher = mcp_anon.http.get(LAUNCHER)
    if launcher.status_code != 200:
        raise Inconclusive(f"{LAUNCHER} answered HTTP {launcher.status_code}")
    says_paper = launcher_says_paper_only(visible_text(launcher.text))

    try:
        roster = _body(mcp_anon.call("list_funds", {"limit": 100})).get("funds") or []
    except McpError as exc:
        raise Inconclusive(f"list_funds failed, so there is no roster: {exc}")
    community = [f for f in roster if f.get("sleeve") == COMMUNITY]
    if not community:
        raise Inconclusive(f"list_funds names no {COMMUNITY} fund, so there is "
                           f"nothing for the launcher's sentence to be about")
    live = [f for f in community if f.get("status") == "live"]

    offers, unread = [], []
    for row in live[:PROFILES]:
        time.sleep(PAUSE_S)
        try:
            fund = _body(mcp_anon.call("get_fund", {"symbol": row["symbol"]})).get("fund") or {}
        except McpError as exc:
            unread.append(f"{row['symbol']} (get_fund: {exc})")
            continue
        url = fund.get("profile_url")
        if not url:
            unread.append(f"{row['symbol']} (no profile_url)")
            continue
        page = mcp_anon.http.get(url)
        if page.status_code != 200:
            unread.append(f"{row['symbol']} (profile HTTP {page.status_code})")
            continue
        said = offers_live_invest(visible_text(page.text))
        if said:
            offers.append({"symbol": row["symbol"], "name": row.get("name"),
                           "invest_url": fund.get("invest_url"),
                           "profile_url": url, "offer": said})
    if live and not offers and len(unread) == len(live[:PROFILES]):
        raise Inconclusive(f"no community profile could be read: {'; '.join(unread)}")

    both = says_paper and bool(live) and bool(offers)
    conclude(Measurement(
        verdict="failed" if both else "passed",
        reason=(f"{LAUNCHER} says community funds are \"Paper trading only ... "
                f"Buying in is simulated\", while {len(live)} of {len(community)} "
                f"{COMMUNITY} funds read status live on list_funds and their "
                f"profiles offer live investment: "
                + "; ".join(f"{o['symbol']} {o['name']!r} \"{o['offer']}\" "
                            f"(invest_url {o['invest_url']})" for o in offers)
                if both else
                f"the launcher {'says' if says_paper else 'no longer says'} "
                f"community funds are paper-only; {len(live)} of {len(community)} "
                f"read live; {len(offers)} profile(s) offer live investment"),
        left={"launcher_paper_only": says_paper, "community_live": len(live),
              "live_invest_offers": len(offers)},
        right="the three surfaces agree on whether a community fund takes real money",
        population={"community": [f.get("symbol") for f in community],
                    "profiles_read": [o["symbol"] for o in offers], "unread": unread},
        sources={"launcher": LAUNCHER, "roster": "MCP list_funds",
                 "fund": "MCP get_fund -> profile_url"}))
