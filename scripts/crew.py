"""The company from the outside: its loops, its tickets, its state (docs/crew-plan.md).

    python scripts/crew.py start               every loop as its own detached process
    python scripts/crew.py stop                every loop ended, its running worker with it
    python scripts/crew.py status              each loop: alive, what it does, its tickets
    python scripts/crew.py loop NAME           one loop in the foreground (what start runs)
    python scripts/crew.py once DEPT           claim one ticket and run it, then return

    python scripts/crew.py ticket --to DEPT --kind KIND --text "..." [--key K]
    python scripts/crew.py done T-NNNN --note "..."
    python scripts/crew.py fail T-NNNN --why "..."
    python scripts/crew.py show T-NNNN | list [--open]

A loop per department claims its tickets and runs one worker at a time: `claude -p` with
the department's model, effort, turn cap and timeout (`qa.crew.DEPARTMENTS`), killed with
its children when the timeout passes. Nothing is claimed while a deep pass runs -- that pass
commits, reverts and pushes -- and nothing at all once `state/crew/stop` exists.

`start` is the operator's word and nothing else's: no hook, session or loop calls it, and a
worker's argv denies it (`qa.crew.DENY_ALL`).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import crew  # noqa: E402
from qa.console import printable  # noqa: E402

LOOPS = ("clock", *crew.DEPARTMENTS)
# How often an idle loop looks again; `QA_CREW_POLL` shortens it for the dry run.
POLL_SECONDS = float(os.environ.get("QA_CREW_POLL") or 30.0)
BACKOFF_MAX_MINUTES = 60
# How long a hold waits for the others to finish what they are running: the longest
# timeout but one (the desk's 50 minutes). Past it, the run goes at level R instead.
HOLD_WAIT_SECONDS = 50 * 60
HOLD_POLL_SECONDS = 10.0
# `QA_CREW_SETTINGS` points the dry run at a settings file of its own; a worker cannot use
# it, because `crew.py start` is denied to every worker.
SETTINGS = Path(os.environ.get("QA_CREW_SETTINGS") or REPO_ROOT / ".claude" / "settings.json")
# What every worker runs to hand over, close and commit; a company started without them
# in the allowlist closes every ticket with nothing done (C8 review).
REQUIRED_ALLOW = ("Bash(python scripts/crew.py:*)", "Bash(python scripts/commit.py:*)")


# -- processes -------------------------------------------------------------------------------

def pid_alive(pid: int | None) -> bool:
    """Whether a process is still running. Never `os.kill(pid, 0)` on Windows: there it
    terminates the process instead of asking about it."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def kill_tree(pid: int | None) -> None:
    """End a process and everything it started -- a worker's bash, python and pytest."""
    if not pid:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(int(pid))],
                       capture_output=True, text=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        return
    import signal

    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(os.getpgid(int(pid)), signal.SIGKILL)


def _group_flags() -> dict:
    """A worker or a tick in a group of its own, so its whole tree can be killed -- and,
    on Windows, without a console window: a detached loop has none, and a console program
    started from it would open one, which closed by hand kills the run (C8 review)."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def spawn(args: list[str], log: str | Path) -> int:
    """Start a process that outlives this one -- and the window it was started from.

    On Windows the Claude app's shell may run its children in a job that dies with it;
    the child asks to break away from it, and is started without it where the job does
    not allow that.
    """
    path = Path(log)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": handle,
                        "stderr": subprocess.STDOUT, "cwd": str(REPO_ROOT),
                        "close_fds": True}
        if os.name != "nt":
            return subprocess.Popen(args, start_new_session=True, **kwargs).pid
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            return subprocess.Popen(args, creationflags=flags | 0x01000000,  # BREAKAWAY
                                    **kwargs).pid
        except OSError:
            return subprocess.Popen(args, creationflags=flags, **kwargs).pid


@contextlib.contextmanager
def loop_lock(name: str):
    """Held for a loop's whole life, so one name runs once; released by the OS when the
    process dies, so a crash never leaves a loop that looks alive."""
    path = crew.crew_dir() / f"loop-{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+b")
    held = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                held = True
            except OSError:
                held = False
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                held = True
            except OSError:
                held = False
        yield held
    finally:
        if held:
            with contextlib.suppress(OSError):
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def loop_alive(name: str) -> bool:
    with loop_lock(name) as free:
        return not free


def _pid_file(name: str) -> Path:
    return crew.crew_dir() / f"loop-{name}.pid"


def loop_pid(name: str) -> int | None:
    """The pid the loop wrote when it took its lock -- what `stop` kills. Not a heartbeat's:
    any process calling `crew.py once` overwrites that one."""
    try:
        return int(_pid_file(name).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


# -- one worker run --------------------------------------------------------------------------

def run_process(args: list[str], env: dict, timeout: int) -> dict:
    """Run one process to its end or its timeout; past the timeout its whole tree is killed.

    Not ended when a deep pass starts: killed mid-edit, a worker would leave half-written
    files the pass then commits (second read). The pass holds the company still before it
    begins instead (`crew.py hold`, its step 0), and the run finishes first."""
    started = time.monotonic()
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                            errors="replace", cwd=str(REPO_ROOT), env=env, **_group_flags())
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(proc.pid)
        try:
            out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            out, err = "", ""
    return {"pid": proc.pid, "code": proc.returncode, "stdout": out or "",
            "stderr": err or "", "timed_out": timed_out,
            "seconds": round(time.monotonic() - started, 1)}


def worker_env(dept: str, ticket: dict) -> dict:
    env = os.environ.copy()
    env["QA_CREW_DEPT"] = dept
    env["QA_CREW_TICKET"] = str(ticket.get("id") or "")
    return env


def _python(script: str, *args: str) -> list[str]:
    return [sys.executable, str(REPO_ROOT / "scripts" / script), *args]


def outsider_proven() -> bool:
    """A probe in the stranger's own process showed nothing of ours (`outsider.py probe`)."""
    from qa import outsider

    return bool(outsider.proven(_sibling("outsider").load()))


