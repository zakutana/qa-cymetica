"""Read today's DeFi rates for the Yield Booster demo from DefiLlama and write data.js beside the page.

Only the pools a route can use, each by its DefiLlama pool id, with the time they were read, and how many pools of the
allowlisted protocols the finder looked through. GET only, no key. Refresh: python outbox/yield-booster/rates.py

The allowlist is ours for the demo (blue-chip, permissionless, no KYC to use); Cymetica makes its own selection.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request
from pathlib import Path

SRC = "https://yields.llama.fi"
CHAINS = ("Ethereum", "Arbitrum", "Base")
# DefiLlama project -> name shown, icon slug on icons.llamao.fi
PROTOCOLS = {
    "aave-v3": ("Aave", "aave-v3"),
    "compound-v3": ("Compound", "compound-v3"),
    "morpho-blue": ("Morpho", "morpho-blue"),
    "spark-savings": ("Spark", "spark"),
    "sky-lending": ("Sky", "sky"),
    "lido": ("Lido", "lido"),
    "ether.fi-stake": ("ether.fi", "ether.fi"),
    "rocket-pool": ("Rocket Pool", "rocket-pool"),
    "ethena-usde": ("Ethena", "ethena"),
    "uniswap-v3": ("Uniswap", "uniswap"),
    "curve-dex": ("Curve", "curve-dex"),
    "gmx-evm": ("GMX", "gmx"),
}
# stablecoin homes for USDC: (project, chain, DefiLlama symbol, name shown)
VAULTS = [
    ("aave-v3", "Ethereum", "USDC", "Aave USDC"),
    ("aave-v3", "Base", "USDC", "Aave USDC"),
    ("aave-v3", "Arbitrum", "USDC", "Aave USDC"),
    ("compound-v3", "Ethereum", "USDC", "Compound USDC"),
    ("spark-savings", "Ethereum", "USDC", "Spark Savings"),
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
    ("gmx-evm", "Arbitrum", "ETH-USDC", None, "gmx"),
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


def get(path: str):
    req = urllib.request.Request(SRC + path, headers={"User-Agent": "qa-cymetica yield-booster demo"})
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
    data = {
        "fetched_at": now,
        "source": f"{SRC}/pools + {SRC}/lendBorrow",
        "protocols": {k: {"name": n, "icon": i} for k, (n, i) in PROTOCOLS.items()},
        "scanned": {"pools": len(looked), "protocols": len({p["project"] for p in looked}), "chains": len(CHAINS)},
        "pools": out,
        "ticker": ticker,
    }
    here = Path(__file__).resolve().parent
    (here / "data.js").write_text("// written by rates.py -- DefiLlama, read " + now + "\nwindow.YB_DATA = "
                                  + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(out)} pools, {len(looked)} looked through, {now}")


if __name__ == "__main__":
    main()
