"""A `hot` signal on a pool nobody can buy is the thing they said they fixed.

THE CONTRACT IS THEIRS, AND IT IS RECENT. On 2026-09-14, answering our
measurement of 899 of their signals, Cymetica wrote on Telegram (recorded as
a REPLY by `scripts/correspond.py`):

    "The floor shipped: a row is only HOT now if it's also TRADEABLE -- its
    5%-slippage max buy (max_buy_5pct_usd) is at least $500. A burst on a thin
    curve is no longer hot; an unreadable reserve fails closed to not-hot (we
    never assume a curve we couldn't read is deep enough). The raw burst is
    still on the row as hot_pressure."

Unqualified, and the conversation it answers covered both chains they serve.

WHAT WE MEASURED, 2026-09-14 08:00 UTC. Their Robinhood rows carry the whole
mechanism -- `max_buy_5pct_usd`, `hot_pressure` and `thin` on 59 of 59 rows --
and honour it: the thinnest hot row allowed $1 447 of max buy, none was
`thin`, and two rows that failed the bar were serving `hot: false` beside
`hot_pressure: true`, exactly as described. Their Solana rows carry none of
the three fields, and two of twenty hot Solana tokens quoted pools of
**$75.16** (CHADSTER) and **$423.77** ($speed), both about 140 seconds old.

WHY $10 000 OF POOL IS THEIR $500. Not assumed: over every Robinhood row that
serves both numbers, `max_buy_5pct_usd / liquidity_usd` was 0.0500 to four
decimal places -- minimum, median and maximum alike. The ratio is read off
their own rows on every run rather than baked in here, so a change in how they
compute it changes the comparison instead of silently invalidating it.

WHAT THIS CHECK ASSERTS, AND IN WHICH DIRECTION. Every claim is that something
IS served: that both chains answered, that Robinhood serves the gate field,
that Robinhood's hot rows all clear it, and that a counted number of Solana
rows are served `hot: true` beside a liquidity their own Robinhood gate would
have refused many times over. It never asserts a field is absent from a
schema -- a chain that simply does not serve `liquidity_usd` is inconclusive,
not a finding.

HOW OFTEN, NOT WHETHER. One thin row is a screenshot. Sampled every thirty
seconds for ten minutes on 2026-09-14: **five distinct Solana tokens** under
their floor, against **zero** of 134 hot Robinhood rows; the thinnest,
`tothemoon`, held a $344.81 pool -- $17.24 of max buy -- and stayed hot across
seven consecutive reads. Every one of the five was 83 to 181 seconds old and
served `max_buy_5pct_usd`, `hot_pressure` and `thin` as null.

Their gated chain is what carries the caution. A pool draining between their
gate and the response would happen on Robinhood too, and over those same ten
minutes it never did, so `BREACH_FRACTION` is serialisation noise rather than
a guess. And one row is still not a finding: `MIN_BREACHES` distinct tokens
must breach in a single read.

SAFE. Keyless GETs on the endpoint the tool publishes.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SIGNALS = "/api/v1/clones/fomo-radar/signals"

# Their floor, in their own unit, from their own message.
FLOOR_MAX_BUY_USD = 500.0

# How far below the floor a row must sit before it counts. Set at a twentieth
# of the floor when this check was written -- out of caution about a pool
# draining between their gate and the response -- and that was measuring a
# strawman: over ten minutes and 320 hot solana rows, five distinct tokens sat
# under their $500 and only ONE of them was under $25, so the check passed
# while the gap it exists for was in front of it.
#
# What answers the caution is not a margin, it is their own gated chain. If a
# pool could drain between gate and serialisation it would do it on Robinhood
# too, and over the same ten minutes NONE of 134 hot Robinhood rows was under
# the floor. So the margin is now only serialisation noise.
BREACH_FRACTION = 0.9

# One thin row mid-index is ordinary in a new-pair feed. Two distinct tokens
# in one read is a gate that is not running.
MIN_BREACHES = 2


def max_buy(row: dict, ratio: float) -> float | None:
    """What their gate would have measured on this row.

    Preferring their own field wherever they serve it, and falling back to
    the pool times the ratio THEY publish elsewhere in the same response
    format. Returns None when neither is readable -- which is not a breach,
    because a row we cannot measure is not a row we have caught.
    """
    served = row.get("max_buy_5pct_usd")
    if isinstance(served, (int, float)):
        return float(served)
    pool = row.get("liquidity_usd")
    if isinstance(pool, (int, float)) and ratio:
        return float(pool) * ratio
    return None


def published_ratio(rows: list[dict]) -> float | None:
    """`max_buy_5pct_usd / liquidity_usd` as their own rows report it.

    The median over every row serving both, so one odd row cannot move it.
    None when no row serves both, and the caller then has nothing to hold the
    other chain against -- inconclusive, not a finding.
    """
    seen = []
    for row in rows:
        buy, pool = row.get("max_buy_5pct_usd"), row.get("liquidity_usd")
        if (isinstance(buy, (int, float)) and isinstance(pool, (int, float))
                and pool > 0):
            seen.append(buy / pool)
    if not seen:
        return None
    seen.sort()
    return seen[len(seen) // 2]


def breaches(rows: list[dict], ratio: float) -> list[dict]:
    """Distinct hot tokens sitting far below their own floor."""
    out, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("hot"):
            continue
        token = str(row.get("token_address") or "").lower()
        if not token or token in seen:
            continue
        measured = max_buy(row, ratio)
        if measured is None or measured >= FLOOR_MAX_BUY_USD * BREACH_FRACTION:
            continue
        seen.add(token)
        out.append(row)
    return out


def decide(solana: dict, robinhood: dict) -> tuple[str, str]:
    """The verdict, as a function of the two chains, testable without a socket.

    Their own gated chain is the control. If Robinhood does not serve the
    gate, or serves no hot row at all, there is nothing here to hold Solana
    against and the answer is inconclusive rather than a finding -- the gate
    may be mid-deploy, and rule 10 says an empty measurement is not a defect.
    """
    if not solana["hot"] and not robinhood["hot"]:
        return ("inconclusive",
                "neither chain returned a hot row, so there is no signal here "
                "to be thin -- a quiet market, not an ungated one")
    if robinhood["ratio"] is None:
        return ("inconclusive",
                "no row on either chain serves max_buy_5pct_usd beside "
                "liquidity_usd, so their own floor cannot be measured in the "
                "unit they stated it in")
    if not robinhood["hot"]:
        return ("inconclusive",
                f"their gated chain returned no hot row this read, so the "
                f"{len(solana['breaches'])} thin solana row(s) have no "
                f"control to be compared against")

    thin_here = len(solana["breaches"])
    thin_control = len(robinhood["breaches"])
    if thin_control >= MIN_BREACHES:
        return ("failed",
                f"the floor is not running on either chain: {thin_control} "
                f"robinhood and {thin_here} solana token(s) are served "
                f"hot: true with a 5%-slippage max buy under "
                f"${FLOOR_MAX_BUY_USD * BREACH_FRACTION:,.0f}, against the "
                f"${FLOOR_MAX_BUY_USD:,.0f} floor they stated on 2026-09-14")
    if thin_here < MIN_BREACHES:
        return ("passed",
                f"every hot row on both chains clears the floor: "
                f"{robinhood['hot']} robinhood and {solana['hot']} solana hot "
                f"rows, the thinnest allowing "
                f"${min(solana['thinnest'], robinhood['thinnest']):,.0f} of "
                f"max buy against a ${FLOOR_MAX_BUY_USD:,.0f} floor")

    worst = min(solana["breaches"],
                key=lambda r: max_buy(r, robinhood["ratio"]) or 0.0)
    return ("failed",
            f"{thin_here} of {solana['hot']} hot solana tokens are served "
            f"hot: true on a pool their own robinhood gate would refuse: the "
            f"thinnest is {worst.get('symbol') or '?'} at "
            f"${worst.get('liquidity_usd', 0):,.2f} of liquidity, about "
            f"${max_buy(worst, robinhood['ratio']) or 0:,.2f} of 5%-slippage "
            f"max buy against the ${FLOOR_MAX_BUY_USD:,.0f} floor. On the same "
            f"endpoint in the same read, {robinhood['hot']} robinhood hot rows "
            f"carry max_buy_5pct_usd and all clear it, so the gate exists and "
            f"is not applied to this chain")


def _rows(client, chain: str) -> list[dict]:
    response = client.get(f"{SIGNALS}?chain={chain}&filter=hot&limit=40")
    if response.status_code != 200:
        raise Inconclusive(
            f"{SIGNALS} (chain={chain}) answered HTTP "
            f"{response.status_code}; a failed read is not an ungated feed")
    try:
        return list((response.json() or {}).get("rows") or [])
    except ValueError as exc:
        raise Inconclusive(f"{SIGNALS} (chain={chain}) is not JSON: {exc}")


def _chain(rows: list[dict], ratio: float | None) -> dict:
    hot = [r for r in rows if isinstance(r, dict) and r.get("hot")]
    measured = [m for m in (max_buy(r, ratio or 0.0) for r in hot)
                if m is not None]
    return {"rows": len(rows), "hot": len(hot), "ratio": ratio,
            "breaches": breaches(rows, ratio or 0.0),
            "thinnest": min(measured) if measured else float("inf")}


@qa(component="rest.clones", tier=SafetyTier.SAFE, surface="rest")
def test_a_hot_signal_clears_the_tradeability_floor_they_shipped(rest_anon):
    """Their floor, held against the two chains their one endpoint serves.

    Solana thin while Robinhood is gated is the finding; both thin is the
    floor not running at all, which is also a finding but a different
    sentence; neither thin is a pass.
    """
    robinhood_rows = _rows(rest_anon, "robinhood")
    solana_rows = _rows(rest_anon, "solana")

    # Read off the gated chain, on every run. Their $500 is stated in max-buy
    # and Solana serves only a pool, so the conversion has to come from their
    # own rows rather than from arithmetic we believe about AMMs.
    ratio = published_ratio(robinhood_rows + solana_rows)
    robinhood = _chain(robinhood_rows, ratio)
    solana = _chain(solana_rows, ratio)

    verdict, reason = decide(solana, robinhood)
    if verdict == "inconclusive":
        raise Inconclusive(reason)

    conclude(Measurement(
        verdict=verdict,
        reason=reason,
        left=[{"chain": "solana", "symbol": r.get("symbol"),
               "token_address": r.get("token_address"),
               "liquidity_usd": r.get("liquidity_usd"),
               "conviction": r.get("conviction"),
               "token_age_seconds": r.get("token_age_seconds"),
               "max_buy_5pct_usd": max_buy(r, ratio or 0.0)}
              for r in solana["breaches"]],
        right=[{"chain": "robinhood", "hot_rows": robinhood["hot"],
                "thinnest_max_buy_usd": (
                    None if robinhood["thinnest"] == float("inf")
                    else robinhood["thinnest"]),
                "serves_gate_fields": robinhood["ratio"] is not None}],
        population={
            "floor_max_buy_usd": FLOOR_MAX_BUY_USD,
            "breach_fraction": BREACH_FRACTION,
            "min_breaches": MIN_BREACHES,
            "published_ratio": ratio,
            "solana_rows": solana["rows"], "solana_hot": solana["hot"],
            "solana_breaches": len(solana["breaches"]),
            "robinhood_rows": robinhood["rows"],
            "robinhood_hot": robinhood["hot"],
            "robinhood_breaches": len(robinhood["breaches"]),
        },
        sources={"signals": SIGNALS},
    ))
