"""A paper bot's trade record says what happened (2026-10-04).

The operator, looking at the laboratory's experiments table (paper clones up 10 % to
33 % within 13 to 48 minutes): did the bots really earn, can their trades be verified,
is it fake or a bug? Verified that evening over every trade of our paper clones still
listed (scratchpad notes of the session; the numbers below are from those reads):

* every trade is a 5-minute up/down bet on BTC or ETH at a fixed stake (5 % of the
  bot's balance) paying +100 % or -100 % of the stake, no fee; +33 % on Bollinger
  Bandit 1b81dff7 is 8 right calls of 10, not a market move (BTC fell ~0.2 % over the
  window). Balance = funding + the sum of the trades, to the cent, on all nine Wave 0
  clones and Stat Oracle 3d5d0bff; take-profit and stop-loss paused each bot at the
  first crossing of its own settings; a second read returned identical rows;
* their prices are market prices: within 0.002 % of Binance spot where the exit was
  taken at the epoch's end; the three ZK arena legs exited at 0.01299, Binance's
  price at their close 48 h later.

Four things are not what the record says; one check each.

1. SETTLED ON THE EPOCH'S PRICE. Each bet names its epoch (`epoch_start`, `epoch_end`)
   and, when settled normally, `resolution_path: epoch_close`. Seen: `price_at_exit`
   is often the market price of the second the bet was closed (`closed_at`), 13 to 54 s
   after `epoch_end` -- ETH epoch 5967592 (2026-09-24) ended 19:25:00 at 2694.62 on Binance
   and was settled at 2697.01, Binance's price at 19:25:53, its `closed_at` -- and
   once a price from before the end (BTC epoch 5967591: 84557.30, Binance's price
   19:19:36-45, against 84615.22 at 19:20:00). Taking each bet's own entry and the price
   at its epoch's end, 9 bets on 3 epoch/asset pairs pay the opposite result.
   ASSERTS: every settled bet's `price_at_exit` is within 0.01 % of Binance spot at its
   `epoch_end` (the close of the epoch's last second). Binance is the reference, not
   their source: where their exits were on time they sat within 0.002 % of it.

2. A DELETED BOT ANSWERS 404. llms.txt: a deleted bot "is listed only with
   ?include_inactive=true; its balance and activity answer 404". Seen: its
   /asset-analytics answers 500 INTERNAL_SERVER_ERROR (all 12 of ours, e.g. 36642175).
   ASSERTS: no deleted clone of ours answers /asset-analytics with a 5xx.

3. HOW A BET ENDED. A bet held to its epoch's end was not exited by a stop. Seen:
   the bet whose settlement crossed the bot's take-profit or stop-loss carries
   `exit_reason` take_profit / stop_loss (and `resolution_path` null) although it was
   closed at the epoch's end at the same price as the epoch's other bets
   (`epoch_resolved`, `epoch_close`): MACD Hunter 31d18d91, BTC epoch 5970199, closed
   20:40:05, exit 84863.35, labelled stop_loss. ASSERTS: no bet closed at or after its
   epoch's end carries take_profit or stop_loss as its exit reason.

4. WHAT A CLONE TRADES. /cloned-bots/available describes each species by its
   indicators ("Exploits volatility expansions and contractions using Bollinger Bands"),
   and llms.txt says "Cloned bot species are price-series indicator strategies". The
   platform's own `live_decision_source` on our clones says they decide on another
   bot's rule, `differs_from_display: true`: Bollinger Bandit and ATR Alpha on STAT
   ("Epoch-number parity heuristic"), Trend Titan and Ichimoku Empress on SYNC
   ("Deterministic epoch-parity alternation (even epoch=YES, odd=NO)"), and the others
   on DELTA, CORR or FADE. Their clone page states it after cloning; the list one
   chooses from does not. ASSERTS: no clone of ours whose decision source differs from
   its display belongs to a species whose description names one of its indicators.

The population is our own clones and the bets they settled. Settled rows did not change
between two reads; new rows appear only when a bot of ours trades, so a later run reads
a superset. A check on our own bots is a sample of what every clone does.

NOT asserted: whether any strategy predicts anything; the flat 1:1 paper payout (the
live market shares a pool; undocumented for paper, a question, not a defect); which
price source they use.

SAFE: GETs only. Their endpoints with our key; Binance's public klines through
`build_source_client`.
"""

from __future__ import annotations

import httpx

from qa import clonetrades as ct
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/cloned-bots"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
PAIRS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
MIN_JUDGED_SHARE = 0.8

