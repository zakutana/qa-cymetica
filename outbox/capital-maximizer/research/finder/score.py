"""The one calculation: every route is priced here once, and a tier is only a filter over the result.

    python -I outbox/capital-maximizer/research/finder/score.py <data-dir> [--top N] [--check] [--json out.json]

A route's dollars come only from this file. A hunter adds routes in candidates/*.json (shape: see load_candidates) and
never computes its own money. The rate rule, the month and the costs are Cymetica's own (read back from their API), so
a gap between us and them is search, not a different rule:

  rate    the lowest of apyBase now, apyBase7d, apyMean30d; a row with no apyBase has no rate
  month   amount x ((1 + net)^(30/365) - 1) - costs
  net     L x asset rate - (L - 1) x borrow rate
  costs   gas in units of their Ethereum lend, swaps as round-trip basis points on what is swapped

Two figures per route. "profit" is by their rule, so it compares with their number. "lasting" is what the same route earns on the
30-day median of apyBase (lasting.py), after the share of a pool's fees that its LPs really keep, against the worse of the borrow rate
now and over the week: the rule's mean keeps a spike, and DefiLlama's fee figure is before the protocol's cut.

Liquidation is computed and shown, never used as a filter: the operator's rule. What does stop a route: no KYC platform,
a deposit gate, a lender that will not lend that much, a pool under the floor.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHAIN_NAMES = {"Polygon": "Polygon PoS", "Optimism": "OP Mainnet", "Hyperliquid L1": "HyperEVM", "Xlayer": "X Layer", "World Chain": "World Chain", "Arbitrum One": "Arbitrum",
               "Polygon PoS": "Polygon PoS", "OP Mainnet": "OP Mainnet", "HyperEVM": "HyperEVM"}
USDC = {"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
        "0x0b2c639c533813f4aa9d7837caf62653d097ff85", "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359", "0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e",
        "epjfwdd5aufqssqem2qn1xzybapc8g4wegghkzwytdt1v"}
DOLLAR = re.compile(r"USD|DAI|GHO|FRAX|DOLA|BOLD|FXSAVE|MIM|USR")
ETHISH = re.compile(r"(^|[^A-Z])(W?ETH|STETH|WSTETH|WEETH|EETH|RETH|OSETH|CBETH|EZETH|METH|ETHX|TETH|RSETH|SFRXETH|FRXETH|OETH|ALETH|MSETH|LSETH|ETH\+)($|[^A-Z])")
BTCISH = re.compile(r"(W?BTC|CBBTC|LBTC|TBTC|SOLVBTC|EBTC|BTC\.B|XBTC|UBTC)")
SOLISH = re.compile(r"(^|[^A-Z])(W?SOL|JITOSOL|MSOL|BSOL|JUPSOL|SSOL|PSOL|DSOL|HSOL|DFDVSOL|INF)($|[^A-Z])")
AVAXISH = re.compile(r"(^|[^A-Z])(W?AVAX|SAVAX)($|[^A-Z])")
HYPEISH = re.compile(r"(^|[^A-Z])(W?HYPE|KHYPE|WSTHYPE|BEHYPE)($|[^A-Z])")
# a token and the issuer whose DefiLlama row says what it earns. Only these earn on their own: a symbol alone lied in 93 routes (AUSD 6.55 from Accountable, USDG 3.76 from Spark, xBTC 9.20 from Liminal)
ISSUER = {"STETH": "lido", "WSTETH": "lido", "WEETH": "ether.fi-stake", "RETH": "rocket-pool", "OSETH": "stakewise-v3", "ETHX": "stader", "EZETH": "renzo",
          "JITOSOL": "jito-liquid-staking", "MSOL": "marinade-liquid-staking", "SAVAX": "benqi-staked-avax", "KHYPE": "kinetiq-khype", "SUSDS": "sky-lending", "STUSDS": "sky-lending",
          "SDAI": "sky-lending", "SUSDE": "ethena-usde", "SUSDAI": "usd-ai", "STCUSD": "cap", "SCRVUSD": "crvusd", "CBETH": "coinbase-wrapped-staked-eth", "SFRXUSD": "frax", "SIUSD": "infinifi"}
ALIAS = {"WSTETH": "STETH"}
PT_ISSUER = {**ISSUER, "USD3": "3jane-lending", "AUSD": "agora", "USDAT": "saturn", "SUSDX": "axis", "STRUSD": "strata", "APYUSD": "apyx-protocol", "APXUSD": "apyx-protocol"}
SKY_ONE_TO_ONE = {"STUSDS", "SUSDS", "USDS"}  # USDC to USDS is Sky's 1:1 window, and staking it is a mint: Cymetica charges 0
SWAP = {"sky": 0, "stable": 10, "volatile": 10, "mint": 1, "pt": 10, "lp": 30}  # round trip, basis points: their $15 on $5,000 for a pool
GAS_UNITS = {"lend": 1.0, "lp": 2.0, "loop": 4.25, "away": 0.65}  # off their own costs at two minutes: 0.46/0.91/1.95 and 2.78/5.47/11.73; any route off Ethereum 1.79
MAJORS = {"WETH", "WSTETH", "WBTC", "CBBTC"}
NOT_SKY = {"USDT", "USDT0", "USD\u20ae0", "PYUSD", "AUSD", "USDE", "GHO", "USDG"}  # a loan in these must be swapped: Sky's 1:1 window is USDC and USDS only
POOLED_LENDERS = {"sparklend", "benqi-lending", "hyperlend-pooled", "kamino-lend", "dolomite"}  # one market: any collateral against any loan


def base_of(symbol: str) -> str:
    up = symbol.upper().replace("PT-", "")
    if "EUR" in up:
        return "other"
    if DOLLAR.search(up):
        return "dollar"
    if ETHISH.search(up):
        return "eth"
    if BTCISH.search(up):
        return "btc"
    if SOLISH.search(up):
        return "sol"
    if AVAXISH.search(up):
        return "avax"
    if HYPEISH.search(up):
        return "hype"
    return "other"


def rate_of(p: dict) -> float | None:
    if p.get("apyBase") is None:
        return None
    week = p.get("apyBase7d")
    return min(v for v in (p.get("apyBase"), week if week else None, p.get("apyMean30d")) if v is not None)


class Data:
    def __init__(self, folder: Path):
        self.folder = folder
        read = lambda n: json.loads((folder / f"{n}.json").read_text(encoding="utf-8"))
        self.pools = read("llama_pools")
        self.lendborrow = {x["pool"]: x for x in read("llama_lendborrow")}
        self.platforms = read("cm_platforms")["platforms"]
        self.markets = read("morpho_markets")
        self.vaults_v2 = read("morpho_vaults_v2")
        self.vaults_v1 = read("morpho_vaults_v1")
        self.aave = read("aave")
        self.pendle = read("pendle")
        self.fluid = read("fluid")
        self.lasting = read("lasting") if (folder / "lasting.json").exists() else {}
        self.refused_list = [x for f in sorted((HERE / "refused").glob("*.json")) if (HERE / "refused").exists() for x in json.loads(f.read_text(encoding="utf-8"))]
        self.top3 = {t: read(f"cm_top3_{t}") for t in ("conservative", "medium", "high", "og")}
        self.cm_tiers = read("cm_tiers")
        self.passed = {x["slug"] for x in self.platforms if x["passed"]}
        self.kind = {x["slug"]: x["kind"] for x in self.platforms}
        self.failed = {x["slug"]: x["reason"] for x in self.platforms if not x["passed"]}
        self.chains = set(self.cm_tiers["counters"]["chain_names"])
        self.taken_at = (folder / "taken_at.txt").read_text(encoding="utf-8")
        self.gas_unit = self._gas_unit()
        self.gates = self._gates()
        self.yields = self._yields()
        self.usdc = set(USDC) | {u.lower() for p in self.pools if p["symbol"].upper() == "USDC" and p.get("exposure") == "single" and p["project"] in ("aave-v3", "compound-v3", "fluid-lending")
                                 for u in (p.get("underlyingTokens") or [])}
        self.books = self._books()

    def _gas_unit(self) -> float:
        """Their Ethereum lend's gas this minute, read back from their own top 3."""
        seen = []
        for d in self.top3.values():
            for r in d["routes"]:
                if r.get("chain_path") == ["Ethereum"]:
                    kind = {"stable_supply": "lend", "lp": "lp", "stable_loop": "loop", "lst_loop": "loop"}.get(r["family"])
                    if kind:
                        seen.append(r["costs"]["gas_usd"] / GAS_UNITS[kind])
        return sum(seen) / len(seen) if seen else 0.5

    def _gates(self) -> dict:
        out = {}
        for v in self.vaults_v2:
            gate = ((v.get("gatesConfig") or {}).get("sendAssetsGate") or {}).get("address")
            if gate and int(gate, 16):
                out[(v["chain"]["network"].lower(), (v.get("symbol") or "").upper())] = gate
        return out

    def _books(self) -> dict:
        """Morpho vault: the share of what it lends that sits against majors. Idle money counts as neither."""
        out = {}

        def share(pairs):
            total = sum(a for _, a in pairs)
            return sum(a for s, a in pairs if s and s.upper() in MAJORS) / total if total else 0.0

        for v in self.vaults_v1:
            alloc = ((v.get("state") or {}).get("allocation") or [])
            pairs = [((a["market"]["collateralAsset"] or {}).get("symbol"), a.get("supplyAssetsUsd") or 0) for a in alloc if a["market"].get("collateralAsset")]
            key = (v["chain"]["network"].lower(), (v.get("symbol") or "").upper())
            out[key] = min(out.get(key, 1.0), share(pairs))
        for v in self.vaults_v2:
            pairs = []
            for ad in v.get("book") or []:
                for it in (ad.get("positions") or {}).get("items", []):
                    pairs.append((((it.get("market") or {}).get("collateralAsset") or {}).get("symbol"), (it.get("state") or {}).get("supplyAssetsUsd") or 0))
            if pairs:
                key = (v["chain"]["network"].lower(), (v.get("symbol") or "").upper())
                out[key] = min(out.get(key, 1.0), share(pairs))
        return out

    def _yields(self) -> dict:
        """What a token earns on its own: the biggest row of its named issuer."""
        out: dict[str, dict] = {}
        for p in self.pools:
            sym = p["symbol"].upper()
            if p["project"] != ISSUER.get(sym) and p["project"] != ISSUER.get(next((k for k, v in ALIAS.items() if v == sym), "")):
                continue
            if rate_of(p) is None or p.get("exposure") != "single":
                continue
            if sym not in out or p["tvlUsd"] > out[sym]["tvlUsd"]:
                out[sym] = p
        return out

    def token_yield(self, symbol: str) -> dict | None:
        s = symbol.upper()
        return self.yields.get(ALIAS.get(s, s))

    def pt_issuer(self, m: dict) -> str:
        """The slug that issues what a PT wraps; unlisted:<name> when nobody has named it."""
        return PT_ISSUER.get(m["name"].upper(), f"unlisted:{m['name']}")


