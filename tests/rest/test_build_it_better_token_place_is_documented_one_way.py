"""llms.txt and the OpenAPI say the same place for the Build it Better request token (2026-10-11).

Filing a request returns a one-time `request_token`; its holder (or the account that filed it)
may then accept, change, give a verdict on or withdraw the request. llms.txt's "## Build it
Better" section writes the REST routes as

    `POST .../requests/{ticket}/accept|change|verdict|withdraw` (request token in the body)

while /openapi-public.json declares, on accept, change and verdict, an optional `x-bb-token`
header parameter and nothing token-shaped in the request body (`accept` has no body;
`BBChangeIn` is `{changes}`, `BBVerdictIn` is `{verdict, note}`), and the 201's `request_token`
says "it is the X-BB-Token for accept/change/verdict". The /build-it-better/api table says
"X-BB-Token, or the signed-in session of the account that filed it" on the same three, and the
page's own script sets `hdr['X-BB-Token']` before every one of them.

**What was seen when this was written** (2026-10-11 ~14:40 UTC): the two documents name different
places -- llms.txt "the body", the OpenAPI "a header". Two documents of one API that disagree
mislead whoever follows the shorter one.

**The rule.** For each of the routes llms.txt writes that sentence for, which /openapi-public.json
describes (a route it does not describe is read by the routes check, not here), the place the
sentence names (body, header) and the places the OpenAPI declares for that route (the X-BB-Token
header parameter; a token-named property of the request body schema) share at least one.
Passes when the sentence is changed to name the header, when the OpenAPI declares a body token, or
when each names both; passes while llms.txt states no place.

NOT asserted: which place the server accepts (we send no write here), or that either is right --
only that the two published statements can both be followed.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_build_it_better_routes_are_in_the_openapi import (
    LLMS, OPENAPI, PREFIX, _norm, _spec, build_it_better_section)

CLAIM = "build-it-better-request-token-place-is-documented-one-way"
API_PAGE = "/build-it-better/api"

# `POST .../requests/{ticket}/accept|change|verdict|withdraw` (request token in the body) -- the words
# after the route: its parenthesis, or else the clause up to the next backtick or sentence end, so
# "... -- the request token goes in the body" says the place too (deep pass 2026-10-11, C04).
_SENTENCE = re.compile(
    r"`(?:POST\s+)?(?:\.\.\.|" + re.escape(PREFIX) + r")/requests/\{[^}]*\}/([a-z|]+)`\s*"
    r"(?:\(([^)]*)\)|([^`.;]*))")
_HEADER = re.compile(r"header|x-bb-token", re.I)
_BODY = re.compile(r"\bbody\b|\bjson\b|\bpayload\b", re.I)
# A place is the token's only when the words name the token: "(JSON body {changes})" is the body's
# shape, not where the token goes (C05).
_TOKEN = re.compile(r"token", re.I)


def llms_token_sentence(llms_text: str) -> dict | None:
    """The routes llms.txt's Build it Better section writes as `.../requests/{ticket}/a|b|c` and the
    places each one's parenthetical names: {'ops': [...every op named], 'per_op': {op: {places}} for
    the ops that state one, 'phrase': the first parenthetical, 'places': all places stated}, or None
    when the section has no such line."""
    section = build_it_better_section(llms_text)
    if section is None:
        return None
    ops, per_op, phrase = [], {}, None
    for m in _SENTENCE.finditer(re.sub(r"\s+", " ", section)):
        names = m.group(1).split("|")
        ops.extend(o for o in names if o not in ops)
        said = (m.group(2) if m.group(2) is not None else m.group(3) or "").strip()
        places = set()
        if _TOKEN.search(said):
            if _BODY.search(said):
                places.add("body")
            if _HEADER.search(said):
                places.add("header")
        if places:
            phrase = phrase or said
            for o in names:
                per_op.setdefault(o, set()).update(places)
    if not ops:
        return None
    return {"ops": ops, "per_op": per_op, "phrase": phrase,
            "places": set().union(*per_op.values()) if per_op else set()}


def _deref(spec: dict, node):
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 8:
        target = spec
        for part in str(node["$ref"]).lstrip("#/").split("/"):
            target = (target or {}).get(part)
        node, seen = target, seen + 1
    return node if isinstance(node, dict) else {}


def openapi_token_places(spec: dict, op: str) -> dict | None:
    """Where the OpenAPI says the token for POST {PREFIX}/requests/{ticket}/<op> goes:
    {'places': {...}, 'header': name|None, 'body_fields': [...]}, or None when it does not
    describe the route."""
    want = _norm(f"{PREFIX}/requests/{{ticket}}/{op}")
    for path, item in ((spec or {}).get("paths") or {}).items():
        if _norm(path) != want:
            continue
        post = _deref(spec, (item or {}).get("post"))
        if not post:
            return None
        places, header, fields = set(), None, []
        for raw in (post.get("parameters") or []) + ((item or {}).get("parameters") or []):
            p = _deref(spec, raw)
            if p.get("in") == "header" and "bb-token" in str(p.get("name", "")).lower().replace("_", "-"):
                places.add("header")
                header = p.get("name")
        content = _deref(spec, post.get("requestBody")).get("content") or {}
        for media in content.values():
            schema = _deref(spec, (media or {}).get("schema"))
            for branch in [schema] + [_deref(spec, b) for b in (schema.get("anyOf") or schema.get("oneOf") or [])]:
                for name in (branch.get("properties") or {}):
                    if "token" in name.lower():
                        places.add("body")
                        fields.append(name)
        return {"places": places, "header": header, "body_fields": sorted(set(fields))}
    return None


def disagreements(sentence: dict, spec: dict) -> dict:
    """{'judged': {op: places}, 'unread': [ops], 'mismatched': {op: places}} for one sentence."""
    judged, unread, mismatched = {}, [], {}
    for op in sentence["ops"]:
        got = openapi_token_places(spec, op)
        if got is None or not got["places"]:
            unread.append(op)
            continue
        judged[op] = sorted(got["places"])
        stated = sentence["per_op"].get(op)
        if stated and not (stated & got["places"]):
            mismatched[op] = sorted(got["places"])
    return {"judged": judged, "unread": unread, "mismatched": mismatched}


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_llms_txt_and_the_openapi_name_the_same_place_for_the_request_token(rest_anon):
    """The place llms.txt gives for the request token against the OpenAPI's, route by route."""
    llms = rest_anon.get(LLMS)
    if llms.status_code != 200:
        raise Inconclusive(f"{LLMS} answered HTTP {llms.status_code}")
    sentence = llms_token_sentence(llms.text)
    if sentence is None:
        raise Inconclusive(f"{LLMS} has no `.../requests/{{ticket}}/accept|...` line in its '## Build it "
                           f"Better' section; the section moved or the app is gone")
    spec = _spec(rest_anon, OPENAPI)
    found = disagreements(sentence, spec)
    if not sentence["places"]:
        conclude(Measurement(
            verdict="passed",
            reason=f"{LLMS} states no place for the request token on {', '.join(sentence['ops'])} "
                   f"(its parenthetical: {sentence['phrase']!r}); nothing to contradict",
            population={"sentence": sentence["phrase"], "openapi": found["judged"]},
            sources={"llms": LLMS, "openapi": OPENAPI}, claim_id=CLAIM))
        return
    if not found["judged"]:
        raise Inconclusive(f"{OPENAPI} declares a token place for none of {', '.join(sentence['ops'])}; "
                           f"there is nothing to compare the sentence with")

    # Context, not judged: what the API page says (a failed read changes nothing).
    page = rest_anon.get(API_PAGE)
    page_header = bool(page.status_code == 200 and re.search(r"X-BB-Token", page.text or "", re.I))
    mismatched = found["mismatched"]
    said = " and ".join(sorted(sentence["places"]))
    conclude(Measurement(
        verdict="failed" if mismatched else "passed",
        reason=(f"{LLMS} says the request token goes in the {said} ({sentence['phrase']!r}) for "
                f"{', '.join(sentence['ops'])}; {OPENAPI} declares "
                + "; ".join(f"{op}: {'/'.join(v)}" for op, v in sorted(mismatched.items()))
                + f" and nothing in the {said}. {API_PAGE} "
                  f"{'also names X-BB-Token' if page_header else 'was not read for it'}"
                if mismatched else
                f"{LLMS} ({sentence['phrase']!r}) and {OPENAPI} share a place for the request token on "
                f"{', '.join(sorted(found['judged']))}"),
        left={"llms_places": sorted(sentence["places"]), "routes_with_another_place": len(mismatched)},
        right={"routes_with_another_place": 0},
        population={"sentence": sentence["phrase"], "ops": sentence["ops"], "openapi": found["judged"],
                    "unread_in_openapi": found["unread"], "api_page_names_x_bb_token": page_header},
        sources={"llms": LLMS, "openapi": OPENAPI, "context": API_PAGE},
        claim_id=CLAIM))
