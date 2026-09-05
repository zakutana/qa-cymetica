"""One-shot: rebuild state/ under the contract, without re-deriving history.

The audit found 71 of 109 state changes were produced by our own code
re-deriving what it already knew. The temptation now is to re-derive one more
time -- to reconstruct what each row "should" have been. That would be the
same mistake with better intentions.

So this script COPIES. Every value comes from a named artefact and is stamped
with where it came from:

    state/ledger.json@ca0bc45          the 20 rows' content
    state/submissions.json             11 filings, ids 46-56
    state/bounty.json                  11 vendor statuses
    archive/round-1-2026-09-04/*.md    4 messages, frontmatter verbatim
    scripts/ledger.py@ca0bc45          4 withdrawals, with dates from git
    outbox/reports.yaml                the corrections paragraph in #54

The 13 run records are not touched. The 53 results they hold that say `failed`
because the old recorder resumed before the Inconclusive classifier are
relabelled AT READ TIME (qa/state.py), which is a label on contaminated data
rather than a recomputation of it.

What day one looks like, honestly: 23 rows, every one UNVERIFIED on the CHECK
axis, 10 of them FIX_CLAIMED by the vendor, and zero verified. Not because
nothing was ever fixed, but because no admissible run has adjudicated anything
yet -- all 13 existing run records fail admissibility for a reason each names.
The first clean tagged run will move the rows that genuinely pass.

The 71 historical transitions are NOT reconstructed. They live in the audit,
which is a record of the past; the ledger does not invent events it never saw.

    python scripts/migrate_ledger.py            dry run: prints everything
    python scripts/migrate_ledger.py --confirm  writes the journal and ledger

Rollback:  git checkout ca0bc45 -- state/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from qa.state import append_event, journal_path, read_events, state_dir  # noqa: E402

LEDGER_SHA = "ca0bc45"
ARCHIVE = REPO_ROOT / "archive" / "round-1-2026-09-04"

# The withdrawal dict that used to live at scripts/ledger.py:36-55, with the
# date each id was added to it, recovered from git. A withdrawal nobody can
# date is exactly what this migration exists to stop producing.
WITHDRAWALS = {
    "CYM-mcp_tool_count": (
        "2026-09-04T13:04:22+00:00",
        "Our check asserted the anonymous tool count equals the manifest "
        "total. That held only while tier gating was broken; once it was "
        "fixed, anonymous correctly returns 25 of 46 and our check reported "
        "their fix as a failure. Replaced by tests/mcp/test_trust_ladder.py.",
    ),
    "CYM-chain_count": (
        "2026-09-04T13:04:22+00:00",
        "Our check compared 'settlement on 10 chains' against the 16 chains "
        "/api/v1/swap/chains supports for swaps. Two different mechanisms; "
        "netting them is the collapsed-layer defect we report in others.",
    ),
    "CYM-documented-405": (
        "2026-09-04T13:27:44+00:00",
        "Measured our own probe method, not their contract. The original 18 "
        "were llms.txt rendering MCP tools as GET-able /mcp/v1/tools/<name> "
        "URLs, and those are gone. The 10 that remain are POST-only endpoints "
        "we probed with GET, where 405 is the correct answer.",
    ),
    "CYM-mcp_tool_names_documented_exist": (
        "2026-09-04T13:27:44+00:00",
        "Never a defect. The check is INCONCLUSIVE, not failing: llms.txt no "
        "longer links any tool names, so there is nothing to verify. It "
        "entered the ledger from a run before the claim was rewritten.",
    ),
}

# The CORRECTIONS paragraph in report #54 retracted two of them to the vendor.
RETRACTIONS_SENT = {
    "CYM-chain_count": 52,
    "CYM-mcp_tool_count": 50,
}

# Five rows named a script as their check. pytest does not collect a script,
# so they sat outside the verification machinery entirely -- two of them
# displaying VERIFIED FIXED. Each is repointed at the nodeid that adjudicates
# it, and these are judgements, so they are operator events and need --confirm.
REBINDS = {
    "CYM-own-reports-unverified": (
        "scripts/bounty.py",
        ["tests/rest/test_bounty_tracker.py::test_reports_they_closed_have_been_rechecked_by_us"],
    ),
    "CYM-tracker-closure-rate": (
        "scripts/bounty.py",
        ["tests/rest/test_bounty_tracker.py::test_closures_in_the_public_tracker_carry_evidence"],
    ),
    "CYM-bounty-filing-unauthenticated": (
        "scripts/bounty.py::probe_filing_auth",
        ["tests/rest/test_bounty_tracker.py::test_filing_a_report_requires_a_credential"],
    ),
    "CYM-anon-tool-surface": (
        "scripts/inventory.py",
        ["tests/mcp/test_trust_ladder.py::test_anonymous_receives_only_public_tools"],
    ),
}

RETIRE = {
    "CYM-documented-405": (
        "scripts/inventory.py",
        "Withdrawn as a finding, and the script it named was never collectible "
        "anyway. Retired rather than rebound: there is nothing left to measure.",
    ),
}

# Three findings exist only in the correspondence -- raised in MSG-0002, never
# filed, never in the ledger. Migrated so the page does not imply the vendor
# was never told about them.
FROM_CORRESPONDENCE = {
    "CYM-bounty-pipeline-deadend": {
        "severity": "S1-INTEGRITY", "component": "rest.support", "section": "support",
        "title": "Reports filed through the bounty API do not reach the tracker "
                 "where work happens",
    },
    "CYM-bounty-fields-dropped": {
        "severity": "S2-MEASUREMENT", "component": "rest.support", "section": "support",
        "title": "Five fields accepted by the filing endpoint are not stored",
    },
    "CYM-bounty-hunter-name-lost": {
        "severity": "S2-MEASUREMENT", "component": "rest.support", "section": "support",
        "title": "hunter_name is accepted on submission and not retained",
    },
}

MIGRATED_AT = "2026-09-04T13:30:00+00:00"


def _git_show(ref: str, path: str) -> str:
    """A committed file, decoded as UTF-8 rather than as the console codepage.

    `text=True` decodes with the locale encoding, which on this machine is
    cp1250. state/bounty.json holds a byte cp1250 has no character for, so the
    decode raised inside subprocess's reader THREAD -- where the exception is
    printed and then dropped -- and stdout came back as None. json.loads(None)
    was the first sign, three layers away from the cause.
    """
    return subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT, capture_output=True,
        check=True, encoding="utf-8", errors="replace",
    ).stdout


def _load(name: str) -> dict:
    """A migration source, read from the commit it belonged to.

    Not from today's state/. This script replays history, so its inputs are
    historical: state/submissions.json has since been deleted (the journal
    replaced it) and state/bounty.json drifts every time the vendor answers
    something. Reading either live made a one-shot migration produce a
    different result on every run -- which is the opposite of what a migration
    is for, and it broke its own test twice.
    """
    try:
        return json.loads(_git_show(LEDGER_SHA, f"state/{name}"))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        path = state_dir() / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    _, front, _ = text.split("---", 2)
    meta = yaml.safe_load(front) or {}
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in meta.items()}


# ---------------------------------------------------------------------------
# Events derived mechanically from the artefacts
# ---------------------------------------------------------------------------
def machine_events() -> list[dict]:
    out: list[dict] = []
    src = "scripts/migrate_ledger.py"

    submissions = _load("submissions.json").get("submissions", [])
    bounty = (_load("bounty.json").get("our_reports") or {}).get("reports", [])
    by_id = {r.get("id"): r for r in bounty}

    for entry in submissions:
        at = entry.get("submitted_at") or MIGRATED_AT
        key = entry["key"]
        out.append({
            "type": "filing_intent", "at": at, "by": "migration", "source": src,
            "key": key, "intent_at": at, "title": entry.get("title"),
            "findings": list(entry.get("findings") or []),
            "migrated_from": "state/submissions.json",
        })
        out.append({
            "type": "filing_outcome", "at": at, "by": "migration", "source": src,
            "key": key, "outcome": "accepted", "report_id": entry.get("report_id"),
            "http_status": entry.get("http_status"),
            "findings": list(entry.get("findings") or []),
            # The response bodies were captured in submissions.json itself,
            # which is the evidence this filing rests on. Naming it is what
            # lets the fold accept the transition at all.
            "evidence_id": f"submissions.json#{key}",
            "migrated_from": "state/submissions.json",
        })

    for report_id in sorted(by_id):
        row = by_id[report_id]
        out.append({
            "type": "vendor_status", "at": MIGRATED_AT, "by": "migration",
            "source": src, "report_id": report_id, "status": row.get("status"),
            "observed_at": _load("bounty.json").get("fetched_at") or MIGRATED_AT,
            "evidence_id": f"bounty.json#report-{report_id}",
            "migrated_from": "state/bounty.json",
        })

    for path in sorted(ARCHIVE.glob("*.md")):
        meta = _frontmatter(path)
        msg_id = meta.get("id")
        if not msg_id:
            continue
        inbound = meta.get("direction") == "in"
        at = meta.get("sent_at") or meta.get("received_at") or meta.get("composed_at")
        event = {
            "type": "reply" if inbound else "message",
            "at": str(at or MIGRATED_AT), "by": "vendor" if inbound else "operator",
            "source": src, "msg_id": msg_id,
            "findings": list(meta.get("findings") or []),
            "origin": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "migrated_from": "archive/round-1-2026-09-04",
        }
        if inbound:
            event["reply_to"] = meta.get("reply_to")
            event["evidence_id"] = f"archive#{msg_id}"
        else:
            # Verbatim from the file. MSG-0001 says delivered: false with a
            # note explaining that attachments are not captured on this
            # channel, and that is the fact of record -- not something to
            # improve on during a migration.
            event["delivered"] = meta.get("delivered") is True
        out.append(event)

    for finding_id, (at, reason) in sorted(WITHDRAWALS.items()):
        out.append({
            "type": "withdraw", "at": at, "by": "operator", "source": src,
            "finding_id": finding_id, "reason": reason,
            "migrated_from": f"scripts/ledger.py@{LEDGER_SHA}",
        })

    for finding_id, report_id in sorted(RETRACTIONS_SENT.items()):
        out.append({
            "type": "retraction_sent", "at": "2026-09-04T13:19:00+00:00",
            "by": "operator", "source": src, "finding_id": finding_id,
            "report_id": report_id,
            "reason": "CORRECTIONS paragraph in report #54",
            "migrated_from": "outbox/reports.yaml",
        })

    for finding_id in sorted(FROM_CORRESPONDENCE):
        out.append({
            "type": "migrated", "at": MIGRATED_AT, "by": "migration", "source": src,
            "finding_id": finding_id,
            "text": "Raised in MSG-0002 and never filed; existed only in the "
                    "correspondence, not in the ledger.",
            "migrated_from": "archive/round-1-2026-09-04/2026-09-04-MSG-0002.md",
        })

    legacy = json.loads(_git_show(LEDGER_SHA, "state/ledger.json"))
    for finding_id, row in sorted(legacy.get("findings", {}).items()):
        out.append({
            "type": "backfill", "at": MIGRATED_AT, "by": "migration", "source": src,
            "finding_id": finding_id,
            "text": f"Content copied from state/ledger.json@{LEDGER_SHA}. "
                    f"Figures are those measured when the finding was made and "
                    f"have not been re-measured.",
            "migrated_from": f"state/ledger.json@{LEDGER_SHA}",
        })
        if row.get("verified_fixed_at"):
            out.append({
                "type": "legacy_verification", "at": MIGRATED_AT,
                "by": "migration", "source": src, "finding_id": finding_id,
                "text": f"The pre-contract ledger recorded this as verified "
                        f"fixed at {row['verified_fixed_at']} with "
                        f"verified_by_run={row.get('verified_by_run')!r}. "
                        f"Recorded as a legacy note, never as a verdict: no "
                        f"admissible run stands behind it.",
                "migrated_from": f"state/ledger.json@{LEDGER_SHA}",
            })

    return out


def judgement_events() -> list[dict]:
    """Decisions, not copies. Printed in the dry run and written only with
    --confirm, because a human is answerable for each one."""
    out: list[dict] = []
    src = "scripts/migrate_ledger.py"

    pinned = yaml.safe_load(
        (REPO_ROOT / "tests" / "pinned" / "documented-404.yaml").read_text(
            encoding="utf-8"))
    rebinds = dict(REBINDS)
    rebinds["CYM-documented-404"] = (
        "scripts/inventory.py",
        [f"tests/pinned/test_documented_404.py::test_documented_path_is_served"
         f"[{p['path']}]" for p in pinned["paths"]],
    )

    for finding_id, (old, nodeids) in sorted(rebinds.items()):
        for nodeid in nodeids:
            out.append({
                "type": "rebind_check", "at": MIGRATED_AT, "by": "operator",
                "source": src, "finding_id": finding_id, "value": old,
                "nodeid": nodeid,
                "reason": f"{old} is not a collectible nodeid, so this row "
                          f"could never be adjudicated. Repointed at the check "
                          f"that measures it.",
            })

    for finding_id, (nodeid, reason) in sorted(RETIRE.items()):
        out.append({
            "type": "retire_check", "at": MIGRATED_AT, "by": "operator",
            "source": src, "finding_id": finding_id, "nodeid": nodeid,
            "reason": reason,
        })

    return out


# ---------------------------------------------------------------------------
# Row content -- copied, stamped, never recomputed
# ---------------------------------------------------------------------------
CONTENT_FIELDS = ("title", "severity", "tag", "kind", "section", "component",
                  "note", "detail", "checks")


def rows() -> dict:
    legacy = json.loads(_git_show(LEDGER_SHA, "state/ledger.json"))
    out: dict = {}

    for finding_id, row in legacy.get("findings", {}).items():
        out[finding_id] = {
            "id": finding_id,
            **{f: row.get(f) for f in CONTENT_FIELDS if row.get(f) is not None},
            "first_seen": {
                "at": row.get("first_seen") or MIGRATED_AT,
                "cause": {"run_id": row.get("first_seen_run") or "legacy"},
            },
            "reproductions": row.get("reproductions", 1),
            # Critique gap 5: the words are imported, the figures in them are
            # not presented as current. measured_at stays null until a run
            # measures them.
            "provenance": {"source": f"legacy@{LEDGER_SHA}", "measured_at": None},
            "check": {"state": "UNVERIFIED", "adjudicated_by": None,
                      "pinned_fingerprint": None},
            "filing": {"state": "NOT_RAISED", "adjudicated_by": None,
                       "reports": [], "refused": []},
            "transitions": [],
            "regressions": [],
        }

    for finding_id, meta in FROM_CORRESPONDENCE.items():
        out[finding_id] = {
            "id": finding_id, **meta, "tag": "PROCESS", "kind": "process",
            "checks": [],
            "first_seen": {"at": MIGRATED_AT, "cause": {"run_id": "legacy"}},
            "reproductions": 1,
            "provenance": {"source": "MSG-0002", "measured_at": None},
            "check": {"state": "UNVERIFIED", "adjudicated_by": None,
                      "pinned_fingerprint": None},
            "filing": {"state": "NOT_RAISED", "adjudicated_by": None,
                       "reports": [], "refused": []},
            "transitions": [],
            "regressions": [],
        }

    return out


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="migrate_ledger.py", description=__doc__)
    parser.add_argument("--confirm", action="store_true",
                        help="write the journal and the ledger")
    args = parser.parse_args(argv)

    if read_events():
        raise SystemExit(
            f"the journal at {journal_path()} already has events.\n"
            f"This migration runs once. To start over: "
            f"git checkout {LEDGER_SHA} -- state/ && rm -rf state/journal"
        )

    machine = machine_events()
    judgements = judgement_events()
    content = rows()

    print(f"{len(content)} rows, {len(machine)} copied events, "
          f"{len(judgements)} judgement events\n")

    kinds: dict[str, int] = {}
    for event in machine:
        kinds[event["type"]] = kinds.get(event["type"], 0) + 1
    for kind, count in sorted(kinds.items()):
        print(f"  {count:>3}  {kind}")

    print("\nJUDGEMENTS -- a human is answerable for each of these:")
    for event in judgements:
        target = event.get("nodeid", "")
        print(f"  {event['type']:<14} {event['finding_id']:<36} -> {target}")

    if not args.confirm:
        print("\nDry run. Nothing written. Re-run with --confirm.")
        print("Day one after this migration: every row UNVERIFIED on the CHECK "
              "axis and 0 verified, because no admissible run has adjudicated "
              "anything yet. That is the honest reading of yesterday.")
        return 0

    for event in machine + judgements:
        append_event(event)
    print(f"\n-> {journal_path()}  ({len(read_events())} events)")

    # The ledger itself is written by folding, not by this script: it is a
    # projection, and building it here by hand would be the defect again.
    seed = state_dir() / "ledger.seed.json"
    seed.write_text(json.dumps({"schema": 2, "findings": content}, indent=2,
                               ensure_ascii=False), encoding="utf-8")
    print(f"-> {seed}")
    print("\nNow fold it:  python scripts/ledger.py --events-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
