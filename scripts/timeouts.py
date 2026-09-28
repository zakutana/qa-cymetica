"""Every timeout and slow answer from their host that we recorded, by UTC time.

    python scripts/timeouts.py                    since two days ago, slow = 10 s
    python scripts/timeouts.py --since 2026-09-26 --slow 5

Cymetica asked for the exact minute of any timeout to match their logs
(REPLY-0098). The main source is `state/timings.jsonl`, where SafetyTransport
times every real request; the older diaries are read beside it, because they
held the only record before that diary existed: the sampler's rounds, the Hot
rounds, their own `balance_check_status`, the Nexus polls, the laboratory's
failed reads, our a2a and filing outcomes, and the discovery reads of each run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BAD = re.compile(r"timeout|timed out|ConnectError|disconnected", re.I)


def _rows(name: str):
    from qa.state import state_dir

    p = state_dir() / name
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue


def collect(since: str, slow_s: float = 10.0) -> list[tuple[str, str, str]]:
    """(at, what, detail) for every timeout or slow answer since `since`, in order."""
    from qa.state import state_dir

    out: set[tuple[str, str, str]] = set()
    fresh = lambda r: str(r.get("at", "")) >= since  # noqa: E731

    for r in _rows("timings.jsonl"):
        if fresh(r) and (r.get("error") or (r.get("ms") or 0) >= slow_s * 1000):
            out.add((r["at"], f"{r.get('method')} {r.get('path')}",
                     f"{r.get('error') or 'HTTP ' + str(r.get('status'))} after "
                     f"{(r.get('ms') or 0) / 1000:.1f} s"))
    for r in _rows("samples.jsonl"):
        if r.get("type") == "tick" and not r.get("ok") and fresh(r):
            bad = {k: v for k, v in (r.get("reads") or {}).items() if BAD.search(str(v))}
            if bad:
                out.add((r["at"], "sampler (bots/balance/activity of our paper clones)",
                         ", ".join(f"{k} {v}" for k, v in bad.items())))
    for r in _rows("hot_watch.jsonl"):
        if not fresh(r) or r.get("ok"):
            continue
        if r.get("type") == "card" and BAD.search(str(r.get("status"))):
            out.add((r["at"], f"event-card index history {str(r.get('card_id'))[:8]}",
                     str(r.get("status"))[:60]))
        errors = (r.get("errors") or []) if r.get("type") == "round" else []
        for err in errors:
            if BAD.search(str(err)):
                out.add((r["at"], "Hot headlines list", str(err)[:80]))
    for r in _rows("nexus.jsonl"):
        if fresh(r) and BAD.search(str(r.get("status") or r.get("error") or "")):
            out.add((r["at"], f"Nexus deep-answer poll {r.get('id')}",
                     str(r.get("status") or r.get("error"))[:60]))
    for r in _rows("clones.jsonl"):
        if fresh(r) and r.get("balance_check_status") == "timeout":
            out.add((r["at"], "account balance: their own balance_check_status",
                     "timeout, balances_provisional true"))
    for r in _rows("lab.jsonl"):
        blob = json.dumps(r.get("failed") or "")
        if fresh(r) and BAD.search(blob):
            out.add((r["at"], "laboratory tick read", blob[:100]))
    for r in _rows("journal/events.jsonl"):
        err = str(r.get("error") or "")
        if fresh(r) and r.get("by") == "agent" and BAD.search(err):
            out.add((r["at"], f"{r.get('type')} ({r.get('source', '')})", err[:80]))
    for f in sorted((state_dir() / "runs").glob("run-*.json")):
        try:
            run = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if str(run.get("started_at", "")) < since:
            continue
        for part, err in (run.get("fingerprint_errors") or {}).items():
            if BAD.search(str(err)):
                out.add((run["started_at"], f"discovery read {part}", str(err)[:80]))
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    two_days = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    parser.add_argument("--since", default=two_days, help="YYYY-MM-DD, UTC")
    parser.add_argument("--slow", type=float, default=10.0,
                        help="seconds; a slower answer is listed too")
    args = parser.parse_args(argv)
    rows = collect(args.since, args.slow)
    for at, what, detail in rows:
        print(f"{at[:16].replace('T', ' ')}  {what}  --  {detail}")
    print(f"\n{len(rows)} timeout(s) or slow answer(s) since {args.since} (UTC)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
