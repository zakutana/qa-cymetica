"""Write data.js for the Promo Market mockup from one snapshot (snap/, read 2026-10-22).

Everything the creator dashboard shows today comes from the snapshot: our own account's links, rewards and queues
(expire76, read with our key), the demo creator's public links (Mumtaz, /api/v1/creator/mumtaz/links), the live page's
own texts (the priority post, the Radar apps, the all-creators measure) and the Build it Better apps leaderboard.
Only what the page shows is kept: no journalist's name or address, no stranger's handle.

The briefs are NEW (the market does not exist yet): one small model below, every figure derived from its row
(spent = posts paid x pay, left = budget - spent), so no screen can contradict another. The house brief is today's
real programme: 1,000 ET10 + 1,000 ETLP per displayed post, open to every creator.
"""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snap"
DAY = "2026-10-22"


def load(name):
    return json.loads((SNAP / name).read_text(encoding="utf-8"))


def clean_title(t):
    return re.sub(r"\s*\(Claude artifact\)$", "", t or "").strip()


def link_row(l):
    kids = []
    for c in l.get("children") or []:
        kids.append([c["title"], c["kind"], c["clicks"], c["unique_visitors"]])
    return {
        "slug": l["slug"], "title": clean_title(l["title"]), "kind": l["kind"], "page": bool(l.get("has_page")),
        "art": l.get("artifact_url"), "target": l.get("target_url"),
        "clicks": l["clicks"], "reads": l["reads"], "likes": l["likes"], "uniq": l["unique_visitors"],
        "series": [[d["click"], d["read"], d["like"]] for d in l["series"]],
        "refs": [[r["host"].replace("www.", ""), r["count"]] for r in (l.get("top_referrers") or [])][:3],
        "created": (l.get("created_at") or "")[:10], "last": (l.get("last_activity") or "")[:16].replace("T", " "),
        "kids": kids,
    }


def creator(name):
    d = load(name)
    links = [link_row(l) for l in d["links"]]
    days = [s["day"] for s in d["links"][0]["series"]]
    tot = [[0, 0, 0] for _ in days]
    for l in d["links"]:
        for i, s in enumerate(l["series"]):
            tot[i][0] += s["click"]; tot[i][1] += s["read"]; tot[i][2] += s["like"]
        for c in l.get("children") or []:
            for i, s in enumerate(c.get("series") or []):
                tot[i][0] += s["click"]
    s = d["summary"]
    return {"username": d["username"], "summary": {"links": s["links"], "clicks": s["clicks"], "reads": s["reads"],
            "likes": s["likes"], "uniq": s["unique_visitors"], "likes_excluded": s.get("likes_excluded", 0),
            "likes_note": (s.get("likes_correction") or {}).get("reason", ""),
            "likes_date": (s.get("likes_correction") or {}).get("date", "")},
            "days": days, "total": tot, "links": links}


def live_texts():
    t = (SNAP / "mumtaz.txt").read_text(encoding="utf-8")
    tweet = re.search(r"X post\n\d+ / 280 weighted characters\n(.*?)\nX may not show", t, re.S).group(1).strip()
    nth = re.search(r"Today's post is (\d+ of \d+)", t).group(1)
    measure = re.search(r"Live measure across all creators, last 30 days: (.*?)\n", t).group(1).strip()
    per_day = re.search(r"One posted page brings at least ([\d–-]+) visitors a day", t).group(1)
    agent = re.search(r"(Read https://cymetica.com/llms.txt.*?Wait for my instructions before placing any trade\.)", t, re.S).group(1)
    return {"tweet": tweet, "tweet_nth": nth, "measure": measure, "per_day": per_day, "trade_prompt": agent}


