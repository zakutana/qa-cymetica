"""What each deep pass cost and what it caught, from the passes' own notebooks.

The pass reviews the repository and never itself. It records a great deal --
every claimed gap, who voted which way, what was fixed and in which commit --
and then that file is overwritten by the next run, so the material for "is
this process still worth what it costs" exists only in git history and nothing
has ever read it.

That question is the operator's, asked on 2026-09-10: *"ten se taky umi
optimalizovat? ze treba casem zjisti ze je zbytecne porad spoustet tu triadu
agentu na verifikaci"*. It cannot be answered from one pass. It can be
answered from the series, and this prints the series:

    python scripts/deep_pass_process.py
    python scripts/deep_pass_process.py --json

The column that decides the triad's fate is `overturned` -- claims a reader
brought that two of three triage agents rejected. That is the number of false
findings the triad removed. If it is zero for three passes running, the triad
is voting unanimously on everything it sees and the second and third readers
are ceremony; `condition()` says so in one line, and dropping it then goes
through the deep pass's own rule 1c (three agents, a test naming the incident,
a paragraph in the report) rather than through anybody's impression.

It reads only committed history, so it is safe to run at any time and says the
same thing to the pass, to the console and to the operator.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRESS = "audits/deep-pass-progress.json"

# A pass whose triad rejected nothing for this many runs is one whose second
# and third readers have never changed an outcome.
QUIET_PASSES = 3


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    return result.stdout if result.returncode == 0 else ""


def _run_key(data: dict, fallback: str = "") -> str:
    return str(data.get("run") or data.get("at") or fallback)


def working_copy() -> dict | None:
    """The notebook as it stands on disk, or None if it cannot be read."""
    try:
        return json.loads((REPO_ROOT / PROGRESS).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def overlay_working(seen: dict[str, dict], working: dict | None) -> dict[str, dict]:
    """The file on disk is the newest state of its run, committed or not.

    Without this the series could only ever see a pass as it was at its
    second-to-last commit, and the dashboard's Stats panel reads these rows.
    On 2026-09-12 the pass rendered the page at 23:04 and finalised its own
    notebook at 23:15, so the committed page said `finished: false` with no
    `elapsed_min` -- and rule 12's guard, which rebuilds the payload and holds
    it against the page, was red on `main` from then until somebody noticed.
    Every pass ends that way by construction: the row is about the run that is
    doing the rendering, and that run cannot be finished while it renders.

    Replacing in place rather than appending: dicts keep insertion order, the
    run is normally already the newest key, and a pass that has not committed
    its notebook at all belongs at the end where it in fact is.
    """
    if not isinstance(working, dict):
        return seen
    run = _run_key(working)
    if not run:
        return seen
    seen[run] = working
    return seen


def versions() -> list[dict]:
    """Every COMMITTED state of the progress file, oldest first.

    Keyed on `run` and keeping the LAST version of each: a pass writes its
    notebook as it goes, so the same run appears in five or six commits and
    only the final one is complete.

    Committed and nothing else, on purpose. This is the series -- what the
    retrospective judges and what `test_the_committed_history_reads` holds its
    assertions against -- and a run still being written is not yet part of it.
    The page wants the other answer and asks `series()` for it.
    """
    seen: dict[str, dict] = {}
    for line in reversed(_git("log", "--format=%H", "--", PROGRESS).split()):
        blob = _git("show", f"{line}:{PROGRESS}")
        if not blob.strip():
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        seen[_run_key(data, line[:12])] = data
    return list(seen.values())


def series() -> list[dict]:
    """The committed history with the notebook on disk on top of its own run.

    What the dashboard renders. Two named functions rather than one with a
    flag, because a default argument only the test ever passes is how a brake
    ends up switched off on the single path that matters.
    """
    seen = {_run_key(d, str(i)): d for i, d in enumerate(versions())}
    return list(overlay_working(seen, working_copy()).values())


def _moment(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def passes(all_versions: list[dict] | None = None) -> list[dict]:
    """One row per pass: what it claimed, what survived, what it cost.

    `overturned` counts claims a reader made that the triage agents rejected,
    which is the only measure of what the triad is for. `unanimous` counts the
    gaps where all three votes agreed -- a triad that is always unanimous is
    one reader with two echoes.
    """
    rows = []
    for data in (versions() if all_versions is None else all_versions):
        gaps = data.get("gaps") or []
        votes_cast = [g for g in gaps if len(_spoken(g)) == 3]
        started, ended = _moment(data.get("at")), _moment(data.get("at_finished"))
        meta = data.get("meta_tests") or {}
        rows.append({
            "run": data.get("run"),
            "at": data.get("at"),
            "finished": bool(data.get("finished")),
            "claimed": len(gaps),
            "real": sum(1 for g in gaps if g.get("verdict") == "real"),
            "minority": sum(1 for g in gaps if g.get("verdict") == "minority"),
            "dropped": sum(1 for g in gaps if g.get("verdict") == "dropped"),
            "undecided": sum(1 for g in gaps if not g.get("verdict")),
            "by_source": _count(g.get("source") for g in gaps),
            "voted": len(votes_cast),
            "unanimous": sum(1 for g in votes_cast
                             if len(set(_spoken(g))) == 1),
            # What the triad actually removed. Zero means every claim that
            # reached it survived it.
            "overturned": sum(1 for g in gaps
                              if g.get("verdict") in ("dropped", "minority")),
            "fixed": sum(1 for g in gaps if g.get("fixed")),
            "elapsed_min": (round((ended - started).total_seconds() / 60)
                            if started and ended else None),
            "meta_tests": [meta.get("start"), meta.get("end")],
            "rule_changes": len(data.get("rule_changes") or []),
        })
    return rows


def _spoken(gap: dict) -> list[str]:
    return [str(v).strip().lower()
            for v in (gap.get("votes") or {}).values() if str(v).strip()]


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value or "unsaid")
        out[key] = out.get(key, 0) + 1
    return out


def condition(rows: list[dict]) -> str | None:
    """The one sentence the series is able to say about the triad.

    Only when there are enough finished passes to say it, and only when every
    one of the newest QUIET_PASSES removed nothing. Anything less is an
    impression, and this file exists to stop the pass forming one about itself.
    """
    finished = [r for r in rows if r["finished"] and r["claimed"]]
    if len(finished) < QUIET_PASSES:
        return None
    recent = finished[-QUIET_PASSES:]
    if any(r["overturned"] for r in recent):
        return None
    return (f"the triage triad has removed no claim in the last "
            f"{QUIET_PASSES} passes ({', '.join(r['run'] or '?' for r in recent)}) "
            f"-- a candidate for rule 1c, which is where dropping it belongs")


def render(rows: list[dict]) -> str:
    if not rows:
        return "no deep pass has committed a notebook yet"
    head = (f"{'pass':22} {'claimed':>7} {'real':>5} {'over':>5} {'fixed':>5} "
            f"{'unan':>5} {'min':>5} {'rules':>5}")
    lines = [head, "-" * len(head)]
    for row in rows:
        lines.append(
            f"{str(row['run'] or '?'):22} {row['claimed']:>7} {row['real']:>5} "
            f"{row['overturned']:>5} {row['fixed']:>5} "
            f"{str(row['unanimous']) + '/' + str(row['voted']):>5} "
            f"{str(row['elapsed_min'] or '?'):>5} {row['rule_changes']:>5}")
    lines.append("")
    lines.append("over  = claims the three readers rejected; the triad's whole output")
    lines.append("unan  = gaps where all three agreed / gaps that got three votes")
    lines.append("min   = minutes from the pass's first note to its last")
    verdict = condition(rows)
    lines.append("")
    lines.append(verdict if verdict else
                 "the triad is still removing claims, so it is still paying for itself")
    return "\n".join(lines)


# --- how big tonight's pass is (plan v2, V7) --------------------------------
#
# The architect's review of 2026-09-23: the pass's self-maintenance was sized
# for a team while it runs on one Pro plan. So a pass is as big as its diff.

# What makes a pass full: anything that is not known to be harmless. The first
# draft listed what was dangerous instead -- the core, a check, six vendor-
# facing scripts -- and all three 1c readers found paths it called light that
# POST to their platform (nexus.py, paper.py, clone.py, bounty.py) or decide
# what the ledger says (ledger.py, findings.py, qa/fingerprint.py). A list of
# the harmless cannot miss a dangerous file added next month; that one could.
CORE = ("qa/state.py", "qa/fold.py", "qa/measure.py")
# Prose only. The second draft also listed tests/meta, tests/repo, audits/,
# the session-start hooks and processes.py -- a 1c reader pointed out those ARE
# the guards -- and the third listed two page scripts, which a reader showed
# write state/ and load the scripts that POST to their platform.
LIGHT_SAFE = ("docs/", "dashboard/", "NEXT.md", "DEEP-PASS.md", "ARCHITECTURE.md")
FULL_COMMITS = 15
# V7's line for the week. At this much of it spent the pass does not run at
# all: it writes nothing, sends nothing, and the reminder keeps saying one is
# owed. Three rounds of 1c readers found a "minimal" pass that gated and
# reported without reviewing could still push, still verify, silence the
# reminder or fail its own guard; not running has none of those failures.
DEFER_WEEKLY_PCT = 85


def _is_check(path: str) -> bool:
    return (path.startswith("tests/") and path.endswith(".py")
            and not path.startswith(("tests/meta/", "tests/repo/")))


def pass_size(files: list[str], commits: int, weekly_pct) -> tuple[str, str]:
    """`full`, `light` or `deferred`, and the reason, from the unpushed diff's
    files, its commit count and the week's use of the plan."""
    try:
        weekly = float(weekly_pct)
    except (TypeError, ValueError):
        return "deferred", "the week's use could not be read"
    if weekly >= DEFER_WEEKLY_PCT:
        return "deferred", f"{weekly:g} % of the week is spent"
    core = [f for f in files if f in CORE]
    if core:
        return "full", f"the core moved: {', '.join(core)}"
    checks = [f for f in files if _is_check(f)]
    if checks:
        return "full", f"{len(checks)} check(s) against their platform moved"
    other = [f for f in files if not f.startswith(LIGHT_SAFE)]
    if other:
        return "full", f"not known harmless: {', '.join(other[:3])}"
    if commits >= FULL_COMMITS:
        return "full", f"{commits} commits"
    return "light", (f"{commits} commit(s), {len(files)} file(s), every one "
                     f"prose")


