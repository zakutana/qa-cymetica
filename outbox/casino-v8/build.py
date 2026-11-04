"""Build the Agent Casino lobby mock v8: their live page with scripts out, everything below their app bar replaced by ours.

    python outbox/casino-v8/build.py
    python scripts/serve_mock.py outbox/casino-v8 8842 --quiet

Reads only, and only ../casino-v7 (index.html, data.js, owner.js), which stays untouched: no request to Cymetica is made here. Every figure on the page comes from their markup or from those two files: nothing is typed here. The table picture is made
once by render/render.py and lives in art/.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
V7 = HERE.parent / "casino-v7"
VERSION = "6"


def source() -> str:
    """v7's copy of their lobby (their HTML, no script of theirs, assets absolute, fonts fixed), taken beside the owner's panels:
    one moment, so a running table's leader and our rank on it cannot contradict each other."""
    html = (V7 / "index.html").read_text(encoding="utf8")
    html = html.replace('<link rel="stylesheet" href="v7.css">', "")
    return re.sub(r'<script src="(data|owner|v7)\.js"></script>', "", html)


def text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=False)).strip() if node else ""


def seat(node) -> dict:
    ava = node.select_one(".at-ava")
    use = node.select_one("use")
    style = ava.get("style", "") if ava else ""
    colour = re.search(r"--c:\s*(#[0-9a-fA-F]{3,8})", style)
    classes = node.get("class", [])
    return {"bot": ava.get("title") if ava else None, "colour": colour.group(1) if colour else None,
            "shape": use.get("href", "#at-bot-a")[-1] if use else None, "lead": "lead" in classes,
            "pending": "pend" in classes, "empty": "empty" in classes}


def card(node) -> dict:
    buy = node.select_one(".at-bbuy")
    small = buy.select_one("small") if buy else None
    tags = node.get("data-tags", "")
    hours = re.search(r"\bh(1|5|24)\b", tags)
    state = node.select_one(".at-st")
    cdn, pb, cdl = node.select_one(".at-cdn"), node.select_one(".at-pb"), node.select_one(".at-cdl")
    prizes = []
    for cell in node.select(".at-c3 > div"):
        b = cell.select_one("b")
        unit = b.select_one("small") if b else None
        prizes.append({"place": text(cell.select_one(".k")), "cash": text(b).replace(text(unit), "").strip() if unit else text(b),
                       "unit": text(unit), "extra": text(cell.select_one(".e"))})
    return {"id": int(node["data-table-id"]) if node.has_attr("data-table-id") else None, "href": node.get("href"),
            "tag": node.get("class", []), "buy": (text(buy).replace(text(small), "").strip() if small else text(buy)),
            "unit": text(small), "cur": "ET10" if re.search(r"\bet10\b", tags) else "USDC", "hours": int(hours.group(1)) if hours else None,
            "len": text(node.select_one(".at-clk b")), "state": [c for c in state.get("class", []) if c not in ("at-st", "glow")][0] if state else None,
            "stateText": text(state), "end": cdn.get("data-end") if cdn else None, "start": pb.get("data-start") if pb else None,
            "cdl": text(cdl), "potKey": text(node.select_one(".at-pot .k")), "pot": text(node.select_one(".at-pot .v")),
            "potSub": text(node.select_one(".at-pot .s")), "prizes": prizes, "who": text(node.select_one(".at-tfoot .who")),
            "cta": text(node.select_one(".at-tfoot .v")), "seats": [seat(s) for s in node.select(".at-seat")]}


def owner_panels() -> dict:
    """What their page draws only for the signed-in owner, from v7's copy of it; 'Flash ' goes, the operator's word."""
    raw = (V7 / "owner.js").read_text(encoding="utf8")
    pieces = dict(re.findall(r"^\s*(asks|agents): (.*?)(?=^\s*(?:asks|agents):|^\};)", raw, flags=re.S | re.M))
    joined = {k: "".join(re.findall(r"'((?:[^'\\]|\\.)*)'", v)) for k, v in pieces.items()}
    live = {int(k): {"bot": b, "rank": r, "roi": o} for k, b, r, o in re.findall(r"(\d+): \{ bot: '([^']*)', rank: '([^']*)', roi: '([^']*)' \}", raw)}
    asks = []
    soup = BeautifulSoup(joined["asks"], "html.parser")
    for row in soup.select(".at-ask"):
        ava, link, small = row.select_one(".at-ava"), row.select_one(".nm a"), row.select_one("small.dim")
        full = text(small)
        first = full.split(". ")[0]              # the allowance sentence, cut only at their own semicolons
        parts = [re.sub(r"\s*\(.*?\)", "", p).strip() for p in first.split(";")]   # the bracket and the middle clauses wait behind More
        asks.append({"bot": ava["title"], "colour": re.search(r"--c:(#\w+)", ava["style"]).group(1), "shape": ava.select_one("use")["href"][-1],
                     "href": link["href"], "table": int(link["href"].rsplit("/", 1)[1]), "label": text(link).replace("Flash ", ""),
                     "short": f"{parts[0]}; {parts[-1]}", "why": [text(x) for x in split_why(small)],
                     "lapses": text(row.select_one(".lapse")), "loss": text(row.select_one(".loss b"))})
    agents = []
    for row in BeautifulSoup(joined["agents"], "html.parser").select(".at-ar.live"):
        need = row.select_one(".needvol")
        rank = row.select_one(".arank")
        agents.append({"bot": text(row.select_one(".nm b")), "table": int(row["href"].rsplit("/", 1)[1]), "href": row["href"],
                       "label": re.sub(r"\s*FLASH$", "", text(row.select_one(".tb b"))).replace("Flash ", ""),
                       "rank": text(rank).replace(" ", ""), "roi": text(row.select_one(".roi")), "need": text(need)})
    head = soup.select_one(".at-asks-all")
    return {"asks": asks, "agents": agents, "live": live, "total": text(soup.select_one("[data-total-loss]")),
            "sub": text(soup.select_one(".sub")), "head": text(soup.select_one(".at-asks-h h2 span")), "approveAll": text(head.select_one(".blue span")),
            "declineAll": text(head.select_one(".no")), "totalLabel": text(head.select_one("small span"))}