CLAIM_SETTLE = "paper-bot-bet-settles-at-epoch-end"
CLAIM_DELETED = "deleted-bot-asset-analytics-answers-404"
CLAIM_EXIT_REASON = "paper-bot-bet-exit-reason-is-how-it-ended"
CLAIM_DECIDES = "cloned-species-trades-its-described-strategy"
LLMS_SENTENCE = "Cloned bot species are price-series indicator strategies"


def _clones(rest_trusted, inactive: bool = False) -> list[dict]:
    params = {"mode": "paper"}
    if inactive:
        params["include_inactive"] = "true"
    r = rest_trusted.get(f"{PREFIX}/my-clones", params=params)
    if r.status_code != 200 or not isinstance(r.json(), list):
        raise Inconclusive(f"my-clones answered HTTP {r.status_code}")
    return [c for c in r.json() if isinstance(c, dict)]


def _activity(rest_trusted, bot_id: str) -> list[dict] | None:
    """Every row of one bot's feed, all pages; None when a page fails."""
    rows, page = [], 1
    while True:
        r = rest_trusted.get(f"{PREFIX}/{bot_id}/activity", params={"page": page, "page_size": 100})
        if r.status_code != 200:
            return None
        body = r.json()
        rows += [t for t in body.get("items") or [] if isinstance(t, dict)]
        if not body.get("has_more") or page >= int(body.get("total_pages") or 1):
            return rows
        page += 1


def _all_bets(rest_trusted) -> tuple[list[dict], list[str]]:
    bets, unread = [], []
    for c in _clones(rest_trusted):
        if not c.get("trades_executed"):
            continue
        rows = _activity(rest_trusted, c["id"])
        if rows is None:
            unread.append(c["id"])
            continue
        for b in ct.epoch_bets(rows):
            b["bot"], b["bot_name"] = c["id"], c.get("source_name")
            bets.append(b)
    return bets, unread


