"""What /build promises an agent, held against what the machine surfaces say.

/build is the page they point outside agents at: one paste that registers you,
names the endpoints to call, and tells you which field of the reply to keep. It
is therefore a CONTRACT with a reader who cannot ask a follow-up question, and
every sentence of it that names a path, a field or a tier is checkable.

Three things are checked here, and each is anchored to a PLACE in the page --
one of their own `data-i18n` keys -- rather than to the words found there on the
day it was written. That is the lesson from claims.yaml: a check that compares
two particular sentences goes green when the publisher deletes one of them.
Anchor missing => inconclusive, never passed.

What is deliberately NOT checked: whether an agent can complete the onboarding.
It cannot be, from here. POST /mcp/v1/register is probe_only -- creating an
account is the operator's action, not ours -- so everything below reads
documents. A check that needed a real registration would be a check we could
never run.
"""

from __future__ import annotations

import json
import re
from html import unescape

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

BUILD = "/build"
OPENAPI = "/openapi-public.json"
LLMS = "/llms.txt"
MANIFEST = "/.well-known/mcp.json"
REGISTER = "/mcp/v1/register"

# The recipes list. Their markup, their i18n keys: every <li> under
# "What to command it to do" carries data-i18n="build.recipe_<something>", and
# the text of the recipe is whatever follows until the tag closes.
#
# Anchored here rather than on the <pre> block that holds the copy-paste
# prompt, because every path in THAT block resolves. A check pointed at the
# prose that is correct would have passed beside the sentence that is not.
RECIPE = re.compile(r'data-i18n="build\.recipe_[a-z_]+"\s*>(.*?)</(?:span|b|li)>', re.S)

# A path as an agent would read one out of an instruction: leading slash, not
# preceded by a word character or another slash (so "https://x/y" and "$25" are
# not mistaken for one).
PATH_IN_PROSE = re.compile(r"(?<![\w/])/[a-z][\w.-]*(?:/[\w.{}-]+)*")

# A recipe can name a path in order to say it is NOT for agents, and one now
# does. #76 was filed because the trade recipe read "search /events/universe
# for an asset, quote it, place a $25 limit buy" -- an instruction. Their fix
# moved the instruction to find_trade_path and the symbols search, and left the
# path in an aside: "/events/universe is the same catalogue as a page for
# humans." Reading every path in the recipe as an instruction reports that
# sentence as the defect it replaced, which is what happened on 2026-09-08.
#
# So the SENTENCE is the unit, not the recipe. A sentence that says its path is
# for people is not sending an agent anywhere; one that says "search
# /events/universe for an asset" still is, and still fails.
FOR_PEOPLE = re.compile(r"\bfor humans\b|\bhuman page\b|\bfor people\b"
                        r"|\bin a browser\b|\bbrowser page\b", re.I)

SENTENCE = re.compile(r"(?<=\.)\s+")

# "Save the returned api_key and send it as X-API-Key on every call."
# The sentence is the anchor; the FIELD NAME is read out of it, never assumed.
#
# Read from tag-stripped prose, not from the markup. The first version of this
# matched over the raw HTML and an intervening <code> tag left it holding
# "_key" -- a field name that appears nowhere, on its way into a sentence
# addressed to the vendor. Extract from text, anchor on markup, never both.
FIELD_TO_SAVE = re.compile(r"Save the returned\s+([a-z][a-z_]{2,})", re.I)

TAG = re.compile(r"<[^>]+>")

# "climb the trust ladder (PUBLIC -> RECOGNIZED -> TRUSTED -> ALLIED)", and
# after their 2026-09-07 fix "(unknown -> recognized -> trusted -> allied --
# the trust_tiers keys in /.well-known/mcp.json; your rung is trust_level on
# GET /mcp/v1/agents/me)". The parenthetical now carries an explanation after
# the rungs, so the cap is wide enough to match it and RUNGS_ONLY cuts the
# prose off. At 120 characters this stopped matching the moment they answered
# the report, and the fix would have reached us as an inconclusive.
LADDER_ON_PAGE = re.compile(r"trust ladder\s*\(([^)]{4,400})\)", re.I)

# Only the rung list: whatever precedes the first em dash, semicolon or " -- ".
RUNGS_ONLY = re.compile(r"^(.*?)(?:—|;| -- |:|\))")

