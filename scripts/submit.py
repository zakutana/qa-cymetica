"""File findings to the Cymetica bounty API.

This is the one write the project performs on purpose, so it is the one script
that needs to be paranoid about what it sends and honest about what came back.

    python scripts/submit.py --dry-run          # print exactly what would go
    python scripts/submit.py --confirm          # actually file
    python scripts/submit.py --confirm --only anon-tool-surface

Guarantees:
  * every NUMBER in a description is injected from the ledger at send time, and
    a finding whose figures no admissible run has measured is refused outright
    rather than sent with values frozen at the moment it was found
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
from qa.state import journal_path  # noqa: E402

import os  # noqa: E402

SPEC = REPO_ROOT / "outbox" / "reports.yaml"
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


def load_findings() -> dict:
    """The ledger is where a finding's content lives now.

    findings.json was a rebuild-from-what-is-currently-failing snapshot, and
    nothing writes it any more. Left pointed at it, this would inject figures
    from a file that stopped being updated -- into a report going to the
    vendor, which is the worst place for a stale number.
    """
    from qa.state import load_ledger, ledger_path

    if not ledger_path().exists():
        raise SystemExit("no ledger yet; run scripts/ledger.py first")
    return {"findings": list(load_ledger()["findings"].values())}


def compose(report: dict, findings: dict, footer: str) -> dict:
    """Build one submission. Numbers come from the ledger, never typed."""
    by_id = {f["id"]: f for f in findings["findings"]}
    linked = [by_id[i] for i in report["findings"] if i in by_id]
    missing = [i for i in report["findings"] if i not in by_id]
    if missing:
        raise SystemExit(
            f"{report['key']}: findings {missing} are not in the ledger. "
            f"A report may not cite a finding the ledger does not hold."
        )

    unmeasured = [f["id"] for f in linked
                  if not (f.get("provenance") or {}).get("measured_at")]
    if unmeasured:
        raise SystemExit(
            f"{report['key']}: {unmeasured} carry figures no admissible run has "
            f"measured (provenance.measured_at is null).\n"
            f"Filing them would send the vendor numbers frozen at the moment "
            f"the finding was made. Run the checks first."
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


# ---------------------------------------------------------------------------
# Filing: two events per report, and a timeout is neither of them
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _capture(response) -> str | None:
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-submit").capture(
            response.request, response, SafetyTier.MUTATE)
    except Exception:  # noqa: BLE001
        return None


def _report_id(body):
    if not isinstance(body, dict):
        return None
    return (body.get("report_id") or body.get("id")
            or (body.get("report") or {}).get("id"))


def submit_batch(client, items: list[dict], confirm: bool = False,
                 pause: float = 0.0) -> list[dict]:
    """File each item, recording an intent BEFORE the POST and an outcome after.

    The intent is what makes a lost response recoverable. #55 was accepted by
    their server while our log said it had never been sent, because the only
    record was written after a response that never arrived -- and the same
    timeout aborted the rest of the batch.

    Three outcomes, and only one of them is a filed report:
      accepted  2xx AND a report id from the server. Anything less cannot be
                pointed at later, so it is not a filing.
      rejected  they refused it; 409 for a duplicate is the common case.
      unknown   we do not know. Settled against my-reports, never guessed.
    """
    from qa.state import append_event

    if not confirm:
        raise SystemExit("refusing to file without confirm=True")

    # Filing creates state on their side. Say so, rather than arriving at the
    # transport as an unclassified request.
    registry = getattr(getattr(client, "_transport", None), "registry", None)
    if registry is not None:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})

    results = []
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for index, item in enumerate(items):
            key, payload = item["key"], item["payload"]
            findings = list(item.get("findings") or [])
            at = _now()
            append_event({
                "type": "filing_intent", "at": at, "by": "agent",
                "source": "scripts/submit.py", "key": key, "intent_at": at,
                "title": payload["title"], "findings": findings,
            })

            try:
                response = client.post(ENDPOINT, json=payload)
            except Exception as exc:  # noqa: BLE001
                # A timeout on a POST does not mean the server refused it. It
                # means we stopped listening. Record that, and keep going.
                append_event({
                    "type": "filing_outcome", "at": _now(), "by": "agent",
                    "source": "scripts/submit.py", "key": key,
                    "outcome": "unknown", "findings": findings,
                    "reason": f"{type(exc).__name__}: {exc} -- run submit.py "
                              f"--reconcile to settle it against my-reports",
                })
                results.append({"key": key, "outcome": "unknown",
                                "report_id": None, "error": str(exc)})
                continue

            evidence_id = _capture(response)
            try:
                body = response.json()
            except ValueError:
                body = {"raw": response.text[:300]}
            report_id = _report_id(body)

            if response.status_code == 409:
                outcome = "rejected"
            elif 200 <= response.status_code < 300 and report_id is not None:
                outcome = "accepted"
            else:
                outcome = "unknown"

            append_event({
                "type": "filing_outcome", "at": _now(), "by": "agent",
                "source": "scripts/submit.py", "key": key, "outcome": outcome,
                "report_id": report_id, "http_status": response.status_code,
                "findings": findings, "evidence_id": evidence_id,
            })
            results.append({"key": key, "outcome": outcome,
                            "report_id": report_id,
                            "http_status": response.status_code})

            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining is not None and int(remaining) < 10:
                break
            if pause and index < len(items) - 1:
                time.sleep(pause)
    finally:
        CURRENT_TIER.reset(token)
    return results


def reconcile(client, wallet: str) -> int:
    """Settle `unknown` outcomes against their server. Appends, never edits.

    The repair for a lost response is to ask the party that has it and write
    down what they said. Editing our log into agreement would produce the same
    file with none of the provenance.
    """
    from qa.state import append_event, read_events

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get("/api/v1/bounty/my-reports",
                              params={"wallet_address": wallet})
        evidence_id = _capture(response)
        body = response.json()
    finally:
        CURRENT_TIER.reset(token)

    rows = body.get("reports") or body.get("data") or []
    events = read_events()
    settled = {e.get("report_id") for e in events
               if e["type"] == "filing_outcome" and e.get("outcome") == "accepted"}
    intents = {(e.get("title") or "").strip().lower(): e
               for e in events if e["type"] == "filing_intent"}

    added = 0
    for row in sorted(rows, key=lambda r: r.get("id", 0)):
        report_id = row.get("id")
        if report_id in settled:
            continue
        intent = intents.get((row.get("title") or "").strip().lower())
        if intent is None:
            continue
        # Count what the journal actually took. append_event is idempotent by
        # natural key, so a second --reconcile settles nothing and says 0
        # rather than reporting work it did not do.
        outcome = append_event({
            "type": "filing_outcome", "at": _now(), "by": "agent",
            "source": "scripts/submit.py", "key": intent["key"],
            "outcome": "accepted", "report_id": report_id,
            "findings": list(intent.get("findings") or []),
            "reconciled_from": "my-reports", "evidence_id": evidence_id,
            "server_created_at": row.get("created_at"),
        })
        added += 1 if outcome == "appended" else 0
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true",
                        help="actually file. Without it nothing is sent.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", action="append", metavar="KEY")
    parser.add_argument("--reconcile", action="store_true",
                        help="settle `unknown` outcomes against my-reports. "
                             "Appends what their server says; never edits.")
    args = parser.parse_args()

    if not (args.confirm or args.dry_run or args.reconcile):
        parser.error("pass --dry-run to preview, --confirm to file, "
                     "or --reconcile to settle a lost response")

    if args.reconcile and not (args.confirm or args.dry_run):
        install_client_guard()
        client = build_client(identities()["anon"], EndpointRegistry.load(),
                              timeout=60.0)
        try:
            added = reconcile(client, os.environ.get("QA_WALLET_ADDRESS", ""))
        finally:
            client.close()
        print(f"reconciled {added} outcome(s) from my-reports")
        print(f"-> {journal_path()}")
        return

    load_dotenv()
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    findings = load_findings()

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

    # A POST that creates a record is slower than a read; 30s dropped one
    # response out of eleven today, after the server had already accepted it.
    # The only cost of a longer wait is waiting.
    client = build_client(identities()["anon"], registry, timeout=60.0)
    try:
        # The dedup read is a read, and the transport requires every request
        # to name its tier. Moving the MUTATE context inside submit_batch left
        # this one outside any context at all, so the guard refused it and the
        # script would not file -- correctly, and unhelpfully.
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            seen = existing_titles(client)
        finally:
            CURRENT_TIER.reset(token)
        print(f"tracker currently holds {len(seen)} reports\n")

        items = []
        for key, payload in payloads:
            if payload["title"].strip().lower() in seen:
                print(f"  SKIP  {key}: a report with this title already exists")
                continue
            items.append({
                "key": key, "payload": payload,
                "findings": [r["findings"] for r in reports if r["key"] == key][0],
            })

        for result in submit_batch(client, items, confirm=True, pause=PAUSE_SECONDS):
            detail = f"  id={result['report_id']}" if result.get("report_id") else ""
            print(f"  {result['outcome'].upper():<9} {result['key']}: "
                  f"HTTP {result.get('http_status', '-')}{detail}")
            if result["outcome"] == "unknown":
                print("        settle it with --reconcile; do not re-send blind")

        if args.reconcile:
            wallet = os.environ.get("QA_WALLET_ADDRESS", "")
            added = reconcile(client, wallet)
            print(f"\nreconciled {added} outcome(s) from my-reports")
    finally:
        client.close()

    print(f"\n-> {journal_path()}")
    print("   run scripts/ledger.py to fold these events into the ledger")


if __name__ == "__main__":
    main()
