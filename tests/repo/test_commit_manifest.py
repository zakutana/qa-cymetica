"""A commit of named paths carries those paths, not the manifest or the page (T-0034, T-0038).

`scripts/commit.py` promises `git commit -- PATH` takes only PATH, whatever else is staged.
`.githooks/pre-commit` runs `keep.py track`, which ends in `git add -f
audits/evidence-manifest.jsonl` (qa/keepset.py), and renders the page and adds
`dashboard/index.html`. Inside a `git commit -- PATH` those adds land in git's TEMPORARY index
-- the one the commit is built from -- so both rode into commits that never named them: desk
3280994c named docs/lab-desk.md and carried +971 manifest lines other departments' state
cites; 880617f5, 2936e9b6, fbed09a5 and 65d4299b carried the page within nine minutes. The real
index was left holding the manifest lines behind HEAD (status MM), and `_commit_the_page`,
which looked only at what was staged, never committed anything (0 "render" commits since
2026-10-11).

The trigger is commit.py's own marker in the environment of every git call it makes
(`qa.keepset.COMMIT_PY_MARKER`), the manager's spec in OP-0016. Not GIT_INDEX_FILE: `git
rev-parse --git-path index` returns exactly $GIT_INDEX_FILE, so a comparison never fires, and a
session's own `git commit -- PATH` needs the manifest to travel with its state. Not
QA_CREW_DEPT: `console poll` and a manual run go without it.

  * with the marker, `track` writes the manifest but does not add it, and the hook renders the
    page but does not add it;
  * commit.py then commits each on its own -- "manifest", then "render" only when state/ is
    clean -- adding first, so the MM state a bare `git commit -- PATH` cannot fix ends clean;
  * without the marker everything is as it was.

The scratch repositories below run the REAL hook (`.githooks/pre-commit`, copied with LF
endings) over two stand-ins for the scripts it calls: `keep.py track` writes what is new and
adds it unless the marker is set (what the first test pins on the real `track`), and
`render.py --if-stale` writes the page when it is stale.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from qa import keepset
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST = "audits/evidence-manifest.jsonl"
PAGE = "dashboard/index.html"
MARKER = "QA_COMMIT_PY"

KEEP_STUB = """\
import os
import subprocess
from pathlib import Path

manifest = Path("audits/evidence-manifest.jsonl")
held = manifest.read_text(encoding="utf-8").split() if manifest.exists() else []
captures = Path(os.environ["STUB_CAPTURES"]).read_text(encoding="utf-8").split()
lines = sorted(set(held) | set(captures))
if lines != held:
    manifest.write_text("".join(line + "\\n" for line in lines), encoding="utf-8",
                        newline="\\n")
if not os.environ.get("%s"):
    subprocess.run(["git", "add", "-f", str(manifest)], check=False)
""" % MARKER

RENDER_STUB = """\
import os
from pathlib import Path

page = Path("dashboard/index.html")
source = Path(os.environ["STUB_PAGE_SOURCE"]).read_text(encoding="utf-8").strip()
want = "render " + source + "\\n"
if not page.exists() or page.read_text(encoding="utf-8") != want:
    page.write_text(want, encoding="utf-8", newline="\\n")
