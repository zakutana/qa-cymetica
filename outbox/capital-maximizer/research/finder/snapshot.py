"""One minute's reading of everything the finder scores against. GET only, no key, nothing sent.

    python -I outbox/capital-maximizer/research/finder/snapshot.py <data-dir>

The data folder stays outside git (it holds megabytes that are stale in an hour). What it writes:
llama_pools.json, llama_lendborrow.json, morpho_markets.json, morpho_vaults_v2.json, morpho_vaults_v1.json,
aave.json, pendle.json, cm_tiers.json, cm_platforms.json, cm_top3_<tier>.json, taken_at.txt.
A source that fails is said out loud in sources.json and never written as empty: a failed read is not an empty one.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
CM = "https://cymetica.com/api/v1/capital-maximizer"
MORPHO = "https://blue-api.morpho.org/graphql?query="
AAVE = "https://api.v3.aave.com/graphql?query="
PENDLE_CHAINS = {1: "Ethereum", 42161: "Arbitrum", 8453: "Base", 10: "OP Mainnet", 999: "HyperEVM", 143: "Monad", 9745: "Plasma", 146: "Sonic"}
AAVE_CHAINS = [1, 42161, 8453, 10, 137, 43114, 59144, 146, 143, 9745, 196]
TIERS = ("conservative", "medium", "high", "og")
sources: dict[str, str] = {}


def fetch(url: str, **headers):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8", "Accept": "application/json", **headers})
    return json.load(urllib.request.urlopen(req, timeout=120))


def save(name: str, body) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")
    sources[name] = f"ok, {len(body) if hasattr(body, '__len__') else '?'} items"


def attempt(name: str, read) -> None:
    try:
        save(name, read())
    except Exception as exc:  # noqa: BLE001 a source that fails is reported, the others still count
        sources[name] = f"FAILED: {exc!r}"


def gql(base: str, query: str):
    body = fetch(base + urllib.parse.quote(query), **{"apollo-require-preflight": "true"})
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"])[:400])
    return body["data"]


def paged(field: str, fields: str, page: int = 500) -> list:
    rows, skip = [], 0
    while True:
        got = gql(MORPHO, '{%s(first:%d,skip:%d){items{%s}}}' % (field, page, skip, fields))[field]["items"]
        rows += got
        if len(got) < page:
            return rows
        skip += page


MARKET = ("marketId lltv listed morphoBlue{chain{id network}} loanAsset{symbol address} collateralAsset{symbol address} "
          "state{supplyAssetsUsd borrowAssetsUsd liquidityAssetsUsd borrowApy weeklyBorrowApy monthlyBorrowApy utilization}")
VAULT_V2 = ("address symbol name listed chain{id network} totalAssetsUsd liquidityUsd avgNetApy netApy curators{items{name}} "
            "gatesConfig{sendAssetsGate{address abdicated} receiveSharesGate{address abdicated}}")
VAULT_V2_BOOK = ('{vaultV2ByAddress(address:"%s",chainId:%d){adapters{items{type assetsUsd ... on MorphoMarketV1Adapter'
                 '{positions{items{state{supplyAssetsUsd} market{collateralAsset{symbol}}}}}}}}}')
VAULT_V1 =("address symbol name listed chain{id network} state{totalAssetsUsd netApy curators{name} "
            "allocation{supplyAssetsUsd market{collateralAsset{symbol}}}}")
AAVE_Q = ('{markets(request:{chainIds:%s}){name chain{chainId name} reserves{underlyingToken{symbol address} isFrozen isPaused '
          'supplyInfo{maxLTV{value} liquidationThreshold{value} canBeCollateral} '
          'borrowInfo{apy{value} availableLiquidity{usd} borrowingState} '
          'eModeInfo{categoryId label maxLTV{value} liquidationThreshold{value} canBeCollateral canBeBorrowed}}}}') % json.dumps(AAVE_CHAINS)

(OUT / "taken_at.txt").write_text(dt.datetime.now(dt.timezone.utc).isoformat(), encoding="utf-8")
attempt("llama_pools", lambda: fetch("https://yields.llama.fi/pools")["data"])
attempt("llama_lendborrow", lambda: fetch("https://yields.llama.fi/lendBorrow"))
attempt("cm_tiers", lambda: fetch(CM + "/tiers?amount=5000"))
attempt("cm_platforms", lambda: fetch(CM + "/platforms"))
for tier in TIERS:
    attempt(f"cm_top3_{tier}", lambda tier=tier: fetch(CM + f"/top3?tier={tier}&amount=5000"))
attempt("morpho_markets", lambda: paged("markets", MARKET))


def vaults_v2() -> list:
    rows = paged("vaultV2s", VAULT_V2, 200)
    for v in rows:
        if (v.get("totalAssetsUsd") or 0) >= 1e6:  # what a vault lends against: only for the ones big enough to route
            try:
                v["book"] = gql(MORPHO, VAULT_V2_BOOK % (v["address"], v["chain"]["id"]))["vaultV2ByAddress"]["adapters"]["items"]
            except Exception as exc:  # noqa: BLE001
                v["book_error"] = repr(exc)
    return rows


def aave() -> list:
    # Aave's API answers queries by POST only. This is a read: it sends the query text and nothing else.
    req = urllib.request.Request(AAVE.split("?")[0], data=json.dumps({"query": AAVE_Q}).encode(),
                                 headers={"User-Agent": "curl/8", "Content-Type": "application/json"})
    body = json.load(urllib.request.urlopen(req, timeout=120))
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"])[:500])
    return body["data"]["markets"]


def fluid() -> list:
    rows = []
    for cid in (1, 42161, 8453, 137, 9745):
        for kind, path in (("vault", "vaults"), ("lending", "lending")):
            try:
                got = fetch(f"https://api.fluid.instadapp.io/v2/{cid}/{path}")
                got = got.get("data", got) if isinstance(got, dict) else got
                rows += [{**r, "chainId": cid, "fluid_kind": kind} for r in got]
            except Exception as exc:  # noqa: BLE001
                sources[f"fluid_{cid}_{kind}"] = f"FAILED: {exc!r}"
    return rows


attempt("morpho_vaults_v2", vaults_v2)
attempt("morpho_vaults_v1", lambda: paged("vaults", VAULT_V1, 300))
attempt("aave", aave)
attempt("fluid", fluid)


def pendle() -> list:
    rows = []
    for cid, chain in PENDLE_CHAINS.items():
        try:
            for m in fetch(f"https://api-v2.pendle.finance/core/v1/{cid}/markets/active")["markets"]:
                rows.append({**m, "chain": chain, "chainId": cid})
        except Exception as exc:  # noqa: BLE001
            sources[f"pendle_{chain}"] = f"FAILED: {exc!r}"
    return rows


attempt("pendle", pendle)
(OUT / "sources.json").write_text(json.dumps(sources, indent=1), encoding="utf-8")
print(json.dumps(sources, indent=1))
