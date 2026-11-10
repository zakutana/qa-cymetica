"""The page's DOM against the data it drew (WS snapshot), and the data's own rules against themselves."""
import json
import re
from collections import Counter

dom = json.load(open("d-dom.json", encoding="utf-8"))


def knot(knots, c):
    p = knots[0][1]
    for x, y in knots:
        if c >= x:
            p = y
    return p


for chain, wsf, key in (("robinhood", "ws_rh.json", "basic_rh"), ("solana", "ws_sol.json", "basic_sol")):
    f = json.load(open(wsf, encoding="utf-8"))
    s, tr = f["signals"], f["traders"]["rows"]
    rows = s["rows"]
    d = dom[key]
    print("=====", chain, "rows", len(rows), "cards", len(d["cards"]))
    buys = [r for r in rows if not r.get("exit_signal")][:12]
    exits = [r for r in rows if r.get("exit_signal")]
    board = {t["wallet"]: (i + 1, t) for i, t in enumerate(tr)}
    # order
    print("card order == signal order:", [c["key"] for c in d["cards"]] == [r["token_address"] for r in buys])
    # chance
    bad = []
    for c, r in zip(d["cards"], buys):
        g = r.get("probability_3x_72h_gated"); p = r.get("probability_3x_72h")
        want = "%.1f%%" % (100 * (g if g is not None and p is not None and g < p else p)) if p is not None else (r.get("probability_display") or "insufficient history")
        if c["p"] != want:
            bad.append((c["name"], c["p"], want))
    print("chance == probability_3x_72h:", not bad, bad[:3])
    # rank, win, sold
    bad, n = [], 0
    for c, r in zip(d["cards"], buys):
        tb = {b["wallet"]: b for b in r.get("top_buyers") or []}
        for w in c["who"]:
            n += 1
            a = w["href"].rsplit("/", 1)[1]
            parts = [x.strip() for x in w["t"].split("|")]
            rank = parts[0]
            want = "#%d" % board[a][0] if a in board else "—"
            if rank != want or w["sold"] != bool(tb[a]["gone"]):
                bad.append((c["name"], a[:8], rank, want, w["sold"], tb[a]["gone"]))
            if a in board:
                wr = "%d%%" % round(100 * board[a][1]["win_rate"])
                if wr not in parts:
                    bad.append((c["name"], a[:8], "win", parts, wr))
    print("rank/win/SOLD on %d wallet lines:" % n, not bad, bad[:4])
    # stats
    bad = []
    for c, r in zip(d["cards"], buys):
        if chain == "robinhood":
            q = "%d smart wallet" % (r["qualified_buyers"] or 0)
            if not c["stats"][0].startswith(q):
                bad.append((c["name"], c["stats"][0], q))
        if bool(c["warn"]) != bool(r.get("thin")):
            bad.append((c["name"], "thin", c["warn"], r.get("thin")))
    print("smart wallets / thin:", not bad, bad[:4])
    print("exit chips == exit rows:", [e[0] for e in d["exits"]] == [(r["symbol"] or r["name"]) for r in exits], len(exits), "| any exit among cards:", any(r.get("exit_signal") for r in buys))
    if chain == "robinhood":
        pons = sum(r.get("launchpad") == "pons" for r in rows)
        print("promo count:", pons, "of", len(rows), "| shown:", (d["promo"]["text"].split("\n")[2] if d["promo"] else None)[:40])
        px = s["eth_usd"]
        for i, t in enumerate(tr[:4]):
            print("   best wallet", i + 1, "page:", d["copy"][i].split("|")[3].strip(), "| realized_eth*eth_usd = %+.0f" % (t["realized_eth"] * px))
    else:
        px = s["sol_usd"]
        for i, t in enumerate(tr[:4]):
            print("   best wallet", i + 1, "page:", d["copy"][i].split("|")[3].strip(), "| realized_sol*sol_usd = %+.0f" % (t["realized_sol"] * px), "| avg hold h", round(t["avg_hold_seconds"] / 3600), "| page says:", d["copy"][i].split("|")[4].strip())
    # ---- data rules ----
    cal = s["calibration"]
    bad = [(r["symbol"], r["conviction"], r["probability_3x_72h"], knot(cal["knots"], r["conviction"])) for r in rows if r["probability_3x_72h"] is not None and abs(r["probability_3x_72h"] - knot(cal["knots"], r["conviction"])) > 1e-6]
    print("probability == isotonic knots(conviction):", not bad, bad[:3])
    conv = [r["conviction"] for r in rows]
    print("rows sorted by conviction:", conv == sorted(conv, reverse=True))
    bad = [(r["symbol"], r["max_buy_5pct_usd"], r["thin"]) for r in rows if r.get("max_buy_5pct_usd") is not None and (r["max_buy_5pct_usd"] < 500) != bool(r["thin"])]
    print("thin == max buy < $500:", not bad, bad[:3], "| thin rows:", sum(bool(r["thin"]) for r in rows), "of", len(rows))
    bad = [(r["symbol"], r["token_age_seconds"], r["fresh"]) for r in rows if r.get("token_age_seconds") is not None and (r["token_age_seconds"] < 86400) != bool(r["fresh"])]
    print("fresh == age < 24 h:", not bad, bad[:3])
    bad = [(r["symbol"], r["hot"], r.get("max_buy_5pct_usd")) for r in rows if r.get("hot") and (r.get("max_buy_5pct_usd") or 0) < 500]
    print("hot only when tradeable:", not bad, bad[:3])
    names = Counter((r["name"] or "").strip().lower() for r in rows)
    bad = [(r["symbol"], r.get("same_name_on_board"), names[(r["name"] or "").strip().lower()] - 1) for r in rows if "same_name_on_board" in r and r["same_name_on_board"] != names[(r["name"] or "").strip().lower()] - 1]
    print("same_name_on_board:", not bad, bad[:4])
    if chain == "robinhood":
        bad = []
        for r in rows:
            for b in r["top_buyers"]:
                if b["bought_tokens"] and (b["sold_tokens"] >= 0.9 * b["bought_tokens"]) != bool(b["gone"]):
                    bad.append((r["symbol"], b["wallet"][:8]))
                if b["wallet"] in board and abs(board[b["wallet"]][1]["score"] - b["score"]) > 0.05:
                    bad.append((r["symbol"], b["wallet"][:8], "score", b["score"], board[b["wallet"]][1]["score"]))
        print("gone == sold >= 90%, buyer score == leaderboard score:", not bad, bad[:4])
        bad = [(r["symbol"], r["eth_invested"], r["usd_invested"]) for r in rows if r["usd_invested"] is not None and abs(r["usd_invested"] - r["eth_invested"] * s["eth_usd"]) > 1]
        print("usd_invested == eth * eth_usd:", not bad, bad[:3])
        bad = [(r["symbol"], r["exit_reason"], r["qualified_gone_wallets"], r["sells_1h"], r["buys_1h"]) for r in rows if r.get("exit_reason") == "credible-exits" and not (r["qualified_gone_wallets"] >= 2 and r["sells_1h"] >= r["buys_1h"])]
        print("credible-exits rule:", not bad, bad[:4])
        # who are the 'smart wallets' on the 12 cards
        contracts = json.load(open("kinds.json")) if __import__("os").path.exists("kinds.json") else {}
        cnt = Counter()
        for r in buys:
            for b in r["top_buyers"]:
                if b["score"] >= 60:
                    cnt[b["wallet"]] += 1
        print("qualified wallets across the 12 cards:", [(a[:10], n, board.get(a, (None,))[0]) for a, n in cnt.most_common(12)])
