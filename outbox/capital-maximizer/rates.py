"""Read today's DeFi rates for the Capital Maximizer demo from DefiLlama and write data.js beside the page.

Only the pools a route can use, each by its DefiLlama pool id, with the time they were read; how many pools of each
allowlisted protocol the finder looked through; and each protocol's own DefiLlama record (category, TVL, audits,
chains) for the Platforms tab. GET only, no key. Refresh: python outbox/capital-maximizer/rates.py

The allowlist is ours for the demo (blue-chip, permissionless, no KYC to use, audited per DefiLlama); Cymetica makes
its own selection. Spark Savings was dropped on 2026-10-28: DefiLlama lists no audit for it.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

SRC = "https://yields.llama.fi"
LLAMA = "https://api.llama.fi"
CHAINS = ("Ethereum", "Arbitrum", "Base")
# DefiLlama project -> name shown, icon slug on icons.llamao.fi
PROTOCOLS = {
    "aave-v3": ("Aave", "aave-v3"),
    "compound-v3": ("Compound", "compound-v3"),
    "morpho-blue": ("Morpho", "morpho-blue"),
    "sky-lending": ("Sky", "sky"),
    "lido": ("Lido", "lido"),
    "ether.fi-stake": ("ether.fi", "ether.fi"),
    "rocket-pool": ("Rocket Pool", "rocket-pool"),
    "ethena-usde": ("Ethena", "ethena"),
    "uniswap-v3": ("Uniswap", "uniswap"),
    "curve-dex": ("Curve", "curve-dex"),
}
# GMX was dropped on 2026-10-28 by the platform rule below: DefiLlama's hacks list $42M taken from GMX V1 in 07/2025,
# $40M returned, so $2M lost.

# The Platforms tab: every platform the product supports, picked 2026-10-28 from DefiLlama's protocol list by one rule,
# re-checked on every refresh (a platform that stops passing stops the refresh, it is never shown quietly):
#   audited per DefiLlama; listed a year or more; at most $1M lost and not returned in the last two years (DefiLlama
#   hacks, any version of the protocol, social-engineering scams of users not counted); at least $30M on chains where
#   Circle's CCTP moves native USDC (developers.circle.com/cctp/cctp-supported-blockchains, read 2026-10-28: BNB Chain
#   has USYC only and Tron none, so the product never holds a wrapped dollar); permissionless, so no token an exchange
#   issues (Binance, Coinbase, Bybit staked ETH/SOL) and no KYC-gated pool (Liquid Collective).
# Left out by it, the large ones: Drift ($295M lost 04/2026), Kelp ($293M, 04/2026), Cetus ($223M, 05/2025), Balancer
# ($128M, 11/2025), Moonwell, Yearn, Across, NAVI, Venus (lost); Jupiter, Orca, Raydium, Hyperliquid HLP, Sanctum
# (no audit on DefiLlama); Maple (lender access not verified as open to all).
CCTP_CHAINS = ["Ethereum", "Arbitrum", "Base", "Optimism", "Polygon", "Avalanche", "Solana", "Sui", "Aptos", "Sonic",
               "Hyperliquid L1", "Linea", "Unichain", "Monad", "Plasma", "Sei", "Ink", "World Chain", "Starknet",
               "Injective", "Plume", "XDC", "Cronos", "Codex", "Stellar", "Morph", "X Layer", "Pharos", "EDGE", "Arc"]
PLATFORMS = {      # DefiLlama slug -> name shown (the finder's own venues come from PROTOCOLS)
    "sparklend": "Spark", "kamino-lend": "Kamino", "fluid-lending": "Fluid", "euler-v2": "Euler",
    "dolomite": "Dolomite", "hyperlend-pooled": "HyperLend", "suilend": "Suilend", "benqi-lending": "BENQI",
    "cap": "Cap", "liquity-v1": "Liquity", "reservoir-protocol": "Reservoir",
    "jito-liquid-staking": "Jito", "marinade-liquid-staking": "Marinade", "stakewise-v3": "StakeWise",
    "stader": "Stader", "sthype": "stHYPE", "springsui": "SpringSui", "benqi-staked-avax": "BENQI sAVAX",
    "renzo": "Renzo", "pendle-v2": "Pendle", "convex-finance": "Convex", "stake-dao-yield": "Stake DAO",
    "falcon-finance": "Falcon", "solstice": "Solstice", "aerodrome-slipstream": "Aerodrome", "quickswap-dex": "QuickSwap",
}
CEX_ISSUED = ("binance", "coinbase", "bybit", "kraken", "okx", "bitget")
MIN_PLATFORM = 30_000_000
# stablecoin homes for USDC: (project, chain, DefiLlama symbol, name shown)
VAULTS = [
    ("aave-v3", "Ethereum", "USDC", "Aave USDC"),
    ("aave-v3", "Base", "USDC", "Aave USDC"),
    ("aave-v3", "Arbitrum", "USDC", "Aave USDC"),
    ("compound-v3", "Ethereum", "USDC", "Compound USDC"),
    ("sky-lending", "Ethereum", "SUSDS", "Sky sUSDS"),
    ("morpho-blue", "Ethereum", "STEAKUSDC", "Steakhouse USDC"),
    ("morpho-blue", "Base", "GTUSDCP", "Gauntlet USDC Prime"),
    ("morpho-blue", "Base", "SPARKUSDC", "Spark USDC"),
]
# what a dollar turns into to earn: (project, chain, symbol, token it gives, asset it tracks)
STAKES = [
    ("lido", "Ethereum", "STETH", "wstETH", "ETH"),
    ("ether.fi-stake", "Ethereum", "WEETH", "weETH", "ETH"),
    ("rocket-pool", "Ethereum", "RETH", "rETH", "ETH"),
    ("ethena-usde", "Ethereum", "SUSDE", "sUSDe", "USD"),
]
# liquidity pools: (project, chain, symbol, fee tier or None, kind)
LPS = [
    ("uniswap-v3", "Ethereum", "USDC-WETH", "0.05%", "uniswap"),
    ("uniswap-v3", "Ethereum", "USDC-WETH", "0.3%", "uniswap"),
    ("uniswap-v3", "Arbitrum", "WETH-USDC", "0.05%", "uniswap"),
    ("uniswap-v3", "Base", "WETH-USDC", "0.3%", "uniswap"),
]
# collateral a loop can borrow against: DefiLlama symbol -> (token, asset, the stake whose yield it carries)
COLLATERAL = {
    "WSTETH": ("wstETH", "ETH", "STETH"),
    "WEETH": ("weETH", "ETH", "WEETH"),
    "WETH": ("ETH", "ETH", None),
    "CBBTC": ("cbBTC", "BTC", None),
    "WBTC": ("WBTC", "BTC", None),
    "SUSDE": ("sUSDe", "USD", "SUSDE"),
}
LOANS = {"USDC", "PYUSD"}          # a Morpho market lends one coin; USDC, or PYUSD for the sUSDe market
MIN_MARKET = 20_000_000            # supplied, USD: a cheap rate on a market of $300k is not a route


def get(path: str, base: str = SRC):
    req = urllib.request.Request(base + path, headers={"User-Agent": "qa-cymetica capital-maximizer demo"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def cautious(p: dict) -> float:
    """The lowest of today's, the 7-day and the 30-day APY: a month's estimate should not ride one day's spike."""
    return round(min(x for x in (p.get("apy"), p.get("apyBase7d"), p.get("apyMean30d")) if x is not None), 4)


