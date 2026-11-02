"""All three channels at once: what moved, what is waiting on whom.

    python scripts/channels.py status              # read the tracker and the inbox, then say
    python scripts/channels.py status --offline    # the journal alone, no network

Everything it knows comes from qa/channels.py. This file is argument parsing and printing.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import channels  # noqa: E402
from qa.console import printable  # noqa: E402


def _bounty():
    spec = importlib.util.spec_from_file_location("bounty_channels", REPO_ROOT / "scripts" / "bounty.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _live_client():
    """Replaced wholesale in tests, so --offline can be asserted, not trusted."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    ids = identities()
    return build_client(ids["trusted"] if ids["trusted"].present else ids["anon"],
                        EndpointRegistry.load(), timeout=60.0)


def _read_live() -> list[str]:
    notes = []
    bounty = _bounty()
    client = _live_client()
    try:
        try:
            snapshot = bounty.refresh_our_reports(client=client)
            notes.append(f"tracker: {snapshot.get('klass')}, {snapshot.get('total')} report(s)")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"tracker: UNREAD ({type(exc).__name__}) -- a failed read is not an empty one")
        try:
            inbox = bounty.fetch_inbox(client=client)
            notes.append(f"a2a inbox: {inbox['klass']}, {inbox.get('rows_returned')} message(s), "
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
        side = "waiting on them" if channel.get("waiting_on") == "them" else "waiting on us"
        print(name.upper())
        print(f"  last heard from them  {channel.get('last_from_them') or 'never'}")
        print(f"  {side:20}  {len(waiting)}" + (f": {', '.join(str(w) for w in waiting[:8])}" if waiting else ""))
        if channel.get("undelivered"):
            print(f"  never confirmed sent  {', '.join(channel['undelivered'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(prog="channels.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="where all three channels stand")
    status.add_argument("--offline", action="store_true", help="the journal alone; makes no request")
    args = parser.parse_args(argv)
    return cmd_status(args)


if __name__ == "__main__":
    raise SystemExit(main())
