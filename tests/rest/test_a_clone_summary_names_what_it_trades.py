"""A clone's summary line names what the bot trades, all of it and nothing else (2026-10-11).

ET-28100 item 1, shipped 2026-10-10 (their message, recorded as REPLY-0151): "every
/clone/{id} page opens with a one-line summary, for example 'This bot trades: BTC/ETH/VAIX/SBIO
5-min epochs (paper)'. It is built from the bot's live settings: perpetual epochs, CLOB pairs,
arena, event cards, catalog, covered calls, arbitrage, paper or live. ... Agents get the same
line as trades_summary from GET /api/v1/cloned-bots/{id}/profile." The page's own script
carries a client-side twin of the server's rule (`ClonedBotProfile.tradesSummary`, used only
when the profile sends no `trades_summary`); the settings form reads `custom_markets` and
`perpetual_markets` as "'NONE' = explicitly off, CSV = those symbols".

**What was seen when this was written** (2026-10-10 22:10 UTC, our 41 paper clones):
30 clones with nine perpetual markets switched on (BTC, ETH, VAIX, SBIO, ET10, ETLP, CYM42,
TBIG, TBIGS) read "This bot trades: BTC/ETH/VAIX/SBIO 5-min epochs (paper)": five markets
gone and no "+5", although the CLOB list in the same rule writes "+N" past four. One clone with
both lists set to 'NONE' (off) reads "This bot trades: CLOB NONE · Arena headline assets
(paper)": a CLOB market called NONE.

**The rule.** For every clone whose profile states a summary and settings: each market its
settings switch on (perpetual epochs, or the CLOB list when no perpetual list is set; CLOB
pairs) is named in the line, or counted by a "+N" that covers the ones left out; and a list
set to 'NONE' never appears as a market called NONE. Any fix passes: all markets named, a
count, a shorter wording that says how many.

NOT asserted: the order, the separators, arena / event cards / catalog / covered calls /
arbitrage (on-off parts with no list), or paper/live. The page's layout is not read.

SAFE: GETs only, our own clones with our key.
"""

from __future__ import annotations

import re
import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/cloned-bots"
CLAIM = "clone-summary-names-every-market-it-trades"
OFF = "NONE"
PAUSE_S = 0.4
MIN_JUDGED = 5


def _csv(raw) -> list[str]:
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else str(raw).split(",")
    out = []
    for item in items:
        sym = str(item).strip().upper()
        if sym and sym not in out:
            out.append(sym)
    return out


def switched_on(settings: dict) -> dict[str, list[str]]:
    """The market lists a clone's settings switch on, read as their form reads them: 'NONE' is off,
    a CSV is those symbols, and no perpetual list means the CLOB list (their rule's fallback)."""
    s = settings or {}
    clob = [] if str(s.get("custom_markets") or "").strip().upper() == OFF else _csv(s.get("custom_markets"))
    perp_raw = s.get("perpetual_markets")
    if str(perp_raw or "").strip().upper() == OFF:
        perp = []
    elif perp_raw:
        perp = _csv(perp_raw)
    else:
        perp = list(clob)
    return {"perpetual": perp, "clob": clob}


def _named(symbol: str, line: str) -> bool:
    return re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", line.upper()) is not None


_PART_OF = {"perpetual": "epoch", "clob": "clob"}


def _count_in_part(kind: str, summary: str) -> list[int]:
    """The "+N" counts of one list's own part of the line ("... 5-min epochs", "CLOB ..."), parts
    split at the line's separators. A count in another list's part covers nothing of this one
    (deep pass 2026-10-11, B04: the CLOB's "+5" excused five perpetual markets left out)."""
    parts = re.split(r"\s*[·•|]\s*", summary)
    mine = [p for p in parts if _PART_OF[kind] in p.lower()]
    return [int(n) for p in mine for n in re.findall(r"\+\s?(\d+)", p)]


