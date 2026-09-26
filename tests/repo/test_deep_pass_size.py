"""The deep pass, sized by what changed and read back by what it left.

Plan v2, V7. The architect's review (2026-09-23): the pass's self-maintenance
was sized for a team while it runs on one Pro plan, and 27 843 Opus messages
stood against 1 133 on Sonnet. So a pass is as big as its diff -- full for
anything but prose, light for prose alone. (A third size, deferred -- not run
at all when the week was nearly spent -- was removed on 2026-09-25: the
operator watches the plan's limits.) And the review's E5: a
pass that dies halfway is silent, and the next step 0 overwrites the gaps it
had confirmed.

Landed in the 1c form (three triage readers, this test, a paragraph under
Změněná pravidla in DEEP-PASS.md), because the pass's spine is a rule.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module(path=REPO / "scripts" / "deep_pass_process.py", name="dp_size"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_is_as_big_as_what_changed():
    dp = _module()
    size = lambda files, commits: dp.pass_size(files, commits)[0]
    assert size(["qa/fold.py"], 2) == "full", "the core moved"
    assert size(["tests/rest/test_cards.py"], 2) == "full", "a check moved"
    assert size(["scripts/submit.py"], 2) == "full", "what talks to them moved"
    # What all three 1c readers of the first draft found called light: code
    # that POSTs to their platform, or decides what the ledger says. Light is
    # now a list of the harmless, so a file nobody listed is full.
    for path in ("scripts/nexus.py", "scripts/paper.py", "scripts/clone.py",
                 "scripts/bounty.py", "scripts/ledger.py", "scripts/findings.py",
                 "qa/fingerprint.py", "state/journal/events.jsonl",
                 "scripts/lab.py", "scripts/a_script_added_next_month.py",
                 # ...and the second draft's: the guards themselves.
                 "tests/meta/test_pipeline_decisions.py", "tests/repo/test_x.py",
                 "audits/checks.json", ".claude/hooks/start/reminders.py",
                 "scripts/processes.py", "scripts/deep_pass_process.py",
                 # ...and the third's: a page script that writes state/ and
                 # loads the scripts that POST.
                 "scripts/lab_page.py", "scripts/morning.py"):
        assert size([path], 1) == "full", path
    assert size(["docs/x.md"], dp.FULL_COMMITS) == "full", "a long day"
    assert size(["docs/x.md", "NEXT.md", "ARCHITECTURE.md"], 3) == "light"
    # No budget any more (operator, 2026-09-25: the plan's limits are theirs
    # to watch): the week's use is not an input and `deferred` is never said.
    assert not hasattr(dp, "DEFER_WEEKLY_PCT")
    assert size(["qa/fold.py"], 30) == "full"
    mode, why = dp.pass_size(["qa/state.py"], 1)
    assert "qa/state.py" in why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_size_command_reads_the_real_commit_count():
    """`_git` keeps git's trailing newline, and "89\\n".isdigit() is False, so
    the first version read every commit count as 0 -- a long day could never
    make a pass full. Found when the unreadable case was made to fail
    closed and this repository's own diff came back "could not be read"."""
    result = subprocess.run([sys.executable, str(REPO / "scripts" / "deep_pass_process.py"),
                             "size"], cwd=REPO, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stderr
    upstream = subprocess.run(["git", "rev-parse", "@{upstream}"], cwd=REPO,
                              capture_output=True, text=True)
    if upstream.returncode == 0:
        assert "could not be read" not in result.stdout, result.stdout

    # The count itself, not only the absence of a message: git's "89\n" must
    # reach pass_size as 89, which the old `else 0` read as 0 and still
    # printed no "could not be read" (deep pass 2026-09-24, A10, 3/3).
    dp = _module()
    seen = []
    dp._git = lambda *a: "89\n" if a[0] == "rev-list" else "docs/x.md\n"
    dp.pass_size = lambda files, commits: seen.append(commits) or ("light", "x")
    assert dp.main(["size"]) == 0
    assert seen == [89], seen


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_gaps_a_dead_pass_confirmed_are_carried_not_overwritten():
    """E5: step 0 overwrites the notebook, so a pass that died between its
    triage and its fixes lost what it had confirmed, silently."""
    dp = _module()
    previous = {"run": "dp-1", "finished": False, "gaps": [
        {"id": "T01", "verdict": "real", "fixed": False},
        {"id": "T02", "verdict": "real", "fixed": True},
        {"id": "T03", "verdict": "false", "fixed": False},
        {"id": "T04", "verdict": "real", "fixed": False,
         "deferred_to_operator": True},
        {"id": "T05", "verdict": None, "fixed": False},
        {"id": "T06", "verdict": "minority", "fixed": False}]}
    carried = dp.carried_gaps(previous)
    # A pass that died never wrote the report that would have shown the
    # operator T04 and the minority T06, so both are carried (1c readers).
    assert [g["id"] for g in carried] == ["T01", "T04", "T05", "T06"], carried
    assert all(g["carried_from"] == "dp-1" for g in carried)
    # A finished pass showed what it handed over; it carries the rest.
    assert [g["id"] for g in dp.carried_gaps(
        {**previous, "finished": True})] == ["T01", "T05"]
    assert dp.carried_gaps({}) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_deferred_pass_relaxes_no_guard_because_it_does_not_run():
    """Three rounds of 1c readers took apart a "minimal" pass that finished
    without reviewing: it could push, verify, silence the "pass owed"
    reminder or fail its own guard. A deferred pass writes nothing, so the
    guard is left exactly as strict: a notebook that finished without a
    review is still a problem, whatever size it claims."""
    spec = importlib.util.spec_from_file_location(
        "finished_guard", REPO / "tests" / "repo" / "test_deep_pass_finished.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    notebook = {"run": "dp-x", "at": "2026-09-24T21:00:00+00:00",
                "at_finished": "2026-09-24T21:20:00+00:00", "finished": True,
                "size": "deferred", "gaps": [],
                "retrospective": {"last": "2026-09-22", "done": False},
                "rule_changes": [], "next": [],
                "meta_tests": {"start": 786, "end": 786, "reason": None}}
    said = guard.problems(notebook, agreed_items=set())
    assert any("review" in p for p in said), said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_area_is_read_whole_after_enough_change_or_a_month():
    """Plan v2, V7: a part of the core is read whole when much changed in it,
    or once a month -- the diff review only ever sees what moved."""
    dp = _module()
    today = date(2026, 9, 23)
    record = {"core": {"at": "2026-09-20", "commit": "abc"},
              "lab": {"at": "2026-08-20", "commit": "def"}}
    due = dp.rereads_due(record, {"core": dp.REREAD_COMMITS, "lab": 1,
                                  "outbound": 0}, today,
                         areas=("core", "lab", "outbound"))
    assert set(due) == {"core", "lab", "outbound"}, due
    assert "commits" in due["core"] and "days" in due["lab"]
    assert "never" in due["outbound"]
    quiet = dp.rereads_due(record, {"core": 2, "lab": 1}, date(2026, 9, 21),
                           areas=("core",))
    assert quiet == {}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_session_start_says_a_pass_died():
    """E5's other half: a pass that died is said at the next session start,
    not found by somebody reading the notebook."""
    hook = _module(REPO / ".claude" / "hooks" / "start" / "deep_pass_handover.py",
                   "handover_died")
    long_ago = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    said = hook.died({"run": "dp-9", "at": long_ago, "finished": False,
                      "gaps": [{"id": "T1", "verdict": "real", "fixed": False},
                               {"id": "T2", "verdict": "real", "fixed": True},
                               {"id": "T3", "verdict": "real", "fixed": False,
                                "deferred_to_operator": True},
                               {"id": "T4", "verdict": "minority", "fixed": False}]})
    assert said and "dp-9" in said[0] and "3 nález" in said[0], said
    assert "T3" in said[0] and "T4" in said[0], (
        "handed to them, or a minority, and never shown: named here")
    running = datetime.now(timezone.utc).isoformat()
    assert hook.died({"run": "dp-9", "at": running, "finished": False}) == []
    assert hook.died({"run": "dp-9", "at": long_ago, "finished": True}) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_dead_pass_does_not_push_its_report_out_of_the_one_slot(tmp_path,
                                                                   monkeypatch):
    """The session start gives the pass one line; the death line first and
    the report after it in a second line meant the report was cut unseen."""
    hook = _module(REPO / ".claude" / "hooks" / "start" / "deep_pass_handover.py",
                   "handover_slot")
    (tmp_path / "audits").mkdir()
    long_ago = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    (tmp_path / "audits" / "deep-pass-progress.json").write_text(
        '{"run": "dp-9", "at": "%s", "finished": false, "gaps": []}' % long_ago,
        encoding="utf-8")
    (tmp_path / "DEEP-PASS.md").write_text(
        "# Deep pass — x\n## Čeká na tebe\n- **ET-1 waits for you.**\n",
        encoding="utf-8")
    monkeypatch.setattr(hook, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("QA_DEEP_PASS", raising=False)
    said = hook.lines()
    assert len(said) == 1 and "dp-9" in said[0] and "ET-1" in said[0], said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_report_is_ten_lines_plus_what_waits_for_them():
    """Plan v2, V7. DEEP-PASS.md was 103 lines for a reader who does not
    read; the detail is in the notebook and the commits. What waits for the
    operator is never cut to fit (a 1c reader, 2026-09-23)."""
    text = (REPO / "DEEP-PASS.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    theirs, section = 0, ""
    for line in lines:
        if line.startswith("## "):
            section = line[3:].strip().lower()
        elif (section.startswith(("čeká na tebe", "změněná pravidla"))
              and line.startswith("- ")):
            # What they must see or can veto is never cut to fit.
            theirs += 1
    assert len(lines) - theirs <= 10, (len(lines), theirs)

    # And the 7:00 report still reads it: what was fixed and what was sent
    # (a 1c reader found the short form had dropped the first two headings
    # qa/morning.py reads, silently). What waits is no longer in the report:
    # the operator's feedback of 2026-09-26 (commit cfef7f3a) took "Čeká na
    # tebe" out of it; DEEP-PASS.md still carries the section for the pass.
    sys.path.insert(0, str(REPO))
    from qa import morning

    kinds = {line["kind"] for line in morning.deep_pass(text)["lines"]}
    assert kinds == {"fixed", "sent"}, kinds


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_tests_meta_is_counted_and_held_to_a_ceiling():
    """225 -> 786 tests in fifteen days, most of them guarding us. A new
    guard replaces or merges one; the ceiling is what says so."""
    procs = _module(REPO / "scripts" / "processes.py", "processes_meta")
    measured = procs.sizes()
    assert measured.get("meta_tests", 0) > 700, measured
    assert procs.CEILINGS["meta_tests"] >= measured["meta_tests"]
