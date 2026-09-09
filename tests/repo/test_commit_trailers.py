"""Which effort wrote this commit, recorded where the week can read it.

`Co-Authored-By` already names the model on 255 of 333 commits, so the weekly
retrospective can ask which model did what. It cannot ask about effort, and
effort is half the question: the operator's table in CLAUDE.md says Sonnet at
high for a sweep and Opus at xhigh for the fold, and nothing in the repository
records which one a commit actually ran under.

`$CLAUDE_EFFORT` carries it, and it carries the EFFECTIVE value rather than the
session's: a subagent whose frontmatter says `effort: high` reads `high` inside
a session set to `max`. Checked before this was built, because a trailer that
recorded the session setting on every commit would answer a question nobody
asked and look like an answer to the one that matters.

So a `prepare-commit-msg` hook appends `Effort: <level>` when the variable is
set. When it is not -- the operator committing by hand -- it appends nothing,
which is the honest record: nobody's effort setting wrote that commit.

**Inconclusive, not failed, when the hook is not installed.** It needs a
`git config` that lives in `.git/config` and cannot be committed, so a fresh
clone does not have it and is not wrong. A red here would be a red the deep
pass cannot resolve, and step 9 of that skill reverts the run's commits on an
unresolvable red -- a test about bookkeeping would then undo a night's work.
Rule 8's shape: not installed is not broken.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
HOOK = REPO / ".githooks" / "prepare-commit-msg"


def _hooks_path() -> str | None:
    try:
        done = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                              cwd=REPO, capture_output=True, text=True)
    except OSError:
        return None
    return done.stdout.strip() or None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_effort_trailer_hook_is_installed_or_honestly_absent():
    """Installed and working, or not installed and said so. Never half."""
    configured = _hooks_path()

    if configured is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="core.hooksPath is not set here, so no commit on this "
                   "machine records its effort. Install with: "
                   "git config core.hooksPath .githooks",
            sources={"hook": ".githooks/prepare-commit-msg"}))
        return

    problems = []
    if configured != ".githooks":
        problems.append(f"core.hooksPath is {configured!r}, so the hook in "
                        f".githooks never runs")
    if not HOOK.is_file():
        problems.append(".githooks/prepare-commit-msg does not exist, and "
                        "core.hooksPath points at a directory without it -- "
                        "which also means no OTHER git hook can be added there")
    else:
        body = HOOK.read_text(encoding="utf-8")
        if "CLAUDE_EFFORT" not in body:
            problems.append("the hook does not read $CLAUDE_EFFORT")
        # Appending unconditionally would stamp a second trailer on every
        # amend and on every rebase that replays a commit.
        if "Effort:" not in body:
            problems.append("the hook does not look for an Effort: trailer "
                            "before adding one")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                "core.hooksPath points at .githooks and the hook there records "
                "the effort a commit was written under"),
        left=problems,
        sources={"hook": ".githooks/prepare-commit-msg"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_quiet_when_nobody_set_an_effort(tmp_path):
    """Run against a message file, twice, the way git runs it.

    The operator commits by hand and no agent effort wrote that commit; the
    hook must add nothing rather than guess. And a second run over a message
    that already carries the trailer must not add a second one -- an amend and
    a rebase both replay this.
    """
    if not HOOK.is_file():
        conclude(Measurement(verdict="inconclusive",
                             reason="no hook to exercise yet"))
        return

    def run(text: str, effort: str | None) -> str:
        msg = tmp_path / "COMMIT_EDITMSG"
        msg.write_text(text, encoding="utf-8")
        import os

        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_EFFORT"}
        if effort is not None:
            env["CLAUDE_EFFORT"] = effort
        done = subprocess.run(["sh", str(HOOK), str(msg), "message"],
                              cwd=REPO, env=env, capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
        return msg.read_text(encoding="utf-8")

    body = "a commit\n\nCo-Authored-By: Someone <x@y>\n"

    silent = run(body, None)
    stamped = run(body, "xhigh")
    twice = run(stamped, "xhigh")

    # The defect this hook shipped with, found by its own first real commit.
    # That message explained the hook, and its prose wrapped so that a line
    # began "Effort: lines read as two commits"; the guard against
    # double-stamping was `^Effort:[[:space:]]`, matched it, and added nothing.
    # A body may say anything. A trailer is the key and one word.
    prose = ("a commit\n\nthe hook skips a message where an\n"
             "Effort: line already appears in the prose, which is not\n"
             "the same thing at all\n")
    wrapped = run(prose, "high")

    ok = (silent == body and "Effort: xhigh" in stamped
          and twice.count("Effort: ") == 1
          and wrapped.rstrip().endswith("Effort: high"))
    conclude(Measurement(
        verdict="passed" if ok else "failed",
        reason=("unset effort adds nothing, a set one is recorded once, a "
                "second pass adds no second trailer, and prose that merely "
                "starts a line with the key does not suppress the real one"
                if ok else
                f"unset={silent!r} set={stamped!r} twice={twice!r} "
                f"prose={wrapped!r}"),
        sources={"hook": ".githooks/prepare-commit-msg"}))
