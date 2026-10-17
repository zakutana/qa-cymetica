"""data.js for the /account (My Balances) mockup: our account's reads of 2026-10-17 with our API key.
No email, username, wallet or deposit address goes in."""
import json
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
J = lambda n: json.loads((src / f"acct_{n}.json").read_text(encoding="utf-8"))
port, bal, buy, dash, cards, tx, summ = J("portfolio"), J("balances"), J("buying"), J("dashboard"), J("cards"), J("tx"), J("summary")
me = dash["me"]

NAMES = {"USDC": "USD Coin", "USDT": "Tether", "ETH": "Ether", "VAIX": "VAIX", "SBIO": "SBIO", "ET10": "EventTrader 10",
         "ETLP": "ETLP", "TBIG": "TBIG", "TBIGS": "TBIGS", "DSCI": "DSCI", "DESCI": "DESCI", "ORBI": "ORBI",
         "tUSDC": "Robinhood testnet USDC", "THF": "Tuatara Hedge Fund", "CYM42": "CyMetica-42", "ET10RWD": "ET10 revenue record"}
GROUP = {"cash": "CASH", "token": "TOKENS", "testnet": "TESTNET"}
assets = []
seen = set()
for a in port["assets"]:
    if a["category"] not in GROUP:
        continue
    seen.add(a["symbol"])
    assets.append({"sym": a["symbol"], "name": NAMES.get(a["symbol"], a["symbol"]), "group": GROUP[a["category"]],
                   "bal": a["balance"], "price": a["price_usd"], "value": a["value_usd"], "pct": a["allocation_pct"]})
# what the page lists at zero is listed at zero here too
for sym in ["USDT", "VAIX", "SBIO"]:
    if sym not in seen:
        price = bal.get(f"{sym.lower()}_price_usd")
        assets.append({"sym": sym, "name": NAMES[sym], "group": "CASH" if sym == "USDT" else "TOKENS",
                       "bal": 0.0, "price": price, "value": 0.0, "pct": 0.0})
assets.append({"sym": "THF", "name": NAMES["THF"], "group": "FUNDS & VAULTS", "bal": bal["totals"]["thf"], "price": None, "value": 0.0, "pct": 0.0})
assets.append({"sym": "CYM42", "name": NAMES["CYM42"], "group": "FUNDS & VAULTS", "bal": bal["totals"]["cym42"], "price": None, "value": 0.0, "pct": 0.0})
for h in bal["holdings"]:
    assets.append({"sym": h["symbol"], "name": NAMES.get(h["symbol"], h["symbol"]), "group": "EXCHANGE",
                   "bal": h["quantity"], "price": h["price_usd"], "value": h["value_usd"], "pct": None})

chains = [{"chain": c["chain"], "usdc": c["usdc"], "usdt": c["usdt"], "native": c["native"], "nsym": c["native_symbol"],
           "cap": c["capacity_usdc"], "capped": c["capped_by_ledger"], "ok": c["readable"]} for c in buy["chains"]]
pos = [{"title": p["card_title"], "side": p["side"], "status": p["status"], "stake": p["notional_usdc"],
        "value": p["current_value_usdc"], "pnl": p["unrealized_pnl_usdc"], "rpnl": p["realized_pnl_usdc"],
        "opened": p["opened_at"], "paper": p["is_paper"]} for p in cards["positions"]]
txs = [{"type": t["type"], "cur": t["currency"], "amt": t["amount"], "status": t["status"], "at": t["created_at"],
        "desc": t["description"]} for t in tx["transactions"]]
mf = [{"title": e["title"], "status": e["mf_status"], "backed": e["amount_backed_usdc"], "verified": e["verified_backed_usdc"],
       "revenue": e["revenue_received_usdc"], "refunded": e["refunded"]} for e in dash["microfunds_portfolio"]["entries"]]
out = {"total": port["total_value_usd"], "assets": assets, "prices": {k: bal[k] for k in bal if k.endswith("_price_usd")},
       "buying": {"ledger": buy["ledger_usdc"], "best": buy["best_chain"], "bestCap": buy["best_capacity_usdc"], "chains": chains},
       "positions": pos, "summaryCards": summ["event_cards"], "tx": txs, "txTotal": tx["total_count"],
       "sim": me["sim_balance"], "simMode": me["simulation_mode"], "created": me["created_at"],
       "rewards": dash["rewards_summary"], "revenue": {k: v for k, v in dash["revenue_report"].items() if k != "wallet"},
       "obligations": dash["obligations"], "pendingDeposits": dash["pending_deposits"], "microfunds": mf,
       "lastCheck": me.get("last_balance_check")}
dst.write_text("/* Our account's balance reads of 2026-10-17 (make_account_data.py); no email, username or address. */\n"
               "const ACCT=" + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")
print(len(assets), "assets,", len(pos), "positions,", len(txs), "tx,", len(mf), "microfunds;", dst.stat().st_size, "bytes")
