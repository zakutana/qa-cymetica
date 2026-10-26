"""Read today's live data for the Promo Market v2 mockup into snap/ (git-ignored).

Our own account (expire76) with our key, the same reads the live dashboard makes. Nothing here writes: GETs only.
make_data.py turns snap/ into data.js; only what the live page shows is kept.
"""
import json
import os
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from qa.config import load_dotenv  # noqa: E402

SNAP = HERE / "snap"
BASE = "https://cymetica.com"
READS = {
    "promo_mine": "/api/v1/promo/mine",
    "promo_briefs": "/api/v1/promo/briefs",
    "promo_house": "/api/v1/promo/house",
    "promo_how_counted": "/api/v1/promo/how-counted",
    "promo_payouts": "/api/v1/promo/payouts",
    "links": "/api/v1/creator/expire76/links",
    "reddit_leads": "/api/v1/creator/reddit-leads?limit=60",
    "twitter_leads": "/api/v1/creator/twitter-leads?limit=60",
    "journalists": "/api/v1/creator/journalist-requests?limit=40",
    "post_kit": "/api/v1/creator/post-kit",
    "rewards": "/api/v1/creator/rewards",
    "channel_posts": "/api/v1/creator/channel-posts",
    "posts": "/api/v1/creator/posts",
    "bib_requests": "/api/v1/build-it-better/requests",
    "bib_leaderboard": "/api/v1/build-it-better/apps/leaderboard?sort=views",
}


def main():
    load_dotenv()
    key = os.environ["QA_TRUSTED_KEY"]
    SNAP.mkdir(exist_ok=True)
    with httpx.Client(base_url=BASE, headers={"X-API-Key": key, "User-Agent": "qa-cymetica promo-market-v2 snapshot"},
                      timeout=60, follow_redirects=True) as c:
        for name, path in READS.items():
            r = c.get(path)
            ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json")
            if ok:
                (SNAP / f"{name}.json").write_text(json.dumps(r.json(), indent=1, ensure_ascii=False), encoding="utf-8")
            body = r.json() if ok else None
            keys = list(body)[:8] if isinstance(body, dict) else (f"list[{len(body)}]" if isinstance(body, list) else "")
            print(f"{r.status_code} {name:22} {len(r.content):>8} B  {keys}")


if __name__ == "__main__":
    main()
