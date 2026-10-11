"""A coin's dashboard publishes supply figures that can all be true at once.

The Crypto dashboards (cymetica.com/crypto/{slug}, `GET /api/v1/crypto/{slug}`, MCP
`crypto_dashboard`) were new on 2026-10-11. Their own tool description makes the promise:
"Every number carries its source and time; a number that failed a plausibility check is
withheld, never guessed." The mechanism exists and fires: 10 of 371 coins carry
`stats.flags: ["circulating_supply"]` with `circulating_supply` null, every one of them a
coin whose circulating supply (the dashboard derives it as market cap / price,
`circulating_is_derived: true`) is above its own maximum, or above its total when no maximum
is published.

**What was seen when this was written** (2026-10-11, 02:30-03:00 UTC, all 371 dashboards read,
HBAR read twice as JSON and once as text): HBAR (market-cap rank 38) publishes `max_supply` 1,000,000,000 and
`total_supply` 50,000,000,000 (CoinPaprika's own ticker says the same two figures, with no
circulating supply), derives `circulating_supply` 43,997,753,874, and so prints "circulating
supply 44.00B of 1.00B", `fdv` $92.3M beside a `market_cap` of $4.06B, and `pct_issued` 1.0,
with `flags: []`. IOTA (rank 179, 4.31B circulating against a 2.78B maximum, FDV $142.7M
under a $221.4M market cap) and ICP (rank 58, 557M against 469M, FDV $1.45B under $1.73B) are
the same shape, unflagged. CHZ, with the same relation as ICP (total above max, circulating
1.19x the max), IS withheld. So the rule that withholds one is not applied to the other.

**The rule.** For a coin whose circulating supply is not flagged as withheld, the published
figures must be possible together: the circulating supply is not above the maximum supply, the
total supply is not above the maximum supply (both by more than 1%, a tolerance for the two
sources being read a minute apart), and the fully diluted value is not below the market cap
(by more than 5%: ETH is 1.5% under, its total being net of burns, and is not judged).
FDV = price x supply that includes everything already out, so below the market cap it cannot be.

**Sampling, stated.** The 140 largest coins of the manifest by market cap, not all 371: every
read is paced, and a sweep that runs long drifts on the fingerprint. The three coins above sit
at positions 14 (HBAR), 24 (ICP) and 74 (IOTA). A coin that breaks a relation is read once more
after a pause, and only a coin that breaks it both times is counted (a rotating source is
sampling, `a-check-on-a-rotating-population-is-sampling`).

SAFE. GETs only, anonymous.
"""

from __future__ import annotations

import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

MANIFEST = "/api/v1/crypto"
COIN = "/api/v1/crypto/{slug}"
SAMPLE = 140
PAUSE_S = 0.8
SECOND_LOOK_S = 20.0
SUPPLY_TOLERANCE = 1.01      # one source read a minute apart from another
FDV_TOLERANCE = 0.95         # ETH is 0.985 (total net of burns) and is not a defect


def supply_contradiction(stats: dict | None) -> dict | None:
    """The relations among a coin's published supply figures that cannot all be true.

    None when the figures can be: a circulating supply the dashboard withheld (flagged), a
    figure missing, or every relation within its tolerance. Otherwise a dict naming each broken
    relation with its factor, so the verdict can say by how much."""
    if not isinstance(stats, dict):
        return None
    flags = stats.get("flags") or []
    if flags:
        # Withheld, or flagged for something this check does not read: not judged.
        return None
    circ, total, top = (stats.get(k) for k in ("circulating_supply", "total_supply", "max_supply"))
    mc, fdv = stats.get("market_cap"), stats.get("fdv")
    broken: dict = {}
    nums = lambda *xs: all(isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0 for x in xs)
    if nums(circ, top) and circ > top * SUPPLY_TOLERANCE:
        broken["circulating_over_max"] = round(circ / top, 3)
    if nums(total, top) and total > top * SUPPLY_TOLERANCE:
        broken["total_over_max"] = round(total / top, 3)
    if nums(mc, fdv) and fdv < mc * FDV_TOLERANCE:
        broken["fdv_under_market_cap"] = round(fdv / mc, 3)
    return broken or None


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0


def judgeable(stats) -> bool:
    """Whether a dashboard's stats can be judged at all: unflagged, with both figures of at least
    one relation. A 200 without them is not a coin judged (deep pass 2026-10-11, B03: a renamed
    `stats` passed 'all 140 can be true' with nothing compared)."""
    if not isinstance(stats, dict) or stats.get("flags"):
        return False
    get = stats.get
    return (_num(get("circulating_supply")) and _num(get("max_supply"))) or (
        _num(get("total_supply")) and _num(get("max_supply"))) or (
        _num(get("market_cap")) and _num(get("fdv")))


def second_look(stats) -> str:
    """The second read of a coin the first found impossible: `confirmed`, `cleared` (judged and
    possible), or `unread` -- a failed read leaves the first look standing, never clears it (rule 8)."""
    if not judgeable(stats):
        return "unread"
    return "confirmed" if supply_contradiction(stats) else "cleared"


