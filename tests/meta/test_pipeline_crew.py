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
import shutil
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
    # The watchdog reads the working tree's git status; here that is no repository at all, so
    # no test reads the real tree's edits (a test that does makes its own, below).
    monkeypatch.setenv("QA_REPO_ROOT", str(tmp_path / "no-repo"))
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
                     # an edit a worker did not make is not its to undo (crew-before-c9, 1)
                     "Bash(git checkout:*)", "Bash(git restore:*)", "Bash(git reset:*)",
                     "Bash(git stash:*)", "Bash(git clean:*)", "PowerShell(git checkout:*)",
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
    # bounty.py appends their side to the journal, so it is the pipeline's too (crew-before-c9,
    # item 2).
    pipeline = ("submit.py", "ledger.py", "render.py", "withdraw.py", "verify.py",
                "prereg.py", "bounty.py")
    for name, spec in crew.DEPARTMENTS.items():
        if spec.model is None:
            continue
        denied = crew.denied(name)
        for script in pipeline:
            for shell in ("Bash", "PowerShell"):
                rule = f"{shell}(python scripts/{script}:*)"
                assert (rule in denied) == (name != "bugs"), (name, rule)
            # A worker never records a send the operator did not make: MSG-0115 was written
            # that way, and the memory index loaded into every run says a written block is
            # recorded as sent. correspond.py is closed to every worker, Bugs included.
            assert f"{shell}(python scripts/correspond.py:*)" in denied, (name, shell)
    told = crew.prompt("bugs", {"id": "T-0009", "kind": "sweep", "from": "clock",
                                "text": "hunt sweep", "payload": {"moved": ["#201 fixed"]}})
    assert "crew.py hold" in told and "submit.py" in told and "#201 fixed" in told
    # The hold returns at once and is asked again (item 4); the tree is tidied by code before
    # a preregistration (item 1).
    assert "crew.py held" in told and "crew.py tidy" in told

    # crew-before-c9, item 6: Bugs keeps pytest, and a test file it writes runs anything, a
    # push included. git's own pre-push hook refuses every push made from a worker's run.
    hook = REPO / ".githooks" / "pre-push"
    assert "QA_CREW_DEPT" in hook.read_text(encoding="utf-8")
    staged = subprocess.run(["git", "-C", str(REPO), "ls-files", "-s", ".githooks/pre-push"],
                            capture_output=True, text=True).stdout
    assert staged.startswith("100755"), "git runs a hook only when it is executable"
    sh = shutil.which("sh") or next((str(p) for p in (
        Path(os.environ.get("ProgramFiles") or "C:/Program Files") / "Git" / "bin" / "sh.exe",)
        if p.exists()), None)
    if sh:
        env = {k: v for k, v in os.environ.items() if k != "QA_CREW_DEPT"}
        assert subprocess.run([sh, str(hook)], env=env, capture_output=True).returncode == 0
        refused = subprocess.run([sh, str(hook)], env={**env, "QA_CREW_DEPT": "bugs"},
                                 capture_output=True, text=True)
        assert refused.returncode != 0 and "bugs" in refused.stderr
    assert "--to bugs" not in told, "Bugs is not told to hand a bug to itself"
    assert "--to bugs" in crew.prompt("desk", {"id": "T-1", "kind": "step", "text": "x"})

    # C8 review: a second worker beside a department's loop (`once`), an allowlisted
    # interpreter running a file the worker just wrote (pytest), and the files that speak
    # to the operator or rule the repository -- closed to every worker; pytest stays Bugs'.
    for name, spec in crew.DEPARTMENTS.items():
        if spec.model is None:
            continue
        denied = crew.denied(name)
        assert "Bash(python scripts/crew.py once:*)" in denied, name
        assert ("Bash(python -m pytest:*)" in denied) == (name != "bugs"), name
        for path in ("CLAUDE.md", "NEXT.md", "DEEP-PASS.md", ".claude/**",
                     # the company's own code, git's hooks and the declared writes: edited,
                     # a worker could push from a hook, lift a brake or drop its own name
                     # (second read, finding 1)
                     "scripts/**", "qa/**", ".githooks/**", "components.yaml",
                     "tests/meta/**", "tests/conftest.py"):
            assert f"Edit({path})" in denied and f"Write({path})" in denied, (name, path)
        # Checks are Bugs' to write; no other department edits a test.
        assert ("Edit(tests/**)" in denied) == (name != "bugs"), name

    # Who may open which ticket: the operator's words come only from a session, the
    # manager's day and the watchdog's alarms only from the code that makes them.
    assert not crew.may_open("lab", "manager", "operator")
    assert crew.may_open("session", "manager", "operator")
    assert not crew.may_open("desk", "manager", "help")
    assert crew.may_open("desk", "bugs", "bug") and crew.may_open("desk", "manager", "decision")
    assert crew.may_open("manager", "bugs", "sweep") and not crew.may_open("lab", "bugs", "sweep")


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
    # C8 review: a refused call to the company's own commands is named, never read as
    # everyone's failure (with the allowlist preflight, only the run itself can cause it --
    # a pipe, a `cd &&`, PowerShell); a run that succeeded stays a success, and work_once
    # decides from whether the ticket was closed (second read, finding 2).
    refused = json.dumps({"is_error": False, "result": "handed the bug to Bugs",
                          "permission_denials": [{"tool_name": "Bash", "tool_input": {
                              "command": "python scripts/crew.py ticket --to bugs ..."}}]})
    said = crew.outcome(0, refused, False)
    assert said["outcome"] == "ok" and not said["widespread"]
    assert "crew.py ticket" in said["company_refused"]
    pushed = json.dumps({"is_error": False, "result": "done", "permission_denials": [
        {"tool_name": "Bash", "tool_input": {"command": "git push"}}]})
    assert crew.outcome(0, pushed, False)["outcome"] == "ok", "a refused push is the floor"
    assert crew.outcome(0, pushed, False)["denials"] == 1
    assert crew.outcome(0, pushed, False)["company_refused"] is None
    assert crew.outcome(1, out, False)["widespread"], "logged out is everyone's"
    # Everyone's is read only off the CLI's own signals, never off the work's words: a run
    # that ran out of turns after a refused /auth/login, or a result about their 429, is
    # the work's failure, counted and bounded (second read, finding 3).
    worked = json.dumps({"is_error": True, "subtype": "error_max_turns", "num_turns": 150,
                         "result": "", "permission_denials": [{"tool_input": {
                             "command": "curl https://cymetica.com/api/v1/auth/login"}}]})
    assert not crew.outcome(1, worked, False)["widespread"]
    their_429 = json.dumps({"is_error": True, "num_turns": 40,
                            "result": "stopped: their rate limit answered 429 three times"})
    assert crew.outcome(1, their_429, False)["outcome"] == "work"
    limit = json.dumps({"is_error": True, "num_turns": 1,
                        "result": "Claude AI usage limit reached|1760241600"})
    assert crew.outcome(1, limit, False)["widespread"], "the CLI's own refusal is everyone's"


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
    # ... and machinery that keeps failing on one ticket spends its attempt in the end, so
    # an unexplained failure cannot hold a ticket in a loop for ever: exactly MAX_RELEASES
    # releases, then an attempt (C8 review, finding 5: it was one fewer than it said).
    monkeypatch.setattr(crew, "MAX_RELEASES", 2)
    sup.work_once("bugs")
    assert crew.tickets()[stuck["id"]]["releases"] == 2
    sup.work_once("bugs")
    after = crew.tickets()[stuck["id"]]
    assert after["attempts"] == 1 and "released 2 times" in after["why"]
    # A failure that is everyone's -- logged out, a usage limit, a deep pass starting --
    # never counts against a ticket: an hour's outage must not fail the front of the queue.
    monkeypatch.setenv("QA_CREW_CLAUDE", json.dumps([sys.executable, str(FAKE)]))
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "notloggedin")
    patient, _ = crew.add_ticket("bugs", "bug", "waits out an outage", now=NOW)
    for _ in range(crew.MAX_RELEASES + 3):
        assert sup.work_once("bugs")["outcome"] == "infra"
    after = crew.tickets()[patient["id"]]
    assert after["status"] == "open" and after["attempts"] == 0 and after["releases"] == 0

    # A run that ended well but whose own close or hand-over was refused did not do what
    # it says: its ticket spends an attempt (and so ends in three, with the manager), it is
    # never quietly closed "done" nor released for ever (second read, finding 2).
    for tid, waiting in crew.tickets().items():  # the queue cleared before the next case
        if waiting["status"] == "open":
            crew.close(tid, "done", by="bugs", note="cleared", now=NOW)
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "refused")
    lost_close, _ = crew.add_ticket("bugs", "bug", "its close is refused", now=NOW)
    row = sup.work_once("bugs")
    assert row["ticket"] == lost_close["id"]
    after = crew.tickets()[lost_close["id"]]
    assert after["status"] == "open" and after["attempts"] == 1
    assert "refused" in after["why"] and row["outcome"] == "work"

    # ... and one that closed its own ticket while its hand-over was refused: the ticket is
    # done, so no attempt can be spent, but the lost hand-over reaches the manager by name
    # (C02, deep pass 2026-10-15) instead of vanishing.
    crew.close(lost_close["id"], "done", by="bugs", note="cleared", now=NOW)
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "handover-refused")
    handed, _ = crew.add_ticket("lab", "lab", "a bug met in the lab", now=NOW)
    sup.work_once("lab")
    assert crew.tickets()[handed["id"]]["status"] == "done"
    told = [t for t in crew.tickets().values()
            if t.get("to") == "manager" and handed["id"] in str(t.get("text"))]
    assert told and "crew.py ticket" in told[0]["text"], told


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

    # Somebody is mid-run (crew-before-c9, item 4): the hold is set at once -- nothing new
    # starts -- and the call returns without waiting, so no single call outlives the Bash
    # tool's two minutes and the caller always learns where it stands. `held` asks again.
    crew.set_active("lab", {"id": "T-0400", "kind": "lab"})
    monkeypatch.setattr(sup, "HOLD_POLL_SECONDS", 0.2)
    started = time.monotonic()
    assert sup.main(["hold", "--why", "another run"]) == 3
    assert time.monotonic() - started < 5, "the hold waited inside the call"
    assert crew.holder()["by"] == "bugs" and crew.holder()["still"] is False
    assert sup.look("desk", paused=lambda: False)[0] == "held", "a waiting hold still holds"
    assert sup.main(["held"]) == 3
    started = time.monotonic()
    assert sup.main(["held", "--wait", "1"]) == 3
    assert time.monotonic() - started < 10, "--wait is bounded"
    assert sup.main(["held", "--wait", "900"]) == 2, "no wait longer than one Bash call"
    # Quiet: the hour starts now, not when the wait began -- a wait of fifty minutes must
    # not leave ten for the run.
    crew.set_active("lab", None)
    assert sup.main(["held"]) == 0
    left = crew.moment(crew.holder()["until"]) - datetime.now(timezone.utc)
    assert crew.holder()["still"] is True and left > timedelta(minutes=55)
    sup.main(["unhold"])

    # Never quiet in time: let go, and the caller hears it.
    crew.set_active("lab", {"id": "T-0401", "kind": "lab"})
    # (Two seconds, not less: a hold's `since` is stamped to the second.)
    monkeypatch.setattr(sup, "HOLD_WAIT_SECONDS", 2.0)
    assert sup.main(["hold", "--why", "never quiet"]) == 3
    time.sleep(3.2)
    assert sup.main(["held"]) == 1
    assert crew.holder() is None, "a hold that could not get quiet is not left behind"
    crew.set_active("lab", None)
    # A waiting hold nobody asks about again expires inside the wait, not after an hour.
    crew.set_hold("bugs", "asked once", now=datetime.now(timezone.utc) - crew.HOLD_WAIT,
                  still=False)
    assert crew.holder() is None

    # And a hold never outlives the run that set it: a worker killed in its wait, or one
    # that forgot `unhold`, leaves the company free when its run ends.
    crew.set_hold("bugs", "set inside the run", now=datetime.now(timezone.utc))
    crew.add_ticket("bugs", "sweep", "a narrow sweep", now=NOW)
    assert sup.work_once("bugs") is not None
    assert crew.holder() is None, "the run ended and its hold stayed"
    assert any(r.get("type") == "hold_released" for r in crew.load(crew.runs_path()))

    # A hold nobody let go expires by itself.
    crew.set_hold("bugs", "forgotten", now=NOW - timedelta(hours=3))
    assert crew.holder() is None

    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    crew.set_hold("bugs", "mine", now=datetime.now(timezone.utc))
    assert sup.main(["unhold"]) == 2, "only its holder lets go of a hold"
    assert crew.holder()["by"] == "bugs"


