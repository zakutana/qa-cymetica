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


def _git_files(*args: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", *args, "state"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return [name for name in out.split("\0") if name]


def _place(names: list[str], into: Path) -> None:
    """Hard links where the volume allows it -- 80 MB of tracked state is
    copied twice otherwise -- and a copy where it does not."""
    import os
    import shutil

    for name in names:
        if name.endswith((".lock", ".tmp")):
            continue
        source, target = REPO / name, into / Path(name).relative_to("state")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_committed_console_hashes_nothing_git_does_not_hold(tmp_path,
                                                                 monkeypatch):
    """D2 of the 2026-09-23 review: the page's hash covered the Nexus diary
    and the memecoin diary, both gitignored, so the committed page was a
    render of files no commit carries and a fresh clone could not reproduce
    it -- rule 12 red on a clone and green here. Since V4 those figures are on
    /lab, which is never committed.

    Held the only way that means anything: the same render over the state git
    tracks, then over that state plus every gitignored file this machine
    really has under state/ -- the diaries, the untracked run records, the
    lab's report. The hash must not move."""
    bare, full = tmp_path / "bare", tmp_path / "full"
    tracked = _git_files()
    _place(tracked, bare)
    _place(tracked, full)
    ignored = _git_files("--others", "--ignored", "--exclude-standard")
    _place(ignored, full)
    assert any(n.endswith("nexus.jsonl") for n in ignored) or not (
        REPO / "state" / "nexus.jsonl").exists(), "the ignored set was not read"

    def digest(state: Path) -> str:
        monkeypatch.setenv("QA_STATE_DIR", str(state))
        spec = importlib.util.spec_from_file_location(
            "render_d2", REPO / "scripts" / "render.py")
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)
        return render.payload_hash(render.build_payload())

    assert digest(bare) == digest(full), (
        "a gitignored file under state/ moved the committed console's hash, "
        "so the committed page is a render of something no commit carries")


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
