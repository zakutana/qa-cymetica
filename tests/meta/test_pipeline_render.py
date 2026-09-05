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

    # The flag has to reach the page, and quietly: it is true on 19 of 23
    # rows, so styling it as an alarm buries the state chip beside it -- the
    # thing actually worth reading. Assert the marking exists and that it
    # carries its own explanation, not that it uses one particular phrase.
    assert 'class="unmeasured"' in render.TEMPLATE
    assert "f.unmeasured ?" in render.TEMPLATE
    import re

    rule = re.search(r"\.unmeasured[^{]*\{([^}]*)\}", render.TEMPLATE)
    assert rule, "the provenance note has no style of its own"
    assert "var(--bad" not in rule.group(1), \
        "the provenance note is styled as an alarm"
    assert "re-measured" in render.TEMPLATE and "title=" in render.TEMPLATE


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_reads_no_field_the_payload_stops_writing(tmp_path, monkeypatch):
    """The class of defect behind three separate visible breakages.

    `f.state` survived the two-axis rewrite; `f.filed`, `f.thread`,
    `f.undelivered` and `f.withdrawn_reason` survived the move of reports onto
    filing.reports and messages into the journal. JavaScript reading a missing
    property is `undefined`, not an error, so the page rendered quietly wrong:
    a tile saying "0 filed to their tracker" beside eleven filed reports, and
    an empty Correspondence panel on every row.
    """
    import re

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    # Measured against the COMMITTED ledger -- the page the operator actually
    # opens -- not against a row this test shaped by hand. A synthetic row
    # would only ever check the page against the test's idea of a row, and
    # miss exactly the drift the guard exists to catch. Fields that are
    # legitimately conditional (a `note` only some claims have) are covered
    # because the union across 23 real rows contains them.
    ledger_file = REPO / "state" / "ledger.json"
    if not ledger_file.exists():
        pytest.skip("no committed ledger to check the page against")

    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    payload = render.build_payload()
    present = {k for f in payload["findings"] for k in f}

    read = {m for m in re.findall(r"\bf\.([a-z_]+)\b", render.TEMPLATE)}
    missing = sorted(read - present)
    assert not missing, (
        "the page reads fields no payload row carries, and JavaScript will "
        f"render them as undefined rather than fail: {missing}"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_filed_reports_and_correspondence_reach_the_page(tmp_path, monkeypatch):
    """Both are rebuilt from the journal now, so both have to arrive."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    from tests.meta.test_pipeline_fold import _filed, event
    from qa.fold import fold

    events = _filed("CYM-a", 46, "pending") + [
        event("message", at="2026-09-04T11:03:00+00:00", by="operator",
              source="scripts/thread.py", msg_id="MSG-0001",
              findings=["CYM-a"], delivered=False),
        event("reply", at="2026-09-04T11:40:00+00:00", by="vendor",
              source="scripts/thread.py", msg_id="REPLY-0001",
              findings=["CYM-a"], reply_to="MSG-0001", evidence_id="e"),
        event("withdraw", at="2026-09-04T13:00:00+00:00", by="operator",
              source="scripts/withdraw.py", finding_id="CYM-a",
              reason="our check measured our own probe, not their contract"),
    ]
    for e in events:
        from qa.state import append_event
        append_event(e)

    from qa.state import head, read_events
    state = fold({"findings": {_row("CYM-a")["id"]: _row("CYM-a")}},
                 events=read_events())
    state["events_head"] = head()

    finding = render.build_payload(ledger=state)["findings"][0]
    assert [r["report_id"] for r in finding["filed"]] == [46]
    assert [m["id"] for m in finding["thread"]] == ["MSG-0001", "REPLY-0001"]
    assert finding["undelivered"] == 1, "a message nobody delivered reads as delivered"
    assert "our own probe" in finding["withdrawn_reason"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_display_state_is_visually_distinct(tmp_path, monkeypatch):
    """A state chip with no colour rule renders as plain grey text, and the
    operator reads straight past it.

    Seven of the sixteen states had a rule and three of those seven named
    states that no longer exist, so nine chips -- PASSING (UNPINNED) and
    WITHDRAWN among them -- were unstyled. The class was also built by
    replacing spaces only, so PASSING (UNPINNED) produced the class
    `s-passing-(unpinned)`: parentheses are not valid in a bare CSS class
    selector, so no rule could have matched it however many were written.
    """
    import re

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.fold import DISPLAY
    render = _render()

    css = render.TEMPLATE
    missing = []
    for state in sorted(set(DISPLAY.values())):
        slug = re.sub(r"[^a-z0-9]+", "-", state.lower()).strip("-")
        assert "(" not in slug and ")" not in slug, slug
        if f".state.s-{slug}" not in css:
            missing.append(f"{state} -> .state.s-{slug}")
    assert not missing, (
        "these display states render with no colour of their own:\n  "
        + "\n  ".join(missing)
    )

    # The class the page emits at runtime has to be the one CSS names, so the
    # two slug rules are pinned to each other rather than left to drift.
    assert 'replace(/[^a-z0-9]+/g, "-")' in css, \
        "the state class is not slugified, so punctuation breaks the selector"
    assert 'replace(/^-|-$/g, "")' in css, \
        "the slug keeps edge hyphens, which the CSS rules do not have"

    # Dead rules are their own hazard: they read as coverage that is not there.
    live = {re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
            for s in set(DISPLAY.values())}
    for slug in re.findall(r"\.state\.s-([a-z0-9-]+)", css):
        assert slug in live, f".state.s-{slug} styles a state that no longer exists"


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
