"""A commit of named paths carries those paths, not the evidence manifest (T-0034).

`scripts/commit.py` promises `git commit -- PATH` takes only PATH, whatever else is staged.
`.githooks/pre-commit` runs `keep.py track`, which ends in `git add -f
audits/evidence-manifest.jsonl` (qa/keepset.py). Inside a `git commit -- PATH` that add lands
in git's TEMPORARY index -- the one the commit is built from -- so the manifest rode into a
commit that never named it: desk 3280994c named docs/lab-desk.md and carried +971 manifest
lines other departments' state cites, and the real index was left holding the file two lines
behind HEAD (status MM). Whoever commits next then owns the others' proof lines in the week's
reading (the Crew: trailer).

Two halves, because the first alone leaves a dirty tree prereg refuses:

  * `track` writes the manifest but does not add it when the hook is running for a commit
    whose index is not the real one;
  * `commit.py` commits the manifest on its own right after, the way it does the page.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

from qa import keepset
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST = "audits/evidence-manifest.jsonl"


def _git(root: Path, *args: str, env: dict | None = None) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True, env=env).stdout


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"commit_manifest_{name}",
                                                  REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _track_adds(monkeypatch, tmp_path: Path, index_file: str | None) -> list[list[str]]:
    """Run `keepset.track` with everything but the `git add` stubbed; return the git calls."""
    from qa import manifest

    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(keepset, "must_keep", lambda: {"x": "y"})
    monkeypatch.setattr(keepset, "tracked_evidence", lambda: set())
    monkeypatch.setattr(manifest, "refresh", lambda keep: (1, 1))
    monkeypatch.setattr(manifest, "manifest_path", lambda: keepset.REPO_ROOT / MANIFEST)
    monkeypatch.setattr(keepset.subprocess, "run", fake_run)
    if index_file is None:
        monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    else:
        monkeypatch.setenv("GIT_INDEX_FILE", index_file)
    keepset.track(quiet=True)
    return [c for c in calls if c[:2] == ["git", "add"]]


@pytest.mark.xfail(strict=True, reason="T-0034: the fix is in qa/keepset.py (_in_a_named_commit "
                   "before the git add), which a worker cannot write; drop the mark with it")
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_track_adds_the_manifest_to_the_real_index_only(monkeypatch, tmp_path):
    """Held-out half of the incident: a hook that runs for `git commit -- PATH` sees
    GIT_INDEX_FILE pointing at a temporary index, and an add there is a commit of the file."""
    real = keepset.REPO_ROOT / ".git" / "index"
    assert _track_adds(monkeypatch, tmp_path, None), "an ordinary run adds the manifest"
    assert _track_adds(monkeypatch, tmp_path, str(real)), "a full commit's index is the real one"
    temporary = str(keepset.REPO_ROOT / ".git" / "next-index-12345.lock")
    assert not _track_adds(monkeypatch, tmp_path, temporary), (
        "a commit of named paths builds its tree from a temporary index; an add there puts the "
        "manifest into a commit that never named it (desk 3280994c, +971 lines)")


@pytest.mark.xfail(strict=True, reason="T-0034: the fix is a manifest follow-up commit in "
                   "scripts/commit.py beside _commit_the_page, which a worker cannot write")
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_named_commit_leaves_the_manifest_to_its_own_commit(tmp_path, monkeypatch):
    """The path the incident took, end to end in a scratch repository: a hook that leaves the
    manifest changed and unstaged (what `track` now does) must not leave the tree dirty."""
    root = tmp_path / "repo"
    (root / "audits").mkdir(parents=True)
    (root / ".hk").mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.hooksPath", ".hk")
    (root / ".hk" / "pre-commit").write_text(
        "#!/bin/sh\necho more >> audits/evidence-manifest.jsonl\nexit 0\n", encoding="utf-8",
        newline="\n")
    (root / "desk.md").write_text("one\n", encoding="utf-8")
    (root / MANIFEST).write_text("a\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "--no-verify", "-m", "start")
    (root / "desk.md").write_text("two\n", encoding="utf-8")

    commit = _script("commit")
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(root))
    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    monkeypatch.setenv("QA_CREW_TICKET", "T-0034")
    monkeypatch.setattr(commit, "pass_in_flight", lambda: False)
    assert commit.main(["-m", "Desk: a note", "--", "desk.md"]) == 0

    named = _git(root, "show", "--name-only", "--format=", "HEAD~1").split()
    assert named == ["desk.md"], f"the named commit carried more: {named}"
    assert _git(root, "show", "--name-only", "--format=", "HEAD").split() == [MANIFEST]
    assert _git(root, "status", "--porcelain").strip() == "", "a dirty tree nobody owns"
    assert "Crew: desk T-0034" in _git(root, "log", "-1", "--format=%B", "HEAD~1")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_still_tracks_the_manifest():
    """Nothing here switched the hook off: it still runs `keep.py track`."""
    text = (REPO / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "scripts/keep.py track" in text
