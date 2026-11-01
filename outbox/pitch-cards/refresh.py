"""Refresh data.js: Nexus's pitch cards and the pitchboard, from Cymetica's live data (GET only, nothing is sent).

    python outbox/pitch-cards/refresh.py

Nexus pitches only what clears its bar (the operator, 2026-10-31: "musi byt high confidence rady podlozene vysledky,
ne jak nove event karty"):
  a fund     live with real money for 8 weeks or more, +5% or more since it went live, and up over the last 30 days;
  a big deal a deal of $10B or more announced in the last 7 days that has a live ripple card.
The pitchboard is every pick Cymetica's AI has made so far, scored since the day it was made: each fund since it went
live (its page's own index history) and each deal-ripple card since it was minted (its index against its base).
A failed read stops the script and leaves the old data.js.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

FUND_WEEKS, FUND_RET, DEAL_USD, DEAL_DAYS = 8, 5.0, 10e9, 7


def get(client, path, what=None):
    for attempt in range(3):   # their server drops a connection now and then; a GET is safe to ask again
        try:
            r = client.get(path)
            break
        except httpx.TransportError:
            if attempt == 2:
                raise
            time.sleep(3)
    if r.status_code != 200:   # a failed read is not an empty product: stop, keep the old data.js
        raise SystemExit(f"{what or path} -> HTTP {r.status_code}; data.js not changed")
    return r


def ranked_funds(html: str) -> list[dict]:
    """The rows of /fund-performance's "All funds, ranked" table, row by row (a standing fund has no link)."""
    sect = html[html.index('id="fp-rank"'):]
    sect = sect[:sect.index("</table>")]
    out = []
    for tr in sect.split("<tr")[1:]:
        tr = tr.split("</tr>")[0]
        cell = re.search(r'<td class="fund">(.*?)</td>', tr, re.S)
        if not cell:
            continue
        href = re.search(r'href="([^"]+)"', cell.group(1))
        status = re.search(r'<span class="st (\w+)">', tr)
        ret = re.search(r'<span class="(?:pos|neg)">([+\-−]?[\d.]+)%</span>\s*</td>\s*$', tr, re.S)
        out.append({"name": unescape(re.sub(r"<[^>]+>", "", cell.group(1))).strip(), "href": href.group(1) if href else None,
                    "status": status.group(1) if status else None,
                    "ret": float(ret.group(1).replace("−", "-")) if ret else None})
    return out


def fund_history(client, f: dict) -> tuple[list, str | None]:
    """[(iso time, value)] and the live-since date, from the fund's own page or, for the ripple fund, its history API."""
    if f["href"] == "/ma-fund":
        pts = get(client, "/api/v1/ma-fund/history").json()["points"]
        return [(p["t"], p["v"]) for p in pts], pts[0]["t"] if pts else None
    if not f["href"] or not f["href"].startswith("/fund-performance/"):
        return [], None
    html = get(client, f["href"]).text
    m = re.search(r"var pts = (\[.*?\]);", html, re.S)
    since = re.search(r"Live since</label><b[^>]*>([\d-]+)", html)
    pts = json.loads(m.group(1)) if m else []
    return [(p["t"], p["v"]) for p in pts], since.group(1) if since else (pts[0]["t"][:10] if pts else None)


def stats(series: list, now: datetime) -> dict:
    """Return since the first point, over the last 30 days, and the deepest fall from a high, all from one series."""
    vs = [v for _, v in series]
    peak, dd = vs[0], 0.0
    for v in vs:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    cut = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    before = [v for t, v in series if t[:10] <= cut]
    base30 = before[-1] if before else vs[0]
    return {"ret": round(100 * (vs[-1] / vs[0] - 1), 2), "ret30": round(100 * (vs[-1] / base30 - 1), 2), "maxdd": round(100 * dd, 2)}


def thin(series: list, n: int = 60) -> list:
    """At most n points for a sparkline, first and last kept."""
    if len(series) <= n:
        return [round(v, 4) for _, v in series]
    step = (len(series) - 1) / (n - 1)
    return [round(series[round(i * step)][1], 4) for i in range(n)]


def rel(series: list) -> list:
    """[(days since the first point, % since the first point)]: lines that started on different days, side by side."""
    def when(t):
        return datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    t0, v0 = when(series[0][0]), series[0][1]
    return [((when(t) - t0).total_seconds() / 86400, 100 * (v / v0 - 1)) for t, v in series]


def line(points: list, upto: float | None = None, n: int = 90) -> list:
    """At most n [day, %] points, first and last kept, cut at day `upto`."""
    pts = [p for p in points if upto is None or p[0] <= upto]
    if len(pts) > n:
        step = (len(pts) - 1) / (n - 1)
        pts = [pts[round(i * step)] for i in range(n)]
    return [[round(d, 3), round(v, 3)] for d, v in pts]


def deal_size(title: str) -> float | None:
    m = re.search(r"\(\$([\d.]+)([BM])\)", title)
    return float(m.group(1)) * (1e9 if m.group(2) == "B" else 1e6) if m else None


