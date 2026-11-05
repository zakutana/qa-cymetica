"""Build the Agent Casino lobby mock v9: their live page as the owner sees it, with only the patches the operator named.

    python outbox/casino-v9/build.py
    python scripts/serve_mock.py outbox/casino-v9 8843 --quiet

Kept theirs: header, headline, the three boxes, Your agents panel and list. Ours: running tables on the rendered table,
Open as a picker in their Open place, Finished folded with a small table beside the placings, a quieter finish.
Reads only (GET): the page anonymously, the results with our key, which never reaches a written file. owner.html is the
owner's part of their page, copied by hand from the signed-in page.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
OUTBOX = HERE.parent
HOST = "https://cymetica.com"
VERSION = "4"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V7 = load("casino_v7_build", OUTBOX / "casino-v7" / "build.py")
V8 = load("casino_v8_build", OUTBOX / "casino-v8" / "build.py")


def anonymous_page() -> str:
    """Their lobby now, no script of theirs: v7's fetch, without v7's own files."""
    html = V7.page().replace('<link rel="stylesheet" href="v7.css">', "")
    return re.sub(r'<script src="(data|owner|v7)\.js"></script>', "", html)


def owner_piece(owner: BeautifulSoup, name: str):
    """One piece of the owner's page, with absolute links and 'Flash' out, the operator's word."""
    raw = owner.select_one(f"template#{name}").decode_contents()
    raw = re.sub(r'<span class="at-kind flash"[^>]*>FLASH</span>', "", raw)
    raw = raw.replace("Flash ", "")
    raw = re.sub(r'href="/(?!/)', f'href="{HOST}/', raw)
    return BeautifulSoup(raw, "html.parser")


def fold_asks(asks: BeautifulSoup) -> None:
    """One line per request: their red sentence; everything else they wrote behind More."""
    for small in asks.select(".at-ask .nm small"):
        red = small.select_one("b.neg")
        line = red.get_text() if red else small.get_text().split(";")[0].strip()
        del small["style"]
        small["hidden"] = ""
        holder = BeautifulSoup(f'<span class="v9-line{" neg" if red else ""}"></span><button type="button" class="v9-more" data-more aria-expanded="false">More</button>', "html.parser")
        holder.select_one(".v9-line").string = line
        small.insert_before(holder)


def agents_by_table(agents: BeautifulSoup) -> dict:
    out = {}
    for row in agents.select(".at-ar.live"):
        need = row.select_one(".needvol")
        out[int(row["href"].rsplit("/", 1)[1])] = {
            "bot": V8.text(row.select_one(".nm b")), "rank": V8.text(row.select_one(".arank")).replace(" ", ""),
            "roi": V8.text(row.select_one(".roi")), "need": V8.text(need)}
    return out


def assemble(html: str) -> tuple[str, dict]:
    soup = BeautifulSoup(html, "html.parser")
    owner = BeautifulSoup((HERE / "owner.html").read_text(encoding="utf8"), "html.parser")
    paper, live = soup.select_one("#atPaperPane"), soup.select_one("#atLivePane")

    agents = owner_piece(owner, "agents")
    data = {"live": [V8.card(c) for c in paper.select("#atLive .at-tcard")],
            "open": [V8.card(c) for c in paper.select("#atOpen .at-tcard")],
            "liveKinds": [{**V8.card(c), "hours": int(re.search(r"\bh(1|5|24)\b", c.get("data-tags", "")).group(1))} for c in live.select(".at-tcard")],
            "liveNote": V8.text(live.select_one(".at-secnote")), "create": HOST + "/agent-casino?create=1",
            "agents": agents_by_table(agents)}
    create = paper.select_one("#open .at-btn.ghost")
    if create and create.get("href"):
        data["create"] = create["href"]

    # the owner's parts go where their page puts them
    hero = soup.select_one("section.at-hero")
    asks = owner_piece(owner, "asks")
    fold_asks(asks)
    for sel in ("#atAsks", "#agents", ".at-agents", ".at-me"):
        for old in soup.select(sel):
            old.decompose()
    hero.insert_before(asks)
    kids = hero.find_all(recursive=False)
    for extra in kids[1:]:
        extra.decompose()
    hero.append(owner_piece(owner, "me"))
    pill = soup.select_one(".at-bar .at-pill")
    if pill:
        pill.replace_with(owner_piece(owner, "pill"))
    head = owner_piece(owner, "agentshead")
    paper.insert_before(head)
    paper.insert_before(agents)

    # Flash out of the hero, the operator's word; the green button goes to the picker
    for p in hero.select(".at-kind p"):
        if p.get_text().strip().startswith("Flash tables only"):
            p.decompose()
    pick = hero.select_one("#atPick")
    if pick:
        pick["href"] = "#open"

    live.decompose()
    holder = soup.new_tag("div", id="v9")
    holder["class"] = "v9"
    paper.replace_with(holder)

    out = str(soup)
    # the smile is what reads as a toy; their other faces stay
    out = out.replace('<path d="M16.2 26.4q3.8 2.4 7.6 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
                      '<path d="M16.8 27h6.4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>')
    v = f"?v={VERSION}"
    out = out.replace("</head>", f'<link rel="preload" as="image" href="art/table.webp{v}"><link rel="stylesheet" href="v9.css{v}"></head>', 1)
    scripts = "".join(f'<script src="{name}{v}"></script>' for name in ("data.js", "lobby.js", "art/geometry.js", "v9.js"))
    bar = (OUTBOX / "casino-v8" / "chatbar.html").read_text(encoding="utf8")
    out = re.sub(r'<div[^>]*id="nexus-chat-widget"[^>]*></div>', "", out)
    out = re.sub(r'(<div class="chat-title"[^>]*>)EventTrader', r"\1Cymetica", out, count=1)
    out = re.sub(r'(<span class="chat-subtitle"[^>]*>)Financial AI Models', r"\1Specialized AI", out, count=1)
    out = out.replace("</head>", "<style>#appDock{display:none}</style></head>", 1)
    return out.replace("</body>", bar + scripts + "</body>", 1), data


def main() -> int:
    results = V7.results()
    page, data = assemble(anonymous_page())
    written = json.dumps(data, ensure_ascii=False)
    text = json.dumps(results, ensure_ascii=False)
    if re.search(r"api[_-]?key|[\w.]+@[\w.]+\.\w+|Bearer ", written + text + (HERE / "owner.html").read_text(encoding="utf8"), re.I):
        print("refused: the data carries something that looks like a credential or an address")
        return 1
    art = HERE / "art"
    if not art.exists():
        shutil.copytree(OUTBOX / "casino-v8" / "art", art)
    (HERE / "data.js").write_text(f"window.CASINO={text};\n", encoding="utf8")
    (HERE / "lobby.js").write_text(f"window.CASINO_LOBBY={written};\n", encoding="utf8")
    (HERE / "index.html").write_text(page, encoding="utf8")
    print(f"{len(data['live'])} running, {len(data['open'])} open, {len(data['liveKinds'])} live kinds, {len(results['tables'])} finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
