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

THEIR RULE, READ FIRST (2026-10-25). The claim is about routes listed "without
an auth note". From PRE-0274 on the check failed on
`/api/v1/cloned-bots/backtest/quote`, and a FAIL went out on 2026-10-21 -- but
llms.txt's own line for it reads "Cost confirmation before a run (session
JWT)", in the capture of that very run, and its 401 says "Valid JWT token
required". A route whose own line documents a session JWT and names no API key
has told the agent which credential it takes: it is named, not judged. A line
that names the key ("session or X-API-Key") is judged like any other.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LLMS = "/llms.txt"
# Concrete paths only. A template (`{id}`, `<addr>`) needs a value we would
# have to invent, and a 401 from a made-up id proves nothing about the route.
DOCUMENTED_GET = re.compile(r"\[GET (/api/v1/[^\]{}<>]+)\]")
# An auth note that documents a session credential, in their own wording: "(session JWT)",
# "(session JWT, run owner only)", "session-only", "JWT only". Prose that merely says
# "sessions" is not a note.
SESSION_NOTE = re.compile(r"\(\s*session JWT\b[^)]*\)|\bsession[- ]only\b|\bJWT[- ]only\b", re.I)
API_KEY_NOTE = re.compile(r"X-API-Key|\bAPI[- ]key\b", re.I)


def documented_session_only(text: str) -> set[str]:
    """The concrete GET paths whose own llms.txt line documents a session credential and
    names no API key -- on every line that lists them."""
    lines: dict[str, list[str]] = {}
    for match in DOCUMENTED_GET.finditer(text or ""):
        start = text.rfind("\n", 0, match.start()) + 1
        end = text.find("\n", match.end())
        lines.setdefault(match.group(1).strip(), []).append(
            text[start:end if end >= 0 else len(text)])
    return {path for path, said in lines.items()
            if all(SESSION_NOTE.search(line) and not API_KEY_NOTE.search(line)
                   for line in said)}


def _said(response) -> str:
    """What a refusal says, for the population: their body, cut short."""
    try:
        return (response.text or "")[:160]
    except Exception:  # noqa: BLE001
        return ""


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

    session_only = documented_session_only(document.text)
    refused, served, other, unread = [], 0, {}, {}
    said_401, as_documented = {}, {}
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
        if response.status_code == 401 and path in session_only:
            as_documented[path] = _said(response)
        elif response.status_code == 401:
            refused.append(path)
            said_401[path] = _said(response)
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

    named = (f". NOT in the verdict: {len(as_documented)} route(s) whose own llms.txt "
             f"line documents a session JWT and names no API key answered 401 as "
             f"documented: {', '.join(sorted(as_documented))}" if as_documented else "")
    conclude(Measurement(
        verdict="failed" if refused else "passed",
        reason=(
            f"{len(refused)} of {len(paths)} GET paths llms.txt documents "
            f"with no session-only note answer 401 to the TRUSTED key their own "
            f"onboarding issues, while {served} answer 200 to the same key in "
            f"the same session: " + ", ".join(refused)
            + ". 401 says the request carried no credential, so an agent "
              "cannot tell 'you may not' from 'who are you' -- there is no "
              "scope to request and no tier to reach"
            if refused else
            f"all {served} of the documented GET paths that answered read the "
            f"agent key") + named,
        left=sorted(refused), right=[],
        population={"documented": len(paths), "served": served,
                    "unauthenticated": len(refused), "other": other,
                    "unreachable": unread, "refusals": said_401,
                    "documented_session_only": as_documented},
        sources={"document": LLMS, "credential": "X-API-Key, trusted tier"},
    ))
