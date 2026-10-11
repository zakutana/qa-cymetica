"""The laboratory's report: what each product earned, after costs.

Plan v2, V4 (docs/laborator-plan.md). The laboratory is a department, and a
department has one shape: its page reads one file, `state/lab/report.json`,
and `lab.py report` writes it from the diaries on this machine. Nothing here
is fetched and nothing here is new arithmetic -- it only regroups what the
board (`qa.lab.board`), the verdicts (V2) and the memecoin answer
(`qa.fomo.ten_dollars`, V3) already say, by product.

A product is a kind of room: cards, bots, funds -- plus memecoins, which is
not a room at all but "$10 into every hot signal". Per product:

* `net_pct`: the mean over its experiments of each one's return after costs
  -- a judged room's verdict return (V2 made it net), otherwise its mark:
  our positions' P&L on the stake priced, less the live round trip for a card
  (`qa.lab._net_of`, the gate's 1.4 %), a bot as their engine books it;
* `n`: the experiments with a number; `running`; `archived`;
* `wilson`: the 95 % band on the share of experiments that made money, and
  `None` under `MIN_N` -- two coins are not a measurement;
* `usdc` and `stake_usdc`: the same net return in money, over what went in.

Every room's own row rides beside them (`rooms`), which is what /lab ranks.

Pure: every input is handed in, so a test holds the whole of it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from qa import fomo, lab
from qa import rooms as rooms_mod
from qa.rooms import names as room_names

# The laboratory's sections (v3, 2026-10-11) and funds, which the report still adds up for
# the rooms opened before they were switched off and the page no longer draws.
PRODUCTS = rooms_mod.SECTIONS + ("funds",)
# Their own score, the line the operator asked about on 2026-09-14.
CONVICTION_MIN = 70.0
# Under this many experiments no band is printed; the page says "málo dat".
MIN_N = 5
# The memecoin headline is read at this swap fee a side; 0.5, 1 and 2 ride beside.
MEMECOIN_FEE_PCT = fomo.HEADLINE_FEE_PCT      # 1.0 until 2026-10-08; no swap fee since


def _latest(room_rows: list[dict], kind: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in room_rows:
        if row.get("type") == kind:
            out[str(row.get("room"))] = row
    return out


def _band(hits: int, n: int) -> list[float] | None:
    if n < MIN_N:
        return None
    band = fomo._wilson(hits, n)
    return [band[0], band[1]] if band else None


def _room_net(room: dict, verdict: dict | None, money: dict | None) -> float | None:
    """A judged room's verdict return; otherwise its mark after costs."""
    if verdict and isinstance(verdict.get("return_pct"), (int, float)):
        return float(verdict["return_pct"])
    if not money or not money.get("priced") or not money.get("priced_stake"):
        return None
    gross = money["pnl"] / money["priced_stake"] * 100.0
    return lab._net_of(gross, lab._cost({"kind": room.get("kind") or "card"}))


def _product(room: dict, bot_origins: set[str], plan: dict | None = None) -> str | None:
    """A room's product -- since v3 (2026-10-11) its section. The section it was opened in,
    when its row names one. Otherwise: rooms opened before 2026-09-21 carry no kind: one
    naming a card holds cards, and one whose answer's order was a clone
    (STR-0001, Perceptron Oracle) holds a bot. And a kindless room whose plan
    holds legs of one kind is that kind -- STR-0045, five bots from our own
    proposal, showed under the cards (2026-09-24). A card room of ours is ours, never among
    his cards (none was opened before v3, so this moves no room). One reading, the rooms'
    own (`qa.rooms.section_of`), so the register and this report cannot disagree."""
    return rooms_mod.section_of(room, plan, bot_origins)


