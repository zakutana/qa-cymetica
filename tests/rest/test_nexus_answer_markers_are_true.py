"""The markers their resolver writes into a Nexus answer are true, and leave the answer usable.

The sequel to #85 and #91. Their fix for #91 (a2a reply, journal seq 1705, release 9b1ab755c,
2026-09-11) put a resolver in front of every deep answer: "an id that would 404 for you is
marked `[not available: this card id does not resolve on the public API - do not trade it]`",
tools are marked `[not available on the MCP surface]` or `[no such tool]`, and "existing
stored answers are re-resolved at serve time". A second marker, `[not served: this path does
not take PATCH; it takes DELETE]`, is in no reply of theirs and in no live document.

NEX-0142 (2026-10-12 21:49 UTC, the question was about our own paper clone, Agent
Tournaments table 5, seat 29) shows both of them misfiring, and it still does on a live
re-read of its job:

  1. `update_bot_settings with instance_id 692c35b3-... [not available: this card id does
     not resolve on the public API - do not trade it]`. That id is a bot instance, the
     answer's own words call it one, and our key lists it in /cloned-bots/my-clones. It was
     never a card, and "do not trade it" is said about the clone the question is about.
  2. `PATCH /api/v1/cloned-bots/692c35b3-... [not served: this path does not take PATCH; it
     takes DELETE] .../settings`, and the same with GET before `/balance`. The marker judges
     the prefix `/api/v1/cloned-bots/{instance_id}` (DELETE only) while the route the
     sentence names is `PATCH .../{instance_id}/settings`, which openapi-public.json serves
     (and `GET .../{instance_id}/balance`). A served route is called not served.
  3. Each marker pair is written twice inside the one path, so the path an agent would copy
     is broken by the text in the middle of it.

WHAT IT ASSERTS. On the newest recorded answer that carries a marker, re-read from their
server by its job id (the markers are applied at serve time, so a re-read is what a fix
changes): no `not available` marker sits on an id that is one of our bot instances (what
my-clones lists, and every clone our own record says was accepted: C10, 2026-10-18); no `not
served` marker names a method that the document serves on the path the sentence names; no
marker sits inside a path, and none is written twice in a row.

WHAT IT DOES NOT. Whether the platform is right to mark a card id that really 404s (that is
#91's fix working), and whether Nexus's advice is good. A re-read with no marker in it
passes, and says it was empty: #85 and #91 judge the other direction.

INCONCLUSIVE when no recorded answer has a marker, the job cannot be read back as done, or
the OpenAPI document cannot be read.

SAFE. A get_deep_answer poll, GET /openapi-public.json, GET /cloned-bots/my-clones.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
OPENAPI = "/openapi-public.json"
MY_CLONES = "/api/v1/cloned-bots/my-clones"
METHODS = ("get", "post", "put", "patch", "delete")

UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
MARK = re.compile(r"\s?\[(not available|not served)([^\]]*)\]")
# A path with at least one marker right behind it, and whatever of the path comes after the
# marker: `/api/v1/cloned-bots/<id> [marker] [marker]/settings`.
PATH_RUN = re.compile(
    r"(?P<head>/api/v1(?:/[A-Za-z0-9_\-{}<>]+)*)"
    r"(?P<marks>(?:\s?\[not (?:available|served)[^\]]*\])+)"
    r"(?P<tail>(?:/[A-Za-z0-9_\-{}]+)*)")
ID_RUN = re.compile(rf"(?P<id>{UUID_RE})(?P<marks>(?:[`'\"]?\s?\[not available[^\]]*\])+)")
TAKES = re.compile(r"does not take ([A-Z]+)")


def _nexus():
    spec = importlib.util.spec_from_file_location("nexus_markers", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clone_record() -> list[dict]:
    """Our own clone record (scripts/clone.py), read-only."""
    spec = importlib.util.spec_from_file_location("clone_markers", REPO / "scripts" / "clone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load()


def has_marker(text: str) -> bool:
    return bool(MARK.search(text or ""))


def served_methods(document: dict, path: str) -> set[str]:
    """The methods the document publishes on the template(s) `path` fills."""
    from tests.rest.test_nexus_routes_exist import _matches

    out: set[str] = set()
    for template, item in (document.get("paths") or {}).items():
        if isinstance(item, dict) and _matches(path, {template}):
            out |= {m.upper() for m in item if m.lower() in METHODS}
    return out


def our_instances(live_rows, recorded_rows) -> set[str]:
    """Every bot instance id that is ours, lower-cased: what my-clones lists now, and every clone our
    own record says the platform accepted -- a clone released since is still the one his answer named
    (NEX-0142's 692c35b3). C10, deep pass 2026-10-18: this replaces judging any id the answer's words
    called a bot, which went past the contract (a marker on one of OUR instances)."""
    ids = {str(r.get("instance_id") or r.get("id")).lower()
           for r in live_rows or [] if isinstance(r, dict) and (r.get("instance_id") or r.get("id"))}
    ids |= {str(r["clone_instance_id"]).lower() for r in recorded_rows or []
            if isinstance(r, dict) and r.get("type") == "outcome" and r.get("outcome") == "accepted"
            and r.get("clone_instance_id")}
    return ids


def misfires(text: str, document: dict, instances: set[str]) -> dict:
    """What is wrong with the markers in `text`, judged against what the platform says."""
    out = {"marked_instances": [], "served_but_marked": [], "split_paths": [],
           "repeated": [], "markers": len(MARK.findall(text or ""))}
    for hit in ID_RUN.finditer(text or ""):
        if hit["id"].lower() in instances and hit["id"] not in out["marked_instances"]:
            out["marked_instances"].append(hit["id"])
    for hit in PATH_RUN.finditer(text or ""):
        full = hit["head"] + hit["tail"]
        marks = MARK.findall(hit["marks"])
        if hit["tail"] and full not in out["split_paths"]:
            out["split_paths"].append(full)
        if len(marks) != len(set(marks)):
            out["repeated"].append(full)
        for kind, body in marks:
            taken = TAKES.search(body) if kind == "not served" else None
            if taken and taken.group(1) in served_methods(document, full):
                claim = f"{taken.group(1)} {full}"
                if claim not in out["served_but_marked"]:
                    out["served_but_marked"].append(claim)
    return out


def broken(found: dict) -> bool:
    return any(found[k] for k in ("marked_instances", "served_but_marked", "split_paths", "repeated"))


CLAIM = "nexus-answer-markers-are-true"


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_nexus_answer_markers_are_true_and_leave_the_answer_usable(rest_anon, rest_trusted, mcp_trusted):
    """Their resolver's markers, on the newest answer that carries one, re-read live."""
    nexus = _nexus()
    rows = nexus.load()
    marked = sorted((r for r in rows if r.get("type") == "answer" and r.get("job_id")
                     and has_marker(r.get("text") or "")),
                    key=lambda r: (r.get("at") or "", r.get("id") or ""))
    if not marked:
        raise Inconclusive("no recorded Nexus answer carries a resolver marker, so there is "
                           "nothing to judge")
    witness = marked[-1]

    answer = mcp_trusted.call(nexus.POLL, {"job_id": witness["job_id"]})
    status = nexus._status_of(answer)
    if status != "done":
        raise Inconclusive(f"{witness['id']} (job {witness['job_id']}) read back as {status!r}, "
                           f"not done; there is no answer to judge")
    live = nexus._text_of(nexus._inner(answer))

    document = rest_anon.get(OPENAPI)
    if document.status_code != 200:
        raise Inconclusive(f"{OPENAPI} answered HTTP {document.status_code}; a failed read "
                           f"is not a document that omits a route")
    try:
        spec = document.json() or {}
    except ValueError:
        raise Inconclusive(f"{OPENAPI} answered 200 with a body that is not JSON")
    if not spec.get("paths"):
        raise Inconclusive(f"{OPENAPI} publishes no paths")

    live_rows: list = []
    mine = rest_trusted.get(MY_CLONES, params={"mode": "paper"})
    if mine.status_code == 200:
        try:
            body = mine.json()
            live_rows = body if isinstance(body, list) else (body.get("clones") or body.get("items") or [])
        except ValueError:
            pass
    instances = our_instances(live_rows, _clone_record())
    if mine.status_code != 200 or not live_rows:
        # A08, deep pass 2026-10-15 (rule 8): without our bot ids a marker on one of them cannot be
        # seen, so a pass would rest on a read that failed.
        raise Inconclusive(f"{MY_CLONES} answered HTTP {mine.status_code} with "
                           f"{len(instances)} bot id(s); a marker on our own bot cannot be judged")

    found = misfires(live, spec, instances)
    bad = {k: v for k, v in found.items() if k != "markers" and v}
    parts = []
    if found["marked_instances"]:
        parts.append(f"{len(found['marked_instances'])} bot instance id(s) marked as a card that "
                     f"does not resolve ({', '.join(found['marked_instances'])})")
    if found["served_but_marked"]:
        parts.append("a served route marked not served: " + "; ".join(found["served_but_marked"]))
    if found["split_paths"]:
        parts.append("a marker written inside a path an agent would copy: "
                     + "; ".join(found["split_paths"]))
    if found["repeated"]:
        parts.append("the same marker written twice in a row: " + "; ".join(found["repeated"]))

    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{witness['id']} (job {witness['job_id']}), re-read live, carries "
                f"{found['markers']} resolver marker(s) and {len(parts)} kind(s) of them are wrong: "
                + " | ".join(parts) if bad else
                f"{witness['id']} re-read live carries {found['markers']} marker(s), none of "
                f"them on a bot instance, on a served route, inside a path or written twice"
                + ("" if found["markers"] else " (the re-read has none left, so this judges "
                   "nothing about #91's direction)")),
        left={"answer": witness["id"], "job_id": witness["job_id"], **bad},
        right={"our_instances_read": len(instances), "published_paths": len(spec["paths"]),
               "marked_ids_our_key_lists_as_its_bots": [
                   i for i in found["marked_instances"] if i.lower() in instances]},
        sources={"their answer": f"get_deep_answer {witness['job_id']}",
                 "their document": OPENAPI, "our clones": MY_CLONES},
        population={"markers": found["markers"], "recorded_answers_with_a_marker": len(marked)}))
