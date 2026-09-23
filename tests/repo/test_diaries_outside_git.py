"""A diary written while a run may be in flight lives outside git.

state/clones.jsonl was committed, and the laboratory writes it in the middle
of a tick -- every clone, transfer and pause (the plan's V2, review of
2026-09-23). A tree that is dirty during a run is one no run reaches level V
from, which is why paper.jsonl, rooms.jsonl and the other diaries left git
long ago. It is gitignored now, untracked once through `keep.py release`, and
copied into audits/lab/ by `keep.py snapshot` like the others, so it does
not live on one disk either.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _keep():
    spec = importlib.util.spec_from_file_location(
        "keep_diaries", REPO / "scripts" / "keep.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_clone_diary_is_outside_git_and_copied_into_audits():
    ignored = subprocess.run(["git", "check-ignore", "-q", "--no-index",
                              "state/clones.jsonl"], cwd=REPO).returncode == 0
    tracked = subprocess.run(["git", "ls-files", "state/clones.jsonl"],
                             cwd=REPO, capture_output=True,
                             text=True).stdout.strip()
    assert ignored, "state/clones.jsonl is not gitignored"
    assert not tracked, "state/clones.jsonl is still tracked -- keep.py release"
    assert "clones.jsonl" in _keep().DIARIES, (
        "nothing copies clones.jsonl into audits/lab/")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_release_lets_go_of_a_diary_and_of_nothing_else():
    """`keep.py release` runs `git rm --cached` on state/, which
    protect_state refuses from the shell -- so it may name only a diary, and
    only one git already ignores. Refused before git is asked anything."""
    keep = _keep()
    # Matched on the refusal's own words: argparse's exit for an unknown
    # subcommand is a SystemExit too, and passed this before `release` existed.
    for name in ("ledger.json", "journal/events.jsonl", "../README.md"):
        with pytest.raises(SystemExit, match="not a diary"):
            keep.main(["release", name])
