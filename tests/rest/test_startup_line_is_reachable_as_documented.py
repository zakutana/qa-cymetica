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

import html
import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PAGE = "/build-it-better/api"
TERMS = "/api/v1/build-it-better/startups/terms"
LINE = "/api/v1/build-it-better/startups/line"
MINE = "/api/v1/build-it-better/startups/mine"
# One row of their table: method, the path as the page writes it, the Auth
# cell. A13, deep pass of 2026-09-22: the Auth column is the contract, and
# until then the check read our own copy of it, never their page.
ROW = re.compile(r'<tr><td><span class="m">(GET|POST)</span>\s*<code>([^<]+)</code>'
                 r'</td><td>.*?</td><td>(.*?)</td></tr>', re.S)


def page_auth(page: str) -> dict[str, str]:
    """GET path on the page -> "public" (a dash) or "account", read off the
    Auth cell. A cell that is neither is left out: not a contract we read."""
    out = {}
    for method, path, cell in ROW.findall(page or ""):
        text = html.unescape(re.sub(r"<[^>]+>", "", cell)).strip().lower()
        if method != "GET":
            continue
        if text in ("-", "–", "—", ""):
            out[path.strip()] = "public"
        elif text.startswith("account"):
            out[path.strip()] = "account"
    return out
# The four the page printed as the status of an application on 2026-09-21, in
# its own order -- kept for the record. The check reads the page's own words
# (page_statuses) since A05, deep pass of 2026-09-22 evening: our copy made a
# page and an endpoint that changed together read as a promise not served.
PAGE_STATUSES = ("submitted", "reviewing", "accepted", "declined")
# Read off the text once the tags are gone -- their markup puts every word in
# its own <code>, so "status" and its colon arrive a space apart.
STATUS_LINE = re.compile(r"status\s*:\s*([a-z_]+(?:\s*(?:→|->|\|)\s*[a-z_]+)+)", re.I)
REFUSALS = (401, 403)


def page_statuses(page: str) -> tuple[str, ...] | None:
    """The application statuses the page prints ("submitted → reviewing →
    accepted | declined"), in its order, or None when it prints none."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", page or ""))
    found = STATUS_LINE.search(text)
    if not found:
        return None
    return tuple(w.lower() for w in re.findall(r"[a-z_]+", found.group(1), re.I))


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_startup_calls_answer_the_reader_their_own_page_promises(rest_anon):
    """Three GETs with no credential: two that must answer, one that must not."""
    terms = rest_anon.get(TERMS)
    line = rest_anon.get(LINE)
    mine = rest_anon.get(MINE)

    # Each status is triaged for what it SAYS. A public call that demands a
    # key is the defect the Auth column names; a 404 is the other one the
    # docstring keeps apart from it, a route the page documents and nobody
    # serves. Anything else -- a 429 of our budget, a 5xx of their restart --
    # is a read that failed, and went out as "answered HTTP 429 to a client
    # carrying no credential" (A09, deep pass of 2026-09-21). Rule 8.
    document = rest_anon.get(PAGE)
    auth = page_auth(document.text if document.status_code == 200 else "")
    subjects = (("terms", TERMS, terms), ("the line", LINE, line),
                ("/startups/mine", MINE, mine))
    unlisted = [path for _, path, _ in subjects
                if path.split("/build-it-better", 1)[-1] not in auth]
    if unlisted:
        raise Inconclusive(
            f"their page {PAGE} (HTTP {document.status_code}) marks no Auth "
            f"for {', '.join(unlisted)}, so there is no published contract to "
            f"hold these calls to")

    problems: list[str] = []
    unread: list[str] = []
    for name, path, response in subjects:
        code = response.status_code
        if auth[path.split("/build-it-better", 1)[-1]] == "public":
            if code in REFUSALS:
                problems.append(
                    f"the page marks {path} as needing no account, and it "
                    f"answered HTTP {code} to a client carrying no credential")
            elif code == 404:
                problems.append(
                    f"the page documents {path} as a call needing no account, "
                    f"and it answered HTTP 404: the route it sends a reader to "
                    f"does not exist")
            elif code != 200:
                unread.append(f"{name} ({path}) answered HTTP {code}")
        elif code == 200:
            problems.append(
                f"{path} is marked as needing an account and answered 200 to "
                f"a client carrying no credential, so one reader can see "
                f"applications that are not theirs")
        elif code == 404:
            problems.append(
                f"{path} is marked as needing an account and answered HTTP "
                f"{code}, which is neither the refusal the page implies nor "
                f"the 200 it promises a signed-in caller")
        elif code not in REFUSALS:
            unread.append(f"{name} ({path}) answered HTTP {code}")

    served, listed, counted, printed = None, None, None, None
    if terms.status_code == 200:
        body = terms.json()
        statuses = body.get("statuses")
        if not isinstance(statuses, dict) or not statuses:
            problems.append(
                "terms carries no `statuses`, which is the vocabulary the page "
                "tells an applicant to expect back from /startups/mine")
        else:
            served = sorted(statuses)
            printed = page_statuses(document.text if document.status_code == 200 else "")
            if printed is None:
                unread.append(f"the page {PAGE} prints no application status "
                              f"vocabulary to hold terms' statuses to")
            else:
                missing = [s for s in printed if s not in statuses]
                if missing:
                    problems.append(
                        f"the page prints the application status as "
                        f"{' -> '.join(printed)} and terms serves "
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
        elif not isinstance(counted, int) or isinstance(counted, bool):
            # The docstring's item 1 names `count`; a line without one passed
            # (A05, deep pass of 2026-09-22 evening).
            problems.append(f"the line carries no `count` (got {counted!r}), "
                            f"which the page promises beside the line itself")
        elif counted != listed:
            problems.append(
                f"the line says count {counted} and carries {listed} row(s)")
        if not str(body.get("rules") or "").strip():
            problems.append(
                "the line carries no `rules` text, which is where the auction "
                "states what a bid buys")

    # A defect measured on one call stands whatever else was lost; with none,
    # an unread call leaves the claim about all three unanswered -- and the
    # passing sentence below would say it was read.
    if unread and not problems:
        raise Inconclusive(
            "; ".join(unread) + " -- a failed read is neither a call that "
            "demands a key nor one that refuses a stranger")

    held = ["each call answers a reader with no credential as the page's Auth "
            "column says: " + ", ".join(
                f"{path.rsplit('/', 1)[-1]} ({auth[path.split('/build-it-better', 1)[-1]]}) "
                f"HTTP {response.status_code}" for _, path, response in subjects)]
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
        right={"statuses_served": served,
               "page_statuses": list(printed) if printed else None,
               "line_rows": listed, "line_count": counted},
        sources={"terms": TERMS, "line": LINE, "mine": MINE},
        population={"applications_in_the_line": listed, "unread": unread}))
