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
  3. The page says which journal event the state it shows was composed at,
     and says only what the ledger knows. It used to REFUSE to render behind
     the journal; that refusal is gone, because the console appends two
     vendor_read events a quarter-hour and the fold moves nothing on them --
     see scripts/ledger.py::drift, which asks the question the refusal was
     reaching for and asks it of the rows.

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


def _lab_page():
    """scripts/lab_page.py -- the laboratory's page, /lab (plan v2, V4): the
    Nexus rooms and the memecoin measurement live there, not in the console."""
    path = REPO / "scripts" / "lab_page.py"
    spec = importlib.util.spec_from_file_location("lab_page_mod", path)
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


def _committed_payload(render):
    """The page as COMMITTED: the ledger in the tree and the run it cites.

    Not `_live_payload`, which composes fresh and therefore stands on the
    newest admissible run -- which, during a test session, is whatever record
    the last pytest invocation wrote. A self-test-only run has no result about
    their platform in it, so every assertion about the tiles passes vacuously
    over an empty list.
    """
    return render.build_payload()


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
def test_the_page_says_which_journal_head_it_stands_on(tmp_path, monkeypatch):
    """A page behind the journal is fine; a page that will not say so is not.

    This replaces test_render_refuses_stale_ledger_head. Refusing was the
    right instinct aimed at the wrong thing: build_payload raised when the
    ledger cited anything but the journal's current head, so the console
    (serve.py:151), both repo guards and this file all passed
    allow_stale_head=True and the refusal reached nobody but the CLI -- while
    the console appended two vendor_read events every fifteen minutes that the
    fold reads only to set or clear stale_from.

    Whether the ledger is WHAT ITS INPUTS FOLD TO is asked, of the rows, by
    scripts/ledger.py::drift. What is left for the page is to say what it is a
    view of, which is the honest version of the same care: the operator can
    read the number and see it move after a fold.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, head
    render = _render()

    append_event({"type": "note", "at": "2026-09-05T10:00:00+00:00",
                  "by": "operator", "source": "t", "finding_id": "CYM-a",
                  "text": "one"})
    behind = _ledger(_row("CYM-a"), head={"seq": 0, "chain": ""})

    # No refusal, and the payload carries the LEDGER's head, never the
    # journal's -- the page may not claim more than the ledger knows.
    payload = render.build_payload(ledger=behind)
    assert payload["events_head"] == {"seq": 0, "chain": ""}
    assert payload["events_head"] != head()

    # And the page reads it. The field was already in the payload and hashed
    # into the marker, and nothing drew it: an unread payload key, which is
    # the class test_the_page_renders_every_field_it_is_given exists for and
    # does not cover, because that one walks per-finding keys only.
    assert re.search(r"\bD\.events_head\b", render.TEMPLATE), (
        "the payload names the journal event the state was composed at and "
        "the page does not print it"
    )
    assert "state as of" in render.render(payload)


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

    # `[A-Za-z_][A-Za-z0-9_]*`, not `[a-z_]+`: the narrow class cannot match a
    # camelCase or digit-bearing property at all, so `f.displayState` and
    # `f.a2a_id` were outside the population this compares and would have
    # rendered as `undefined` with the guard green. The sibling in
    # test_pipeline_rooms.py was widened for the identical defect (P13) on
    # 2026-09-11 and this one was not.
    read = {m for m in re.findall(r"\bf\.([A-Za-z_][A-Za-z0-9_]*)\b",
                                  render.TEMPLATE)}
    missing = sorted(read - present)
    assert not missing, (
        "the page reads fields no payload row carries, and JavaScript will "
        f"render them as undefined rather than fail: {missing}"
    )

    # The same check one level down. Missing it here put the literal words
    # "see undefined" on the page, inside a message quoted to the operator.
    threaded = {k for f in payload["findings"] for m in f["thread"] for k in m}
    if threaded:
        read_m = {m for m in re.findall(r"\bm\.([A-Za-z_][A-Za-z0-9_]*)\b",
                                        render.TEMPLATE)}
        missing_m = sorted(read_m - threaded)
        assert not missing_m, (
            f"the page reads message fields no thread entry carries: {missing_m}"
        )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_verdict_the_inventory_can_produce_is_drawable():
    """A verdict the page cannot draw is a hole in the bar, not a zero.

    `server_error` and `unreachable` were producible by inventory.py and
    absent from the page's ORDER, so an endpoint in either state fell out of
    the coloured bar, out of the legend, and -- because the bar's total is
    summed over ORDER -- out of the denominator the segments are drawn
    against. A section could read 80% with the remaining fifth represented by
    nothing at all.

    Neither had ever occurred, which is exactly why nobody noticed. Held
    against the source of the verdicts rather than against a list written
    beside it, so adding a tenth kind fails here rather than on the day it
    first happens.
    """
    import inspect

    spec = importlib.util.spec_from_file_location(
        "inventory_mod", REPO / "scripts" / "inventory.py")
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    render = _render()

    produced = set(re.findall(r'return "([a-z_]+)"',
                              inspect.getsource(inventory.verdict)))
    order = re.search(r"const ORDER = \[(.*?)\];", render.TEMPLATE, re.S)
    assert order, "the page no longer declares an ORDER of verdicts"
    drawable = set(re.findall(r'"([a-z_]+)"', order.group(1)))

    assert not produced - drawable, (
        f"inventory.py produces verdicts the page cannot draw: "
        f"{sorted(produced - drawable)}"
    )
    words = re.search(r"VERDICT_WORDS = \{(.*?)\};", render.TEMPLATE, re.S)
    described = set(re.findall(r"^\s+([a-z_]+):", words.group(1), re.M))
    assert not drawable - described, (
        f"drawn with no words to explain them: {sorted(drawable - described)}"
    )
    uncoloured = [k for k in sorted(drawable)
                  if f".seg-{k}{{" not in render.TEMPLATE
                  and f".seg-{k}," not in render.TEMPLATE]
    assert not uncoloured, f"drawn with no colour of their own: {uncoloured}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_renders_every_field_it_is_given(monkeypatch):
    """The other direction, and the one that stayed open longer.

    Its sibling above catches a page reading a field the payload stopped
    writing -- undefined on screen, loudly. This catches a payload writing a
    field the page never reads, which is silent, and therefore worse: nothing
    ever tells you the value stopped being right, because nothing is looking
    at it.

    Two rules were half-built behind exactly that. `stale_from` carried rule
    8's "mark the row stale" and was rendered nowhere, so a failed read of the
    vendor's tracker changed nothing an operator could see. `obligations`
    carried rule 11's "the row shows retraction owed on #N" and was rendered
    nowhere, so the two rows owing a re-verify said so in CLI output alone.
    Both were found by hand; this is here to find the next one.

    The payload row used to be `{**row, ...derived}`, shipping eleven of
    nineteen ledger fields to the browser unread. It is a named projection
    now, which is what makes this a contract rather than a chore.
    """
    render = _render()
    payload = _live_payload(render)
    present = {k for f in payload["findings"] for k in f}

    # `f.x` is how the template reads a row, but a bare `.x` counts too: a
    # field read through a helper under another name is still read, and this
    # guard must not push anyone into renaming variables to satisfy it.
    unread = sorted(
        field for field in present
        if not re.search(r"\.%s\b" % re.escape(field), render.TEMPLATE)
    )
    assert not unread, (
        "the payload ships row fields the page never reads, so nothing would "
        f"notice if they stopped being correct: {unread}. Render them, or "
        f"stop sending them."
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
    # Anchored on the panel id, not on a heading. The legend moved into its
    # own tab on 2026-09-06 and its <h3> went with it -- the tab label says it
    # now -- so a test keyed to that sentence broke on a presentation change
    # while the thing it guards was untouched.
    static = render.TEMPLATE[render.TEMPLATE.index('id="panel-legend"'):
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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_css_variable_the_sheet_uses_is_defined():
    """A var() with no definition is invisible, not broken.

    The notification panel was written with background:var(--card). This sheet
    has no --card; the token is --surface. CSS does not complain -- the
    declaration is simply dropped, so the panel had no background at all and
    the page read straight through it. Nothing in the suite noticed, because
    every test asked whether an element existed, and it did.

    One line catches the whole class, including the next typo in a token name.
    """
    import re

    css = _render().TEMPLATE
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", css))
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", css))
    missing = sorted(used - defined)

    assert not missing, (
        f"{len(missing)} CSS variable(s) are used but never defined, so every "
        f"declaration reading them is silently dropped: {', '.join(missing)}"
    )
    assert used, "the sheet reads no variables at all, which cannot be right"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_vendor_reply_carries_a_stable_date():
    """A reply with no date is one the reader can never mark as read.

    The page marks a row when the vendor said something newer than the last
    time you looked. Two replies had no date at all: a report closed as
    `invalid` carries none of fixed_at, validated_at, triaged_at or even
    updated_at -- only created_at, which is when WE filed it. The page filled
    the gap with Date.now(), which is recomputed on every render, so those two
    rows were newer than any "seen" moment forever and their envelopes could
    not be cleared. "Mark all as read" appeared to do nothing.

    Two properties, and the second is the one the first fix missed: the date
    must EXIST, and it must not move. bounty.py appends a vendor_status event
    on every run, so dating a reply from the newest observation would record
    when we last polled and bring the mark back after every sweep.
    """
    render = _render()
    first = render.build_payload()
    second = render.build_payload()

    def replies(payload):
        return {(f["id"], m.get("report_id")): m.get("at")
                for f in payload["findings"]
                for m in (f.get("thread") or [])
                if m.get("who") and m["who"] != "us"}

    a, b = replies(first), replies(second)
    undated = sorted(k for k, v in a.items() if not v)
    assert not undated, (
        f"{len(undated)} vendor repl(ies) carry no date, so the row they are "
        f"on can never be marked read: {undated}"
    )

    moved = sorted(k for k in a if a[k] != b.get(k))
    assert not moved, (
        f"{len(moved)} vendor repl(ies) changed date between two builds of the "
        f"same state, so the unread mark would return on every render: {moved}"
    )

    # The half the comparison above cannot see. Two builds over ONE journal are
    # identical whether the date is taken from the first observation or the
    # newest, so the failure the docstring names -- a mark that returns after
    # every sweep, because bounty.py appends a vendor_status on every run --
    # passed this test. Measured from the journal instead: where a status was
    # observed more than once, the page must be showing the EARLIEST.
    from qa.state import read_events

    observations: dict[tuple, list[str]] = {}
    for ev in read_events():
        if ev.get("type") != "vendor_status":
            continue
        when = ev.get("observed_at") or ev.get("at")
        if when:
            observations.setdefault(
                (ev.get("report_id"), ev.get("status")), []).append(when)
    repeated = {k: v for k, v in observations.items() if len(set(v)) > 1}
    assert repeated, (
        "no status in the journal was observed at two different times, so "
        "'dated from the first observation, not the newest' is untested here "
        "-- this control is vacuous until bounty.py has polled twice"
    )
    latest = {report_id: max(times)
              for (report_id, _), times in repeated.items()}
    dated_from_the_newest = sorted(
        k for k, when in a.items()
        if k[1] in latest and when == latest[k[1]] and when != min(
            t for (rid, _), times in repeated.items() if rid == k[1] for t in times)
    )
    assert not dated_from_the_newest, (
        f"{len(dated_from_the_newest)} repl(ies) are dated from the newest "
        f"observation of their status rather than the first, so the unread "
        f"mark returns after every sweep: {dated_from_the_newest}"
    )


# The stubs the page needs to run outside a browser. Deliberately dumb: every
# element records what was written into it and answers nothing back, because
# the question is whether the script REACHES the end, not whether the DOM is
# faithful. A stub that returned live nodes would be a second implementation
# of the page, and the second copy of a fact is the defect this repo keeps
# finding.
HARNESS = """
const captured = {};
const nodes = {};
// The ORDER the page re-appends its rows in. `sortRows()` sorts the nodes and
// re-appends them, so this is where the effective sort becomes visible -- and
// until 2026-09-12 `appendChild` was a no-op, so the page's opening order was
// pinned by a string in the source instead. Three readers each inserted a line
// that flipped the default to damage while leaving that string untouched, and
// the guard stayed green (B10). It records the dataset rather than the node
// so it survives JSON.
const appended = {};
function appendedTo(id) { return (appended[id] = appended[id] || []); }
function node(id) {
  if (nodes[id]) return nodes[id];
  const el = {
    id: id, dataset: {}, hidden: false, open: false, className: "",
    textContent: "",
    get innerHTML() { return captured[id] || ""; },
    set innerHTML(v) { captured[id] = String(v); },
    addEventListener() {}, insertAdjacentHTML() {}, setAttribute() {},
    appendChild(child) { appendedTo(id).push((child && child.dataset) || {}); },
    scrollIntoView() {}, closest() { return null; },
    querySelector() { return null; },
    // Rows PARSED OUT OF THE HTML THIS ELEMENT WAS GIVEN, not invented. This
    // returned [] until 2026-09-10, so the sort comparator and changedSince
    // never ran over a single row: typing `dataset.changedAt` or the
    // `data-changed-at` attribute left the page exiting 0 with every row
    // reading as unchanged, and the test whose docstring says it catches
    // "a typo in either" stayed green. Three readers reproduced it.
    //
    // Reading the captured markup is not a second implementation of the page
    // -- it is the page's own output, which is the only thing that makes this
    // faithful.
    querySelectorAll(sel) { return rowsOf(captured[id] || "", sel); },
  };
  nodes[id] = el;
  return el;
}

