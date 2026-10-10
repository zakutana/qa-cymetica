"""The trading station opens every tab it shows by default, for the symbol it shows by default.

The contract is the station's own catalogue, `GET /api/v1/station/apps` (feature #799): its
rule is "A tab is any app already live on the platform; nothing gets a tab before it ships",
`default_symbol` and `default_tabs` are what /station opens with, and each app's `url` fills
`{sym}` / `{sym_lower}` with the symbol. The page says "One symbol drives the chart and every
tab around it", and its "Trade {sym} on the CLOB" button links where the CLOB tab does.

**What was seen when this was written** (2026-10-10, the link Cymetica posted on X,
/station?symbol=BTC&tabs=clob,weekly,news,alerts): default symbol BTC, default tabs chart,
clob, weekly, news, alerts. The clob tab is /exchange/btc-pro, which answers 404 "Page Not
Found" inside the tab, and so does the "Trade BTC on the CLOB" button; /exchange/btc
redirects there too. BTC is not among the 16 markets of /api/v1/exchange/markets.

**The rule.** Every default tab's page, filled with the default symbol, answers 2xx. A
default tab the catalogue does not describe is a failure too: the page could not open it.
A catalogue that cannot be read, or names no default symbol, is unread.

SAFE. GETs only, anonymous.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

APPS = "/api/v1/station/apps"


def default_tab_paths(body: dict) -> list[tuple[str, str | None]]:
    """Each default tab with the page it opens for the default symbol; None for a tab the
    catalogue does not describe. Empty when there is no default symbol to fill in."""
    sym = str((body or {}).get("default_symbol") or "").strip()
    if not sym:
        return []
    apps = {a.get("id"): a for a in (body or {}).get("apps") or [] if isinstance(a, dict)}
    out = []
    for tab in (body or {}).get("default_tabs") or []:
        app = apps.get(tab)
        url = (app or {}).get("url")
        out.append((tab, url.replace("{sym_lower}", sym.lower()).replace("{sym}", sym)
                    if isinstance(url, str) and url else None))
    return out


@qa(component="rest.clob", tier=SafetyTier.SAFE, surface="rest")
def test_the_station_opens_every_default_tab_for_its_default_symbol(rest_anon):
    """Each tab /station opens with answers for the symbol it opens with."""
    response = rest_anon.get(APPS)
    if response.status_code != 200:
        raise Inconclusive(f"{APPS} answered HTTP {response.status_code}; a failed read is not a station")
    body = response.json() or {}
    paths = default_tab_paths(body)
    if not paths:
        raise Inconclusive(f"{APPS} names no default symbol or no default tab")
    answers = []
    for tab, path in paths:
        if path is None:
            answers.append({"tab": tab, "path": None, "status": None})
            continue
        page = rest_anon.get(path, headers={"Accept": "text/html"})
        answers.append({"tab": tab, "path": path, "status": page.status_code})
    dead = [a for a in answers if a["status"] is None or not 200 <= a["status"] < 300]
    sym = body.get("default_symbol")
    conclude(Measurement(
        verdict="failed" if dead else "passed",
        reason=(f"{len(dead)} of {len(answers)} default tabs of /station (default symbol {sym}) do not open: "
                + "; ".join(f"{a['tab']} {a['path'] or '(not in the catalogue)'} -> HTTP {a['status']}"
                            for a in dead)
                + f"; {APPS} says \"{body.get('rule')}\""
                if dead else
                f"all {len(answers)} default tabs of /station open for {sym}: "
                + ", ".join(f"{a['tab']} {a['status']}" for a in answers)),
        left={"default_tabs_not_opening": len(dead)},
        right={"default_tabs_not_opening": 0},
        population={"answers": answers, "default_symbol": sym, "default_tabs": body.get("default_tabs")},
        sources={"catalogue": APPS}))
