"""Read the public sources for retail index v5 and write the compact weekly table.

    python -I outbox/retail-index/fetch.py [--refresh]

Anonymous GETs of public APIs through `build_source_client` (the guard, no credential, no write). Raw answers are cached
under `cache/` (not in git; `--refresh` reads them again), the weekly table is `data/weekly.csv` and what was read, when,
and its hash is `data/sources.json`. A source that does not answer is named there and its columns stay empty: an empty
column is never read as agreement. Rules: RESULT.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from qa import retailindex as R  # noqa: E402
from qa.client import build_client, build_source_client  # noqa: E402
from qa.config import identities  # noqa: E402
from qa.paths import atomic_write  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

CACHE = HERE / "cache"
DATA = HERE / "data"
FIRST_WEEK = R.ordinal("2015-08-03")
BINANCE = "https://data-api.binance.vision/api/v3"
FAPI = "https://fapi.binance.com/fapi/v1"
CM = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
COINBASE = "https://api.exchange.coinbase.com/products/{pair}/candles"
UPBIT = "https://api.upbit.com/v1/candles/weeks"
FX = "https://api.frankfurter.dev/v1/{a}..{b}"
FNG = "https://api.alternative.me/fng/?limit=0&format=json"
CYMETICA = "/api/v1/gem-screener/altseason"
UA = {"User-Agent": "qa-cymetica-retail-index/1.0"}
STABLE = {"USDC", "TUSD", "BUSD", "FDUSD", "USDP", "DAI", "USDD", "EUR", "GBP", "TRY", "BRL", "AEUR", "USD1", "PYUSD",
          "USDE", "XUSD", "RLUSD", "BFUSD", "UST", "USDS", "EURI", "ZAR", "UAH", "PLN", "RON", "ARS", "JPY", "MXN",
          "COP", "CZK"}
NOT_ALT = {"BTC", "WBTC", "WBETH", "BETH", "WBNB", "BNSOL", "WEETH", "RETH", "LBTC", "CBBTC", "SOLV"}
COINBASE_FIRST = {"BTC-USD": R.ordinal("2015-07-20"), "ETH-USD": R.ordinal("2016-05-18")}


class SourceError(Exception):
    pass


def get_json(client, url, params=None, headers=None, tries=4):
    last = "no answer"
    for i in range(tries):
        try:
            r = client.get(url, params=params, headers={**UA, **(headers or {})})
        except Exception as exc:  # noqa: BLE001 - named in sources.json, never swallowed
            last = type(exc).__name__
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                raise SourceError(f"{url}: a body that is not JSON")
        last = f"HTTP {r.status_code}"
        if r.status_code in (418, 429, 500, 502, 503, 504):
            time.sleep(3 * (i + 1))
            continue
        break
    raise SourceError(f"{url}: {last}")


class Reader:
    def __init__(self, client, refresh):
        self.client, self.refresh = client, refresh
        self.log: dict[str, dict] = {}

    def cached(self, name, fn):
        path = CACHE / f"{name}.json"
        if path.exists() and not self.refresh:
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = fn()
            atomic_write(path, json.dumps(data))
        raw = path.read_bytes()
        self.log[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        return data


def iso_z(day: int, end=False) -> str:
    return R.iso(day) + ("T23:59:59Z" if end else "T00:00:00Z")


# ---- one function per source: the raw JSON, paged ---------------------------------------------

def read_coinmetrics(c):
    rows, url, params = [], CM, {"assets": "btc,eth", "metrics": "AdrActCnt,CapMrktCurUSD,PriceUSD", "frequency": "1d",
                                 "start_time": "2015-07-01", "page_size": 10000}
    for _ in range(30):
        d = get_json(c, url, params=params)
        rows.extend(d.get("data") or [])
        url, params = d.get("next_page_url"), None
        if not url:
            return rows
    raise SourceError("Coin Metrics: more than 30 pages")


def read_coinbase(c, pair, last_day):
    rows, t1 = [], last_day
    first = COINBASE_FIRST[pair]
    while t1 >= first:
        t0 = max(first, t1 - 299)
        part = get_json(c, COINBASE.format(pair=pair), params={"granularity": 86400, "start": iso_z(t0), "end": iso_z(t1, True)})
        if not isinstance(part, list):
            raise SourceError(f"Coinbase {pair}: {part}")
        rows.extend(part)
        t1 = t0 - 1
        time.sleep(0.2)
    return rows


def read_binance_weeks(c, symbol):
    return get_json(c, f"{BINANCE}/klines", params={"symbol": symbol, "interval": "1w", "startTime": 1500000000000, "limit": 1000})


def read_alt_symbols(c, n=100):
    tick = get_json(c, f"{BINANCE}/ticker/24hr")
    out = []
    for t in tick:
        s = t.get("symbol", "")
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if base in STABLE or base in NOT_ALT or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        out.append((float(t.get("quoteVolume") or 0), s))
    out.sort(reverse=True)
    return [s for _, s in out[:n]]


def read_upbit(c, market, last_monday):
    rows, to = [], None
    for _ in range(8):
        params = {"market": market, "count": 200}
        if to:
            params["to"] = to
        part = get_json(c, UPBIT, params=params)
        if not part:
            break
        rows.extend(part)
        oldest = min(x["candle_date_time_utc"] for x in part)
        if len(part) < 200:
            break
        to = oldest + "Z"
        time.sleep(0.15)
    return rows


def read_funding(c, symbol):
    rows, start = [], int(datetime(2019, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    while True:
        part = get_json(c, f"{FAPI}/fundingRate", params={"symbol": symbol, "startTime": start, "limit": 1000})
        rows.extend(part)
        if len(part) < 1000:
            return rows
        start = int(part[-1]["fundingTime"]) + 1
        time.sleep(0.2)


def read_fx(c, last_day):
    out = {}
    for year in range(2015, R.date.fromordinal(last_day).year + 1):
        a, b = f"{year}-01-01", f"{year}-12-31"
        d = get_json(c, FX.format(a=a, b=b), params={"base": "USD", "symbols": "KRW"})
        out.update(d.get("rates") or {})
    return out


def read_cymetica(client):
    d = get_json(client, CYMETICA)["altseason"]
    return {"weeks": d["weeks"], "v4": d["series"]["retail"], "v3": d["series"]["retail_euphoria"],
            "others": d["series"]["others_usd"]}


# ---- the weekly table -------------------------------------------------------------------------

def build_table(raw: dict, weeks: list[int], last_day: int) -> tuple[dict, dict]:
    n = len(weeks)
    col = {k: [None] * n for k in ("cb_turn", "up_turn", "bn_turn", "users_btc", "users_eth", "kimchi", "cb_prem",
                                    "fund", "breadth", "froth", "alt_level", "alt_n", "btc", "fng", "cy_v4", "cy_v3", "cy_others")}
    first_day = FIRST_WEEK - 400

    cm = R.parse_coinmetrics(raw.get("cm"))
    cap = {a: cm.get(a, {}).get("CapMrktCurUSD", {}) for a in ("btc", "eth")}
    price = cm.get("btc", {}).get("PriceUSD", {})
    cb = {p: R.parse_coinbase_candles(raw.get(f"cb_{p}")) for p in ("BTC-USD", "ETH-USD")}
    bn = {s: R.parse_binance_weeks(raw.get(f"bn_{s}")) for s in ("BTCUSDT", "ETHUSDT")}
    up = {m: R.parse_upbit_weeks(raw.get(f"up_{m}")) for m in ("KRW-BTC", "KRW-ETH")}
    fx = R.fill_forward(R.parse_fx(raw.get("fx") or {}), first_day, last_day)
    fund = [R.parse_funding(raw.get(f"fund_{s}")) for s in ("BTCUSDT", "ETHUSDT")]
    fng = R.parse_fng((raw.get("fng") or {}).get("data"))
    pair_of = {"btc": ("BTC-USD", "BTCUSDT", "KRW-BTC"), "eth": ("ETH-USD", "ETHUSDT", "KRW-ETH")}

    def turnover(vol_of):
        out = []
        for i, W in enumerate(weeks):
            num = den = 0.0
            for a in ("btc", "eth"):
                v, k = vol_of(a, W), R.week_last(cap[a], W)
                if v is not None and k:
                    num, den = num + v, den + k
            out.append(num / den if den else None)
        return out

    cb_vol = {p: {d: x[1] for d, x in rows.items()} for p, rows in cb.items()}
    col["cb_turn"] = turnover(lambda a, W: R.week_sum(cb_vol[pair_of[a][0]], W))
    col["bn_turn"] = turnover(lambda a, W: (bn[pair_of[a][1]].get(W - 7) or (None, None))[1])

    def up_usd(a, W):
        v = (up[pair_of[a][2]].get(W - 7) or (None, None))[1]
        rate = R.week_mean(fx, W, min_days=1)
        return v / rate if v is not None and rate else None

    col["up_turn"] = turnover(up_usd)
    for i, W in enumerate(weeks):
        for a in ("btc", "eth"):
            col[f"users_{a}"][i] = R.week_mean(cm.get(a, {}).get("AdrActCnt", {}), W)
        col["btc"][i] = R.week_last(price, W)
        col["fng"][i] = R.week_last(fng, W)
        bnb, upb = bn["BTCUSDT"].get(W - 7), up["KRW-BTC"].get(W - 7)
        rate = R.week_last(fx, W)
        if bnb and upb and rate:
            col["kimchi"][i] = upb[0] / (bnb[0] * rate) - 1
        cbc = cb["BTC-USD"].get(W - 1)
        if bnb and cbc:
            col["cb_prem"][i] = (cbc[0] - bnb[0]) / bnb[0]
        fv = [R.week_mean(f, W) for f in fund]
        fv = [v for v in fv if v is not None]
        col["fund"][i] = sum(fv) / len(fv) if fv else None

    alts = {s: R.parse_binance_weeks(raw.get(f"alt_{s}")) for s in raw.get("alt_symbols") or []}
    btc_w = bn["BTCUSDT"]
    level = None
    for i, W in enumerate(weeks):
        k = W - 7
        b13 = (btc_w.get(k) or (None,))[0], (btc_w.get(k - 91) or (None,))[0]
        rets13, froth, rets1 = [], [], []
        for s, wk in alts.items():
            now = (wk.get(k) or (None,))[0]
            if now is None or (wk.get(k - 28) or (None,))[0] is None:
                continue
            p4 = wk[k - 28][0]
            froth.append(now / p4 - 1 >= 0.5)
            p1 = (wk.get(k - 7) or (None,))[0]
            if p1:
                rets1.append(now / p1 - 1)
            p13 = (wk.get(k - 91) or (None,))[0]
            if p13 and b13[0] and b13[1]:
                rets13.append(now / p13 - 1 > b13[0] / b13[1] - 1)
        col["alt_n"][i] = len(froth)
        if len(froth) >= 15:
            col["froth"][i] = 100.0 * sum(froth) / len(froth)
        if len(rets13) >= 15:
            col["breadth"][i] = 100.0 * sum(rets13) / len(rets13)
        if len(rets1) >= 5:
            level = (level if level is not None else 100.0) * (1 + sum(rets1) / len(rets1))
            col["alt_level"][i] = level

    cy = raw.get("cy") or {}
    by_week = {R.ordinal_of_epoch(w): i for i, w in enumerate(cy.get("weeks") or [])}
    for i, W in enumerate(weeks):
        j = by_week.get(W)
        if j is not None:
            col["cy_v4"][i] = (cy["v4"] or [None] * (j + 1))[j]
            col["cy_v3"][i] = (cy["v3"] or [None] * (j + 1))[j]
            col["cy_others"][i] = (cy.get("others") or [None] * (j + 1))[j]
    return col, {"alts_used": len(alts)}


def write_table(weeks, col):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    names = list(col)
    w.writerow(["week"] + names)
    for i, W in enumerate(weeks):
        w.writerow([R.iso(W)] + ["" if col[k][i] is None else f"{col[k][i]:.8g}" for k in names])
    atomic_write(DATA / "weekly.csv", out.getvalue())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true", help="read the sources again instead of the cache")
    args = ap.parse_args(argv)

    today = datetime.now(timezone.utc).date().toordinal()
    last_monday = R.monday_on_or_before(today)
    last_day = last_monday - 1
    weeks = R.week_grid(FIRST_WEEK, last_monday)

    source = build_source_client(timeout=90.0)
    cymetica = build_client(identities()["anon"], EndpointRegistry.load(), timeout=90.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    rd = Reader(source, args.refresh)
    raw: dict = {}
    errors: dict[str, str] = {}

    def take(name, fn, key=None):
        try:
            raw[key or name] = rd.cached(name, fn)
        except Exception as exc:  # noqa: BLE001
            errors[name] = f"{type(exc).__name__}: {str(exc)[:160]}"
            print("NOT READ", name, errors[name], flush=True)

    try:
        take("cm", lambda: read_coinmetrics(source))
        for pair in COINBASE_FIRST:
            take(f"cb_{pair}", lambda p=pair: read_coinbase(source, p, last_day))
        for s in ("BTCUSDT", "ETHUSDT"):
            take(f"bn_{s}", lambda s=s: read_binance_weeks(source, s))
        for m in ("KRW-BTC", "KRW-ETH"):
            take(f"up_{m}", lambda m=m: read_upbit(source, m, last_monday))
        take("fx", lambda: read_fx(source, last_day))
        for s in ("BTCUSDT", "ETHUSDT"):
            take(f"fund_{s}", lambda s=s: read_funding(source, s))
        take("fng", lambda: get_json(source, FNG))
        take("alt_symbols", lambda: read_alt_symbols(source))
        for s in raw.get("alt_symbols") or []:
            take(f"alt_{s}", lambda s=s: read_binance_weeks(source, s))
        CURRENT_TIER.reset(token)
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        take("cy", lambda: read_cymetica(cymetica))
    finally:
        CURRENT_TIER.reset(token)
        source.close()
        cymetica.close()

    col, extra = build_table(raw, weeks, last_day)
    write_table(weeks, col)
    first_last = {k: (R.iso(weeks[next(i for i, v in enumerate(col[k]) if v is not None)]),
                      R.iso(weeks[max(i for i, v in enumerate(col[k]) if v is not None)]),
                      sum(v is not None for v in col[k]))
                  for k in col if any(v is not None for v in col[k])}
    sources = {"as_of": R.iso(today), "last_week": R.iso(last_monday), "rows": len(weeks), **extra,
               "not_read": errors, "columns": {k: {"first": a, "last": b, "weeks": n} for k, (a, b, n) in first_last.items()},
               "empty_columns": [k for k in col if not any(v is not None for v in col[k])],
               "raw": rd.log}
    atomic_write(DATA / "sources.json", json.dumps(sources, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(weeks)} weeks to {DATA / 'weekly.csv'}; not read: {sorted(errors) or 'nothing'}; "
          f"empty: {sources['empty_columns'] or 'none'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
