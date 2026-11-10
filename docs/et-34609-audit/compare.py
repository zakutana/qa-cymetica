"""Their /traders leaderboard (the snapshot the page drew) against the chain's own trade logs for the same window."""
import json
from collections import defaultdict
from chain import rpc
from recount import legs

f = json.load(open("ws_rh.json", encoding="utf-8"))
rows = f["traders"]["rows"]
L = legs(json.load(open("window_logs.json")))
by_curve_addr = defaultdict(list)
raw = json.load(open("window_logs.json"))
i = 0
for l in raw:
    if l["topics"][0] in ("0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455", "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df"):
        L[i]["curve"] = l["address"]
        i += 1
print("legs", len(L), "their trades_indexed", f["signals"]["trades_indexed"])


def rec(key):
    """Per address (by sender or by recipient): buys, sells, ETH, and round trips per curve by their published 90% rule."""
    per = defaultdict(lambda: defaultdict(list))
    for x in L:
        per[x[key] if x["side"] == "buy" else x["who"]][x["curve"]].append(x)
    out = {}
    for a, curves in per.items():
        r = {"buys": 0, "sells": 0, "eth_in": 0.0, "eth_out": 0.0, "trips": 0, "wins": 0, "realized": 0.0, "open": 0, "open_cost": 0.0, "curves": len(curves), "recips": set()}
        for c, xs in curves.items():
            bought = sold = cost = proc = 0.0
            for x in xs:
                if x["side"] == "buy":
                    r["buys"] += 1; r["eth_in"] += x["eth"]; bought += x["tok"]; cost += x["eth"]; r["recips"].add(x["who"])
                else:
                    r["sells"] += 1; r["eth_out"] += x["eth"]; sold += x["tok"]; proc += x["eth"]
                    if bought > 0 and sold >= 0.9 * bought:
                        r["trips"] += 1; r["wins"] += proc > cost; r["realized"] += proc - cost
                        bought = sold = cost = proc = 0.0
            if bought > 0:
                r["open"] += 1; r["open_cost"] += cost
        r["recips"] = len(r["recips"])
        out[a] = r
    return out


S, R = rec("sender"), rec("who")
print()
print("%-3s %-12s %-9s | THEIR buys sells eth_bought  rt wins realized | CHAIN(by sender) buys sells eth_in eth_out net  rt wins realized | recipients | as recipient: buys" % ("#", "address", "kind"))
for n, t in enumerate(rows, 1):
    a = t["wallet"]
    code = rpc("eth_getCode", [a, "latest"])
    size = (len(code) - 2) // 2
    kind = "EOA" if size == 0 else ("7702" if size == 23 else "C%d" % size)
    s, r = S.get(a), R.get(a)
    cs = ("%4d %4d %8.4f %8.4f %+8.4f %3d %3d %+8.4f | %4d" % (s["buys"], s["sells"], s["eth_in"], s["eth_out"], s["eth_out"] - s["eth_in"], s["trips"], s["wins"], s["realized"], s["recips"])) if s else "none"
    cr = ("%4d" % r["buys"]) if r else "   0"
    print("%-3d %-12s %-9s | %4d %4d %9.4f %3d %3d %+9.4f | %s | %s" % (n, a[:12], kind, t["buys"], t["sells"], t["eth_bought"], t["round_trips"], t["wins"], t["realized_eth"], cs, cr))

# what share of all buys goes through addresses that buy for other people
tot = sum(x["eth"] for x in L if x["side"] == "buy")
nb = sum(1 for x in L if x["side"] == "buy")
routed = [x for x in L if x["side"] == "buy" and x["sender"] != x["who"]]
print()
print("buys on chain in window: %d, %.2f ETH; sender != recipient: %d (%.0f%%), %.2f ETH (%.0f%%)" % (nb, tot, len(routed), 100 * len(routed) / nb, sum(x["eth"] for x in routed), 100 * sum(x["eth"] for x in routed) / tot))
top = sorted(S.items(), key=lambda kv: -kv[1]["recips"])[:8]
print("senders by distinct recipients:", [(a[:12], v["recips"], v["buys"]) for a, v in top])
json.dump({"S": {a: v for a, v in S.items()}, "R": {a: v for a, v in R.items()}}, open("recount_all.json", "w"))
