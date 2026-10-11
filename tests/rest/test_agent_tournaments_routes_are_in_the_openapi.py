"""Every Agent Tournaments route llms.txt names is in the OpenAPI (2026-10-11).

Agent Tournaments (cymetica.com/agent-tournaments) is the Build it Better app ET-30773,
shipped 2026-10-10 22:50 UTC. Its llms.txt entry names the API an agent uses to take a seat:
`GET https://cymetica.com/api/v1/agent-tournaments/rules`, then, relative to it, `/lobby`,
`/tables/{id}`, `/tables/{id}/prompt` (no auth), `GET /my-bots`, `POST /tables/{id}/seat` and
`POST /seats/{id}/leave` (X-API-Key). The page's fine print names the same routes.

**What was seen when this was written** (2026-10-11 11:30 UTC): /openapi-public.json (345
paths), which /api-docs is built from, describes none of them; /openapi.json (27 paths) does
not either. The routes answer (rules, lobby and a table 200 anonymously; an unknown table 404
`not_found`), so an agent that reads the schema finds no request or response shape for the
seat it is told to take. #183 was the same shape for one Gem Screener route.

**The rule.** Every route the llms.txt entry names under /api/v1/agent-tournaments -- written
in full, or relative to the first full one in the same entry -- is a path of
/openapi-public.json, with every `{x}` read as one parameter. Passes the moment they are
described, whatever their parameter names.

NOT asserted: what the schema says about each route, or /openapi.json (stated as context).

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LLMS = "/llms.txt"
OPENAPI = "/openapi-public.json"
OPENAPI_SMALL = "/openapi.json"
PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-routes-are-in-the-openapi"

_FULL = re.compile(re.escape(PREFIX) + r"(?:/[A-Za-z0-9_\-{}<>]+)*")
_TICKED = re.compile(r"`(?:(?:GET|POST|PUT|PATCH|DELETE)\s+)?(/[^`\s]*)`")


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}|<[^>]*>", "{}", path.split("?")[0].rstrip("/"))


def tournament_routes(llms_text: str) -> list[str]:
    """The routes the llms.txt entry names under PREFIX: the full ones, and in the line that holds
    a full one, every backticked path relative to it (one starting with '/' but not '/api/')."""
    named = set()
    for line in (llms_text or "").splitlines():
        full = _FULL.findall(line)
        if not full:
            continue
        named.update(_norm(p) for p in full)
        for rel in _TICKED.findall(line):
            if not rel.startswith("/api/"):
                named.add(_norm(PREFIX + rel))
    return sorted(named)


def missing_from(routes: list[str], openapi: dict) -> list[str]:
    have = {_norm(p) for p in (openapi or {}).get("paths") or {}}
    return [r for r in routes if r not in have]


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


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_every_agent_tournaments_route_llms_txt_names_is_in_the_openapi(rest_anon):
    """llms.txt's Agent Tournaments routes against /openapi-public.json's paths."""
    llms = rest_anon.get(LLMS)
    if llms.status_code != 200:
        raise Inconclusive(f"{LLMS} answered HTTP {llms.status_code}")
    routes = tournament_routes(llms.text)
    if not routes:
        raise Inconclusive(f"{LLMS} names no route under {PREFIX}; the entry moved or the app is gone")
    spec = _spec(rest_anon, OPENAPI)
    missing = missing_from(routes, spec)
    small = _spec(rest_anon, OPENAPI_SMALL)
    in_small = [r for r in routes if r not in missing_from(routes, small)]
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{LLMS} names {len(routes)} route(s) under {PREFIX}; {OPENAPI} ({len(spec['paths'])} paths) "
                f"describes {len(routes) - len(missing)} of them. Missing: {', '.join(missing)}. "
                f"{OPENAPI_SMALL} ({len(small['paths'])} paths) describes {len(in_small)}"
                if missing else
                f"all {len(routes)} route(s) {LLMS} names under {PREFIX} are paths of {OPENAPI}"),
        left={"routes_missing_from_openapi": len(missing), "routes_named": len(routes)},
        right={"routes_missing_from_openapi": 0},
        population={"named": routes, "missing": missing, "openapi_paths": len(spec["paths"]),
                    "in_openapi_json": in_small},
        sources={"llms": LLMS, "openapi": OPENAPI, "context": OPENAPI_SMALL},
        claim_id=CLAIM))
