"""File one bug to the Cymetica bounty API with one command.

    python scripts/submit.py <key>              run its check, file it, record it
    python scripts/submit.py <key> --dry-run    show what would go; nothing is sent
    python scripts/submit.py <key> --force      file even though the check passes, could not measure, or a report exists

The bug is written in outbox/reports.yaml under `key`; `check:` names the pytest check behind it, if there is one.
A check that passes stops the filing (the bug is gone), and so does one that could not measure: an inconclusive
is never a defect. A bug already filed is not filed twice, by its key, its findings, its check, or a title on their
tracker: a recurrence is reopened by a fail verdict from sweep.py. A report marked `withdrawn` stays withdrawn.

Filing is anonymous by design; reading our own pending reports needs the key. Both reads check the status first:
an unreadable tracker is byte for byte an empty one unless somebody looks at the status line.
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import httpx  # noqa: E402
import yaml  # noqa: E402

from qa import checks  # noqa: E402
from qa.client import build_client, install_client_guard, never_left  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.paths import append_event, load_filed, read_events, updating_filed  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

SPEC = REPO_ROOT / "outbox" / "reports.yaml"
ENDPOINT = "/api/v1/bounty/reports"
SOURCE = "scripts/submit.py"

SEVERITIES = {"critical", "high", "medium", "low", "suggestion"}
CATEGORIES = {"security", "smart_contract", "api", "ui_ux", "logic",
              "performance", "documentation", "compatibility"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def wrap(text: str, width: int = 78) -> str:
    """Collapse YAML folding, then rewrap. Their form is a plain textarea."""
    return "\n".join(textwrap.fill(" ".join(para.split()), width, break_long_words=False, break_on_hyphens=False)
                     for para in text.strip().split("\n\n"))


def nodeids_of(report: dict, rows: list[dict]) -> list[str]:
    """The check(s) behind this bug: its own `check:`, or those of the filed rows its `findings` name."""
    named = report.get("check")
    if named:
        return [named] if isinstance(named, str) else list(named)
    wanted = set(report.get("findings") or [])
    return [n for row in rows if row.get("key") in wanted for n in row.get("nodeids") or []]


def already_filed(report: dict, rows: list[dict]) -> list:
    """Report ids this bug already holds, by its key, its findings or its check: fresh wording on a check already
    filed is the same bug. [operator 2026-10-07] "mas otevrit stary bug kdyz je stejne"."""
    wanted = {report.get("key"), *(report.get("findings") or [])}
    named = set(nodeids_of({"check": report.get("check")}, []))

    def same(row: dict) -> bool:
        return row.get("key") in wanted or (not row.get("withdrawn") and bool(named & set(row.get("nodeids") or [])))

    return [i for row in rows if same(row) for i in row.get("report_ids") or []]


def refusal(readings: dict, force: bool) -> str | None:
    """Why the check stops this filing, or None."""
    if force or not readings:
        return None
    word = checks.overall(list(readings.values()))
    if word == "fail":
        return None
    why = "; ".join(r.get("reason") or "" for r in readings.values() if r.get("result") != "pass")
    return (f"the check passes, so there is no bug to report" if word == "pass"
            else f"the check could not measure, and an inconclusive is never a defect: {why[:300]}")


def compose(report: dict, footer: str, readings: dict) -> dict:
    """Build one submission: what we wrote, and what a failing check read just now. Only a failure is a reading:
    a crash, a timeout or a gone check is ours, and is not called measured."""
    parts = [wrap(report["body"])]
    failing = {n: r for n, r in readings.items() if r.get("result") == "fail"}
    if failing:
        parts.append("\nMEASURED VALUES (from the live service):")
        for nodeid, reading in failing.items():
            parts.append(f"\n  [{nodeid}] {reading.get('reason') or ''}")
            for key in ("left", "right"):
                if reading.get(key) is not None:
                    parts.append(f"    {key}: {reading[key]}")
    parts.append("\nREPRODUCE:")
    parts.extend(f"  - {step}" for step in report.get("steps", []))
    parts.append("\n" + wrap(footer))
    return {
        "title": report["title"].strip(),
        "description": "\n".join(parts),
        "severity_reported": report["severity"],
        "category": report["category"],
        "steps_to_reproduce": "\n".join(report.get("steps", [])),
        "expected_behavior": wrap(report["expected"]),
        "actual_behavior": wrap(report["actual"]),
        "url": report.get("url", "https://cymetica.com"),
        "hunter_name": os.environ.get("QA_HUNTER_NAME", ""),
        "wallet_address": os.environ.get("QA_WALLET_ADDRESS", ""),
    }


def validate(payload: dict, key: str) -> None:
    title = payload["title"]
    if not 10 <= len(title) <= 200:
        raise SystemExit(f"{key}: title is {len(title)} chars, must be 10-200")
    if len(payload["description"]) < 50:
        raise SystemExit(f"{key}: description under 50 chars")
    if payload["severity_reported"] not in SEVERITIES:
        raise SystemExit(f"{key}: severity {payload['severity_reported']!r} not in {SEVERITIES}")
    if payload["category"] not in CATEGORIES:
        raise SystemExit(f"{key}: category {payload['category']!r} not in {CATEGORIES}")
    if not payload["wallet_address"]:
        raise SystemExit(f"{key}: no wallet_address, so the report cannot accrue to the hunter. "
                         f"Set QA_WALLET_ADDRESS in .env.")


def _rows(response, what: str) -> list:
    if response.status_code != 200:
        raise SystemExit(f"{what} answered HTTP {response.status_code}, so what is already filed cannot be "
                         f"known. Refusing to file blind: a read that failed is not a tracker that is empty.")
    try:
        body = response.json()
    except ValueError:
        body = None
    if not isinstance(body, dict) or not {"reports", "data"} & set(body):
        raise SystemExit(f"{what} answered 200 with no list of reports, so what is already filed cannot be known. "
                         f"Refusing to file blind.")
    return body.get("reports") or body.get("data") or []


def on_their_tracker(client) -> dict[str, object]:
    """Title (lower case) -> report id, for our own reports including the pending ones."""
    wallet = os.environ.get("QA_WALLET_ADDRESS", "")
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        try:
            rows = _rows(client.get("/api/v1/bounty/my-reports", params={"wallet_address": wallet}), "my-reports")
        except httpx.HTTPError as exc:
            raise SystemExit(f"could not read the tracker ({type(exc).__name__}); refusing to file blind") from exc
    finally:
        CURRENT_TIER.reset(token)
    return {(r.get("title") or "").strip().lower(): r.get("id") for r in rows}


def _record(report: dict, report_id, nodeids: list[str]) -> None:
    with updating_filed() as filed:
        if any(report_id in (r.get("report_ids") or []) for r in filed["rows"]):
            return
        filed["rows"].append({"key": report["key"], "nodeids": list(nodeids), "report_ids": [report_id],
                              "title": report["title"].strip(), "filed_at": _now(), "verdicts_sent": [],
                              "their_status": {str(report_id): "pending"}, "withdrawn": False})


def _report_id(body):
    if not isinstance(body, dict):
        return None
    return body.get("report_id") or body.get("id") or (body.get("report") or {}).get("id")


def outcome_of(status: int, report_id) -> str:
    """accepted needs 2xx and an id from their server. A 4xx without an id is their refusal."""
    if 200 <= status < 300 and report_id is not None:
        return "accepted"
    if status == 409 or (400 <= status < 500 and report_id is None):
        return "rejected"
    return "unknown"


def file_report(client, report: dict, footer: str, nodeids: list[str], readings: dict, reader=None) -> dict:
    """POST one bug unless their tracker already holds its title. Intent before the POST, outcome after."""
    key = report["key"]
    payload = compose(report, footer, readings)
    validate(payload, key)

    # An earlier try may have landed under the title it had then: their 409 only catches a retry that keeps it.
    earlier = [str(e.get("title") or "").strip().lower() for e in read_events()
               if e.get("type") == "filing_intent" and e.get("key") == key]
    tracker = on_their_tracker(reader or client)
    existing = next((tracker[t] for t in (payload["title"].lower(), *earlier) if t in tracker), None)
    if existing is not None:
        _record(report, existing, nodeids)   # a lost answer: their tracker holds it, so we hold it now too
        if earlier:
            append_event({"type": "filing_outcome", "at": _now(), "by": "agent", "source": SOURCE, "key": key,
                          "outcome": "accepted", "report_id": existing, "reconciled_from": "my-reports"})
        return {"key": key, "outcome": "already filed", "report_id": existing}

    append_event({"type": "filing_intent", "at": _now(), "by": "agent", "source": SOURCE, "key": key,
                  "title": payload["title"], "nodeids": nodeids})
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(ENDPOINT, json=payload)
    except Exception as exc:  # noqa: BLE001
        # A timeout means we stopped listening, not that they refused. Only what cannot have left is not_sent.
        outcome = "not_sent" if never_left(exc) else "unknown"
        append_event({"type": "filing_outcome", "at": _now(), "by": "agent", "source": SOURCE, "key": key,
                      "outcome": outcome, "reason": f"{type(exc).__name__}: {exc}"})
        return {"key": key, "outcome": outcome, "report_id": None, "error": str(exc)}
    finally:
        CURRENT_TIER.reset(token)

    try:
        body = response.json()
    except ValueError:
        body = {}
    report_id = _report_id(body)
    outcome = outcome_of(response.status_code, report_id)
    append_event({"type": "filing_outcome", "at": _now(), "by": "agent", "source": SOURCE, "key": key,
                  "outcome": outcome, "report_id": report_id, "http_status": response.status_code})
    if outcome == "accepted":
        _record(report, report_id, nodeids)
    return {"key": key, "outcome": outcome, "report_id": report_id}


def _clients():
    """(the anonymous client that files, the keyed client that reads our own reports)."""
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    ids = identities()
    # A POST that creates a record is slower than a read: 30 s once dropped an answer the server had accepted.
    return (build_client(ids["anon"], registry, timeout=60.0),
            build_client(ids["trusted"] if ids["trusted"].present else ids["anon"], registry, timeout=60.0))


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(prog="submit.py", description=__doc__)
    parser.add_argument("key", help="the report's key in outbox/reports.yaml")
    parser.add_argument("--dry-run", action="store_true", help="show what would go; nothing is sent")
    parser.add_argument("--force", action="store_true",
                        help="file even if the check passes, could not measure, or a report already exists")
    args = parser.parse_args(argv)

    load_dotenv()
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    report = next((r for r in spec["reports"] if r.get("key") == args.key), None)
    if report is None:
        raise SystemExit(f"no report with key {args.key!r} in {SPEC.name}")
    rows = load_filed()["rows"]

    held = already_filed(report, rows)
    if args.dry_run:
        print(compose(report, spec["footer"], {})["description"])
        print(f"\n{'already filed as ' + ', '.join(f'#{i}' for i in held) if held else 'not filed yet'}. Nothing sent.")
        return 0
    if report.get("withdrawn") and not args.force:
        print(f"not filed: this report is withdrawn ({report['withdrawn']}). --force overrides.")
        return 0
    if held and not args.force:
        print(f"already filed as {', '.join(f'#{i}' for i in held)}. A recurrence is reopened by a fail verdict "
              f"(scripts/sweep.py --send), not by a new report; --force files anew, for a row we withdrew or they "
              f"rejected, where no verdict can go.")
        return 0

    nodeids = nodeids_of(report, rows)
    try:
        readings = checks.run(nodeids)[0] if nodeids else {}
    except checks.CannotRun as exc:
        print(f"not filed: {exc}")
        return 1
    why = refusal(readings, args.force)
    if why:
        print(f"not filed: {why}. --force overrides.")
        return 1

    client, reader = _clients()
    try:
        result = file_report(client, report, spec["footer"], nodeids, readings, reader=reader)
    finally:
        client.close()
        reader.close()
    print(f"{result['outcome']}: {args.key}" + (f" as #{result['report_id']}" if result.get("report_id") else ""))
    if result["outcome"] == "unknown":
        print("  it may have landed. Do not re-send blind: the next sweep settles it from their tracker.")
    return 0 if result["outcome"] in ("accepted", "already filed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
