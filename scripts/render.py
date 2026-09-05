"""Render state/*.json into the operator dashboard.

The page is read-only by design: every control lives in the chat session with
the QA agent. What the dashboard owes the operator is an honest picture of
which parts of the platform are worth testing next, and what was actually said
to the vendor about each finding.

Sections are grouped by the product as a user meets it -- exchange, bots,
arena, money -- rather than by URL layout, because "which part of Cymetica is
this?" is the question being asked. Blast radius survives as a stripe on each
card, so prioritisation stays visible without organising the page around it.

Two numbers per section, deliberately kept apart:

  REACHABILITY  how much of the documented surface answers correctly. Measured
                now, by read-only GET, at two identities.
  CHECKS        how many real assertions exist about that section.

Collapsing them into one "health" score would be the exact defect this project
exists to catch: a section can be 100% reachable and completely unverified.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.findings import TAG_ORDER, TAGS  # noqa: E402

STATE = REPO_ROOT / "state"
OUT = REPO_ROOT / "dashboard" / "index.html"

COMPONENT_TO_SECTION = {
    "reconciliation": "discovery", "discovery.wellknown": "discovery",
    "discovery.llmstxt": "discovery", "discovery.openapi": "discovery",
    "mcp.tools_list": "mcp", "mcp.protocol": "mcp",
    "mcp.trust_ladder": "identity_trust", "rest.agents": "agents",
    "rest.clob": "clob", "rest.markets": "markets", "rest.account": "account",
    "funding.withdraw": "funding", "funding.deposit": "funding",
    "platform.ai_native_proof": "provenance", "platform.status": "swaps",
    "rest.support": "support", "meta.guard": "_meta", "meta.classifier": "_meta",
}


def load(name: str) -> dict:
    # Through the seam, so a test session reads its own state directory
    # rather than the committed one.
    from qa.state import state_dir

    path = state_dir() / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _api_conversation() -> tuple[dict, dict]:
    """The exchange that happens through THEIR bounty API, per report.

    This is the only thing the page calls Correspondence. Telegram is a
    different channel with different properties -- attachments silently
    dropped, delivery unconfirmable -- and mixing the two produced a panel
    where a message nobody received sat beside a report they had answered, as
    though both were the same kind of fact.

    Returns (what we sent, what they said back), both keyed by report id.
    """
    import yaml

    spec = yaml.safe_load((REPO_ROOT / "outbox" / "reports.yaml").read_text(
        encoding="utf-8")) if (REPO_ROOT / "outbox" / "reports.yaml").exists() else {}
    by_key = {r["key"]: r for r in (spec or {}).get("reports", [])}

    # From the JOURNAL, not from state/submissions.json. That file stopped
    # being written when filing became two events, so it ends at #56 -- and
    # every report filed since rendered as an empty bubble with a date on it.
    # A projection nobody updates is worse than no projection: it looks
    # current.
    from qa.state import read_events

    intents: dict[str, dict] = {}
    ours: dict[int, dict] = {}
    for event in read_events():
        if event.get("type") == "filing_intent":
            intents[event["key"]] = event
        elif (event.get("type") == "filing_outcome"
              and event.get("outcome") == "accepted"
              and event.get("report_id") is not None):
            intent = intents.get(event.get("key"), {})
            report = by_key.get(event.get("key"), {})
            ours[event["report_id"]] = {
                "at": intent.get("intent_at") or event.get("at"),
                "title": intent.get("title") or report.get("title"),
                "text": (report.get("body") or "").strip(),
                "expected": (report.get("expected") or "").strip(),
                "actual": (report.get("actual") or "").strip(),
            }

    theirs: dict[int, dict] = {}
    for report in (load("bounty.json").get("our_reports") or {}).get("reports", []):
        report_id = report.get("id")
        if report_id is None:
            continue
        theirs[report_id] = {
            "at": report.get("fixed_at") or report.get("validated_at")
                  or report.get("triaged_at"),
            "status": report.get("status"),
            # Their own words, which is the whole reason this panel exists.
            "text": (report.get("status_notes") or "").strip(),
        }
    return ours, theirs


def _message_bodies() -> dict[str, dict]:
    """Every message file, indexed by its id.

    The journal records WHICH messages touch a finding; the words stay in the
    files, pasted verbatim. Reading them here is what puts the vendor's actual
    sentences on the page instead of a summary of them -- and archive/ is
    included, because where a file was filed afterwards says nothing about
    what it said.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "thread_reader", REPO_ROOT / "scripts" / "thread.py")
    thread_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thread_mod)

    out: dict[str, dict] = {}
    for folder in (REPO_ROOT / "outbox", REPO_ROOT / "inbox",
                   *sorted((REPO_ROOT / "archive").glob("*"))):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            meta = thread_mod.parse(path)
            if meta is None or not meta.get("id"):
                continue
            out[meta["id"]] = {
                "file": meta.get("file"),
                "channel": meta.get("channel"),
                "delivered_as": meta.get("delivered_as"),
                "delivery_note": meta.get("delivery_note"),
                "covers": meta.get("covers") or {},
                "blocks": thread_mod.blocks(meta.get("body") or ""),
                "body": meta.get("body") or "",
            }
    return out


def _thread_for(row: dict, sent: dict, replied: dict, filed_at: dict) -> list[dict]:
    """The conversation about this finding, through their API, in order."""
    out = []
    for report in (row.get("filing") or {}).get("reports", []):
        report_id = report["report_id"]
        ours = sent.get(report_id, {})
        out.append({
            "who": "us", "report_id": report_id,
            "at": ours.get("at") or filed_at.get(report_id),
            "title": ours.get("title"),
            "text": ours.get("text") or "",
            "expected": ours.get("expected") or "",
            "actual": ours.get("actual") or "",
        })
        answer = replied.get(report_id) or {}
        if answer.get("status") and answer["status"] != "pending":
            out.append({
                "who": "them", "report_id": report_id,
                "at": answer.get("at"), "status": answer.get("status"),
                "text": answer.get("text") or "",
            })
    return sorted(out, key=lambda m: (m.get("at") or "", m["report_id"]))


def _summary(row: dict) -> str | None:
    """What this finding says, in one sentence."""
    detail = row.get("detail") or {}
    reason = (detail.get("reason") or "").strip()
    if reason:
        return reason
    note = (row.get("note") or "").strip()
    return note or None


def _excerpt_for(source: dict, finding_id: str) -> str | None:
    """The part of a message that discusses this finding, or nothing.

    `covers` in the message's own frontmatter maps a heading to the findings
    that section is about. A finding named in the message but not mapped to a
    section gets NO excerpt rather than a wrong one -- the page then says the
    message mentions it and points at the file, which is true, instead of
    quoting a paragraph about something else.
    """
    if not source:
        return None

    needles = [n for n, ids in (source.get("covers") or {}).items()
               if finding_id in (ids if isinstance(ids, list) else [ids])]
    if not needles:
        return None

    parts = []
    for needle in needles:
        for heading, text in source.get("blocks") or []:
            if needle.lower() in heading.lower():
                parts.append(f"{heading}\n\n{text}".strip())
    if parts:
        return "\n\n".join(parts)

    # Their messages are not shaped like ours: the vendor numbers answers as
    # "1) ..." running on into a full paragraph, so nothing in them is a
    # heading and the block split yields one nameless block. Fall back to the
    # paragraph the needle begins, which is how `covers` was written anyway.
    # Without this the single most valuable text on the page -- what they
    # actually said -- rendered as nothing.
    paragraphs = [p.strip() for p in (source.get("body") or "").split("\n\n")]
    for needle in needles:
        for para in paragraphs:
            if para.lower().startswith(needle.lower()):
                parts.append(para)
    return "\n\n".join(parts) if parts else None


def out_path() -> Path:
    from qa.state import state_dir

    override = __import__("os").environ.get("QA_STATE_DIR")
    return (state_dir() / "dashboard" / "index.html") if override else OUT


