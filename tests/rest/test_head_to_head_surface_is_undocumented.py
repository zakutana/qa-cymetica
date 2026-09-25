"""Head-to-head paper matchups answer live and are named in no document a
machine reads.

Both machine-readable schemas link agent builders to the same claim --
`llms.txt` (lines 30, 643) tells a reader to import `/openapi-public.json`
(curated, importable by ChatGPT Custom-GPT Actions and schema-driven tool
layers) or `/openapi.json` ("consumed natively by AWS Bedrock, Azure AI, and
most agent frameworks"). `llms.txt` also names its own REST sections
directly, in prose -- "## REST API" headings for markets, event cards,
agents, movers, cloned bots, launchpads, creator dashboard, and so on.

**What was seen when this was written.** `GET /api/v1/head-to-head/sides`
answers 200 with the callable sides of a matchup (an account's own bot in
paper mode, its paper clones); `GET /api/v1/head-to-head/mine` answers 200
with `{"items": []}` (empty, but 200 -- the shape of an authenticated list
endpoint, not a 404). `GET /api/v1/head-to-head` itself answers 405 with
`Allow: POST`, and `OPTIONS` on `/sides` and `/mine` each answer 405 naming
`GET` -- all three, live router evidence that the route exists (the same
evidence `test_every_cloned_bot_route_they_serve_is_one_they_document` uses
for cloned-bots).

None of `/api/v1/head-to-head`, `/api/v1/head-to-head/sides` or
`/api/v1/head-to-head/mine` appears in `/openapi.json` (13 paths, 0 mention
`head`), `/openapi-public.json` (173 paths, 0 mention `head`), or the text of
`llms.txt` (71 KB, no case-insensitive match for `head-to-head`, `head to
head`, `h2h`, `matchup`, `versus`, `sides`, or `duel`, including the U+2011
non-breaking hyphen). An agent reading either schema, or the prose that tells
it which schema to import, cannot discover this surface exists at all --
distinct from the cloned-bots finding, where the routes were served but the
one that starts a bot was merely missing a method; here the whole feature is
absent from every document.

WHY THE PROBE IS GET AND OPTIONS, NOT POST. The mutating route,
`POST /api/v1/head-to-head` (creating a matchup), is out of scope for this
suite -- MUTATE tier, off by default. What is claimed here is only that the
paths exist and are routed, which GET, OPTIONS and their status codes prove
without ever placing a matchup.

SAFE. GET and OPTIONS only; /mine and /sides read our own account's state.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

OPENAPI_SMALL = "/openapi.json"
OPENAPI_CURATED = "/openapi-public.json"
LLMS = "/llms.txt"

PREFIX = "/api/v1/head-to-head"
PROBE_PATHS = (PREFIX, f"{PREFIX}/sides", f"{PREFIX}/mine")



def _routed(response) -> str | None:
    """The `Allow` header of a 405, or None. 405-with-Allow is router
    evidence; a 2xx is stronger evidence still and is read directly by the
    caller, never through this helper."""
    if response.status_code == 405:
        return response.headers.get("allow")
    return None


@qa(component="rest.head_to_head", tier=SafetyTier.SAFE, surface="rest",
    claim="head-to-head-surface-is-documented")
def test_the_head_to_head_routes_they_serve_are_named_in_no_document(rest_trusted):
    """GET/OPTIONS evidence that the three routes are live, against both
    OpenAPI documents and llms.txt."""
    small = rest_trusted.get(OPENAPI_SMALL)
    curated = rest_trusted.get(OPENAPI_CURATED)
    llms = rest_trusted.get(LLMS)
    unread = [name for name, resp in
              ((OPENAPI_SMALL, small), (OPENAPI_CURATED, curated), (LLMS, llms))
              if resp.status_code != 200]
    if unread:
        raise Inconclusive(
            f"{', '.join(unread)} could not be read (non-200), so whether "
            f"they document this surface was not measured -- a failed read "
            f"is not an empty read")

    small_paths = set((small.json().get("paths") or {}).keys())
    curated_paths = set((curated.json().get("paths") or {}).keys())
    llms_text = llms.text.replace("‑", "-")

    # A03, deep pass of 2026-09-24 (3/3): "documented" was any OpenAPI path
    # containing "head", or "matchup"/"duel" anywhere in llms.txt -- an
    # unrelated /headlines route passed it while these three stayed unnamed.
    # Each route is documented only where its own path is: a key of either
    # OpenAPI document, or the path written out in llms.txt.
    def named_in(path: str) -> list[str]:
        return ([OPENAPI_SMALL] if path in small_paths else []) + \
               ([OPENAPI_CURATED] if path in curated_paths else []) + \
               ([LLMS] if re.search(re.escape(path) + r"(?![\w/-])", llms_text)
                else [])
    small_hit = any(p in small_paths for p in PROBE_PATHS)
    curated_hit = any(p in curated_paths for p in PROBE_PATHS)
    llms_hit = [p for p in PROBE_PATHS if LLMS in named_in(p)]

    # Live evidence: GET first (a 2xx is direct proof), OPTIONS where GET
    # named no method (the same fallback the cloned-bots check uses).
    served, unread = {}, []
    for path in PROBE_PATHS:
        get = rest_trusted.get(path)
        if get.status_code == 200:
            served[path] = "200 (GET)"
            continue
        allow = _routed(get)
        if not allow:
            opt = rest_trusted.options(path)
            allow = _routed(opt)
        if allow:
            served[path] = f"405, Allow: {allow}"
        elif get.status_code in (401, 403, 429) or get.status_code >= 500:
            # Neither proof the route exists nor that it is gone: a failed
            # read is not an absent route (rule 8; deep pass 2026-09-25, A06).
            unread.append(f"{path} (HTTP {get.status_code})")

    if not served:
        raise Inconclusive(
            f"none of {', '.join(PROBE_PATHS)} answered 200 or a 405 with an "
            f"Allow header, so no route could be shown to exist -- this "
            f"check only ever claims existence")

    unnamed = [p for p in served if not named_in(p)]
    documented = not unnamed
    if documented and unread:
        raise Inconclusive(f"every route that answered is documented, but "
                           f"{len(unread)} did not answer: {', '.join(unread)}")
    conclude(Measurement(
        verdict="passed" if documented else "failed",
        reason=(
            f"{len(unnamed)} of the {len(served)} live head-to-head route(s) "
            f"({', '.join(f'{p} -> {served[p]}' for p in unnamed)}) "
            f"appear(s) in neither {OPENAPI_SMALL} ({len(small_paths)} paths), "
            f"{OPENAPI_CURATED} ({len(curated_paths)} paths), nor {LLMS} "
            f"({len(llms.text)} chars) by its own path -- undiscoverable "
            f"to an agent that reads only what those documents tell it to"
            if not documented else
            "every live head-to-head route is named by its own path: "
            + "; ".join(f"{p} in {', '.join(named_in(p))}" for p in served)
        ),
        left=sorted(unnamed), right=[],
        population={"served_routes": served,
                    "openapi_json_paths": len(small_paths),
                    "openapi_public_paths": len(curated_paths),
                    "llms_txt_chars": len(llms.text),
                    "llms_txt_hits": llms_hit},
        sources={"contract": "llms.txt lines 30/643 point agent builders at "
                              "openapi.json / openapi-public.json for the "
                              "REST surface; llms.txt itself names every "
                              "other REST section in prose",
                 "small": OPENAPI_SMALL, "curated": OPENAPI_CURATED,
                 "llms": LLMS},
        claim_id="head-to-head-surface-is-documented",
    ))
