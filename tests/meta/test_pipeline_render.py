"""REN: the dashboard may not claim more than the ledger knows.

render.py printed *"We re-ran the check and it passes... this line is our own
measurement"* under every row whose state was VERIFIED FIXED, regardless of
where that state came from -- and all ten of them came from a hand-written
ledger in which `verified_by_run` was null on every single one. The timestamp
beside the sentence was `datetime.now()` from the merge that wrote it, not the
time of any run.

It also showed three different counts of the same thing on one screen: the
filter said 16, the tiles summed to 6, the ledger held 20.

Three rules here, each of which would have caught one of those:

  1. The verification sentence is printed only from `check.adjudicated_by`,
     and it prints the run id and the nodeid, so it can be checked.
  2. Every row lands in exactly one displayed bucket, and the buckets sum to
     the number of rows.
  3. Rendering is refused when the ledger does not cite the journal's current
     head -- a projection that has fallen behind its source is not a view of
     anything.

Fails at 1188032: render.py imports load_ledger from scripts.ledger, which no
longer exists, and reads a `state` field that rows no longer carry.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _render():
    path = REPO / "scripts" / "render.py"
    spec = importlib.util.spec_from_file_location("render_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ledger(*rows, head=None):
    from qa.state import head as journal_head

    return {
        "schema": 2,
        "findings": {r["id"]: r for r in rows},
        "events_head": head if head is not None else journal_head(),
    }


def _row(fid, check_state="UNVERIFIED", filing_state="NOT_RAISED", **over):
    from tests.meta.test_pipeline_fold import row

    r = row(fid, check_state=check_state, checks=["tests/a.py::test_x"])
    r["filing"]["state"] = filing_state
    r["severity"] = over.pop("severity", "S3-CONTRACT")
    r["section"] = over.pop("section", "discovery")
    r["obligations"] = {"reverify": False, "repair_check": False,
                        "reopen": [], "retractions": []}
    r.update(over)
    return r


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_verdict_requires_run_tuple_and_shows_not_checked(tmp_path, monkeypatch):
    """The sentence is printed from the adjudication, or not at all."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    backed = _row("CYM-backed", check_state="PASSING", filing_state="FIX_CLAIMED")
    backed["check"]["adjudicated_by"] = {"run_id": "run-20260905T120000Z-abc1234",
                                         "at": "2026-09-05T12:00:00+00:00"}
    unbacked = _row("CYM-unbacked", check_state="PASSING", filing_state="FIX_CLAIMED")
    unbacked["check"]["adjudicated_by"] = None
    skipped = _row("CYM-skipped", check_state="REPRODUCING", filing_state="RAISED")
    skipped["check"]["not_checked_in"] = "run-20260905T120000Z-abc1234"

    payload = render.build_payload(ledger=_ledger(backed, unbacked, skipped))
    by_id = {f["id"]: f for f in payload["findings"]}

    assert by_id["CYM-backed"]["verification"] == {
        "run_id": "run-20260905T120000Z-abc1234",
        "at": "2026-09-05T12:00:00+00:00",
        "nodeid": "tests/a.py::test_x",
    }
    assert by_id["CYM-unbacked"]["verification"] is None, \
        "a row with no adjudication was given a verification sentence"
    assert by_id["CYM-skipped"]["not_checked_in"] == "run-20260905T120000Z-abc1234"

    # And the template may not print the sentence off the display state alone.
    template = render.TEMPLATE
    assert "f.state === \"VERIFIED FIXED\"" not in template, \
        "the verification sentence is still driven by the display state"
    assert "f.verification" in template


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_counts_reconcile_and_every_bucket_rendered(tmp_path, monkeypatch):
    """Filter said 16, tiles summed to 6, the ledger held 20."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    rows = [
        _row("CYM-a", "REPRODUCING", "NOT_RAISED"),
        _row("CYM-b", "REPRODUCING", "RAISED"),
        _row("CYM-c", "PASSING", "FIX_CLAIMED"),
        _row("CYM-d", "INCONCLUSIVE", "FIX_CLAIMED"),
        _row("CYM-e", "UNVERIFIABLE", "RAISED"),
        _row("CYM-f", "UNVERIFIED", "NOT_RAISED"),
        _row("CYM-g", "REPRODUCING", "WITHDRAWN"),
    ]
    payload = render.build_payload(ledger=_ledger(*rows))

    assert len(payload["findings"]) == len(rows), \
        "a row was dropped between the ledger and the page"
    assert sum(payload["display_counts"].values()) == len(rows), (
        f"display counts {payload['display_counts']} do not sum to "
        f"{len(rows)} rows"
    )
    for finding in payload["findings"]:
        assert finding["display_state"] in payload["display_counts"]

    # Withdrawn rows are still counted somewhere, not silently dropped.
    assert payload["display_counts"].get("WITHDRAWN") == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_render_refuses_stale_ledger_head(tmp_path, monkeypatch):
    """A projection that has fallen behind its source is not a view of
    anything, and a dashboard that renders anyway is worse than no dashboard:
    it looks current."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event
    render = _render()

    append_event({"type": "note", "at": "2026-09-05T10:00:00+00:00",
                  "by": "operator", "source": "t", "finding_id": "CYM-a",
                  "text": "one"})
    stale = _ledger(_row("CYM-a"), head={"seq": 0, "chain": ""})

    with pytest.raises(SystemExit, match="head"):
        render.build_payload(ledger=stale)

    # Current head renders.
    from qa.state import head
    render.build_payload(ledger=_ledger(_row("CYM-a"), head=head()))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_legacy_content_is_labelled_unmeasured(tmp_path, monkeypatch):
    """Critique gap 5. The migration imports titles frozen at their last
    failing values -- CYM-anon-tool-surface says "served all 46" against
    today's 25. Importing the words is right; presenting them as current
    figures is not."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    legacy = _row("CYM-legacy", "UNVERIFIED", "RAISED")
    legacy["title"] = "An unauthenticated caller is served all 46 MCP tools"
    legacy["provenance"] = {"source": "legacy@ca0bc45", "measured_at": None}

    measured = _row("CYM-measured", "REPRODUCING", "RAISED")
    measured["provenance"] = {"run_id": "run-1", "measured_at": "2026-09-05T12:00:00+00:00"}

    payload = render.build_payload(ledger=_ledger(legacy, measured))
    by_id = {f["id"]: f for f in payload["findings"]}

    assert by_id["CYM-legacy"]["unmeasured"] is True
    assert by_id["CYM-measured"]["unmeasured"] is False
    assert "not measured in an admissible run" in render.TEMPLATE


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_regression_timeline_comes_from_transitions(tmp_path, monkeypatch):
    """Not from a timestamp field that the next merge could clear."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    row = _row("CYM-a", "REPRODUCING", "FIX_CLAIMED")
    row["regressions"] = [{"at": "2026-09-05T11:00:00+00:00", "run_id": "run-w",
                           "from_run": "run-v"}]
    row["transitions"] = [
        {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
         "cause": {"run_id": "run-v"}, "at": "2026-09-05T10:00:00+00:00"},
        {"axis": "check", "from": "PASSING", "to": "REPRODUCING",
         "cause": {"run_id": "run-w"}, "at": "2026-09-05T11:00:00+00:00"},
    ]

    payload = render.build_payload(ledger=_ledger(row))
    timeline = payload["timeline"]

    assert [e["to"] for e in timeline] == ["PASSING", "REPRODUCING"]
    assert all(e.get("run_id") for e in timeline), \
        "a timeline entry with no run behind it"
    assert timeline[-1]["finding_id"] == "CYM-a"