def latest_run() -> dict:
    """The newest ADMISSIBLE run, by started_at -- never the last filename.

    Three copies of `sorted(glob(...))[-1]` used to decide which run the
    dashboard was describing, so a one-result re-run became the run of record
    for every number on the page.
    """
    from qa.state import latest_admissible_run_id, load_run

    run_id = latest_admissible_run_id("R")
    return load_run(run_id) if run_id else {}


def build_payload(ledger: dict | None = None, inventory: dict | None = None,
                  thread: dict | None = None, run: dict | None = None) -> dict:
    """Everything the page shows, derived and reconciled before it is shown.

    The arguments exist so this can be exercised without the committed state
    directory. Passing none of them reads the repository, which is what
    __main__ does.
    """
    from qa.fold import display_state
    from qa.state import head, load_run

    from qa.state import read_events

    inventory = inventory if inventory is not None else load("inventory.json")

    # Message counts come from the journal, not from thread.json. That file is
    # a scan of outbox/ and inbox/, and once round 1 was moved to archive/ it
    # reported zero messages sent -- while three had been. Correspondence is
    # events now, and an event does not care where the file ended up.
    events = read_events()
    if thread is None:
        sent = [e for e in events if e["type"] == "message"]
        thread = {"counts": {
            "sent": len(sent),
            "received": sum(1 for e in events if e["type"] == "reply"),
            "undelivered": sum(1 for e in sent if not e.get("delivered")),
        }}

    # The ledger, not the current run, is the source of truth for findings.
    # A finding whose check has started passing must still appear -- as
    # VERIFIED FIXED, the one state that means "we checked" rather than "they
    # said". Deriving the list from what is currently failing would delete
    # exactly the records worth keeping.
    from scripts.ledger import as_findings, load_previous
    current = head()
    if ledger is None:
        # No ledger at all is not a stale projection -- it is a repository
        # that has not folded one yet, and an empty page is the honest view.
        ledger = load_previous() or {"findings": {}, "events_head": current}

    # A projection that has fallen behind its source IS a different matter: a
    # page that renders anyway is worse than no page, because it looks
    # current. Refuse, and say how to fix it.
    cited = ledger.get("events_head")
    if cited != current:
        raise SystemExit(
            f"refusing to render: the ledger cites journal head {cited} but the "
            f"journal is at {current}.\nRe-fold it first: python scripts/ledger.py"
        )

    # The page describes the run the LEDGER was composed from, not whatever
    # record is newest. A two-test re-run of tests/repo/ is a perfectly valid
    # record and would otherwise have become the run of record for every
    # per-section count on the page -- the partial-run problem, reappearing in
    # the display layer after being closed in the fold.
    if run is None:
        composed = ledger.get("run_id")
        try:
            run = load_run(composed) if composed else {}
        except KeyError:
            run = {}

    # Per-row correspondence, rebuilt from the journal. The rewrite moved
    # reports onto `filing.reports` and messages into events, but the page was
    # still reading `f.filed`, `f.thread`, `f.undelivered` and
    # `f.withdrawn_reason` -- fields no row carries any more. The result was a
    # tile reading "0 filed to their tracker" beside eleven filed reports, and
    # the Correspondence panel empty on every row. Same class as the display
    # state: the page read a field the fold had stopped writing.
    sent, replied = _api_conversation()
    withdrawn_reason: dict[str, str] = {}
    filed_at: dict[int, str] = {}
    for event in events:
        etype = event.get("type")
        if etype == "withdraw" and event.get("finding_id"):
            withdrawn_reason[event["finding_id"]] = event.get("reason") or ""
        elif etype == "filing_outcome" and event.get("outcome") == "accepted":
            filed_at.setdefault(event.get("report_id"), event.get("at"))

    rows = as_findings(ledger)
    findings = []
    display_counts: dict[str, int] = {}
    timeline = []

    for row in rows:
        shown = display_state(row)
        display_counts[shown] = display_counts.get(shown, 0) + 1

        adjudicated = (row.get("check") or {}).get("adjudicated_by")
        row_checks = row.get("checks") or []
        findings.append({
            **row,
            "display_state": shown,
            # The verification sentence is printed from THIS, or not at all.
            # Ten rows read VERIFIED FIXED with verified_by_run null on every
            # one, beneath a sentence claiming we had re-run the check.
            "verification": (
                {"run_id": adjudicated["run_id"], "at": adjudicated.get("at"),
                 "nodeid": row_checks[0] if row_checks else None}
                if adjudicated and adjudicated.get("run_id")
                and shown == "VERIFIED FIXED" else None
            ),
            "not_checked_in": (row.get("check") or {}).get("not_checked_in"),
            # Critique gap 5: content carried over from the hand-written
            # ledger quotes figures frozen at their last failing values.
            #
            # Shown only where it is ACTIONABLE -- a row with a working check
            # that has not run again yet. On a withdrawn row it is noise, and
            # on an unverifiable one the state already says the stronger
            # thing: nothing can measure this. The operator asked three times
            # what the tag meant, and on those rows the honest answer was
            # "nothing you can do".
            "unmeasured": (not (row.get("provenance") or {}).get("measured_at")
                           and shown not in ("WITHDRAWN", "SUPERSEDED",
                                             "UNVERIFIABLE")),
            "filed": [
                {"report_id": r["report_id"], "status": r.get("status"),
                 "submitted_at": filed_at.get(r["report_id"])}
                for r in (row.get("filing") or {}).get("reports", [])
            ],
            "thread": _thread_for(row, sent, replied, filed_at),
            "withdrawn_reason": withdrawn_reason.get(row["id"]),
            # One sentence, from what the check deliberately measured. The
            # panel used to show left / right / sources / population / reason
            # as a table of field names -- accurate, and unreadable.
            "summary": _summary(row),
        })

        for transition in row.get("transitions", []):
            if transition.get("axis") == "check":
                timeline.append({
                    "finding_id": row["id"], "at": transition["at"],
                    "from": transition.get("from"), "to": transition["to"],
                    "run_id": (transition.get("cause") or {}).get("run_id"),
                })

    timeline.sort(key=lambda e: e["at"])

    # Every row lands in exactly one bucket, and the buckets sum to the rows.
    # The filter said 16, the tiles summed to 6, the ledger held 20.
    assert sum(display_counts.values()) == len(rows), (
        f"display counts {display_counts} do not sum to {len(rows)} rows"
    )

    by_severity: dict[str, int] = {}
    for finding in findings:
        if finding["display_state"] not in ("VERIFIED FIXED", "WITHDRAWN"):
            by_severity[finding["severity"]] = by_severity.get(
                finding["severity"], 0) + 1

    checks: dict[str, dict[str, int]] = {}
    for result in run.get("results", []):
        section = COMPONENT_TO_SECTION.get(result.get("component", ""), "_other")
        bucket = checks.setdefault(
            section, {"passed": 0, "failed": 0, "inconclusive": 0, "total": 0})
        bucket["total"] += 1
        if result.get("outcome") in bucket:
            bucket[result["outcome"]] += 1

    by_section: dict[str, list[str]] = {}
    for finding in findings:
        if finding["display_state"] in ("VERIFIED FIXED", "WITHDRAWN"):
            continue
        targets = set(finding.get("affected_sections") or []) | {finding.get("section")}
        for section in targets:
            if section:
                by_section.setdefault(section, []).append(finding["severity"])

    sections = [
        {**s,
         "checks": checks.get(s["id"], {}),
         "finding_severities": by_section.get(s["id"], [])}
        for s in inventory.get("sections", [])
    ]

    groups = [
        {"tag": tag, "title": TAGS[tag][0], "blurb": TAGS[tag][1],
         "sections": TAGS[tag][2]}
        for tag in TAG_ORDER
    ]

    from qa.fold import CHECK_STATES, DISPLAY, FILING_STATES
    from qa.state import admissibility

    # The legend's diagram is generated from the real composition table, not
    # written out beside it. A hand-drawn legend is a second source of truth
    # for the thing this whole rebuild exists to keep single.
    composition = {
        "check_states": [c for c in CHECK_STATES if c != "CHECK_CHANGED"],
        "filing_states": [f for f in FILING_STATES if f not in ("WITHDRAWN", "SUPERSEDED")],
        "terminal": ["WITHDRAWN", "SUPERSEDED"],
        "table": {c: {f: DISPLAY[(c, f)] for f in FILING_STATES}
                  for c in CHECK_STATES},
    }

    verdict = admissibility(run) if run else None
    return {
        "composition": composition,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run.get("run_id"),
        # Critique gap 8: "V" and "V (partial identity)" are different claims
        # about how much of the ladder this run could reach.
        "run_level": verdict.label if verdict else "none",
        "run_notes": verdict.notes if verdict else [],
        "fingerprint": (run.get("platform_fingerprint") or "")[:23],
        "events_head": ledger.get("events_head"),
        "totals": inventory.get("totals", {}),
        "sections": sections,
        "findings": findings,
        "display_counts": display_counts,
        "timeline": timeline,
        "by_severity": by_severity,
        "groups": groups,
        "thread_counts": thread.get("counts", {}),
    }


