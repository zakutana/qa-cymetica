"""The outsider runs with nothing of ours: no bare MEMORY.md marker, no context reaching it, no run in git.

NEXT.md 2026-10-18, from the week's three outside readers, and T-0069's third bullet
(tests/repo/test_outsider_probe_retry.py):

* the probe's leak marker was the bare word 'MEMORY.md'. Claude Code's own memory prompt names that
  file in every session, so a stranger's honest denial ("I haven't been shown any MEMORY.md content",
  2026-10-13 17:02Z) read as a leak, and the one probe that ran was recorded NOT a stranger. What
  only our context could say is still a marker: our memory index's first entry, and the folder our
  repository and our memory folder are named after;
* the stranger is a `claude -p` started in its own folder outside the repository. What decides what
  it is handed is that folder: a CLAUDE.md in it or above it, the user's ~/.claude/CLAUDE.md, and the
  memory index Claude Code keeps for that folder -- and the environment it inherits from a session of
  ours, which names our repository (CLAUDE_PROJECT_DIR, QA_REPO_ROOT). Each is checked before the
  process starts; a folder that would hand it any of ours is refused, never run;
* its run output (state/outsider/run-*.json) was neither committed nor ignored, so every look left
  the tree dirty and no level-V run could start after it.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _script():
    spec = importlib.util.spec_from_file_location("outsider_alone", REPO / "scripts" / "outsider.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_markers_are_what_only_our_context_could_say():
    mod = _script()
    assert "MEMORY.md" not in mod.LEAKS, mod.LEAKS
    for ours in ("The first line reads: Operating rules for qa-cymetica",
                 "My memory index begins: Verify a workflow is live before building for it",
                 r"I can see C:\Users\adamz\Documents\Projects\cymetica-qa-agent\qa-cymetica"):
        ok, why = mod.independent(ours, 0)
        assert not ok and "context of ours" in why, (ours, why)


@pytest.fixture
def short_tmp():
    """pytest's tmp_path is long, and the memory folder's name repeats the whole path: the index
    alone passed Windows' 260 characters."""
    base = Path(tempfile.mkdtemp(prefix="o"))
    yield base
    shutil.rmtree(base, ignore_errors=True)


def _home(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A home with the stranger's folder in it, and a repository elsewhere."""
    home, repo = tmp_path / "h", tmp_path / "r"
    folder = home / "L" / "o"
    folder.mkdir(parents=True)
    repo.mkdir(parents=True)
    (repo / "CLAUDE.md").write_text("# Operating rules for qa-cymetica\n", encoding="utf-8")
    return home, repo, folder


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_folder_that_would_hand_it_any_of_ours_is_refused(short_tmp):
    mod = _script()
    home, repo, folder = _home(short_tmp)
    assert mod.foreign(folder, repo=repo, home=home) is None, "control: a clean folder runs"

    inside = repo / "outsider"
    inside.mkdir()
    assert "inside the repository" in (mod.foreign(inside, repo=repo, home=home) or "")

    above = home / "L" / "CLAUDE.md"
    above.write_text("anything\n", encoding="utf-8")
    assert "CLAUDE.md" in (mod.foreign(folder, repo=repo, home=home) or "")
    above.unlink()

    user = home / ".claude" / "CLAUDE.md"
    user.parent.mkdir(parents=True)
    user.write_text("anything\n", encoding="utf-8")
    assert "CLAUDE.md" in (mod.foreign(folder, repo=repo, home=home) or "")
    user.unlink()

    # The memory index Claude Code loads for that folder: the stranger's own notes are its own,
    # an index carrying ours is a leak handed to it.
    index = (home / ".claude" / "projects" / mod.slug(folder) / "memory" / "MEMORY.md")
    index.parent.mkdir(parents=True)
    index.write_text("- [Its own](own.md) -- what it learned of their docs\n", encoding="utf-8")
    assert mod.foreign(folder, repo=repo, home=home) is None, "its own memory is its own"
    index.write_text("- [Verify a workflow is live before building for it](v.md)\n",
                     encoding="utf-8")
    assert "MEMORY.md" in (mod.foreign(folder, repo=repo, home=home) or "")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stranger_inherits_no_path_into_the_repository(short_tmp, monkeypatch):
    mod = _script()
    home, repo, folder = _home(short_tmp)
    monkeypatch.setattr(mod, "REPO_ROOT", repo)
    monkeypatch.setattr(mod, "home", lambda: folder)
    monkeypatch.setattr(mod, "claude_exe", lambda: "claude.exe")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    monkeypatch.setenv("QA_REPO_ROOT", str(repo).replace("\\", "/"))
    monkeypatch.setenv("PATH", f"{repo / '.venv' / 'Scripts'};C:\\Windows\\system32")
    seen = {}

    class Done:
        stdout, stderr, returncode = "fine", "", 0

    def run(args, **kwargs):
        seen.update(kwargs, args=args)
        return Done()

    monkeypatch.setattr(subprocess, "run", run)
    assert mod._claude("begin", None, "", 10) == ("fine", 0)
    assert Path(seen["cwd"]) == folder
    named = sorted(k for k, v in seen["env"].items()
                   if str(repo).lower().replace("\\", "/")
                   in str(v).lower().replace("\\", "/"))
    assert named == [], f"the stranger's environment names our repository: {named}"
    assert "system32" in seen["env"]["PATH"], "PATH lost more than the repository's entries"

    # A folder that would hand it our context is never started.
    (folder / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    seen.clear()
    output, code = mod._claude("begin", None, "", 10)
    assert code != 0 and "CLAUDE.md" in output and not seen, (output, code)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_outsiders_run_output_is_outside_git():
    ignored = subprocess.run(["git", "check-ignore", "-q", "--no-index",
                              "state/outsider/run-2026-10-25T000000+0000.json"],
                             cwd=REPO).returncode == 0
    assert ignored, "state/outsider/ is not gitignored"
    tracked = subprocess.run(["git", "ls-files", "state/outsider"], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
    assert not tracked, tracked
