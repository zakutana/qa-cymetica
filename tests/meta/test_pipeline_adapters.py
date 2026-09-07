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
