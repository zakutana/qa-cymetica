"""/movers ranks the event cards it says it ranks, not the first page of them (2026-10-11).

/movers ("Top Movers -- EventTrader products") says: "What is hot on EventTrader right now,
products only: event cards, index funds and platform tokens ranked by move and by activity",
under the headings "Biggest gainers" and "Biggest losers". llms.txt lists it as "Biggest
gainers, losers and most active across EventTrader's own products". The boards are drawn in
the browser by the page's own script, from two reads: `/api/v1/event-cards/?limit=100` and
`/api/v1/exchange/markets`. A card's move is `current_index / index_base - 1` (the script's
own formula).

**What was seen when this was written** (2026-10-10 22:00 UTC, again 2026-10-11 11:20 UTC):
the listing's `total` is 641, the endpoint refuses `limit=500` with 422, and the script asks
for one page of 100, in an order that is neither by move nor by date. So the boards rank 100
of 641 cards: the page's biggest loser was SAIB: TTD -19.17% while SAIB: CTVA -83.92% was
the biggest of all, and none of the ten biggest losers and three of the ten biggest gainers
over all 641 cards were among the cards the page reads.

**The rule.** Every card that is among the ten biggest gainers or the ten biggest losers over
the whole default listing is among the cards the page's script reads. Any fix passes: a page
that reads every page of the listing, a server-side order by move, a dedicated endpoint the
script calls instead (then the check is re-pointed: a page that stops reading the listing
is Inconclusive, never passed).

NOT asserted: the "Event cards leading the deck" board (it falls back to the size of the move
when no card has activity, by its own sort), the token rows, or whether "since listing" is
the right window.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import html as _html
import re
import time
from urllib.parse import parse_qsl, urlsplit

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PAGE = "/movers"
LISTING = "/api/v1/event-cards/"
CLAIM = "movers-page-ranks-every-event-card"
BOARD_ANCHOR = "pm-gainers"
PAGE_SIZE = 100
TOP = 10
PAUSE_S = 1.0
MAX_PAGES = 30

_FETCH = re.compile(r"fetch\(\s*(['\"`])(/api/v1/event-cards/?[^'\"`]*)\1(\s*\+)?")


def board_script(page_html: str) -> str | None:
    """The page script that writes the boards: anchored on the board's element id."""
    for m in re.finditer(r"<script[^>]*>(.*?)</script>", page_html or "", flags=re.S):
        if BOARD_ANCHOR in m.group(1):
            return m.group(1)
    return None


def card_requests(script: str | None) -> tuple[list[str], bool]:
    """(the event-card URLs the script fetches, whether it pages through the listing). A URL
    built by concatenation, or a script that sends an offset with it, pages."""
    urls, pages = [], False
    for m in _FETCH.finditer(script or ""):
        url = _html.unescape(m.group(2))
        urls.append(url)
        if m.group(3) or url.endswith("=") or "offset" in url:
            pages = True
    return urls, pages


def move(card) -> float | None:
    """The page's own move of a card: current_index / index_base - 1, in %."""
    try:
        base, cur = float(card.get("index_base") or 0), float(card.get("current_index") or 0)
    except (TypeError, ValueError):
        return None
    return (cur / base - 1) * 100 if base > 0 and cur > 0 else None


def boards(cards) -> dict[str, list[dict]]:
    """The ten biggest gainers and losers by the page's rule."""
    rows = [{"id": c.get("id"), "title": (c.get("title") or c.get("strategy_name") or "")[:60], "move": move(c)}
            for c in cards if isinstance(c, dict)]
    rows = [r for r in rows if r["move"] is not None and r["id"]]
    return {"gainers": sorted((r for r in rows if r["move"] > 0), key=lambda r: -r["move"])[:TOP],
            "losers": sorted((r for r in rows if r["move"] < 0), key=lambda r: r["move"])[:TOP]}


def outside_the_page(page_cards, all_cards) -> dict[str, list[dict]]:
    """Per board, the cards of the true top ten that the page never reads."""
    have = {c.get("id") for c in page_cards if isinstance(c, dict)}
    return {name: [r for r in rows if r["id"] not in have] for name, rows in boards(all_cards).items()}


def _cards(body) -> list[dict] | None:
    if isinstance(body, list):
        return [c for c in body if isinstance(c, dict)]
    if isinstance(body, dict):
        for key in ("cards", "items"):
            if isinstance(body.get(key), list):
                return [c for c in body[key] if isinstance(c, dict)]
    return None