def _result(text: str, error: bool = False) -> str:
    """A code department's end, in the shape `claude -p --output-format json` ends in, so
    one reader settles every ticket."""
    return json.dumps({"is_error": error, "result": text, "num_turns": 0})


def run_outsider(ticket: dict) -> dict:
    """The outsider's daily look, as code: the probe when none has passed, the stranger's
    run (its own `claude -p` outside the repository), the actions its picks may take, the
    coins' checkpoints -- and its stumbles and low scores handed on as tickets."""
    env = worker_env("outsider", ticket)
    deadline = time.monotonic() + crew.DEPARTMENTS["outsider"].timeout

    def step(*args: str) -> dict:
        left = max(60, int(deadline - time.monotonic()))
        return run_process(_python(*args), env, left)

    def ended(ran: dict, text: str, error: bool) -> dict:
        return {**ran, "stdout": _result(text, error)}

    if not outsider_proven():
        probed = step("outsider.py", "probe")
        if probed["code"] != 0:
            # Not a stranger yet, or not logged in: the machinery, not the look.
            return {**probed, "code": 1, "stdout": "", "stderr": probed["stdout"][-400:]}
    ran = step("outsider.py", "run")
    found = re.search(r"\b(OUT-\d+)\b", ran["stdout"])
    if ran["code"] != 0 or not found:
        return {**ran, "code": ran["code"] or 1, "stdout": "",
                "stderr": (ran["stdout"] + ran["stderr"])[-400:]}
    run_id = found.group(1)
    step("lab.py", "outsider-act", run_id)
    step("outsider.py", "track")
    row = next((r for r in reversed(_sibling("outsider").load())
                if r.get("type") == "run" and r.get("id") == run_id), {})
    made = [crew.add_ticket(t["to"], t["kind"], t["text"], key=t["key"], by="outsider")
            for t in crew.outsider_tickets(row)]
    opened = [ticket_["id"] for ticket_, new in made if new]
    return ended(ran, f"{run_id}: {len(opened)} ticket(s) handed on "
                      f"({', '.join(opened) or 'none'})", False)


CODE_DEPARTMENTS = {"outsider": run_outsider}


def run_ticket(dept: str, ticket: dict) -> dict:
    """Start the department's worker on one ticket and wait for it, within its timeout."""
    spec = crew.DEPARTMENTS[dept]
    if spec.model is None:
        return CODE_DEPARTMENTS[dept](ticket)
    command = crew.claude_command()
    if command is None:
        return {"pid": None, "code": 127, "stdout": "no claude executable on this machine",
                "stderr": "", "timed_out": False, "seconds": 0.0}
    args = crew.argv(dept, crew.prompt(dept, ticket), command)
    return run_process(args, worker_env(dept, ticket), spec.timeout)


