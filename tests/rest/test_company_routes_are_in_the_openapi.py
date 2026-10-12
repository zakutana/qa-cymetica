"""Every Build a Company route llms.txt names is in the OpenAPI (2026-10-12).

Build a Company (cymetica.com/company, feature #911) is a Manager agent that runs departments of
expert agents for the account owner. Its llms.txt entry names an owner-only API: "Owner-only API
`https://cymetica.com/api/v1/company`: `GET /templates`, `POST /`, `GET /mine`,
`POST /{id}/message` ..., `GET /{id}/messages?after=`, `POST /{id}/approvals/{aid}` ...,
`POST /{id}/pause|resume`, `GET /{id}/audits`", and four MCP tools whose descriptions give the
same routes as their REST twins.

**What was seen when this was written** (2026-10-12 ~13:00 UTC): /openapi-public.json (which
/api-docs is built from) has no path under /api/v1/company at all, and /openapi.json has none
either. The routes answer: `GET /templates` 200 anonymously (five departments), `GET /mine` 401
without a key and 404 {"detail": "no company"} with ours. #191 (Agent Tournaments) and #193
(Build it Better withdraw) were the same shape.

**The rule.** Every `METHOD path` the entry names -- the full URL, or a path relative to it
written in the same line, `POST /` being the URL itself and `a|b` one route each -- is a method
of a path of /openapi-public.json, every `{x}` read as one parameter. Passes the moment they are
described, whatever their parameter names.

NOT asserted: what the schema says about a route, that the route works, or /openapi.json (stated
as context).

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_build_it_better_routes_are_in_the_openapi import _label, _norm, _spec, missing_from

LLMS = "/llms.txt"
OPENAPI = "/openapi-public.json"
OPENAPI_SMALL = "/openapi.json"
PREFIX = "/api/v1/company"
CLAIM = "company-routes-are-in-the-openapi"

_FULL = re.compile(r"`(?:https://cymetica\.com)?" + re.escape(PREFIX) + r"`")
_TICKED = re.compile(r"`(?:(GET|POST|PUT|PATCH|DELETE)\s+)(/[^`\s]*)`")


def company_routes(llms_text: str) -> list[tuple[str, str]]:
    """The (method, path) pairs named in the line that gives PREFIX as a ticked URL: each ticked
    `METHOD /x` is PREFIX + /x (`/` is PREFIX itself), and `a|b` in its last segment one route
    each. A ticked path that already starts with /api/ is taken as written."""
    named: set[tuple[str, str]] = set()
    for line in (llms_text or "").splitlines():
        if not _FULL.search(line):
            continue
        for method, path in _TICKED.findall(line):
            path = path.split("?")[0]
            if not path.startswith("/api/"):
                path = PREFIX + ("" if path == "/" else path)
            path = path.rstrip("/")
            head, _, last = path.rpartition("/")
            for alt in (last.split("|") if "|" in last else [last]):
                named.add((method, _norm(f"{head}/{alt}")))
    return sorted(named)


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_every_company_route_llms_txt_names_is_in_the_openapi(rest_anon):
    """llms.txt's Build a Company routes against /openapi-public.json's paths and methods."""
    llms = rest_anon.get(LLMS)
    if llms.status_code != 200:
        raise Inconclusive(f"{LLMS} answered HTTP {llms.status_code}")
    routes = company_routes(llms.text)
    if not routes:
        raise Inconclusive(f"{LLMS} names no route under {PREFIX}; the entry moved or the app is gone")
    spec = _spec(rest_anon, OPENAPI)
    missing = missing_from(routes, spec)
    small = _spec(rest_anon, OPENAPI_SMALL)
    in_small = [r for r in routes if r not in missing_from(routes, small)]
    named = [_label(r) for r in routes]
    absent = [_label(r) for r in missing]
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{LLMS} names {len(routes)} route(s) under {PREFIX}; {OPENAPI} ({len(spec['paths'])} paths) "
                f"describes {len(routes) - len(missing)} of them. Missing: {', '.join(absent)}. "
                f"{OPENAPI_SMALL} ({len(small['paths'])} paths) describes {len(in_small)}"
                if missing else
                f"all {len(routes)} route(s) {LLMS} names under {PREFIX} are described in {OPENAPI}"),
        left={"routes_missing_from_openapi": len(missing), "routes_named": len(routes)},
        right={"routes_missing_from_openapi": 0},
        population={"named": named, "missing": absent, "openapi_paths": len(spec["paths"]),
                    "in_openapi_json": [_label(r) for r in in_small]},
        sources={"llms": LLMS, "openapi": OPENAPI, "context": OPENAPI_SMALL},
        claim_id=CLAIM))
