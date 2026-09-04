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
    path = STATE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def latest_run() -> dict:
    runs = sorted((STATE / "runs").glob("run-*.json"))
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else {}


def build_payload() -> dict:
    inventory = load("inventory.json")
    thread = load("thread.json")
    run = latest_run()

    # The ledger, not the current run, is the source of truth for findings.
    # A finding whose check has started passing must still appear -- as
    # VERIFIED FIXED, the one state that means "we checked" rather than "they
    # said". Deriving the list from what is currently failing would delete
    # exactly the records worth keeping.
    from scripts.ledger import as_findings, load_ledger
    ledger = load_ledger()
    findings = {"findings": as_findings(ledger),
                "by_severity": {}}
    for f in findings["findings"]:
        if f.get("state") != "VERIFIED FIXED":
            findings["by_severity"][f["severity"]] =                 findings["by_severity"].get(f["severity"], 0) + 1

    checks: dict[str, dict[str, int]] = {}
    for result in run.get("results", []):
        section = COMPONENT_TO_SECTION.get(result.get("component", ""), "_other")
        bucket = checks.setdefault(
            section, {"passed": 0, "failed": 0, "inconclusive": 0, "total": 0})
        bucket["total"] += 1
        if result.get("outcome") in bucket:
            bucket[result["outcome"]] += 1

    by_section: dict[str, list[str]] = {}
    for finding in findings.get("findings", []):
        if finding.get("state") == "VERIFIED FIXED":
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

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run.get("run_id"),
        "fingerprint": (run.get("platform_fingerprint") or "")[:23],
        "totals": inventory.get("totals", {}),
        "sections": sections,
        "findings": findings.get("findings", []),
        "by_severity": findings.get("by_severity", {}),
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
.state.s-not-raised-yet { background:var(--none-bg); color:var(--text-dim); }
.state.s-raised { background:var(--auth-bg); color:var(--auth); }
.state.s-they-replied { background:var(--wait-bg); color:var(--wait); }
.state.s-fix-claimed { background:var(--warn-bg); color:var(--warn); }
.state.s-verified { background:var(--ok-bg); color:var(--ok); }
.filed { font-family:var(--mono); font-size:11px; color:var(--text-faint); }
.undelivered {
  font-family:var(--mono); font-size:10px; font-weight:600; padding:2px 6px;
  border-radius:4px; background:var(--bad-bg); color:var(--bad); white-space:nowrap;
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

    <p><b>The big percentage answers one question:</b> of all the addresses Cymetica
    publishes for this part of the platform, how many actually answer when you call them?</p>

    <p>We call each address twice &mdash; once with no key, once with the API key &mdash;
    and take the better of the two answers. Then each address lands in one of these:</p>

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

    <p class="example"><b>Worked example &mdash; Markets &amp; prices, 64%.</b> It publishes
    16 addresses. Five could not be checked with a simple call, leaving 11. Of those, seven
    answered properly and four said &ldquo;no such thing here&rdquo;. Seven out of eleven is 64%.</p>

    <p><b>&ldquo;Checks&rdquo; is a completely different number</b>, and most cards say
    <em>no checks yet</em>. It counts the real tests written for that part. An address
    answering does not mean the answer is <em>correct</em> &mdash; 100% with no checks means
    &ldquo;it is alive, and nobody has verified a word it says&rdquo;. Those two things are kept
    apart on purpose: merging them would hide the gap that is actually worth acting on.</p>

    <p><b>So this page does not tell you</b> whether the numbers Cymetica returns are right,
    whether the locks are on the right doors, or whether anything behaves the way they
    documented. That is what the checks are for, and that is the work still ahead.</p>
  </div>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
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
  + `<div class="tri ok"><div class="n">${D.findings.filter(f=>f.state==="VERIFIED FIXED").length}</div><div class="l">verified fixed by us</div></div>`
  + `<div class="tri"><div class="n">${D.findings.filter(f=>f.state==="FIX CLAIMED").length}</div><div class="l">fix claimed, unverified</div></div>`;

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
    `report #${x.report_id}${x.status ? ` — ${esc(x.status)}` : ""}` +
    `${x.submitted_at ? ` — filed ${x.submitted_at.replace("T"," ").slice(0,16)}Z` : ""}`
  ).join("<br>");
  return `<div class="awaiting">Filed to their bug tracker via the API:<br>${rows}
    <br><br>A status of <em>fixed</em> here is a claim, not a verification. It becomes
    verified only when the check below is re-run and passes.</div>`;
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
    const text = m.excerpt || ("(this message references the finding but no section was "
      + "mapped to it — see " + m.file + ")");
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
          <span class="state s-${esc(f.state.toLowerCase().replace(/ /g,"-"))}">${esc(f.state)}</span>
          ${f.filed && f.filed.length ? `<span class="filed">filed as #${f.filed.map(x=>x.report_id).join(", #")}</span>` : ""}
          ${f.undelivered ? `<span class="undelivered">${f.undelivered} message never delivered</span>` : ""}
          <span>${esc(f.id)}</span><span>${esc(f.kind)}</span>
        </div>
      </span>
    </summary>
    <div class="f-body">
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
  `<button data-kind="all" aria-pressed="true">all &middot; ${D.findings.length}</button>`
  + `<span class="sep"></span>`
  + SEV.filter(s => sevCounts[s[0]]).map(s =>
      `<button data-kind="sev" data-v="${s[0]}" aria-pressed="false">${s[1]} &middot; ${sevCounts[s[0]]}</button>`).join("")
  + `<span class="sep"></span>`
  + D.groups.filter(g => tagCounts[g.tag]).map(g =>
      `<button data-kind="tag" data-v="${g.tag}" aria-pressed="false">${g.tag} &middot; ${tagCounts[g.tag]}</button>`).join("");

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


def render() -> str:
    data = json.dumps(build_payload(), ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", data)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"-> {OUT.relative_to(REPO_ROOT)}  ({OUT.stat().st_size // 1024} KB)")
