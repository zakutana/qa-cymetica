"""The manifest: what we held, why, and what it was — after the body is gone.

Git holds 167 MB of capture bodies and grew 47 MB in the eight hours after the
prune of 2026-09-12. The bodies are leaving git for a monthly archive, and the
thing that has to survive that move is the PROOF: evidence is addressed by the
sha256 of its content, so an id plus a size plus the call it answered is enough
to say what we had and that it has not changed.

The whole design rests on one property, and it is the one a careless rewrite
destroys: **`call_key` needs the body.** Once a capture is archived off this
disk the key can never be recomputed, so a refresh that rebuilds the manifest
from what it can currently see would quietly blank the oldest half of it — the
half we most need to prove, since those are the verdicts the vendor was told
are "provided on request".

So the manifest accumulates and a thinner entry never replaces a fuller one.
"""

from __future__ import annotations

import json
from pathlib import Path

from qa import keepset, manifest
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _store(tmp_path: Path) -> Path:
    return tmp_path / "evidence"


def _capture(tmp_path: Path, evidence_id: str, record: dict) -> Path:
    """Placed through the same reader the code uses, so the fixture cannot
    invent a layout of its own -- captures are sharded
    `sha256/<first two>/<hash>.json` and an earlier draft of this file guessed
    otherwise."""
    path = keepset.evidence_path(evidence_id, _store(tmp_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _record(path="/api/v1/event-cards", method="GET"):
    return {"request": {"method": method, "url": f"https://x.test{path}"},
            "response": {"status": 200, "body": {"ok": True}}}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_entry_says_what_the_capture_was_while_the_body_is_still_here(
        tmp_path, monkeypatch):
    """Id, size, the call it answered, and why we are keeping it."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    body = _capture(tmp_path, "a" * 64, _record())

    entry = manifest.entry("a" * 64, "promised", root=_store(tmp_path))

    assert entry["id"] == "a" * 64
    assert entry["bytes"] == body.stat().st_size
    assert entry["why"] == "promised"
    assert entry["call"], "an entry with no call key cannot prove what it was"
    assert entry["archive"] == "", "nothing is archived until D2 puts it there"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_body_that_is_gone_keeps_its_entry_rather_than_losing_it():
    """The property the whole manifest exists for.

    `call_key` reads the body. After the archive takes it, a refresh can no
    longer compute the key -- so if merging preferred what it can see now, the
    manifest would forget precisely the oldest captures, which are the ones
    whose bodies are gone and whose proof therefore matters most.
    """
    known = {"a" * 64: {"id": "a" * 64, "bytes": 1234, "call": "GET /cards",
                        "why": "promised", "archive": "evidence-2026-09"}}

    merged = manifest.merge(known, {})
    assert merged == known, "a refresh that cannot see the body dropped it"

    thin = {"a" * 64: {"id": "a" * 64, "bytes": 0, "call": "", "why": "row",
                       "archive": ""}}
    merged = manifest.merge(known, thin)
    kept = merged["a" * 64]
    assert kept["call"] == "GET /cards", "a blank call key overwrote a real one"
    assert kept["bytes"] == 1234, "a zero size overwrote a real one"
    assert kept["archive"] == "evidence-2026-09", "the archive pointer was lost"
    assert kept["why"] == "row", (
        "why a capture is kept CAN change -- a row can start standing on one "
        "the vendor was already promised -- so that field does refresh")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fuller_entry_does_replace_a_thinner_one():
    """The other direction, or a manifest written before a body arrived would
    never pick the body up."""
    known = {"b" * 64: {"id": "b" * 64, "bytes": 0, "call": "", "why": "row",
                        "archive": ""}}
    fresh = {"b" * 64: {"id": "b" * 64, "bytes": 900, "call": "GET /bots",
                        "why": "row", "archive": ""}}

    kept = manifest.merge(known, fresh)["b" * 64]
    assert kept["bytes"] == 900 and kept["call"] == "GET /bots"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_file_is_sorted_and_rewriting_it_changes_nothing(
        tmp_path, monkeypatch):
    """A manifest that reorders itself would put a diff in every commit and
    nobody would read the one that mattered."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    path = tmp_path / "audits" / "evidence-manifest.jsonl"
    entries = {h * 64: {"id": h * 64, "bytes": 10, "call": "GET /x",
                        "why": "row", "archive": ""} for h in "cab"}

    manifest.write(entries, path=path)
    first = path.read_text(encoding="utf-8")
    ids = [json.loads(line)["id"] for line in first.splitlines() if line.strip()]
    assert ids == sorted(ids), "the manifest is not sorted by id"

    manifest.write(manifest.read(path=path), path=path)
    assert path.read_text(encoding="utf-8") == first, (
        "rewriting an unchanged manifest produced a diff")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_refresh_adds_what_is_on_disk_and_keeps_what_is_not(
        tmp_path, monkeypatch):
    """End to end, over the two cases that matter together."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    path = tmp_path / "audits" / "evidence-manifest.jsonl"
    manifest.write({"d" * 64: {"id": "d" * 64, "bytes": 77, "call": "GET /old",
                               "why": "promised",
                               "archive": "evidence-2026-08"}}, path=path)
    _capture(tmp_path, "e" * 64, _record("/api/v1/bots"))

    added, held = manifest.refresh({"d" * 64: "promised", "e" * 64: "row"},
                                   root=_store(tmp_path), path=path)

    known = manifest.read(path=path)
    assert added == 1 and held == 2, (added, held)
    assert known["d" * 64]["call"] == "GET /old", (
        "the archived capture lost its proof on a refresh")
    assert known["e" * 64]["call"], "the capture on disk was not read"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_manifest_lands_beside_the_state_it_describes(tmp_path, monkeypatch):
    """The same trap `keep.snapshot_dir` fell into on 2026-09-12: a path fixed
    at import wrote a test's data into the repository's own audits/."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    target = manifest.manifest_path()

    assert target == tmp_path / "audits" / "evidence-manifest.jsonl", target
    assert REPO not in target.parents, (
        "a test would write into the repository's committed manifest")
