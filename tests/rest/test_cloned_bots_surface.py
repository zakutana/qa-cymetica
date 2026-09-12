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

import re

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
    # Their parameter NAME is not part of the contract. The templated form was
    # built with the literal `{instance_id}` and compared against their path
    # keys verbatim, so renaming the parameter to `{clone_id}` in openapi -- a
    # documentation-only change -- would have made two routes they document
    # read as served-but-undocumented, and this check sends that to them. What
    # is being asserted is that the ROUTE is documented, so both sides are
    # normalised to one placeholder first. 3/3, deep pass of 2026-09-13.
    def shape(route: str) -> str:
        return re.sub(r"\{[^}]*\}", "{}", route)

    by_shape = {shape(route): route for route in documented}
    out = []
    for path, allow in sorted(probed.items()):
        if not allow:
            continue
        tail = path[len(PREFIX):].lstrip("/")
        rest = tail.split("/", 1)[1:]
        template = f"{PREFIX}/" + "/".join(["{instance_id}", *rest])
        if shape(template) not in by_shape:
            out.append({"path": template,
                        "methods": allow,
                        "probed_as": path})
    return out


def _credential_headers(op: dict, schemes: dict) -> set:
    """The headers an operation authenticates with: its header parameters,
    and the headers its `security` requirement resolves to. Until the deep
    pass of 2026-09-11 only the parameters were read, so a route whose auth
    is declared through `security` had none and was skipped as public (V10,
    triage 3/3)."""
    headers = {q.get("name") for q in (op.get("parameters") or [])
               if q.get("in") == "header"}
    for requirement in op.get("security") or []:
        for name in (requirement or {}):
            scheme = (schemes or {}).get(name) or {}
            if scheme.get("type") == "apiKey" and scheme.get("in") == "header":
                headers.add(scheme.get("name"))
            elif scheme.get("type") in ("http", "oauth2", "openIdConnect"):
                headers.add("authorization")
    return {h for h in headers if h}


# The steps that move a clone forward, reported separately so the reason can
# say which refusal blocks the flow the docstring names. NOT the verdict.
#
# C03 of the 2026-09-13 pass was right that the verdict should not fail on a
# route outside the flow -- a documented user-only DELETE would have sent them
# a `fail` on a row they have paid for twice. The fix that narrowed the VERDICT
# to these two segments was wrong and the full run caught it within the hour:
# their `/fund` is fixed and publishes `x-api-key`, and the route still
# refusing it is `GET /api/v1/cloned-bots/{instance_id}/activity` -- which is
# what #89/#98 is currently about. Narrowing to fund/go-live turned a live,
# filed, twice-paid finding into `passed`, and `verify.py` would have sent that
# pass. An agent reading its own clone's activity is inside the flow by any
# honest reading; "moves the clone forward" was my boundary, not theirs.
#
# So the verdict reads `refuses` as it always did, and the narrower criterion
# waits for one we can actually read off their document. See DEEP-PASS.md.
MOVES_THE_CLONE = ("fund", "go-live")


