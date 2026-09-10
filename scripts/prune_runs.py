"""Delete run records nothing needs, by name, with the reason printed.

779 records, 74 MB, and nothing has ever removed one. They are gitignored, so
this is local disk only -- but the operator asked not to have to think about
anything growing, and three of the readers here scan every record on disk, so
the pile is a cost even when nobody looks at it.

Nothing is deleted that anything can still cite. The keep set is the union of
five reasons, and each surviving record prints the one that saved it:

    tracked     git has it, so it is evidence somebody committed on purpose
    cited       the ledger, the journal or audits/checks.json names its run id
    young       newer than --older-than days (default 7)
    scope       it holds the newest known definition of a check that still
                exists, which is what the deep pass's audit scope is built from
    last-verdict / last-refusal
                it is the most recent run in which some verdict, or some
                refusal reason, occurred -- what never_fired.py reports on.
                Two names, because two branches writing one word meant
                deleting either left the guard over both of them green
    unreadable  it could not be parsed, so nothing can show it is safe to
                remove. A failed read is not an empty read

    python scripts/prune_runs.py              # say what would go, delete nothing
    python scripts/prune_runs.py --apply

By name, never by glob: a cleanup glob once removed the record the ledger had
just been folded from, which is why the sweep's rules say so in as many words.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.state import journal_path, read_events, runs_dir, state_dir  # noqa: E402


def records_on_disk() -> list[Path]:
    """Every record file. `qa.state.list_runs` parses them; here the FILE is
    the unit, because the whole point is to remove one by name."""
    return sorted(runs_dir().glob("*.json"))


UNREADABLE = "unreadable"


def _load(path: Path) -> dict:
    """The record, or a marker saying it could not be read.

    It returned an empty dict on any failure, and every keep-reason then missed
    the record: no started_at so not young, no results so neither scope nor a
    last occurrence -- and an untracked, uncited one went straight into
    victims() and was deleted. A failed read treated as an empty one, in the
    only script here that removes anything. qa/report_plugin.py writes these
    with a non-atomic write_text, so a record caught mid-write by a concurrent
    pytest parses as garbage; three readers reproduced the deletion.

    Rule 8, and its safe direction: a record we cannot read is one we cannot
    show is safe to remove.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {UNREADABLE: True}