"""


def _git(root: Path, *args: str, env: dict | None = None) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True, env=env).stdout


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"commit_manifest_{name}",
                                                  REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _track_adds(monkeypatch, marker: bool, index_file: str | None) -> tuple[list, int]:
    """Run `keepset.track` with everything but the `git add` stubbed; return the adds and
    how many times the manifest was written."""
    from qa import manifest

    calls: list[list[str]] = []
    written: list[int] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fake_refresh(keep):
        written.append(1)
        return 1, 1

    monkeypatch.setattr(keepset, "must_keep", lambda: {"x": "y"})
    monkeypatch.setattr(keepset, "tracked_evidence", lambda: set())
    monkeypatch.setattr(manifest, "refresh", fake_refresh)
    monkeypatch.setattr(manifest, "manifest_path", lambda: keepset.REPO_ROOT / MANIFEST)
    monkeypatch.setattr(keepset.subprocess, "run", fake_run)
    if marker:
        monkeypatch.setenv(MARKER, "1")
    else:
        monkeypatch.delenv(MARKER, raising=False)
    if index_file is None:
        monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    else:
        monkeypatch.setenv("GIT_INDEX_FILE", index_file)
    keepset.track(quiet=True)
    return [c for c in calls if c[:2] == ["git", "add"]], len(written)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_track_adds_the_manifest_unless_commit_py_runs(monkeypatch):
    """The manifest half of the incident, on the real `track`: commit.py's marker stops the
    add and nothing else does -- the manifest is still written, for commit.py to commit."""
    temporary = str(keepset.REPO_ROOT / ".git" / "next-index-12345.lock")
    adds, written = _track_adds(monkeypatch, False, None)
    assert adds and written == 1, "an ordinary run writes and adds the manifest"
    adds, written = _track_adds(monkeypatch, False, temporary)
    assert adds and written == 1, (
        "a session's own `git commit -- PATH` runs the hook on a temporary index too, and "
        "needs the manifest to travel with its state: GIT_INDEX_FILE is not the trigger")
    adds, written = _track_adds(monkeypatch, True, temporary)
    assert not adds, (
        "under commit.py an add lands in the temporary index of a commit that never named the "
        "manifest (desk 3280994c, +971 lines)")
    assert written == 1, "the marker stops the add, not the write commit.py commits after"
    assert getattr(keepset, "COMMIT_PY_MARKER", None) == MARKER, "one name for the marker"


def _scratch(tmp_path: Path, monkeypatch) -> Path:
    """A repository with the real hook, the two stand-ins, and one commit."""
    root = tmp_path / "repo"
    for folder in ("audits", "dashboard", "scripts", ".hk"):
        (root / folder).mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.hooksPath", ".hk")
    _git(root, "config", "core.autocrlf", "false")
    hook = (REPO / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    (root / ".hk" / "pre-commit").write_text(hook.replace("\r\n", "\n"), encoding="utf-8",
                                              newline="\n")
    (root / "scripts" / "keep.py").write_text(KEEP_STUB, encoding="utf-8", newline="\n")
    (root / "scripts" / "render.py").write_text(RENDER_STUB, encoding="utf-8", newline="\n")
    (tmp_path / "captures.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "page-source.txt").write_text("1\n", encoding="utf-8")
    (root / "desk.md").write_text("one\n", encoding="utf-8")
    (root / MANIFEST).write_text("a\n", encoding="utf-8", newline="\n")
    (root / PAGE).write_text("render 1\n", encoding="utf-8", newline="\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "--no-verify", "-m", "start")

    monkeypatch.setenv("STUB_CAPTURES", str(tmp_path / "captures.txt"))
    monkeypatch.setenv("STUB_PAGE_SOURCE", str(tmp_path / "page-source.txt"))
    # The hook's `python` is the interpreter running this test.
    monkeypatch.setenv("PATH", os.path.dirname(sys.executable) + os.pathsep
                       + os.environ.get("PATH", ""))
    monkeypatch.delenv(MARKER, raising=False)
    monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(root))
    return root


def _something_new(tmp_path: Path) -> None:
    """A capture to prove and a page gone stale: what the hook finds at a desk commit."""
    (tmp_path / "captures.txt").write_text("a\nb\n", encoding="utf-8")
    (tmp_path / "page-source.txt").write_text("2\n", encoding="utf-8")


def _named(root: Path, rev: str) -> list[str]:
    return sorted(_git(root, "show", "--name-only", "--format=", rev).split())


def _env(marker: bool) -> dict:
    env = {key: value for key, value in os.environ.items() if key != MARKER}
    if marker:
        env[MARKER] = "1"
    return env


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_commit_without_the_marker_carries_the_manifest_and_the_page_as_before(
        tmp_path, monkeypatch):
    """A session's own `git commit -- PATH`: the hook brings the manifest and the page with
    it, as it always has. Nothing here changes a commit commit.py did not make."""
    root = _scratch(tmp_path, monkeypatch)
    _something_new(tmp_path)
    (root / "desk.md").write_text("two\n", encoding="utf-8")
    _git(root, "commit", "-q", "-m", "session", "--", "desk.md", env=_env(False))
    assert _named(root, "HEAD") == sorted([MANIFEST, PAGE, "desk.md"]), (
        "the hook did not run, or a commit without the marker lost what it carried")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_with_the_marker_the_hook_leaves_the_page_and_the_manifest_unstaged(
        tmp_path, monkeypatch):
    """The page twin of the first test, on the real hook: with commit.py's marker a named
    commit carries only what it names, and the hook's page waits in the tree."""
    root = _scratch(tmp_path, monkeypatch)
    _something_new(tmp_path)
    (root / "desk.md").write_text("two\n", encoding="utf-8")
    _git(root, "commit", "-q", "-m", "named", "--", "desk.md", env=_env(True))
    assert _named(root, "HEAD") == ["desk.md"], (
        "the page rode into a commit that never named it (880617f5, 2936e9b6, fbed09a5, "
        "65d4299b)")
    status = _git(root, "status", "--porcelain")
    assert f" M {PAGE}" in status and f" M {MANIFEST}" in status, (
        f"the hook should still render and write, for commit.py to commit: {status!r}")


