"""A creator's link list names every tracked link its summary counts.

`/llms.txt`, the creator section:

    GET /api/v1/creator/{username}/links: All of one creator's tracked links
    with a summary. No key

**Written 2026-09-24 on a misreading, repaired before anything was filed.**
The first version read only the list's top-level `slug`s -- the creator's 8
pages, `kind: artifact` -- and called all 14 per-reply tracked links missing.
They were there all along: each page carries its reply links in `children`
(`kind: post`), and the children's clicks plus the pages' add up to
`summary.clicks`. The deep pass's contract audit caught it (A01, 3/3); the
lesson is in memory as another absence got wrong.

What it holds now: every tracked link the creator's own claimed leads carry
(the reply queue's `reply_slug`s, read with `?status=claimed,replied`, which
needs the creator's key) appears in the list, at the top level or as a child
of its page. A reply link whose stats cannot be read makes the check
inconclusive, never a pass (rule 8).

SAFE. Every request is a GET.
"""

from __future__ import annotations

import pytest

from qa.client import build_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CREATOR = "tg_expire76"
LINKS = f"/api/v1/creator/{CREATOR}/links"
LEADS = ("/api/v1/creator/twitter-leads", "/api/v1/creator/reddit-leads")
CLAIM_ID = "creator-links-list-names-every-tracked-link"


@pytest.fixture(scope="module")
def rest_creator(registry, evidence_store, budget, all_identities):
    """The operator's own key: the creator queue answers it since 2026-09-25,
    and the tg_expire76 key it used before was retired that day."""
    identity = all_identities.get("trusted")
    if identity is None or not identity.present:
        pytest.skip("no QA_TRUSTED_KEY: the creator's claimed leads cannot be read")
    client = build_client(identity, registry, evidence_store, budget)
    yield client
    client.close()


@qa(component="rest.creator", tier=SafetyTier.SAFE, surface="rest",
    claim=CLAIM_ID)
def test_creator_links_lists_every_reply_tracked_link(rest_anon, rest_creator):
    """Every reply tracked link of the creator's claimed leads is in the link list, at the top or as a page's child."""
    listed = rest_anon.get(LINKS)
    if listed.status_code != 200:
        raise Inconclusive(f"{LINKS} answered HTTP {listed.status_code}")
    body = listed.json() or {}
    links = body.get("links")
    if not isinstance(links, list):
        raise Inconclusive(f"{LINKS} answered 200 with no `links` list")
    # A reply link is listed as a child of the page it points at (`children`,
    # kind post). Reading the top level alone called all 14 missing while the
    # list held every one (deep pass 2026-09-24, A01 3/3 -- caught before it
    # was filed).
    in_list = set()
    for link in links:
        if isinstance(link, dict):
            in_list.add(link.get("slug"))
            in_list |= {c.get("slug") for c in link.get("children") or []
                        if isinstance(c, dict)}

    reply_slugs: set[str] = set()
    for path in LEADS:
        answer = rest_creator.get(path, params={"status": "claimed,replied",
                                                "limit": 200})
        if answer.status_code != 200:
            raise Inconclusive(f"{path}?status=claimed,replied answered HTTP "
                               f"{answer.status_code}")
        for lead in (answer.json() or {}).get("leads") or []:
            if isinstance(lead, dict) and lead.get("reply_slug"):
                reply_slugs.add(str(lead["reply_slug"]))
    if not reply_slugs:
        raise Inconclusive("the creator has no claimed lead with a reply_slug, "
                           "so there is no reply link to look for")

    missing, reply_clicks, unread = [], 0, []
    for slug in sorted(reply_slugs):
        stats = rest_anon.get(f"/api/v1/creator-links/{slug}/stats")
        if stats.status_code == 404:
            continue  # a slug with no link behind it is not a tracked link
        if stats.status_code != 200:
            unread.append(f"{slug} HTTP {stats.status_code}")
            continue
        reply_clicks += int((stats.json() or {}).get("clicks") or 0)
        if slug not in in_list:
            missing.append(slug)
    # A failed read is not an absent link (rule 8; deep pass A05, 3/3): a pass
    # needs every reply link read, and a fail needs only the ones it read.
    if unread and not missing:
        raise Inconclusive(f"{len(unread)} reply link stats unread: "
                           f"{', '.join(unread[:5])}")

    summary = body.get("summary") or {}
    listed_clicks = sum(int(l.get("clicks") or 0) for l in links
                        if isinstance(l, dict))
    listed_clicks += sum(int(c.get("clicks") or 0) for l in links
                         if isinstance(l, dict) for c in l.get("children") or []
                         if isinstance(c, dict))
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(
            f"{LINKS} lists {len(links)} link(s); {len(missing)} of the "
            f"{len(reply_slugs)} reply tracked link(s) the creator's own claimed "
            f"leads carry, each with its own stats, are not among them "
            f"({', '.join(missing[:8])}{', ...' if len(missing) > 8 else ''}). "
            f"summary.clicks reads {summary.get('clicks')!r} while the listed "
            f"links' clicks sum to {listed_clicks}; the reply links hold "
            f"{reply_clicks}"
            if missing else
            f"every one of the {len(reply_slugs)} reply tracked link(s) is in "
            f"{LINKS}"),
        left=missing, right=[],
        population={"listed": len(links), "reply_slugs": len(reply_slugs),
                    "summary": summary, "listed_clicks": listed_clicks,
                    "reply_clicks": reply_clicks},
        sources={"contract": "/llms.txt: GET /api/v1/creator/{username}/links: "
                             "\"All of one creator's tracked links with a "
                             "summary.\"",
                 "endpoint": LINKS},
        claim_id=CLAIM_ID,
    ))
