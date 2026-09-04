"""File findings to the Cymetica bounty API.

This is the one write the project performs on purpose, so it is the one script
that needs to be paranoid about what it sends and honest about what came back.

    python scripts/submit.py --dry-run          # print exactly what would go
    python scripts/submit.py --confirm          # actually file
    python scripts/submit.py --confirm --only anon-tool-surface

Guarantees:
  * every NUMBER in a description is injected from state/findings.json at send
    time, so a figure cannot go stale between measuring and reporting it
  * a report whose title already exists in the tracker is skipped, not retried
    (their API answers 409 on a duplicate title within 24h; better not to ask)
  * the rate-limit budget is read from the response headers and the run stops
    before exhausting it -- the vendor said 20/hour, the header advertises 60,
    and that is unresolved, so we use the smaller number
  * every submission is appended to state/submissions.json with the id the
    server assigned, which is what later lets us poll for status changes
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

import os  # noqa: E402

SPEC = REPO_ROOT / "outbox" / "reports.yaml"
FINDINGS = REPO_ROOT / "state" / "findings.json"
SUBMISSIONS = REPO_ROOT / "state" / "submissions.json"

ENDPOINT = "/api/v1/bounty/reports"
# The vendor said 20 reports/hour (ET-21999); the response header advertises
# x-ratelimit-limit: 60. Unresolved, so assume the stricter of the two.
MAX_PER_RUN = 12
PAUSE_SECONDS = 4

SEVERITIES = {"critical", "high", "medium", "low", "suggestion"}
CATEGORIES = {"security", "smart_contract", "api", "ui_ux", "logic",
              "performance", "documentation", "compatibility"}


def wrap(text: str, width: int = 78) -> str:
    """Collapse YAML folding, then rewrap. Their form is a plain textarea."""
    import textwrap
    return "\n".join(
        textwrap.fill(" ".join(para.split()), width)
        for para in text.strip().split("\n\n")
    )


def compose(report: dict, findings: dict, footer: str) -> dict:
    """Build one submission. Numbers come from the findings file, never typed."""
    by_id = {f["id"]: f for f in findings["findings"]}
    linked = [by_id[i] for i in report["findings"] if i in by_id]
    missing = [i for i in report["findings"] if i not in by_id]
    if missing:
        raise SystemExit(
            f"{report['key']}: findings {missing} are not in state/findings.json. "
            f"Re-run scripts/findings.py, or the report would cite figures that "
            f"no longer exist."
        )

    parts = [wrap(report["body"])]

    parts.append("\nMEASURED VALUES (from the live service):")
    for finding in linked:
        parts.append(f"\n  [{finding['id']}] {finding['title']}")
        for key, value in (finding.get("detail") or {}).items():
            parts.append(f"    {key}: {value}")

    parts.append("\nREPRODUCE:")
    for step in report.get("steps", []):
        parts.append(f"  - {step}")

    checks = sorted({c for f in linked for c in f.get("checks", [])})
    if checks:
        parts.append("\nAUTOMATED CHECKS (public repo: github.com/zakutana/qa-cymetica):")
        for check in checks:
            parts.append(f"  {check}")

    parts.append("\n" + wrap(footer))

    description = "\n".join(parts)

    return {
        "title": report["title"].strip(),
        "description": description,
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
        raise SystemExit(
            f"{key}: no wallet_address. Per ET-21999 the hunter profile is keyed "
            f"to it -- filing without one cannot accrue to the profile. Set "
            f"QA_WALLET_ADDRESS in .env."
        )


def existing_titles(client) -> set[str]:
    """Titles already on the server, so a retry never files a duplicate.

    The public list alone is not enough: it hides pending reports, so a report
    whose POST response was lost to a timeout would be invisible here and only
    the server's 409 would stop the retry. Our own pending reports live behind
    my-reports, keyed by wallet -- read both.
    """
    titles: set[str] = set()
    try:
        reports = client.get(ENDPOINT).json().get("reports", [])
        titles |= {(r.get("title") or "").strip().lower() for r in reports}
        wallet = os.environ.get("QA_WALLET_ADDRESS", "")
        if wallet:
            # Filing is anonymous by design, but READING our own pending
            # reports is not: my-reports answers the credentialed caller. The
            # first version of this read used the anonymous filing client and
            # silently saw nothing, so two retries reached the server's 409
            # instead of being stopped here. Read with the key.
            ids = identities()
            reader = build_client(
                ids["trusted"] if ids["trusted"].present else ids["anon"],
                client._transport.registry, timeout=40.0,
            )
            try:
                mine = reader.get("/api/v1/bounty/my-reports",
                                  params={"wallet_address": wallet}).json()
            finally:
                reader.close()
            rows = mine.get("reports") or mine.get("data") or []
            titles |= {(r.get("title") or "").strip().lower() for r in rows}
        return titles
    except Exception as exc:  # noqa: BLE001
        print(f"  ! could not read the tracker first ({exc}); refusing to file blind")
        raise SystemExit(1)


def load_submissions() -> dict:
    if SUBMISSIONS.exists():
        return json.loads(SUBMISSIONS.read_text(encoding="utf-8"))
    return {"submissions": []}


def save_submission(record: dict) -> None:
    data = load_submissions()
    data["submissions"].append(record)
    data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    SUBMISSIONS.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true",
                        help="actually file. Without it nothing is sent.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", action="append", metavar="KEY")
    args = parser.parse_args()

    if not (args.confirm or args.dry_run):
        parser.error("pass --dry-run to preview or --confirm to file")

    load_dotenv()
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    findings = json.loads(FINDINGS.read_text(encoding="utf-8"))

    reports = spec["reports"]
    if args.only:
        reports = [r for r in reports if r["key"] in args.only]
        if not reports:
            raise SystemExit(f"no report matches {args.only}")

    payloads = []
    for report in reports:
        payload = compose(report, findings, spec["footer"])
        validate(payload, report["key"])
        payloads.append((report["key"], payload))

    if args.dry_run:
        for key, payload in payloads:
            print("=" * 78)
            print(f"{key}   [{payload['severity_reported']} / {payload['category']}]")
            print("=" * 78)
            print(f"TITLE ({len(payload['title'])} chars): {payload['title']}\n")
            print(payload["description"])
            print(f"\nwallet_address: {payload['wallet_address']}")
            print(f"hunter_name:    {payload['hunter_name']}")
            print()
        print(f"{len(payloads)} reports composed. Nothing sent (--dry-run).")
        return

    if len(payloads) > MAX_PER_RUN:
        raise SystemExit(f"{len(payloads)} reports exceeds the {MAX_PER_RUN} per-run cap")

    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        # A POST that creates a record is slower than a read; 30s dropped one
        # response out of eleven today, after the server had already accepted
        # it. The write itself is idempotent on our side because of the title
        # check above, so the only cost of a longer wait is waiting.
        client = build_client(identities()["anon"], registry, timeout=60.0)
        try:
            seen = existing_titles(client)
            print(f"tracker currently holds {len(seen)} reports\n")

            for key, payload in payloads:
                if payload["title"].strip().lower() in seen:
                    print(f"  SKIP  {key}: a report with this title already exists")
                    continue

                response = client.post(ENDPOINT, json=payload)
                remaining = response.headers.get("x-ratelimit-remaining")
                ok = 200 <= response.status_code < 300

                try:
                    body = response.json()
                except Exception:  # noqa: BLE001
                    body = {"raw": response.text[:300]}

                # The server answers {"success": true, "report_id": N, ...}.
                report_id = (body.get("report_id") or body.get("id")
                             or (body.get("report") or {}).get("id"))
                status = "OK  " if ok else "FAIL"
                print(f"  {status}  {key}: HTTP {response.status_code}"
                      f"{f'  id={report_id}' if report_id else ''}"
                      f"  (rate-limit remaining {remaining})")
                if not ok:
                    print(f"        {json.dumps(body)[:400]}")

                save_submission({
                    "key": key,
                    "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "http_status": response.status_code,
                    "report_id": report_id,
                    "title": payload["title"],
                    "severity_reported": payload["severity_reported"],
                    "category": payload["category"],
                    "findings": [r["findings"] for r in reports if r["key"] == key][0],
                    "wallet_address": payload["wallet_address"],
                    "response": body,
                })

                if remaining is not None and int(remaining) < 10:
                    print("  stopping: rate-limit budget nearly exhausted")
                    break
                time.sleep(PAUSE_SECONDS)
        finally:
            client.close()
    finally:
        CURRENT_TIER.reset(token)

    print(f"\n-> {SUBMISSIONS.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
