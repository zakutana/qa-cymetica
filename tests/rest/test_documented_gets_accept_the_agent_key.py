"""A documented GET does not tell an authenticated agent it is unauthenticated.

`llms.txt` is the agent-facing document: it exists so a machine can read the
platform and act on it. Measured 2026-09-11 with the TRUSTED API key their
own onboarding tells an agent to use, over every concrete GET path llms.txt
names:

    44 of 48 answered 200
     1 answered 422 (a missing query parameter -- fine, it read the key)
     3 answered 401 {"detail":"Not authenticated"}

        /api/v1/swap/history
        /api/v1/rewards/summary
        /api/v1/robinhood/wallet

The same client, the same key, in the same session, gets 200 from
`/api/v1/account/me` and `/api/v1/bounty/reward-tiers`. And `rewards/summary`
answers 401 to all three identities we hold -- anonymous, recognized and
trusted alike -- so there is no tier at which an API key reaches it.

401 is the specific claim here, not 403. A 403 would be a decision about
this caller's tier, which is theirs to make and not a defect. **401 says the
request carried no credential at all**, to a request that carried one the
rest of the surface accepts. So an agent cannot tell "you may not" from "who
are you", and has nothing to act on: no scope to request, no tier to reach.

This is the same family as #89, where /cloned-bots/{id}/fund and /go-live
accepted only a bearer `authorization` and refused the agent key. They fixed
that within the hour. These three are the same shape on the read side, and
llms.txt lists all three without an auth note.

The check claims PRESENCE -- it looks for 401s among paths their own document
advertises, and finds them or does not. The 200 count travels with the
verdict so a reader can see the key works.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LLMS = "/llms.txt"
# Concrete paths only. A template (`{id}`, `<addr>`) needs a value we would
# have to invent, and a 401 from a made-up id proves nothing about the route.
DOCUMENTED_GET = re.compile(r"\[GET (/api/v1/[^\]{}<>]+)\]")


@qa(component="discovery.llmstxt", tier=SafetyTier.SAFE, surface="rest")
def test_every_documented_get_accepts_the_key_its_own_document_issues(rest_trusted):
    """The agent-facing document lists routes no agent key can read."""
    document = rest_trusted.get(LLMS)
    if document.status_code != 200:
        raise Inconclusive(
            f"{LLMS} answered HTTP {document.status_code}, so what they "
            f"document could not be read -- a failed read is not an empty "
            f"document")

    paths: list[str] = []
    for match in DOCUMENTED_GET.finditer(document.text):
        path = match.group(1).strip()
        if path not in paths:
            paths.append(path)
    if not paths:
        raise Inconclusive(
            f"{LLMS} names no concrete GET path, so there was nothing to call")

    refused, served, other, unread = [], 0, {}, {}
    for path in paths:
        # Forty-eight sequential calls against a platform that times out now
        # and then. One unreachable path is a hole in the sample, not a
        # reason to throw away the other forty-seven: the verdict is about
        # the paths that ANSWERED, and the holes travel in population so a
        # reader can see how much of the surface was actually covered.
        try:
            response = rest_trusted.get(path)
        except Exception as exc:  # noqa: BLE001
            unread[path] = type(exc).__name__
            continue
        if response.status_code == 401:
            refused.append(path)
        elif response.status_code == 200:
            served += 1
        else:
            other[path] = response.status_code

    if len(unread) > len(paths) // 4:
        raise Inconclusive(
            f"{len(unread)} of {len(paths)} documented paths could not be "
            f"reached at all ({sorted(unread)[:4]}), so this run says more "
            f"about the platform's availability than about its credentials")

    if not served:
        raise Inconclusive(
            f"none of the {len(paths)} documented GET paths answered 200 with "
            f"this key, so the key itself is the likelier subject and this "
            f"check cannot separate the two")

    conclude(Measurement(
        verdict="failed" if refused else "passed",
        reason=(
            f"{len(refused)} of {len(paths)} GET paths llms.txt documents "
            f"answer 401 Not authenticated to the TRUSTED key their own "
            f"onboarding issues, while {served} answer 200 to the same key in "
            f"the same session: " + ", ".join(refused)
            + ". 401 says the request carried no credential, so an agent "
              "cannot tell 'you may not' from 'who are you' -- there is no "
              "scope to request and no tier to reach"
            if refused else
            f"all {served} of the documented GET paths that answered read the "
            f"agent key"),
        left=sorted(refused), right=[],
        population={"documented": len(paths), "served": served,
                    "unauthenticated": len(refused), "other": other,
                    "unreachable": unread},
        sources={"document": LLMS, "credential": "X-API-Key, trusted tier"},
    ))
