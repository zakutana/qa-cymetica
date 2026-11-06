"""Build the one-page Traffic mock: /traffic, /traffic/mine and /app-usage as one page with Basic and Advanced views.

    python outbox/traffic-one/build.py --snap     # re-read every API the three pages use (GET only), then build
    python outbox/traffic-one/build.py            # build from snapshot/
    python scripts/serve_mock.py outbox/traffic-one 8844 --quiet

Kept theirs: the /traffic page chrome (header, sidebar, footer) fetched live with no script of theirs, their panel
styles (.tl-* from /traffic, .au-* from /app-usage, .tm-* from /traffic/mine, copied into theirs-mine.css because that
page needs a sign-in), Chart.js 4.4.7 and the same chart settings. Ours: main.html, one.css, one.js.
The API key goes in a header and never into a written file; snapshot/ holds what the APIs answered.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HOST = "https://cymetica.com"
SNAP = HERE / "snapshot"
VERSION = "1"


def fetch(path: str, key: str | None = None) -> tuple[bytes, float, int]:
    headers = {"User-Agent": "qa-cymetica", "Cache-Control": "no-cache"}
    if key:
        headers["X-API-Key"] = key
    started = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(HOST + path, headers=headers), timeout=180) as r:
            return r.read(), time.time() - started, r.status
    except urllib.error.HTTPError as e:
        return e.read(), time.time() - started, e.code


def api_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            if k in ("QA_TRUSTED_KEY", "QA_RECOGNIZED_KEY") and v:
                return v.strip().strip('"')
    raise SystemExit("no key in .env")


def snap() -> None:
    key = api_key()
    SNAP.mkdir(exist_ok=True)
    timings = {}
    calls = [("/api/v1/app-usage", "app-usage", None), ("/api/v1/app-usage/history", "app-usage-history", None),
             ("/api/v1/company/products", "products", key)]
    for d in (7, 14, 30, 90):
        calls += [(f"/api/v1/traffic/public?days={d}", f"public-{d}", None),
                  (f"/api/v1/traffic/activity?days={d}", f"activity-{d}", None),
                  (f"/api/v1/traffic/mine?days={d}", f"mine-{d}", key)]
    for path, name, k in calls:
        body, took, status = fetch(path, k)
        timings[path] = {"seconds": round(took, 2), "status": status}
        print(f"{path:45s} {status} {took:5.2f}s")
        data = json.loads(body) if body[:1] in (b"{", b"[") else {"error": body[:200].decode("utf8", "replace")}
        if name == "products":   # 237 KB of build history; the mock needs the product rows and the season
            data = {"days": data.get("days"), "definitions": data.get("definitions"), "season": data.get("season"),
                    "products": [{k2: p.get(k2) for k2 in ("name", "path", "unique_visitors", "uses", "daily")} for p in data["products"]]}
        (SNAP / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SNAP / "timings.json").write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "calls": timings}, indent=1), encoding="utf-8")


def their_page() -> str:
    """/traffic as anyone sees it, with no script of theirs and every link absolute."""
    html = fetch("/traffic")[0].decode("utf8")
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", html, flags=re.S | re.I)
    html = re.sub(r'(<link\b[^>]*?)\s+media="print"([^>]*>)', r"\1\2", html)
    html = re.sub(r'(<link\b[^>]*?)\s+onload="[^"]*"([^>]*>)', r"\1\2", html)
    html = re.sub(r'(href|src|action)="/(?!/)', rf'\1="{HOST}/', html)
    return html.replace("url(/static", f"url({HOST}/static")


def style_block(html: str, marker: str) -> str:
    for block in re.findall(r"<style\b[^>]*>(.*?)</style>", html, flags=re.S):
        if marker in block:
            return block
    raise SystemExit(f"their style with {marker} is gone")


def build() -> None:
    page = their_page()
    usage = fetch("/app-usage")[0].decode("utf8")
    (HERE / "theirs.css").write_text("/* copied by build.py from cymetica.com /traffic and /app-usage */\n"
                                     + style_block(page, ".tl-page {") + "\n" + style_block(usage, ".au-container {"), encoding="utf-8")
    data = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(SNAP.glob("*.json"))}
    (HERE / "data.js").write_text("window.SNAP = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    main = (HERE / "main.html").read_text(encoding="utf-8")
    page, n = re.subn(r'<main class="content-main" id="main-content">.*?</main>', lambda _: main, page, count=1, flags=re.S)
    if not n:
        raise SystemExit("their <main> is gone")
    page = re.sub(r"<title>.*?</title>", "<title>Traffic | EventTrader</title>", page, count=1, flags=re.S)
    css = "".join(f'<link rel="stylesheet" href="{f}?v={VERSION}">' for f in ("theirs.css", "theirs-mine.css", "one.css"))
    page = page.replace("</head>", css + "</head>", 1)
    js = ('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>'
          f'<script src="data.js?v={VERSION}"></script><script src="one.js?v={VERSION}"></script>')
    page = page.replace("</body>", js + "</body>", 1)
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print("index.html", len(page) // 1024, "KB; data.js", (HERE / "data.js").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    if "--snap" in sys.argv:
        snap()
    build()
