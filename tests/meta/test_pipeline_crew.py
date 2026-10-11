"""The company's shell: the ticket bus, the supervisor and what a worker may do.

docs/crew-plan.md, C1. Departments run as their own `claude -p` processes and talk only
through tickets. What can go wrong in a shell like that is the same few things in every
multi-agent system, and each test below is one of them:

  * a ticket nobody owns, or one done twice -- a key makes a ticket once, a claim is taken
    under the lock, an end is final;
  * a worker that hangs, and takes its children with it into the next hour -- the run is
    killed at its timeout, tree and all;
  * a failure that is not the ticket's fault spending its attempts -- a CLI that is not
    logged in would fail every ticket on the bus in minutes;
  * a worker that pushes, tags or sweeps another department's half-done edit into its
    commit -- denied in the argv of every run;
  * the company working under a deep pass, which commits, reverts and pushes.

Every run here is the stand-in `tests/meta/fixtures/fake_claude.py`, started exactly as
the real executable would be. No model is called.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
FAKE = REPO / "tests" / "meta" / "fixtures" / "fake_claude.py"
NOW = datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc)


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"crew_test_{name}",
                                                  REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def company(tmp_path, monkeypatch):
    """An empty company in a temporary state directory, its workers the stand-in."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_CREW_CLAUDE", json.dumps([sys.executable, str(FAKE)]))
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(tmp_path / "fake.log"))
    monkeypatch.delenv("FAKE_CLAUDE_PLAN", raising=False)
    monkeypatch.delenv("QA_CREW_DEPT", raising=False)
    monkeypatch.delenv("QA_CREW_TICKET", raising=False)
    return tmp_path


def _fake_log(root: Path) -> list[dict]:
    path = root / "fake.log"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] \
        if path.exists() else []


# -- the bus ---------------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_ticket_has_one_owner_is_made_once_claimed_once_and_ends_once(company):
    first, made = crew.add_ticket("bugs", "bug", "a 500 on /movers", key="bug:movers-500",
                                  by="desk", now=NOW)
    again, made_again = crew.add_ticket("bugs", "bug", "the same bug, met again",
                                        key="bug:movers-500", by="outsider", now=NOW)
    assert made and not made_again and again["id"] == first["id"] == "T-0001"
    crew.close(first["id"], "done", by="bugs", note="filed #200", now=NOW)
    # Done, and still once: a key never makes a second ticket.
    later, made_later = crew.add_ticket("bugs", "bug", "x", key="bug:movers-500", now=NOW)
    assert not made_later and later["status"] == "done"

    with pytest.raises(ValueError):
        crew.add_ticket("nobody", "bug", "no owner")
    with pytest.raises(ValueError):
        crew.add_ticket("desk", "bug", "the desk files nothing: bugs are the Bugs department's")

    # Claimed once, most urgent first: a bug before a hunt, whatever came first.
    hunt, _ = crew.add_ticket("bugs", "hunt", "a hunt", now=NOW)
    crew.add_ticket("desk", "step", "a desk step", now=NOW)
    bug, _ = crew.add_ticket("bugs", "bug", "a bug", now=NOW)
    taken = crew.claim("bugs", now=NOW)
    assert taken["id"] == bug["id"], "a bug before a hunt, whatever came first"
    assert crew.claim("bugs", now=NOW)["id"] == hunt["id"]
    assert crew.claim("bugs", now=NOW) is None, "claimed tickets are not claimed twice"
    state = crew.tickets()
    assert state[bug["id"]]["status"] == "claimed" and state[bug["id"]]["lease_until"]

    # Ends once: three failed attempts are its end, and an end is final.
    ticket, _ = crew.add_ticket("lab", "lab", "answer NEX-0200", now=NOW)
    for attempt in range(1, crew.MAX_ATTEMPTS + 1):
        assert crew.claim("lab", now=NOW)["id"] == ticket["id"]
        after = crew.close(ticket["id"], "fail", by="lab", note=f"try {attempt}", now=NOW)
        assert after["attempts"] == attempt
    assert after["status"] == "failed"
    assert crew.claim("lab", now=NOW) is None
    # A late `done` from a run already given up on reopens nothing.
    assert crew.close(ticket["id"], "done", by="lab", now=NOW)["status"] == "failed"

    released, _ = crew.add_ticket("lab", "lab", "learn", now=NOW)
    crew.claim("lab", now=NOW)
    back = crew.close(released["id"], "release", by="lab", note="stopped", now=NOW)
    assert back["status"] == "open" and back["attempts"] == 0, "a release spends nothing"
    assert back["releases"] == 1

    # Ended only by its owner, the manager or the supervisor (review of C1, finding 3).
    theirs, _ = crew.add_ticket("bugs", "bug", "a real defect", now=NOW)
    with pytest.raises(PermissionError):
        crew.close(theirs["id"], "done", by="desk", note="not mine to end", now=NOW)
    assert crew.tickets()[theirs["id"]]["status"] == "open"
    assert crew.close(theirs["id"], "done", by="manager", now=NOW)["status"] == "done"


