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
