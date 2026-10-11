"""Agent Tournaments offers for a seat only bots that exist (2026-10-11).

Agent Tournaments (cymetica.com/agent-tournaments, the Build it Better app ET-30773, shipped
2026-10-10) lets an owner seat one of their bots at a 10-seat table. Its llms.txt entry names
`GET /api/v1/agent-tournaments/my-bots` (X-API-Key) as the list an agent picks from, and the
rules it serves say: "On approval your bot gets the table's trading capital from your paper USDC
and starts trading."

**What was seen when this was written** (2026-10-11, 17:30-17:50 UTC, our key): /my-bots offered
53 bots; GET /api/v1/cloned-bots/my-clones (paper and live) listed 41. Each of the 12 others
answered GET /api/v1/cloned-bots/{id}/profile with 404 "Bot not found." -- clones that were
deleted, among them "lab MACD Hunter" (996cd23e-...), which we deleted on 2026-09-28 (our
record CLN-0101, DELETE -> 200) and which /my-bots listed with trading: true. Table 2 (paper,
Pro, running since 16:46 UTC) had a member seat, seat_id 1, named "lab MACD Hunter", with 0
trades and 0 volume while the house seats had 1 to 20 trades each.

**The rule.** Every bot /my-bots offers is one the platform still knows: in our clone list, or
its profile answers 200. A bot whose profile answers 404 is offered but gone. Passes the moment
the list leaves deleted bots out, however that is done.

NOT asserted: anything about a table, a seat or its trades (stated as context above), the
order of the list, or the `trading` flag of a bot that exists.

SAFE: GETs only, our own bots with our key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLONES = "/api/v1/cloned-bots"
CLAIM = "agent-tournaments-offers-only-bots-that-exist"


def _rows(said) -> list[dict]:
    rows = said if isinstance(said, list) else (said or {}).get("bots") or (said or {}).get(
        "clones") or (said or {}).get("items") or []
    return [row for row in rows if isinstance(row, dict)]


def offered_but_gone(offered: list[dict], have: set[str],
                     statuses: dict[str, int]) -> tuple[list[dict], list[str]]:
    """The offered bots the platform no longer knows (their profile answered 404), and the ones
    that could not be read. A bot in our own clone list is known without asking."""
    gone, unread = [], []
    for bot in offered:
        bot_id = bot.get("instance_id")
        if not bot_id or bot_id in have:
            continue
        status = statuses.get(bot_id)
        if status == 404:
            gone.append(bot)
        elif status != 200:
            unread.append(bot_id)
    return gone, unread


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_offers_only_bots_that_exist(rest_trusted):
    """/my-bots against our clone list and, for the rest, each bot's own profile."""
    r = rest_trusted.get(f"{PREFIX}/my-bots")
    if r.status_code != 200:
        raise Inconclusive(f"{PREFIX}/my-bots answered HTTP {r.status_code}")
    offered = _rows(r.json())
    if not offered:
        raise Inconclusive(f"{PREFIX}/my-bots offered no bot; nothing to judge")
    have: set[str] = set()
    for mode in ("paper", "live"):
        mine = rest_trusted.get(f"{CLONES}/my-clones", params={"mode": mode})
        if mine.status_code != 200:
            raise Inconclusive(f"my-clones?mode={mode} answered HTTP {mine.status_code}")
        have |= {row.get("id") for row in _rows(mine.json()) if row.get("id")}
    statuses = {}
    for bot in offered:
        bot_id = bot.get("instance_id")
        if bot_id and bot_id not in have:
            statuses[bot_id] = rest_trusted.get(f"{CLONES}/{bot_id}/profile").status_code
    gone, unread = offered_but_gone(offered, have, statuses)
    if unread and not gone:
        raise Inconclusive(f"{len(unread)} offered bot(s) could not be read: {unread[:6]}")
    named = "; ".join(f"{b.get('name')!r} ({str(b.get('instance_id'))[:8]}, trading "
                      f"{b.get('trading')})" for b in gone[:12])
    conclude(Measurement(
        verdict="failed" if gone else "passed",
        reason=(f"{len(gone)} of the {len(offered)} bots {PREFIX}/my-bots offers for a seat no "
                f"longer exist: their profile answers 404 'Bot not found.', and our clone lists "
                f"(paper and live) hold {len(have)}. {named}"
                if gone else
                f"all {len(offered)} bots {PREFIX}/my-bots offers exist ({len(have)} in our clone "
                f"lists, the rest with a profile)"),
        left={"offered_but_gone": len(gone)},
        right={"offered_but_gone": 0},
        population={"offered": len(offered), "in_our_clone_lists": len(have),
                    "asked_by_profile": len(statuses), "unread": unread,
                    "gone": [{"instance_id": b.get("instance_id"), "name": b.get("name"),
                              "trading": b.get("trading")} for b in gone]},
        sources={"offered": f"{PREFIX}/my-bots", "known": f"{CLONES}/my-clones?mode=paper|live",
                 "profile": f"{CLONES}/{{id}}/profile",
                 "contract": "llms.txt: GET /my-bots is the list an owner seats from; the rules: "
                             "'On approval your bot gets the table's trading capital ... and "
                             "starts trading'"},
        claim_id=CLAIM))
