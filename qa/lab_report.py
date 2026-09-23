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
* `best`: the room that made the most.

Pure: every input is handed in, so a test holds the whole of it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from qa import fomo, lab

PRODUCTS = ("cards", "bots", "memecoins", "funds")
KIND_PRODUCT = {"card": "cards", "arena": "cards", "bot": "bots",
                "fund": "funds"}
# Under this many experiments no band is printed; the page says "málo dat".
MIN_N = 5
# The memecoin headline is read at this swap fee a side; 0.5 and 2 ride beside.
MEMECOIN_FEE_PCT = 1.0


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


def _rooms(answers, notebook, room_rows, paper_rows, sample_rows,
           clone_rows) -> list[dict]:
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
    out = []
    for room in room_rows:
        if room.get("type") != "strategy":
            continue
        rid = str(room.get("id"))
        verdict = verdicts.get(rid)
        gone = rid in archived
        out.append({
            "id": rid, "title": room.get("title"), "origin": room.get("origin"),
            "product": KIND_PRODUCT.get(room.get("kind") or "card", "cards"),
            "status": status.get(rid), "archived": gone,
            "verdict": (verdict or {}).get("verdict"),
            "net_pct": None if gone else _room_net(room, verdict, money.get(rid))})
    return out


def _product(rooms: list[dict]) -> dict:
    judged = [r for r in rooms if r["net_pct"] is not None]
    best = max(judged, key=lambda r: r["net_pct"], default=None)
    return {
        "n": len(judged),
        "net_pct": (sum(r["net_pct"] for r in judged) / len(judged)
                    if judged else None),
        "wins": sum(1 for r in judged if r["net_pct"] > 0),
        "wilson": _band(sum(1 for r in judged if r["net_pct"] > 0), len(judged)),
        "min_n": MIN_N,
        "running": sum(1 for r in rooms if r["status"] == "running"),
        "archived": sum(1 for r in rooms if r["archived"]),
        "best": ({"room": best["id"], "title": best["title"],
                  "net_pct": best["net_pct"]} if best else None)}


def _memecoins(fomo_rows: list[dict], now) -> dict:
    said = fomo.ten_dollars(fomo_rows, now=now) if fomo_rows else {}
    by_fee = said.get("by_fee") or {}
    head = by_fee.get(MEMECOIN_FEE_PCT) or {}
    n = int(head.get("n") or 0)
    rate = head.get("win_rate")
    wins = round(rate * n) if isinstance(rate, (int, float)) else 0
    return {
        "n": n, "net_pct": head.get("mean_net_pct"), "wins": wins,
        "wilson": _band(wins, n), "min_n": MIN_N,
        "running": int(said.get("window_open") or 0), "archived": None,
        "best": None, "fee_pct": MEMECOIN_FEE_PCT,
        "signals": said.get("signals"),
        "could_buy_share": said.get("could_buy_share"),
        "fees": [{"fee_pct": fee, "net_pct": row.get("mean_net_pct"),
                  "n": row.get("n")} for fee, row in sorted(by_fee.items())]}


def _nexus(nexus_rows, notebook, room_rows) -> dict:
    """His questions followed to the end: asked, answered, what his answers
    picked (the rooms holding a pick), what the gate passed, what survived."""
    answers = [r for r in nexus_rows if r.get("type") == "answer"]
    gates = [r for r in notebook if r.get("type") == "gate"]
    verdicts = list(_latest(room_rows, "verdict").values())
    return {
        "questions": sum(1 for r in nexus_rows if r.get("type") == "question"),
        "answered": len({str(a.get("id")) for a in answers}),
        "picks": len(lab.picked_rooms(room_rows, answers)),
        "gated": len(gates),
        "gate_pass": sum(1 for g in gates if g.get("verdict") == "pass"),
        "survived": sum(1 for v in verdicts if v.get("verdict") == "survived"),
        "refuted": sum(1 for v in verdicts if v.get("verdict") == "refuted")}


def report(nexus_rows: list[dict], notebook: list[dict], room_rows: list[dict],
           paper_rows: list[dict], sample_rows: list[dict],
           clone_rows: list[dict], fomo_rows: list[dict], now=None) -> dict:
    moment = now or datetime.now(timezone.utc)
    answers = [r for r in nexus_rows if r.get("type") == "answer"]
    rooms = _rooms(answers, notebook, room_rows, paper_rows, sample_rows,
                   clone_rows)
    products = {p: _product([r for r in rooms if r["product"] == p])
                for p in PRODUCTS if p != "memecoins"}
    products["memecoins"] = _memecoins(fomo_rows, moment)
    return {"generated_at": moment.isoformat(timespec="seconds"),
            "products": {p: products[p] for p in PRODUCTS},
            "nexus": _nexus(nexus_rows, notebook, room_rows),
            "rooms": rooms}
