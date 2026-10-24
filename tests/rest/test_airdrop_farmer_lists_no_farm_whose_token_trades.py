"""Airdrop Farmer: no farm in a list gated "No token live yet" has a token that already trades (2026-10-24).

GET /api/v1/airdrop-farm/farms answered on 2026-10-24 with 49 farms under a gate whose first line is
"No token live yet", and the page says "Every farm here passed the automatic checks". Six of them had a
token priced and traded that day: Fables (FABLES on Robinhood Chain, DexScreener pair since 2026-10-20),
Zircuit Staking (ZRC), and the Galxe task farms Travala.com (AVA, trading since 2018), Sonic SVM (SONIC),
INFINIT (IN) and Rivalz Network (RIZ), all on CoinGecko. A farm whose token is out is not an airdrop farm:
the airdrop has happened, and an agent farming it for a user farms nothing.

The cause, read in each row's `evidence`: the chips and the gate are fed by headlines matched on the name
(Axis is TOKEN CONFIRMED from "Axis Robotics price today", Ink from a TV singer called INK, Tempo is
POINTS LIVE from the WNBA's Toronto Tempo, Fables from "Royal Fables Season 16"). That is recorded in the
report, not judged here: this check holds them to the gate line only.

**The rule.** While the gate promises "No token live yet", none of the PINNED farms may be in the list
while its own token has traded at least MIN_VOLUME_USD in the last 24 hours. A farm is found by its id,
its name, or its own page, so a renamed or re-keyed row is still found.

VERDICTS. failed: a pinned farm is listed and its token traded. passed: every pinned farm whose token
trades is gone from the list (or its token stopped trading). inconclusive: the list could not be read or
is empty; the gate no longer promises tokenless farms; a listed pinned farm's market could not be read.

NOT asserted: farms outside PINNED (the rest of their list was not priced token by token); whether the
farms left are worth farming; the chips' wording.
SAFE: one anonymous GET of the farms list; anonymous reads of CoinGecko markets and one DexScreener pair.
"""

from __future__ import annotations

import re

import httpx

from qa import gemaudit as g
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

FARMS = "/api/v1/airdrop-farm/farms"
PAGE = "https://cymetica.com/airdrop-farmer"
MIN_VOLUME_USD = 5_000.0

# Each farm whose token was trading on 2026-10-24: the ids, names and page fragments it is found by,
# and where its token's market is read.
PINNED = [
    {"key": "fables", "token": "FABLES", "ids": {"fables"}, "names": {"fables"}, "pages": ["fables.fi"],
     "market": ("dexscreener", "robinhood", "0xcce8dcf7c4dcfee6b6588db724240d9d6a22ee456f9387bb831c8fcea970869e")},
    {"key": "zircuit", "token": "ZRC", "ids": {"zircuit-staking"}, "names": {"zircuit", "zircuitstaking"},
     "pages": ["zircuit.com"], "market": ("coingecko", "zircuit")},
    {"key": "travala", "token": "AVA", "ids": {"task-travala"}, "names": {"travala", "travalacom"},
     "pages": ["quest/travala", "travala.com"], "market": ("coingecko", "concierge-io")},
    {"key": "sonic-svm", "token": "SONIC", "ids": {"task-sonicsvm"}, "names": {"sonicsvm"},
     "pages": ["quest/sonicsvm", "sonic.game"], "market": ("coingecko", "sonic-svm")},
    {"key": "infinit", "token": "IN", "ids": {"task-infinit"}, "names": {"infinit"},
     "pages": ["quest/infinit", "infinit.tech"], "market": ("coingecko", "infinit")},
    {"key": "rivalz", "token": "RIZ", "ids": {"task-rivalznetwork"}, "names": {"rivalz", "rivalznetwork"},
     "pages": ["quest/rivalznetwork", "rivalz.ai"], "market": ("coingecko", "rivalz-network")},
]


def _norm(name) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def _matches(pin: dict, farm: dict) -> bool:
    if str(farm.get("id") or "") in pin["ids"] or _norm(farm.get("name")) in pin["names"]:
        return True
    url = str(farm.get("url") or "").lower()
    return bool(url) and any(re.search(re.escape(p) + r"(?![a-z0-9])", url) for p in pin["pages"])


def listed(farms: list[dict]) -> list[tuple[dict, dict]]:
    """(pin, farm) for every pinned farm found in the list."""
    out = []
    for pin in PINNED:
        farm = next((f for f in farms if isinstance(f, dict) and _matches(pin, f)), None)
        if farm is not None:
            out.append((pin, farm))
    return out


