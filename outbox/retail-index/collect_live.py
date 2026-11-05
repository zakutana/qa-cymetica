"""Collect the two live social rows that have no history: YouTube views and the US App Store chart.

    python -I outbox/retail-index/collect_live.py

Neither source gives a backfill (YouTube's public RSS lists the last 15 videos of a channel; Apple's chart is today's), so
this only starts the record. One line per run is appended to `state/retail_index/live.jsonl`; a row joins a back-test
only after 52 weeks of lines exist, so nothing here can move the v6 numbers. Anonymous GETs through
`build_source_client`; a source that does not answer is named in the line, never filled. Channels are the two whose id was
checked by hand on 2026-11-05: add the rest of Kryptomagazin's list to CHANNELS as their ids are checked.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from qa.client import build_source_client  # noqa: E402
from qa.paths import state_dir  # noqa: E402
from qa.safety import CURRENT_TIER, SafetyTier  # noqa: E402

CHANNELS = {"Coin Bureau": "UCqK_GSMbpiV8spgD3ZGloSw", "Benjamin Cowen": "UCRvqjQPSeaWn-uEx-w0XOIg"}
APPS = {"886427730": "Coinbase", "6741115427": "fomo", "1598432977": "Phantom", "6503993131": "Moonshot",
        "1492670702": "Binance.US", "1262148500": "Crypto.com", "1481947260": "Kraken", "1278383455": "Coinbase Wallet",
        "1288339409": "Trust", "6717572591": "pump.fun", "938003185": "Robinhood"}
CHART = "https://itunes.apple.com/us/rss/topfreeapplications/limit=100/{genre}json"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={id}"
UA = {"User-Agent": "qa-cymetica-retail-index/1.0 (https://github.com/zakutana/qa-cymetica; public research read, GET only)"}


def youtube(client, errors):
    out = {}
    for name, cid in CHANNELS.items():
        try:
            r = client.get(FEED.format(id=cid), headers=UA)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            views = [int(v) for v in re.findall(r'views="(\d+)"', r.text)]
            if not views:
                raise ValueError("no videos in the feed")
            out[name] = {"videos": len(views), "median_views": statistics.median(views)}
        except Exception as exc:  # noqa: BLE001 - named in the line
            errors[f"youtube {name}"] = f"{type(exc).__name__}: {str(exc)[:80]}"
    return out


def appstore(client, errors):
    ranks: dict[str, dict] = {}
    for key, genre in (("overall", ""), ("finance", "genre=6015/")):
        try:
            r = client.get(CHART.format(genre=genre), headers=UA)
            entries = ((r.json() if r.status_code == 200 else {}).get("feed") or {}).get("entry") or []
            if len(entries) < 50:   # a chart that did not come back is not "no crypto app in the top 100"
                raise ValueError(f"HTTP {r.status_code}, {len(entries)} entries")
            for i, e in enumerate(entries, 1):
                ranks.setdefault(e["id"]["attributes"]["im:id"], {})[key] = i
        except Exception as exc:  # noqa: BLE001
            errors[f"appstore {key}"] = f"{type(exc).__name__}: {str(exc)[:80]}"
            return {}
    return {name: [ranks.get(a, {}).get("overall"), ranks.get(a, {}).get("finance")] for a, name in APPS.items()}


def main():
    client = build_source_client(timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    errors: dict[str, str] = {}
    try:
        line = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "youtube": youtube(client, errors),
                "appstore_overall_finance": appstore(client, errors), "not_read": errors}
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    path = state_dir() / "retail_index" / "live.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")
    print(f"live line written: youtube {sorted(line['youtube'])}, app store {'yes' if line['appstore_overall_finance'] else 'no'}; not read: {sorted(errors) or 'nothing'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
