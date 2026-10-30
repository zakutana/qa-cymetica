"""Refresh data.js: our company's Quant Lab as their owner-only API returns it (GET only, nothing is sent).

    python outbox/quant-lab-v2/refresh.py

Reads the four calls their experiments page makes (quantsearch.js, quantlab.js) for company 14 and writes the parts the
mock draws into data.js. The search memory's 1,728 rows are kept as counts only.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

COMPANY = 14
BASE = f"/api/v1/company/{COMPANY}/quant-lab"


def read() -> dict:
    load_dotenv(REPO / ".env")
    install_client_guard()
    client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    out = {}
    try:
        for name, path in [("lab", BASE), ("search", BASE + "/search"), ("results", BASE + "/search/results?limit=12"),
                           ("memory", BASE + "/search/memory?limit=60&offset=0")]:
            r = client.get(path)
            if r.status_code != 200:   # a failed read is not an empty lab: stop, keep the old data.js
                raise SystemExit(f"{path} -> HTTP {r.status_code}; data.js not changed")
            out[name] = r.json()
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    return out


def shape(raw: dict) -> dict:
    s, res, lab, mem = raw["search"], raw["results"], raw["lab"], raw["memory"]
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "company": COMPANY,
        "plan": s["access"]["plan_name"],
        "models": s["models"],
        "markets": s["markets"],
        "combinations_tried": s["combinations_tried"],
        "method": s["method"],
        "searches": [{k: x[k] for k in ("id", "status", "origin", "requested_at", "finished_at", "total_jobs", "done_jobs")}
                     | {"summary": x.get("summary"), "error": (x.get("error") or "").split("\n")[0][:80] or None}
                     for x in res["searches"]],
        "held_back": [{k: x[k] for k in ("model", "market", "settings_label", "entry_threshold", "verdict", "reason")}
                      | {"search": {k: x["search_period"][k] for k in ("return_pct", "trades", "max_drawdown_pct", "win_rate")},
                         "held": {k: x["held_back"][k] for k in ("return_pct", "trades")},
                         "bar": {k: x["bar"][k] for k in ("n_tried", "z", "bar_pct")}}
                      for x in res["held_back_results"]],
        "rule": lab["rule"],
        "rule_text": lab["rule_text"],
        "running": lab["plan"]["running"],
        "trading_cap": lab["plan"]["trading_cap"],
        "experiments": lab["experiments"],
        "memory_total": mem["total"],
        "can_tune": s["can_tune"],
        "cannot_tune": [{"what": c["what"], "size": c["feasibility"]} for c in s["cannot_tune"]],
        "does_not_do": s["what_it_does_not_do"],
        "cost": s["cost"],
    }


def write(data: dict) -> None:
    body = json.dumps(data, ensure_ascii=False, indent=1)
    (HERE / "data.js").write_text(
        "/* Our company's Quant Lab, read from their owner-only API by refresh.py. Real, not simulated. */\n"
        f"window.QL_DATA = {body};\n", encoding="utf-8")


if __name__ == "__main__":
    write(shape(read()))
    print("data.js written")