def radar():
    h = (SNAP / "mumtaz.html").read_text(encoding="utf-8")
    i = h.find("Radar apps: post these"); j = h.find("Tracked links", i)
    txt = html.unescape(re.sub(r"<[^>]+>", "\n", h[i:j]))
    lines = [re.sub(r"\s+", " ", x).strip() for x in txt.split("\n")]
    lines = [x for x in lines if x and x != ","]
    names = lines[lines.index("Safe Launch Check"):lines.index("Safe Launch Check") + 5]
    apps, cur = [], None
    k = 0
    while k < len(lines):
        x = lines[k]
        if x == "Rebuilt from":
            cur = {"name": names[len(apps)], "from": lines[k + 1], "line": lines[k + 2].lstrip()}
            # "(anti-rug token launchpad). Paste any new token ..." -> kind and pitch
            m = re.match(r"\((.*?)\)\.\s*(.*)", cur["line"])
            if m:
                cur["from_kind"], cur["line"] = m.group(1), m.group(2)
            apps.append(cur)
        elif cur is not None and x == "Who to reach:":
            cur["who"] = lines[k + 1]
        elif cur is not None and x == "Subreddits:":
            subs = []
            k += 1
            while lines[k].startswith("r/"):
                subs.append(lines[k]); k += 1
                if lines[k] == ".":
                    break
            cur["subs"] = subs
        elif cur is not None and x.startswith("Open ") and x.endswith("↗"):
            cur["url"] = lines[k + 1]
        elif cur is not None and x == "title + body":
            cur["reddit_title"] = lines[k + 1]
            body, k = [], k + 2
            while lines[k] != "Copy title":
                body.append(lines[k]); k += 1
            cur["reddit_body"] = "\n\n".join(body)
        elif cur is not None and x == "≤ 280 weighted characters":
            cur["x_post"] = lines[k + 1]
        elif cur is not None and x == "copy it into the group yourself":
            cur["tg_post"] = lines[k + 1]
        elif cur is not None and x == "Telegram groups:":
            groups = []
            k += 1
            while lines[k].startswith("@"):
                groups.append(lines[k]); k += 1
            cur["groups"] = groups
        k += 1
    return apps


def rewards():
    d = load("api_v1_creator_rewards.json")
    rec = [{"where": r["where"], "text": r["text"][:90], "status": r["reward_status"], "note": r["reward_note"],
            "day": r["replied_at"][:10]} for r in d["recent"]]
    return {"summary": d["summary"], "recent": rec}


def queues():
    r = load("api_v1_creator_reddit-leads.json")
    x = load("api_v1_creator_twitter-leads.json")
    p = load("api_v1_creator_journalist-requests.json")
    reddit = [{"id": l["id"], "sub": l["subreddit"], "title": l["title"], "rel": l["relevance"], "score": l["score"],
               "tool": l["tool_name"], "path": l["tool_path"], "at": (l.get("posted_at") or "")[:16].replace("T", " "),
               "kind": l["kind"], "body": re.sub(r"\s+", " ", l.get("body") or "")[:260]} for l in r["leads"][:14]]
    xs = [{"id": l["id"], "group": l["group_name"], "followers": l["author_followers"], "likes": l["likes"],
           "views": l["impressions"], "tool": l["tool_name"], "path": l["tool_path"],
           "at": (l.get("posted_at") or "")[:16].replace("T", " "),
           "body": re.sub(r"@\w+\s*", "", re.sub(r"\s+", " ", l.get("body") or ""))[:220]} for l in x["leads"][:10]]
    press = [{"id": q["id"], "outlet": q["outlet"], "tier": q["outlet_tier"].replace("tier_", "").upper(),
              "cat": q["category"], "subject": q["subject"], "hours": q["hours_left"], "topics": q.get("topics") or []}
             for q in p["requests"]]
    pages = [{"slug": a["slug"], "title": clean_title(a["title"]), "surface": a.get("surface")} for a in r["artifacts"]]
    return {"reddit": {"stats": r["stats"], "items": reddit}, "x": {"stats": x["stats"], "items": xs},
            "press": {"stats": p["stats"], "items": press}, "pages": pages}


