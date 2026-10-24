"""Two writers of the evidence manifest at once lose nothing (the week of 2026-10-18).

`audits/evidence-manifest.jsonl` has more than one writer: the pre-commit hook's `keep.py
track` and every fold (`keepset.track` -> `manifest.refresh`) append what is newly cited, and
`keep.py archive` stamps what a bundle holds. Each is a read, a merge and a write of the whole
file, and nothing serialised them but the operator running one command at a time -- which
the company ended: five departments commit, fold and run the hook side by side. Two at once
can each read the same file, merge their own lines and write, and the second write drops the
first's lines. The archive's window is the widest: it read the manifest before building the
bundle (minutes) and wrote its stamps over what it had read, so a line `track` added
meanwhile was gone. The manifest only accumulates because an archived capture's call key can
never be recomputed (qa/manifest.py), so a lost line is proof lost.

One helper, `manifest.update`, takes the manifest's own lock, re-reads the file as it is now,
applies the change and writes it back -- and every writer goes through it. On Windows a
replace is refused while another process holds the file open (memory "adding a writer
changes every other writer"), so the writers here run as real processes beside a reader that
keeps opening it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

from qa import archive, evidence, keepset, manifest
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
# Before the lock, two writers of 40 lines each kept 6 of 80; 25 each is plenty to see it.
PER_WRITER = 25

WRITER = """\
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from qa import manifest
path, root, start = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
ids = Path(sys.argv[5]).read_text(encoding="utf-8").split()
while not start.exists():
    time.sleep(0.002)
for evidence_id in ids:
    manifest.refresh({evidence_id: "row"}, root=root, path=path)
"""

READER = """\
import sys, time
from pathlib import Path
path, stop = Path(sys.argv[1]), Path(sys.argv[2])
while not stop.exists():
    try:
        with open(path, "rb") as handle:
            handle.read()
            time.sleep(0.002)
    except OSError:
        pass
    time.sleep(0.004)
"""


def _ids(tag: str, count: int) -> list[str]:
    return [hashlib.sha256(f"{tag}-{n}".encode()).hexdigest() for n in range(count)]


def _bodies(root: Path, ids: list[str]) -> None:
    for evidence_id in ids:
        target = keepset.evidence_path(evidence_id, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"request": {"method": "GET", "url": "/x"}}),
                          encoding="utf-8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_writers_at_once_lose_nothing(tmp_path, monkeypatch):
    """Two processes refresh one manifest 25 times each while a third keeps opening it, which
    on Windows refuses their replaces (about five refusals a write, measured)."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    root = tmp_path / "evidence"
    path = tmp_path / "audits" / "evidence-manifest.jsonl"
    start, stop = tmp_path / "start", tmp_path / "stop"
    (tmp_path / "writer.py").write_text(WRITER, encoding="utf-8")
    (tmp_path / "reader.py").write_text(READER, encoding="utf-8")
    manifest.write({}, path=path)

    wanted: set[str] = set()
    writers = []
    for tag in ("hook", "fold"):
        ids = _ids(tag, PER_WRITER)
        wanted |= set(ids)
        _bodies(root, ids)
        listing = tmp_path / f"{tag}.txt"
        listing.write_text("\n".join(ids), encoding="utf-8")
        writers.append(subprocess.Popen(
            [sys.executable, str(tmp_path / "writer.py"), str(REPO), str(path), str(root),
             str(start), str(listing)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True))
    reader = subprocess.Popen([sys.executable, str(tmp_path / "reader.py"), str(path),
                               str(stop)])
    time.sleep(1.0)            # both writers imported and waiting at the line
    start.write_text("go", encoding="utf-8")
    try:
        results = [writer.communicate(timeout=300) + (writer.returncode,)
                   for writer in writers]
    finally:
        stop.write_text("stop", encoding="utf-8")
        for process in (*writers, reader):
            if process.poll() is None:
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    process.kill()

    for out, err, code in results:
        assert code == 0, f"a writer failed: {err.strip()[-600:]}"
    held = set(manifest.read(path=path))
    lost = wanted - held
    assert not lost, (f"{len(lost)} of {len(wanted)} lines were lost by two writers at once; "
                      f"each read the file, merged its own line and wrote over the other's")
    leftovers = sorted(p.name for p in path.parent.iterdir() if p.name.endswith(".tmp"))
    assert not leftovers, f"a writer left its temporary file behind: {leftovers}"


def _keep():
    spec = importlib.util.spec_from_file_location("manifest_lock_keep",
                                                  REPO / "scripts" / "keep.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture(n: int) -> str:
    """Stored as `qa.evidence.EvidenceStore.write` stores one, so the bundle verifies."""
    record = {"n": n, "captured_at": "2026-10-18T10:00:00+00:00", "run_id": "run-x",
              "nodeid": "tests/x.py::test_y"}
    evidence_id = evidence.content_id(record)
    target = keepset.evidence_path(evidence_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return evidence_id


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_archive_stamp_keeps_what_track_wrote_while_it_built(tmp_path, monkeypatch, capsys):
    """The widest window: `keep.py archive` reads the manifest, builds the bundle for minutes,
    then stamps. A line `track` added in between must still be there after the stamp."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    bundled = [_capture(n) for n in range(3)]
    manifest.refresh({evidence_id: "row" for evidence_id in bundled})
    late = _capture(99)
    real_build = archive.build

    def build(*args, **kwargs):
        # The pre-commit hook of a commit made while the bundle is being built.
        manifest.refresh({late: "promised"})
        return real_build(*args, **kwargs)

    monkeypatch.setattr(archive, "build", build)
    assert _keep()._archive("2026-10", release=False) == 0, capsys.readouterr().out

    known = manifest.read()
    assert late in known, "the archive's stamp wrote over a line track added while it built"
    for evidence_id in bundled:
        assert known[evidence_id]["archive"] == "evidence-2026-10", known[evidence_id]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lock_and_a_writers_temporary_file_stay_out_of_git():
    """Beside the manifest, untracked, either would make every tree dirty and every
    preregistration refuse it -- the reason state/*.lock and state/*.tmp are ignored."""
    for name in ("audits/evidence-manifest.jsonl.lock",
                 "audits/evidence-manifest.jsonl.1234.tmp"):
        ignored = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", name])
        assert ignored.returncode == 0, f"{name} is not ignored"
