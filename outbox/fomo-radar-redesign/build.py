"""Build the FOMO Radar redesign mock: their live /fomo-radar (header, Connect your AI, Back, chat bar) with our page
in place of theirs.

    python outbox/fomo-radar-redesign/build.py
    python outbox/fomo-radar-redesign/serve.py        ->  http://127.0.0.1:8846/

Reads only (GET, anonymous). Their scripts are dropped, so nothing on the copy can act; fomo.js reads the same public
API through serve.py, so every figure is their live one.
"""
from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = "https://cymetica.com"


def page() -> str:
    request = urllib.request.Request(f"{HOST}/fomo-radar", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(request, timeout=90).read().decode("utf8")
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", html, flags=re.S | re.I)
    html = re.sub(r'(<link\b[^>]*?)\s+media="print"([^>]*>)', r"\1\2", html)
    html = re.sub(r'(<link\b[^>]*?)\s+onload="[^"]*"([^>]*>)', r"\1\2", html)
    html = re.sub(r'(href|src|action)="/(?!/)', rf'\1="{HOST}/', html)
    html = html.replace("url(/static", f"url({HOST}/static")
    return html


def main() -> None:
    html = page()
    start = html.index('<div class="clone-page">')
    end = html.index("</main>", start)
    body = (HERE / "body.html").read_text(encoding="utf8")
    html = html[:start] + body + "\n    " + html[end:]
    v = str(int(time.time()))
    html = html.replace("</head>", f'<link rel="stylesheet" href="fomo.css?v={v}"></head>', 1)
    html = html.replace("</body>", f'<script src="fomo.js?v={v}"></script></body>', 1)
    (HERE / "index.html").write_text(html, encoding="utf8")
    print(f"index.html {len(html)} bytes")


if __name__ == "__main__":
    main()