# -- a worker's run --------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_worker_is_denied_push_tag_and_raw_commits():
    for name, spec in crew.DEPARTMENTS.items():
        if spec.model is None:
            continue
        args = crew.argv(name, "the prompt", ["claude"])
        assert args[args.index("--model") + 1] == spec.model
        assert args[args.index("--effort") + 1] == spec.effort
        assert args[args.index("--permission-mode") + 1] == "acceptEdits", name
        assert "--bare" not in args, "hooks stay on: protect_state.py guards workers too"
        assert "--max-turns" in args and "--output-format" in args
        denied = args[args.index("--disallowedTools") + 1:]
        for rule in ("Bash(git push:*)", "Bash(git tag:*)", "Bash(git commit:*)",
                     "Bash(git add:*)", "Bash(python scripts/crew.py start:*)",
                     "PowerShell(git push:*)", "PowerShell(git tag:*)",
                     "PowerShell(git commit:*)", "CronCreate", "ScheduleWakeup"):
            assert rule in denied, (name, rule)
    assert crew.DEPARTMENTS["manager"].model == "opus"
    assert crew.DEPARTMENTS["desk"].model == "opus"
    assert crew.DEPARTMENTS["bugs"].model == "sonnet"
    # One executable for the workers and the outsider's stranger (finding 9).
    assert _script("outsider").claude_exe is crew.claude_exe

    # C2: the bug pipeline has one writer. Every other department hands a bug over as a
    # ticket; it cannot file, fold, render, withdraw, verify or preregister.
    pipeline = ("submit.py", "ledger.py", "render.py", "withdraw.py", "verify.py",
                "prereg.py")
    for name, spec in crew.DEPARTMENTS.items():
        if spec.model is None:
            continue
        denied = crew.denied(name)
        for script in pipeline:
            for shell in ("Bash", "PowerShell"):
                rule = f"{shell}(python scripts/{script}:*)"
                assert (rule in denied) == (name != "bugs"), (name, rule)
    told = crew.prompt("bugs", {"id": "T-0009", "kind": "sweep", "from": "clock",
                                "text": "hunt sweep", "payload": {"moved": ["#201 fixed"]}})
    assert "crew.py hold" in told and "submit.py" in told and "#201 fixed" in told
    assert "--to bugs" not in told, "Bugs is not told to hand a bug to itself"
    assert "--to bugs" in crew.prompt("desk", {"id": "T-1", "kind": "step", "text": "x"})


