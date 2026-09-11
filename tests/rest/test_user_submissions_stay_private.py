"""A user-submitted card is visible only to its author -- their words, tested.

Their reply to A2A-0002, 2026-09-11 04:47, explaining #91: the 40% leg
5bd86126 "was a private user-submitted card: live in the catalogue, visible
only to its author, hence 404 for everyone else".

Card a4a5b71e-de11-4805-b8a3-ed9c3f8f8161 carries source_url
`user-submission://99/...` -- user 99's submission. Our account is 113. It
answers 200 to us, with status live and tradeable_now true, and it is absent
from the public listing walked end to end by offset (6,880 cards).

So one of two things is wrong, and this check cannot say which: either the
card is private and a non-author can read it -- and, by tradeable_now, trade
it -- or it is public and the listing omits it. The report says both and
asks. What it can measure is the half their own sentence commits to: a
user-submitted card whose author is not the caller answers 404.

Found because #90's listing check went red on exactly this card after their
pagination fix, and reading the card before believing the failure showed the
listing was never the problem.

THE CLAIM IS PRESENCE: a 200 carrying a user-submission source_url whose
author id is not ours. Witnesses are the card ids Nexus has named; a card we
cannot read, or one that is not a user submission, is skipped, never counted.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
ACCOUNT = "/api/v1/account/me"
CARD = "/api/v1/event-cards/{id}"
AUTHOR = re.compile(r"^user-submission://(\d+)/")


def _listing_module():
    spec = importlib.util.spec_from_file_location(
        "listing_reaches", REPO / "tests" / "rest"
        / "test_event_card_listing_reaches_them.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def author_of(card) -> int | None:
    """The submitting user's id, or None for a card that is not a submission."""
    if not isinstance(card, dict):
        return None
    match = AUTHOR.match(str(card.get("source_url") or ""))
    return int(match.group(1)) if match else None


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_user_submitted_card_is_visible_only_to_its_author(rest_trusted):
    """Their rule, in their words, held against a card they serve us."""
    me = rest_trusted.get(ACCOUNT)
    if me.status_code != 200:
        raise Inconclusive(
            f"{ACCOUNT} answered HTTP {me.status_code}, so who we are -- and "
            f"therefore whose submissions we may see -- is unknown")
    body = me.json()
    body = body.get("result", body) if isinstance(body, dict) else {}
    our_id = body.get("id")
    if not isinstance(our_id, int):
        raise Inconclusive(f"{ACCOUNT} carries no integer id to compare with")

    listing = _listing_module()
    witnesses = listing.card_ids_named(listing._nexus().load())
    if not witnesses:
        raise Inconclusive(
            "no recorded Nexus answer names a card id, so there is no card to "
            "look up")

    submissions, leaks = 0, []
    for card_id in witnesses[:20]:
        response = rest_trusted.get(CARD.format(id=card_id))
        if response.status_code != 200:
            continue
        card = response.json()
        card = card.get("result", card) if isinstance(card, dict) else {}
        author = author_of(card)
        if author is None:
            continue
        submissions += 1
        if author != our_id:
            leaks.append({"id": card_id, "author": author,
                          "status": card.get("status"),
                          "tradeable_now": card.get("tradeable_now")})

    if not submissions:
        raise Inconclusive(
            "none of the cards Nexus has named that we can read is a user "
            "submission, so their rule could not be exercised either way")

    conclude(Measurement(
        verdict="failed" if leaks else "passed",
        reason=(
            "; ".join(
                f"user {l['author']}'s submitted card {l['id']} answers 200 to "
                f"account {our_id}, status {l['status']}, tradeable_now "
                f"{l['tradeable_now']}" for l in leaks)
            + ". Their stated rule is that a user-submitted card is visible "
              "only to its author and 404 for everyone else; either the card "
              "is private and readable by others, or it is public and missing "
              "from the listing"
            if leaks else
            f"every one of the {submissions} user-submitted card(s) we could "
            f"read is our own"),
        left=[l["id"] for l in leaks], right=[],
        population={"our_account": our_id, "witnesses": len(witnesses),
                    "user_submissions_read": submissions,
                    "not_ours": len(leaks)},
        sources={"account": ACCOUNT, "card": f"GET {CARD}",
                 "rule": "vendor reply to A2A-0002, 2026-09-11 04:47"},
    ))