def work_once(dept: str) -> dict | None:
    """Claim one ticket, run it, and settle it; the run's row, or None when nothing waits.

    A worker closes its own ticket (`crew.py done`/`fail`). One that ends without having
    done so is settled here from how it ended: success closes it -- unless one of the
    company's own commands was refused in it, and then its close or hand-over is what was
    lost, so an attempt is spent; a failure of the work spends an attempt; a failure of the
    machinery gives it back, counted against the ticket only when it is unexplained, never
    when it is everyone's (logged out, a usage limit).
    """
    # The marker goes up before the look at the hold, and `hold` sets the hold before it
    # looks at the markers: so either the hold sees this run coming, or this run sees the
    # hold. Looked at the other way round, both could see nothing and both go ahead.
    crew.set_active(dept, {"id": None, "kind": "starting"})
    held = crew.holder()
    if held and held.get("by") != dept:
        crew.set_active(dept, None)
        return None
    ticket = crew.claim(dept)
    if ticket is None:
        crew.set_active(dept, None)
        return None
    crew.set_active(dept, ticket, pid=os.getpid())
    crew.beat(dept, "running", f"{ticket['id']} {ticket['kind']}")
    try:
        ran = run_ticket(dept, ticket)
    except Exception as exc:  # noqa: BLE001 -- a worker that cannot start is machinery
        ran = {"pid": None, "code": None, "stdout": "",
               "stderr": f"the worker could not be started: {exc!r}"[:400],
               "timed_out": False, "seconds": 0.0}
    finally:
        crew.set_active(dept, None)
    said = crew.outcome(ran["code"], ran["stdout"], ran["timed_out"], ran["stderr"])
    after = crew.tickets().get(ticket["id"]) or {}
    if after.get("status") == "claimed" and said["outcome"] == "ok" and said.get(
            "company_refused"):
        # It ended well and never closed its ticket, and one of the company's commands was
        # refused: the close or the hand-over it reports is what did not happen. Not done
        # quietly, not released for ever: an attempt, so three end with the manager.
        said = {**said, "outcome": "work",
                "why": f"a company command was refused: {said['company_refused'][:160]}"}
    if after.get("status") == "claimed":
        releases = after.get("releases", 0)
        if said["outcome"] == "ok":
            crew.close(ticket["id"], "done", by="supervisor",
                       note=said["result"][:300] or "the run ended without a word")
        elif said["outcome"] == "infra" and (said["widespread"]
                                             or releases < crew.MAX_RELEASES):
            crew.close(ticket["id"], "release", by="supervisor", note=said["why"],
                       widespread=said["widespread"])
        elif said["outcome"] == "infra":
            crew.close(ticket["id"], "fail", by="supervisor",
                       note=f"released {releases} times: {said['why']}")
        else:
            crew.close(ticket["id"], "fail", by="supervisor", note=said["why"])
    return crew.record({"type": "run", "dept": dept, "ticket": ticket["id"],
                        "kind": ticket["kind"], "pid": ran["pid"], "exit": ran["code"],
                        "timed_out": ran["timed_out"], "seconds": ran["seconds"],
                        **{k: said[k] for k in ("outcome", "why", "turns", "cost_usd",
                                                "tokens", "result", "denials",
                                                "widespread")}})


# -- the loops -------------------------------------------------------------------------------

_SIBLINGS: dict = {}