def post_kit():
    k = load("api_v1_creator_post-kit.json")
    return {"x_rule": k["kit"]["x"]["rule"], "reddit_rule": k["kit"]["reddit"]["rule"],
            "telegram_rule": k["kit"]["telegram"]["rule"], "discord_rule": k["kit"]["discord"]["rule"],
            "mention": k["kit"]["x"]["mention"], "x_tags": k["kit"]["x"]["hashtags"],
            "discord_invite": k["kit"]["discord"]["invite"], "playbook": k["playbook"]}


# ---------------- the market: NEW, a model. Figures are placeholders, each derived from its own row. ----------------
# A brief pays a promoter two things, in USDC, and nothing else is on its card (the operator, 2026-10-22: "jako marketer
# me jen zajima kolik muzu vydelat kdyz to postnu a kolik ziskam za kazdeho noveho unique uzivatele"): a fixed sum per
# post that stays up, and a sum per new unique user the promoter's link brings (checked before it is paid: "plati se jen
# za vysledek ... aby to neslo ojebavat"). Up for grabs is what is left of the budget.
# why a sign-up was not counted, and each reason's share (one split for every brief; the owner's view shows it)
REJECT = [("same device or network as another user", 0.38), ("wallet funded by the promoter or a known farm", 0.27),
          ("no proof of person (Telegram or a wallet with history)", 0.21), ("gone before the 14-day check", 0.14)]
# key, product, path, the ask (the product's own live words), per post, per new user (USDC), budget, posts paid,
# new users paid, not counted, unique visitors the links brought, days left, posted (days ago). gem, casino, chart and
# supply are the operator's own products (part B); company and launch are Cymetica's.
BRIEFS = [
    ("gem", "Gem Screener", "/gem-screener", "Most token lists rank by hype. This one ranks by revenue.", 5, 4, 2000, 38, 61, 148, 2180, 12, 18),
    ("casino", "Agent Tournaments", "/agent-tournaments", "10 agents, 1 table, best ROI wins. Paper tables are open now.", 8, 12, 3000, 20, 38, 97, 1410, 5, 9),
    ("chart", "Chart Analyzer", "/chart-analyzer", "READY TO POP, READY TO DUMP or NO EDGE: a probability from history, never a promise.", 4, 3, 1500, 52, 112, 260, 3900, 9, 21),
    ("supply", "Supply Analyzer", "/supply-analyzer", "Type any token and see its supply. One source per number.", 5, 5, 1200, 9, 22, 41, 690, 18, 12),
    ("company", "Build a Company", "/company", "A team of AI departments run by NEXUS on your own plan.", 25, 40, 4000, 6, 9, 12, 300, 21, 9),
    ("launch", "Safe Launch Check", "/launch-check", "Paste a token contract and read the rug risks straight from the chain.", 3, 2, 800, 41, 140, 301, 4400, 2, 12),
]
# The operator's own products: the apps their Build it Better requests built (their tickets cite this repository), with
# the leaderboard's 30-day traffic. key, path, the picture's kind.
MINE = [("gem", "/gem-screener"), ("chart", "/chart-analyzer"), ("casino", "/agent-tournaments"), ("nexus", "/nexus-panel"),
        ("supply", "/supply-analyzer"), ("team", "/team-dump-radar"), ("infil", "/infiltrator"), ("agents", "/my-agents")]