def main() -> dict:
    load_dotenv(REPO / ".env")
    install_client_guard()
    client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=60.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    now = datetime.now(timezone.utc)
    try:
        funds = ranked_funds(get(client, "/fund-performance").text)
        board, pitches, fund_lines = [], [], {}
        for f in funds:
            series, since = fund_history(client, f)
            if len(series) < 2 or not since:
                continue
            fund_lines[f["name"]] = rel(series)
            s = stats(series, now)
            weeks = (now - datetime.fromisoformat(since[:10]).replace(tzinfo=timezone.utc)).days // 7
            row = {"kind": "fund", "name": f["name"], "href": f["href"], "status": f["status"], "since": since[:10],
                   "weeks": weeks, "ret": f["ret"] if f["ret"] is not None else s["ret"], "ret30": s["ret30"], "maxdd": s["maxdd"]}
            board.append(row)
            if f["status"] == "live" and weeks >= FUND_WEEKS and row["ret"] >= FUND_RET and s["ret30"] > 0:
                pitches.append(row | {"spark": thin(series)})
        cards, offset = [], 0
        while True:
            page = get(client, f"/api/v1/event-cards?limit=200&offset={offset}", "event-cards").json()
            cards += page["cards"]
            offset += len(page["cards"])
            if not page["cards"] or offset >= page["total"]:
                break
        deals = []
        for c in cards:
            # a deal-ripple card reads "AN — SAIB: Penske Automotive Group acquisition ($16.3B)"; the 550-odd
            # "SAIB: ZTS — Zoetis" cards are one per listed company, not a pick on news, and stay off the board
            m = re.match(r"^(\S+) — SAIB: (.+)$", c.get("title") or "")
            if not m or not c.get("index_base") or c.get("current_index") is None:
                continue
            ticker, what = m.groups()
            row = {"kind": "deal", "name": what, "ticker": ticker, "id": c["id"], "since": c["created_at"][:10],
                   "ret": round(100 * (c["current_index"] / c["index_base"] - 1), 2), "size": deal_size(c["title"])}
            deals.append(row)
        board += deals
        fresh = [d for d in deals if (d["size"] or 0) >= DEAL_USD and d["since"] >= (now - timedelta(days=DEAL_DAYS)).strftime("%Y-%m-%d")]
        def card_line(d):
            hist = get(client, f"/api/v1/event-cards/{d['id']}/index-history?interval=all").json()["points"]
            return rel([(p["t"], p["index"]) for p in hist]) if len(hist) >= 2 else []
        for d in sorted(fresh, key=lambda d: d["since"], reverse=True)[:1]:
            own = card_line(d)
            others = [card_line(o) for o in deals if (o["size"] or 0) >= DEAL_USD and o["id"] != d["id"]]
            pitches.append(d | {"line": line(own), "peers": [line(o, own[-1][0], 40) for o in others if len(o) >= 2]})
        for p in pitches:
            if p["kind"] == "fund":   # the one line lit, every other fund faint behind it, each from its own first day
                own = fund_lines[p["name"]]
                p |= {"line": line(own), "peers": [line(o, own[-1][0], 40) for n, o in fund_lines.items() if n != p["name"]],
                      "rank": 1 + sum(1 for r in board if r["kind"] == "fund" and r["ret"] > p["ret"]), "of": sum(1 for r in board if r["kind"] == "fund")}
                p.pop("spark", None)
        ripple = next((r for r in board if r["href"] == "/ma-fund"), None)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    pitches.sort(key=lambda p: -(p["ret"] or 0))   # strongest first; pc.js sorts the same way
    board.sort(key=lambda r: r["since"], reverse=True)
    big = [d for d in deals if (d["size"] or 0) >= DEAL_USD]
    return {"as_of": now.strftime("%Y-%m-%d %H:%M UTC"),
            "bar": {"fund_weeks": FUND_WEEKS, "fund_ret": FUND_RET, "deal_usd": DEAL_USD, "deal_days": DEAL_DAYS},
            "ripple_fund": {"ret": ripple["ret"], "since": ripple["since"]} if ripple else None,
            "big_deals": {"n": len(big), "up": sum(1 for d in big if d["ret"] > 0),
                          "avg": round(sum(d["ret"] for d in big) / len(big), 2) if big else None},
            "pitches": pitches, "board": board}


if __name__ == "__main__":
    d = main()
    (HERE / "data.js").write_text(
        "/* Live data for the Pitch Cards mock, read by refresh.py (GET only). Real, not simulated. */\n"
        f"window.PC_DATA = {json.dumps(d, ensure_ascii=False, indent=1)};\n", encoding="utf-8")
    print(json.dumps({"as_of": d["as_of"], "pitches": [(p["kind"], p["name"], p["ret"]) for p in d["pitches"]],
                      "board": len(d["board"]), "ripple": d["ripple_fund"]}, ensure_ascii=False))
