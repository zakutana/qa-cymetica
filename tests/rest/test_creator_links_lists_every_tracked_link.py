"""A creator's link list names every tracked link its summary counts.

`/llms.txt`, the creator section:

    GET /api/v1/creator/{username}/links: All of one creator's tracked links
    with a summary. No key

**What was seen when this was written (2026-09-24).** For tg_expire76 the
list held 8 links, all `kind: artifact` (the creator's pages), with per-link
clicks summing to 1 -- while `summary.clicks` read 23 and `summary.links` read
8. The other 22 clicks sit on the per-reply tracked links the reply queue
mints (`POST /api/v1/creator/{outlet}-leads/{id}/reply`, one `reply_slug` per
thread, `https://cymetica.com/c/<reply_slug>`): each answers
`GET /api/v1/creator-links/{slug}/stats` with `kind: post` and its own
clicks, and none of them is in the list. So the summary counts links the list
does not show, and a creator reading the list cannot see which reply brought
the clicks -- the per-thread measurement the reply queue exists for.

The check reads the list, then the stats of every tracked link the creator's
own claimed leads carry (the reply queue's `tracked_url`s, read with
`?status=claimed,replied`, which needs the creator's key), and fails when a
reply link with its own stats is missing from the list. The summary's click
total against the list's is reported beside it as context.

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
    """The creator account's own key (QA_CREATOR_KEY): only it lists the
    reply queue's claimed leads and their tracked links."""
    identity = all_identities.get("creator")
    if identity is None or not identity.present:
        pytest.skip("no QA_CREATOR_KEY: the creator's claimed leads cannot be read")
    client = build_client(identity, registry, evidence_store, budget)
    yield client
    client.close()


@qa(component="rest.creator", tier=SafetyTier.SAFE, surface="rest",
    claim=CLAIM_ID)
def test_creator_links_lists_every_reply_tracked_link(rest_anon, rest_creator):
    listed = rest_anon.get(LINKS)
    if listed.status_code != 200:
        raise Inconclusive(f"{LINKS} answered HTTP {listed.status_code}")
    body = listed.json() or {}
    links = body.get("links")
    if not isinstance(links, list):
        raise Inconclusive(f"{LINKS} answered 200 with no `links` list")
    in_list = {l.get("slug") for l in links if isinstance(l, dict)}

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

    missing, reply_clicks = [], 0
    for slug in sorted(reply_slugs):
        stats = rest_anon.get(f"/api/v1/creator-links/{slug}/stats")
        if stats.status_code != 200:
            continue  # a link without stats is not a tracked link to list
        reply_clicks += int((stats.json() or {}).get("clicks") or 0)
        if slug not in in_list:
            missing.append(slug)

    summary = body.get("summary") or {}
    listed_clicks = sum(int(l.get("clicks") or 0) for l in links
                        if isinstance(l, dict))
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