def _references(bets: list[dict], evidence_store) -> dict:
    """(symbol, second) -> Binance close of that second, for every epoch end and close."""
    windows: dict = {}
    for b in bets:
        if b["symbol"] not in PAIRS:
            continue
        key = (b["symbol"], b["epoch_end_s"])
        windows[key] = max(windows.get(key, 0), b["closed_s"])
    prices: dict = {}
    source = build_source_client(evidence=evidence_store, timeout=60.0)
    try:
        for (symbol, end), last in sorted(windows.items()):
            start = end - 1
            limit = min(1000, max(2, last - start + 2))
            try:
                r = source.get(BINANCE, params={"symbol": PAIRS[symbol], "interval": "1s",
                                                "startTime": start * 1000, "limit": limit})
                rows = r.json() if r.status_code == 200 else []
            except (httpx.HTTPError, ValueError):
                rows = []
            for k in rows if isinstance(rows, list) else []:
                try:
                    prices[(symbol, int(k[0]) // 1000)] = float(k[4])
                except (TypeError, ValueError, IndexError):
                    continue
    finally:
        source.close()
    return prices


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_SETTLE)
def test_a_settled_bet_is_paid_on_the_price_at_its_epoch_end(rest_trusted, evidence_store):
    """Every settled 5-minute bet of our paper clones: its exit price against
    Binance spot at its epoch's end."""
    bets, unread = _all_bets(rest_trusted)
    if not bets:
        raise Inconclusive(f"no settled 5-minute bet on our paper clones ({len(unread)} feeds unread)")
    prices = _references(bets, evidence_store)
    readings = []
    for b in bets:
        r = ct.settlement_reading(b, prices.get((b["symbol"], b["epoch_end_s"] - 1)),
                                  prices.get((b["symbol"], b["closed_s"])))
        if r:
            r["bot"], r["bot_name"] = b["bot"], b["bot_name"]
            readings.append(r)
    if len(readings) < MIN_JUDGED_SHARE * len(bets):
        raise Inconclusive(f"only {len(readings)} of {len(bets)} bets could be priced on Binance")
    s = ct.judge_settlement(readings)
    off, flipped = s["off_end"], s["flipped"]
    pairs = sorted({(r["symbol"], r["epoch_id"]) for r in flipped})
    off_pairs = {(r["symbol"], r["epoch_id"]) for r in off}
    worst, seen = [], set()
    for r in sorted(off, key=lambda r: (not r["at_closed"], -abs(r["off_end_pct"]))):
        if (r["symbol"], r["epoch_id"]) not in seen:
            seen.add((r["symbol"], r["epoch_id"]))
            worst.append(r)
    worst = worst[:4]
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(
            f"{len(off)} of {s['judged']} settled bets ({len(off_pairs)} epoch/asset pairs) were paid on an "
            f"exit price more than {100 * ct.TOLERANCE:g}% from Binance at their epoch's end; "
            f"{len(s['at_closed'])} of them "
            f"equal Binance at the second the bet was closed (closed_at, "
            f"{min((r['late_s'] for r in s['at_closed']), default=0)}-"
            f"{max((r['late_s'] for r in s['at_closed']), default=0)} s after epoch_end). "
            + "; ".join(f"{r['symbol']} epoch {r['epoch_id']}: exit {r['exit']:g} against "
                        f"{r['ref_end']:g} at {r['epoch_end'][11:19]}, closed {r['closed_at'][11:19]}"
                        for r in worst)
            + f". With each bet's own entry and the epoch-end price, {len(flipped)} bets on "
              f"{len(pairs)} epoch/asset pairs pay the opposite result ("
            + ", ".join(f"{sym} {ep}" for sym, ep in pairs) + ")"
            if off else
            f"all {s['judged']} settled bets were paid within {s['max_ok_off_pct']}% of Binance at their epoch's end"),
        left={"exits_off_epoch_end": len(off), "results_reversed": len(flipped)},
        right={"exits_off_epoch_end": 0},
        population={"off_end": off, "flipped": flipped, "judged": s["judged"], "bets": len(bets),
                    "unread_feeds": unread, "max_ok_off_pct": s["max_ok_off_pct"]},
        sources={"activity": f"{PREFIX}/{{id}}/activity", "binance": BINANCE},
        claim_id=CLAIM_SETTLE))


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_DELETED)
def test_a_deleted_bot_answers_asset_analytics_like_its_activity(rest_trusted):
    """Every deleted paper clone of ours: /activity (documented 404) and /asset-analytics."""
    deleted = [c for c in _clones(rest_trusted, inactive=True) if c.get("status") == "deleted"]
    if not deleted:
        raise Inconclusive("no deleted paper clone of ours is listed with include_inactive=true")
    rows = []
    for c in deleted:
        act = rest_trusted.get(f"{PREFIX}/{c['id']}/activity")
        ana = rest_trusted.get(f"{PREFIX}/{c['id']}/asset-analytics")
        body = ana.text[:200] if ana.status_code >= 500 else None
        rows.append({"id": c["id"], "deleted_at": c.get("deleted_at"), "activity": act.status_code,
                     "asset_analytics": ana.status_code, "analytics_body": body})
    errors = [r for r in rows if r["asset_analytics"] >= 500]
    conclude(Measurement(
        verdict="failed" if errors else "passed",
        reason=(f"{len(errors)} of {len(rows)} deleted paper clones answer GET {PREFIX}/{{id}}/asset-analytics "
                f"with HTTP {sorted({r['asset_analytics'] for r in errors})} while their /activity answers "
                f"{sorted({r['activity'] for r in errors})}: "
                + ", ".join(r["id"][:8] for r in errors[:6])
                if errors else
                f"all {len(rows)} deleted paper clones answer /asset-analytics without a server error"),
        left={"server_errors": len(errors)},
        right={"server_errors": 0},
        population={"deleted": rows},
        claim_id=CLAIM_DELETED))


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_EXIT_REASON)
def test_a_bet_held_to_its_epoch_end_is_not_labelled_as_stopped(rest_trusted):
    """Every settled 5-minute bet of our paper clones: a take_profit or stop_loss
    exit reason on a bet closed at or after its epoch's end."""
    bets, unread = _all_bets(rest_trusted)
    if not bets:
        raise Inconclusive(f"no settled 5-minute bet on our paper clones ({len(unread)} feeds unread)")
    flagged = ct.pause_reason_on_full_term(bets)
    twins = {(b["symbol"], b["epoch_id"], b["exit"]) for b in bets if b.get("exit_reason") == "epoch_resolved"}
    shown = [{"bot": b["bot"], "bot_name": b["bot_name"], "symbol": b["symbol"], "epoch_id": b["epoch_id"],
              "exit_reason": b["exit_reason"], "resolution_path": b["resolution_path"],
              "epoch_end": b["epoch_end"], "closed_at": b["closed_at"], "exit": b["exit"],
              "same_exit_as_an_epoch_resolved_bet": (b["symbol"], b["epoch_id"], b["exit"]) in twins}
             for b in flagged]
    conclude(Measurement(
        verdict="failed" if flagged else "passed",
        reason=(f"{len(flagged)} of {len(bets)} settled bets closed at or after their epoch's end carry "
                f"exit_reason take_profit/stop_loss; {sum(x['same_exit_as_an_epoch_resolved_bet'] for x in shown)} "
                f"of them have the same exit price as a bet of the same epoch labelled epoch_resolved: "
                + "; ".join(f"{x['bot_name']} {x['symbol']} epoch {x['epoch_id']} {x['exit_reason']}, "
                            f"closed {x['closed_at'][11:19]} after end {x['epoch_end'][11:19]}" for x in shown[:4])
                if flagged else
                f"none of {len(bets)} settled bets held to their epoch's end is labelled as stopped"),
        left={"labelled_stopped": len(flagged)},
        right={"labelled_stopped": 0},
        population={"flagged": shown, "bets": len(bets), "unread_feeds": unread},
        claim_id=CLAIM_EXIT_REASON))


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_DECIDES)
def test_a_clone_decides_on_the_strategy_its_species_is_described_by(rest_trusted, rest_anon):
    """Our paper clones' live_decision_source against their species' description."""
    clones = _clones(rest_trusted)
    r = rest_trusted.get(f"{PREFIX}/available")
    if r.status_code != 200 or not isinstance(r.json(), dict):
        raise Inconclusive(f"{PREFIX}/available answered HTTP {r.status_code}")
    species = {}
    for group in ("wta_species", "perpetual_agents"):
        for s in r.json().get(group) or []:
            if isinstance(s, dict) and s.get("id"):
                species[s["id"]] = s
    read = [c for c in clones if isinstance(c.get("live_decision_source"), dict)]
    if not read:
        raise Inconclusive("no clone of ours carries a live_decision_source to read")
    # A contradiction is a description naming one of the species' own primary indicators.
    # If no species carries a readable primary_indicators any more, nothing can be found,
    # and "nothing found" would read as every clone deciding as described (deep pass
    # 2026-10-08, T04, 3/3).
    if not any(ct._indicator_words(s) for s in species.values()):
        raise Inconclusive(f"no species in {PREFIX}/available carries readable "
                           f"primary_indicators, so no description can be held against them")
    llms = rest_anon.get("/llms.txt")
    llms_says = llms.status_code == 200 and LLMS_SENTENCE in llms.text
    found = ct.decision_source_contradictions(clones, species)
    judged = ct.decision_source_reads(clones, species)
    # A differing clone whose species has no readable indicators is unread, not clean (B06).
    unread = ct.decision_source_unread(clones, species)
    if not found and judged == 0:
        # A renamed flag, or species ids that no longer join, judges nothing: not a clean read.
        raise Inconclusive(f"{len(read)} clones carry a decision source, but none carries "
                           f"differs_from_display as true/false beside a species it joins in {PREFIX}/available")
    if ct.decision_verdict(found, judged, unread) == "inconclusive":
        # B06 (deep pass 2026-10-11): the differing clones unread, the rest clean, is no pass.
        raise Inconclusive(f"{len(unread)} clone(s) that differ from their display belong to species "
                           f"with no readable primary_indicators: {unread[:6]}; the rest reading clean "
                           f"says nothing of them")
    by_species = {}
    for f in found:
        by_species.setdefault(f["species"], f)
    conclude(Measurement(
        verdict="failed" if found else "passed",
        reason=(f"{len(by_species)} species' clones decide on another rule than the indicators their "
                f"description names (live_decision_source.differs_from_display true): "
                + "; ".join(f"{f['species']} (\"{f['description'][:70]}\") decides on {f['strategy_symbol']} "
                            f"\"{f['decides_on']}\"" for f in list(by_species.values())[:5])
                + (f"; llms.txt says \"{LLMS_SENTENCE}\"" if llms_says else "")
                if found else
                f"all {judged} clones with a decision source decide on what their species is described by"
                + (f"; {len(unread)} differing clone(s) of a species with no readable primary_indicators "
                   f"were not judged" if unread else "")),
        left={"species_contradicted": len(by_species)},
        right={"species_contradicted": 0},
        population={"contradictions": list(by_species.values()), "clones_read": len(read), "unread": unread,
                    "llms_sentence_present": llms_says},
        sources={"clones": f"{PREFIX}/my-clones?mode=paper", "species": f"{PREFIX}/available", "llms": "/llms.txt"},
        claim_id=CLAIM_DECIDES))