def judge(farms: list[dict], gate: list, markets: dict) -> dict:
    """`markets` is {pin key: 24h volume in USD} for each market read; a key missing means not read."""
    if not farms:
        return {"verdict": "inconclusive", "why": "the farms list was empty", "offenders": [], "unread": []}
    if not any("no token" in str(line).lower() for line in gate or []):
        return {"verdict": "inconclusive", "offenders": [], "unread": [],
                "why": f"the gate no longer promises tokenless farms: {gate!r}"}
    found = listed(farms)
    offenders, unread = [], []
    for pin, farm in found:
        volume = markets.get(pin["key"])
        row = {"key": pin["key"], "token": pin["token"], "farm": farm.get("name"), "id": farm.get("id"),
               "volume_24h_usd": volume}
        if volume is None:
            unread.append(row)
        elif volume >= MIN_VOLUME_USD:
            offenders.append(row)
    if offenders:
        names = ", ".join(f"{o['farm']} ({o['token']}, ${o['volume_24h_usd']:,.0f} traded in 24 h)" for o in offenders)
        return {"verdict": "failed", "offenders": offenders, "unread": unread,
                "why": f"{len(offenders)} farm(s) listed under 'No token live yet' have a token that trades: {names}"}
    if unread:
        return {"verdict": "inconclusive", "offenders": [], "unread": unread,
                "why": "a listed farm's market could not be read: " + ", ".join(u["farm"] for u in unread)}
    return {"verdict": "passed", "offenders": [], "unread": [],
            "why": f"none of the {len(PINNED)} farms whose token trades is listed any more"}


def read_markets(pins: list[dict], evidence_store) -> tuple[dict, list[str]]:
    """{pin key: 24h volume in USD} for the pins given, and the sources that could not be read."""
    markets: dict = {}
    failed: list[str] = []
    client = build_source_client(evidence=evidence_store)
    try:
        cg = {p["market"][1]: p["key"] for p in pins if p["market"][0] == "coingecko"}
        if cg:
            try:
                for row in g.fetch_coingecko(client.get, cg):
                    if row.get("id") in cg and isinstance(row.get("total_volume"), (int, float)):
                        markets[cg[row["id"]]] = float(row["total_volume"])
            except (g.SourceUnavailable, httpx.HTTPError) as exc:
                failed.append(f"CoinGecko: {exc}")
        dex = [p for p in pins if p["market"][0] == "dexscreener"]
        if dex:
            try:
                pairs, chains_failed = g.fetch_dexscreener(client.get, [p["market"][1:] for p in dex])
                failed += [f"DexScreener {c}" for c in chains_failed]
                for p in dex:
                    pair = pairs.get((p["market"][1], p["market"][2].lower()))
                    vol = ((pair or {}).get("volume") or {}).get("h24")
                    if isinstance(vol, (int, float)):
                        markets[p["key"]] = float(vol)
            except (g.SourceUnavailable, httpx.HTTPError) as exc:
                failed.append(f"DexScreener: {exc}")
    finally:
        client.close()
    return markets, failed


@qa(component="rest.airdrop_farmer", tier=SafetyTier.SAFE, surface="rest")
def test_airdrop_farmer_lists_no_farm_whose_token_trades(rest_anon, evidence_store):
    """No farm in the 'No token live yet' list has a token that traded in the last 24 hours."""
    try:
        r = get_patiently(rest_anon, FARMS)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{FARMS} could not be read: {type(exc).__name__}")
    if r.status_code != 200:
        raise Inconclusive(f"{FARMS} answered HTTP {r.status_code}")
    try:
        body = r.json()
    except ValueError:
        raise Inconclusive(f"{FARMS} answered 200 with a body that is not JSON")
    farms = body.get("farms") if isinstance(body, dict) else None
    if not isinstance(farms, list):
        raise Inconclusive(f"{FARMS} answered no farms list")
    gate = body.get("gate") or []

    found = listed(farms)
    markets, unread_sources = read_markets([pin for pin, _ in found], evidence_store) if found else ({}, [])
    out = judge(farms, gate, markets)
    population = {
        "farms_listed": len(farms), "generated_at": body.get("generated_at"),
        "gate_first_line": gate[0] if gate else None,
        "pinned_found": [{"key": p["key"], "id": f.get("id"), "name": f.get("name"), "url": f.get("url"),
                          "chip": f.get("chip"), "volume_24h_usd": markets.get(p["key"])} for p, f in found],
        "sources_unread": unread_sources,
    }
    if out["verdict"] == "inconclusive":
        raise Inconclusive(out["why"])
    conclude(Measurement(
        verdict=out["verdict"],
        reason=out["why"],
        left={"listed_with_token_trading": len(out["offenders"])},
        right={"listed_with_token_trading": 0},
        population=population,
        sources={"farms": FARMS, "page": PAGE,
                 "markets": "CoinGecko /coins/markets (total_volume); DexScreener pair for FABLES"}))
