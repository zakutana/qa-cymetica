"""Nothing may be deleted that anything can still cite.

The pile is real -- 836 records, and every `pytest tests/meta -q` while
working adds one -- and the operator asked not to have to think about it. But
a cleanup glob once removed the record the ledger had just been folded from,
which is why the sweep's rules say "by name, never by glob", and why this file
exists before the script is ever run with --apply.

Each test names one reason a record survives. The dangerous one is `scope`:
the deep pass builds its audit scope from the newest known definition of each
live check, so deleting the only record carrying one silently drops that check
out of the audit -- the same defect the 2026-09-09 pass found in itself, this
time caused by tidying up.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "prune_runs", REPO / "scripts" / "prune_runs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(state, run_id, started, results=None, tracked=False):
    (state / "runs").mkdir(parents=True, exist_ok=True)
    (state / "runs" / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id, "started_at": started, "finished_at": started,
        "results": results or [], "schema": 2,
    }), encoding="utf-8")


def _ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _state(tmp_path, monkeypatch, ledger=None, tracked=()):
    state = tmp_path / "state"
    (state / "journal").mkdir(parents=True, exist_ok=True)
    (state / "journal" / "events.jsonl").write_text("", encoding="utf-8")
    (state / "ledger.json").write_text(json.dumps(
        ledger or {"schema": 2, "findings": {}}), encoding="utf-8")
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    import qa.state

    importlib.reload(qa.state)
    mod = _module()
    monkeypatch.setattr(mod, "tracked_records", lambda: set(tracked))
    return state, mod


def _capture(state, digest, *, url="https://cymetica.com/api/v1/thing",
             method="GET", rpc=None, age_days=0):
    """One capture on disk, with a timestamp we control.

    `rpc` makes it an MCP call: every one of those goes to the same path, so
    the JSON-RPC method and tool are what tell two of them apart.
    """
    import os

    path = state / "evidence" / "sha256" / digest[:2] / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"encoding": "empty", "value": None}
    if rpc:
        body = {"encoding": "json", "value": {
            "jsonrpc": "2.0", "method": "tools/call",
            "params": {"name": rpc, "arguments": {}}}}
    path.write_text(json.dumps({
        "captured_at": _ago(age_days), "run_id": "run-whatever", "nodeid": None,
        "request": {"method": method, "url": url, "headers": {}, "body": body},
        "response": {"status_code": 200, "headers": {},
                     "body": {"encoding": "json", "value": {}}},
    }), encoding="utf-8")
    stamp = (datetime.now(timezone.utc) - timedelta(days=age_days)).timestamp()
    os.utime(path, (stamp, stamp))
    return path


def _no_git(monkeypatch):
    """git holds nothing in a temporary repository, and saying so is the point:
    otherwise `tracked` would keep every capture and no reason could be told
    from any other."""
    from qa import keepset

    monkeypatch.setattr(keepset, "tracked_evidence", lambda: set())


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_capture_a_row_stands_on_is_never_a_victim(tmp_path, monkeypatch):
    """What a verdict cited is what we promised them "on request"."""
    run_id = "run-20260901T000000Z-stood"
    ledger = {"schema": 2, "findings": {"CYM-a": {
        "checks": ["tests/x.py::test_y"],
        "check": {"adjudicated_by": {"run_id": run_id}},
    }}}
    state, mod = _state(tmp_path, monkeypatch, ledger=ledger)
    _no_git(monkeypatch)
    stood, newer, older = "a" * 64, "b" * 64, "c" * 64
    _write(state, run_id, _ago(30), results=[
        {"nodeid": "tests/x.py::test_y", "evidence_ids": [stood]}])
    _capture(state, stood, age_days=30)
    # Same call twice, both old: one of them is the last answer that surface
    # ever gave us, and the other is nothing to anybody.
    _capture(state, newer, url="https://cymetica.com/api/v1/cards", age_days=20)
    _capture(state, older, url="https://cymetica.com/api/v1/cards", age_days=25)

    keep = mod.evidence_keep_set()
    assert keep.get(stood) == "kept", keep
    assert keep.get(newer) == "witness", keep
    assert older not in keep, "an old capture nothing stands on is a victim"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_capture_is_as_young_as_the_newest_run_that_cites_it(tmp_path,
                                                               monkeypatch):
    """The store dedupes by content, so the file's own date is the FIRST
    sighting. Five captures were cited by runs four days younger than
    themselves on the day this was written; deleting one of those would have
    cut the evidence under a run somebody may still fold."""
    state, mod = _state(tmp_path, monkeypatch)
    _no_git(monkeypatch)
    revisited, stale = "d" * 64, "e" * 64
    _write(state, "run-20260910T000000Z-fresh", _ago(1), results=[
        {"nodeid": "tests/x.py::test_y", "evidence_ids": [revisited]}])
    _capture(state, revisited, url="https://cymetica.com/api/v1/same",
             age_days=30)
    _capture(state, stale, url="https://cymetica.com/api/v1/same", age_days=29)

    keep = mod.evidence_keep_set()
    assert keep.get(revisited) == "young", keep
    assert keep.get(stale) == "witness", (
        "the newest capture of a call survives even when a younger sibling is "
        "kept for another reason -- that is one file per call, by design")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_mcp_tools_are_two_calls_even_on_one_path(tmp_path, monkeypatch):
    """All 812 MCP calls on this machine go to `/mcp/v1/`. Keyed on the path
    alone, the newest capture of the whole endpoint would be the only one kept
    -- and the tool catalogue the laboratory compares Nexus against, before and
    after their upgrade, is one of those calls."""
    state, mod = _state(tmp_path, monkeypatch)
    _no_git(monkeypatch)
    catalogue, returns, older_returns = "1" * 64, "2" * 64, "3" * 64
    mcp = "https://cymetica.com/mcp/v1/"
    _capture(state, catalogue, url=mcp, method="POST", rpc="tools/list",
             age_days=20)
    _capture(state, returns, url=mcp, method="POST",
             rpc="get_strategy_returns", age_days=20)
    _capture(state, older_returns, url=mcp, method="POST",
             rpc="get_strategy_returns", age_days=25)

    keep = mod.evidence_keep_set()
    assert keep.get(catalogue) == "witness", keep
    assert keep.get(returns) == "witness", keep
    assert older_returns not in keep


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_record_the_ledger_cites_is_never_a_victim(tmp_path, monkeypatch):
    ledger = {"schema": 2, "findings": {"CYM-a": {
        "check": {"adjudicated_by": {"run_id": "run-20260901T000000Z-cited"}},
        "transitions": [{"cause": {"run_id": "run-20260901T000000Z-deep"}}],
    }}}
    state, mod = _state(tmp_path, monkeypatch, ledger=ledger)
    _write(state, "run-20260901T000000Z-cited", _ago(30))
    _write(state, "run-20260901T000000Z-deep", _ago(30))
    # Older than the other two, so they have already accounted for every
    # refusal reason an empty record carries. `last-fired` keeps at most one
    # record per symbol, and this is what "at most one" looks like.
    _write(state, "run-20260901T000000Z-loose", _ago(40))

    keep = mod.keep_set()
    assert keep.get("run-20260901T000000Z-cited") == "cited"
    assert keep.get("run-20260901T000000Z-deep") == "cited", (
        "a run id nested inside a transition's cause is still a citation"
    )
    assert "run-20260901T000000Z-loose" not in keep


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_young_record_and_a_tracked_one_both_survive(tmp_path, monkeypatch):
    state, mod = _state(tmp_path, monkeypatch,
                        tracked={"run-20260901T000000Z-intree"})
    _write(state, "run-20260901T000000Z-intree", _ago(30))
    _write(state, "run-20260909T000000Z-fresh", _ago(1))
    _write(state, "run-20260801T000000Z-old", _ago(40))

    keep = mod.keep_set(older_than_days=7)
    assert keep.get("run-20260901T000000Z-intree") == "tracked"
    assert keep.get("run-20260909T000000Z-fresh") == "young"
    assert "run-20260801T000000Z-old" not in keep


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_newest_definition_of_a_live_check_is_never_deleted(
        tmp_path, monkeypatch):
    """The audit scope is built from these, and losing one is silent."""
    state, mod = _state(tmp_path, monkeypatch)
    live = sorted(mod._live_nodeids())
    assert live, "no live checks found, so this test proves nothing"
    nodeid = live[0]

    _write(state, "run-20260801T000000Z-newest", _ago(30),
           results=[{"nodeid": nodeid, "check_fingerprint": "sha256:new",
                     "outcome": "passed"}])
    _write(state, "run-20260701T000000Z-older", _ago(60),
           results=[{"nodeid": nodeid, "check_fingerprint": "sha256:old",
                     "outcome": "passed"}])

    keep = mod.keep_set()
    assert keep.get("run-20260801T000000Z-newest") == "scope"
    assert "run-20260701T000000Z-older" not in keep, (
        "only the newest definition of each check has to survive"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_last_run_a_verdict_ever_occurred_in_survives(tmp_path, monkeypatch):
    """never_fired.py answers "has this ever happened"; deleting the only
    record where it did would turn a yes into a no.

    The reason is `last-verdict`, and it must not be the same word the refusals
    branch writes. Both said "last-fired", so deleting the verdict branch
    outright left this assertion green -- `admissibility()` on the same bare
    fixture returns four unseen refusal reasons and the other branch set the
    identical string. Three readers reproduced that by removing the four lines.
    Two mechanisms whose output cannot be told apart are one mechanism as far
    as any test can see.
    """
    state, mod = _state(tmp_path, monkeypatch)
    _write(state, "run-20260801T000000Z-rare", _ago(30),
           results=[{"nodeid": "tests/gone.py::test_x", "outcome": "failed",
                     "measurement": {"verdict": "inconclusive"}}])

    assert mod.keep_set().get("run-20260801T000000Z-rare") == "last-verdict"

    # The distinguishing case: a NEWER record carrying the same refusal reasons
    # and no measurements at all. It takes `last-refusal`, and the older one
    # must still be saved by its verdict rather than sharing the same word.
    _write(state, "run-20260901T000000Z-empty", _ago(20), results=[])
    keep = mod.keep_set()
    assert keep.get("run-20260801T000000Z-rare") == "last-verdict", (
        f"the sole occurrence of a verdict lost its own reason to a newer "
        f"record with none: {keep}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_record_that_cannot_be_read_is_never_a_victim(tmp_path, monkeypatch):
    """Rule 8, in the only script here that deletes.

    `_load` returned `{}` on any failure and every keep-reason then missed the
    record -- no started_at so not young, no results so neither scope nor
    last-fired -- and an untracked, uncited one went straight into `victims()`.
    `qa/report_plugin.py` writes these with a non-atomic `write_text`, so a
    record caught mid-write by a concurrent pytest parses as garbage. Three
    readers reproduced the deletion.
    """
    state, mod = _state(tmp_path, monkeypatch)
    _write(state, "run-20260801T000000Z-fine", _ago(30), results=[])
    broken = state / "runs" / "run-20260801T000000Z-corrupt.json"
    broken.write_text('{"run_id": "run-20260801T000000Z-corr', encoding="utf-8")

    keep = mod.keep_set()
    assert keep.get("run-20260801T000000Z-corrupt") == "unreadable", (
        f"a record that cannot be parsed is one we cannot show is safe to "
        f"remove: {keep}")
    assert broken not in mod.victims()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_named_only_in_prose_is_still_cited(tmp_path, monkeypatch):
    """`cited_run_ids` claims "every run id anything in the repository still
    names" and matched only the literal key `run_id`.

    It missed run-20260908T150721Z-435ad0b, which is named inside a withdraw
    event's REASON TEXT as the capture proving their fix predated our fail
    verification -- the evidence behind the retraction owed on #83. The
    structural walk returned 170 ids against 171 by text scan, and that record
    survived only as "young", which runs out. Three readers reproduced it.
    """
    named = "run-20260801T000000Z-abc1234"
    # The id sits in a REASON, which is prose. No `run_id` key holds it, and
    # that is the whole point: the structural walk cannot see it.
    ledger = {"schema": 2, "findings": {"CYM-a": {
        "detail": {"reason": f"withdrawn: the capture in {named} shows their "
                             f"fix predated our fail verification"},
    }}}
    state, mod = _state(tmp_path, monkeypatch, ledger=ledger)
    _write(state, named, _ago(30), results=[])

    assert named in mod.cited_run_ids(), (
        "a run id the repository names in prose is still a citation")
    assert mod.keep_set().get(named) == "cited"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_ledger_that_cannot_be_read_is_not_a_ledger_citing_nothing(
        tmp_path, monkeypatch):
    """Rule 8 over the other two files the keep set is built from.

    The journal already refuses: `qa.state.read_events` raises on a truncated
    line, and both sweeps here then keep everything, loudly. The ledger read
    beside it did not -- `keepset._ledger_as_written` swallowed the
    JSONDecodeError and returned `{}` on purpose, so a file caught mid-write
    left `must_keep` silently thin instead of raising, and `--apply` deleted
    captures a row stands on: the request and response every verdict we have
    sent promises the vendor "on request". The record sweep had the same hole
    through `_load`, where an unreadable ledger cites no run at all.

    Reproduced against the same fixture healthy and truncated: 0 victims,
    then the cited capture and the cited record among them.
    """
    run_id = "run-20260901T000000Z-stood"
    ledger = {"schema": 2, "findings": {"CYM-a": {
        "checks": ["tests/x.py::test_y"],
        "check": {"adjudicated_by": {"run_id": run_id}},
    }}}
    state, mod = _state(tmp_path, monkeypatch, ledger=ledger)
    _no_git(monkeypatch)
    stood, sibling = "a" * 64, "b" * 64
    _write(state, run_id, _ago(30), results=[
        {"nodeid": "tests/x.py::test_y", "evidence_ids": [stood]}])
    capture = _capture(state, stood, age_days=30)
    # A younger capture of the SAME call, so `witness` is already spoken for
    # and losing `kept` really does mean deletion rather than a changed label.
    _capture(state, sibling, age_days=20)

    assert mod.evidence_keep_set().get(stood) == "kept"
    assert mod.keep_set().get(run_id) == "cited"
    assert mod.evidence_victims() == [] and mod.victims() == [], (
        "the healthy half of this test must have nothing to delete, or the "
        "truncated half proves nothing")

    # Truncated before the run id, so the prose scan cannot rescue it either.
    (state / "ledger.json").write_text('{"schema": 2, "findings": {"CYM-a": {"ch',
                                       encoding="utf-8")

    assert mod.evidence_keep_set().get(stood) == "unreadable", (
        "a ledger that cannot be parsed is not a ledger that cites nothing; "
        "the capture behind a verdict we sent went into the victims")
    assert capture not in mod.evidence_victims()
    assert mod.keep_set().get(run_id) == "unreadable"
    assert state / "runs" / f"{run_id}.json" not in mod.victims()

    # And a ledger that is simply not there yet is still an empty one: a fresh
    # state directory has no rows, and refusing to prune there would mean the
    # pile only ever grows on the machine that has never folded anything.
    (state / "ledger.json").unlink()
    assert mod.evidence_keep_set().get(stood) != "unreadable"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_capture_the_manifest_knows_is_not_pruned_before_a_bundle_holds_it(
        tmp_path, monkeypatch, capsys):
    """D1 of the 2026-09-23 review (3/3). The manifest is the proof that
    outlives a body -- but only once a bundle holds the body. When the ledger
    folded onto a new run, captures stopped being cited; the pruner deleted
    them as nothing-stands-on-it before any archive had taken them, and 392
    are gone for good: known to the manifest, `archive: ""` for ever, their
    bodies in no bundle and on no disk.

    So a capture the manifest knows is held back until a bundle on this disk
    holds it: no stamp, or a stamp whose bundle is not here, keeps it. Only a
    body the bundle lists may go. And the pruner says how many it held back,
    so a failed archive is a number on screen, not a pile that quietly
    grows."""
    from qa import archive, manifest

    state, mod = _state(tmp_path, monkeypatch)
    _no_git(monkeypatch)
    url = "https://cymetica.com/api/v1/same"
    witness, bundled, unstamped, elsewhere = ("f" * 64, "1a" * 32,
                                              "2b" * 32, "3c" * 32)
    _capture(state, witness, url=url, age_days=10)
    for digest in (bundled, unstamped, elsewhere):
        _capture(state, digest, url=url, age_days=20)
    target = archive.archive_path("2026-09")
    archive.build([bundled], target)
    archive.commit(target, releasable=True)
    assert archive.members(target) == {bundled}
    manifest.write({
        bundled: {"id": bundled, "archive": "evidence-2026-09"},
        unstamped: {"id": unstamped, "archive": ""},
        # Stamped into a bundle that is not on this disk.
        elsewhere: {"id": elsewhere, "archive": "evidence-2026-08"},
    })

    keep = mod.evidence_keep_set()
    assert keep.get(witness) == "witness", keep
    assert keep.get(unstamped) == "unarchived", keep
    assert keep.get(elsewhere) == "unarchived", keep
    assert bundled not in keep, "a body a bundle holds may go"

    capsys.readouterr()
    assert mod.main(["--apply"]) == 0
    out = capsys.readouterr().out
    assert "held back 2" in out, out
    left = {p.stem for p in (state / "evidence").rglob("*.json")}
    assert left == {witness, unstamped, elsewhere}, left


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_dry_run_deletes_nothing_and_apply_deletes_only_the_victims(
        tmp_path, monkeypatch, capsys):
    state, mod = _state(tmp_path, monkeypatch)
    _write(state, "run-20260909T000000Z-fresh", _ago(1))
    _write(state, "run-20260801T000000Z-old", _ago(40))
    before = {p.name for p in (state / "runs").glob("*.json")}

    assert mod.main([]) == 0
    assert {p.name for p in (state / "runs").glob("*.json")} == before, \
        "a dry run deleted something"
    assert "Nothing deleted" in capsys.readouterr().out

    assert mod.main(["--apply"]) == 0
    left = {p.name for p in (state / "runs").glob("*.json")}
    assert left == {"run-20260909T000000Z-fresh.json"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unreadable_audit_file_is_not_an_audit_file_citing_nothing(
        tmp_path, monkeypatch):
    """The same refusal, over the OTHER file `cited_run_ids` opens.

    The first version of this guard covered `state/ledger.json` and left
    `audits/checks.json` one line below it reading `.get("audited") or {}` --
    so an unreadable one cited nothing and every record it alone cites went
    into `victims()`. Two readers of the 2026-09-13 pass reproduced the loss by
    simulation: four records, among them
    run-20260907T175903Z-c4b34d4, moved from kept to doomed. The claim that
    reached them said checks.json cites 607 run ids; it cites twelve. The
    number was wrong and the deletion was real, which is why a claim is
    reproduced rather than believed.

    `_live_nodeids` is stubbed because the refusal returns before it is
    reached, and with REPO_ROOT moved it would look for never_fired.py in the
    temporary tree.
    """
    state, mod = _state(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "_live_nodeids", lambda: set())
    cited = "run-20260801T000000Z-audited"
    _write(state, cited, _ago(30), results=[])

    audits = tmp_path / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    (audits / "checks.json").write_text(json.dumps(
        {"audited": {"tests/x.py::test_y": {"run_id": cited,
                                            "fingerprint": "sha256:a"}}}),
        encoding="utf-8")
    assert mod.keep_set().get(cited) == "cited", (
        "a record named only by audits/checks.json is cited; without that the "
        "truncated half below proves nothing")

    (audits / "checks.json").write_text('{"audited": {"tests/x.py::test_',
                                        encoding="utf-8")
    assert mod.keep_set().get(cited) == "unreadable", (
        "a checks.json that cannot be parsed is not one that cites nothing")
    assert mod.victims() == []

    # Absent is still empty: a clone that has never run an audit has no such
    # file, and refusing there would mean nothing is ever pruned on it.
    (audits / "checks.json").unlink()
    assert mod.keep_set().get(cited) != "unreadable"
