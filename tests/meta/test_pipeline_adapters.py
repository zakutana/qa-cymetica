"""BNT / SUB / THR: the three I/O paths that feed the FILING axis.

Every event that can move a row towards VERIFIED FIXED enters through one of
these scripts, and all three had the same shape of defect: an untyped result.

  * bounty.py never checked an HTTP status, so a 401 was byte-for-byte the
    same as an empty tracker -- an expired key read as the vendor having
    closed every report.
  * submit.py wrote every POST into submissions.json regardless of status,
    lost the record entirely on a timeout, and aborted the rest of the batch.
    Report #55 exists on their server and did not exist in our log, and the
    reconciliation was done by hand.
  * thread.py built the correspondence by scanning directories with
    `delivered` defaulting to True, so moving a file into archive/ deleted a
    vendor reply and three reported findings.

They talk to the platform through httpx.MockTransport here. Nothing in this
file makes a live request.

Fails at 38d48ed: none of classify_read, submit_batch or ingest exist.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module(relpath: str):
    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(path.stem + "_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler, timeout=5.0) -> httpx.Client:
    """Through qa.client's factory, not around the construction guard: the
    mock still travels the real SafetyTransport, so a tier violation in a
    test is still a tier violation."""
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=timeout)


# ---------------------------------------------------------------------------
# BNT -- a failed read is not an empty read
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("status,body,klass", [
    (200, '{"reports": [], "total": 0}', "ok"),
    (401, '{"detail": "Invalid API key"}', "unauthorized"),
    (403, '{"detail": "forbidden"}', "forbidden"),
    (404, "not found", "not_found"),
    (200, "<html>login</html>", "malformed"),
    (500, "boom", "server_error"),
    (503, "", "server_error"),
])
def test_read_outcomes_are_classified_not_assumed(status, body, klass):
    bounty = _module("scripts/bounty.py")
    response = httpx.Response(status, text=body,
                              request=httpx.Request("GET", "https://cymetica.com/x"))
    assert bounty.classify_read(response) == klass


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_401_read_is_not_empty(tmp_path, monkeypatch):
    """The incident, executable: a good read, then an expired key.

    The second read must not produce "the tracker is empty". It must keep the
    snapshot we already had, mark it stale, and emit no vendor_status event --
    because we did not learn anything about any report."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    bounty = _module("scripts/bounty.py")

    good = _client(lambda r: httpx.Response(200, json={
        "reports": [{"id": 46, "status": "pending", "title": "t"},
                    {"id": 47, "status": "fixed", "title": "u"}],
        "total": 23,
    }))
    first = bounty.fetch_our_reports(client=good, wallet="0xabc")
    assert first["klass"] == "ok"
    assert first["rows_returned"] == 2
    assert first["server_total"] == 23, "the server's own total is recorded beside ours"
    assert "stale_from" not in first

    denied = _client(lambda r: httpx.Response(401, json={"detail": "Invalid API key"}))
    second = bounty.fetch_our_reports(client=denied, wallet="0xabc", previous=first)

    assert second["klass"] == "unauthorized"
    assert second["reports"] == first["reports"], "a refused read replaced the data"
    assert second["rows_returned"] is None, "0 rows would claim we read an empty tracker"
    assert second["stale_from"], "the snapshot must be marked stale"

    from qa.state import read_events
    types = [e["type"] for e in read_events()]
    assert types.count("vendor_status") == 2, types
    assert types.count("vendor_read") == 2
    assert [e for e in read_events() if e["type"] == "vendor_read"][-1]["klass"] == "unauthorized"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refresh_writes_the_section_the_bell_reads(tmp_path, monkeypatch):
    """The success path of serve.py --ask, which nothing covered.

    The bell renders the vendor's status out of state/bounty.json, not out of
    the journal, so a refresher that appends the event and writes no file
    leaves the page saying the old thing. That is exactly what --ask shipped
    doing: it called fetch_our_reports, which appends and returns rows without
    touching the snapshot, and every test stayed green because the only test
    of the refresher exercised the FAILURE path, where the correct behaviour
    is to leave the file alone.

    So this asserts the write, on a clean read, with new statuses -- and that
    reverting serve.py to fetch_our_reports would fail here.
    """
    import json as _json

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("QA_WALLET_ADDRESS", "0xabc")
    bounty = _module("scripts/bounty.py")

    snapshot = bounty.out_path()
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(_json.dumps({
        "our_reports": {"klass": "ok", "rows_returned": 1,
                        "reports": [{"id": 46, "status": "pending"}]},
        "leaderboard": ["untouched"],
    }), encoding="utf-8")

    moved = _client(lambda r: httpx.Response(200, json={
        "reports": [{"id": 46, "status": "fixed", "title": "t",
                     "status_notes": "shipped @abc123"}],
        "total": 1,
    }))
    ours = bounty.refresh_our_reports(client=moved)
    assert ours["klass"] == "ok"

    on_disk = _json.loads(snapshot.read_text(encoding="utf-8"))["our_reports"]
    assert on_disk["reports"][0]["status"] == "fixed", \
        "the new status never reached the file the bell reads"
    assert on_disk["reports"][0]["status_notes"] == "shipped @abc123", \
        "their words did not reach the snapshot"
    assert _json.loads(snapshot.read_text(encoding="utf-8"))["leaderboard"] == \
        ["untouched"], "the refresher rewrote a section it was not asked to touch"

    from qa.state import read_events
    statuses = [e for e in read_events() if e["type"] == "vendor_status"]
    assert [(e["report_id"], e["status"]) for e in statuses] == [(46, "fixed")], \
        "the journal and the snapshot disagree about what changed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refresh_that_could_not_read_keeps_the_snapshot(tmp_path, monkeypatch):
    """Rule 8 on the write side, where losing it costs the data.

    fetch_our_reports returns the previous snapshot marked stale on any read
    that is not clean -- except one path. The missing-wallet branch returned a
    bare {"error", "klass"} with no rows and no stale_from, so a run with no
    QA_WALLET_ADDRESS in the environment wrote an empty our_reports over a
    good one. serve.py --ask made that worse by calling the refresher on a
    timer, unattended.

    Verified against the live snapshot while writing this: the first draft of
    refresh_our_reports dropped 20 reports on its first invocation.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("QA_WALLET_ADDRESS", raising=False)
    bounty = _module("scripts/bounty.py")

    good = {"klass": "ok", "rows_returned": 2,
            "reports": [{"id": 46, "status": "fixed"},
                        {"id": 47, "status": "pending"}]}
    snapshot = bounty.out_path()
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps({"our_reports": good, "leaderboard": ["keep me"]}),
                        encoding="utf-8")
    assert snapshot.is_relative_to(tmp_path), \
        "the fixture is writing outside the temp state directory"

    ours = bounty.refresh_our_reports()

    assert ours["klass"] == "unreachable"
    assert ours["reports"] == good["reports"], \
        "a read that could not be made replaced the rows it could not read"
    assert ours["rows_returned"] is None, "0 rows would claim an empty tracker"
    assert ours["stale_from"], "the snapshot was not marked stale"

    on_disk = json.loads(snapshot.read_text(encoding="utf-8"))
    assert on_disk["our_reports"]["reports"] == good["reports"]
    assert on_disk["leaderboard"] == ["keep me"], \
        "the refresher rewrote sections it was not asked to touch"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_duplicate_guard_refuses_a_read_it_could_not_make(monkeypatch):
    """The same incident on the write path, where it costs the vendor.

    existing_titles reads what is already filed so a retry cannot duplicate a
    report. It called .json() without looking at the status, and my-reports
    answers a bad or expired key with 401 and a perfectly parseable
    {"detail": ...} -- so an unreadable tracker produced an empty title set,
    no exception, and a duplicate on the vendor's desk. Its own docstring said
    the anonymous-read version of this had been fixed by reading with the key;
    an expired key brought it straight back.

    A read that failed is not a tracker that is empty. Filing blind is the one
    thing this function exists to prevent, so it exits instead.
    """
    # The public read alone is the subject here. With a wallet in the
    # environment -- and .env puts one there -- existing_titles would go on to
    # build a real client for my-reports, which is a live request in a test
    # that is asserting about status codes.
    monkeypatch.delenv("QA_WALLET_ADDRESS", raising=False)
    submit = _module("scripts/submit.py")

    class _Response:
        def __init__(self, status, body):
            self.status_code, self._body = status, body

        def json(self):
            return self._body

    class _Client:
        def __init__(self, response):
            self._response = response

        def get(self, *args, **kwargs):
            return self._response

    ok = _Client(_Response(200, {"reports": [{"title": "Alpha"}]}))
    assert submit.existing_titles(ok) == {"alpha"}

    for status in (401, 403, 500):
        with pytest.raises(SystemExit) as raised:
            submit.existing_titles(_Client(_Response(status, {"detail": "no"})))
        assert str(status) in str(raised.value), \
            "the refusal does not say what the tracker actually answered"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_vendor_status_events_carry_the_evidence_they_rest_on(tmp_path, monkeypatch):
    """Critique gap 2. FIX_CLAIMED is half of the strongest statement the
    dashboard makes; the fold refuses it without a captured response."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    bounty = _module("scripts/bounty.py")

    client = _client(lambda r: httpx.Response(200, json={
        "reports": [{"id": 46, "status": "fixed", "title": "t"}], "total": 1}))
    bounty.fetch_our_reports(client=client, wallet="0xabc")

    from qa.state import read_events
    for event in read_events():
        if event["type"] in ("vendor_status", "vendor_read"):
            assert event.get("evidence_id"), f"{event['type']} has no evidence_id"


