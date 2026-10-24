"""The /build recipes, walked instead of read.

Four checks already hold /build against the machine-readable documents: that
the paths it names are callable, that the register response documents the field
it tells you to save, that the trust ladder reads the same everywhere. All of
them compare a document with a document.

None of them asks the question the page is actually making a promise about:
**can an agent do what the recipe says?** The recipes are the product -- "one
paste and your agent can register itself, show you your deposit address, trade
the full asset universe, clone funds and bots" -- and the surfaces they point
at, event-cards and backtest, had not one check between them on 2026-09-08.

So each recipe becomes one check per step it names, and the checks stop at the
last read. The recipes end in "place a $25 limit buy" and "fund it with $50, go
live"; those move money and are not ours to perform. Where the walk stops is
recorded in the verdict rather than left implicit, because the last reachable
step is exactly what a report about this needs to say.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

BUILD = "/build"
SEARCH = "/api/v1/event-cards/symbols/search"
LEADERBOARD = "/api/v1/backtest/leaderboard"
FEED = "/api/v1/event-cards"
POSITIONS = "/api/v1/event-cards/positions"
CARD = "/api/v1/event-cards/{card_id}"
HISTORY = "/api/v1/event-cards/{card_id}/index-history"

# How many distinct cards the position check probes. A cap is right on a
# live surface; a cap under the word "every" is not, so the verdict says
# how many were probed whenever it is fewer than we hold.
CARD_PROBE_CAP = 20


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest",
    volatile=True)
def test_the_asset_search_the_recipe_names_finds_a_major_asset(rest_anon):
    """Recipe 1, step 1: "find the asset".

    The recipe tells raw HTTP agents to search
    `GET /api/v1/event-cards/symbols/search?q=<asset>`. A search that answers
    200 with an empty list for the largest asset on earth would be a dead end
    dressed as a success, and the shape of failure a check that only looks at
    status codes cannot see.

    `volatile`: which assets are listed is theirs to change. That BTC resolves
    at all is not a moving target -- the recipe's own example is trading a
    major asset, and a catalogue without one answers nothing.
    """
    response = rest_anon.get(SEARCH, params={"q": "BTC"})
    # A rate limit or a 5xx says nothing about the recipe, and this check used
    # to mint a defect out of one -- "the recipe's first step fails" about a
    # step nothing was established for. The identical repair was already made
    # to test_bounty_tracker.py on 2026-09-07, after one transient filed
    # "answers HTTP 429" against #47, and `volatile=True` does not save it: the
    # marker is recorded and read by neither findings.py nor fold.py, so the
    # failure opens a row like any other. Deep pass, 2026-09-08.
    if response.status_code == 429 or response.status_code >= 500:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the search answered HTTP {response.status_code}, a "
                   f"transient that establishes nothing about the recipe",
            sources={"search": SEARCH, "page": BUILD}))
        return
    if response.status_code != 200:
        conclude(Measurement(
            verdict="failed",
            reason=f"the search a /build recipe names answered HTTP "
                   f"{response.status_code}, so the recipe's first step fails",
            sources={"search": SEARCH, "page": BUILD}))
        return

    results = (response.json() or {}).get("results") or []
    hit = next((r for r in results if str(r.get("symbol", "")).upper() == "BTC"), None)
    priced = hit is not None and hit.get("price_usd") is not None

    conclude(Measurement(
        verdict="passed" if priced else "failed",
        reason=(f"the recipe's search resolves BTC with a price, so step 1 of "
                f"\"find the asset, quote it\" is callable: {len(results)} "
                f"result(s)"
                if priced else
                f"the recipe's search answered 200 with "
                f"{'no BTC row' if hit is None else 'a BTC row carrying no price'}"
                f", so an agent following /build cannot complete \"find the "
                f"asset, quote it\""),
        left=len(results), right="BTC",
        population={"results": len(results)},
        sources={"search": SEARCH, "page": BUILD}))


@qa(component="rest.backtest", tier=SafetyTier.SAFE, surface="rest")
def test_the_leaderboard_can_answer_the_ranking_the_recipe_asks_for(rest_anon):
    """Recipe 2: "show the leaderboard, clone the best 30-day performer".

    For that instruction to be followable, the rows an agent ranks have to be
    comparable. Either every row's headline covers the same period, or the
    endpoint narrows to one. Measured 2026-09-08: neither. Sixteen rows carry
    six different `headline_period` values -- "30 days", "6 months", "24h /
    355 markets", 48h, 72h, 120h -- `?period=30d` is ignored and returns all
    sixteen, and sorting by `headline_return_pct` as any agent would puts a
    SIX-MONTH figure on top.

    So an agent that follows the recipe literally clones a six-month performer
    believing it picked the best over thirty days. The next clause of the same
    sentence is "fund it with $50, go live", which is why this is not cosmetic:
    the incomparable number is the one the funding decision rests on.

    The structure is the claim here, not the values. Which bot leads is theirs
    to change; that the rows cannot be ranked against each other is not.
    """
    response = rest_anon.get(LEADERBOARD)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{LEADERBOARD} answered HTTP {response.status_code}, so "
                   f"the recipe's ranking could not be measured",
            sources={"leaderboard": LEADERBOARD, "page": BUILD}))
        return

    rows = (response.json() or {}).get("bots") or []
    if not rows:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the leaderboard returned no rows, so there is nothing to "
                   "rank and nothing to conclude",
            sources={"leaderboard": LEADERBOARD, "page": BUILD}))
        return

    periods = sorted({str(r.get("headline_period")) for r in rows})
    narrowed = rest_anon.get(LEADERBOARD, params={"period": "30d"})
    if narrowed.status_code != 200:
        # Rule 8, and the reason the old shape was wrong in both directions: a
        # non-200 used to collapse into `filtered = []`, which made `filters`
        # false and emitted "?period=30d does not narrow them" about a request
        # that errored. A failed read is not an empty read.
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the narrowed leaderboard answered HTTP "
                   f"{narrowed.status_code}, so whether the period filter "
                   f"works could not be measured",
            sources={"leaderboard": LEADERBOARD, "page": BUILD}))
        return

    filtered = (narrowed.json() or {}).get("bots") or []
    # Comparability is about the PERIODS the rows carry, not about the count.
    # `0 < len(filtered) < len(rows)` merely says the set shrank -- so eight of
    # sixteen rows still spanning four different headline_period values read as
    # "the period narrows the set" and passed on the violation. Deep pass,
    # 2026-09-08, 3/3.
    filtered_periods = {str(r.get("headline_period")) for r in filtered}
    filters = bool(filtered) and len(filtered_periods) == 1

    ranked = sorted((r for r in rows if r.get("headline_return_pct") is not None),
                    key=lambda r: -r["headline_return_pct"])
    top = ranked[0] if ranked else {}
    comparable = len(periods) == 1 or filters

    conclude(Measurement(
        verdict="passed" if comparable else "failed",
        reason=(f"the leaderboard's rows are rankable: "
                f"{'one period for every row' if len(periods) == 1 else 'the period narrows the set'}"
                if comparable else
                f"a /build recipe says to clone \"the best 30-day performer\", "
                f"but the {len(rows)} leaderboard rows carry {len(periods)} "
                f"different headline_period values and ?period=30d does not "
                f"narrow them, so headline_return_pct is not comparable across "
                f"rows: the top row by return is "
                f"{top.get('name')!r} at {top.get('headline_return_pct')}% over "
                f"{top.get('headline_period')!r}, not over thirty days"),
        left=periods, right=["one comparable period, or a period filter"],
        population={"rows": len(rows), "periods": len(periods),
                    "rows_with_30_days": sum(1 for r in rows
                                             if r.get("headline_period") == "30 days")},
        sources={"leaderboard": LEADERBOARD, "page": BUILD}))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_the_event_card_feed_carries_headlines_an_agent_can_match(rest_trusted):
    """Recipe 3, step 1: "watch the event-card feed; when a headline matches
    my thesis, alert me or place the pre-approved order."

    Matching a headline needs a headline. A feed that answers 200 with cards
    carrying scores about a headline and not the headline itself would leave
    the recipe's only decision -- does this match my thesis -- unmakeable, and
    every card does publish two headline SCORES, which is exactly the shape
    that could pass a shallower check.

    The count is held against the rows in the same breath, because this
    repository has filed that reconciliation four times on other surfaces.
    """
    response = rest_trusted.get(FEED)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="failed",
            reason=f"the event-card feed a /build recipe tells an agent to "
                   f"watch answered HTTP {response.status_code}",
            sources={"feed": FEED, "page": BUILD}))
        return

    body = response.json() or {}
    cards = body.get("cards") or []
    titled = [c for c in cards if str(c.get("title") or "").strip()]
    counted = body.get("count")
    # `count` is a stated total and `len(cards)` is a window: the endpoint
    # documents `limit`, defaulting to 50, and returns exactly 50 today. So a
    # disagreement is a PAGE, not a missing headline, and failing on it would
    # have told the vendor "an agent told to match a headline cannot" about
    # titles that are all present -- report #52 went out for that exact
    # conflation. And `counted is None` passing vacuously means a feed that
    # stops publishing the field is never noticed. Both halves: deep pass,
    # 2026-09-08, 2/3.
    if counted is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the feed returned {len(cards)} card(s) and published no "
                   f"`count`, so the reconciliation this check claims to make "
                   f"could not be made",
            population={"cards": len(cards), "titled": len(titled)},
            sources={"feed": FEED, "page": BUILD}))
        return
    if counted != len(cards):
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the feed states {counted} card(s) and returned "
                   f"{len(cards)}, which is a page rather than a headline "
                   f"defect; {len(titled)} of the returned rows carry a title",
            population={"cards": len(cards), "titled": len(titled),
                        "count_field": counted},
            sources={"feed": FEED, "page": BUILD}))
        return
    agrees = True

    conclude(Measurement(
        verdict="passed" if cards and len(titled) == len(cards) and agrees
        else "failed",
        reason=(f"every one of the {len(cards)} cards in the feed carries a "
                f"title an agent can match a thesis against, and count agrees "
                f"with the rows returned"
                if cards and len(titled) == len(cards) and agrees else
                f"the feed returned {len(cards)} card(s), {len(titled)} with a "
                f"title, and count says {counted}: an agent told to match a "
                f"headline cannot"),
        left=len(titled), right=len(cards),
        population={"cards": len(cards), "titled": len(titled),
                    "count_field": counted},
        sources={"feed": FEED, "page": BUILD}))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_in_the_feed_resolves_and_publishes_its_index_history(rest_trusted):
    """Recipe 3, steps 2 and 3: read the card, then decide from its history.

    Walked forward from the feed rather than from an id typed in here, so the
    check cannot outlive the card it was written against -- the failure mode
    that retires a check the day the platform rotates its data.
    """
    feed = rest_trusted.get(FEED)
    cards = (feed.json() or {}).get("cards") or [] if feed.status_code == 200 else []
    if not cards:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the feed returned no card to walk forward from "
                   f"(HTTP {feed.status_code})",
            sources={"feed": FEED}))
        return

    card_id = cards[0].get("id") or cards[0].get("card_id")
    detail = rest_trusted.get(CARD.format(card_id=card_id))
    history = rest_trusted.get(HISTORY.format(card_id=card_id))
    points = ((history.json() or {}).get("points") or []
              if history.status_code == 200 else [])

    walked = detail.status_code == 200 and history.status_code == 200 and points
    conclude(Measurement(
        verdict="passed" if walked else "failed",
        reason=(f"a card taken from the feed resolves and publishes "
                f"{len(points)} index point(s), so the monitor recipe can read "
                f"a card and decide from its history"
                if walked else
                f"walking the monitor recipe forward from the feed stops: "
                f"card detail HTTP {detail.status_code}, index-history HTTP "
                f"{history.status_code}, {len(points)} point(s)"),
        left=card_id, right=len(points),
        population={"points": len(points)},
        sources={"feed": FEED, "card": CARD, "history": HISTORY}))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_every_card_we_hold_a_position_in_still_resolves(rest_trusted):
    """A position pointing at a card that has stopped existing.

    Not a recipe step -- a consequence of one. The recipes end in holding
    something, and `/positions` is where an agent reads what it holds. A
    position whose card_id 404s is a row an agent cannot price, close or
    explain, and nothing else here would notice: the position endpoint answers
    200 with the stale row in it.

    OPEN POSITIONS ONLY (2026-10-25). PRE-0274 failed this on a closed position
    whose card had since been deleted. A closed row has nothing left to price or
    close, llms.txt documents the route as "Your open card positions", and each
    row carries `status` (33 open, 90 closed that day). So only rows whose
    status reads "open" are judged; closed rows are counted, and a row whose
    status does not read is named and not judged (rule 8). A card read that
    raises is unread, not unresolved.
    """
    response = rest_trusted.get(POSITIONS)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{POSITIONS} answered HTTP {response.status_code}, so what "
                   f"we hold could not be read",
            sources={"positions": POSITIONS}))
        return

    every = (response.json() or {}).get("positions") or []
    positions = [p for p in every if isinstance(p, dict) and p.get("status") == "open"]
    closed = sum(1 for p in every if isinstance(p, dict) and p.get("status") == "closed")
    no_status = [str(p.get("position_id") or p.get("card_id")) for p in every
                 if not isinstance(p, dict) or p.get("status") not in ("open", "closed")]
    if not positions:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"we hold no OPEN event-card position ({len(every)} row(s): "
                    f"{closed} closed, {len(no_status)} with no readable status), so "
                    f"there is no card to resolve and this establishes nothing"),
            population={"positions": len(every), "open": 0, "closed": closed,
                        "status_unread": no_status[:20]},
            sources={"positions": POSITIONS}))
        return

    # Distinct ids only, and capped: this is a live surface and the point is
    # whether the reference holds, not how many times we can ask.
    #
    # The cap and the word "every" cannot both stand. Today's 39 positions hold
    # 19 distinct cards so the truncation does not bite, but the 21st distinct
    # card can 404 under a sentence claiming all of them resolve -- and account
    # growth, not a vendor change, is what reaches it. So the population says
    # how many were probed, and the verdict says "the N we probed" whenever
    # that is fewer than we hold. Deep pass, 2026-09-08, 2/3.
    distinct = list(dict.fromkeys(p.get("card_id") for p in positions))
    probed = distinct[:CARD_PROBE_CAP]
    unresolved, unread = [], {}
    for card_id in probed:
        try:
            status = rest_trusted.get(CARD.format(card_id=card_id)).status_code
        except Exception as exc:  # noqa: BLE001 -- a failed read is not a 404
            unread[card_id] = type(exc).__name__
            continue
        if status != 200:
            unresolved.append(card_id)
    complete = len(probed) == len(distinct)
    if not unresolved and len(unread) > len(probed) // 4:
        # A pass may not rest on the cards that happened to answer: more than a
        # quarter unread is a hole in the sample, not a sample.
        raise Inconclusive(f"{len(unread)} of the {len(probed)} cards of our open positions "
                           f"could not be read ({sorted(set(unread.values()))})")

    conclude(Measurement(
        verdict="passed" if not unresolved else "failed",
        reason=((f"every card we hold an open position in resolves"
                 if complete else
                 f"the {len(probed)} most recent of our {len(distinct)} "
                 f"distinct open-position cards resolve; the rest were not probed")
                + (f" ({len(unread)} could not be read: {', '.join(sorted(unread))})"
                   if unread else "")
                if not unresolved else
                f"{len(unresolved)} card(s) we hold an OPEN position in no longer "
                f"resolve, so those rows cannot be priced or closed from the "
                f"API: {', '.join(unresolved)}")
               + f". Closed positions are not judged ({closed} of {len(every)} rows)",
        left=sorted(unresolved), right=[],
        population={"positions": len(every), "open": len(positions), "closed": closed,
                    "status_unread": no_status[:20], "distinct_cards": len(distinct),
                    "cards_probed": len(probed), "cards_unread": unread},
        sources={"positions": POSITIONS, "card": CARD}))
