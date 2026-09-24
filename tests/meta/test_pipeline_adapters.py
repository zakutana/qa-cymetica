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
import re
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
    from qa.state import read_events as _journal
    seen_at_post = []

    def handler(request):
        body = json.loads(request.content)
        # What is on disk WHILE the POST is in flight: the journal's final
        # order is the same whether the intent went before or after it, so
        # only a read here measures rule 9 (deep pass 2026-09-24, G12, 3/3).
        seen_at_post.append([e["type"] for e in _journal()
                             if e.get("key") == body["title"]])
        if body["title"] == "times-out":
            raise httpx.ReadTimeout("timed out", request=request)
        if body["title"] == "duplicate":
            return httpx.Response(409, json={"detail": "already reported"})
        return httpx.Response(201, json={"report_id": 100 + len(body["title"])})

    items = [{"key": k, "payload": _payload(k), "findings": [f"CYM-{k}"],
              "runs": {f"CYM-{k}": "run-evidence"}}
             for k in ("first", "times-out", "duplicate", "last")]

    results = submit.submit_batch(_client(handler), items, confirm=True)
    assert [r["outcome"] for r in results] == ["accepted", "unknown", "rejected", "accepted"], \
        "the batch stopped early, or a timeout was recorded as a failure to send"

    from qa.state import read_events
    events = read_events()
    intents = [e for e in events if e["type"] == "filing_intent"]
    outcomes = [e for e in events if e["type"] == "filing_outcome"]

    assert len(intents) == 4 and len(outcomes) == 4
    assert seen_at_post == [["filing_intent"]] * 4, seen_at_post
    for item in items:
        pair = [e for e in events if e.get("key") == item["key"]]
        assert [e["type"] for e in pair] == ["filing_intent", "filing_outcome"], \
            f"{item['key']}: the intent must be on disk before the POST is made"

    timed_out = next(e for e in outcomes if e["key"] == "times-out")
    assert timed_out["outcome"] == "unknown"
    assert timed_out.get("report_id") is None
    assert "reconcile" in (timed_out.get("reason") or "").lower()

    # B4 of the review of 2026-09-23 (3/3): every report promises its
    # evidence "on request", and 0 of 151 filing events named the run that
    # holds it, so the keepset could not keep it. Both halves carry it now.
    for e in intents + outcomes:
        assert e.get("runs") == {f"CYM-{e['key']}": "run-evidence"}, e
    from qa import keepset
    cited = keepset.cited(events, {"findings": {"CYM-first": {"checks": ["t::c"]}}},
                          lambda run_id: {"results": [
                              {"nodeid": "t::c", "evidence_ids": ["e" * 64]}]}
                          if run_id == "run-evidence" else None)
    assert cited.get("e" * 64) == "promised", cited


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

    # B6 of the review of 2026-09-23 (3/3): an `accepted` outcome carrying no
    # evidence is refused by the fold (gap 2) -- and reconcile counted it as
    # settled, so the report stayed invisible to both for good. Without its
    # capture it is not settled: reconcile appends one that has it.
    from qa.state import append_event
    append_event({"type": "filing_outcome", "at": "2026-09-05T10:00:00+00:00",
                  "by": "agent", "source": "scripts/submit.py", "key": "other",
                  "outcome": "accepted", "report_id": 77, "findings": ["CYM-o"]})
    append_event({"type": "filing_intent", "at": "2026-09-05T09:59:00+00:00",
                  "by": "agent", "source": "scripts/submit.py", "key": "other",
                  "intent_at": "2026-09-05T09:59:00+00:00", "title": "other report",
                  "findings": ["CYM-o"]})

    def handler_77(request):
        return httpx.Response(200, json={"reports": [
            {"id": 77, "title": "other report", "status": "pending",
             "created_at": "2026-09-05T10:00:00Z"}]})
    assert submit.reconcile(_client(handler_77), wallet="0xabc") == 1, \
        "an accepted outcome with no capture was counted as settled"
    last = [e for e in read_events() if e["type"] == "filing_outcome"][-1]
    assert last["report_id"] == 77 and last.get("evidence_id"), last


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fold_that_writes_no_ledger_writes_nothing_to_the_journal(tmp_path, monkeypatch):
    """LDG: looking at what the state folds to is a read, and reads do not write.

    compose() attested the run record unconditionally, so every caller that
    folded merely to look appended to the append-only journal. One of them --
    the page's field-coverage check in tests/meta -- folds fresh on every
    session against whichever run is NEWEST, which is that session's own
    exploratory record. On 2026-09-07 that was 98 of the 137 run_recorded
    events: attestations of runs the ledger never stood on, in the file whose
    whole value is that nothing enters it by accident.

    Nothing moved -- the fold does not read this event type. The damage was to
    the audit trail, and then to the guard in tests/repo, which asks that every
    cited record be in the repository and was being handed ids that never would
    be.

    Three claims: a fold that folds a real run and only looks appends nothing,
    the same fold asked to attest appends exactly one event, and a second
    attesting fold of the same run adds nothing on top. The first is the
    regression. The second is what stops this being "fixed" by deleting the
    feature -- and the reason the fold here has to stand on an actual run
    record: the `attest` branch sits inside `if not events_only`, so a test
    that only ever folds the journal cannot reach it, and an earlier version
    of this one passed with the fix reverted.
    """
    ledger_mod = _module("scripts/ledger.py")
    state = tmp_path / "state"
    (state / "journal").mkdir(parents=True)
    (state / "runs").mkdir(parents=True)
    monkeypatch.setenv("QA_STATE_DIR", str(state))

    from qa.state import append_event, read_events

    def _events():
        return [e for e in read_events()]

    append_event({"type": "note", "at": "2026-09-07T00:00:00+00:00",
                  "by": "test", "source": "test", "finding_id": "CYM-x",
                  "text": "so the journal is not empty"})
    before = len(_events())

    run_id = "run-20260907T000000Z-abc1234"
    (state / "runs" / f"{run_id}.json").write_text(json.dumps({
        "schema": 2, "run_id": run_id,
        "started_at": "2026-09-07T00:00:00+00:00",
        "finished_at": "2026-09-07T00:00:10+00:00",
        "collected": [], "results": [], "exit_status": 0,
        "platform_fingerprint": "sha256:" + "0" * 64,
        "fingerprint_drifted": False, "git_dirty": False,
        "selector": ["tests"], "totals": {},
    }), encoding="utf-8")

    ledger_mod.compose(run_id=run_id)
    assert len(_events()) == before, \
        "a fold that only looked appended to the journal"

    ledger_mod.compose(run_id=run_id, attest=True)
    attested = [e for e in _events() if e["type"] == "run_recorded"]
    assert len(_events()) == before + 1 and len(attested) == 1, \
        "the writing path no longer attests the record it stands on"
    assert attested[0]["run_id"] == run_id

    # Idempotent by run_id, so re-composing the same run adds nothing.
    ledger_mod.compose(run_id=run_id, attest=True)
    assert len(_events()) == before + 1, "the same run was attested twice"

    # A journal-only fold has no record to pin, whatever it is asked for.
    ledger_mod.compose(events_only=True, attest=True)
    assert len(_events()) == before + 1, \
        "an events-only fold attested a run it never read"

    # And main() is what asks -- unless --check, which writes nothing.
    source = (REPO / "scripts" / "ledger.py").read_text(encoding="utf-8")
    assert "attest=not args.check" in source, \
        "main() no longer attests the record the ledger it writes stands on"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_folded_run_record_is_tracked_even_though_the_others_are_not(tmp_path):
    """LDG: `state/runs/` is ignored, so the fold has to force what it stood on.

    The ignore rule is what stops every exploratory run from dirtying the tree
    and making prereg.py refuse. The cost of getting it wrong is silent: an
    ordinary `git add` succeeds, reports nothing, and adds nothing, leaving a
    ledger that cites evidence a clone cannot read. So this asserts the -f,
    inside a throwaway repository carrying the same ignore rule.

    tests/repo states the property over the real state -- every cited record
    is tracked. This states the mechanism that keeps it true.
    """
    import subprocess

    ledger_mod = _module("scripts/ledger.py")

    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, check=True,
                              capture_output=True, text=True).stdout

    git("init", "-q")
    git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (tmp_path / ".gitignore").write_text("state/runs/\n", encoding="utf-8")
    runs = tmp_path / "state" / "runs"
    runs.mkdir(parents=True)
    record = runs / "run-20260907T000000Z-abc1234.json"
    record.write_text(json.dumps({"run_id": "run-20260907T000000Z-abc1234"}),
                      encoding="utf-8")

    # The premise: git really is ignoring it, so the assertion below is not
    # passing for the trivial reason that nothing was ignored in the first
    # place.
    git("add", "state")
    assert "state/runs" not in git("ls-files"), "the ignore rule did not apply"

    monkey = ledger_mod.runs_dir
    try:
        ledger_mod.runs_dir = lambda: runs
        ledger_mod._track_run_record("run-20260907T000000Z-abc1234")
    finally:
        ledger_mod.runs_dir = monkey

    assert "state/runs/run-20260907T000000Z-abc1234.json" in git("ls-files"), \
        "the record the ledger stands on was not forced past the ignore rule"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refused_ledger_still_leaves_its_attestation_tracked(monkeypatch):
    """LDG: the journal is append-only, so the pair cannot be split.

    2026-09-07, and mine from that morning. compose() appended the
    run_recorded event; main() force-added the record AFTERWARDS, with
    write_ledger between them. write_ledger then did what it is for -- refused
    a ledger that was not forward-only -- main() returned before the add, and
    the append-only journal was left permanently citing
    run-20260907T121855Z-ee26eda while the record itself stayed gitignored and
    unclonable. tests/repo caught it, which is the right outcome and one step
    later than it needed to be.

    A refusal is not an exceptional path here. Every guard in qa/state.py can
    take it, and each one leaves the journal already written. So the property
    is not "tracking happens" but "tracking happens on the failing path too",
    and the two calls have to be adjacent with nothing fallible between them.

    Stated behaviourally rather than by scanning the source for an ordering:
    a source check would pass on any file that merely mentions both names.
    """
    ledger_mod = _module("scripts/ledger.py")
    tracked: list[str] = []
    attested: list[str] = []

    class Refused(Exception):
        pass

    def refuse(*_a, **_k):
        raise Refused("not forward-only")

    monkeypatch.setattr(ledger_mod, "_track_run_record", tracked.append)
    monkeypatch.setattr(ledger_mod, "write_ledger", refuse)
    monkeypatch.setattr(ledger_mod, "append_event",
                        lambda e: attested.append(e.get("run_id")))
    monkeypatch.setattr(ledger_mod, "load_previous", lambda: None)

    run_id = ledger_mod.latest_admissible_run_id("R")
    if run_id is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no admissible run record exists, so the write cannot be "
                   "driven as far as the refusal this is about"))
        return

    with pytest.raises(Refused):
        ledger_mod.main(["--run", run_id])

    assert attested == [run_id], \
        f"the journal did not attest {run_id}, so there is nothing to orphan"
    assert tracked == [run_id], (
        f"write_ledger refused and {run_id} was never force-added, so the "
        f"journal cites a record no clone can read. Track it beside the "
        f"attestation, not after the write."
    )