TEMPLATE = r"""<title>Cymetica QA Console</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {
  --bg:#f6f7f6; --surface:#ffffff; --surface-2:#eef1f0; --line:#d5dbd9;
  --line-soft:#e6eae9; --text:#10171a; --text-dim:#5a6a6c; --text-faint:#8b9a9b;
  --accent:#0d6b66; --accent-dim:#0d6b6622;
  --ok:#17803d;   --ok-bg:#17803d1f;
  --auth:#0e7490; --auth-bg:#0e74901f;
  --warn:#9a6300; --warn-bg:#9a63001f;
  --bad:#b3261e;  --bad-bg:#b3261e1f;
  --wait:#6b3fc4; --wait-bg:#6b3fc41f;
  --none:#9aa8a8; --none-bg:#9aa8a826;
  --radius:7px;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#0c1214; --surface:#121b1d; --surface-2:#182326; --line:#243436;
    --line-soft:#1b282a; --text:#e4ecea; --text-dim:#93a5a5; --text-faint:#6a7b7c;
    --accent:#4ecfc4; --accent-dim:#4ecfc422;
    --ok:#4ec97a; --ok-bg:#4ec97a1f; --auth:#45b8d6; --auth-bg:#45b8d61f;
    --warn:#e0a338; --warn-bg:#e0a3381f; --bad:#f2685e; --bad-bg:#f2685e1f;
    --wait:#a98cf0; --wait-bg:#a98cf01f; --none:#647476; --none-bg:#64747626;
  }
}
:root[data-theme="dark"] {
  --bg:#0c1214; --surface:#121b1d; --surface-2:#182326; --line:#243436;
  --line-soft:#1b282a; --text:#e4ecea; --text-dim:#93a5a5; --text-faint:#6a7b7c;
  --accent:#4ecfc4; --accent-dim:#4ecfc422;
  --ok:#4ec97a; --ok-bg:#4ec97a1f; --auth:#45b8d6; --auth-bg:#45b8d61f;
  --warn:#e0a338; --warn-bg:#e0a3381f; --bad:#f2685e; --bad-bg:#f2685e1f;
  --wait:#a98cf0; --wait-bg:#a98cf01f; --none:#647476; --none-bg:#64747626;
}

* { box-sizing:border-box; }
body {
  margin:0; background:var(--bg); color:var(--text); font-family:var(--sans);
  font-size:16.5px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1240px; margin:0 auto; padding:32px 22px 80px; }

.mast { border-bottom:2px solid var(--text); padding-bottom:14px; }
.mast h1 {
  font-size:clamp(26px,4vw,38px); font-weight:600; letter-spacing:-0.022em;
  margin:0 0 4px; text-wrap:balance;
}
.mast .sub { color:var(--text-dim); font-size:16.0px; max-width:70ch; margin:0; }
.meta {
  display:flex; flex-wrap:wrap; gap:6px 20px; margin-top:14px;
  font-family:var(--mono); font-size:13.0px; color:var(--text-faint);
}
.meta b { color:var(--text-dim); font-weight:500; }

.triage {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:var(--radius);
  overflow:hidden; margin:26px 0 6px;
}
.tri { background:var(--surface); padding:13px 15px; }
.tri .n {
  font-family:var(--mono); font-size:27px; font-weight:600; line-height:1.1;
  font-variant-numeric:tabular-nums;
}
.tri .l {
  font-size:12.0px; text-transform:uppercase; letter-spacing:0.09em;
  color:var(--text-faint); margin-top:3px; font-weight:600;
}
.tri.s0 .n,.tri.s1 .n { color:var(--bad); }
.tri.s2 .n,.tri.s3 .n { color:var(--warn); }
.tri.s4 .n { color:var(--text-dim); }
.tri.ok .n { color:var(--ok); }

h2.group {
  font-size:13.5px; text-transform:uppercase; letter-spacing:0.13em;
  font-weight:700; margin:38px 0 3px; display:flex; align-items:center; gap:10px;
}
.tagchip {
  font-family:var(--mono); font-size:11.5px; font-weight:600; letter-spacing:0.06em;
  padding:3px 7px; border-radius:4px; background:var(--accent-dim);
  color:var(--accent); white-space:nowrap;
}
p.group-note { margin:0 0 15px; color:var(--text-dim); font-size:15.0px; max-width:74ch; }

/* align-items:start, so opening one card does not stretch every other card
   in its row to the same height -- which is what made one open tile look
   like the whole row had come apart. */
.grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:12px; align-items:start;
}
.card {
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
  padding:15px 16px 14px; border-left:3px solid var(--none);
}
/* The card is a <details> now, so the column layout lives on the summary --
   display:flex on a details element breaks the open/closed flow. */
.card > summary { display:flex; flex-direction:column; gap:10px; }
.card.h-ok{border-left-color:var(--ok)} .card.h-warn{border-left-color:var(--warn)}
.card.h-bad{border-left-color:var(--bad)} .card.h-none{border-left-color:var(--none)}
.card-top { display:flex; align-items:baseline; justify-content:space-between; gap:12px; }
.card h3 { margin:0; font-size:16.0px; font-weight:600; letter-spacing:-0.01em; }
.pct {
  font-family:var(--mono); font-size:25px; font-weight:600; line-height:1;
  font-variant-numeric:tabular-nums; white-space:nowrap;
}
.pct.h-ok{color:var(--ok)} .pct.h-warn{color:var(--warn)} .pct.h-bad{color:var(--bad)}
.pct.h-none{color:var(--text-faint); font-size:14.5px}
.pct small { font-size:13.5px; font-weight:500; color:var(--text-faint); }

.bar { display:flex; height:7px; border-radius:3px; overflow:hidden; background:var(--surface-2); }
.bar span { display:block; }
.seg-ok{background:var(--ok)} .seg-auth{background:var(--auth)}
.seg-param{background:var(--auth);opacity:.6} .seg-method{background:var(--warn)}
.seg-missing{background:var(--bad)}
.seg-unprobed,.seg-websocket{
  background:repeating-linear-gradient(135deg,var(--none-bg) 0 4px,transparent 4px 8px);
  box-shadow:inset 0 0 0 1px var(--none-bg);
}
.pct-wrap { display:flex; flex-direction:column; align-items:flex-end; gap:2px; }
.pct-cap {
  font-family:var(--mono); font-size:11.0px; color:var(--text-faint);
  white-space:nowrap; letter-spacing:.02em;
}
.chip.untested {
  color:var(--text-faint); background:transparent;
  border:1px dashed var(--line); font-weight:600;
}
.blurb { font-size:14.1px; color:var(--text-dim); margin:0; line-height:1.5; }
.stats { display:flex; flex-wrap:wrap; gap:5px; font-family:var(--mono); font-size:12.5px; }
.chip {
  border:1px solid var(--line); border-radius:4px; padding:2px 6px;
  color:var(--text-dim); background:var(--surface-2); white-space:nowrap;
}
.chip.bad{color:var(--bad);border-color:transparent;background:var(--bad-bg);font-weight:600}
.chip.warn{color:var(--warn);border-color:transparent;background:var(--warn-bg);font-weight:600}
.chip.ok{color:var(--ok);border-color:transparent;background:var(--ok-bg);font-weight:600}
.chip.none{color:var(--text-faint)}

.filters { display:flex; flex-wrap:wrap; gap:6px; margin:16px 0 14px; align-items:center; }
.filters button {
  font-family:var(--mono); font-size:13.0px; padding:5px 11px; cursor:pointer;
  border:1px solid var(--line); background:var(--surface); color:var(--text-dim);
  border-radius:20px; font-weight:500;
}
.filters button[aria-pressed="true"] { background:var(--text); color:var(--bg); border-color:var(--text); }
.filters button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.filters .sep { width:1px; height:20px; background:var(--line); margin:0 5px; }
.filters .fl {
  font-family:var(--mono); font-size:11.5px; text-transform:uppercase;
  letter-spacing:.06em; color:var(--text-faint); margin-right:2px;
}

.finding {
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); margin-bottom:9px; overflow:hidden;
}
.finding > summary {
  cursor:pointer; padding:13px 15px; display:grid;
  grid-template-columns:auto 1fr; gap:12px; align-items:start; list-style:none;
}
.finding > summary::-webkit-details-marker { display:none; }
.finding > summary:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.sev {
  font-family:var(--mono); font-size:11.5px; font-weight:600; padding:3px 7px;
  border-radius:4px; letter-spacing:.04em; white-space:nowrap; margin-top:2px;
}
.sev.S0,.sev.S1 { background:var(--bad-bg); color:var(--bad); }
.sev.S2,.sev.S3 { background:var(--warn-bg); color:var(--warn); }
.sev.S4 { background:var(--none-bg); color:var(--text-dim); }
.f-title { font-weight:500; font-size:16.0px; line-height:1.45; }
.f-sub {
  font-family:var(--mono); font-size:12.5px; color:var(--text-faint); margin-top:5px;
  display:flex; flex-wrap:wrap; gap:5px 9px; align-items:center;
}
.state {
  font-family:var(--mono); font-size:11.5px; font-weight:600; padding:2px 6px;
  border-radius:4px; white-space:nowrap;
}
/* Every cell of the composition table gets a colour. Seven of the sixteen
   were styled and three of those seven named states that no longer exist, so
   nine chips -- PASSING (UNPINNED) and WITHDRAWN among them -- rendered as
   plain grey text and were easy to read straight past. A state with no colour
   is a state the eye does not register.

   Grouped by what the operator should DO about it, not by axis:
     red     it reproduces; the defect is live
     amber   waiting on somebody -- them, or a decision of ours
     teal    our check passes, but something short of a verification
     green   verified: our measurement and their claim agree
     grey    we cannot tell
     muted   terminal and ours (struck through) */
.state.s-still-reproducible { background:var(--bad-bg); color:var(--bad); }
.state.s-not-raised-yet     { background:var(--bad-bg); color:var(--bad); }
.state.s-raised             { background:var(--auth-bg); color:var(--auth); }
.state.s-they-replied       { background:var(--wait-bg); color:var(--wait); }
.state.s-fix-claimed        { background:var(--warn-bg); color:var(--warn); }
.state.s-check-changed      { background:var(--warn-bg); color:var(--warn); }
.state.s-passing-unpinned   { background:var(--accent-dim); color:var(--accent); }
.state.s-passing-never-raised { background:var(--accent-dim); color:var(--accent); }
.state.s-verified-fixed     { background:var(--ok-bg); color:var(--ok); }
.state.s-unverified         { background:var(--none-bg); color:var(--text-dim); }
.state.s-inconclusive       { background:var(--none-bg); color:var(--text-dim); }
.state.s-not-reproducible   { background:var(--none-bg); color:var(--text-dim); }
.state.s-unverifiable       { background:var(--none-bg); color:var(--text-dim); }
.state.s-withdrawn  { background:var(--none-bg); color:var(--text-faint); text-decoration:line-through; }
.state.s-superseded { background:var(--none-bg); color:var(--text-faint); text-decoration:line-through; }

.filed { font-family:var(--mono); font-size:13.5px; color:var(--text-faint); }

/* ---------- cards open, and the bar says what it means ---------- */
.card > summary { list-style:none; cursor:pointer; }
.card > summary::-webkit-details-marker { display:none; }
.card-more {
  display:inline-block; margin-top:11px; font-family:var(--mono);
  font-size:12.5px; color:var(--accent);
}
.card[open] .card-more { visibility:hidden; }
.blegend {
  display:flex; flex-wrap:wrap; gap:4px 14px; margin:8px 0 0;
  font-size:12.5px; color:var(--text-dim);
}
.blabel { display:flex; align-items:center; gap:5px; }
.blabel i { width:9px; height:9px; border-radius:2px; display:inline-block; }
.card-detail {
  margin-top:14px; padding-top:14px; border-top:1px solid var(--line-soft);
}
.epgroup { margin-bottom:15px; }
.epgroup-h {
  display:flex; align-items:center; gap:7px; font-size:13.5px; color:var(--text);
  margin-bottom:7px; font-weight:600;
}
.epgroup-h i { width:9px; height:9px; border-radius:2px; display:inline-block; }
.ep { padding:4px 0 4px 16px; border-left:2px solid var(--line-soft); margin:2px 0; }
.ep code { font-family:var(--mono); font-size:13px; color:var(--text-dim); }
.ep-meta {
  display:block; font-family:var(--mono); font-size:12px; color:var(--text-faint);
}

/* ---------- the finding body ---------- */
.f-lede {
  font-size:17.5px; line-height:1.5; color:var(--text); margin:16px 0 4px;
  max-width:80ch;
}
.f-ref { margin-top:20px; border-top:1px solid var(--line-soft); padding-top:14px; }
.f-ref > div {
  display:flex; gap:14px; align-items:baseline; margin:7px 0; flex-wrap:wrap;
}
.ref-k {
  flex:0 0 168px; font-size:13.5px; color:var(--text-faint);
  text-transform:uppercase; letter-spacing:.04em;
}
.ref-v { font-size:15.0px; color:var(--text-dim); min-width:0; word-break:break-word; }
.ref-v.mono { font-family:var(--mono); font-size:14.0px; }
.kvt { border-collapse:collapse; font-size:14.5px; }
.kvt td { padding:1px 14px 1px 0; vertical-align:top; color:var(--text-dim); }
.kvt td:first-child { font-family:var(--mono); font-size:13.5px; color:var(--text-faint); }

/* ---------- the conversation, as a conversation ---------- */
.chat { margin:14px 0; max-width:84%; }
.chat.us { margin-left:auto; }
.chat-meta {
  display:flex; gap:10px; align-items:baseline; font-size:14.0px;
  color:var(--text-dim); margin-bottom:5px;
}
.chat.us .chat-meta { justify-content:flex-end; }
.chat-meta time { font-family:var(--mono); font-size:13.0px; color:var(--text-faint); }
.chat-status {
  font-family:var(--mono); font-size:12.5px; text-transform:uppercase;
  padding:1px 6px; border-radius:4px; background:var(--ok-bg); color:var(--ok);
}
.chat-body {
  border-radius:12px; padding:12px 15px; font-size:16.0px; line-height:1.55;
  border:1px solid var(--line-soft); white-space:normal;
}
.chat.us .chat-body {
  background:var(--accent-dim); border-color:transparent;
  border-bottom-right-radius:3px;
}
.chat.them .chat-body { background:var(--surface-2); border-bottom-left-radius:3px; }
.chat-body p { margin:0 0 9px; }
.chat-body p:last-child { margin-bottom:0; }
.chat-title { font-weight:600; margin-bottom:8px; color:var(--text); }
.chat-quiet { color:var(--text-faint); font-style:italic; }
.chat-note {
  margin:16px 0 0; font-size:15.0px; color:var(--text-dim);
  padding-left:12px; border-left:3px solid var(--line);
}
.chat-note.ok { border-left-color:var(--ok); }
.chat-note.bad { border-left-color:var(--bad); }
.undelivered {
  font-family:var(--mono); font-size:11.5px; font-weight:600; padding:2px 6px;
  border-radius:4px; background:var(--bad-bg); color:var(--bad); white-space:nowrap;
}
/* On 19 of 23 rows, so it must not shout. Red made it the loudest thing on
   the page and pushed the state chip -- the thing actually worth reading --
   into the background. It is a provenance note, not an alarm. */
.unmeasured, .unmeasured-demo {
  font-family:var(--mono); font-size:11.5px; padding:2px 6px; border-radius:4px;
  background:transparent; color:var(--text-faint);
  border:1px dashed var(--line); white-space:nowrap; cursor:help;
}
.unmeasured-demo { font-weight:400; cursor:default; }

/* ---------- legend: two axes, then the grid they make ---------- */
.lead { font-size:15.0px; color:var(--text-dim); max-width:74ch; margin:14px 0 10px; }
.lead .hi { color:var(--ok); font-weight:600; }

.axes { display:flex; gap:14px; align-items:stretch; flex-wrap:wrap; margin:14px 0 22px; }
.axis {
  flex:1 1 260px; min-width:0; background:var(--surface-2);
  border:1px solid var(--line-soft); border-radius:var(--radius); padding:12px 13px;
}
.axis-h { font-size:14.5px; font-weight:600; color:var(--text); }
.axis-h b { color:var(--accent); }
.axis-sub {
  font-size:13.0px; color:var(--text-faint); margin:2px 0 10px;
  padding-bottom:8px; border-bottom:1px solid var(--line-soft);
}
.axis-row {
  display:flex; gap:9px; align-items:baseline; margin:6px 0;
  font-size:13.9px; color:var(--text-dim);
}
/* An axis VALUE, not a display state. Deliberately its own class: reusing
   .state gave NOT_RAISED the class s-not-raised, which no rule matches --
   the same unstyled-chip problem one level up. These are inputs to the grid;
   the colours belong to the squares the grid produces. */
.axv {
  flex:0 0 auto; font-family:var(--mono); font-size:11.5px; font-weight:600;
  padding:2px 6px; border-radius:4px; white-space:nowrap;
  background:var(--none-bg); color:var(--text-dim);
}
.axis-join {
  align-self:center; font-family:var(--mono); font-size:22px; color:var(--text-faint);
}

.matrix-wrap { overflow-x:auto; margin:6px 0 10px; }
.matrix { border-collapse:separate; border-spacing:3px; font-size:12.5px; }
.matrix th {
  font-family:var(--mono); font-size:11.5px; font-weight:600; color:var(--text-faint);
  text-align:left; white-space:nowrap; padding:3px 6px; text-transform:uppercase;
  letter-spacing:.04em;
}
.matrix tr th:first-child { text-align:right; }
.matrix td { padding:0; }
.matrix .state { display:block; text-align:center; }
.matrix-note {
  display:flex; flex-direction:column; gap:5px; font-size:13.9px; color:var(--text-dim);
}
.marks { flex:none; margin:10px 0 20px; }
.marks .axis-row { align-items:baseline; margin:8px 0; }
.marks .axis-row > span:last-child { max-width:70ch; }
.mono-faint {
  font-family:var(--mono); font-size:12.5px; color:var(--text-faint); flex:0 0 auto;
}
.matrix-note span span.state { margin-right:7px; }

@media (max-width: 640px) {
  .axis-join { display:none; }
}

.f-body {
  padding:0 15px 15px; border-top:1px solid var(--line-soft); font-size:13.5px;
}
.f-body .f-lede { font-size:15px; }
.f-body .chat-body { font-size:13.5px; padding:10px 13px; }
.f-body .ref-k { font-size:11.5px; flex-basis:150px; }
.f-body .ref-v { font-size:12.5px; }
.f-body .ref-v.mono { font-size:11.8px; }
.ref-note { color:var(--text-faint); }
.f-note {
  font-size:14.7px; color:var(--text-dim); margin:12px 0 0; padding-left:11px;
  border-left:2px solid var(--accent-dim); max-width:78ch;
}
.kv { overflow-x:auto; }
.kv table { border-collapse:collapse; width:100%; font-family:var(--mono); font-size:13.5px; }
.kv td { padding:4px 10px 4px 0; vertical-align:top; border-bottom:1px solid var(--line-soft); }
.kv td:first-child { color:var(--text-faint); white-space:nowrap; width:1%; }
.kv td:last-child { color:var(--text); word-break:break-word; }
.checks {
  margin-top:13px; font-family:var(--mono); font-size:12.5px; color:var(--text-faint);
  word-break:break-all;
}
.checks b { color:var(--text-dim); font-weight:500; }

h4.sec {
  font-size:12.0px; text-transform:uppercase; letter-spacing:.1em; font-weight:700;
  color:var(--text-faint); margin:18px 0 8px;
}
.msg { border:1px solid var(--line-soft); border-radius:6px; margin-bottom:8px; overflow:hidden; }
.msg-head {
  display:flex; flex-wrap:wrap; gap:4px 10px; align-items:center; padding:8px 11px;
  background:var(--surface-2); font-family:var(--mono); font-size:12.5px; color:var(--text-faint);
}
.dir { font-weight:600; }
.dir.out { color:var(--auth); }
.dir.in  { color:var(--ok); }
.dir.dead { color:var(--bad); }
.msg pre {
  margin:0; padding:11px 13px; font-family:var(--mono); font-size:13.0px;
  line-height:1.6; white-space:pre-wrap; word-break:break-word; color:var(--text);
  max-height:360px; overflow:auto; background:var(--surface);
}
.awaiting {
  font-size:14.0px; color:var(--text-faint); padding:9px 11px;
  border:1px dashed var(--line); border-radius:6px; max-width:78ch;
}

.note {
  margin-top:42px; padding:18px 20px; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--surface); font-size:15.0px;
  color:var(--text-dim); max-width:82ch;
}
.note h3 { margin:0 0 8px; font-size:14.5px; color:var(--text); text-transform:uppercase; letter-spacing:.09em; }
.note p { margin:0 0 9px; }
.note code { font-family:var(--mono); font-size:13.5px; background:var(--surface-2); padding:1px 5px; border-radius:3px; }
.note .verdicts { border-collapse:collapse; margin:12px 0 16px; }
.note .verdicts td { padding:5px 12px 5px 0; vertical-align:top; font-size:14.7px; line-height:1.45; }
.note .verdicts td:first-child { width:1%; padding-right:9px; padding-top:9px; }
.note .verdicts td:nth-child(2) { white-space:nowrap; color:var(--text); }
.note .verdicts i {
  display:inline-block; width:10px; height:10px; border-radius:2px;
  box-shadow:inset 0 0 0 1px var(--line);
}
.note .verdicts i.faint { opacity:.6; }
.note .example {
  background:var(--surface-2); border-radius:6px; padding:11px 13px;
  border-left:2px solid var(--accent); font-size:14.7px;
}
@media (prefers-reduced-motion: reduce) { * { transition:none!important; animation:none!important; } }
</style>

<div class="wrap">
  <header class="mast">
    <h1>Cymetica QA Console</h1>
    <p class="sub">Independent verification of the Cymetica / EventTrader API, MCP and
    discovery surfaces. Every number below was measured, not reported.</p>
    <div class="meta" id="meta"></div>
  </header>

  <div class="triage" id="triage"></div>

  <div id="map"></div>

  <h2 class="group" style="margin-top:46px">Findings</h2>
  <p class="group-note">Everything found so far, including defects in the platform's own
  documentation. Open one to read the exact correspondence sent about it. Nothing here is
  marked fixed &mdash; only <em>verified against a named surface, at a named time, by a
  named check</em>.</p>
  <div class="filters" id="filters"></div>
  <div id="findings"></div>

  <div class="note">
    <h3>How to read this page</h3>

    <p class="lead">Every badge answers <b>two</b> questions at once. That is why there
    are so many of them &mdash; and the badge is just the square where the two answers meet.</p>

    <div id="axes"></div>

    <p class="lead"><b>The grid below is the whole pipeline.</b> Down the side: what
    <b>we</b> measured. Along the top: where it stands <b>with them</b>.
    <span class="hi">Only one square is green</span> &mdash; our check passes <em>and</em>
    they claim a fix. Nothing else counts as verified.</p>

    <div id="matrix"></div>

    <p class="lead"><b>A row carries other marks too.</b> None of them is a state:</p>

    <div id="marks"></div>

    <h4>S0 to S4 &mdash; how much damage, not how sure we are</h4>

    <div id="sevs"></div>

    <h4>The cards are places, not test suites</h4>

    <p class="lead">One card = one part of the platform. Its chips count four
    different things:</p>

    <div id="cardmarks"></div>

    <p class="lead">The buttons at the top of the page filter the finding list:
    the first row by <b>damage</b> (the S numbers), the second by <b>area</b>
    &mdash; the same areas the cards are grouped under.</p>

    <h4>The percentage on each card is a different thing</h4>

    <p><b>It answers one question:</b> of all the addresses Cymetica publishes for this
    part of the platform, how many actually answer when you call them? We call each twice
    &mdash; once with no key, once with the API key &mdash; and take the better answer:</p>

    <table class="verdicts">
      <tr><td><i style="background:var(--ok)"></i></td>
          <td><b>It works.</b></td>
          <td>Counts as good.</td></tr>
      <tr><td><i style="background:var(--auth)"></i></td>
          <td><b>&ldquo;You need to log in.&rdquo;</b></td>
          <td>The lock is doing its job. Counts as good.</td></tr>
      <tr><td><i style="background:var(--auth)" class="faint"></i></td>
          <td><b>&ldquo;You forgot something.&rdquo;</b></td>
          <td>It is there, it just wants a parameter. Counts as good.</td></tr>
      <tr><td><i style="background:var(--bad)"></i></td>
          <td><b>&ldquo;No such thing here.&rdquo;</b></td>
          <td>They wrote it in their own docs but it does not exist. Counts as bad.</td></tr>
      <tr><td><i style="background:var(--warn)"></i></td>
          <td><b>&ldquo;Wrong way to ask.&rdquo;</b></td>
          <td>Our mistake, not theirs. Left out of the score entirely.</td></tr>
      <tr><td><i style="background:var(--none-bg)"></i></td>
          <td><b>Cannot be checked this way.</b></td>
          <td>Live feeds, or addresses needing an ID we do not have. Left out.</td></tr>
    </table>

    <p class="example"><b>Markets &amp; prices, 64%.</b> 16 addresses published, 5 not
    checkable by a simple call, 7 of the remaining 11 answered. 7/11 = 64%.</p>

    <p><b>&ldquo;Checks&rdquo; is a different number again.</b> An address answering does
    not mean the answer is <em>correct</em>. <b>100% with no checks</b> means
    &ldquo;it is alive, and nobody has verified a word it says&rdquo;.</p>
  </div>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// "PASSING (UNPINNED)" -> "s-passing-unpinned". The old version replaced only
// spaces, so the class came out as s-passing-(unpinned) -- parentheses are not
// valid in a bare CSS class selector, so no rule could ever match it and the
// chip rendered unstyled however many rules were written.
const stateClass = s =>
  "s-" + String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const SEV = [
  ["S0-CUSTODY","custody / auth","s0"], ["S1-INTEGRITY","data integrity","s1"],
  ["S2-MEASUREMENT","measurement","s2"], ["S3-CONTRACT","contract","s3"],
  ["S4-COSMETIC","cosmetic","s4"],
];

document.getElementById("meta").innerHTML = [
  ["run", D.run_id || "—"],
  ["fingerprint", D.fingerprint || "—"],
  ["documented paths", D.totals.paths_documented ?? "—"],
  ["MCP tools anon / trusted", `${D.totals.tools_served_anon ?? "—"} / ${D.totals.tools_served_trusted ?? "—"}`],
  ["messages sent / received", `${D.thread_counts.sent ?? 0} / ${D.thread_counts.received ?? 0}`],
  ["generated", D.generated_at.replace("T"," ").replace("+00:00","Z")],
].map(([k,v]) => `<span><b>${esc(k)}</b> ${esc(v)}</span>`).join("");

document.getElementById("triage").innerHTML =
  SEV.map(([k,l,c]) => `<div class="tri ${c}"><div class="n">${D.by_severity[k]||0}</div><div class="l">${l}</div></div>`).join("")
  + `<div class="tri"><div class="n">${D.sections.filter(s=>!(s.checks&&s.checks.total)).length}</div><div class="l">sections with no checks</div></div>`
  + `<div class="tri"><div class="n">${D.findings.filter(f=>f.filed&&f.filed.length).length}</div><div class="l">filed to their tracker</div></div>`
  + `<div class="tri ok"><div class="n">${D.display_counts["VERIFIED FIXED"]||0}</div><div class="l">verified fixed by us</div></div>`
  + `<div class="tri"><div class="n">${D.display_counts["FIX CLAIMED"]||0}</div><div class="l">fix claimed, unverified</div></div>`;

/* ---------- section map, grouped by product area ---------- */
function health(s) {
  if (s.finding_severities.some(v => v === "S0-CUSTODY" || v === "S1-INTEGRITY")) return "h-bad";
  if (s.reachable_pct == null) return "h-none";
  if (s.reachable_pct < 60) return "h-bad";
  if (s.reachable_pct < 90 || s.finding_severities.length) return "h-warn";
  return "h-ok";
}
// What each bar segment and each verdict actually means, in the operator's
// words. "ok 6, method 1, unprobed 3" told nobody anything.
const VERDICT_WORDS = {
  ok:        "answers properly",
  auth:      "asks for a key -- the lock works",
  param:     "wants a parameter we did not send",
  method:    "we asked the wrong way (our fault, left out of the score)",
  missing:   "documented, but there is nothing there",
  unprobed:  "cannot be checked by a simple call",
  websocket: "a live feed, not a request",
};
const ORDER = ["ok","auth","param","method","missing","unprobed","websocket"];

function card(s) {
  const h = health(s);
  const total = ORDER.reduce((a,k) => a + (s.verdicts[k]||0), 0) || 1;
  const bar = ORDER.filter(k => s.verdicts[k]).map(k =>
    `<span class="seg-${k}" style="width:${(s.verdicts[k]/total*100).toFixed(2)}%"
      title="${s.verdicts[k]} ${VERDICT_WORDS[k]}"></span>`).join("");

  const legend = ORDER.filter(k => s.verdicts[k]).map(k =>
    `<span class="blabel"><i class="seg-${k}"></i>${s.verdicts[k]} ${VERDICT_WORDS[k]}</span>`
  ).join("");

  const pct = s.reachable_pct == null
    ? `<div class="pct-wrap"><span class="pct h-none">not checkable</span>
       <span class="pct-cap">nothing here answers a simple call</span></div>`
    : `<div class="pct-wrap"><span class="pct ${h}">${s.reachable_pct}<small>%</small></span>
       <span class="pct-cap">${s.endpoints_reachable} of ${s.endpoints_probed}
       published addresses answer</span></div>`;

  const checks = s.checks && s.checks.total
    ? `<span class="chip ${s.checks.failed ? "bad" : "ok"}">${s.checks.total} tests written${s.checks.failed ? ", "+s.checks.failed+" failing" : ""}</span>`
    : `<span class="chip untested">0 tests written</span>`;
  const sev = {};
  s.finding_severities.forEach(v => { sev[v] = (sev[v]||0)+1; });
  const fnd = Object.entries(sev).map(([k,n]) =>
    `<span class="chip ${/^S[01]/.test(k) ? "bad" : /^S4/.test(k) ? "" : "warn"}">${n}&times; ${k.split("-")[0]}</span>`).join("");

  // Every address behind the number, so the percentage can be checked rather
  // than believed. Grouped by what happened, worst first.
  const byVerdict = {};
  (s.endpoint_detail || []).forEach(e => {
    (byVerdict[e.verdict] = byVerdict[e.verdict] || []).push(e);
  });
  const detail = ["missing","param","method","auth","ok","unprobed","websocket"]
    .filter(k => byVerdict[k]).map(k => `
      <div class="epgroup">
        <div class="epgroup-h"><i class="seg-${k}"></i>${byVerdict[k].length}
          ${VERDICT_WORDS[k]}</div>
        ${byVerdict[k].map(e => `<div class="ep">
          <code>${esc(e.path)}</code>
          <span class="ep-meta">${esc((e.methods||["GET"]).join(", "))}
            ${e.status_anon != null ? "&middot; anon " + e.status_anon : ""}
            ${e.status_trusted != null && e.status_trusted !== e.status_anon
               ? "&middot; with key " + e.status_trusted : ""}
            ${e.sources && e.sources.length ? "&middot; from " + esc(e.sources.join(", ")) : ""}
          </span></div>`).join("")}
      </div>`).join("");

  return `<details class="card ${h}">
    <summary>
      <div class="card-top"><h3>${esc(s.title)}</h3>${pct}</div>
      <div class="blegend">${legend}</div>
      <p class="blurb">${esc(s.blurb)}</p>
      <div class="stats">
        <span class="chip">${s.endpoints_documented} addresses published</span>
        ${s.tools_declared ? `<span class="chip">${s.tools_declared} MCP tools</span>` : ""}
        ${s.verdicts.missing ? `<span class="chip bad">${s.verdicts.missing} &times; not there</span>` : ""}
        ${checks}${fnd}
      </div>
    </summary>
    <div class="card-detail">${detail || "<p class=\"blurb\">Nothing documented here.</p>"}</div>
  </details>`;
}
document.getElementById("map").innerHTML = D.groups.map(g => {
  const items = D.sections.filter(s => g.sections.includes(s.id));
  if (!items.length) return "";
  items.sort((a,b) => (a.reachable_pct ?? 999) - (b.reachable_pct ?? 999));
  return `<h2 class="group"><span class="tagchip">${esc(g.tag)}</span>${esc(g.title)}</h2>
          <p class="group-note">${esc(g.blurb)}</p>
          <div class="grid">${items.map(card).join("")}</div>`;
}).join("");

/* ---------- findings: the conversation through THEIR API ---------- */
// Only the bounty API. Telegram is a different channel with different
// properties -- attachments silently dropped, delivery unconfirmable -- and
// mixing them produced a panel where a message nobody received sat beside a
// report they had answered, as if both were the same kind of fact.
function conversation(f) {
  const when = t => t ? t.replace("T", " ").slice(0, 16) : "";

  if (!f.thread || !f.thread.length) {
    return `<h4 class="sec">Conversation with Cymetica</h4>
      <div class="awaiting">Not filed to their tracker yet.</div>`;
  }

  const bubbles = f.thread.map(m => {
    const head = m.who === "us"
      ? `<b>We filed report #${m.report_id}</b>`
      : `<b>They answered</b> <span class="chat-status">${esc(m.status || "")}</span>`;
    const body = m.who === "us"
      ? [m.title && `<div class="chat-title">${esc(m.title)}</div>`,
         m.text && `<p>${esc(m.text)}</p>`,
         m.expected && `<p><b>Expected.</b> ${esc(m.expected)}</p>`,
         m.actual && `<p><b>Actually.</b> ${esc(m.actual)}</p>`].filter(Boolean).join("")
      : (m.text ? `<p>${esc(m.text)}</p>`
                : `<p class="chat-quiet">Status changed with no note.</p>`);
    return `<div class="chat ${m.who}">
      <div class="chat-meta">${head}<time>${esc(when(m.at))}</time></div>
      <div class="chat-body">${body}</div></div>`;
  }).join("");

  // Said once, under the thread, rather than under every message.
  const note = f.verification
    ? `<div class="chat-note ok"><b>We re-ran the test and it passes.</b>
       ${esc(when(f.verification.at))} by run <code>${esc(f.verification.run_id)}</code>.
       ${f.thread.some(m => m.who === "them" && /fix|resolv|complet|clos/i.test(m.status || ""))
         ? "Their claim and our measurement agree, which is what closes it."
         : "They never claimed a fix for this one; our own test is what closes it."}</div>`
    : f.regressions && f.regressions.length
    ? `<div class="chat-note bad"><b>This was fixed and has broken again</b>
       (run <code>${esc(f.regressions[f.regressions.length-1].run_id)}</code>).</div>`
    : f.thread.some(m => m.who === "them")
    ? `<div class="chat-note">Their answer is a claim until our own test passes.</div>`
    : `<div class="chat-note">Filed, no answer yet.</div>`;

  return `<h4 class="sec">Conversation with Cymetica</h4>${bubbles}${note}`;
}

// One bounty report can cover several findings -- #51 carried both the skill
// ids and the skill count. Without saying so, two rows show the same number
// and it reads as a collision.
function sharedWith(f, reportId) {
  return D.findings
    .filter(o => o.id !== f.id && (o.filed || []).some(x => x.report_id === reportId))
    .map(o => o.id);
}

function finding(f) {
  const numbers = Object.entries(f.detail || {})
    .filter(([k]) => k !== "reason")
    .map(([k,v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");

  // The header carries only what identifies and prioritises the row. The
  // report number, the internal kind word and the id moved inside: they are
  // reference data, and on the summary line they read as though "#51" and
  // "CYM-skill_ids" were competing names for the same thing.
  return `<details class="finding" data-sev="${esc(f.severity)}" data-tag="${esc(f.tag)}">
    <summary>
      <span class="sev ${f.severity.split("-")[0]}">${esc(f.severity.split("-")[0])}</span>
      <span>
        <span class="f-title">${esc(f.title)}</span>
        <div class="f-sub">
          <span class="tagchip">${esc(f.tag)}</span>
          <span class="state ${stateClass(f.display_state)}">${esc(f.display_state)}</span>
          ${f.filed && f.filed.length ? `<span class="filed">${f.filed.map(x=>"#"+x.report_id).join(", ")}</span>` : ""}
          ${f.unmeasured ? `<span class="unmeasured" title="The wording and numbers here are from the day this was written; no run since has confirmed they still hold.">figures not re-measured</span>` : ""}
        </div>
      </span>
    </summary>
    <div class="f-body">
      ${f.summary ? `<p class="f-lede">${esc(f.summary)}</p>` : ""}
      ${f.withdrawn_reason ? `<p class="f-note"><b>We withdrew this.</b> ${esc(f.withdrawn_reason)}</p>` : ""}
      ${f.note ? `<p class="f-note">${esc(f.note)}</p>` : ""}
      ${conversation(f)}
      <div class="f-ref">
        <div><span class="ref-k">Our name for it</span>
             <span class="ref-v mono">${esc(f.id)}</span></div>
        ${f.filed && f.filed.length ? `<div><span class="ref-k">Their report number</span>
             <span class="ref-v mono">${f.filed.map(x => "#" + x.report_id +
               (sharedWith(f, x.report_id).length
                 ? ` <span class="ref-note">(one report, filed together with ` +
                   sharedWith(f, x.report_id).map(esc).join(", ") + `)</span>` : "")
             ).join(", ")}</span></div>` : ""}
        <div><span class="ref-k">Test that decides it</span>
             <span class="ref-v mono">${(f.checks||[]).map(esc).join("<br>") || "&mdash; none, so nothing can settle this"}</span></div>
        ${numbers ? `<div><span class="ref-k">What was measured</span>
             <span class="ref-v"><table class="kvt">${numbers}</table></span></div>` : ""}
      </div>
    </div></details>`;
}

const box = document.getElementById("findings");
box.innerHTML = D.findings.map(finding).join("");

const sevCounts = {}, tagCounts = {};
D.findings.forEach(f => {
  sevCounts[f.severity] = (sevCounts[f.severity]||0)+1;
  tagCounts[f.tag] = (tagCounts[f.tag]||0)+1;
});
document.getElementById("filters").innerHTML =
  // Labelled, because two unlabelled rows of buttons filtering different
  // things is a puzzle: one row is how much damage, the other is which part
  // of the platform, and nothing on screen said so.
  `<button data-kind="all" aria-pressed="true">all &middot; ${D.findings.length}</button>`
  + `<span class="sep"></span><span class="fl">damage</span>`
  + SEV.filter(s => sevCounts[s[0]]).map(s =>
      `<button data-kind="sev" data-v="${s[0]}" aria-pressed="false">${s[1]} &middot; ${sevCounts[s[0]]}</button>`).join("")
  + `<span class="sep"></span><span class="fl">area</span>`
  + D.groups.filter(g => tagCounts[g.tag]).map(g =>
      `<button data-kind="tag" data-v="${g.tag}" aria-pressed="false">${g.tag} &middot; ${tagCounts[g.tag]}</button>`).join("");

/* ---------- legend: the composition table, drawn from the real one ---------- */
// Plain-language gloss for each axis value. Six words or fewer: the point of
// the diagram is that you do not have to read.
const CHECK_WORDS = {
  UNVERIFIED:        ["no valid run has looked yet", "grey"],
  REPRODUCING:       ["we ran it &mdash; still broken", "bad"],
  PASSING:           ["we ran it &mdash; it passes", "ok"],
  PASSING_UNPINNED:  ["passes, but never seen failing", "teal"],
  INCONCLUSIVE:      ["the check measured nothing", "grey"],
  UNVERIFIABLE:      ["no check can answer this", "grey"],
};
const FILING_WORDS = {
  NOT_RAISED:  "not sent to them",
  RAISED:      "filed &mdash; no answer yet",
  REPLIED:     "they answered",
  FIX_CLAIMED: "they say it is fixed",
};
const TERMINAL_WORDS = {
  WITHDRAWN:  "we took it back: we were wrong",
  SUPERSEDED: "replaced by another finding",
};

const C = D.composition;
const short = s => s.replace(/_/g, " ");

document.getElementById("axes").innerHTML = `
  <div class="axes">
    <div class="axis">
      <div class="axis-h">What <b>we</b> measured</div>
      <div class="axis-sub">changes only when a proper test run actually ran this check</div>
      ${C.check_states.map(s => `<div class="axis-row">
        <span class="axv">${esc(short(s))}</span>
        <span>${CHECK_WORDS[s] ? CHECK_WORDS[s][0] : ""}</span></div>`).join("")}
    </div>
    <div class="axis-join">&times;</div>
    <div class="axis">
      <div class="axis-h">Where it stands <b>with them</b></div>
      <div class="axis-sub">changes only when a message or their tracker says so</div>
      ${C.filing_states.map(s => `<div class="axis-row">
        <span class="axv">${esc(short(s))}</span>
        <span>${FILING_WORDS[s] || ""}</span></div>`).join("")}
    </div>
  </div>`;

document.getElementById("matrix").innerHTML = `
  <div class="matrix-wrap"><table class="matrix">
    <tr><td></td>${C.filing_states.map(f =>
      `<th>${esc(short(f))}</th>`).join("")}</tr>
    ${C.check_states.map(c => `<tr>
      <th>${esc(short(c))}</th>
      ${C.filing_states.map(f => {
        const v = C.table[c][f];
        return `<td><span class="state ${stateClass(v)}">${esc(v)}</span></td>`;
      }).join("")}
    </tr>`).join("")}
  </table></div>
  <div class="matrix-note">
    ${C.terminal.map(t => `<span><span class="state ${stateClass(t)}">${esc(t)}</span>
      ${TERMINAL_WORDS[t] || ""} &mdash; ours, final, whatever the check says</span>`).join("")}
  </div>`;

// Everything on a finding row that is NOT a state. The operator hit exactly
// this: an unexplained "figures not re-measured" beside a badge, with the
// legend explaining only the badge. Five marks share that line; explaining one
// of them is worse than explaining none, because it implies the rest are
// obvious.
const MARKS = [
  [`<span class="tagchip">MCP</span>`,
   "which part of the platform this belongs to"],
  [`<span class="unmeasured-demo">figures not re-measured</span>`,
   "the wording and numbers here are from the day the finding was written, and no run since has confirmed they still hold &mdash; read them as history, not as today"],
  [`<span class="filed">filed as #46</span>`,
   "the report number it has with them"],
  [`<span class="undelivered">1 message never delivered</span>`,
   "we sent it and nobody ever confirmed it arrived"],
  [`<span class="mono-faint">contradiction</span>`,
   "how it was found: sources disagreeing, a check failing, or the reporting channel itself"],
  [`<span class="mono-faint">CYM-mcp_resource_count</span>`,
   "our id for it &mdash; the same id in every report and every message"],
];

document.getElementById("marks").innerHTML = `
  <div class="axis marks">
    ${MARKS.map(([chip, words]) =>
      `<div class="axis-row">${chip}<span>${words}</span></div>`).join("")}
  </div>`;

// Severity is blast radius: what breaks if this is real. It is not confidence,
// and it is not urgency. The colours on the page are these.
const SEV_WORDS = [
  ["S0", "s0", "money, keys, or who is allowed to do what"],
  ["S1", "s1", "wrong data that someone would act on"],
  ["S2", "s2", "counts or labels that mislead"],
  ["S3", "s3", "their documentation disagrees with their platform"],
  ["S4", "s4", "cosmetic"],
];
document.getElementById("sevs").innerHTML = `
  <div class="axis marks">
    ${SEV_WORDS.map(([k, cls, words]) =>
      `<div class="axis-row"><span class="sev ${cls}">${k}</span>
       <span>${words}</span></div>`).join("")}
  </div>`;

const CARD_MARKS = [
  [`<span class="chip">10 addresses published</span>`,
   "URLs their own documentation lists for this part"],
  [`<span class="chip">3 MCP tools</span>`,
   "tools declared for it in the MCP manifest"],
  [`<span class="chip bad">4 &times; not there</span>`,
   "of those addresses, how many answer 404"],
  [`<span class="chip untested">0 tests written</span>`,
   "checks we have written here &mdash; zero means nobody has verified a word this part says, however green the percentage is"],
  [`<span class="chip ok">6 tests written, 1 failing</span>`,
   "the same count once checks exist"],
  [`<span class="chip warn">1&times; S2</span>`,
   "an open finding in this part, at that damage level"],
];
document.getElementById("cardmarks").innerHTML = `
  <div class="axis marks">
    ${CARD_MARKS.map(([chip, words]) =>
      `<div class="axis-row">${chip}<span>${words}</span></div>`).join("")}
  </div>`;

document.getElementById("filters").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  document.querySelectorAll("#filters button").forEach(b =>
    b.setAttribute("aria-pressed", String(b === btn)));
  const kind = btn.dataset.kind, want = btn.dataset.v;
  box.querySelectorAll(".finding").forEach(el => {
    el.hidden = kind !== "all" &&
      (kind === "sev" ? el.dataset.sev !== want : el.dataset.tag !== want);
  });
});
</script>
"""