function rowsOf(html, sel) {
  const cls = String(sel || "").replace(/^\\./, "");
  if (!cls) return [];
  const out = [];
  const open = new RegExp('<[a-z]+([^>]*class="[^"]*\\\\b' + cls + '\\\\b[^"]*"[^>]*)>', "gi");
  let m;
  while ((m = open.exec(html)) !== null) {
    const attrs = m[1];
    const dataset = {};
    const attr = /data-([a-z0-9-]+)="([^"]*)"/gi;
    let a;
    while ((a = attr.exec(attrs)) !== null) {
      // The browser's own camelCase mapping: data-changed-at -> changedAt.
      dataset[a[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = a[2];
    }
    out.push({ dataset, hidden: false, className: cls,
               querySelector() { return null; },
               setAttribute() {}, appendChild() {} });
  }
  return out;
}
globalThis.document = {
  getElementById: node,
  createElement: () => node("created-" + Math.random()),
  querySelectorAll: () => [],
  addEventListener() {},
};
globalThis.localStorage = {
  store: {},
  getItem(k) { return k in this.store ? this.store[k] : null; },
  setItem(k, v) { this.store[k] = String(v); },
};
globalThis.location = { hostname: "test-harness", host: "test-harness" };
globalThis.window = { addEventListener() {}, scrollY: 0, scrollTo() {} };
process.on("exit", () => {
  // A file, not stdout: on Linux a pipe is written asynchronously and whatever
  // is still queued when the process exits is dropped, so a page that captures
  // more than the 64 kB pipe buffer arrived cut off mid-string (2026-09-29).
  require("fs").writeFileSync("captured.json",
    JSON.stringify(Object.assign({}, captured, {"__appended__": appended})));
});
"""


class _Captured(dict):
    """id -> the HTML the page wrote, with the append ORDER on the side."""

    appended: dict = {}


def _run_page(node, workdir, payload, after: str = "", page=None):
    """Execute the page's own script over `payload`.

    Returns (returncode, stderr, captured), where `captured` maps element id
    to the HTML the page wrote into it. `after` runs once the page has loaded,
    so a test can call what the page exposes on `window` -- the Nexus rooms
    arrive by fetch, which the harness never makes. `page` is the module whose
    TEMPLATE runs: the console by default, `_lab_page()` for /lab.
    """
    import subprocess

    workdir.mkdir(parents=True, exist_ok=True)
    html = (page or _render()).TEMPLATE
    opening = "<script>\n"
    start = html.index(opening, html.index('id="data"'))
    script = html[start + len(opening):html.rindex("</script>")]
    script = script.replace("__DIGEST__", "0" * 64)

    (workdir / "harness.js").write_text(
        HARNESS + '\ndocument.getElementById("data").textContent = '
        + json.dumps(json.dumps(payload)) + ";\n", encoding="utf-8")
    (workdir / "page.js").write_text(script, encoding="utf-8")
    (workdir / "run.js").write_text(
        'require("./harness.js");\nrequire("./page.js");\n' + after + "\n",
        encoding="utf-8")

    (workdir / "captured.json").unlink(missing_ok=True)   # never read a previous run's

    # encoding is named: the page carries the vendor's own text, and this
    # machine's console codepage is cp1250, which cannot decode it.
    result = subprocess.run([node, str(workdir / "run.js")], capture_output=True,
                            text=True, encoding="utf-8", errors="replace",
                            timeout=60, cwd=str(workdir))
    written = workdir / "captured.json"
    raw = json.loads(written.read_text(encoding="utf-8")) if written.exists() else {}
    # The append order rides out of the page beside the markup, but NOT inside
    # the same mapping: `captured` is id -> HTML and two tests join its values
    # into one string. So it comes back as an attribute.
    captured = _Captured(
        (key, value) for key, value in raw.items() if key != "__appended__")
    captured.appended = raw.get("__appended__") or {}
    return result.returncode, result.stderr, captured


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_runs_end_to_end_and_not_only_parses(tmp_path, monkeypatch):
    """Parsing is not running, and two marks on the page had never been run.

    `finding()` calls the formatter on `f.last_checked_at` and `f.stale_from`,
    which are ISO strings, and the function in scope there was the hoisted
    `when(ms)` -- the bell's relative-age formatter, which expects epoch
    milliseconds. `Date.now() - "2026-09-09T22:13:39+00:00"` is NaN, so every
    comparison in it is false and all three relative branches are unreachable;
    it falls through to `new Date(ms).toISOString().slice(0, 10)`, which does
    parse an ISO string, and the chip printed a bare date where the moment was
    meant. Not a crash -- this test was written expecting one and the run said
    otherwise -- but two marks whose only job is to say WHEN, printing less
    than they were given.

    They had never been drawn at all: `not_checked_in` is set by a NARROW
    sweep and `stale_from` by a failed read of their tracker, and every
    committed row has both null. `test_the_pages_javascript_parses` cannot see
    either: `node --check` parses without executing, and both identifiers
    resolve. So this one runs the page -- over the payload it renders today,
    and over the payload the next `qa-sweep` produces.
    """
    import shutil

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    if not (REPO / "state" / "ledger.json").exists():
        pytest.skip("no committed ledger, so there is no page to run")

    # Against the real payload, for the reason
    # test_the_page_reads_no_field_the_payload_stops_writing gives: a row this
    # test shaped by hand would only ever check the page against the test's
    # idea of a row. Composing reads; nothing here writes.
    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    live = _live_payload(render)

    code, err, captured = _run_page(node, tmp_path / "now", live)
    assert code == 0, f"the page throws on today's payload:\n{err[:900]}"
    assert captured.get("findings"), "the page wrote no findings"

    # The sweep that has never run while the console was up: a narrower
    # selector leaves rows it did not adjudicate, and the fold marks them.
    narrow = json.loads(json.dumps(live))
    assert narrow["findings"], "no rows, so this test would prove nothing"
    for row in narrow["findings"]:
        row["not_checked_in"] = "run-20260910T045212Z-de93be7"
        row["last_checked_at"] = "2026-09-09T22:13:39+00:00"
        # A different moment from last_checked_at, so each mark has to print
        # its own: with one timestamp for both, one mark covered for the
        # other and `stale_from` printing a bare date stayed green (P04, deep
        # pass of 2026-09-11).
        row["stale_from"] = "2026-09-08T11:05:02+00:00"

    code, err, captured = _run_page(node, tmp_path / "narrow", narrow)
    assert code == 0, (
        "the page throws on a payload from a narrow sweep, which is the "
        "ordinary sweep -- and a throw at the top level of the page's only "
        f"script would render nothing at all:\n{err[:900]}"
    )
    body = captured.get("findings", "")
    assert "not re-checked" in body, (
        "the mark saying a row was not re-checked never reached the page"
    )
    assert "their side unread" in body
    assert "2026-09-09 22:13" in body, (
        "the moment beside those marks is printed plainly; a relative age is "
        "what the wrong `when` was reaching for"
    )
    assert "2026-09-08 11:05" in body, (
        "the stale mark does not print its own moment plainly -- it was only "
        "ever covered by the not-re-checked mark's timestamp (P04)")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_row_says_when_it_last_changed(tmp_path, monkeypatch):
    """The operator ran a sweep, six rows closed, and the page could not say so.

    Their words, 2026-09-10: *"mame open issues nejake a pak dam sweep a ty
    plno veci opravis a ony zmiznou z toho tabu protoze se uzavrely a ja nevim
    co se deje... neni tam zaden cas zmeny posledni videt, nebo to nejde nijak
    sesortovat podle casu"*. The ledger has the answer on every row and had
    never projected it: `transitions[]` carries `at` for both axes, and the
    payload carried neither that nor `first_seen.at`.

    Both axes count. A row that closed because THEY answered moved on the
    filing axis and never touched the check axis, and it disappears from the
    open filter exactly as loudly as one our own run closed.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    moved = _row("CYM-moved", check_state="PASSING", filing_state="FIX_CLAIMED")
    moved["first_seen"] = {"at": "2026-09-04T10:00:00+00:00",
                           "cause": {"run_id": "run-a"}}
    moved["transitions"] = [
        {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
         "cause": {"run_id": "run-b"}, "at": "2026-09-08T09:00:00+00:00"},
        {"axis": "filing", "from": "REPLIED", "to": "FIX_CLAIMED",
         "cause": {"event_id": "e1"}, "at": "2026-09-09T22:13:39+00:00"},
    ]
    quiet = _row("CYM-quiet", check_state="UNVERIFIED")
    quiet["first_seen"] = {"at": "2026-09-05T08:30:00+00:00",
                           "cause": {"run_id": "run-a"}}
    quiet["transitions"] = []

    rows = {f["id"]: f for f in render.build_payload(
        ledger=_ledger(moved, quiet))["findings"]}

    assert rows["CYM-moved"]["last_change"] == {
        "at": "2026-09-09T22:13:39+00:00", "axis": "filing",
        "from": "REPLIED", "to": "FIX_CLAIMED",
    }, "the newest transition wins, whichever axis it is on"
    assert rows["CYM-moved"]["first_seen_at"] == "2026-09-04T10:00:00+00:00"

    # A row nothing has moved still has a date: the day it was first seen.
    # Sorting by change puts it where it belongs rather than at the top with
    # an empty cell, which is what a null would do.
    assert rows["CYM-quiet"]["last_change"] == {
        "at": "2026-09-05T08:30:00+00:00", "axis": None,
        "from": None, "to": None,
    }
    assert rows["CYM-quiet"]["first_seen_at"] == "2026-09-05T08:30:00+00:00"

    # Every committed row, so a shape the fold can produce cannot slip past a
    # synthetic pair.
    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    committed = _committed_payload(render)["findings"]
    assert committed, "no committed rows, so the rest of this proves nothing"
    for row in committed:
        change = row["last_change"]
        assert change and change.get("at"), (
            f"{row['id']} cannot say when it last changed"
        )
        assert change["axis"] in ("check", "filing", None)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_opens_on_what_moved_and_says_it_in_one_line(tmp_path, monkeypatch):
    """Two of the operator's eight complaints, and they are the same complaint.

    *"co to tu je nahore jako za statistiky, to nikdy nectu a je to hnus"* --
    seven labelled figures across the masthead, none of which anyone had ever
    used. And the Findings intro, three lines of prose above the list. Both
    were written for a reader; there is none. What is left in the header is
    what the page cannot be read without: which run, at what level, standing
    on which journal event. The rest moved into the tooltip, where it costs
    nothing until somebody wants it.

    The other half is the sweep problem. `changed since read` reuses the
    watermark the bell already keeps (`qa.seenAt`), so the rows a sweep just
    closed stay reachable in one click until the operator marks them read --
    and the list is sorted by when each row last moved, newest first.

    One read switch, not two: the bell's "Mark all as read" and this chip both
    call the same `markRead`, or the two would drift and the page would hold
    two ideas of what "since you last looked" means.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()
    template = render.TEMPLATE

    assert "Everything found so far" not in template, (
        "the Findings intro is prose above a list nobody reads"
    )
    assert 'class="sub"' not in template, "the masthead blurb is still there"
    for gone in ("documented paths", "MCP tools anon / trusted",
                 "messages sent / received"):
        assert f'["{gone}"' not in template, (
            f"{gone!r} is still a labelled figure in the header rather than "
            "a line in the tooltip"
        )

    # The three chips, the switch and the sort, by the attributes the click
    # handler dispatches on -- not by their labels, which are copy.
    for kind in ('data-kind="open"', 'data-kind="changed"', 'data-kind="all"'):
        assert kind in template, f"the {kind} chip is missing"
    # ONE read switch, counted as CALL SITES rather than as occurrences of the
    # string. `template.count("markRead()") >= 2` was satisfied by the function
    # DEFINITION plus one call, so giving the chip its own `markChangedRead()`
    # with a second watermark left the check green while the bell and the chip
    # held two ideas of "since you last looked" -- which is the exact drift
    # this test's own docstring says it exists to prevent. Three readers each
    # reproduced it by making that split. Found 2026-09-10.
    assert "function markRead" in template
    watermarks = set(re.findall(r"""(?:localStorage|qa)[.\[]\s*['"]?(seenAt|\w*[sS]eenAt)""",
                                template))
    assert watermarks <= {"seenAt"}, (
        f"the page keeps more than one 'since you last looked' watermark "
        f"({sorted(watermarks)}), so the bell and the chip can disagree")
    call_sites = len(re.findall(r"(?<!function )\bmarkRead\(\)", template))
    assert call_sites >= 2, (
        f"the bell and the chip must CALL the same read switch; found "
        f"{call_sites} call site(s) beside its definition")
    assert 'data-sort="changed"' in template and 'data-sort="damage"' in template
    # The DEFAULT, which is the claim: the page opens sorted by what moved.
    # Only the two buttons were asserted, so a "damage" default stayed green
    # (P08, deep pass of 2026-09-11).
    assert 'readStore("qa.sort", "changed")' in template, (
        "the page no longer opens sorted by when each row last moved")

    # And the order the page actually opens in, which is the claim. The line
    # above pins a string, and a string is not an order: all three readers of
    # 2026-09-12 added `if (!seen) sortBy = "damage";` a few lines below the
    # declaration, left that literal untouched, and watched the page open on
    # damage with this green (B10, triage 3/3). `sortRows()` re-appends the
    # nodes it sorted, so the harness records that order and it is read here.
    import shutil

    node = shutil.which("node")
    if node:
        # Two rows whose two orders DISAGREE: the one that moved today is the
        # least damaging. Newest-movement-first opens on the S4; damage-first
        # opens on the S0. Built here rather than borrowed from the live
        # payload, which this test's own monkeypatched QA_STATE_DIR empties.
        def moved(fid, severity, at):
            return _row(fid, severity=severity, transitions=[
                {"at": at, "axis": "check", "from": "UNVERIFIED",
                 "to": "REPRODUCING", "cause": {"run_id": "run-x"}}])

        payload = render.build_payload(ledger=_ledger(
            moved("cosmetic-today", "S4-COSMETIC", "2026-09-12T18:00:00+00:00"),
            moved("custody-old", "S0-CUSTODY", "2026-09-01T08:00:00+00:00")))
        code, err, captured = _run_page(node, tmp_path / "sortorder", payload)
        assert code == 0, f"the page throws:\n{err[:600]}"
        order = [row.get("sev") for row in captured.appended.get("findings", [])]
        assert order == ["S4-COSMETIC", "S0-CUSTODY"], (
            f"the page opened in {order}; the S4 row moved today and the S0 "
            f"row moved eleven days ago, so newest-movement-first puts S4 on "
            f"top and this opened in damage order instead")

    # The header still says the two things the guards pin, and the run's own
    # moment is now in the payload rather than the render's clock.
    assert "D.events_head" in template and "state as of" in render.render(
        _live_payload_or_empty(render))
    assert "D.run_at" in template


