"""The only way a human changes state: by appending an event with a reason.

Four findings were retracted by adding their ids to a dict literal at
scripts/ledger.py:36-55. That is why none of those withdrawals has a date, an
author, or -- for the two that had already been filed with the vendor -- any
record that we owed somebody a correction. The same defect wearing different
clothes is `if False and method:` in findings.py, a finding switched off by
editing the generator that produces it.

Every judgement call an operator makes goes through here and becomes one line
in the journal. This script never opens state/ledger.json. The ledger is a
projection; to change it, change what it is a projection of and re-fold.

    python scripts/withdraw.py withdraw CYM-mcp_tool_count --reason "..."
    python scripts/withdraw.py rebind-check CYM-x --from scripts/inventory.py \
        --to tests/rest/test_inventory.py::test_documented_paths --reason "..."
    python scripts/withdraw.py retraction-sent CYM-x --report 54 --reason "..."
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.fold import _fingerprint_of, display_state  # noqa: E402
from qa.state import append_event, journal_path, ledger_path  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint_from_run(run: dict, checks: list) -> str:
    """The fingerprint that run observed for these checks.

    Derived, never retyped. Pinning a repaired check needs the value the run
    saw, and twice on 2026-09-07 that was fetched with a throwaway one-liner
    over the run record and pasted in by hand.

    The reason it calls the fold's own `_fingerprint_of` instead of reading a
    field: a row can declare several checks, and the combined value is a hash
    of the sorted nodeid=fingerprint pairs -- not the first one, not the newest.
    A second implementation here would pin something the fold never computes,
    and the row would read CHECK CHANGED for ever with a justification
    attached to it: a badge nobody can clear, signed.
    """
    # Built exactly as qa/fold.py:236 builds it -- same comprehension, same
    # last-wins on a repeated nodeid, and deliberately no filter of its own.
    # An earlier draft here skipped results carrying no fingerprint, which
    # would have picked a different object than the fold whenever a nodeid
    # appeared twice. Two selections is two rules.
    by_nodeid = {r["nodeid"]: r for r in run.get("results") or []}
    missing = [c for c in checks if c not in by_nodeid]
    if missing:
        raise SystemExit(
            f"run {run.get('run_id')} did not adjudicate "
            f"{len(missing)} of this row's checks, so it cannot say what "
            f"fingerprint they have: {', '.join(missing)}"
        )
    value = _fingerprint_of([by_nodeid[c] for c in checks])
    if not value:
        raise SystemExit(f"run {run.get('run_id')} recorded no fingerprint for "
                         f"this row's checks")
    return value


def _require_reason(reason: str | None, what: str) -> str:
    text = (reason or "").strip()
    if not text:
        raise SystemExit(
            f"refusing to record a {what} with no reason.\n"
            f"The reason is the whole value of the record: a state change "
            f"nobody can explain later is the thing this script exists to "
            f"prevent."
        )
    return text


def _known_ids() -> set[str] | None:
    """Every finding id in the ledger, or None if it cannot be read.

    None means "cannot tell", and is never treated as "not there".
    """
    import json

    path = ledger_path()
    if not path.exists():
        return None
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    findings = ledger.get("findings")
    return set(findings) if isinstance(findings, dict) else None


def _must_exist(*finding_ids: str) -> None:
    """Refuse to write an event about a finding that is not there.

    Nothing checked this, so a mistyped id appended a permanent event to an
    append-only journal, printed "appended: withdraw CYM-reallll" as though it
    had worked, and left the row it was meant for exactly as it was. Both
    halves are bad: the retraction that was owed never got recorded, and the
    journal keeps a judgement about a finding that does not exist, which
    cannot be deleted -- only annotated.

    An unreadable or absent ledger means we cannot tell, and that must not
    stop an operator recording a judgement: bootstrapping is a real case.
    """
    import difflib

    known = _known_ids()
    if known is None:
        return
    for finding_id in finding_ids:
        if finding_id in known:
            continue
        close = difflib.get_close_matches(finding_id, sorted(known), n=3, cutoff=0.5)
        hint = f"\n  did you mean: {', '.join(close)}" if close else ""
        raise SystemExit(
            f"no finding {finding_id!r} in the ledger, so this event would be "
            f"a permanent no-op in an append-only journal.{hint}\n"
            f"  {len(known)} findings exist; scripts/ledger.py lists them."
        )


def _affected(finding_id: str) -> tuple[list[int], str | None]:
    """Which vendor reports this finding is filed under, and how it renders.

    Read-only, and best-effort: the ledger may not exist yet, and its absence
    must not stop an operator from recording a judgement.
    """
    import json

    path = ledger_path()
    if not path.exists():
        return [], None
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], None
    row = (ledger.get("findings") or {}).get(finding_id)
    if row is None:
        return [], None
    reports = [r["report_id"] for r in (row.get("filing") or {}).get("reports", [])]
    try:
        return reports, display_state(row)
    except KeyError:
        return reports, None


def _emit(event: dict, finding_id: str, owes: str | None = None) -> int:
    outcome = append_event(event)
    reports, shown = _affected(finding_id)

    print(f"{outcome}: {event['type']} {finding_id}")
    print(f"  journal  {journal_path()}")
    if shown:
        print(f"  currently displayed as {shown}")
    if reports:
        joined = ", ".join(f"#{r}" for r in reports)
        print(f"  filed as {joined}")
        if owes:
            print(f"  OWED: {owes} on {joined}")
    # --events-only, not bare ledger.py. This appended a journal event and
    # nothing else; a bare fold also composes the newest admissible run, which
    # would fold a run the operator did not ask about into the same write.
    print("  run scripts/ledger.py --events-only to fold this in")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="withdraw.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("withdraw", help="retract a finding we got wrong")
    p.add_argument("finding_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("retire-check", help="a check that no longer measures anything")
    p.add_argument("finding_id")
    p.add_argument("--nodeid", required=True)
    p.add_argument("--reason", required=True)

    p = sub.add_parser("rebind-check", help="point a row at the check that adjudicates it")
    p.add_argument("finding_id")
    p.add_argument("--from", dest="from_check", required=True)
    p.add_argument("--to", dest="to_check", required=True)
    p.add_argument("--reason", required=True)

    p = sub.add_parser("pin-fingerprint", help="accept a changed check definition")
    p.add_argument("finding_id")
    p.add_argument("--value", help="the fingerprint to pin; or use --from-run")
    p.add_argument("--from-run", metavar="RUN_ID",
                   help="read it from that run, the way the fold computes it")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("retraction-sent", help="a correction was actually sent")
    p.add_argument("finding_id")
    p.add_argument("--report", type=int, required=True)
    p.add_argument("--reason", required=True)

    p = sub.add_parser("supersede", help="one row replaces another")
    p.add_argument("from_id")
    p.add_argument("to_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("split-report",
                       help="move one report off a row onto a row of its own")
    p.add_argument("finding_id")
    p.add_argument("--report", type=int, required=True)
    p.add_argument("--to", dest="to_id", required=True)
    p.add_argument("--check", dest="nodeid", required=True,
                   help="the check that adjudicates the new row")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("note", help="record something without changing state")
    p.add_argument("finding_id")
    p.add_argument("--text", required=True)

    args = parser.parse_args(argv)
    at, source = _now(), "scripts/withdraw.py"
    base = {"at": at, "by": "operator", "source": source}

    # Before anything is written. supersede names two rows and both have to be
    # real, or half the event lands and the other half points at nothing.
    if args.command == "supersede":
        _must_exist(args.from_id, args.to_id)
    else:
        _must_exist(args.finding_id)

    if args.command == "withdraw":
        reason = _require_reason(args.reason, "withdrawal")
        return _emit({**base, "type": "withdraw", "finding_id": args.finding_id,
                      "reason": reason}, args.finding_id,
                     owes="a correction to the vendor")

    if args.command == "retire-check":
        reason = _require_reason(args.reason, "check retirement")
        return _emit({**base, "type": "retire_check", "finding_id": args.finding_id,
                      "nodeid": args.nodeid, "reason": reason}, args.finding_id,
                     owes="a replacement check, or a correction")

    if args.command == "rebind-check":
        reason = _require_reason(args.reason, "check rebinding")
        return _emit({**base, "type": "rebind_check", "finding_id": args.finding_id,
                      "value": args.from_check, "nodeid": args.to_check,
                      "reason": reason}, args.finding_id)

    if args.command == "pin-fingerprint":
        reason = _require_reason(args.reason, "fingerprint pin")
        value = args.value
        if bool(value) == bool(args.from_run):
            raise SystemExit("pin-fingerprint needs exactly one of --value or "
                             "--from-run")
        if args.from_run:
            from qa.state import load_ledger, load_run

            row = (load_ledger().get("findings") or {}).get(args.finding_id)
            if row is None:
                raise SystemExit(f"the ledger has no row {args.finding_id!r}")
            value = fingerprint_from_run(load_run(args.from_run),
                                         row.get("checks") or [])
            print(f"   fingerprint from {args.from_run}: {value}")
        return _emit({**base, "type": "pin_fingerprint", "finding_id": args.finding_id,
                      "value": value, "reason": reason}, args.finding_id)

    if args.command == "retraction-sent":
        reason = _require_reason(args.reason, "retraction")
        return _emit({**base, "type": "retraction_sent", "finding_id": args.finding_id,
                      "report_id": args.report, "reason": reason}, args.finding_id)

    if args.command == "split-report":
        # The report has to be on the row, and the new row must not already
        # exist -- either way the event would be permanent and move nothing.
        reports, _ = _affected(args.finding_id)
        if _known_ids() is not None and args.report not in reports:
            raise SystemExit(f"{args.finding_id} holds no report #{args.report} "
                             f"(it holds {reports or 'none'})")
        if args.to_id == args.finding_id or args.to_id in (_known_ids() or set()):
            raise SystemExit(f"{args.to_id} already exists; a split makes a new row")
        reason = _require_reason(args.reason, "split")
        return _emit({**base, "type": "split_report", "finding_id": args.finding_id,
                      "report_id": args.report, "to_id": args.to_id,
                      "nodeid": args.nodeid, "reason": reason}, args.finding_id)

    if args.command == "supersede":
        reason = _require_reason(args.reason, "supersede")
        return _emit({**base, "type": "supersede", "from_id": args.from_id,
                      "to_id": args.to_id, "reason": reason}, args.from_id)

    text = _require_reason(args.text, "note")
    return _emit({**base, "type": "note", "finding_id": args.finding_id,
                  "text": text}, args.finding_id)


if __name__ == "__main__":
    raise SystemExit(main())
