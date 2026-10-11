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
POLL_SECONDS = 30.0
BACKOFF_MAX_MINUTES = 60


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
                       capture_output=True, text=True)
        return
    import signal

    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(os.getpgid(int(pid)), signal.SIGKILL)


def _group_flags() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
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


def run_ticket(dept: str, ticket: dict) -> dict:
    """Start the department's worker on one ticket and wait for it, within its timeout."""
    spec = crew.DEPARTMENTS[dept]
    command = crew.claude_command()
    if command is None:
        return {"pid": None, "code": 127, "stdout": "no claude executable on this machine",
                "stderr": "", "timed_out": False, "seconds": 0.0}
    args = crew.argv(dept, crew.prompt(dept, ticket), command)
    return run_process(args, worker_env(dept, ticket), spec.timeout)


def work_once(dept: str) -> dict | None:
    """Claim one ticket, run it, and settle it; the run's row, or None when nothing waits.

    A worker closes its own ticket (`crew.py done`/`fail`). One that ends without having
    done so is settled here from how it ended: success closes it, a failure of the work
    spends an attempt, a failure of the machinery (not logged in, overloaded) gives it
    back without spending one.
    """
    ticket = crew.claim(dept)
    if ticket is None:
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
    if after.get("status") == "claimed":
        if said["outcome"] == "ok":
            crew.close(ticket["id"], "done", by="supervisor",
                       note=said["result"][:300] or "the run ended without a word")
        elif said["outcome"] == "infra" and after.get("releases", 0) + 1 < crew.MAX_RELEASES:
            crew.close(ticket["id"], "release", by="supervisor", note=said["why"])
        elif said["outcome"] == "infra":
            crew.close(ticket["id"], "fail", by="supervisor",
                       note=f"released {crew.MAX_RELEASES} times: {said['why']}")
        else:
            crew.close(ticket["id"], "fail", by="supervisor", note=said["why"])
    return crew.record({"type": "run", "dept": dept, "ticket": ticket["id"],
                        "kind": ticket["kind"], "pid": ran["pid"], "exit": ran["code"],
                        "timed_out": ran["timed_out"], "seconds": ran["seconds"],
                        **{k: said[k] for k in ("outcome", "why", "turns", "cost_usd",
                                                "tokens", "result")}})


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


def clock_look() -> tuple[str, str]:
    """The clock's look. It makes tickets on the departments' behalf (C3 on)."""
    crew.beat("clock", "idle", "nothing on the clock yet")
    write_report()
    return "idle", "nothing on the clock yet"


def look(name: str, paused=deep_pass_running) -> tuple[str, str]:
    """One look of a loop: what it did, and why."""
    if name == "clock":
        return clock_look()
    if paused():
        crew.beat(name, "paused", "a deep pass is running")
        return "paused", "a deep pass is running"
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
        if name in running:
            doing = (f"running {running[name].get('ticket')} "
                     f"{_age(running[name].get('since'), now)}")
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


def start() -> int:
    command = crew.claude_command()
    if command is None:
        print("[crew] no claude executable on this machine; nothing started")
        return 1
    ok, why = logged_in(command)
    if not ok:
        print(f"[crew] {why}; nothing started")
        return 1
    crew.set_stop(False)
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
    args = parser.parse_args(argv)

    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.cmd == "start":
        return start()
    if args.cmd == "stop":
        return stop()
    if args.cmd == "status":
        print("\n".join(printable(line) for line in write_report()))
        return 0
    if args.cmd == "loop":
        return loop(args.name)
    if args.cmd == "once":
        row = work_once(args.dept)
        print(json.dumps(row, ensure_ascii=False) if row else "no tickets")
        return 0
    if args.cmd == "ticket":
        try:
            ticket, made = crew.add_ticket(args.to, args.kind, args.text, key=args.key,
                                           payload=json.loads(args.payload)
                                           if args.payload else None, by=_by())
        except ValueError as exc:
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
    if args.cmd == "list":
        for ticket in crew.tickets().values():
            if args.open and ticket["status"] not in ("open", "claimed"):
                continue
            print(printable(f"{ticket['id']} {ticket['status']:<8} {ticket['to']:<9} "
                            f"{ticket['kind']:<9} {ticket['text'][:90]}"))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
