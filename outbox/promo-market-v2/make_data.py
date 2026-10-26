"""Write data.js for the Promo Market v2 mockup.

Three globals, so the page can be lifted onto the live site by swapping one function (`api` in app.js) for fetch():

* window.LIVE   -- the live answers, read 2026-10-26 with our own key (snap.py), keyed by the endpoint path the live
                   dashboard calls, field names unchanged. Trimmed to what the page shows: strangers' handles and
                   journalists' addresses are masked (the page is shared outside the account).
* window.PAGE   -- the texts the live page shows that no endpoint returns: page.json (read off the signed-in page) and
                   the public creator page (snap/expire76_public.html): the priority post, the agent prompt, the
                   all-creators measure, the company guide.
* window.SAMPLE -- briefs, for the states the live market cannot show today (it has none open). Every figure comes
                   from one row below and the rules the live API states (how-counted), so the market, a brief's card,
                   its owner's detail and My products are the same numbers. The materials are NEW: no endpoint has them.
"""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snap"


def load(name):
    return json.loads((SNAP / f"{name}.json").read_text(encoding="utf-8"))


def mask(handle):
    """A stranger's handle, first letter kept: the page shows that a person is there, not who."""
    h = (handle or "").lstrip("@")
    return (h[:1] + "•••") if h else ""


def mask_at(text):
    return re.sub(r"@(\w)\w+", lambda m: "@" + m.group(1) + "•••", text or "")


EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


# ---------------- LIVE: the endpoints, as they answered ----------------
def live():
    out = {}
    for name, path in [("promo_mine", "/api/v1/promo/mine"), ("promo_briefs", "/api/v1/promo/briefs"),
                       ("promo_house", "/api/v1/promo/house"), ("promo_how_counted", "/api/v1/promo/how-counted"),
                       ("promo_payouts", "/api/v1/promo/payouts"), ("post_kit", "/api/v1/creator/post-kit"),
                       ("channel_posts", "/api/v1/creator/channel-posts"), ("posts", "/api/v1/creator/posts")]:
        out[path] = load(name)

    links = load("links")
    for l in links["links"]:
        for c in l.get("children") or []:
            c["title"] = mask_at(c.get("title"))
    out["/api/v1/creator/expire76/links"] = links

    r = load("reddit_leads")
    keep = ["id", "kind", "subreddit", "permalink", "title", "score", "relevance", "status", "tool_path", "tool_name",
            "tool_score", "body", "posted_at", "surface", "surface_name"]
    leads = []
    for l in r["leads"][:40]:
        d = {k: l.get(k) for k in keep}
        d["author"] = mask(l.get("author"))
        d["body"] = re.sub(r"\s+\n", "\n", d["body"] or "")[:900]
        leads.append(d)
    out["/api/v1/creator/reddit-leads"] = {"stats": r["stats"], "leads": leads, "artifacts": r["artifacts"]}

    x = load("twitter_leads")
    keep = ["id", "group_key", "group_name", "permalink", "author_followers", "likes", "replies", "impressions",
            "relevance", "status", "tool_path", "tool_name", "tool_score", "body", "posted_at", "surface_name"]
    xs = []
    for l in x["leads"][:30]:
        d = {k: l.get(k) for k in keep}
        d["author"] = mask(l.get("author"))
        d["body"] = mask_at(d["body"])
        d["permalink"] = None                      # the link names the author
        xs.append(d)
    out["/api/v1/creator/twitter-leads"] = {"stats": x["stats"], "leads": xs, "groups": x["groups"]}

    j = load("journalists")
    reqs = []
    for q in j["requests"]:
        d = {k: q.get(k) for k in ["id", "platform", "outlet", "outlet_tier", "category", "subject", "topics",
                                   "relevance", "deadline_at", "hours_left", "status"]}
        d["query"] = EMAIL.sub("(their address is on the request)", q.get("query") or "")
        reqs.append(d)
    out["/api/v1/creator/journalist-requests"] = {"stats": j["stats"], "requests": reqs, "pitched": j.get("pitched") or []}

    rw = load("rewards")
    for e in rw["recent"]:
        e["where"] = mask_at(e.get("where"))
        e["text"] = mask_at(e.get("text"))
        if e.get("source") != "self":
            e["permalink"] = None                  # a stranger's thread
    out["/api/v1/creator/rewards"] = rw
    return out