def chain_ok(data: Data, chain: str) -> str | None:
    name = CHAIN_NAMES.get(chain, chain)
    return name if name in data.chains else None


def hold_routes(data: Data) -> list[dict]:
    rows = []
    for p in data.pools:
        rate, chain = rate_of(p), chain_ok(data, p["chain"])
        if rate is None or rate <= 0 or not chain:
            continue
        slug, sym = p["project"], p["symbol"].upper()
        if slug not in data.kind or slug in ("pendle-v2", "fluid-dex"):  # Pendle is read from Pendle; DefiLlama's Fluid DEX row is fees only, its real rate is a hunter's sum
            continue
        meta = p.get("poolMeta") or ""
        under = {u.lower() for u in (p.get("underlyingTokens") or [])}
        kind = data.kind[slug]
        one_usdc = len(under) == 1 and bool(under & data.usdc)
        single = p.get("exposure") == "single" or (kind == "lending" and one_usdc)
        family, first = None, SWAP["stable"]
        if single and (sym == "USDC" or under & data.usdc) and kind == "lending":
            family, first = ("usd_lend" if sym == "USDC" else "usd_vault"), 0
        elif single and p.get("stablecoin"):
            family = "savings" if kind in ("stable", "savings") else "usd_vault"
            first = 0 if under & data.usdc else SWAP["sky"] if sym in SKY_ONE_TO_ONE else SWAP["stable"]
        elif single and kind in ("lst", "restaking"):
            family, first = "stake_hold", SWAP["volatile"]
        elif kind == "perps":
            family, first = "perps_lp", SWAP["stable"]
        elif p.get("exposure") == "multi" or kind == "dex":
            bases = {base_of(t) for t in re.split(r"[-/]", sym) if t}
            if bases == {"dollar"}:
                family = "lp_stable"
            elif len(bases) == 1 and "other" not in bases:
                family = "lp_correlated"
            else:
                family = "lp_volatile"
            tier = re.match(r"([0-9.]+)%", meta)
            first = max(SWAP["lp"], float(tier.group(1)) * 100) if tier else SWAP["lp"]
        if not family:
            continue
        rows.append({"id": f"hold:{p['pool']}", "name": f"{p['symbol']}{' ' + meta if meta else ''}", "family": family, "platforms": [slug], "issuers": [],
                     "chain": chain, "rate": rate, "tvl": _size(data, p), "pool": p["pool"], "max_l": 1.0, "borrow": None, "free": None, "lltv": None,
                     "first_bps": first, "loop_bps": 0, "gas": GAS_UNITS["lp" if family.startswith("lp") else "lend"], "meta": meta,
                     "flags": _rate_flags(p), "symbol": sym, "gate": data.gates.get((p["chain"].lower(), sym))})
    return rows


