"""What their public pages read without a key, an agent can find in the docs.

`/openapi-public.json` is the document Cymetica tells outside agents to import
(llms.txt, the agent card), and the platform sells itself as AI-native: "your
AI agents ... interact ... programmatically via our REST API, MCP tools and
SDKs" (/fund-performance). The operator's observation of 2026-09-24, kept in
NEXT.md: they ship pages and do not put what the pages call into the docs.

**What was seen when this was written** (2026-09-25): the 73 pages the home
page links to, with their own scripts, name 224 `/api/v1` paths absent from
`/openapi-public.json`. Most need a session -- account, funding, chat -- and a
public agent document may leave those out. But 61 of them answer HTTP 200 with
JSON to an anonymous GET: public data a visitor's browser reads and an agent
cannot discover. Among them `/api/v1/fta-fund/history` and
`/api/v1/ma-fund/history` (the charts on /fund-performance; MCP
`get_fund_history` refuses FTA-STOCKS with "see its page URL"),
`/api/v1/vaults/cymetica-42/trade-log`, `/api/v1/headlines`,
`/api/v1/agentbook/feed`, `/api/v1/microfunds`.

**The claim:** every such path either appears in `/openapi-public.json` (a
templated path counts) or stops answering an anonymous read. Passes when none
is left. What stays out of scope, deliberately:

  * a path with a template in the page's own string (`${id}`) -- we cannot
    choose an id for it without guessing;
  * a path whose last segments read as an action (buy, create, enter, ...):
    never called, whatever the method;
  * the plumbing no agent needs documented: CSRF token, push VAPID key,
    per-user "me" reads, analytics/telemetry beacons.

SAFE: GETs only -- of their pages, their scripts, and of read-shaped paths.
"""

from __future__ import annotations

import re
import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SITE = "https://cymetica.com"
SPEC = "/openapi-public.json"
PAUSE_S = 1.2
MAX_PAGES = 90
MAX_PROBES = 120

LINK = re.compile(r'href="(/[a-z0-9][a-z0-9\-/]*)"')
SCRIPT = re.compile(r'<script[^>]+src="(/static/js/[^"?]+)')
API = re.compile(r"(/api/v1/[A-Za-z0-9_\-/{}$.]*)")
ACTION = re.compile(
    r"/(enter|buy|sell|create|cancel|cancel-all|close|withdraw|withdraw-request|release|"
    r"commit|subscribe|equip|run|compile|send|connect|upload|apply|ask|submit|delete|"
    r"register|login|logout|reset|claim|redeem|deposit|mint|swap|vote|order|orders|"
    r"image|clone|toggle|enable|disable|pause|resume|fund|stake|unstake|arm|disarm)(/|$)")
PLUMBING = re.compile(r"csrf|vapid|telemetry|analytics|bootstrap|/me$|/me/|/account")


def documented_patterns(spec: dict) -> list[re.Pattern]:
    return [re.compile("^" + re.sub(r"\\{[^}]+\\}", "[^/]+", re.escape(p)) + "$")
            for p in (spec.get("paths") or {})]


def called_paths(text: str) -> set[str]:
    """The /api/v1 literals a page or script names, a `${...}` kept as a template."""
    return {re.sub(r"\$\{[^}]*\}", "{x}", m).rstrip("/.") for m in API.findall(text or "")}


def candidates(paths, documented: list[re.Pattern]) -> list[str]:
    """Undocumented, concrete, read-shaped, not plumbing."""
    out = []
    for path in sorted(set(paths)):
        if "{" in path or ACTION.search(path) or PLUMBING.search(path):
            continue
        if any(p.match(path) for p in documented):
            continue
        out.append(path)
    return out


@qa(component="discovery.openapi", tier=SafetyTier.SAFE, surface="rest")
def test_what_a_public_page_reads_without_a_key_is_documented(rest_anon):
    """Pages linked from home, their scripts, and each undocumented read they name."""
    spec = rest_anon.get(SPEC)
    if spec.status_code != 200:
        raise Inconclusive(f"{SPEC} answered HTTP {spec.status_code}")
    documented = documented_patterns(spec.json() or {})
    home = rest_anon.get(SITE + "/")
    if home.status_code != 200:
        raise Inconclusive(f"the home page answered HTTP {home.status_code}")
    pages = sorted({h for h in LINK.findall(home.text)
                    if not h.startswith(("/static", "/api", "/."))})[:MAX_PAGES]
    names: dict[str, set] = {}
    scripts_seen: set = set()
    read = 0
    for link in pages:
        time.sleep(PAUSE_S)
        page = rest_anon.get(SITE + link)
        if page.status_code != 200:
            continue
        read += 1
        texts = [page.text]
        for js in SCRIPT.findall(page.text):
            if js in scripts_seen:
                continue
            scripts_seen.add(js)
            script = rest_anon.get(SITE + js)
            if script.status_code == 200:
                texts.append(script.text)
        for text in texts:
            for path in called_paths(text):
                names.setdefault(path, set()).add(link)
    if not read:
        raise Inconclusive("no linked page could be read")

    probe = candidates(names, documented)[:MAX_PROBES]
    public, refused = [], 0
    for path in probe:
        time.sleep(PAUSE_S)
        answer = rest_anon.get(path, headers={"Accept": "application/json"})
        if answer.status_code == 200 and "json" in answer.headers.get("content-type", ""):
            public.append(path)
        else:
            refused += 1
    conclude(Measurement(
        verdict="failed" if public else "passed",
        reason=(f"{len(public)} path(s) that {read} public pages call answer an "
                f"anonymous GET with 200 JSON and are not in {SPEC}: "
                + ", ".join(f"{p} ({sorted(names[p])[0]})" for p in public[:12])
                + (f" (+{len(public) - 12} more)" if len(public) > 12 else "")
                if public else
                f"every read-shaped path {read} public pages name is documented or "
                f"refuses an anonymous read ({len(probe)} probed)"),
        left={"pages_read": read, "probed": len(probe), "public_undocumented": len(public)},
        right={"public_undocumented": 0},
        population={"public_undocumented": public, "refused_or_not_json": refused},
        sources={"spec": SPEC, "pages": "links on the home page, with their /static/js"}))
