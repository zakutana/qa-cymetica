"""A route their server serves is a route their documents name.

Cloning works. `POST /api/v1/cloned-bots/clone` returned 200 with `is_paper:
true` and no balance movement on 2026-09-10, and the clone came back
`is_trading: false` -- which their own description says is correct: *"The
cloned bot starts PAUSED - user must enable trading."*

Nothing they publish says how to enable it. `openapi-public.json` serves five
routes under `cloned-bots` -- `available`, `clone`, `my-clones`,
`{instance_id}/fund`, `{instance_id}/go-live` -- and none of them starts,
pauses or configures anything. NEXUS, asked directly, tells an agent to call
the MCP tool `update_bot_settings`, which `tools/list` does not serve, and
offers as a fallback a "bot-indicators REST endpoint under /api/v1/cloned-
bots" that is in no path.

**The route exists.** That is the finding, and it is not the one this check
was about to be written for. A GET against a path FastAPI serves for another
method answers 405 and names the method in `Allow`:

    405  GET /api/v1/cloned-bots/{id}           allow: DELETE
    405  GET /api/v1/cloned-bots/{id}/settings  allow: PATCH

So an agent cannot enable trading on the bot the platform just sold it, while
the endpoint that would do it sits one PATCH away and appears nowhere a
machine can read. Deleting a clone is in the same position.

WHY THE PROBE IS A GET AND THE CLAIM IS ONLY ABOUT EXISTENCE. 405 with an
`Allow` header is positive evidence: the router matched the path. A 404 is
not evidence of anything -- it means this path did not match under GET, which
is also what an unrouted path looks like -- so a route that answers 404 here
is left out of the verdict rather than counted as missing. Every claim this
check makes is a claim that something IS served, never that something is not.
That direction is deliberate: of the audit claims this repository has had
rejected at triage, every one asserted an absence.

SAFE. GET only, and against a clone we already own.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

OPENAPI = "/openapi-public.json"
PREFIX = "/api/v1/cloned-bots"

# The operations their own clone description implies a user performs, each as
# the path an agent would try. `{id}` is filled with a clone we own.
PROBES = ["{id}", "{id}/settings", "{id}/fund", "{id}/go-live"]


def served_but_undocumented(probed: dict, documented: set) -> list[dict]:
    """Routes the router matched, minus the ones they publish.

    `probed` maps a concrete path to the `Allow` header of its 405, or to None
    where the path did not answer 405. Only the 405s are evidence, and the
    templated form is what is compared: their documents write `{instance_id}`
    where we send a uuid.
    """
    out = []
    for path, allow in sorted(probed.items()):
        if not allow:
            continue
        tail = path[len(PREFIX):].lstrip("/")
        rest = tail.split("/", 1)[1:]
        template = "/".join(["{instance_id}", *rest])
        if f"{PREFIX}/{template}" not in documented:
            out.append({"path": f"{PREFIX}/{template}",
                        "methods": allow,
                        "probed_as": path})
    return out


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_every_cloned_bot_route_they_serve_is_one_they_document(rest_trusted):
    """A clone starts paused, and the way to start it is unpublished."""
    spec = rest_trusted.get(OPENAPI)
    if spec.status_code != 200:
        raise Inconclusive(
            f"{OPENAPI} answered HTTP {spec.status_code}, so what they "
            f"document could not be read -- a failed read is not an empty one")
    documented = {p for p in (spec.json().get("paths") or {})
                  if p.startswith(PREFIX)}
    if not documented:
        raise Inconclusive(
            f"their openapi names no {PREFIX} path at all, which is a "
            f"different fault from an undocumented one and this check cannot "
            f"tell them apart")

    mine = rest_trusted.get(f"{PREFIX}/my-clones", params={"mode": "paper"})
    rows = mine.json() if mine.status_code == 200 else None
    rows = rows if isinstance(rows, list) else None
    if not rows:
        raise Inconclusive(
            "no paper clone of ours to probe against, so a 404 could not be "
            "told from a wrong id; `python scripts/clone.py clone ...` makes "
            "one, and a paper clone is free")
    clone_id = rows[0].get("id")

    probed = {}
    for shape in PROBES:
        path = f"{PREFIX}/{shape.format(id=clone_id)}"
        response = rest_trusted.get(path)
        # The Allow header IS the evidence. A 405 without one proves the path
        # is routed but names nothing, and is not usable as a finding.
        probed[path] = (response.headers.get("allow")
                        if response.status_code == 405 else None)

    if not any(probed.values()):
        raise Inconclusive(
            "no probe answered 405 with an Allow header, so no route could be "
            "shown to exist -- and this check only ever claims existence")

    hidden = served_but_undocumented(probed, documented)

    conclude(Measurement(
        verdict="failed" if hidden else "passed",
        reason=(
            "their server routes " + ", ".join(
                f"{h['methods']} {h['path']}" for h in hidden)
            + f", and none of those paths is in {OPENAPI}. A clone is created "
              f"paused -- their own description says the user must enable "
              f"trading -- so an agent that clones a bot through the "
              f"documented endpoint cannot start it through any documented "
              f"endpoint, while the one that would do it answers 405 to "
              f"anything but the method it does not publish"
            if hidden else
            f"every {PREFIX} route that answered 405 with an Allow header is "
            f"one of the {len(documented)} they document"),
        left=sorted(h["path"] for h in hidden),
        right=sorted(documented),
        population={"probed": len(probed),
                    "routed": sum(1 for a in probed.values() if a),
                    "documented": len(documented),
                    "undocumented": len(hidden),
                    "clone": clone_id},
        sources={"documented": OPENAPI, "served": f"GET {PREFIX}/... (405)"},
    ))
