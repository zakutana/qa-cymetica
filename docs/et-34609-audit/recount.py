"""Recount one wallet's trades on one curve from the chain's own CurveBuy / CurveSell logs.
python recount.py <logs.json> <wallet> [from_block]"""
import json
import sys

BUY = "0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455"
SELL = "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df"


def legs(ls):
    out = []
    for l in ls:
        t = l["topics"][0]
        if t not in (BUY, SELL):
            continue
        d = l["data"][2:]
        w = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
        a1, a2 = "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:]
        if t == BUY:
            out.append({"side": "buy", "sender": a1, "who": a2, "eth": w[0] / 1e18, "tok": w[1] / 1e18, "fee": w[2] / 1e18, "block": int(l["blockNumber"], 16), "tx": l["transactionHash"]})
        else:
            out.append({"side": "sell", "sender": a1, "who": a2, "tok": w[0] / 1e18, "eth": w[1] / 1e18, "fee": w[2] / 1e18, "block": int(l["blockNumber"], 16), "tx": l["transactionHash"]})
    return out


def record(L, wallet, frm=0, key="who"):
    """Their rule: a round trip closes when the wallet has sold >= 90% of the tokens it bought on that curve."""
    mine = [x for x in L if x[key] == wallet and x["block"] >= frm]
    buys = [x for x in mine if x["side"] == "buy"]
    sells = [x for x in mine if x["side"] == "sell"]
    # walk in order: position opens on a buy, closes when cumulative sold >= 90% of cumulative bought since open
    trips, bought, sold, cost, proc, opened = [], 0.0, 0.0, 0.0, 0.0, None
    for x in mine:
        if x["side"] == "buy":
            if bought == 0:
                opened = x["block"]
            bought += x["tok"]; cost += x["eth"]
        else:
            sold += x["tok"]; proc += x["eth"]
            if bought > 0 and sold >= 0.9 * bought:
                trips.append({"cost": cost, "proceeds": proc, "pnl": proc - cost, "blocks": x["block"] - opened})
                bought = sold = cost = proc = 0.0
    return {"buys": len(buys), "sells": len(sells), "eth_in": sum(x["eth"] for x in buys), "eth_out": sum(x["eth"] for x in sells),
            "tok_in": sum(x["tok"] for x in buys), "tok_out": sum(x["tok"] for x in sells), "trips": trips,
            "open_cost": cost, "open_tok": bought - sold, "first": mine[0]["block"] if mine else None, "last": mine[-1]["block"] if mine else None}


if __name__ == "__main__":
    L = legs(json.load(open(sys.argv[1])))
    w = sys.argv[2].lower()
    frm = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    print("legs", len(L), "buys", sum(x["side"] == "buy" for x in L), "sells", sum(x["side"] == "sell" for x in L), "blocks", L[0]["block"], L[-1]["block"])
    for key in ("who", "sender"):
        r = record(L, w, frm, key)
        t = r.pop("trips")
        wins = sum(x["pnl"] > 0 for x in t)
        print(key, {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})
        print("   round trips", len(t), "wins", wins, "realized", round(sum(x["pnl"] for x in t), 6), "avg hold s", round(sum(x["blocks"] for x in t) * 0.1079 / max(1, len(t)), 1))
        if key == "who":
            for x in t:
                print("     cost %.4f proceeds %.4f pnl %+.4f hold %.0fs" % (x["cost"], x["proceeds"], x["pnl"], x["blocks"] * 0.1079))
    from collections import Counter
    tot = sum(x["eth"] for x in L if x["side"] == "buy")
    c = Counter()
    for x in L:
        if x["side"] == "buy":
            c[x["who"]] += x["eth"]
    print("total buy eth", round(tot, 4), "top buyers by eth:", [(a[:10], round(e, 3), round(100 * e / tot)) for a, e in c.most_common(5)])