def carried_gaps(previous: dict) -> list[dict]:
    """What the last pass confirmed or claimed and did not fix -- carried into
    the next notebook, never overwritten (E5). A claim the triage never
    reached is carried too, to be triaged again. One handed to the operator
    is carried only when that pass died: then its report was never written,
    so the operator was never shown it (a 1c reader, 2026-09-23)."""
    run = str(previous.get("run") or "")
    shown = bool(previous.get("finished"))
    out = []
    for gap in previous.get("gaps") or []:
        handed = gap.get("deferred_to_operator") or gap.get("verdict") == "minority"
        if gap.get("fixed") or (handed and shown):
            continue
        # A minority verdict is the operator's to see (step 4), and a pass
        # that died before step 10 never showed it (a 1c reader).
        if gap.get("verdict") not in ("real", "minority", None):
            continue
        out.append({**gap, "carried_from": run})
    return out


# Areas read whole now and then, because the diff review sees only what moved.
AREAS = {
    "core": ("qa/state.py", "qa/fold.py", "qa/measure.py"),
    "outbound": ("scripts/submit.py", "scripts/verify.py", "qa/safety.py",
                 "qa/client.py"),
    "lab": ("qa/lab.py", "scripts/lab.py", "scripts/clone.py", "scripts/paper.py"),
    "memecoins": ("qa/fomo.py", "scripts/fomo_watch.py", "qa/hot.py"),
}
REREAD_COMMITS = 15
REREAD_DAYS = 30
REREADS = "audits/rereads.json"


