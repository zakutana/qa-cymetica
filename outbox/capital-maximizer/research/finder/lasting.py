"""What a rate does over a month, for the routes near the top: DefiLlama's own daily chart of apyBase. GET only.

    python -I outbox/capital-maximizer/research/finder/lasting.py <data-dir> [--top 60]

Their rule takes the lowest of today, the 7-day and the 30-day mean, and a mean keeps a spike: WETH-USDT 0.3% read a 49.97 mean
in the row while 25 of its last 30 days were below that. score.py uses the median from here for its second figure, "lasting".
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def chart(pool: str) -> dict | None:
    req = urllib.request.Request(f"https://yields.llama.fi/chart/{pool}", headers={"User-Agent": "curl/8"})
    for wait in (0, 20, 60, 120):  # DefiLlama answers 429 past a few reads a second
        time.sleep(wait)
        try:
            rows = json.load(urllib.request.urlopen(req, timeout=60)).get("data") or []
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or wait == 120:
                raise
    days =[r["apyBase"] for r in rows[-30:] if r.get("apyBase") is not None]
    if not days:
        return None
    return {"median": statistics.median(days), "mean": statistics.fmean(days), "today": days[-1], "days": len(days)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--top", type=int, default=60)
    a = ap.parse_args()
    folder = Path(a.data)
    tiers = json.loads((folder / "scored.json").read_text(encoding="utf-8"))["tiers"]
    pools = set()
    for t in tiers.values():
        for side in ("listed", "outside"):
            for r in t[side][:a.top]:
                p = r.get("pool") or ""
                if len(p) == 36 and p.count("-") == 4:  # a DefiLlama pool id: a PT address has no such chart and its rate is fixed
                    pools.add(p)
    out_file = folder / "lasting.json"
    out = json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else {}
    todo = sorted(pools - set(out))

    def one(p):
        try:
            return p, chart(p)
        except Exception as exc:  # noqa: BLE001 a failed read stays out; the route keeps only the figure by their rule
            print("failed", p, repr(exc)[:100])
            return p, None

    with cf.ThreadPoolExecutor(2) as ex:
        for p, got in ex.map(one, todo):
            if got:
                out[p] = got
    out_file.write_text(json.dumps(out), encoding="utf-8")
    print(f"{len(pools)} pools near the top, {len(todo)} read now, {len(out)} held")


if __name__ == "__main__":
    main()