# Both forms they have published: the old parenthesised list
# "access levels (Public, Authenticated, Federated, Allied)" and, after the
# 2026-09-07 fix, a colon with the explanation moved into the parenthesis:
# "access levels: unknown -> recognized -> trusted -> allied (the trust_tiers
# keys in /.well-known/mcp.json...)". Anchored on the phrase, tolerant of what
# introduces the list, and stopping before the parenthetical.
LADDER_IN_LLMS = re.compile(r"access levels[:\s]*\(?\s*([^(\n]{4,200})", re.I)

# Rungs are separated by commas on one surface and by U+2192 arrows on the
# other. qa.extractors.regex_set splits on [,\s]+ only, so it would return the
# arrow as a rung; this splits on both and compares the words.
RUNG_SEPARATORS = re.compile(r"[,\s→>-]+")


def _fetch(rest, path):
    """The body, or a reason it could not be read. Never a silent empty."""
    response = rest.get(path)
    if response.status_code != 200:
        return None, f"{path} answered HTTP {response.status_code}"
    return response, None


def _openapi(rest):
    response, why = _fetch(rest, OPENAPI)
    if response is None:
        return None, why
    try:
        return response.json(), None
    except ValueError:
        return None, f"{OPENAPI} did not parse as JSON ({len(response.text)} bytes)"


def _prose(html):
    """The page as a reader sees it: tags out, entities in, spaces collapsed."""
    return re.sub(r"\s+", " ", unescape(TAG.sub(" ", html)))


def _rungs(text):
    """The rung names in a stated ladder, or None if this does not read as one.

    The shape test is the point. Without it any parenthetical after the phrase
    became "the rungs": "trust ladder (see the docs)" would have been filed to
    the vendor as the three surfaces disagreeing. A capture that is not a short
    list of single bare words is something else, and something else is
    inconclusive, not a defect.
    """
    head = RUNGS_ONLY.match(text)
    rungs = frozenset(
        part.strip().lower()
        for part in RUNG_SEPARATORS.split(head.group(1) if head else text)
        if part.strip()
    )
    if not 2 <= len(rungs) <= 8:
        return None
    if any(not r.isalpha() for r in rungs):
        return None
    return rungs


@qa(component="discovery.onboarding", tier=SafetyTier.SAFE, surface="discovery",
    claim="build-recipe-names-a-browser-route")
def test_every_route_a_recipe_names_is_reachable_as_an_api(rest_anon):
    """A path a recipe SENDS AN AGENT TO must be one an agent can call.

    Either it is in the curated schema the page tells ChatGPT users to import,
    or it answers JSON. A browser route in a list of things to command an agent
    to do is a dead end for the HTTP callers the same page invites ("raw HTTP
    agents start at /llms.txt").

    Sends an agent to, not merely mentions: a sentence that says its path is a
    page for people is describing the catalogue, not routing a caller at it.
    That distinction is the difference between #76 and #76's fix, and the
    excluded paths are named in the verdict so the exclusion is never silent.
    """
    page, why = _fetch(rest_anon, BUILD)
    if page is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"page": BUILD}))
        return

    recipes = RECIPE.findall(page.text)
    if not recipes:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no element of /build carries a data-i18n=\"build.recipe_*\" "
                   "key, so the recipes this check reads were not on the page",
            population={"page_bytes": len(page.text)},
            sources={"page": BUILD}))
        return

    sentences = [s for recipe in recipes
                 for s in SENTENCE.split(_prose(recipe)) if s.strip()]
    named = sorted({m for s in sentences if not FOR_PEOPLE.search(s)
                    for m in PATH_IN_PROSE.findall(s)})
    # Kept and reported, never dropped in silence: a check that quietly stops
    # looking at something is indistinguishable from one that looked and found
    # nothing, and this exclusion is the whole reason the check can pass today.
    for_people = sorted({m for s in sentences if FOR_PEOPLE.search(s)
                         for m in PATH_IN_PROSE.findall(s)} - set(named))
    if not named:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the {len(recipes)} recipes on /build name no path at all, "
                   f"so there was nothing to resolve",
            population={"recipes": len(recipes)}, sources={"page": BUILD}))
        return

    spec, why = _openapi(rest_anon)
    if spec is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"schema": OPENAPI}))
        return

    documented = set(spec.get("paths") or {})
    unreachable = {}
    for path in named:
        if path in documented:
            continue
        response = rest_anon.get(path)
        content_type = response.headers.get("content-type", "")
        status = response.status_code
        # An AUTH answer means the API is there and this caller is anonymous:
        # 401 application/json on a route absent from the public schema is a
        # route the key-holding agent this page creates can call, and filing
        # that would be a sentence its own parenthesis refutes. Audit,
        # 2026-09-07.
        #
        # But the repair that widened it dropped the status entirely, and this
        # platform answers 404 in application/json -- our own evidence store
        # holds GET /api/v1/cloned-bot/create -> 404 {"detail":"Not Found"} and
        # dozens like it. So a recipe naming a stale or misspelled path, the
        # commonest form of the very defect #76 exists for, passed under the
        # sentence "every path a /build recipe sends an agent to is callable".
        # Deep pass, 2026-09-08, three auditors and three triage agents.
        #
        # A transient is neither: it says nothing about the route, so the check
        # cannot conclude from it at all.
        if status == 429 or status >= 500:
            conclude(Measurement(
                verdict="inconclusive",
                reason=f"{path} answered HTTP {status}, which says nothing "
                       f"about whether the route exists; nothing established",
                sources={"page": BUILD, "path": path}))
            return
        if "json" in content_type and status in (200, 201, 401, 403):
            continue
        unreachable[path] = f"HTTP {status} {content_type.split(';')[0]}"

    reason = (
        f"a /build recipe sends an agent to a route that is not in the curated "
        f"schema and does not answer JSON: "
        + ", ".join(f"{p} ({w})" for p, w in sorted(unreachable.items()))
    ) if unreachable else (
        f"every path a /build recipe sends an agent to is callable: "
        f"{len(named)} checked against {len(documented)} documented paths"
        + (f"; {', '.join(for_people)} named as being for people, not called"
           if for_people else "")
    )

    conclude(Measurement(
        verdict="failed" if unreachable else "passed",
        reason=reason,
        left=sorted(unreachable), right=sorted(named),
        population={"recipes": len(recipes), "paths_named": len(named),
                    "paths_named_for_people": len(for_people),
                    "documented_paths": len(documented)},
        sources={"page": BUILD, "schema": OPENAPI}))


