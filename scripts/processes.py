"""What is due, and what the operator's own words were since the last pass.

[operator 2026-09-12] *"ne zadene schedulery automaticke nechci ... Proste
mibudes jen pripominat co mam kdy delat alke vse si chci spoustet sam"* -- so
nothing here starts anything. `reminders` composes at most a few lines saying
what is on the table and the words that start it; `.claude/hooks/start/reminders.py`
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
# Rebuilding the month's xz costs minutes, so the line waits until there is a
# bundle's worth to carry. 1 145 stood unarchived the day this was set.
UNARCHIVED_CAPTURES = 400
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

    # Plan v2, V11: the overnight loop's tick makes the 7:00 report. When no
    # tick ran, the session that starts is the one to make it -- at once.
    if facts.get("morning_missing"):
        out.append(
            "Ranní přehled z laborky za dnešek chybí — udělej ho hned: "
            "`python scripts/lab.py morning`, pak ho publikuj (laborator, "
            "Ranní přehled).")

    for session in facts.get("lab_open") or []:
        out.append(
            f"Laboratoř má otevřenou session {session} — zavře ji „jdi do "
            f"laboratoře\", a do té doby neví další session, kde jste skončili.")

    # Nexus's own leading indicator (2026-09-12, unprompted, about its own top
    # strategy): "when average pairwise correlation crosses ~0.6-0.7 the
    # breadth collapses and that precedes the drawdown." Below that threshold
    # a correlated pair is the ordinary state of a small book.
    n_eff = facts.get("n_eff")
    if isinstance(n_eff, dict) and (n_eff.get("rho") or 0) >= 0.6:
        out.append(
            f"Kniha je moc korelovaná (N_eff {n_eff['n_eff']:.1f} z "
            f"{n_eff['n']}, ⍴={n_eff['rho']:.2f}) — drawdown by mohl přijít "
            f"najednou.")

    retry = _hours_since(facts.get("nexus_last_try"), now)
    if facts.get("nexus_down") and retry is not None and retry >= 2:
        out.append(
            f"Nexus neodpověděl {facts['nexus_down']}× za sebou a od posledního "
            f"pokusu je {retry:.0f} h — je čas zkusit ho znovu: „jdi do "
            f"laboratoře\".")

    # `keep.py archive` has no trigger of its own: the deep pass calls `track`
    # and `snapshot`, never this. So the bundle stayed a snapshot of the day it
    # was first built while the manifest went on adding rows with `archive: ""`
    # -- bodies on disk that nothing will ever let go of. This is the trigger,
    # and it stays quiet until there is enough to be worth an xz rebuild.
    pending = facts.get("evidence_unarchived") or 0
    if pending >= UNARCHIVED_CAPTURES:
        month = now.strftime("%Y-%m")
        out.append(
            f"{pending} captures není v žádném archivu — zabalí je `python "
            f"scripts/keep.py archive --month {month} --release`.")

    carried = " ".join(facts.get("open_next") or [])
    for phase in facts.get("plan_phases") or []:
        if not phase.get("open"):
            continue
        name, plan = phase.get("id", "?"), phase.get("plan", "?")
        # The id as a WORD: "V1" in "otevřená fáze V11" hid an open V1 (R06,
        # deep pass of 2026-09-24).
        named = re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)", carried)
        if named and Path(plan).name in carried:
            continue
        out.append(
            f"Fáze {name} z {plan} nemá ani commit, ani řádek v NEXT.md — "
            f"schválený plán, o kterém by nikdo nevěděl.")

    # Their side moved under us -- the one line about a change we did not
    # make. [operator 2026-09-12] asked how it was possible we would not
    # notice; it keeps saying it until `processes.py surface --update`
    # acknowledges the new shape. ONE line, and after what is due: as a
    # header, five lines and a confirm line it filled the session start's
    # whole slot and hid the morning report and the owed pass behind
    # "(+N dalších)" (R02, deep pass of 2026-09-24). R10 (2026-09-22): the
    # command is ours to run, so it says who runs it.
    drift = facts.get("surface_drift") or []
    if drift:
        named = "; ".join(str(line) for line in drift[:5])
        more = f"; +{len(drift) - 5} další" if len(drift) > 5 else ""
        out.append(
            f"Cymetica změnila povrch od minule ({len(drift)}: {named}{more})"
            " — session je projde a potvrdí sama: "
            "`python scripts/processes.py surface --update`")
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

# Every ceiling sits ABOVE where the repository stood when it was set, and
# tests/repo/test_process_dna.py holds them there: a warning that is on from
# the first day is a warning nobody reads. Re-measured at the end of 2026-09-12,
# after the capture bodies left git: evidence 385 MB ON DISK (no longer in the
# pack), pack 61.4 MiB, CLAUDE.md 700 lines, MEMORY.md 40, oldest open NEXT
# item 2.7 days.
#
# The key was `pack_growth_mb` until three reviewers noticed `sizes()` emits
# `pack_mb` -- so `flags()` looked up a key nothing produced and the one ceiling
# aimed at the operator's actual question about GitHub could never fire, on the
# day whose whole plan was the size of git. 150 is ~3 months at the ~1 MB/day
# the repository now grows, and fires long before anyone finds gigabytes there.
CEILINGS = {
    "evidence_mb": 1000,
    # Plan v2, V7: 750 -> 300 when the file was cut to 198 lines (the maps
    # went to ARCHITECTURE.md). A 750 ceiling on a 200-line file is dead.
    "claude_md_lines": 300,
    # LIVE pointers now, not raw lines -- see sizes(). Raised 45 -> 48 twice in
    # one day while it was counting lines, which is what exposed it: retired
    # lines stay for ever, so the measured number could only grow and the only
    # response to the warning was to raise it again. Against the live count
    # the deep pass's prořez (1b) can actually bring it down by merging, which
    # it did on 2026-09-13: 49 raw lines, 45 in force. Left at 48 rather than
    # lowered to 45 -- a ceiling set flush against today is one that fires on
    # the next honest memory, and CLAUDE.md says a warning on from the first
    # day is a warning nobody reads. A sweep raised it to 52 on 2026-09-25 to
    # fit one new memory; put back the same night -- a ceiling that moves for
    # the next memory is no ceiling. When it fires, merge or retire one.
    "memory_lines": 48,
    "next_oldest_days": 10,
    "pack_mb": 150,
    # Plan v2, V6: the laboratory's skill is loaded on every firing of its
    # loop -- it was 400 lines. The pins stay verbatim; the rest lives in the
    # commands it names (`lab.py brief` carries what we know about Nexus).
    "lab_skill_lines": 100,
    # Plan v2, V7: tests/meta grows only by replacement -- 225 to 786 test
    # functions in fifteen days, most of them guarding us rather than testing
    # them. A new guard replaces or merges one; the room above today's 786 is
    # for V8's findings, whose tests the plan already owes.
    #
    # 2026-09-28: that room is spent. Raised 800 -> 801 for
    # test_last_full_run_backfill_stays_off_the_committed_page (the D2 gap:
    # build_payload() was reading state/runs/*.json, gitignored, into the
    # committed dashboard), then 801 -> 802 the same sweep for
    # test_a_broken_first_read_does_not_poison_the_second (EvidenceStore
    # .capture() swallowing a read failure left the response unreadable a
    # second time -- StreamConsumed, reported at the caller's line with no
    # trace of evidence.py). Two distinct defects the same run turned up. No
    # slack added on top of either: the next addition earns its own raise.
    # 802 -> 803 the same morning for
    # test_a_check_with_hundreds_of_captures_still_fits_their_evidence_field:
    # verify.py listed ~200 evidence ids, their 8000-character field refused
    # the #130 correction with a 422.
    "meta_tests": 803,
}

BASH_SCRIPT = re.compile(r"python\s+scripts[/\\]([a-z_]+)\.py")
SLASH = re.compile(r"^/([a-z][a-z0-9-]+)")
COMMAND_NAME = re.compile(r"<command-name>(/[^<\s]+)</command-name>")
# A preregistration is Markdown (scripts/prereg.py), and the patrol globbed
# *.json: 155 of them were invisible, so prereg.py read as never run (E4).
REGISTERED = re.compile(r"^\s*Registered\s+(\S+)", re.M)


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
    # A department's diaries are its script's records (plan v2, V9): found by
    # the department shape, not by a line added here.
    from qa import departments

    for dept, paths in departments.diaries(state).items():
        if f"{dept}.py" in PART_RECORDS:
            continue
        for path in paths:
            for row in _jsonl(path):
                note(f"{dept}.py", row.get("at"))
    for path in sorted((state / "preregistrations").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        note("prereg.py", row.get("at") or row.get("created_at"))
    # bounty.py rewrites state/bounty.json on every read; since V8 its journal
    # events come only on a door's health change, so the file is its trace.
    try:
        note("bounty.py", datetime.fromtimestamp(
            (state / "bounty.json").stat().st_mtime, timezone.utc).isoformat())
    except OSError:
        pass
    for path in sorted((state / "preregistrations").glob("*.md")):
        try:
            found = REGISTERED.search(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if found:
            note("prereg.py", found.group(1))
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


def within(by_part: dict[str, list[str]], since) -> dict[str, list[str]]:
    """The same stamps, bounded below. Pure, so the two passes share one read.

    `patrol` needs both answers at once and they must not be the same walk:
    the WINDOW says how much a part did lately, the WHOLE HISTORY says when it
    was last seen at all. Collapse them and the fortnight warning goes out — a
    part idle for sixty days would get `last = None`, `idle_days = None`, and
    `flags()` skips exactly the part it exists to name.
    """
    # `since` arrives as a datetime from `patrol` and as an ISO STRING from the
    # command line, which is how the first version of this crashed the CLI
    # while its test passed -- the test handed it a datetime, so fixture and
    # code shared one assumption. One coercion, both callers.
    floor = since if isinstance(since, datetime) else _moment(since)
    if floor is None:
        return {part: list(stamps) for part, stamps in by_part.items()}
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    out = {}
    for part, stamps in by_part.items():
        kept = [s for s in stamps if (_moment(s) or epoch) >= floor]
        if kept:
            out[part] = kept
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
            # A typed slash command reaches the transcript as
            # `<command-name>/deep-pass</command-name>`, not as "/deep-pass",
            # so SLASH never saw one (E4, review of 2026-09-23).
            named = COMMAND_NAME.search(content)
            found = SLASH.match(named.group(1) if named else content.strip())
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
                elif block.get("name") in ("Agent", "Task"):
                    # An agent is spawned, not invoked or run from a shell;
                    # without this the deep pass's auditors read 0 runs.
                    part = (block.get("input") or {}).get("subagent_type") or None
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

    # Spelled as a literal subscript, not through a one-element loop: the
    # ceiling guard reads the keys this function can emit off its own source,
    # because a list of them beside it is a thing to forget, and a loop
    # variable is a key no reader can see.
    try:
        out["claude_md_lines"] = len(
            (base / "CLAUDE.md").read_text(encoding="utf-8").splitlines())
    except OSError:
        pass
    try:
        out["meta_tests"] = sum(
            1 for path in (base / "tests" / "meta").glob("*.py")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("def test_"))
    except OSError:
        pass
    try:
        out["lab_skill_lines"] = len(
            (base / ".claude" / "skills" / "laborator" / "SKILL.md")
            .read_text(encoding="utf-8").splitlines())
    except OSError:
        pass

    # LIVE pointers, not raw lines. Step 1b of the deep pass requires a retired
    # memory to keep its line for ever -- marked RETIRED, never removed,
    # because MEMORY.md is the only history that directory has outside git --
    # so a raw line count is monotone: a retirement could not reduce the number
    # it was meant to reduce, and the only response to the warning was to raise
    # the ceiling, twice in one day (45 -> 48 -> red at 49). A ceiling on a
    # number that can only grow is a warning that can never be cleared, which
    # is the same defect as a check over a growing log. What prořez CAN reduce
    # is the count of pointers still in force, by merging one into another.
    # (Since V7 retired lines live in MEMORY-retired.md; still skipped here in
    # case one is left behind.) THIS project's index: `*cymetica*` took the
    # first match, which could be the web-qa-agent project's.
    candidate = (Path.home() / ".claude" / "projects" / project_slug()
                 / "memory" / "MEMORY.md")
    try:
        lines = candidate.read_text(encoding="utf-8").splitlines()
        out["memory_lines"] = len(
            [line for line in lines
             if line.strip().startswith("- [") and "RETIRED" not in line])
    except OSError:
        pass

    oldest = None
    for path in (base / "NEXT.md",):
        try:
            source = base / ".claude" / "hooks" / "start" / "next_step.py"
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
        # Never seen at all had no age, so this flag could not fire for it
        # (E4): "nothing idle" was then reported as health. Only where a part
        # can leave a record -- a hook cannot, and `unwired` covers hooks --
        # and only once it has existed long enough to have run.
        age = seen.get("age_days")
        if (idle is None and seen.get("runs", 0) == 0
                and seen.get("kind") in ("skill", "agent", "script")
                and age is not None and age >= IDLE_DAYS):
            out.append(f"{name}: not seen in the patrol's window and it leaves "
                       f"no record, {age:.0f} days after it was added -- idle, "
                       f"unreachable, or leaving no trace the patrol reads")
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
    # Two passes over ONE read. `runs` is what the part did inside the window;
    # `last` is when it was last seen at all. Counting both from the same walk
    # was the defect docs/data-plan.md named and did not fix: an unbounded
    # record count was ADDED to a windowed transcript count, so ledger.py
    # reported 419 runs over seven days. Windowing the records too would have
    # been worse -- it takes `last` with it, and the fortnight warning then
    # cannot fire on any part at all.
    stamps = records_by_part(base)
    seen: dict[str, dict] = {}
    left_records: set[str] = set()
    lifetime = runs_from_records(stamps)
    for name, entry in runs_from_records(within(stamps, since)).items():
        seen[name] = {"runs": entry["runs"], "last": entry["last"], "errors": 0}
        left_records.add(name)
    for name, entry in lifetime.items():
        row = seen.setdefault(name, {"runs": 0, "last": None, "errors": 0})
        left_records.add(name)
        if entry.get("last") and (row["last"] is None
                                  or entry["last"] > row["last"]):
            row["last"] = entry["last"]
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
        if last is None:
            # How long it has existed: the commit that added it.
            added = _git("log", "--diff-filter=A", "--format=%aI", "--",
                         part["path"]).strip().splitlines()
            born = _moment(added[-1]) if added else None
            row["age_days"] = (round((now - born).total_seconds() / 86400, 1)
                               if born else None)
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


UNREADABLE = {"__unreadable__": True}


def _notebook() -> dict:
    """The deep pass's own notebook, or a value that says it could not be read.

    NOT `{}` on a parse failure. The pass rewrites this file repeatedly as it
    goes, so a read landing mid-write is ordinary -- and `{}` means "no pass is
    running", which switches the interlock OFF at exactly the moment a pass IS
    running. Rule 8: a failed read is not an empty read. A file that is simply
    absent is a genuine `{}`.
    """
    path = REPO_ROOT / NOTEBOOK
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(UNREADABLE)


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
    if notebook.get("__unreadable__"):
        # Rule 8, and it lands on the safe side by itself: the file exists and
        # we could not read it, which is what a pass writing to it looks like.
        # Answering "no pass" here would open the interlock during the one
        # event it exists to close it for.
        return True
    if not notebook or notebook.get("finished"):
        return False
    started = _moment(notebook.get("at"))
    if started is None:
        return False
    return (now or datetime.now(timezone.utc)) - started < timedelta(hours=24)


def _open_next() -> list[str]:
    """The open lines, through the hook's own parser: one reader, one format."""
    path = REPO_ROOT / ".claude" / "hooks" / "start" / "next_step.py"
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


