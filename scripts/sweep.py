"""Where every bug we filed stands, and with --send tell them what our checks found.

    python scripts/sweep.py            read their tracker and inbox, run the checks of open rows, print the table
    python scripts/sweep.py --all      the same over every row, the ones we already passed included
    python scripts/sweep.py --send     also post the verdicts

Open means: not withdrawn, not rejected by them, and we have not told them it passes. `pass` goes when every check
of a report passes and our last word was not a pass. `fail` goes when a check fails and they claim a fix (their
status says fixed or paid) or we told them it passed, unless our last fail is newer than their last claim.

Two old rules survive here because they stop false claims to the vendor. Rule 10: a check that could not measure
is never a verdict. Rule 8: a read that failed is not an empty read, so nothing goes out on one. And the check is
run a second time right before anything is sent: a sweep can take twenty minutes, and their platform ships faster.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import checks  # noqa: E402
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.paths import append_event, load_filed, save_filed  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

SOURCE = "scripts/sweep.py"
# They said 20 reports an hour; the header says 60. The smaller number, as in filing.
MAX_PER_RUN = 12
PAUSE_SECONDS = 4
# Their `evidence` field holds 8000 characters (422 on #130).
EVIDENCE_LIMIT = 8000
FIX_CLAIMED = {"fixed", "paid"}
REJECTED = {"invalid", "duplicate", "wontfix"}


class Unread(Exception):
    """A read of theirs did not succeed, so what they hold is not known."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bounty():
    spec = importlib.util.spec_from_file_location("bounty_sweep", REPO_ROOT / "scripts" / "bounty.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Deciding
# ---------------------------------------------------------------------------
def _last_verdict(row: dict, report_id) -> str | None:
    sent = [v for v in row.get("verdicts_sent") or [] if v.get("report_id") == report_id]
    return sent[-1].get("verdict") if sent else None


def _closed(row: dict) -> bool:
    ids = row.get("report_ids") or []
    return bool(ids) and all(_last_verdict(row, i) == "pass" for i in ids)


def _rejected(row: dict) -> bool:
    statuses = [str(s).lower() for s in (row.get("their_status") or {}).values()]
    return bool(statuses) and all(s in REJECTED for s in statuses)


def open_rows(rows: list[dict], everything: bool = False) -> list[dict]:
    live = [r for r in rows if not r.get("withdrawn")]
    return live if everything else [r for r in live if not _closed(r) and not _rejected(r)]


def by_report(rows: list[dict], readings: dict[str, dict]) -> dict:
    """One result per report: several rows can share one, and it passes only when all of them do."""
    out: dict = {}
    for row in rows:
        for report_id in row.get("report_ids") or []:
            entry = out.setdefault(report_id, {"nodeids": [], "rows": [], "by_hand": False})
            entry["rows"].append(row["key"])
            nodeids = row.get("nodeids") or []
            entry["nodeids"].extend(n for n in nodeids if n not in entry["nodeids"])
            if not nodeids:
                entry["by_hand"] = True
    for entry in out.values():
        found = [readings[n] for n in entry["nodeids"] if n in readings]
        if entry["by_hand"]:
            found.append({"result": "inconclusive"})   # a row with no check cannot say it passes
        entry["result"] = checks.overall(found)
    return out


def decide(result: str, status: str, newest: dict | None, fixed_at: str | None) -> str | None:
    """Which verdict this report is owed, or None."""
    status = str(status or "").lower()
    last = (newest or {}).get("verdict")
    if result == "inconclusive" or status in REJECTED:
        return None
    if result == "pass":
        return None if last == "pass" else "pass"
    if status not in FIX_CLAIMED and last != "pass":
        return None   # filed and failing: we said that when we filed it
    if last == "fail" and not (fixed_at and str(fixed_at) > str((newest or {}).get("at") or "")):
        return None
    return "fail"


def their_last_word(client, report_id) -> dict | None:
    """The newest verification on their server: {verdict, at}, or None when it holds none."""
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        try:
            response = client.get(f"/api/v1/bounty/reports/{report_id}/verifications")
        except Exception as exc:  # noqa: BLE001
            raise Unread(f"{type(exc).__name__}: {exc}") from exc
    finally:
        CURRENT_TIER.reset(token)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise Unread(f"HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise Unread("not JSON") from exc
    rows = (body.get("verifications") if isinstance(body, dict) else body) or []

    def rank(row: dict) -> tuple:
        raw = str(row.get("id") or "")
        return (str(row.get("created_at") or ""), int(raw) if raw.isdigit() else -1)

    if not rows:
        return None
    newest = max(rows, key=rank)
    return {"verdict": newest.get("verdict"), "at": newest.get("created_at")}


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------
def _fingerprint(nodeids: list[str]) -> str:
    """sha256 of the test file(s) behind the verdict."""
    digest = hashlib.sha256()
    for name in sorted({n.split("::")[0] for n in nodeids}):
        path = REPO_ROOT / name
        digest.update(path.read_bytes() if path.exists() else name.encode())
    return digest.hexdigest()


def _head() -> str:
    done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def _shown(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)[:240]


def _evidence(verdict: str, nodeids: list[str], readings: dict) -> str:
    """What we say: which check, and on a fail what it read. Their field holds EVIDENCE_LIMIT characters."""
    head = ("VERDICT pass -- the check that recorded this defect now passes." if verdict == "pass" else
            "VERDICT fail -- the check that recorded this defect fails. Our reading is below.")
    checks_line = "CHECK(S):\n" + "\n".join(f"  {n}" for n in nodeids)

    def text(cap: int) -> str:
        parts = ["Independent re-check by the QA agent for hunter expire76.", head]
        if verdict == "fail":
            for nodeid in nodeids:
                reading = readings.get(nodeid) or {}
                if reading.get("result") != "fail":
                    continue
                reason = str(reading.get("reason") or "").strip()
                if len(reason) > cap:
                    reason = reason[:cap].rstrip() + " [...]"
                parts.append(f"WHAT FAILED:\n  {nodeid}\n  expected: {_shown(reading.get('right'))}; "
                             f"read: {_shown(reading.get('left'))}\n  {reason}")
        parts.append(checks_line)
        return "\n\n".join(parts)

    for cap in (3000, 1500, 700, 300, 100, 0):
        evidence = text(cap)
        if len(evidence) <= EVIDENCE_LIMIT:
            return evidence
    return evidence[:EVIDENCE_LIMIT]


def payload(verdict: str, report_id, nodeids: list[str], readings: dict, run_file: str) -> dict:
    return {"verdict": verdict, "test_run_id": run_file or "no-run", "fingerprint": _fingerprint(nodeids),
            "tree_sha": _head(), "checked_at": _now(), "evidence": _evidence(verdict, nodeids, readings)}


def _server_id(body) -> object:
    """2xx and an id from their server, or it is not a created verification."""
    if not isinstance(body, dict) or body.get("success") is False:
        return None
    nested = body.get("verification")
    if isinstance(nested, dict) and nested.get("id") is not None:
        return nested["id"]
    return body.get("verification_id") or body.get("id")


def send_verdict(client, report_id, verdict: str, nodeids: list[str], readings: dict, run_file: str) -> str:
    """POST one verdict. accepted / rejected / unknown; only accepted is written into filed.json."""
    body = payload(verdict, report_id, nodeids, readings, run_file)
    common = {"at": _now(), "by": "agent", "source": SOURCE, "report_id": report_id, "verdict": verdict,
              "run_id": run_file, "fingerprint": body["fingerprint"], "tree_sha": body["tree_sha"]}
    append_event({**common, "type": "verification_intent"})
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(f"/api/v1/bounty/reports/{report_id}/verification", json=body)
    except Exception as exc:  # noqa: BLE001
        append_event({**common, "type": "verification_outcome", "at": _now(), "outcome": "unknown",
                      "reason": f"{type(exc).__name__}: {exc}"})
        return "unknown"
    finally:
        CURRENT_TIER.reset(token)

    try:
        answer = response.json()
    except ValueError:
        answer = None
    status = response.status_code
    outcome = ("accepted" if 200 <= status < 300 and _server_id(answer) is not None
               else "rejected" if 400 <= status < 500 else "unknown")
    append_event({**common, "type": "verification_outcome", "at": _now(), "outcome": outcome, "http_status": status})
    if outcome == "accepted":
        filed = load_filed()
        for row in filed["rows"]:
            if report_id in (row.get("report_ids") or []):
                row.setdefault("verdicts_sent", []).append({"report_id": report_id, "verdict": verdict, "at": _now()})
        save_filed(filed)
    return outcome


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------
def _sync_status(rows: list[dict], reports: list[dict]) -> None:
    """Their status into filed.json, and a row for nothing: a report we did not file through here stays out."""
    status = {r.get("id"): r.get("status") for r in reports}
    for row in rows:
        for report_id in row.get("report_ids") or []:
            if report_id in status:
                row.setdefault("their_status", {})[str(report_id)] = status[report_id]


def run_sweep(client, run_checks=checks.run, send: bool = False, everything: bool = False,
              only: list | None = None) -> dict:
    bounty = _bounty()
    ours = bounty.refresh_our_reports(client=client)
    inbox = bounty.fetch_inbox(client=client)
    tracker = ours.get("klass")
    reports = {r.get("id"): r for r in ours.get("reports") or []}

    filed = load_filed()
    if tracker == "ok":
        _sync_status(filed["rows"], list(reports.values()))
        save_filed(filed)

    rows = open_rows(filed["rows"], everything=everything)
    if only:
        rows = [r for r in rows if set(r.get("report_ids") or []) & set(only)]
    nodeids = sorted({n for r in rows for n in r.get("nodeids") or []})
    readings, run_file = run_checks(nodeids) if nodeids else ({}, "")
    grouped = by_report(rows, readings)

    table, due, unread = [], [], []
    for report_id, entry in sorted(grouped.items(), key=lambda kv: str(kv[0])):
        status = (reports.get(report_id) or {}).get("status") or next(
            (r["their_status"].get(str(report_id)) for r in rows if report_id in (r.get("report_ids") or [])), None)
        fixed_at = (reports.get(report_id) or {}).get("fixed_at")
        line = {"report": report_id, "status": status, "result": entry["result"], "keys": entry["rows"],
                "by_hand": entry["by_hand"], "would_send": None}
        # What they hold is read only for what could go out, so a look at the table costs them nothing extra.
        if entry["result"] != "inconclusive" and str(status or "").lower() not in REJECTED and tracker == "ok":
            try:
                newest = their_last_word(client, report_id)
            except Unread as exc:
                unread.append(report_id)
                line["unread"] = str(exc)
            else:
                line["would_send"] = decide(entry["result"], status, newest, fixed_at)
                if line["would_send"]:
                    due.append((report_id, line["would_send"], entry["nodeids"]))
        table.append(line)

    report = {"tracker": tracker, "inbox": inbox, "table": table, "unread": unread,
              "by_hand": [r["report"] for r in table if r["by_hand"]], "sent": [], "held": [], "run": run_file}
    if not send or not due or tracker != "ok":
        return report

    # Rule: the re-check runs immediately before sending, and a verdict goes only if it still says the same.
    batch = due[:MAX_PER_RUN]
    again, again_file = run_checks(sorted({n for _, _, ns in batch for n in ns}))
    for index, (report_id, verdict, node_list) in enumerate(batch):
        now_word = checks.overall([again.get(n) or {"result": "inconclusive"} for n in node_list])
        if {"pass": "pass", "fail": "fail"}.get(now_word) != verdict:
            report["held"].append({"report": report_id, "verdict": verdict, "now": now_word})
            continue
        outcome = send_verdict(client, report_id, verdict, node_list, again, again_file)
        report["sent"].append({"report": report_id, "verdict": verdict, "outcome": outcome})
        if PAUSE_SECONDS and index < len(batch) - 1:
            time.sleep(PAUSE_SECONDS)
    report["not_sent_this_run"] = max(0, len(due) - MAX_PER_RUN)
    return report


def _print(report: dict) -> None:
    inbox = report["inbox"]
    print(f"tracker: {report['tracker']}   a2a inbox: {inbox.get('klass')}, "
          f"{len([m for m in inbox.get('new') or [] if not m.get('auto')])} new from them")
    for message in inbox.get("new") or []:
        if not message.get("auto"):
            first = (message.get("text") or "").strip().splitlines()
            print(f"  >> {message.get('msg_id')}  {(first[0] if first else '')[:100]}")
    print(f"\n{'report':>7}  {'their status':<12} {'our check':<13} action")
    for line in report["table"]:
        action = line["would_send"] and f"owes {line['would_send']}" or ""
        if line.get("unread"):
            action = f"could not read what they hold ({line['unread']})"
        if line["by_hand"]:
            action = "no check: look by hand"
        print(f"{'#' + str(line['report']):>7}  {str(line['status']):<12} {line['result']:<13} {action}")
    words = [line["result"] for line in report["table"]]
    print(f"\n{len(words)} reports: {words.count('fail')} fail, {words.count('pass')} pass, "
          f"{words.count('inconclusive')} inconclusive. Run: {report['run'] or 'none'}")
    if report["tracker"] != "ok":
        print("The tracker could not be read, which is not an empty tracker: nothing is sent on it.")
    for item in report["sent"]:
        print(f"  sent {item['verdict']} on #{item['report']}: {item['outcome']}")
    for item in report["held"]:
        print(f"  held {item['verdict']} on #{item['report']}: the re-check now says {item['now']}")
    if report.get("not_sent_this_run"):
        print(f"  {report['not_sent_this_run']} more owed: run --send again")


def _client():
    install_client_guard()
    load_dotenv()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=60.0)


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(prog="sweep.py", description=__doc__)
    parser.add_argument("--send", action="store_true", help="post the verdicts that are owed")
    parser.add_argument("--all", action="store_true", dest="everything", help="every row, not only the open ones")
    parser.add_argument("--only", type=int, action="append", metavar="REPORT", help="one report id; repeatable")
    args = parser.parse_args(argv)
    client = _client()
    try:
        report = run_sweep(client, send=args.send, everything=args.everything, only=args.only)
    finally:
        client.close()
    _print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