def _size(data: Data, p: dict) -> float:
    """DefiLlama's tvlUsd on a lending row is supply minus borrow: Benqi USDC with $16.3M supplied read $1.5M. On Morpho rows totalSupplyUsd is the collateral, so it stays out."""
    x = data.lendborrow.get(p["pool"]) or {}
    return p["tvlUsd"] if p["project"].startswith("morpho") else max(p["tvlUsd"], x.get("totalSupplyUsd") or 0)


def _rate_flags(p: dict) -> list[str]:
    flags = []
    if p.get("apyMean30d") is not None and p.get("apyBase") is not None and p["apyBase"] > 2 * p["apyMean30d"]:
        flags.append("spike: today over twice the 30-day mean")
    if p.get("apyBase7d") is None:
        flags.append("no 7-day reading")
    return flags


def max_lever(limit: float, step: float) -> float:
    """The highest leverage a lender gives at this limit, on the grid; strictly under the limit, or the loop cannot open."""
    if limit <= 0 or limit >= 1:
        return 1.0
    top = 1 / (1 - limit)
    return max(1.0, math.floor((top - 1e-9) / step) * step if (top / step) % 1 else top - step)


def loop_route(data: Data, step: float, *, venue: str, chain: str, collateral: str, loan: str, y: dict | None, y_rate: float | None, y_tvl: float, bor: float,
               limit: float, free: float, ident: str, extra_issuers=(), market_size=0.0, flags=(), liq_limit: float | None = None, bor_week: float | None = None) -> dict | None:
    rate = y_rate if y_rate is not None else (rate_of(y) if y else None)
    if rate is None:
        return None
    flags = list(flags)
    # a debt in a token that earns grows by what it earns as well as by its interest: wstETH borrowed at 0 still costs Lido's yield
    grows = data.token_yield(loan)
    grows_by = rate_of(grows) if grows else 0
    if grows_by:
        bor += grows_by
        flags.append(f"debt also grows {grows_by:.2f}% a year: {loan} earns")
    cb, lb = base_of(collateral), base_of(loan)
    family = "loop_dollar" if cb == lb == "dollar" else "loop_correlated" if cb == lb and cb != "other" else "loop_volatile"
    up = collateral.upper()
    if family == "loop_dollar":
        first = SWAP["sky"] if up in SKY_ONE_TO_ONE else SWAP["stable"]
        loop_bps = SWAP["stable"] if loan.upper() in NOT_SKY or first else SWAP["sky"]
    elif up.startswith("PT-"):
        first, loop_bps = SWAP["pt"], SWAP["pt"]
    else:
        first, loop_bps = SWAP["volatile"], SWAP["mint"] if chain == "Ethereum" and cb == lb else SWAP["volatile"]
    issuers = [y["project"]] if y else []
    return {"id": ident, "name": f"{collateral} / {loan} loop", "family": family, "platforms": [venue], "issuers": issuers + list(extra_issuers), "chain": chain,
            "rate": rate, "tvl": market_size or y_tvl, "pool": y["pool"] if y else None, "max_l": max_lever(limit, step), "borrow": bor, "free": free, "lltv": liq_limit or limit,
            "borrow_week": (bor_week + grows_by) if bor_week else None, "first_bps": first, "loop_bps": loop_bps, "gas": GAS_UNITS["loop"], "meta": "", "flags": flags, "symbol": up, "gate": None}


