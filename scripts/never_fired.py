"""Which of our mechanisms have never once produced an effect.

A green test says a mechanism would work if it ran. It says nothing about
whether it has ever run. On 2026-09-06, three mechanisms here had never fired
in the whole life of the project -- `stale_from`, the obligations block, and
`selector_full` -- and two of them were broken. 289 passing guards did not
notice, because each one exercised its mechanism itself and then went home.
Counting occurrences in the real data found all three in a few minutes.

This is that question, made repeatable. For every vocabulary the code can
produce -- the two axes' states, the verdicts, the journal's event types, the
reasons a run can be refused, the obligations a row can carry -- count how
often the ledger, the journal and the run records actually contain it, and
print the zeros first.

A zero is not automatically a bug. Some of these describe conditions we hope
never to meet, and the report cannot tell those from the ones that are wired
wrong. What it can do is put the question in front of someone, which is the
part that was missing: by the next session an unfired mechanism looks exactly
like a working one.

Read as: what the code offers, against what the world has ever asked of it.

    python scripts/never_fired.py            # everything
    python scripts/never_fired.py --zeros    # only what has never fired

Parses every run record -- 297 of them, 29 MB of JSON on 2026-09-07 -- in
about half a second. Cheap enough to be a step in the sweep rather than a
thing you decide to do.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qa.fold import CHECK_STATES, FILING_STATES  # noqa: E402
from qa.measure import VERDICTS  # noqa: E402
from qa.state import (EVENT_TYPES, admissibility, ledger_path,  # noqa: E402
                      list_runs, read_events)

# The two short vocabularies with no constant to import. They are literals in
# the source, and tests/meta/test_pipeline_never_fired.py scans that source and
# fails if either list drifts from it -- so a new block reason or obligation
# cannot be added without showing up here.
BLOCK_REASONS = (
    "legacy_schema", "no_fingerprint", "fingerprint_drifted",
    "results_not_collected", "exit_status_disagrees",
    "git_dirty", "no_prereg", "prereg_commit_mismatch",
)
OBLIGATIONS = ("reverify", "repair_check", "reopen", "retractions")


def _ledger() -> dict:
    path = ledger_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _states(ledger: dict, axis: str) -> tuple[Counter, dict[str, str]]:
    """Every state each row has ever occupied on this axis.

    Transitions record where a row went, never where it started, so counting
    only `to` reported UNVERIFIED and NOT_RAISED as never reached -- the two
    states every row is born in. The first transition's `from` is that birth,
    and a row with no transition on the axis has only ever been where it is.
    """
    seen: Counter = Counter()
    last: dict[str, str] = {}

    def note(state: str, at: str) -> None:
        seen[state] += 1
        if at > last.get(state, ""):
            last[state] = at

    for row in (ledger.get("findings") or {}).values():
        moves = [t for t in (row.get("transitions") or [])
                 if t.get("axis") == axis and t.get("to")]
        moves.sort(key=lambda t: t.get("at") or "")
        if moves:
            if moves[0].get("from"):
                note(moves[0]["from"], (row.get("first_seen") or {}).get("at") or "")
            for t in moves:
                note(t["to"], t.get("at") or "")
        else:
            current = (row.get(axis) or {}).get("state")
            if current:
                note(current, (row.get("first_seen") or {}).get("at") or "")
    return seen, last


def _verdicts(runs: list[dict]) -> tuple[Counter, dict[str, str]]:
    seen: Counter = Counter()
    last: dict[str, str] = {}
    for run in runs:
        at = run.get("started_at") or ""
        for result in run.get("results") or []:
            # The verdict lives on the measurement, not beside pytest's
            # outcome: a result with `measurement: null` is a test that ran
            # without concluding one, and has no verdict to count.
            v = (result.get("measurement") or {}).get("verdict")
            if v:
                seen[v] += 1
                if at > last.get(v, ""):
                    last[v] = at
    return seen, last


def _events() -> tuple[Counter, dict[str, str]]:
    seen: Counter = Counter()
    last: dict[str, str] = {}
    for event in read_events():
        t = event.get("type")
        if t:
            seen[t] += 1
            at = event.get("at") or ""
            if at > last.get(t, ""):
                last[t] = at
    return seen, last


def _blocks(runs: list[dict]) -> tuple[Counter, dict[str, str]]:
    seen: Counter = Counter()
    last: dict[str, str] = {}
    for run in runs:
        at = run.get("started_at") or ""
        # `reasons` only, never `notes`: identity_absent:<name> qualifies a
        # level rather than blocking one, and lives on the other field. Counted
        # whole, so a reason this report does not know about shows up as
        # itself and fails the guard test instead of being trimmed into
        # something that looks familiar.
        for reason in admissibility(run).reasons:
            seen[reason] += 1
            if at > last.get(reason, ""):
                last[reason] = at
    return seen, last


def _obligations(ledger: dict) -> tuple[Counter, dict[str, str]]:
    seen: Counter = Counter()
    for row in (ledger.get("findings") or {}).values():
        for name, value in (row.get("obligations") or {}).items():
            if value:
                seen[name] += 1
    return seen, {}


def vocabularies() -> list[dict]:
    """Every vocabulary, its symbols, and how often each has occurred."""
    ledger = _ledger()
    runs = list_runs()

    check_seen, check_last = _states(ledger, "check")
    filing_seen, filing_last = _states(ledger, "filing")
    verdict_seen, verdict_last = _verdicts(runs)
    event_seen, event_last = _events()
    block_seen, block_last = _blocks(runs)
    ob_seen, ob_last = _obligations(ledger)

    return [
        {"name": "check states", "over": "ledger transitions and current rows",
         "symbols": CHECK_STATES, "seen": check_seen, "last": check_last},
        {"name": "filing states", "over": "ledger transitions and current rows",
         "symbols": FILING_STATES, "seen": filing_seen, "last": filing_last},
        {"name": "verdicts", "over": f"results in {len(runs)} run records",
         "symbols": VERDICTS, "seen": verdict_seen, "last": verdict_last},
        {"name": "journal events", "over": "the journal",
         "symbols": tuple(sorted(EVENT_TYPES)), "seen": event_seen,
         "last": event_last},
        {"name": "run refusals", "over": f"admissibility of {len(runs)} run records",
         "symbols": BLOCK_REASONS, "seen": block_seen, "last": block_last},
        # An obligation that was raised and then cleared leaves no trace: the
        # ledger holds only what is owed NOW, and transitions record the axes,
        # not the obligations. A zero here means "not owed today", which is a
        # weaker statement than every other line in this report.
        {"name": "obligations", "over": "the CURRENT ledger only",
         "symbols": OBLIGATIONS, "seen": ob_seen, "last": ob_last},
    ]


def render(vocabs: list[dict], zeros_only: bool = False) -> str:
    lines: list[str] = []

    never = [(v["name"], s) for v in vocabs
             for s in v["symbols"] if not v["seen"].get(s)]
    if never:
        lines.append(f"NEVER FIRED -- {len(never)} of "
                     f"{sum(len(v['symbols']) for v in vocabs)}")
        for name, symbol in never:
            lines.append(f"  {symbol:<26} {name}")
        lines.append("")
        lines.append("A zero can be a condition we have been lucky enough not to")
        lines.append("meet, or a mechanism that has never worked. This cannot tell")
        lines.append("them apart; that is the reading it is asking for.")
    else:
        lines.append("every mechanism has fired at least once")
    if zeros_only:
        return "\n".join(lines)

    for v in vocabs:
        lines.append("")
        lines.append(f"{v['name']}  ({v['over']})")
        for symbol in v["symbols"]:
            count = v["seen"].get(symbol, 0)
            last = (v["last"].get(symbol) or "")[:16].replace("T", " ")
            mark = "  " if count else "->"
            lines.append(f"  {mark} {symbol:<26} {count:>6}  {last}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="never_fired.py", description=__doc__)
    parser.add_argument("--zeros", action="store_true",
                        help="print only the mechanisms that have never fired")
    args = parser.parse_args(argv)
    print(render(vocabularies(), zeros_only=args.zeros))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
