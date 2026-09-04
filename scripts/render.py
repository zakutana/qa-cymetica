"""Render state/*.json into the operator dashboard.

The page is read-only by design: every control lives in the chat session with
the QA agent. What the dashboard owes the operator is an honest picture of
which parts of the platform are worth testing next.

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

STATE = REPO_ROOT / "state"
OUT = REPO_ROOT / "dashboard" / "index.html"


def load(name: str) -> dict:
    path = STATE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def latest_run() -> dict:
    runs = sorted((STATE / "runs").glob("run-*.json"))
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else {}


BLAST_GROUPS = [
    ("custody", "Money, keys and authorization",
     "A wrong belief here costs funds or access. Verified first, always."),
    ("integrity", "Data that drives decisions",
     "Prices, positions, market state. Wrong numbers here move real money indirectly."),
    ("measurement", "Counts, labels and documentation",
     "Misreads a dashboard rather than a wallet. Still a defect when a summary "
     "lets a reader infer something untrue."),
]


def build_payload() -> dict:
    inventory = load("inventory.json")
    findings = load("findings.json")
    run = latest_run()

    checks_by_section: dict[str, dict[str, int]] = {}
    component_to_section = {
        "reconciliation": "discovery", "discovery.wellknown": "discovery",
        "discovery.llmstxt": "discovery", "discovery.openapi": "discovery",
        "mcp.tools_list": "mcp", "mcp.protocol": "mcp",
        "mcp.trust_ladder": "identity_trust", "rest.agents": "agents",
        "rest.clob": "clob", "rest.markets": "markets", "rest.account": "account",
        "funding.withdraw": "funding", "funding.deposit": "funding",
        "platform.ai_native_proof": "provenance", "platform.status": "swaps",
        "meta.guard": "_meta", "meta.classifier": "_meta",
    }
    for result in run.get("results", []):
        section = component_to_section.get(result.get("component", ""), "_other")
        bucket = checks_by_section.setdefault(
            section, {"passed": 0, "failed": 0, "inconclusive": 0, "total": 0}
        )
        bucket["total"] += 1
        outcome = result.get("outcome")
        if outcome in bucket:
            bucket[outcome] += 1

    findings_by_section: dict[str, list[str]] = {}
    for finding in findings.get("findings", []):
        targets = set(finding.get("affected_sections") or [])
        targets.add(finding.get("section", "discovery"))
        for section in targets:
            findings_by_section.setdefault(section, []).append(finding["severity"])

    sections = []
    for section in inventory.get("sections", []):
        sid = section["id"]
        sections.append({
            **section,
            "checks": checks_by_section.get(sid, {}),
            "finding_severities": findings_by_section.get(sid, []),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run.get("run_id"),
        "fingerprint": (run.get("platform_fingerprint") or "")[:23],
        "totals": inventory.get("totals", {}),
        "tools": inventory.get("tools", {}),
        "sections": sections,
        "findings": findings.get("findings", []),
        "by_severity": findings.get("by_severity", {}),
        "blast_groups": BLAST_GROUPS,
        "run_totals": run.get("totals", {}),
    }


TEMPLATE = r"""<title>Cymetica QA Console</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {
  --bg:        #f6f7f6;
  --surface:   #ffffff;
  --surface-2: #eef1f0;
  --line:      #d5dbd9;
  --line-soft: #e6eae9;
  --text:      #10171a;
  --text-dim:  #5a6a6c;
  --text-faint:#8b9a9b;
  --accent:    #0d6b66;
  --accent-dim:#0d6b6622;

  --ok:      #17803d;
  --ok-bg:   #17803d1f;
  --auth:    #0e7490;
  --auth-bg: #0e74901f;
  --warn:    #9a6300;
  --warn-bg: #9a63001f;
  --bad:     #b3261e;
  --bad-bg:  #b3261e1f;
  --wait:    #6b3fc4;
  --wait-bg: #6b3fc41f;
  --none:    #9aa8a8;
  --none-bg: #9aa8a826;

  --radius: 7px;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:        #0c1214;
    --surface:   #121b1d;
    --surface-2: #182326;
    --line:      #243436;
    --line-soft: #1b282a;
    --text:      #e4ecea;
    --text-dim:  #93a5a5;
    --text-faint:#6a7b7c;
    --accent:    #4ecfc4;
    --accent-dim:#4ecfc422;
    --ok:      #4ec97a;  --ok-bg:   #4ec97a1f;
    --auth:    #45b8d6;  --auth-bg: #45b8d61f;
    --warn:    #e0a338;  --warn-bg: #e0a3381f;
    --bad:     #f2685e;  --bad-bg:  #f2685e1f;
    --wait:    #a98cf0;  --wait-bg: #a98cf01f;
    --none:    #647476;  --none-bg: #64747626;
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

* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: var(--sans); font-size: 15px; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 1240px; margin: 0 auto; padding: 32px 22px 80px; }

