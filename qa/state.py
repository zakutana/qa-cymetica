"""State layer: run records, admissibility, the event journal, ledger I/O.

The one module that owns `state/`. Everything that reads or writes a run
record, the append-only event journal, or the ledger goes through here, so the
invariants the audit found missing live in exactly one place:

  * A run record is evidence only if it is *admissible* (§4.4 of the plan):
    schema 2 with a `collected` list, undrifted fingerprint, self-consistent
    exit status (level R); plus a clean tree and a preregistration tag whose
    commit is HEAD (level V). All 13 legacy records fail this, by a named
    reason each.
  * A run is found by its `run_id` FIELD, never by filename sort -- the three
    copies of `sorted(glob(...))[-1]` that let a 1-result partial run close
    everything are gone.
  * The ledger loader refuses any row carrying a key no code writes
    (`backfilled_from`, `verified_note`, a bare `verified_fixed_at`) or any
    transition without a cause; the writer refuses to move history backwards.
  * The journal is append-only, sequence-numbered, hash-chained and
    idempotent by a per-type natural key.

Phase 0's state_dir() seam stays at the top.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def state_dir() -> Path:
    """`QA_STATE_DIR` if set, else `<repo>/state`."""
    override = os.environ.get("QA_STATE_DIR")
    return Path(override) if override else REPO_ROOT / "state"


def runs_dir() -> Path:
    return state_dir() / "runs"


def journal_path() -> Path:
    return state_dir() / "journal" / "events.jsonl"


def ledger_path() -> Path:
    return state_dir() / "ledger.json"


# ---------------------------------------------------------------------------
# Run records
# ---------------------------------------------------------------------------
INCONCLUSIVE_MARKER = "qa.marks.Inconclusive:"


def _relabel_legacy(run: dict) -> dict:
    """Legacy records wrote Inconclusive-classified checks as `failed` (the
    trylast-recorder bug fixed in phase 1). Relabel them on read, keeping the
    original beside as `reclassified_from`. The file is never rewritten -- this
    is a label on contaminated data, not a recomputation (methodology §1.5)."""
    if run.get("schema") == 2:
        return run  # a v2 record was written by the fixed recorder; trust it
    for result in run.get("results", []):
        if result.get("outcome") == "failed" and \
                INCONCLUSIVE_MARKER in (result.get("failure_repr") or ""):
            result["reclassified_from"] = "failed"
            result["outcome"] = "inconclusive"
    return run


def load_run(run_id: str, runs: Path | None = None) -> dict:
    """Load one run record by its run_id FIELD, not by filename."""
    directory = runs or runs_dir()
    # Glob every JSON: a record is identified by its run_id FIELD. Matching on
    # the filename is the dependence this module exists to remove.
    for path in sorted(directory.glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        if run.get("run_id") == run_id:
            return _relabel_legacy(run)
    raise KeyError(run_id)


def list_runs(runs: Path | None = None) -> list[dict]:
    """All run records, ordered by started_at (not by filename)."""
    directory = runs or runs_dir()
    out = [
        _relabel_legacy(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(directory.glob("*.json"))
    ]
    out = [r for r in out if r.get("run_id")]
    out.sort(key=lambda r: r.get("started_at") or "")
    return out


@dataclass
class Verdict:
    level: str                       # "none" | "R" | "V"
    reasons: list[str] = field(default_factory=list)
    # Things that do not block the level but qualify it. Critique gap 8: a
    # clean, tagged, full run made WITHOUT the trusted key is level V and has
    # never adjudicated a single S0 row -- the checks that need that key were
    # skipped. The fold is already safe (a skipped check moves nothing), but
    # an operator reading "V" deserves to be told which half of the ladder the
    # run could not reach.
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.level == "V" and self.notes:
            return "V (partial identity)"
        return self.level


def admissibility(run: dict) -> Verdict:
    """Two levels, each blocker named. R may open a defect; V may verify a fix.

    A reason that blocks R also blocks V. A reason that blocks only V leaves R.
    """
    blocks_r: list[str] = []
    blocks_v: list[str] = []

    if run.get("schema") != 2 or "collected" not in run:
        blocks_r.append("legacy_schema")
    if run.get("platform_fingerprint") is None:
        blocks_r.append("no_fingerprint")
    if run.get("fingerprint_drifted"):
        blocks_r.append("fingerprint_drifted")

    collected = set(run.get("collected") or [])
    seen = {r["nodeid"] for r in run.get("results", [])}
    if "collected" in run and not seen <= collected:
        blocks_r.append("results_not_collected")

    exit_status = run.get("exit_status")
    # Judge the RAW record: a result relabelled from failed still means the
    # session pytest saw a failure, so exit 0 beside it is a disagreement in
    # the record even after our reinterpretation.
    any_red = any(
        r.get("outcome") in ("failed", "error") or r.get("reclassified_from") == "failed"
        for r in run.get("results", [])
    )
    if exit_status not in (0, 1) or (exit_status == 1) != any_red:
        blocks_r.append("exit_status_disagrees")

    if run.get("git_dirty"):
        blocks_v.append("git_dirty")
    if not run.get("prereg_id"):
        blocks_v.append("no_prereg")
    elif run.get("prereg_commit") != run.get("git_head"):
        # Absent is a mismatch, not a pass. Guarding this with
        # `if run.get("prereg_commit") and ...` meant a record naming a
        # preregistration but declining to say which commit it was tagged at
        # sailed through to level V, and run_integrity's git re-resolution had
        # the same guard, so nothing checked the tag either. The gap 1
        # hardening closed EDITING two strings in a run record; deleting one
        # bought the same verification. Falsy-versus-absent, in the one place
        # this module calls the way in.
        blocks_v.append("prereg_commit_mismatch")

    notes = [f"identity_absent:{name}"
             for name, present in sorted((run.get("identities_present") or {}).items())
             if not present]

    if blocks_r:
        return Verdict("none", blocks_r + blocks_v, notes)
    if blocks_v:
        return Verdict("R", blocks_v, notes)
    return Verdict("V", [], notes)


class RunIntegrityError(RuntimeError):
    """A run record contradicts something outside itself."""


def run_integrity(run: dict, path: Path | None = None,
                  events: list[dict] | None = None) -> list[str]:
    """Check a run record against facts it does not control.

    Critique gap 1: run records are the only input to the whole pipeline that
    nothing corroborates. Level V is granted from fields the file asserts
    ABOUT ITSELF -- `git_dirty: false`, `prereg_commit: <sha>` -- so editing
    two strings in state/runs/*.json buys a verification carrying a real run
    id. Everything else in the system is chained, hashed or cross-checked;
    this was the way in.

    Two corroborations, both cheap:
      * the preregistration tag is re-resolved with git. The record may claim
        any commit it likes; the tag is in the repository's object store.
      * the file's hash is compared against the `run_recorded` event appended
        when it was first composed, so a record cannot be edited after the
        journal has attested to it.
    """
    import hashlib
    import subprocess

    problems: list[str] = []
    prereg = run.get("prereg_id")
    if prereg:
        try:
            resolved = subprocess.run(
                ["git", "rev-parse", f"prereg/{prereg}^{{commit}}"],
                cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
            ).stdout.strip()
        except (subprocess.CalledProcessError, OSError):
            problems.append(f"no tag prereg/{prereg} in this repository")
        else:
            claimed = run.get("prereg_commit")
            if not claimed:
                # The tag exists but the record declines to name a commit, so
                # there is nothing to corroborate against it. Silence here is
                # not agreement.
                problems.append(
                    f"the record names {prereg} but carries no prereg_commit, "
                    f"so the tag it claims cannot be checked against it"
                )
            elif claimed != resolved:
                problems.append(
                    f"the record says prereg_commit {claimed[:12]} "
                    f"but prereg/{prereg} resolves to {resolved[:12]}"
                )

    if path is not None and path.exists():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for event in events if events is not None else read_events():
            if event.get("type") == "run_recorded" \
                    and event.get("run_id") == run.get("run_id") \
                    and event.get("file_sha256") not in (None, digest):
                problems.append(
                    f"the record has changed since the journal attested to it "
                    f"({event['file_sha256'][:12]} -> {digest[:12]})"
                )
    return problems


def latest_admissible_run_id(level: str = "V", runs: Path | None = None) -> str | None:
    """Newest admissible run of at least `level`, by started_at."""
    wanted = {"R": {"R", "V"}, "V": {"V"}, "none": {"none", "R", "V"}}[level]
    best = None
    for run in list_runs(runs=runs):
        if admissibility(run).level in wanted:
            best = run["run_id"]  # list_runs is sorted ascending, so last wins
    return best


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
class LedgerError(RuntimeError):
    """The ledger on disk, or a proposed write, violates the state contract."""


# Keys no code writes. Their presence means the file was edited by hand.
FORBIDDEN_ROW_KEYS = frozenset({
    "backfilled_from", "verified_note", "verified_fixed_at", "verified_by_run",
    "first_seen_run",
})


def _check_row(fid: str, row: dict, errors: list[str]) -> None:
    hand = sorted(FORBIDDEN_ROW_KEYS & set(row))
    if hand:
        errors.append(f"{fid}: hand-written keys no code produces: {hand}")

    first_seen = row.get("first_seen")
    if not isinstance(first_seen, dict) or "cause" not in first_seen:
        errors.append(f"{fid}: first_seen must be {{at, cause}}, got {first_seen!r}")

    for t in row.get("transitions", []):
        axis, cause = t.get("axis"), (t.get("cause") or {})
        if axis == "check" and not cause.get("run_id"):
            errors.append(f"{fid}: a CHECK transition to {t.get('to')!r} has no run_id")
        if axis == "filing" and not cause.get("event_id"):
            errors.append(f"{fid}: a FILING transition to {t.get('to')!r} has no event_id")


def _first_seen_at(row: dict) -> str | None:
    """`first_seen` is a bare timestamp in legacy rows and {at, cause} in v2.
    The monotonic check must read both, or it cannot police the one file the
    hand-rewrite actually happened in."""
    value = row.get("first_seen")
    if isinstance(value, dict):
        return value.get("at")
    return value if isinstance(value, str) else None


def _verified_run(row: dict) -> str | None:
    """Verification provenance: v2 keeps it under check.adjudicated_by, legacy
    rows on a bare verified_by_run."""
    v2 = ((row.get("check") or {}).get("adjudicated_by") or {}).get("run_id")
    return v2 or row.get("verified_by_run")


def load_ledger(path: Path | None = None) -> dict:
    p = path or ledger_path()
    ledger = json.loads(p.read_text(encoding="utf-8"))
    errors: list[str] = []
    for fid, row in ledger.get("findings", {}).items():
        _check_row(fid, row, errors)
    if errors:
        raise LedgerError(
            "ledger contains state no code could have written -- it was edited "
            "by hand. Corrections are events (scripts/withdraw.py), never edits.\n  "
            + "\n  ".join(errors)
        )
    return ledger


def write_ledger(prev: dict | None, new: dict, path: Path | None = None,
                 check_journal: bool = True) -> None:
    """Write the ledger only if it moves forward monotonically.

    Refuses a disappeared row, first_seen moved earlier, reproductions
    decreased, a verification provenance cleared to null, or transitions that
    are not an extension of the previous ones. Atomic (tmp + os.replace).
    """
    p = path or ledger_path()
    errors: list[str] = []

    prev_rows = (prev or {}).get("findings", {})
    new_rows = new.get("findings", {})

    for fid in prev_rows:
        if fid not in new_rows:
            errors.append(f"{fid}: row disappeared -- findings are created once and never deleted")

    for fid, before in prev_rows.items():
        after = new_rows.get(fid)
        if after is None:
            continue
        fb, fa = _first_seen_at(before), _first_seen_at(after)
        if fb and fa and fa < fb:
            errors.append(f"{fid}: first_seen moved backwards {fb[11:19]} -> {fa[11:19]}")
        rb, ra = before.get("reproductions") or 0, after.get("reproductions") or 0
        if ra < rb:
            errors.append(f"{fid}: reproductions {rb} -> {ra} (may not decrease)")
        if _verified_run(before) and not _verified_run(after):
            errors.append(f"{fid}: verified_by_run (verification provenance) cleared to null")
        # The invariant is that history is never LOST, not that it keeps its
        # position in the file. A positional prefix check also forbids two
        # legitimate things: writing the transitions in a stable chronological
        # order (the FILING half is rebuilt from the journal on every fold
        # while the CHECK half accumulates, so construction order interleaves
        # them arbitrarily), and ingesting a back-dated event discovered later
        # -- an archived reply, say -- which belongs earlier in the history it
        # describes. Compare as a multiset instead.
        tb = Counter(_canonical(t) for t in before.get("transitions", []))
        ta = Counter(_canonical(t) for t in after.get("transitions", []))
        dropped = tb - ta
        if dropped:
            errors.append(
                f"{fid}: {sum(dropped.values())} transition(s) disappeared from "
                f"the prior history: {sorted(dropped)[:2]}"
            )

    # The written file must itself pass the load contract.
    for fid, row in new_rows.items():
        _check_row(fid, row, errors)

    if check_journal:
        want = head().get("chain")
        if new.get("events_head", {}).get("chain") != want:
            errors.append(
                f"events_head {new.get('events_head')} != journal head chain {want}; "
                f"the ledger is a projection of the journal and must cite its head"
            )

    if errors:
        raise LedgerError(
            "refusing to write the ledger -- the change is not forward-only:\n  "
            + "\n  ".join(errors)
        )

    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


# ---------------------------------------------------------------------------
# Event journal: append-only, sequence-numbered, hash-chained, idempotent
# ---------------------------------------------------------------------------
class JournalError(RuntimeError):
    """The event journal is malformed, tampered with, or an event is invalid."""


EVENT_TYPES = frozenset({
    "run_recorded", "filing_intent", "filing_outcome", "vendor_status",
    "vendor_read", "message", "reply", "withdraw", "retire_check",
    "rebind_check", "pin_fingerprint", "retraction_sent", "supersede",
    "backfill", "legacy_verification", "migrated", "note",
})
REQUIRED_EVENT_KEYS = ("type", "at", "by", "source")
ALLOWED_EVENT_KEYS = frozenset({
    "seq", "event_id", "chain", "type", "at", "by", "source",
    "finding_id", "report_id", "msg_id", "key", "intent_at", "title",
    "findings", "outcome", "http_status", "status", "observed_at", "reason",
    "reply_to", "delivered", "nodeid", "from_id", "to_id", "value",
    "evidence_id", "reconciled_from", "server_created_at", "text",
    "run_id", "file_sha256", "migrated_from", "note", "origin", "via",
    "klass", "rows_returned", "server_total", "stale_from",
})


def _natural_key(event: dict) -> str:
    t = event["type"]
    g = event.get
    if t == "filing_intent":
        return f"{t}|{g('key')}|{g('intent_at')}"
    if t == "filing_outcome":
        # The outcome is part of the identity. A submission that timed out and
        # was later settled against my-reports produces two genuinely
        # different facts about the same key -- and they can land in the same
        # second, so time alone does not separate them.
        return f"{t}|{g('key')}|{g('outcome')}|{g('report_id')}|{g('at')}|{g('source')}"
    if t == "vendor_status":
        return f"{t}|{g('report_id')}|{g('status')}|{g('observed_at')}"
    if t == "vendor_read":
        return f"{t}|{g('at')}|{g('source')}|{g('klass')}"
    if t in ("message", "reply"):
        return f"{t}|{g('msg_id')}"
    if t == "run_recorded":
        return f"{t}|{g('run_id')}"
    if t in ("withdraw", "retire_check", "rebind_check", "pin_fingerprint"):
        return f"{t}|{g('finding_id')}|{g('nodeid') or ''}|{g('at')}"
    if t == "retraction_sent":
        return f"{t}|{g('finding_id')}|{g('report_id')}"
    if t == "supersede":
        return f"{t}|{g('from_id')}|{g('to_id')}"
    # backfill / legacy_verification / migrated / note
    return f"{t}|{g('finding_id')}|{hashlib.sha256((g('text') or g('note') or '').encode()).hexdigest()[:12]}"


def event_id(event: dict) -> str:
    """The event's identity: type + its natural key, hashed.

    Public because the fold cites it as the cause of every FILING transition,
    and must be able to do so for an event it was handed directly rather than
    read back off the journal.
    """
    return hashlib.sha256(
        (event["type"] + "|" + _natural_key(event)).encode("utf-8")
    ).hexdigest()


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _validate_event(event: dict) -> None:
    for key in REQUIRED_EVENT_KEYS:
        if not event.get(key):
            raise JournalError(f"event missing required key {key!r}: {event}")
    if event["type"] not in EVENT_TYPES:
        raise JournalError(f"unknown event type {event['type']!r}")
    unknown = set(event) - ALLOWED_EVENT_KEYS
    if unknown:
        raise JournalError(f"event has unknown keys {sorted(unknown)}")
    if event["type"] == "withdraw" and not (event.get("reason") or "").strip():
        raise JournalError("a withdraw event needs a non-empty reason")


def read_events(path: Path | None = None) -> list[dict]:
    p = path or journal_path()
    if not p.exists():
        return []
    events: list[dict] = []
    prev_chain = ""
    raw = p.read_text(encoding="utf-8")
    lines = raw.split("\n")
    # A well-formed file ends with a newline, so the final split piece is "".
    if lines and lines[-1] == "":
        lines = lines[:-1]
    elif lines:
        raise JournalError("journal has a truncated final line (no trailing newline)")

    for i, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise JournalError(f"line {i} is truncated or not JSON: {exc}") from exc
        if event.get("seq") != i:
            raise JournalError(f"seq gap: line {i} has seq {event.get('seq')}")
        for key in set(event) - {"seq", "event_id", "chain"}:
            if key not in ALLOWED_EVENT_KEYS:
                raise JournalError(f"line {i}: unknown key {key!r}")
        body = {k: v for k, v in event.items() if k not in ("chain",)}
        expect = hashlib.sha256((prev_chain + _canonical(body)).encode("utf-8")).hexdigest()
        if event.get("chain") != expect:
            raise JournalError(f"line {i}: chain mismatch (payload edited?)")
        events.append(event)
        prev_chain = event["chain"]
    return events


def head(path: Path | None = None) -> dict:
    events = read_events(path=path)
    if not events:
        return {"seq": 0, "chain": ""}
    return {"seq": events[-1]["seq"], "chain": events[-1]["chain"]}


@contextlib.contextmanager
def _journal_lock(path: Path):
    """Hold an exclusive cross-process lock for the length of one append.

    `append_event` reads the whole journal, derives `seq` and `chain` from what
    it read, and only then writes. Two writers interleaving inside that window
    both derive the same seq, and the file ends up with a duplicate sequence
    number and a broken chain. That is not a lost event: `read_events` raises
    on the next load, so the ledger cannot fold, the page cannot render and
    every session aborts -- and rule 4 forbids repairing it by hand, so there
    is no way out that does not break another rule.

    It stayed theoretical while every writer was an operator typing a command.
    `serve.py --ask` ended that: it appends on a timer, unattended, and can
    land in the middle of a sweep.

    A separate .lock file rather than the journal itself, so the lock is never
    confused with the data and locking cannot truncate or extend it. Held
    around the read as well as the write, because the read is what the write
    is derived from.
    """
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            # LK_LOCK retries for about ten seconds, then raises. Locking one
            # byte past EOF is legal on Windows and is the usual idiom.
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def append_event(event: dict, path: Path | None = None) -> str:
    """Append one event. Returns 'appended' or 'duplicate' (idempotent by
    natural key). Never rewrites an existing line.

    Serialised across processes: see `_journal_lock`.
    """
    _validate_event(event)
    p = path or journal_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    with _journal_lock(p):
        existing = read_events(path=p)
        key = _natural_key(event)
        for e in existing:
            if _natural_key(e) == key:
                return "duplicate"

        seq = len(existing) + 1
        prev_chain = existing[-1]["chain"] if existing else ""
        body = dict(event)
        body["seq"] = seq
        body["event_id"] = event_id(event)
        chain = hashlib.sha256((prev_chain + _canonical(body)).encode("utf-8")).hexdigest()
        line = dict(body)
        line["chain"] = chain

        with open(p, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(_canonical(line) + "\n")
            # Flushed inside the lock: a line still sitting in a buffer when
            # the next writer reads would give it the same seq all over again.
            fh.flush()
        return "appended"