# ---------------- PAGE: what only the page says ----------------
def page_texts():
    p = json.loads((HERE / "page.json").read_text(encoding="utf-8"))
    h = (SNAP / "expire76_public.html").read_text(encoding="utf-8")
    t = html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S))
    t = re.sub(r"<[^>]+>", "\n", t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    flat = re.sub(r"\s*\n\s*", " ", t)

    def grab(a, b, src=flat):
        m = re.search(re.escape(a) + r"\s*(.*?)\s*" + re.escape(b), src, re.S)
        return re.sub(r"\s+([,.:;])", r"\1", m.group(1).strip()) if m else None

    p["trade_prompt"] = re.search(r"(Read https://cymetica\.com/llms\.txt.*?Wait for my instructions before placing any trade\.)",
                                  t, re.S).group(1)
    p["trade_prompt"] = re.sub(r'"contact_email": "\s*\n\s*"', '"contact_email": ""', p["trade_prompt"])
    p["trade_lead"] = "Stay in your chatbox. Copy this into ChatGPT, Claude, Gemini, Meta Muse or any MCP/HTTP agent — it registers itself, funds with your own USDC and trades. No website, no install."
    note = grab("Tweet this now — top priority", "X post")
    p["tweet_note"] = note
    p["tweet_nth"] = re.search(r"Today's post is (\d+ of \d+)", note).group(1)
    p["tweet_chars"] = int(re.search(r"(\d+) / 280 weighted characters", flat).group(1))
    p["tweet"] = grab("weighted characters", "X may not show the link card")
    p["tweet_img"] = re.findall(r'<img[^>]+src="(https://cymetica\.com/og/app/[^"]+)"', h)[0]
    p["why_post"] = grab("Why post: every post is a small, permanent stream of visitors", "Live measure")
    m = re.search(r"Live measure across all creators, last 30 days: ([\d.]+) clicks per posted link per day \(median ([\d.]+)\) over (\d+) links, (\d+) unique visitors", flat)
    p["measure"] = {"per_link_day": float(m.group(1)), "median": float(m.group(2)), "links": int(m.group(3)), "uniq": int(m.group(4))}
    steps = re.sub(r"\s+([,.:;])", r"\1", re.search(r"Step by step\s*(.*?climb on this dashboard\.)", flat).group(1))
    p["step_by_step"] = [s.strip() for s in re.split(r"\s(?=Open a reply queue|Reply with this page:|Mark posted with|Repeat daily)", steps)]
    # the company guide: a title line ending in "." followed by its paragraph
    g = t[t.find("Start an app and a company"):]
    g = g[:g.find("This guide describes")]
    intro = grab("Start an app and a company", "Build the company on the platform.", re.sub(r"\s*\n\s*", " ", g))
    body = g[g.find("Build the company on the platform."):]
    parts = re.split(r"\n(?=[A-Z][^\n]{3,60}\.\n )", "\n" + body)
    gsteps = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title, _, text = part.partition("\n")
        gsteps.append([title.strip(), re.sub(r"\s+", " ", text).strip()])
    stake = gsteps[-1][1].split(" Cymetica takes a 1%")[0] if gsteps else ""
    if gsteps and " Cymetica takes a 1%" in gsteps[-1][1]:
        gsteps[-1][1] = stake
    p["company"] = {"intro": intro.replace(" , ", ", ").replace(" .", "."), "steps": gsteps,
                    "disclaimer": "This guide describes the platform's process and public facts. It is not legal, tax or investment advice; ask your own counsel before choosing a domicile or structure."}
    return p


# ---------------- SAMPLE: briefs, one model ----------------
# id, product path, name, per post, per new user, per new visitor (USDC), budget, days, days run, owner (us = the operator's
# own product), promoters, clicks through the links, posts paid, users counted / checking / not counted, new visitors
# counted / held / not counted. Spent and up for grabs are derived, never typed.
ROWS = [
    (101, "/gem-screener", "Gem Screener", 2, 5, 0.05, 500, 14, 5, True, 9, 1840, 14, 11, 4, 9, 820, 190, 214),
    (102, "/chart-analyzer", "Chart Analyzer", 2, 4, 0.05, 400, 30, 12, True, 7, 2410, 19, 16, 3, 12, 1190, 160, 302),
    (103, "/agent-tournaments", "Agent Tournaments", 3, 8, 0, 300, 14, 9, True, 4, 690, 11, 9, 2, 6, 0, 0, 0),
    (104, "/supply-analyzer", "Supply Analyzer", 1, 0, 0.03, 120, 7, 2, True, 3, 410, 6, 0, 0, 0, 260, 64, 41),
    (105, "/launch-check", "Safe Launch Check", 2, 6, 0.04, 800, 30, 4, False, 12, 2950, 21, 14, 6, 11, 1300, 420, 380),
]
SAY = {
    "/gem-screener": "Most token lists rank by hype. This one ranks by revenue.",
    "/chart-analyzer": "READY TO POP, READY TO DUMP or NO EDGE: a probability from history, never a promise.",
    "/agent-tournaments": "10 agents, 1 table, best ROI wins. Paper tables are open now.",
    "/supply-analyzer": "Type any token and see its supply. One source per number.",
    "/launch-check": "Paste any new token and see, on-chain, whether it can rug you.",
}
# each product page's own og:image (read 2026-10-22); the material a promoter downloads first
OG = {
    "/gem-screener": "https://cymetica.com/og/app/gem-screener.png?t=Gem%20Screener%20%7C%20EventTrader&v=4",
    "/agent-tournaments": "https://cymetica.com/og/app/agent-tournaments.png?t=Agent%20Tournaments%3A%2010%20agents.%201%20table.%20Best%20ROI%20wins.&v=4",
    "/chart-analyzer": "https://cymetica.com/og/app/chart-analyzer.png?v=4",
    "/supply-analyzer": "https://cymetica.com/og/app/supply-analyzer.png?v=4",
    "/launch-check": "https://cymetica.com/og/app/launch-check.png?t=Safe%20Launch%20Check%20%E2%80%94%20EventTrader&v=4",
}
# where the visitors came from (the referrer host of each visit through a promoter's link), one split per brief
SOURCES = {101: [("X", .46), ("Reddit", .31), ("Telegram", .14), ("Discord", .05), ("Other", .04)],
           102: [("X", .38), ("Reddit", .40), ("Telegram", .12), ("Discord", .04), ("Other", .06)],
           103: [("X", .52), ("Reddit", .18), ("Telegram", .10), ("Discord", .15), ("Other", .05)],
           104: [("X", .30), ("Reddit", .55), ("Telegram", .08), ("Discord", .02), ("Other", .05)],
           105: [("X", .35), ("Reddit", .22), ("Telegram", .33), ("Discord", .05), ("Other", .05)]}
# why a new user or a new visitor was not counted: the live API's own reasons, one split for every brief
USER_NOT = [("blocked_same_ip", .34), ("late_signup", .22), ("no_deposit", .26), ("fees_below_price", .18)]
VISIT_NOT = [("datacenter", "a hosting or cloud network", .41), ("seen", "seen before on this brief", .33),
             ("check", "failed the browser check", .18), ("own", "the promoter's own visit", .08)]


def split(total, shares):
    out = [int(total * s) for s in shares]
    out[0] += total - sum(out)
    return out


def daily(total, n, seed):
    """`total` over the last `n` days, rising as more posts go up: one curve per brief."""
    w = [(i + 1) ** 0.8 * (1 + 0.35 * ((seed * 7 + i * 13) % 5 - 2) / 2) for i in range(n)]
    s = sum(w)
    out = [round(total * x / s) for x in w]
    out[-1] += total - sum(out)
    return out


def sample(day_labels):
    briefs, results = [], {}
    for (bid, path, name, pp, pu, pv, budget, days, run, ours, prom, clicks, posts, uc, uchk, unot, vc, vh, vnot) in ROWS:
        spent = round(posts * pp + uc * pu + vc * pv, 2)
        left = round(budget - spent, 2)
        # unique visitors through the links: never fewer than the visitors and users the checks looked at
        uniq = max(vc + vh + vnot + uc + uchk + unot, round(clicks * 0.62))
        b = {"id": bid, "name": name, "path": path, "url": "https://cymetica.com" + path, "per_post_usdc": pp,
             "per_user_usdc": pu, "per_visitor_usdc": pv, "budget_usdc": budget, "up_for_grabs_usdc": left,
             "days": days, "days_left": days - run, "ends_at": None, "status": "open", "say_line": SAY[path],
             "owner_funds": {"state": "covered", "checked_at": "2026-10-26T10:12:00+00:00"}, "mine": ours,
             # NEW: what the owner uploaded for promoters (no endpoint has it yet)
             "materials": materials(path, name)}
        briefs.append(b)
        n14 = min(14, run)
        by_day = [0] * (14 - n14) + daily(uniq, n14, bid)
        users_by_day = [0] * (14 - n14) + daily(uc, n14, bid + 3)
        # the promoters: the totals split by weight, so their rows add up to the brief
        wts = [1 / (k + 1) ** 0.9 for k in range(prom)]
        sw = sum(wts)
        shares = [x / sw for x in wts]
        cols = [split(v, shares) for v in (clicks, uniq, posts, vc, uc)]
        promoters = []
        for k in range(prom):
            e = round(cols[2][k] * pp + cols[4][k] * pu + cols[3][k] * pv, 2)
            promoters.append({"n": k + 1, "slug": "c/" + "abcdefghjkmnpqrstuvwxyz"[(bid + k * 7) % 23] + "x" + str(bid)[-1] + "k" + str(k),
                              "clicks": cols[0][k], "visitors": cols[1][k], "posts": cols[2][k], "new_visitors": cols[3][k],
                              "new_users": cols[4][k], "earned_usdc": e, "paid": k % 3 == 2})
        mat_use = [[m["title"], round(prom * f)] for m, f in zip(b["materials"], (0.9, 0.7, 0.5, 0.35, 0.2))]
        results[bid] = {"brief": b, "promoters": prom, "visitors_14d": uniq, "visitors_by_day": dict(zip(day_labels, by_day)),
                        "new_users": {"counted": uc, "checking": uchk, "not_counted": unot},
                        "new_visitors": {"counted": vc, "held": vh, "not_counted": vnot,
                                         "not_counted_by_reason": [{"reason": k, "text": t, "count": c} for (k, t, _), c in
                                                                   zip(VISIT_NOT, split(vnot, [s for _, _, s in VISIT_NOT]))]},
                        "users_not_by_reason": [[k, c] for (k, _), c in zip(USER_NOT, split(unot, [s for _, s in USER_NOT]))],
                        "posts": {"paid": posts, "checking": max(0, prom // 3)}, "spent_usdc": spent,
                        "payouts": "Earnings wait for your Pay press.",
                        # NEW in this mockup: the table the owner reads to see who brought what
                        "clicks": clicks, "users_by_day": users_by_day,
                        "sources": [[s, c] for (s, _), c in zip(SOURCES[bid], split(uniq, [x for _, x in SOURCES[bid]]))],
                        "by_promoter": promoters, "materials_used": mat_use,
                        "quotes": quotes(bid, path)}
    taken = {"takes": [{"brief_id": 105, "name": "Safe Launch Check", "path": "/launch-check", "slug": "c/q7w2launch",
                        "tracked_url": "https://cymetica.com/c/q7w2launch", "taken_at": "2026-10-23T09:12:00+00:00"}],
             "earnings": [], "earned_usdc": 0, "payouts_enabled": True}
    p = results[105]["by_promoter"][2]                     # we are the third promoter on Safe Launch Check
    taken["takes"][0].update({"visitors": p["visitors"], "posts": p["posts"], "new_visitors": p["new_visitors"],
                              "new_users": p["new_users"], "earned_usdc": p["earned_usdc"]})
    taken["earned_usdc"] = p["earned_usdc"]
    return {"briefs": briefs, "results": results, "taken": taken}


def materials(path, name):
    """What the owner uploads on Post a brief (NEW). Pictures are the product's own og image; texts its own words."""
    slug = path.strip("/").replace("/", "-")
    return [
        {"kind": "image", "title": "Share card", "file": slug + "-card.png", "size": "1200 × 630", "src": OG.get(path)},
        {"kind": "text", "title": "X post", "body": SAY[path] + " https://cymetica.com" + path},
        {"kind": "video", "title": "30-second demo", "file": slug + "-demo.mp4", "size": "0:30 · 6.2 MB"},
        {"kind": "text", "title": "Reddit post", "body": name + ": " + SAY[path]},
        {"kind": "link", "title": "Product page", "url": "https://cymetica.com" + path},
    ]


def quotes(bid, path):
    """An influencer's price for one post to their audience (the live API has quotes: audience_url, size, price)."""
    if bid not in (101, 105):
        return []
    return [{"id": bid * 10 + 1, "audience_url": "https://x.com/" + ("c•••" if bid == 101 else "d•••"),
             "audience_size": 48200 if bid == 101 else 120400, "price_usdc": 60 if bid == 101 else 150, "status": "waiting"}]


def main():
    L = live()
    P = page_texts()
    days = L["/api/v1/promo/mine"]["products"]["day_labels"]
    S = sample(days)
    js = ("/* Written by make_data.py from snap/ (read 2026-10-26) and page.json. Do not edit by hand. */\n"
          "window.LIVE = " + json.dumps(L, ensure_ascii=False, separators=(",", ":")) + ";\n"
          "window.PAGE = " + json.dumps(P, ensure_ascii=False, separators=(",", ":")) + ";\n"
          "window.SAMPLE = " + json.dumps(S, ensure_ascii=False, separators=(",", ":")) + ";\n")
    (HERE / "data.js").write_text(js, encoding="utf-8")
    print("data.js", len(js), "bytes")
    print("products", len(L["/api/v1/promo/mine"]["products"]["products"]), "| reddit", len(L["/api/v1/creator/reddit-leads"]["leads"]),
          "| x", len(L["/api/v1/creator/twitter-leads"]["leads"]), "| press", len(L["/api/v1/creator/journalist-requests"]["requests"]),
          "| links", len(L["/api/v1/creator/expire76/links"]["links"]))
    print("tweet", P["tweet_chars"], P["tweet_nth"], P["tweet"][:60], "| img", P["tweet_img"])
    print("company steps", [s[0] for s in P["company"]["steps"]])
    cat = len(P["catalogue_named"]) + len([n for n, _ in P["queue_tools"] if n not in dict(P["catalogue_named"])]) + \
        len([n for n in P["queue_tools_empty"] if n not in dict(P["catalogue_named"])])
    print("catalogue", cat, "of", P["catalogue_count"])
    # one cross-screen sum: a brief's promoters add up to the brief, the market's total is the briefs'
    for bid, r in S["results"].items():
        bp = r["by_promoter"]
        assert sum(p["new_users"] for p in bp) == r["new_users"]["counted"]
        assert sum(p["visitors"] for p in bp) == r["visitors_14d"]
        assert abs(sum(p["earned_usdc"] for p in bp) - r["spent_usdc"]) < 0.05, (bid, sum(p["earned_usdc"] for p in bp), r["spent_usdc"])
        assert sum(r["visitors_by_day"].values()) == r["visitors_14d"]
        b = r["brief"]
        print(bid, b["name"], "spent", r["spent_usdc"], "left", b["up_for_grabs_usdc"], "visitors", r["visitors_14d"],
              "users", r["new_users"]["counted"], "nv", r["new_visitors"]["counted"])
    print("market up for grabs", round(sum(b["up_for_grabs_usdc"] for b in S["briefs"]), 2), "open", len(S["briefs"]))


if __name__ == "__main__":
    main()
