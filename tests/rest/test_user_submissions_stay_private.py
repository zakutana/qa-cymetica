"""A private user-submitted card is visible only to its author -- their rule, tested.

Their reply to A2A-0002, 2026-09-11 04:47, explaining #91: the 40% leg
5bd86126 "was a private user-submitted card: live in the catalogue, visible
only to its author, hence 404 for everyone else".

Card a4a5b71e-de11-4805-b8a3-ed9c3f8f8161 carries source_url
`user-submission://99/...` -- user 99's submission. Our account is 113. It
answers 200 to us, with status live and tradeable_now true, and the listing
walked end to end by offset (6,880 cards) did not carry it. Reported as #95:
either the card is private and a non-author can read it, or it is public and
the listing omits it.

Their resolution of #95, 2026-09-11 09:47 (ET-24616), says which: the second,
and the omission is the documented default. The one visibility rule keys on
is_public, not on where a card came from; only is_public=false cards 404 for
a non-owner, and a4a5b71e is public. The listing leaves user submissions out
unless asked -- openapi documents `include_user_submitted`, default false,
"user-submitted cards are reachable ... by passing this flag explicitly" --
and with the flag, they say, the card is listed.

Until 2026-09-11 this check held every user submission to "404 for everyone
but its author", reading a sentence about one private card as the rule for
all of them, so it could only ever fail on a public one. The card body
carries no is_public, so the check reads the rule's consequence instead: a
submission of another user's that answers 200 must be one the listing hands
out under include_user_submitted=true, which is to say public. One that
answers 200 and that listing does not carry is a private card served to
someone who does not own it -- the defect their rule forbids.

THE CLAIM IS PRESENCE: a 200 for another user's submission that the listing,
asked with include_user_submitted=true and walked to its end, does not carry.
Witnesses are the card ids Nexus has named; a card we cannot read, or one that
is not a user submission, is skipped, never counted. A walk that cannot reach
the end of the listing is no verdict.
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
LIST = "/api/v1/event-cards"
FLAG = "include_user_submitted"
AUTHOR = re.compile(r"^user-submission://(\d+)/")
MAX_PAGES = 50


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


def _flagged(client):
    """The listing walker's `get(params)`, asking for user submissions too."""
    def get(params):
        response = client.get(LIST, params={**params, FLAG: "true"})
        try:
            body = response.json()
        except ValueError:
            body = None
        return response.status_code, body
    return get


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

    submissions, others = 0, []
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
            others.append({"id": card_id, "author": author,
                           "status": card.get("status"),
                           "tradeable_now": card.get("tradeable_now")})

    if not submissions:
        raise Inconclusive(
            "none of the cards Nexus has named that we can read is a user "
            "submission, so their rule could not be exercised either way")

    leaks, listed_count = [], None
    if others:
        cards, offset_ignored = listing.walk_listing(
            _flagged(rest_trusted), max_pages=MAX_PAGES)
        if cards is None or offset_ignored:
            raise Inconclusive(
                f"{LIST}?{FLAG}=true could not be walked to its end -- "
                + ("offset was ignored" if offset_ignored
                   else "a page could not be read")
                + f" -- so whether the {len(others)} readable submission(s) of "
                  f"other users are public is unknown")
        if len(cards) >= listing.MAX_LIMIT * MAX_PAGES:
            raise Inconclusive(
                f"the walk of {LIST}?{FLAG}=true stopped at {len(cards)} cards, "
                f"its page cap, before the listing ended; a card beyond it "
                f"could be public and unseen")
        listed = {c.get("id") for c in cards}
        listed_count = len(cards)
        leaks = [o for o in others if o["id"] not in listed]

    conclude(Measurement(
        verdict="failed" if leaks else "passed",
        reason=(
            "; ".join(
                f"user {l['author']}'s submitted card {l['id']} answers 200 to "
                f"account {our_id}, status {l['status']}, tradeable_now "
                f"{l['tradeable_now']}, and is not among the {listed_count} "
                f"cards {LIST} lists with {FLAG}=true" for l in leaks)
            + ". Their rule is that only a public card is readable by someone "
              "who does not own it, and a public submission is listed under "
              "that flag; one readable and unlisted is a private card served "
              "to a non-owner"
            if leaks else
            (f"{len(others)} submission(s) of other users answer 200 to account "
             f"{our_id}, and every one is among the {listed_count} cards listed "
             f"with {FLAG}=true, so each is public"
             if others else
             f"every one of the {submissions} user-submitted card(s) we could "
             f"read is our own")),
        left=[l["id"] for l in leaks], right=[],
        population={"our_account": our_id, "witnesses": len(witnesses),
                    "user_submissions_read": submissions,
                    "not_ours": len(others), "listed_with_flag": listed_count},
        sources={"account": ACCOUNT, "card": f"GET {CARD}",
                 "listing": f"GET {LIST}?{FLAG}=true",
                 "rule": "their resolution of #95, 2026-09-11 09:47 (ET-24616)"},
    ))
