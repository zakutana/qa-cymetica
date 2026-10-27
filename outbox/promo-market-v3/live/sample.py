"""One sample brief, and every answer the page reads about it, from one model (memory: mock figures come from one model).

The operator, 2026-10-27: "kdyz kliknu na brief co jsme vytvoril, tak tam to chci nejak videt ty nabidky atd, pridej
priklad at na to mrknu jak to je a bude". There is no live brief (their market is empty), so the copy serves this one
to both versions: /expire76?v2 draws it as their v2 does today, /expire76 as v3 would.

Invented, all of it: the brief, the promoters (handles end in _demo), their X numbers and the engine's answers. The
shapes are the ones their promo_market_v2.js reads. The engine here is a stand-in: expected visitors = real views of a
post x 2 %; the real one is Cymetica's verification layer.
"""
from __future__ import annotations

import json
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ID = 9001
AS_OF = "2026-10-27T09:30:00+00:00"
DAYS = ["2026-10-18", "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25", "2026-10-26"]
VISITORS = [6, 31, 48, 39, 27, 22, 30, 28, 24]          # 255, the sum of the promoters' visitors below
USERS = [0, 0, 1, 0, 1, 0, 0, 1, 0]                       # 2 counted + 1 in the 14-day check
PER_VISITOR, PER_USER, BUDGET = 0.05, 5, 100
CLICK_RATE = 0.02                                         # the stand-in engine: visitors a post brings per real view

# the X accounts the stand-in engine knows; anything else gets numbers from its handle's hash
ACCOUNTS = {
    "gemhunter_demo": dict(f=12400, v=6800, r=88, age="3.1 y"),
    "onchain_notes_demo": dict(f=4100, v=2350, r=93, age="1.4 y"),
    "alpha_threads_demo": dict(f=41000, v=15200, r=79, age="5.0 y"),
    "defi_digest_demo": dict(f=8900, v=4100, r=91, age="2.2 y"),
    "memecoin_mia_demo": dict(f=22000, v=9500, r=84, age="4.0 y"),
    "moonfarm_demo": dict(f=52000, v=310, r=21, age="0.8 y", out="52,000 followers but 310 views a post: the audience looks bought"),
}
# (handle, state, new visitors counted, held, new users counted, visitors, posts)
PROMOTERS = [("gemhunter_demo", "paid", 150, 18, 2, 203, 1), ("onchain_notes_demo", "paid", 31, 0, 0, 40, 1),
             ("alpha_threads_demo", "posted", 0, 9, 0, 12, 1)]
PENDING = [("defi_digest_demo", "1h ago"), ("memecoin_mia_demo", "3h ago")]
FILTERED = [["views far under followers: a bought audience", 4], ["X account under 30 days old", 3], ["one device or wallet behind two promoters", 2]]


def nice(usdc: float) -> float:
    """The offer, rounded so it reads well: halves under 10, whole USDC to 100, fives above."""
    step = 0.5 if usdc < 10 else 1 if usdc < 100 else 5
    return max(step, round(usdc / step) * step)


def engine(handle: str, per_visitor: float = PER_VISITOR) -> dict:
    """What Cymetica's verification layer would answer for an X handle: real reach, expected visitors, the offer."""
    h = handle.strip().lstrip("@").lower()
    a = ACCOUNTS.get(h)
    if a is None:
        k = zlib.crc32(h.encode())
        v = 600 + k % 9000
        a = dict(f=v * (2 + k % 5), v=v, r=70 + k % 26, age=f"{1 + k % 6}.{k % 10} y")
    out = dict(handle=h, followers=a["f"], views=a["v"], real=a["r"], age=a["age"])
    if a.get("out"):
        return dict(out, ok=False, why=a["out"])
    exp = round(a["v"] * CLICK_RATE)
    return dict(out, ok=True, expected=exp, offer=nice(exp * per_visitor))


def _earned(p) -> float:
    h, state, counted, _held, users, _vis, _posts = p
    e = engine(h)
    if state == "posted":                 # the post is in its 7-day check: nothing earned yet
        return 0.0
    extra = max(0, counted - e["expected"]) * PER_VISITOR   # the post was paid for the expected visitors already
    return round(e["offer"] + extra + users * PER_USER, 2)


SPENT = round(sum(_earned(p) for p in PROMOTERS), 2)


