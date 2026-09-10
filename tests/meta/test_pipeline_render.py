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
function node(id) {
  if (nodes[id]) return nodes[id];
  const el = {
    id: id, dataset: {}, hidden: false, open: false, className: "",
    textContent: "",
    get innerHTML() { return captured[id] || ""; },
    set innerHTML(v) { captured[id] = String(v); },
    addEventListener() {}, insertAdjacentHTML() {}, setAttribute() {},
    appendChild() {}, scrollIntoView() {}, closest() { return null; },
    querySelector() { return null; }, querySelectorAll() { return []; },
  };
  nodes[id] = el;
  return el;
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
  process.stdout.write("CAPTURED-JSON:" + JSON.stringify(captured));
});
"""


def _run_page(node, workdir, payload):
    """Execute the page's own script over `payload`.

    Returns (returncode, stderr, captured), where `captured` maps element id
    to the HTML the page wrote into it.
    """
    import subprocess

    workdir.mkdir(parents=True, exist_ok=True)
    render = _render()
    html = render.TEMPLATE
    opening = "<script>\n"
    start = html.index(opening, html.index('id="data"'))
    script = html[start + len(opening):html.rindex("</script>")]
    script = script.replace("__DIGEST__", "0" * 64)

    (workdir / "harness.js").write_text(
        HARNESS + '\ndocument.getElementById("data").textContent = '
        + json.dumps(json.dumps(payload)) + ";\n", encoding="utf-8")
    (workdir / "page.js").write_text(script, encoding="utf-8")
    (workdir / "run.js").write_text(
        'require("./harness.js");\nrequire("./page.js");\n', encoding="utf-8")

    # encoding is named: the page carries the vendor's own text, and this
    # machine's console codepage is cp1250, which cannot decode it.
    result = subprocess.run([node, str(workdir / "run.js")], capture_output=True,
                            text=True, encoding="utf-8", errors="replace",
                            timeout=60, cwd=str(workdir))
    marker = "CAPTURED-JSON:"
    captured = (json.loads(result.stdout.split(marker, 1)[1])
                if marker in result.stdout else {})
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
        row["stale_from"] = "2026-09-09T22:13:39+00:00"

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
