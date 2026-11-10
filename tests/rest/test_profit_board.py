"""The Profit Board and pitches of ET-33678 (/pitch-cards), against the page's own promise and the numbers they come from.

The contract is the page's note and the ticket: "every live fund and every public event card since it was minted (72h
cards at their close), shown only while it is up"; nothing at a loss; Days old / peak day. `GET /api/v1/pitch-cards`
is what the page draws; `GET /api/v1/event-cards/{id}` and /fund-performance's ranked table are where those numbers
come from.

**What was seen when this was written** (2026-11-03 04:28 UTC, 6,854 rows). Quantum Frontier Index reads +7.25 % with
its card at -25.55 %, Project Omega +5.09 % at -28.41 %; DeFi Undercurrent Short +60.56 % beside the fund of that name
at -60.55 %; FTA Fund -- Cryptos, live and +7.17 %, is not there; 2,774 of 6,482 72h cards have their peak on the day
they are read, weeks after they closed; one reading of 30.97 between 8.58 and 8.42 draws Molecular's pitch chart flat.

NOT asserted: the design, or which kinds of thing belong on the board (ET-33678 leaves that to them). SAFE: GETs only.
"""

from __future__ import annotations

import re
from html import unescape

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

DATA = "/api/v1/pitch-cards"
RANKED = "/fund-performance"
OFF_BY = 10.0       # percentage points between a row and its card: the board refreshes every 5 minutes, a card moves less
LAST_72H_DAY = 4    # a 72-hour card closes on its third day; one day of slack for a day boundary
SPIKE = 100.0       # percentage points a lone reading stands off both neighbours, while they agree within NEIGHBOURS
NEIGHBOURS = 10.0
LINE_OFF_BY = 2.0   # percentage points between a pitch's line and its big number: the line is thinned, not re-read


def _verdict(breaches: list, checked, passed: str, sources: dict) -> None:
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason="; ".join(str(b.get("what", b)) for b in breaches[:8]) if breaches else passed,
        left={"breaches": len(breaches), "checked": checked},
        right={"breaches": 0},
        population={"breaches": breaches[:20]},
        sources=sources))


def _json(client, url: str) -> dict:
    response = get_patiently(client, url)
    if response.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {response.status_code}")
    return response.json() or {}


def _data(client) -> dict:
    data = _json(client, DATA)
    if not (data.get("board") or {}).get("rows"):
        raise Inconclusive(f"{DATA} has no board rows")
    return data


def _ranked(client) -> list[dict]:
    """The rows of /fund-performance's "All funds, ranked" table."""
    response = get_patiently(client, RANKED, headers={"Accept": "text/html"})
    if response.status_code != 200 or 'id="fp-rank"' not in response.text:
        raise Inconclusive(f"{RANKED} answered HTTP {response.status_code} without its ranked table")
    html = response.text[response.text.index('id="fp-rank"'):]
    html = html[:html.index("</table>")]
    funds = []
    for tr in html.split("<tr")[1:]:
        tr = tr.split("</tr>")[0]
        cell = re.search(r'<td class="fund">(.*?)</td>', tr, re.S)
        # the Return cell, wherever it sits: since 2026-11-10 an Outside holders column follows it, and a fund
        # with no figure yet reads a dash and is left out
        ret = re.search(r'<span class="(?:pos|neg)">([+\-−]?[\d.]+)%</span>', tr, re.S)
        if not cell or not ret:
            continue
        href = re.search(r'href="([^"]+)"', cell.group(1))
        status = re.search(r'<span class="st (\w+)">', tr)
        side = re.search(r'<span class="dir">(\w+)</span>', tr)
        funds.append({"name": unescape(re.sub(r"<[^>]+>", "", cell.group(1))).strip(), "href": href.group(1) if href else None,
                      "status": status.group(1) if status else None, "side": side.group(1) if side else "long",
                      "ret": float(ret.group(1).replace("−", "-"))})
    if not funds:
        raise Inconclusive(f"{RANKED}: no rows read from the ranked table")
    return funds


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_profit_board_reads_each_event_card_as_it_is_now(rest_anon):
    """An event card on the board is up on its own record, by about what the row says."""
    rows = [r for r in _data(rest_anon)["board"]["rows"] if r.get("k") == "card"]
    breaches = []
    for row in rows:
        card = _json(rest_anon, "/api/v1/event-cards/" + row["u"].rsplit("/", 1)[-1])
        card = card.get("card", card)
        index, base = card.get("current_index"), card.get("index_base")
        if not (isinstance(index, (int, float)) and isinstance(base, (int, float)) and base > 0):
            continue
        now = 100 * (index / base - 1)
        if now <= 0 or abs(now - row["r"]) > OFF_BY:
            breaches.append({"what": f"{row['n'][:50]}: the board reads +{row['r']} %, its card {now:+.2f} %", "url": row["u"]})
    _verdict(breaches, len(rows), "every event card on the board reads what its card reads",
             {"board": DATA, "card": "/api/v1/event-cards/{id}"})


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_losing_short_fund_is_not_on_the_profit_board_as_up(rest_anon):
    """A row named as a short fund that /fund-performance ranks at a loss. Its rise is the basket's; the short lost it."""
    rows = _data(rest_anon)["board"]["rows"]
    losers = {f["name"]: f for f in _ranked(rest_anon) if f["side"] == "short" and f["ret"] <= 0}
    breaches = [{"what": f"{r['n']}: on the board at +{r['r']} %, on /fund-performance at {losers[r['n']]['ret']} % (short)", "url": r["u"]}
                for r in rows if r.get("n") in losers]
    _verdict(breaches, len(losers), "no short fund at a loss is on the board as up", {"board": DATA, "funds": RANKED})


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_every_live_fund_that_is_up_is_on_the_profit_board(rest_anon):
    """Every row of /fund-performance's ranked table that is live, up and has a page of its own."""
    urls = {r.get("u") for r in _data(rest_anon)["board"]["rows"] if r.get("k") == "fund"}
    up = [f for f in _ranked(rest_anon) if f["status"] == "live" and f["ret"] > 0 and f["href"]]
    breaches = [{"what": f"{f['name']}, live at +{f['ret']} % on /fund-performance, is not on the board", "url": f["href"]}
                for f in up if f["href"] not in urls]
    _verdict(breaches, len(up), "every live fund that is up is on the board", {"board": DATA, "funds": RANKED})


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_72h_cards_peak_day_is_inside_its_72_hours(rest_anon):
    """A 72h card is measured at its close, so its peak came in its first days, not on the day it is read."""
    rows = [r for r in _data(rest_anon)["board"]["rows"] if r.get("k") == "h72"]
    late = [r for r in rows if r["days"] - r["dp"] > LAST_72H_DAY]
    breaches = [{"what": f"{len(late)} of {len(rows)} 72h cards show a peak day after their 72 hours, "
                         f"e.g. {r['n'][:40]}: {r['days']} / {r['days'] - r['dp']}", "url": r["u"]} for r in late[:5]]
    _verdict(breaches, len(rows), "every 72h card's peak day is inside its 72 hours", {"board": DATA})


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_pitch_chart_ends_where_its_big_number_does(rest_anon):
    """The card's line is the result so far, so it ends at the big number. A line that does, or a card that says what
    else its line is, clears it. FTA Fund -- Cryptos, 2026-11-03: +7.45 % over a two-point line ending at +1.52 %, and
    "flat this week" with ret5 empty."""
    pitches = _data(rest_anon).get("pitches") or []
    breaches = []
    for pitch in pitches:
        line, ret = pitch.get("line") or [], pitch.get("ret")
        if line and isinstance(ret, (int, float)) and abs(line[-1][1] - ret) > LINE_OFF_BY:
            breaches.append({"what": f"{pitch['name']}: big number {ret:+.2f} %, its line ends at {line[-1][1]:+.2f} % "
                                     f"after {len(line)} points", "url": pitch.get("href")})
    if not pitches:
        raise Inconclusive(f"{DATA}: no pitches")
    _verdict(breaches, len(pitches), "every pitch's line ends at its big number", {"board": DATA})


