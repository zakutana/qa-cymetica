"""Compose one run and the journal into the ledger.

This script used to be `merge()`: it took the last run record by filename,
rebuilt the finding list from whatever was currently failing, and stamped
VERIFIED FIXED on every row that was no longer in it. The audit traced 71 of
the 109 state changes an operator watched back to that function -- not to the
platform changing, but to us re-deriving what we already knew.

It now does no deriving at all. The rules live in qa/fold.py, which is pure;
this file only reads the inputs, calls it, and writes the result through
qa.state.write_ledger, which refuses anything that moves history backwards.

    python scripts/ledger.py --run <run_id>   compose that run
    python scripts/ledger.py                  the newest admissible run
    python scripts/ledger.py --events-only    the journal alone, no run
    python scripts/ledger.py --check          does the committed ledger match?

There is no invocation that picks a run for you when none is admissible. If
that is the situation, the answer is to make an admissible run, and the script
says so and names what is wrong with each candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import findings as findings_mod  # noqa: E402

from qa.fold import display_state, fold  # noqa: E402
from qa.state import (  # noqa: E402
    RunIntegrityError,
    admissibility,
    append_event,
    head,
    latest_admissible_run_id,
    ledger_path,
    list_runs,
    load_run,
    read_events,
    run_integrity,
    runs_dir,
    write_ledger,
)

DISPLAY_RANK = {
    "STILL REPRODUCIBLE": 0, "NOT RAISED YET": 1, "RAISED": 2,
    "THEY REPLIED": 3, "FIX CLAIMED": 4, "UNVERIFIED": 5,
    "OUR CHECK CANNOT TELL": 6, "INCONCLUSIVE": 7, "CHECK CHANGED": 8,
    "UNVERIFIABLE": 9, "NEVER SEEN BROKEN": 10, "PASSING, UNCLAIMED": 11,
    "PASSING, NEVER RAISED": 12, "VERIFIED FIXED": 13, "WITHDRAWN": 14,
}
SEVERITY_RANK = ["S0-CUSTODY", "S1-INTEGRITY", "S2-MEASUREMENT",
                 "S3-CONTRACT", "S4-COSMETIC"]


def load_previous() -> dict | None:
    path = ledger_path()
    if not path.exists():
        return None
    # Deliberately the raw read, not load_ledger(): composing must still work
    # against a ledger the loader would reject, so that the fix for a bad
    # ledger is to re-fold it rather than to hand-edit it.
    return json.loads(path.read_text(encoding="utf-8"))


def _candidates(run: dict | None) -> list[dict]:
    return findings_mod.candidates(run) if run is not None else []


def _run_path(run_id: str) -> Path | None:
    for path in sorted(runs_dir().glob("*.json")):
        if json.loads(path.read_text(encoding="utf-8")).get("run_id") == run_id:
            return path
    return None


def _run_recorded(run: dict, path: Path | None) -> dict:
    """The journal's attestation of the bytes this composition read.

    Once written, the record cannot be edited without run_integrity noticing.
    """
    import hashlib

    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path else None
    return {
        "type": "run_recorded", "at": run.get("finished_at") or run.get("started_at"),
        "by": "agent", "source": "scripts/ledger.py",
        "run_id": run["run_id"], "file_sha256": digest,
    }


def _no_admissible_run_message() -> str:
    lines = ["no admissible run record exists, so there is nothing to compose.",
             "Every candidate and what is wrong with it:"]
    runs = list_runs()
    if not runs:
        lines.append("  (no run records at all)")
    for run in runs[-8:]:
        verdict = admissibility(run)
        lines.append(f"  {run['run_id']}  {verdict.level:<4} {', '.join(verdict.reasons)}")
    lines.append("")
    lines.append("A run that may verify needs a clean tree and a tagged")
    lines.append("preregistration:  python scripts/prereg.py new --tag")
    return "\n".join(lines)


def compose(run_id: str | None = None, events_only: bool = False,
            seed: Path | None = None) -> dict:
    """Fold one run and the whole journal onto the previous ledger.

    `seed` replaces the previous ledger as the fold's starting rows. It exists
    for the one-shot migration, which produces the row CONTENT from named
    artefacts and then hands it here to be folded -- rather than writing a
    ledger itself, which is the thing this whole plan exists to stop.
    """
    events = read_events()
    prev = json.loads(seed.read_text(encoding="utf-8")) if seed else load_previous()

    run = None
    if not events_only:
        if run_id is None:
            run_id = latest_admissible_run_id("R")
            if run_id is None:
                raise SystemExit(_no_admissible_run_message())
        run = load_run(run_id)

        # Gap 1: corroborate the record against things it does not control,
        # before anything it says is allowed to move a row.
        problems = run_integrity(run, path=_run_path(run_id), events=events)
        if problems:
            raise RunIntegrityError(
                f"run {run_id} contradicts facts outside itself:\n  "
                + "\n  ".join(problems)
            )
        # Attest to the bytes, in the chained journal. Idempotent by run_id,
        # so re-composing the same run adds nothing.
        append_event(_run_recorded(run, _run_path(run_id)))
        events = read_events()

    ledger = fold(prev, run=run, candidates=_candidates(run), events=events)
    ledger["events_head"] = head()
    return ledger


def as_findings(ledger: dict) -> list[dict]:
    """Ledger rows in the order the dashboard shows them, worst first."""
    rows = list(ledger.get("findings", {}).values())
    rows.sort(key=lambda r: (
        DISPLAY_RANK.get(display_state(r), 99),
        SEVERITY_RANK.index(r["severity"]) if r.get("severity") in SEVERITY_RANK else 9,
        r["id"],
    ))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ledger.py", description=__doc__)
    parser.add_argument("--run", dest="run_id", default=None,
                        help="run record to compose (default: newest admissible)")
    parser.add_argument("--events-only", action="store_true",
                        help="fold the journal alone, adjudicating no checks")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the committed ledger is not what the "
                             "inputs fold to; writes nothing")
    parser.add_argument("--seed", type=Path, default=None,
                        help="start the fold from these rows instead of the "
                             "committed ledger (one-shot migration only)")
    args = parser.parse_args(argv)

    ledger = compose(run_id=args.run_id, events_only=args.events_only,
                     seed=args.seed)

    if args.check:
        committed = load_previous()
        if committed == ledger:
            print("ledger matches its inputs")
            return 0
        print("the committed ledger is not what its inputs fold to.")
        print("Re-fold it (scripts/ledger.py) rather than editing it.")
        before = {fid: display_state(r)
                  for fid, r in (committed or {}).get("findings", {}).items()}
        after = {fid: display_state(r) for fid, r in ledger["findings"].items()}
        for fid in sorted(set(before) | set(after)):
            if before.get(fid) != after.get(fid):
                print(f"  {fid}: {before.get(fid, '-')} -> {after.get(fid, '-')}")
        return 1

    if "rejected_run" in ledger:
        # Refuse rather than write. Composing an inadmissible record would
        # move nothing anyway, and writing the ledger afterwards would leave
        # a timestamp implying somebody had looked.
        rejected = ledger["rejected_run"]
        print(f"run {rejected['run_id']} is not evidence: "
              f"{', '.join(rejected['reasons'])}")
        print("Nothing written. Fold the journal alone with --events-only, or "
              "produce an admissible run.")
        return 2

    write_ledger(load_previous(), ledger)
    print(f"-> {ledger_path()}")
    if ledger.get("run_carried"):
        # Say which it was. "composed" would claim this fold judged something,
        # and the whole point of --events-only is that it judged nothing.
        print(f"   journal only; rows still stand on {ledger.get('run_id')} "
              f"at level {ledger.get('run_level', '-')}")
    else:
        print(f"   composed run {ledger.get('run_id', '(journal only)')} "
              f"at level {ledger.get('run_level', '-')}")
    print(f"   {ledger['counts']}")
    for row in as_findings(ledger):
        reports = ", ".join(f"#{r['report_id']}" for r in row["filing"]["reports"]) or "-"
        owed = [k for k, v in row["obligations"].items() if v]
        print(f"   {display_state(row):<22} {row.get('severity', '?'):<15} "
              f"{reports:<10} {row['id']}"
              + (f"  OWED: {', '.join(owed)}" if owed else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