# ---------------------------------------------------------------------------
# VER -- the outbound claim, and the two things that make it honest
# ---------------------------------------------------------------------------
def _owed_ledger(fid="CYM-a", report_id=46, run_id="run-1"):
    return {"schema": 2, "findings": {fid: {
        "id": fid, "title": "t", "checks": ["tests/rest/test_x.py::test_y"],
        "provenance": {"run_id": run_id, "measured_at": "2026-09-07T12:40:29+00:00"},
        "check": {"state": "PASSING", "pinned_fingerprint": "fp-1",
                  "adjudicated_by": {"run_id": run_id, "at": "2026-09-07T12:40:29+00:00"}},
        "filing": {"state": "FIX_CLAIMED", "reports": [{"report_id": report_id}],
                   "refused": [], "verifications": []},
        "obligations": {"verification_owed": [report_id]},
    }}}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verification_is_refused_unless_the_run_could_verify(monkeypatch):
    """VER: rule 6, applied to the one place it leaves the building.

    Inside this repository a level-R run simply moves nothing, and the ledger
    is the only thing that notices. A verification is different: it is a
    sentence sent to somebody else, and "our check passes" said on the back of
    a dirty tree or an untagged selector is a claim our own rules do not let us
    make about ourselves. So the level is checked at the point of sending, not
    inferred from the row having reached PASSING.

    Deliberately fatal rather than a skip. A batch where some items are
    verified and some quietly are not is worse than one that refuses: the
    operator would have to reconstruct which was which from the journal.
    """
    verify = _module("scripts/verify.py")
    ledger = _owed_ledger()

    class Verdict:
        def __init__(self, level, reasons):
            self.level, self.reasons = level, reasons

    monkeypatch.setattr(verify, "load_run", lambda rid: {"run_id": rid})

    monkeypatch.setattr(verify, "admissibility", lambda run: Verdict("R", ["git_dirty"]))
    with pytest.raises(SystemExit, match="level R"):
        verify.owed(ledger, None)

    monkeypatch.setattr(verify, "admissibility", lambda run: Verdict("none", ["legacy_schema"]))
    with pytest.raises(SystemExit, match="Nothing sent"):
        verify.owed(ledger, None)

    # The control: with a level-V run the same ledger yields the work, so the
    # refusals above are the level and not something else about the fixture.
    monkeypatch.setattr(verify, "admissibility", lambda run: Verdict("V", []))
    work = verify.owed(ledger, None)
    assert [(w["finding_id"], w["report_id"]) for w in work] == [("CYM-a", 46)]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verification_whose_response_cannot_be_kept_is_not_claimed():
    """VER: the capture is part of the transaction, not a courtesy afterwards.

    submit.py's `_capture` swallows any exception and returns None. The cost
    shows up one layer away: qa/fold.py refuses an outcome with no evidence_id,
    so the request went out, the journal recorded it, and the ledger cannot use
    it -- a claim we made and cannot stand behind. Here it stops the run.
    """
    verify = _module("scripts/verify.py")

    class Boom:
        request = httpx.Request("POST", "https://cymetica.com/api/v1/bounty/reports/46/verification")

    with pytest.raises(SystemExit, match="was not captured"):
        verify._capture(Boom())


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_verifications_they_already_hold_are_not_sent_again(tmp_path, monkeypatch):
    """VER: and a read that failed is not a server holding nothing (rule 8).

    The obligation already stops us re-sending what OUR journal records. This
    is the other half: their server is the authority on what they have, and
    submit.py exists because the two once disagreed -- report #55 was on their
    server and not in our log.
    """
    # QA_STATE_DIR, because already_sent() captures the read it makes and the
    # evidence store follows that seam. Without it this test wrote five real
    # records into the committed archive on every run -- a test that became a
    # writer of durable artefacts, which is what the seam exists to stop.
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    verify = _module("scripts/verify.py")

    held = _client(lambda r: httpx.Response(
        200, json={"verifications": [
            {"fingerprint": "fp-1", "verdict": "pass", "id": "1",
             "created_at": "2026-09-10T20:08:29"},
            {"fingerprint": "fp-old", "verdict": "fail", "id": "2",
             "created_at": "2026-09-10T16:52:51"}]}))
    newest, evidence_id = verify.already_sent(held, 46)
    assert newest == {"fp-1": {"pass"}, "fp-old": {"fail"}}
    assert evidence_id,         "the read that deduplicates is also the read that settles, so it has "         "to hand back what it can be stood on"

    # Their LAST word under a fingerprint, not every word they hold. #85 held
    # a pass at 20:08 and a fail at 21:46 under one definition; membership
    # said "they already have this pass", so the correction could never be
    # made and their tracker kept the fail as the final reading for ten days
    # while our check passed. Architecture audit, 2026-09-20.
    both = _client(lambda r: httpx.Response(
        200, json={"verifications": [
            {"fingerprint": "fp-1", "verdict": "fail", "id": "90",
             "created_at": "2026-09-10T21:46:08"},
            {"fingerprint": "fp-1", "verdict": "pass", "id": "88",
             "created_at": "2026-09-10T20:08:29"}]}))
    assert verify.already_sent(both, 46)[0] == {"fp-1": {"fail"}}

    # And the promise the other way, which the first version made in its
    # docstring and did not keep: when NO row under a fingerprint can be
    # ranked, every verdict they hold stays, degrading to the old
    # duplicate-averse reading. It kept whichever row came first in their
    # list instead and called the other one fresh, i.e. re-sent it.
    unrankable = _client(lambda r: httpx.Response(
        200, json={"verifications": [
            {"fingerprint": "fp-1", "verdict": "fail"},
            {"fingerprint": "fp-1", "verdict": "pass"}]}))
    assert verify.already_sent(unrankable, 46)[0] == {"fp-1": {"fail", "pass"}}, (
        "neither row can claim to be the last word, so neither may be "
        "discarded -- and nothing they hold may be re-sent")

    # A dated row still wins over an undatable one, in both orders.
    for rows in ([{"fingerprint": "fp-1", "verdict": "pass"},
                  {"fingerprint": "fp-1", "verdict": "fail", "id": "90",
                   "created_at": "2026-09-10T21:46:08"}],
                 [{"fingerprint": "fp-1", "verdict": "fail", "id": "90",
                   "created_at": "2026-09-10T21:46:08"},
                  {"fingerprint": "fp-1", "verdict": "pass"}]):
        mixed = _client(lambda r, rs=rows: httpx.Response(
            200, json={"verifications": rs}))
        assert verify.already_sent(mixed, 46)[0] == {"fp-1": {"fail"}}, rows

    # No verifications yet is a real answer; a failed read is not.
    empty = _client(lambda r: httpx.Response(404, text="not found"))
    assert verify.already_sent(empty, 46)[0] == {}

    for status in (401, 500, 503):
        broken = _client(lambda r, s=status: httpx.Response(s, text="nope"))
        with pytest.raises(SystemExit, match="Refusing to send blind"):
            verify.already_sent(broken, 46)