def morpho_loops(data: Data, step: float) -> list[dict]:
    pts = {}
    for m in data.pendle:
        pts[m["pt"].split("-", 1)[1].lower()] = m
    rows = []
    for m in data.markets:
        st, c, l = m.get("state") or {}, m.get("collateralAsset"), m.get("loanAsset")
        if not c or not l or not st or base_of(l["symbol"]) == "other":
            continue
        chain = chain_ok(data, (m.get("morphoBlue") or {}).get("chain", {}).get("network") or "")
        if not chain or (st.get("liquidityAssetsUsd") or 0) < 5000 or (st.get("supplyAssetsUsd") or 0) < 1e6:
            continue
        lltv, sym, bor = int(m["lltv"]) / 1e18, c["symbol"], (st.get("borrowApy") or 0) * 100
        pt = pts.get(c["address"].lower())
        flags = []
        if st.get("weeklyBorrowApy") and st["weeklyBorrowApy"] * 100 > 1.5 * max(bor, .01):
            flags.append(f"borrow was {st['weeklyBorrowApy'] * 100:.2f}% over the week")
        common = dict(venue="morpho-blue", chain=chain, collateral=sym, loan=l["symbol"], bor=bor, limit=lltv, free=st.get("liquidityAssetsUsd") or 0,
                      ident=f"morpho:{m['marketId']}", market_size=st.get("supplyAssetsUsd") or 0, flags=flags, bor_week=(st.get("weeklyBorrowApy") or 0) * 100 or None)
        if pt:
            days = _days_to(pt["expiry"], data.taken_at)
            if days < 7:
                continue
            issuers = ["pendle-v2", data.pt_issuer(pt)]
            r = loop_route(data, step, y=None, y_rate=pt["details"]["impliedApy"] * 100, y_tvl=pt["details"]["liquidity"], extra_issuers=issuers, **common)
            if r:
                r["flags"].append(f"PT matures in {days:.0f} days")
                rows.append(r)
            continue
        y = data.token_yield(sym)
        if not y:
            continue
        r = loop_route(data, step, y=y, y_rate=None, y_tvl=y["tvlUsd"], **common)
        if r:
            rows.append(r)
    return rows


def _days_to(expiry: str, now: str) -> float:
    import datetime as dt
    a = dt.datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    b = dt.datetime.fromisoformat(now)
    return (a - b).total_seconds() / 86400


def aave_loops(data: Data, step: float) -> list[dict]:
    rows = []
    for mk in data.aave:
        chain = chain_ok(data, mk["chain"]["name"])
        if not chain:
            continue
        res = [r for r in mk["reserves"] if not r["isFrozen"] and not r["isPaused"]]
        borrowable = [r for r in res if (r.get("borrowInfo") or {}).get("borrowingState") == "ENABLED"]
        for c in res:
            y = data.token_yield(c["underlyingToken"]["symbol"])
            if not y:
                continue
            routes = []
            ltv = float(c["supplyInfo"]["maxLTV"]["value"] or 0)
            if c["supplyInfo"]["canBeCollateral"] and ltv > 0:
                routes += [(b, ltv, "main") for b in borrowable]
            for e in c.get("eModeInfo") or []:
                if not e["canBeCollateral"]:
                    continue
                for b in borrowable:
                    for be in b.get("eModeInfo") or []:
                        if be["categoryId"] == e["categoryId"] and be["canBeBorrowed"]:
                            routes.append((b, float(e["maxLTV"]["value"]), f"e-mode {e['label']}"))
            for b, limit, mode in routes:
                if b["underlyingToken"]["symbol"] == c["underlyingToken"]["symbol"] or base_of(b["underlyingToken"]["symbol"]) == "other":
                    continue
                bi = b["borrowInfo"]
                r = loop_route(data, step, venue="aave-v3", chain=chain, collateral=c["underlyingToken"]["symbol"], loan=b["underlyingToken"]["symbol"], y=y, y_rate=None,
                               y_tvl=y["tvlUsd"], bor=float(bi["apy"]["value"]) * 100, limit=limit, free=float(bi["availableLiquidity"]["usd"] or 0),
                               ident=f"aave:{mk['name']}:{c['underlyingToken']['symbol']}:{b['underlyingToken']['symbol']}:{mode}", flags=[mode])
                if r:
                    rows.append(r)
    return rows


