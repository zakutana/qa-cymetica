"""The panels beside the rank say what their own data says (2026-10-02).

Three independent audits of the Altseason panel, the Retail panel and the Sectors
tab found their numbers faithful to the sources (weekly closes, category revenue,
BTC.D, OTHERS, the retail rows) and four places where the page says two things at
once. Each is held here as a rule the page itself publishes, so any redesign has to
keep it true:

1. **A theme is priced on one date.** `theme_prices.live` holds a live point per
   coin. A theme whose weight is covered only in part carries the live move of the
   coins that had one and the weekly close of the rest. On 2026-10-02 (snapshot
   1790921065) CoinGecko answered 403 and 429, 11 of 320 coins had a live point,
   RWA (1 of 12) and DePIN (1 of 15) showed +111.6 % and +96.3 % over a month
   where weekly closes alone give about +56 % and +45 %, and the page said nothing.
   A healthy snapshot passes; this row is a watch for the next partial fetch.

2. **"Hot" means one thing.** The table and "Hot right now" read `stage == 'hot'`
   (4 themes that day); the theme panel prints "This theme is hot." from the older
   `hot` flag (8), so DeFi and Privacy were hot in the panel and Fading in the table.

3. **"Only BTC runs" is not said over a week most alts beat BTC.** The panel prints
   the phase word beside the share of the top 50 that beat BTC. On 2026-10-02: 17 of
   154 such weeks had at least 60 % -- 2024-12-02 at 74 %, with OTHERS up from
   $198bn to $397bn in four weeks.

4. **"How sure" follows its own tooltip.** "Sure: 5+ rows that agree within 30
   points." Five of six rows sat between 4 and 14; the panel said unsure, because
   the code took the spread of all six (84).

NOT asserted: how Cymetica fixes any of them, whether the Altseason words or the
Retail measure are good ones (the audits' improvements are goals for the next
Build it Better request, not findings), or that the other words at turning points
are wrong -- only the one that contradicts the number printed beside it.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import time

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import (
    MAX_SNAPSHOT_AGE_H,
    get_patiently,
    read_page,
    read_snapshot,
)


def read_api(rest_anon, path: str, *, dated: bool = False) -> dict:
    """A JSON endpoint of the Gem Screener, or Inconclusive: a read that failed, a
    body that is not JSON, or (for the snapshot itself) one too old to say anything."""
    try:
        response = get_patiently(rest_anon, path)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{path} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{path} answered HTTP {response.status_code}; a failed read is not an empty body")
    try:
        body = response.json()
    except ValueError:
        raise Inconclusive(f"{path} did not answer JSON")
    if not isinstance(body, dict):
        raise Inconclusive(f"{path} answered a {type(body).__name__}, not an object")
    if dated:
        age = g.age_hours(body, time.time())
        if age is None or age > MAX_SNAPSHOT_AGE_H:
            raise Inconclusive(f"the snapshot is {age if age is None else round(age, 1)} h old; past "
                               f"{MAX_SNAPSHOT_AGE_H:.0f} h a comparison measures drift")
    return body


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_theme_is_priced_on_one_date(rest_anon):
    """Every theme's live leg covers all its members, none of them, or at least 95 %
    of its weight. Anything else is a basket priced on two dates."""
    api = read_api(rest_anon, g.SNAPSHOT_API, dated=True)
    said = g.theme_live_coverage(api)
    if not said["themes"]:
        raise Inconclusive("no theme could be read: " + "; ".join(said["unread"][:3]))
    live = (api.get("theme_prices") or {}).get("live") or {}
    coins = (api.get("theme_prices") or {}).get("coins") or {}
    warnings = [{"source": w.get("source"), "http_status": w.get("http_status")}
                for w in api.get("fetch_warnings") or []
                if "theme_prices.live" in (w.get("affected") or [])]
    partial = said["partial"]
    conclude(Measurement(
        verdict="failed" if partial else "passed",
        reason=(f"{len(partial)} of {len(said['themes'])} themes are priced on two dates "
                f"({'; '.join(f'{t['theme']} {t['with_live']} of {t['members']} members live' for t in partial[:6])}); "
                f"{len(live)} of {len(coins)} coins have a live point"
                + (f"; fetch_warnings: {warnings}" if warnings else "; no fetch warning names theme_prices.live")
                if partial else
                f"all {len(said['themes'])} themes are priced on one date ({len(live)} of {len(coins)} coins live)"),
        left={"themes_partial": len(partial), "themes_read": len(said["themes"]),
              "live_coins": len(live), "coins": len(coins)},
        right={"themes_partial": 0},
        population={"partial": partial, "warnings": warnings, "snapshot_generated_at": api.get("generated_at")},
        sources={"api": g.SNAPSHOT_API}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_hot_means_one_thing_on_the_sectors_tab(rest_anon):
    """The set of themes the table calls hot (`stage`) is the set the theme panel
    calls hot (`hot`)."""
    snap = read_snapshot(rest_anon)
    said = g.hot_definitions(snap)
    if said["unread"]:
        raise Inconclusive("; ".join(said["unread"]))
    disagree = said["disagree"]
    conclude(Measurement(
        verdict="failed" if disagree else "passed",
        reason=(f"the table calls {len(said['stage_hot'])} themes hot ({', '.join(said['stage_hot'])}) and "
                f"the theme panel {len(said['flag_hot'])} ({', '.join(said['flag_hot'])}); they differ on "
                f"{', '.join(disagree)}"
                if disagree else
                f"both definitions of hot name the same {len(said['stage_hot'])} themes"),
        left={"themes_that_differ": len(disagree), "stage_hot": len(said["stage_hot"]),
              "flag_hot": len(said["flag_hot"])},
        right={"themes_that_differ": 0},
        population={"disagree": disagree, "stage_hot": said["stage_hot"], "flag_hot": said["flag_hot"]},
        sources={"page": g.APP_PAGE}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_only_btc_runs_is_not_said_over_a_week_most_alts_beat_btc(rest_anon):
    """No week carries the phase "btc_only" ("Only BTC runs") while the breadth
    printed for it is 60 % or more."""
    alt = read_api(rest_anon, g.ALTSEASON_API)
    said = g.phase_word_breaches(alt)
    if said["unread"] or said["weeks_read"] < 100:
        raise Inconclusive("the weekly phase and breadth could not be read: "
                           + ("; ".join(said["unread"]) or f"only {said['weeks_read']} weeks"))
    if not said["only_btc_weeks"]:
        # Deep pass 2026-10-02 (T04): the phase code is read by name. A history with no such
        # week is either a fix that reclassified all of them or a renamed code, and the page
        # may still print "Only BTC runs" -- a pass here would verify a fix that never happened.
        raise Inconclusive(f"none of the {said['weeks_read']} weeks carries the phase 'btc_only': "
                           f"the code may have been renamed, so no week can be judged")
    breaches = said["breaches"]
    latest = max(breaches, key=lambda b: b["week"]) if breaches else None
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(f"{len(breaches)} of {said['only_btc_weeks']} weeks worded 'Only BTC runs' have a breadth "
                f"of {g.ALTS_MAJORITY:g} % or more (highest {max(b['breadth'] for b in breaches):g} %, "
                f"latest week {time.strftime('%Y-%m-%d', time.gmtime(latest['week']))})"
                if breaches else
                f"none of the {said['only_btc_weeks']} weeks worded 'Only BTC runs' has a breadth of "
                f"{g.ALTS_MAJORITY:g} % or more"),
        left={"weeks_that_contradict": len(breaches), "only_btc_weeks": said["only_btc_weeks"]},
        right={"weeks_that_contradict": 0},
        population={"breaches": breaches[-12:], "weeks_read": said["weeks_read"]},
        sources={"api": g.ALTSEASON_API}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_how_sure_follows_its_own_tooltip(rest_anon):
    """The panel's 'How sure' word is the one its tooltip's rule gives for the six
    retail scores it shows."""
    snap, text = read_page(rest_anon)
    said = g.retail_sure_breach(snap, text)
    if said["unread"]:
        raise Inconclusive("; ".join(said["unread"]))
    breach = said["breach"]
    conclude(Measurement(
        verdict="failed" if breach else "passed",
        reason=(f"the tooltip rule (sure = {breach['rule']['sure'][0]}+ rows within {breach['rule']['sure'][1]} "
                f"points, fairly sure = {breach['rule']['fairly'][0]}+ within {breach['rule']['fairly'][1]}) gives "
                f"'{breach['expected']}' for the scores {breach['scores']}; the panel says '{breach['shown']}'"
                if breach else
                "the 'How sure' word is the one the tooltip's rule gives for the scores shown"),
        left={"shown": breach["shown"] if breach else None},
        right={"expected": breach["expected"] if breach else None},
        population={"breach": breach},
        sources={"page": g.APP_PAGE}))