def credential_gap(paths: dict, schemes: dict | None = None) -> dict:
    """Which cloned-bots routes accept the agent credential, and which do not.

    A comparison between their own routes, not an assertion that a header is
    missing. `clone` and `my-clones` document `x-api-key` beside
    `authorization`; `fund` and `go-live` document only `authorization`. Those
    four are steps of one flow, so the difference is the finding, and it is
    stated as a difference rather than as an absence.

    `blocked` is the subset of `refuses` that is a step of that flow, and it is
    what the verdict reads. Everything else stays in `refuses` and is reported,
    because a route outside the flow refusing the agent credential is worth
    seeing and is not worth a `fail`.
    """
    accepts, refuses = {}, {}
    for path, ops in sorted(paths.items()):
        for method, op in sorted(ops.items()):
            if method.upper() not in ("GET", "POST", "PATCH", "DELETE"):
                continue
            headers = _credential_headers(op, schemes)
            if not headers:
                continue  # public, and not part of the credential question
            (accepts if "x-api-key" in headers else refuses)[
                f"{method.upper()} {path}"] = sorted(headers)
    blocked = {route: headers for route, headers in refuses.items()
               if route.rsplit("/", 1)[-1] in MOVES_THE_CLONE}
    return {"accepts": accepts, "refuses": refuses, "blocked": blocked}


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_one_credential_carries_a_clone_from_creation_to_funding(rest_trusted):
    """An agent that can clone a bot can put money in it.

    Measured 2026-09-10, with the API key their own documents tell an agent to
    use: `POST /api/v1/cloned-bots/clone` returned 200 and created
    d778102d in paper; `POST /api/v1/cloned-bots/d778102d/fund` with
    {"amount": 1.0} returned **401 with an empty body**.

    The clone arrives with a practice balance of 0.00 -- their own UI card
    shows it beside a Fund button -- so a bot that cannot be funded cannot
    trade. An agent following the documented path therefore gets a bot it
    owns, can see, and can never start.

    This reads the credential question off their own document rather than off
    the 401, so it is a comparison between their routes: two steps of one flow
    publish `x-api-key`, two do not. The live 401 is what makes the difference
    consequential rather than cosmetic, and it is in the report.
    """
    spec = rest_trusted.get(OPENAPI)
    if spec.status_code != 200:
        raise Inconclusive(
            f"{OPENAPI} answered HTTP {spec.status_code}; a failed read is "
            f"not an empty document")
    paths = {p: ops for p, ops in (spec.json().get("paths") or {}).items()
             if p.startswith(PREFIX)}
    if not paths:
        raise Inconclusive(f"their openapi names no {PREFIX} path at all")

    schemes = (spec.json().get("components") or {}).get("securitySchemes") or {}
    gap = credential_gap(paths, schemes)
    if not gap["accepts"]:
        raise Inconclusive(
            f"no {PREFIX} route documents x-api-key, so there is no agent "
            f"credential on this surface to be inconsistent with -- a "
            f"different fault, and not the one this check reads")

    funds = [r for r in gap["blocked"] if r.rsplit("/", 1)[-1] == "fund"]
    aside = sorted(set(gap["refuses"]) - set(gap["blocked"]))
    conclude(Measurement(
        verdict="failed" if gap["refuses"] else "passed",
        reason=(
            f"{len(gap['accepts'])} cloned-bots route(s) accept the agent's "
            f"x-api-key and {len(gap['refuses'])} do not: "
            + ", ".join(sorted(gap["refuses"]))
            # What their document says, and nothing this check did not read:
            # the live 401 it used to assert here was never measured by any
            # branch (V10, deep pass of 2026-09-11).
            + (". A clone is created with a practice balance of 0.00, so an "
               "agent that authenticates the documented way can create a bot "
               "and, by their own document, cannot put money in it"
               if funds else
               ". The funding route is not among them, so a clone can be "
               "created and paid for with the agent credential; what that "
               "same credential cannot reach is the route named above")
            + (f" ({len(gap['blocked'])} of them a step that moves the clone "
               f"forward)" if gap["blocked"] else "")
            if gap["refuses"] else
            f"every step of the clone-to-funding flow accepts the same agent "
            f"credential; {len(gap['accepts'])} route(s) publish it"
            + (f", and {len(aside)} authenticated route(s) outside the flow do "
               f"not, which is theirs to decide: {', '.join(aside)}"
               if aside else "")),
        left=sorted(gap["refuses"]),
        right=sorted(gap["accepts"]),
        population={"authenticated_routes":
                    len(gap["accepts"]) + len(gap["refuses"]),
                    "accept_api_key": len(gap["accepts"]),
                    "authorization_only": len(gap["refuses"]),
                    "blocked_flow_steps": sorted(gap["blocked"]),
                    "outside_the_flow": aside},
        sources={"documented": OPENAPI},
    ))


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
            hidden_reason(hidden)
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


# The routes that start or configure a bot. An agent that cannot find one of
# THESE cannot start the clone it made; one that cannot find a DELETE can.
STARTS = ("/settings", "/toggle-trading", "/go-live")


def hidden_reason(hidden: list[dict]) -> str:
    """The failure sentence for routes they serve and do not document.

    "Cannot start it through any documented endpoint" only when a hidden
    route is one that starts or configures the bot. Until the deep pass of
    2026-09-11 every hidden route got that sentence, so an undocumented
    DELETE beside a documented toggle would have sent a false claim about
    starting (V11, triage 3/3).
    """
    listed = ", ".join(f"{h['methods']} {h['path']}" for h in hidden)
    text = f"their server routes {listed}, and none of those paths is in {OPENAPI}"
    if any(str(h.get("path", "")).endswith(STARTS) for h in hidden):
        return text + (
            ". A clone is created paused -- their own description says the "
            "user must enable trading -- so an agent that clones a bot through "
            "the documented endpoint cannot start it through any documented "
            "endpoint, while the one that would do it answers 405 to anything "
            "but the method it does not publish")
    return text + ". An agent that reads their document cannot know these exist"
