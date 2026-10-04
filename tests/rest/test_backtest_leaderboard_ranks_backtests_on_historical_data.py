"""The backtest leaderboard ranks bots on trades against historical data, as the page says (2026-10-04).

/backtest describes itself as "Backtest your AI trading strategies against historical data on
EventTrader" (its meta description) and llms.txt lists it as "Clone-able bot backtests and
leaderboard". GET /api/v1/backtest/leaderboard ranks 16 bots; the first is Multi-Indicator
Ensemble, "+61.2%" over "6 months", `data_sources` polymarket, kalshi, eventtrader.

Seen on 2026-10-04 (a read-only survey of every species, then this check): the ten `bot-*`
rows rest on 1,521 trades, and every one of them carries `is_synthetic: true` on
/api/v1/backtest/bots/{slug}/trades. Their prices are not the assets': every entry lies between
90.00 and 110.00 whatever the symbol, BTC at 92.56 (Trend Following SMA, 2026-04-07), TSLA,
AAPL and ETH the same. Neither the leaderboard row nor the bot profile says the run is
synthetic, and the page's trade table marks a row "LABS/SYNTHETIC" only when it has no times
and no prices, so these rows are drawn as trades.

ASSERTS: no bot on the leaderboard is ranked on trades that its own trade list marks
`is_synthetic`, while /backtest says its backtests run against historical data. Either side
of the fix passes: trades on the assets' historical prices, or a page and leaderboard that
say the run is synthetic (the check reads the page's sentence each time).

NOT asserted: whether a backtest's headline return follows from its trade list (their
endpoint describes the two as possibly different), or any strategy's merit.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LEADERBOARD = "/api/v1/backtest/leaderboard"
TRADES = "/api/v1/backtest/bots/{slug}/trades"
PAGE = "/backtest"
CLAIM = "backtest-leaderboard-ranks-historical-trades"
HISTORICAL = "against historical data"
PAGE_SIZE = 200
MIN_READ_SHARE = 0.8


def _trades(rest_anon, slug: str) -> list[dict] | None:
    rows, offset = [], 0
    while True:
        r = rest_anon.get(TRADES.format(slug=slug), params={"limit": PAGE_SIZE, "offset": offset})
        if r.status_code != 200:
            return None
        body = r.json()
        page = body.get("trades") if isinstance(body, dict) else None
        if not isinstance(page, list):
            return None
        rows += [t for t in page if isinstance(t, dict)]
        total = body.get("total")
        offset += PAGE_SIZE
        if not page or not isinstance(total, int) or offset >= total:
            return rows


@qa(component="rest.backtest", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_leaderboard_ranks_no_bot_on_synthetic_trades(rest_anon):
    """Every leaderboard bot's trade list, against the page's own description."""
    page = rest_anon.get(PAGE, headers={"Accept": "text/html"})
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    says_historical = HISTORICAL in page.text
    synthetic_word = "synthetic" in page.text.lower()
    board = rest_anon.get(LEADERBOARD, params={"limit": 50})
    if board.status_code != 200 or not isinstance(board.json(), dict):
        raise Inconclusive(f"{LEADERBOARD} answered HTTP {board.status_code}")
    bots = [b for b in board.json().get("bots") or [] if isinstance(b, dict) and b.get("slug")]
    if not bots:
        raise Inconclusive(f"{LEADERBOARD} lists no bot")
    read, unread, ranked_on_synthetic = [], [], []
    for b in bots:
        trades = _trades(rest_anon, b["slug"])
        if trades is None:
            unread.append(b["slug"])
            continue
        synth = [t for t in trades if t.get("is_synthetic") is True]
        prices = [float(t["entry_price"]) for t in synth
                  if isinstance(t.get("entry_price"), (int, float, str)) and str(t["entry_price"]).strip()]
        btc = [t for t in synth if t.get("symbol") == "BTC"]
        row = {"slug": b["slug"], "rank": len(read) + len(unread), "headline_return_pct": b.get("headline_return_pct"),
               "headline_period": b.get("headline_period"), "data_sources": b.get("data_sources"),
               "trades": len(trades), "synthetic": len(synth),
               "entry_price_range": [min(prices), max(prices)] if prices else None,
               "btc_example": ({k: btc[0].get(k) for k in ("entry_time", "entry_price", "exit_price")}
                               if btc else None),
               "leaderboard_says_synthetic": "synthetic" in str(b).lower()}
        read.append(row)
        if synth and says_historical and not row["leaderboard_says_synthetic"]:
            ranked_on_synthetic.append(row)
    if len(read) < MIN_READ_SHARE * len(bots):
        raise Inconclusive(f"only {len(read)} of {len(bots)} trade lists could be read: {unread[:5]}")
    total_synth = sum(r["synthetic"] for r in ranked_on_synthetic)
    total_trades = sum(r["trades"] for r in ranked_on_synthetic)
    conclude(Measurement(
        verdict="failed" if ranked_on_synthetic else "passed",
        reason=(f"{len(ranked_on_synthetic)} of {len(read)} leaderboard bots are ranked on trades their own trade "
                f"list marks is_synthetic ({total_synth} of their {total_trades} trades), while {PAGE} says "
                f"\"{HISTORICAL}\" and no leaderboard row says synthetic: "
                + "; ".join(f"{r['slug']} {r['headline_return_pct']}% over {r['headline_period']}, "
                            f"{r['synthetic']}/{r['trades']} synthetic, entry prices "
                            f"{r['entry_price_range'][0]:g}-{r['entry_price_range'][1]:g}"
                            + (f", BTC entered at {r['btc_example']['entry_price']}" if r["btc_example"] else "")
                            for r in ranked_on_synthetic[:4])
                if ranked_on_synthetic else
                f"none of {len(read)} leaderboard bots is ranked on synthetic trades under a page that says "
                f"\"{HISTORICAL}\" (page says it: {says_historical})"),
        left={"bots_ranked_on_synthetic_trades": len(ranked_on_synthetic)},
        right={"bots_ranked_on_synthetic_trades": 0},
        population={"ranked_on_synthetic": ranked_on_synthetic, "read": len(read), "unread": unread,
                    "page_says_historical": says_historical, "page_mentions_synthetic": synthetic_word},
        sources={"page": PAGE, "leaderboard": LEADERBOARD, "trades": TRADES},
        claim_id=CLAIM))