def generic_loops(data: Data, step: float) -> list[dict]:
    """Other lenders from DefiLlama's lendBorrow: collateral and loan in one venue, one chain, one market."""
    by_market = defaultdict(list)
    for p in data.pools:
        x = data.lendborrow.get(p["pool"])
        if x and p["project"] in POOLED_LENDERS and p["project"] in data.passed:
            by_market[(p["project"], p["chain"], p.get("poolMeta") or "")].append((p, x))
    rows = []
    for (venue, chain, meta), items in by_market.items():
        name = chain_ok(data, chain)
        if not name:
            continue
        for pc, xc in items:
            limit = xc.get("ltv") or 0
            if limit <= 0:
                continue
            y = data.token_yield(pc["symbol"])
            if not y:
                continue
            for pb, xb in items:
                if pb["pool"] == pc["pool"] or not xb.get("borrowable") or xb.get("apyBaseBorrow") is None or base_of(pb["symbol"]) == "other":
                    continue
                free = (xb.get("totalSupplyUsd") or 0) - (xb.get("totalBorrowUsd") or 0)
                r = loop_route(data, step, venue=venue, chain=name, collateral=pc["symbol"], loan=pb["symbol"], y=y, y_rate=None, y_tvl=y["tvlUsd"], bor=xb["apyBaseBorrow"],
                               limit=limit, free=free, ident=f"{venue}:{chain}:{meta}:{pc['symbol']}:{pb['symbol']}")
                if r:
                    r["meta"] = meta
                    rows.append(r)
    return rows


def fluid_loops(data: Data, step: float) -> list[dict]:
    """Fluid's plain vaults (type 1): one collateral, one loan, the limit and the rates are the vault's own. The smart vaults are a hunter's."""
    names = {1: "Ethereum", 42161: "Arbitrum", 8453: "Base", 137: "Polygon PoS", 9745: "Plasma"}
    rows = []
    for v in data.fluid:
        if str(v.get("type")) != "1" or v.get("fluid_kind") != "vault":
            continue
        c, l = v["supplyToken"]["token0"], v["borrowToken"]["token0"]
        y = data.token_yield(c["symbol"])
        lent = float(v["supplyRate"]["vault"]["rate"]) / 100  # the vault pays its own supply rate on top of what the token earns
        if (not y and lent <= 0) or base_of(l["symbol"]) == "other" or c["symbol"] == l["symbol"]:
            continue
        free = int(v.get("borrowable") or 0) / 10 ** int(l.get("decimals") or 18) * float(l.get("price") or 0)
        r = loop_route(data, step, venue="fluid-lending", chain=names[v["chainId"]], collateral=c["symbol"], loan=l["symbol"], y=y, y_rate=(rate_of(y) if y else 0) + lent,
                       y_tvl=y["tvlUsd"] if y else 0,
                       market_size=int(v.get("totalSupply") or 0) / 10 ** int(c.get("decimals") or 18) * float(c.get("price") or 0),
                       bor=float(v["borrowRate"]["vault"]["rate"]) / 100, limit=float(v["collateralFactor"]) / 1e4, liq_limit=float(v["liquidationThreshold"]) / 1e4,
                       free=free, ident=f"fluid:{v['chainId']}:{v['id']}")
        if r:
            rows.append(r)
    return rows


def pendle_holds(data: Data) -> list[dict]:
    rows = []
    for m in data.pendle:
        days = _days_to(m["expiry"], data.taken_at)
        if days < 7 or m["details"]["liquidity"] < 1e6:
            continue
        dollar = base_of(m["name"]) == "dollar"
        rows.append({"id": f"pendle:{m['pt']}", "name": f"PT-{m['name']} {m['expiry'][:10]}", "family": "pt_hold_dollar" if dollar else "pt_hold_other", "platforms": ["pendle-v2"],
                     "issuers": [data.pt_issuer(m)], "chain": m["chain"], "rate": m["details"]["impliedApy"] * 100, "tvl": m["details"]["liquidity"],
                     "pool": m["pt"], "max_l": 1.0, "borrow": None, "free": None, "lltv": None, "first_bps": SWAP["pt"], "loop_bps": 0, "gas": GAS_UNITS["lend"], "meta": "",
                     "flags": [f"PT matures in {days:.0f} days"], "symbol": f"PT-{m['name']}".upper(), "gate": None})
    return rows


def load_candidates(step: float) -> list[dict]:
    """candidates/*.json: a list of routes in the shape above (id, name, family, platforms, issuers, chain, rate, tvl, pool, max_l, borrow, free, lltv,
    first_bps, loop_bps, gas, meta, flags, symbol, gate) plus "source": where a human reads each number. A rate is a figure the rule allows, never a guess."""
    rows = []
    for f in sorted((HERE / "candidates").glob("*.json")) if (HERE / "candidates").exists() else []:
        for r in json.loads(f.read_text(encoding="utf-8")):
            r.setdefault("flags", [])
            r.setdefault("gate", None)
            r.setdefault("meta", "")
            r["hunter"] = f.stem
            days = next((re.search(r"matures in (\d+)", x) for x in r["flags"] if "matures in" in x), None)
            if days and "matures_days" not in r:
                r["matures_days"] = int(days.group(1))
            rows.append(r)
    return rows