CREDIT = re.compile(r"\b(helped|drove|driven|pushed|lifted|led|behind|powered|boosted|carried)\b", re.I)


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_theme_pitch_does_not_credit_a_holding_that_fell(rest_anon):
    """A pitch that says holdings pushed the basket up names legs of that basket whose own return, over the same
    window, is positive. 2026-11-04: "Vultisig and Matrixdock Gold helped push this crypto basket up 3 percent this
    week", legs at -3.78 % and -2.82 % over 5 days, while Ambire Wallet, DMT-NAT and Hatom made it."""
    pitches = [p for p in _data(rest_anon).get("pitches") or [] if p.get("kind") == "theme"]
    if not pitches:
        raise Inconclusive(f"{DATA}: no theme pitch in the deck")
    breaches = []
    for pitch in pitches:
        slug = (pitch.get("href") or "").split("#theme-")[-1]
        legs = []
        for asset in ("stocks", "crypto"):
            response = get_patiently(rest_anon, f"/api/v1/themes/performance/{slug}?asset_class={asset}")
            if response.status_code == 200:
                legs = ((response.json().get("windows") or {}).get("5d") or {}).get("legs") or []
                if legs:
                    break
        said = pitch.get("say") or ""
        if not legs or not CREDIT.search(said):
            continue
        for leg in legs:
            name = str(leg.get("name") or "")
            named = re.search(r"\b" + re.escape(str(leg.get("symbol") or "~")) + r"\b", said) or (len(name) > 3 and name.lower() in said.lower())
            if named and isinstance(leg.get("return_pct"), (int, float)) and leg["return_pct"] <= 0:
                breaches.append({"what": f"{pitch['name']}: \"{said[:110]}\" names {name}, {leg['return_pct']:+.2f} % over 5 days", "url": pitch.get("href")})
    _verdict(breaches, len(pitches), "no theme pitch credits a holding that fell", {"board": DATA, "themes": "/api/v1/themes/performance/{slug}"})


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_pitch_chart_is_not_drawn_around_one_bad_reading(rest_anon):
    """A faint peer line on a pitch with one reading far off both neighbours, which agree. Dropped at the source or
    left out of the chart's scale, it clears."""
    pitches = _data(rest_anon).get("pitches") or []
    breaches, lines = [], 0
    for pitch in pitches:
        for line in pitch.get("peers") or []:
            lines += 1
            vals = [p[1] for p in line]
            for a, v, b in zip(vals, vals[1:], vals[2:]):
                if abs(v - a) > SPIKE and abs(v - b) > SPIKE and abs(a - b) < NEIGHBOURS:
                    breaches.append({"what": f"{pitch['name']}'s chart: a peer reads {a}, {v}, {b} in three readings"})
    if not lines:
        raise Inconclusive(f"{DATA}: no peer lines on any pitch")
    _verdict(breaches, lines, "no peer line has a lone reading off both neighbours", {"board": DATA})