# -- the clock -------------------------------------------------------------------------------

TICK_OUTPUT = """\
[lab] tick 2026-10-11 18:00
  answered: NEX-0201 opened STR-0130
  failed: /api/v1/movers answered 500 twice
  their side moved: #201 status FIXED, A2A-0090 answered
decide: answer NEX-0201 + gap + hunt sweep + outsider + desk
"""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_clock_runs_the_laboratorys_tick_and_routes_what_it_decided(company,
                                                                       monkeypatch):
    """C3. The laboratory's tick stays the company's one clock for vendor news and hunts;
    what it decides becomes tickets for the department whose work it is. The desk keeps
    its own pace, so the tick's `desk` is dropped; a chat /loop does not tick beside it."""
    assert crew.decide_items(TICK_OUTPUT) == ["answer NEX-0201", "gap", "hunt sweep",
                                              "outsider", "desk"]
    assert crew.decide_items("decide: none\n") == []
    assert crew.moved_lines(TICK_OUTPUT) == ["#201 status FIXED, A2A-0090 answered"]
    at = "2026-10-11T18:00:00+00:00"
    routed = crew.route(crew.decide_items(TICK_OUTPUT), TICK_OUTPUT, at, {})
    by_to = {t["to"]: t for t in routed}
    assert set(by_to) == {"lab", "bugs", "outsider"}, "the desk keeps its own pace"
    assert by_to["lab"]["payload"]["items"] == ["answer NEX-0201", "gap"]
    assert "answered 500 twice" in by_to["lab"]["payload"]["tick"]
    assert by_to["bugs"]["kind"] == "sweep"
    assert by_to["bugs"]["payload"]["moved"] == ["#201 status FIXED, A2A-0090 answered"]
    assert by_to["outsider"]["key"] == "outsider:2026-10-11"
    # A hunt waits behind an open sweep or hunt; a sweep does not wait behind a hunt.
    open_hunt = {"T-0001": {"to": "bugs", "kind": "hunt", "status": "open"}}
    assert not crew.route(["hunt bugs"], "", at, open_hunt)
    assert crew.route(["hunt sweep"], "", at, open_hunt)[0]["kind"] == "sweep"
    # The laboratory still working on a question when the next tick decides it again: the
    # item is not handed over twice (a /loop never overlapped itself; the company does).
    busy = {"T-0002": {"to": "lab", "kind": "lab", "status": "claimed",
                       "payload": {"items": ["question"]}}}
    again = crew.route(["question", "learn"], "", at, busy)
    assert [t["payload"]["items"] for t in again] == [["learn"]]
    assert not crew.route(["question"], "", at, busy)

    # The clock itself: due every twenty minutes, the tick a process of its own, run with
    # QA_CREW_DEPT=clock and marked active so a hold waits for it.
    sup = _script("crew")
    fake_tick = company / "fake_tick.py"
    fake_tick.write_text(
        "import os, sys\n"
        f"open(r'{company / 'tick.env'}', 'w').write(os.environ.get('QA_CREW_DEPT', ''))\n"
        f"sys.stdout.write({TICK_OUTPUT!r})\n", encoding="utf-8")
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, str(fake_tick)]))
    first = datetime.now(timezone.utc)
    sup.clock_look(now=first)
    assert (company / "tick.env").read_text(encoding="utf-8") == "clock"
    state = crew.tickets()
    ticks = [r for r in crew.load(crew.runs_path()) if r.get("type") == "tick"]
    assert len(ticks) == 1 and ticks[0]["decide"][0] == "answer NEX-0201"
    # What the tick made; the desk's step and the manager's day come from the clock's own
    # pace (C4, C5), never from the tick's `desk`.
    routed = [state[tid] for tid in ticks[0]["made"]]
    assert sorted((t["to"], t["kind"]) for t in routed) == [
        ("bugs", "sweep"), ("lab", "lab"), ("outsider", "outsider")]
    assert all(t["from"] == "clock" for t in state.values())
    sup.clock_look(now=first + timedelta(minutes=5))
    assert len([r for r in crew.load(crew.runs_path()) if r.get("type") == "tick"]) == 1
    # Held still for a level-V run, the tick waits: it can append to the journal.
    crew.set_hold("bugs", "level V")
    sup.clock_look(now=first + timedelta(minutes=25))
    assert len([r for r in crew.load(crew.runs_path()) if r.get("type") == "tick"]) == 1
    crew.clear_hold()
    assert "clock" not in crew.active(), "a tick that waited leaves no marker behind"
    # And the clock follows the protocol work_once does: its marker goes up before it
    # looks at the hold, so a hold set in between still sees the tick coming (C8 review,
    # finding 9).
    seen: list[bool] = []
    real_holder = crew.holder

    def holder_watching(now=None):
        seen.append("clock" in crew.active())
        return real_holder(now)

    monkeypatch.setattr(crew, "holder", holder_watching)
    sup.clock_look(now=first + timedelta(minutes=50))
    assert seen and seen[0], "the clock read the hold before its marker was up"
    monkeypatch.setattr(crew, "holder", real_holder)

    # The lab worker is told the laboratory's step, without the parts that are not its own.
    told = crew.prompt("lab", state[next(t for t in state if state[t]["to"] == "lab")])
    assert "laborator" in told and "answer NEX-0201" in told and "--to bugs" in told
    for name in crew.DEPARTMENTS:
        if crew.DEPARTMENTS[name].model and name != "lab":
            assert "Artifact" in crew.denied(name), name
            assert "Bash(python scripts/lab.py ask:*)" in crew.denied(name), name
    assert "Artifact" not in crew.denied("lab"), "the morning report is the lab's"

    # A chat /loop does not tick beside the company's clock.
    lab_script = _script("lab")
    said: list[str] = []
    with sup.loop_lock("clock"):
        result = lab_script.tick_exclusive(out=said.append)
    assert result.get("company") and said[-1] == "decide: none"

    # crew-before-c9, item 5: a tick the clock killed at its timeout never removed its marker
    # (taskkill /F skips the `finally`), so the next tick printed "tick skipped" with
    # `decide: none` and was recorded ok -- failed, ok, failed, ok, and the watchdog's three
    # in a row never tripped. A skipped tick is not ok; a killed tick's marker goes with it;
    # and a marker whose process is gone holds nothing off.
    skipped = company / "skipped_tick.py"
    skipped.write_text("print('tick skipped -- another tick is running since 18:00 (pid 1); "
                       "it will finish the work')\nprint('decide: none')\n", encoding="utf-8")
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, str(skipped)]))
    row = sup.run_tick(datetime.now(timezone.utc))
    assert row["ok"] is False and "skipped" in row["tail"], row
    for _ in range(2):
        sup.run_tick(datetime.now(timezone.utc))
    assert crew.tick_failing(crew.load(crew.runs_path())), "three skipped ticks went unseen"

    from qa.state import state_dir
    marker = state_dir() / "lab_tick.running"
    hung = company / "hung_tick.py"
    hung.write_text("import json, os, sys, time\n"
                    f"open(r'{marker}', 'w').write(json.dumps({{'pid': os.getpid(), "
                    "'at': '2026-10-12T00:00:00+00:00'}))\n"
                    "sys.stdout.flush()\ntime.sleep(60)\n", encoding="utf-8")
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, str(hung)]))
    monkeypatch.setattr(crew, "TICK_TIMEOUT", 3)
    row = sup.run_tick(datetime.now(timezone.utc))
    assert row["timed_out"] and not marker.exists(), "the killed tick's marker stayed"

    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    marker.write_text(json.dumps({"pid": gone.pid, "at": datetime.now(timezone.utc).isoformat()}),
                      encoding="utf-8")
    monkeypatch.setattr(lab_script, "tick", lambda **kwargs: {"ran": True})
    assert lab_script.tick_exclusive(out=said.append).get("ran"), (
        "a dead tick's marker held the next one off")
    marker.write_text(json.dumps({"pid": os.getpid(),
                                  "at": datetime.now(timezone.utc).isoformat()}),
                      encoding="utf-8")
    assert lab_script.tick_exclusive(out=said.append).get("busy"), "a live tick was run over"
    marker.unlink()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_outsiders_look_is_code_and_its_stumbles_become_tickets(company, monkeypatch):
    """C3. The outsider department starts no model of ours: the stranger is its own
    `claude -p` outside the repository. What it stumbled on goes to Bugs, one ticket a
    stumble; the surfaces it would not put money into go to the desk as input."""
    run_row = {"type": "run", "id": "OUT-0004", "at": "2026-10-11T18:00:00+00:00",
               "stumbles": [{"where": "/agent-league", "what": "the join button 404s"},
                            {"where": "llms.txt", "what": "no word on paper mode"}],
               "surfaces": [{"name": "Bots", "score": 3, "why": "no track record shown"},
                            {"name": "Gem Screener", "score": 8, "why": "clear"},
                            {"name": "Event cards", "score": None, "why": ""}]}
    made = crew.outsider_tickets(run_row)
    bugs = [t for t in made if t["to"] == "bugs"]
    assert [t["key"] for t in bugs] == ["OUT-0004-S1", "OUT-0004-S2"]
    assert "join button 404s" in bugs[0]["text"]
    desk = [t for t in made if t["to"] == "desk"]
    assert len(desk) == 1 and desk[0]["kind"] == "input" and "Bots 3/10" in desk[0]["text"]
    assert "Gem Screener" not in desk[0]["text"]

    sup = _script("crew")
    calls: list[list[str]] = []

    def fake_process(args, env, timeout):
        calls.append(args[1:])
        out = ""
        if args[-1] == "run":
            out = "OUT-0004: would deposit False, 2 pick(s) -- next: ..."
            path = Path(os.environ["QA_STATE_DIR"]) / "outsider.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(run_row) + "\n", encoding="utf-8")
        return {"pid": 1, "code": 0, "stdout": out, "stderr": "", "timed_out": False,
                "seconds": 0.1}

    monkeypatch.setattr(sup, "run_process", fake_process)
    monkeypatch.setattr(sup, "outsider_proven", lambda: True)
    ticket, _ = crew.add_ticket("outsider", "outsider", "the daily look", now=NOW)
    row = sup.work_once("outsider")
    assert row["outcome"] == "ok"
    steps = [" ".join(Path(a).name if i == 0 else a for i, a in enumerate(c)) for c in calls]
    assert steps == ["outsider.py run", "lab.py outsider-act OUT-0004", "outsider.py track"]
    assert not _fake_log(company), "no model of ours was started"
    state = crew.tickets()
    assert state[ticket["id"]]["status"] == "done"
    assert sorted(t["key"] for t in state.values() if t["from"] == "outsider") == [
        "OUT-0004-S1", "OUT-0004-S2", "OUT-0004-input"]

    # Without a stranger proven independent, the look is the probe first; a probe that
    # cannot run (logged out) gives the ticket back.
    calls.clear()
    monkeypatch.setattr(sup, "outsider_proven", lambda: False)

    def logged_out(args, env, timeout):
        calls.append(args[1:])
        return {"pid": 1, "code": 1, "stdout": "probe: NOT a stranger -- the probe did not "
                "run (exit 1): Not logged in", "stderr": "", "timed_out": False,
                "seconds": 0.1}

    monkeypatch.setattr(sup, "run_process", logged_out)
    again, _ = crew.add_ticket("outsider", "outsider", "tomorrow's look", now=NOW)
    assert sup.work_once("outsider")["outcome"] == "infra"
    assert [Path(c[0]).name + " " + c[1] for c in calls] == ["outsider.py probe"]
    assert crew.tickets()[again["id"]]["status"] == "open"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_desk_keeps_its_own_pace_sleeps_on_purpose_and_its_brakes_are_code(
        company, monkeypatch):
    """C4. The desk works one step after another with a pause, sleeps when it says nothing
    can move until a date, and cannot file past two Build it Better requests a day or send
    past three a2a messages an hour while it works for the company -- a refusal before any
    body exists. Every send here has a second barrier: the client raises if reached."""
    now = datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc)
    assert crew.desk_due({}, None, None, now)
    step = {"T-0001": {"to": "desk", "kind": "step", "status": "claimed"}}
    assert not crew.desk_due(step, None, None, now), "one step at a time"
    assert not crew.desk_due({}, now - timedelta(minutes=10), None, now), "the pause"
    assert crew.desk_due({}, now - crew.DESK_PAUSE, None, now)
    asleep = {"until": crew.stamp(now + timedelta(hours=5)), "why": "STR-0130 closes at 23:00"}
    assert not crew.desk_due({}, None, asleep, now)

    sup = _script("crew")
    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    assert sup.main(["snooze", "--hours", "5", "--why", "STR-0130 closes at 23:00"]) == 0
    assert "STR-0130" in crew.snoozed("desk")["why"]
    assert sup.main(["snooze", "--hours", "30", "--why", "a long sleep"]) == 2, "a day at most"
    crew.set_snooze("desk", None)

    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, "-c",
                                                   "print('decide: none')"]))
    sup.clock_look(now=datetime.now(timezone.utc))
    made = [t for t in crew.tickets().values() if t["to"] == "desk"]
    assert [t["kind"] for t in made] == ["step"]

    told = crew.prompt("desk", made[0])
    assert ".claude/agents/desk.md" in told and "crew.py snooze" in told
    for name, spec in crew.DEPARTMENTS.items():
        if spec.model:
            assert ("Bash(python scripts/bb.py:*)" in crew.denied(name)) == (name != "desk")
    # Deep pass 2026-10-11, R04 (3/3): a message to Cymetica is a draft the operator sends
    # (CLAUDE.md, "Nové oddělení"; the laborator skill), so no worker sends a2a -- the desk's
    # question goes to the manager as a decision carrying the draft.
    for name, spec in crew.DEPARTMENTS.items():
        if spec.model:
            assert "Bash(python scripts/a2a.py:*)" in crew.denied(name), name
    assert "draft" in told and "a2a.py send" not in told

    # The brakes, pure ...
    filed = [{"type": "intent", "kind": "file", "at": crew.stamp(now - timedelta(hours=h))}
             for h in (2, 20)]
    assert "2 Build it Better" in crew.bb_brake(filed, now)
    assert crew.bb_brake(filed[:1], now) is None
    assert crew.bb_brake([{**filed[0], "kind": "verdict"}] * 5, now) is None
    sent = [{"type": "a2a_intent", "at": crew.stamp(now - timedelta(minutes=m))}
            for m in (5, 20, 50)]
    assert "3 a2a" in crew.a2a_brake(sent, now)
    older = {"type": "a2a_intent", "at": crew.stamp(now - timedelta(minutes=70))}
    assert crew.a2a_brake(sent[:2] + [older], now) is None, "an hour is an hour"

    # ... and where the sends are: refused before an intent or a client exists.
    a2a = _script("a2a")
    bb = _script("bb")

    def no_network(*args, **kwargs):
        raise AssertionError("the brake let a send through")

    monkeypatch.setattr(a2a, "_client_for", no_network)
    monkeypatch.setattr(a2a, "append_event", no_network)
    monkeypatch.setattr(a2a, "read_events", lambda: [
        {"type": "a2a_intent", "at": crew.stamp(datetime.now(timezone.utc)
                                                - timedelta(minutes=m))} for m in (1, 2, 3)])
    message = company / "q.md"
    message.write_text("a question", encoding="utf-8")
    assert a2a.main(["send", "--text-file", str(message), "--confirm"]) == 2
    monkeypatch.setattr(bb, "_client", no_network)
    monkeypatch.setattr(bb, "load", lambda: [
        {"type": "intent", "kind": "file", "at": crew.stamp(datetime.now(timezone.utc)
                                                            - timedelta(hours=h))}
        for h in (1, 3)])
    improvements = company / "improvements.txt"
    improvements.write_text("1. Show the bot's record.", encoding="utf-8")
    assert bb.main(["file", "--app-name", "Bots", "--improvements-file", str(improvements),
                    "--confirm"]) == 2
    # crew-before-c9, item 3: the operator's grant was to FILE. Accept, change, verdict and
    # withdraw act only on a ticket the company filed itself (`bb.mine`) -- refused before a
    # client exists, the same barrier as above.
    filed_here = [{"type": "intent", "kind": "file", "id": "BB-0001", "body": {"app_name": "Bots"}},
                  {"type": "outcome", "kind": "file", "id": "BB-0001", "ticket": "ET-31000",
                   "outcome": "accepted"}]
    monkeypatch.setattr(bb, "load", lambda: filed_here)
    assert bb.ours("ET-31000", filed_here) and not bb.ours("ET-30773", filed_here)
    assert bb.main(["verdict", "ET-30773", "pass", "--confirm"]) == 2, "someone else's ticket"
    assert bb.main(["withdraw", "ET-30773", "--confirm"]) == 2

    # crew-before-c9, item 8: one rule for a gap and for a written block, in the skill the lab
    # worker follows and in the plan behind it (CLAUDE.md: a gap is said and relayed, a defect
    # is filed; a written block is recorded in the turn it is written; no worker sends a2a).
    skill = (REPO / ".claude" / "skills" / "laborator" / "SKILL.md").read_text(encoding="utf-8")
    assert "only once they say it went" not in skill
    assert "or a documentation gap gets a check and a report" not in skill
    assert "a2a copy" not in (REPO / "docs" / "laborator-plan.md").read_text(encoding="utf-8")
    # Outside the company the operator's own sends are not braked here.
    monkeypatch.delenv("QA_CREW_DEPT")
    assert crew.crew_brake("a2a", list(range(9)), now) is None


