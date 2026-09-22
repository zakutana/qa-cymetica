"""A request example on /api-docs carries the fields its route requires.

The contract is between two of their own documents. `/api-docs` shows, for
each write it documents, a `curl` an agent can copy; `/openapi-public.json` is
the schema llms.txt tells agent builders to import, and for each route it
names the request body's `required` fields. An example that leaves one out is
a request the route refuses (422), copied from the page that teaches it.

**What was seen when this was written** (2026-09-22, 18:0x UTC): of the ten
`curl` examples on /api-docs that send a JSON body, the one for
`POST /api/v1/cloned-bots/clone` sends

    {"bot_id": "bot_abc123", "is_paper": true}

while CloneBotRequest requires `source_type` and `source_id` and has no
`bot_id`. The example's response block (`clone_id`, `simulated_balance:
10000.00`, `status: "active"`) is not what the route returns either --
llms.txt: "starts PAUSED with 0 balance" -- but a response example is prose
about an outcome, and this check holds only the request, which is
mechanically comparable.

**What it reads.** Every `<div class="code-block">` on the page -- anchored
on the markup, read as text after the tags are gone, because a `<span>`
inside a JSON body is how a regex over raw HTML captures the wrong thing.
Each `curl -X POST|PUT|PATCH https://cymetica.com/api/...` with a `-d '{...}'`
body is matched to a route and method in the openapi; its schema's `required`
fields must all be present. An example for a route the openapi does not
publish, or whose body does not parse, is counted and not judged -- that is
`test_the_two_openapi_documents_agree`'s business, or nobody's.

SAFE. Two anonymous GETs.
"""

from __future__ import annotations

import html
import json
import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PAGE = "/api-docs"
OPENAPI = "/openapi-public.json"
BLOCK = re.compile(r'<div class="code-block"[^>]*>(.*?)</div>', re.S)
CURL = re.compile(
    r"curl\s+-X\s+(POST|PUT|PATCH)\s+https://cymetica\.com(/api/[^\s\\'\"?]+)"
    r"(.*?)(?=curl\s+-X|\Z)", re.S)
BODY = re.compile(r"-d\s+'(\{.*?\})'", re.S)


def examples(page: str) -> list[dict]:
    """Every documented write with a JSON body: method, path, body (or the
    raw text when it does not parse)."""
    out = []
    for block in BLOCK.findall(page):
        text = html.unescape(re.sub(r"<[^>]+>", "", block))
        for method, path, rest in CURL.findall(text):
            found = BODY.search(rest)
            if not found:
                continue
            try:
                body = json.loads(found.group(1))
            except json.JSONDecodeError:
                body = None
            out.append({"method": method, "path": path, "body": body,
                        "raw": " ".join(found.group(1).split())[:200]})
    return out


def route_of(spec: dict, path: str, method: str):
    """The openapi route and operation a concrete path answers, or (None, None)."""
    for route, ops in (spec.get("paths") or {}).items():
        pattern = "^" + re.sub(r"\{[^}]+\}", "[^/]+", re.escape(route)
                               .replace(r"\{", "{").replace(r"\}", "}")) + "$"
        if re.match(pattern, path) and method.lower() in (ops or {}):
            return route, ops[method.lower()]
    return None, None


def required_of(spec: dict, operation: dict) -> tuple[list[str], set[str]]:
    """The body's required fields and every field it names, from the schema."""
    content = ((operation.get("requestBody") or {}).get("content") or {})
    schema = (content.get("application/json") or {}).get("schema") or {}
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = ((spec.get("components") or {}).get("schemas") or {}).get(name) or {}
    return list(schema.get("required") or []), set((schema.get("properties") or {}))


def judge(page: str, spec: dict) -> dict:
    found = examples(page)
    out = {"examples": len(found), "breaches": [], "held": [],
           "unpublished": [], "unparsed": []}
    for ex in found:
        where = f"{ex['method']} {ex['path']}"
        if ex["body"] is None:
            out["unparsed"].append(f"{where}: {ex['raw']}")
            continue
        route, operation = route_of(spec, ex["path"], ex["method"])
        if route is None:
            out["unpublished"].append(where)
            continue
        required, named = required_of(spec, operation)
        missing = [f for f in required if f not in ex["body"]]
        if missing:
            out["breaches"].append({
                "example": where, "route": route, "missing": missing,
                "sends": sorted(ex["body"]),
                "not_in_schema": sorted(k for k in ex["body"] if named and k not in named)})
        else:
            out["held"].append(where)
    return out


@qa(component="discovery.openapi", tier=SafetyTier.SAFE, surface="rest")
def test_every_request_example_on_api_docs_carries_what_its_route_requires(rest_anon):
    """Each /api-docs curl body, against the required fields of its openapi route."""
    page = rest_anon.get(PAGE)
    spec = rest_anon.get(OPENAPI)
    if page.status_code != 200 or spec.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code} and {OPENAPI} "
                           f"HTTP {spec.status_code}; a failed read is not an "
                           f"example that holds")
    try:
        document = spec.json()
    except ValueError:
        raise Inconclusive(f"{OPENAPI} is not JSON")
    said = judge(page.text, document)
    if not said["examples"]:
        raise Inconclusive(f"no curl example with a JSON body was found on {PAGE}: "
                           f"the page changed shape, or this reader broke -- "
                           f"either way nothing was compared")
    judged = len(said["breaches"]) + len(said["held"])
    if not judged:
        raise Inconclusive(f"{said['examples']} example(s) found and none targets "
                           f"a route {OPENAPI} publishes with a readable body")
    first = said["breaches"][0] if said["breaches"] else None
    conclude(Measurement(
        verdict="failed" if first else "passed",
        reason=(f"{len(said['breaches'])} of {judged} request example(s) on {PAGE} "
                f"leave out a field {OPENAPI} requires: {first['example']} sends "
                f"{first['sends']} and its schema requires {first['missing']}"
                + (f" ({first['not_in_schema']} are not in the schema at all)"
                   if first["not_in_schema"] else "")
                if first else
                f"all {judged} request example(s) on {PAGE} that target a "
                f"published route carry every field it requires"),
        left=[b["example"] for b in said["breaches"]], right=[],
        population=said,
        sources={"page": PAGE, "schema": OPENAPI,
                 "contract": "llms.txt names /openapi-public.json as the schema "
                             "to import; /api-docs shows the curl to copy"}))