def month_rate(route: dict, rate: float) -> float:
    """A PT that matures inside the month earns its fixed rate only until it does, then what its token earns."""
    left = route.get("matures_days")
    if left is not None and left < 30:
        return (left * rate + (30 - left) * (route.get("after_rate") or 0)) / 30
    return rate


def price(route: dict, leverage: float, amount: float, gas_unit: float) -> dict:
    rate = month_rate(route, route["rate"])
    net = leverage * rate - (leverage - 1) * (route.get("borrow") or 0)
    gross = amount * ((1 + net / 100) ** (30 / 365) - 1) if net > -100 else -amount  # a carry worse than -100% loses everything
    swap =amount * route["first_bps"] / 1e4 + amount * (leverage - 1) * route["loop_bps"] / 1e4
    gas = (route["gas"] if route["chain"] == "Ethereum" else GAS_UNITS["away"]) * gas_unit
    liq = None
    if leverage > 1 and route.get("lltv"):
        liq = round((1 - (leverage - 1) / leverage / route["lltv"]) * 100, 2)
    cap = None
    if leverage > 1 and route.get("free") is not None:
        cap = route["free"] / (leverage - 1)
    return {"leverage": leverage, "net": round(net, 2), "gross": round(gross, 2), "swap": round(swap, 2), "gas": round(gas, 2), "profit": round(gross - swap - gas, 2), "liq_pct": liq, "capacity_usd": cap}


def lp_share(cfg: dict, route: dict) -> float:
    """What a pool's LPs keep of the fee DefiLlama counts: read on-chain per tier and chain by the hunters, 1.0 where nobody read it."""
    if not route["family"].startswith("lp_"):
        return 1.0
    table = cfg["lp_fee_share"].get(route["platforms"][0], {})
    if route["chain"] in table.get("off_on", []) or (table.get("only_on") and route["chain"] not in table["only_on"]):
        return 1.0
    meta = route.get("meta") or ""
    return next((v for k, v in table.items() if k in ("*", meta) and isinstance(v, float)), 1.0)


def lasting(data: Data, cfg: dict, route: dict, leverage: float, amount: float, q: dict) -> float | None:
    """The same route on the 30-day median and the worse borrow rate. None when no chart was read: a fixed rate (a PT) keeps its own."""
    fixed = route["family"].startswith("pt_") or str(route.get("symbol", "")).startswith("PT-")
    row = data.lasting.get(route.get("pool") or "")
    if route.get("lasting_rate") is not None:
        rate = route["lasting_rate"]
    elif fixed:
        rate = month_rate(route, route["rate"])
    elif row:
        rate = min(route["rate"], row["median"]) * lp_share(cfg, route)
    else:
        return None
    bor = max(route.get("borrow") or 0, route.get("borrow_week") or 0, route.get("lasting_borrow") or 0)
    net = leverage * rate - (leverage - 1) * bor
    gross = amount * ((1 + net / 100) ** (30 / 365) - 1) if net > -100 else -amount
    return round(gross - q["swap"] - q["gas"], 2)


def refused(data: Data, cfg: dict, route: dict, amount: float, q: dict) -> str | None:
    for item in data.refused_list:
        if item["match"].lower() in f"{route.get('id')} {route.get('name')} {route.get('pool')}".lower():
            return item["reason"]
    if route.get("gate"):
        return f"deposit gate {route['gate']}"
    for token in re.split(r"[-/ ]", (route.get("symbol") or "").upper().replace("PT-", "")):
        if token in cfg["kyc_refused_tokens"] or token.startswith("SYRUP"):
            return f"KYC token {token}"
    for slug in list(route["platforms"]) + list(route.get("issuers") or []):
        if "identity" in data.failed.get(slug, "").lower() or "kyc" in data.failed.get(slug, "").lower():
            return f"KYC platform {slug}"
    if route.get("tvl", 0) < cfg["floors"]["pool_tvl_usd"]:
        return f"under the $3M floor ({route.get('tvl', 0):,.0f})"
    if q["capacity_usd"] is not None and q["capacity_usd"] < amount:
        return f"lender has only ${route['free']:,.0f} free"
    return None


def outside(data: Data, route: dict) -> list[str]:
    """What this route needs that their list does not pass: empty means it runs on the list as it stands."""
    out = []
    for slug in list(route["platforms"]) + list(route.get("issuers") or []):
        if slug not in data.passed:
            out.append(slug.replace("unlisted:", ""))
    return out


def allowed(cfg: dict, tier: str, route: dict) -> bool:
    fams, fam = cfg["tiers"][tier]["families"], route["family"]
    if fams != ["*"] and fam not in fams and fam != "usd_lend":
        return False
    if tier == "conservative":
        if fam not in ("usd_lend", "usd_lend_main") or route["platforms"][0] not in cfg["conservative_venues"]:
            return False
        if any(word.lower() in route.get("meta", "").lower() for word in cfg["conservative_market_refused"]):
            return False
    return True