# ---------------------------------------------------------------------------
# A2A -- the inbox nothing was reading
# ---------------------------------------------------------------------------
def _inbox(*messages):
    return _client(lambda r: httpx.Response(200, json={"messages": list(messages)}))


def _msg(msg_id, at, content="hello", auto=False, thread="th-1"):
    meta = {"auto": True, "kind": "first_pass"} if auto else {}
    return {"id": msg_id, "created_at": at, "content": content,
            "from_agent_id": "nexus", "thread_id": thread, "metadata": meta}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_settle_reads_the_newest_mark_the_way_the_fold_does(tmp_path,
                                                            monkeypatch):
    """Two readers of "already told", and they stopped agreeing.

    `settle()` refuses to write when ANY accepted outcome for this
    (finding, report, fingerprint, verdict) exists, with no time bound. That
    matched `_told` while `_told` asked whether a verdict had EVER been sent.
    Since 2026-09-20 `_told` reads the NEWEST mark -- the #85 repair -- and
    the two now disagree on exactly one path:

      pass at T1, fail at T2, our check passes again, so a pass is owed. The
      POST is accepted and `_capture` raises, so the outcome is recorded as
      `unknown` and no mark is written. Every later run then sees their
      server's newest is a pass, calls the item a duplicate, and settle finds
      the accepted pass from T1 and writes nothing. The obligation can never
      clear -- which is the badge settle() exists to prevent.

    So settle asks the same question the fold asks: is this verdict the last
    accepted word for that definition?
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    verify = _module("scripts/verify.py")
    from qa.state import append_event

    item = {"finding_id": "CYM-a", "report_id": 46, "fingerprint": "fp-1",
            "verdict": "pass", "run_id": "run-1", "tree_sha": "t",
            "checked_at": "2026-09-20T09:00:00+00:00"}

    def mark(verdict, at, fingerprint="fp-1"):
        append_event({"type": "verification_outcome", "at": at, "by": "agent",
                      "source": "scripts/verify.py", "finding_id": "CYM-a",
                      "report_id": 46, "fingerprint": fingerprint,
                      "verdict": verdict, "outcome": "accepted",
                      "run_id": "run-0", "tree_sha": "t",
                      "checked_at": at, "evidence_id": "e"})

    mark("pass", "2026-09-10T20:08:29+00:00")
    mark("fail", "2026-09-10T21:46:08+00:00")
    # C02, deep pass of 2026-09-22 evening (3/3): the docstring's own path --
    # the re-sent pass recorded with outcome `unknown` -- was never written
    # here, so dropping the `accepted` filter stayed green while the unknown
    # pass became the newest mark and the obligation could never clear.
    append_event({"type": "verification_outcome",
                  "at": "2026-09-11T09:00:00+00:00", "by": "agent",
                  "source": "scripts/verify.py", "finding_id": "CYM-a",
                  "report_id": 46, "fingerprint": "fp-1", "verdict": "pass",
                  "outcome": "unknown", "run_id": "run-0", "tree_sha": "t",
                  "checked_at": "2026-09-11T09:00:00+00:00", "evidence_id": "e"})

    assert verify.settle(dict(item), "evidence-1") is True, (
        "their last accepted word is the fail, so the pass is owed and has "
        "to be recordable -- this is #85's shape one reader down")

    # And once it IS the last word, a second send writes nothing.
    assert verify.settle(dict(item), "evidence-2") is False

    # C04, deep pass of 2026-09-22: the tie the fold's own reader covers.
    # Their timestamps are truncated to the second, so a pass and a fail can
    # share one; journal order says the fail is the newer word, and the pass
    # is owed again. Read by `at` alone, max() keeps the first it meets.
    mark("pass", "2026-09-11T08:00:00+00:00", fingerprint="fp-2")
    mark("fail", "2026-09-11T08:00:00+00:00", fingerprint="fp-2")
    tied = {**item, "fingerprint": "fp-2"}
    assert verify.settle(dict(tied), "evidence-3") is True, (
        "a fail written after the pass in the same second is the last word")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_correction_we_send_says_which_of_the_three_things_happened():
    """The fold tells the three apart; this is the half that goes out.

    A correction said, on every one of them, "either a fix was claimed and our
    re-check does not agree, or we sent you a pass we can no longer stand
    behind". Both halves are false of a report they accepted and PAID without
    claiming a fix -- #89 and #98 -- and a sentence we cannot stand behind is
    one that does not get sent, which is how those two came to sit with them
    under nothing at all.

    Each sentence has to be checkable against the reason beside it, so this
    asserts on what the wording CLAIMS, not on its prose.
    """
    verify = _module("scripts/verify.py")
    base = {"finding_id": "CYM-a", "report_id": 89, "fingerprint": "fp",
            "verdict": "fail", "run_id": "r", "tree_sha": "t", "pin": None,
            "checked_at": "2026-09-20T09:00:00+00:00", "checks": ["x::y"],
            "evidence_ids": [], "prereg_id": "PRE-0001", "title": "t",
            "level": "R"}

    accepted = verify.body({**base, "correction_reason": "accepted"})["evidence"]
    assert "accepted and paid" in accepted, accepted
    # C03, deep pass of 2026-09-22: "claim of yours" alone was satisfied by
    # "This answers a claim of yours that the defect is fixed" -- the very
    # thing this sentence may not say. It has to be the negated form.
    assert re.search(r"\bnot\b[^.]{0,40}\bclaim of yours\b", accepted), (
        "it has to say it is NOT answering a claim of theirs")
    for wrong in ("a fix was claimed", "sent you a pass"):
        assert wrong not in accepted, f"still says {wrong!r}: {accepted[:400]}"

    ours = verify.body({**base, "correction_reason": "our_pass"})["evidence"]
    assert "we sent you a pass" in ours.lower(), ours
    assert "a fix was claimed" not in ours, ours

    claimed = verify.body({**base, "correction_reason": "fix_claimed"})["evidence"]
    assert "a fix was claimed" in claimed, claimed
    assert "accepted and paid" not in claimed, claimed
    # C03, deep pass of 2026-09-22 evening (3/3): the default wording holds
    # "a fix was claimed" too, so deleting this branch stayed green. Its own
    # sentence says it without the disjunction.
    for default_only in ("either a fix was claimed", "sent you a pass"):
        assert default_only not in claimed, f"fell back to the default: {claimed[:300]}"

    # No reason recorded says LESS, not something false. Each sentence above
    # asserts a specific thing about what they did, so the narrowest of them
    # is the wrong default; the old disjunction is true whichever it was.
    unknown = verify.body({**base})["evidence"]
    assert "either a fix was claimed" in unknown, unknown


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_reason_reaches_the_message_from_the_ledger():
    """The two halves above are each tested and the seam between them is not.

    `correction_reason` is driven directly in the fold's tests and `body()` is
    driven with a hand-built item here, so a typo in the key, an inverted
    `if verdict == "fail"`, or a `by_id` built from the wrong list would leave
    every correction falling to the default while both files stayed green.
    That is `driving-the-helper-is-not-running-the-check`, which this session
    wrote down about a different function an hour earlier.
    """
    verify = _module("scripts/verify.py")
    ledger = {"findings": {"CYM-a": {
        "title": "t",
        "checks": ["tests/rest/test_x.py::test_y"],
        "provenance": {"measured_at": "2026-09-20T09:00:00+00:00"},
        "check": {"pinned_fingerprint": "fp",
                  "adjudicated_by": {"run_id": "run-1",
                                     "at": "2026-09-20T09:00:00+00:00"}},
        "filing": {"reports": [{"report_id": 89, "status": "paid"},
                               {"report_id": 90, "status": "fixed"}],
                   "verifications": []},
        "obligations": {"correction_owed": [89, 90], "verification_owed": []},
    }}}

    run = {"run_id": "run-1", "git_head": "abc", "prereg_id": "PRE-0001",
           "results": [], "schema": 2, "git_dirty": False,
           "prereg_tag_sha": "t", "prereg_commit": "abc",
           "platform_fingerprint": "sha256:f", "fingerprint_drifted": False,
           "collected": [], "exit_status": 0,
           "record_integrity": {"consistent": True},
           "started_at": "2026-09-20T09:00:00+00:00"}
    verify.load_run = lambda *a, **k: run

    reasons = {item["report_id"]: item["correction_reason"]
               for item in verify.owed(ledger, None)}
    assert reasons == {89: "accepted", 90: "fix_claimed"}, reasons
    assert "accepted and paid" in verify.body(
        next(i for i in verify.owed(ledger, None)
             if i["report_id"] == 89))["evidence"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_unreadable_report_does_not_take_the_whole_run_with_it(
        tmp_path, monkeypatch):
    """VER: refusing to send blind is per report, so the loss must be too.

    `already_sent` raises rather than guess -- correct, and rule 8. But the
    raise crossed the loop that reads every report in the run, so their TLS
    timing out on ONE report at 20:55 on 2026-09-12 took every other verdict
    with it, including ones whose own read had already come back fine. A
    refusal about one report is not evidence about another.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    verify = _module("scripts/verify.py")

    work = [{"finding_id": "CYM-a", "report_id": 46, "fingerprint": "fp-1",
             "verdict": "pass", "run_id": "run-1", "tree_sha": "t",
             "checked_at": "2026-09-12T20:00:00+00:00", "checks": ["x::y"],
             "evidence_ids": [], "pin": None, "prereg_id": "PRE-0001",
             "title": "a", "level": "V"},
            {"finding_id": "CYM-b", "report_id": 47, "fingerprint": "fp-2",
             "verdict": "pass", "run_id": "run-1", "tree_sha": "t",
             "checked_at": "2026-09-12T20:00:00+00:00", "checks": ["x::z"],
             "evidence_ids": [], "pin": None, "prereg_id": "PRE-0001",
             "title": "b", "level": "V"}]
    monkeypatch.setattr(verify, "owed", lambda ledger, only: list(work))
    monkeypatch.setattr(verify, "load_ledger", lambda: {"findings": {}})
    monkeypatch.setattr(verify, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(verify, "install_client_guard", lambda: None)
    monkeypatch.setattr(verify, "identities", lambda: {"trusted": None})

    posted = []

    def handle(request):
        if request.url.path.endswith("/verifications"):
            # #46's record is unreadable and this is the shape that actually
            # happened: their TLS timed out at 20:55 on 2026-09-12. A timeout
            # surfaces as httpx.TransportError, NOT as the SystemExit
            # `already_sent` raises on a bad status -- and the first version of
            # this test used a 503, which takes the SystemExit path. So it was
            # green while the scenario its own comment named still aborted the
            # whole run. Found by two readers on 2026-09-20.
            if "/46/" in str(request.url):
                raise httpx.ReadTimeout("their TLS timed out", request=request)
            return httpx.Response(200, json={"verifications": []})
        posted.append(str(request.url))
        return httpx.Response(200, json={"id": 1})

    def _sender(*a, **k):
        client = _client(handle)
        client._transport.registry.mutate_enabled = True
        client._transport.registry.mutate_allowed_hosts = frozenset(
            {"cymetica.com"})
        return client

    monkeypatch.setattr(verify, "build_client", _sender)
    monkeypatch.setattr(verify, "settle", lambda *a, **k: True)

    verify.main(["--confirm"])
    assert any("/47/" in url for url in posted), (
        f"the readable report's verification was dropped because another "
        f"report could not be read: {posted}")
    assert not any("/46/" in url for url in posted), (
        "a report we could not read was sent blind")

    # And main() acts on what their server HOLDS: the partition was tested
    # only directly, so `fresh = work` inside main() -- the incident its
    # sibling names -- stayed green (deep pass 2026-09-24, G11, 3/3).
    posted.clear()
    held = {"fingerprint": "fp-2", "verdict": "pass",
            "created_at": "2026-09-12T20:30:00+00:00", "id": "9"}

    def holding(request):
        if request.url.path.endswith("/verifications"):
            if "/46/" in str(request.url):
                raise httpx.ReadTimeout("their TLS timed out", request=request)
            return httpx.Response(200, json={"verifications": [held]})
        posted.append(str(request.url))
        return httpx.Response(200, json={"id": 1})
    handle_ = handle
    handle = holding  # noqa: F841 -- _sender reads `handle` late
    verify.main(["--confirm"])
    handle = handle_  # noqa: F841
    assert not any("/47/" in url for url in posted), (
        f"a verification their server already holds was sent again: {posted}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_their_server_already_holds_is_dropped_before_sending():
    """VER: the sibling above tests the READ; this tests that anything acts on it.

    The dedup lived as five lines inside verify.main(), which no test calls, so
    `already_sent()` could parse their server's answer perfectly while nothing
    used it. Replacing the filter with `fresh = work` left the whole suite
    green and sent the vendor a duplicate verification for every pair they
    already held. Found by the contract audit on 2026-09-07 and confirmed by
    three independent triage agents.

    The partition is now a named function, so deleting it is a visible change
    rather than an invisible one.
    """
    verify = _module("scripts/verify.py")

    work = [
        {"finding_id": "CYM-a", "report_id": 49, "fingerprint": "fp-1",
         "verdict": "pass"},
        {"finding_id": "CYM-b", "report_id": 49, "fingerprint": "fp-2",
         "verdict": "pass"},
        # Same fingerprint as the first, opposite verdict: a correction is new
        # information and must go, or we can never take a claim back.
        {"finding_id": "CYM-c", "report_id": 59, "fingerprint": "fp-1",
         "verdict": "fail"},
        # And the other direction, which is what #85 needed: their newest word
        # under this definition is a fail, ours passes now. Membership said
        # "they already hold a pass for fp-3" -- true, and three hours older
        # than the fail that superseded it -- so the pass could never be
        # re-sent and their tracker kept the wrong final reading.
        {"finding_id": "CYM-d", "report_id": 85, "fingerprint": "fp-3",
         "verdict": "pass"},
        # Their rows under fp-4 carry neither a date nor a numeric id, so
        # neither is the last word and both count as held -- the set of two
        # `_newest_per_fingerprint` exists to be able to say.
        {"finding_id": "CYM-e", "report_id": 90, "fingerprint": "fp-4",
         "verdict": "pass"},
    ]
    # Built by the function main() builds it with, not typed. This fixture was
    # `{"fp-1": "pass"}` -- a string where production holds a SET -- so `in`
    # changed to `==` in the partition stayed green here while in production
    # it matched nothing and re-sent every duplicate (B11, deep pass of
    # 2026-09-21).
    def row(fingerprint, verdict, at=None, id_=None):
        return {"fingerprint": fingerprint, "verdict": verdict,
                "created_at": at, "id": id_}

    theirs = {
        49: [row("fp-1", "pass", "2026-09-07T10:00:00+00:00", "1")],
        59: [row("fp-1", "pass", "2026-09-07T10:00:00+00:00", "2")],
        85: [row("fp-3", "pass", "2026-09-10T20:08:00+00:00", "3"),
             row("fp-3", "fail", "2026-09-10T21:46:00+00:00", "4")],
        90: [row("fp-4", "pass"), row("fp-4", "fail")],
    }
    held = {rid: verify._newest_per_fingerprint(rows)
            for rid, rows in theirs.items()}
    assert held[85] == {"fp-3": {"fail"}} and \
        held[90] == {"fp-4": {"pass", "fail"}}, held

    fresh, duplicates, later = verify.partition_by_what_they_hold(work, held)

    assert [i["finding_id"] for i in duplicates] == ["CYM-a", "CYM-e"], \
        "a verification their server already holds was queued for sending again"
    assert [i["finding_id"] for i in fresh] == ["CYM-b", "CYM-c", "CYM-d"], \
        "a verification they do not hold was dropped, so the debt cannot be paid"
    assert later == []

    # RO03 (deep pass of 2026-09-24): two rows sharing one check and one
    # report -- CYM-skill_count and CYM-skill_ids on #51 -- each sent the same
    # pass in one run, twice (2026-09-07, 2026-09-10): the dedup only knew
    # what their server held before the batch. One goes; the other waits for
    # the next run's read, which finds it held and settles it.
    twins = [{"finding_id": f, "report_id": 51, "fingerprint": "fp-9",
              "verdict": "pass"} for f in ("CYM-skill_count", "CYM-skill_ids")]
    fresh, duplicates, later = verify.partition_by_what_they_hold(
        twins, {51: {}})
    assert [i["finding_id"] for i in fresh] == ["CYM-skill_count"], fresh
    assert [i["finding_id"] for i in later] == ["CYM-skill_ids"], later

    # RO07: a duplicate whose read could not be kept cannot settle -- and
    # settle() refusing it stopped the WHOLE run before any fresh send. It
    # is held back alone; the rest goes on.
    ready, held_back = verify.settleable(
        [{"finding_id": "CYM-a", "report_id": 49},
         {"finding_id": "CYM-e", "report_id": 90}], {49: "ev-1", 90: None})
    assert [i["finding_id"] for i in ready] == ["CYM-a"]
    assert [i["finding_id"] for i in held_back] == ["CYM-e"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_a2a_inbox_is_read_and_each_message_recorded_once(tmp_path, monkeypatch):
    """A2A: the channel we send questions down, and nothing was reading back.

    Found on 2026-09-07 by the operator asking how I would notice a reply.
    The answer was that I would not: bounty.py reads my-reports and nothing
    else, serve.py --ask runs bounty.py, and the only other reader parsed an
    archive that stopped being written in round one (qa/messages.py, retired
    2026-09-09 with the dead render helper that was its one importer). Twenty-three messages had
    accumulated in the a2a inbox and the only reason any of them had been read
    was that somebody asked out loud.

    So the read joins the sweep, and each message becomes one journal event
    keyed by its own id -- which makes re-reading the same inbox on the next
    sweep free, and makes forgetting impossible rather than unlikely.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    bounty = _module("scripts/bounty.py")
    from qa.state import read_events

    inbox = _inbox(_msg("a2a_1", "2026-09-07T10:00:00+00:00", "the routing guide", auto=True),
                   _msg("a2a_2", "2026-09-07T13:22:00+00:00", "a real answer"))

    first = bounty.fetch_inbox(client=inbox, agent_id="expire76-qa")
    assert first["klass"] == "ok"
    assert first["rows_returned"] == 2
    assert [m["msg_id"] for m in first["new"]] == ["a2a_1", "a2a_2"]

    messages = [e for e in read_events() if e["type"] == "message"]
    assert [e["msg_id"] for e in messages] == ["a2a_1", "a2a_2"]
    assert all(e["by"] == "vendor" for e in messages), \
        "a message from them recorded as ours"
    assert messages[1]["text"] == "a real answer", \
        "the body is not kept, so the journal records that they spoke and not what they said"
    # D6 of the review of 2026-09-23 (3/3): their words are kept (VENDOR_WORDS
    # includes `message`), but the capture they came in named no message, so
    # the keepset could not keep it. Each message now names the inbox read's
    # capture.
    read = [e for e in read_events() if e["type"] == "vendor_read"][0]
    assert all(m.get("evidence_id") == read.get("evidence_id") for m in messages), \
        [(m.get("evidence_id"), read.get("evidence_id")) for m in messages]

    # The next sweep reads the same inbox. Nothing is owed twice.
    again = bounty.fetch_inbox(client=inbox, agent_id="expire76-qa")
    assert again["new"] == []
    assert len([e for e in read_events() if e["type"] == "message"]) == 2
    # Plan v2, V8: a read is journaled when its HEALTH changes, not every
    # time -- a second clean read of the same door says nothing rule 8 needs,
    # and every console poll used to become a journal event and a commit.
    assert len([e for e in read_events() if e["type"] == "vendor_read"]) == 1

    # And the automated first pass is distinguishable from an answer, because
    # 21 of the 23 messages sitting in the real inbox were routing prompts.
    assert [m["msg_id"] for m in first["new"] if not m["auto"]] == ["a2a_2"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_inbox_we_could_not_read_records_no_messages(tmp_path, monkeypatch):
    """Rule 8, on the newest read. A refused inbox is not an empty inbox.

    The failure mode this forbids is the quiet one: 401, zero messages parsed,
    zero events written, and a sweep that says nothing -- indistinguishable
    from a vendor who has not replied. The read itself is still recorded, so
    the journal can tell "we looked and could not see" from "we did not look".
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    bounty = _module("scripts/bounty.py")
    from qa.state import read_events

    for status, klass in ((401, "unauthorized"), (500, "server_error"),
                          (404, "not_found")):
        denied = _client(lambda r, s=status: httpx.Response(s, text="no"))
        out = bounty.fetch_inbox(client=denied, agent_id="expire76-qa")
        assert out["klass"] == klass
        assert out["new"] == []
        assert out["rows_returned"] is None, \
            "0 would claim we read an inbox and found it empty"

    assert [e["type"] for e in read_events()] == ["vendor_read"] * 3, \
        "a refused read wrote a message event, or did not record that we looked"
    assert all(e["source"] != "scripts/bounty.py" for e in read_events()), \
        ("the inbox read shares a source with the tracker read, and vendor_read "
         "is keyed on at|source|klass -- two reads in one second would collapse")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_reply_full_of_emoji_does_not_kill_the_read():
    """Their text is data, and on this workspace data can kill the process.

    The console codepage here is cp1250. Their automated first pass opens with
    a trophy emoji, and printing it through an un-pinned stdout raises
    UnicodeEncodeError -- which happened to a scratch script on 2026-09-07 and
    would have taken the whole fetch down with it had it happened inside
    bounty.py, between the read and the events it writes.

    Every entry point pins utf-8, so this is a second line rather than the
    first. It is worth having because the input is a third party's and the
    failure is total: no snapshot, no events, and a sweep that stops on a
    character.
    """
    bounty = _module("scripts/bounty.py")

    trophy = "\U0001f3c6 Reward Pathways \u2014 stack your bonuses"
    # The encoding is a parameter so this asserts the reduction rather than
    # whatever pytest's own stdout happens to be. It is utf-8 here, and a test
    # that trusted it would watch the emoji sail straight through.
    safe = bounty._printable(trophy, "cp1250")
    assert "Reward Pathways" in safe
    safe.encode("cp1250")  # raises if a character survived that cannot be shown

    for hostile in ("", "\U0001f4b0" * 40, "line\nbreak", "\u2014\u2019\u201c"):
        bounty._printable(hostile, "cp1250").encode("cp1250")

    # One message, one line: a newline would break the shape the caller prints.
    assert "\n" not in bounty._printable("two\nlines", "cp1250")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verification_is_accepted_only_with_an_id_from_their_server():
    """VER: rule 9's other half, which verify.py shipped without.

    CLAUDE.md rule 9: "`accepted` needs 2xx **and** a server report id."
    submit.py implements exactly that; verify.py took the status alone. A 200
    that is not a created verification -- `{"success": false}`, a proxy's HTML,
    a 202 queued -- recorded as accepted, and the fold then clears
    verification_owed permanently, because the obligation is the only thing
    the sender ever reads. The dashboard would show them holding a
    verification their server never created, with no path to unwind it.

    Their real response carries one: {"success": true, "verification": {"id": 19}}.
    """
    verify = _module("scripts/verify.py")

    assert verify.verification_id({"success": True, "verification": {"id": 19}}) == 19
    assert verify.verification_id({"id": 3}) == 3
    assert verify.verification_id({"verification_id": 7}) == 7

    for refused in ({"success": False}, {"detail": "queued"}, {}, [], None,
                    {"verification": {}}, {"verification": None}):
        assert verify.verification_id(refused) is None, \
            f"{refused!r} was read as a created verification"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verification_their_server_already_holds_is_settled_not_re_sent(tmp_path, monkeypatch):
    """VER: the read that deduplicates is also the read that settles.

    If evidence capture fails between the POST and the outcome event, the
    vendor holds a verification and our journal holds only an intent. The
    obligation is computed from accepted outcomes, so it stays owed for ever;
    the next run's dedup read sees their copy and SKIPs; nothing is ever
    sent and nothing ever clears. A badge nobody can clear, which is the shape
    CLAUDE.md names.

    The fix is not a new flag. `already_sent()` is ALREADY a read of their
    server, which is the same evidence `--reconcile` gathers in submit.py --
    we simply were not writing down what it found. So a pair they hold and we
    do not settles itself, with the GET as its evidence.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    verify = _module("scripts/verify.py")
    from qa.state import read_events

    item = {"finding_id": "CYM-a", "report_id": 46, "fingerprint": "fp-1",
            "verdict": "pass", "run_id": "run-1", "tree_sha": "abc",
            "checked_at": "2026-09-07T12:00:00+00:00"}

    settled = verify.settle(item, evidence_id="ev-read")
    assert settled is True

    outcomes = [e for e in read_events() if e["type"] == "verification_outcome"]
    assert len(outcomes) == 1
    assert outcomes[0]["outcome"] == "accepted"
    assert outcomes[0]["evidence_id"] == "ev-read", \
        "the settlement cites nothing, so the fold will refuse it"
    assert outcomes[0]["reconciled_from"] == "verifications", \
        "a settlement must be distinguishable from an outcome we watched happen"

    # Idempotent, and asserted ACROSS a second boundary. The outcome's natural
    # key ends in |outcome|at, so two settlements a second apart are two
    # events unless something looks at the journal. The first version of this
    # test called settle() twice in a row and passed only because both landed
    # inside one wall-clock second -- a guard that measured the clock, not the
    # property its own comment named. Found by the adversarial round.
    later = ["2026-09-07T16:00:01+00:00", "2026-09-07T16:05:00+00:00",
             "2026-09-08T09:00:00+00:00"]
    for when in later:
        monkeypatch.setattr(verify, "_now", lambda w=when: w)
        assert verify.settle(item, evidence_id="ev-read") is False,             f"settling again at {when} wrote a second event for one fact"
    assert len([e for e in read_events() if e["type"] == "verification_outcome"]) == 1

    # A different verdict for the same report and definition IS a second fact.
    monkeypatch.setattr(verify, "_now", lambda: "2026-09-07T17:00:00+00:00")
    assert verify.settle({**item, "verdict": "fail"}, evidence_id="ev-read") is True
    assert len([e for e in read_events() if e["type"] == "verification_outcome"]) == 2

    # And it refuses to invent evidence.
    with pytest.raises(SystemExit, match="evidence"):
        verify.settle(item, evidence_id=None)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_broken_tracker_read_does_not_silence_the_inbox():
    """ASK: two surfaces, two faults, no shared control flow.

    The a2a inbox read was appended to serve.py's poll on 2026-09-07 after the
    tracker block's existing `continue`s, so a non-ok tracker read ended the
    iteration before it. An expired key on my-reports -- the exact incident
    classify_read exists for -- would therefore also stop a2a replies being
    noticed, for as long as the key stayed expired.

    That is the failure the inbox read was added to end: "a reply sat there
    until somebody thought to look, which is not a mechanism". Coupling it to
    an unrelated endpoint's health puts it straight back.

    Three triage agents reproduced it independently.
    """
    serve = _module("scripts/serve.py")

    class Bounty:
        def __init__(self, tracker):
            self.tracker, self.inbox_reads = tracker, 0

        def _last_status_by_report(self):
            return {}

        def refresh_our_reports(self):
            if self.tracker == "raises":
                raise RuntimeError("connection reset")
            return {"klass": self.tracker}

        def fetch_inbox(self):
            self.inbox_reads += 1
            return {"klass": "ok", "rows_returned": 1,
                    "new": [{"msg_id": "a2a_1", "at": "2026-09-07T16:00:00+00:00",
                             "auto": False, "text": "a real answer"}]}

        @staticmethod
        def _printable(text, encoding=None):
            return text

    for tracker in ("ok", "unauthorized", "server_error", "raises"):
        stub = Bounty(tracker)
        serve.poll_once(stub)
        assert stub.inbox_reads == 1, (
            f"a tracker read of {tracker!r} skipped the inbox; the one channel "
            f"their replies arrive on went silent on an unrelated fault")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_send_actually_sends(tmp_path, monkeypatch):
    """VER: the one test that calls send(), because nothing did.

    The rule-9 fix on 2026-09-07 added `body = response.json()` inside send().
    `body` is also the module-level function that composes the payload, and a
    local binding shadows it for the WHOLE function -- so `payload = body(item)`
    on the loop's first line raised UnboundLocalError before any POST. Every
    suite stayed green (321 and 47) because the five tests touching verify.py
    called owed, _capture, already_sent, verification_id and settle, and never
    the function that sends.

    A test that exercised the outcome branches would still have missed it; it
    had to be one that enters the loop. So this one drives a real batch through
    a mock transport and asserts on the journal, which is the only record that
    would have existed if it had gone out.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    verify = _module("scripts/verify.py")
    from qa.state import read_events

    item = {"finding_id": "CYM-a", "report_id": 46, "fingerprint": "fp-1",
            "verdict": "pass", "run_id": "run-1", "tree_sha": "abc123",
            "checked_at": "2026-09-07T12:00:00+00:00", "prereg_id": "PRE-0001",
            "checks": ["tests/a.py::test_x"], "title": "t"}

    def _sender(handler):
        """A mock client the guard will let POST, the way main() arranges it.

        Left to itself the transport refuses -- `MUTATE test attempted POST
        bounty.verification without --allow-mutate` -- which is the guard doing
        its job and is worth seeing here rather than mocked away.
        """
        client = _client(handler)
        client._transport.registry.mutate_enabled = True
        client._transport.registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
        return client

    in_flight = []

    def _made(request):
        # The journal while the POST is in flight (G12, deep pass 2026-09-24).
        in_flight.append([e["type"] for e in read_events()
                          if e["type"].startswith("verification_")])
        return httpx.Response(200, json={"success": True, "verification": {"id": 19}})
    created = _sender(_made)
    [result] = verify.send(created, [copy_item(item)], pause=0)
    assert result["outcome"] == "accepted", result
    assert in_flight == [["verification_intent"]], \
        "the intent must be on disk before the POST is made"

    events = [e for e in read_events() if e["type"].startswith("verification_")]
    assert [e["type"] for e in events] == ["verification_intent",
                                           "verification_outcome"], \
        "rule 9 wants the intent before the POST and the outcome after it"
    assert events[1]["evidence_id"], "the outcome cites nothing"

    # A 2xx that is not a created verification is not accepted (rule 9), and
    # the outcome is still written -- the attempt must never vanish.
    vague = _sender(lambda r: httpx.Response(200, json={"success": False}))
    [result] = verify.send(vague, [copy_item(item, report_id=47)], pause=0)
    assert result["outcome"] == "unknown"
    assert [e["type"] for e in read_events()
            if e.get("report_id") == 47] == ["verification_intent",
                                             "verification_outcome"]

    # RO07 (deep pass of 2026-09-24): an answer that could not be kept stops
    # the batch -- and the rest of it vanished with no line, the fault the
    # docstring finds in submit.py. They are named, as the rate-limit stop
    # names them.
    def _lost(response, tier=None):
        raise SystemExit("disk full")
    monkeypatch.setattr(verify, "_capture", _lost)
    said = verify.send(created, [copy_item(item, report_id=48),
                                 copy_item(item, report_id=49)], pause=0)
    assert [r["outcome"] for r in said] == ["unknown", "not attempted"], said


def copy_item(item, **over):
    out = dict(item)
    out.update(over)
    return out
