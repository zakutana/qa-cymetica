"""A card is tradeable on every surface that says so, or on none.

The contract is the card's own `tradeability` block on
`GET /api/v1/event-cards/{id}` -- the page #117 holds them to:

    tradeable_now: "True when a position can be opened on this card RIGHT NOW
    via POST /buy, /sell or /short (paper or live per your account mode);
    False carries trading_blocked_reason. This is the only trade gate."

Their MCP tool `get_event_card_info` -- the one Nexus reads a card through,
and the one an agent on `/mcp/v1` has -- returns a field of the same name for
the same card. Two answers to "can a position be opened right now", from one
platform, about one card, at one moment, have to be the same answer.

**What was seen when this was written** (2026-09-22, 23:20 UTC, US equity
markets closed -- the listing itself said `us_market_open: false`): of 25
live cards the listing marked closed, 21 read `tradeable_now: false` on REST
with "US equity markets are closed -- this card holds stocks and trades
during US market hours", and `tradeable_now: true` through
`get_event_card_info` in the same minute. Every one of the 21 has stock legs;
the tool's own `trading_window` reads only the card's close date. The same
evening Nexus answered NEX-0078 with card a70b8d5e as "Verified live and
tradeable this run ... get_event_card_info returned status: live,
tradeable_now: true", and the REST gate refused it.

**What it reads.** Up to twelve cards the listing marks closed and four it
marks open, each read on both surfaces a moment apart; the two reads could straddle a market open or
close, which is why the reason names both times. It judges only where one
surface reads a card closed:

  * any card closed on one and open on the other -- fail;
  * at least one card closed on both, none disagreeing -- pass;
  * every card open on both (markets open, nothing closed), or no pair
    readable -- inconclusive: the case this is about was not exercised.

A tool error, an absent card or a non-boolean is unread, never agreement.

SAFE. Up to seventeen GETs and sixteen read-tool calls.
"""

from __future__ import annotations

from datetime import datetime, timezone

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LIST = "/api/v1/event-cards"
CARD = "/api/v1/event-cards/{id}"
TOOL = "get_event_card_info"
SAMPLE = 12
OPEN_SAMPLE = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bool(value):
    return value if isinstance(value, bool) else None


def _tool_card(said, card_id: str):
    """The card the tool returned for this id, or None."""
    if not isinstance(said, dict):
        return None
    body = said.get("result") if isinstance(said.get("result"), dict) else said
    for card in body.get("cards") or []:
        if isinstance(card, dict) and card.get("id") == card_id:
            return card
    return None


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="mcp")
def test_a_card_is_tradeable_on_every_surface_or_on_none(mcp_trusted, rest_trusted):
    """tradeable_now on REST against get_event_card_info, for cards read closed."""
    listing = rest_trusted.get(LIST, params={"limit": 200})
    if listing.status_code != 200:
        raise Inconclusive(f"{LIST} answered HTTP {listing.status_code}; a failed "
                           f"read is not a board with nothing closed on it")
    body = listing.json() or {}
    rows = body.get("cards") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise Inconclusive(f"{LIST} carries no `cards` list to read")
    closed = [r.get("id") for r in rows
              if isinstance(r, dict) and r.get("id") and r.get("tradeable_now") is False]
    # A few the listing marks open as well: a disagreement is one in either
    # direction, and a card the tool reads closed while REST trades it is the
    # same defect the other way round.
    opened = [r.get("id") for r in rows
              if isinstance(r, dict) and r.get("id") and r.get("tradeable_now") is True]
    subjects = closed[:SAMPLE] + opened[:OPEN_SAMPLE]
    if not closed:
        raise Inconclusive(
            f"the listing marks no card closed (us_market_open "
            f"{body.get('us_market_open')!r}), so no surface could disagree "
            f"about one; the closed case was not exercised")

    pairs, unread = [], []
    for card_id in subjects:
        at = _now()
        one = rest_trusted.get(CARD.format(id=card_id))
        rest = _bool((one.json() or {}).get("tradeable_now")) if one.status_code == 200 else None
        reason = (one.json() or {}).get("trading_blocked_reason") if one.status_code == 200 else None
        try:
            answered = mcp_trusted.call(TOOL, {"query": card_id})
            # Both read times, as the docstring promises (A06, deep pass of
            # 2026-09-24): a pair can straddle a market open or close, and one
            # time taken before the first read could not show it.
            tool_at = _now()
            tool = _bool((_tool_card(answered, card_id) or {}).get("tradeable_now"))
        except McpError as exc:
            unread.append(f"{card_id[:8]}: {TOOL} answered {str(exc)[:80]}")
            continue
        if rest is None or tool is None:
            unread.append(f"{card_id[:8]}: REST {rest!r}, {TOOL} {tool!r}")
            continue
        pairs.append({"card": card_id, "rest": rest, "tool": tool, "at": at,
                      "tool_at": tool_at, "reason": reason})

    differ = [p for p in pairs if p["rest"] != p["tool"]]
    closed_both = [p for p in pairs if p["rest"] is False and p["tool"] is False]
    population = {"sampled": len(subjects), "read_on_both": len(pairs),
                  "disagree": len(differ), "closed_on_both": len(closed_both),
                  "us_market_open": body.get("us_market_open"),
                  "pairs": pairs[:SAMPLE], "unread": unread}
    sources = {"contract": "GET /api/v1/event-cards/{id} tradeability.tradeable_now: "
                           "'the only trade gate'",
               "rest": CARD, "mcp": f"tools/call {TOOL}"}
    if differ:
        first = differ[0]
        conclude(Measurement(
            verdict="failed",
            reason=(f"{len(differ)} of {len(pairs)} card(s) read on both surfaces "
                    f"disagree on tradeable_now: card {first['card']} reads "
                    f"{first['rest']} on {CARD} ({first['reason']!r}) and "
                    f"{first['tool']} through {TOOL} (REST read at "
                    f"{first['at']}, tool read at {first['tool_at']}) "
                    f"(listing us_market_open {body.get('us_market_open')!r}); "
                    f"an agent or Nexus reading the tool is told a card can be "
                    f"traded that the trade gate refuses"),
            left=[(p["card"][:8], p["rest"], p["tool"]) for p in differ],
            right="the same tradeable_now on both surfaces",
            population=population, sources=sources))
        return
    if not closed_both:
        raise Inconclusive(
            f"{len(pairs)} card(s) read on both surfaces and none is closed on "
            f"both" + (f"; unread: {'; '.join(unread[:3])}" if unread else "")
            + " -- the closed case was not exercised")
    conclude(Measurement(
        verdict="passed",
        reason=(f"{len(closed_both)} card(s) read closed on both {CARD} and "
                f"{TOOL}, and none of the {len(pairs)} read on both disagrees"),
        left=len(differ), right=0, population=population, sources=sources))