def split_why(small) -> list:
    """Their three warnings as they wrote them: the allowance, the sentence they set in red, the one-member note."""
    parts, out = [], []
    bold = small.select_one("b")
    before = bold.previous_sibling if bold else None
    after = bold.next_sibling if bold else None
    for chunk in (before, bold, after):
        if chunk is not None:
            holder = BeautifulSoup("<span></span>", "html.parser").span
            holder.string = chunk.get_text() if hasattr(chunk, "get_text") else str(chunk)
            parts.append(holder)
    return parts


def lobby(html: str) -> dict:
    a = html.index('<section class="at-hero">')
    b = html.index('<footer class="at-foot">')
    soup = BeautifulSoup(html[a:b], "html.parser")
    pane = soup.select_one("#atPaperPane")
    kinds = soup.select(".at-kinds .at-kind p")
    feat = soup.select_one(".at-feat")
    create = soup.select_one("#open .at-btn.ghost")
    return {"kick": text(soup.select_one(".at-kick")), "h1": str(soup.select_one(".at-h1")),
            "pot": text(kinds[1]) if len(kinds) > 1 else "", "onTop": text(kinds[2]) if len(kinds) > 2 else "",
            "steps": [text(s).lstrip("0123456789 ") for s in soup.select(".at-steps span:not(.sep)")], "noBot": str(soup.select_one(".at-nobot")),
            "featured": int(feat["data-featured"]) if feat and feat.has_attr("data-featured") else None, "featuredLabel": text(feat.select_one(".at-lbl")) if feat else "",
            "live": [card(c) for c in pane.select("#atLive .at-tcard")], "open": [card(c) for c in pane.select("#atOpen .at-tcard")],
            "liveKinds": [{**card(c), "hours": int(re.search(r"\bh(1|5|24)\b", c.get("data-tags", "")).group(1)), "live": True} for c in soup.select("#atLiveKinds .at-tcard")],
            "liveNote": text(soup.select_one("#atLivePane .at-secnote")), "openNote": text(soup.select_one("#open + .at-secnote")),
            "create": create.get("href") if create else None, "owner": owner_panels()}


def page(html: str) -> str:
    a = html.index('<section class="at-hero">')
    b = html.index('<footer class="at-foot">')
    html = html[:a] + '<div class="v8" id="v8"></div>\n' + html[b:]
    # nothing of ours is cached against his open tab: the version goes on every file of ours
    v = f"?v={VERSION}"
    html = html.replace("</head>", f'<link rel="preload" as="image" href="art/table.webp{v}"><link rel="stylesheet" href="v8.css{v}"></head>', 1)
    scripts = "".join(f'<script src="{name}{v}"></script>' for name in ("data.js", "lobby.js", "art/geometry.js", "v8.js"))
    bar = (HERE / "chatbar.html").read_text(encoding="utf8")   # their chat bar is drawn by a script of theirs: a still copy, render/chatbar.py
    html = re.sub(r'<div[^>]*id="nexus-chat-widget"[^>]*></div>', "", html)
    # their script sets the brand and fills the dock; live, anonymous, the header reads Cymetica with no dock
    html = re.sub(r'(<div class="chat-title"[^>]*>)EventTrader', r"\1Cymetica", html, count=1)
    html = re.sub(r'(<span class="chat-subtitle"[^>]*>)Financial AI Models', r"\1Specialized AI", html, count=1)
    html = html.replace("</head>", "<style>#appDock{display:none}</style></head>", 1)
    return html.replace("</body>", bar + scripts + "</body>", 1)


def main() -> int:
    html = source()
    data = lobby(html)
    results = (V7 / "data.js").read_text(encoding="utf8")
    written = json.dumps(data, ensure_ascii=False)
    if re.search(r"api[_-]?key|[\w.]+@[\w.]+\.\w+|Bearer ", written + results + (HERE / "chatbar.html").read_text(encoding="utf8"), re.I):
        print("refused: the data carries something that looks like a credential or an address")
        return 1
    shutil.copyfile(V7 / "data.js", HERE / "data.js")
    (HERE / "lobby.js").write_text(f"window.CASINO_LOBBY={written};\n", encoding="utf8")
    (HERE / "index.html").write_text(page(html), encoding="utf8")
    print(f"{len(data['live'])} running, {len(data['open'])} open, {len(data['liveKinds'])} live kinds, {len(data['owner']['asks'])} asks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
