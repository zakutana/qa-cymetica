"""The company can commit the run record its fold staged (OP-0009, T-0029).

A company sweep failed three times (T-0002) on a leftover nobody could clear: `ledger.py
--run` stages `state/runs/<id>.json` with `git add -f`, because the folder is gitignored and
a record becomes evidence only when a fold stands on it; scripts/commit.py then ran a plain
`git add -- PATH`, which git refuses for a path under an ignored folder EVEN WHEN the index
already holds it, and a worker has no other way into git. So the record stayed staged, the
tree stayed dirty, and level V stayed out of reach (run-20261012T170213Z-a898f46d waited for a
session).

The manager's spec, as decided: commit.py can commit the run record the fold staged; `tidy`
counts it as housekeeping; the Bugs department names it in its fold commit; the laboratory
commits its own lesson. What stays refused is the reason the folder is ignored: a record
nothing staged -- a debug run's -- is not committed by naming it.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
RECORD = "state/runs/run-20261012T170213Z-a898f46d.json"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"run_record_{name}",
                                                  REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repo(tmp_path: Path, monkeypatch) -> Path:
    """A tree shaped like ours where it matters: state/runs/ ignored, a ledger, a journal."""
    root = tmp_path / "repo"
    (root / "state" / "runs").mkdir(parents=True)
    (root / "state" / "journal").mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.autocrlf", "false")
    (root / ".gitignore").write_text("state/runs/\nevidence/\n", encoding="utf-8")
    (root / "state" / "ledger.json").write_text("{}\n", encoding="utf-8")
    (root / "state" / "journal" / "events.jsonl").write_text("", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "start")
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(root))
    monkeypatch.setenv("QA_CREW_DEPT", "bugs")
    monkeypatch.setenv("QA_CREW_TICKET", "T-0002")
    return root


def _fold(root: Path) -> None:
    """What `ledger.py --run` leaves: the ledger and the journal changed, the record staged."""
    (root / RECORD).write_text('{"run_id": "run-20261012T170213Z-a898f46d"}\n',
                               encoding="utf-8")
    _git(root, "add", "-f", RECORD)
    (root / "state" / "ledger.json").write_text('{"run_id": "run-20261012T170213Z-a898f46d"}\n',
                                                encoding="utf-8")
    with (root / "state" / "journal" / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write('{"type": "fold"}\n')


def _commit(monkeypatch):
    commit = _script("commit")
    monkeypatch.setattr(commit, "pass_in_flight", lambda: False)
    return commit


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_commit_py_commits_the_run_record_the_fold_staged(tmp_path, monkeypatch):
    """Bugs' fold commit, named the way its body now says: the ledger, the journal and the
    record, in one commit, and a clean tree after it."""
    root = _repo(tmp_path, monkeypatch)
    _fold(root)
    commit = _commit(monkeypatch)
    assert commit.main(["-m", "Bugs: fold PRE-0273", "--", "state/ledger.json",
                        "state/journal/events.jsonl", RECORD]) == 0, (
        "commit.py's plain git add refuses a path under an ignored folder even when the "
        "index holds it (T-0029)")
    named = sorted(_git(root, "show", "--name-only", "--format=", "HEAD").split())
    assert named == sorted(["state/ledger.json", "state/journal/events.jsonl", RECORD]), named
    assert _git(root, "status", "--porcelain").strip() == "", "the record stayed staged"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_ignored_path_nothing_staged_is_still_refused(tmp_path, monkeypatch):
    """The other direction, and the reason the folder is ignored: a record no fold stood on,
    or a capture body, is not committed by naming it."""
    root = _repo(tmp_path, monkeypatch)
    (root / "state" / "runs" / "run-debug.json").write_text("{}\n", encoding="utf-8")
    (root / "evidence").mkdir()
    (root / "evidence" / "body.json").write_text("{}\n", encoding="utf-8")
    head = _git(root, "rev-parse", "HEAD")
    commit = _commit(monkeypatch)
    for path in ("state/runs/run-debug.json", "evidence/body.json"):
        assert commit.main(["-m", "x", "--", path]) != 0, path
    assert _git(root, "rev-parse", "HEAD") == head, "an ignored path nobody staged went in"
    assert _git(root, "ls-files", "--", "state/runs", "evidence").strip() == ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_tidy_commits_a_staged_run_record_as_housekeeping(tmp_path, monkeypatch, capsys):
    """Under Bugs' own hold, `crew.py tidy` commits what the pipeline wrote; a record the fold
    staged is the pipeline's, not another department's half-edit (T-0002's third try stopped
    on it)."""
    root = _repo(tmp_path, monkeypatch)
    _fold(root)
    sup = _script("crew")
    monkeypatch.setattr(sup, "fold_and_render", lambda base: None)
    assert sup.housekeeping(RECORD), "a staged run record read as somebody's half-edit"
    crew.set_hold("bugs", "level V of PRE-0300")
    try:
        assert sup.main(["tidy"]) == 0, capsys.readouterr().out
    finally:
        crew.clear_hold()
    assert RECORD in _git(root, "show", "--name-only", "--format=", "HEAD").split()
    assert _git(root, "status", "--porcelain").strip() == ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_bugs_fold_commit_names_the_record_and_the_lab_commits_its_lesson():
    """What a worker is told, since the worker's prompt is the only place it learns it."""
    bugs = crew.BODIES["bugs"]
    fold = bugs[bugs.index("After any change to state"):]
    assert "state/runs/" in fold and "scripts/commit.py" in fold, (
        "the fold commit does not name the run record ledger.py staged")
    assert "audits/evidence-manifest.jsonl" in fold, (
        "under commit.py the hook no longer adds the manifest, so a fold commit that does not "
        "name it cites captures its own manifest does not prove until the next commit")
    lab = crew.BODIES["lab"]
    assert "docs/lab-knowledge.md" in lab and "scripts/commit.py" in lab, (
        "the laboratory is not told to commit its own lesson (T-0025's sat uncommitted and "
        "failed T-0002's sweep on a dirty tree)")
