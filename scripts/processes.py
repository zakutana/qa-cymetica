"""What is due, and what the operator's own words were since the last pass.

[operator 2026-09-12] *"ne zadene schedulery automaticke nechci ... Proste
mibudes jen pripominat co mam kdy delat alke vse si chci spoustet sam"* -- so
nothing here starts anything. `reminders` composes at most a few lines saying
what is on the table and the words that start it; `.claude/hooks/reminders.py`
prints them at the start of a session and CLAUDE.md says to repeat them in the
first answer, because hook output is not something they read.

    python scripts/processes.py reminders
    python scripts/processes.py messages --since-last-pass

Two halves on purpose. `reminders(facts, now)` is pure -- every rule is a
fixture in tests/repo/test_reminders.py, in both directions, because a line
that appears every evening is a line they stop reading. `facts()` is the impure
half: git, the deep pass's notebook, NEXT.md, the phase tables in docs/.

`messages` is here because step 1 of the deep pass needs it and had it wrong:
it filtered the transcripts by TODAY's date while every timestamp in them is
UTC, so a pass starting after midnight local read one hour of the new day and
called it "what the operator said today". Nothing went red; the pass simply
learned nothing from the evening that produced the work it was reviewing.

This file grows in F3 into the patrol over every part of the system (see
docs/lab-plan.md). Today it answers one question: what is due.
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(os.environ.get("QA_REPO_ROOT")
                 or Path(__file__).resolve().parent.parent)

# A pass runs every evening they are working, so 36 hours means a night went by
# without one -- not "they are late", which they never are.
MISSED_NIGHT_HOURS = 36
WEEK_DAYS = 7
NOTEBOOK = "audits/deep-pass-progress.json"

PHASE_ROW = re.compile(r"^\|\s*\**\s*(F\d+)\b")
COMMIT_IN_STATUS = re.compile(r"\b([0-9a-f]{7,40})\b")


def _moment(value) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _hours_since(value, now: datetime) -> float | None:
    stamp = _moment(value)
    return None if stamp is None else (now - stamp).total_seconds() / 3600.0


def reminders(facts: dict, now: datetime) -> list[str]:
    """At most a few lines: what is due, and the words that start it."""
    out: list[str] = []

    since = _hours_since(facts.get("last_pass"), now)
    if facts.get("unpushed") and (since is None or since > MISSED_NIGHT_HOURS):
        waited = f"{since:.0f} h" if since is not None else "neznámo jak dlouho"
        out.append(
            f"Deep pass neběžel {waited} a čeká na něj {facts['unpushed']} "
            f"commitů — až půjdeš spát, řekni „jdu spat\".")

    week = _hours_since(facts.get("week_last"), now)
    if week is None or week / 24.0 >= WEEK_DAYS:
        due = "nikdy neproběhl" if week is None else f"je {week / 24:.0f} dní starý"
        out.append(
            f"Týdenní ohlédnutí {due} — příští „jdu spat\" ho udělá i s týdnem, "
            f"i když nebude co kontrolovat.")

    carried = " ".join(facts.get("open_next") or [])
    for phase in facts.get("plan_phases") or []:
        if not phase.get("open"):
            continue
        name, plan = phase.get("id", "?"), phase.get("plan", "?")
        if name in carried and Path(plan).name in carried:
            continue
        out.append(
            f"Fáze {name} z {plan} nemá ani commit, ani řádek v NEXT.md — "
            f"schválený plán, o kterém by nikdo nevěděl.")
    return out


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip() if result.returncode == 0 else ""


def _notebook() -> dict:
    try:
        return json.loads((REPO_ROOT / NOTEBOOK).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _open_next() -> list[str]:
    """The open lines, through the hook's own parser: one reader, one format."""
    path = REPO_ROOT / ".claude" / "hooks" / "next_step.py"
    target = REPO_ROOT / "NEXT.md"
    if not path.is_file() or not target.is_file():
        return []
    try:
        spec = importlib.util.spec_from_file_location("next_step_reader", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        items = module.parse(target.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 -- a reader we cannot run says nothing
        return []
    return [item["what"] for item in items if not item["done"]]


def plan_phases() -> list[dict]:
    """Every phase of every plan in docs/, and whether it is still open.

    A phase is done when its status names a commit this repository has. A hash
    that is not here is not a phase that was done -- it is a status somebody
    typed, which is the failure this rule exists for.
    """
    found = []
    for path in sorted((REPO_ROOT / "docs").glob("*plan*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            match = PHASE_ROW.match(line)
            if not match:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            status = cells[-1].lower() if cells else ""
            done = "hotovo" in status
            if done:
                commit = COMMIT_IN_STATUS.search(status.replace("`", ""))
                done = bool(commit) and bool(
                    _git("cat-file", "-t", commit.group(1)))
            found.append({
                "plan": path.relative_to(REPO_ROOT).as_posix(),
                "id": match.group(1), "open": not done})
    return found


def facts() -> dict:
    """The impure half: git, the notebook, NEXT.md, the phase tables."""
    notebook = _notebook()
    unpushed = _git("rev-list", "--count", "@{upstream}..HEAD")
    return {
        "unpushed": int(unpushed) if unpushed.isdigit() else 0,
        "last_pass": notebook.get("at_finished") or notebook.get("at"),
        "week_last": (notebook.get("retrospective") or {}).get("last"),
        "open_next": _open_next(),
        "plan_phases": plan_phases(),
    }


def messages(rows, since: str | None) -> list[tuple[str, str]]:
    """What the operator said since a moment, oldest first.

    Theirs only, and never the harness's own blocks -- a summary injected after
    a compaction is typed by nobody and reads like a wall of instructions.
    """
    floor = _moment(since) if since else None
    out = []
    for row in rows:
        if row.get("type") != "user":
            continue
        stamp = _moment(row.get("timestamp"))
        if stamp is None or (floor is not None and stamp < floor):
            continue
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if content.lstrip().startswith("<"):
            continue
        out.append((str(row.get("timestamp")), " ".join(content.split())))
    return sorted(out)


def transcript_rows():
    """Every line of this project's transcripts. 20-30 MB each, so the caller
    filters; nothing here holds a file open longer than one pass over it."""
    pattern = str(Path.home() / ".claude" / "projects" / "*cymetica*" / "*.jsonl")
    for path in glob.glob(pattern):
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reminders", help="what is due, in the words that start it")
    said = sub.add_parser("messages", help="what the operator said since when")
    said.add_argument("--since", help="ISO timestamp")
    said.add_argument("--since-last-pass", action="store_true",
                      help="since the deep pass's own notebook says it started")
    said.add_argument("--limit", type=int, default=60)
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if args.cmd == "reminders":
        for line in reminders(facts(), datetime.now(timezone.utc)):
            print(line)
        return 0

    since = args.since
    if args.since_last_pass and not since:
        notebook = _notebook()
        since = notebook.get("at")
        # A pass that started this morning is the wrong floor for the pass that
        # is about to read what happened since YESTERDAY's. Fall back a day
        # rather than to nothing: an empty floor prints a month of messages.
        if since is None:
            since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    found = messages(transcript_rows(), since)
    print(f"# {len(found)} message(s) from the operator since {since}")
    for stamp, text in found[-args.limit:]:
        print(f"{stamp[11:16]}  {text[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