def _ends_are_read():
    ok = json.dumps({"is_error": False, "result": "done", "num_turns": 4,
                     "total_cost_usd": 0.2, "usage": {"input_tokens": 10, "output_tokens": 2}})
    assert crew.outcome(0, ok, False)["outcome"] == "ok"
    assert crew.outcome(0, ok, False)["tokens"] == {"input_tokens": 10, "output_tokens": 2}
    out = json.dumps({"is_error": True, "result": "Not logged in · Please run /login",
                      "terminal_reason": "api_error"})
    assert crew.outcome(1, out, False)["outcome"] == "infra"
    assert crew.outcome(1, json.dumps({"is_error": True, "result": "boom"}),
                        False)["outcome"] == "work"
    assert crew.outcome(None, "", True)["outcome"] == "work"
    turns = json.dumps({"is_error": True, "subtype": "error_max_turns", "result": ""})
    assert crew.outcome(1, turns, False)["why"] == "ran out of turns"
    # A run that succeeded is a success whatever its summary says: a hunt that filed a
    # defect on /login, or met their rate limit, did its work (review of C1, finding 1).
    said = json.dumps({"is_error": False, "result": "filed #201: /login answers 500 past "
                       "the rate limit"})
    assert crew.outcome(0, said, False)["outcome"] == "ok"
    # A CLI that never produced its result object did not run the work at all; why it
    # failed is on stderr (finding 4).
    lost = crew.outcome(1, "", False, stderr="error: unknown option '--effort'")
    assert lost["outcome"] == "infra" and "unknown option" in lost["why"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_settles_its_ticket_by_how_it_ended(company, monkeypatch):
    """Closed by the worker, or by the supervisor when it forgot; a failed run spends an
    attempt, a failure of the machinery spends none."""
    _ends_are_read()
    sup = _script("crew")
    mine, _ = crew.add_ticket("bugs", "bug", "closes itself", now=NOW)
    row = sup.work_once("bugs")
    assert row["ticket"] == mine["id"] and row["outcome"] == "ok"
    after = crew.tickets()[mine["id"]]
    assert after["status"] == "done" and after["note"] == "done by the fake"
    assert after["closed_by"] == "bugs"

    monkeypatch.setenv("FAKE_CLAUDE_MODE", "silent")
    forgot, _ = crew.add_ticket("bugs", "bug", "forgets", now=NOW)
    sup.work_once("bugs")
    after = crew.tickets()[forgot["id"]]
    assert after["status"] == "done" and after["closed_by"] == "supervisor"
    seen = _fake_log(company)
    assert [entry["ticket"] for entry in seen] == [mine["id"], forgot["id"]]
    assert all(entry["dept"] == "bugs" for entry in seen)
    runs = [r for r in crew.load(crew.runs_path()) if r.get("type") == "run"]
    assert len(runs) == 2 and runs[0]["tokens"]["output_tokens"] == 300

    ticket, _ = crew.add_ticket("bugs", "hunt", "a hunt", now=NOW)
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "notloggedin")
    assert sup.work_once("bugs")["outcome"] == "infra"
    after = crew.tickets()[ticket["id"]]
    assert after["status"] == "open" and after["attempts"] == 0

    monkeypatch.setenv("FAKE_CLAUDE_MODE", "fail")
    assert sup.work_once("bugs")["outcome"] == "work"
    after = crew.tickets()[ticket["id"]]
    assert after["status"] == "open" and after["attempts"] == 1

    monkeypatch.setenv("FAKE_CLAUDE_MODE", "fail-ticket")
    sup.work_once("bugs")
    assert crew.tickets()[ticket["id"]]["attempts"] == 2, "its own fail, counted once"

    # A worker that cannot even be started gives its ticket back instead of holding it
    # claimed until its lease runs out (finding 2) ...
    monkeypatch.setenv("QA_CREW_CLAUDE", json.dumps([str(company / "no-such-claude.exe")]))
    stuck, _ = crew.add_ticket("bugs", "bug", "the CLI is gone", now=NOW)
    assert sup.work_once("bugs")["outcome"] == "infra"
    assert crew.tickets()[stuck["id"]]["status"] == "open"
    # ... and machinery that keeps failing on one ticket spends its attempt in the end,
    # so an infrastructure failure cannot hold a ticket in a loop for ever.
    monkeypatch.setattr(crew, "MAX_RELEASES", 2)
    sup.work_once("bugs")
    after = crew.tickets()[stuck["id"]]
    assert after["attempts"] == 1 and "released 2 times" in after["why"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_past_its_timeout_is_killed_with_its_children(company, monkeypatch):
    sup = _script("crew")
    monkeypatch.setitem(crew.DEPARTMENTS, "bugs",
                        dataclasses.replace(crew.DEPARTMENTS["bugs"], timeout=4))
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "sleep")
    marker = company / "child.pid"
    monkeypatch.setenv("FAKE_CLAUDE_CHILD", str(marker))
    ticket, _ = crew.add_ticket("bugs", "bug", "hangs", now=NOW)
    started = time.monotonic()
    row = sup.work_once("bugs")
    assert time.monotonic() - started < 60
    assert row["outcome"] == "work" and row["timed_out"]
    assert not sup.pid_alive(row["pid"]), "the worker outlived its timeout"
    child = int(marker.read_text(encoding="utf-8"))
    for _ in range(50):
        if not sup.pid_alive(child):
            break
        time.sleep(0.1)
    assert not sup.pid_alive(child), "the worker's own child outlived the kill"
    assert crew.tickets()[ticket["id"]]["attempts"] == 1
    assert not crew.active(), "a finished run leaves no active marker"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_level_v_run_holds_the_tree_still_and_the_hold_cannot_freeze_the_company(
        company, monkeypatch):
    """C2. Verification needs a clean tree (CLAUDE.md, rule 6) while four other departments
    edit it. Bugs holds the tree: it waits until nobody else is mid-run, and nothing new
    starts until it lets go. A hold that is never let go expires, and one that cannot get
    quiet in time is given up rather than waited on for ever."""
    sup = _script("crew")
    monkeypatch.setenv("QA_CREW_DEPT", "bugs")
    assert sup.main(["hold", "--why", "level-V run of PRE-0300"]) == 0
    held = crew.holder()
    assert held["by"] == "bugs" and "PRE-0300" in held["why"]

    step, _ = crew.add_ticket("desk", "step", "a desk step", now=NOW)
    assert sup.look("desk", paused=lambda: False)[0] == "held"
    assert crew.tickets()[step["id"]]["status"] == "open"
    assert crew.beats()["desk"]["state"] == "held"

    # The race between the two: a loop that read "nobody holds it" a moment before the
    # hold was set still finds it before it claims -- its marker goes up first, then it
    # looks, so either the hold sees the marker or the loop sees the hold.
    assert sup.work_once("desk") is None
    after = crew.tickets()[step["id"]]
    assert after["status"] == "open" and after["releases"] == 0
    assert not crew.active()

    assert sup.main(["unhold"]) == 0 and crew.holder() is None
    assert sup.look("desk", paused=lambda: False)[0] == "worked"

    # Somebody is mid-run: the hold waits for them, and gives up if they do not finish.
    crew.set_active("lab", {"id": "T-0400", "kind": "lab"})
    monkeypatch.setattr(sup, "HOLD_WAIT_SECONDS", 1.5)
    monkeypatch.setattr(sup, "HOLD_POLL_SECONDS", 0.2)
    assert sup.main(["hold", "--why", "another run"]) == 1
    assert crew.holder() is None, "a hold that could not get quiet is not left behind"
    crew.set_active("lab", None)

    # The hour starts when the tree is still, not when the wait began: a wait of fifty
    # minutes must not leave ten for the run.
    crew.set_hold("bugs", "waited long", now=datetime.now(timezone.utc) - timedelta(minutes=50))
    assert sup.main(["hold", "--why", "waited long"]) == 0
    left = crew.moment(crew.holder()["until"]) - datetime.now(timezone.utc)
    assert left > timedelta(minutes=55)
    sup.main(["unhold"])

    # A hold nobody let go expires by itself.
    crew.set_hold("bugs", "forgotten", now=NOW - timedelta(hours=3))
    assert crew.holder() is None

    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    crew.set_hold("bugs", "mine", now=datetime.now(timezone.utc))
    assert sup.main(["unhold"]) == 2, "only its holder lets go of a hold"
    assert crew.holder()["by"] == "bugs"