def _get(client, path, **params):
    time.sleep(PAUSE_S)
    return client.get(path, params=params or None)


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_movers_boards_rank_every_card_of_the_listing(rest_anon):
    """The true ten biggest gainers and losers are among the cards the page reads."""
    page = rest_anon.get(PAGE, headers={"Accept": "text/html"})
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    script = board_script(page.text)
    if script is None:
        raise Inconclusive(f"{PAGE} carries no script writing #{BOARD_ANCHOR}; the boards moved")
    urls, pages = card_requests(script)
    if not urls:
        raise Inconclusive(f"{PAGE}'s board script no longer fetches {LISTING}; re-point the check")
    if pages:
        conclude(Measurement(
            verdict="passed",
            reason=f"{PAGE}'s board script pages through the listing ({urls})",
            left={"pages_through_listing": True}, right={"pages_through_listing": True},
            population={"requests": urls}, sources={"page": PAGE, "listing": LISTING}, claim_id=CLAIM))
        return

    page_cards, totals = {}, []
    for url in urls:
        parts = urlsplit(url)
        r = _get(rest_anon, parts.path, **dict(parse_qsl(parts.query)))
        cards = _cards(r.json()) if r.status_code == 200 else None
        if cards is None:
            raise Inconclusive(f"{url}, which the page reads, answered HTTP {r.status_code} without a card list")
        page_cards.update({c.get("id"): c for c in cards if c.get("id")})
        body = r.json()
        if isinstance(body, dict) and isinstance(body.get("total"), int):
            totals.append(body["total"])
    total = max(totals) if totals else None

    base = dict(parse_qsl(urlsplit(urls[0]).query))
    every, offset = {}, 0
    for _ in range(MAX_PAGES):
        r = _get(rest_anon, LISTING, **dict(base, limit=PAGE_SIZE, offset=offset))
        cards = _cards(r.json()) if r.status_code == 200 else None
        if cards is None:
            raise Inconclusive(f"{LISTING} offset {offset} answered HTTP {r.status_code}; the listing could "
                               f"not be read whole")
        every.update({c.get("id"): c for c in cards if c.get("id")})
        offset += PAGE_SIZE
        if not cards or (total is not None and offset >= total):
            break
    if total is not None and len(every) < total * 0.95:
        raise Inconclusive(f"read {len(every)} of the {total} cards the listing totals")
    big = _get(rest_anon, LISTING, limit=500)

    missed = outside_the_page(list(page_cards.values()), list(every.values()))
    on_page = boards(list(page_cards.values()))
    truth = boards(list(every.values()))
    n_missed = sum(len(v) for v in missed.values())
    fmt = lambda r: f"{r['title']} {r['move']:+.2f}%"  # noqa: E731
    conclude(Measurement(
        verdict="failed" if n_missed else "passed",
        reason=(f"{PAGE} ranks the {len(page_cards)} cards its script reads ({', '.join(urls)}) of the "
                f"{total if total is not None else len(every)} the listing totals: {len(missed['losers'])} of the "
                f"{len(truth['losers'])} biggest losers and {len(missed['gainers'])} of the {len(truth['gainers'])} "
                f"biggest gainers are cards the page never reads. Biggest loser over every card: "
                f"{fmt(truth['losers'][0]) if truth['losers'] else 'none'}; the page's: "
                f"{fmt(on_page['losers'][0]) if on_page['losers'] else 'none'}. Biggest gainer over every card: "
                f"{fmt(truth['gainers'][0]) if truth['gainers'] else 'none'}; the page's: "
                f"{fmt(on_page['gainers'][0]) if on_page['gainers'] else 'none'}. {LISTING}?limit=500 answers "
                f"HTTP {big.status_code}"
                if n_missed else
                f"every card of the true top {TOP} gainers and losers ({len(every)} cards read) is among the "
                f"{len(page_cards)} cards {PAGE} reads"),
        left={"top_cards_the_page_never_reads": n_missed, "cards_the_page_reads": len(page_cards)},
        right={"top_cards_the_page_never_reads": 0},
        population={"requests": urls, "listing_total": total, "cards_read": len(every),
                    "missed": {k: [fmt(r) for r in v] for k, v in missed.items()},
                    "page_boards": {k: [fmt(r) for r in v] for k, v in on_page.items()},
                    "true_boards": {k: [fmt(r) for r in v] for k, v in truth.items()},
                    "limit_500_status": big.status_code},
        sources={"page": PAGE, "listing": LISTING,
                 "contract": "/movers: 'event cards, index funds and platform tokens ranked by move and by "
                             "activity'; llms.txt: 'Biggest gainers, losers and most active across "
                             "EventTrader's own products'"},
        claim_id=CLAIM))
