"""A filing they refused, or one that never left, is not a report we may have filed.

Deep pass 2026-10-25, O03 (3/3). `submit_batch` wrote `unknown` for every
answer but a 2xx with an id and a 409, and for every exception raised around
the POST -- our own guard refusing it, a connection never made. `unknown` is
"possibly filed" to `filed_in_journal`, so the finding was refused for ever,
and `--reconcile` can settle only what their server lists: a 422 for an
over-long description (validate() does not cap it) or a request that never
left is listed nowhere, so nothing could ever clear it.

Rule 9, in the journal's words (scripts/bb.py, clone.py): `accepted` a 2xx with
their id; `rejected` any 4xx, 409 included -- they refused it; `not_sent` an
exception before anything left (our guard, a connect error, the pool);
`unknown` a timeout, a 5xx, a 2xx without an id -- it may have landed, and
--reconcile settles it against my-reports.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _submit():
    spec = importlib.util.spec_from_file_location("submit_outcomes", REPO / "scripts" / "submit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(title):
    return {"title": title, "description": "d", "severity": "medium",
            "category": "api", "url": "https://cymetica.com"}


def _handler(request):
    """Their side, one answer per title. A SafetyViolation raised here stands for
    our own guard refusing the request before it left: both are raised before
    anything reaches the network."""
    from qa.safety import SafetyViolation

    title = json.loads(request.content)["title"]
    if title == "guard":
        raise SafetyViolation("MUTATE refused")
    if title == "connect":
        raise httpx.ConnectError("connection refused", request=request)
    if title == "timeout":
        raise httpx.ReadTimeout("timed out", request=request)
    if title == "disk":
        # Our own code failing AFTER the request left -- writing the capture of their answer
        # (qa/evidence.py write_text) on a locked or full disk. The POST may have landed, so
        # this is `unknown`, never `not_sent`: a `not_sent` frees the finding and the next
        # sweep files it twice (second round of the deep pass of 2026-10-25).
        raise OSError(28, "No space left on device")
    return {"too-long": httpx.Response(422, json={"detail": "description too long"}),
            "duplicate": httpx.Response(409, json={"detail": "already reported"}),
            "broken": httpx.Response(500, text="boom"),
            "no-id": httpx.Response(200, json={"ok": True}),
            "filed": httpx.Response(201, json={"report_id": 301})}[title]


KEYS = ("guard", "connect", "timeout", "disk", "too-long", "duplicate", "broken", "no-id", "filed")
EXPECTED = ["not_sent", "not_sent", "unknown", "unknown", "rejected", "rejected", "unknown",
            "unknown", "accepted"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_answer_is_recorded_as_what_it_was(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    submit = _submit()
    from qa.client import build_mock_client
    from qa.state import read_events

    items = [{"key": k, "payload": _payload(k), "findings": [f"CYM-{k}"]} for k in KEYS]
    results = submit.submit_batch(build_mock_client(_handler), items, confirm=True)

    assert [r["outcome"] for r in results] == EXPECTED, results
    events = read_events()
    outcomes = {e["key"]: e for e in events if e["type"] == "filing_outcome"}
    assert [outcomes[k]["outcome"] for k in KEYS] == EXPECTED
    assert "reconcile" in outcomes["timeout"]["reason"]
    assert "reconcile" not in (outcomes["connect"].get("reason") or ""), \
        "nothing left, so there is nothing on their side to reconcile against"

    # What may be filed again: only what they refused or what never left.
    payloads = [(k, _payload(f"{k} again")) for k in KEYS]
    reports = [{"key": k, "findings": [f"CYM-{k}"]} for k in KEYS]
    ready, refused = submit.select_items(payloads, reports, {"findings": []}, seen=set(),
                                         events=events)
    assert sorted(i["key"] for i in ready) == ["connect", "duplicate", "guard", "too-long"], ready
    assert sorted(k for k, _ in refused) == ["broken", "disk", "filed", "no-id", "timeout"], refused


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_never_answers_a_later_intent():
    """An outcome answers the intent before it, not one written after. With a
    refusal no longer blocking, a key refused once and filed again, whose second
    POST left no outcome (the process died), read as answered by the first."""
    submit = _submit()
    events = [
        {"type": "filing_intent", "key": "k", "findings": ["CYM-k"]},
        {"type": "filing_outcome", "key": "k", "findings": ["CYM-k"], "outcome": "rejected"},
        {"type": "filing_intent", "key": "k", "findings": ["CYM-k"]},
    ]
    assert submit.filed_in_journal(events) == {"CYM-k": ["no outcome"]}
    assert submit.filed_in_journal(events[:2]) == {}
