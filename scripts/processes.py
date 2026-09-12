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
# Where the code lives, which is not where the DATA lives when a test points
# QA_REPO_ROOT at a fixture. Importing `qa` from a fixture would import nothing.
CODE_ROOT = Path(__file__).resolve().parent.parent
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

# A pass runs every evening they are working, so 36 hours means a night went by
# without one -- not "they are late", which they never are.
MISSED_NIGHT_HOURS = 36
WEEK_DAYS = 7
NOTEBOOK = "audits/deep-pass-progress.json"

# Any letter, not just F. The second plan of 2026-09-12 numbered its phases
# N0..N5 and every one of them was invisible to this rule, which is the shape
# of a watcher that only sees what it was written for.
PHASE_ROW = re.compile(r"^\|\s*\**\s*([A-Z]\d+)\b")
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

    # First, because it is the only line about a change we did not make. The
    # patrol below measures OUR parts; this one says their side moved under us.
    # [operator 2026-09-12] asked how it was possible we would not notice --
    # and the answer that day was that nothing looked. It keeps saying it until
    # `processes.py surface --update` acknowledges the new shape.
    drift = facts.get("surface_drift") or []
    if drift:
        out.append(f"Cymetica změnila povrch od minule ({len(drift)}):")
        out.extend(f"  {line}" for line in drift[:5])
        out.append("  potvrď příkazem `python scripts/processes.py surface --update`")

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

    for session in facts.get("lab_open") or []:
        out.append(
            f"Laboratoř má otevřenou session {session} — zavře ji „jdi do "
            f"laboratoře\", a do té doby neví další session, kde jste skončili.")

    # A night is an open session ON PURPOSE, until the hour it was given. Only
    # a session left open past that is something to close.
    if facts.get("night_running"):
        until = str(facts.get("night_until") or "")[:16].replace("T", " ")
        out.append(
            f"Laboratoř právě běží v noci jako {facts['night_running']}"
            + (f" do {until}" if until else "")
            + " — neptej se Nexuse souběžně, ráno ji shrne `lab.py status`.")

    retry = _hours_since(facts.get("nexus_last_try"), now)
    if facts.get("nexus_down") and retry is not None and retry >= 2:
        out.append(
            f"Nexus neodpověděl {facts['nexus_down']}× za sebou a od posledního "
            f"pokusu je {retry:.0f} h — je čas zkusit ho znovu: „jdi do "
            f"laboratoře\".")

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


# --- the patrol -----------------------------------------------------------
#
# [operator 2026-09-11] asked for the self-improvement to be in the DNA -- a
# part added in a month measures itself without anyone wiring it in. The first
# design declared five keys in every SKILL.md; a reviewer named it for what it
# was, a registry, and a registry is a thing to forget. So nothing is declared:
# the parts are found, and what each did is read from what it left behind.

# What a part leaves behind when it runs. The journal covers the scripts that
# write it (by `source`), so only the narrow records need naming here.
PART_RECORDS = {
    "nexus.py": "nexus.jsonl",
    "rooms.py": "rooms.jsonl",
    "paper.py": "paper.jsonl",
    "clone.py": "clones.jsonl",
    "sampler.py": "samples.jsonl",
    "lab.py": "lab.jsonl",
}

IDLE_DAYS = 14

# Every ceiling sits ABOVE where the repository stood on 2026-09-12, and
# tests/repo/test_process_dna.py holds them there: a warning that is on from
# the first day is a warning nobody reads. Measured that day: evidence 290 MB,
# pack 54 MiB, CLAUDE.md 658 lines, MEMORY.md 38, oldest open NEXT item 2 days.
CEILINGS = {
    "evidence_mb": 1000,
    "claude_md_lines": 700,
    "memory_lines": 45,
    "next_oldest_days": 10,
    "pack_growth_mb": 25,
}