def _commit(monkeypatch, ticket: str = "T-0038"):
    commit = _script("commit")
    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    monkeypatch.setenv("QA_CREW_TICKET", ticket)
    monkeypatch.setattr(commit, "pass_in_flight", lambda: False)
    return commit


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_named_commit_leaves_the_manifest_and_the_page_to_their_own_commits(
        tmp_path, monkeypatch):
    """The path the incident took, end to end: the named commit, then the manifest on its
    own, then the page on its own, and a clean tree."""
    root = _scratch(tmp_path, monkeypatch)
    _something_new(tmp_path)
    (root / "desk.md").write_text("two\n", encoding="utf-8")
    commit = _commit(monkeypatch)
    assert commit.main(["-m", "Desk: a note", "--", "desk.md"]) == 0

    assert _named(root, "HEAD~2") == ["desk.md"], "the named commit carried more"
    assert _named(root, "HEAD~1") == [MANIFEST]
    assert _named(root, "HEAD") == [PAGE]
    subjects = _git(root, "log", "-3", "--format=%s").split("\n")[:3]
    assert subjects == ["render", "manifest", "Desk: a note"], subjects
    assert "b" in _git(root, "show", f"HEAD:{MANIFEST}").split()
    assert _git(root, "show", f"HEAD:{PAGE}") == "render 2\n"
    assert _git(root, "status", "--porcelain").strip() == "", "a dirty tree nobody owns"
    assert "Crew: desk T-0038" in _git(root, "log", "-1", "--format=%B", "HEAD~2")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_named_commit_from_the_mm_state_ends_clean(tmp_path, monkeypatch):
    """Today's state: the index behind HEAD for the manifest and the page, the tree equal to
    HEAD. A bare `git commit -- PATH` cannot fix that -- it ends in "nothing to commit" and
    puts the index back -- so commit.py adds first, and finding nothing to commit is not an
    error."""
    root = _scratch(tmp_path, monkeypatch)
    for name, behind in ((MANIFEST, "older\n"), (PAGE, "render 0\n")):
        now = (root / name).read_text(encoding="utf-8")
        (root / name).write_text(behind, encoding="utf-8", newline="\n")
        _git(root, "add", name)
        (root / name).write_text(now, encoding="utf-8", newline="\n")
    status = _git(root, "status", "--porcelain")
    assert f"MM {MANIFEST}" in status and f"MM {PAGE}" in status, status

    (root / "desk.md").write_text("two\n", encoding="utf-8")
    commit = _commit(monkeypatch)
    assert commit.main(["-m", "Desk: a note", "--", "desk.md"]) == 0
    assert _git(root, "status", "--porcelain").strip() == "", "the MM state outlived a commit"
    assert _git(root, "log", "--format=%s").split("\n")[:2] == ["Desk: a note", "start"], (
        "an index put right needs no commit of its own")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_waits_while_state_is_not_clean(tmp_path, monkeypatch):
    """The page goes in on its own only as a render of committed state: with state/ changed
    and uncommitted it stays in the tree for the commit that brings the state."""
    root = _scratch(tmp_path, monkeypatch)
    (root / "state").mkdir()
    (root / "state" / "ledger.json").write_text("{}\n", encoding="utf-8")
    _git(root, "add", "state/ledger.json")
    _git(root, "commit", "-q", "--no-verify", "-m", "state")
    (root / "state" / "ledger.json").write_text('{"folded": 1}\n', encoding="utf-8")
    (root / PAGE).write_text("render of the folded ledger\n", encoding="utf-8")
    (root / "desk.md").write_text("two\n", encoding="utf-8")
    commit = _commit(monkeypatch)
    assert commit.main(["-m", "Desk: a note", "--", "desk.md"]) == 0
    assert _named(root, "HEAD") == ["desk.md"]
    assert f" M {PAGE}" in _git(root, "status", "--porcelain")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_still_tracks_the_manifest():
    """Nothing here switched the hook off: it still runs `keep.py track`, and the page's add
    is the only thing it gates on commit.py's marker."""
    text = (REPO / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "scripts/keep.py track" in text
    assert MARKER in text
