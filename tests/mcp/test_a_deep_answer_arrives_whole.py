"""A finished deep investigation is served whole, not with its start cut off.

`ask_nexus_deep` starts an investigation and `get_deep_answer` returns it:
"Poll get_deep_answer with this job_id", and the finished job carries the
answer in `result.answer`. That field is the only copy an outside caller
gets.

**What was seen when this was written.** NEX-0054 (job bfb44eb7-1d12-4e78-
abdb-67ddcc4d52d3, asked 2026-09-21 07:36 UTC, finished in about five
minutes) came back with `result.answer` beginning, verbatim,
`...ols with the hot basket is the predicted outcome` -- mid-word, 1665
characters, and no other field of the result holding the rest. Re-reading
the job returns the same text, so it is what their server stores, not a
transport accident. The question had asked (a), (b) and (c); what survives
is the tail of (c) and a closing list. The concrete rule asked for under (b)
is gone. Our other twenty recorded answers run from 168 to 7416 characters
and none begins with an ellipsis, so this is not a length cap applied
uniformly.

**What is measured.** Every deep investigation we asked in the last
`WINDOW_HOURS` that finished with an answer, re-read LIVE through
`get_deep_answer`, so the check judges what their server serves now rather
than our copy -- and a fix that repairs stored answers, or only new ones,
reads green once the window holds no cut answer. An answer that begins with
an ellipsis ("..." or the single character) is counted as cut. A job whose
re-read fails is unmeasured, never a defect (rule 8).

**Deliberately NOT asserted:** that an answer is complete in any other sense,
or how long it should be. Presence of a leading ellipsis is the safe
direction: it is in the text they sent, or it is not.
"""

from __future__ import annotations

import importlib.util
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
WINDOW_HOURS = 72
PAUSE_S = 2.0
ELLIPSES = ("...", "…")


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_whole", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _at(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def recent_jobs(rows, now, hours: float = WINDOW_HOURS) -> list[dict]:
    """Answered deep jobs asked inside the window: [{id, job_id, at}], oldest first."""
    since = now - timedelta(hours=hours)
    answered = {r.get("id") for r in rows if r.get("type") == "answer"}
    out = []
    for r in rows:
        if r.get("type") != "question" or not r.get("job_id"):
            continue
        when = _at(r.get("at"))
        if when is None or when < since or r.get("id") not in answered:
            continue
        out.append({"id": r["id"], "job_id": r["job_id"], "at": r["at"]})
    return sorted(out, key=lambda j: j["at"])


def served_answer(payload):
    """`result.answer` from their envelope, however deep it is wrapped.

    The MCP layer puts their JSON in result.content[0].text; their own
    envelope is {success, tool, result: {..., answer}}.
    """
    node = payload
    for _ in range(6):
        if isinstance(node, dict) and isinstance(node.get("answer"), str):
            return node["answer"]
        if isinstance(node, dict) and isinstance(node.get("content"), list) and node["content"]:
            first = node["content"][0]
            text = first.get("text") if isinstance(first, dict) else None
            try:
                node = json.loads(text) if isinstance(text, str) else None
            except ValueError:
                return None
            continue
        if isinstance(node, dict) and isinstance(node.get("result"), dict):
            node = node["result"]
            continue
        return None
    return None


def is_cut(answer: str) -> bool:
    return answer.lstrip().startswith(ELLIPSES)


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_a_deep_answer_arrives_whole(mcp_trusted):
    """Re-read each recent finished job: does any served answer start cut off?"""
    jobs = recent_jobs(_nexus().load(), datetime.now(timezone.utc))
    if not jobs:
        raise Inconclusive(
            f"no deep investigation was answered in the last {WINDOW_HOURS} h, "
            f"so there is nothing to re-read")

    cut, whole, unmeasured = [], [], []
    for job in jobs:
        try:
            time.sleep(PAUSE_S)
            raw = mcp_trusted.call_raw("get_deep_answer", {"job_id": job["job_id"]})
        except McpError as exc:
            unmeasured.append(f"{job['id']}: read failed ({str(exc)[:80]})")
            continue
        answer = served_answer(raw)
        if not isinstance(answer, str) or not answer.strip():
            unmeasured.append(f"{job['id']}: no answer served on re-read")
            continue
        (cut if is_cut(answer) else whole).append(
            {"id": job["id"], "job_id": job["job_id"], "asked": job["at"],
             "chars": len(answer), "opens": answer[:60]})

    measured = len(cut) + len(whole)
    if not measured:
        raise Inconclusive(f"no job could be re-read: {'; '.join(unmeasured)}")

    named = "; ".join(f"{c['id']} (job {c['job_id']}, {c['chars']} chars) opens "
                      f"{c['opens']!r}" for c in cut)
    conclude(Measurement(
        verdict="failed" if cut else "passed",
        reason=(f"{len(cut)} of {measured} deep answers asked in the last "
                f"{WINDOW_HOURS} h are served by get_deep_answer with their "
                f"start cut off: {named}"
                if cut else
                f"all {measured} deep answers asked in the last {WINDOW_HOURS} h "
                f"are served whole"),
        left=[c["id"] for c in cut], right=[],
        population={"cut": cut, "whole": whole, "unmeasured": unmeasured},
        sources={"contract": "ask_nexus_deep: 'Poll get_deep_answer with this "
                             "job_id' -- the finished job's result.answer",
                 "jobs": "state/nexus.jsonl (our questions and their job ids)",
                 "read": "POST /mcp/v1 tools/call get_deep_answer {job_id}"},
    ))
