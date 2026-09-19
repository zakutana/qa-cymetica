"""A public GET in one published OpenAPI document is in the other one too.

`llms.txt` links two machine-readable schemas for the same API:

    line 30:  [Curated OpenAPI](https://cymetica.com/openapi-public.json)
              -- Machine-readable public REST schema (importable by ChatGPT
              Custom-GPT Actions and schema-driven tool layers)
    line 643: [OpenAPI Specification](/openapi.json): Machine-readable API schema

and its own advice to platforms (line 572) is to publish `/openapi.json`
because it is "consumed natively by AWS Bedrock, Azure AI, and most agent
frameworks". So an agent builder will import one or the other, and which one
they pick should not change which endpoints exist.

**What was seen when this was written.** `/openapi.json` declared 13 paths,
`/openapi-public.json` 109, and only 5 were in both. Eight paths were in the
small document alone. Five of those are private or not GETs at all (401 on
`/account/me/balances` and `/account/me/portfolio`, 405 on `/agents/clone`,
`/backtest/bots/{slug}/run-backtest`, `/funding/withdraw`) and a *public*
schema may leave those out. Three answered 200 to an anonymous GET and were
still missing from the curated one: `/api/v1/prices`, `/api/v1/arena/market`,
`/api/v1/clob/book/hybrid`.

**That asymmetry is what is measured**, and only in that direction: a path in
the curated document but not in `/openapi.json` is not counted, because the
curated one is the larger, deliberately assembled list and 104 such paths
would drown the finding. This check asks one thing -- if your own small
schema declares a GET and that GET is public, is it in the document you tell
agent builders to import?

A path that needs a key (401/403), that is not a GET (405), or that we cannot
read at all is not counted: a private endpoint is allowed to be absent from a
public schema, and a failed read is not an empty read (rule 8). Path
templates carrying `{...}` are skipped rather than guessed at.
"""

from __future__ import annotations

import json

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SMALL = "/openapi.json"
CURATED = "/openapi-public.json"


def _paths(rest, where: str) -> set[str] | None:
    """The path set of one published document, or None when it cannot be read."""
    response = rest.get(where)
    if response.status_code != 200:
        return None
    try:
        document = response.json()
    except json.JSONDecodeError:
        return None
    paths = document.get("paths")
    return set(paths) if isinstance(paths, dict) else None


@qa(component="discovery.openapi", tier=SafetyTier.SAFE, surface="rest",
    claim="published-openapi-documents-agree")
def test_a_public_get_in_openapi_json_is_in_the_curated_schema_too(rest_anon):
    """Paths only in /openapi.json, probed anonymously, against the curated one."""
    small = _paths(rest_anon, SMALL)
    curated = _paths(rest_anon, CURATED)
    if small is None or curated is None:
        missing = [name for name, value in ((SMALL, small), (CURATED, curated))
                   if value is None]
        raise Inconclusive(f"{missing} could not be read as an OpenAPI document, "
                           f"so the two cannot be compared")

    only_small = sorted(p for p in small - curated if "{" not in p)
    templated = sorted(p for p in small - curated if "{" in p)

    public_and_absent, not_public, unreadable = [], [], []
    for path in only_small:
        response = rest_anon.get(path)
        code = response.status_code
        if code == 200:
            public_and_absent.append(path)
        elif code in (401, 403, 404, 405):
            not_public.append(f"{path} ({code})")
        else:
            unreadable.append(f"{path} ({code})")

    conclude(Measurement(
        verdict="failed" if public_and_absent else "passed",
        reason=(f"{len(public_and_absent)} path(s) answer an anonymous GET and "
                f"are declared in {SMALL} but not in {CURATED}, the schema "
                f"llms.txt tells agent builders to import: "
                f"{', '.join(public_and_absent)}"
                if public_and_absent else
                f"every public GET declared in {SMALL} is also in {CURATED} "
                f"({len(small)} vs {len(curated)} paths, "
                f"{len(not_public)} of the difference private or not a GET)"),
        left=public_and_absent, right=[],
        population={"openapi_json": len(small), "openapi_public": len(curated),
                    "shared": len(small & curated),
                    "only_in_openapi_json": only_small,
                    "not_public": not_public, "templated_skipped": templated,
                    "unreadable": unreadable},
        sources={"contract": "llms.txt lines 30 and 643, both linking a "
                             "machine-readable schema for the same API",
                 "small": SMALL, "curated": CURATED},
        claim_id="published-openapi-documents-agree"))