# -- the loops ------------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_loop_runs_once_per_name_waits_out_a_deep_pass_and_ends_on_stop(company):
    sup = _script("crew")
    ticket, _ = crew.add_ticket("bugs", "bug", "waits", now=NOW)
    said = sup.look("bugs", paused=lambda: True)
    assert said == ("paused", "a deep pass is running")
    assert crew.tickets()[ticket["id"]]["status"] == "open"
    assert crew.beats()["bugs"]["state"] == "paused"
    assert sup.look("bugs", paused=lambda: False)[0] == "worked"

    with sup.loop_lock("bugs") as held:
        assert held
        assert sup.loop_alive("bugs")
        with sup.loop_lock("bugs") as second:
            assert not second, "two loops of one department would claim side by side"
    assert not sup.loop_alive("bugs")

    crew.set_stop(True)
    started = time.monotonic()
    assert sup.loop("bugs", poll=0.05, paused=lambda: False) == 0
    assert time.monotonic() - started < 10
    # What `stop` kills is the pid the loop itself wrote, never a heartbeat's, which any
    # process calling `crew.py once` overwrites (finding 5).
    crew.beat("bugs", "idle", "written by somebody else")
    assert sup.loop_pid("bugs") == os.getpid()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_detached_loop_outlives_its_parent_and_stop_kills_its_tree(company):
    """The operator closes the window and the company goes on; `vypni laborku` ends it."""
    sup = _script("crew")
    parent = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util, sys; "
         f"spec = importlib.util.spec_from_file_location('c', r'{REPO / 'scripts' / 'crew.py'}'); "
         "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
         "print(m.spawn([sys.executable, '-c', 'import time; time.sleep(120)'], "
         f"r'{company / 'child.log'}'))"],
        capture_output=True, text=True, timeout=60)
    pid = int(parent.stdout.strip().splitlines()[-1])
    try:
        time.sleep(1.0)
        assert sup.pid_alive(pid), "the child died with its parent"
    finally:
        sup.kill_tree(pid)
    for _ in range(50):
        if not sup.pid_alive(pid):
            break
        time.sleep(0.1)
    assert not sup.pid_alive(pid)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_status_names_every_loop_and_what_each_waits_on(company):
    sup = _script("crew")
    crew.add_ticket("bugs", "bug", "open one", now=NOW)
    crew.beat("bugs", "idle", "no tickets")
    lines = sup.status_lines()
    text = "\n".join(lines)
    assert lines[0].startswith("company: stopped"), lines[0]
    for name in sup.LOOPS:
        assert any(line.split()[0] == name for line in lines[1:]), (name, text)
    bugs = next(line for line in lines if line.startswith("bugs"))
    assert "open 1" in bugs and "not running" in bugs

    # The department shape: the report is what /lab lists, with nobody wiring it in.
    from qa import departments

    sup.write_report()
    listed = {d["id"]: d for d in departments.departments()}
    assert listed["crew"]["title"] == "Company" and listed["crew"]["lines"][0] == lines[0]