def messages_floor(notebook, now) -> tuple[str, str]:
    """From when `messages --since-last-pass` should read, and whose moment it is.

    THE PREVIOUS pass, not this one. Step 0 of the deep pass opens the progress
    file by writing this run's own `at` into it, and step 1 then asks this
    question -- so `notebook["at"]` was always "a few minutes ago", the window
    was empty, and step 1 read nothing. It happened tonight, in the pass that
    found it: 0 messages, on an evening of a dozen. Nothing went red, because
    an empty window and a quiet evening look identical from here.

    That is the whole value of step 1 -- the operator's short corrections are
    the one record of which inference failed, and CLAUDE.md says so where it
    tells a pass to run this. So step 0 now carries the moment of the pass it
    is overwriting into `previous_at`, and this reads that.

    The fallback stays a day back rather than nothing -- an empty floor prints
    a month -- but it SAYS which of the three it used, because a floor that is
    wrong in this direction is silent by construction. S01, deep pass of
    2026-09-12.
    """
    previous = (notebook or {}).get("previous_at")
    if previous:
        return str(previous), "the previous pass"
    mine = (notebook or {}).get("at")
    day_back = (now - timedelta(days=1)).isoformat()
    if mine:
        # This pass's own moment would read zero minutes of the evening that
        # produced the work it is reviewing. A day back is a worse floor than
        # the real one and a far better one than that.
        return day_back, ("a day back: the notebook names no previous pass, "
                          "only this one")
    return day_back, "a day back: no pass has written a notebook"


