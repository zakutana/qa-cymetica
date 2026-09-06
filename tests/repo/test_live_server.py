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

    listener = live.subscribe()

    # Change what the page shows, without touching the committed state: the
    # digest is a function of the payload, so this is the same signal a real
    # ledger change produces.
    live.payload = dict(live.payload)
    live.payload["display_counts"] = {"MADE UP": 1}
    live.digest = "0" * 64
    live.notify()

    got = listener.get(timeout=5)
    conclude(Measurement(
        verdict="passed" if got == live.digest else "failed",
        reason=("a subscriber received the new digest"
                if got == live.digest else
                f"the subscriber received {got!r}, not the current digest"),
        left=got, right=live.digest,
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
    html = render.render(render.build_payload(allow_stale_head=True))

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

    # And clearing writes the timestamp the comparison reads.
    assert 'writeStore("qa.seenAt"' in template, \
        "nothing persists the read timestamp, so the switch forgets on reload"