def _rooms(answers, notebook, room_rows, paper_rows, sample_rows,
           clone_rows) -> list[dict]:
    bot_origins = {str((r.get("nexus") or {}).get("id"))
                   for r in clone_rows or ()
                   if r.get("type") == "intent" and isinstance(r.get("nexus"), dict)}
    status = {k: str(v.get("status")) for k, v in
              _latest(room_rows, "status").items()}
    verdicts = _latest(room_rows, "verdict")
    money: dict[str, dict] = {}
    for row in lab.board(answers, notebook, room_rows, paper_rows,
                         sample_rows, clone_rows):
        for each in row["rooms"]:
            if each.get("money"):
                money[str(each["id"])] = each["money"]
    archived = lab.archived_rooms(room_rows, answers, paper_rows, clone_rows)
    # A room's name is its newest `title` row, as /lab says it: the opening
    # title named STR-0004 by a basket it no longer holds (R04, deep pass of
    # 2026-09-24).
    titles = room_names(room_rows)
    plans = rooms_mod.plans(room_rows)
    out = []
    for room in room_rows:
        if room.get("type") != "strategy":
            continue
        rid = str(room.get("id"))
        verdict = verdicts.get(rid)
        gone = rid in archived
        book = money.get(rid) or {}
        net = None if gone else _room_net(room, verdict, book)
        stake = book.get("priced_stake") if book.get("priced") else None
        out.append({
            "id": rid, "title": titles.get(rid, room.get("title")),
            "origin": room.get("origin"),
            "product": _product(room, bot_origins, plans.get(rid)),
            "status": status.get(rid), "archived": gone,
            "verdict": (verdict or {}).get("verdict"),
            "net_pct": net, "stake_usdc": stake,
            # The same net return, in money, over what was put in.
            "usdc": (stake * net / 100.0
                     if stake and net is not None else None)})
    return out


def _sector(rooms: list[dict]) -> dict:
    judged = [r for r in rooms if r["net_pct"] is not None]
    moneyed = [r for r in judged if r["usdc"] is not None]
    return {
        "n": len(judged),
        "net_pct": (sum(r["net_pct"] for r in judged) / len(judged)
                    if judged else None),
        "usdc": sum(r["usdc"] for r in moneyed) if moneyed else None,
        "stake_usdc": (sum(r["stake_usdc"] for r in moneyed)
                       if moneyed else None),
        "wins": sum(1 for r in judged if r["net_pct"] > 0),
        "wilson": _band(sum(1 for r in judged if r["net_pct"] > 0), len(judged)),
        "min_n": MIN_N,
        "running": sum(1 for r in rooms if r["status"] == "running"),
        "archived": sum(1 for r in rooms if r["archived"])}


def _high_conviction(fomo_rows: list[dict]) -> list[dict]:
    """The signals their own score put at CONVICTION_MIN or more, each with
    its own checkpoints. A signal with no score is not a low one."""
    keep = {r.get("key") for r in fomo_rows
            if r.get("type") == "signal"
            and isinstance(r.get("conviction"), (int, float))
            and not isinstance(r.get("conviction"), bool)
            and r["conviction"] >= CONVICTION_MIN}
    return [r for r in fomo_rows if r.get("key") in keep]


def _memecoins(fomo_rows: list[dict], now) -> dict:
    said = fomo.ten_dollars(fomo_rows, now=now) if fomo_rows else {}
    by_fee = said.get("by_fee") or {}
    head = by_fee.get(MEMECOIN_FEE_PCT) or {}
    n = int(head.get("n") or 0)
    rate = head.get("win_rate")
    wins = round(rate * n) if isinstance(rate, (int, float)) else 0
    # [operator 2026-09-14] asked what entering only at conviction 70 and up
    # would make: the same question, over those signals alone.
    high = _high_conviction(fomo_rows or [])
    high_said = fomo.ten_dollars(high, now=now) if high else {}
    high_head = (high_said.get("by_fee") or {}).get(MEMECOIN_FEE_PCT) or {}
    return {
        "n": n, "net_pct": head.get("mean_net_pct"), "wins": wins,
        "median_pct": head.get("median_net_pct"),
        "usdc": None, "stake_usdc": None,
        "wilson": _band(wins, n), "min_n": MIN_N,
        "running": int(said.get("window_open") or 0), "archived": None,
        "fee_pct": MEMECOIN_FEE_PCT,
        # What could not be bought or measured, by reason: the page names the
        # filter (the operator, 2026-09-14) rather than hiding it.
        "excluded": said.get("excluded") or {},
        # Kept in the answer: a drained pool, sold for what is left in it.
        "switched": int(said.get("switched") or 0),
        "signals": said.get("signals"),
        "could_buy_share": said.get("could_buy_share"),
        "conviction_70": {"min": CONVICTION_MIN,
                          "n": int(high_head.get("n") or 0),
                          "net_pct": high_head.get("mean_net_pct")},
        "fees": [{"fee_pct": fee, "net_pct": row.get("mean_net_pct"),
                  "n": row.get("n")} for fee, row in sorted(by_fee.items())]}


