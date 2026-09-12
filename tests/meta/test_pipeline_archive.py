"""The archive: verified before anything is let go of.

D2 of docs/data-plan.md. 167 MB of capture bodies leave git for a monthly
bundle, and the ordering is the whole safety property: **hash every member back
out of the written archive, and only then release the originals.** Reversed, a
truncated write would take the evidence with it, and the vendor was told these
are "provided on request".

`.tar.xz` rather than the plan's `.tar.zst`: lzma is in the standard library and
gave the same ratio on a sample of this store (9:1), and an archive that opens
without a third-party package is one that still opens when somebody finally
asks for it.

The verification reads the file back from DISK and hashes the CONTENT against
the member's own name. Evidence is content-addressed, so that comparison is the
integrity proof -- checking the tar against the same bytes we just held in
memory would only prove that memory is consistent with itself.
"""

from __future__ import annotations

import io
import json
import lzma
import tarfile
from pathlib import Path

from qa import archive, evidence, keepset, manifest
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _store(tmp_path: Path) -> Path:
    return tmp_path / "evidence"


def _capture(tmp_path: Path, body: dict) -> str:
    """Stored exactly as `qa.evidence.EvidenceStore.write` stores one.

    Indented, keeping the volatile fields, and named by `content_id` -- which
    is taken over the record WITHOUT them. An earlier draft of this fixture
    wrote the file and hashed those same bytes, so it agreed with a verifier
    that was wrong in the same direction and the pair went green. Against the
    real store every one of 1 178 captures came out corrupt.
    """
    record = dict(body, captured_at="2026-09-12T10:00:00+00:00",
                  run_id="run-x", nodeid="tests/x.py::test_y")
    evidence_id = evidence.content_id(record)
    path = keepset.evidence_path(evidence_id, _store(tmp_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True,
                               ensure_ascii=False), encoding="utf-8")
    return evidence_id


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_what_is_not_yet_archived_is_pending():
    """Pure, so the decision about what to move can be read without a disk."""
    known = {
        "a" * 64: {"id": "a" * 64, "archive": ""},
        "b" * 64: {"id": "b" * 64, "archive": "evidence-2026-08"},
        "c" * 64: {"id": "c" * 64},
    }
    assert archive.pending(known) == ["a" * 64, "c" * 64], (
        "a capture already in an archive would be bundled twice")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_written_archive_verifies_against_the_names_of_its_members(
        tmp_path, monkeypatch):
    """The round trip, read back off disk."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    ids = [_capture(tmp_path, {"n": n}) for n in range(4)]
    target = tmp_path / "archive" / "evidence-2026-09.tar.xz"

    written, missing = archive.build(ids, target, root=_store(tmp_path))
    assert written == 4 and missing == [], (written, missing)
    assert archive.commit(target, releasable=True) is True

    good, bad = archive.verify(target, set(ids))
    assert sorted(good) == sorted(ids), "a member the archive holds did not verify"
    assert bad == [], bad


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_member_whose_content_moved_is_caught_and_nothing_is_released(
        tmp_path, monkeypatch):
    """The negative control, and it never touches the release path.

    A test that proved this by letting the release run would be the defect it
    exists to stop -- the same shape as mutation-testing a guard by performing
    the withdrawal it refuses.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    ids = [_capture(tmp_path, {"n": n}) for n in range(3)]
    target = tmp_path / "archive" / "evidence-2026-09.tar.xz"
    archive.build(ids, target, root=_store(tmp_path))
    archive.commit(target, releasable=True)

    def _respun(mutate) -> Path:
        with tarfile.open(target, "r:xz") as src:
            members = [(m, src.extractfile(m).read()) for m in src.getmembers()]
        out_path = tmp_path / "archive" / f"spoiled-{mutate.__name__}.tar.xz"
        with tarfile.open(out_path, "w:xz") as out:
            for member, data in members:
                if member.name.endswith(ids[1] + ".json"):
                    data = mutate(data)
                    member.size = len(data)
                out.addfile(member, io.BytesIO(data))
        return out_path

    def whitespace(data: bytes) -> bytes:
        return data + b"\n  "

    def content(data: bytes) -> bytes:
        record = json.loads(data)
        record["n"] = 999
        return json.dumps(record, indent=2, sort_keys=True).encode("utf-8")

    # Formatting is NOT content. The id is taken over the parsed record, so a
    # re-indented or whitespace-padded body is the same evidence and must not
    # be condemned -- otherwise every reformat would look like tampering.
    good, bad = archive.verify(_respun(whitespace), set(ids))
    assert bad == [], f"a whitespace change was read as corruption: {bad}"
    assert archive.releasable(good, bad) is True

    # A changed VALUE is caught.
    good, bad = archive.verify(_respun(content), set(ids))
    assert bad == [ids[1]], f"the altered member was not caught: {bad}"
    assert ids[1] not in good
    assert sorted(good) == sorted([ids[0], ids[2]])
    assert archive.releasable(good, bad) is False, (
        "a bundle with one bad member must not release ANY original -- the "
        "archive is one artefact and a partial trust in it is no trust")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_body_that_is_not_on_disk_is_reported_not_skipped(
        tmp_path, monkeypatch):
    """Otherwise we would bundle 900 of 1 178 and believe we had them all."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    here = _capture(tmp_path, {"n": 1})
    gone = "f" * 64
    target = tmp_path / "archive" / "evidence-2026-09.tar.xz"

    written, missing = archive.build([here, gone], target, root=_store(tmp_path))
    archive.commit(target, releasable=True)

    assert written == 1 and missing == [gone], (written, missing)
    good, bad = archive.verify(target, {here, gone})
    assert good == [here] and bad == [], (good, bad)
    assert archive.releasable(good, bad) is True, (
        "a body that was already gone is not a corrupt archive; it is simply "
        "not in it, and the caller is told which")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_archive_lands_beside_the_state_it_came_from(tmp_path, monkeypatch):
    """The trap keep.snapshot_dir and the manifest both had to learn."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    target = archive.archive_path("2026-09")

    assert target == tmp_path / "archive" / "evidence-2026-09.tar.xz", target
    assert Path(__file__).resolve().parent.parent.parent not in target.parents


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_month_must_look_like_a_month(tmp_path, monkeypatch):
    """A stray argument would name an archive nothing ever finds again."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    for bad in ("2026", "september", "2026-13", "../etc", ""):
        try:
            archive.archive_path(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} was accepted as a month")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_bundle_is_actually_compressed(tmp_path, monkeypatch):
    """Nine to one on this store, measured. A bundle the size of its input
    means the compressor silently did nothing."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    ids = [_capture(tmp_path, {"n": n, "pad": "x" * 4000}) for n in range(12)]
    target = tmp_path / "archive" / "evidence-2026-09.tar.xz"
    archive.build(ids, target, root=_store(tmp_path))
    archive.commit(target, releasable=True)

    raw = sum(keepset.evidence_path(i, _store(tmp_path)).stat().st_size
              for i in ids)
    assert target.stat().st_size < raw / 2, (target.stat().st_size, raw)
    with lzma.open(target) as handle:
        assert handle.read(1), "the archive is empty"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_second_run_in_the_same_month_keeps_what_the_first_one_bundled(
        tmp_path, monkeypatch):
    """The loss path all three independent reviewers reproduced on 2026-09-12.

    `tarfile` truncates and xz cannot append, while `pending()` returns only
    rows with no stamp. So a second run in the same month rewrote the bundle
    from the newly pending ids alone, over the top of one holding 1 178 -- and
    the manifest went on stamping the lost ones as archived. Nothing could see
    it: the guard read the stamp, which the archive writes to itself.

    It is a loss path rather than a lost backup because `must_keep` can shrink
    (115 captures lost their citation the same day, when the ledger folded onto
    a new run) and `prune_runs` then deletes a body the archive was the only
    remaining copy of.

    Driven through the CLI, because the defect is in what the caller ASKS for:
    `build` writes what it is given, and it was being given only the new ids.
    """
    # The CLI resolves captures through `evidence_root()`, which is
    # QA_STATE_DIR/"evidence" -- so the fixture writes where the code will look
    # rather than where an explicit `root=` would have put them.
    state = tmp_path / "state"
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    import importlib
    import importlib.util

    import qa.state
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "keep_under_test", REPO / "scripts" / "keep.py")
    keep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(keep)

    first = [_capture(state, {"n": n}) for n in range(3)]
    manifest.write({i: {"id": i, "bytes": 1, "call": "GET /x", "why": "row",
                        "archive": ""} for i in first})
    assert keep.main(["archive", "--month", "2026-09"]) == 0

    target = archive.archive_path("2026-09")
    assert sorted(archive.members(target)) == sorted(first)

    second = [_capture(state, {"n": n}) for n in range(10, 12)]
    known = manifest.read()
    known.update({i: {"id": i, "bytes": 1, "call": "GET /y", "why": "row",
                      "archive": ""} for i in second})
    manifest.write(known)
    assert keep.main(["archive", "--month", "2026-09"]) == 0

    held = archive.members(target)
    assert sorted(held) == sorted(first + second), (
        f"the second run lost {sorted(set(first) - held)} from the bundle")
    good, bad = archive.verify(target, set(first + second))
    assert bad == [] and sorted(good) == sorted(first + second)
    assert not archive.staged(target).exists(), "a staged bundle was left behind"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_body_gone_from_disk_is_carried_out_of_the_old_bundle(
        tmp_path, monkeypatch):
    """The archive is the only copy once the pruner has been past.

    Rebuilding from disk alone would drop exactly the captures the archive
    exists for -- the old ones.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    old = _capture(tmp_path, {"n": "old"})
    target = tmp_path / "archive" / "evidence-2026-09.tar.xz"
    archive.build([old], target, root=_store(tmp_path))
    archive.commit(target, releasable=True)
    keepset.evidence_path(old, _store(tmp_path)).unlink()

    fresh = _capture(tmp_path, {"n": "fresh"})
    written, missing = archive.build([old, fresh], target,
                                     root=_store(tmp_path), carry=target)
    archive.commit(target, releasable=True)

    assert missing == [], f"a body the old bundle holds was reported missing: {missing}"
    assert written == 2
    good, bad = archive.verify(target, {old, fresh})
    assert sorted(good) == sorted([old, fresh]) and bad == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bundle_that_fails_to_verify_never_replaces_the_good_one(
        tmp_path, monkeypatch):
    """Write beside it, verify, then move. The order is the whole property.

    A truncated or mangled write must cost nothing: the bundle that was already
    there is the one the vendor's "provided on request" rests on.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    ids = [_capture(tmp_path, {"n": n}) for n in range(3)]
    target = tmp_path / "archive" / "evidence-2026-09.tar.xz"
    archive.build(ids, target, root=_store(tmp_path))
    archive.commit(target, releasable=True)
    before = target.read_bytes()

    # A body whose content no longer hashes to its name: the store was
    # corrupted under us between one run and the next.
    spoiled = keepset.evidence_path(ids[1], _store(tmp_path))
    spoiled.write_text(json.dumps({"n": "tampered"}), encoding="utf-8")

    written, missing = archive.build(ids, target, root=_store(tmp_path),
                                     carry=target)
    good, bad = archive.verify(archive.staged(target), set(ids))
    assert bad == [ids[1]], bad
    assert archive.commit(target, releasable=archive.releasable(good, bad)) is False

    assert target.read_bytes() == before, (
        "a bundle that did not verify replaced the one that did")
