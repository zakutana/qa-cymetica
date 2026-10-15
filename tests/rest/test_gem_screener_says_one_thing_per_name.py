"""The Gem Screener says one thing under one name, and its unlock dates agree with themselves.

Found by the degen audit's browser pass of 2026-10-15 (outbox/gem-screener-degen-audit.md, section 4):

1. **A Degen pick is not red on its own Dilution.** The Apps table's SUPPLY column is "Dilution, 12
   months" (new tokens of the next 12 months / circulating supply), red at 25 % or more (ET-31267). The
   Dilution gate a Degen pick passes allows up to 1 % of market cap a week. 2026-10-15: SOLV is a pick
   and reads +32.1 %, red.
2. **The altseason panel names one retail figure.** The Retail tile reads `components.retail.value`
   (retail-v4, 19.7 "asleep"); the "Is the market euphoric?" line reads "retail by dollar volume" from
   `components.retail.euphoria_retail` (47.7), and that is the figure the index uses.
3. **A coin's next cliff lies inside the window its own unlock record counts.** `unlocks.next_cliff`
   within 30 days of the record's `as_of` while `next30_tokens` is 0 says two things at once.
   2026-10-15: KNTQ, a 12.9M cliff on 10-27 against 0 tokens in the 30 days from 10-08; the Supply
   Analyzer puts the same 12.9M on 11-28.
4. **An unlock countdown counts from the moment it is served.** The Supply Analyzer batch the coin
   detail reads states `next_unlock.days` beside `next_unlock.ts`; read at the batch's own `as_of`, the
   two differ by 0.8 days on 17 of 17 rows (SOLV: "Oct 19 · in 5 days" on Oct 15, 3.75 days away).

NOT asserted: which dilution threshold is right, or which retail measure is better. A field that cannot
be read is INCONCLUSIVE, never agreement. SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import re
from datetime import datetime

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import read_page
from tests.rest.test_gem_screener_panels_say_what_their_data_says import read_api

SUPPLY_BATCH = "/api/v1/supply-analyzer/batch/gem-screener"
RED_12M = re.compile(r"red at (\d+(?:\.\d+)?)\s*% or more", re.I)
RETAIL_GAP_POINTS = 10.0     # two readings of one thing this far apart are two things
COUNTDOWN_TOLERANCE_DAYS = 0.5


def _at(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _num(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _batch_items(batch: dict) -> list[dict]:
    items = batch.get("items") or []
    return list(items.values()) if isinstance(items, dict) else list(items)


def _by_identity(items: list[dict]) -> dict:
    """Supply Analyzer rows by slug and by CoinGecko id -- never by ticker (four tickers are two apps)."""
    out = {}
    for item in items:
        token = item.get("token") or {}
        for field in ("slug", "gecko_id"):
            if token.get(field):
                out.setdefault((field, str(token[field]).lower()), item)
    return out


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_degen_pick_is_not_red_on_the_dilution_its_own_row_shows(rest_anon):
    """A pick passes the Dilution gate (1 % of market cap a week at most); the same row's "Dilution, 12
    months" turns red at the threshold the page states. A pick at or over it is red and passed at once."""
    _, text = read_page(rest_anon)
    stated = RED_12M.search(text or "")
    if not stated:
        raise Inconclusive("the page no longer states the 12-month dilution's red line as 'red at N% or more'")
    red = float(stated.group(1))
    snap = read_api(rest_anon, g.SNAPSHOT_API, dated=True)
    by_key = {a.get("key"): a for a in snap.get("apps") or []}
    picks = [by_key[k] for k in (snap.get("degen") or {}).get("shortlist") or [] if k in by_key]
    if not picks:
        raise Inconclusive("the snapshot names no Degen picks")
    sa = _by_identity(_batch_items(read_api(rest_anon, SUPPLY_BATCH)))
    read, red_picks = 0, []
    for app in picks:
        item = (sa.get(("slug", str(app.get("slug") or "").lower()))
                or sa.get(("gecko_id", str(app.get("gecko_id") or "").lower())))
        tile = ((item or {}).get("tiles") or {}).get("dilution_12m") or {}
        pct = _num(tile.get("pct"))
        if pct is None:
            continue
        read += 1
        if pct >= red:
            red_picks.append({"pick": f"{app.get('symbol')}({app.get('key')})", "dilution_12m_pct": pct,
                              "gate_week_pct": _num((app.get("dilution") or {}).get("week_pct"))})
    if not read:
        raise Inconclusive(f"none of the {len(picks)} picks has a 12-month dilution in the Supply Analyzer batch")
    conclude(Measurement(
        verdict="failed" if red_picks else "passed",
        reason=(f"{len(red_picks)} of {len(picks)} Degen picks pass the Dilution gate and read red on the same "
                f"page's 'Dilution, 12 months' (red at {red:g}% or more): "
                + "; ".join(f"{p['pick']} {p['dilution_12m_pct']:g}% over 12 months, gate {p['gate_week_pct']}% a week"
                            for p in red_picks)
                if red_picks else
                f"no Degen pick reads red on its 12-month dilution ({read} of {len(picks)} read, red at {red:g}%)"),
        left={"red_picks": len(red_picks), "read": read},
        right={"red_picks": 0},
        population={"red_picks": red_picks, "red_line_pct": red, "generated_at": snap.get("generated_at")},
        sources={"page": g.APP_PAGE, "api": g.SNAPSHOT_API, "batch": SUPPLY_BATCH}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_altseason_panel_names_one_retail_figure(rest_anon):
    """The Retail tile and the euphoria line's "retail by dollar volume" are both called retail on one
    panel; they read two fields. Two readings more than RETAIL_GAP_POINTS apart are two figures under one name."""
    _, text = read_page(rest_anon)
    if "retail by dollar volume" not in (text or "") or "'Retail'" not in (text or ""):
        raise Inconclusive("the panel no longer labels both a Retail tile and 'retail by dollar volume'")
    alt = read_api(rest_anon, g.ALTSEASON_API)
    retail = (((alt.get("altseason") or {}).get("components") or {}).get("retail")) or {}
    tile, euphoria = _num(retail.get("value")), _num(retail.get("euphoria_retail"))
    if tile is None or euphoria is None:
        raise Inconclusive("components.retail states no value or no euphoria_retail")
    gap = abs(tile - euphoria)
    conclude(Measurement(
        verdict="failed" if gap > RETAIL_GAP_POINTS else "passed",
        reason=(f"the altseason panel shows Retail {tile:g}/100 ({retail.get('verdict')}, {retail.get('version')}) "
                f"on its tile and 'retail by dollar volume {euphoria:g}/100' under euphoria, {gap:.1f} points apart; "
                f"the index's euphoria uses the second"
                if gap > RETAIL_GAP_POINTS else
                f"the two retail readings agree within {RETAIL_GAP_POINTS:g} points ({tile:g} and {euphoria:g})"),
        left={"tile": tile, "euphoria_retail": euphoria, "gap": round(gap, 1)},
        right={"gap_at_most": RETAIL_GAP_POINTS},
        population={"retail": {k: retail.get(k) for k in ("version", "value", "verdict", "euphoria_retail")}},
        sources={"page": g.APP_PAGE, "api": g.ALTSEASON_API}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_next_cliff_lies_inside_the_window_its_own_unlock_record_counts(rest_anon):
    """`unlock.next_cliff.ts` inside 30 (90) days of the record's `as_of` while `next30_tokens`
    (`next90_tokens`) is 0: one record, two answers to when tokens next unlock."""
    snap = read_api(rest_anon, g.SNAPSHOT_API, dated=True)
    checked, breaches = 0, []
    for app in snap.get("apps") or []:
        unlock = app.get("unlock") or {}
        cliff = unlock.get("next_cliff") or {}
        ts, as_of = _num(cliff.get("ts")), _num(unlock.get("as_of"))
        if ts is None or as_of is None:
            continue
        checked += 1
        days = (ts - as_of) / 86400.0
        for window, field in ((30, "next30_tokens"), (90, "next90_tokens")):
            counted = _num(unlock.get(field))
            if 0 <= days <= window and counted == 0:
                breaches.append({"row": f"{app.get('symbol')}({app.get('key')})", "cliff_tokens": cliff.get("tokens"),
                                 "cliff_days_after_as_of": round(days, 1), "window": field, "counted": counted})
                break
    if checked < 5:
        raise Inconclusive(f"only {checked} rows state a next cliff beside their unlock record")
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(f"{len(breaches)} of {checked} rows put their next cliff inside a window their own record counts "
                f"as 0 tokens: " + "; ".join(f"{b['row']} {b['cliff_tokens']:,.0f} tokens {b['cliff_days_after_as_of']} days "
                                            f"after as_of, {b['window']} 0" for b in breaches[:5])
                if breaches else
                f"all {checked} next cliffs fall where their own unlock windows count tokens"),
        left={"rows_contradicting": len(breaches), "checked": checked},
        right={"rows_contradicting": 0},
        population={"breaches": breaches[:10], "generated_at": snap.get("generated_at")},
        sources={"api": g.SNAPSHOT_API}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_an_unlock_countdown_counts_from_the_moment_it_is_served(rest_anon):
    """The batch states `next_unlock.days` beside `next_unlock.ts` and its own `as_of`. The coin detail
    shows the days as "in N days"; read at `as_of` they should be (ts - as_of) / 1 day."""
    batch = read_api(rest_anon, SUPPLY_BATCH)
    served = _at(batch.get("as_of"))
    if served is None:
        raise Inconclusive("the batch states no as_of")
    checked, off = 0, []
    for item in _batch_items(batch):
        nxt = item.get("next_unlock") or {}
        ts, days = _num(nxt.get("ts")), _num(nxt.get("days"))
        if ts is None or days is None:
            continue
        checked += 1
        true_days = (ts - served.timestamp()) / 86400.0
        if true_days > 0 and abs(days - true_days) > COUNTDOWN_TOLERANCE_DAYS:
            token = item.get("token") or {}
            off.append({"row": f"{token.get('symbol')}({token.get('slug')})", "days_stated": days,
                        "days_at_as_of": round(true_days, 2), "refreshed_at": item.get("refreshed_at")})
    if checked < 5:
        raise Inconclusive(f"only {checked} rows state a dated next unlock")
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"{len(off)} of {checked} next unlocks state a countdown more than {COUNTDOWN_TOLERANCE_DAYS:g} days off "
                f"the time to their own date at the batch's as_of {batch.get('as_of')}: "
                + "; ".join(f"{o['row']} {o['days_stated']:g} stated, {o['days_at_as_of']:g} true" for o in off[:5])
                if off else
                f"all {checked} countdowns match their dates at the batch's as_of"),
        left={"rows_off": len(off), "checked": checked},
        right={"rows_off": 0},
        population={"off": off[:10], "as_of": batch.get("as_of")},
        sources={"batch": SUPPLY_BATCH}))