BASH_SCRIPT = re.compile(r"python\s+scripts[/\\]([a-z_]+)\.py")
SLASH = re.compile(r"^/([a-z][a-z0-9-]+)")


def parts(root: Path | None = None) -> list[dict]:
    """Every skill, agent, script and hook, found rather than registered."""
    base = Path(root or REPO_ROOT)
    found = []
    for path in sorted((base / ".claude" / "skills").glob("*/SKILL.md")):
        found.append({"name": path.parent.name, "kind": "skill",
                      "path": path.relative_to(base).as_posix()})
    for path in sorted((base / ".claude" / "agents").glob("*.md")):
        found.append({"name": path.stem, "kind": "agent",
                      "path": path.relative_to(base).as_posix()})
    for path in sorted((base / "scripts").glob("*.py")):
        found.append({"name": path.name, "kind": "script",
                      "path": path.relative_to(base).as_posix()})
    for path in sorted((base / ".claude" / "hooks").glob("*.py")):
        found.append({"name": path.name, "kind": "hook",
                      "path": path.relative_to(base).as_posix()})
    return found


def records_by_part(root: Path | None = None) -> dict[str, list[str]]:
    """When each part last left something behind, from its own records.

    The journal names its writer in `source`, which covers everything that
    files, verifies, corresponds or polls. The narrow records under state/ are
    mapped by name. Preregistrations are a sweep's own mark.
    """
    base = Path(root or REPO_ROOT)
    state = base / "state"
    out: dict[str, list[str]] = {}

    def note(part: str, when):
        if isinstance(when, str) and when:
            out.setdefault(part, []).append(when)

    for row in _jsonl(state / "journal" / "events.jsonl"):
        source = str(row.get("source") or "")
        if source.startswith("scripts/"):
            # `scripts/bounty.py a2a-inbox` is the poller saying which door it
            # read. The part is the script; the argument is not a second part,
            # which is what the first version of this made of it.
            note(Path(source.split()[0]).name, row.get("at"))
    for part, name in PART_RECORDS.items():
        for row in _jsonl(state / name):
            note(part, row.get("at") or row.get("asked") or row.get("started"))
    for path in sorted((state / "preregistrations").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        note("prereg.py", row.get("at") or row.get("created_at"))
    return out


def _jsonl(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def runs_from_records(by_part: dict[str, list[str]]) -> dict[str, dict]:
    """One run, not one record.

    A poll of their tracker writes several events in the same second, and
    counting rows made the console's fifteen-minute poller the busiest part of
    the system by an order of magnitude -- 972 "runs" in eight days, which is
    96 polls a day seen through the wrong lens. Distinct minutes is the honest
    unit: nothing here runs twice in one.
    """
    out = {}
    for part, stamps in by_part.items():
        kept = sorted(s for s in stamps if s)
        if kept:
            out[part] = {"runs": len({s[:16] for s in kept}), "last": kept[-1]}
    return out


def runs_from_transcripts(rows, known: set[str] | None = None) -> dict[str, dict]:
    """What was invoked, and what blew up, from the session transcripts.

    Counted from the COMMAND, not only from a Skill call: sessions follow these
    skills by reading them -- the Nexus session of 2026-09-11 called the Skill
    tool zero times on the day it opened four rooms.
    """
    out: dict[str, dict] = {}
    owner: dict[str, str] = {}

    def note(part: str, when, key="runs"):
        entry = out.setdefault(part, {"runs": 0, "errors": 0, "last": None})
        entry[key] += 1
        if when and (entry["last"] is None or str(when) > entry["last"]):
            entry["last"] = str(when)

    for row in rows:
        when = row.get("timestamp")
        content = (row.get("message") or {}).get("content")
        if isinstance(content, str):
            found = SLASH.match(content.strip())
            # Only a name we know, or a plugin's `namespace:skill`. Anything
            # else beginning with a slash is the operator typing -- "/btw" was
            # counted as a part for exactly one run before this line existed.
            if row.get("type") == "user" and found and (
                    known is None or found.group(1) in known
                    or ":" in found.group(1)):
                note(found.group(1), when)
            continue
        for block in content or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                part = None
                if block.get("name") == "Skill":
                    part = (block.get("input") or {}).get("skill")
                else:
                    command = str((block.get("input") or {}).get("command") or "")
                    hit = BASH_SCRIPT.search(command)
                    part = f"{hit.group(1)}.py" if hit else None
                if part:
                    owner[str(block.get("id"))] = part
                    note(part, when)
            elif block.get("type") == "tool_result" and block.get("is_error"):
                part = owner.get(str(block.get("tool_use_id")))
                if part:
                    note(part, when, key="errors")
    return out


EFFORT_LINE = re.compile(r"^Effort:\s*(\S+)\s*$", re.M)


def effort_counts(limit: int = 200, trailers_only: bool = False) -> dict[str, int]:
    """How many commits ran at each effort, read the lenient way.

    `.githooks/prepare-commit-msg` appends the line and git's own parser reads
    it -- unless the message is one line (subject and trailer become one
    paragraph) or the agent wrote its own Effort paragraph above
    Co-Authored-By. 73 of 188 commits were unreadable that way on 2026-09-12.
    The hook is fixed for what comes next; the history cannot be, so the
    reader takes the line wherever it stands and the week stops being blind to
    a third of its own evidence.
    """
    out: dict[str, int] = {}
    if trailers_only:
        raw = _git("log", f"-{limit}",
                   "--format=%(trailers:key=Effort,valueonly)%x00")
        values = [v.strip() for v in raw.split("\0")]
    else:
        raw = _git("log", f"-{limit}", "--format=%B%x00")
        values = [(EFFORT_LINE.search(block).group(1)
                   if EFFORT_LINE.search(block) else "")
                  for block in raw.split("\0")]
    for value in values:
        value = value.strip()
        if value:
            out[value] = out.get(value, 0) + 1
    return out


def sizes(root: Path | None = None) -> dict:
    """The numbers a growing system has to be held to, measured now."""
    base = Path(root or REPO_ROOT)
    out: dict[str, float] = {}

    store = base / "evidence"
    if store.is_dir():
        total = sum(p.stat().st_size for p in store.glob("sha256/*/*.json"))
        out["evidence_mb"] = round(total / 1048576, 1)

    for key, path in (("claude_md_lines", base / "CLAUDE.md"),):
        try:
            out[key] = len(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            pass

    index = Path.home() / ".claude" / "projects"
    for candidate in index.glob("*cymetica*/memory/MEMORY.md"):
        try:
            out["memory_lines"] = len(
                candidate.read_text(encoding="utf-8").splitlines())
        except OSError:
            pass
        break

    oldest = None
    for path in (base / "NEXT.md",):
        try:
            source = base / ".claude" / "hooks" / "next_step.py"
            spec = importlib.util.spec_from_file_location("next_for_sizes",
                                                          source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for item in module.parse(path.read_text(encoding="utf-8")):
                if not item["done"] and (oldest is None or item["at"] < oldest):
                    oldest = item["at"]
        except Exception:  # noqa: BLE001
            pass
    if oldest:
        age = _moment(oldest + "T00:00:00+00:00")
        if age:
            out["next_oldest_days"] = round(
                (datetime.now(timezone.utc) - age).total_seconds() / 86400, 1)

    pack = _git("count-objects", "-v")
    for line in pack.splitlines():
        if line.startswith("size-pack:"):
            out["pack_mb"] = round(int(line.split()[1]) / 1024, 1)
    return out


def unwired_hooks(root: Path | None = None) -> list[str]:
    """Hooks on disk that .claude/settings.json never names.

    A hook leaves no record when it runs, so the patrol cannot count its runs
    the way it counts a script's -- and the failure that matters is not "it ran
    twice" anyway. It is a hook written, committed, and never fired because
    nobody wired it, which is what "a mechanism nobody can reach" looks like
    from the outside. That one is static, so it is asserted rather than
    counted. Nothing had checked the SessionStart wiring before 2026-09-12;
    tests/repo/test_state_guard.py checks the PreToolUse matcher and stops
    there.
    """
    base = Path(root or REPO_ROOT)
    settings = base / ".claude" / "settings.json"
    try:
        text = settings.read_text(encoding="utf-8")
    except FileNotFoundError:
        # No settings file is not "nothing to report": it means no hook fires
        # at all, which is the loudest form of the thing this looks for.
        text = ""
    except OSError:
        # A read we could not make is not an empty read (rule 8), and here the
        # safe direction is to say nothing rather than to name every hook.
        return []
    return [path.name for path in sorted((base / ".claude" / "hooks").glob("*.py"))
            if path.name not in text]


def flags(state: dict) -> list[str]:
    """What is off, said in one line each. Never an exception, never a failure:
    step 9 of the deep pass reverts a night on a red it cannot resolve, and a
    script nobody ran for a fortnight is a question for the week."""
    out = []
    for name, seen in sorted((state.get("parts") or {}).items()):
        idle = seen.get("idle_days")
        if seen.get("runs", 0) == 0 and idle is not None and idle >= IDLE_DAYS:
            out.append(f"{name}: nothing for {idle:.0f} days -- a candidate for "
                       f"the prořez, or a mechanism nobody can reach")
        if seen.get("errors") and seen.get("runs"):
            share = seen["errors"] / max(seen["runs"], 1)
            if share >= 0.5:
                out.append(f"{name}: {seen['errors']} error(s) in "
                           f"{seen['runs']} run(s)")
    for name in state.get("unwired") or []:
        out.append(f"{name}: a hook nothing in .claude/settings.json names, so "
                   f"it has never fired")
    measured = state.get("sizes") or {}
    for key, ceiling in CEILINGS.items():
        value = measured.get(key)
        if value is not None and value > ceiling:
            out.append(f"{key} is {value}, over the {ceiling} this was held to "
                       f"on 2026-09-12")
    return out


def extract(root: Path | None, day: dict) -> None:
    """Append one day's counts, once. The transcripts are kept about thirty
    days and the laboratory will run for months, so the series lives in git."""
    base = Path(root or REPO_ROOT)
    target = base / "audits" / "processes.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in _jsonl(target) if r.get("day") != day.get("day")]
    rows.append(day)
    rows.sort(key=lambda r: str(r.get("day")))
    target.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                  for r in rows) + "\n", encoding="utf-8")


def patrol(root: Path | None = None, since: str | None = None) -> dict:
    """Every part, what it did, and the numbers the whole system is held to."""
    base = Path(root or REPO_ROOT)
    now = datetime.now(timezone.utc)
    known = {part["name"] for part in parts(base)}
    seen: dict[str, dict] = {}
    left_records: set[str] = set()
    for name, entry in runs_from_records(records_by_part(base)).items():
        seen[name] = {"runs": entry["runs"], "last": entry["last"], "errors": 0}
        left_records.add(name)
    for name, entry in runs_from_transcripts(
            messages_rows(since), known=known).items():
        row = seen.setdefault(name, {"runs": 0, "last": None, "errors": 0})
        row["runs"] += entry.get("runs", 0)
        row["errors"] += entry.get("errors", 0)
        if entry.get("last") and (row["last"] is None
                                  or entry["last"] > row["last"]):
            row["last"] = entry["last"]

    out = {"at": now.isoformat(timespec="seconds"),
           "day": now.date().isoformat(), "parts": {}, "sizes": sizes(base),
           "unwired": unwired_hooks(base)}
    for part in parts(base):
        row = dict(seen.get(part["name"], {"runs": 0, "last": None,
                                           "errors": 0}))
        last = _moment(row.get("last"))
        row["kind"] = part["kind"]
        row["idle_days"] = round((now - last).total_seconds() / 86400, 1) \
            if last else None
        out["parts"][part["name"]] = row
    # Two kinds of part that is not here, and they are not the same question.
    # `gone` left records and no longer exists -- migrate_ledger.py, retired
    # and still cited by three events. `invoked` is something we ran that was
    # never ours: a built-in skill, a plugin. Reporting both as "gone" made the
    # first list read like a graveyard of our own work.
    for name, row in seen.items():
        out["parts"].setdefault(
            name, {**row, "idle_days": None,
                   "kind": "gone" if name in left_records else "invoked"})
    return out


def messages_rows(since: str | None):
    """Transcript rows since a moment, or an empty list when there are none."""
    floor = _moment(since) if since else None
    for row in transcript_rows():
        stamp = _moment(row.get("timestamp"))
        if floor is not None and (stamp is None or stamp < floor):
            continue
        yield row


def render(state: dict) -> str:
    lines = [f"{'part':26} {'kind':7} {'runs':>5} {'err':>4} {'idle':>6}  last"]
    lines.append("-" * len(lines[0]))
    for name, row in sorted(state["parts"].items(),
                            key=lambda kv: (-kv[1]["runs"], kv[0])):
        idle = "" if row.get("idle_days") is None else f"{row['idle_days']:.0f}d"
        last = (row.get("last") or "-")[:16].replace("T", " ")
        lines.append(f"{name[:26]:26} {row.get('kind', '?'):7} "
                     f"{row.get('runs', 0):>5} {row.get('errors', 0):>4} "
                     f"{idle:>6}  {last}")
    lines.append("")
    lines.append("a hook leaves no record when it runs, so its runs are not "
                 "counted -- only its wiring")
    lines.append("  ".join(f"{k}={v}" for k, v in sorted(
        (state.get("sizes") or {}).items())))
    warned = flags(state)
    lines.append("")
    lines.extend(warned or ["nothing over a ceiling, nothing idle"])
    return "\n".join(lines)


def _notebook() -> dict:
    try:
        return json.loads((REPO_ROOT / NOTEBOOK).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def pass_in_flight(now: datetime | None = None) -> bool:
    """Whether a deep pass is running right now, from its own notebook.

    One reader, because three things need the answer and none of them may
    disagree: the laboratory (which must not ask Nexus or trade while the pass
    verifies #85, #86 and #87 over those very answers), the reminder rules, and
    the guard in tests/repo. `finished` is the last thing a pass writes; a
    notebook without it that is older than a day is a pass that died, not one
    that is running -- the same window tests/repo/test_deep_pass_finished.py
    draws, and for the same reason.
    """
    notebook = _notebook()
    if not notebook or notebook.get("finished"):
        return False
    started = _moment(notebook.get("at"))
    if started is None:
        return False
    return (now or datetime.now(timezone.utc)) - started < timedelta(hours=24)


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


def _lab_facts() -> dict:
    """What the laboratory is owed: an unfinished session, and a lane that may
    have come back. Both are read from files; a reminder that asked the vendor
    would itself be counted by the check that measures how often we ask."""
    out: dict[str, object] = {"lab_open": [], "nexus_down": 0,
                              "nexus_last_try": None, "night_running": None,
                              "night_until": None}
    try:
        from qa import lab

        running = lab.night_running()
        if running:
            out["night_running"], out["night_until"] = running
        out["lab_open"] = [session for session in lab.open_sessions()
                           if session != out["night_running"]]
    except Exception:  # noqa: BLE001
        pass

    rows = _jsonl(REPO_ROOT / "state" / "nexus.jsonl")
    asked = [r for r in rows if r.get("type") == "question"]
    finished = {r.get("id"): r.get("type") for r in rows
                if r.get("type") in ("answer", "gave_up")}
    streak = 0
    for row in reversed(asked):
        outcome = finished.get(row.get("id"))
        if outcome == "answer":
            break
        streak += 1
    out["nexus_down"] = streak if streak >= 3 else 0
    if asked:
        out["nexus_last_try"] = asked[-1].get("at")
    return out


def surface_drift(update: bool = False) -> list[str]:
    """What moved on THEIR side since we last agreed what it looked like.

    Read from captures we already make, so it costs no request of its own and
    works with the network down. Two references on purpose:
    `audits/surface.json` is what we have acknowledged and is what this
    compares against, while `audits/nexus-baseline.json` stays frozen as the
    before-the-upgrade marker `lab.py surface` reads. Acknowledging here must
    not quietly move that marker.

    `update` writes the seen shape back, which is how a drift stops being
    reported -- a reminder that cannot be cleared is one nobody reads.
    """
    from qa import surface

    stored = surface.remembered()
    seen = surface.shapes_since()
    said = surface.drift_against(stored.get("calls") or {}, seen)

    listed = surface.tools_seen()
    if listed is not None:
        known = stored.get("tools") or []
        if known:
            moved = surface.tools_drift(known, listed)
            said += [f"{c['tool']}: {'; '.join(c['what'][:2])}"
                     for c in moved["changed"]]
            said += [f"nový nástroj {n}" for n in moved["new"]]
            said += [f"nástroj zmizel: {n}" for n in moved["gone"]]

    if update:
        calls = dict(stored.get("calls") or {})
        calls.update(seen)
        surface.remember({"calls": calls,
                          "tools": listed if listed is not None
                                   else stored.get("tools") or [],
                          "agreed_at": datetime.now(timezone.utc).isoformat(
                              timespec="seconds")})
    return said


def _surface_facts() -> dict:
    """Never raises: a session start is not the place to die on a stray file."""
    try:
        return {"surface_drift": surface_drift()}
    except Exception:  # noqa: BLE001
        return {"surface_drift": []}


def facts() -> dict:
    """The impure half: git, the notebook, NEXT.md, the phase tables, the lab."""
    notebook = _notebook()
    unpushed = _git("rev-list", "--count", "@{upstream}..HEAD")
    return {
        "unpushed": int(unpushed) if unpushed.isdigit() else 0,
        "last_pass": notebook.get("at_finished") or notebook.get("at"),
        "week_last": (notebook.get("retrospective") or {}).get("last"),
        "open_next": _open_next(),
        "plan_phases": plan_phases(),
        **_lab_facts(),
        **_surface_facts(),
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
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("reminders", help="what is due, in the words that start it")
    watch = sub.add_parser("patrol", help="every part, what it did, the ceilings")
    watch.add_argument("--since", help="ISO; default: seven days back")
    watch.add_argument("--extract", action="store_true",
                       help="append today's counts to audits/processes.jsonl")
    watch.add_argument("--flags", action="store_true",
                       help="print only what is off")
    shape = sub.add_parser("surface", help="what moved on THEIR side")
    shape.add_argument("--update", action="store_true",
                       help="agree to the shape seen now, so it stops being reported")
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

    if args.cmd == "surface":
        moved = surface_drift(update=args.update)
        for line in moved:
            print(f"  {line}")
        if not moved:
            print("their surface reads the same as the shape we agreed")
        if args.update:
            print(f"agreed; {len(moved)} change(s) now the reference")
        return 0

    if args.cmd in (None, "patrol"):
        # A week by default: reading every transcript is 200 MB, and the
        # question the patrol answers is about the recent past.
        floor = getattr(args, "since", None) or (
            datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        state = patrol(since=floor)
        if getattr(args, "extract", False):
            extract(REPO_ROOT, {"at": state["at"], "day": state["day"],
                                "parts": {k: {"runs": v["runs"],
                                              "errors": v["errors"]}
                                          for k, v in state["parts"].items()},
                                "sizes": state["sizes"]})
        if getattr(args, "flags", False):
            for line in flags(state):
                print(line)
            return 0
        print(render(state))
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
