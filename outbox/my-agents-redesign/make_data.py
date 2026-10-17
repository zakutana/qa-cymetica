"""data.js for the My Agents mockup: our paper clones (my-clones) and one clone's profile, read 2026-10-17 with our API key.
Wallet addresses and owner records are left out."""
import json
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
rows = json.loads((src / "my_clones.json").read_text(encoding="utf-8"))
prof = json.loads((src / "profile.json").read_text(encoding="utf-8"))

ICON = {"MACD": "crosshairs", "RSI": "gauge-high", "BOLL": "mask", "VOL": "chart-column", "TREND": "arrow-trend-up",
        "STOCH": "hand-fist", "ICHI": "crown", "FIB": "fire", "ATR": "arrows-up-down", "DIV": "dragon",
        "PCPN": "brain", "LIQHUNT": "bullseye", "STAT": "chart-simple", "SYNC": "arrows-rotate",
        "FADE": "arrow-trend-down", "CORR": "link", "CRASH": "burst", "VORTX": "hurricane", "GLOOM": "moon",
        "SENT": "water", "DELTA": "bolt", "DREAD": "newspaper"}
f = lambda v: round(float(v or 0), 2)
bots = []
for r in rows:
    lds = r.get("live_decision_source") or {}
    bots.append({"id": r["id"], "name": r.get("name") or r.get("source_name"), "species": r.get("source_name"),
                 "sym": r.get("source_symbol"), "icon": ICON.get(r.get("source_symbol"), "robot"),
                 "pnl": f(r.get("total_profit_usdc")), "bal": f(r.get("current_balance_usdc")),
                 "trades": int(r.get("trades_executed") or 0), "wr": round(float(r.get("win_rate") or 0) * 100),
                 "trading": bool(r.get("is_trading")), "paper": bool(r.get("is_paper")), "status": r.get("status"),
                 "why": r.get("auto_pause_reason"), "whyPct": r.get("auto_pause_pnl_pct"), "team": r.get("team"),
                 "style": r.get("strategy_type"), "risk": r.get("risk_profile"), "rule": lds.get("label"),
                 "ind": [i.get("name") for i in r.get("primary_indicators") or []],
                 "lastTrade": r.get("last_trade_at"), "created": r.get("created_at")})
keep = ["id", "name", "source_name", "source_symbol", "reference_number", "is_paper", "is_trading", "team", "risk_profile",
        "strategy_type", "tagline", "settings", "readiness", "live_strategy", "live_decision_source", "trades_summary",
        "perpetual_markets_status", "equipped_skills", "equipped_models", "performance", "current_balance_usdc"]
profile = {k: prof.get(k) for k in keep}
profile["icon"] = ICON.get(prof.get("source_symbol"), "robot")
dst.write_text("/* Our paper clones and one clone's profile, read 2026-10-17 from cymetica.com with our API key (make_data.py). */\n"
               "const BOTS=" + json.dumps(bots, ensure_ascii=False) + ";\n"
               "const PROFILE=" + json.dumps(profile, ensure_ascii=False, indent=0) + ";\n", encoding="utf-8")
print(len(bots), "bots;", dst.stat().st_size, "bytes")