@qa(component="discovery.onboarding", tier=SafetyTier.SAFE, surface="discovery")
def test_a_recipe_that_routes_an_agent_is_still_told_from_one_that_does_not():
    """The repair above, pinned. Offline: two sentences, no network.

    Narrowing a check the day its finding is fixed is how a check quietly stops
    catching the thing it was written for. So both halves are held here: #76's
    sentence as filed must still read as routing an agent at /events/universe,
    and their fix must not. If a later edit widens FOR_PEOPLE until the first
    one is excluded too, this fails rather than the sweep going green on a
    defect that came back.
    """
    def routed(text):
        parts = [s for s in SENTENCE.split(text) if s.strip()]
        return sorted({p for s in parts if not FOR_PEOPLE.search(s)
                       for p in PATH_IN_PROSE.findall(s)})

    as_filed = '— "search /events/universe for an asset, quote it, place a buy."'
    as_fixed = ("raw HTTP agents search GET /api/v1/event-cards/symbols/search"
                "?q=<asset> (JSON). /events/universe is the same catalogue as "
                "a page for humans.")

    assert "/events/universe" in routed(as_filed), (
        "the sentence #76 was filed for must still read as an instruction"
    )
    assert "/events/universe" not in routed(as_fixed)
    assert "/api/v1/event-cards/symbols/search" in routed(as_fixed), (
        "the instruction in the same recipe must still be read and checked"
    )


@qa(component="discovery.onboarding", tier=SafetyTier.SAFE, surface="discovery",
    claim="register-response-undocumented")