def sessions_to_close(open_sessions, night_running) -> list:
    """Open laboratory sessions worth a reminder: not the night's own.

    One line, and its own function because it is a decision rather than
    plumbing -- a night is an open session on purpose, for up to fourteen
    hours. It lived inside `_lab_facts` until 2026-09-12, where nothing could
    reach it: the test that names this rule handed `lab_open` in already
    filtered, so deleting the clause left every reminder test green and the
    hook nagging "close LAB-0007" all night about the night itself. C05,
    triage 3/3.
    """
    return [session for session in open_sessions if session != night_running]


def _lab_facts() -> dict:
    """What the laboratory is owed: an unfinished session, and a lane that may
    have come back. Both are read from files; a reminder that asked the vendor
    would itself be counted by the check that measures how often we ask."""
    out: dict[str, object] = {"lab_open": [], "nexus_down": 0,
                              "nexus_last_try": None, "night_running": None,
                              "night_until": None, "n_eff": None}
    try:
        from qa import lab

        running = lab.night_running()
        if running:
            out["night_running"], out["night_until"] = running
        out["lab_open"] = sessions_to_close(lab.open_sessions(),
                                            out["night_running"])
        # The newest READING, not computed here -- this function stays a
        # local-file read, same as the rest of it. `book_correlation` does the
        # one live call, per lab session, and logs it; this reads that log
        # back, so a reminder never itself touches the network.
        out["n_eff"] = lab.last_n_eff()
    except Exception:  # noqa: BLE001
        pass

    # Through the state seam, not this module's REPO_ROOT: the three lab
    # readings above already follow qa.state.state_dir(), so reading the
    # questions behind QA_REPO_ROOT made one function answer from two
    # different state directories -- which tests/repo/test_reminders.py works
    # around by setting both. Architecture audit, 2026-09-20.
    from qa.state import state_dir

    rows = _jsonl(state_dir() / "nexus.jsonl")
    asked = [r for r in rows if r.get("type") == "question"]
    # Counted only from THEIR side breaking -- any gave-up used to count here,
    # including our own read failures (`unread: ReadTimeout`, `unknown`), so a
    # session that merely failed to read three answers reported Nexus as down.
    # qa.lab.their_down_streak makes the same "theirs, not ours" distinction
    # #86's own check does, duplicated rather than shared so that check's
    # fingerprint never moves for a reminder-side fix (rule 5).
    from qa.lab import their_down_streak

    streak = their_down_streak(rows)
    out["nexus_down"] = streak if streak >= 3 else 0
    if asked:
        out["nexus_last_try"] = asked[-1].get("at")
    return out


