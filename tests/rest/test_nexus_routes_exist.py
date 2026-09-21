"""Every REST route Nexus tells an agent to call is a route they publish.

The third of the family. #85 asserts it about the MCP tools their AI names,
#91 about the event cards it names, and this about the HTTP routes: when an
answer says "call `PATCH /api/v1/cloned-bots/{instance_id}/settings`", an
agent that follows it has to find that path in the document it discovers the
platform through.

It exists because on 2026-09-21 an answer did exactly that, and was right. Ten
days of this laboratory reading NEXUS advice had produced one tool that is not
served (#85) and one card that never existed (#91); NEX-0049 named
`PATCH /api/v1/cloned-bots/{instance_id}/settings` as the lever for a clone's
stop-loss, claimed it was "in the public OpenAPI surface and llms.txt, not an
internal/console-only route", and it is -- the path is in openapi-public.json
with a patch operation, and `stop_loss_pct` appears in llms.txt. The same
answer also sent the caller to `update_bot_settings`, the MCP tool #85 is
about, which is neither served nor documented. One answer, both halves.

So the class is worth measuring on the REST side too, and worth measuring
even when it passes: a check that only ever ran on the day it failed tells
nobody whether the fix held.

WHAT IT ASSERTS. Every concrete `/api/v1/...` path named in the newest answer
that names one appears in `openapi-public.json`. Concrete only -- a path with
a `{placeholder}` is matched against the template, and a path we cannot parse
is not evidence of anything.

The NEWEST answer that names a route, not every answer ever recorded, for the
reason #85's own docstring gives: a union over the whole history can only
grow, and it made us send the vendor a verdict about an answer from before
their release.

WHAT IT DOES NOT. Not whether the route works, whether our key reaches it, or
whether the method he named is the one served -- those are separate questions
and two of them are already filed (#89, #98). Only: does the platform publish
the path its own AI is sending agents to.

INCONCLUSIVE when no recorded answer names a route, when the document cannot
be read, or when the newest naming answer is over 24 h old -- an answer from
last week is not a current instruction and their surface moves under it.

SAFE. One GET of a public document, and our own diary.
"""

from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

OPENAPI = "/openapi-public.json"
REPO = Path(__file__).resolve().parent.parent.parent
# `/api/v1/...` as it appears in prose: inside backticks, after a verb, or
# bare. Trailing punctuation is not part of a path.
ROUTE = re.compile(r"/api/v1/[A-Za-z0-9_\-/{}]+")
FRESH_HOURS = 24


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_diary", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def routes_named(text: str) -> set[str]:
    """Concrete API paths an answer tells a caller to use."""
    found = set()
    for raw in ROUTE.findall(text or ""):
        path = raw.rstrip(".,;:)`'\"")
        if len(path) > len("/api/v1/"):
            found.add(path)
    return found


def _templates(document: dict) -> set[str]:
    return {p for p in (document.get("paths") or {})}


def _matches(path: str, templates: set[str]) -> bool:
    """A path matches a published template when the fixed parts line up.

    `{instance_id}` in one and `{id}` in the other are the same segment: the
    name inside the braces is theirs to choose and an agent copying the route
    keeps whatever was written.
    """
    if path in templates:
        return True
    parts = path.strip("/").split("/")
    for template in templates:
        candidate = template.strip("/").split("/")
        if len(candidate) != len(parts):
            continue
        if all(c.startswith("{") or p.startswith("{") or c == p
               for c, p in zip(candidate, parts)):
            return True
    return False


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="rest")
def test_every_route_nexus_tells_an_agent_to_call_is_published(rest_anon):
    """Their AI's newest routed answer, against their own OpenAPI."""
    nexus = _nexus()
    answers = [r for r in nexus.load() if r.get("type") == "answer"]
    dated = sorted([r for r in answers if r.get("text")],
                   key=lambda r: (r.get("at") or "", r.get("id") or ""))
    newest = None
    for row in reversed(dated):
        if routes_named(row["text"]):
            newest = row
            break
    if newest is None:
        raise Inconclusive(
            "no recorded answer names an /api/v1 route, so there is nothing "
            "their AI has sent an agent to that could be missing")

    when = str(newest.get("at") or "")
    try:
        at = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError:
        at = None
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    if at is not None and datetime.now(timezone.utc) - at > timedelta(hours=FRESH_HOURS):
        raise Inconclusive(
            f"the newest answer naming a route, {newest.get('id')} ({when}), "
            f"is over {FRESH_HOURS} h old: it is not a current instruction "
            f"and their surface moves under it")

    document = rest_anon.get(OPENAPI)
    if document.status_code != 200:
        raise Inconclusive(
            f"{OPENAPI} answered HTTP {document.status_code}; a failed read "
            f"is not a document that omits a route")
    try:
        templates = _templates(document.json() or {})
    except ValueError:
        raise Inconclusive(f"{OPENAPI} answered 200 with a body that is not JSON")
    if not templates:
        raise Inconclusive(
            f"{OPENAPI} publishes no paths at all, so nothing can be missing "
            f"from it")

    named = sorted(routes_named(newest["text"]))
    missing = [p for p in named if not _matches(p, templates)]

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{newest.get('id')} sends an agent to "
                f"{', '.join(missing)}, which {OPENAPI} does not publish"
                if missing else
                f"every one of the {len(named)} route(s) {newest.get('id')} "
                f"names is published: {', '.join(named)}"),
        left={"answer": newest.get("id"), "at": when, "routes": named},
        right={"published_paths": len(templates)},
        sources={"their document": OPENAPI, "our diary": "state/nexus.jsonl"},
        population={"routes_named": len(named), "missing": len(missing)}))
