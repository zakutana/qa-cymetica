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
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import findings as findings_mod  # noqa: E402

from qa import keepset  # noqa: E402
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


def _track_run_record(run_id: str | None) -> None:
    """Keep the record this ledger stands on; let the exploratory ones go.

    `state/runs/` is gitignored, because most of what lands there adjudicated
    nothing -- 237 of 283 records on the day this was written -- while every
    one of them made the tree dirty enough for prereg.py to refuse, so each
    sweep began by committing debug output.

    A record becomes evidence at exactly one moment: when the journal attests
    it. So this is called from there, on the next line, and not from main()
    after the write -- a write that can be refused, and was.

    Failing to track it is worth a warning and not an abort: the attestation
    is already in an append-only journal by then, so stopping here would not
    unmake the citation, and tests/repo names the record until somebody does
    add it.
    """
    if not run_id:
        return
    path = _run_path(run_id)
    if path is None:
        return
    import subprocess

    try:
        subprocess.run(["git", "add", "-f", str(path)],
                       cwd=path.parents[2], check=True,
                       capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:  # noqa: BLE001
        print(f"   WARNING: could not track {path.name}: {exc}. The ledger "
              f"cites a run record that is not in the repository; "
              f"tests/repo will fail until it is.")


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


def _settled(run: dict) -> set:
    """The checks this run actually ADJUDICATED.

    Not `collected`. A nodeid is in `collected` whether it ran, was skipped,
    errored, or was never executed at all -- `pytest --collect-only` writes a
    schema-2 record with every nodeid collected, zero results and exit 0,
    which passes every rule in qa/state.py. On 2026-09-20 there were 113 such
    records of 496 on disk, 111 of them from a collection, and the first
    version of this function walked back from one empty run to another and
    picked one: 1053 collected, 0 results, 59 of 63 rows satisfying
    `checks <= collected` and not one of them adjudicated.

    So this is the same condition `qa/fold.py::_apply_run` uses before it
    moves anything: a result exists and its outcome is neither skipped nor an
    error. Two readers found the gap from different angles, which is what it
    took -- the docstring said "settled" and the code said "collected" for
    the whole of the day it was written in.
    """
    return {r["nodeid"] for r in (run.get("results") or [])
            if r.get("nodeid") and r.get("outcome") not in ("skipped", "error")}


def _run_that_adjudicates(prev: dict, runs: Path | None = None) -> str | None:
    """The newest admissible run that settled at least one row of the ledger.

    Admissible is not the same as relevant. On 2026-09-12 a fold with no
    `--run` took a `tests/meta tests/repo` run of my own -- admissible,
    newest, and measuring nothing from their platform. No row moved, because
    the fold never closes what it did not run, but the page describes the run
    the ledger was composed from, so every section tile emptied.

    "Settled" is rule 1: EVERY check the row declares, adjudicated by this
    run. Half a row's checks adjudicates none of it. An empty ledger has no
    rows to judge, so there the newest admissible run is the answer -- the
    first fold must not be unfoldable.
    """
    declared = [set(row.get("checks") or [])
                for row in (prev.get("findings") or {}).values()]
    declared = [checks for checks in declared if checks]
    admissible = [run for run in list_runs(runs=runs)
                  if admissibility(run).level in {"R", "V"}]
    if not admissible:
        return None
    if not declared:
        return admissible[-1]["run_id"]
    for run in reversed(admissible):  # list_runs is sorted ascending
        settled = _settled(run)
        if any(checks <= settled for checks in declared):
            return run["run_id"]
    return None


def _nothing_adjudicating_message(prev: dict) -> str:
    rows = len([row for row in (prev.get("findings") or {}).values()
                if row.get("checks")])
    newest = latest_admissible_run_id("R")
    return "\n".join([
        f"the newest admissible run ({newest}) settled none of the {rows} "
        "row(s) the ledger declares checks for, and neither did any older "
        "one.",
        "Composing from it would describe the page with a run that measured "
        "something else.",
        "",
        "Run the checks first (see the qa-sweep skill), or name the run you "
        "mean with --run <id>.",
    ])


def compose(run_id: str | None = None, events_only: bool = False,
            attest: bool = False) -> dict:
    """Fold one run and the whole journal onto the previous ledger.

    `attest` appends the `run_recorded` event that pins the record's bytes, and
    is OFF by default because most callers here are not writing a ledger. It
    used to be unconditional, so a fold performed only to look -- the page's
    field-coverage check in tests/meta/test_pipeline_render.py folds fresh on
    every session -- wrote into the append-only journal, attesting whatever run
    was newest, which was that session's own exploratory record. 98 of the 137
    run_recorded events on 2026-09-07 cite a run the ledger never used. None of
    them moved a row; the fold does not read this event type at all. What they
    did was fill the audit trail with attestations of runs nobody stood on, and
    -- once state/runs/ became gitignored -- cite records that would never be
    tracked. Default-off means a caller that only looks cannot write by
    accident; only main() asks for it, and then only for a fold that took the
    run and is about to be written.
    """
    events = read_events()
    prev = load_previous()

    run = None
    if not events_only:
        if run_id is None:
            if latest_admissible_run_id("R") is None:
                raise SystemExit(_no_admissible_run_message())
            run_id = _run_that_adjudicates(prev)
            if run_id is None:
                raise SystemExit(_nothing_adjudicating_message(prev))
        run = load_run(run_id)

        # Gap 1: corroborate the record against things it does not control,
        # before anything it says is allowed to move a row.
        problems = run_integrity(run, path=_run_path(run_id), events=events)
        if problems:
            raise RunIntegrityError(
                f"run {run_id} contradicts facts outside itself:\n  "
                + "\n  ".join(problems)
            )
    ledger = fold(prev, run=run, candidates=_candidates(run), events=events)

    # Attest to the bytes, in the chained journal. Idempotent by run_id, so
    # re-composing the same run adds nothing.
    #
    # After the fold, and only if the fold took the run. Attesting before it
    # meant an INADMISSIBLE run was pinned too: compose() appended, fold()
    # then set rejected_run, and main() printed "is not evidence" and returned
    # without writing a ledger -- leaving the journal permanently vouching for
    # a record nothing stands on, which is the same stray attestation the
    # `attest` flag exists to stop. The fold never reads this event type, so
    # moving it after costs nothing and saves a second read of the journal.
    #
    # Tracked in the same breath as the attestation, because the journal is
    # append-only and write_ledger can still refuse what follows. It did, at
    # 12:18 today: the ledger was rejected as not forward-only, main() never
    # reached the `git add -f` it used to do afterwards, and the journal was
    # left permanently citing run-20260907T121855Z-ee26eda while the record
    # itself stayed gitignored and unclonable. One statement between the two
    # was enough to split a pair that has to hold.
    if attest and run is not None and "rejected_run" not in ledger:
        append_event(_run_recorded(run, _run_path(run_id)))
        _track_run_record(run_id)

    # Read AFTER the append: write_ledger refuses a ledger whose events_head
    # is not the journal's current head (qa/state.py).
    ledger["events_head"] = head()
    return ledger


def drift(committed: dict, refolded: dict, events: Sequence[dict]) -> dict:
    """Rule 12, asked as one question: are the committed rows what the inputs
    fold to?

    One definition, called by `--check` and by tests/repo, so the CLI and the
    guard cannot grow two ideas of what "stale" means.

    Everything is compared against a refold over the WHOLE journal, pending
    events included, so an event that would move something turns this red
    whether or not anybody has folded it yet. The one key held out is
    `events_head`, and holding it out is the change:

      Until 2026-09-09 it was compared like any other key. It is the journal's
      head at the moment of the compose, so `serve.py --ask 15` -- two
      `vendor_read` events per tick, which the fold reads only to set or clear
      `stale_from`, and an `ok` read moves nothing -- put this guard in the red
      within fifteen minutes of every fold and left it there until the next
      one. The comment that widened the comparison (tests/repo, 2026-09-07)
      wanted "an events_head left behind by a bounty.py run nobody re-folded",
      and that reading conflated two questions: whether the ledger is BEHIND
      the journal, and whether it is NOT WHAT ITS INPUTS FOLD TO. The second is
      rule 12 and is kept exactly, by the rows. The first is answered at the
      moment of the write, by `write_ledger`, which refuses a ledger whose head
      is not the journal's head; that invariant is untouched.

    So the head is checked as a CITATION: the line it names must be a line the
    journal really has, at that seq, with that chain. A ledger folded against
    some other journal -- a temp state directory leaking in, a journal rewritten
    underneath it -- names a line that is not there.

    What this no longer catches, stated plainly rather than discovered later: a
    head hand-rolled BACKWARDS to an older line the journal really has. It
    anchors, over-reports the suffix, and changes nothing else, because the rows
    are still compared against the whole journal. `write_ledger` refuses to
    write such a ledger in the first place.

    Returns `rows`, `keys`, `anchored`, `since_head` (the pending suffix counted
    by type -- a report, never the verdict) and a `reason` in English.
    """
    from collections import Counter

    head_cited = committed.get("events_head") or {}
    seq, chain = head_cited.get("seq"), head_cited.get("chain")

    if seq == 0 and chain == "":
        # The empty prefix, which every journal has. This is what head() gives
        # before the first event, and it is a citation like any other.
        anchored, pending = True, list(events)
    elif isinstance(seq, int) and 1 <= seq <= len(events) \
            and events[seq - 1].get("chain") == chain:
        anchored, pending = True, list(events[seq:])
    else:
        anchored, pending = False, []

    committed_rows = committed.get("findings") or {}
    refolded_rows = refolded.get("findings") or {}
    rows = sorted(fid for fid in set(committed_rows) | set(refolded_rows)
                  if committed_rows.get(fid) != refolded_rows.get(fid))
    keys = sorted(key for key in set(committed) | set(refolded)
                  if key not in ("findings", "events_head")
                  and committed.get(key) != refolded.get(key))
    since_head = dict(Counter(e.get("type") for e in pending))

    if not anchored:
        reason = (f"the ledger cites journal head {head_cited}, and the journal "
                  f"has no such line: it holds {len(events)} event(s)"
                  + (f" and line {seq} is {events[seq - 1].get('chain')!r}"
                     if isinstance(seq, int) and 1 <= seq <= len(events) else ""))
    elif rows:
        reason = (f"{len(rows)} committed row(s) are not what the journal and "
                  f"run records fold to: {rows}")
    elif keys:
        reason = (f"the committed rows fold correctly, but {len(keys)} "
                  f"top-level key(s) of the ledger do not: {keys}")
    else:
        pending_says = (", ".join(f"{n} {t}" for t, n in sorted(since_head.items()))
                        if since_head else "nothing")
        reason = (f"the committed ledger matches its inputs; anchored at journal "
                  f"event {seq} of {len(events)}, {pending_says} since, "
                  f"none moved a row")

    return {"rows": rows, "keys": keys, "anchored": anchored,
            "since_head": since_head, "reason": reason}


def refold_recipe(committed: dict) -> dict:
    """The inputs that produced this ledger, so a refold can use the same ones.

    Both `--check` and rule 12's guard used to refold through the run branch
    whatever the committed ledger was made of. A ledger folded by
    `ledger.py --events-only` -- the path `scripts/withdraw.py` prints after
    every withdrawal, and the one `main()` offers below as the remedy --
    carries `run_carried`, which the run branch never sets. So the refold
    differed from the committed ledger by exactly that key, and both the CLI
    and the guard reported a ledger wrong that was precisely what its inputs
    fold to. The same class of boring red the `events_head` change removed on
    2026-09-09, arriving the same day through a different key. Found by the
    deep pass, three votes of three.
    """
    if committed.get("run_carried"):
        return {"run_id": None, "events_only": True}
    return {"run_id": committed.get("run_id"), "events_only": False}


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
    args = parser.parse_args(argv)

    if args.check:
        # Refold through the branch that PRODUCED this ledger, against the run
        # it cites rather than whichever is newest. Folding --check against
        # "latest admissible" made it answer about a different document: every
        # pytest session writes a run record, so the newest is usually some
        # two-test re-run and every row it did not collect reads
        # not_checked_in. And always taking the RUN branch made it disagree by
        # `run_carried` with any ledger folded by --events-only, which is the
        # path withdraw.py prints after every withdrawal.
        committed = load_previous() or {}
        recipe = refold_recipe(committed)
        run_id = args.run_id if args.run_id is not None else recipe['run_id']
        events_only = args.events_only or recipe['events_only']
        try:
            ledger = compose(run_id=run_id, events_only=events_only,
                             attest=False)
        except KeyError as exc:
            # The ledger names a run record that is not here. state/runs/ is
            # gitignored with only the cited records force-tracked, and
            # _track_run_record downgrades a tracking failure to a warning, so
            # a committed ledger CAN cite a record that never reached the
            # repository. This was the guard you would run to find that out,
            # dying with a traceback instead of saying it. Found 2026-09-09.
            print(f'the committed ledger cites run {exc.args[0]!r} and no '
                  f'record in {runs_dir()} carries that id. Without it nothing '
                  f'can say whether these rows are what their inputs fold to.')
            return 1
        if 'rejected_run' in ledger:
            # compose() already worked out WHY, and --check used to return
            # before the block that prints it -- so the operator got a generic
            # key-drift message and advice to re-fold, which would exit 2 and
            # write nothing. Found 2026-09-09.
            bad = ledger['rejected_run']
            print(f"the committed ledger stands on run {bad['run_id']}, "
                  f"which is not admissible: {', '.join(bad['reasons'])}. "
                  f"Re-folding cannot fix that; produce an admissible run, "
                  f"or fold the journal alone with --events-only.")
            return 1
        verdict = drift(committed, ledger, read_events())
        print(verdict['reason'])
        if not (verdict['rows'] or verdict['keys']) and verdict['anchored']:
            return 0
        print('Re-fold it (scripts/ledger.py) rather than editing it.')
        before = {fid: display_state(r)
                  for fid, r in committed.get('findings', {}).items()}
        after = {fid: display_state(r) for fid, r in ledger['findings'].items()}
        for fid in sorted(set(before) | set(after)):
            if before.get(fid) != after.get(fid):
                print(f"  {fid}: {before.get(fid, '-')} -> {after.get(fid, '-')}")
        return 1

    # --check returned above, so this is always True -- written as the
    # expression anyway, because tests/meta pins it: a fold that writes no
    # ledger must write nothing to the journal, and the pin is what stops a
    # restructure attesting during a read-only check. It caught this one.
    ledger = compose(run_id=args.run_id, events_only=args.events_only,
                     attest=not args.check)

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

    # The run record was tracked by compose(), beside the attestation that
    # cites it -- not here, where a refused write skips it.
    write_ledger(load_previous(), ledger)
    print(f"-> {ledger_path()}")

    # A fold is when a row starts standing on a new run, and what a row stands
    # on is what our next verdict will tell them is "provided on request".
    # evidence/ is gitignored, so those captures have to be force-added: the
    # commit hook does it for every commit, and this does it at the moment the
    # citation is made, so the commit that follows finds them staged already.
    keepset.track(quiet=True)
    # And let go of what the PREVIOUS run's rows cited and these no longer do.
    # The fold is the only moment the keep set shrinks, and until 2026-09-12
    # nothing shrank it: folding onto a fresh verification run left 115
    # captures tracked with nothing standing on them, the guard went red, and
    # the only cure was `git rm --cached` by hand.
    keepset.untrack(quiet=True)
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