def _compact(n) -> str:
    if not isinstance(n, (int, float)):
        return str(n)
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= size:
            return f"{n / size:.2f}{unit}"
    return f"{n:.4g}"


@qa(component="rest.markets", tier=SafetyTier.SAFE, surface="rest")
def test_a_coins_supply_figures_can_all_be_true(rest_anon):
    """Circulating, total and max supply, FDV and market cap of one dashboard are not impossible."""
    response = rest_anon.get(MANIFEST)
    if response.status_code != 200:
        raise Inconclusive(f"the coin manifest answered HTTP {response.status_code}")
    coins = [c for c in (response.json() or {}).get("coins") or []
             if isinstance(c, dict) and c.get("slug") and isinstance(c.get("mc"), (int, float))]
    if len(coins) < SAMPLE:
        raise Inconclusive(f"the manifest lists only {len(coins)} coins with a market cap")
    coins.sort(key=lambda c: -c["mc"])
    tried = [c["slug"] for c in coins[:SAMPLE]]

    first_look, judged, unread = {}, 0, []
    for slug in tried:
        time.sleep(PAUSE_S)
        r = rest_anon.get(COIN.format(slug=slug))
        if r.status_code != 200:
            unread.append(f"{slug}: HTTP {r.status_code}")
            continue
        stats = (r.json() or {}).get("stats")
        if not judgeable(stats):
            if not (isinstance(stats, dict) and stats.get("flags")):
                unread.append(f"{slug}: no supply figures to compare")
            continue
        judged += 1
        broken = supply_contradiction(stats)
        if broken:
            first_look[slug] = broken
    if judged < SAMPLE // 2:
        raise Inconclusive(f"only {judged} of {SAMPLE} dashboards could be read: {unread[:5]}")

    confirmed, unsettled = {}, []
    if first_look:
        time.sleep(SECOND_LOOK_S)
    for slug, first in first_look.items():
        time.sleep(PAUSE_S)
        r = rest_anon.get(COIN.format(slug=slug))
        body = r.json() if r.status_code == 200 else None
        stats = (body or {}).get("stats") if isinstance(body, dict) else None
        seen = second_look(stats)
        if seen == "unread":
            unsettled.append(f"{slug}: HTTP {r.status_code}")
            continue
        if seen == "cleared":
            continue
        again = supply_contradiction(stats)
        confirmed[slug] = {
            "broken": again, "first_look": first,
            "price": stats.get("price"), "market_cap": stats.get("market_cap"), "fdv": stats.get("fdv"),
            "circulating_supply": stats.get("circulating_supply"),
            "circulating_is_derived": stats.get("circulating_is_derived"),
            "total_supply": stats.get("total_supply"), "max_supply": stats.get("max_supply"),
            "pct_issued": stats.get("pct_issued"), "market_cap_rank": stats.get("market_cap_rank"),
            "source_updated": stats.get("source_updated"), "summary": (body or {}).get("summary"),
        }

    def line(slug: str, row: dict) -> str:
        parts = []
        if "circulating_over_max" in row["broken"]:
            parts.append(f"circulating {_compact(row['circulating_supply'])} against a max of "
                         f"{_compact(row['max_supply'])} ({row['broken']['circulating_over_max']}x)")
        if "total_over_max" in row["broken"]:
            parts.append(f"total {_compact(row['total_supply'])} against a max of "
                         f"{_compact(row['max_supply'])} ({row['broken']['total_over_max']}x)")
        if "fdv_under_market_cap" in row["broken"]:
            parts.append(f"FDV {_compact(row['fdv'])} under a market cap of {_compact(row['market_cap'])} "
                         f"({row['broken']['fdv_under_market_cap']}x)")
        return f"{slug.upper()} (rank {row['market_cap_rank']}, source updated {row['source_updated']}): " + ", ".join(parts)

    if unsettled and not confirmed:
        raise Inconclusive(f"{len(unsettled)} coin(s) the first look found impossible could not be read "
                           f"again: {unsettled[:5]}; neither confirmed nor cleared")
    conclude(Measurement(
        verdict="failed" if confirmed else "passed",
        reason=(f"{len(confirmed)} of {judged} dashboards (the {SAMPLE} largest coins by market cap) publish "
                f"supply figures that cannot all be true, with flags empty on both reads: "
                + "; ".join(line(s, r) for s, r in confirmed.items())
                if confirmed else
                f"the supply figures of all {judged} dashboards read can be true together"),
        left={"dashboards_with_impossible_figures": sorted(confirmed)},
        right={"dashboards_with_impossible_figures": []},
        population={"manifest": len(coins), "tried": tried, "judged": judged, "unread": unread,
                    "first_look": first_look, "confirmed": confirmed},
        sources={"manifest": MANIFEST, "coin": COIN,
                 "contract": "MCP crypto_dashboard: 'a number that failed a plausibility check is "
                             "withheld, never guessed'"}))
