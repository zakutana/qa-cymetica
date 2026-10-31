"""Refresh data.js: the live numbers the Prove It mock draws on its product cards (GET only, nothing is sent).

    python outbox/prove-it/refresh.py

Public reads: the event-card listing's total, /themes/performance (stocks, 5 days), the ranked table of
/fund-performance (the same rows the MCP tool `list_funds` returns, which is a POST and so default-denied here) and the
Airdrop Farmer's farms. One owner-only read, our company 14's Quant Lab search results,
through the repo's client at the SAFE tier. A failed read stops the script and leaves the old data.js.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

COMPANY = 14


def ok(r, what):
    if r.status_code != 200:   # a failed read is not an empty product: stop, keep the old data.js
        raise SystemExit(f"{what} -> HTTP {r.status_code}; data.js not changed")
    return r.json()


def read() -> dict:
    load_dotenv(REPO / ".env")
    install_client_guard()
    client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=40.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        cards = ok(client.get("/api/v1/event-cards"), "event-cards")
        themes = ok(client.get("/api/v1/themes/performance"), "themes/performance")
        page = client.get("/fund-performance")   # list_funds is an MCP POST, default-denied here: read its page
        if page.status_code != 200:
            raise SystemExit(f"fund-performance -> HTTP {page.status_code}; data.js not changed")
        farms = ok(client.get("/api/v1/airdrop-farm/farms"), "airdrop-farm/farms")
        lab = ok(client.get(f"/api/v1/company/{COMPANY}/quant-lab/search/results?limit=20"), "quant-lab results")
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    return {"cards": cards, "themes": themes, "funds": {"funds": ranked_funds(page.text)}, "farms": farms, "lab": lab}


def ranked_funds(html: str) -> list[dict]:
    """The rows of the page's "All funds, ranked" table: name and return since inception, anchored on its ids."""
    sect = html[html.index('id="fp-rank"'):]
    sect = sect[:sect.index("</table>")]
    out = []
    for tr in sect.split("<tr")[1:]:   # row by row: a standing fund has no link, and a match across rows took its neighbour's return
        name = re.search(r'<td class="fund">(.*?)</td>', tr, re.S)
        ret = re.search(r'<span class="(?:pos|neg)">([+\-−]?[\d.]+)%</span>\s*</td>\s*$', tr.split("</tr>")[0], re.S)
        if name:
            out.append({"name": unescape(re.sub(r"<[^>]+>", "", name.group(1))).strip(),
                        "return_since_inception_pct": float(ret.group(1).replace("−", "-")) if ret else None})
    if not out:
        raise SystemExit("fund-performance: no ranked rows found; data.js not changed")
    return out


def shape(raw: dict) -> dict:
    th, fu, lab = raw["themes"], raw["funds"]["funds"], raw["lab"]
    rets = [f["return_since_inception_pct"] for f in fu if f.get("return_since_inception_pct") is not None]
    best = max(fu, key=lambda f: f.get("return_since_inception_pct") or -1e9)
    worst = min(fu, key=lambda f: f.get("return_since_inception_pct") or 1e9)
    done = [s for s in lab["searches"] if s["status"] == "done" and isinstance(s.get("summary"), dict)]
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "cards": {"live": raw["cards"]["total"]},
        "themes": {"as_of": th["as_of"], "period": th["period"], "published": len(th["rows"]),
                   "spy_pct": th["rows"][0]["benchmark"]["return_pct"],
                   "top": [{"label": r["theme"]["label"], "pct": r["basket_return_pct"], "excess": r["excess_pct"]}
                           for r in th["rows"][:3]]},
        "funds": {"count": len(fu), "up": sum(1 for x in rets if x > 0), "down": sum(1 for x in rets if x <= 0),
                  "best": {"name": best["name"], "pct": best["return_since_inception_pct"]},
                  "worst": {"name": worst["name"], "pct": worst["return_since_inception_pct"]}},
        "farms": {"count": raw["farms"]["count"]},
        "bots": {"tried": max((s["summary"]["n_tried_total"] for s in done), default=0),
                 "blind_tested": len(lab["held_back_results"]),
                 "won": sum(1 for x in lab["held_back_results"] if x["verdict"] == "kept")},
    }


def write(data: dict) -> None:
    body = json.dumps(data, ensure_ascii=False, indent=1)
    (HERE / "data.js").write_text(
        "/* Live numbers for the Prove It mock, read by refresh.py (GET and one MCP read). Real, not simulated. */\n"
        f"window.PI_DATA = {body};\n", encoding="utf-8")


if __name__ == "__main__":
    d = shape(read())
    write(d)
    print(json.dumps(d, ensure_ascii=False))
