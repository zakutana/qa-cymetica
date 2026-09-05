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
    bodies = _message_bodies()
    messages: dict[str, list[dict]] = {}
    withdrawn_reason: dict[str, str] = {}
    filed_at: dict[int, str] = {}
    for event in events:
        etype = event.get("type")
        if etype in ("message", "reply"):
            msg_id = event.get("msg_id")
            source = bodies.get(msg_id, {})
            for fid in event.get("findings") or []:
                messages.setdefault(fid, []).append({
                    "msg_id": msg_id,
                    "direction": "in" if etype == "reply" else "out",
                    "at": event.get("at"),
                    "delivered": event.get("delivered", True) if etype == "message" else True,
                    "file": event.get("origin") or source.get("file"),
                    "channel": source.get("channel"),
                    "delivered_as": source.get("delivered_as"),
                    "delivery_note": source.get("delivery_note"),
                    # What this message actually said ABOUT THIS FINDING. The
                    # journal is the index of which messages touch a row; the
                    # words stay in the message files, where they were pasted
                    # verbatim.
                    "excerpt": _excerpt_for(source, fid),
                })
        elif etype == "withdraw" and event.get("finding_id"):
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
            "unmeasured": not (row.get("provenance") or {}).get("measured_at"),
            "filed": [
                {"report_id": r["report_id"], "status": r.get("status"),
                 "submitted_at": filed_at.get(r["report_id"])}
                for r in (row.get("filing") or {}).get("reports", [])
            ],
            "thread": sorted(messages.get(row["id"], []),
                             key=lambda m: m.get("at") or ""),
            "undelivered": sum(1 for m in messages.get(row["id"], [])
                               if m["direction"] == "out" and not m["delivered"]),
            "withdrawn_reason": withdrawn_reason.get(row["id"]),
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
  font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1240px; margin:0 auto; padding:32px 22px 80px; }

.mast { border-bottom:2px solid var(--text); padding-bottom:14px; }
.mast h1 {
  font-size:clamp(26px,4vw,38px); font-weight:600; letter-spacing:-0.022em;
  margin:0 0 4px; text-wrap:balance;
}
.mast .sub { color:var(--text-dim); font-size:14.5px; max-width:70ch; margin:0; }
.meta {
  display:flex; flex-wrap:wrap; gap:6px 20px; margin-top:14px;
  font-family:var(--mono); font-size:11.5px; color:var(--text-faint);
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
  font-size:10.5px; text-transform:uppercase; letter-spacing:0.09em;
  color:var(--text-faint); margin-top:3px; font-weight:600;
}
.tri.s0 .n,.tri.s1 .n { color:var(--bad); }
.tri.s2 .n,.tri.s3 .n { color:var(--warn); }
.tri.s4 .n { color:var(--text-dim); }
.tri.ok .n { color:var(--ok); }

h2.group {
  font-size:12px; text-transform:uppercase; letter-spacing:0.13em;
  font-weight:700; margin:38px 0 3px; display:flex; align-items:center; gap:10px;
}
.tagchip {
  font-family:var(--mono); font-size:10px; font-weight:600; letter-spacing:0.06em;
  padding:3px 7px; border-radius:4px; background:var(--accent-dim);
  color:var(--accent); white-space:nowrap;
}
p.group-note { margin:0 0 15px; color:var(--text-dim); font-size:13.5px; max-width:74ch; }