/* ---------- masthead ---------- */
.mast { border-bottom: 2px solid var(--text); padding-bottom: 14px; margin-bottom: 8px; }
.mast h1 {
  font-size: clamp(26px, 4vw, 38px); font-weight: 600; letter-spacing: -0.022em;
  margin: 0 0 4px; text-wrap: balance;
}
.mast .sub { color: var(--text-dim); font-size: 14.5px; max-width: 68ch; margin: 0; }
.meta {
  display: flex; flex-wrap: wrap; gap: 6px 20px; margin-top: 14px;
  font-family: var(--mono); font-size: 11.5px; color: var(--text-faint);
}
.meta b { color: var(--text-dim); font-weight: 500; }

/* ---------- triage strip ---------- */
.triage {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 1px; background: var(--line); border: 1px solid var(--line);
  border-radius: var(--radius); overflow: hidden; margin: 26px 0 10px;
}
.tri { background: var(--surface); padding: 13px 15px; }
.tri .n {
  font-family: var(--mono); font-size: 27px; font-weight: 600;
  line-height: 1.1; font-variant-numeric: tabular-nums;
}
.tri .l {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.09em;
  color: var(--text-faint); margin-top: 3px; font-weight: 600;
}
.tri.s0 .n { color: var(--bad); } .tri.s1 .n { color: var(--bad); }
.tri.s2 .n { color: var(--warn); } .tri.s3 .n { color: var(--warn); }
.tri.s4 .n { color: var(--text-dim); }

/* ---------- sections ---------- */
h2.group {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.13em;
  font-weight: 700; margin: 40px 0 3px; color: var(--text);
}
h2.group::before {
  content: ""; display: inline-block; width: 26px; height: 2px;
  background: var(--accent); vertical-align: middle; margin-right: 10px;
}
p.group-note { margin: 0 0 16px 36px; color: var(--text-dim); font-size: 13.5px; max-width: 72ch; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 12px; }

.card {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 15px 16px 14px;
  display: flex; flex-direction: column; gap: 10px;
  border-left: 3px solid var(--none);
}
.card.h-ok   { border-left-color: var(--ok); }
.card.h-warn { border-left-color: var(--warn); }
.card.h-bad  { border-left-color: var(--bad); }
.card.h-none { border-left-color: var(--none); }