def _sibling(name: str):
    if name not in _SIBLINGS:
        spec = importlib.util.spec_from_file_location(f"crew_{name}",
                                                      REPO_ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SIBLINGS[name] = module
    return _SIBLINGS[name]


def deep_pass_running() -> bool:
    """The deep pass's own notebook says it runs (`processes.pass_in_flight`, the reader
    the laboratory already holds its orders on)."""
    return bool(_sibling("processes").pass_in_flight())


def tick_command() -> list[str]:
    """The laboratory's tick; `QA_CREW_TICK` (a JSON list) puts a stand-in there."""
    override = os.environ.get("QA_CREW_TICK")
    return json.loads(override) if override else [sys.executable, "-u",
                                                  str(REPO_ROOT / "scripts" / "lab.py"),
                                                  "tick"]


def run_tick(now: datetime) -> dict:
    """One tick of the laboratory as a process of its own, and its decision routed."""
    env = os.environ.copy()
    env["QA_CREW_DEPT"] = "clock"
    crew.set_active("clock", {"id": None, "kind": "tick"})
    try:
        ran = run_process(tick_command(), env, crew.TICK_TIMEOUT)
    finally:
        crew.set_active("clock", None)
    output = ran["stdout"]
    items = crew.decide_items(output)
    decided = any(line.startswith("decide: ") for line in output.splitlines())
    made = []
    at = crew.stamp(now)
    for spec in crew.route(items, output, at, crew.tickets()):
        ticket, new = crew.add_ticket(spec["to"], spec["kind"], spec["text"], key=spec["key"],
                                      payload=spec.get("payload"), by="clock", now=now)
        if new:
            made.append(ticket["id"])
    return crew.record({"type": "tick", "decide": items, "made": made, "exit": ran["code"],
                        "ok": ran["code"] == 0 and decided, "timed_out": ran["timed_out"],
                        "seconds": ran["seconds"],
                        "tail": "" if decided else (output + ran["stderr"])[-400:]}, now=now)


def watch(now: datetime) -> list[str]:
    """The watchdog's look (C6): every incident said once, by key, and every chain ending
    with a person -- a failure goes to the manager, the manager's own to the operator."""
    said = []
    for tid in crew.expired_leases(crew.tickets(), now):
        crew.close(tid, "fail", by="watchdog", now=now,
                   note="the lease ran out: the loop holding it never reported back")
        said.append(f"lease {tid}")
    state = crew.tickets()
    runs = crew.load(crew.runs_path())
    keys = {t.get("key") for t in state.values()}
    told = {n.get("key") for n in crew.load(crew.operator_path()) if n.get("type") == "note"}
    day = now.astimezone().date().isoformat()

    def to_manager(kind: str, key: str, text: str, payload: dict | None = None) -> None:
        if key not in keys:
            ticket, new = crew.add_ticket("manager", kind, text, key=key, payload=payload,
                                          by="watchdog", now=now)
            keys.add(key)
            if new:
                said.append(f"{kind} {ticket['id']}")

    def to_operator(key: str, text: str) -> None:
        if key not in told:
            crew.tell(text, by="watchdog", key=key, now=now)
            told.add(key)
            said.append(f"note {key}")

    for ticket in state.values():
        if ticket["status"] != "failed":
            continue
        if ticket["to"] == "manager":
            to_operator(f"failed:{ticket['id']}",
                        f"Manažer nezvládl {ticket['id']} ({ticket['kind']}) ani na třetí "
                        f"pokus: {ticket['text'][:160]} — {ticket.get('why') or ''}")
        else:
            to_manager("help", f"help:{ticket['id']}",
                       f"{ticket['id']} ({ticket['to']}, {ticket['kind']}) failed "
                       f"{crew.MAX_ATTEMPTS} times: {ticket.get('why') or ''}",
                       {"ticket": ticket["id"]})
    for dept in crew.stuck_departments(state, runs, now, crew.running_since()):
        if dept == "manager":
            to_operator(f"stuck:manager:{day}",
                        "Manažer firmy se den nepohnul: lístky na něj čekají nebo mu "
                        "nevychází žádný běh. `python scripts/crew.py status` ukáže proč.")
        else:
            to_manager("stuck", f"stuck:{dept}:{day}",
                       f"{dept} moved nothing for a day", {"dept": dept})
    if crew.login_lost(runs, now):
        to_operator(f"login:{day}", "claude na tomhle počítači není přihlášený, takže firma "
                                    "stojí. Spusť jednou `claude` a dej /login.")
    tail = crew.tick_failing(runs)
    if tail:
        to_manager("help", f"tick:{day}",
                   f"the laboratory's tick failed {crew.TICK_FAILURES} times running: {tail}")
    return said


def heal(now: datetime, me: str = "clock") -> list[str]:
    """Start again a loop that died while the company is on -- three times an hour at most,
    then the operator hears of it instead. The clock heals the departments, and each
    department the clock: a loop's lock makes a second start of one name exit at once."""
    since = crew.running_since()
    if crew.stopping() or since is None or now - since < crew.HEAL_GRACE:
        return []
    names = [n for n in LOOPS if n != me] if me == "clock" else ["clock"]
    runs = crew.load(crew.runs_path())
    said = []
    for name in names:
        if loop_alive(name):
            continue
        if crew.respawns(runs, name, now) >= crew.RESPAWNS_PER_HOUR:
            key = f"dead:{name}:{now.astimezone().date().isoformat()}"
            crew.tell(f"Smyčka {name} umřela {crew.RESPAWNS_PER_HOUR}× za hodinu, dál ji "
                      f"nespouštím. Log: state/crew/logs/{name}.log", by="watchdog", key=key,
                      now=now)
            continue
        pid = spawn(_python("crew.py", "loop", name), crew.crew_dir() / "logs" / f"{name}.log")
        runs.append(crew.record({"type": "respawn", "loop": name, "pid": pid}, now=now))
        said.append(f"restarted {name}")
    return said


def clock_look(now: datetime | None = None) -> tuple[str, str]:
    """The clock's look: the tickets it makes on the departments' behalf, when each is due."""
    now = now or datetime.now(timezone.utc)
    said = [*heal(now), *watch(now)]
    state = crew.clock_state()
    last = crew.moment(state.get("tick_at"))
    if last is None or now - last >= crew.TICK_EVERY:
        # work_once's protocol: the marker up before the look at the hold, so a hold set in
        # between still sees the tick coming (C8 review). Held, the tick waits: it can
        # append to the journal under a level-V run.
        crew.set_active("clock", {"id": None, "kind": "tick"})
        hold = crew.holder(now)
        if hold:
            crew.set_active("clock", None)
            said.append(f"tick waits: the tree is held by {hold.get('by')}")
        else:
            state["tick_at"] = crew.stamp(now)
            crew.save_clock_state(state)
            row = run_tick(now)
            said.append(f"tick: decide {' + '.join(row['decide']) or 'none'}"
                        + (f", {len(row['made'])} ticket(s)" if row["made"] else ""))
    else:
        left = crew.TICK_EVERY - (now - last)
        said.append(f"next tick in {int(left.total_seconds() // 60)}m")
    daily = crew.daily_key(now)
    if daily and state.get("metrics_day") != daily:
        # The auditor's daily half, written before the manager's day so the day reads it.
        numbers = crew.metrics(crew.tickets(), crew.load(crew.runs_path()), now)
        crew.record({"type": "metrics", **numbers, "flags": crew.metric_flags(numbers)},
                    now=now)
        state["metrics_day"] = daily
        crew.save_clock_state(state)
        ticket, new = crew.add_ticket(
            "manager", "daily", "the day's review: progress, memories, a note if needed",
            key=daily, payload={"memory_over": crew.memories_over(), "metrics": numbers,
                                "flags": crew.metric_flags(numbers)}, by="clock", now=now)
        if new:
            said.append(f"daily review: {ticket['id']}")
    if crew.desk_due(crew.tickets(), crew.last_run_end("desk"), crew.snoozed("desk", now), now):
        ticket, new = crew.add_ticket(
            "desk", "step", "one step towards proving that money can be made on Cymetica",
            key=f"desk:{crew.stamp(now)}", by="clock", now=now)
        if new:
            said.append(f"desk: {ticket['id']}")
    crew.beat("clock", "idle", "; ".join(said), now=now)
    write_report(now)
    return "idle", "; ".join(said)


def look(name: str, paused=deep_pass_running) -> tuple[str, str]:
    """One look of a loop: what it did, and why."""
    if name == "clock":
        return clock_look()
    heal(datetime.now(timezone.utc), me=name)
    if paused():
        crew.beat(name, "paused", "a deep pass is running")
        return "paused", "a deep pass is running"
    hold = crew.holder()
    if hold and hold.get("by") != name:
        why = f"the tree is held still by {hold.get('by')}: {hold.get('why')}"
        crew.beat(name, "held", why)
        return "held", why
    row = work_once(name)
    if row is None:
        crew.beat(name, "idle", "no tickets")
        return "idle", "no tickets"
    crew.beat(name, "idle", f"last: {row['ticket']} {row['outcome']}")
    return "worked", row["outcome"]


def backoff(failures: int) -> timedelta:
    """1, 2, 4 ... minutes after consecutive failed runs, at most an hour: a broken run
    retried at once is a loop that spends its tickets' attempts in a minute."""
    return timedelta(minutes=min(BACKOFF_MAX_MINUTES, 2 ** max(0, failures - 1)))


def _sleep(seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end and not crew.stopping():
        time.sleep(min(1.0, max(0.0, end - time.monotonic())))


def loop(name: str, poll: float = POLL_SECONDS, paused=deep_pass_running) -> int:
    """A department's loop until the company stops."""
    with loop_lock(name) as held:
        if not held:
            print(f"[crew] {name} is already running")
            return 0
        _pid_file(name).write_text(str(os.getpid()), encoding="utf-8")
        crew.record({"type": "loop", "loop": name, "event": "start", "pid": os.getpid()})
        failures, resume_at = 0, None
        while not crew.stopping():
            now = datetime.now(timezone.utc)
            if resume_at and now < resume_at:
                crew.beat(name, "backoff", f"after {failures} failed run(s), until "
                          f"{crew.stamp(resume_at)}")
                _sleep(poll)
                continue
            try:
                state, why = look(name, paused=paused)
            except Exception as exc:  # noqa: BLE001 -- a loop reports and carries on
                state, why = "worked", "error"
                with contextlib.suppress(Exception):
                    crew.record({"type": "error", "loop": name, "error": repr(exc)[:400]})
            if state == "worked":
                failures = 0 if why == "ok" else failures + 1
                resume_at = now + backoff(failures) if failures else None
                continue
            _sleep(poll)
        crew.beat(name, "stopped", "the company stopped")
        crew.record({"type": "loop", "loop": name, "event": "stop", "pid": os.getpid()})
    return 0


# -- status ----------------------------------------------------------------------------------

def _age(value, now: datetime) -> str:
    when = crew.moment(value)
    if when is None:
        return "never"
    seconds = max(0, int((now - when).total_seconds()))
    if seconds < 120:
        return f"{seconds}s"
    if seconds < 7200:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h"


def status_lines(now: datetime | None = None) -> list[str]:
    """One line for the company, one per loop: alive, what it does, its tickets."""
    now = now or datetime.now(timezone.utc)
    beats, running = crew.beats(), crew.active()
    state = crew.tickets()
    alive = {name: loop_alive(name) for name in LOOPS}
    day_ago = now - timedelta(days=1)
    head = (f"company: running ({sum(alive.values())}/{len(LOOPS)} loops)"
            if any(alive.values()) else "company: stopped")
    if crew.stopping():
        head += " -- stop flag set"
    lines = [head]
    for name in LOOPS:
        beat = beats.get(name) or {}
        light = "alive" if alive[name] else "not running"
        doing = beat.get("state") or "-"
        asleep = crew.snoozed(name, now) if name in crew.DEPARTMENTS else None
        if name in running:
            doing = (f"running {running[name].get('ticket')} "
                     f"{_age(running[name].get('since'), now)}")
        elif asleep:
            doing = f"asleep until {asleep['until'][:16]}: {asleep.get('why')}"
        elif beat.get("why"):
            doing = f"{doing}: {beat['why']}"
        line = f"{name:<9}{light}, seen {_age(beat.get('at'), now)} ago; {doing}"
        if name in crew.DEPARTMENTS:
            mine = [t for t in state.values() if t["to"] == name]
            open_ = sum(t["status"] in ("open", "claimed") for t in mine)
            closed = [t for t in mine if (crew.moment(t.get("closed_at")) or now) >= day_ago
                      and t["status"] in ("done", "failed")]
            line += (f" | open {open_}, done 24h {sum(t['status'] == 'done' for t in closed)}"
                     f", failed 24h {sum(t['status'] == 'failed' for t in closed)}")
        lines.append(line)
    return lines


def write_report(now: datetime | None = None) -> list[str]:
    """The department report /lab lists (`qa/departments.py`): the status, line by line."""
    lines = status_lines(now)
    crew._write_json(crew.crew_dir() / "report.json", {"title": "Company", "lines": lines})
    return lines


# -- start and stop --------------------------------------------------------------------------

def logged_in(command: list[str]) -> tuple[bool, str]:
    """Whether the CLI can run a worker at all: a company started logged out fails every
    run it makes. A stand-in (`QA_CREW_CLAUDE`) is not asked."""
    if os.environ.get("QA_CREW_CLAUDE"):
        return True, ""
    try:
        done = subprocess.run([*command, "auth", "status"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
        said = json.loads(done.stdout or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return False, f"`claude auth status` did not answer: {exc}"
    if not said.get("loggedIn"):
        return False, "claude is not logged in on this machine: run `claude` once and /login"
    return True, ""


def allowlist_missing() -> list[str]:
    """What the project's allowlist lacks of what every worker must run."""
    try:
        allow = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]["allow"]
    except (OSError, ValueError, KeyError, TypeError):
        allow = []
    return [rule for rule in REQUIRED_ALLOW if rule not in allow]


def start() -> int:
    missing = allowlist_missing()
    if missing:
        # A headless worker cannot be asked: refused, its hand-over, its close and its
        # commit would all be lost while its ticket read "done".
        print(f"[crew] .claude/settings.json does not allow {', '.join(missing)}; every "
              f"worker needs them -- nothing started")
        return 1
    command = crew.claude_command()
    if command is None:
        print("[crew] no claude executable on this machine; nothing started")
        return 1
    ok, why = logged_in(command)
    if not ok:
        print(f"[crew] {why}; nothing started")
        return 1
    if not os.environ.get("QA_CREW_CLAUDE") and not outsider_proven():
        # The laboratory decides the outsider's look only once a probe has passed, and
        # the first one can run only now that the CLI is logged in.
        probed = run_process(_python("outsider.py", "probe"), os.environ.copy(), 600)
        print(f"[crew] {(probed['stdout'] or probed['stderr']).strip()[:200]}")
    crew.set_stop(False)
    crew.set_running(True)
    started = []
    for name in LOOPS:
        if loop_alive(name):
            continue
        pid = spawn([sys.executable, str(REPO_ROOT / "scripts" / "crew.py"), "loop", name],
                    crew.crew_dir() / "logs" / f"{name}.log")
        started.append(f"{name} ({pid})")
    crew.record({"type": "company", "event": "start", "loops": started})
    print("[crew] started: " + (", ".join(started) or "every loop was already running"))
    return 0


def stop(grace: float = 20.0) -> int:
    crew.set_stop(True)
    crew.set_running(False)
    for name in LOOPS:
        if loop_alive(name):
            kill_tree(loop_pid(name))
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and any(loop_alive(n) for n in LOOPS):
        time.sleep(0.5)
    for dept in crew.active():
        crew.set_active(dept, None)
    for ticket in crew.tickets().values():
        if ticket["status"] == "claimed":
            crew.close(ticket["id"], "release", by="supervisor", note="the company stopped")
    still = [n for n in LOOPS if loop_alive(n)]
    crew.record({"type": "company", "event": "stop", "still": still})
    print("[crew] stopped" + (f"; still ending: {', '.join(still)}" if still else ""))
    return 0 if not still else 1


# -- the tree held still ---------------------------------------------------------------------

def hold(why: str) -> int:
    """Hold the tree still for a level-V run: no new run starts, and this returns once
    nobody else is mid-run. Given up -- and let go -- if they are not done in time."""
    by = _by()
    crew.set_hold(by, why)
    deadline = time.monotonic() + HOLD_WAIT_SECONDS
    while True:
        others = sorted(name for name in crew.active() if name != by)
        if not others:
            # The hour runs from here: the wait must not eat the run's time.
            crew.set_hold(by, why)
            print(f"[crew] held by {by}: the tree is still")
            return 0
        if time.monotonic() > deadline:
            crew.clear_hold()
            print(f"[crew] {', '.join(others)} still running after "
                  f"{HOLD_WAIT_SECONDS / 60:.0f} min; let go -- run at level R, or later")
            return 1
        time.sleep(HOLD_POLL_SECONDS)


def snooze(hours: float | None, until: str | None, why: str) -> int:
    """A department sleeps on purpose, and says why -- quiet, not stuck."""
    dept = _by()
    if dept not in crew.DEPARTMENTS:
        print("[crew] refused: a department sleeps, not a session")
        return 2
    now = datetime.now(timezone.utc)
    when = crew.moment(until) if until else (now + timedelta(hours=hours)
                                             if hours is not None else None)
    if when is None:
        print("[crew] refused: --hours N or --until <ISO time>")
        return 2
    try:
        crew.set_snooze(dept, when, why, now=now)
    except ValueError as exc:
        print(f"[crew] refused: {exc}")
        return 2
    print(f"[crew] {dept} sleeps until {crew.stamp(when)}: {why}")
    return 0


def tell(text: str, key: str | None) -> int:
    try:
        note, new = crew.tell(text, by=_by(), key=key)
    except PermissionError as exc:
        print(f"[crew] refused: {exc}")
        return 2
    print(f"[crew] {note['id']} {'written' if new else 'already written'}")
    return 0


def inbox() -> int:
    """What the manager says to the operator, printed once and marked read. A session's
    to read; a department marking them read would hide them from the operator."""
    if os.environ.get("QA_CREW_DEPT"):
        print("[crew] refused: the operator's inbox is read by a session")
        return 2
    notes = crew.unread_notes()
    for note in notes:
        print(f"{note['id']} {note['at'][:16]} {note['from']}: {note['text']}")
    crew.mark_read([note["id"] for note in notes])
    if not notes:
        print("nothing unread")
    return 0


def lesson(dept: str, heading: str, text: str) -> int:
    by = _by()
    if by in crew.DEPARTMENTS and by not in (dept, "manager"):
        print(f"[crew] refused: {dept}'s memory is written by {dept} or the manager")
        return 2
    try:
        path = crew.add_lesson(dept, heading, text)
    except (ValueError, OSError) as exc:
        print(f"[crew] refused: {exc}")
        return 2
    over = crew.memory_over(path)
    print(f"[crew] written to {path.name}"
          + (f"; over ten lines: {over} -- the manager's daily review curates" if over else ""))
    return 0


def audit(days: float) -> int:
    """The auditor's numbers over a window, for the manager and the deep pass's week."""
    now = datetime.now(timezone.utc)
    numbers = crew.metrics(crew.tickets(), crew.load(crew.runs_path()), now,
                           timedelta(days=days))
    print(f"the company over {days:g} day(s), to {numbers['at'][:16]}")
    print(f"{'dept':9} {'state':20} {'open':>4} {'done':>4} {'fail':>4} {'retry':>5} "
          f"{'lead m':>6} {'runs':>4} {'bad':>4} {'tok/done':>9}")
    for dept, row in numbers["departments"].items():
        print(f"{dept:9} {row['state'][:20]:20} {row['opened']:>4} {row['done']:>4} "
              f"{row['failed']:>4} {row['retried']:>5} {row['lead_minutes'] or '-':>6} "
              f"{row['runs']:>4} {row['failed_runs']:>4} {row['tokens_per_done'] or '-':>9}")
    for line in crew.metric_flags(numbers) or ["nothing off"]:
        print(line)
    return 0


def unhold() -> int:
    held, by = crew.holder(), _by()
    if held is None:
        print("[crew] nothing is held")
        return 0
    if by not in (held.get("by"), "session", "manager"):
        print(f"[crew] refused: the hold is {held.get('by')}'s")
        return 2
    crew.clear_hold()
    print(f"[crew] let go of {held.get('by')}'s hold")
    return 0


# -- the CLI ---------------------------------------------------------------------------------

def _by() -> str:
    return os.environ.get("QA_CREW_DEPT") or "session"


def _show(ticket_id: str) -> int:
    rows = [r for r in crew.load(crew.tickets_path()) if r.get("id") == ticket_id]
    if not rows:
        print(f"no ticket {ticket_id}")
        return 1
    print(json.dumps(crew.tickets()[ticket_id], ensure_ascii=False, indent=1))
    for row in rows[1:]:
        print(f"  {row.get('at')} {row.get('type')} by {row.get('by')}: "
              f"{row.get('note') or row.get('why') or ''}")
    for run in crew.load(crew.runs_path()):
        if run.get("type") == "run" and run.get("ticket") == ticket_id:
            print(f"  run {run.get('at')} {run.get('outcome')} {run.get('seconds')}s "
                  f"{run.get('why') or ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    one = sub.add_parser("loop")
    one.add_argument("name", choices=LOOPS)
    once = sub.add_parser("once")
    once.add_argument("dept", choices=list(crew.DEPARTMENTS))
    new = sub.add_parser("ticket")
    new.add_argument("--to", required=True, choices=list(crew.DEPARTMENTS))
    new.add_argument("--kind", required=True)
    new.add_argument("--text", required=True)
    new.add_argument("--key")
    new.add_argument("--payload", help="a JSON object")
    done = sub.add_parser("done")
    done.add_argument("id")
    done.add_argument("--note", default="")
    fail = sub.add_parser("fail")
    fail.add_argument("id")
    fail.add_argument("--why", required=True)
    show = sub.add_parser("show")
    show.add_argument("id")
    listing = sub.add_parser("list")
    listing.add_argument("--open", action="store_true")
    held = sub.add_parser("hold", help="hold the tree still for a level-V run")
    held.add_argument("--why", required=True)
    sub.add_parser("unhold")
    sleep = sub.add_parser("snooze", help="a department sleeps on purpose until a moment")
    sleep.add_argument("--hours", type=float)
    sleep.add_argument("--until")
    sleep.add_argument("--why", required=True)
    note = sub.add_parser("tell", help="the manager's note to the operator")
    note.add_argument("--text", required=True)
    note.add_argument("--key")
    sub.add_parser("inbox", help="the manager's notes, printed and marked read")
    learned = sub.add_parser("lesson", help="one line into a department's memory")
    learned.add_argument("dept", choices=list(crew.DEPARTMENTS))
    learned.add_argument("--heading", required=True, choices=list(crew.HEADINGS))
    learned.add_argument("--text", required=True)
    audited = sub.add_parser("audit", help="each department's numbers over a window")
    audited.add_argument("--days", type=float, default=1.0)
    args = parser.parse_args(argv)

    printable()
    if args.cmd == "start":
        return start()
    if args.cmd == "stop":
        return stop()
    if args.cmd == "status":
        print("\n".join(write_report()))
        return 0
    if args.cmd == "loop":
        return loop(args.name)
    if args.cmd == "once":
        # Beside a running loop it would be a second writer of the department, and its end
        # would delete the loop's marker under a live worker (C8 review).
        with loop_lock(args.dept) as held:
            if not held:
                print(f"[crew] refused: the {args.dept} loop is running")
                return 2
            if deep_pass_running():
                print("[crew] refused: a deep pass is running")
                return 2
            row = work_once(args.dept)
        print(json.dumps(row, ensure_ascii=False) if row else "no tickets")
        return 0
    if args.cmd == "ticket":
        try:
            ticket, made = crew.add_ticket(args.to, args.kind, args.text, key=args.key,
                                           payload=json.loads(args.payload)
                                           if args.payload else None, by=_by())
        except (ValueError, PermissionError) as exc:
            print(f"[crew] refused: {exc}")
            return 2
        print(f"{ticket['id']} {'opened' if made else 'already exists: ' + ticket['status']}")
        return 0
    if args.cmd in ("done", "fail"):
        try:
            after = crew.close(args.id, args.cmd, by=_by(),
                               note=args.note if args.cmd == "done" else args.why)
        except PermissionError as exc:
            print(f"[crew] refused: {exc}")
            return 2
        if after is None:
            print(f"no ticket {args.id}")
            return 1
        print(f"{args.id} {after['status']} (attempts {after['attempts']})")
        return 0
    if args.cmd == "show":
        return _show(args.id)
    if args.cmd == "hold":
        return hold(args.why)
    if args.cmd == "unhold":
        return unhold()
    if args.cmd == "snooze":
        return snooze(args.hours, args.until, args.why)
    if args.cmd == "tell":
        return tell(args.text, args.key)
    if args.cmd == "inbox":
        return inbox()
    if args.cmd == "lesson":
        return lesson(args.dept, args.heading, args.text)
    if args.cmd == "audit":
        return audit(args.days)
    if args.cmd == "list":
        for ticket in crew.tickets().values():
            if args.open and ticket["status"] not in ("open", "claimed"):
                continue
            print(f"{ticket['id']} {ticket['status']:<8} {ticket['to']:<9} "
                  f"{ticket['kind']:<9} {ticket['text'][:90]}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