def _live_payload_or_empty(render):
    try:
        return _live_payload(render)
    except Exception:  # noqa: BLE001 -- a state dir with no journal is fine here
        return render.build_payload(ledger=_ledger())


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_runs_with_the_new_filters(tmp_path, monkeypatch):
    """The filters are JavaScript, so the guard for them has to execute.

    Sorting re-appends nodes and the chips read `data-changed-at`; a typo in
    either is invisible to every assertion about the template's text, and the
    last time something in this script threw at the top level the whole page
    rendered blank below the masthead.
    """
    import shutil

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    if not (REPO / "state" / "ledger.json").exists():
        pytest.skip("no committed ledger, so there is no page to run")

    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    code, err, captured = _run_page(node, tmp_path / "filters",
                                    _live_payload(render))
    assert code == 0, f"the page throws with the new filters:\n{err[:900]}"
    filters = captured.get("filters", "")
    for kind in ("open", "changed", "all"):
        assert f'data-kind="{kind}"' in filters, (
            f"the {kind} chip never reached the page"
        )
    assert "mark read" in filters.lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_component_lands_on_a_tile_or_is_declared_a_self_test():
    """A tile said "2 tests written" while 460 of 525 results counted nowhere.

    `COMPONENT_TO_SECTION` is a hand-written map and components.yaml is the
    registry every `@qa(component=)` is validated against at collection time,
    so the two drift in one direction only: a component is added, tests are
    written under it, and the map does not hear about it. Eight of the
    twenty-six were unmapped -- among them `rest.event_cards` with seven
    checks and `discovery.onboarding` with four -- and every result they
    produced fell into a bucket no tile carries.

    Both halves are asserted, because the other drift is a section id that was
    renamed under a mapping still pointing at the old one.
    """
    import yaml

    render = _render()
    registry = yaml.safe_load(
        (REPO / "components.yaml").read_text(encoding="utf-8"))["components"]
    # From inventory.py, not from state/inventory.json: the snapshot is
    # whatever the last inventory run wrote, and the committed one was six
    # days old and missing a section the code has declared since. A guard that
    # reads the snapshot fails when the snapshot is stale and passes when the
    # map is wrong, which is backwards.
    inventory_mod = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location(
            "inventory_sections", REPO / "scripts" / "inventory.py"))
    inventory_mod.__loader__.exec_module(inventory_mod)
    section_ids = {s["id"] for s in inventory_mod.SECTIONS} | {"_meta"}

    unmapped = sorted(c for c in registry
                      if c not in render.COMPONENT_TO_SECTION)
    assert not unmapped, (
        "components.yaml declares these and the page has nowhere to put "
        f"their results, so the tiles undercount: {unmapped}"
    )
    stray = sorted({c: s for c, s in render.COMPONENT_TO_SECTION.items()
                    if s not in section_ids}.items())
    assert not stray, (
        f"these map to a section the inventory does not have: {stray}"
    )
    assert all(render.COMPONENT_TO_SECTION[c] == "_meta"
               for c in registry if c.startswith("meta.")), (
        "our own self-tests belong to no part of their platform"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tile_lists_the_tests_behind_its_count(tmp_path, monkeypatch):
    """*"chci si to rozkliknout a videt ktere testy to jsou"* -- and one line
    each saying what they check.

    The count was the only thing a tile said about its checks: a number with
    nothing behind it. The names come from the run, and the sentence from the
    check's own docstring, so neither can be typed in and drift. A
    parametrised reconciliation case has no docstring of its own -- it is one
    function over five claims -- so it borrows the claim's `question`, which
    is the sentence that claim exists to ask.

    Self-tests are excluded from the tiles: they measure us, not them, and
    448 of them on a platform tile is the loudest possible wrong number.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    run = {
        "run_id": "run-20260910T000000Z-abc1234",
        "results": [
            {"nodeid": "tests/rest/test_support.py::test_a", "role": "verdict",
             "component": "rest.support", "outcome": "passed",
             "measurement": {"reason": "the desk answers"}},
            {"nodeid": "tests/rest/test_support.py::test_b", "role": "verdict",
             "component": "rest.support", "outcome": "failed",
             "measurement": {"reason": "it does not"}},
            {"nodeid": "tests/mcp/test_trust_ladder.py::test_c", "role": "verdict",
             "component": "mcp.trust_ladder", "outcome": "passed",
             "measurement": {}},
            {"nodeid": "tests/meta/test_pipeline_render.py::test_d",
             "role": "verdict", "component": "meta.pipeline",
             "outcome": "passed", "measurement": {}},
            # A self-test wearing a PLATFORM component. The only self-test in
            # this fixture used to be meta.pipeline, which `_tests_by_section`
            # drops one line later at `section == "_meta"` -- so removing the
            # SELF_TEST_DIRS filter entirely left this test green and the
            # exclusion it names guarded by the other branch. Three readers
            # reproduced that deletion. This row can only be excluded by the
            # directory filter, which is the thing under test.
            {"nodeid": "tests/meta/test_guard_is_real.py::test_e",
             "role": "verdict", "component": "rest.support",
             "outcome": "passed", "measurement": {}},
            {"nodeid": "tests/repo/test_repo_consistency.py::test_f",
             "role": "verdict", "component": "rest.support",
             "outcome": "passed", "measurement": {}},
        ],
    }
    inventory = {"totals": {}, "sections": [
        {"id": "support", "title": "Support desk", "blurb": "", "blast": "",
         "verdicts": {}, "reachable_pct": None, "endpoint_detail": []},
        {"id": "identity_trust", "title": "Identity and trust", "blurb": "",
         "blast": "", "verdicts": {}, "reachable_pct": None,
         "endpoint_detail": []},
    ]}
    sections = {s["id"]: s for s in render.build_payload(
        ledger=_ledger(), inventory=inventory, run=run)["sections"]}

    support = sections["support"]
    assert [t["nodeid"] for t in support["tests"]] == [
        "tests/rest/test_support.py::test_a",
        "tests/rest/test_support.py::test_b",
    ]
    assert support["checks"]["total"] == len(support["tests"]), (
        "the count and the list must be the same fact, or the tile is back "
        "to a number nobody can open"
    )
    assert support["checks"]["failed"] == 1
    assert {t["outcome"] for t in support["tests"]} == {"passed", "failed"}

    for section in sections.values():
        for test in section["tests"]:
            assert not test["nodeid"].startswith(("tests/meta/", "tests/repo/")), (
                "a self-test reached a tile about their platform"
            )

    # 2026-09-25: after a narrow sweep the page's run holds a handful of
    # checks, and the tiles read "untested" on 27 of 28 areas while the full
    # suite had run the night before. A check the page's run did not include
    # is shown from the last full run, marked with when -- never dropped, and
    # never counted twice when both ran it.
    earlier = {"run_id": "run-20260909T220000Z-full", "finished_at": "2026-09-09T22:05:00+00:00",
               "results": [
                   {"nodeid": "tests/rest/test_support.py::test_a", "role": "verdict",
                    "component": "rest.support", "outcome": "failed", "measurement": {}},
                   {"nodeid": "tests/rest/test_support.py::test_z", "role": "verdict",
                    "component": "rest.support", "outcome": "passed", "measurement": {}},
                   {"nodeid": "tests/meta/test_guard_is_real.py::test_e", "role": "verdict",
                    "component": "rest.support", "outcome": "passed", "measurement": {}}]}
    both = {s["id"]: s for s in render.build_payload(
        ledger=_ledger(), inventory=inventory, run=run, earlier_run=earlier)["sections"]}
    tests = {t["nodeid"]: t for t in both["support"]["tests"]}
    assert set(tests) == {"tests/rest/test_support.py::test_a",
                          "tests/rest/test_support.py::test_b",
                          "tests/rest/test_support.py::test_z"}, tests
    assert tests["tests/rest/test_support.py::test_a"]["outcome"] == "passed", (
        "the page's own run wins over the older one")
    assert not tests["tests/rest/test_support.py::test_a"].get("stale_at")
    assert tests["tests/rest/test_support.py::test_z"]["stale_at"] == "2026-09-09T22:05:00+00:00"
    assert both["support"]["checks"]["total"] == 3

    # Every check on a tile can say in one sentence what it looks at.
    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    live = _committed_payload(render)
    assert sum(len(s["tests"]) for s in live["sections"]), (
        "no check reached any tile, so the rest of this proves nothing"
    )
    described, silent = 0, []
    for section in live["sections"]:
        for test in section["tests"]:
            if test.get("gone"):
                continue  # retired since that run; the tile says so
            if test.get("doc"):
                described += 1
            else:
                silent.append(test["nodeid"])
    assert described, "no check on any tile says what it checks"
    assert not silent, (
        f"{len(silent)} check(s) on a tile cannot say what they look at; the "
        f"first line of the function's docstring is where that comes "
        f"from: {silent[:5]}"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_last_full_run_backfill_stays_off_the_committed_page(tmp_path, monkeypatch):
    """tests/repo/test_diaries_outside_git.py::D2 caught this on 2026-09-28:
    a narrow sweep's committed dashboard differed from a bare-checkout
    re-render, because `_last_full_run` filled stale tiles from a
    `state/runs/*.json` record that was admissible but had never been
    force-added to git (its prereg had drifted, so no fold ever cited it --
    an admissible run and a committed one are not the same set).

    `build_payload()`'s default must not touch that file at all: the
    backfill only runs when a caller opts in with `use_last_full_run=True`,
    which is what scripts/serve.py's live view does and scripts/render.py's
    committed-page __main__ does not.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    (tmp_path / "runs").mkdir()
    old_full = {
        "schema": 2, "run_id": "run-20260101T000000Z-old0000",
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:05:00+00:00",
        "git_head": "abc123", "git_dirty": False,
        "prereg_id": "PRE-0001", "prereg_tag_sha": "t", "prereg_commit": "abc123",
        "platform_fingerprint": "sha256:f", "fingerprint_drifted": False,
        "selector_full": True,
        "collected": ["tests/rest/test_support.py::test_old_full_run"],
        "exit_status": 0,
        "results": [{"nodeid": "tests/rest/test_support.py::test_old_full_run",
                     "role": "verdict", "component": "rest.support",
                     "outcome": "passed", "measurement": {}}],
        "record_integrity": {"consistent": True},
    }
    (tmp_path / "runs" / "run-20260101T000000Z-old0000.json").write_text(
        json.dumps(old_full), encoding="utf-8")

    render = _render()
    narrow_run = {"run_id": "run-20260910T000000Z-abc1234", "results": []}
    inventory = {"totals": {}, "sections": [
        {"id": "support", "title": "Support desk", "blurb": "", "blast": "",
         "verdicts": {}, "reachable_pct": None, "endpoint_detail": []},
    ]}

    committed = {s["id"]: s for s in render.build_payload(
        ledger=_ledger(), inventory=inventory, run=narrow_run)["sections"]}
    assert "test_old_full_run" not in {
        n.rsplit("::", 1)[-1] for n in
        {t["nodeid"] for t in committed["support"]["tests"]}
    }, "the default payload read a run record git never committed"

    live = {s["id"]: s for s in render.build_payload(
        ledger=_ledger(), inventory=inventory, run=narrow_run,
        use_last_full_run=True)["sections"]}
    assert "tests/rest/test_support.py::test_old_full_run" in {
        t["nodeid"] for t in live["support"]["tests"]
    }, "use_last_full_run=True must still reach the local record -- serve.py needs it"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stats_are_derived_and_a_re_pin_is_not_a_fix(tmp_path, monkeypatch):
    """Five figures the operator asked for, and one judgement inside them.

    *"kolik jsme opravili bugu, kolik mame testu napsanych, kolik jsme
    vydelali odmen uz, pak porovnani A2A komunikace vs. telegram"*.

    The judgement is which transition counts as a fix. `REPRODUCING ->
    PASSING` is something that was broken and now is not. `CHECK_CHANGED ->
    PASSING` is a definition we re-pinned by hand -- there are 41 of those
    against 18 real ones, six of them written this morning -- and counting
    them would treble the headline with our own bookkeeping. That is the exact
    shape of defect this repository keeps finding in itself, so it is asserted
    rather than commented.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    fixed = _row("CYM-fixed", check_state="PASSING", filing_state="FIX_CLAIMED")
    fixed["transitions"] = [
        {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
         "cause": {"run_id": "run-a"}, "at": "2026-09-08T09:00:00+00:00"},
    ]
    fixed["filing"]["verifications"] = [
        {"report_id": 1, "verdict": "pass", "at": "2026-09-08T10:00:00+00:00"},
        {"report_id": 1, "verdict": "fail", "at": "2026-09-08T11:00:00+00:00"},
    ]
    repinned = _row("CYM-repinned", check_state="PASSING",
                    filing_state="FIX_CLAIMED")
    repinned["transitions"] = [
        {"axis": "check", "from": "CHECK_CHANGED", "to": "PASSING",
         "cause": {"run_id": "run-b"}, "at": "2026-09-10T04:56:30+00:00"},
    ]

    stats = render.build_payload(ledger=_ledger(fixed, repinned))["stats"]

    assert stats["fixes"]["verified_by_us"] == 1, (
        "a definition we re-pinned was counted as a defect they repaired"
    )
    assert stats["fixes"]["by_day"] == [{"day": "2026-09-08", "n": 1}]

    # A bug that regressed and was fixed AGAIN is one bug. The headline summed
    # transitions, so the live ledger's 19 REPRODUCING->PASSING moves across 16
    # findings printed 19 under a heading the operator reads as a count of
    # bugs. The fold has a `reopen` obligation precisely because a row can go
    # back and forth, so this is the ordinary case. Found by review 2026-09-10,
    # confirmed 3/3.
    regressed = _row("CYM-regressed", check_state="PASSING",
                     filing_state="FIX_CLAIMED")
    regressed["transitions"] = [
        {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
         "cause": {"run_id": "run-c"}, "at": "2026-09-08T12:00:00+00:00"},
        {"axis": "check", "from": "PASSING", "to": "REPRODUCING",
         "cause": {"run_id": "run-d"}, "at": "2026-09-09T09:00:00+00:00"},
        {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
         "cause": {"run_id": "run-e"}, "at": "2026-09-09T18:00:00+00:00"},
    ]
    twice = render.build_payload(ledger=_ledger(fixed, repinned, regressed))["stats"]
    assert twice["fixes"]["verified_by_us"] == 2, (
        f"one bug fixed, broken and fixed again is one bug: "
        f"{twice['fixes']}")
    assert twice["fixes"]["re_fixed"] == 1, (
        f"and the second repair is not thrown away -- it is named apart, so "
        f"the headline can be small and honest without hiding it: "
        f"{twice['fixes']}")
    # The daily series still counts each event, because a repair IS a thing
    # that happened on a day.
    assert sum(d["n"] for d in twice["fixes"]["by_day"]) == 3
    assert stats["fixes"]["told_them"] == 1, "only a pass verdict was told to them"

    # Counted off the files, not recalled: every number quoted for this has
    # come from a different command.
    assert stats["tests"]["vendor_facing"] > 0
    assert stats["tests"]["self_tests"] > stats["tests"]["vendor_facing"]
    assert sum(d["n"] for d in stats["tests"]["by_dir"]) == (
        stats["tests"]["vendor_facing"] + stats["tests"]["self_tests"])

    # And the channel block is the one reader's own answer, not a second copy
    # of the arithmetic.
    from qa.state import read_events

    assert stats["channels"] == __import__(
        "qa.channels", fromlist=["compare"]).compare(read_events())


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rewards_come_from_their_tracker(tmp_path, monkeypatch):
    """35,000 ET10 is their figure, and ours must agree with it or say why."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    (tmp_path / "bounty.json").write_text(json.dumps({
        "our_reports": {"reports": [
            {"id": 1, "status": "paid", "reward_amount": 1000.0,
             "fixed_at": "2026-09-08T14:25:31"},
            {"id": 2, "status": "paid", "reward_amount": 1000.0,
             "fixed_at": "2026-09-08T15:25:31"},
            {"id": 3, "status": "fixed", "reward_amount": 0.0,
             "fixed_at": "2026-09-09T10:00:00"},
            {"id": 4, "status": "invalid", "reward_amount": 0.0,
             "created_at": "2026-09-05T10:00:00"},
        ]},
        "leaderboard": [{"reward_currency": "ET10", "total_paid": 2000.0}],
        "creator_rewards": {"klass": "ok", "read_at": "2026-09-25T20:00:00+00:00",
                            "stale_from": None,
                            "summary": {"paid": 7, "pending": 1, "et10": 7000,
                                        "etlp": 7000}},
    }), encoding="utf-8")
    render = _render()

    rewards = render.build_payload(ledger=_ledger())["stats"]["rewards"]
    assert rewards["paid_n"] == 2
    # The operator, 2026-09-25: "at to jde rozpoznat co je z bugu a co z
    # tweetu" -- bug rewards and post rewards side by side, never summed into
    # one figure that hides which is which.
    assert rewards["paid_total"] == 2000, "post rewards leaked into the bug total"
    # No read time in the payload: every quiet poll rewrote it and made the
    # page stale against its inputs (deep pass 2026-09-25, R01). Only a
    # failed read's moment is shown.
    assert rewards["posts"] == {"paid_n": 7, "pending_n": 1, "et10": 7000,
                                "etlp": 7000, "stale_from": None}
    for field in ("posts.et10", "posts.etlp", "posts.paid_n", "posts.pending_n",
                  "posts.stale_from"):
        assert field in render.TEMPLATE, f"the page never shows {field}"
    assert rewards["pending_n"] == 1, "a fixed report is owed a reward"
    assert rewards["invalid_n"] == 1
    assert rewards["currency"] == "ET10"
    assert rewards["by_day"] == [{"day": "2026-09-08", "amount": 2000}]

    # "or say why" -- the half this test named and never checked. Their figure
    # sat in the same fixture and only `reward_currency` was ever read from it,
    # so setting total_paid to anything at all left the check green. A
    # my-reports read windowed to 20 of 44 would have printed 20,000 beside
    # their 37,000 with nothing failing: the report-#52 shape. Found by a
    # check-auditor 2026-09-10, confirmed 3/3.
    assert rewards["their_total"] == 2000.0
    assert rewards["disagrees"] is False, rewards

    def rebuild(**over):
        blob = json.loads((tmp_path / "bounty.json").read_text(encoding="utf-8"))
        for key, value in over.items():
            if key == "total_paid":
                blob["leaderboard"][0]["total_paid"] = value
            else:
                blob["our_reports"][key] = value
        (tmp_path / "bounty.json").write_text(json.dumps(blob), encoding="utf-8")
        return _render().build_payload(ledger=_ledger())["stats"]["rewards"]

    disagreeing = rebuild(total_paid=37000.0)
    assert disagreeing["disagrees"] is True, (
        f"their figure is 37000 and ours 2000, and the page says nothing: "
        f"{disagreeing}")
    assert disagreeing["their_total"] == 37000.0

    # And the other half of a windowed read: they hold more rows than we read.
    windowed = rebuild(total_paid=2000.0, total=44)
    assert windowed["rows_read"] == 4 and windowed["rows_they_hold"] == 44
    assert windowed["disagrees"] is True, (
        f"we counted 4 of the 44 reports they hold and the totals happened to "
        f"match anyway: {windowed}")

    # A tracker that publishes no figure is not a disagreement. Rule 8's shape:
    # absent is not zero.
    silent = rebuild(total_paid=None, total=4)
    assert silent["their_total"] is None and silent["disagrees"] is False, silent


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stats_panel_draws_without_throwing(tmp_path, monkeypatch):
    """The panel is JavaScript over a payload that can be empty in five ways.

    Every block has to survive a missing key: a fresh state directory has no
    bounty.json, git may be absent so the deep-pass table is empty, and a
    channel with no answered question has a null median. A throw here is not a
    blank panel -- it is a blank PAGE, because this runs at the top level of
    the page's only script.
    """
    import shutil

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    if not (REPO / "state" / "ledger.json").exists():
        pytest.skip("no committed ledger, so there is no page to run")

    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    payload = _committed_payload(render)

    code, err, captured = _run_page(node, tmp_path / "stats", payload)
    assert code == 0, f"the stats panel throws:\n{err[:900]}"
    panel = captured.get("stats", "")
    assert "Rewards" in panel and "Defects fixed" in panel
    # Redrawn 2026-09-11 at the operator's word -- only Rewards and Defects
    # fixed said anything at a glance, and they wanted to see how reliable
    # Nexus is beside Telegram, in pictures. The two panels that replaced
    # "Checks written" and the latency table are pinned here instead.
    assert "Can we rely on them" in panel and "What we test" in panel
    assert "Nexus" in panel, "the channel the operator asked about is on the panel"

    empty = json.loads(json.dumps(payload))
    empty["stats"] = {}
    code, err, _ = _run_page(node, tmp_path / "stats-empty", empty)
    assert code == 0, (
        "the page throws when a figure is missing, which blanks everything "
        f"below it:\n{err[:900]}"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_model_table_on_the_page_is_the_one_in_the_operating_rules(
        tmp_path, monkeypatch):
    """The operator sets /model and /effort, and the table lived where they do
    not look.

    Parsed at render time rather than retyped, and this holds the two to each
    other: a row added to CLAUDE.md appears on the page at the next render, and
    a row edited on the page is impossible, because there is no copy to edit.

    The independent parse below is deliberately a different expression from
    the one in render.py. Two implementations of the same read disagree on
    exactly the malformed row that matters.
    """
    import re

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    block = text.split("## What a task needs", 1)[1]
    expected = []
    for line in block.splitlines():
        row = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line.strip())
        if not row:
            if expected:
                break
            continue
        task, needs = (c.replace("`", "").strip() for c in row.groups())
        if task.lower() == "task" or set(task) <= {"-"}:
            continue
        model, _, effort = needs.partition(" · ")
        expected.append({"task": task, "model": model.strip(),
                         "effort": effort.strip()})

    assert expected, "the operating rules' table did not parse; fix the test"
    assert render._help_models() == expected

    # ON THE PAGE, which is what the docstring above claims and what neither
    # side of the comparison touched: both are Python parsers over CLAUDE.md,
    # so deleting the only site that reads `D.help.models` left them agreeing
    # while the page showed nothing. All three readers reproduced that.
    # `test_the_page_renders_every_field_it_is_given` does not cover it either
    # -- it walks per-finding keys, which is the blind spot its sibling names
    # in its own docstring.
    import shutil

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    payload = render.build_payload(ledger=_ledger())
    code, err, captured = _run_page(node, tmp_path / "models", payload)
    assert code == 0, f"the page throws:\n{err[:600]}"
    drawn = " ".join(captured.values())
    for row in expected[:3]:
        assert row["task"][:30] in drawn, (
            f"the model table is in the payload and not on the page: "
            f"{row['task'][:40]!r} never rendered")
        assert row["model"] in drawn

    # And a file without the table is a page that must not pretend.
    empty = tmp_path / "CLAUDE.md"
    empty.write_text("## What a task needs\n\nnothing here\n", encoding="utf-8")
    monkeypatch.setattr(render, "REPO_ROOT", tmp_path)
    with pytest.raises(RuntimeError):
        render._help_models()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_help_panel_is_outside_the_legend_and_speaks_plainly(
        tmp_path, monkeypatch):
    """*"opet takovy uzky tunel nechapu proc to neni sirsi a zas strasne moc
    textu"*.

    The prose was capped at 82 characters wide and ran to two screens. What
    went: the tour of their four documents, and the worked example of a
    percentage. What arrived: a picture of the machine, and the table saying
    what to run me on.

    The picture sits in its own section BEFORE the legend, which keeps the
    legend's scanned slice exactly where it was -- and it is held to the same
    standard anyway, because a diagram that needs the vocabulary is a diagram
    that has not been drawn yet.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()
    template = render.TEMPLATE

    assert 'id="panel-help"' in template
    assert template.index('id="panel-help"') < template.index('id="panel-legend"')
    assert "Where to start on their side" not in template, \
        "the tour of their documents is gone"
    assert "paintPctExample" not in template, "the worked example is gone"
    assert "max-width:82ch" not in template, "the prose is still in a tunnel"

    panel = template[template.index('id="panel-help"'):
                     template.index('id="panel-legend"')]
    for word in ("ledger", "fold", "journal", "admissible", "fingerprint",
                 "nodeid", "adjudicat"):
        assert word not in panel.lower(), (
            f"the diagram explains the machine using the machine's own word "
            f"{word!r}, which is the thing it is there to replace"
        )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_our_own_verifications_appear_in_the_conversation(tmp_path, monkeypatch):
    """The operator read #86 and asked why the last word was theirs.

    It was not. We had sent them a FAIL verification an hour after their
    "Resolved via ticket ET-24493", and the panel did not show it: the thread
    was built from the report we filed and the answer they gave, and a
    verification goes out through a different endpoint entirely -- POST
    /reports/{id}/verification rather than a comment -- so it had no bubble.

    What the operator could see was our own verdict quoted back at them inside
    THEIR bubble, because their status_notes is one growing text field and
    their server appends our verification marker to it. So the page showed our
    correction as a fragment of their message, dated by their first reply. The
    conversation read: we filed, they said fixed. It ended there, on a row
    the same page was calling STILL REPRODUCIBLE.

    The verifications come from `filing.verifications`, which the fold already
    computes, so the panel and the ledger cannot disagree about what was sent.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    render = _render()

    row = _row("CYM-checked", check_state="REPRODUCING", filing_state="FIX_CLAIMED")
    row["filing"]["reports"] = [{"report_id": 86, "status": "fixed"}]
    row["filing"]["verifications"] = [
        {"report_id": 86, "verdict": "pass", "run_id": "run-a",
         "at": "2026-09-10T09:00:00+00:00", "fingerprint": "sha256:aaa"},
        {"report_id": 86, "verdict": "fail", "run_id": "run-b",
         "at": "2026-09-10T13:51:00+00:00", "fingerprint": "sha256:aaa"},
    ]

    thread = {f["id"]: f["thread"]
              for f in render.build_payload(ledger=_ledger(row))["findings"]}["CYM-checked"]

    verdicts = [m for m in thread if m.get("verdict")]
    assert len(verdicts) == 2, (
        f"both verifications we sent must be in the conversation: {thread}"
    )
    assert [m["verdict"] for m in verdicts] == ["pass", "fail"], "in the order sent"
    assert all(m["who"] == "us" for m in verdicts), (
        "a verification is something WE said; it arrives on their side as our "
        "verdict, not as their answer"
    )
    assert all(m["report_id"] == 86 for m in verdicts)
    assert all((m.get("text") or "").strip() for m in verdicts), (
        "an empty bubble is the defect this panel already has a guard for"
    )
    assert "fail" in verdicts[1]["text"].lower() or \
           "still" in verdicts[1]["text"].lower(), (
        f"the bubble has to say which way the verdict went: {verdicts[1]['text']!r}"
    )

    # And the last word on a row we are still reporting as broken is ours.
    assert thread[-1]["who"] == "us"
    assert thread[-1].get("verdict") == "fail"

    # The template has to draw it, or the payload grew a field nobody reads.
    assert "m.verdict" in render.TEMPLATE


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_memecoin_measurement_is_on_the_lab_page_and_the_console_links_there():
    """[operator 2026-09-13] they asked for "separatni sekci jen pro
    memecoiny" and then could not find it.

    It shipped as the fifth and last block of the Stats tab, which is a
    section only in the sense that a paragraph is one -- the same class of
    miss as `look-at-the-page-before-calling-it-done`: every test green, the
    data present, and nobody had checked whether a person could reach it.
    It then had a tab of its own; since V4 of plan v2 it is a section of the
    laboratory's page, /lab, because its figures come from a gitignored diary
    and the committed console may hash only what git holds.

    So "findable" is now two things: the console carries a link to /lab, and
    the lab page has a section, an element to draw into and a writer for it.
    That the writer runs and draws is the node test above.
    """
    console = _render().TEMPLATE
    assert 'href="/lab"' in console, (
        "the console does not link to the laboratory, so the memecoins and the "
        "rooms are reachable only by typing a URL nobody was told")
    assert 'id="memecoins"' not in console, "drawn in the console as well"

    # On /lab the memecoins are one of the sections (2026-09-23, seven since 2026-10-11): in
    # the list of sections lab_view() writes and the tabs are drawn from, and a room of their own.
    page = _lab_page().TEMPLATE
    assert "memecoins" in _lab_page().SECTOR_NAMES, "no Memecoiny room among the sections"
    assert "const SECTORS = (V.sectors || []).map(lp => lp.key);" in page, (
        "the tabs are not drawn from the sections the view writes")
    assert "function memeRoom(" in page and 'SECTOR === "memecoins"' in page, (
        "nothing draws the memecoin room, so it opens empty")
    # The hover bubble is ours: an element to draw into and a handler that
    # follows the cursor. Without both, the graph has no readable labels at
    # all now that the native <title> is gone.
    assert 'id="tip"' in page, "no bubble element"
    assert "mousemove" in page and ".mc-pt" in page, "nothing shows the bubble"
