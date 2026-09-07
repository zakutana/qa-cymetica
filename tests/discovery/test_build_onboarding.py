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
RECIPE = re.compile(r'data-i18n="build\.recipe_[a-z_]+"\s*>(.*?)</', re.S)

# A path as an agent would read one out of an instruction: leading slash, not
# preceded by a word character or another slash (so "https://x/y" and "$25" are
# not mistaken for one).
PATH_IN_PROSE = re.compile(r"(?<![\w/])/[a-z][\w.-]*(?:/[\w.{}-]+)*")

# "Save the returned api_key and send it as X-API-Key on every call."
# The sentence is the anchor; the FIELD NAME is read out of it, never assumed.
#
# Read from tag-stripped prose, not from the markup. The first version of this
# matched over the raw HTML and an intervening <code> tag left it holding
# "_key" -- a field name that appears nowhere, on its way into a sentence
# addressed to the vendor. Extract from text, anchor on markup, never both.
FIELD_TO_SAVE = re.compile(r"Save the returned\s+([a-z][a-z_]{2,})", re.I)

TAG = re.compile(r"<[^>]+>")

# "climb the trust ladder (PUBLIC -> RECOGNIZED -> TRUSTED -> ALLIED)"
LADDER_ON_PAGE = re.compile(r"trust ladder\s*\(([^)]{4,120})\)", re.I)

# "Register via MCP for trust-based access levels (Public, Authenticated, ...)"
LADDER_IN_LLMS = re.compile(r"access levels\s*\(([^)]{4,120})\)", re.I)

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
    return frozenset(
        part.strip().lower()
        for part in RUNG_SEPARATORS.split(text)
        if part.strip()
    )


@qa(component="discovery.onboarding", tier=SafetyTier.SAFE, surface="discovery",
    claim="build-recipe-names-a-browser-route")
def test_every_route_a_recipe_names_is_reachable_as_an_api(rest_anon):
    """A path in an agent-facing recipe must be one an agent can call.

    Either it is in the curated schema the page tells ChatGPT users to import,
    or it answers JSON. A browser route in a list of things to command an agent
    to do is a dead end for the HTTP callers the same page invites ("raw HTTP
    agents start at /llms.txt").
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

    named = sorted({m for recipe in recipes
                    for m in PATH_IN_PROSE.findall(_prose(recipe))})
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
        if response.status_code == 200 and "json" in content_type:
            continue
        unreachable[path] = f"HTTP {response.status_code} {content_type.split(';')[0]}"

    reason = (
        f"a /build recipe sends an agent to a route that is not in the curated "
        f"schema and does not answer JSON: "
        + ", ".join(f"{p} ({w})" for p, w in sorted(unreachable.items()))
    ) if unreachable else (
        f"every path named in a /build recipe is callable: "
        f"{len(named)} checked against {len(documented)} documented paths"
    )

    conclude(Measurement(
        verdict="failed" if unreachable else "passed",
        reason=reason,
        left=sorted(unreachable), right=sorted(named),
        population={"recipes": len(recipes), "paths_named": len(named),
                    "documented_paths": len(documented)},
        sources={"page": BUILD, "schema": OPENAPI}))


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