def score(data: Data, cfg: dict, routes: list[dict], amount: float, by: str = "rule") -> dict:
    result = {t: {"listed": [], "outside": [], "refused": []} for t in cfg["ladder"]}
    for route in routes:
        for tier in cfg["ladder"]:
            if not allowed(cfg, tier, route):
                continue
            cap = cfg["tiers"][tier]["max_leverage"]
            top = route.get("max_l", 1.0)
            lev = min(top, cap) if cap else top
            q = price(route, lev, amount, data.gas_unit)
            if lev > 1:
                if route.get("borrow") is not None and route["rate"] <= route["borrow"] and route["family"].startswith(("loop", "stack")):
                    continue  # a lever that loses is not a route
                # the best lever under the cap, on the grid: costs can make a lower one pay more
                grid = [1 + i * cfg["lever_step"] for i in range(1, int((lev - 1) / cfg["lever_step"]) + 1)]
                best = max((price(route, x, amount, data.gas_unit) for x in grid), key=lambda z: z["profit"], default=q)
                if best["profit"] > q["profit"]:
                    q, lev = best, best["leverage"]
            q["lasting"] = lasting(data, cfg, route, lev, amount, q)
            if lev > 1 and q["lasting"] is not None:
                grid = [1 + i * cfg["lever_step"] for i in range(1, int((lev - 1) / cfg["lever_step"]) + 1)]
                tried = [(lasting(data, cfg, route, x, amount, price(route, x, amount, data.gas_unit)), x) for x in grid]
                top_last, top_lev = max(tried, key=lambda t: t[0] if t[0] is not None else -1e12)
                if top_last is not None and top_last > q["lasting"]:
                    q["lasting"], q["lasting_leverage"] = top_last, top_lev
            why = refused(data, cfg, route, amount, q)
            row = {**{k: route.get(k) for k in ("id", "name", "family", "platforms", "issuers", "chain", "rate", "borrow", "borrow_week", "tvl", "free", "lltv", "pool", "flags", "meta", "hunter", "source", "symbol")}, **q}
            if why:
                row["why"] = why
                result[tier]["refused"].append(row)
                continue
            miss = outside(data, route)
            if miss:
                row["needs"] = miss
                result[tier]["outside"].append(row)
            else:
                result[tier]["listed"].append(row)
    for tier in result:
        for k in result[tier]:
            result[tier][k].sort(key=lambda r: -(r["profit"] if by == "rule" else r["lasting"] if r.get("lasting") is not None else -1e9))
    return result


def show(rows: list[dict], n: int) -> None:
    for i, r in enumerate(rows[:n], 1):
        needs = f" NEEDS {','.join(r['needs'])}" if r.get("needs") else ""
        cap = f" cap ${r['capacity_usd']:,.0f}" if r.get("capacity_usd") is not None else ""
        last = f"{r['lasting']:>8.2f}" if r.get("lasting") is not None else "       ?"
        print(f"  {i:>2} ${r['profit']:>8.2f} last {last} {r['leverage']:>5.2f}x net {r['net']:>7.2f}% {r['chain'][:10]:<10} {r['family']:<15} {r['name'][:44]:<44} {','.join(r['platforms'])[:18]:<18} tvl {r['tvl'] / 1e6:>7.1f}M{cap}{needs} {'|'.join(f for f in r['flags'] if 'no 7-day' not in f)[:70]}")


