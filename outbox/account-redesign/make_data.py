"""data.js for the /account (My Balances) mockup: our account's reads of 2026-10-17 with our API key.

Each block is what one part of the live page renders, from the endpoint that part reads (see parity.md).
No email, username, wallet, deposit address or key goes in.
Usage: python make_data.py <dir with the acct_*.json reads> <out data.js>
"""
import json
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
J = lambda n: json.loads((src / f"acct_{n}.json").read_text(encoding="utf-8"))
port, bal, buy, dash, cards, tx = J("portfolio"), J("balances"), J("buying"), J("dashboard"), J("cards"), J("tx")
cad, agents, mq = J("cadence"), J("agents"), J("movequote")
me = dash["me"]
T = bal["totals"]

# Positions (on-chain, /account/me/balances totals): the boxes the live page draws, with its show rules.
onchain = {"USDC": T["usdc"], "USDT": T["usdt"], "ETH": T["eth"], "VAIX": T["vaix"] + T["wvaix"], "SBIO": T["sbio"],
           "ET10": T["et10"], "ETLP": T["etlp"], "TBIG": T["tbig"], "TBIGS": T["tbigs"], "DSCI": T["dsci"],
           "DESCI": T["desci"], "ORBI": T["orbi"], "THF": T["thf"], "CYM42": T["cym42"]}
# Valuation (ledger, /account/me/portfolio assets).
ledger = {}
for a in port["assets"]:
    paper = bool(a.get("is_paper"))
    ledger[a["symbol"]] = {"cat": a["category"], "bal": a["balance"], "price": a["price_usd"],
                           "value": a.get("paper_value_usd") if paper else a["value_usd"],
                           "pct": a["allocation_pct"], "paper": paper, "detail": a.get("detail") or ""}
NAMES = {"USDC": "USD Coin", "USDT": "Tether", "ETH": "Ether", "VAIX": "VAIX", "SBIO": "SBIO", "ET10": "EventTrader 10",
         "ETLP": "ETLP", "TBIG": "TBIG", "TBIGS": "TBIGS", "DSCI": "DSCI", "DESCI": "DESCI", "ORBI": "ORBI",
         "THF": "Tuatara Hedge Fund", "CYM42": "CyMetica-42", "tUSDC": "Robinhood Testnet"}
rows = []
for sym, q in onchain.items():
    lv = ledger.get(sym, {})
    group = "CASH" if sym in ("USDC", "USDT") else "FUND SHARES" if sym == "THF" else "VAULT SHARES" if sym == "CYM42" else "TOKENS"
    rows.append({"sym": sym, "name": NAMES[sym], "group": group, "pos": q, "ledger": lv.get("bal"), "price": lv.get("price"),
                 "value": lv.get("value"), "link": {"THF": "/fund-performance", "CYM42": "/fund/cymetica-42"}.get(sym)})
for sym, lv in ledger.items():  # ledger rows the boxes do not have: positions, testnet
    if sym in onchain or lv["cat"] == "cash":
        continue
    if lv["cat"] == "testnet":
        rows.append({"sym": sym, "name": NAMES.get(sym, sym), "group": "TOKENS", "pos": lv["bal"], "ledger": lv["bal"],
                     "price": lv["price"], "value": lv["value"], "paperOnly": True})
    elif lv["cat"] == "positions":
        m = re.match(r"(BULL|BEAR)", lv["detail"])
        rows.append({"sym": sym, "name": lv["detail"], "group": "POSITIONS", "pos": None, "ledger": lv["bal"], "price": lv["price"],
                     "value": lv["value"], "paper": lv["paper"]})
cash_trading = sum(a["balance"] for a in port["assets"] if a["category"] == "cash" and a["symbol"] == "USDC")
pos = [{"id": p["card_id"][:8], "title": p["card_title"], "side": p["side"], "status": p["status"], "stake": p["notional_usdc"],
        "value": p["current_value_usdc"], "pnl": p["unrealized_pnl_usdc"], "opened": p["opened_at"], "paper": p["is_paper"]}
       for p in cards["positions"]]
mfp = dash["microfunds_portfolio"]
mf = [{"id": e["feature_request_id"] or e["ai_app_id"], "app": not e["feature_request_id"], "title": e["title"], "status": e["mf_status"],
       "backed": float(e["amount_backed_usdc"]), "received": float(e["revenue_received_usdc"]), "cap": float(e["cap_usdc"]),
       "custodied": e["custodied"]} for e in mfp["entries"] if not e["refunded"]]
order = next(({"pair": "BRRR/USDC", "side": "buy", "type": "immediate", "price": 0.0101, "qty": 1.0, "status": "filled", "at": t["created_at"]}
              for t in tx["transactions"] if t["description"].startswith("CLOB buy 1.00 BRRR")), None)
rwd = next((h for h in bal["holdings"] if h["symbol"] == "ET10RWD"), {"quantity": 0})
out = {
    "simMode": me["simulation_mode"], "sim": me["sim_balance"], "lastCheck": me.get("last_balance_check"),
    "valuationTotal": port["total_value_usd"], "rows": rows,
    "cash": {"USDC": {"trading": cash_trading, "payable": (port.get("payable_now") or {}).get("USDC"),
                      "pendingLiquidity": (port.get("pending_buyer_liquidity") or {}).get("usdc"),
                      "move": {"enabled": mq["enabled"], "available": float(mq["available"]), "moved": float(mq["already_moved"]),
                               "minimum": float(mq["minimum"])}}},
    "buying": {"best": buy["best_chain"], "bestCap": buy["best_capacity_usdc"], "ledger": buy["ledger_usdc"],
               "chains": [{"chain": c["chain"], "cap": c["capacity_usdc"], "usdc": c["usdc"], "usdt": c["usdt"], "native": c["native"],
                           "nsym": c["native_symbol"], "capped": c["capped_by_ledger"], "wallet": c["wallet_capacity_usdc"]}
                          for c in buy["chains"] if c["readable"]]},
    "positions": pos,
    "microfunds": {"backed": float(mfp["total_backed_usdc"]), "verified": float(mfp["total_verified_backed_usdc"]),
                   "received": float(mfp["total_received_usdc"]), "entries": mf},
    "et10Accrued": rwd["quantity"],
    "rewardsSummary": dash["rewards_summary"],
    "tokenRevenue": {k: v for k, v in dash["revenue_report"].items() if k != "wallet"},
    "cadence": {"value": cad["cadence"], "next": cad["next_delivery_date"], "note": cad["note"], "choices": cad["choices"]},
    "obligations": dash["obligations"], "pendingDeposits": dash["pending_deposits"]["pending"],
    "agents": {"available": float(agents["owner_usdc_available"]), "list": agents["agents"]},
    "order": order,
}
dst.write_text("/* Our account's reads of 2026-10-17 (make_data.py, parity.md): one block per part of the live page.\n"
               "   The recent order is the CLOB fill from our ledger; the orders list itself is not readable with an API key. */\n"
               "const ACCT=" + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")
print(len(rows), "rows,", len(pos), "positions,", len(mf), "microfund entries;", dst.stat().st_size, "bytes")
