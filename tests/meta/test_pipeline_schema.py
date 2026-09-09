"""STATE (ledger) and EVT (journal): the loader refuses what no code could
have written, the writer refuses to move history backwards, and the event
log is append-only, hash-chained and idempotent.

Phase 2 of the hardening plan. Fails at 517731f: qa.state has none of
load_ledger, write_ledger, append_event, read_events, head.

The fixtures are the real thing: state/ledger.json as committed at ca0bc45
(hand-rewritten, 13 rows carrying a key no code writes) and at 7518e8e (the
last machine-written version before it), so the tests replay the actual
incident rather than a synthetic one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

FIX = Path(__file__).resolve().parent / "fixtures"
LEDGER = FIX / "ledger"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_load_rejects_hand_written_rows():
    """ledger@ca0bc45 carries backfilled_from (13 rows), verified_note (10) and
    a bare verified_fixed_at (10) -- keys the code never wrote. The loader
    must name them and refuse."""
    from qa.state import LedgerError, load_ledger

    with pytest.raises(LedgerError) as exc:
        load_ledger(LEDGER / "ledger@ca0bc45.json")
    msg = str(exc.value)
    for key in ("backfilled_from", "verified_note", "verified_fixed_at"):
        assert key in msg, f"{key!r} not named in:\n{msg}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_write_refuses_monotonic_violations(tmp_path):
    """Replaying the ca0bc45 rewrite over 7518e8e must be refused, listing
    every violation: first_seen moved backwards, reproductions decreased,
    a machine-written verification provenance went to null."""
    from qa.state import LedgerError, write_ledger

    prev = json.loads((LEDGER / "ledger@7518e8e.json").read_text(encoding="utf-8"))
    new = json.loads((LEDGER / "ledger@ca0bc45.json").read_text(encoding="utf-8"))

    with pytest.raises(LedgerError) as exc:
        write_ledger(prev, new, path=tmp_path / "ledger.json", check_journal=False)
    msg = str(exc.value)
    for needle in (
        "CYM-agent_names", "first_seen", "12:49:12", "10:29:00",
        "reproductions 4 -> 1",
        "verified_by_run",
        "CYM-mcp_resource_count", "reproductions 6 -> 3",
    ):
        assert needle in msg, f"{needle!r} not named in:\n{msg}"
    assert not (tmp_path / "ledger.json").exists(), "a refused write left a file behind"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_write_refuses_a_disappearing_row(tmp_path):
    from qa.state import LedgerError, write_ledger

    prev = {"schema": 2, "findings": {"CYM-a": {"id": "CYM-a"}, "CYM-b": {"id": "CYM-b"}}}
    new = {"schema": 2, "findings": {"CYM-a": {"id": "CYM-a"}}}
    with pytest.raises(LedgerError, match="CYM-b"):
        write_ledger(prev, new, path=tmp_path / "ledger.json", check_journal=False)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_write_is_atomic_and_round_trips(tmp_path):
    from qa.state import load_ledger, write_ledger

    path = tmp_path / "ledger.json"
    row = {
        "id": "CYM-x", "title": "t", "severity": "S3-CONTRACT", "checks": ["tests/x.py::test_a"],
        "first_seen": {"at": "2026-09-05T00:00:00+00:00", "cause": {"run_id": "run-1"}},
        "reproductions": 1,
        "check": {"state": "REPRODUCING", "adjudicated_by": {"run_id": "run-1"}},
        "filing": {"state": "NOT_RAISED"},
        "transitions": [{"axis": "check", "from": None, "to": "REPRODUCING",
                         "cause": {"run_id": "run-1"}, "at": "2026-09-05T00:00:00+00:00"}],
    }
    ledger = {"schema": 2, "findings": {"CYM-x": row}}
    write_ledger(None, ledger, path=path, check_journal=False)
    assert load_ledger(path)["findings"]["CYM-x"]["check"]["state"] == "REPRODUCING"
    assert not list(tmp_path.glob("*.tmp")), "temp file left behind"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_load_rejects_transitions_without_a_cause(tmp_path):
    """A CHECK transition must cite a run_id; a FILING one an event_id.

    Rule 3 at the loader, which is where it has to be: there is nowhere to
    write a state by hand, and a file that carries one is refused rather than
    read. test_pipeline_tamper.py stated the same thing over the check axis
    alone until 2026-09-09; this one covers both, so the weaker copy went and
    its framing came here. Its parametrised sibling, the four hand-written keys
    that were really in the committed ledger, is not a duplicate and stays.
    """
    from qa.state import LedgerError, load_ledger

    def ledger_with(transition):
        return {"schema": 2, "findings": {"CYM-x": {
            "id": "CYM-x", "checks": [],
            "first_seen": {"at": "2026-09-05T00:00:00+00:00", "cause": {"run_id": "run-1"}},
            "transitions": [transition],
        }}}

    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(ledger_with(
        {"axis": "check", "from": None, "to": "REPRODUCING", "cause": {}, "at": "x"})),
        encoding="utf-8")
    with pytest.raises(LedgerError, match="run_id"):
        load_ledger(path)

    path.write_text(json.dumps(ledger_with(
        {"axis": "filing", "from": None, "to": "RAISED", "cause": {"run_id": "run-1"}, "at": "x"})),
        encoding="utf-8")
    with pytest.raises(LedgerError, match="event_id"):
        load_ledger(path)


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------
def _intent(key: str, at: str) -> dict:
    return {"type": "filing_intent", "at": at, "by": "agent", "source": "scripts/submit.py",
            "key": key, "intent_at": at, "title": f"t-{key}", "findings": ["CYM-x"]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_events_log_is_append_only_chained_and_idempotent(tmp_path):
    from qa.state import JournalError, append_event, head, read_events

    path = tmp_path / "events.jsonl"

    assert append_event(_intent("k1", "2026-09-05T00:00:01+00:00"), path=path) == "appended"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    assert head(path=path)["seq"] == 1

    # Same natural key -> duplicate, no new line, head unchanged.
    assert append_event(_intent("k1", "2026-09-05T00:00:01+00:00"), path=path) == "duplicate"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    assert append_event(_intent("k2", "2026-09-05T00:00:02+00:00"), path=path) == "appended"
    events = read_events(path=path)
    assert [e["seq"] for e in events] == [1, 2]
    assert all(len(e["event_id"]) == 64 and len(e["chain"]) == 64 for e in events)
    assert head(path=path) == {"seq": 2, "chain": events[-1]["chain"]}

    lines = path.read_text(encoding="utf-8").splitlines()

    # Deleted middle line -> seq gap.
    (tmp_path / "gap.jsonl").write_text(lines[1] + "\n", encoding="utf-8")
    with pytest.raises(JournalError, match="seq"):
        read_events(path=tmp_path / "gap.jsonl")

    # Edited payload -> chain mismatch.
    edited = lines[0].replace('"t-k1"', '"t-EDITED"')
    (tmp_path / "edited.jsonl").write_text(edited + "\n" + lines[1] + "\n", encoding="utf-8")
    with pytest.raises(JournalError, match="chain"):
        read_events(path=tmp_path / "edited.jsonl")

    # Unknown key -> refused.
    obj = json.loads(lines[0]); obj["verified_note"] = "hand"
    (tmp_path / "unknown.jsonl").write_text(json.dumps(obj) + "\n", encoding="utf-8")
    with pytest.raises(JournalError, match="verified_note"):
        read_events(path=tmp_path / "unknown.jsonl")

    # Truncated tail -> reported as such, not silently dropped.
    (tmp_path / "trunc.jsonl").write_text(lines[0] + "\n" + lines[1][: len(lines[1]) // 2], encoding="utf-8")
    with pytest.raises(JournalError, match="truncated"):
        read_events(path=tmp_path / "trunc.jsonl")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_append_refuses_incomplete_or_unknown_events(tmp_path):
    from qa.state import JournalError, append_event

    path = tmp_path / "events.jsonl"
    with pytest.raises(JournalError, match="type"):
        append_event({"at": "x", "by": "agent", "source": "s"}, path=path)
    with pytest.raises(JournalError, match="unknown event type"):
        append_event({"type": "made_up", "at": "x", "by": "agent", "source": "s"}, path=path)
    with pytest.raises(JournalError, match="reason"):
        append_event({"type": "withdraw", "at": "x", "by": "operator", "source": "cli",
                      "finding_id": "CYM-x", "reason": ""}, path=path)
    assert not path.exists() or path.read_text(encoding="utf-8") == ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_verifications_on_one_report_do_not_collapse(tmp_path):
    """VER: a new event type without a natural key dedupes against itself.

    `_natural_key` ends in a fallback that keys on finding_id plus a hash of
    `text or note or ''` -- both empty on a verification. So two genuinely
    different verifications sent to the same report, which is exactly what
    #50, #51, #52 and #67 need (each covers two checks with two fingerprints),
    would produce the same key, and append_event would answer "duplicate" and
    return WITHOUT raising. The second fingerprint would simply never be
    recorded, and nothing would say so.

    Stated over the pair that actually collides in our data rather than over
    the function, so it stays true if the keying is rewritten.
    """
    from qa.state import append_event, read_events

    path = tmp_path / "events.jsonl"

    def verification(finding_id, fingerprint, report_id=50, type_="verification_outcome"):
        return {
            "type": type_, "at": "2026-09-07T13:00:00+00:00", "by": "agent",
            "source": "scripts/verify.py", "finding_id": finding_id,
            "report_id": report_id, "fingerprint": fingerprint,
            "verdict": "pass", "outcome": "accepted",
            "run_id": "run-20260907T123825Z-8bf609f", "evidence_id": "ev-1",
        }

    assert append_event(verification("CYM-mcp_resource_count", "d5a3824c"),
                        path=path) == "appended"
    assert append_event(verification("CYM-mcp_tool_names_declared_vs_served",
                                     "sha256:1"), path=path) == "appended", \
        "the second check on report #50 collapsed into the first"
    # And the same fact twice really is one fact.
    assert append_event(verification("CYM-mcp_resource_count", "d5a3824c"),
                        path=path) == "duplicate"

    events = read_events(path=path)
    assert len(events) == 2
    assert {e["fingerprint"] for e in events} == {"d5a3824c", "sha256:1"}

    # The intent half is keyed without the outcome, so re-running the sender
    # after a timeout does not add a second intent for the same attempt.
    assert append_event(verification("CYM-mcp_resource_count", "d5a3824c",
                                     type_="verification_intent"),
                        path=path) == "appended"
    assert append_event(verification("CYM-mcp_resource_count", "d5a3824c",
                                     type_="verification_intent"),
                        path=path) == "duplicate"

    # But the VERDICT is part of the identity, and was not until 2026-09-07.
    # A correction is a different fact from the pass it corrects even when
    # every other field matches -- which is the case when the vendor regresses
    # and our check's definition never moved. Losing that intent means a POST
    # leaves with nothing in the journal saying we tried, on the one leg that
    # exists because we can be wrong.
    correction = verification("CYM-mcp_resource_count", "d5a3824c",
                             type_="verification_intent")
    correction["verdict"] = "fail"
    assert append_event(correction, path=path) == "appended",         "the correction's intent collided with the pass it corrects"
    assert append_event(correction, path=path) == "duplicate"