def check(data: Data, routes: list[dict]) -> int:
    """Their own routes through our formula. The figure that has to match is theirs, on their rate and leverage."""
    bad = 0
    for tier, d in data.top3.items():
        for r in d["routes"]:
            rate = sum(n.get("rate") or 0 for n in r["nodes"] if n["kind"] in ("stake", "lp", "vault") or (n["kind"] == "supply")) * 100
            bor = sum(n.get("rate") or 0 for n in r["nodes"] if n["kind"] == "borrow") * 100
            lev = r["leverage"]
            route = {"rate": rate, "borrow": bor, "first_bps": 0, "loop_bps": 0, "gas": 0, "chain": "Ethereum"}
            if r["family"] == "split3":
                continue
            net = lev * rate - (lev - 1) * bor
            gross = 5000 * ((1 + net / 100) ** (30 / 365) - 1)
            ours = gross - r["costs"]["total_usd"]
            off = abs(ours - r["profit_month_usd"]) / max(abs(r["profit_month_usd"]), 1)
            flag = "ok " if off <= 0.02 else "OFF"
            bad += off > 0.02
            print(f"  {flag} {tier:<13} {r['name'][:38]:<38} lev {lev:<4} theirs ${r['profit_month_usd']:>8.2f} ours ${ours:>8.2f} (their costs {r['costs']['total_usd']})")
    print(f"  gas unit this minute: ${data.gas_unit:.2f}")
    print("their routes against the same route scored here, our costs:")
    for tier, d in data.top3.items():
        for r in d["routes"]:
            if r["family"] == "split3":
                continue
            lever = r["leverage"]
            node = next((n for n in r["nodes"] if n.get("rate") and n["kind"] in ("stake", "lp", "vault", "supply")), None)
            if not node:
                continue
            match = [x for x in routes if x["platforms"][0] == node["platform"] and abs(x["rate"] - node["rate"] * 100) < 0.02 and x.get("max_l", 1) >= lever]
            if not match and node["kind"] == "stake":
                match = [x for x in routes if x["family"].startswith("loop") and abs(x["rate"] - node["rate"] * 100) < 0.02 and x.get("max_l", 1) >= lever]
            if not match:
                print(f"  ??  {tier:<13} {r['name'][:38]:<38} not found here")
                continue
            q = price(match[0], lever, 5000, data.gas_unit)
            off = abs(q["profit"] - r["profit_month_usd"]) / max(abs(r["profit_month_usd"]), 1)
            bad += off > 0.02
            print(f"  {'ok ' if off <= 0.02 else 'OFF'} {tier:<13} {r['name'][:38]:<38} theirs ${r['profit_month_usd']:>8.2f} (gas {r['costs']['gas_usd']}, swap {r['costs']['swap_usd']}) ours ${q['profit']:>8.2f} (gas {q['gas']}, swap {q['swap']})")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--tier")
    ap.add_argument("--by", choices=("rule", "lasting"), default="rule", help="rank by their rule, or by what lasts")
    a = ap.parse_args()
    cfg = json.loads((HERE / "tiers.json").read_text(encoding="utf-8"))
    data = Data(Path(a.data))
    step = cfg["lever_step"]
    hunted = load_candidates(step)
    gone = {m for c in hunted for f in c["flags"] + [c.get("replaces") or ""] for m in re.findall(r"hold:[0-9a-f-]{36}", f)}
    same = {c["pool"] for c in hunted if c.get("pool") and (c.get("max_l") or 1) <= 1 and not c["family"].startswith(("stack", "lp_levered"))}
    has_pendle = any(c["hunter"] == "pendle" for c in hunted)
    built = hold_routes(data) + morpho_loops(data, step) + aave_loops(data, step) + fluid_loops(data, step) + generic_loops(data, step) + ([] if has_pendle else pendle_holds(data))
    built = [r for r in built if r["id"] not in gone and not (r["id"].startswith("hold:") and r["pool"] in same) and not (has_pendle and r["symbol"].startswith("PT-"))]
    routes = built + hunted
    seen, unique = set(), []
    for r in routes:  # one market listed twice is one route
        key = (r["platforms"][0], r["chain"], r["name"], round(r["rate"], 3), round(r.get("borrow") or 0, 3), r.get("max_l"))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    routes = unique
    overrides = json.loads((HERE / "overrides.json").read_text(encoding="utf-8")) if (HERE / "overrides.json").exists() else []
    for r in routes:  # what a reader established about a route, by its own source, with the reason in overrides.json
        text = f"{r.get('id')} {r.get('name')}"
        for o in overrides:
            if o["match"].lower() in text.lower():
                r["issuers"] = list(r.get("issuers") or []) + o.get("issuers", [])
                for k in ("lasting_rate", "lasting_borrow", "first_bps", "loop_bps", "after_rate"):
                    if k in o:
                        r[k] = o[k]
                r["flags"] = list(r.get("flags") or []) + ([o["note"]] if o.get("note") else [])
    for r in routes:  # after a PT matures its money earns what the token earns, or nothing
        if r.get("matures_days") is None and str(r.get("symbol", "")).startswith("PT-"):
            found = next((re.search(r"matures in (\d+)", x) for x in r["flags"] if "matures in" in x), None)
            r["matures_days"] = int(found.group(1)) if found else None
        if r.get("matures_days") is not None and r.get("after_rate") is None:
            token = re.split(r"[-/ ]", str(r.get("symbol", "")).upper().replace("PT-", ""))[0]
            y = data.token_yield(token)
            r["after_rate"] = rate_of(y) if y else 0
    for r in routes:  # the main market of a big venue, or a Morpho vault lending 90% against majors, is what Conservative may hold
        if r["family"] == "usd_lend":
            morpho_ok = r["platforms"][0] != "morpho-blue" or "majors" in (r.get("meta") or "")
            r["family"] = "usd_lend_main" if r["platforms"][0] in cfg["conservative_venues"] and morpho_ok else "usd_lend"
        elif r["family"] == "usd_vault" and r["platforms"][0] == "morpho-blue" and "USDC" in r.get("symbol", "").upper() and data.books.get((r["chain"].lower(), r.get("symbol", "").upper()), 0) >= 0.9:
            r["family"] = "usd_lend_main"
    print(f"taken {data.taken_at} | {len(routes)} routes | gas unit ${data.gas_unit:.2f} | passed platforms {len(data.passed)}")
    if a.check:
        print("their routes through our formula:")
        check(data, routes)
    res = score(data, cfg, routes, cfg["floors"]["amount_usd"], a.by)
    for tier in ([a.tier] if a.tier else cfg["ladder"]):
        print(f"== {tier}: on their list ({len(res[tier]['listed'])}), needs an addition ({len(res[tier]['outside'])}), refused ({len(res[tier]['refused'])})")
        show(res[tier]["listed"], a.top)
        print("   -- their live top 3:", [(r["name"][:28], r["leverage"], r["profit_month_usd"]) for r in data.top3[tier]["routes"]])
        print("   -- needs an addition:")
        show(res[tier]["outside"], min(a.top, 6))
    if a.json:
        Path(a.json).write_text(json.dumps({"taken_at": data.taken_at, "gas_unit": data.gas_unit, "tiers": res}, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main()
