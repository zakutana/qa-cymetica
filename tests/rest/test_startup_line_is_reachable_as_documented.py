"""The Startup section of the Build it Better API, read against its own page.

`/build-it-better/api#startup` documents five calls that spin a rebuilt app
out as a company, and an auction for the place in the queue:

    GET  /startups/terms      what applying means, statuses, socials, chains   –
    GET  /startups/line       the public line: position, startup_name, bid_usd  –
    GET  /startups/mine       your applications and their status          account
    POST /startups            apply                                       account
    POST /startups/{id}/bid   place or raise a bid                        account

The Auth column is the contract this check reads. A dash means a reader with
no credential is served; "account" means one is not. Both halves matter and
they fail in opposite directions: an account-gated call that answers an
anonymous reader is a leak of other people's applications, and a call the page
calls public that demands a key is a door an agent is told to use and cannot.

WHAT IT ASSERTS.

  1. The two calls marked public answer 200 to a client carrying no
     credential at all, and their bodies carry the fields the page names --
     `statuses` and `token_chains` on terms, `line`, `count` and the rules on
     the line.
  2. The call marked `account` refuses that same client, and refuses it as an
     authentication problem: 401 or 403, never 200 and never 404. A 404 would
     say the route does not exist, which is a different defect from a route
     that will not talk to a stranger, and the reason says which one it saw.
  3. The statuses the page prints in prose -- submitted, reviewing, accepted,
     declined -- are the keys the endpoint serves. The page is the claimant
     here: it tells an agent what to expect back from `/startups/mine`.

WHAT IT DOES NOT. Not the auction's ordering rule (highest bid first, ties by
arrival). The line is empty today -- `count: 0` -- and a rule asserted over no
rows is the `0 == 0` verdict this repository spent 2026-09-20 removing. It
belongs here the day somebody applies, and the reason says so out loud every
run so the gap is visible rather than assumed.

Nor anything that applies or bids. Both are POSTs, one of them a commitment in
money, and this is a SAFE check: three GETs, no key, nothing written.

Their whole Startup surface is in none of /api-docs, /llms.txt or
/openapi-public.json (MSG-0032). That is a documentation gap and not what this
measures -- a surface being undiscoverable does not make it wrong.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

TERMS = "/api/v1/build-it-better/startups/terms"
LINE = "/api/v1/build-it-better/startups/line"
MINE = "/api/v1/build-it-better/startups/mine"
# The four the page prints as the status of an application, in its own order.
PAGE_STATUSES = ("submitted", "reviewing", "accepted", "declined")
REFUSALS = (401, 403)


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_startup_calls_answer_the_reader_their_own_page_promises(rest_anon):
    """Three GETs with no credential: two that must answer, one that must not."""
    terms = rest_anon.get(TERMS)
    line = rest_anon.get(LINE)
    mine = rest_anon.get(MINE)

    problems: list[str] = []
    for name, path, response in (("terms", TERMS, terms), ("the line", LINE, line)):
        if response.status_code != 200:
            problems.append(
                f"the page marks {path} as needing no account, and it answered "
                f"HTTP {response.status_code} to a client carrying no "
                f"credential")

    if mine.status_code == 200:
        problems.append(
            f"{MINE} is marked as needing an account and answered 200 to a "
            f"client carrying no credential, so one reader can see "
            f"applications that are not theirs")
    elif mine.status_code not in REFUSALS:
        problems.append(
            f"{MINE} is marked as needing an account and answered HTTP "
            f"{mine.status_code}, which is neither the refusal the page "
            f"implies nor the 200 it promises a signed-in caller")

    served, listed, counted = None, None, None
    if terms.status_code == 200:
        body = terms.json()
        statuses = body.get("statuses")
        if not isinstance(statuses, dict) or not statuses:
            problems.append(
                "terms carries no `statuses`, which is the vocabulary the page "
                "tells an applicant to expect back from /startups/mine")
        else:
            served = sorted(statuses)
            missing = [s for s in PAGE_STATUSES if s not in statuses]
            if missing:
                problems.append(
                    f"the page prints the application status as "
                    f"{' -> '.join(PAGE_STATUSES)} and terms serves "
                    f"{served}, so {missing} is promised and not served")
        if not isinstance(body.get("token_chains"), dict):
            problems.append(
                "terms carries no `token_chains`, and the page sends a "
                "caller here for the chain names it must send")

    if line.status_code == 200:
        body = line.json()
        rows, counted = body.get("line"), body.get("count")
        listed = len(rows) if isinstance(rows, list) else None
        if listed is None:
            problems.append("the line carries no `line` array to read")
        elif isinstance(counted, int) and counted != listed:
            problems.append(
                f"the line says count {counted} and carries {listed} row(s)")
        if not str(body.get("rules") or "").strip():
            problems.append(
                "the line carries no `rules` text, which is where the auction "
                "states what a bid buys")

    held = ["terms and the line answer a reader with no credential, and "
            f"/startups/mine refuses one with HTTP {mine.status_code}"]
    if served:
        held.append(f"every status the page prints is served: {', '.join(served)}")
    # Said every run, so an empty auction is never mistaken for a tested one.
    held.append(
        f"NOT measured: the ordering rule -- highest bid first, ties by arrival "
        f"-- has {listed if listed is not None else 'no readable'} application(s) "
        f"to order, so nothing about it was asserted")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason="; ".join(problems) if problems else "; ".join(held),
        left={"terms": terms.status_code, "line": line.status_code,
              "mine": mine.status_code},
        right={"statuses_served": served, "page_statuses": list(PAGE_STATUSES),
               "line_rows": listed, "line_count": counted},
        sources={"terms": TERMS, "line": LINE, "mine": MINE},
        population={"applications_in_the_line": listed}))
