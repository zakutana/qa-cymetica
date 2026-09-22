"""A paper clone their document says will be made is made, or refused for a reason.

The contract is their own entry for `POST /api/v1/cloned-bots/clone` in
`/openapi-public.json`, read 2026-09-22:

    "Clone a bot for the current user. Paper mode clones are free -- no
    deposit required. [...] The cloned bot starts PAUSED."

    requestBody  CloneBotRequest: source_type and source_id required,
                 `paper` / `is_paper` "true = paper clone"
    responses    200 CloneBotResponse, 422 HTTPValidationError -- nothing else

**What was seen when this was written.** CLN-0017, 2026-09-22 13:39:02 UTC: a
paper clone of Perceptron Oracle (wta_species 23441934), the body shape three
other species had been cloned with seconds before (CLN-0014 RSI Sniper and two
more), answered HTTP 400

    {"detail": "Invalid clone request. Please try again."}

The same request again, CLN-0020 at 17:47:14 UTC: the same 400, the same
sentence. This account already holds a paper clone of that species (d778102d,
CLN-0002, 2026-09-10), and a limit of one per species may be the reason -- a
guess, not part of the claim. What the claim is: the refusal tells the caller
to try again, trying again is refused the same way, and neither the 400 nor
any limit appears in their document. An agent reading the answer retries.

Their own refusals elsewhere say why. `/fund`, the sibling route, refused our
key on 2026-09-10 with `{"detail": {"error": {"code": "UNAUTHORIZED",
"message": "Valid JWT token required"}}}`; the MCP filter answers
QUERY_RESTRICTED with a `reason` and a `hint`. #93 is the same distinction on
another door: a refusal that names nothing leaves an agent unable to tell
"you may not" from "ask differently".

**This check places no clone.** It reads what `scripts/clone.py` recorded and
the response each record's evidence id captured -- the capture, not our
record's `response`, which read `{}` for every refusal until 2026-09-22
(`_recorded`, and #89 went out saying "empty body" because of it). Its
subjects are EVERY source a clone of ours was refused on, each judged by its
NEWEST attempt, so a fix is shown by a clone of that source, not by the
calendar:

  * accepted                               -- the clone works: pass
  * refused 4xx, the body asks for a retry, and an earlier attempt at the
    same source was refused with the same body       -- fail
  * refused 4xx with no detail at all                  -- fail
  * refused 4xx with a detail that does not ask for a retry -- pass: the
    refusal now says something other than "again"
  * a first refusal nobody has retried yet, a 5xx, or a capture that cannot
    be read                                            -- unmeasured

It does not decide what the reason should say. A new message, a 409, a
documented limit are all theirs to choose; the one reading it holds is that an
answer asking to be retried is not one a retry refutes.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qa.evidence import EvidenceStore
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
OPENAPI = "/openapi-public.json"
ROUTE = "/api/v1/cloned-bots/clone"
RETRY = "try again"


def _clones():
    spec = importlib.util.spec_from_file_location(
        "clone_records", REPO / "scripts" / "clone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clone_attempts(rows) -> list[dict]:
    """Every clone we attempted -- not a fund, enable or disable -- oldest first."""
    chains: dict[str, dict] = {}
    for row in rows:
        if row.get("id"):
            chains.setdefault(row["id"], {})[row.get("type")] = row
    out = []
    for clone_id, chain in chains.items():
        intent, outcome = chain.get("intent") or {}, chain.get("outcome") or {}
        if not intent or intent.get("kind") or not outcome:
            continue
        if not intent.get("source_id") or outcome.get("outcome") == "not_sent":
            continue
        out.append({"id": clone_id, "at": intent.get("at") or "",
                    "source_id": intent.get("source_id"),
                    "paper": intent.get("paper"),
                    "status": outcome.get("http_status"),
                    "outcome": outcome.get("outcome"),
                    "evidence_id": outcome.get("evidence_id")})
    return sorted(out, key=lambda a: (a["at"], a["id"]))


def _refused(attempt: dict) -> bool:
    status = attempt["status"]
    return isinstance(status, int) and 400 <= status < 500


def _accepted(attempt: dict) -> bool:
    status = attempt["status"]
    return (isinstance(status, int) and 200 <= status < 300
            and attempt["outcome"] == "accepted")


def their_body(attempt: dict):
    """What they answered, from the capture. None when it cannot be read --
    a missing capture is not an empty body."""
    evidence = attempt.get("evidence_id")
    if not evidence:
        return None
    try:
        record = EvidenceStore.load(evidence)
    except (OSError, ValueError):
        return None
    body = (record.get("response") or {}).get("body") or {}
    return body.get("value")


def detail_of(body) -> str:
    """The refusal's words, flattened: `detail` as a string, or the text of
    whatever it nests. Empty when there is nothing to read."""
    if body is None:
        return ""
    detail = body.get("detail") if isinstance(body, dict) else body
    if detail in (None, "", {}, []):
        return ""
    return detail if isinstance(detail, str) else json.dumps(detail, sort_keys=True)


def judge(attempts: list[dict], bodies: dict[str, object]) -> dict:
    """Each refused source by its newest attempt: `breaches`, `passes`,
    `unmeasured`, as lists of (source_id, reason, attempts on it)."""
    newest: dict[str, dict] = {}
    for attempt in attempts:
        newest[attempt["source_id"]] = attempt
    struck = [s for s in newest if any(
        _refused(a) for a in attempts if a["source_id"] == s)]
    out = {"struck": struck, "breaches": [], "passes": [], "unmeasured": []}
    for source in struck:
        mine = [a for a in attempts if a["source_id"] == source]
        latest = mine[-1]
        if _accepted(latest):
            out["passes"].append((source, f"{latest['id']} was accepted", mine))
            continue
        if not _refused(latest):
            out["unmeasured"].append((source, f"{latest['id']} came back "
                                      f"{latest['status']} {latest['outcome']}", mine))
            continue
        body = bodies.get(latest["id"])
        if body is None:
            out["unmeasured"].append((source, f"{latest['id']}'s capture cannot "
                                      f"be read", mine))
            continue
        said = detail_of(body)
        if not said:
            out["breaches"].append((source, f"{latest['id']} was refused HTTP "
                                    f"{latest['status']} with no detail at all "
                                    f"({json.dumps(body)[:120]})", mine))
            continue
        if RETRY not in said.lower():
            out["passes"].append((source, f"{latest['id']} was refused HTTP "
                                  f"{latest['status']} saying {said[:160]!r}", mine))
            continue
        earlier = [a for a in mine[:-1] if _refused(a)
                   and detail_of(bodies.get(a["id"])) == said]
        if not earlier:
            out["unmeasured"].append((source, f"{latest['id']} asks for a retry "
                                      f"and nobody has retried it yet", mine))
            continue
        out["breaches"].append((source, said, mine))
    return out


def _documented(rest) -> str:
    """What their document lists for the route, as a phrase -- or why it
    could not be read. A failed read is not an empty one."""
    spec = rest.get(OPENAPI)
    if spec.status_code != 200:
        return f"{OPENAPI} could not be read (HTTP {spec.status_code})"
    try:
        op = (spec.json().get("paths") or {}).get(ROUTE, {}).get("post") or {}
    except ValueError:
        return f"{OPENAPI} is not JSON"
    codes = sorted((op.get("responses") or {}).keys())
    if not codes:
        return f"{OPENAPI} documents no responses for POST {ROUTE}"
    return f"{OPENAPI} documents POST {ROUTE} as answering {', '.join(codes)}"


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_a_refused_paper_clone_says_why(rest_trusted):
    """Every source a paper clone of ours was refused on, by its newest attempt."""
    attempts = clone_attempts(_clones().load())
    if not attempts:
        raise Inconclusive("no clone has been attempted")
    bodies = {a["id"]: their_body(a) for a in attempts if _refused(a)}
    said = judge(attempts, bodies)
    if not said["struck"]:
        raise Inconclusive("no clone of ours has been refused, so no refusal "
                           "has been read")
    documented = _documented(rest_trusted)

    if said["breaches"]:
        source, detail, mine = said["breaches"][0]
        refused = [a for a in mine if _refused(a)]
        conclude(Measurement(
            verdict="failed",
            reason=(f"a paper clone of wta source {source} was refused HTTP "
                    f"{refused[-1]['status']} {detail!r} {len(refused)} times "
                    f"({', '.join(a['id'] + ' ' + a['at'][:10] + ' ' + a['at'][11:19] for a in refused)} UTC): "
                    f"the refusal asks for a retry and the retry is refused the "
                    f"same way; {documented}"
                    + (f"; {len(said['breaches']) - 1} other source(s) the same"
                       if len(said["breaches"]) > 1 else "")),
            left=detail, right="a clone, or a refusal a retry does not refute",
            population={"attempts_on_source": mine,
                        "other_sources": [s for s, _, _ in said["breaches"][1:]],
                        "evidence": [a["evidence_id"] for a in refused]},
            sources={"contract": f"{OPENAPI} POST {ROUTE}: 'Paper mode clones "
                                 f"are free'; responses 200 and 422",
                     "log": "state/clones.jsonl (CLN intent / outcome, with "
                            "evidence ids; the body read from the capture)"}))
        return
    if said["unmeasured"]:
        raise Inconclusive("; ".join(f"{s}: {why}" for s, why, _ in said["unmeasured"]))
    conclude(Measurement(
        verdict="passed",
        reason=("every source a paper clone of ours was refused on has since "
                "been cloned or refused for a stated reason: "
                + "; ".join(f"{s} ({why})" for s, why, _ in said["passes"])),
        left=[why for _, why, _ in said["passes"]],
        right="a clone, or a refusal a retry does not refute",
        population={"passes": [(s, why) for s, why, _ in said["passes"]]},
        sources={"log": "state/clones.jsonl"}))