def biggest(pools, **want):
    hits = [p for p in pools if all(p.get(k) == v for k, v in want.items())]
    if not hits:
        raise SystemExit(f"no pool for {want}")
    return max(hits, key=lambda p: p["tvlUsd"] or 0)


def row(p: dict, role: str, **extra) -> dict:
    out = {"id": p["pool"], "project": p["project"], "chain": p["chain"], "symbol": p["symbol"], "role": role,
           "apy": cautious(p), "apy_now": round(p.get("apy") or 0, 4), "apy_7d": p.get("apyBase7d"),
           "apy_30d": p.get("apyMean30d"), "tvl": round(p["tvlUsd"] or 0)}
    out.update(extra)
    return out


def platforms(facts: dict, hacks: list) -> list:
    """Every platform of the tab with the facts its rule reads; a platform that fails the rule stops the refresh."""
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    family = lambda f: f.get("parentProtocol") or f["slug"]
    by_id, by_name = {str(f.get("id")): f for f in facts.values()}, {f["name"].lower(): f for f in facts.values()}
    lost = {}
    for h in hacks:
        if h["date"] < now - 2 * 365 * 86400 or h.get("classification") == "Social Engineering":
            continue
        f = by_id.get(str(h.get("defillamaId"))) or by_name.get(h["name"].lower())
        if f:
            lost[family(f)] = lost.get(family(f), 0) + max(0, (h["amount"] or 0) - (h.get("returnedFunds") or 0))
    out, bad = [], []
    for slug, name in [(k, n) for k, (n, _) in PROTOCOLS.items()] + list(PLATFORMS.items()):
        f = facts[slug]
        ct = {c: v for c, v in (f.get("chainTvls") or {}).items() if c in CCTP_CHAINS and v >= 1_000_000}
        p = {"slug": slug, "name": name, "icon": PROTOCOLS[slug][1] if slug in PROTOCOLS else slug,
             "category": f.get("category"), "tvl": round(sum(ct.values())),
             "audited": str(f.get("audits") or "0") != "0",
             # DefiLlama records a listing date only for later listings: none means listed before it kept them
             "age_years": round((now - f["listedAt"]) / 86400 / 365, 1) if f.get("listedAt") else None,
             "lost_24m": round(lost.get(family(f), 0)), "chains": sorted(ct, key=lambda c: -ct[c]),
             "site": urllib.parse.urlsplit(f.get("url") or "").netloc, "in_finder": slug in PROTOCOLS}
        if not (p["audited"] and (p["age_years"] is None or p["age_years"] >= 1) and p["lost_24m"] <= 1_000_000
                and p["tvl"] >= MIN_PLATFORM and not slug.startswith(CEX_ISSUED)):
            bad.append(f"{slug}: {p}")
        out.append(p)
    if bad:
        raise SystemExit("platforms that no longer pass the rule:\n" + "\n".join(bad))
    return sorted(out, key=lambda p: -p["tvl"])


