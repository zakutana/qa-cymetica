"""What we agreed to do next has to survive a /clear on its own.

The operator, 2026-09-10, after being told twice in one day where we had left
off: they do not want to carry that. And they were right that nothing carried
it for them. Three things reach a fresh session -- MEMORY.md's index,
DEEP-PASS.md's handover, the unanswered Telegram threads -- and none of them is
"the piece of work we agreed on". DEEP-PASS.md's *Čeká na tebe* is deliberately
the opposite: things that need THEIR judgement, not things we said we would do.

So the agreed next step is written down when it is agreed, and a SessionStart
hook prints it. The rules it has to obey are the ones this repository has
learned the hard way about anything that reaches auto-loaded context:

  * one line per item, because a hook that pastes bodies into context is the
    one the operator called wasted context;
  * dated, and going stale is loud -- an item nobody has ticked in two weeks
    is a badge nobody can clear, which is the same defect as a memory that
    grows every run;
  * ticked items stay in the file as history and stop being printed, because
    deleting the record of what we decided is the mistake outbox/reports.yaml
    taught this morning.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
NEXT = REPO / "NEXT.md"
HOOK = REPO / ".claude" / "hooks" / "next_step.py"
PROGRESS = REPO / "audits" / "deep-pass-progress.json"

# An item nobody has ticked in this long is either done and unrecorded, or was
# never really next. Either way the file has stopped describing the work.
STALE_DAYS = 14


def _hook():
    """The hook's own parser, so this asserts on what the session will see."""
    spec = importlib.util.spec_from_file_location("next_step_hook", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pass_in_flight() -> str | None:
    """The run id of a deep pass that is running right now, or None.

    `liveness` is imported rather than reimplemented: it holds the 24-hour
    window and the reason the window is elapsed time rather than a calendar
    day, and two copies of that judgement would drift the first time one is
    corrected. `tests/` is not a package, hence the path import.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "deep_pass_guard", REPO / "tests" / "repo" / "test_deep_pass_finished.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
        if module.liveness(progress) == "running":
            return str(progress.get("run") or "a deep pass")
    except Exception:
        return None
    return None


def items() -> list[dict]:
    if not NEXT.is_file():
        return []
    return _hook().parse(NEXT.read_text(encoding="utf-8"))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_line_that_looks_like_an_item_is_one():
    """A malformed line is an item that will never be printed and never noticed."""
    if not NEXT.is_file():
        raise Inconclusive("NEXT.md does not exist yet")
    hook = _hook()
    loose = [line for line in hook.body(NEXT.read_text(encoding="utf-8"))
             if hook.LOOKS_LIKE_ITEM.match(line) and not hook.ITEM.match(line.rstrip())]

    # The shapes a hand edit actually produces, pinned as data. This held only
    # lines beginning exactly `- [` against ITEM, so a bullet written `*` or
    # with no space after the dash was invisible to the hook AND to this guard
    # -- an agreed next step that will never be printed and never noticed,
    # which is the sentence in this test's own docstring.
    for shape in ("* [ ] 2026-09-10  clone the bot Nexus recommended",
                  "-[ ] 2026-09-10  clone the bot Nexus recommended",
                  "  - [ ] 2026-09-10  clone the bot Nexus recommended",
                  "+ [x] 2026-09-10  already done"):
        assert hook.LOOKS_LIKE_ITEM.match(shape), \
            f"a reader would call this an item and the guard would not: {shape!r}"
        assert not hook.ITEM.match(shape.rstrip()), \
            f"the fixture no longer represents a malformed line: {shape!r}"
    # And a line that is prose, not a bullet, is not an item.
    assert not hook.LOOKS_LIKE_ITEM.match("Formát je závazný, protože [...]")
    assert not loose, (
        "these lines start like an item and do not parse as one, so the hook "
        f"will silently skip them: {loose}"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_open_has_gone_stale():
    """The file describes the work, or it describes the past.

    **Inconclusive while a deep pass is in flight**, and that is not politeness.
    This test lives in `tests/repo`, which the pass runs at step 6, and step 9
    reverts the run's commits on a red it cannot resolve. Whether a fifteen-day
    item happened and nobody ticked it, or was never really next, is exactly
    the judgement an unattended pass may not make -- so left alone it would
    turn a stale line into a reverted night. The same shape cost this
    repository a day on 2026-09-09, in the guard next door.

    Step 10 is where it belongs instead: the pass carries the item forward and
    names it, and the morning decides.
    """
    running = _pass_in_flight()
    if running:
        raise Inconclusive(
            f"{running} is running; whether a stale item happened or was never "
            f"next is a judgement, and step 9 reverts a night on a red it "
            f"cannot resolve")
    rows = [i for i in items() if not i["done"]]
    if not rows:
        raise Inconclusive("nothing is open, so nothing can be stale")
    cutoff = date.today() - timedelta(days=STALE_DAYS)
    stale = [i for i in rows
             if datetime.strptime(i["at"], "%Y-%m-%d").date() < cutoff]
    assert not stale, (
        f"open for more than {STALE_DAYS} days without being ticked or "
        f"removed: {[i['what'][:60] for i in stale]}. Either it happened and "
        f"nobody said so, or it was never next."
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_prints_the_open_items_and_nothing_else(tmp_path):
    """One line each, never the body, and silent when there is nothing."""
    assert HOOK.is_file(), "the hook that prints it does not exist"

    result = subprocess.run([sys.executable, str(HOOK)], cwd=REPO,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60)
    assert result.returncode == 0, "a hook may never fail a session start"

    printed = [line for line in result.stdout.splitlines() if line.strip()]
    open_items = [i for i in items() if not i["done"]]
    if not open_items:
        assert not printed, "the hook spoke when there was nothing to say"
        return

    assert printed, "there are open items and the hook printed nothing"
    assert len(printed) <= len(open_items) + 1, (
        f"the hook printed {len(printed)} lines for {len(open_items)} open "
        f"item(s); it is an index, not the file"
    )
    for item in open_items[:3]:
        assert any(item["what"][:40] in line for line in printed), (
            f"an open item never reached the session: {item['what'][:60]}"
        )

    empty = tmp_path / "NEXT.md"
    empty.write_text("# Next\n\nnothing open\n", encoding="utf-8")
    quiet = subprocess.run(
        [sys.executable, str(HOOK)], cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
        env={**os.environ, "QA_NEXT_FILE": str(empty)})
    assert quiet.returncode == 0
    assert not quiet.stdout.strip(), "silent when there is nothing open"