def merge_shapes(stored: dict | None, seen: dict) -> dict:
    """Acknowledge a shape without forgetting what it used to carry.

    `seen` is the memory -- every field a call has EVER carried -- and it is
    what `shape_drift` uses to tell their DESIGN from their CHANGE. Replacing
    it with a 48-hour sample made an intermittent field oscillate for ever:
    vanished, acknowledged, appeared, acknowledged, in the first line of every
    session start. So `seen` unions. `always` is a claim about the present and
    takes the newest reading.

    Pure, and its own function, because that is the half worth a test.
    """
    calls = dict(stored or {})
    for call, shape in (seen or {}).items():
        was = calls.get(call) or {}
        calls[call] = {
            "always": sorted(shape.get("always") or []),
            "seen": sorted(set(was.get("seen") or [])
                           | set(shape.get("seen") or [])),
        }
    return calls


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
    # Under the route's key: shapes agreed before 2026-09-22 carried one key
    # per card or report, and fold into their route here (`surface.rekey`).
    agreed = surface.rekey(stored.get("calls"))
    said = surface.drift_against(agreed, seen)

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
        # UNION the `seen` sets, replace `always`. `seen` is the memory -- every
        # field this call has EVER carried -- and a plain `calls.update(seen)`
        # overwrote it with a 48-hour sample, so an intermittent field
        # oscillated: vanished, acknowledged, appeared, acknowledged, for ever,
        # in the first line of every session start. `always` is the opposite: it
        # is a claim about the present, so the newest reading replaces it.
        calls = merge_shapes(agreed, seen)
        surface.remember({"calls": calls,
                          "tools": listed if listed is not None
                                   else stored.get("tools") or [],
                          "agreed_at": datetime.now(timezone.utc).isoformat(
                              timespec="seconds")})
    try:
        # Agreed to, nothing is left to report.
        _cache_drift([] if update else said)
    except OSError:
        pass
    return said


