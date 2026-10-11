"""Every REST route llms.txt's "## Build it Better" section names is in the OpenAPI (2026-10-11).

The section lists the routes an agent files and steers a request with: the board
(`GET /api/v1/build-it-better/requests`), one ticket, `POST .../requests` to file, and
`POST .../requests/{ticket}/accept|change|verdict|withdraw`, then the traffic reads and the
startup calls. /openapi-public.json, which /api-docs is built from, declares the routes of the
request lifecycle one operation each (the 2026-09 report on the missing Build it Better routes
was fixed that way). The withdraw route is the newest of them: a Telegram answer of 2026-09-26
(Nexus) announced it as a route, the MCP tool `bb_withdraw_request` and a "Withdraw this request"
button, "not yet" in the OpenAPI or llms.txt; llms.txt has it today.

**What was seen when this was written** (2026-10-11 ~14:40 UTC): llms.txt names
`POST .../requests/{ticket}/withdraw` ("takes back your own request while it is requested or
funded"), mcp.json carries `bb_withdraw_request`, the page's own button posts to it (its script
calls `act('/withdraw')`); /openapi-public.json (345 paths) declares accept, change and verdict
and has no withdraw path (the only "withdraw" paths are `cloned-bots/{instance_id}/withdraw` and
`withdrawals/token-gates`); /openapi.json (27 paths) has none of the Build it Better routes.
The /build-it-better/api endpoint table has no withdraw row either. The response schemas stop
at the same place: the 201's `request_token` says it is "the X-BB-Token for
accept/change/verdict" and `yours` lists the same three.

**The rule.** Every `METHOD path` the section names under /api/v1/build-it-better -- written in
full, or as `.../x` (the same prefix), with `a|b` read as one route each -- is a method of a path
of /openapi-public.json, every `{x}` read as one parameter. Passes the moment the withdraw route
is described, whatever its parameter names, summary or response.

NOT asserted: what the schema says about a route, that the route works, or /openapi.json (stated
as context). Websocket URLs and routes the section writes without /api/v1/build-it-better are
not read.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LLMS = "/llms.txt"
OPENAPI = "/openapi-public.json"
OPENAPI_SMALL = "/openapi.json"
PREFIX = "/api/v1/build-it-better"
CLAIM = "build-it-better-rest-routes-are-in-the-openapi"

_HEADING = re.compile(r"(?m)^## Build it Better[ \t]*$")
_ANY_HEADING = re.compile(r"(?m)^## ")
_TICKED = re.compile(r"`([^`]+)`")
_ROUTE = re.compile(
    r"^(?:(GET|POST|PUT|PATCH|DELETE)\s+)?"
    r"(?:https://cymetica\.com)?(" + re.escape(PREFIX) + r"[^\s]*|\.\.\./[^\s]*)$")


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}|<[^>]*>", "{}", path.split("?")[0].rstrip("/"))


def build_it_better_section(llms_text: str) -> str | None:
    """The text of llms.txt's "## Build it Better" section, or None when it is not there."""
    m = _HEADING.search(llms_text or "")
    if not m:
        return None
    rest = llms_text[m.end():]
    n = _ANY_HEADING.search(rest)
    return rest[: n.start()] if n else rest


def named_routes(llms_text: str) -> list[tuple[str, str]]:
    """The (method, path) pairs the section names under PREFIX. A bare path has method '' (any).
    `.../x` is PREFIX + '/x'; an `a|b` in the last segment is one route each."""
    section = build_it_better_section(llms_text)
    if section is None:
        return []
    flat = re.sub(r"\s+", " ", section)
    named: set[tuple[str, str]] = set()
    for span in _TICKED.findall(flat):
        m = _ROUTE.match(span.strip())
        if not m:
            continue
        method, path = m.group(1) or "", m.group(2)
        if path.startswith("..."):
            path = PREFIX + path[3:]
        path = path.split("?")[0].rstrip("/")
        head, _, last = path.rpartition("/")
        for alt in (last.split("|") if "|" in last else [last]):
            named.add((method, _norm(f"{head}/{alt}")))
    return sorted(named)


def missing_from(routes: list[tuple[str, str]], openapi: dict) -> list[tuple[str, str]]:
    """Routes that are not a path of the OpenAPI, or whose method the path does not carry."""
    have: dict[str, set[str]] = {}
    for path, item in ((openapi or {}).get("paths") or {}).items():
        have.setdefault(_norm(path), set()).update(k.upper() for k in (item or {}) if isinstance(k, str))
    out = []
    for method, path in routes:
        methods = have.get(path)
        if methods is None or (method and method not in methods):
            out.append((method, path))
    return out


def _label(route: tuple[str, str]) -> str:
    return " ".join(p for p in route if p)


def _spec(rest_anon, path: str) -> dict:
    r = rest_anon.get(path)
    if r.status_code != 200:
        raise Inconclusive(f"{path} answered HTTP {r.status_code}; a failed read is not an empty document")
    try:
        spec = r.json()
    except ValueError:
        raise Inconclusive(f"{path} is not JSON")
    if not isinstance(spec, dict) or not spec.get("paths"):
        raise Inconclusive(f"{path} carries no paths")
    return spec


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_every_build_it_better_route_llms_txt_names_is_in_the_openapi(rest_anon):
    """llms.txt's Build it Better REST routes against /openapi-public.json's paths and methods."""
    llms = rest_anon.get(LLMS)
    if llms.status_code != 200:
        raise Inconclusive(f"{LLMS} answered HTTP {llms.status_code}")
    routes = named_routes(llms.text)
    if not routes:
        raise Inconclusive(f"{LLMS} names no route under {PREFIX} in its '## Build it Better' section; "
                           f"the section moved or the app is gone")
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
