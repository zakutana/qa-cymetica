"""The page is re-rendered by the commit that moves what it shows.

Rule 12 says the committed dashboard must be a render of the committed state,
and `tests/repo/test_repo_consistency.py` checks it. What nothing did was
*produce* that state: the rule reduced to "the operator remembers", and on
2026-09-20 it broke three times in one session -- twice by committing
correspondence without a render, once by adding a test, because the payload
carries the suite's own counts. A guard that is usually red for a boring
reason is a guard that stops being read, which is the same sentence
`ARCHITECTURE.md` wrote about the `events_head` red it replaced.

So `.githooks/pre-commit` renders. Two properties make that safe, and both are
asserted here:

* **`--if-stale` writes only when the page would change.** `generated_at` is
  stamped fresh on every render and excluded from the hash, so a blind render
  would rewrite 684 KB on every commit and make `git status` dirty for
  nothing -- which `prereg.py` then refuses. The same trick already guards the
  console's own loop (`scripts/serve.py`), and the digest now has one
  implementation, in `render.py`, which `serve.py` imports.
* **It cannot fail a commit.** The hook's contract, inherited from
  `keep.py track`: bookkeeping may not be the reason a commit cannot be made.

The hook assertion is INCONCLUSIVE rather than failed when `core.hooksPath` is
unset: a fresh clone does not have it and is not wrong (the reasoning is
`tests/repo/test_commit_trailers.py`, and rule 8's shape -- not installed is
not broken).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
RENDER = REPO / "scripts" / "render.py"
HOOK = REPO / ".githooks" / "pre-commit"


def _hooks_path() -> str | None:
    proc = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                          cwd=str(REPO), capture_output=True, text=True)
    return proc.stdout.strip() or None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_if_stale_writes_once_and_then_leaves_the_page_alone(tmp_path):
    """Twice in a row: the second run must not touch the file."""
    env = {"QA_STATE_DIR": str(tmp_path), "PYTHONIOENCODING": "utf-8"}
    import os

    env = dict(os.environ, **env)
    page = tmp_path / "dashboard" / "index.html"

    first = subprocess.run([sys.executable, str(RENDER), "--if-stale"],
                           cwd=str(REPO), capture_output=True, text=True, env=env)
    assert first.returncode == 0, first.stderr
    assert page.exists(), f"the first --if-stale wrote nothing: {first.stdout}"
    stamp = page.stat().st_mtime_ns
    body = page.read_bytes()

    second = subprocess.run([sys.executable, str(RENDER), "--if-stale"],
                            cwd=str(REPO), capture_output=True, text=True, env=env)
    assert second.returncode == 0, second.stderr
    assert page.read_bytes() == body, (
        "the second --if-stale rewrote a page that had not changed; "
        "generated_at moves on every render, so this would dirty the tree "
        "on every commit and prereg.py refuses a dirty tree")
    assert page.stat().st_mtime_ns == stamp, "the file was rewritten byte-identically"
    assert second.stdout.strip() == "", (
        f"--if-stale spoke when it had nothing to do: {second.stdout!r}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_if_stale_rewrites_when_the_payload_moved(tmp_path):
    """A page that no longer matches its state must be rebuilt."""
    import os

    env = dict(os.environ, QA_STATE_DIR=str(tmp_path), PYTHONIOENCODING="utf-8")
    page = tmp_path / "dashboard" / "index.html"

    subprocess.run([sys.executable, str(RENDER), "--if-stale"], cwd=str(REPO),
                   capture_output=True, text=True, env=env, check=True)
    # A page whose trailer says it was rendered from something else. The
    # digest is what the guard compares, so corrupting it is what "stale"
    # means to this flag.
    page.write_text(page.read_text(encoding="utf-8").replace(
        "qa-payload-sha256: ", "qa-payload-sha256: 0"), encoding="utf-8")
    before = page.read_bytes()

    again = subprocess.run([sys.executable, str(RENDER), "--if-stale"],
                           cwd=str(REPO), capture_output=True, text=True, env=env)
    assert again.returncode == 0, again.stderr
    assert page.read_bytes() != before, "a stale page was left in place"
    assert again.stdout.strip(), "a render that wrote must say so"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_commit_hook_renders_the_page_it_commits():
    """The rule that used to be "the operator remembers"."""
    if _hooks_path() is None:
        raise Inconclusive(
            "core.hooksPath is not set in this clone, so the hook does not "
            "run here -- not installed is not broken (rule 8)")
    body = HOOK.read_text(encoding="utf-8")
    renders = "--if-stale" in body and "dashboard" in body
    # And only from state that is going into the commit. The render reads the
    # WORKING TREE, so with state/ modified-but-unstaged -- commit a code
    # change first, fold second, which is the ordinary order here -- staging
    # the page attaches a render of a ledger the commit does not carry.
    # tests/repo reads the working tree too, so it stays green locally and
    # rule 12 goes red on a fresh clone, where the working tree IS the
    # commit. Found by three readers on 2026-09-20.
    guarded = "git diff --name-only -- state/" in body
    conclude(Measurement(
        verdict="passed" if renders and guarded else "failed",
        reason=("the pre-commit hook re-renders the dashboard and stages it, "
                "and only when state/ has nothing unstaged"
                if renders and guarded else
                "the pre-commit hook does not render, so rule 12's guard is "
                "left to memory again"
                if not renders else
                "the hook renders from the working tree and stages the page "
                "without checking that state/ is what the commit carries, so "
                "a page from an unstaged ledger reaches the history"),
        left=[renders, guarded], right=[True, True],
        population={"hook": HOOK.relative_to(REPO).as_posix()},
        sources={"rule": "CLAUDE.md rule 12 and 'After any change to state'"},
    ))