def tracked_records() -> set[str]:
    """What git holds. A committed record is somebody's deliberate evidence."""
    result = subprocess.run(["git", "ls-files", "state/runs"], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        # No git, no answer, and the safe answer is "keep everything".
        return {p.stem for p in records_on_disk()}
    return {Path(line).stem for line in result.stdout.split() if line.strip()}


def cited_run_ids() -> set[str]:
    """Every run id anything in the repository still names.

    Structural rather than a text scan: walk the ledger for any `run_id` key,
    read the journal's run-bearing events, and take the run recorded against
    each audited check. audits/checks.json is in here because it cites 607 of
    them and no existing guard looks at it.
    """
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "run_id" and isinstance(value, str):
                    found.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(_load(state_dir() / "ledger.json"))
    for event in read_events():
        if isinstance(event.get("run_id"), str):
            found.add(event["run_id"])
    audited = _load(REPO_ROOT / "audits" / "checks.json").get("audited") or {}
    for entry in audited.values():
        if isinstance(entry, dict) and isinstance(entry.get("run_id"), str):
            found.add(entry["run_id"])

    # And a run id named in PROSE. The structural walk matches only the literal
    # key run_id, while this function's own claim is "every run id anything in
    # the repository still names". It missed one that matters:
    # run-20260908T150721Z-435ad0b is named inside a withdraw event's reason
    # text, as the capture proving their fix predated our fail verification --
    # the evidence behind the retraction owed on #83. The structural walk
    # returned 170 ids, a text scan 171, and that record survived only as
    # "young", which runs out. Three readers reproduced it.
    pattern = re.compile(r"\brun-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}\b")
    for path in (state_dir() / "ledger.json", journal_path(),
                 REPO_ROOT / "audits" / "checks.json",
                 REPO_ROOT / "audits" / "deep-pass-progress.json"):
        try:
            found.update(pattern.findall(path.read_text(encoding="utf-8")))
        except OSError:
            # Unreadable here is not empty either, but the caller's safe
            # direction is already "keep": a citation we cannot read leaves
            # the record to the other reasons.
            continue
    return found


def _started(record: dict) -> str:
    return str(record.get("started_at") or record.get("finished_at") or "")


def keep_set(older_than_days: int = 7) -> dict[str, str]:
    """run_id -> the reason it survives. Absence from this is the only licence."""
    records = {p.stem: _load(p) for p in records_on_disk()}
    order = sorted(records, key=lambda r: _started(records[r]), reverse=True)
    cutoff = (datetime.now(timezone.utc)
              - timedelta(days=older_than_days)).isoformat()

    keep: dict[str, str] = {}
    for run_id, record in records.items():
        if record.get(UNREADABLE):
            keep.setdefault(run_id, "unreadable")
    for run_id in tracked_records():
        keep.setdefault(run_id, "tracked")
    for run_id in cited_run_ids():
        keep.setdefault(run_id, "cited")
    for run_id in order:
        if _started(records[run_id]) >= cutoff:
            keep.setdefault(run_id, "young")

    # The newest record that knows each live check's current definition. This
    # is the same walk the deep pass's audit scope does, and deleting the only
    # record carrying a fingerprint silently drops that check out of scope --
    # which is the defect that pass found in itself on 2026-09-09, recreated
    # by a tidy-up instead of by a partial run.
    live = _live_nodeids()
    seen_check: set[str] = set()
    seen_symbol: set[str] = set()
    for run_id in order:
        record = records[run_id]
        for result in record.get("results") or []:
            nodeid = result.get("nodeid")
            if nodeid in live and nodeid not in seen_check:
                seen_check.add(nodeid)
                keep.setdefault(run_id, "scope")
            # "last-verdict" and "last-refusal", not one shared word. Both
            # branches wrote "last-fired", so deleting the verdict branch
            # entirely left the guard green -- the refusals branch set the same
            # string on the same fixture record. Three readers reproduced that.
            # Two mechanisms whose output cannot be told apart are one
            # mechanism as far as any test can see.
            verdict = (result.get("measurement") or {}).get("verdict")
            if verdict and verdict not in seen_symbol:
                seen_symbol.add(verdict)
                keep.setdefault(run_id, "last-verdict")
        for reason in _refusals(record):
            if reason not in seen_symbol:
                seen_symbol.add(reason)
                keep.setdefault(run_id, "last-refusal")
    return keep


def _live_nodeids() -> set[str]:
    """Checks that still exist, borrowed from never_fired's own reader."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "never_fired_for_prune", REPO_ROOT / "scripts" / "never_fired.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {f"{path}::{name}" for path, name, _ in module._test_functions()}


def _refusals(record: dict) -> list[str]:
    from qa.state import admissibility

    try:
        return list(admissibility(record).reasons or [])
    except Exception:  # noqa: BLE001 -- a record too broken to judge is not a symbol
        return []


def victims(older_than_days: int = 7) -> list[Path]:
    keep = keep_set(older_than_days)
    return [p for p in records_on_disk() if p.stem not in keep]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="actually delete; without it nothing is touched")
    parser.add_argument("--older-than", type=int, default=7, metavar="DAYS",
                        help="keep everything newer than this (default 7)")
    args = parser.parse_args(argv)

    on_disk = records_on_disk()
    keep = keep_set(args.older_than)
    doomed = [p for p in on_disk if p.stem not in keep]

    # Counted over what is actually here. The keep set legitimately names run
    # ids no longer on disk -- the ledger cites two that were lost before the
    # guard existed -- and reporting those as "kept" would be a number about
    # nothing.
    reasons: dict[str, int] = {}
    for path in on_disk:
        reason = keep.get(path.stem)
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
    print(f"{len(on_disk)} record(s) on disk; keeping {sum(reasons.values())} "
          f"({', '.join(f'{n} {r}' for r, n in sorted(reasons.items()))})")

    if not doomed:
        print("nothing to remove")
        return 0

    freed = sum(p.stat().st_size for p in doomed if p.exists())
    if not args.apply:
        for path in doomed[:10]:
            print(f"  would delete {path.name}")
        if len(doomed) > 10:
            print(f"  ... and {len(doomed) - 10} more")
        print(f"would free {freed / 1048576:.1f} MB. Nothing deleted "
              f"(--apply to do it).")
        return 0

    for path in doomed:
        path.unlink()
    print(f"deleted {len(doomed)} record(s), freed {freed / 1048576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