def payload_hash(payload: dict) -> str:
    """A stable hash of everything the page shows, minus when it was made.

    Embedded in the rendered file so a committed dashboard can be checked
    against a re-render (critique gap 9). Without it, nothing catches a
    dashboard that has fallen behind the ledger it claims to display --
    exactly the drift behind 16 rows on the filter, 6 in the tiles and 20 in
    the ledger.
    """
    import hashlib

    stable = {k: v for k, v in payload.items() if k != "generated_at"}
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False)
    # The template is part of what the page shows. Hashing only the data let a
    # presentation change land in the code with the committed page still built
    # from the old template, and rule 12's check saw nothing -- which is how
    # nine unstyled state chips could have survived a re-render.
    blob += "\n" + hashlib.sha256(TEMPLATE.encode("utf-8")).hexdigest()
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def render(payload: dict | None = None) -> str:
    payload = payload if payload is not None else build_payload()
    digest = payload_hash(payload)
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (TEMPLATE.replace("__DATA__", data)
            + f"\n<!-- qa-payload-sha256: {digest} -->\n")


if __name__ == "__main__":
    target = out_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    target.write_text(render(payload), encoding="utf-8")
    try:
        shown = target.relative_to(REPO_ROOT)
    except ValueError:
        shown = target
    print(f"-> {shown}  ({target.stat().st_size // 1024} KB)")
    print(f"   payload sha256 {payload_hash(payload)[:16]}  "
          f"{sum(payload['display_counts'].values())} rows  "
          f"run {payload['run_id'] or '(none admissible)'} "
          f"at level {payload['run_level']}")
