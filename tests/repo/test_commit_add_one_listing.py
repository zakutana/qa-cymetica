"""`scripts/commit.py::_add` asks git's index once, not once per path (deep pass 2026-10-25, R07).

It ran `git ls-files --error-unmatch -- PATH` for every path it was handed, to tell the ones the index
already holds (staged with `-f`, the run record a fold put there; OP-0009) from the rest. A fold commit
names three paths and a tidy more; each call is a git process, held under the one commit lock every
department waits on. One `git ls-files -z -- PATH...` answers the same question for all of them. The
behaviour it decides stays in tests/repo/test_commit_run_record.py; this holds the count, and the paths
git would quote (non-ASCII) or that arrive spelled differently from how the index lists them.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
RECORD = "state/runs/run-20261025T000000Z-00000000.json"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def _repo(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    (root / "state" / "runs").mkdir(parents=True)
    (root / "docs").mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.autocrlf", "false")
    (root / ".gitignore").write_text("state/runs/\n", encoding="utf-8")
    for name in ("a.txt", "docs/laboratoř.md"):
        (root / name).write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "start")
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(root))
    return root


def _commit():
    spec = importlib.util.spec_from_file_location("commit_one_listing", REPO / "scripts" / "commit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_add_lists_the_index_once_for_every_path(tmp_path, monkeypatch):
    root = _repo(tmp_path, monkeypatch)
    for name in ("a.txt", "docs/laboratoř.md"):
        (root / name).write_text("two\n", encoding="utf-8")
    (root / "new.txt").write_text("new\n", encoding="utf-8")
    (root / RECORD).write_text("{}\n", encoding="utf-8")
    _git(root, "add", "-f", RECORD)

    commit = _commit()
    real, calls = commit._git, []

    def counted(base, *args):
        calls.append(args)
        return real(base, *args)

    monkeypatch.setattr(commit, "_git", counted)
    paths = ["./a.txt", "docs/laboratoř.md", "new.txt", RECORD]
    assert commit._add(root.resolve(), paths) is None
    listings = [args for args in calls if args and args[0] == "ls-files"]
    assert len(listings) == 1, f"{len(listings)} ls-files calls for {len(paths)} paths: {listings}"

    staged = set(_git(root, "diff", "--cached", "--name-only", "-z").split("\0")) - {""}
    assert staged == {"a.txt", "docs/laboratoř.md", "new.txt", RECORD}, staged
    # The held ones went in with -f and the rest without: an ignored path nothing staged
    # is still refused (test_commit_run_record.py), so `new.txt` must not have ridden on -f.
    forced = [args for args in calls if args[:2] == ("add", "-f")]
    assert forced and "new.txt" not in forced[0], forced