# ---------------------------------------------------------------------------
# SUB -- a submission is two events, and a timeout is not a failure to submit
# ---------------------------------------------------------------------------
def _payload(title):
    return {"title": title, "description": "d", "severity": "medium",
            "category": "api", "url": "https://cymetica.com"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_submit_intent_outcome_log_survives_timeout_and_409(tmp_path, monkeypatch):
    """Four submissions: accepted, timed out, duplicate, accepted.

    The timeout must not lose the record and must not abort the batch -- that
    is exactly what happened to #55, which existed on their server while our
    log said it had never been sent."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    submit = _module("scripts/submit.py")

    def handler(request):
        body = json.loads(request.content)
        if body["title"] == "times-out":
            raise httpx.ReadTimeout("timed out", request=request)
        if body["title"] == "duplicate":
            return httpx.Response(409, json={"detail": "already reported"})
        return httpx.Response(201, json={"report_id": 100 + len(body["title"])})

    items = [{"key": k, "payload": _payload(k), "findings": [f"CYM-{k}"]}
             for k in ("first", "times-out", "duplicate", "last")]

    results = submit.submit_batch(_client(handler), items, confirm=True)
    assert [r["outcome"] for r in results] == ["accepted", "unknown", "rejected", "accepted"], \
        "the batch stopped early, or a timeout was recorded as a failure to send"

    from qa.state import read_events
    events = read_events()
    intents = [e for e in events if e["type"] == "filing_intent"]
    outcomes = [e for e in events if e["type"] == "filing_outcome"]

    assert len(intents) == 4 and len(outcomes) == 4
    for item in items:
        pair = [e for e in events if e.get("key") == item["key"]]
        assert [e["type"] for e in pair] == ["filing_intent", "filing_outcome"], \
            f"{item['key']}: the intent must be on disk before the POST is made"

    timed_out = next(e for e in outcomes if e["key"] == "times-out")
    assert timed_out["outcome"] == "unknown"
    assert timed_out.get("report_id") is None
    assert "reconcile" in (timed_out.get("reason") or "").lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_accepted_requires_both_a_2xx_and_a_server_report_id(tmp_path, monkeypatch):
    """A 200 with no id is not a filed report. Calling it accepted would put a
    row in front of the vendor that we cannot point at."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    submit = _module("scripts/submit.py")

    client = _client(lambda r: httpx.Response(200, json={"ok": True}))
    results = submit.submit_batch(client, [{"key": "k", "payload": _payload("k"),
                                            "findings": ["CYM-k"]}], confirm=True)
    assert results[0]["outcome"] == "unknown"

    from qa.fold import fold

    from tests.meta.test_pipeline_fold import ledger, row
    from qa.state import read_events

    state = fold(ledger(row("CYM-k", checks=["tests/a.py::test_x"])), events=read_events())
    assert state["findings"]["CYM-k"]["filing"]["state"] == "NOT_RAISED"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_reconcile_adds_the_missing_record_and_never_edits(tmp_path, monkeypatch):
    """#55's response was lost to a timeout. The repair is to read their
    server and append what it says -- never to edit the log into agreement."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    submit = _module("scripts/submit.py")

    def handler(request):
        if request.method == "POST":
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"reports": [
            {"id": 55, "title": "llms-self-contradiction", "status": "pending",
             "created_at": "2026-09-04T13:10:00Z"}]})

    client = _client(handler)
    submit.submit_batch(client, [{"key": "llms-self-contradiction",
                                  "payload": _payload("llms-self-contradiction"),
                                  "findings": ["CYM-llms"]}], confirm=True)

    from qa.state import read_events
    before = read_events()
    assert [e["outcome"] for e in before if e["type"] == "filing_outcome"] == ["unknown"]

    added = submit.reconcile(client, wallet="0xabc")
    assert added == 1

    events = read_events()
    assert events[:len(before)] == before, "reconcile rewrote history instead of appending"
    resolved = [e for e in events if e["type"] == "filing_outcome"][-1]
    assert resolved["outcome"] == "accepted" and resolved["report_id"] == 55
    assert resolved["reconciled_from"] == "my-reports"

    assert submit.reconcile(client, wallet="0xabc") == 0, "reconcile is not idempotent"


# ---------------------------------------------------------------------------
# THR -- retired 2026-09-06, with the mechanism it guarded
#
# test_delivery_defaults_false_and_ingest_is_once held scripts/thread.py's
# ingest(): moving a message into archive/ must not delete a vendor reply, and
# an outbound message counts as delivered only when somebody said so. Both are
# real incidents and the test was right about them.
#
# ingest() is gone. Nothing called it -- not the sweep, not render.py, not the
# module's own __main__ -- and the workflow it served, correspondence pasted
# into inbox/ by hand, was tried once in round one and never again. A guard
# over a code path that no longer exists does not protect anything; it just
# asserts that a deleted function still behaves.
#
# The incident cannot recur because the mechanism cannot run. If messages are
# ever ingested from files again, restore this test in the same commit as the
# code -- it names exactly what goes wrong. Correspondence now arrives through
# the bounty API alone (scripts/bounty.py), which has its own guards.
# ---------------------------------------------------------------------------
