"""Their quant-lab.js and quant-lab.css (their/, freeze.py) with our changes on top. Every replacement must land once.

python outbox/quant-lab-v3/build.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
js = (HERE / "their" / "quant-lab.js").read_text(encoding="utf-8")
css = (HERE / "their" / "quant-lab.css").read_text(encoding="utf-8")


def sub(old: str, new: str) -> None:
    global js
    if js.count(old) != 1:
        raise SystemExit(f"{js.count(old)} matches: {old[:70]}")
    js = js.replace(old, new)


# ours, before their start-up
sub("  // ---------------------------------------------------------------- start\n",
    (HERE / "q3.js").read_text(encoding="utf-8") + "  // ---------------------------------------------------------------- start\n  q3Order();\n")
# winners and thrown-out rows in place of 94 long rows; the old rows stay for runs with no windows
sub("    var lo = Math.min(-15, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 2), hi =",
    "    if (q3Top()) return;\n    var lo = Math.min(-15, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 2), hi =")
# runs: one line each, the newest five
sub("    var cur = M.picked ? M.picked.id : (LAST_GOOD ? LAST_GOOD.id : null);\n    el.innerHTML = runs.map(",
    "    if (q3Runs()) return;\n    var cur = M.picked ? M.picked.id : (LAST_GOOD ? LAST_GOOD.id : null);\n    el.innerHTML = runs.map(")
# BLIND: the windows, not the old 60% cut, when the run has them
sub("  function drawBlind(p) {\n", "  function drawBlind(p) {\n    if (q3Windows()) return q3DrawBlind(p);\n")
# THE BAR: winners and nearest misses only, timed to fit however many there are
sub("    var n = M.candidates.length, top = 104, bot = H - 50, gap = 26, w = (W - 140 - gap * Math.max(0, n - 1)) / Math.max(1, n);\n"
    "    var hi = Math.max(36, Math.max.apply(null, M.candidates.map(function (c) { return Math.max(c.search || 0, c.bar); })) + 4);\n"
    "    var lo = Math.min(-16, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 3);\n",
    "    var B3 = q3Bar(), CL = B3.list, n = CL.length, top = 104, bot = H - 50, gap = 26, w = (W - 140 - gap * Math.max(0, n - 1)) / Math.max(1, n);\n"
    "    var hi = Math.max(12, Math.max.apply(null, CL.map(function (c) { return Math.max(c.search || 0, c.bar); })) + 4);\n"
    "    var lo = Math.min(-6, Math.min.apply(null, CL.map(function (c) { return c.held; })) - 3);\n"
    "    if (B3.more) txt('+' + B3.more + ' MORE', W - 30, 46, '700 12px ' + MONO, C.dim, 'right');\n")
sub("    M.candidates.forEach(function (c, i) {\n      var x = 90 + i * (w + gap), st = 0.08 + i * 0.16, run = ease(seg(p, st, st + 0.12)), doneP = p >= st + 0.12;\n"
    "      txt(setupText(c.setup).split(' + ')[0], x, top - 40, '700 13px ' + MONO, C.text, 'left');\n",
    "    CL.forEach(function (c, i) {\n      var step = n > 6 ? 0.82 / n : 0.16, x = 90 + i * (w + gap), st = 0.04 + i * step, run = ease(seg(p, st, st + Math.max(0.05, step))), doneP = p >= st + Math.max(0.05, step);\n"
    "      ctx.font = '700 12px ' + MONO; var nm = setupText(c.setup).split(' + ')[0]; while (ctx.measureText(nm).width > w - 58 && nm.length > 3) nm = nm.slice(0, -1);\n"
    "      txt(nm, x, top - 40, '700 12px ' + MONO, C.text, 'left');\n")
sub("txt(pct(c.search), x + w * 0.24, Y(c.search || 0) - 12, '700 12px ' + MONO, C.cyan, 'center');",
    "if (w > 80) txt(pct(c.search), x + w * 0.24, Y(c.search || 0) - 12, '700 11px ' + MONO, C.cyan, 'center');")
sub("txt('BAR ' + c.bar.toFixed(2) + '%', x, lz + 14, '700 12px ' + MONO, C.green, 'left');",
    "txt(c.bar.toFixed(1) + '%', x, lz - 12, '700 11px ' + MONO, C.green, 'left');")
sub("txt((c.won ? '✓ ' : '✗ ') + pct(c.held), x + w * 0.68, c.won ? yv - 20 : Math.max(yv, y0) + 22, '400 22px ' + BLACK, c.won ? C.green : C.red, 'center', 16);",
    "txt((c.won ? '✓ ' : '✗ ') + pct(c.held), x + w * 0.5, c.won ? yv - 20 : Math.max(yv, y0) + 22, '400 ' + (w < 110 ? 13 : 19) + 'px ' + BLACK, c.won ? C.green : C.red, 'center', 10);")
# FOUND: one animation, then all the agents it found on one screen
sub("    slam('PROFITABLE AGENT', px0, 56, 50, 0.38, p);\n",
    "    var nb3 = M.mode === 'real' ? M.botList.length : 1;\n"
    "    slam(nb3 > 1 ? nb3 + ' PROFITABLE AGENTS' : 'PROFITABLE AGENT', px0, 40, 44, 0.38, p);\n")
sub("    slam('FOUND', px0, 112, 50, 0.44, p, C.green);\n", "    slam('FOUND', px0, 92, 44, 0.44, p, C.green);\n")
sub("    coin(c.market, px0 + 16, 170, 16);\n",
    "    if (M.mode === 'real') { ctx.restore(); q3Cards(px0, pw, p); return; }\n    coin(c.market, px0 + 16, 170, 16);\n")
sub("    renderScore(); renderTop(); renderBots(); renderCaps();\n", "    renderScore(); renderTop(); renderBots(); renderCaps(); q3Note();\n")
# the company's own state, for "paused"
sub("    S.cid = o.id; connect(); return loadAll().then(function () {\n",
    "    S.cid = o.id; api('GET', '/mine').then(function (m) { S.mine = m; q3Note(); }, function () {}); connect(); return loadAll().then(function () {\n")

(HERE / "quant-lab.js").write_text(js, encoding="utf-8")
(HERE / "quant-lab.css").write_text(css + (HERE / "q3.css").read_text(encoding="utf-8"), encoding="utf-8")
print("built", len(js), "js,", len(css), "css")