def told_text(notes: list[dict]) -> str:
    return " ".join(note["text"] for note in notes)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_manager_alone_speaks_to_the_operator_and_curates_every_memory(company,
                                                                         monkeypatch,
                                                                         capsys):
    """C5. Departments talk to the manager, and only the manager (and the supervisor's
    own alarms) talks to the operator; what it says waits, unread, until a session reads it.
    Each department writes its own memory under three headings; the manager's daily
    review is told which of them have grown past ten lines."""
    sup = _script("crew")
    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    assert sup.main(["tell", "--text", "I need money"]) == 2, "a department tells the manager"
    monkeypatch.setenv("QA_CREW_DEPT", "manager")
    assert sup.main(["tell", "--text", "Desk: STR-0130 +4,1 % po 3 dnech; nic po tobě",
                     "--key", "desk-2026-10-11"]) == 0
    assert sup.main(["tell", "--text", "the same again", "--key", "desk-2026-10-11"]) == 0
    unread = crew.unread_notes()
    assert [n["text"] for n in unread] == ["Desk: STR-0130 +4,1 % po 3 dnech; nic po tobě"]
    assert unread[0]["id"] == "OP-0001" and unread[0]["from"] == "manager"
    monkeypatch.delenv("QA_CREW_DEPT")
    capsys.readouterr()
    assert sup.main(["inbox"]) == 0
    assert "OP-0001" in capsys.readouterr().out and "STR-0130" in told_text(unread)
    assert crew.unread_notes() == [], "read once, by a session, and marked read"

    # Memory: its own file, its own headings, written by itself or the manager.
    memory = company / "repo-docs" / "bugs.md"
    memory.parent.mkdir()
    memory.write_text("# Bugs\n\n## What we know\n\n- 2026-10-01 one\n\n## How we work\n\n"
                      "## How we went wrong\n\n## Archive\n", encoding="utf-8")
    monkeypatch.setitem(crew.DEPARTMENTS, "bugs", dataclasses.replace(
        crew.DEPARTMENTS["bugs"], memory=(str(memory),)))
    monkeypatch.setenv("QA_CREW_DEPT", "bugs")
    assert sup.main(["lesson", "bugs", "--heading", "wrong",
                     "--text", "trusted a ticket's wording; reproduce first"]) == 0
    text = memory.read_text(encoding="utf-8")
    wrong = text.split("## How we went wrong", 1)[1].split("## Archive", 1)[0]
    assert "trusted a ticket's wording" in wrong
    assert sup.main(["lesson", "manager", "--heading", "know", "--text", "x"]) == 2
    assert sup.main(["lesson", "lab", "--heading", "know", "--text", "x"]) == 2, \
        "the laboratory keeps its lessons per section (lab.py log --lesson)"
    for n in range(12):
        crew.add_lesson("bugs", "know", f"fact {n}")
    assert crew.memory_over(memory) == {"What we know": 13}

    # The daily review: once a local day from six, told which memories grew past ten.
    prague = timezone(timedelta(hours=2))
    assert crew.daily_key(datetime(2026, 10, 12, 5, 59, tzinfo=prague)) is None
    assert crew.daily_key(datetime(2026, 10, 12, 6, 0, tzinfo=prague)) == "daily:2026-10-12"
    monkeypatch.delenv("QA_CREW_DEPT")
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, "-c",
                                                   "print('decide: none')"]))
    morning = datetime.now(timezone.utc).replace(hour=10)
    sup.clock_look(now=morning)
    sup.clock_look(now=morning + timedelta(hours=1))
    daily = [t for t in crew.tickets().values() if t["kind"] == "daily"]
    assert len(daily) == 1 and daily[0]["to"] == "manager"
    assert daily[0]["payload"]["memory_over"] == {str(memory): {"What we know": 13}}
    told = crew.prompt("manager", daily[0])
    for kind in ("operator", "help", "stuck", "decision", "audit", "daily"):
        assert f"`{kind}`" in told, kind
    assert "crew.py tell" in told and "Archive" in told


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_watchdog_leaves_nothing_stuck_in_the_mud(company, monkeypatch):
    """C6. What multi-agent systems die of, each answered by the clock's watchdog: a claim
    whose loop died; a ticket that failed three times; a department that moved nothing for
    a day; a CLI that logged out; a tick that keeps failing; a loop that died. Each one is
    said once -- a key per incident -- and every chain ends with a person: a failure goes to
    the manager, the manager's own failure goes to the operator."""
    sup = _script("crew")
    now = datetime.now(timezone.utc)
    # A claim outliving its lease: its loop died mid-run.
    lost, _ = crew.add_ticket("lab", "lab", "learn", now=now - timedelta(hours=2))
    crew.claim("lab", now=now - timedelta(hours=2))
    # A ticket at its end after three failures, and one of the manager's.
    dead, _ = crew.add_ticket("bugs", "bug", "the 500 on /movers", now=now)
    mine, _ = crew.add_ticket("manager", "decision", "money for H1?", now=now)
    for ticket in (dead, mine):
        for _ in range(crew.MAX_ATTEMPTS):
            crew.claim(ticket["to"], now=now)
            crew.close(ticket["id"], "fail", by="supervisor", note="it broke", now=now)
    # A department sitting on a ticket for a day.
    old, _ = crew.add_ticket("desk", "input", "low scores", now=now - timedelta(hours=26))
    # A CLI that logged out, and a tick that failed three times running.
    crew.record({"type": "run", "dept": "bugs", "outcome": "infra", "widespread": True,
                 "why": "Not logged in · Please run /login"}, now=now)
    # A worker's own words about a login page are not the CLI logged out (second read).
    crew.record({"type": "run", "dept": "lab", "outcome": "infra",
                 "why": "the CLI produced no result: GET /login answered 500"}, now=now)
    assert crew.login_lost([{"type": "run", "outcome": "infra", "at": crew.stamp(now),
                             "why": "GET /login answered 500"}], now) is False
    for minutes in (60, 40, 20):
        crew.record({"type": "tick", "ok": False, "decide": [],
                     "tail": "Traceback: boom"}, now=now - timedelta(minutes=minutes))

    for _ in range(2):  # twice: everything is said once
        sup.watch(now)
    state = crew.tickets()
    assert state[lost["id"]]["attempts"] == 1 and state[lost["id"]]["status"] == "open"
    help_ = [t for t in state.values() if t["kind"] == "help"]
    assert sorted(t["key"] for t in help_) == [f"help:{dead['id']}",
                                              f"tick:{now.astimezone().date()}"]
    stuck = [t for t in state.values() if t["kind"] == "stuck"]
    assert [t["key"] for t in stuck] == [f"stuck:desk:{now.astimezone().date()}"]
    notes = crew.unread_notes()
    keys = sorted(n["key"] for n in notes)
    assert keys == [f"failed:{mine['id']}", f"login:{now.astimezone().date()}"], keys
    assert all(n["from"] == "watchdog" for n in notes)

    # Pure halves, both directions.
    assert crew.stuck_departments({}, [], now) == []
    runs = [{"type": "run", "dept": "lab", "outcome": "work",
             "at": crew.stamp(now - timedelta(hours=h))} for h in (1, 2, 3)]
    assert crew.stuck_departments({}, runs, now) == ["lab"]
    assert crew.stuck_departments({}, runs + [{**runs[0], "outcome": "ok"}], now) == []

    # A dead loop is started again while the company is on, three times an hour at most;
    # then the operator hears of it instead.
    started: list[list[str]] = []
    monkeypatch.setattr(sup, "spawn", lambda args, log: started.append(args) or 99)
    monkeypatch.setattr(sup, "loop_alive", lambda name: name != "desk")
    sup.heal(now)
    assert not started, "a company nobody started is not healed"
    crew.set_running(True, now=now)
    sup.heal(now + timedelta(seconds=30))
    assert not started, "just after start a loop not yet alive is starting, not dead"
    crew.set_running(True, now=now - timedelta(hours=1))
    for minutes in range(0, 12, 3):     # each look past the start grace of the last respawn
        sup.heal(now + timedelta(minutes=minutes))
    assert [a[-1] for a in started] == ["desk", "desk", "desk"]
    assert any(n["key"].startswith("dead:desk") for n in crew.unread_notes())
    crew.set_stop(True)
    sup.heal(now + timedelta(minutes=10))
    assert len(started) == 3, "a stopping company is not healed"
    # Deep pass 2026-10-11, R06: one death, seen by two departments inside the new clock's start,
    # is one respawn -- not two of the three an hour allows.
    crew.set_stop(False)
    later = now + timedelta(hours=3)
    started.clear()
    monkeypatch.setattr(sup, "loop_alive", lambda name: name != "clock")
    sup.heal(later, me="bugs")
    sup.heal(later + timedelta(seconds=1), me="lab")
    assert [a[-1] for a in started] == ["clock"], "two departments each started the dead clock"
    assert crew.respawns(crew.load(crew.runs_path()), "clock", later + timedelta(seconds=2)) == 1

    # A department asleep says why.
    crew.set_snooze("desk", now + timedelta(hours=3), "STR-0130 closes at 23:00", now=now)
    assert "STR-0130" in next(l for l in sup.status_lines(now) if l.startswith("desk"))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_auditor_counts_what_each_department_cost_and_produced(company, monkeypatch,
                                                                   capsys):
    """C7. The process auditor's daily half is code and free: how long tickets waited,
    how many failed or were retried, who sat idle (and that idle is not stuck), what was
    done twice, and the tokens one useful result cost. The patrol carries it, the manager's
    day reads it, and the deep pass's week judges it. No data is no verdict: a company
    that never ran raises no flag."""
    now = datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"type": "ticket", "id": "T-0001", "at": crew.stamp(now - timedelta(hours=5)),
         "to": "bugs", "kind": "bug", "key": "a", "text": "500 on /movers"},
        {"type": "done", "id": "T-0001", "at": crew.stamp(now - timedelta(hours=4)),
         "by": "bugs", "note": "filed #201"},
        {"type": "ticket", "id": "T-0002", "at": crew.stamp(now - timedelta(hours=3)),
         "to": "bugs", "kind": "bug", "key": "b", "text": "500 on /movers"},
        {"type": "fail", "id": "T-0002", "at": crew.stamp(now - timedelta(hours=2)),
         "by": "bugs", "why": "no repro"},
        {"type": "ticket", "id": "T-0003", "at": crew.stamp(now - timedelta(hours=1)),
         "to": "lab", "kind": "lab", "key": "c", "text": "learn"},
    ]
    state = crew.fold(rows)
    runs = [{"type": "run", "dept": "bugs", "outcome": o, "timed_out": False,
             "at": crew.stamp(now - timedelta(hours=h)),
             "tokens": {"input_tokens": 9000, "output_tokens": 1000}}
            for o, h in (("ok", 4), ("work", 2), ("work", 1.5))]
    numbers = crew.metrics(state, runs, now)
    bugs = numbers["departments"]["bugs"]
    assert bugs["opened"] == 2 and bugs["done"] == 1 and bugs["retried"] == 1
    # Deep pass 2026-10-11, R09: opened, retried and done inside the window is ONE retried ticket.
    once = crew.fold([
        {"type": "ticket", "id": "T-0009", "at": crew.stamp(now - timedelta(hours=3)), "to": "desk",
         "kind": "step", "key": "z", "text": "a step"},
        {"type": "fail", "id": "T-0009", "at": crew.stamp(now - timedelta(hours=2)), "by": "desk", "why": "w"},
        {"type": "done", "id": "T-0009", "at": crew.stamp(now - timedelta(hours=1)), "by": "desk"}])
    assert crew.metrics(once, [], now)["departments"]["desk"]["retried"] == 1, "counted twice"
    assert bugs["lead_minutes"] == 60 and bugs["runs"] == 3 and bugs["failed_runs"] == 2
    assert bugs["tokens"] == 30000 and bugs["tokens_per_done"] == 30000
    assert numbers["departments"]["lab"]["oldest_open_hours"] == 1.0
    assert numbers["departments"]["desk"]["state"] == "idle: no work came"
    assert numbers["duplicates"] == [{"to": "bugs", "text": "500 on /movers",
                                      "tickets": ["T-0001", "T-0002"]}]
    said = crew.metric_flags(numbers)
    assert any("bugs" in f and "2 of 3 runs failed" in f for f in said), said
    assert any("twice" in f and "T-0001" in f for f in said), said
    assert crew.metric_flags(crew.metrics({}, [], now)) == [], "no data, no verdict"

    # The clock writes the day's numbers once, and the manager's day carries them.
    sup = _script("crew")
    for row in rows:
        crew._append(crew.tickets_path(), row)
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, "-c",
                                                   "print('decide: none')"]))
    morning = datetime.now(timezone.utc).replace(hour=10)
    sup.clock_look(now=morning)
    sup.clock_look(now=morning + timedelta(minutes=30))
    daily_numbers = [r for r in crew.load(crew.runs_path()) if r.get("type") == "metrics"]
    assert len(daily_numbers) == 1 and "bugs" in daily_numbers[0]["departments"]
    day = next(t for t in crew.tickets().values() if t["kind"] == "daily")
    assert "metrics" in day["payload"]

    # The audit command, and the patrol: the company is one more part it measures. Read
    # as printed: the dry run found every CLI line printing "None" (printable() was taken
    # for a filter; it configures the stream).
    capsys.readouterr()
    # The rows are dated `now` (2026-10-11); the CLI counts back from the real clock. A fixed
    # "--days 7" went stale on 2026-10-18 and aborted a sweep before any live request, so the
    # window is the fixture's age plus its week.
    window = (datetime.now(timezone.utc) - now).total_seconds() / 86400 + 7
    assert sup.main(["audit", "--days", f"{window:.2f}"]) == 0
    printed = capsys.readouterr().out
    assert "bugs" in printed and "twice" in printed and "None" not in printed, printed
    procs = _script("processes")
    section = procs.crew_section(company)
    assert "bugs" in section["departments"]
    assert "crew_section(" in (REPO / "scripts" / "processes.py").read_text(encoding="utf-8")


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

    # A heartbeat that cannot be written -- Windows refuses a replace while another process
    # reads the file -- is skipped, never raised: the dry run lost a loop to exactly that.
    def refused(*args, **kwargs):
        raise PermissionError(13, "access denied")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(crew.os, "replace", refused)
        patch.setattr(crew.time, "sleep", lambda seconds: None)
        crew.beat("bugs", "backoff", "after 1 failed run(s)")

    crew.set_stop(True)
    started = time.monotonic()
    assert sup.loop("bugs", poll=0.05, paused=lambda: False) == 0
    assert time.monotonic() - started < 10
    # What `stop` kills is the pid the loop itself wrote, never a heartbeat's, which any
    # process calling `crew.py once` overwrites (finding 5).
    crew.beat("bugs", "idle", "written by somebody else")
    assert sup.loop_pid("bugs") == os.getpid()

    # C8 review: `once` beside a running loop would be a second writer of its department,
    # and its end would delete the loop's marker under a live worker. Refused.
    crew.set_stop(False)
    with sup.loop_lock("bugs"):
        assert sup.main(["once", "bugs"]) == 2
    # A marker that cannot be deleted this moment (Windows, a reader holding it) is
    # retried and never raised: raised in work_once's finally, it skipped the settlement.
    crew.set_active("bugs", {"id": "T-7", "kind": "bug"})
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "unlink", refused)
        patch.setattr(crew.time, "sleep", lambda seconds: None)
        crew.set_active("bugs", None)
        crew.clear_hold()
        crew.set_stop(False)


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
    # A detached loop has no console, so a worker, a tick or taskkill started from it would
    # each open a window of its own -- closing one kills the run (C8 review, finding 7).
    if os.name == "nt":
        assert sup._group_flags()["creationflags"] & subprocess.CREATE_NO_WINDOW
    # Deep pass 2026-10-11, R10: the stop the operator asks for gives a running ticket back as
    # everyone's, so five stops cannot spend the ticket's release budget.
    ticket, _ = crew.add_ticket("bugs", "sweep", "a sweep", key="stop-test", by="session")
    crew.claim("bugs")
    sup.stop(grace=0.0)
    after = crew.tickets()[ticket["id"]]
    assert after["status"] == "open" and after["releases"] == 0, after
    crew.set_stop(False)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_status_names_every_loop_and_what_each_waits_on(company, monkeypatch, capsys):
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

    # A company whose workers could not run its own commands would close every ticket
    # "done" with nothing handed over: start refuses until the allowlist has them (C8 review,
    # finding 1). Checked before anything else, the CLI included.
    settings = company / "settings.json"
    settings.write_text(json.dumps({"permissions": {"allow": ["Bash(git status:*)"]}}),
                        encoding="utf-8")
    monkeypatch.setattr(sup, "SETTINGS", settings)
    monkeypatch.delenv("QA_CREW_CLAUDE")

    # Reaching the CLI at all means the allowlist was not checked first: fail here rather
    # than run the real login check and spawn real loops (C03, deep pass 2026-10-15).
    def reached(*args, **kwargs):
        raise AssertionError("start() reached the CLI before refusing on the allowlist")

    monkeypatch.setattr(crew, "claude_command", reached)
    capsys.readouterr()
    assert sup.start() == 1 and not crew.running_since()
    assert "does not allow" in capsys.readouterr().out, "refused, but not for the allowlist"
    assert sup.allowlist_missing() == ["Bash(python scripts/crew.py:*)",
                                       "Bash(python scripts/commit.py:*)"]

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

    # crew-before-c9, item 1: the pre-commit hook renders the page and stages it, and a
    # pathspec commit leaves it staged and changed (MM) -- a dirty tree nobody owns, which
    # prereg refuses. Rendered from a clean state/, the page is committed right after.
    (root / "dashboard").mkdir()
    (root / "dashboard" / "index.html").write_text("page 1\n", encoding="utf-8")
    _git(root, "add", "dashboard/index.html")
    _git(root, "commit", "-q", "-m", "page")
    (root / "dashboard" / "index.html").write_text("page 2\n", encoding="utf-8")
    _git(root, "add", "dashboard/index.html")        # what the hook does
    (root / "desk.md").write_text("three\n", encoding="utf-8")
    assert commit.main(["-m", "Desk: H4", "--", "desk.md"]) == 0
    assert "dashboard/index.html" not in _git(root, "status", "--porcelain"), "the page left MM"
    assert "page 2" in _git(root, "show", "HEAD:dashboard/index.html")

    # Bugs owns the tree's housekeeping (item 1): under its own hold, `crew.py tidy` folds and
    # renders (stubbed here), commits what the clock, the console and the hooks wrote, and
    # names what is left -- another department's half-edit, which no level-V run gets past.
    sup = _script("crew")
    (root / "state" / "journal").mkdir(parents=True)
    (root / "audits" / "lab").mkdir(parents=True)
    # The tick's diary snapshots (keep.py snapshot) are housekeeping too: the company's first
    # tick left audits/lab/lab.jsonl and outsider.jsonl changed (2026-10-12).
    for name in ("state/bounty.json", "state/journal/events.jsonl", "audits/lab/lab.jsonl"):
        (root / name).write_text("{}\n", encoding="utf-8")
        _git(root, "add", name)
    _git(root, "commit", "-q", "-m", "state")
    (root / "state" / "bounty.json").write_text('{"polled": 1}\n', encoding="utf-8")
    (root / "audits" / "lab" / "lab.jsonl").write_text('{"snapshot": 2}\n', encoding="utf-8")
    with (root / "state" / "journal" / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write('{"type": "tick"}\n')
    folded: list[Path] = []
    monkeypatch.setattr(sup, "fold_and_render", lambda base: folded.append(base) or None)
    monkeypatch.setenv("QA_CREW_DEPT", "bugs")
    monkeypatch.setenv("QA_CREW_TICKET", "T-0010")
    assert sup.main(["tidy"]) == 2, "tidy runs under the caller's own hold"
    crew.set_hold("bugs", "level V of PRE-0300")
    assert sup.main(["tidy"]) == 1, "another department's half-edit is still there"
    assert folded == [root]
    left = _git(root, "status", "--porcelain")
    assert "bounty.json" not in left and "events.jsonl" not in left and "other.md" in left
    assert "audits/lab/lab.jsonl" not in left, "the tick's snapshot was left as a half-edit"
    assert "console poll" in _git(root, "log", "-1", "--format=%B")
    _git(root, "checkout", "--", "other.md")
    assert sup.main(["tidy"]) == 0
    crew.clear_hold()

    # The watchdog reads the tree too: git's lock left by a killed worker is removed once it
    # is stale, and an edit nobody is making any more goes to the manager, once a day.
    lock = root / ".git" / "index.lock"
    lock.write_text("", encoding="utf-8")
    old = time.time() - 3600
    os.utime(lock, (old, old))
    (root / "other.md").write_text("left by a worker killed at its timeout\n", encoding="utf-8")
    os.utime(root / "other.md", (old - 7200, old - 7200))
    now = datetime.now(timezone.utc)
    sup.watch(now)
    sup.watch(now)
    assert not lock.exists(), "a stale index.lock blocks every commit"
    left = [t for t in crew.tickets().values() if t["to"] == "manager"
            and str(t.get("key", "")).startswith("dirty:")]
    assert len(left) == 1 and "other.md" in left[0]["text"], left
    assert "never to commit, undo" in left[0]["text"], "they may be the operator's own"
    fresh = root / ".git" / "index.lock"
    fresh.write_text("", encoding="utf-8")
    sup.watch(now)
    assert fresh.exists(), "a lock a commit holds right now was taken away"
    fresh.unlink()
    _git(root, "checkout", "--", "other.md")
    monkeypatch.setenv("QA_CREW_DEPT", "desk")
    monkeypatch.setenv("QA_CREW_TICKET", "T-0007")

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

    # A worker commits nothing while a deep pass runs: a commit landing between the pass's
    # review and its push would go out unreviewed (C8 review, finding 2).
    monkeypatch.setattr(commit, "pass_in_flight", lambda: True)
    assert commit.main(["-m", "x", "--", "desk.md"]) == 2
