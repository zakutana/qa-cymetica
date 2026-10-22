"""Build index.html (this folder): cymetica.com/build-it-better as served on 2026-10-22, with the new design spliced in.

The operator, 2026-10-22: "vytvor novy top design pro stranku https://cymetica.com/build-it-better i lokalne abych na ni pak
se podival. nemen funkcionalitu jen design zmenime ... Hlavne musi byt jak prijdem na stranku nejak husto zobrazeno srovnani
Vibe codingu vs pouziti cymetica build it better ... hlavni slogan je ze proste AI je jen tool stejne jako brain surgeon kit a
ze kdyz mas kit nedela to s tebe automaticky brain surgeona. A cymetica ten brain surgeon jakoby je pro staveni veci."

So only these change in their page: the Build it Better <style> block becomes bib.css, and the markup between
<div class="bb-page"> and the page's own <script> becomes bib.html. The script itself, the header, the footer and every
other script stay as they were served (render.py checks the script byte for byte). One addition, asked for the same day
("katalog ze klikam doprava a doleva uz buildnutych apek ... serazenych podle nejvic views a navstevniku"): catalog.js,
its own <script> after theirs, reading only the public /apps/leaderboard.

One script is added for the mockup only, never for Cymetica: the page opens its live-board socket on its own host, which
serve.py cannot answer, and wss://cymetica.com refuses a socket from 127.0.0.1 (closed 1006: it checks the origin, as it
should). So the shim hands the page a socket that only opens: the dot reads "Live" as it does on cymetica.com, the board
is the live read made when the page loads, and no update arrives after that.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
live = (HERE / "live-2026-10-22.html").read_text(encoding="utf-8")
css = (HERE / "bib.css").read_text(encoding="utf-8")
frag = (HERE / "bib.html").read_text(encoding="utf-8")

# 1. the page's own stylesheet: the one <style> that defines .bb-page
styles = list(re.finditer(r"(<style[^>]*>)(.*?)(</style>)", live, re.S))
own = [m for m in styles if ".bb-page {" in m.group(2)]
assert len(own) == 1, f"expected one Build it Better <style>, found {len(own)}"
m = own[0]
out = live[:m.start(2)] + css + live[m.end(2):]

# 2. the markup, up to (not including) the page script
start = out.find('<div class="bb-page">')
script = re.search(r"<script[^>]*>\s*\(function \(\) \{\s*'use strict';\s*var API = '/api/v1/build-it-better';", out[start:])
assert start > 0 and script, "the Build it Better block or its script moved"
out = out[:start] + frag + out[start + script.start():]

# 3. the catalog (asked for the same day): its own script, after the page script and apart from it
end = out.find("</script>", start + len(frag)) + len("</script>")
nonce = re.search(r'<script nonce="([^"]+)"', out[start + len(frag):end])
out = out[:end] + f'\n    <script{" nonce=" + chr(34) + nonce.group(1) + chr(34) if nonce else ""}>\n' + \
    (HERE / "catalog.js").read_text(encoding="utf-8") + "    </script>" + out[end:]

# 4. mockup only: the live-board socket is a stub that opens and stays quiet
SHIM = """<script id="mockup-only">/* mockup preview only, not part of the design: cymetica.com refuses this origin's socket */
(function () { var WS = window.WebSocket; if (!WS) return;
  window.WebSocket = function (url, p) {
    if (!/\\/ws\\/build-it-better$/.test(String(url))) return p ? new WS(url, p) : new WS(url);
    var s = { readyState: 0, send: function () {}, close: function () { s.readyState = 3; } };
    setTimeout(function () { s.readyState = 1; if (s.onopen) s.onopen(); }, 300);
    return s;
  };
  window.WebSocket.prototype = WS.prototype; ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'].forEach(function (k) { window.WebSocket[k] = WS[k]; });
})();</script>
"""
head = out.find("<head>") + len("<head>")
out = out[:head] + "\n" + SHIM + out[head:]

(HERE / "index.html").write_text(out, encoding="utf-8")
print(f"index.html {len(out):,} bytes")