# each product page's own og:image, as its <meta property="og:image"> read 2026-10-22: the ?t= is the title the
# picture carries (without it the endpoint draws another title, e.g. a Build it Better request's)
OG = {
    "gem-screener": "https://cymetica.com/og/app/gem-screener.png?t=Gem%20Screener%20%7C%20EventTrader&v=4",
    "agent-tournaments": "https://cymetica.com/og/app/agent-tournaments.png?t=Agent%20Tournaments%3A%2010%20agents.%201%20table.%20Best%20ROI%20wins.&v=4",
    "chart-analyzer": "https://cymetica.com/og/app/chart-analyzer.png?v=4",
    "supply-analyzer": "https://cymetica.com/og/app/supply-analyzer.png?v=4",
    "company": "https://cymetica.com/og/app/company.png?t=Build%20a%20Company%20%7C%20EventTrader&v=4",
    "launch-check": "https://cymetica.com/og/app/launch-check.png?t=Safe%20Launch%20Check%20%E2%80%94%20EventTrader&v=4",
}


def daily(total, days, seed):
    """`total` visitors spread over the last `days` days, rising as more posts go up: one curve per brief, so the
    owner's chart and its counters are the same numbers."""
    w = [(i + 1) ** 0.8 * (1 + 0.35 * ((seed * 7 + i * 13) % 5 - 2) / 2) for i in range(days)]
    s = sum(w)
    out = [round(total * x / s) for x in w]
    out[-1] += total - sum(out)
    return out


def market(q):
    apps = {a["path"]: a for a in load("bib_apps.json")["apps"]}
    out = []
    for i, (key, name, path, ask, per_post, per_user, budget, posts, users, rejected, visitors, days, age) in enumerate(BRIEFS):
        spent = posts * per_post + users * per_user
        run = min(14, age)                                   # days the brief has run inside the 14-day window
        series = [0] * (14 - run) + daily(round(visitors * run / age), run, i)
        out.append({"key": key, "name": name, "path": path, "ask": ask, "per_post": per_post, "per_user": per_user,
                    "budget": budget, "posts": posts, "users": users, "rejected": rejected, "visitors": visitors,
                    "spent": spent, "left": budget - spent, "days": days, "age": age, "series": series,
                    "rejects": [[why, round(rejected * share)] for why, share in REJECT],
                    "threads": sum(1 for l in q["reddit"]["items"] + q["x"]["items"] if l["path"] == path)})
    mine = []
    for key, path in MINE:
        a = apps.get(path) or {}
        mine.append({"key": key, "name": a.get("name"), "path": path, "visitors30": a.get("visitors"),
                     "uses30": a.get("uses"), "views30": a.get("views"),
                     "brief": key if any(b["key"] == key for b in out) else None})
    replied = q["reddit"]["stats"]["replied"] + q["x"]["stats"]["replied"]
    house = {"pay": 1000, "pay2": 1000, "replied": replied, "open_threads": q["reddit"]["stats"]["new"] + q["x"]["stats"]["new"]}
    return {"briefs": out, "mine": mine, "house": house}


def main():
    q = queues()
    data = {"day": DAY, "me": creator("our_links.json"), "pub": creator("mumtaz_links.json"), "live": live_texts(),
            "radar": radar(), "rewards": rewards(), "queues": q, "kit": post_kit(), "market": market(q)}
    js = "/* Written by make_data.py from snap/ (read " + DAY + "). Do not edit by hand. */\nwindow.PM = " + \
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (HERE / "data.js").write_text(js, encoding="utf-8")
    m = data["market"]
    print("data.js", len(js), "bytes | me", data["me"]["summary"], "| pub links", len(data["pub"]["links"]),
          "| radar", [a["name"] for a in data["radar"]], [len(a.get("subs", [])) for a in data["radar"]],
          "| briefs", len(m["briefs"]), "| mine", [(x["name"], x["visitors30"], x["brief"]) for x in m["mine"]])
    # the chart's sum against the page's own counters, so the picture never says more than the page does
    for who in ("me", "pub"):
        c = data[who]
        print(who, "14d clicks", sum(d[0] for d in c["total"]), "reads", sum(d[1] for d in c["total"]),
              "likes", sum(d[2] for d in c["total"]), "| all-time", c["summary"]["clicks"], c["summary"]["reads"], c["summary"]["likes"])


if __name__ == "__main__":
    main()
