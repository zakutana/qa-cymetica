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
import re
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


def _live_payload(render):
    """The page as it would render RIGHT NOW, folded fresh from the journal.

    Never off the committed ledger. Reading that made two separate tests fail
    whenever the ledger was merely a re-fold behind the journal -- a
    bookkeeping lag -- and a meta failure aborts the session, so the run that
    would have caught up died at 88% on an unrelated assertion. Twice.
    """
    ledger_mod = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location(
            "ledger_live", REPO / "scripts" / "ledger.py"))
    ledger_mod.__loader__.exec_module(ledger_mod)
    from qa.state import RunIntegrityError

    try:
        current = ledger_mod.compose()
    except (SystemExit, RunIntegrityError):
        # No admissible run, or the newest one contradicts the repository.
        # Either is a real condition to report elsewhere; neither says
        # anything about whether the page reads fields the payload carries.
        current = ledger_mod.compose(events_only=True)
    return render.build_payload(ledger=current)


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

    # ...and only where it is actionable. On a withdrawn row it is noise; on
    # an unverifiable one the state already says the stronger thing. Six rows
    # wore it with nothing the operator could do about it.
    quiet = _row("CYM-withdrawn", "REPRODUCING", "WITHDRAWN")
    quiet["provenance"] = {"source": "legacy@ca0bc45", "measured_at": None}
    unmeasurable = _row("CYM-nocheck", "UNVERIFIABLE", "NOT_RAISED", checks=[])
    unmeasurable["provenance"] = {"source": "MSG-0002", "measured_at": None}

    shown = {f["id"]: f["unmeasured"] for f in
             render.build_payload(ledger=_ledger(quiet, unmeasurable))["findings"]}
    assert shown == {"CYM-withdrawn": False, "CYM-nocheck": False}, shown

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
def test_the_pages_javascript_parses(tmp_path, monkeypatch):
    """A syntax error in the page is invisible from Python and total in the
    browser: nothing renders, and the file still writes, commits and
    publishes. One shipped -- a duplicate `const ORDER` left behind by an edit
    -- and the page came up with the masthead and no findings at all.

    Skipped rather than failed where node is absent: a missing tool is not a
    defect in the page.
    """
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page's JS cannot be parsed here")

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()
    html = render.TEMPLATE

    start = html.index('<script>\n', html.index('id="data"'))
    script = html[start + len("<script>\n"):html.rindex("</script>")]
    script = script.replace("__DATA__", "{}")

    # No preamble: --check parses without running, and the page declares its
    # own `D`. Adding one produced exactly the duplicate-declaration error
    # this test exists to catch, in the scaffolding rather than the page.
    js = tmp_path / "page.js"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run([node, "--check", str(js)], capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, (
        "the dashboard's JavaScript does not parse, so the page renders "
        f"nothing:\n{result.stderr[:800]}"
    )


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
    payload = _live_payload(render)
    present = {k for f in payload["findings"] for k in f}

    read = {m for m in re.findall(r"\bf\.([a-z_]+)\b", render.TEMPLATE)}
    missing = sorted(read - present)
    assert not missing, (
        "the page reads fields no payload row carries, and JavaScript will "
        f"render them as undefined rather than fail: {missing}"
    )

    # The same check one level down. Missing it here put the literal words
    # "see undefined" on the page, inside a message quoted to the operator.
    threaded = {k for f in payload["findings"] for m in f["thread"] for k in m}
    if threaded:
        read_m = {m for m in re.findall(r"\bm\.([a-z_]+)\b", render.TEMPLATE)}
        missing_m = sorted(read_m - threaded)
        assert not missing_m, (
            f"the page reads message fields no thread entry carries: {missing_m}"
        )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_conversation_is_the_api_exchange_and_nothing_else(tmp_path, monkeypatch):
    """One channel per panel.

    Telegram and the bounty API have different properties -- attachments
    silently dropped on one, delivery unconfirmable on one, a report number
    and a written answer on the other. Showing both in one list produced a
    panel where a message nobody received sat beside a report they had
    answered, as though both were the same kind of fact. The panel is the API
    exchange: what we filed, and what they wrote back.
    """
    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()

    payload = _live_payload(render)
    threads = {f["id"]: f["thread"] for f in payload["findings"]}

    speakers = {m["who"] for t in threads.values() for m in t}
    assert speakers <= {"us", "them"}, speakers
    assert any(m["who"] == "them" and m.get("text") for t in threads.values() for m in t), \
        "not one of their written answers reached the page"
    for thread in threads.values():
        for message in thread:
            assert message.get("report_id"), "a message with no report behind it"
            assert "msg_id" not in message, "a Telegram message leaked into the API panel"

    # Every row that was filed has our side of it; nothing else has a thread.
    for finding in payload["findings"]:
        assert bool(finding["thread"]) == bool(finding["filed"]), finding["id"]

    # And our side of it has WORDS. state/submissions.json stopped being
    # written when filing became two events, so every report from #59 on
    # rendered as an empty green bubble with a date on it -- a projection
    # nobody updates, looking current. The words come from the journal now.
    speechless = sorted({m["report_id"] for t in threads.values() for m in t
                         if m["who"] == "us" and not (m.get("text") or "").strip()})
    assert not speechless, (
        f"reports {speechless} render as an empty bubble: what we sent them is "
        f"not reaching the page"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_filed_reports_reach_the_page(tmp_path, monkeypatch):
    """The report numbers still have to arrive, from the journal."""
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
def test_the_legend_explains_every_mark_and_uses_no_internal_words(tmp_path, monkeypatch):
    """A legend that needs its own glossary is not a legend.

    Two failures the operator hit. "figures not re-measured" appeared on rows
    and was explained only as the last sentence under the grid, in the same
    muted grey -- which is the same as not being explained. And the sentence
    said the wording came from "the old ledger", a word the page has never
    defined and the reader has no reason to know.

    A row carries six marks. Explaining one of them implies the rest are
    obvious, which is worse than explaining none.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()
    # The legend's own markup and the JS that fills it -- not the whole file,
    # which would drag in the masthead and every unrelated string below it.
    static = render.TEMPLATE[render.TEMPLATE.index("How to read this page"):
                             render.TEMPLATE.index('<script id="data"')]
    # From CHECK_WORDS, so the axis panels' own copy is checked too -- they
    # are the most-read part of the legend and were the first place the word
    # "adjudicates" slipped in.
    js = render.TEMPLATE[render.TEMPLATE.index("const CHECK_WORDS"):
                         render.TEMPLATE.index('document.getElementById("filters").addEventListener')]
    legend = static + js

    for chip in ("unmeasured-demo", "tagchip", "filed", "undelivered",
                 "mono-faint"):
        assert chip in legend, f"the legend shows no example of the {chip} mark"
    assert legend.count("MARKS") >= 2, "the marks panel is not rendered"

    # Words that mean something inside the pipeline and nothing to a reader.
    internal = ("ledger", "fold", "journal", "admissible", "fingerprint",
                "nodeid", "adjudicat")
    prose = re.sub(r"<[^>]+>", " ", legend)
    prose = re.sub(r"/\*.*?\*/", " ", prose, flags=re.S)      # CSS comments
    prose = re.sub(r"//[^\n]*", " ", prose)                    # JS comments
    prose = re.sub(r"\.[a-z-]+\s*\{[^}]*\}", " ", prose)       # CSS rules
    leaked = sorted({w for w in internal if w in prose.lower()})
    assert not leaked, (
        f"the legend uses vocabulary the reader has no way to know: {leaked}"
    )


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