.card-top { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.card h3 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
.pct {
  font-family: var(--mono); font-size: 25px; font-weight: 600; line-height: 1;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.pct.h-ok { color: var(--ok); } .pct.h-warn { color: var(--warn); }
.pct.h-bad { color: var(--bad); } .pct.h-none { color: var(--text-faint); font-size: 15px; }
.pct small { font-size: 12px; font-weight: 500; color: var(--text-faint); }

.bar { display: flex; height: 7px; border-radius: 3px; overflow: hidden; background: var(--surface-2); }
.bar span { display: block; }
.seg-ok { background: var(--ok); } .seg-auth { background: var(--auth); }
.seg-param { background: var(--auth); opacity: 0.6; }
.seg-method { background: var(--warn); } .seg-missing { background: var(--bad); }
.seg-unprobed, .seg-websocket {
  background: repeating-linear-gradient(135deg, var(--none-bg) 0 4px, transparent 4px 8px);
  box-shadow: inset 0 0 0 1px var(--none-bg);
}

.blurb { font-size: 12.8px; color: var(--text-dim); margin: 0; line-height: 1.5; }

.stats {
  display: flex; flex-wrap: wrap; gap: 5px; font-family: var(--mono); font-size: 11px;
}
.chip {
  border: 1px solid var(--line); border-radius: 4px; padding: 2px 6px;
  color: var(--text-dim); background: var(--surface-2); white-space: nowrap;
}
.chip.bad  { color: var(--bad);  border-color: transparent; background: var(--bad-bg); font-weight: 600; }
.chip.warn { color: var(--warn); border-color: transparent; background: var(--warn-bg); font-weight: 600; }
.chip.ok   { color: var(--ok);   border-color: transparent; background: var(--ok-bg); font-weight: 600; }
.chip.none { color: var(--text-faint); }

/* ---------- findings ---------- */
.filters { display: flex; flex-wrap: wrap; gap: 6px; margin: 18px 0 14px; }
.filters button {
  font-family: var(--mono); font-size: 11.5px; padding: 5px 11px; cursor: pointer;
  border: 1px solid var(--line); background: var(--surface); color: var(--text-dim);
  border-radius: 20px; font-weight: 500;
}
.filters button[aria-pressed="true"] {
  background: var(--text); color: var(--bg); border-color: var(--text);
}
.filters button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.finding {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); margin-bottom: 9px; overflow: hidden;
}
.finding > summary {
  cursor: pointer; padding: 13px 15px; display: grid;
  grid-template-columns: auto 1fr auto; gap: 12px; align-items: start;
  list-style: none;
}
.finding > summary::-webkit-details-marker { display: none; }
.finding > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.sev {
  font-family: var(--mono); font-size: 10px; font-weight: 600; padding: 3px 7px;
  border-radius: 4px; letter-spacing: 0.04em; white-space: nowrap; margin-top: 2px;
}
.sev.S0 { background: var(--bad-bg);  color: var(--bad); }
.sev.S1 { background: var(--bad-bg);  color: var(--bad); }
.sev.S2 { background: var(--warn-bg); color: var(--warn); }
.sev.S3 { background: var(--warn-bg); color: var(--warn); }
.sev.S4 { background: var(--none-bg); color: var(--text-dim); }
.f-title { font-weight: 500; font-size: 14.5px; line-height: 1.45; }
.f-id { font-family: var(--mono); font-size: 11px; color: var(--text-faint); margin-top: 3px; }
.f-kind {
  font-family: var(--mono); font-size: 10px; color: var(--text-faint);
  text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap; margin-top: 4px;
}
.f-body { padding: 0 15px 15px; border-top: 1px solid var(--line-soft); }
.f-note {
  font-size: 13.2px; color: var(--text-dim); margin: 12px 0 0;
  padding-left: 11px; border-left: 2px solid var(--accent-dim); max-width: 76ch;
}
.kv { margin-top: 12px; overflow-x: auto; }
.kv table { border-collapse: collapse; width: 100%; font-family: var(--mono); font-size: 12px; }
.kv td { padding: 4px 10px 4px 0; vertical-align: top; border-bottom: 1px solid var(--line-soft); }
.kv td:first-child { color: var(--text-faint); white-space: nowrap; width: 1%; }
.kv td:last-child { color: var(--text); word-break: break-word; }
.checks {
  margin-top: 11px; font-family: var(--mono); font-size: 11px; color: var(--text-faint);
  word-break: break-all;
}
.checks b { color: var(--text-dim); font-weight: 500; }

/* ---------- footer note ---------- */
.note {
  margin-top: 42px; padding: 18px 20px; border: 1px solid var(--line);
  border-radius: var(--radius); background: var(--surface); font-size: 13.5px;
  color: var(--text-dim); max-width: 80ch;
}
.note h3 { margin: 0 0 8px; font-size: 13px; color: var(--text); text-transform: uppercase; letter-spacing: 0.09em; }
.note p { margin: 0 0 9px; }
.note code { font-family: var(--mono); font-size: 12px; background: var(--surface-2); padding: 1px 5px; border-radius: 3px; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 12px; font-size: 12px; font-family: var(--mono); }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>

<div class="wrap">
  <header class="mast">
    <h1>Cymetica QA Console</h1>
    <p class="sub">Independent verification of the Cymetica / EventTrader API, MCP and discovery
    surfaces. Every number below was measured, not reported.</p>
    <div class="meta" id="meta"></div>
  </header>

  <div class="triage" id="triage"></div>

  <div id="map"></div>

  <h2 class="group" style="margin-top:44px">Findings</h2>
  <p class="group-note">Everything found so far, including defects in the platform's own
  documentation. Nothing here is marked fixed &mdash; only <em>verified against a named surface,
  at a named time, by a named check</em>.</p>
  <div class="filters" id="filters"></div>
  <div id="findings"></div>

  <div class="note">
    <h3>What these numbers mean</h3>
    <p><b>Reachability</b> is the share of each section's documented endpoints that answer
    correctly right now, measured by read-only GET at two identities (anonymous and TRUSTED).
    A <code>401</code> counts as healthy &mdash; the gate doing its job is not a defect. A
    <code>404</code> on an endpoint the platform documents does not.</p>
    <p><b>Checks</b> is how many real assertions exist about that section. It is deliberately
    a separate number: a section can be 100% reachable and entirely unverified, and merging
    the two would hide exactly the gap worth acting on.</p>
    <p><b>Not established by this page:</b> that reachable endpoints return correct data, that
    gated endpoints are gated for the right reasons, or that any documented behaviour matches
    what actually happens when called. Those need checks, and most sections have none yet.</p>
    <div class="legend">
      <span><i style="background:var(--ok)"></i>responds</span>
      <span><i style="background:var(--auth)"></i>correctly gated / needs params</span>
      <span><i style="background:var(--warn)"></i>wrong method documented</span>
      <span><i style="background:var(--bad)"></i>documented but 404</span>
      <span><i style="background:var(--none-bg)"></i>not probeable by GET</span>
    </div>
  </div>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ---- masthead meta ---- */
document.getElementById("meta").innerHTML = [
  ["run", D.run_id || "—"],
  ["fingerprint", D.fingerprint || "—"],
  ["documented paths", D.totals.paths_documented ?? "—"],
  ["MCP tools declared", D.totals.tools_declared ?? "—"],
  ["served anon / trusted", `${D.totals.tools_served_anon ?? "—"} / ${D.totals.tools_served_trusted ?? "—"}`],
  ["generated", D.generated_at.replace("T", " ").replace("+00:00", "Z")],
].map(([k, v]) => `<span><b>${esc(k)}</b> ${esc(v)}</span>`).join("");

/* ---- triage ---- */
const SEV = [
  ["S0-CUSTODY", "custody / auth", "s0"],
  ["S1-INTEGRITY", "data integrity", "s1"],
  ["S2-MEASUREMENT", "measurement", "s2"],
  ["S3-CONTRACT", "contract", "s3"],
  ["S4-COSMETIC", "cosmetic", "s4"],
];
document.getElementById("triage").innerHTML = SEV.map(([key, label, cls]) =>
  `<div class="tri ${cls}"><div class="n">${D.by_severity[key] || 0}</div><div class="l">${label}</div></div>`
).join("") + `<div class="tri"><div class="n">${D.sections.filter(s => !(s.checks && s.checks.total)).length}</div><div class="l">sections with no checks</div></div>`;

/* ---- section map ---- */
const ORDER = ["ok", "auth", "param", "method", "missing", "unprobed", "websocket"];
function health(s) {
  if (s.finding_severities.some(v => v === "S0-CUSTODY" || v === "S1-INTEGRITY")) return "h-bad";
  if (s.reachable_pct === null || s.reachable_pct === undefined) return "h-none";
  if (s.reachable_pct < 60) return "h-bad";
  if (s.reachable_pct < 90 || s.finding_severities.length) return "h-warn";
  return "h-ok";
}
function card(s) {
  const h = health(s);
  const total = ORDER.reduce((a, k) => a + (s.verdicts[k] || 0), 0) || 1;
  const bar = ORDER.filter(k => s.verdicts[k]).map(k =>
    `<span class="seg-${k}" style="width:${(s.verdicts[k] / total * 100).toFixed(2)}%" title="${k}: ${s.verdicts[k]}"></span>`).join("");

  const pct = (s.reachable_pct === null || s.reachable_pct === undefined)
    ? `<span class="pct h-none">no GET surface</span>`
    : `<span class="pct ${h}">${s.reachable_pct}<small>%</small></span>`;

  const checks = s.checks && s.checks.total
    ? `<span class="chip ${s.checks.failed ? "bad" : "ok"}">${s.checks.failed ? s.checks.failed + " failing / " : ""}${s.checks.total} checks</span>`
    : `<span class="chip none">no checks yet</span>`;

  const sev = {};
  s.finding_severities.forEach(v => { sev[v] = (sev[v] || 0) + 1; });
  const findings = Object.entries(sev).map(([k, n]) =>
    `<span class="chip ${k.startsWith("S0") || k.startsWith("S1") ? "bad" : k.startsWith("S4") ? "" : "warn"}">${n}&times; ${k.split("-")[0]}</span>`).join("");

  return `<article class="card ${h}">
    <div class="card-top"><h3>${esc(s.title)}</h3>${pct}</div>
    <div class="bar">${bar}</div>
    <p class="blurb">${esc(s.blurb)}</p>
    <div class="stats">
      <span class="chip">${s.endpoints_documented} paths</span>
      ${s.tools_declared ? `<span class="chip">${s.tools_declared} tools</span>` : ""}
      ${s.verdicts.missing ? `<span class="chip bad">${s.verdicts.missing} &times; 404</span>` : ""}
      ${checks}${findings}
    </div>
  </article>`;
}
document.getElementById("map").innerHTML = D.blast_groups.map(([id, title, note]) => {
  const items = D.sections.filter(s => s.blast === id);
  if (!items.length) return "";
  items.sort((a, b) => (a.reachable_pct ?? 999) - (b.reachable_pct ?? 999));
  return `<h2 class="group">${esc(title)}</h2><p class="group-note">${esc(note)}</p>
          <div class="grid">${items.map(card).join("")}</div>`;
}).join("");

/* ---- findings ---- */
function finding(f) {
  const rows = Object.entries(f.detail || {}).map(([k, v]) =>
    `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
  return `<details class="finding" data-sev="${esc(f.severity)}">
    <summary>
      <span class="sev ${f.severity.split("-")[0]}">${esc(f.severity.split("-")[0])}</span>
      <span><span class="f-title">${esc(f.title)}</span><div class="f-id">${esc(f.id)} · ${esc(f.component)}</div></span>
      <span class="f-kind">${esc(f.kind)}</span>
    </summary>
    <div class="f-body">
      ${f.note ? `<p class="f-note">${esc(f.note)}</p>` : ""}
      ${rows ? `<div class="kv"><table>${rows}</table></div>` : ""}
      <div class="checks"><b>check</b> ${(f.checks || []).map(esc).join("<br>")}</div>
    </div>
  </details>`;
}
const box = document.getElementById("findings");
box.innerHTML = D.findings.map(finding).join("");

const counts = {};
D.findings.forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1; });
const chips = [["all", D.findings.length]].concat(SEV.filter(s => counts[s[0]]).map(s => [s[0], counts[s[0]]]));
document.getElementById("filters").innerHTML = chips.map(([k, n], i) =>
  `<button data-sev="${esc(k)}" aria-pressed="${i === 0}">${esc(k === "all" ? "all" : k.split("-")[1].toLowerCase())} · ${n}</button>`).join("");

document.getElementById("filters").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  const want = btn.dataset.sev;
  document.querySelectorAll("#filters button").forEach(b =>
    b.setAttribute("aria-pressed", String(b === btn)));
  box.querySelectorAll(".finding").forEach(el =>
    el.hidden = !(want === "all" || el.dataset.sev === want));
});
</script>
"""


def render() -> str:
    payload = build_payload()
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", data)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"-> {OUT.relative_to(REPO_ROOT)}  ({OUT.stat().st_size // 1024} KB)")