def rereads_due(record: dict, counts: dict, today, areas=None) -> dict[str, str]:
    """Areas owed a whole reading, with why: never read, REREAD_COMMITS
    commits touched them since, or REREAD_DAYS days went by."""
    due = {}
    for area in (areas or AREAS):
        last = (record or {}).get(area)
        if not last:
            due[area] = "never read whole"
            continue
        changed = int(counts.get(area) or 0)
        if changed >= REREAD_COMMITS:
            due[area] = f"{changed} commits since {last.get('commit', '?')[:8]}"
            continue
        try:
            days = (today - datetime.fromisoformat(str(last["at"])[:10]).date()).days
        except (KeyError, ValueError):
            due[area] = "its last reading has no date"
            continue
        if days >= REREAD_DAYS:
            due[area] = f"{days} days since the last reading"
    return due


def _commits_touching(paths, since: str | None) -> int:
    span = f"{since}..HEAD" if since else "HEAD"
    out = _git("rev-list", "--count", span, "--", *paths).strip()
    # Unreadable counts as owed: a reading nobody can date is due (rule 8).
    return int(out) if out.isdigit() else REREAD_COMMITS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true",
                        help="the rows, for the console")
    sub = parser.add_subparsers(dest="cmd")
    size_cmd = sub.add_parser("size", help="full, light or deferred, and why")
    size_cmd.add_argument("--weekly", help="the week's use of the plan, per cent")
    sub.add_parser("carry", help="the last notebook's unfixed gaps, as JSON")
    sub.add_parser("reread", help="which areas are owed a whole reading")
    args = parser.parse_args(argv)

    if args.cmd == "size":
        # --no-renames: a check moved into tests/repo is a deletion of the
        # check's path and an addition, so the check's path is seen (1c).
        files = [f for f in _git("diff", "--name-only", "--no-renames",
                                 "@{upstream}..HEAD").splitlines() if f]
        # Stripped: `_git` keeps git's newline, and "89\n" is not a digit
        # string -- which made every count 0 until this read failed closed.
        commits = _git("rev-list", "--count", "@{upstream}..HEAD").strip()
        if not commits.isdigit():
            # A diff nobody could read is not an empty one (rule 8): full,
            # never light (round-five readers of the 1c change).
            mode, why = pass_size([], 0, args.weekly)
            if mode != "deferred":
                mode, why = "full", "the diff could not be read"
            print(f"{mode} -- {why}")
            return 0
        mode, why = pass_size(files, int(commits), args.weekly)
        print(f"{mode} -- {why}")
        return 0
    if args.cmd == "carry":
        try:
            previous = json.loads((REPO_ROOT / PROGRESS).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = {}
        print(json.dumps(carried_gaps(previous), ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "reread":
        try:
            record = json.loads((REPO_ROOT / REREADS).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            record = {}
        counts = {area: _commits_touching(paths, (record.get(area) or {}).get("commit"))
                  for area, paths in AREAS.items()}
        due = rereads_due(record, counts, datetime.now().date())
        for area, why in due.items():
            print(f"{area}: {why} -- {' '.join(AREAS[area])}")
        if not due:
            print("no area is owed a whole reading")
        return 0

    rows = passes()
    if args.json:
        print(json.dumps({"passes": rows, "condition": condition(rows)},
                         indent=2, ensure_ascii=False))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
