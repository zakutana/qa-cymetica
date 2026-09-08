"""All three channels at once: what moved, what is waiting on whom.

The operator's ask on 2026-09-08, in two halves.

**When the console is running** it already polls both their tracker and the a2a
inbox every fifteen minutes (`serve.py --ask 15`, `console.cmd:52`). That was
never the missing part -- it prints to the server's stdout, where nobody reads
it. `watch` is the missing part: one line per thing worth interrupting for,
onto stdout, so a Monitor turns it into a message in the operator's chat.

**When it is not running**, `status` is the whole check by hand: read every
channel live, then say where all three stand.

    python scripts/channels.py status              # read them all, now
    python scripts/channels.py status --offline    # the journal alone, no network
    python scripts/channels.py watch               # one line per new thing, forever

`watch` polls the JOURNAL, not the network. It costs nothing, it covers both
inbound channels at once because `serve.py --ask` is already writing them
there, and two pollers of one vendor API would be the thing that gets us
rate-limited. If the console is not running, `watch` will sit quiet forever and
that is honest: nothing is arriving to see.

Everything it knows comes from `qa/channels.py`. This file is argument parsing
and printing, so a second idea of what "unanswered" means cannot grow here.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import channels  # noqa: E402
from qa.state import read_events  # noqa: E402

POLL_SECONDS = 30.0


def _live_client():
    """Replaced wholesale in tests, so --offline can be asserted, not trusted."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    ids = identities()
    return build_client(ids["trusted"] if ids["trusted"].present else ids["anon"],
                        EndpointRegistry.load(), timeout=60.0)


def _bounty():
    import importlib.util

    path = REPO_ROOT / "scripts" / "bounty.py"
    spec = importlib.util.spec_from_file_location("bounty_channels", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_live() -> list[str]:
    """The same two calls serve.py --ask makes, so nothing here can drift."""
    notes = []
    bounty = _bounty()
    client = _live_client()
    try:
        try:
            snapshot = bounty.refresh_our_reports(client=client)
            notes.append(f"tracker: {snapshot.get('klass')}, "
                         f"{snapshot.get('total')} report(s)")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"tracker: UNREAD ({type(exc).__name__}) -- "
                         f"a failed read is not an empty one")
        try:
            inbox = bounty.fetch_inbox(client=client)
            notes.append(f"a2a inbox: {inbox['klass']}, "
                         f"{inbox.get('rows_returned')} message(s), "
                         f"{len(inbox.get('new') or [])} new")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"a2a inbox: UNREAD ({type(exc).__name__})")
    finally:
        client.close()
    return notes


def cmd_status(args) -> int:
    if not args.offline:
        for note in _read_live():
            print(f"  {note}")
        print()

    state = channels.state()
    for name in ("bug", "telegram", "a2a"):
        channel = state[name]
        waiting = channel.get("unanswered") or []
        last = channel.get("last_from_them") or "never"
        side = "waiting on them" if channel.get("waiting_on") == "them" \
            else "waiting on us"
        print(f"{name.upper()}")
        print(f"  last heard from them  {last}")
        print(f"  {side:20}  {len(waiting)}"
              + (f": {', '.join(str(w) for w in waiting[:8])}" if waiting else ""))
        if name == "a2a" and channel.get("undelivered"):
            print(f"  never confirmed sent  {', '.join(channel['undelivered'])}")
    return 0


def cmd_compare(args) -> int:
    """Telegram against a2a, with the size of the evidence said out loud."""
    report = channels.compare()
    for name in ("telegram", "a2a"):
        row = report[name]
        median = ("no answered question yet" if row["median_minutes"] is None
                  else f"{row['median_minutes']} min median over n={row['n']}")
        print(f"{name.upper():9} asked {row['asked']}, {median}"
              + (f", {row['unanswered']} still unanswered"
                 if row["unanswered"] else "")
              + (f", {row['answered_but_untimed']} answered but not timeable"
                 if row.get("answered_but_untimed") else ""))
    print()
    if report["conclusive"]:
        print("Both channels have enough answered questions to compare.")
    else:
        print(f"NOT a comparison yet: each channel needs {channels.ENOUGH} "
              f"answered questions.")
        print("Three answers on one evening is a demonstration. The point of "
              "measuring was")
        print("to replace an impression with a number, and a number from n=1 "
              "is the impression")
        print("wearing a number's clothes.")
    return 0


def cmd_watch(args) -> int:
    """One line per new thing they said. Every line is a chat message."""
    seen: set = set()
    # The backlog is the watermark, not an alert: arming this must not replay
    # forty messages the operator has already dealt with.
    #
    # Inside the loop, not before it. serve.py --ask appends every fifteen
    # minutes, and a journal caught mid-append raises the same JournalError the
    # comment below calls normal -- so priming outside the guard killed `watch`
    # at start-up and left the alert silently off for the session, which is the
    # one failure this command exists to prevent.
    primed = False
    while True:
        try:
            lines, seen = channels.new_lines(read_events(), seen)
            if not primed:
                lines, primed = [], True
        except Exception as exc:  # noqa: BLE001
            # A half-written journal line is normal -- another process appends
            # to it. Never die on one; the next tick reads a whole file.
            #
            # stderr, not stdout: every stdout line of this command becomes a
            # message in the operator's chat, and a routine transient must not
            # page anyone. Monitor sends stderr to the log instead.
            print(f"[channels] read failed, retrying: {type(exc).__name__}",
                  file=sys.stderr, flush=True)
            time.sleep(args.interval)
            continue
        for line in lines:
            print(line, flush=True)
        time.sleep(args.interval)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(prog="channels.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="where all three channels stand")
    status.add_argument("--offline", action="store_true",
                        help="the journal alone; makes no request")

    watch = sub.add_parser("watch", help="one line per new thing they said")
    watch.add_argument("--interval", type=float, default=POLL_SECONDS)

    sub.add_parser("compare", help="which channel answers, and how fast")

    args = parser.parse_args(argv)
    return {"status": cmd_status, "watch": cmd_watch,
            "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
