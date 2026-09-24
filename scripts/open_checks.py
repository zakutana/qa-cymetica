"""The selector for a sweep that only looks at what is still open.

A full sweep re-adjudicates every row and takes about a minute and a half,
nearly all of it waiting on their server. Most sweeps have nothing to say about
almost all of them: they are verified fixed, withdrawn or superseded, and
re-running them changes a state about as often as never. (This said "all 31
rows" and "29 of those" until 2026-09-09, when the ledger held 41 -- 31 is the
count of VERIFIED FIXED, which is why the wrong number survived: it is still on
the dashboard, against a different label.) The operator asked for the default to
be the two that are actually open, with the full pass kept as its own command.

That is safe, but only because of two things that are easy to get wrong:

  * `tests/meta` is always included, whatever else is selected. Those are the
    self-tests that prove the safety guard blocks -- they run first and abort
    the session on failure, so that a broken guard stops every live request.
    A selector that skipped them would issue live requests with the guard
    unproven, which is worse than a slow sweep. They cost ~18s of the 82.

  * The fold already refuses to close a row it did not run (qa/fold.py, "a
    check that did not run tells us nothing"): the row keeps its state, its
    numbers and the timestamp of the run that last adjudicated it, and gets
    marked `not_checked_in`. The dashboard prints that as "not re-checked",
    so a partial sweep cannot quietly present old readings as fresh.

Rows counted as open are those the sweep's own table gives an action for.
The four it says to skip -- verified fixed, withdrawn, superseded, and passing
but never raised -- are the ones left out.

    python scripts/open_checks.py              # nodeids, one per line
    python scripts/open_checks.py --selector   # one line, for prereg/pytest
    python scripts/open_checks.py --explain    # which rows and why
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qa.fold import display_state  # noqa: E402
from qa.state import ledger_path  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Always run, whatever is open: the guard must be proven before any live
# request. tests/repo is deliberately NOT here -- a stale ledger must not
# abort the run that would fix it.
ALWAYS = ["tests/meta"]

# The four states the sweep's table answers with "nothing to do".
SETTLED = {
    "VERIFIED FIXED",
    "WITHDRAWN",
    "SUPERSEDED",
    "PASSING, NEVER RAISED",
}


def open_rows() -> list[dict]:
    # Through ledger_path(), not a path built here: QA_STATE_DIR is the one
    # seam the whole project reads state behind, and a hard-coded
    # REPO/"state"/"ledger.json" made this the exception -- a test pointing
    # QA_STATE_DIR at a temp tree would have got the committed ledger back
    # and built a selector out of production rows.
    path = ledger_path()
    if not path.exists():
        raise SystemExit(f"no ledger at {path}; run a full sweep first")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    findings = ledger["findings"]
    rows = list(findings.values()) if isinstance(findings, dict) else findings
    return [r for r in rows if display_state(r) not in SETTLED]


def since_last_full_run() -> str:
    """How long since a run offered the whole suite, in words.

    The narrow sweep cannot see a settled row regress: a VERIFIED FIXED row is
    not in the selector, so nothing re-runs its check and nothing notices when
    the platform takes the fix back. On 2026-09-07 two had, and both had been
    sitting green -- one of them a side effect of a fix shipped that same day.

    Only a full run can also tell a check that is GONE from one that merely
    did not run, which is the other reason to say this out loud here, where
    the width is being chosen.
    """
    from qa.state import list_runs

    # And judged something on their side: `pytest --collect-only tests` is
    # selector_full with zero results, and tests/repo spawns one every
    # session; a full run the meta gate aborted has results, every one of
    # them tests/meta (R01, deep pass of 2026-09-22 evening).
    # And JUDGED it: passed or failed. A run in an outage where every one of
    # their checks came back inconclusive measured nothing (rule 10), and
    # read as the last full run (B09, deep pass of 2026-09-24).
    def judged_theirs(run: dict) -> bool:
        return any(not str(r.get("nodeid") or "").replace("\\", "/")
                   .startswith(("tests/meta/", "tests/repo/"))
                   and r.get("outcome") in ("passed", "failed")
                   for r in run.get("results") or [])

    full = [r for r in list_runs() if r.get("selector_full") and judged_theirs(r)]
    if not full:
        return ("no run on record ever offered the whole suite -- a narrow "
                "sweep cannot see a settled row regress")

    newest = max(full, key=lambda r: r.get("started_at") or "")
    at = newest.get("started_at") or "?"
    try:
        from datetime import datetime, timezone
        hours = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(at)).total_seconds() / 3600
    except (TypeError, ValueError):
        return f"last full run {at} ({newest.get('run_id')})"

    when = f"{hours:.0f}h ago" if hours < 48 else f"{hours / 24:.0f} days ago"
    note = "" if hours < 24 else "  <- the settled rows have not been re-checked since"
    return f"last full run {when}, {at} ({newest.get('run_id')}){note}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selector", action="store_true",
                    help="print one space-joined line instead of one per line")
    ap.add_argument("--explain", action="store_true",
                    help="print the rows behind the selector, with their state")
    args = ap.parse_args()

    rows = open_rows()
    checks: list[str] = []
    for row in rows:
        for nodeid in row.get("checks") or []:
            if nodeid not in checks:
                checks.append(nodeid)

    if args.explain:
        if not rows:
            print("nothing open; a sweep would run tests/meta only")
        for row in rows:
            print(f"{display_state(row):<22} {row['id']}")
            for nodeid in row.get("checks") or []:
                print(f"{'':<22}   {nodeid}")
        print(f"\n{len(rows)} open row(s), {len(checks)} check(s), "
              f"plus {' '.join(ALWAYS)}")
        print(since_last_full_run())
        return

    parts = ALWAYS + checks
    if args.selector:
        # Quoted: nodeids carry :: and [] that a shell would otherwise eat.
        print(" ".join(f'"{p}"' if "::" in p else p for p in parts))
    else:
        for part in parts:
            print(part)


if __name__ == "__main__":
    main()