# -- commits ---------------------------------------------------------------------------------

def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_commit_takes_the_lock_and_only_the_paths_it_names(company, monkeypatch):
    """Two departments edit side by side; one commits. Only its own file goes in."""
    root = company / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "desk.md").write_text("one\n", encoding="utf-8")
    (root / "other.md").write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "start")
    (root / "desk.md").write_text("two\n", encoding="utf-8")
    (root / "other.md").write_text("half-done by another department\n", encoding="utf-8")
    (root / "new.md").write_text("new\n", encoding="utf-8")
    monkeypatch.setenv("QA_REPO_ROOT", str(root))
    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    monkeypatch.setenv("QA_CREW_TICKET", "T-0007")

    commit = _script("commit")
    assert commit.main(["-m", "Desk: H3 moved", "--", "desk.md", "new.md"]) == 0
    shown = _git(root, "show", "--stat", "--format=%B", "HEAD")
    assert "desk.md" in shown and "new.md" in shown and "other.md" not in shown
    assert "Crew: desk T-0007" in shown
    assert "other.md" in _git(root, "status", "--porcelain")

    assert commit.main(["-m", "everything"]) == 2, "no paths: nothing is committed"
    assert commit.main(["-m", "everything", "--", "."]) == 2, "the whole tree is not a path"
    assert commit.main(["-m", "x", "--", "../outside.md"]) == 2
    # A pattern or a directory takes in every department's edits under it (finding 8).
    (root / "docs").mkdir()
    for wide in ("docs/*", "*.md", ":(glob)**", "docs", "d?sk.md"):
        assert commit.main(["-m", "x", "--", wide]) == 2, wide

    # A git that cannot be started is said as such at once, not waited on as if the
    # lock were held (finding 7).
    def broken(*args):
        raise FileNotFoundError("git")

    monkeypatch.setattr(commit, "_git", broken)
    started = time.monotonic()
    assert commit.main(["-m", "x", "--", "desk.md"]) == 1
    assert time.monotonic() - started < 30