def brief() -> dict:
    return {"id": ID, "name": "Gem Screener", "path": "/gem-screener", "url": "https://cymetica.com/gem-screener",
            "art": "/static/img/promo-art/gem.svg", "preview_url": "/uploads/bb-previews/gem-screener.jpg?v=1792881466",
            "status": "open", "days": 14, "days_left": 5, "ends_at": "2026-11-01T09:00:00+00:00",
            "budget_usdc": BUDGET, "up_for_grabs_usdc": round(BUDGET - SPENT, 2),
            # their v2 has one price per post; v3 prices the post per promoter (post_by_reach)
            "per_post_usdc": 2, "post_by_reach": True, "per_user_usdc": PER_USER, "per_visitor_usdc": PER_VISITOR,
            "say_line": "Sample brief: how a live one looks.",
            "materials": [{"id": 1, "kind": "image", "title": "Cover picture", "url": "/uploads/bb-previews/gem-screener.jpg?v=1792881466", "size": "the product page"},
                          {"id": 2, "kind": "text", "title": "X post", "body": "Found my last 3 gems on the Gem Screener before CT did. Free, no wallet needed:"}],
            "owner_funds": {"state": "ok", "checked_at": AS_OF}}


def results() -> dict:
    nvc, nvh = sum(p[2] for p in PROMOTERS), sum(p[3] for p in PROMOTERS)
    by = []
    for n, p in enumerate(PROMOTERS, 1):
        by.append({"n": n, "slug": "c/gem-" + p[0][:4], "posts": p[6], "visitors": p[5], "new_visitors": p[2], "new_users": p[4],
                   "earned_usdc": _earned(p), "paid": p[1] == "paid", "pending_ids": []})
    offers = [dict(engine(h), state=s, promoter=n) for n, (h, s, *_r) in enumerate(PROMOTERS, 1)]
    offers += [dict(engine(h), state="pending", applied=ago) for h, ago in PENDING]
    return {"brief": brief(), "spent_usdc": SPENT, "promoters": len(PROMOTERS), "clicks": 318, "visitors_14d": sum(VISITORS),
            "visitors_by_day": dict(zip(DAYS, VISITORS)), "users_by_day": USERS,
            "new_visitors": {"counted": nvc, "held": nvh, "not_counted": 41,
                             "not_counted_by_reason": [{"text": "a hosting network, not a person", "count": 23}, {"text": "seen before on this brief", "count": 18}]},
            "new_users": {"counted": 2, "checking": 1, "not_counted": 4},
            "not_counted_by_reason": [{"reason": "fees_below_price", "count": 3}, {"reason": "blocked_duplicate_ip", "count": 1}],
            "posts": {"confirmed": 2, "checking": 1}, "posts_paid": 2, "sources": [["X", 231], ["Telegram", 24]],
            "by_promoter": by, "materials_used": [["Cover picture", 3], ["X post", 2]], "quotes": [],
            # v3: the offers for a post, what the engine measured, and who it filtered out
            "offers": offers, "filtered_out": FILTERED}


def mine(base: dict) -> dict:
    m = json.loads(json.dumps(base))
    P = m["products"]
    r = results()
    P["products"][0]["brief"] = r
    P["live_briefs"] = 1
    P["totals"] = {"up_for_grabs_usdc": r["brief"]["up_for_grabs_usdc"], "visitors_14d": r["visitors_14d"], "new_users": 2, "spent_usdc": SPENT}
    P["series"] = [{"name": "Gem Screener", "values": [0, 0, 0, 0] + VISITORS + [0]}]
    return m


def market_stats() -> dict:
    return {"up_for_grabs_usdc": brief()["up_for_grabs_usdc"], "open_briefs": 1, "top_per_user_usdc": PER_USER,
            "top_per_user_name": "Gem Screener", "as_of": AS_OF}


def answers() -> dict:
    """path -> answer, for every read the page makes about the sample brief."""
    base = json.loads((HERE / "fixtures" / "mine.json").read_text(encoding="utf-8"))
    stats = market_stats()
    return {
        "/api/v1/promo/mine": mine(base),
        "/api/v1/promo/briefs": {"stats": stats, "briefs": [brief()], "sort": "left", "how_counted": []},
        "/api/v1/promo/house": {"market": stats, "top": [], "mine": {"visitors_14d": sum(VISITORS), "new_users": 2, "products": 13}},
        f"/api/v1/promo/briefs/{ID}": {"brief": brief(), "mine": None},
        f"/api/v1/promo/briefs/{ID}/results": results(),
    }