def summary_misstates(settings, summary) -> dict | None:
    """What a summary line gets wrong about its own settings, or None when it can't be judged
    (no line or no settings). `{}` when the line is right."""
    if not isinstance(summary, str) or not summary.strip() or not isinstance(settings, dict):
        return None
    wrong = {}
    for kind, symbols in switched_on(settings).items():
        if not symbols:
            continue
        left_out = [s for s in symbols if not _named(s, summary)]
        if left_out and len(left_out) not in _count_in_part(kind, summary):
            wrong[f"{kind}_left_out"] = {"on": len(symbols), "named": len(symbols) - len(left_out),
                                         "left_out": left_out}
    off = [k for k in ("custom_markets", "perpetual_markets") if str(settings.get(k) or "").strip().upper() == OFF]
    if off and _named(OFF, summary):
        wrong["off_named_as_a_market"] = off
    return wrong


def _profile(rest_trusted, bot_id: str) -> dict | None:
    time.sleep(PAUSE_S)
    r = rest_trusted.get(f"{PREFIX}/{bot_id}/profile")
    if r.status_code != 200:
        return None
    try:
        body = r.json()
    except ValueError:
        return None
    body = body.get("result", body) if isinstance(body, dict) else None
    return body if isinstance(body, dict) else None


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_a_clone_summary_names_every_market_it_trades_and_no_other(rest_trusted):
    """Every paper clone's trades_summary against the settings its own profile states."""
    r = rest_trusted.get(f"{PREFIX}/my-clones", params={"mode": "paper"})
    if r.status_code != 200 or not isinstance(r.json(), list):
        raise Inconclusive(f"my-clones answered HTTP {r.status_code}")
    clones = [c for c in r.json() if isinstance(c, dict) and c.get("id")]
    judged, wrong, unread, examples = 0, [], [], {}
    for clone in clones:
        profile = _profile(rest_trusted, clone["id"])
        said = summary_misstates((profile or {}).get("settings"), (profile or {}).get("trades_summary"))
        if said is None:
            unread.append(clone["id"][:8])
            continue
        judged += 1
        if said:
            on = switched_on(profile["settings"])
            row = {"id": clone["id"][:8], "name": clone.get("name"), "trades_summary": profile["trades_summary"],
                   "perpetual_markets": profile["settings"].get("perpetual_markets"),
                   "custom_markets": profile["settings"].get("custom_markets"), "switched_on": on, "wrong": said}
            wrong.append(row)
            examples.setdefault(tuple(sorted(said)), row)
    if judged < MIN_JUDGED:
        raise Inconclusive(f"only {judged} of {len(clones)} clones state a summary and settings; unread {unread[:8]}")
    left_out = [w for w in wrong if any(k.endswith("_left_out") for k in w["wrong"])]
    none_named = [w for w in wrong if "off_named_as_a_market" in w["wrong"]]

    def said(w) -> str:
        parts = []
        for k, v in w["wrong"].items():
            if k.endswith("_left_out"):
                parts.append(f"{v['named']} of {v['on']} {k.split('_')[0]} markets named, "
                             f"{', '.join(v['left_out'])} left out with no count")
            else:
                parts.append(f"{' and '.join(v)} set to '{OFF}' (off) printed as a market called {OFF}")
        return (f"{w['id']} \"{w['trades_summary']}\" with perpetual_markets {w['perpetual_markets']!r}, "
                f"custom_markets {w['custom_markets']!r}: " + "; ".join(parts))

    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(f"{len(wrong)} of {judged} paper clones state a trades_summary that misstates their own settings: "
                f"{len(left_out)} leave switched-on markets out with no \"+N\", {len(none_named)} print a list set to "
                f"'{OFF}' as a market. " + " | ".join(said(w) for w in examples.values())
                if wrong else
                f"all {judged} paper clones' summaries name every market they switch on and no list set to "
                f"'{OFF}'"),
        left={"clones_misstated": len(wrong), "left_out": len(left_out), "none_named": len(none_named)},
        right={"clones_misstated": 0},
        population={"judged": judged, "clones": len(clones), "unread": unread, "wrong": wrong[:12]},
        sources={"list": f"{PREFIX}/my-clones?mode=paper", "profile": f"{PREFIX}/{{id}}/profile",
                 "contract": "ET-28100 item 1 (REPLY-0151): one line built from the bot's live settings; the "
                             "settings form: 'NONE' = explicitly off, CSV = those symbols"},
        claim_id=CLAIM))