def test_register_response_documents_the_field_the_page_says_to_save(rest_anon):
    """The field /build tells you to keep must exist in the published schema.

    /build names one field of the registration reply and tells the reader to
    save it. The same page tells ChatGPT users to import openapi-public.json as
    a Custom GPT Action schema. Those two sentences are only consistent if the
    schema describes the response the first one talks about.
    """
    page, why = _fetch(rest_anon, BUILD)
    if page is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"page": BUILD}))
        return

    told_to_save = FIELD_TO_SAVE.search(_prose(page.text))
    if not told_to_save:
        conclude(Measurement(
            verdict="inconclusive",
            reason="/build no longer tells a reader to save a named field out "
                   "of the registration reply, so there is no claim to settle",
            population={"page_bytes": len(page.text)}, sources={"page": BUILD}))
        return
    field = told_to_save.group(1)

    spec, why = _openapi(rest_anon)
    if spec is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"schema": OPENAPI}))
        return

    operation = (spec.get("paths") or {}).get(REGISTER, {}).get("post")
    if operation is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{OPENAPI} documents no POST {REGISTER}, so the response "
                   f"/build describes has no schema to disagree with",
            sources={"schema": OPENAPI}))
        return

    described = set()
    for status, response in (operation.get("responses") or {}).items():
        if not str(status).startswith("2"):
            continue
        schema = ((response.get("content") or {})
                  .get("application/json") or {}).get("schema") or {}
        while "$ref" in schema:
            target = spec
            for step in schema["$ref"].lstrip("#/").split("/"):
                target = target.get(step, {})
            schema = target
        described |= set(schema.get("properties") or {})

    reason = (
        f"the field /build tells an agent to save is absent from the published "
        f"schema for the call that returns it: {field!r} is in no 2xx response "
        f"of POST {REGISTER}, which describes {len(described)} field(s)"
    ) if field not in described else (
        f"POST {REGISTER} documents the field /build says to save: {field!r}"
    )

    conclude(Measurement(
        verdict="failed" if field not in described else "passed",
        reason=reason,
        left=field, right=sorted(described),
        population={"described_fields": len(described)},
        sources={"page": BUILD, "schema": OPENAPI}))


@qa(component="discovery.onboarding", tier=SafetyTier.SAFE, surface="discovery",
    claim="trust-ladder-vocabulary")
def test_trust_ladder_rungs_agree_across_surfaces(rest_anon):
    """One ladder, named the same way everywhere an agent can read it.

    mcp.json is the surface that DECIDES: its per-tool trust_tier is what
    tools/list gates on, and what the regression check for report #46 reads. So
    the prose surfaces are held against it rather than against each other.

    Compared lowercased. The rungs disagreeing in capitalisation alone would be
    nothing worth anyone's time; what this fails on is different words.
    """
    page, why = _fetch(rest_anon, BUILD)
    if page is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"page": BUILD}))
        return
    on_page = LADDER_ON_PAGE.search(_prose(page.text))

    llms, why = _fetch(rest_anon, LLMS)
    if llms is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"document": LLMS}))
        return
    in_llms = LADDER_IN_LLMS.search(llms.text)

    manifest, why = _fetch(rest_anon, MANIFEST)
    if manifest is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"manifest": MANIFEST}))
        return
    try:
        tools = manifest.json().get("tools") or []
    except ValueError:
        tools = []
    served = frozenset(str(t.get("trust_tier")).lower()
                       for t in tools if t.get("trust_tier"))

    missing = [name for name, found in
               (("/build", on_page), ("llms.txt", in_llms), ("mcp.json", served))
               if not found]
    if missing:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the trust ladder is not stated where this check reads it: "
                   f"{', '.join(missing)}",
            population={"tools": len(tools)},
            sources={"page": BUILD, "document": LLMS, "manifest": MANIFEST}))
        return

    stated = {"/build": _rungs(on_page.group(1)),
              "llms.txt": _rungs(in_llms.group(1)),
              "mcp.json": served}
    unreadable = [where for where, rungs in stated.items() if rungs is None]
    if unreadable:
        # The anchor matched but what followed is not a ladder. Saying the
        # surfaces disagree on the strength of that would be a defect filed out
        # of a sentence that names no rungs.
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"the text this check reads as the ladder does not read as "
                    f"a list of rungs on {', '.join(unreadable)}, so the "
                    f"surfaces were not compared"),
            left=[where for where in unreadable],
            right={k: sorted(v) if v else None for k, v in stated.items()},
            sources={"page": BUILD, "document": LLMS, "manifest": MANIFEST}))
        return
    agree = len({frozenset(v) for v in stated.values()}) == 1

    reason = (
        "the same trust ladder is named differently on each surface an agent "
        "reads, so an agent cannot tell which rung it holds: "
        + "; ".join(f"{where} says {sorted(rungs)}"
                    for where, rungs in stated.items())
    ) if not agree else (
        f"every surface names the same rungs: {sorted(served)}"
    )

    conclude(Measurement(
        verdict="failed" if not agree else "passed",
        reason=reason,
        left=sorted(stated["mcp.json"]),
        right=json.dumps({k: sorted(v) for k, v in stated.items()}, sort_keys=True),
        population={"tools": len(tools), "surfaces": len(stated)},
        sources={"page": BUILD, "document": LLMS, "manifest": MANIFEST}))
