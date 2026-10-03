"""The morning report as a page: qa/morning.py's view, drawn.

Plan v2, V11. Published as the one Artifact this project makes (CLAUDE.md's
"Do not publish an Artifact" names this exception), to one fixed address,
updated in place every morning -- so it is written to the Artifact page
contract: no document skeleton of its own, a <title> first, both themes,
phone width first. The look is /lab's (scripts/lab_page.py): the same
tokens, the same sector hues, the same Czech numbers, so the report and the
laboratory read as one thing.

scripts/lab.py `morning` builds the view, calls render() and writes
state/lab/morning.html; the session publishes that file.
"""

from __future__ import annotations

from datetime import date
from html import escape

SECTOR_HUES = {"cards": ("#2a78d6", "#00aaff"), "bots": ("#eda100", "#ffb020"),
               "memecoins": ("#4a3aa7", "#b08cff"), "funds": ("#e87ba4", "#ff6fae")}
DAYS = ("pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle")
NB = " "


def _num(value: float, digits: int) -> str:
    text = f"{abs(value):,.{digits}f}".replace(",", NB).replace(".", ",")
    return ("−" if value < 0 and text.strip("0, ") else "") + text


def _pct(value) -> str:
    if value is None:
        return "—"
    digits = 0 if abs(value) >= 100 else 1 if abs(value) >= 10 else 2
    sign = "+" if value > 0 and _num(value, digits).strip("0,") else ""
    return f"{sign}{_num(value, digits)}{NB}%"


def _usd(value) -> str:
    if value is None:
        return ""
    digits = 0 if abs(value) >= 100 else 2
    return f"{'+' if value > 0 else ''}{_num(value, digits)}{NB}$"


def _tone(value) -> str:
    return "flat" if value is None else "up" if value > 0 else "down" if value < 0 else "flat"


def _confidence(sector: dict) -> str:
    band = sector.get("wilson")
    if not sector.get("n"):
        return "zatím bez výsledku"
    if not band:
        return "málo dat na jistotu"
    if band[0] > 0.5:
        return "spíš vydělává"
    if band[1] < 0.5:
        return "spíš prodělává"
    return "zatím nerozhodnuto"


def _tile(sector: dict) -> str:
    key = sector["key"]
    net = sector.get("net_pct")
    if key == "memecoins":
        sub = (f"{_num(sector.get('n') or 0, 0)} obchodů po 10{NB}$"
               if sector.get("n") else "zatím žádný obchod")
    else:
        usd = sector.get("usdc")
        sub = (f'<b class="{_tone(usd)}">{_usd(usd)}</b> · ' if usd is not None else "") + (
            f"{sector.get('n') or 0} pokusů, {sector.get('running') or 0} běží")
    return (f'<div class="kpi" style="--hue:var(--c-{key})">'
            f'<span class="kpi-name">{escape(sector["name"])}</span>'
            f'<span class="kpi-val {_tone(net)}">{_pct(net)}</span>'
            f'<span class="kpi-sub">{sub}</span>'
            f'<span class="kpi-conf">{_confidence(sector)}</span></div>')


def _list(items: list[str], empty: str) -> str:
    if not items:
        return f'<p class="empty">{escape(empty)}</p>'
    return "<ul class=\"lines\">" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


DEEP_TAGS = {"fixed": ("ok", "Opraveno u nás"), "sent": ("", "Odešlo Cymetice")}


def _bucket(label: str, ids: list, titles: dict) -> str:
    """One kind of news: its label, then each report on a line of its own with
    what it is about (the operator, 2026-10-01: a bare #138 says nothing)."""
    if not ids:
        return f"<li>{escape(label)}: žádný</li>"
    rows = "".join(
        f"<li>#{i}" + (f" — {escape(str(titles[i]))}" if titles.get(i) else "") + "</li>"
        for i in ids)
    return f'<li>{escape(label)}:<ul class="sub">{rows}</ul></li>'


def _cymetica(said: dict) -> str:
    """Sweeps, what we filed, what they fixed, what we verified -- since the
    last report (the operator, 2026-09-26)."""
    titles = said.get("titles") or {}
    rows = [f"<li>Sweep: {said.get('sweeps', 0)}</li>",
            _bucket("Našel jsem a nahlásil", said.get("filed") or [], titles),
            _bucket("Opravili", said.get("fixed") or [], titles),
            _bucket("Ověřil jsem, že oprava drží", said.get("verified") or [], titles)]
    if said.get("failing"):
        rows.append(_bucket("Znovu selhává, poslal jsem jim to",
                            said["failing"], titles))
    return '<ul class="lines">' + "".join(rows) + "</ul>"


