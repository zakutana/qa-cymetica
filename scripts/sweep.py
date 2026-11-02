"""Where every bug we filed stands, and with --send tell them what our checks found.

    python scripts/sweep.py                 read their tracker and inbox, run the checks of open reports, print the table
    python scripts/sweep.py --all           every report, and also every vendor check no filed bug holds
    python scripts/sweep.py --send          also post the verdicts
    python scripts/sweep.py --only 7        just these reports, closed or not; repeatable

Open means: not withdrawn, not rejected by them, and we have not told them it passes (or it failed since). A verdict
is per report and rests on every check of that report. `pass` goes when all of them pass and our last word was not a
pass. `fail` goes when one fails and they claim a fix (their status says fixed or paid) or we told them it passed,
unless our last fail is newer than their last claim. A row whose `hold` says why (the operator's word is awaited)
sends nothing.

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
from qa.channels import FIX_CLAIMED, REJECTED, decide, last_verdict  # noqa: E402,F401
from qa.client import build_client, install_client_guard, never_left  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.paths import append_event, load_filed, read_events, updating_filed  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

SOURCE = "scripts/sweep.py"
# They said 20 reports an hour; the header says 60. The smaller number, as in filing.
MAX_PER_RUN = 12
PAUSE_SECONDS = 4
# Their `evidence` field holds 8000 characters (422 on #130).
EVIDENCE_LIMIT = 8000


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
def _is_rejected(row: dict, report_id) -> bool:
    return str((row.get("their_status") or {}).get(str(report_id)) or "").lower() in REJECTED


def _closed(row: dict) -> bool:
    """We told them it passes (or they rejected the report), and the last time we looked it still did."""
    ids = row.get("report_ids") or []
    return (bool(ids) and row.get("last_check") != "fail"
            and all(_is_rejected(row, i) or last_verdict(row, i) == "pass" for i in ids))


def _rejected(row: dict) -> bool:
    ids = row.get("report_ids") or []
    return bool(ids) and all(_is_rejected(row, i) for i in ids)


def open_rows(rows: list[dict], everything: bool = False) -> list[dict]:
    live = [r for r in rows if not r.get("withdrawn")]
    return live if everything else [r for r in live if not _closed(r) and not _rejected(r)]


def chosen(rows: list[dict], everything: bool, only: list | None) -> tuple[set, list[dict]]:
    """Which reports this pass is about, and every live row of each: closed rows too, since a verdict is per
    report and a pass may rest only on all of its checks."""
    wanted = set(only) if only else {i for r in open_rows(rows, everything) for i in r.get("report_ids") or []}
    return wanted, [r for r in rows if not r.get("withdrawn") and wanted & set(r.get("report_ids") or [])]


def by_report(rows: list[dict], readings: dict[str, dict]) -> dict:
    """One result per report: several rows can share one, and it passes only when all of them do."""
    out: dict = {}
    for row in rows:
        for report_id in row.get("report_ids") or []:
            entry = out.setdefault(report_id, {"nodeids": [], "rows": [], "by_hand": False, "hold": None})
            entry["rows"].append(row["key"])
            nodeids = row.get("nodeids") or []
            entry["nodeids"].extend(n for n in nodeids if n not in entry["nodeids"])
            entry["hold"] = entry["hold"] or row.get("hold")
            if not nodeids:
                entry["by_hand"] = True
    for entry in out.values():
        found = [readings[n] for n in entry["nodeids"] if n in readings]
        if entry["by_hand"]:
            found.append({"result": "inconclusive"})   # a row with no check cannot say it passes
        entry["result"] = checks.overall(found)
    return out


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
    head = ("VERDICT pass -- the check we hold for this defect passes now. It may have been repaired since the defect "
            "was recorded, so this does not say it is the identical test." if verdict == "pass" else
            "VERDICT fail -- the check we hold for this defect fails. Our reading is below.")
    tail = ("CHECK(S):\n" + "\n".join(f"  {n}" for n in nodeids) + "\n\nFINGERPRINT: a SHA-256 of the test file(s). "
            "The formula changed on 2026-11-02, so a value that differs from one we sent before does not by itself "
            "mean the check moved.")

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
        parts.append(tail)
        return "\n\n".join(parts)

    for cap in (3000, 1500, 700, 300, 100, 0):
        evidence = text(cap)
        if len(evidence) <= EVIDENCE_LIMIT:
            return evidence
    return evidence[:EVIDENCE_LIMIT]


def payload(verdict: str, nodeids: list[str], readings: dict, run_file: str) -> dict:
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


def _remember(report_id, verdict: str, at: str) -> None:
    """Into filed.json, on every row that holds the report."""
    with updating_filed() as filed:
        for row in filed["rows"]:
            if report_id in (row.get("report_ids") or []) and last_verdict(row, report_id) != verdict:
                row.setdefault("verdicts_sent", []).append({"report_id": report_id, "verdict": verdict, "at": at})


def send_verdict(client, report_id, verdict: str, nodeids: list[str], readings: dict, run_file: str) -> str:
    """POST one verdict. accepted / rejected / unknown / not_sent; only accepted is written into filed.json."""
    body = payload(verdict, nodeids, readings, run_file)
    common = {"at": _now(), "by": "agent", "source": SOURCE, "report_id": report_id, "verdict": verdict,
              "run_id": run_file, "fingerprint": body["fingerprint"], "tree_sha": body["tree_sha"]}
    append_event({**common, "type": "verification_intent"})
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(f"/api/v1/bounty/reports/{report_id}/verification", json=body)
    except Exception as exc:  # noqa: BLE001
        outcome = "not_sent" if never_left(exc) else "unknown"
        append_event({**common, "type": "verification_outcome", "at": _now(), "outcome": outcome,
                      "reason": f"{type(exc).__name__}: {exc}"})
        return outcome
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
        _remember(report_id, verdict, _now())
    return outcome


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------
def _sync_status(rows: list[dict], reports: list[dict]) -> None:
    """Their status into filed.json. A tracker report no row holds stays out: not every one was filed through here."""
    status = {r.get("id"): r.get("status") for r in reports}
    for row in rows:
        for report_id in row.get("report_ids") or []:
            if report_id in status:
                row.setdefault("their_status", {})[str(report_id)] = status[report_id]


def _settle_filings(rows: list[dict], reports: list[dict]) -> list[str]:
    """A filing whose answer was lost: their tracker holding its title makes it a row. Returns the keys still
    unknown, so nobody has to remember them."""
    open_filings: dict = {}
    for event in read_events():
        if event.get("type") == "filing_intent":
            open_filings[event.get("key")] = event
        elif event.get("type") == "filing_outcome" and event.get("outcome") in ("accepted", "rejected", "not_sent"):
            open_filings.pop(event.get("key"), None)
    titles = {str(r.get("title") or "").strip().lower(): r for r in reports}
    unsettled = []
    for key, intent in open_filings.items():
        report = titles.get(str(intent.get("title") or "").strip().lower())
        if report is None:
            unsettled.append(key)
            continue
        report_id = report.get("id")
        if not any(report_id in (r.get("report_ids") or []) for r in rows):
            rows.append({"key": key, "nodeids": list(intent.get("nodeids") or []), "report_ids": [report_id],
                         "title": intent.get("title"), "filed_at": intent.get("at"), "verdicts_sent": [],
                         "their_status": {str(report_id): report.get("status")}, "withdrawn": False})
        append_event({"type": "filing_outcome", "at": _now(), "by": "agent", "source": SOURCE, "key": key,
                      "outcome": "accepted", "report_id": report_id, "reconciled_from": "my-reports"})
    return unsettled


def run_sweep(client, run_checks=checks.run, vendor_checks=checks.vendor_checks, send: bool = False,
              everything: bool = False, only: list | None = None) -> dict:
    bounty = _bounty()
    ours = bounty.refresh_our_reports(client=client)
    inbox = bounty.fetch_inbox(client=client)
    tracker = ours.get("klass")
    reports = {r.get("id"): r for r in ours.get("reports") or []}

    unsettled: list[str] = []
    if tracker == "ok":
        with updating_filed() as filed:
            unsettled = _settle_filings(filed["rows"], list(reports.values()))
            _sync_status(filed["rows"], list(reports.values()))
    wanted, rows = chosen(load_filed()["rows"], everything, only)

    nodeids = sorted({n for r in rows for n in r.get("nodeids") or []})
    extra = [n for n in vendor_checks() if n not in set(nodeids)] if everything and not only else []
    readings, run_file = run_checks(nodeids + extra) if nodeids or extra else ({}, "")
    grouped = {report_id: entry for report_id, entry in by_report(rows, readings).items() if report_id in wanted}

    # The last conclusive word: one 503 must not make us forget a failure.
    with updating_filed() as filed:
        for row in filed["rows"]:
            found = [readings[n] for n in row.get("nodeids") or [] if n in readings]
            word = checks.overall(found)
            if found and word != "inconclusive":
                row["last_check"] = word

    table, due, unread = [], [], []
    for report_id, entry in sorted(grouped.items(), key=lambda kv: str(kv[0])):
        status = (reports.get(report_id) or {}).get("status") or next(
            (r["their_status"].get(str(report_id)) for r in rows if report_id in (r.get("report_ids") or [])), None)
        fixed_at = (reports.get(report_id) or {}).get("fixed_at")
        line = {"report": report_id, "status": status, "result": entry["result"], "keys": entry["rows"],
                "by_hand": entry["by_hand"], "would_send": None, "held": entry["hold"]}
        # What they hold is read only for what could go out, and it is the authority on what we told them.
        if entry["result"] != "inconclusive" and str(status or "").lower() not in REJECTED and tracker == "ok":
            try:
                newest = their_last_word(client, report_id)
            except Unread as exc:
                unread.append(report_id)
                line["unread"] = str(exc)
            else:
                if newest:
                    _remember(report_id, newest["verdict"], newest["at"])
                verdict = decide(entry["result"], status, newest, fixed_at)
                if verdict and not entry["hold"]:
                    line["would_send"] = verdict
                    due.append((report_id, verdict, entry["nodeids"]))
        table.append(line)

    report = {"tracker": tracker, "inbox": inbox, "table": table, "unread": unread,
              "by_hand": [r["report"] for r in table if r["by_hand"]], "sent": [], "held": [], "run": run_file,
              "unfiled": [n for n in extra if (readings.get(n) or {}).get("result") == "fail"],
              "unsettled": unsettled}
    if not send or not due or tracker != "ok":
        return report

    # Rule: the re-check runs immediately before sending, and a verdict goes only if it still says the same.
    batch = due[:MAX_PER_RUN]
    again, again_file = run_checks(sorted({n for _, _, ns in batch for n in ns}))
    for index, (report_id, verdict, node_list) in enumerate(batch):
        now_word = checks.overall([again.get(n) or {"result": "inconclusive"} for n in node_list])
        if now_word != verdict:
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
          f"{len([m for m in inbox.get('new') or [] if not m.get('auto')])} new from them"
          + ("  (the page is full: older messages may not have been read)" if inbox.get("full") else ""))
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
        if line.get("held"):
            action = f"held: {line['held']}"
        print(f"{'#' + str(line['report']):>7}  {str(line['status']):<12} {line['result']:<13} {action}")
    words = [line["result"] for line in report["table"]]
    print(f"\n{len(words)} reports: {words.count('fail')} fail, {words.count('pass')} pass, "
          f"{words.count('inconclusive')} inconclusive. Run: {report['run'] or 'none'}")
    if report["tracker"] != "ok":
        print("The tracker could not be read, which is not an empty tracker: nothing is sent on it.")
    for nodeid in report.get("unfiled") or []:
        print(f"  fails, and no filed bug holds it: {nodeid}")
    for key in report.get("unsettled") or []:
        print(f"  filing {key}: outcome unknown and not on their tracker; run scripts/submit.py {key} once it is clear")
    for item in report["sent"]:
        print(f"  {item['verdict']} on #{item['report']}: {item['outcome']}")
    for item in report["held"]:
        print(f"  held {item['verdict']} on #{item['report']}: the re-check now says {item['now']}")
    if report.get("not_sent_this_run"):
        print(f"  {report['not_sent_this_run']} more owed: run --send again")


def _client(write: bool = False):
    install_client_guard()
    load_dotenv()
    registry = EndpointRegistry.load()
    if write:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=60.0)


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(prog="sweep.py", description=__doc__)
    parser.add_argument("--send", action="store_true", help="post the verdicts that are owed")
    parser.add_argument("--all", action="store_true", dest="everything",
                        help="every report, and every vendor check no filed bug holds")
    parser.add_argument("--only", type=int, action="append", metavar="REPORT", help="one report id; repeatable")
    args = parser.parse_args(argv)
    client = _client(write=args.send)
    try:
        report = run_sweep(client, send=args.send, everything=args.everything, only=args.only)
    except checks.CannotRun as exc:
        print(f"Nothing was measured and nothing sent. {exc}")
        return 1
    finally:
        client.close()
    _print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