def drift_cache_path() -> Path:
    from qa.state import state_dir

    return state_dir() / "surface_drift.json"


def _cache_drift(said: list[str]) -> None:
    """What the last scan found, for the session start to read (plan v2, V7,
    E1): the scan took 3.4 s of the hook's 4.3 and grows with the evidence
    store, and four of 24 hook runs timed out and printed nothing."""
    target = drift_cache_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(
        timespec="seconds"), "drift": said}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)


def _surface_facts() -> dict:
    """The drift the patrol or the laboratory tick last found -- read, never
    computed here. Never raises: a session start is not the place to die on
    a stray file."""
    try:
        cached = json.loads(drift_cache_path().read_text(encoding="utf-8"))
        drift = [str(line) for line in cached.get("drift") or []]
    except Exception:  # noqa: BLE001
        return {}
    return {"surface_drift": drift} if drift else {}


def _unarchived() -> int:
    """How many captures the manifest knows and no bundle holds.

    Read rather than counted from disk: `archive.pending` is the same reader
    `keep.py archive` uses to decide what to bundle, so the reminder cannot
    name a number the command would disagree with.
    """
    try:
        from qa import archive, keepset, manifest

        # Only what an archive run could take: a body `prune_runs.py` already
        # let go of can never be bundled, and counting it kept the reminder
        # at 392 after `keep.py archive` had taken everything it could.
        return sum(1 for key in archive.pending(manifest.read())
                   if keepset.evidence_path(key).is_file())
    except Exception:  # noqa: BLE001 -- a reminder never fails a session
        return 0


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
        "evidence_unarchived": _unarchived(),
        "morning_missing": _morning_missing(),
        **_lab_facts(),
        **_surface_facts(),
    }


