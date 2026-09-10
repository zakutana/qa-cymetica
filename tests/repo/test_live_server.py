"""The local server pushes a change, and stays quiet when nothing changed.

The console became a page held open in a tab all day, which makes one question
load-bearing: is what I am looking at current? The answer is only trustworthy
if two things hold, and they pull in opposite directions.

  A real change must reach the open tab.        Otherwise it is a stale page
                                                that claims to be live, which
                                                is worse than a snapshot.
  Nothing else may reach it.                    A page that reloads whenever
                                                any file is touched throws away
                                                scroll position and open rows
                                                for no reason, and teaches the
                                                operator to distrust it.

Both are asserted here against the real module, in a temp state directory. The
second one is the reason the watcher compares the payload DIGEST rather than
file mtimes: every pytest session writes a run record, so an mtime watcher
would reload the page several times a sweep with nothing to show for it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import types
import queue
import shutil
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent


def _serve_module():
    spec = importlib.util.spec_from_file_location(
        "serve_under_test", REPO / "scripts" / "serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def serve(tmp_path, monkeypatch):
    """The module under test, so a test can reach its import seam."""
    return _serve_module()


@pytest.fixture
def live(tmp_path, monkeypatch, serve):
    """A Live built over a copy of the committed state, writing nowhere real."""
    state = tmp_path / "state"
    shutil.copytree(REPO / "state", state)
    # QA_STATE_DIR alone is enough: render.out_path() follows it, so the only
    # file Live writes lands under the temp tree. REPO_ROOT stays real, because
    # that is how the server finds scripts/render.py.
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    return serve.Live()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_real_change_reaches_a_subscriber(live):
    """A changed payload wakes every open tab, exactly once."""
    first = live.digest
    assert first, "the server produced no payload to begin with"

    # TWO listeners, because the docstring says "every open tab" and one
    # subscriber cannot measure that: a notify() waking only listeners[0] used
    # to pass here. The emptiness check below is the "exactly once" half, and
    # it is the pattern the sibling test already owns. Deep pass, 2026-09-08,
    # 3/3.
    listener, second = live.subscribe(), live.subscribe()

    # A REAL change to the state this Live renders from, then rebuild().
    #
    # This used to set live.payload, set live.digest to zeros and call
    # live.notify() by hand -- which exercised the last step and skipped every
    # one before it. Nothing in the file entered rebuild() on a changed state,
    # so `rebuild` returning False on a genuine change, or a file dropping out
    # of WATCHED, left the tab permanently stale with this test green. The
    # module docstring calls that outcome worse than a snapshot.
    # A section title, because that is something the page RENDERS. A new
    # top-level key would not do: build_payload reads `sections` and `totals`
    # and nothing else out of this file, so an invented key changes the bytes
    # on disk and not the payload -- and a test that perturbed one would report
    # "no change reached the tab" for a change the page was never going to
    # show. Checked before writing it, rather than after.
    inventory_path = Path(os.environ["QA_STATE_DIR"]) / "inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["sections"][0]["title"] += " (a real change)"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    # The pair the poll loop runs (serve.py:292-293): rebuild decides, notify
    # wakes. The old test performed only the second half, on a digest it had
    # set itself.
    changed = live.rebuild()
    if changed:
        live.notify()
    got = listener.get(timeout=5) if changed else None
    also = second.get(timeout=5) if changed else None
    twice = False
    if changed:
        for queued in (listener, second):
            try:
                queued.get(timeout=0.5)
                twice = True
            except queue.Empty:
                pass

    agrees = (changed and got == live.digest and got != first
              and also == live.digest and not twice)
    conclude(Measurement(
        verdict="passed" if agrees else "failed",
        reason=("a change under state/ was detected by rebuild() and the new "
                "digest reached BOTH subscribers, exactly once each"
                if agrees else
                "rebuild() did not report the state as changed"
                if not changed else
                "a subscriber was woken twice for one change, so every open "
                "tab would reload twice"
                if twice else
                f"the subscribers received {got!r} and {also!r}, not the "
                f"current digest"),
        left=[got, also], right={"digest": live.digest, "before": first,
                                 "rebuild_reported_a_change": changed,
                                 "woken_twice": twice},
        sources={"module": "scripts/serve.py"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_rebuilding_unchanged_state_notifies_nobody(live):
    """The quiet half, and the one that decides whether the page is bearable.

    A pytest session writes a run record every time it runs. If that alone
    reloaded the page, a sweep would throw the operator's scroll position away
    four or five times while they were reading.
    """
    listener = live.subscribe()
    changed = live.rebuild()

    assert changed is False, \
        "rebuilding identical state reported a change, so the page would reload"
    with pytest.raises(queue.Empty):
        listener.get(timeout=0.5)

    conclude(Measurement(
        verdict="passed",
        reason=("re-rendering unchanged state produced no change and woke no "
                "subscriber, so the open tab keeps its scroll and open rows"),
        left=False, right=live.digest,
        sources={"module": "scripts/serve.py"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_broken_render_keeps_serving_the_last_good_page(live, serve, monkeypatch):
    """A page that dies on a bad fold is a page nobody trusts to be open.

    The console is the thing being read while the pipeline is being changed,
    so a render error has to degrade to "the last good page, plus an error the
    server names" rather than to a blank tab.
    """
    good_html, good_digest = live.html, live.digest
    assert good_html

    # Patched at the import seam, not on the loaded module: rebuild() now
    # re-imports render.py first, so that a change to the renderer reaches the
    # open tab -- which means a patch applied to the old object is discarded
    # before it is ever called.
    def explode(*_, **__):
        raise ValueError("deliberate")

    broken = types.SimpleNamespace(build_payload=explode,
                                   render=explode, payload_hash=explode,
                                   out_path=live.render.out_path)
    monkeypatch.setattr(serve, "_render_module", lambda: broken)
    live.rebuild()

    conclude(Measurement(
        verdict="passed" if live.html == good_html and live.error else "failed",
        reason=(f"a failed render left the last good page in place and recorded "
                f"the reason: {live.error}"
                if live.html == good_html and live.error else
                "a failed render discarded the page the tab is showing"),
        left=live.error, right=good_digest[:16],
        sources={"module": "scripts/serve.py"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_page_that_stopped_updating_says_so_on_itself(live, serve, monkeypatch):
    """The failure that served a two-hour-old truth without a word.

    2026-09-08: `auto` and `kind` were added to ALLOWED_EVENT_KEYS. The console
    had been running since before that, holding the older qa.state -- rebuild()
    re-imports render.py by design but nothing under it -- so its loader
    refused every journal line carrying the new key. From 11:32 to 13:30 it
    served a page showing 39 rows and three findings as STILL REPRODUCIBLE that
    had been verified as fixed hours earlier, and the operator found it by
    disbelieving their own dashboard.

    Two things made it silent, and this holds the second one. rebuild() keeps
    the last good html on an exception, which is right. But `changed` compares
    the error to the PREVIOUS error, so an identical failure repeating every
    minute reads as "nothing moved": no log line, no notification, and a page
    that looks live.

    A page that has stopped being rebuilt must say so on itself. The server
    window is not where anyone looks -- the page is.
    """
    assert live.html, "nothing to go stale"
    good = live.html

    # At the import seam, like the sibling above: rebuild() re-imports render.py
    # every time, so a patch on the loaded object is discarded before it is used.
    def explode(*_, **__):
        raise RuntimeError("JournalError: line 1338: unknown key 'auto'")

    broken = types.SimpleNamespace(build_payload=explode, render=explode,
                                   payload_hash=explode,
                                   out_path=live.render.out_path)
    monkeypatch.setattr(serve, "_render_module", lambda: broken)
    # Twice, with the SAME error: the second is the one that used to go silent.
    live.rebuild()
    live.rebuild()

    assert live.error and "unknown key" in live.error
    served = live.serve_html()
    assert served != good, (
        "the page served after a failed rebuild is byte-identical to the last "
        "good one, so a stalled console is indistinguishable from a working one"
    )
    # The band's own words, not any occurrence of "stale". The first version
    # accepted `"stale" in served.lower()`, and the rendered page carries
    # "stale" 8 times and "stale_from" 43 more from TEMPLATE itself -- so the
    # disjunct was true of every page the renderer can emit, and replacing the
    # band with an empty div would have kept all three assertions green while
    # the page named nothing. Deep pass, 2026-09-08, 3/3.
    assert serve.STALE_BANNER in served, (
        "the page does not say it stopped updating; the only trace is a line "
        "in a server window nobody reads"
    )
    assert "unknown key" in served, (
        "the band is there but does not name the error, so a reader cannot "
        "tell a stalled console from a slow one"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_knows_which_render_it_is():
    """A tab that reconnects must compare against itself, not against a memory.

    The live client held the server's digest in a variable and overwrote it on
    every hello. So when the server restarted -- which happens on any change to
    the renderer -- the tab reconnected, adopted the new digest, printed "live"
    and never reloaded. It then showed markup from before the restart while
    claiming to be current: the console committing the exact drift it exists to
    catch, and the reason an operator sat looking at notification marks that a
    later render had already fixed.

    Two properties make it self-healing, and both are structural:

      the page carries the digest it was RENDERED from, so the comparison has
        a fixed point that cannot be reassigned
      hello and changed take the same path, because a hello after a dropped
        connection carries exactly what a missed change would have
    """
    import re

    render = _render_module_for_page()
    html = render.render(render.build_payload())

    baked = re.search(r'const RENDERED_AS = "([0-9a-f]{64})"', html)
    assert baked, "the page does not carry the digest it was rendered from"

    footer = re.search(r"qa-payload-sha256: ([0-9a-f]{64})", html)
    assert footer and footer.group(1) == baked.group(1), (
        "the digest baked into the page differs from the one stamped on it, so "
        "the tab would compare against the wrong fixed point"
    )
    assert "__DIGEST__" not in html, "the placeholder was never substituted"

    # Both events must reach the same handler. Asserted on the source because
    # the failure is a missing branch, and a missing branch has no behaviour to
    # observe until the day it costs you an afternoon.
    for event in ("hello", "changed"):
        assert f'src.addEventListener("{event}", catchUp)' in html, (
            f"the {event} event does not go through the catch-up path, so a "
            f"tab that lost the connection can stay stale while saying live"
        )


def _render_module_for_page():
    spec = importlib.util.spec_from_file_location(
        "render_for_page_test", REPO / "scripts" / "render.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_marking_read_is_the_only_switch_and_it_hides_every_mark():
    """"Mark all as read" is one switch, and after it nothing is marked.

    The operator stated the contract in one sentence: after clicking it, no
    envelope may appear anywhere. That is only guaranteed if there is exactly
    ONE place that decides whether a mark shows, and its decision is a
    comparison against the read timestamp -- a second code path that could
    reveal a mark would be a switch that does not switch.

    So this asserts the shape rather than a behaviour: one renderer, one
    decision, and a mark that ships hidden. The behaviour was verified in a
    browser (23 marks, click, 0, reload, 0); what a test can hold down for
    good is that the structure making it true does not quietly grow a second
    branch.
    """
    import re

    render = _render_module_for_page()
    template = render.TEMPLATE

    # It ships hidden: no window between render and paintBell where every row
    # flashes a mark it has not earned.
    assert re.search(r'<span class="newreply" data-newreply hidden', template), \
        "the mark does not ship hidden, so it shows before anything decides"

    # Exactly one place assigns its visibility, and it compares against seenAt.
    assignments = re.findall(r"\.hidden\s*=\s*([^;]+);", template)
    mark_rules = [a for a in assignments if "vendorAt" in a]
    assert len(mark_rules) == 1, (
        f"{len(mark_rules)} code paths decide whether a reply mark shows; one "
        f"of them could reveal a mark the operator already cleared: {mark_rules}"
    )
    assert "seenAt()" in mark_rules[0], (
        f"the mark's visibility is not decided by the read timestamp, so "
        f'"Mark all as read" is not the switch that controls it: {mark_rules[0]}'
    )

    # The assertion above counts only rules that MENTION vendorAt, so a second
    # path that reveals a mark without consulting the read timestamp -- the
    # obvious shape being `m.hidden = false` inside some expand-all or debug
    # affordance -- would slip past it entirely while breaking the contract it
    # claims to guard. Unconditional reveals are therefore enumerated: exactly
    # one exists, and it is the inbox jumping to a row the filter had hidden.
    # Matched on the source directly, not on `assignments`: that pattern reads
    # up to the next semicolon, so an arrow-function body -- `forEach(m =>
    # m.hidden = false)` -- captures "false)" and would not compare equal to
    # "false". That is the likeliest shape a reveal would take, and the first
    # draft of this assertion missed exactly it.
    unconditional = re.findall(r"\.hidden\s*=\s*(false|!1)\b", template)
    assert len(unconditional) == 1, (
        f"{len(unconditional)} places set .hidden = false unconditionally; each "
        f"one can reveal something the operator already cleared, so a new one "
        f"needs a look rather than a silent pass: {unconditional}"
    )
    assert "row.hidden = false" in template, (
        "the one permitted unconditional reveal is the inbox un-hiding the row "
        "it jumps to; it is gone, so this allowance no longer describes the code"
    )

    # And clearing writes the timestamp the comparison reads.
    assert 'writeStore("qa.seenAt"' in template, \
        "nothing persists the read timestamp, so the switch forgets on reload"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hidden_attribute_actually_hides():
    """Setting el.hidden must remove the element, not merely mark it.

    This is the bug the sibling structural test could not catch, and the more
    embarrassing half is how it survived verification.

    `.newreply { display: inline-flex }` is a CLASS selector. The browser's own
    `[hidden] { display: none }` lives in the user-agent stylesheet, which any
    class rule outranks. So "Mark all as read" set el.hidden = true on all 30
    marks, cleared the badge, and changed nothing on screen: every envelope
    stayed drawn. Published as an Artifact it never showed, because that
    runtime injects exactly this rule; served raw from localhost, nothing did.

    It survived because the check measured `el.hidden` -- the property that was
    being set correctly -- instead of `getComputedStyle(el).display`, which is
    what a reader sees. A test that asks the code what it did, rather than the
    page what it shows, will confirm any bug that lies in the gap between them.

    One `!important` rule closes the whole class, for every element the page
    toggles this way, now and later.
    """
    import re

    css = _render_module_for_page().TEMPLATE

    rule = re.search(r"\[hidden\]\s*\{[^}]*display\s*:\s*none\s*!important", css)
    assert rule, (
        "the sheet has no `[hidden] { display: none !important }`, so any class "
        "rule setting `display` on a toggled element silently wins and the "
        "element stays on screen with its hidden attribute set"
    )

    # The rule above wins on !important, and the one thing that can still beat
    # it is another !important on display. That is not hypothetical: the bug it
    # replaced was a plain class rule beating the UA stylesheet, and the same
    # mistake one notch louder would beat this one. So no other rule may set
    # display with !important.
    #
    # (This used to collect the names of toggled elements and assert only that
    # the set was non-empty -- a check that could not fail for any realistic
    # edit, sitting under a comment promising it verified coverage.)
    important_display = [
        m.group(0) for m in re.finditer(r"[^{}]+\{[^}]*display\s*:[^;}]*!important[^}]*\}", css)
        if "[hidden]" not in m.group(0)
    ]
    assert not important_display, (
        f"{len(important_display)} rule(s) other than [hidden] set display with "
        f"!important, and any of them can beat the hide rule the way a plain "
        f"class beat the browser's: {[r.strip()[:70] for r in important_display]}"
    )

    toggled = set(re.findall(r"(\w+)\.hidden\s*=", css))
    assert toggled, "nothing is toggled via .hidden -- has the mechanism changed?"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_client_hanging_up_is_not_reported_as_an_error():
    """A live reload drops its own SSE stream, and that is not a crash.

    Every reload abandons an in-flight event stream and a keep-alive
    connection. Windows reports the second one as WinError 10053, and
    socketserver's default handle_error prints a full traceback for it -- so
    the console window filled with stack traces while the server was working
    exactly as designed. The operator asked what was broken; nothing was.

    The danger is not the noise itself but what it hides: a genuine handler
    exception prints into the same stream and would have been read as more of
    the same. So the suppression is narrow -- three connection-dropped types,
    nothing else -- and this asserts both halves, because a handler that
    swallowed everything would turn a cosmetic problem into a silent one.
    """
    import contextlib
    import io

    serve = _serve_module()
    server = serve.SingleServer.__new__(serve.SingleServer)

    def stderr_from(exc):
        buf = io.StringIO()
        try:
            raise exc
        except Exception:
            with contextlib.redirect_stderr(buf):
                server.handle_error(None, ("127.0.0.1", 1234))
        return buf.getvalue()

    for dropped in (ConnectionAbortedError(10053, "aborted"),
                    ConnectionResetError("reset"),
                    BrokenPipeError("pipe")):
        assert stderr_from(dropped) == "", (
            f"{type(dropped).__name__} still prints a traceback; every live "
            f"reload produces one, so the console fills with stack traces that "
            f"look like a failing server"
        )

    real = stderr_from(ValueError("a genuine handler bug"))
    assert "ValueError" in real, (
        "a real handler exception was swallowed along with the client "
        "disconnects, which turns visible noise into an invisible failure"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_starting_the_server_does_not_rewrite_a_page_that_is_already_current(
        tmp_path, monkeypatch, serve):
    """Starting the console dirtied the tree, and a dirty tree refuses a run.

    `rebuild()` compared the new digest against its OWN previous one, which is
    the empty string on a fresh process -- so the first rebuild always wrote
    dashboard/index.html, whatever was already there. The page it wrote was
    byte-identical apart from `generated_at`, which is deliberately not in the
    digest, so the write said nothing and cost everything: `git status` came
    up dirty, `prereg.py` refuses a dirty tree, and the operator opened this
    morning on a diff they had not made and could not explain.

    The digest is already embedded in the page it describes. Comparing against
    that answers the actual question -- is the file on disk this render? --
    and the in-memory comparison stays exactly as it is, because it answers a
    different one: has anything changed since the last tick, and should the
    open tab be told.
    """
    state = tmp_path / "state"
    shutil.copytree(REPO / "state", state)
    monkeypatch.setenv("QA_STATE_DIR", str(state))

    first = serve.Live()
    page = first.render.out_path()
    assert page.exists(), "the first start has to write the page"
    written = page.stat().st_mtime_ns
    body = page.read_text(encoding="utf-8")

    # A second server over the same state: same payload, same template, same
    # digest. Nothing about the page has changed, so nothing may be written.
    second = serve.Live()
    assert second.digest == first.digest
    assert page.stat().st_mtime_ns == written, (
        "starting the console rewrote a page that was already current, which "
        "is what leaves an unexplained diff in the tree"
    )
    assert page.read_text(encoding="utf-8") == body

    # And a real change still lands on disk, or the console would serve a page
    # it never wrote.
    inventory = state / "inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["sections"][0]["title"] = data["sections"][0]["title"] + " (moved)"
    inventory.write_text(json.dumps(data), encoding="utf-8")

    assert second.rebuild() is True
    assert page.stat().st_mtime_ns != written, \
        "a real change did not reach the file"
    assert "(moved)" in page.read_text(encoding="utf-8")

    conclude(Measurement(
        verdict="passed",
        reason=("starting the server over an already-current page wrote "
                "nothing, and a real change still wrote"),
        left=first.digest, right=second.digest,
        sources={"module": "scripts/serve.py"}))
