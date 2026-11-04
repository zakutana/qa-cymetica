"""Build the Agent Casino lobby mock: their live page, scripts out, our v7.css and v7.js on top, our real results as data.js.

    python outbox/casino-v7/build.py
    python scripts/serve_mock.py outbox/casino-v7 8841

Reads only (GET). The page comes anonymously; the results with our key, which never reaches a written file.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HOST = "https://cymetica.com"


def casino_script():
    sys.path[:0] = [str(REPO), str(REPO / "scripts")]
    spec = importlib.util.spec_from_file_location("casino_script", REPO / "scripts" / "casino.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def page() -> str:
    """Their lobby with no script of theirs: a copy of a page with seat buttons must not be able to act."""
    request = urllib.request.Request(f"{HOST}/agent-casino", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(request, timeout=90).read().decode("utf8")
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", html, flags=re.S | re.I)
    # their script flips these print-only links on; with the script gone the fonts would never load
    html = re.sub(r'(<link\b[^>]*?)\s+media="print"([^>]*>)', r"\1\2", html)
    html = re.sub(r'(<link\b[^>]*?)\s+onload="[^"]*"([^>]*>)', r"\1\2", html)
    html = re.sub(r'(href|src|action)="/(?!/)', rf'\1="{HOST}/', html)
    html = html.replace("url(/static", f"url({HOST}/static")
    tail = '<link rel="stylesheet" href="v7.css"></head>'
    html = html.replace("</head>", tail, 1)
    return html.replace("</body>", '<script src="data.js"></script><script src="owner.js"></script><script src="v7.js"></script></body>', 1)


def seat_row(row: dict) -> dict:
    return {"bot": row.get("bot"), "rank": row.get("rank"), "house": bool(row.get("house")), "roi": row.get("roi_pct"),
            "pnl": row.get("pnl_usdc"), "prize": row.get("prize_usdc") or 0, "et10": row.get("prize_et10") or 0,
            "trades": row.get("trades"), "no_trades": bool(row.get("no_trades")), "seat_id": row.get("seat_id")}


def results() -> dict:
    casino = casino_script()
    tables, bots = [], []
    with casino._client() as client:
        lobby = casino._read(client, f"{casino.BASE}/lobby")
        newest = max(t["id"] for t in lobby["tables"])
        for table_id in range(1, newest + 1):
            table = casino._read(client, f"{casino.BASE}/tables/{table_id}")
            if not isinstance(table, dict) or table.get("status") != "done" or table.get("mode") != "paper":
                continue
            ranked = [seat_row(r) for r in (table.get("results") or {}).get("ranked") or []]
            mine = {s.get("seat_id") for s in table.get("my_seats") or [] if isinstance(s, dict)}
            if isinstance(table.get("my_seat"), dict):
                mine.add(table["my_seat"].get("seat_id"))
            tables.append({"id": table_id, "tier": table.get("tier"), "currency": table.get("currency"),
                           "hours": table.get("hours"), "buyin": table.get("buyin_usdc"), "pot": table.get("pot_usdc"),
                           "ends_at": table.get("ends_at"), "winner": table.get("winner"),
                           "winner_note": table.get("winner_note"), "ranked": ranked,
                           "mine": [r for r in ranked if r["seat_id"] in mine]})
        board = casino._read(client, f"{casino.BASE}/leaderboard?mine=true")
        for row in board.get("rows") or []:
            bots.append({k: row.get(k) for k in ("bot", "avatar", "won_usdc", "won_et10", "wins", "avg_roi_pct", "tables",
                                                 "live", "bot_page")})
    return {"tables": tables, "bots": bots}


def main() -> int:
    data = results()
    text = json.dumps(data, ensure_ascii=False)
    if re.search(r"api[_-]?key|[\w.]+@[\w.]+\.\w+|Bearer ", text, re.I):
        print("refused: the data carries something that looks like a credential or an address")
        return 1
    (HERE / "data.js").write_text(f"window.CASINO={text};\n", encoding="utf8")
    (HERE / "index.html").write_text(page(), encoding="utf8")
    print(f"{len(data['tables'])} finished tables, {len(data['bots'])} bots of ours")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
