"""Every part of this system is found, counted and looked at -- without being registered.

[operator 2026-09-11] asked for the self-improvement to be in the DNA: a part
added in a month must record itself, measure itself and be looked back at
without anyone remembering to wire it in. The first design put five declared
keys in every SKILL.md. A reviewer pointed out what that really is -- a
registry, and a registry is a thing to forget.

So the patrol discovers instead: every skill, agent, script and hook by glob,
and what each one did from the records it left and from the commands in the
transcripts. Nothing to declare, nothing to keep in step.

These tests are the DNA: they are what stops the patrol being quietly switched
off, and they are written so a new part cannot be invisible to it.

  * a skill that exists only in a fixture directory is found, with no entry
    anywhere;
  * a run is credited from what a part LEFT BEHIND, not only from a Skill call.
    Sessions follow these skills by reading them: the Nexus session counted
    zero Skill calls on the day it opened four rooms;
  * the extract is idempotent and still says the same thing when the
    transcripts are gone -- they are deleted after thirty days and the
    laboratory will run for months;
  * an idle part produces a flag, never a failure. A quiet script must not be
    able to make the night revert its own work (step 9);
  * the deep pass reads it in the steps that look back, or the numbers are
    computed for nobody;
  * no ceiling is set below where the repository already stands, because a
    warning that is on from the first day is a warning nobody reads.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "processes_dna", REPO / "scripts" / "processes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture_repo(tmp_path: Path) -> Path:
    """A repository with one skill, one hook and one script, and nothing else."""
    (tmp_path / ".claude" / "skills" / "laborator").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "laborator" / "SKILL.md").write_text(
        "---\nname: laborator\ndescription: a part added later\n---\n\nbody\n",
        encoding="utf-8")
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks" / "room_notes.py").write_text(
        "print()\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "lab.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "audits").mkdir()
    return tmp_path


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_part_nobody_registered_is_found_anyway(tmp_path, monkeypatch):
    mod = _module()
    root = _fixture_repo(tmp_path)
    found = {part["name"]: part for part in mod.parts(root)}

    assert "laborator" in found, found
    assert found["laborator"]["kind"] == "skill"
    assert "lab.py" in found, found
    assert "room_notes.py" in found, found
    assert found["lab.py"]["kind"] == "script"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_is_credited_from_what_it_left_behind(tmp_path):
    """The session that opened four rooms on 2026-09-11 called the Skill tool
    zero times: it read the file and followed it. A patrol that counts only
    Skill calls would have reported the laboratory as never used while its
    records grew all day."""
    mod = _module()
    rows = [
        {"type": "user", "timestamp": "2026-09-12T08:00:00Z",
         "message": {"content": "jdi do laboratore"}},
        {"type": "assistant", "timestamp": "2026-09-12T08:01:00Z",
         "message": {"content": [
             {"type": "tool_use", "name": "Bash",
              "input": {"command": "python scripts/lab.py status"}}]}},
    ]
    seen = mod.runs_from_transcripts(rows)
    assert seen.get("lab.py", {}).get("runs") == 1, seen

    left = mod.runs_from_records({"lab.py": ["2026-09-12T09:00:00+00:00",
                                             "2026-09-12T10:00:00+00:00"]})
    assert left["lab.py"]["runs"] == 2, left
    assert left["lab.py"]["last"] == "2026-09-12T10:00:00+00:00", left


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_extract_is_idempotent_and_outlives_the_transcripts(tmp_path):
    """Transcripts are kept about thirty days; the laboratory runs for months.
    The counts are appended to audits/ so the series survives, and appending
    the same day twice may not double it."""
    mod = _module()
    root = _fixture_repo(tmp_path)
    day = {"at": "2026-09-12T20:00:00+00:00", "day": "2026-09-12",
           "parts": {"lab.py": {"runs": 3, "errors": 0}}}

    mod.extract(root, day)
    mod.extract(root, day)
    written = [json.loads(line) for line in
               (root / "audits" / "processes.jsonl").read_text(
                   encoding="utf-8").splitlines() if line.strip()]
    assert len(written) == 1, written

    mod.extract(root, {**day, "day": "2026-09-13"})
    written = [json.loads(line) for line in
               (root / "audits" / "processes.jsonl").read_text(
                   encoding="utf-8").splitlines() if line.strip()]
    assert len(written) == 2, written
    assert written[0]["parts"]["lab.py"]["runs"] == 3


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_idle_part_is_a_flag_and_never_a_failure(tmp_path):
    """Step 9 reverts a night on a red it cannot resolve. A script nobody ran
    for a fortnight is a question for the week, not a reason to throw away the
    work of a night."""
    mod = _module()
    flags = mod.flags({
        "parts": {"lab.py": {"runs": 0, "last": None, "idle_days": 30}},
        "sizes": {},
    })
    assert any("lab.py" in line for line in flags), flags
    # It is a sentence, not an exception: nothing here raises.
    assert all(isinstance(line, str) for line in flags)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hook_nobody_wired_is_named(tmp_path):
    """A hook leaves no record when it runs, so the patrol cannot count its
    runs -- and the failure that matters is not how often it ran. It is a hook
    written, committed and never fired because nobody put it in settings.json.
    Nothing checked the SessionStart wiring before this."""
    mod = _module()
    root = _fixture_repo(tmp_path)
    assert "room_notes.py" in mod.unwired_hooks(root)

    (root / ".claude" / "settings.json").write_text(json.dumps({
        "hooks": {"SessionStart": [{"hooks": [
            {"args": [".claude/hooks/room_notes.py"]}]}]}}), encoding="utf-8")
    assert mod.unwired_hooks(root) == []
    assert mod.unwired_hooks(REPO) == [], "a hook here that never fires"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_effort_of_a_commit_is_read_even_when_git_will_not_parse_it():
    """73 of 188 commits carry an `Effort:` line git does not read as a
    trailer: one-line messages, and an Effort paragraph written above
    Co-Authored-By. The hook is fixed for what comes next; the history cannot
    be, so the reader takes the line wherever it stands."""
    mod = _module()
    lenient = mod.effort_counts(limit=200)
    strict = mod.effort_counts(limit=200, trailers_only=True)
    conclude(Measurement(
        # FAILED, not inconclusive. The lenient reader is a superset of git's
        # trailer parser by construction -- same commits, a looser regex over
        # the whole body -- so `lenient < strict` cannot mean "could not
        # measure". It can only mean the reader broke, and reporting that as
        # inconclusive made this check green-or-skipped with no red state at
        # all: three readers each broke EFFORT_LINE and watched the suite stay
        # green while the week went blind to a third of its own evidence.
        # Rule 10's "inconclusive is never a defect" is about THEIR surfaces,
        # not about our own reader refuting itself.
        #
        # `>=`, not `>`. The comment above states the broken-reader condition
        # as `lenient < strict`, and the verdict asked for `lenient > strict` --
        # so EQUALITY read as a broken reader. The 47 malformed messages in the
        # window are history and the hook that made them is fixed, so the day
        # 200 well-formed commits sit on top, lenient == strict == 200 and this
        # goes red with the reader perfect. It is a window sliding over a
        # repaired past, which is the same shape as a check over a growing log.
        #
        # And zero is not equality. `_git` returns "" on a non-zero exit, which
        # gives 0 >= 0 -- a read that never happened reported as a reader that
        # works. Rule 8, so that case is inconclusive and says which.
        #
        # But only when git found none EITHER. Strict above zero proves git
        # answered, so a lenient zero beside it is the broken reader itself --
        # the mutation of EFFORT_LINE the paragraph above names read
        # inconclusive until C03, deep pass of 2026-09-19 (3/3).
        verdict=("inconclusive" if not sum(lenient.values())
                 and not sum(strict.values())
                 else "passed" if sum(lenient.values()) >= sum(strict.values())
                 else "failed"),
        reason=(f"no commit in the window carries an effort at all, so the "
                f"reader was not exercised -- git may not have answered"
                if not sum(lenient.values()) and not sum(strict.values())
                else
                f"the lenient reader finds {sum(lenient.values())} efforts "
                f"where git's trailer parser finds {sum(strict.values())}"),
        left=lenient, right=strict,
        sources={"history": "git log --format=%B"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_ceiling_is_set_below_where_we_already_stand():
    """A warning that is on from the first day is a warning nobody reads. Every
    ceiling is checked against the repository as it is now."""
    mod = _module()
    standing = mod.sizes()
    over = [line for line in mod.flags({"parts": {}, "sizes": standing})]
    conclude(Measurement(
        verdict="failed" if over else "passed",
        reason=("a ceiling is already exceeded on the day it was set: "
                + "; ".join(over) if over else
                f"none of the {len(standing)} ceilings fires today"),
        left=standing, right={"flags": len(over)},
        sources={"patrol": "scripts/processes.py::flags"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_deep_pass_reads_the_patrol_in_the_steps_that_look_back():
    """Numbers computed for nobody are the shape this whole phase replaces."""
    text = (REPO / ".claude" / "skills" / "deep-pass" / "SKILL.md").read_text(
        encoding="utf-8")
    missing = [step for step, marker in (
        ("1", "### 1 · What the work so far taught"),
        ("1b", "### 1b · Prořez"),
        ("11", "### 11 · Týden"),
    ) if "processes.py" not in text.split(marker)[-1].split("### ")[0]]
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"step(s) {', '.join(missing)} of the deep pass never read the "
                f"patrol" if missing else
                "steps 1, 1b and 11 all read scripts/processes.py"),
        left={"steps": ["1", "1b", "11"]}, right={"missing": missing},
        sources={"skill": ".claude/skills/deep-pass/SKILL.md"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_memory_ceiling_counts_what_can_actually_be_brought_down():
    """P01, deep pass of 2026-09-13, triage 2/3.

    `memory_lines` counted RAW LINES of MEMORY.md, and step 1b of the deep
    pass requires a retired memory to keep its line for ever -- marked
    `RETIRED`, never removed, because that index is the only history the
    directory has outside git. So a retirement could not reduce the number it
    was supposed to reduce, every pass that retired anything pushed it up, and
    the only available response was to raise the ceiling: 45 -> 48 earlier the
    same day, and red again at 49 by the evening.

    A ceiling on a monotone number is the same defect as a check over a
    growing log that can never go green. What it watches now is the count of
    LIVE pointers -- the thing prořez can actually reduce, by merging.
    """
    module = _module()
    measured = module.sizes()
    live = measured.get("memory_lines")
    if live is None:
        pytest.skip("no memory index on this machine, so nothing to count")

    index = next(iter((Path.home() / ".claude" / "projects").glob(
        "*cymetica*/memory/MEMORY.md")), None)
    assert index is not None
    text = index.read_text(encoding="utf-8")
    raw = len(text.splitlines())
    retired = len([l for l in text.splitlines() if "RETIRED" in l])

    assert live < raw, (
        f"the ceiling still counts every line ({live} of {raw}); a retired "
        f"line can never be removed, so the number can only grow")
    assert live == raw - retired - len(
        [l for l in text.splitlines() if not l.strip().startswith("- [")]), (
        f"live={live}, raw={raw}, retired={retired}: the count should be the "
        f"pointers that are still in force")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_ceiling_watches_something_that_is_actually_measured():
    """A ceiling on a key nothing emits is a warning that can never fire.

    `CEILINGS["pack_growth_mb"]` against `sizes()["pack_mb"]`: `flags()` does
    `measured.get(key)`, gets None, and continues. So on 2026-09-12 -- the day
    whose entire plan was the size of git -- **nothing watched the size of
    git**, and the test that looks like it covers this only asserts "no flag
    today", which a dead ceiling makes MORE likely to pass.

    Stated over the whole set rather than that one key, because the defect is
    the pairing, not the name.

    **Read from what `sizes()` CAN emit, not from what it did.** Three of its
    keys are conditional: `evidence_mb` only when `<root>/evidence` is a
    directory -- gitignored since D3, so absent in any clone -- `memory_lines`
    only when the memory index exists, and `next_oldest_days` only when NEXT.md
    has an open item, which is the state we are trying to reach. So on a clone,
    or on a day with nothing open, this reported two correctly-paired ceilings
    as watching nothing. A machine's momentary emission is not the pairing.

    Taken off the source with `ast` rather than from a list beside it: a
    declaration of what `sizes()` emits is a thing to forget, and CLAUDE.md's
    DNA rule is that every part is found rather than registered.
    """
    import ast

    module = _module()
    tree = ast.parse((REPO / "scripts" / "processes.py").read_text(
        encoding="utf-8"))
    emits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "sizes":
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Subscript):
                    continue
                if not (isinstance(inner.value, ast.Name)
                        and inner.value.id == "out"):
                    continue
                key = inner.slice
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    emits.add(key.value)
    assert emits, (
        "no `out[...]` assignment was found in sizes(), so this check read "
        "nothing and could not have failed -- the reader, not the pairing")

    dead = sorted(set(module.CEILINGS) - emits)
    conclude(Measurement(
        verdict="failed" if dead else "passed",
        reason=(f"ceiling(s) on nothing: {', '.join(dead)} — sizes() can emit "
                f"{', '.join(sorted(emits))}" if dead else
                f"all {len(module.CEILINGS)} ceiling(s) watch a measurement "
                f"sizes() can emit"),
        left=sorted(module.CEILINGS), right=sorted(emits),
        sources={"patrol": "scripts/processes.py::CEILINGS"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_window_counts_runs_while_the_whole_history_keeps_the_last_seen(
        tmp_path, monkeypatch):
    """Verification step 5 of docs/data-plan.md, which the plan claimed and
    did not deliver.

    `patrol(since=...)` bounded only the transcript half; `records_by_part()`
    took no floor at all, so the printed `runs` was a lifetime count ADDED to a
    windowed one — ledger.py read 419 over a seven-day window.

    The trap in the obvious fix is the reason this test pins both halves: push
    the window into the records and `last` goes with it, `idle_days` becomes
    None, and `flags()` stops firing the fortnight warning on exactly the parts
    it exists to find. Two passes over one read — the window counts, the whole
    history remembers.
    """
    module = _module()
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "quiet.py").write_text("", encoding="utf-8")
    old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "state" / "nexus.jsonl").write_text(
        json.dumps({"at": old, "type": "question"}) + "\n", encoding="utf-8")

    stamps = {"quiet.py": [old]}
    since = datetime.now(timezone.utc) - timedelta(days=30)
    windowed = module.runs_from_records(module.within(stamps, since))
    lifetime = module.runs_from_records(stamps)

    assert windowed.get("quiet.py", {}).get("runs", 0) == 0, (
        "a record older than the window was counted inside it")
    assert lifetime["quiet.py"]["last"] == old, (
        "the window swallowed the last-seen, which is what lights the "
        "fortnight warning")

    # The CLI hands `since` in as an ISO STRING. The first version of `within`
    # compared it to a datetime and crashed every `patrol --since` on the
    # command line, while this test passed because it handed in a datetime.
    assert module.within(stamps, since.isoformat()) ==         module.within(stamps, since), "a string floor is not the same floor"

    state = {"parts": {"quiet.py": {"runs": 0, "errors": 0, "last": old,
                                    "kind": "script", "idle_days": 60.0}},
             "sizes": {}}
    assert any("quiet.py" in line for line in module.flags(state)), (
        "a part idle for 60 days lights no warning")

    # Through `patrol` itself. Everything above composes `within` and
    # `runs_from_records` in the TEST, so reverting scripts/processes.py's own
    # line to `runs_from_records(stamps)` -- the exact regression this
    # docstring names -- left all of it green: no test in the repository called
    # `patrol` at all, and the two fixture files written above were handed to
    # nothing. 3/3, deep pass of 2026-09-13.
    monkeypatch.setattr(module, "records_by_part", lambda base: stamps)
    walked = module.patrol(root=tmp_path, since=since)
    row = walked["parts"].get("quiet.py")
    assert row is not None, f"patrol did not find quiet.py: {sorted(walked['parts'])}"
    assert row["runs"] == 0, (
        f"patrol counted {row['runs']} run(s) inside a thirty-day window for a "
        f"record sixty days old -- the lifetime count added to the windowed one")
    assert row["last"] == old, (
        "patrol lost the last-seen, and the fortnight warning reads it")