def _deep(deep: dict) -> str:
    if not deep.get("lines"):
        return '<p class="empty">Deep pass zatím nemá záznam.</p>'
    rows = []
    for line in deep["lines"]:
        cls, word = DEEP_TAGS[line["kind"]]
        count = f" {line['count']}" if line["kind"] == "fixed" and line["count"] else ""
        items = line.get("items") or []
        if items:
            # Whose they are, then each fix on a line of its own (never one run-on paragraph).
            lead = line["text"].split(": ", 1)[0]
            body = (f'{escape(lead)}<ul class="sub">'
                    + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>")
        else:
            body = escape(line["text"])
        rows.append(f'<li><span class="tag {cls}">{word}{count}</span>'
                    f'<span>{body}</span></li>')
    return '<ul class="deep">' + "".join(rows) + "</ul>"


def _nexus(nexus: dict) -> str:
    if not nexus:
        return ""
    # Said as what happened to the ideas, not as a funnel of nouns: the
    # operator read "0 vyšlo" as "nothing was tested" (2026-09-26). Each
    # figure after the arrow is his rooms' own count, never a difference.
    won, lost = nexus.get("survived", 0) or 0, nexus.get("refuted", 0) or 0
    return (f'<p class="nexus"><b>Nexus</b> {nexus.get("questions", 0)} otázek, '
            f'{nexus.get("answered", 0)} odpovědí, navrhl {nexus.get("picks", 0)} věcí, '
            f'{nexus.get("gate_pass", 0) or 0} prošlo jeho backtestem a šlo na papír → '
            f'<b class="{"up" if won else ""}">{won} vydělalo</b> · {lost} prodělalo'
            f' · {nexus.get("inconclusive", 0) or 0} bez závěru'
            f' · {nexus.get("running", 0) or 0} ještě běží</p>')


def _heading_date(iso: str) -> str:
    day = date.fromisoformat(iso)
    return f"{DAYS[day.weekday()]} {day.day}.{NB}{day.month}."


def render(view: dict) -> str:
    hues_light = "".join(f"--c-{k}:{v[0]};" for k, v in SECTOR_HUES.items())
    hues_dark = "".join(f"--c-{k}:{v[1]};" for k, v in SECTOR_HUES.items())
    deep = view.get("deep_pass") or {}
    telegram = view.get("telegram")
    made = str(view.get("made_at") or "")[11:16]
    return TEMPLATE.format(
        hues_light=hues_light, hues_dark=hues_dark,
        when=_heading_date(view["date"]), made=escape(made),
        deep_title=escape((deep.get("title") or "").replace("Deep pass — ", "")),
        deep=_deep(deep),
        cymetica=_cymetica(view.get("cymetica") or {}),
        tiles="".join(_tile(s) for s in view.get("sectors") or []),
        nexus=_nexus(view.get("nexus") or {}),
        overnight=_list(view.get("overnight") or [],
                        "Přes noc se nic nepohnulo." if view.get("compared") else
                        "První přehled — od zítřka tu bude, co se změnilo přes noc."),
        today=_list(view.get("today") or [],
                    "Pás jede dál: nové nápady od Nexuse, backtest, papír."),
        telegram=(TELEGRAM.format(text=escape(telegram)) if telegram else ""),
        acted=_list(view.get("acted") or [],
                    "Zatím žádná. Napiš mi k přehledu, co chceš jinak — "
                    "zítra tu uvidíš, co jsem podle toho změnil."))


TELEGRAM = """
  <section class="block">
    <h2>Na Telegram pro Cymetiku</h2>
    <pre class="tg" id="tg">{text}</pre>
    <button class="copy" type="button" id="copy">Zkopírovat</button>
  </section>"""

TEMPLATE = """<title>Ranní přehled laborky</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#f3f5f4; --surface:#ffffff; --surface-2:#eef1f0; --line:#d9dfdd;
  --text:#0f1719; --text-dim:#56676a; --text-faint:#7d8d8e;
  --ok:#17803d; --ok-bg:#17803d17; --bad:#b3261e; --bad-bg:#b3261e14;
  --warn:#8a5a00; --warn-bg:#eda10024; --accent:#0d6b66;
  {hues_light}
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#0a0e17; --surface:#111827; --surface-2:#182234; --line:rgba(0,150,255,.16);
    --text:#ffffff; --text-dim:#9fb3c8; --text-faint:#7b8794;
    --ok:#00ff88; --ok-bg:rgba(0,255,136,.12); --bad:#ff4444; --bad-bg:rgba(255,68,68,.14);
    --warn:#ffb020; --warn-bg:rgba(255,176,32,.13); --accent:#00cfff;
    {hues_dark}
    color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#0a0e17; --surface:#111827; --surface-2:#182234; --line:rgba(0,150,255,.16);
  --text:#ffffff; --text-dim:#9fb3c8; --text-faint:#7b8794;
  --ok:#00ff88; --ok-bg:rgba(0,255,136,.12); --bad:#ff4444; --bad-bg:rgba(255,68,68,.14);
  --warn:#ffb020; --warn-bg:rgba(255,176,32,.13); --accent:#00cfff;
  {hues_dark}
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--text); font: 16px/1.5 var(--sans);
  -webkit-font-smoothing: antialiased; }}
.mr {{ max-width: 760px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 44px;
  display: flex; flex-direction: column; gap: 26px; }}
.up {{ color: var(--ok); }} .down {{ color: var(--bad); }} .flat {{ color: var(--text-faint); }}
header p {{ margin: 0; }}
.kicker {{ font: 500 13px var(--mono); color: var(--accent); letter-spacing: .02em; }}
h1 {{ margin: 4px 0 2px; font-size: 30px; line-height: 1.15; letter-spacing: -.02em;
  text-wrap: balance; }}
.meta {{ font-size: 13.5px; color: var(--text-dim); }}
h2 {{ margin: 0 0 10px; font-size: 13px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--text-dim); display: flex; align-items: baseline;
  gap: 8px; }}
h2 span {{ font: 400 12.5px var(--mono); letter-spacing: 0; text-transform: none;
  color: var(--text-faint); }}
.deep {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }}
.deep li {{ display: flex; gap: 10px; align-items: baseline; }}
.deep .sub {{ margin: 6px 0 0; padding-left: 18px; display: flex; flex-direction: column; gap: 5px;
  font-size: 14px; color: var(--text-dim); }}
.deep .sub li {{ display: list-item; }}
.tag {{ flex: none; font-size: 12px; font-weight: 600; padding: 2px 9px; border-radius: 999px;
  background: var(--surface-2); color: var(--text-dim); white-space: nowrap; }}
.tag.ok {{ background: var(--ok-bg); color: var(--ok); }}
.tag.warn {{ background: var(--warn-bg); color: var(--warn); }}
.kpis {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
.kpi {{ position: relative; background: var(--surface); border: 1px solid var(--line);
  border-radius: 12px; padding: 12px 14px 12px 18px; display: flex; flex-direction: column;
  gap: 1px; min-width: 0; }}
.kpi::before {{ content: ""; position: absolute; left: 0; top: 12px; bottom: 12px; width: 4px;
  border-radius: 0 4px 4px 0; background: var(--hue); }}
.kpi-name {{ font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: var(--text-dim); }}
.kpi-val {{ font-size: 30px; font-weight: 700; line-height: 1.2; letter-spacing: -.015em; }}
.kpi-sub {{ font-size: 13.5px; color: var(--text-dim); }}
.kpi-conf {{ font-size: 12.5px; color: var(--text-faint); }}
.nexus {{ margin: 12px 0 0; font-size: 14px; color: var(--text-dim); }}
.nexus b {{ color: var(--text); }} .nexus b.up {{ color: var(--ok); }}
.lines {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }}
.lines li::marker {{ color: var(--accent); }}
.lines .sub {{ margin: 4px 0 2px; padding-left: 18px; display: flex; flex-direction: column;
  gap: 3px; font-size: 14px; color: var(--text-dim); }}
.empty {{ margin: 0; color: var(--text-dim); }}
.block {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  padding: 14px 16px; }}
.tg {{ margin: 0 0 10px; padding: 12px 14px; border-radius: 8px; background: var(--surface-2);
  font: 13.5px/1.5 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; }}
.copy {{ font: 600 14px var(--sans); color: var(--surface); background: var(--accent);
  border: 0; border-radius: 999px; padding: 7px 16px; cursor: pointer; }}
.copy:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
footer {{ font-size: 13px; color: var(--text-faint); }}
footer code {{ font-family: var(--mono); }}
@media (min-width: 640px) {{
  .kpis {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
  h1 {{ font-size: 34px; }}
}}
</style>

<main class="mr">
  <header>
    <p class="kicker">Ranní přehled · {when}</p>
    <h1>Laborka přes noc</h1>
    <p class="meta">sestaveno v {made} · papírové obchody, čísla po poplatcích</p>
  </header>

  <section>
    <h2>Cymetica přes noc</h2>
    {cymetica}
  </section>

  <section>
    <h2>Deep pass <span>{deep_title}</span></h2>
    {deep}
  </section>

  <section>
    <h2>Laborka <span>celkem od začátku, ne za noc</span></h2>
    <div class="kpis">{tiles}</div>
    {nexus}
  </section>

  <section>
    <h2>Přes noc</h2>
    {overnight}
  </section>

  <section>
    <h2>Dnes udělám</h2>
    {today}
  </section>
{telegram}
  <section>
    <h2>Podle tvé zpětné vazby</h2>
    {acted}
  </section>

  <footer>Detail každého pokusu je na <code>http://127.0.0.1:8787/lab</code>
    (jen na tvém počítači, když běží konzole).</footer>
</main>

<script>
(function () {{
  const button = document.getElementById("copy"), text = document.getElementById("tg");
  if (!button || !text) return;
  button.addEventListener("click", () => {{
    const done = () => {{ button.textContent = "Zkopírováno ✓"; }};
    const select = () => {{
      const range = document.createRange();
      range.selectNodeContents(text);
      const sel = window.getSelection();
      sel.removeAllRanges(); sel.addRange(range);
      button.textContent = "Označeno — Ctrl+C";
    }};
    try {{
      navigator.clipboard.writeText(text.textContent).then(done, select);
    }} catch (_) {{ select(); }}
  }});
}})();
</script>
"""