.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:12px; }
.card {
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
  padding:15px 16px 14px; display:flex; flex-direction:column; gap:10px;
  border-left:3px solid var(--none);
}
.card.h-ok{border-left-color:var(--ok)} .card.h-warn{border-left-color:var(--warn)}
.card.h-bad{border-left-color:var(--bad)} .card.h-none{border-left-color:var(--none)}
.card-top { display:flex; align-items:baseline; justify-content:space-between; gap:12px; }
.card h3 { margin:0; font-size:14.5px; font-weight:600; letter-spacing:-0.01em; }
.pct {
  font-family:var(--mono); font-size:25px; font-weight:600; line-height:1;
  font-variant-numeric:tabular-nums; white-space:nowrap;
}
.pct.h-ok{color:var(--ok)} .pct.h-warn{color:var(--warn)} .pct.h-bad{color:var(--bad)}
.pct.h-none{color:var(--text-faint); font-size:13px}
.pct small { font-size:12px; font-weight:500; color:var(--text-faint); }

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
  font-family:var(--mono); font-size:9.5px; color:var(--text-faint);
  white-space:nowrap; letter-spacing:.02em;
}
.chip.untested {
  color:var(--text-faint); background:transparent;
  border:1px dashed var(--line); font-weight:600;
}
.blurb { font-size:12.6px; color:var(--text-dim); margin:0; line-height:1.5; }
.stats { display:flex; flex-wrap:wrap; gap:5px; font-family:var(--mono); font-size:11px; }
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
  font-family:var(--mono); font-size:11.5px; padding:5px 11px; cursor:pointer;
  border:1px solid var(--line); background:var(--surface); color:var(--text-dim);
  border-radius:20px; font-weight:500;
}
.filters button[aria-pressed="true"] { background:var(--text); color:var(--bg); border-color:var(--text); }
.filters button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.filters .sep { width:1px; height:20px; background:var(--line); margin:0 5px; }
.filters .fl {
  font-family:var(--mono); font-size:10px; text-transform:uppercase;
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
  font-family:var(--mono); font-size:10px; font-weight:600; padding:3px 7px;
  border-radius:4px; letter-spacing:.04em; white-space:nowrap; margin-top:2px;
}
.sev.S0,.sev.S1 { background:var(--bad-bg); color:var(--bad); }
.sev.S2,.sev.S3 { background:var(--warn-bg); color:var(--warn); }
.sev.S4 { background:var(--none-bg); color:var(--text-dim); }
.f-title { font-weight:500; font-size:14.5px; line-height:1.45; }
.f-sub {
  font-family:var(--mono); font-size:11px; color:var(--text-faint); margin-top:5px;
  display:flex; flex-wrap:wrap; gap:5px 9px; align-items:center;
}
.state {
  font-family:var(--mono); font-size:10px; font-weight:600; padding:2px 6px;
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
.state.s-passing-unclaimed  { background:var(--accent-dim); color:var(--accent); }
.state.s-passing-never-raised { background:var(--accent-dim); color:var(--accent); }
.state.s-verified-fixed     { background:var(--ok-bg); color:var(--ok); }
.state.s-unverified         { background:var(--none-bg); color:var(--text-dim); }
.state.s-inconclusive       { background:var(--none-bg); color:var(--text-dim); }
.state.s-not-reproducible   { background:var(--none-bg); color:var(--text-dim); }
.state.s-unverifiable       { background:var(--none-bg); color:var(--text-dim); }
.state.s-withdrawn  { background:var(--none-bg); color:var(--text-faint); text-decoration:line-through; }
.state.s-superseded { background:var(--none-bg); color:var(--text-faint); text-decoration:line-through; }

.filed { font-family:var(--mono); font-size:11px; color:var(--text-faint); }
.undelivered {
  font-family:var(--mono); font-size:10px; font-weight:600; padding:2px 6px;
  border-radius:4px; background:var(--bad-bg); color:var(--bad); white-space:nowrap;
}
/* On 19 of 23 rows, so it must not shout. Red made it the loudest thing on
   the page and pushed the state chip -- the thing actually worth reading --
   into the background. It is a provenance note, not an alarm. */
.unmeasured, .unmeasured-demo {
  font-family:var(--mono); font-size:10px; padding:2px 6px; border-radius:4px;
  background:transparent; color:var(--text-faint);
  border:1px dashed var(--line); white-space:nowrap; cursor:help;
}
.unmeasured-demo { font-weight:400; cursor:default; }

/* ---------- legend: two axes, then the grid they make ---------- */
.lead { font-size:13.5px; color:var(--text-dim); max-width:74ch; margin:14px 0 10px; }
.lead .hi { color:var(--ok); font-weight:600; }

.axes { display:flex; gap:14px; align-items:stretch; flex-wrap:wrap; margin:14px 0 22px; }
.axis {
  flex:1 1 260px; min-width:0; background:var(--surface-2);
  border:1px solid var(--line-soft); border-radius:var(--radius); padding:12px 13px;
}
.axis-h { font-size:13px; font-weight:600; color:var(--text); }
.axis-h b { color:var(--accent); }
.axis-sub {
  font-size:11.5px; color:var(--text-faint); margin:2px 0 10px;
  padding-bottom:8px; border-bottom:1px solid var(--line-soft);
}
.axis-row {
  display:flex; gap:9px; align-items:baseline; margin:6px 0;
  font-size:12.4px; color:var(--text-dim);
}
/* An axis VALUE, not a display state. Deliberately its own class: reusing
   .state gave NOT_RAISED the class s-not-raised, which no rule matches --
   the same unstyled-chip problem one level up. These are inputs to the grid;
   the colours belong to the squares the grid produces. */
.axv {
  flex:0 0 auto; font-family:var(--mono); font-size:10px; font-weight:600;
  padding:2px 6px; border-radius:4px; white-space:nowrap;
  background:var(--none-bg); color:var(--text-dim);
}
.axis-join {
  align-self:center; font-family:var(--mono); font-size:22px; color:var(--text-faint);
}

.matrix-wrap { overflow-x:auto; margin:6px 0 10px; }
.matrix { border-collapse:separate; border-spacing:3px; font-size:11px; }
.matrix th {
  font-family:var(--mono); font-size:10px; font-weight:600; color:var(--text-faint);
  text-align:left; white-space:nowrap; padding:3px 6px; text-transform:uppercase;
  letter-spacing:.04em;
}
.matrix tr th:first-child { text-align:right; }
.matrix td { padding:0; }
.matrix .state { display:block; text-align:center; }
.matrix-note {
  display:flex; flex-direction:column; gap:5px; font-size:12.4px; color:var(--text-dim);
}
.marks { flex:none; margin:10px 0 20px; }
.marks .axis-row { align-items:baseline; margin:8px 0; }
.marks .axis-row > span:last-child { max-width:70ch; }
.mono-faint {
  font-family:var(--mono); font-size:11px; color:var(--text-faint); flex:0 0 auto;
}
.matrix-note span span.state { margin-right:7px; }

@media (max-width: 640px) {
  .axis-join { display:none; }
}

.f-body { padding:0 15px 15px; border-top:1px solid var(--line-soft); }
.f-note {
  font-size:13.2px; color:var(--text-dim); margin:12px 0 0; padding-left:11px;
  border-left:2px solid var(--accent-dim); max-width:78ch;
}
.kv { overflow-x:auto; }
.kv table { border-collapse:collapse; width:100%; font-family:var(--mono); font-size:12px; }
.kv td { padding:4px 10px 4px 0; vertical-align:top; border-bottom:1px solid var(--line-soft); }
.kv td:first-child { color:var(--text-faint); white-space:nowrap; width:1%; }
.kv td:last-child { color:var(--text); word-break:break-word; }
.checks {
  margin-top:13px; font-family:var(--mono); font-size:11px; color:var(--text-faint);
  word-break:break-all;
}
.checks b { color:var(--text-dim); font-weight:500; }

h4.sec {
  font-size:10.5px; text-transform:uppercase; letter-spacing:.1em; font-weight:700;
  color:var(--text-faint); margin:18px 0 8px;
}
.msg { border:1px solid var(--line-soft); border-radius:6px; margin-bottom:8px; overflow:hidden; }
.msg-head {
  display:flex; flex-wrap:wrap; gap:4px 10px; align-items:center; padding:8px 11px;
  background:var(--surface-2); font-family:var(--mono); font-size:11px; color:var(--text-faint);
}
.dir { font-weight:600; }
.dir.out { color:var(--auth); }
.dir.in  { color:var(--ok); }
.dir.dead { color:var(--bad); }
.msg pre {
  margin:0; padding:11px 13px; font-family:var(--mono); font-size:11.5px;
  line-height:1.6; white-space:pre-wrap; word-break:break-word; color:var(--text);
  max-height:360px; overflow:auto; background:var(--surface);
}
.awaiting {
  font-size:12.5px; color:var(--text-faint); padding:9px 11px;
  border:1px dashed var(--line); border-radius:6px; max-width:78ch;
}

.note {
  margin-top:42px; padding:18px 20px; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--surface); font-size:13.5px;
  color:var(--text-dim); max-width:82ch;
}
.note h3 { margin:0 0 8px; font-size:13px; color:var(--text); text-transform:uppercase; letter-spacing:.09em; }
.note p { margin:0 0 9px; }
.note code { font-family:var(--mono); font-size:12px; background:var(--surface-2); padding:1px 5px; border-radius:3px; }
.note .verdicts { border-collapse:collapse; margin:12px 0 16px; }
.note .verdicts td { padding:5px 12px 5px 0; vertical-align:top; font-size:13.2px; line-height:1.45; }
.note .verdicts td:first-child { width:1%; padding-right:9px; padding-top:9px; }
.note .verdicts td:nth-child(2) { white-space:nowrap; color:var(--text); }
.note .verdicts i {
  display:inline-block; width:10px; height:10px; border-radius:2px;
  box-shadow:inset 0 0 0 1px var(--line);
}
.note .verdicts i.faint { opacity:.6; }
.note .example {
  background:var(--surface-2); border-radius:6px; padding:11px 13px;
  border-left:2px solid var(--accent); font-size:13.2px;
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
const ORDER = ["ok","auth","param","method","missing","unprobed","websocket"];
function health(s) {
  if (s.finding_severities.some(v => v === "S0-CUSTODY" || v === "S1-INTEGRITY")) return "h-bad";
  if (s.reachable_pct == null) return "h-none";
  if (s.reachable_pct < 60) return "h-bad";
  if (s.reachable_pct < 90 || s.finding_severities.length) return "h-warn";
  return "h-ok";
}
function card(s) {
  const h = health(s);
  const total = ORDER.reduce((a,k) => a + (s.verdicts[k]||0), 0) || 1;
  const bar = ORDER.filter(k => s.verdicts[k]).map(k =>
    `<span class="seg-${k}" style="width:${(s.verdicts[k]/total*100).toFixed(2)}%" title="${k}: ${s.verdicts[k]}"></span>`).join("");
  const pct = s.reachable_pct == null
    ? `<div class="pct-wrap"><span class="pct h-none">not checkable</span>
       <span class="pct-cap">nothing here answers a simple call</span></div>`
    : `<div class="pct-wrap"><span class="pct ${h}">${s.reachable_pct}<small>%</small></span>
       <span class="pct-cap">${s.endpoints_reachable} of ${s.endpoints_probed} answered</span></div>`;
  const checks = s.checks && s.checks.total
    ? `<span class="chip ${s.checks.failed ? "bad" : "ok"}">${s.checks.total} tests written${s.checks.failed ? ", "+s.checks.failed+" failing" : ""}</span>`
    : `<span class="chip untested">0 tests written</span>`;
  const sev = {};
  s.finding_severities.forEach(v => { sev[v] = (sev[v]||0)+1; });
  const fnd = Object.entries(sev).map(([k,n]) =>
    `<span class="chip ${/^S[01]/.test(k) ? "bad" : /^S4/.test(k) ? "" : "warn"}">${n}&times; ${k.split("-")[0]}</span>`).join("");
  return `<article class="card ${h}">
    <div class="card-top"><h3>${esc(s.title)}</h3>${pct}</div>
    <div class="bar">${bar}</div>
    <p class="blurb">${esc(s.blurb)}</p>
    <div class="stats">
      <span class="chip">${s.endpoints_documented} addresses published</span>
      ${s.tools_declared ? `<span class="chip">${s.tools_declared} MCP tools</span>` : ""}
      ${s.verdicts.missing ? `<span class="chip bad">${s.verdicts.missing} &times; not there</span>` : ""}
      ${checks}${fnd}
    </div></article>`;
}
document.getElementById("map").innerHTML = D.groups.map(g => {
  const items = D.sections.filter(s => g.sections.includes(s.id));
  if (!items.length) return "";
  items.sort((a,b) => (a.reachable_pct ?? 999) - (b.reachable_pct ?? 999));
  return `<h2 class="group"><span class="tagchip">${esc(g.tag)}</span>${esc(g.title)}</h2>
          <p class="group-note">${esc(g.blurb)}</p>
          <div class="grid">${items.map(card).join("")}</div>`;
}).join("");

/* ---------- findings, each carrying its correspondence ---------- */
function filedNote(f) {
  if (!f.filed || !f.filed.length) return "";
  const rows = f.filed.map(x =>
    `report #${x.report_id}${x.status ? ` &mdash; ${esc(x.status)}` : ""}` +
    `${x.submitted_at ? ` &mdash; filed ${x.submitted_at.replace("T"," ").slice(0,16)}Z` : ""}`
  ).join("<br>");
  // Printed from the adjudication or not at all. Ten rows once carried this
  // sentence with verified_by_run null on every one of them, and a timestamp
  // taken from the merge that wrote the row rather than from any run.
  const verdict =
    f.verification
      ? `<br><br><b>We re-ran the check and it passes.</b> Verified ${
          (f.verification.at || "").replace("T"," ").slice(0,16)}Z by run
         <code>${esc(f.verification.run_id)}</code> running
         <code>${esc(f.verification.nodeid || "-")}</code>. Their status above is
         their claim; this line is our own measurement, and the two agreeing is
         what closes it.`
      : f.regressions && f.regressions.length
      ? `<br><br><b>This was verified fixed and has started failing again</b>
         (run <code>${esc(f.regressions[f.regressions.length-1].run_id)}</code>).`
      : f.not_checked_in
      ? `<br><br>Not checked in run <code>${esc(f.not_checked_in)}</code> &mdash;
         that run did not collect this check, so it says nothing either way.`
      : `<br><br>A status of <em>fixed</em> here is their claim, not a verification.
         It becomes verified only once the check below is re-run and passes.`;
  return `<div class="awaiting">Filed to their bug tracker via the API:<br>${rows}${verdict}</div>`;
}

function thread(f) {
  if (!f.thread || !f.thread.length) {
    const filed = filedNote(f);
    return `<h4 class="sec">Correspondence</h4>` + (filed ||
      `<div class="awaiting">Not yet raised with the vendor.</div>`);
  }
  const rows = f.thread.map(m => {
    const dead = m.direction === "out" && m.delivered === false;
    const arrow = m.direction === "in" ? "← reply from vendor"
                : dead ? "✕ sent but NEVER DELIVERED" : "→ sent to vendor";
    const when = m.at ? m.at.replace("T"," ").slice(0,16) + "Z" : "not sent";
    const text = m.excerpt || ("This message names the finding but has no section "
      + "specifically about it." + (m.file ? "\nFull message: " + m.file : ""));
    return `<div class="msg"><div class="msg-head">
        <span class="dir ${dead ? "dead" : m.direction}">${arrow}</span>
        ${m.delivery_note ? `<span title="${esc(m.delivery_note)}">why</span>` : ""}
        <span>${esc(m.msg_id)}</span><span>${esc(when)}</span>
        <span>${esc(m.channel || "")}</span>
        ${m.delivered_as ? `<span>${esc(m.delivered_as)}</span>` : ""}
      </div><pre>${esc(text)}</pre></div>`;
  }).join("");
  const replies = f.thread.filter(m => m.direction === "in").length;
  const tail = replies ? "" :
    `<div class="awaiting">Sent, no reply yet. The finding stays open until they answer, and
     any answer claiming a fix is recorded as a claim until the failing check is re-run.</div>`;
  return `<h4 class="sec">Correspondence</h4>${rows}${filedNote(f)}${tail}`;
}

function finding(f) {
  const rows = Object.entries(f.detail || {}).map(([k,v]) =>
    `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
  return `<details class="finding" data-sev="${esc(f.severity)}" data-tag="${esc(f.tag)}">
    <summary>
      <span class="sev ${f.severity.split("-")[0]}">${esc(f.severity.split("-")[0])}</span>
      <span>
        <span class="f-title">${esc(f.title)}</span>
        <div class="f-sub">
          <span class="tagchip">${esc(f.tag)}</span>
          ${f.unmeasured ? `<span class="unmeasured" title="The title and figures on this row were carried over from the hand-written ledger when the pipeline was rebuilt. They were true when the finding was made and no admissible run has re-measured them since, so read them as history rather than as the current state. A run that adjudicates this row refreshes them.">figures not re-measured</span>` : ""}
          <span class="state ${stateClass(f.display_state)}">${esc(f.display_state)}</span>
          ${f.filed && f.filed.length ? `<span class="filed">filed as #${f.filed.map(x=>x.report_id).join(", #")}</span>` : ""}
          ${f.undelivered ? `<span class="undelivered">${f.undelivered} message never delivered</span>` : ""}
          <span>${esc(f.id)}</span><span>${esc(f.kind)}</span>
        </div>
      </span>
    </summary>
    <div class="f-body">
      ${f.withdrawn_reason ? `<p class="f-note"><b>Withdrawn by us.</b> ${esc(f.withdrawn_reason)}</p>` : ""}
      ${f.note ? `<p class="f-note">${esc(f.note)}</p>` : ""}
      ${rows ? `<h4 class="sec">Measured</h4><div class="kv"><table>${rows}</table></div>` : ""}
      ${thread(f)}
      <div class="checks"><b>check</b> ${(f.checks||[]).map(esc).join("<br>")}</div>
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
