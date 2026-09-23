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
  * every submission is two journal events, intent before the POST and
    outcome after, so a timeout leaves the text on disk with the id the
    server assigned where one came back. It used to be appended to
    state/submissions.json as well; that file stopped being written when
    filing became two events, ends at #56, and the last read of it was
    deleted on 2026-09-20
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


def evidence_runs(findings: dict, cited: list[str]) -> dict[str, str]:
    """Per finding, the run that last adjudicated its row: its numbers are the
    ones injected into the report and its captures are the evidence the report
    offers "on request" (B4 of the review of 2026-09-23)."""
    rows = {row.get("id"): row for row in findings.get("findings") or []}
    out = {}
    for fid in cited:
        run_id = (((rows.get(fid) or {}).get("check") or {})
                  .get("adjudicated_by") or {}).get("run_id")
        if run_id:
            out[fid] = run_id
    return out


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
        # The row's TITLE is frozen at the measurement that first opened it --
        # deliberately, so a finding keeps describing what was found -- while
        # detail.reason is what the run being cited actually measured. Printing
        # the title here labelled "from the live service" published the old
        # sentence as a current reading: this block was about to tell them "20
        # rows record an award below the minimum, e.g. #67 at low: 1000
        # recorded against 5000-25000" when every amount had been zeroed hours
        # earlier. Exactly the frozen figure this script's contract promises
        # never to send.
        detail = finding.get("detail") or {}
        headline = detail.get("reason") or finding["title"]
        parts.append(f"\n  [{finding['id']}] {headline}")
        for key, value in detail.items():
            if key == "reason":
                continue
            parts.append(f"    {key}: {value}")

    parts.append("\nREPRODUCE:")
    for step in report.get("steps", []):
        parts.append(f"  - {step}")

    checks = sorted({c for f in linked for c in f.get("checks", [])})
    if checks:
        # It named the repository as public and it is not: the vendor is not
        # on it, so the line offered them a door that does not open. What we
        # can actually offer is the evidence itself.
        parts.append("\nAUTOMATED CHECKS (evidence retained; the request and "
                     "response behind each are provided on request):")
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

    Both reads check the STATUS before the body. my-reports answers a bad or
    expired key with 401 and a perfectly parseable {"detail": ...}, so
    `.json().get("reports", [])` returned an empty list, no exception was
    raised, the "refusing to file blind" branch never ran, and the duplicate
    went out. Same shape as the read bounty.py's classify_read exists for: an
    unreadable tracker is byte-for-byte an empty one unless somebody looks at
    the status line.
    """
    def _rows(response, what: str) -> list:
        if response.status_code != 200:
            raise SystemExit(
                f"  ! {what} answered HTTP {response.status_code}, so what is "
                f"already filed cannot be known. Refusing to file blind -- a "
                f"read that failed is not a tracker that is empty."
            )
        body = response.json()
        return body.get("reports") or body.get("data") or []

    titles: set[str] = set()
    try:
        reports = _rows(client.get(ENDPOINT), "the public tracker")
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
                rows = _rows(
                    reader.get("/api/v1/bounty/my-reports",
                               params={"wallet_address": wallet}),
                    "my-reports")
            finally:
                reader.close()
            titles |= {(r.get("title") or "").strip().lower() for r in rows}
        return titles
    except SystemExit:
        # Already said exactly what went wrong, with the status code in it.
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"  ! could not read the tracker first ({exc}); refusing to file blind")
        raise SystemExit(1)


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
            # Which run holds the evidence behind each finding (B4 of the
            # review of 2026-09-23, 3/3): the report promises it "on request",
            # and qa/keepset.py keeps a run's captures only when an event
            # names the run.
            runs = dict(item.get("runs") or {})
            at = _now()
            append_event({
                "type": "filing_intent", "at": at, "by": "agent",
                "source": "scripts/submit.py", "key": key, "intent_at": at,
                "title": payload["title"], "findings": findings, "runs": runs,
            })

            try:
                response = client.post(ENDPOINT, json=payload)
            except Exception as exc:  # noqa: BLE001
                # A timeout on a POST does not mean the server refused it. It
                # means we stopped listening. Record that, and keep going.
                append_event({
                    "type": "filing_outcome", "at": _now(), "by": "agent",
                    "source": "scripts/submit.py", "key": key,
                    "outcome": "unknown", "findings": findings, "runs": runs,
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
                "findings": findings, "runs": runs, "evidence_id": evidence_id,
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

    if response.status_code != 200:
        raise SystemExit(
            f"cannot reconcile: my-reports answered HTTP {response.status_code}. "
            f"A failed read is not an empty tracker -- settling against it "
            f"would record that nothing was filed.\n{response.text[:200]}")

    rows = body.get("reports") or body.get("data") or []
    if not rows:
        raise SystemExit(
            "cannot reconcile: my-reports returned 200 and zero rows. Either "
            "nothing was ever filed from this wallet, or the wrong wallet was "
            "asked about -- neither is a reason to settle an outcome.")

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
        # TRUSTED, not anon. my-reports requires authentication; with the
        # anonymous identity it answers 401, the body carries no `reports`
        # key, rows read as empty, and --reconcile reported "reconciled 0"
        # while having read nothing at all. That is the failure this whole
        # repository exists to stop, sitting in the one path whose job is to
        # repair a lost response.
        client = build_client(identities()["trusted"], EndpointRegistry.load(),
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
            cited = [r["findings"] for r in reports if r["key"] == key][0]
            items.append({"key": key, "payload": payload, "findings": cited,
                          "runs": evidence_runs(findings, cited)})

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
