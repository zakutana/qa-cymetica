"""A clone's perpetual market list names only 5-minute markets that exist (2026-10-13).

A cloned bot's settings carry `perpetual_markets`, the 5-minute epoch markets it trades, and its
profile's `trades_summary` is built from that list (ET-28100, REPLY-0151; #190 holds the summary
to the settings). llms.txt names the live 5-minute markets: "GET /api/v1/perpetual/markets/
batch-status: The live 5-minute markets (BTC, ETH, NVDA, AAPL, GOOG, VAIX, SBIO) with epoch,
price, time remaining and trading_active".

**What was seen when this was written** (2026-10-13 06:55 UTC): our tournament clone 692c35b3
("tournament Perceptron Oracle", Perceptron Oracle species, settings left at the species' market
list) reads perpetual_markets "BTC,ETH,VAIX,SBIO,ET10,ETLP,CYM42,TBIG,TBIGS" and trades_summary
"This bot trades: BTC/ETH/VAIX/SBIO +5 5-min epochs (paper)"; batch-status lists BTC, ETH, NVDA,
AAPL, GOOG, VAIX, SBIO. ET10, ETLP, CYM42, TBIG and TBIGS have no 5-minute market, so five of the
nine markets the bot is said to trade cannot be traded. Its 47 trades since 2026-10-11 are all
BTC and ETH.

**The rule.** Every symbol a paper clone's `perpetual_markets` switches on is one of the live
5-minute markets batch-status lists. Passes the moment the default list, or batch-status, agree --
whichever side is fixed.

NOT asserted: why a clone trades only some of its live markets (its strategy decides), the CLOB
list (custom_markets), or live clones.

SAFE: GETs only, anonymous for batch-status and our own clones with our key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_a_clone_summary_names_what_it_trades import _profile, switched_on

PREFIX = "/api/v1/cloned-bots"
LIVE = "/api/v1/perpetual/markets/batch-status"
CLAIM = "a-clone-trades-only-live-epoch-markets"
MAX_CLONES = 12


def live_symbols(body) -> list[str]:
    """The symbols batch-status lists, or [] when it lists none (unread, never 'no markets')."""
    rows = (body or {}).get("markets") if isinstance(body, dict) else None
    return sorted({str(m.get("symbol")).upper() for m in rows or []
                   if isinstance(m, dict) and m.get("symbol")})


def dead_markets(perpetual: list[str], live: list[str]) -> list[str]:
    """The switched-on perpetual symbols with no live 5-minute market."""
    have = set(live)
    return [s for s in perpetual if s not in have]


@qa(component="rest.clones", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_a_clones_perpetual_markets_are_live_five_minute_markets(rest_anon, rest_trusted):
    """Our paper clones' perpetual_markets against the live 5-minute markets."""
    r = rest_anon.get(LIVE)
    if r.status_code != 200:
        raise Inconclusive(f"{LIVE} answered HTTP {r.status_code}")
    live = live_symbols(r.json())
    if not live:
        raise Inconclusive(f"{LIVE} listed no market; nothing to hold a list against")
    mine = rest_trusted.get(f"{PREFIX}/my-clones", params={"mode": "paper"})
    if mine.status_code != 200 or not isinstance(mine.json(), list):
        raise Inconclusive(f"my-clones answered HTTP {mine.status_code}")
    clones = [c for c in mine.json() if isinstance(c, dict) and c.get("id")][:MAX_CLONES]
    judged, wrong, dead_all = 0, [], set()
    for clone in clones:
        profile = _profile(rest_trusted, clone["id"])
        if not profile or not isinstance(profile.get("settings"), dict):
            continue
        perp = switched_on(profile["settings"])["perpetual"]
        if not perp:
            continue
        judged += 1
        dead = dead_markets(perp, live)
        if dead:
            dead_all.update(dead)
            wrong.append({"id": clone["id"][:8], "name": profile.get("name"),
                          "perpetual_markets": profile["settings"].get("perpetual_markets"),
                          "trades_summary": profile.get("trades_summary"), "dead": dead})
    if not judged:
        raise Inconclusive("no clone of ours states a perpetual market list; nothing judged")
    ex = wrong[0] if wrong else None
    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(f"{len(wrong)} of {judged} paper clones switch on perpetual markets with no 5-minute "
                f"market: {', '.join(sorted(dead_all))}; {LIVE} lists {', '.join(live)}. E.g. {ex['id']} "
                f"perpetual_markets {ex['perpetual_markets']!r}, trades_summary {ex['trades_summary']!r}"
                if wrong else
                f"all {judged} paper clones switch on only live 5-minute markets ({', '.join(live)})"),
        left={"clones_with_dead_markets": len(wrong)},
        right={"clones_with_dead_markets": 0},
        population={"live": live, "judged": judged, "wrong": wrong[:6]},
        sources={"live": LIVE, "settings": f"{PREFIX}/{{id}}/profile settings.perpetual_markets",
                 "contract": "llms.txt: batch-status lists the live 5-minute markets"},
        claim_id=CLAIM))
