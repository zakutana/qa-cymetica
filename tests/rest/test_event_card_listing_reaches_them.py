"""Every tradeable card is reachable from the list that advertises them.

`GET /api/v1/event-cards` is the only listing an agent has. Measured
2026-09-10 around 21:30 UTC:

  * `limit` caps at 200; 201 and above answer 422.
  * `offset`, `skip` and `page` are accepted and ignored -- every call
    returns the identical window, same first id.
  * `q`, `search`, `query`, `symbol`, `status` and `tradeable_now` are
    accepted and ignored; the response is the same unfiltered window.
  * card `a4a5b71e-de11-4805-b8a3-ed9c3f8f8161` answers 200 on
    `GET /api/v1/event-cards/{id}` with `status: live` and
    `tradeable_now: true`, and appears in no listing response at all.

So there are tradeable cards an agent cannot discover. It can only trade a
card whose id it already holds -- and on this platform the thing that hands
out ids is NEXUS, which is how this was found: it recommended three cards by
id and two of them are unreachable through the listing.

**Why this is a market defect and not a paging nit.** An agent that enumerates
the board and picks the best of what it sees is making a decision over a
sample it cannot know the shape of. Nothing in the response says it is
truncated: `count` echoes the rows returned, not a total, so 200 looks like
the whole market. A strategy measured against "every live card" is measured
against the first 200, silently.

THE CLAIM IS REACHABILITY, NOT ABSENCE. This check does not assert that any
particular card is missing from the platform. It takes cards the platform
itself confirms are live and tradeable, and asks whether the listing returns
them -- a comparison between two of their own endpoints. The witness ids come
from what NEXUS has recommended, so the set grows as they recommend more.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
LIST = "/api/v1/event-cards"
CARD = "/api/v1/event-cards/{id}"
# Their own ceiling: 201 answers 422, so this is the whole window an agent
# can ever see.
MAX_LIMIT = 200
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                  r"[0-9a-f]{4}-[0-9a-f]{12}\b")


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_cards", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def card_ids_named(rows) -> list[str]:
    """Every card-shaped id NEXUS has named, newest answer first."""
    answers = [r for r in rows
               if r.get("type") == "answer" and r.get("text")]
    answers.sort(key=lambda r: (r.get("at") or "", r.get("id") or ""),
                 reverse=True)
    out: list[str] = []
    for row in answers:
        for found in UUID.findall(row["text"]):
            if found not in out:
                out.append(found)
    return out


def is_user_submission(card) -> bool:
    """Whether a card is one user's own submission rather than a public card.

    Their account of #91, 2026-09-11: a user-submitted card is "visible only
    to its author, hence 404 for everyone else". By their design it is not
    part of the public market, so the public listing owes it nothing. When one
    is readable to us anyway, that is a visibility defect with its own check
    (test_user_submissions_stay_private.py) and not a listing defect -- which
    is exactly what a4a5b71e was, the morning this check nearly reported
    their working pagination fix as broken.
    """
    return (isinstance(card, dict)
            and str(card.get("source_url") or "").startswith("user-submission://"))


def walk_listing(get, limit=MAX_LIMIT, max_pages=50):
    """Every card the listing will hand out, walked by offset.

    `get(params)` returns (status, body). The result is (cards,
    offset_ignored), or (None, False) when a page could not be read.

    Until 2026-09-11 this check read ONE page, because on 2026-09-10 offset,
    skip and page were all ignored and one page was all there was. Their
    release of ~04:35 that morning made offset work and added a total -- and a
    one-page read cannot tell a card beyond the first window that is now
    reachable from one that is not, so the check would have reported their fix
    as broken. Where offset is still ignored the same first id comes back, and
    the walk stops and says so instead of looping.
    """
    cards, seen, offset = [], set(), 0
    for _ in range(max_pages):
        status, body = get({"limit": limit, "offset": offset})
        if status != 200 or not isinstance(body, dict):
            return None, False
        batch = body.get("cards")
        if not isinstance(batch, list):
            return None, False
        fresh = [c for c in batch
                 if isinstance(c, dict) and c.get("id") not in seen]
        if batch and not fresh:
            return cards, True
        for card in fresh:
            seen.add(card.get("id"))
            cards.append(card)
        offset += len(batch)
        total = body.get("total")
        if (not batch or len(batch) < limit
                or (isinstance(total, int) and offset >= total)):
            return cards, False
    return cards, False


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_the_listing_returns_every_card_it_says_is_tradeable(rest_trusted):
    """A card you cannot find is a card you cannot trade."""
    def page(params):
        response = rest_trusted.get(LIST, params=params)
        try:
            body = response.json() if response.status_code == 200 else {}
        except ValueError:
            body = {}
        return response.status_code, body

    rows, offset_ignored = walk_listing(page)
    if rows is None:
        raise Inconclusive(
            f"{LIST} could not be read page by page; a failed read is not "
            f"an empty market")
    if not rows:
        raise Inconclusive(f"{LIST} returned no cards to compare against")
    seen = {r.get("id") for r in rows if isinstance(r, dict)}

    witnesses = card_ids_named(_nexus().load())
    if not witnesses:
        raise Inconclusive(
            "no recorded Nexus answer names a card id, so there is no witness "
            "to look up; this check compares their own two endpoints and "
            "needs an id from outside the listing to do it")

    unreachable, checked, private = [], 0, []
    for card_id in witnesses[:12]:
        if card_id in seen:
            checked += 1
            continue
        one = rest_trusted.get(CARD.format(id=card_id))
        if one.status_code != 200:
            # A 404 is a different finding and not this one. Silence here is
            # deliberate: this check claims reachability, never absence.
            continue
        body = one.json()
        body = body.get("result", body) if isinstance(body, dict) else {}
        if is_user_submission(body):
            private.append(card_id)
            continue
        checked += 1
        if body.get("tradeable_now") is True:
            unreachable.append({"id": card_id,
                                "index": body.get("current_index"),
                                "status": body.get("status")})

    if not checked:
        raise Inconclusive(
            f"none of the {len(witnesses)} card id(s) Nexus named could be "
            f"read from {CARD}, so the listing had nothing to be compared "
            f"against")

    conclude(Measurement(
        verdict="failed" if unreachable else "passed",
        reason=(
            f"{len(unreachable)} card(s) answer status live and "
            f"tradeable_now true on {CARD} and appear in no response from "
            f"{LIST}: " + ", ".join(u["id"] for u in unreachable)
            + (f". The listing caps at {MAX_LIMIT} rows a page and ignores offset, "
               f"so an agent enumerating the market cannot reach them and "
               f"nothing in the response says the window is truncated"
               if offset_ignored else
               f". The listing was walked by offset through all {len(rows)} "
               f"cards it hands out, and they are not among them")
            if unreachable else
            f"every one of the {checked} tradeable card(s) checked appears in "
            f"the listing"),
        left=sorted(u["id"] for u in unreachable),
        right=sorted(seen)[:5],
        population={"listed": len(rows), "offset_ignored": offset_ignored,
                    "user_submissions_skipped": private, "witnesses": len(witnesses),
                    "checked": checked, "unreachable": len(unreachable)},
        sources={"listing": f"GET {LIST}?limit={MAX_LIMIT}",
                 "card": f"GET {CARD}"},
    ))