def main() -> None:
    pools = get("/pools")["data"]
    lend = {x["pool"]: x for x in get("/lendBorrow")}
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    mine = [p for p in pools if p["project"] in PROTOCOLS and p["chain"] in CHAINS]
    plain = [p for p in mine if not p.get("poolMeta")]
    out = []
    for project, chain, symbol, name in VAULTS:
        out.append(row(biggest(plain, project=project, chain=chain, symbol=symbol), "vault", name=name))
    for project, chain, symbol, token, asset in STAKES:
        out.append(row(biggest(mine, project=project, chain=chain, symbol=symbol), "stake", token=token, asset=asset))
    for project, chain, symbol, fee, kind in LPS:
        p = biggest(mine, project=project, chain=chain, symbol=symbol, poolMeta=fee)
        out.append(row(p, "lp", kind=kind, name=f"ETH/USDC {fee}" if fee else "GM ETH-USDC"))
    # Aave lends USDC at the chain's USDC pool rate against each collateral it accepts
    for chain in CHAINS:
        usdc = biggest(plain, project="aave-v3", chain=chain, symbol="USDC")
        for p in plain:
            b = lend.get(p["pool"])
            if (p["project"] == "aave-v3" and p["chain"] == chain and p["symbol"] in COLLATERAL and b and b.get("ltv")
                    and (b.get("totalSupplyUsd") or 0) >= MIN_MARKET):
                token, asset, stake = COLLATERAL[p["symbol"]]
                out.append(row(p, "market", token=token, asset=asset, stake=stake, ltv=b["ltv"], loan="USDC",
                               borrow=round(lend[usdc["pool"]]["apyBaseBorrow"], 4), loan_pool=usdc["pool"]))
    # a Morpho market is one collateral and one loan; the biggest of each pair on each chain
    seen = set()
    for p in sorted(mine, key=lambda p: -(p["tvlUsd"] or 0)):
        b = lend.get(p["pool"])
        if (p["project"] != "morpho-blue" or not b or p["symbol"] not in COLLATERAL or b.get("mintedCoin") not in LOANS
                or (b.get("totalSupplyUsd") or 0) < MIN_MARKET):
            continue
        token, asset, stake = COLLATERAL[p["symbol"]]
        if (p["chain"], p["symbol"], b["mintedCoin"]) in seen or (b["mintedCoin"] == "PYUSD") != (asset == "USD"):
            continue
        seen.add((p["chain"], p["symbol"], b["mintedCoin"]))
        out.append(row(p, "market", token=token, asset=asset, stake=stake, ltv=b["ltv"], loan=b["mintedCoin"],
                       borrow=round(b["apyBaseBorrow"], 4), size=round(b.get("totalSupplyUsd") or 0)))
    looked = [p for p in mine if (p["tvlUsd"] or 0) >= 1_000_000]
    ticker = [[p["project"], p["symbol"], p["chain"], round(p.get("apy") or 0, 2)]
              for p in sorted(looked, key=lambda p: -(p["tvlUsd"] or 0))[:48]]
    # each protocol's own DefiLlama record: what it is, how much it holds, whether it is audited, where it runs
    facts = {p["slug"]: p for p in get(LLAMA + "/protocols", base="")}
    protocols = {}
    for k, (n, i) in PROTOCOLS.items():
        f = facts[k]
        protocols[k] = {"name": n, "icon": i, "llama_name": f["name"], "category": f.get("category"),
                        "tvl": round(f.get("tvl") or 0), "audited": str(f.get("audits") or "0") != "0",
                        "audit_links": len(f.get("audit_links") or []), "chains": len(f.get("chains") or []),
                        "site": urllib.parse.urlsplit(f.get("url") or "").netloc,
                        "pools_read": sum(1 for p in looked if p["project"] == k)}
    data = {
        "fetched_at": now,
        "source": f"{SRC}/pools + {SRC}/lendBorrow + {LLAMA}/protocols + {LLAMA}/hacks",
        "protocols": protocols,
        "cctp_chains": CCTP_CHAINS,
        "platforms": platforms(facts, get(LLAMA + "/hacks", base="")),
        "scanned": {"pools": len(looked), "protocols": len({p["project"] for p in looked}), "chains": len(CHAINS)},
        "pools": out,
        "ticker": ticker,
    }
    here = Path(__file__).resolve().parent
    (here / "data.js").write_text("// written by rates.py -- DefiLlama, read " + now + "\nwindow.CM_DATA = "
                                  + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(out)} pools, {len(looked)} looked through, {now}")


if __name__ == "__main__":
    main()