def _morning_missing() -> bool:
    """Past 7:00 local and today's morning report not published (V11). A
    local-file read, like every fact here."""
    try:
        from qa import morning
        from qa.state import state_dir

        try:
            state = json.loads((state_dir() / "lab" / "morning.json")
                               .read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        return morning.missing(datetime.now().astimezone(),
                               state if isinstance(state, dict) else {})
    except Exception:  # noqa: BLE001 -- a reminder never fails a session
        return False


# A block the harness injects into the user's side. `messages()` learned this
# on compaction summaries; the skill-reinvocation notice has the same shape and
# leaked straight through the first run of the trail.
_HARNESS_BLOCK = re.compile(
    r"^(?:Skill /\S+ was loaded earlier|This session is being continued"
    r"|Caveat: The messages below|<)")


def HARNESS_WROTE_IT(content: str) -> bool:
    """A block the harness injected into the transcript as the operator.

    Matched at the START so quoting one back in a real message does not vanish
    the message, and each opener is fixed text rather than something a person
    types. Narrow on purpose: everything this filter eats is something the
    pass will never read, so a rule that is nearly right here is worse than
    one that is small and certain.

    It knew only the compaction summary until the deep pass of 2026-09-13,
    when `trail()` was given a wider version and this one was not -- so the
    two readers disagreed about what the operator said, and the skill
    re-invocation notice appeared as two of the 38 "messages from the
    operator" in that pass's own step 1, in the reader whose entire job is
    finding their short Czech corrections. One list, both readers.
    """
    return bool(_HARNESS_BLOCK.match(content.lstrip()))


def messages(rows, since: str | None) -> list[tuple[str, str]]:
    """What the operator said since a moment, oldest first.

    Theirs only, and never the harness's own blocks -- a summary injected after
    a compaction is typed by nobody and reads like a wall of instructions.

    It filtered only blocks opening with `<`, and a compaction summary opens
    with a sentence. So three of the 23 "messages from the operator" read on
    2026-09-12 were walls of text I had written myself, each one longer than
    everything they actually said that day put together -- in the one reader
    whose whole job is to find the short Czech corrections. Anchored on the
    harness's own opening sentence, which is fixed text and not something a
    person types. S02, found by step 1 the first time it could see anything.
    """
    floor = _moment(since) if since else None
    out = []
    for row in rows:
        # isMeta: the harness speaking as the user -- a /loop's own prompt on
        # every firing, which made most of step 1's reading "jdi do laborky"
        # (E6, review of 2026-09-23).
        if row.get("type") != "user" or row.get("isMeta"):
            continue
        stamp = _moment(row.get("timestamp"))
        if stamp is None or (floor is not None and stamp < floor):
            continue
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if content.lstrip().startswith("<") or HARNESS_WROTE_IT(content):
            continue
        out.append((str(row.get("timestamp")), " ".join(content.split())))
    return sorted(out)



# How much of one entry the trail keeps. The source is tens of megabytes and
# the point is a few readable pages, not a second copy of the day.
TRAIL_CHARS = 400

# A sentence in which the assistant says it had been wrong. Czech and English,
# because the thinking is English and the answers to the operator are Czech.
# Deliberately narrow: "I was wrong" is evidence, "this is wrong" is a bug
# report about something else, and a list that matches both is a list that
# matches everything.
_ADMITS = re.compile(
    r"\b(?:"
    r"m[yý]lil jsem se|m[aá][sš] pravdu|m[aá]te pravdu|to bylo [sš]patn[eě]"
    r"|opravuj[iu]|opravil jsem|mus[ií]m (?:se )?opravit|p[rř]izn[aá]v[aá]m"
    r"|odbyl jsem|to je m[aá] chyba|moje (?:vina|chyba)"
    r"|i was wrong|i got (?:this|that|it) wrong|my (?:mistake|error)"
    r"|correcting myself|i overstated|that was wrong of me"
    r")\b", re.I)

# Breakage in something that was supposed to already work. NOT a pytest
# failure: CLAUDE.md requires the test before the implementation, so every new
# check is red once on purpose. Over three hours of 2026-09-13 the first draft
# of this reader returned eight "errors" of which nearly all were the workflow
# working, against one correction -- a reader whose loudest signal is the rule
# being followed buries the one line worth reading.
_WENT_RED = re.compile(
    r"\bTraceback \(most recent"
    r"|\b(?:Syntax|Type|Key|Name|Value|Attribute|Index)Error\b"
    r"|\bUnicode\w*Error\b")

# Broke because a machine was busy, not because anything was inferred wrongly.
# Three screenshot timeouts landed in the first run of this reader.
_JUST_THE_MACHINE = re.compile(
    r"screenshot failed|did not finish rendering|timed out after"
    r"|ECONNREFUSED|Read timed out|was denied or failed", re.I)

# pytest's own banners. An exception raised INSIDE a test run is the
# test-first rule working -- a new check names a function nobody has written
# and fails with AttributeError -- while the same exception from a probe
# script is a real mistake. Told apart by where it happened, not by what it
# says, because the words are identical.
_A_TEST_RUN = re.compile(r"short test summary info|=+ FAILURES =+|"
                         r"\d+ (?:passed|failed)[,.]")
# A traceback printed by Python itself -- a probe script or a crash -- and not
# by pytest's report, which never prints this header.
_A_PROBE_TRACEBACK = re.compile(r"\bTraceback \(most recent call last\)")

def _blocks(row) -> list:
    content = (row.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def trail(rows, since: str | None, limit: int = 120) -> list[dict]:
    """The day as the transcript remembers it: theirs, ours, and what broke.

    [operator 2026-09-13] asked why the whole context is not kept for the deep
    pass. It already is -- the harness writes every row of every session to
    disk, and this session's own file is 13 MB of which 5 MB is the
    assistant's side. What was missing was a reader: `messages()` keeps
    `type == "user"` and drops the rest, so step 1's question -- which
    inference failed -- could see the correction and never the thing corrected.

    Three kinds, interleaved by time, because the ORDER carries the finding: a
    correction after an operator message is being caught, and one after a red
    test is catching yourself. Grouped by kind that distinction is gone.

    Bounded twice, per entry and in total. A reader that has to be skimmed is
    one nobody runs, which is the failure this whole file exists to name.
    """
    floor = _moment(since) if since else None
    out: list[dict] = []
    for row in rows:
        stamp = _moment(row.get("timestamp"))
        if stamp is None or (floor is not None and stamp < floor):
            continue
        at = str(row.get("timestamp"))
        kind = row.get("type")

        if kind == "user":
            if row.get("isMeta"):
                continue  # a /loop's own prompt, not the operator (E6)
            content = (row.get("message") or {}).get("content")
            if isinstance(content, str) and content.strip():
                if (_HARNESS_BLOCK.match(content.lstrip())
                        or HARNESS_WROTE_IT(content)):
                    continue
                out.append({"at": at, "kind": "operator",
                            "text": " ".join(content.split())[:TRAIL_CHARS]})
                continue
            for block in _blocks(row):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_result":
                    continue
                body = block.get("content")
                if isinstance(body, list):
                    body = " ".join(str(b.get("text", "")) for b in body
                                    if isinstance(b, dict))
                body = str(body or "")
                # The harness's own flag is the signal. Until the deep pass of
                # 2026-09-13 a SUCCESSFUL result was kept whenever its text
                # matched _WENT_RED, so a Read of qa/lab.py or of NEXT.md, or
                # grep output, was filed as breakage because the word
                # "TypeError" appeared in it -- 35 of 48 error rows over
                # 2026-09-12 (A02, 3/3). And _A_TEST_RUN was applied to the
                # whole result, so one Bash call running a probe and then
                # pytest lost the probe's traceback to the green half that
                # followed it (R04, 3/3). Both go away by reading the flag:
                # a result that did not fail is not breakage, and a pytest
                # failure alone does not set the flag.
                if not block.get("is_error"):
                    continue
                if _JUST_THE_MACHINE.search(body):
                    continue
                # A red test run and nothing else is the test-first rule
                # working; a red run whose output ALSO carries a traceback
                # from something that was meant to work is not. Told apart by
                # the traceback's own header, which pytest's report does not
                # print: an `AttributeError` INSIDE the run is the test naming
                # a function not yet written, and matching _WENT_RED on it
                # kept every test-first run as breakage (C05, deep pass of
                # 2026-09-19, 3/3).
                if (_A_TEST_RUN.search(body)
                        and not _A_PROBE_TRACEBACK.search(body)):
                    continue
                out.append({"at": at, "kind": "error",
                            "text": " ".join(body.split())[:TRAIL_CHARS]})

        elif kind == "assistant":
            for block in _blocks(row):
                if not isinstance(block, dict) or block.get("type") != "text":
                    continue
                text = str(block.get("text") or "")
                if _ADMITS.search(text):
                    out.append({"at": at, "kind": "correction",
                                "text": " ".join(text.split())[:TRAIL_CHARS]})

    out.sort(key=lambda r: r["at"])
    return out[-limit:]


def trail_cut(rows, since: str | None, limit: int = 120) -> int:
    """How many older entries `trail` left out at this limit -- it cut to 120
    without a word, so step 1 could not tell a quiet day from a cut one (E6)."""
    return max(0, len(trail(rows, since, limit=10 ** 9)) - limit)


def day_row(state: dict) -> dict:
    """The patrol's state as one row of audits/processes.jsonl. The counts are
    over the patrol's window, seven days, so they say so: labelled `runs`,
    daily rows of seven-day totals read as a week's work every day (E8)."""
    return {"at": state["at"], "day": state["day"],
            "parts": {name: {"runs_7d": part.get("runs", 0),
                             "errors_7d": part.get("errors", 0)}
                      for name, part in (state.get("parts") or {}).items()},
            "sizes": state.get("sizes") or {}}

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


# --- what a day of the laboratory's /loop costs (plan v2, V6) --------------

# A firing is the loop's prompt arriving: "jdi do laborky" as the operator gave
# it to /loop, and its older name. The /loop command itself runs it once too;
# typed into an idle session it is recorded as <command-message>, skips the
# queue, and so is one firing a loop start this does not count.
LOOP_PROMPT = re.compile(r"^\s*(?:/loop\s+\S+\s+)?(?:jdi do labor|pokra[cč]uj)",
                         re.I)
TYPED_LOOP_PROMPT = re.compile(r"^\s*(?:/loop\s+\S+\s+)?jdi do labor", re.I)
# The tick's own last line, at the start of a line -- the skill quotes it in
# backticks, so its text is never read as a tick's decision.
DECIDE_LINE = re.compile(r"(?:^|\n)decide: ([^\n]+)")


def project_slug(root: Path | None = None) -> str:
    """This project's directory name under ~/.claude/projects."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(root or CODE_ROOT).resolve()))


def project_transcripts(home: Path | None = None,
                        since: datetime | None = None) -> list[Path]:
    """THIS project's transcripts, newest last. `transcript_rows()` globs
    `*cymetica*` and so reads the web-qa-agent project's too (plan v1, L7);
    what is written from V6 on does not inherit that."""
    folder = Path(home or Path.home()) / ".claude" / "projects" / project_slug()
    found = []
    for path in folder.glob("*.jsonl"):
        try:
            stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            continue
        if since is None or stamp >= since:
            found.append((stamp, path))
    return [path for _, path in sorted(found)]


def _texts(content) -> list[str]:
    """Every tool result's text in one user record."""
    out = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        inner = block.get("content")
        if isinstance(inner, str):
            out.append(inner)
        elif isinstance(inner, list):
            out.extend(str(part.get("text") or "") for part in inner
                       if isinstance(part, dict))
    return out


def loop_firings(lines) -> list[dict]:
    """One transcript's loop firings: when, how many model calls followed
    (a call streamed as several records is one), on which model, and what
    the tick decided -- [] for none, None when no tick line was seen.

    A firing's calls run until the next prompt that is not a task
    notification: the operator speaking starts their own turn."""
    firings: list[dict] = []
    current = None
    for line in lines:
        if not ('"assistant"' in line or "queue-operation" in line
                or "decide: " in line
                or ('"type":"user"' in line and "tool_result" not in line)):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        kind = row.get("type")
        if kind == "queue-operation" and row.get("operation") == "enqueue":
            content = str(row.get("content") or "")
            if LOOP_PROMPT.match(content):
                current = {"at": str(row.get("timestamp") or ""), "ids": set(),
                           "models": {}, "decide": None}
                firings.append(current)
            elif not content.startswith("<task-notification>"):
                current = None
            continue
        message = row.get("message") or {}
        typed = message.get("content") if kind == "user" else None
        if isinstance(typed, str) and not row.get("isMeta") \
                and not typed.startswith("<"):
            # Typed while the session was idle, a prompt skips the queue. Only
            # the laboratory's own words: "pokračuj" TYPED is the operator
            # saying carry on in whatever session they are in -- two plan
            # sessions were counted as lab firings that way (R01, deep pass of
            # 2026-09-24). A /loop queues its prompt, old name and all.
            if not TYPED_LOOP_PROMPT.match(typed):
                current = None
            elif current is None or current["ids"]:
                current = {"at": str(row.get("timestamp") or ""), "ids": set(),
                           "models": {}, "decide": None}
                firings.append(current)
            continue
        if current is None:
            continue
        if kind == "assistant":
            ident = message.get("id") or row.get("uuid")
            if ident and ident not in current["ids"]:
                current["ids"].add(ident)
                model = str(message.get("model") or "?")
                current["models"][model] = current["models"].get(model, 0) + 1
        elif kind == "user" and not row.get("isMeta"):
            for text in _texts(message.get("content")):
                for said in DECIDE_LINE.findall(text):
                    said = said.strip()
                    current["decide"] = ([] if said == "none" else
                                         [item.strip() for item in said.split(" + ")])
    out = []
    for firing in firings:
        models = firing.pop("models")
        firing["calls"] = len(firing.pop("ids"))
        firing["models"] = models
        firing["model"] = max(models, key=models.get) if models else None
        out.append(firing)
    return out


def loop_days(firings: list[dict]) -> dict[str, dict]:
    """Per UTC day: firings, how many worked (the tick decided something),
    how many were quiet and what the dearest quiet one cost, and the models
    every call ran on -- V6's done-when, as numbers."""
    days: dict[str, dict] = {}
    for firing in firings:
        day = days.setdefault(firing["at"][:10], {
            "firings": 0, "working": 0, "quiet": 0, "unknown": 0,
            "calls": 0, "quiet_calls_max": 0, "models": {}})
        day["firings"] += 1
        day["calls"] += firing["calls"]
        for model, n in firing["models"].items():
            day["models"][model] = day["models"].get(model, 0) + n
        if firing["decide"] is None:
            day["unknown"] += 1
        elif firing["decide"]:
            day["working"] += 1
        else:
            day["quiet"] += 1
            day["quiet_calls_max"] = max(day["quiet_calls_max"], firing["calls"])
    return days


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
    walk = sub.add_parser("trail", help="theirs, our corrections, and what "
                                        "went red -- interleaved in time")
    walk.add_argument("--since", help="ISO timestamp")
    walk.add_argument("--since-last-pass", action="store_true",
                      help="since the deep pass's own notebook says it started")
    walk.add_argument("--limit", type=int, default=120)
    cost = sub.add_parser("loop", help="what each day of the laboratory's "
                                       "/loop cost: firings, working, calls, "
                                       "models (plan v2, V6)")
    cost.add_argument("--days", type=int, default=3)
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if args.cmd == "reminders":
        for line in reminders(facts(), datetime.now(timezone.utc)):
            print(line)
        return 0

    if args.cmd == "loop":
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        firings = []
        for path in project_transcripts(since=since):
            with open(path, encoding="utf-8", errors="replace") as handle:
                firings += loop_firings(handle)
        days = loop_days([f for f in firings
                          if (_moment(f["at"]) or since) >= since])
        if not days:
            print("no loop firing in the window")
        for day, row in sorted(days.items()):
            models = ", ".join(f"{m} {n}" for m, n in sorted(row["models"].items()))
            print(f"{day}: {row['firings']} firing(s), {row['working']} working, "
                  f"{row['quiet']} quiet (dearest {row['quiet_calls_max']} "
                  f"call(s)), {row['unknown']} without a decide line; "
                  f"{row['calls']} call(s) -- {models}")
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
        # The deep pass runs the patrol, so the pass refreshes the drift the
        # session start reads (V7); the laboratory tick does it by day.
        try:
            surface_drift()
        except Exception:  # noqa: BLE001 -- the patrol is not about their side
            pass
        state = patrol(since=floor)
        if getattr(args, "extract", False):
            extract(REPO_ROOT, day_row(state))
        if getattr(args, "flags", False):
            for line in flags(state):
                print(line)
            return 0
        print(render(state))
        return 0

    since = args.since
    whose = "asked for"
    if args.since_last_pass and not since:
        since, whose = messages_floor(_notebook(), datetime.now(timezone.utc))

    if args.cmd == "trail":
        rows = list(transcript_rows())
        walked = trail(rows, since, limit=args.limit)
        cut = trail_cut(rows, since, limit=args.limit)
        counts = {k: sum(1 for r in walked if r["kind"] == k)
                  for k in ("operator", "correction", "error")}
        print(f"# {len(walked)} entr(ies) since {since} ({whose}) -- "
              + ", ".join(f"{v} {k}" for k, v in counts.items())
              + (f"; {cut} older not shown (--limit)" if cut else ""))
        mark = {"operator": "THEY", "correction": "WRONG", "error": "RED "}
        for row in walked:
            print(f"{row['at'][11:16]}  {mark[row['kind']]}  {row['text']}")
        return 0

    found = messages(transcript_rows(), since)
    print(f"# {len(found)} message(s) from the operator since {since} ({whose})")
    for stamp, text in found[-args.limit:]:
        print(f"{stamp[11:16]}  {text[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