def _hot(notebook: list[dict]) -> dict | None:
    """The newest Hot headlines reading the tick wrote (`hot_reading`, qa/hot.py), as the
    memecoin section shows it: crypto that entered Hot against crypto that did not, 24 h on,
    and the Nexus rule with the most trades behind it. None when nothing was read."""
    readings = [r for r in notebook or () if r.get("type") == "hot_reading"]
    if not readings:
        return None
    newest = max(readings, key=lambda r: str(r.get("at") or ""))

    def day(rows):
        row = next((r for r in rows or () if r.get("hours") == 24.0), None)
        return ({"n": row.get("n"), "mean": row.get("mean"), "up": row.get("up")}
                if row else None)

    rules = newest.get("rules") or {}
    best = max(rules, key=lambda k: (rules[k].get("n") or 0, k), default=None)
    rule = None
    if best:
        verdict = str(rules[best].get("verdict") or "")
        of = re.search(r"of (\d+) trades", verdict)
        rule = {"id": best, "n": rules[best].get("n") or 0,
                "of": int(of.group(1)) if of else None,
                "mean_net": rules[best].get("mean_net")}
    return {"at": newest.get("at"),
            "entered": day((newest.get("follow") or {}).get("crypto")),
            "not_in_hot": day((newest.get("control") or {}).get("crypto")),
            "rule": rule}


def _nexus(nexus_rows, notebook, room_rows) -> dict:
    """His questions followed to the end: asked, answered, what his answers
    picked (the rooms holding a pick), what the gate passed, what survived."""
    answers = [r for r in nexus_rows if r.get("type") == "answer"]
    gates = [r for r in notebook if r.get("type") == "gate"]
    # His record only: a room of ours (V5, OUR-...) is our idea, and what it
    # earned is not a pick of his that survived.
    ours = {str(r.get("id")) for r in room_rows
            if r.get("type") == "strategy" and lab.is_ours(r.get("origin"))}
    verdicts = [v for room, v in _latest(room_rows, "verdict").items()
                if room not in ours]
    statuses = [s for room, s in _latest(room_rows, "status").items()
                if room not in ours]
    return {
        "questions": sum(1 for r in nexus_rows if r.get("type") == "question"),
        "answered": len({str(a.get("id")) for a in answers}),
        "picks": len(lab.picked_rooms(room_rows, answers)),
        "gated": len(gates),
        "gate_pass": sum(1 for g in gates if g.get("verdict") == "pass"),
        "survived": sum(1 for v in verdicts if v.get("verdict") == "survived"),
        "refuted": sum(1 for v in verdicts if v.get("verdict") == "refuted"),
        "inconclusive": sum(1 for v in verdicts if v.get("verdict") == "inconclusive"),
        "running": sum(1 for s in statuses if s.get("status") == "running")}


def report(nexus_rows: list[dict], notebook: list[dict], room_rows: list[dict],
           paper_rows: list[dict], sample_rows: list[dict],
           clone_rows: list[dict], fomo_rows: list[dict], now=None) -> dict:
    moment = now or datetime.now(timezone.utc)
    answers = [r for r in nexus_rows if r.get("type") == "answer"]
    rooms = _rooms(answers, notebook, room_rows, paper_rows, sample_rows,
                   clone_rows)
    products = {p: _sector([r for r in rooms if r["product"] == p])
                for p in PRODUCTS if p != "memecoins"}
    products["memecoins"] = dict(_memecoins(fomo_rows, moment), hot=_hot(notebook))
    return {"generated_at": moment.isoformat(timespec="seconds"),
            "products": {p: products[p] for p in PRODUCTS},
            "nexus": _nexus(nexus_rows, notebook, room_rows),
            "rooms": rooms}
