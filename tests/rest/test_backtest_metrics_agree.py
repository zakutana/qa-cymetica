"""Their Sharpe ratios carry no window, and their two surfaces do not share one.

Cymetica told the operator on 2026-09-11 how an agent should use them: pull the
backtest surfaces first, "rank strategies by Sharpe and max-drawdown, not raw
return", and only then ask NEXUS anything. `list_backtest_surfaces` is their map
of where those numbers live and it names two doors to the same strategies:

    GET /api/v1/backtest/leaderboard   (auth: none) -- the ranking their page shows
    get_strategy_returns(strategy)     "the grounded backtest metrics
                                       (ROI/Sharpe/win-rate/drawdown) for a
                                       strategy concept. Metrics come only from
                                       real backtest_results rows."

Read on 2026-09-12, for one strategy, CryptoBull Bot (Blue):

    leaderboard   sharpe 4.6907   win 0.5366   82 trades   headline_period
                                                           "48h / 354 markets"
    the tool      sharpe 5.1594   win 55.27   275 trades   ran_at 2026-03-15,
                                                           run_id 6a485376-…

Those are not contradictory numbers -- they are different measurements, and the
first reading of this was wrong about that. The defect is what neither of them
says. **The tool's answer carries no window at all**: `ran_at` is when the
backtest ran, not what period it covers, and nothing in the payload distinguishes
a 48-hour run from a six-month one. So an agent doing exactly what their guide
asks -- rank these strategies by Sharpe -- puts 5.1594 beside 4.6907 and cannot
know it is comparing a March backtest of 275 trades with a rolling 48-hour
window of 82.

The same defect is visible on their own page without leaving it: the
leaderboard's rows carry `headline_period` values of 24h, 48h, 72h, 120h and
"6 months", sorted into one list by a Sharpe column. The check reports that
spread as context; what it fails on is the missing window on the tool, because
that is the reading an agent cannot repair for itself.

A strategy the tool has no rows for is not a defect -- their description
promises exactly that note -- and a read that fails on either side skips that
strategy rather than counting as a zero (rule 8).

Two smaller things this check records but does not judge:

  * the leaderboard's slug is rejected by the tool: `cryptobull-blue` answers
    "unknown strategy", and `bt-cryptobull-blue` is what it wants. An agent
    walking their own map between the two doors has to guess the prefix.
  * ten of the fourteen rows on the leaderboard (`bot-*` species) resolve in
    the tool at all, so most of the ranking cannot be cross-read.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LEADERBOARD = "/api/v1/backtest/leaderboard"
TOOL = "get_strategy_returns"

# What would say which period a number covers. Any one of them is enough; the
# claim is that NONE of them is there.
WINDOW_KEYS = ("period", "window", "horizon", "days", "hours", "from", "since",
               "start", "timeframe", "lookback", "interval", "range")


def _unwrap(payload):
    node = payload
    for _ in range(4):
        if isinstance(node, dict) and isinstance(node.get("result"), (dict, str)):
            node = node["result"]
        else:
            break
    return node


def _keys(node, found: set[str]) -> set[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(str(key).lower())
            _keys(value, found)
    elif isinstance(node, list):
        for item in node:
            _keys(item, found)
    return found


def _sharpe(payload) -> float | None:
    found = None

    def walk(node):
        nonlocal found
        if found is not None:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in ("sharpe_ratio", "sharpe") and isinstance(
                        value, (int, float)):
                    found = float(value)
                    return
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


@qa(component="rest.backtest", tier=SafetyTier.SAFE, surface="rest")
def test_a_published_sharpe_says_what_period_it_covers(rest_anon, mcp_anon):
    """Rank by Sharpe, their guide says. A Sharpe with no window cannot be."""
    listed = rest_anon.get(LEADERBOARD)
    if listed.status_code != 200:
        raise Inconclusive(
            f"{LEADERBOARD} answered HTTP {listed.status_code}, so there was no "
            f"ranking to read")
    bots = (listed.json() or {}).get("bots")
    if not isinstance(bots, list) or not bots:
        raise Inconclusive(f"{LEADERBOARD} returned no bots to compare")

    windowless, compared, unknown, unread = [], [], [], []
    periods: dict[str, str] = {}
    for bot in bots:
        if not isinstance(bot, dict):
            continue
        slug = str(bot.get("slug") or "")
        theirs = bot.get("sharpe_ratio")
        if not slug or not isinstance(theirs, (int, float)):
            continue
        periods[slug] = str(bot.get("headline_period") or "unsaid")
        forms = [slug] if slug.startswith("bt-") else [slug, f"bt-{slug}"]
        payload, resolved, failed = None, None, None
        for form in forms:
            try:
                candidate = _unwrap(mcp_anon.call(TOOL, {"strategy": form}))
            except Exception as exc:  # noqa: BLE001
                # Rule 8, and the reason this branch is not `continue` into the
                # same bucket: a call that failed is not a strategy they do not
                # have. Counting one as the other made the population swing
                # from four strategies to one between two runs a minute apart.
                failed = f"{type(exc).__name__}: {str(exc)[:80]}"
                continue
            if _sharpe(candidate) is not None:
                payload, resolved = candidate, form
                break
        if payload is None:
            (unread if failed else unknown).append(
                f"{slug} ({failed})" if failed else slug)
            continue

        compared.append(slug)
        keys = _keys(payload, set())
        says_when = [key for key in keys
                     if any(word in key for word in WINDOW_KEYS)]
        if not says_when:
            windowless.append({
                "strategy": bot.get("name") or slug,
                "slug_the_tool_took": resolved,
                "slug_on_the_leaderboard": slug,
                "tool_sharpe": round(float(_sharpe(payload)), 4),
                "tool_trades": next((v for k, v in _pairs(payload)
                                     if k in ("total_trades", "trades")), None),
                "leaderboard_sharpe": round(float(theirs), 4),
                "leaderboard_trades": bot.get("total_trades"),
                "leaderboard_period": periods[slug],
                "keys_the_tool_returned": sorted(keys)[:14],
            })

    if not compared:
        raise Inconclusive(
            f"no strategy on the leaderboard could be read in {TOOL}: "
            f"{len(unknown)} unknown to it, {len(unread)} failed on the way "
            f"({'; '.join(unread[:3])})")

    spread = sorted({p for p in periods.values() if p != "unsaid"})
    conclude(Measurement(
        verdict="failed" if windowless else "passed",
        reason=(f"{len(windowless)} of {len(compared)} strategies come back from "
                f"{TOOL} with a Sharpe and no period, while the same strategy on "
                f"{LEADERBOARD} carries one -- so ranking them together, which "
                f"your own guide asks an agent to do, compares windows nothing "
                f"names. The leaderboard alone spans {', '.join(spread)}"
                if windowless else
                f"all {len(compared)} answers name the period they cover"),
        left={"windowless": [w["strategy"] for w in windowless]},
        right={"periods_on_the_leaderboard": spread},
        population={"detail": windowless[:6],
                    "not_in_the_tool": unknown[:10],
                    "read_failed": unread[:5],
                    "compared": len(compared)},
        sources={"ranking": LEADERBOARD,
                 "tool": f"POST /mcp/v1 tools/call {TOOL}",
                 "their_guide": "Telegram ET-24713, 2026-09-11"}))


def _pairs(node, prefix=""):
    """Every (key, value) in an answer, flattened, for reading one figure out."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key).lower(), value
            yield from _pairs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _pairs(item)
