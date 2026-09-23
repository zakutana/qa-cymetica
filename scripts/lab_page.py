"""The laboratory's page, served at /lab and never committed.

Plan v2, V4 (docs/laborator-plan.md): the laboratory is the product, and it
has a page of its own. At the top, per product -- Karty, Boti, Memecoiny,
Fondy -- what it earned after costs, how many experiments that stands on and
how sure it is, from `state/lab/report.json` (`lab.py report`, rewritten on
every visit). Under it the rooms with Nexus -- the thread, the strategy's
numbers and the box the operator writes a note in -- and the memecoin
measurement in full.

Everything here used to be two tabs of the committed console (the Nexus and
Memecoiny tabs of scripts/render.py). They moved because every figure on them
comes from a gitignored diary, and the committed page hashed those diaries:
a fresh clone could not re-render what was committed (D2 of the 2026-09-23
review). This page is rendered on request by scripts/serve.py and written
nowhere, so it may read anything on this machine.

What the page reaches: /rooms.json (build_rooms, below), /token and
POST /notes -- the one write, through qa.rooms.add_operator_note, behind the
guards serve.py already holds -- and /events for "the rooms moved".
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _nexus_questions() -> list[dict] | None:
    """Every question put to ask_nexus_deep, once, with what happened to it.

    One derivation for two readers -- the Stats row counts these and the Nexus
    tab draws them -- so the two cannot disagree about which question was
    answered. None when nexus.py's record cannot be read at all, which is not
    the same thing as a record with nothing in it.

    Outcomes: answered; partial -- finalised "done" with only an opening
    sentence, their NEX-0009, fixed 2026-09-10 21:22; failed -- our loop gave
    up; refused -- no investigation started, QUERY_RESTRICTED and the like;
    waiting.
    """
    import importlib.util

    from qa.rooms import ANSWERED_CHARS

    try:
        spec = importlib.util.spec_from_file_location(
            "nexus_stats", REPO_ROOT / "scripts" / "nexus.py")
        nexus = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nexus)
        rows = nexus.load()
    except Exception:  # noqa: BLE001 -- an unreadable record is not a page defect
        return None
    questions = []
    for question in rows:
        if question.get("type") != "question":
            continue
        qid = question.get("id")
        mine = [r for r in rows if r.get("id") == qid]
        answer = next((r for r in mine if r.get("type") == "answer"), None)
        gave_up = next((r for r in mine if r.get("type") == "gave_up"), None)
        if answer is not None:
            whole = len(answer.get("text") or "") >= ANSWERED_CHARS
            outcome = "answered" if whole else "partial"
        elif gave_up is not None:
            outcome = "failed"
        elif question.get("accepted") is False:
            outcome = "refused"
        else:
            outcome = "waiting"
        lower, upper = nexus.latency_bounds(rows, qid)
        seconds = (round((lower + upper) / 2, 1)
                   if lower is not None and upper is not None else None)
        questions.append({"id": qid, "at": question.get("at"),
                          "outcome": outcome, "seconds": seconds,
                          "upper": upper, "question": question,
                          "answer": answer, "gave_up": gave_up})
    return questions


def _nexus_summary(questions: list[dict]) -> dict:
    """The counts, and a typical time taken ONLY over questions we watched.

    Watched means both bounds known. A question looked at once, late, has only
    an upper bound, and counting it is how our pickup delay went out as their
    latency once already.
    """
    watched = sorted(q["seconds"] for q in questions
                     if q["seconds"] is not None
                     and q["outcome"] in ("answered", "partial"))
    median = None
    if watched:
        middle = len(watched) // 2
        median = (watched[middle] if len(watched) % 2
                  else round((watched[middle - 1] + watched[middle]) / 2, 1))

    def count(outcome):
        return sum(1 for q in questions if q["outcome"] == outcome)

    return {"asked": len(questions), "answered": count("answered"),
            "partial": count("partial"), "failed": count("failed"),
            "refused": count("refused"), "waiting": count("waiting"),
            "measured": len(watched), "median_seconds": median}


def _nexus_channel() -> dict:
    """Every question put to ask_nexus_deep, one entry each, by what happened.

    Not on the page at all until 2026-09-11, when the operator asked whether
    Nexus is reliable yet, next to Telegram. The outcomes are
    _nexus_questions()'s and the typical time is _nexus_summary()'s. On the
    console's Stats tab until V4; on /lab's Nexus line since, because the
    record it counts is gitignored.

    Verdicts and times, never the words: the words are in the rooms.
    """
    derived = _nexus_questions()
    if not derived:
        return {"asked": 0, "answered": 0, "partial": 0, "failed": 0,
                "refused": 0, "waiting": 0, "measured": 0,
                "median_seconds": None, "questions": []}
    return {**_nexus_summary(derived),
            "questions": [{k: q[k] for k in ("id", "at", "outcome", "seconds",
                                             "upper")} for q in derived]}


def _response_of(outcome: dict | None) -> dict:
    """The server's own reply stored inside an outcome row, parsed -- or {}."""
    raw = (outcome or {}).get("response")
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _amount(value) -> str:
    """10000.0 -> '10 000', 0.00216 -> '0.00216': a figure as a sentence says it."""
    number = _num(value)
    if number is None:
        return "?"
    if number.is_integer():
        return f"{int(number):,}".replace(",", " ")
    if abs(number) >= 1:
        return f"{number:,.2f}".replace(",", " ")
    return f"{number:g}"


def _said(outcome: dict | None) -> str:
    """What became of an order, in its outcome row's own words."""
    if not outcome:
        return "no outcome recorded"
    said = outcome.get("outcome") or "unknown"
    status = outcome.get("http_status")
    return f"{said} (HTTP {status})" if status and said != "accepted" else said


def _orders(rows: list[dict]) -> list[tuple[str, dict, dict | None]]:
    """(id, intent, outcome) for every order in a paper.py or clone.py record,
    in the order the intents were written. A sample is not an order."""
    parts: dict[str, dict] = {}
    for row in rows:
        rid, kind = row.get("id"), row.get("type")
        if isinstance(rid, str) and kind in ("intent", "outcome"):
            parts.setdefault(rid, {}).setdefault(kind, row)
    return [(rid, p["intent"], p.get("outcome")) for rid, p in parts.items()
            if "intent" in p]


def _sampler_state(tick: dict | None) -> dict:
    """Where the console's sampler stands: when it last went round, whether
    that round read everything, and whether it has gone quiet.

    Stale is three intervals without a round -- the plan's measure -- so one
    slow round is not an alarm and a dead loop is. None when it never ran,
    which is neither fresh nor stale.
    """
    from datetime import datetime, timezone

    if not tick:
        return {"sampled_at": None, "sampler_ok": None, "sampler_every": None,
                "stale": None, "sampler_reads": None}
    every = _num(tick.get("every")) or 600.0
    try:
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(str(tick.get("at")))).total_seconds()
    except (TypeError, ValueError):
        age = None
    return {"sampled_at": tick.get("at"), "sampler_ok": tick.get("ok"),
            "sampler_every": every,
            "stale": None if age is None else age > 3 * every,
            "sampler_reads": tick.get("reads")}


# A card whose trading is over. A leg on one that was never bought is past
# buying, not waiting for it.
CARD_CLOSED = ("settled", "resolved", "closed", "expired")


def _moment(text):
    """An ISO time as an aware datetime, or None. Their API writes +00:00 and
    so do we; a naive one is read as UTC."""
    from datetime import datetime, timezone

    try:
        moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _index_at(series: list, when) -> float | None:
    """Where a card's index stood at `when`: the last point at or before it,
    else the first after it -- the price a proposal would have been bought at."""
    moment = _moment(when)
    if moment is None:
        return None
    stood = None
    for t, value in series:
        at = _moment(t)
        if at is None or value is None:
            continue
        if at <= moment:
            stood = value
        elif stood is None:
            return value
        else:
            break
    return stood


def _label(card: dict) -> str | None:
    """A card named by what it holds, which its headline does not say: "BTC"
    when one coin is nearly all of it, else the two heaviest -- "68 % BCH ·
    32 % OKB". None until the sampler has described the card."""
    weighed = sorted(((b.get("symbol"), _num(b.get("weight")))
                      for b in card.get("basket") or [] if isinstance(b, dict)),
                     key=lambda pair: -(pair[1] or 0.0))
    weighed = [(symbol, weight) for symbol, weight in weighed
               if symbol and weight is not None]
    if not weighed:
        return None
    if weighed[0][1] >= 0.95:
        return str(weighed[0][0])
    return " · ".join(f"{round(weight * 100)} % {symbol}"
                      for symbol, weight in weighed[:2])


def _lay_out(panel: dict, plan: dict, described: dict, index_points: dict,
             proposed_at) -> None:
    """A strategy's legs: Nexus's plan, with what was done laid over it.

    An order finds its leg by the card it bought; an order on a card the plan
    does not name becomes a leg of its own, so nothing that was done is left
    off the table. A leg keeps where its card stood when Nexus answered, so an
    unbought one can say how it moved since -- which the page labels as what
    would have happened, never as ours. Its levels are the take-profit and
    stop Nexus gave, in percent, from the entry -- or from that price while
    nothing was bought.
    """
    bankroll = _num(plan.get("bankroll"))
    legs: list[dict] = []
    by_card: dict[str, dict] = {}
    live: dict[str, list] = {}

    def leg(card: str, planned: dict) -> dict:
        row = described.get(card) or {}
        points = index_points.get(card) or {}
        series = [[t, points[t]] for t in sorted(points)]
        share = _num(planned.get("share"))
        at_proposal = _index_at(series, proposed_at) if planned else None
        last = series[-1][1] if series else None
        # Their page for the card -- the address their API returns as share_url
        # -- and none for a card their API does not know.
        view = {"card": card, "url": (None if row.get("status") == "not_found"
                                      else "https://cymetica.com/events/" + card),
                "label": _label(row), "card_title": row.get("title"),
                "symbol": row.get("evcdx_symbol"), "card_status": row.get("status"),
                "closes_at": row.get("trading_closes_at"),
                "planned": bool(planned), "side": planned.get("side"),
                "share": share,
                "usdc_proposed": (round(share * bankroll, 2)
                                  if share is not None and bankroll else None),
                "tp": _num(planned.get("tp")), "sl": _num(planned.get("sl")),
                "orders": [], "state": "not bought", "entry": None,
                "current": last, "invested": 0.0, "value": None, "pnl": None,
                "tp_level": None, "sl_level": None, "at_proposal": at_proposal,
                "since_proposal": (round((last / at_proposal - 1) * 100, 4)
                                   if last is not None and at_proposal else None),
                "series": series[-400:]}
        by_card[card] = view
        legs.append(view)
        return view

    for planned in plan.get("legs") or []:
        if planned.get("card") and planned["card"] not in by_card:
            leg(planned["card"], planned)
    for trade in panel["trades"]:
        if trade["outcome"] != "accepted" or not trade.get("card"):
            continue
        view = by_card.get(trade["card"]) or leg(trade["card"], {})
        view["orders"].append(trade["id"])
        view["invested"] += trade["usdc"] or 0.0
        view["side"] = view["side"] or trade["side"]
        if view["entry"] is None:
            view["entry"] = trade["entry"]
        if trade["closed_by"]:
            if trade["realized"] is not None:
                view["pnl"] = round((view["pnl"] or 0.0) + trade["realized"], 6)
            continue
        view["state"] = "open"
        if trade["current_index"] is not None:
            view["current"] = trade["current_index"]
            if trade["live_at"]:
                live[trade["card"]] = [trade["live_at"], trade["current_index"]]
        if trade["unrealized"] is not None:
            view["pnl"] = round((view["pnl"] or 0.0) + trade["unrealized"], 6)
        if trade["live_value"] is not None:
            view["value"] = round((view["value"] or 0.0) + trade["live_value"], 6)
    for view in legs:
        # A position's own reading, when it is newer than the card's last index
        # point, ends the line -- so the chart's "now" is the table's.
        reading = live.get(view["card"])
        if reading and view["series"]:
            newer, last = _moment(reading[0]), _moment(view["series"][-1][0])
            if newer and last and newer > last:
                view["series"].append(reading)
        if view["orders"]:
            view["state"] = "open" if view["state"] == "open" else "closed"
        elif view["card_status"] == "not_found":
            view["state"] = "card not found"
        elif view["card_status"] in CARD_CLOSED:
            view["state"] = "card closed"
        base = view["entry"] or view["at_proposal"]
        if base:
            if view["tp"] is not None:
                view["tp_level"] = base * (1 + view["tp"] / 100)
            if view["sl"] is not None:
                view["sl_level"] = base * (1 + view["sl"] / 100)

    pnls = [v["pnl"] for v in legs if v["pnl"] is not None]
    values = [v["value"] for v in legs if v["value"] is not None]
    shares = [v["share"] for v in legs if v["share"]]
    moves = [(v["share"], v["since_proposal"]) for v in legs
             if v["share"] and v["since_proposal"] is not None]
    weight = sum(share for share, _ in moves)
    # The countdown is to the card that is held; with nothing held, to the
    # first of the proposed ones to close.
    held = [v["closes_at"] for v in legs if v["closes_at"] and v["state"] == "open"]
    waiting = [v["closes_at"] for v in legs
               if v["closes_at"] and v["state"] == "not bought"]
    invested = panel["staked"]
    pnl = round(sum(pnls), 2) if pnls else None
    value = round(sum(values), 2) if values else None
    bots = panel["clones"]
    if bots:
        invested, pnl, value = bots[0]["funded"], bots[0]["pnl"], bots[0]["balance"]
    panel.update(
        holds="bot" if bots else "cards" if legs else None,
        legs=legs, reserve=_num(plan.get("reserve")), bankroll=bankroll,
        proposed_at=proposed_at,
        proposed_share=round(sum(shares), 6) if shares else None,
        invested=invested, pnl=pnl, value=value,
        pnl_pct=(round(pnl / invested * 100, 3) if pnl is not None and invested
                 else None),
        closes_at=min(held or waiting, default=None),
        if_bought_pct=(round(sum(s * m for s, m in moves) / weight, 4)
                       if weight else None))


def build_rooms() -> dict:
    """The Nexus tab: every room, its thread, and its panel.

    NOT part of build_payload(), and that is the design rather than an
    omission. The rooms carry the operator's notes and, later, what the sampler
    reads on a timer; both arrive while a sweep may be running. Anything in
    the payload rewrites dashboard/index.html, which is committed, so a note
    would dirty the tree mid-run and cost the run its level V -- the reason
    state/nexus.jsonl is gitignored at all. serve.py answers /rooms.json from
    this function instead and tells the open tab with an event of its own.

    Texts are verbatim. Escaping happens once, in the page, where they are
    drawn: a Nexus answer is data (CLAUDE.md), and the page treats it as text.

    Each reply sits straight after its own question, whenever it arrived. A
    question given up on eighteen minutes later still belongs under the one
    it answers, not after the two that were asked in between.

    A strategy room is opened from one whole Nexus answer (qa/rooms.py
    refuses anything else) and draws what was done about it from records
    that already say so: an order carries the Nexus id it acts on, a close
    follows the order that opened its position, and everything done to a bot
    afterwards -- funding it, switching it on, every sample -- carries the
    bot's instance id. A `link` draws in what names nothing. What names no
    room stays in General and says which it is: an order drawn inside a
    strategy it did not come from would be our activity dressed as Nexus's
    guidance.

    What their API says since -- a card's index, the bot's own trades, what
    it has locked, its indicators -- comes from state/samples.jsonl, which
    the console's sampler writes (scripts/sampler.py), and every panel says
    when that was last read.

    A strategy is called by its newest `title`, and its plan -- Nexus's
    proposal, leg by leg -- is laid under what was done (_lay_out), so a
    panel can say what it holds before it says anything in words.
    """
    from datetime import datetime, timezone

    from qa import rooms as store

    try:
        from qa.lab import gates as lab_gates
    except Exception:  # the laboratory's diary is gitignored; a clone has none
        def lab_gates():
            return {}

    derived = _nexus_questions() or []
    stored = store.load()
    sampled = store.load_samples()
    sampler = _sampler_state(max((r for r in sampled if r.get("type") == "tick"),
                                 key=lambda r: str(r.get("at") or ""), default=None))
    marks = store.read_marks(stored)
    opened = store.strategies(stored)
    titles = store.names(stored)
    # A WHOLE-ANSWER room (no card) takes every order that acts on its answer.
    # A card room takes only the orders for its card: every order from one
    # answer carries the same Nexus id, and an order for a card none of the
    # answer's rooms holds belongs in General (R12, deep pass of 2026-09-21 --
    # it fell back to the answer's LAST room, a strategy it did not come from).
    # A bot or fund room (2026-09-22) has no card and is not a whole-answer
    # room either: it holds one thing of its answer, like a card room.
    by_origin = {s.get("origin"): s["id"] for s in opened
                 if store.room_key(s) is None}
    by_card = {(s.get("origin"), str(s.get("card")).lower()): s["id"]
               for s in opened if s.get("card")}
    linked: dict[str, str] = {}
    history: dict[str, list[dict]] = {room: [] for room in titles}
    for row in stored:
        room = row.get("room")
        if room not in titles:
            continue
        if row.get("type") == "link":
            linked[row.get("ref")] = room
        elif row.get("type") == "status":
            history[room].append({"status": row.get("status"),
                                  "why": row.get("why"), "at": row.get("at")})

    threads: dict[str, list[dict]] = {store.GENERAL: [],
                                      **{room: [] for room in titles}}
    order: dict[int, tuple] = {}

    def place(room: str, message: dict, at, rank: int) -> None:
        thread = threads[room if room in threads else store.GENERAL]
        order[id(message)] = (str(at or ""), rank, len(thread))
        thread.append(message)

    # Our summary of an answer is drawn inside it. The newest wins; one it
    # replaced stays on the page as a note, so nothing written disappears.
    asked = {q["id"] for q in derived}
    gists = {row["re"]: row for row in stored
             if row.get("type") == "claude_note" and row.get("gist") and row.get("re")}
    inside = {row.get("id") for qid, row in gists.items() if qid in asked}

    for q in derived:
        question, qid = q["question"], q["id"]
        home = (question.get("room") if question.get("room") in titles
                else linked.get(qid, store.GENERAL))
        opened_here = [s["id"] for s in opened if s.get("origin") == qid]
        gist = gists.get(qid)
        for room in [home] + [r for r in opened_here if r != home]:
            place(room, {"kind": "question", "id": qid, "at": q["at"],
                         "text": question.get("question") or "",
                         "opened": opened_here}, q["at"], 0)
            reply = {"kind": "reply", "id": qid, "outcome": q["outcome"],
                     "seconds": q["seconds"], "upper": q["upper"], "at": None,
                     "text": None, "gist": gist.get("text") if gist else None}
            if q["answer"] is not None:
                reply.update(at=q["answer"].get("at"),
                             text=q["answer"].get("text") or "")
            elif q["gave_up"] is not None:
                reply["at"] = q["gave_up"].get("at")
            elif q["outcome"] == "refused":
                reply.update(at=q["at"], text=question.get("error") or None)
            place(room, reply, q["at"], 1)
        if home != store.GENERAL:
            place(store.GENERAL, {"kind": "pointer", "id": qid, "at": q["at"],
                                  "room": home, "title": titles[home],
                                  "text": question.get("question") or ""},
                  q["at"], 0)

    panels: dict[str, dict] = {}
    for s in opened:
        changes = history[s["id"]]
        now = changes[-1] if changes else {}
        # What it was accepted on, and what the numbers said at the end of the
        # window. A room with neither is one nobody could score afterwards,
        # and the panel says so rather than leaving the space blank.
        accepted = store.acceptance_of(stored, s["id"])
        decided = store.verdict_of(stored, s["id"])
        panels[s["id"]] = {
            "kind": "strategy", "origin": s.get("origin"), "title": titles[s["id"]],
            "opened_at": s.get("at"), "status": now.get("status") or "proposed",
            "why": now.get("why"), "since": now.get("at") or s.get("at"),
            "history": changes, "trades": [], "staked": 0.0, "unclosed": 0,
            "realized": None, "clones": [],
            "criterion": ({"window_days": accepted.get("window_days"),
                           "stop_pct": accepted.get("stop_pct"),
                           "adopted": bool(accepted.get("adopted")),
                           "benchmark": accepted.get("benchmark_card"),
                           "at": accepted.get("at"), "why": accepted.get("why")}
                          if accepted else None),
            "verdict": ({"verdict": decided.get("verdict"),
                         "why": decided.get("why"),
                         "return_pct": decided.get("return_pct"),
                         "max_drawdown_pct": decided.get("max_drawdown_pct"),
                         "benchmark_pct": decided.get("benchmark_pct"),
                         "coverage": decided.get("coverage"),
                         "at": decided.get("at")}
                        if decided else None),
            "claim": (store.claim_of(stored, s["id"]) or {}).get("numbers") or None,
            **sampler}
        for change in changes:
            place(s["id"], {"kind": "status", "at": change["at"],
                            "status": change["status"], "text": change["why"]},
                  change["at"], 0)

    paper = store.records("paper.jsonl")
    opener_of: dict[str, dict] = {}
    for tid, intent, outcome in _orders(paper):
        said = (outcome or {}).get("outcome")
        if intent.get("kind") == "close":
            position = intent.get("position_id")
            opener = opener_of.get(position)
            room = linked.get(tid) or (opener["room"] if opener else store.GENERAL)
            realized = _num((outcome or {}).get("realized_pnl_usdc"))
            text = (f"{tid} · closed position {str(position)[:8]}"
                    + (f", opened by {opener['trade']['id']}" if opener
                       else ", which no order of ours opened")
                    + (f" · realized {realized:+g} USDC" if realized is not None
                       else "")
                    + ("" if said == "accepted" else f" · {_said(outcome)}"))
            if opener and said == "accepted":
                opener["trade"].update(closed_by=tid, closed_at=intent.get("at"),
                                       realized=realized)
        else:
            nexus_id = (intent.get("nexus") or {}).get("id")
            room = (linked.get(tid)
                    or by_card.get((nexus_id, str(intent.get("card_id")).lower()))
                    or by_origin.get(nexus_id) or store.GENERAL)
            response = _response_of(outcome)
            position = ((outcome or {}).get("position_id")
                        or response.get("position_id"))
            side = response.get("side")
            text = (f"{tid} · paper buy{', ' + str(side) if side else ''}, "
                    f"{_amount(intent.get('usdc'))} USDC on card "
                    f"{str(intent.get('card_id'))[:8]}"
                    + (f" · after {nexus_id}" if nexus_id
                       else " · ours, no Nexus answer behind it")
                    + (f" · position {str(position)[:8]}"
                       if said == "accepted" and position else f" · {_said(outcome)}"))
            trade = {"id": tid, "at": intent.get("at"), "card": intent.get("card_id"),
                     "side": side, "usdc": _num(intent.get("usdc")), "outcome": said,
                     "position": position, "entry": _num(response.get("entry_index")),
                     "closed_by": None, "closed_at": None, "realized": None,
                     "live_status": None, "current_index": None, "unrealized": None,
                     "live_value": None, "live_at": None, "series": []}
            if said == "accepted" and position:
                opener_of[position] = {"room": room, "trade": trade}
            if room in panels:
                panels[room]["trades"].append(trade)
        place(room, {"kind": "leg", "id": tid, "at": intent.get("at"),
                     "text": text, "outcome": said}, intent.get("at"), 0)
    for panel in panels.values():
        done = [t for t in panel["trades"] if t["outcome"] == "accepted"]
        closed = [t["realized"] for t in done if t["realized"] is not None]
        panel.update(staked=sum(t["usdc"] or 0.0 for t in done),
                     unclosed=sum(1 for t in done if not t["closed_by"]),
                     realized=round(sum(closed), 6) if closed else None)

    clone_rows = store.records("clones.jsonl")
    bots: dict[str, dict] = {}
    for cid, intent, outcome in _orders(clone_rows):
        said = (outcome or {}).get("outcome")
        kind = intent.get("kind")
        response = _response_of(outcome)
        if not kind:
            nexus_id = (intent.get("nexus") or {}).get("id")
            room = linked.get(cid) or by_origin.get(nexus_id) or store.GENERAL
            name = response.get("name") or intent.get("custom_name")
            source = response.get("source_name") or intent.get("source_type")
            if said == "accepted":
                result = ""
            elif said == "not_sent":
                result = f" · not sent: {(outcome or {}).get('error')}"
            else:
                result = f" · {_said(outcome)}"
            text = (f"{cid} · clone {source} as \"{name}\""
                    + (", paper" if intent.get("paper") else "") + result)
            instance = (outcome or {}).get("clone_instance_id")
            if said == "accepted" and instance:
                bot = {"id": cid, "at": intent.get("at"), "name": name,
                       "source": response.get("source_name"),
                       "symbol": response.get("source_symbol"),
                       "strategy": response.get("strategy_type"),
                       "risk": response.get("risk_profile"),
                       "paper": (outcome or {}).get("is_paper", intent.get("paper")),
                       "instance": instance, "funded": 0.0, "trading": None,
                       "balance": None, "pnl": None, "trades": None,
                       "win_rate": None, "sampled_at": None, "samples": [],
                       "locked": None, "available": None, "config": None,
                       "activity": []}
                bots[instance] = {"room": room, "bot": bot, "marks": [
                    (str(intent.get("at") or ""), (outcome or {}).get("is_trading"))]}
                if room in panels:
                    panels[room]["clones"].append(bot)
        else:
            owner = bots.get(intent.get("instance_id"))
            room = linked.get(cid) or (owner["room"] if owner else store.GENERAL)
            if kind == "fund":
                balance = response.get("bot_balance")
                text = f"{cid} · fund {_amount(intent.get('amount'))} USDC"
                if said != "accepted":
                    text += f" · {_said(outcome)}"
                else:
                    if balance is not None:
                        text += f" · bot balance {_amount(balance)}"
                    if owner:
                        owner["bot"]["funded"] += _num(intent.get("amount")) or 0.0
            elif kind in ("enable", "disable"):
                switched = "on" if kind == "enable" else "off"
                text = f"{cid} · trading switched {switched}"
                if said != "accepted":
                    text += f" · {_said(outcome)}"
                elif owner:
                    owner["marks"].append((str(intent.get("at") or ""),
                                           kind == "enable"))
            else:
                text = f"{cid} · {kind} · {_said(outcome)}"
        place(room, {"kind": "leg", "id": cid, "at": intent.get("at"),
                     "text": text, "outcome": said}, intent.get("at"), 0)

    # The bot's readings: the old ones clone.py watch left in clones.jsonl and
    # the console sampler's in samples.jsonl, one series in time order.
    readings = [r for r in clone_rows if r.get("type") == "sample"] + [
        r for r in sampled if r.get("type") == "sample" and r.get("kind") == "bot"]
    for row in sorted(readings, key=lambda r: str(r.get("at") or "")):
        owner = bots.get(row.get("instance_id"))
        if owner is None:
            continue
        reading = {"at": row.get("at"), "balance": _num(row.get("balance_usdc")),
                   "pnl": _num(row.get("total_profit_usdc")),
                   "trades": row.get("trades_executed"),
                   "trading": row.get("is_trading")}
        owner["bot"]["samples"].append(reading)
        owner["bot"].update(balance=reading["balance"], pnl=reading["pnl"],
                            trades=reading["trades"],
                            win_rate=_num(row.get("win_rate")),
                            sampled_at=reading["at"])
        if "locked_usdc" in row:
            owner["bot"].update(locked=_num(row.get("locked_usdc")),
                                available=_num(row.get("available_usdc")))
        owner["marks"].append((str(row.get("at") or ""), row.get("is_trading")))
    # What only the sampler reads: the bot's configuration and its own trades,
    # each as the newest version on record.
    newest_trade: dict[str, dict] = {}
    for row in sampled:
        owner = bots.get(row.get("instance_id"))
        if owner is None:
            continue
        if row.get("type") == "config":
            owner["bot"]["config"] = {k: row.get(k) for k in (
                "strategy_type", "risk_profile", "primary_indicators",
                "secondary_indicators", "execution_class")}
        elif row.get("type") == "trade" and row.get("trade_id"):
            newest_trade[row["trade_id"]] = row
    for row in newest_trade.values():
        bots[row["instance_id"]]["bot"]["activity"].append(
            {k: row.get(k) for k in ("trade_id", "symbol", "side", "trade_type",
                                     "amount_usdc", "profit_usdc", "is_closed",
                                     "exit_reason", "executed_at", "closed_at")})
    # Switched on at one moment and stopped by itself at a later one: the
    # newest reading of whether it trades is the one that is true.
    for owner in bots.values():
        known = [mark for mark in owner["marks"] if mark[1] is not None]
        if known:
            owner["bot"]["trading"] = max(known, key=lambda mark: mark[0])[1]
        owner["bot"]["activity"].sort(key=lambda a: str(a.get("executed_at") or ""),
                                      reverse=True)

    # Each of our positions as the sampler last read it, and its card's index.
    live_positions: dict[str, dict] = {}
    index_points: dict[str, dict] = {}
    for row in sampled:
        if row.get("type") == "sample" and row.get("kind") == "position":
            live_positions[row.get("position_id")] = row
        elif row.get("type") == "index" and row.get("card_id"):
            points = index_points.setdefault(row["card_id"], {})
            for point in row.get("points") or []:
                if isinstance(point, list) and len(point) == 2:
                    points[str(point[0])] = _num(point[1])
    for panel in panels.values():
        for trade in panel["trades"]:
            live = live_positions.get(trade["position"])
            if live:
                trade.update(live_status=live.get("status"),
                             current_index=_num(live.get("current_index")),
                             unrealized=_num(live.get("unrealized_pnl_usdc")),
                             live_value=_num(live.get("current_value_usdc")),
                             live_at=live.get("at"))
            points = index_points.get(trade["card"]) or {}
            trade["series"] = [[t, points[t]] for t in sorted(points)][-400:]

    # Nexus's proposal under what was done, and each card by what it holds.
    plans = store.plans(stored)
    described: dict[str, dict] = {}
    for row in sampled:
        if row.get("type") == "card" and row.get("card_id"):
            described[row["card_id"]] = row
    answered_at = {q["id"]: q["answer"].get("at") for q in derived if q.get("answer")}
    # [operator 2026-09-20, N-0035] "kde je prehled vubec o nejakych
    # backtestech? prece nez se spusti strategie tak se rikalo ze backtstry
    # maji byt slibne". The decision exists per (answer, card) as a `gate`
    # row -- qa.lab.note_gate -- so the room can show what was measured before
    # it opened, or say plainly that nothing was. Today nothing was: the
    # register holds 334 backtests and not one gate row, because every room
    # here was opened before that brake existed.
    decided = lab_gates()
    for s in opened:
        _lay_out(panels[s["id"]], plans.get(s["id"]) or {}, described, index_points,
                 answered_at.get(s.get("origin")))
        panel = panels[s["id"]]
        origin = str(s.get("origin") or "")
        panel["backtests"] = [
            {"card": leg.get("card"), "title": leg.get("card_title"),
             **{k: decided[(origin, str(leg.get("card")))].get(k)
                for k in ("verdict", "period", "return_pct", "sharpe",
                          "drawdown_pct", "why")}}
            for leg in panel.get("legs") or []
            if (origin, str(leg.get("card"))) in decided]

    for row in stored:
        kind = row.get("type")
        if kind not in store.NOTE_TYPES or row.get("id") in inside:
            continue
        message = {"kind": kind, "id": row.get("id"), "at": row.get("at"),
                   "text": row.get("text") or "", "re": row.get("re")}
        if kind == "operator_note":
            message["read"] = store.is_read(row, marks)
        place(row.get("room") or store.GENERAL, message, row.get("at"), 0)

    for thread in threads.values():
        thread.sort(key=lambda m: order[id(m)])

    waiting = store.unread(stored)

    # The newest reason each room gave for its state, so a stopped room says
    # why on its own card (N-0050, 2026-09-22: "musím rozkliknout").
    reasons: dict[str, str] = {}
    for row in sorted((r for r in stored if r.get("type") == "status"),
                      key=lambda r: str(r.get("at") or "")):
        reasons[row.get("room")] = str(row.get("why") or "")

    def entry(room: str, title: str, kind: str, origin, status) -> dict:
        thread = threads[room]
        panel = panels.get(room) or {}
        return {"id": room, "title": title, "kind": kind, "origin": origin,
                "status": status, "why": reasons.get(room, ""),
                "messages": len(thread),
                "last_at": max((m["at"] for m in thread if m.get("at")),
                               default=None),
                "unread_by_claude": sum(
                    1 for r in waiting if (r.get("room") or store.GENERAL) == room),
                # What the strip across the top says of it, at a glance.
                **{k: panel.get(k) for k in ("holds", "pnl", "pnl_pct", "invested",
                                             "proposed_share", "if_bought_pct",
                                             "criterion", "verdict")}}

    # The paper account as the newest order of ours read it afterwards. Live
    # figures are the sampler's (docs/nexus-rooms-plan.md, P4), not these.
    book = max((r for r in paper if r.get("type") == "after"),
               key=lambda r: str(r.get("at") or ""), default=None) or {}
    # The scoreboard: every experiment, best first, with what it was accepted
    # on and what it came to. This is the answer to "which of his strategies
    # actually made money", which is the whole question the laboratory exists
    # to answer -- and nothing on this page said it before 2026-09-12.
    scoreboard = []
    for s in opened:
        panel = panels[s["id"]]
        said = panel.get("verdict") or {}
        scoreboard.append({
            "room": s["id"], "title": titles[s["id"]],
            "status": panel.get("status"),
            "verdict": said.get("verdict"),
            "return_pct": said.get("return_pct"),
            "benchmark_pct": said.get("benchmark_pct"),
            "drawdown_pct": said.get("max_drawdown_pct"),
            "pnl": panel.get("pnl"), "pnl_pct": panel.get("pnl_pct"),
            "criterion": panel.get("criterion"),
            "claim": panel.get("claim")})
    scoreboard.sort(key=lambda row: (
        row["return_pct"] is None, -(row["return_pct"] or 0)))

    general = {**_nexus_summary(derived), "strip": [q["outcome"] for q in derived],
               "balance": _num(book.get("sim_balance_usdc")),
               "notional": _num(book.get("notional_usdc")),
               "book_trades": book.get("sim_total_trades"),
               "balance_at": book.get("at"), "scoreboard": scoreboard, **sampler}
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rooms": [entry(store.GENERAL, "General", "general", None, None)]
            + [entry(s["id"], titles[s["id"]], "strategy", s.get("origin"),
                     panels[s["id"]]["status"]) for s in opened],
            "threads": threads,
            "panels": {store.GENERAL: general, **panels}}


def _fomo_stats() -> dict | None:
    """FOMO Radar's `hot` signal, measured: does it predict a memecoin
    moving? Local diary only -- `scripts/fomo_watch.py` is what calls their
    API. None when the diary has never been written, so the page can tell
    "never watched" from "watched and found nothing"."""
    from qa.state import state_dir

    path = state_dir() / "fomo_signals.jsonl"
    if not path.is_file():
        return None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)

    from qa.fomo import basket, curves, stats

    # The curves are what the page DRAWS; the stats are what it concludes.
    # Both, because a hit rate without the shape hides a coin that ran 900%
    # in hour three and gave it back by six.
    #
    # And the basket, which is what the operator asked the page to lead with:
    # what an equal stake in every signal would be worth. `curves` is trimmed
    # HERE rather than inside, so the page can say how many it is not showing
    # -- it draws the forty biggest movers, and a table of winners that does
    # not say it is a table of winners is the whole of "looks too promising".
    drawn = curves(rows, limit=None)
    return {**stats(rows), "basket": basket(rows), "curves": drawn[:40],
            "curves_total": len(drawn)}


def _lab_script():
    spec = importlib.util.spec_from_file_location(
        "lab_for_page", REPO_ROOT / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_lab(now=None) -> dict:
    """What the page draws on load: the report, rewritten now, and the memecoin
    measurement. The rooms are not in it -- they arrive by /rooms.json and
    redraw on their own event, so a note being typed is never reloaded away."""
    return {"report": _lab_script().write_report(now),
            "channel": _nexus_channel(),
            "stats": {"fomo": _fomo_stats()}}


def render_lab(data: dict | None = None) -> str:
    data = data if data is not None else build_lab()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", blob)


TEMPLATE = r"""<!doctype html>
<html lang="cs">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Laboratoř</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
[hidden] { display: none !important; }

:root {
  --bg:#f6f7f6; --surface:#ffffff; --surface-2:#eef1f0; --line:#d5dbd9;
  --line-soft:#e6eae9; --text:#10171a; --text-dim:#5a6a6c; --text-faint:#8b9a9b;
  --accent:#0d6b66; --accent-dim:#0d6b6622;
  --ok:#17803d;   --ok-bg:#17803d1f;
  --auth:#0e7490; --auth-bg:#0e74901f;
  --warn:#9a6300; --warn-bg:#9a63001f;
  --bad:#b3261e;  --bad-bg:#b3261e1f;
  --wait:#6b3fc4; --wait-bg:#6b3fc41f;
  --none:#9aa8a8; --none-bg:#9aa8a826;
  --radius:7px;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#0c1214; --surface:#121b1d; --surface-2:#182326; --line:#243436;
    --line-soft:#1b282a; --text:#e4ecea; --text-dim:#93a5a5; --text-faint:#6a7b7c;
    --accent:#4ecfc4; --accent-dim:#4ecfc422;
    --ok:#4ec97a; --ok-bg:#4ec97a1f; --auth:#45b8d6; --auth-bg:#45b8d61f;
    --warn:#e0a338; --warn-bg:#e0a3381f; --bad:#f2685e; --bad-bg:#f2685e1f;
    --wait:#a98cf0; --wait-bg:#a98cf01f; --none:#647476; --none-bg:#64747626;
  }
}
:root[data-theme="dark"] {
  --bg:#0c1214; --surface:#121b1d; --surface-2:#182326; --line:#243436;
  --line-soft:#1b282a; --text:#e4ecea; --text-dim:#93a5a5; --text-faint:#6a7b7c;
  --accent:#4ecfc4; --accent-dim:#4ecfc422;
  --ok:#4ec97a; --ok-bg:#4ec97a1f; --auth:#45b8d6; --auth-bg:#45b8d61f;
  --warn:#e0a338; --warn-bg:#e0a3381f; --bad:#f2685e; --bad-bg:#f2685e1f;
  --wait:#a98cf0; --wait-bg:#a98cf01f; --none:#647476; --none-bg:#64747626;
}

* { box-sizing:border-box; }
body {
  margin:0; background:var(--bg); color:var(--text); font-family:var(--sans);
  font-size:16.5px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1240px; margin:0 auto; padding:32px 22px 80px; }

.mast { border-bottom:2px solid var(--text); padding-bottom:14px; }
.mast h1 {
  font-size:clamp(26px,4vw,38px); font-weight:600; letter-spacing:-0.022em;
  margin:0 0 4px; text-wrap:balance;
}
.mast .sub { color:var(--text-dim); font-size:16.0px; max-width:70ch; margin:0; }
.meta {
  display:flex; flex-wrap:wrap; gap:6px 20px; margin-top:14px;
  font-family:var(--mono); font-size:13.0px; color:var(--text-faint);
}
.meta b { color:var(--text-dim); font-weight:500; }

.blurb { font-size:14.1px; color:var(--text-dim); margin:0; line-height:1.5; }
.live {
  font-family:var(--mono); font-size:12px; color:var(--text-faint);
  display:inline-flex; align-items:center; gap:6px;
}
.live i { width:7px; height:7px; border-radius:50%; background:var(--text-faint); }
.live.on i { background:var(--ok); }
.live.off i { background:var(--warn); }
.meta a { color:var(--accent); text-decoration:none; }
h2.group {
  font-size:13.5px; text-transform:uppercase; letter-spacing:0.13em;
  font-weight:700; margin:38px 0 3px; display:flex; align-items:center; gap:10px;
}
.tab-n { background:var(--accent); color:var(--surface); border-radius:9px;
  padding:0 .45rem; font-size:.75em; font-weight:600; letter-spacing:0; }

/* ---------- the four products ----------
   One card each, the same four every time, so a product with nothing to say
   is visibly empty rather than missing. The number is the net return after
   costs; under it how many experiments it stands on, and how sure that is --
   no band under five, because two coins are not a measurement. */
.lab-products { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
  gap:14px; margin:26px 0 12px; }
.lab-p { background:var(--surface); border:1px solid var(--line); border-radius:12px;
  padding:16px 18px 15px; display:flex; flex-direction:column; gap:4px; min-width:0; }
.lab-p h3 { margin:0; font-size:13px; text-transform:uppercase; letter-spacing:.08em;
  color:var(--text-dim); }
.lab-big { font-size:40px; font-weight:700; line-height:1.15;
  font-variant-numeric:tabular-nums; }
.lab-big.up { color:var(--ok); } .lab-big.down { color:var(--bad); }
.lab-big.none { color:var(--text-faint); }
.lab-sub { font-size:13.5px; color:var(--text-dim); }
.lab-band { font-size:13.5px; }
.lab-band.thin { color:var(--text-faint); }
.lab-best { font-size:13px; color:var(--text-faint); overflow-wrap:anywhere; }
.lab-nexus { margin:6px 0 0; font-size:15px; color:var(--text-dim); }
.lab-nexus b { color:var(--text); font-variant-numeric:tabular-nums; }
/* The rooms: a strip of named strategies across the top; under it the chat
   with Nexus on the left and, beside it, the strategy's numbers, chart and
   configuration. The page takes the whole width (the console keeps its
   column), and both columns scroll on their own, so the
   composer is always under the thread and never over it -- it once floated
   over it, sticky, and the operator said so. Ours and the operator's messages
   sit on the right like any chat, Nexus on the left. Every class is nx- so
   nothing here can restyle the findings' own conversation. */
.wrap{max-width:none;padding-left:28px;padding-right:28px}

/* ---------- the Memecoiny tab ----------------------------------------
   Green up, red down, and big enough to read from across the desk. The
   operator asked twice; the first answer was the last block of another tab
   in the same grey as everything else. */
.mc-up{color:var(--ok);font-weight:700}
.mc-down{color:var(--bad);font-weight:700}
.mc-flat{color:var(--text-faint)}

.mc-top{margin:4px 0 26px}
.mc-top h2{margin:0 0 6px;font-size:26px;letter-spacing:-.2px}
.mc-top .blurb{max-width:70ch;margin-top:10px}
.mc-count{font-size:40px;font-weight:700;line-height:1.1;color:var(--text)}
.mc-count span{font-size:14px;font-weight:400;color:var(--text-dim);
  margin-left:10px;letter-spacing:0}

.mc-grid{display:grid;gap:16px;margin-bottom:30px;
  grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.mc-card{background:var(--surface);border:1px solid var(--line);
  border-radius:var(--radius);padding:20px 22px}
.mc-h{font-size:13px;text-transform:uppercase;letter-spacing:.6px;
  color:var(--text-dim)}
.mc-big{font-size:48px;font-weight:800;line-height:1.15;margin:8px 0 2px;
  letter-spacing:-1px}
.mc-sub{font-size:13px;color:var(--text-dim)}
.mc-figs{display:flex;gap:26px;margin:16px 0 0;padding-top:14px;
  border-top:1px solid var(--line-soft)}
.mc-figs dt{font-size:12px;color:var(--text-dim);margin:0}
.mc-figs dd{margin:2px 0 0;font-size:19px;font-weight:600}

.mc-figs .mc-of{font-size:12px;color:var(--text-dim);font-weight:400}
.mc-list{width:100%;border-collapse:collapse;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.mc-list th{text-align:left;font-size:12px;text-transform:uppercase;
  letter-spacing:.5px;color:var(--text-dim);font-weight:600;
  padding:11px 16px;border-bottom:1px solid var(--line)}
.mc-list th:nth-child(3),.mc-list th:nth-child(4){text-align:right}
.mc-list td{padding:10px 16px;border-bottom:1px solid var(--line-soft);
  font-size:16px;vertical-align:middle}
.mc-list tr:last-child td{border-bottom:0}
.mc-list tr:hover td{background:var(--surface-2)}
.mc-g{width:170px;padding-right:18px!important}
.mc-spark{display:block;width:150px;height:30px;overflow:visible}
.mc-spark .mc-pt{cursor:crosshair}
.mc-tip{position:fixed;z-index:60;pointer-events:none;
  background:var(--surface);border:1px solid var(--line);
  border-radius:10px;padding:8px 14px;
  box-shadow:0 8px 26px rgba(0,0,0,.45);white-space:nowrap}
.mc-tip .mc-th{font-size:12px;color:var(--text-dim);letter-spacing:.4px;
  text-transform:uppercase}
.mc-tip .mc-tv{font-size:26px;font-weight:800;line-height:1.15;
  font-variant-numeric:tabular-nums}
.mc-table{margin:0 0 26px}
.mc-table h3{font-size:15px;margin:0 0 10px;color:var(--text-dim);
  font-weight:600}
.mc-table table{width:100%;border-collapse:collapse;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.mc-table th{text-align:left;font-size:12px;text-transform:uppercase;
  letter-spacing:.5px;color:var(--text-dim);font-weight:600;
  padding:11px 16px;border-bottom:1px solid var(--line)}
.mc-table td{padding:12px 16px;border-bottom:1px solid var(--line-soft);
  font-size:16px}
.mc-table tr:last-child td{border-bottom:0}
.mc-sym{font-weight:600}
.mc-conv{color:var(--text-dim);font-variant-numeric:tabular-nums}
.mc-ret{text-align:right;font-size:20px;font-variant-numeric:tabular-nums}
.nx-strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;margin:18px 0 16px}
.nx-card{position:relative;display:flex;flex-direction:column;gap:5px;min-width:0;text-align:left;padding:12px 15px 13px;border:1px solid var(--line);border-radius:12px;background:var(--surface);color:var(--text);font:inherit;cursor:pointer}
.nx-card:hover{border-color:var(--text-faint)}
.nx-card.on{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.nx-card-top{display:flex;align-items:center;gap:8px;min-width:0;font-size:12.5px;color:var(--text-dim);white-space:nowrap;overflow:hidden}
.nx-card-name{font-size:17px;font-weight:600;line-height:1.25;overflow-wrap:anywhere}
.nx-card-num{font-size:15px;font-weight:600;color:var(--text-dim)}
.nx-card-why{font-size:12px;line-height:1.3;color:var(--text-dim)}
.nx-card.nx-ended{opacity:.75;border-style:dashed}
.nx-badge{position:absolute;top:10px;right:12px;background:var(--accent);color:var(--surface);border-radius:9px;padding:0 .45rem;font-size:.75em;font-weight:600}
.nx-main{display:grid;grid-template-columns:minmax(360px,2fr) minmax(0,3fr);gap:18px;height:calc(100vh - 48px);min-height:680px}
.nx-chatcol{display:flex;flex-direction:column;min-width:0;min-height:0;border:1px solid var(--line);border-radius:12px;background:var(--surface);overflow:hidden}
.nx-chat{flex:1 1 auto;min-height:0;overflow-y:auto;padding:18px 18px 22px;display:flex;flex-direction:column;gap:14px}
.nx-compose{flex:none;display:flex;flex-direction:column;gap:6px;padding:12px 14px;border-top:1px solid var(--line);background:var(--surface-2)}
.nx-compose textarea{width:100%;box-sizing:border-box;resize:vertical;min-height:3.2em;font:inherit;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:.5rem .65rem}
.nx-send{display:flex;justify-content:space-between;align-items:center;gap:.6rem;font-size:.8em;color:var(--text-dim)}
.nx-send button{font:inherit;font-size:1.15em;padding:.3rem .9rem;border-radius:6px;border:1px solid var(--wait);background:var(--wait);color:var(--surface);cursor:pointer}
.nx-send button:disabled{opacity:.5;cursor:default}
.nx-panel{min-width:0;min-height:0;overflow-y:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:22px 26px 26px}
@media (max-width:1100px){.nx-main{grid-template-columns:1fr;height:auto}.nx-chatcol{height:75vh}.nx-panel{overflow:visible}}
.nx-note{margin-top:14px;padding:.7rem .9rem;border:1px dashed var(--line);border-radius:var(--radius);color:var(--text-dim)}
.nx-msg{border:1px solid var(--line);border-radius:14px;padding:.75rem .95rem;background:var(--surface);max-width:min(52rem,90%);align-self:flex-start}
.nx-msg.nx-ours{align-self:flex-end;background:var(--accent-dim);border-color:var(--accent)}
.nx-msg.nx-op{align-self:flex-end;background:var(--wait-bg);border-color:var(--wait)}
.nx-msg.nx-cl{background:var(--surface-2)}
.nx-msg.nx-sys{align-self:center;max-width:92%;border:none;background:none;padding:0 1rem;color:var(--text-faint);font-size:.8em;text-align:center}
.nx-msg.nx-failed,.nx-msg.nx-refused{border-color:var(--bad)}
.nx-msg.nx-partial,.nx-msg.nx-waiting{border-color:var(--warn)}
.nx-h{font-size:.78em;color:var(--text-dim);margin-bottom:.4rem}
.nx-h b{color:var(--text);font-weight:600}
.nx-s{font-size:.85em;color:var(--text-dim);font-style:italic}
.nx-b{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}
.nx-b.nx-clamp{max-height:9.5em;overflow:hidden;-webkit-mask-image:linear-gradient(#000 65%,transparent);mask-image:linear-gradient(#000 65%,transparent)}
.nx-b code{font-family:var(--mono);font-size:.9em;background:var(--surface-2);padding:0 .2em;border-radius:3px}
.nx-more{margin-top:.35rem;background:none;border:none;color:var(--accent);cursor:pointer;font:inherit;font-size:.82em;padding:0}
.nx-tick{color:var(--ok);margin-left:.3rem}
.nx-st{font-weight:700}
.nx-st.nx-running{color:var(--ok)}
.nx-st.nx-paused{color:var(--warn)}
.nx-st.nx-stopped{color:var(--bad)}
.nx-st.nx-proposed{color:var(--text-dim)}
.nx-gist{margin:.1rem 0 .5rem;padding:.45rem .65rem;border-left:3px solid var(--accent);background:var(--surface-2);border-radius:0 6px 6px 0;font-size:.95em;line-height:1.45}
.nx-gist span{display:block;font-size:.72em;color:var(--text-dim);margin-bottom:.1rem}
.nx-opened{margin-top:.35rem;font-size:.8em}
.nx-goto{background:none;border:none;color:var(--accent);cursor:pointer;font:inherit;padding:0;text-decoration:underline}
.nx-leg.nx-no{color:var(--bad)}
.nx-hero{display:flex;flex-wrap:wrap;align-items:center;gap:10px 12px}
.nx-hero h2{margin:0;font-size:26px;font-weight:600;letter-spacing:-.01em;line-height:1.2;overflow-wrap:anywhere}
.nx-sub{margin:6px 0 0;font-size:13px;color:var(--text-faint)}
.nx-pill{display:inline-flex;align-items:center;gap:6px;padding:3px 11px;border-radius:999px;background:var(--surface-2);color:var(--text-dim);font-size:13px;font-weight:600;white-space:nowrap}
.nx-pill.nx-running{background:var(--ok-bg);color:var(--ok)}
.nx-pill.nx-paused{background:var(--warn-bg);color:var(--warn)}
.nx-pill.nx-stopped{background:var(--bad-bg);color:var(--bad)}
/* [operator 2026-09-20, N-0035] "Vice barev pouyivej pro tagz jako Bot Cards":
   what a room HOLDS is the thing they scan the strip for, and it was the one
   pill with no colour at all. */
.nx-pill.nx-holds-bot{background:rgba(139,111,232,.20);color:#c3b4ff}
.nx-pill.nx-holds-cards{background:rgba(72,150,232,.20);color:#9ecbff}
.nx-pill.nx-trading-on{background:var(--ok-bg);color:var(--ok)}
.nx-pill.nx-trading-off{background:var(--surface-2);color:var(--text-dim)}
.nx-gist{margin:0;font-size:16px;line-height:1.45;font-weight:600}
.nx-more{margin-top:8px}
.nx-more>summary{cursor:pointer;color:var(--text-dim);font-size:13px;
  font-weight:600;list-style:none;user-select:none}
.nx-more>summary::-webkit-details-marker{display:none}
.nx-more>summary::before{content:"▸ ";color:var(--text-dim)}
.nx-more[open]>summary::before{content:"▾ "}
.nx-more>summary:hover{color:var(--text)}
.nx-cap{margin:-2px 0 10px}
.nx-table.nx-bt .nx-tr{grid-template-columns:2fr 1.2fr .8fr .8fr .8fr}
.nx-card-top .nx-pill{padding:1px 8px;font-size:12px}
.nx-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 4px}
.nx-tile{min-width:0;padding:13px 15px;border-radius:10px;background:var(--surface-2)}
.nx-tile span{display:block;font-size:12.5px;color:var(--text-dim)}
.nx-tile b{display:block;margin-top:2px;font-size:26px;font-weight:600;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nx-tile i{display:block;margin-top:2px;font-style:normal;font-size:12.5px;color:var(--text-faint)}
.nx-up{color:var(--ok)}
.nx-down{color:var(--bad)}
.nx-warn{color:var(--warn)}
.nx-sec{margin:28px 0 8px;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-faint)}
.nx-table{font-size:14px}
.nx-tr{display:grid;gap:10px;align-items:center;padding:9px 0;border-top:1px solid var(--line-soft)}
.nx-tr > *{min-width:0;overflow-wrap:anywhere}
.nx-tr small{display:block;font-size:12px;color:var(--text-faint)}
.nx-th{border-top:none;padding-top:0;font-size:12.5px;color:var(--text-faint)}
.nx-legs .nx-tr{grid-template-columns:minmax(0,2.3fr) .8fr 1.2fr 1.5fr 1.3fr 1fr}
.nx-trades .nx-tr{grid-template-columns:minmax(0,1.4fr) .8fr .8fr 1.3fr 1.1fr}
.nx-orders .nx-tr{grid-template-columns:.9fr 1.1fr minmax(0,2.2fr) 1fr}
.nx-strats .nx-tr{grid-template-columns:minmax(0,1.8fr) .6fr 1fr .9fr 1fr 1.2fr}
.nx-state{font-size:13px;font-weight:600;color:var(--text-dim)}
.nx-state.nx-open{color:var(--ok)}
.nx-state.nx-card-closed{color:var(--text-faint)}
.nx-state.nx-card-not-found{color:var(--bad)}
.nx-dim{color:var(--text-faint)}
.nx-kv{display:flex;flex-wrap:wrap;gap:8px 28px;font-size:14px}
.nx-kv span{margin-right:6px;color:var(--text-faint)}
.nx-chips{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:10px}
.nx-chips > span{min-width:5.5rem;margin-right:4px;font-size:12.5px;color:var(--text-faint)}
.nx-chip{padding:3px 9px;border-radius:6px;border:1px solid var(--line-soft);background:var(--surface-2);font-family:var(--mono);font-size:12.5px}
.nx-ct{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:22px 0 4px;font-size:14px;font-weight:600}
.nx-ct small{font-size:12.5px;font-weight:400;color:var(--text-faint)}
.nx-chart{display:block;max-width:100%;height:auto;overflow:visible}
.nx-chart text{font-size:12px;fill:var(--text-dim)}
.nx-chart .nx-gl{stroke:var(--line-soft);stroke-width:1}
.nx-chart .nx-area{fill:var(--accent-dim);stroke:none}
.nx-chart .nx-line{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.nx-chart .nx-ref{stroke-width:1.5;stroke-dasharray:6 4}
.nx-chart .nx-ref-tp{stroke:var(--ok)}
.nx-chart .nx-ref-sl{stroke:var(--bad)}
.nx-chart .nx-ref-entry,.nx-chart .nx-ref-base{stroke:var(--text-dim);stroke-dasharray:2 4}
.nx-chart .nx-tp{fill:var(--ok)}
.nx-chart .nx-sl{fill:var(--bad)}
.nx-chart .nx-now{fill:var(--text);font-weight:600}
.nx-chart .nx-vl{stroke:var(--wait);stroke-width:1.5;stroke-dasharray:3 3}
.nx-chart .nx-vt{fill:var(--wait)}
.nx-chart .nx-dot{fill:var(--accent);stroke:var(--surface);stroke-width:2}
.nx-chart .nx-dot-open{fill:var(--surface);stroke:var(--accent);stroke-width:2}
.nx-chart .nx-dot-loss{fill:var(--bad);stroke:var(--surface);stroke-width:2}
/* Why a strategy stands where it does: under its name, above its numbers,
   coloured by where it stands, and every earlier move under it. */
.nx-status{margin:18px 0 4px;padding:14px 18px 13px;border-radius:10px;background:var(--surface-2);border-left:4px solid var(--accent)}
.nx-status.nx-paused{border-left-color:var(--warn);background:var(--warn-bg)}
.nx-status.nx-stopped{border-left-color:var(--bad);background:var(--bad-bg)}
.nx-status.nx-proposed{border-left-color:var(--text-faint)}
.nx-status h3{margin:0;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-dim)}
.nx-status>p{margin:6px 0 0;font-size:16px;line-height:1.55;white-space:pre-wrap}
.nx-moves{display:grid;gap:5px;margin:12px 0 0;padding-top:10px;border-top:1px solid var(--line-soft)}
.nx-moves p{margin:0;font-size:13.5px;line-height:1.5;color:var(--text-dim)}
.nx-moves b{font-weight:600}
/* A card's name opens the card itself on cymetica.com. */
.nx-link{color:inherit;text-decoration:none;border-bottom:1px dotted var(--text-faint)}
.nx-link:hover{color:var(--accent);border-bottom-color:var(--accent)}
.nx-out{font-size:.8em;color:var(--accent)}
.nx-foot{margin:12px 0 0;font-size:12.5px;color:var(--text-faint)}
.nx-stale b{color:var(--bad)}
.nx-pf{padding:0;border:none;background:none;color:var(--text);font:inherit;font-weight:600;text-align:left;cursor:pointer}
.nx-pf:hover{color:var(--accent)}

</style>

<div class="wrap" id="wrap">
  <header class="mast">
    <h1>Laboratoř</h1>
    <p class="sub">Co laborka s Nexusem vydělala, po nákladech. Jen papír,
    žádné skutečné peníze.</p>
    <div class="meta" id="meta"><a href="/">&larr; konzole</a>
      <span id="reportAt"></span></div>
  </header>

  <section class="lab-products" id="products" aria-label="Produkty"></section>
  <p class="lab-nexus" id="nexusLine"></p>

  <h2 class="group">Roomy <span class="tab-n" id="nexusN" hidden></span></h2>
  <section class="panel" id="panel-nexus">
  <div class="nx-note" id="roomsNote" hidden></div>
  <nav class="nx-strip" id="roomList" aria-label="Strategies"></nav>
  <div class="nx-main" id="nxMain">
    <div class="nx-chatcol">
      <div class="nx-chat" id="roomChat"></div>
      <form class="nx-compose" id="nxCompose" hidden>
        <textarea id="nxDraft" rows="2" maxlength="4000"
          placeholder="Your feedback for this room. Claude reads it when you ask."></textarea>
        <div class="nx-send"><span id="nxSendNote">Ctrl+Enter sends</span>
          <button type="submit" id="nxSend">Send</button></div>
      </form>
    </div>
    <aside class="nx-panel" id="roomPanel"></aside>
  </div>
  </section>


  <h2 class="group">Memecoiny do detailu</h2>
  <section class="panel" id="panel-memecoins">
  <div id="memecoins"></div>
  <div id="mcTip" class="mc-tip" hidden></div>
  </section>


</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const stamp = t => t ? String(t).replace("T", " ").slice(0, 16) : "";

// localStorage is a convenience here, never state: every read falls back to
// its default and every write may fail silently.
function readStore(key, dflt) {
  try { const v = localStorage.getItem(key); return v === null ? dflt : v; }
  catch (_) { return dflt; }
}
function writeStore(key, value) {
  try { localStorage.setItem(key, String(value)); } catch (_) {}
}

/* ---------- the four products, from state/lab/report.json ----------
   `lp.` is a product and `ln.` the Nexus line: named, so a test can hold
   every field read here against what qa/lab_report.py writes. */
const PRODUCT_NAMES = {cards: "Karty", bots: "Boti", memecoins: "Memecoiny",
                       funds: "Fondy"};
function labPct(v) {
  if (v == null) return "&mdash;";
  return (v > 0 ? "+" : "") + v.toFixed(2).replace(".", ",") + "&nbsp;%";
}
function labShare(v) { return Math.round(v * 100) + "&nbsp;%"; }
function labProduct(key, lp) {
  const tone = lp.net_pct == null ? "none" : (lp.net_pct > 0 ? "up" : "down");
  const band = lp.wilson
    ? `<div class="lab-band">vydělalo ${labShare(lp.wilson[0])}&ndash;${
        labShare(lp.wilson[1])} pokusů (95&nbsp;%)</div>`
    : `<div class="lab-band thin">${lp.wins} z ${lp.n} v plusu &middot; málo dat
        na jistotu (n&nbsp;&lt;&nbsp;${lp.min_n})</div>`;
  let sub, extra = "";
  if (key === "memecoins") {
    sub = `10&nbsp;$ do každého hot signálu, den držení, ${
      String(lp.fee_pct).replace(".", ",")}&nbsp;% za stranu &middot; ${lp.n} obchodů`;
    const fees = (lp.fees || []).filter(f => f.fee_pct !== lp.fee_pct)
      .map(f => `${String(f.fee_pct).replace(".", ",")}&nbsp;%: ${labPct(f.net_pct)}`);
    extra = `<div class="lab-best">${lp.could_buy_share == null ? ""
        : `stihli bychom ${labShare(lp.could_buy_share)} z ${lp.signals} signálů`}${
        fees.length ? " &middot; " + fees.join(", ") : ""}${
        lp.running ? ` &middot; ${lp.running} ještě nemá celý den` : ""}</div>`;
  } else {
    sub = `${lp.n} pokusů &middot; běží ${lp.running} &middot; v archivu ${lp.archived}`;
    if (lp.best) extra = `<div class="lab-best">nejlepší ${esc(lp.best.room)} ${
      esc((lp.best.title || "").slice(0, 40))} ${labPct(lp.best.net_pct)}</div>`;
  }
  return `<article class="lab-p"><h3>${PRODUCT_NAMES[key] || esc(key)}</h3>
    <div class="lab-big ${tone}">${labPct(lp.net_pct)}</div>
    <div class="lab-sub">${sub}</div>${band}${extra}</article>`;
}
function labNexus(ln, nch) {
  // How reliable he is, beside what came of it: the typical answer time is
  // taken only over questions watched from the start (_nexus_summary).
  // `nch.` is _nexus_channel(); `nc.` is taken, it is a bot in the rooms.
  const typical = nch && nch.median_seconds != null
    ? ` &middot; odpovídá typicky za <b>${Math.round(nch.median_seconds / 60)}&nbsp;min</b>
       (sledováno ${nch.measured}), selhalo ${nch.failed}, odmítl ${nch.refused}` : "";
  return `Nexus: <b>${ln.questions}</b> otázek &rarr; <b>${ln.answered}</b> odpovědí
    &rarr; <b>${ln.picks}</b> voleb &rarr; brána pustila <b>${ln.gate_pass}</b>
    z ${ln.gated} &rarr; přežilo <b>${ln.survived}</b>, vyvráceno ${ln.refuted}${typical}`;
}
(function products() {
  const R = D.report || {};
  const all = R.products || {};
  document.getElementById("products").innerHTML = ["cards", "bots", "memecoins", "funds"]
    .filter(k => all[k]).map(k => labProduct(k, all[k])).join("");
  if (R.nexus) document.getElementById("nexusLine").innerHTML = labNexus(R.nexus, D.channel);
  if (R.generated_at) document.getElementById("reportAt").textContent =
    "report " + R.generated_at.replace("T", " ").slice(0, 16) + " UTC";
})();

/* ---------- the Nexus tab: rooms, served beside the payload, never in it ----------
   The operator's notes and the sampler's rows land while a sweep may be
   running, and everything in D is written into the committed dashboard -- so
   the console serves the rooms at /rooms.json and says when they move with an
   event of its own. Opened as a file there is no console to ask, and the tab
   says so rather than showing an empty room as if nobody had said anything. */
const NX_LOCAL = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
let NX = null;

// Nexus writes markdown. Escape first, always, and only then turn a few marks
// back into tags of our own -- so nothing the vendor wrote can become markup.
function nxText(text) {
  let s = esc(text == null ? "" : text);
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
  s = s.replace(/^#{1,6} +(.+)$/gm, "<b>$1</b>");
  s = s.replace(/^[ \t]*[-*] +/gm, "• ");
  return s;
}
function nxSecs(s) {
  if (s == null) return "";
  if (s < 90) return Math.round(s) + " s";
  if (s < 5400) return Math.round(s / 60) + " min";
  return (s / 3600).toFixed(1) + " h";
}
const nxDigits = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
const NX_OUTCOME = {
  partial: "cut short — only an opening line came back",
  failed: "no answer — our loop gave up waiting",
  refused: "refused before an investigation started",
  waiting: "waiting for Nexus…",
};

// The tab names its own shapes -- `nm` a message, `nr` a room, `np` a panel,
// and inside a strategy's panel `nt` a trade, `nh` a change of status, `nc` a
// bot and `ns` one of its samples -- because `f.` and `m.` belong to the
// payload's field guard, and these arrive by fetch.
// tests/meta/test_pipeline_rooms.py holds each name against what
// build_rooms() writes, the same way that guard holds the payload.
const NX_STATUS = { proposed: "○", running: "●", paused: "‖", stopped: "■" };
function nxGlyph(status) {
  return '<span class="nx-st nx-' + esc(status || "proposed") + '">' +
    (NX_STATUS[status] || "○") + "</span>";
}
// Money the way the operator reads it: 10 000, 89 000.96, 0.00216, −50.
function nxMoney(v) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v), a = Math.abs(n);
  const parts = a.toFixed(a >= 1 || a === 0 ? 2 : 5).split(".");
  const tail = Number(parts[1]) ? "." + parts[1].replace(/0+$/, "") : "";
  return (n < 0 ? "−" : "") + nxDigits(parts[0]) + tail;
}
function nxShort(text, n) {
  const s = String(text == null ? "" : text);
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
// A way into another room, from a line in this one.
function nxGoto(room, label) {
  return '<button type="button" class="nx-goto" data-room="' + esc(room) + '">' +
    esc(label) + "</button>";
}
function nxBubble(nm, current) {
  const at = nm.at ? " · " + esc(stamp(nm.at)) : "";
  if (nm.kind === "question") {
    const opened = (nm.opened || []).map(room => room === current
      ? '<span class="nx-s">this room was opened from this answer</span>'
      : nxGoto(room, "→ it opened " + room)).join(" ");
    return '<div class="nx-msg nx-ours"><div class="nx-h"><b>Claude → Nexus</b>' + at +
      " · " + esc(nm.id) + '</div><div class="nx-b">' + nxText(nm.text) + "</div>" +
      (opened ? '<div class="nx-opened">' + opened + "</div>" : "") + "</div>";
  }
  if (nm.kind === "reply") {
    const text = nm.text || "";
    const took = nm.seconds != null ? " · " + nxSecs(nm.seconds)
               : (nm.upper != null && text ? " · ≤ " + nxSecs(nm.upper) : "");
    const note = NX_OUTCOME[nm.outcome];
    const long = text.length > 700;
    const label = "▾ whole answer (" + nxDigits(text.length) + " characters)";
    return '<div class="nx-msg nx-' + esc(nm.outcome || "answered") + '">' +
      '<div class="nx-h"><b>Nexus</b>' + at + took + "</div>" +
      (note ? '<div class="nx-s">' + esc(note) + "</div>" : "") +
      (nm.gist ? '<div class="nx-gist"><span>Claude · summary</span>' + nxText(nm.gist) +
                 "</div>" : "") +
      (text ? '<div class="nx-b' + (long ? " nx-clamp" : "") + '">' + nxText(text) + "</div>" : "") +
      (long ? '<button class="nx-more" type="button" data-label="' + esc(label) + '">' +
              esc(label) + "</button>" : "") +
      "</div>";
  }
  if (nm.kind === "operator_note") {
    return '<div class="nx-msg nx-op"><div class="nx-h"><b>You</b>' + at +
      ' <span class="nx-tick" title="' + (nm.read ? "read by Claude" : "saved, not read yet") +
      '">' + (nm.read ? "✓✓" : "✓") + '</span></div><div class="nx-b">' +
      nxText(nm.text) + "</div></div>";
  }
  if (nm.kind === "claude_note") {
    return '<div class="nx-msg nx-cl"><div class="nx-h"><b>Claude</b>' +
      (nm.re ? " · on " + esc(nm.re) : "") + at + '</div><div class="nx-b">' +
      nxText(nm.text) + "</div></div>";
  }
  if (nm.kind === "pointer") {
    return '<div class="nx-msg nx-sys">' + esc(nm.id) + at + " · asked in " +
      nxGoto(nm.room, nm.room + (nm.title ? " · " + nm.title : "")) + ": " +
      esc(nxShort(nm.text, 110)) + "</div>";
  }
  if (nm.kind === "status") {
    // One line in the thread; the whole reason is in the panel, folded.
    return '<div class="nx-msg nx-sys" title="' + esc(nm.text || "") + '">' +
      nxGlyph(nm.status) + " " + esc(nm.status || "") +
      (nm.text ? " — " + esc(nxShort(nm.text, 140)) : "") + at + "</div>";
  }
  if (nm.kind === "leg") {
    return '<div class="nx-msg nx-sys nx-leg' +
      (nm.outcome === "accepted" ? "" : " nx-no") + '">' + esc(nm.text || "") + at + "</div>";
  }
  return '<div class="nx-msg nx-sys">' + esc(nm.text || "") + "</div>";
}

// Where a strategy stands, as a word beside its name; the thread's status
// lines keep the bare glyph.
// [operator 2026-09-20, N-0034] "vubec se v tom detialu nevyznam, ma to byt
// uplne jednoduche pro degeny z co nejmin ctenim". So the words on this tab
// are Czech and short: it is the one surface in this console written for the
// operator rather than for the vendor, and they read Czech. Ids, card
// symbols and numbers are untouched -- those are the same in both languages.
const NX_WORD = { proposed: "Návrh", running: "Běží", paused: "Pauza",
                  stopped: "Stojí" };
const NX_HOLDS = { bot: "Bot", cards: "Karty" };
function nxPill(status) {
  const s = status || "proposed";
  return '<span class="nx-pill nx-' + esc(s) + '">' + (NX_STATUS[s] || "○") + " " +
    esc(NX_WORD[s] || s) + "</span>";
}
// Signed money and percentages the way the operator reads them -- +14.48,
// −50, +0.7 % -- and the class that colours them.
function nxSigned(v) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v);
  return (n > 0 ? "+" : "") + nxMoney(n);
}
function nxTone(v) {
  const n = Number(v);
  return v == null || v === "" || isNaN(n) || n === 0 ? "" : n > 0 ? " nx-up" : " nx-down";
}
function nxPct(v, digits) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v);
  const places = digits != null ? digits : Math.abs(n) >= 10 ? 0 : 1;
  const s = Math.abs(n).toFixed(places);
  return (Number(s) === 0 ? "" : n > 0 ? "+" : "−") + s + " %";
}
// A drawdown and a stop are magnitudes, not directions: their sign is in the
// word, not the number. nxPct puts a + in front of any positive figure, so
// "Propad +10.5 %" said a loss had gained, and "Stopka +10 %" said a stop-loss
// was a profit. Seen on the page 2026-09-21, the first night a room carried a
// backtest at all.
function nxMag(v, digits) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Math.abs(Number(v));
  const places = digits != null ? digits : n >= 10 ? 0 : 1;
  return n.toFixed(places) + " %";
}
function nxShare(v) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v) * 100;
  return (Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : n.toFixed(1)) + " %";
}
function nxLevel(v) {
  return v == null || v === "" || isNaN(Number(v)) ? "—" : Number(v).toFixed(2);
}
const NX_MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                  "Oct", "Nov", "Dec"];
// "11 Sep 10:25" -- UTC, like every other time on this page.
function nxDay(iso) {
  const d = new Date(iso || "");
  if (isNaN(d.getTime())) return "";
  return d.getUTCDate() + " " + NX_MONTH[d.getUTCMonth()] + " " +
    String(d.getUTCHours()).padStart(2, "0") + ":" +
    String(d.getUTCMinutes()).padStart(2, "0");
}
// How long until a card stops trading: "in 36 h", "in 3 d", "closed".
function nxUntil(iso) {
  const t = Date.parse(iso || "");
  if (!t) return null;
  const hours = (t - Date.now()) / 3600000;
  if (hours <= 0) return "skončila";
  if (hours < 1) return "za " + Math.max(1, Math.round(hours * 60)) + " min";
  if (hours < 48) return "za " + Math.round(hours) + " h";
  return "za " + Math.round(hours / 24) + " d";
}
// Four big numbers, each with its label above it and one quiet line under it.
function nxTiles(tiles) {
  return '<div class="nx-tiles">' + tiles.map(([label, value, sub, tone]) =>
    '<div class="nx-tile"><span>' + esc(label) + '</span><b class="' +
    (tone || "").trim() + '">' + esc(value == null ? "—" : String(value)) + "</b>" +
    (sub ? "<i>" + esc(String(sub)) + "</i>" : "") + "</div>").join("") + "</div>";
}
function nxHero(name, pills, sub) {
  return '<div class="nx-hero"><h2>' + esc(name) + "</h2>" + pills + "</div>" +
    (sub ? '<p class="nx-sub">' + sub + "</p>" : "");
}
// Where the console's sampler stands, said the same way in every panel: when
// it last read their API, and "stale" once three rounds have gone by without one.
function nxSampler(np) {
  if (!np.sampled_at) {
    return '<p class="nx-foot">Their API has not been read yet: the console reads it ' +
      "when it runs with --sample.</p>";
  }
  const failed = Object.entries(np.sampler_reads || {}).filter(([, verdict]) => verdict !== "ok");
  return '<p class="nx-foot' + (np.stale ? " nx-stale" : "") + '">' +
    (np.stale ? "<b>stale</b> — no round for over three intervals. " : "") +
    "Read from their API " + esc(stamp(np.sampled_at)) + " UTC, every " +
    esc(nxSecs(np.sampler_every)) +
    (np.sampler_ok === false ? " · failed: " +
      esc(failed.map(([door, verdict]) => door + " " + verdict).join(", ")) : "") + ".</p>";
}
function nxParams(params) {
  return Object.entries(params || {}).map(([k, v]) => k + " " + v).join(", ");
}

// Round numbers for an axis, three to five of them between lo and hi.
function nxTicks(lo, hi) {
  const raw = (hi - lo) / 4;
  if (!(raw > 0)) return [lo];
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= raw) || raw;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-6; v += step) {
    out.push(Number(v.toFixed(10)));
  }
  return out;
}
// Labels down the right edge of a chart, pushed apart so no two overlap.
function nxPlace(labels, top, bottom) {
  const sorted = labels.slice().sort((a, b) => a.y - b.y);
  let last = -Infinity;
  sorted.forEach(label => { label.y = Math.max(label.y, last + 15); last = label.y; });
  const over = sorted.length ? sorted[sorted.length - 1].y - bottom : 0;
  if (over > 0) sorted.forEach(label => { label.y -= over; });
  sorted.forEach(label => { label.y = Math.max(label.y, top); });
  return sorted;
}
// A line over time with levels across it -- a card's entry, Nexus's
// take-profit and stop -- each dashed and named at its right end, and the
// moment something happened as a mark. Drawn at the width of the panel it
// sits in, so its text is the size of the text around it. No library: the
// Stats tab draws the same way.
function nxChart(series, opts) {
  const o = opts || {};
  const pts = (series || []).map(p => [Date.parse(p[0]), Number(p[1])])
    .filter(p => isFinite(p[0]) && isFinite(p[1]));
  if (pts.length < 2) return "";
  const refs = (o.refs || []).filter(r => r && r.v != null && isFinite(Number(r.v)));
  const box = document.getElementById("roomPanel");
  const W = Math.max(360, Math.round((box && box.clientWidth ? box.clientWidth : 700) - 54));
  const H = 230, L = 52, R = 100, T = 14, B = 30;
  const values = pts.map(p => p[1]).concat(refs.map(r => Number(r.v)));
  let lo = Math.min(...values), hi = Math.max(...values);
  if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;
  const t0 = pts[0][0], t1 = pts[pts.length - 1][0], span = t1 - t0 || 1;
  const x = t => L + (t - t0) / span * (W - L - R);
  const y = v => T + (hi - v) / (hi - lo) * (H - T - B);
  const fmt = o.format || nxLevel;
  const r1 = n => n.toFixed(1);
  let svg = '<svg class="nx-chart" viewBox="0 0 ' + W + " " + H + '" width="' + W +
    '" height="' + H + '" role="img" aria-label="' + esc(o.label || "") + '">';
  // An axis of whole numbers reads 105, not 105.00.
  const ticks = nxTicks(lo, hi);
  const whole = ticks.every(v => Math.abs(v - Math.round(v)) < 1e-9);
  const tick = o.format ? fmt : v => (whole ? String(Math.round(v)) : nxLevel(v));
  ticks.forEach(v => {
    svg += '<line class="nx-gl" x1="' + L + '" x2="' + (W - R) + '" y1="' + r1(y(v)) +
      '" y2="' + r1(y(v)) + '"/><text x="' + (L - 8) + '" y="' + r1(y(v) + 4) +
      '" text-anchor="end">' + esc(tick(v)) + "</text>";
  });
  const line = pts.map(p => r1(x(p[0])) + "," + r1(y(p[1]))).join(" ");
  svg += '<path class="nx-area" d="M' + r1(x(t0)) + "," + (H - B) + " L" +
    line.split(" ").join(" L") + " L" + r1(x(t1)) + "," + (H - B) + ' Z"/>';
  const labels = [];
  refs.forEach(r => {
    const at = y(Number(r.v));
    svg += '<line class="nx-ref nx-ref-' + esc(r.kind) + '" data-ref="' + esc(r.kind) +
      '" x1="' + L + '" x2="' + (W - R) + '" y1="' + r1(at) + '" y2="' + r1(at) + '"/>';
    labels.push({ y: at + 4, text: r.label, cls: "nx-" + r.kind });
  });
  if (o.vline && isFinite(Date.parse(o.vline.t))) {
    const at = Date.parse(o.vline.t);
    if (at >= t0 && at <= t1) {
      svg += '<line class="nx-vl" x1="' + r1(x(at)) + '" x2="' + r1(x(at)) + '" y1="' + T +
        '" y2="' + (H - B) + '"/><text class="nx-vt" x="' +
        r1(Math.min(x(at) + 5, W - R - 96)) + '" y="' + (T + 11) + '">' +
        esc(o.vline.label || "") + "</text>";
    }
  }
  svg += '<polyline class="nx-line" points="' + line + '"/>';
  (o.marks || []).forEach(mark => {
    const at = Date.parse(mark.t);
    if (!isFinite(at) || at < t0 || at > t1 || mark.v == null) return;
    svg += '<circle class="nx-dot-' + esc(mark.kind || "open") + '" cx="' + r1(x(at)) +
      '" cy="' + r1(y(Number(mark.v))) + '" r="4.5"><title>' + esc(mark.title || "") +
      "</title></circle>";
  });
  const last = pts[pts.length - 1];
  svg += '<circle class="nx-dot" cx="' + r1(x(last[0])) + '" cy="' + r1(y(last[1])) +
    '" r="5"/>';
  labels.push({ y: y(last[1]) + 4, text: "teď " + fmt(last[1]), cls: "nx-now" });
  nxPlace(labels, T + 8, H - B).forEach(label => {
    svg += '<text class="' + label.cls + '" x="' + (W - R + 8) + '" y="' + r1(label.y) +
      '">' + esc(label.text) + "</text>";
  });
  [0, 1 / 3, 2 / 3, 1].forEach((k, i) => {
    const at = t0 + span * k;
    svg += '<text x="' + r1(x(at)) + '" y="' + (H - 8) + '" text-anchor="' +
      (i === 0 ? "start" : i === 3 ? "end" : "middle") + '">' +
      esc(nxDay(new Date(at).toISOString())) + "</text>";
  });
  return svg + "</svg>";
}

// A strategy's cards: Nexus's plan with what was done laid over it. An event
// card is a piece of news, so a leg is named by its headline, and the basket
// its index tracks sits under that, quietly. A card their API does not know is
// said to be one: an id means nothing to the operator.
function nxLegName(nl) {
  if (nl.state === "card not found") return "Karta, která neexistuje";
  return nl.card_title ? nxShort(nl.card_title, 64) : nl.label || "Kartu jsme ještě nečetli";
}
function nxLegNote(nl) {
  if (nl.state === "card not found") return "Nexus si ji vymyslel, jejich API na ni vrací 404";
  return nl.label ? "sleduje: " + nl.label : "";
}
// The payload keeps its English states -- the guards pin those names -- and
// the page says them in the operator's words. N-0031: "to ma tento room 2
// cards co testvoal? proc jsou obe not bought".
const NX_LEG = {"not bought": "nekoupeno", "card not found": "karta neexistuje",
                bought: "koupeno", closed: "zavřeno", open: "drží se"};
// A card's own page on cymetica.com, in a new tab, wherever the card is named;
// plain text for a card their API does not know. `inner` is already escaped.
function nxCardLink(nl, inner) {
  return nl && nl.url ? '<a class="nx-link" href="' + esc(nl.url) +
    '" target="_blank" rel="noopener" title="Open the card on cymetica.com">' + inner +
    ' <span class="nx-out">↗</span></a>' : inner;
}
function nxLegs(np) {
  const legs = np.legs || [];
  if (!legs.length) return "";
  const rows = legs.map(nl => {
    const share = nl.share != null
      ? nxShare(nl.share) + (nl.usdc_proposed != null ? " · " + nxMoney(nl.usdc_proposed) : "")
      : nl.invested ? nxMoney(nl.invested) + " USDC" : "—";
    const moved = nl.entry != null
      ? esc(nxLevel(nl.entry) + " → " + nxLevel(nl.current))
      : nl.at_proposal != null
        ? esc(nxLevel(nl.at_proposal) + " → " + nxLevel(nl.current)) +
          "<small>od chvíle, co to Nexus navrhl</small>"
        : "—";
    const exits = (nl.tp != null ? nxPct(nl.tp, nl.tp % 1 ? 1 : 0) : "—") + " / " +
      (nl.sl != null ? nxPct(nl.sl, nl.sl % 1 ? 1 : 0) : "—");
    const state = nl.state || "not bought";
    return '<div class="nx-tr"><span><b title="' + esc(nl.card_title || "") + '">' +
      nxCardLink(nl, esc(nxLegName(nl))) + "</b><small>" + esc(nxLegNote(nl)) + "</small></span><span>" +
      (nl.side === "bear" ? "▼ bear" : nl.side ? "▲ " + esc(nl.side) : "—") + "</span><span>" +
      esc(share) + "</span><span>" + moved + "</span><span>" + esc(exits) +
      '</span><span class="nx-state nx-' + esc(state.split(" ").join("-")) + '">' +
      esc(NX_LEG[state] || state) + "</span></div>";
  }).join("");
  return '<div class="nx-sec">Karty téhle strategie</div><div class="nx-table nx-legs">' +
    '<div class="nx-tr nx-th"><span>Karta</span><span>Sázka</span><span>Podíl</span>' +
    "<span>Vstup → teď</span><span>Zisk / stopka</span><span>Stav</span></div>" +
    rows + (np.reserve != null
      ? '<div class="nx-tr nx-dim"><span>Rezerva</span><span></span><span>' +
        esc(nxShare(np.reserve)) + "</span><span></span><span></span><span></span></div>"
      : "") + "</div>";
}
// One chart per card that has an index: the entry and Nexus's exits across it
// when it was bought; when it was not, where it stood when Nexus proposed it
// and how it moved since -- what would have happened, and said so.
function nxLegCharts(np) {
  return (np.legs || []).filter(nl => (nl.series || []).length >= 2).map(nl => {
    const bought = nl.entry != null;
    const refs = [];
    if (bought) {
      refs.push({ v: nl.entry, label: "entry " + nxLevel(nl.entry), kind: "entry" });
    } else if (nl.at_proposal != null) {
      refs.push({ v: nl.at_proposal, label: "navrženo " + nxLevel(nl.at_proposal),
                  kind: "base" });
    }
    if (nl.tp_level != null) {
      refs.push({ v: nl.tp_level, label: "TP " + nxLevel(nl.tp_level), kind: "tp" });
    }
    if (nl.sl_level != null) {
      refs.push({ v: nl.sl_level, label: "SL " + nxLevel(nl.sl_level), kind: "sl" });
    }
    const order = bought ? (np.trades || []).find(nt => nt.card === nl.card &&
                                                        nt.outcome === "accepted") : null;
    const head = nxLegName(nl) + (bought ? "" : " · nekoupeno");
    const note = bought
      ? (nl.pnl != null ? "zisk " + nxSigned(nl.pnl) + " USDC" : "")
      : "kdybychom koupili, když to navrhl: " + nxPct(nl.since_proposal, 2);
    return '<div class="nx-ct"><span>' + nxCardLink(nl, esc(head)) + "</span><small>" +
      esc(note) +
      "</small></div>" + nxChart(nl.series, {
        refs: refs, label: head,
        vline: bought ? (order ? { t: order.at, label: "koupeno" } : null)
                      : (np.proposed_at ? { t: np.proposed_at, label: "Nexus navrhl" }
                                        : null) });
  }).join("");
}
function nxOrders(np) {
  const orders = np.trades || [];
  if (!orders.length) return "";
  const legOf = card => (np.legs || []).find(nl => nl.card === card);
  return '<div class="nx-sec">Orders</div><div class="nx-table nx-orders">' +
    '<div class="nx-tr nx-th"><span>Order</span><span>When</span><span>What</span>' +
    "<span>State</span></div>" + orders.map(nt => {
      const leg = legOf(nt.card);
      const state = nt.outcome !== "accepted" ? (nt.outcome || "no outcome recorded")
        : nt.closed_by ? "closed " + nxSigned(nt.realized) + " USDC" : "open";
      return '<div class="nx-tr"><span>' + esc(nt.id) + '</span><span class="nx-dim">' +
        esc(nxDay(nt.at)) + "</span><span>" + esc((nt.side || "buy") + " · " +
        nxMoney(nt.usdc) + " USDC · ") + (leg ? nxCardLink(leg, esc(nxLegName(leg)))
                                            : esc(nxShort(nt.card, 9))) +
        '</span><span class="nx-state' + (state === "open" ? " nx-open"
          : nt.outcome !== "accepted" ? " nx-card-not-found" : "") + '">' + esc(state) +
        "</span></div>";
    }).join("") + "</div>";
}
function nxCardTiles(np) {
  const legs = np.legs || [];
  const closes = np.closes_at ? nxDay(np.closes_at) + " UTC" : "";
  // Every leg counted by where it stands, so a card they no longer have is
  // counted too: "2 not bought · 1 card not found".
  const states = {};
  legs.forEach(nl => { states[nl.state] = (states[nl.state] || 0) + 1; });
  const told = Object.entries(states).map(
    ([word, n]) => n + " " + (NX_LEG[word] || word)).join(" · ");
  if ((np.invested || 0) > 0) {
    const proposed = np.proposed_share != null && np.bankroll
      ? np.proposed_share * np.bankroll : null;
    return nxTiles([
      ["Zisk", np.pnl != null ? nxSigned(np.pnl) + " USDC" : "—",
       np.pnl_pct != null ? nxPct(np.pnl_pct, 2) + " z vloženého" : "", nxTone(np.pnl)],
      ["Vloženo", nxMoney(np.invested),
       proposed != null ? "z " + nxMoney(proposed) + " navržených" : "USDC", ""],
      ["Teď to má cenu", np.value != null ? nxMoney(np.value) : "—", "USDC", ""],
      ["Karta končí", nxUntil(np.closes_at) || "—", closes, ""]]);
  }
  return nxTiles([
    ["Navrhl vsadit", np.proposed_share != null ? nxShare(np.proposed_share) : "—",
     np.bankroll ? "z " + nxMoney(np.bankroll) + " USDC" : "z účtu", ""],
    ["Kdybychom koupili", nxPct(np.if_bought_pct, 2), "tolik by to dělalo dneska",
     nxTone(np.if_bought_pct)],
    ["Karet", legs.length, told, ""],
    ["První končí", nxUntil(np.closes_at) || "—", closes, ""]]);
}
// A bot: what it is, the indicators it trades on, its P&L with each of its
// trades on the line, and the trades themselves.
function nxBot(nc) {
  const cfg = nc.config || {};
  const chips = list => (list || []).map(ind => '<span class="nx-chip" title="' +
    esc(nxParams(ind && ind.params)) + '">' + esc((ind && ind.name) || "?") +
    "</span>").join("");
  const mode = cfg.execution_class
    ? String(cfg.execution_class).toLowerCase().split("_").join(" ")
    : nc.paper === false ? "LIVE" : "paper";
  const pairs = [["Bot", nc.name],
                 ["Clone of", [nc.source, nc.symbol].filter(Boolean).join(" · ")],
                 ["Strategy", cfg.strategy_type || nc.strategy],
                 ["Risk", cfg.risk_profile || nc.risk], ["Mode", mode]]
    .filter(([, v]) => v);
  const acts = nc.activity || [];
  const series = (nc.samples || []).filter(ns => ns.pnl != null).map(ns => [ns.at, ns.pnl]);
  // Where the line stands at a trade's moment, between the two samples around
  // it, so each dot sits on the line rather than above a drop it caused.
  const valueAt = when => {
    const t = Date.parse(when);
    let prev = null;
    for (const p of series) {
      const at = Date.parse(p[0]);
      if (at >= t) {
        if (!prev || at === t) return p[1];
        const from = Date.parse(prev[0]);
        return prev[1] + (p[1] - prev[1]) * (t - from) / ((at - from) || 1);
      }
      prev = p;
    }
    return prev ? prev[1] : null;
  };
  const marks = acts.map(na => na.is_closed && na.closed_at
    ? { t: na.closed_at, v: valueAt(na.closed_at),
        kind: Number(na.profit_usdc) < 0 ? "loss" : "open",
        title: (na.symbol || "?") + " " + (na.trade_type || "") + " closed " +
               nxSigned(na.profit_usdc) + " USDC" }
    : { t: na.executed_at, v: valueAt(na.executed_at), kind: "open",
        title: (na.symbol || "?") + " " + (na.trade_type || "") + " " +
               nxMoney(na.amount_usdc) + " USDC, open" });
  return '<div class="nx-sec">Jak je bot nastavený</div><div class="nx-kv">' +
    pairs.map(([k, v]) => "<div><span>" + esc(k) + "</span>" + esc(v) + "</div>").join("") +
    "</div>" +
    ((cfg.primary_indicators || []).length
      ? '<div class="nx-chips"><span>Hlavní</span>' + chips(cfg.primary_indicators) +
        "</div>" : "") +
    ((cfg.secondary_indicators || []).length
      ? '<div class="nx-chips"><span>Vedlejší</span>' + chips(cfg.secondary_indicators) +
        "</div>" : "") +
    (series.length >= 2
      ? '<div class="nx-ct"><span>Zisk od zapnutí</span><small>' +
        esc(nc.win_rate != null ? "úspěšnost " + nc.win_rate + " %" : "") + "</small></div>" +
        nxChart(series, { marks: marks, format: nxSigned, label: "Zisk bota v čase" })
      : "") +
    (acts.length
      ? '<div class="nx-sec">Jeho obchody</div><div class="nx-table nx-trades">' +
        '<div class="nx-tr nx-th"><span>Mince</span><span>Typ</span><span>USDC</span>' +
        "<span>Výsledek</span><span>Kdy</span></div>" + acts.map(na =>
          '<div class="nx-tr"><span><b>' + esc(na.symbol || "?") + "</b> · " +
          esc(na.side || "") + "</span><span>" + esc(na.trade_type || "") + "</span><span>" +
          esc(nxMoney(na.amount_usdc)) + "</span>" + (na.is_closed
            ? '<span class="' + nxTone(na.profit_usdc).trim() + '">' +
              esc(nxSigned(na.profit_usdc)) + " · zavřeno" +
              (na.exit_reason ? "<small>" + esc(na.exit_reason) + "</small>" : "") + "</span>"
            : '<span class="nx-dim">drží se</span>') +
          '<span class="nx-dim">' + esc(nxDay(na.executed_at)) + "</span></div>").join("") +
        "</div>"
      : "");
}
// Why a strategy stands where it does, and every move before it, newest first:
// under the name, above the numbers. It is the operator's first question about
// a strategy, and folded at the bottom it was the one thing they could not find.
// The current move is said once, as the why, not again in the list.
// One line, derived from the fields -- not the stored `why`, which is a
// paragraph written for a reader who is not there. N-0032 and N-0034 are the
// same complaint twice: "kdo to ma cist". The paragraph and the whole history
// are one click away and nothing is thrown out.
function nxGist(np) {
  const v = np.verdict, why = String(np.why || "");
  if (np.status === "proposed") return "Jen návrh. Nekoupili jsme nic.";
  if (v && v.verdict === "inconclusive") {
    const cov = v.coverage != null ? Math.round(v.coverage * 100) + " %" : "málo";
    return "Nedá se říct, jestli to vyšlo: karta hlásila cenu jen " + cov +
           " okna. Chybí data, ne peníze.";
  }
  if (v && v.verdict === "survived") return "Vyšlo to.";
  if (v && v.verdict === "refuted") return "Nevyšlo to.";
  if (/drop\b/i.test(why) && /^NEX-/.test(why)) return "Nexus to sám odvolal.";
  if (np.status === "paused") return "Zastavilo se to samo.";
  if (np.status === "running") return "Běží, verdikt ještě není.";
  return "";
}
function nxStatus(np) {
  const moves = (np.history || []).filter(nh =>
    !(nh.status === np.status && nh.why === np.why)).reverse();
  const gist = nxGist(np);
  if (!np.why && !moves.length && !gist) return "";
  const long = (np.why ? "<p>" + esc(np.why) + "</p>" : "") +
    (moves.length ? '<div class="nx-moves">' + moves.map(nh => "<p>" +
      nxGlyph(nh.status) + " <b>" + esc(NX_WORD[nh.status] || nh.status || "") + "</b> · " +
      esc(nxDay(nh.at)) + (nh.why ? " — " + esc(nh.why) : "") + "</p>").join("") +
      "</div>" : "");
  return '<div class="nx-status nx-' + esc(np.status || "proposed") + '">' +
    (gist ? '<p class="nx-gist">' + esc(gist) + "</p>" : "") +
    (long ? "<details class=\"nx-more\"><summary>víc</summary>" + long + "</details>" : "") +
    "</div>";
}
// What a room was accepted on, and what the numbers said at the end of its
// window. A room with neither is one nobody could score afterwards, so the
// panel says that first rather than leaving the space blank.
const NX_SAID = {survived: ["Vyšlo", " nx-up"], refuted: ["Nevyšlo", " nx-down"],
                 inconclusive: ["Nedá se říct", ""], open: ["Ještě běží", ""]};
// When the verdict becomes computable: the moment it was accepted plus its
// window, which is the arithmetic qa/lab.py:verdict does -- it starts the
// window at acceptance["at"], never at the moment the room went running. A
// window already past says "due now", because then nobody has run the verdict
// yet and that is the one state worth noticing on this page.
function nxDue(c) {
  const t = Date.parse(c.at || ""), d = Number(c.window_days);
  if (!t || !(d > 0)) return ["—", "není okno, které by skončilo"];
  const end = new Date(t + d * 86400000).toISOString(), left = nxUntil(end);
  return left === "closed" ? ["čeká se na něj", "okno skončilo " + nxDay(end), " nx-warn"]
                           : [left, "okno končí " + nxDay(end), ""];
}
function nxVerdict(np) {
  const c = np.criterion, v = np.verdict;
  if (!c && !v) {
    return '<div class="nx-sec">Jak se pozná úspěch</div><p class="nx-foot">' +
      "Nikdo to dopředu nenapsal, takže se po skončení nedá říct, jestli to vyšlo." +
      " Píše to <code>lab.py adopt</code> a bez toho už room běžet nesmí.</p>";
  }
  let html = '<div class="nx-sec">Jak to dopadlo</div>';
  if (v) {
    const said = NX_SAID[v.verdict] || [v.verdict, ""];
    html += nxTiles([
      [said[0], v.return_pct != null ? nxPct(v.return_pct, 2) : "—",
       "tolik to vydělalo za okno", said[1]],
      ["Největší propad", v.max_drawdown_pct != null ? nxMag(v.max_drawdown_pct, 2) : "—",
       c && c.stop_pct != null ? "brali jsme to se stopkou " + nxMag(c.stop_pct, 0) : "",
       ""],
      ["Pro srovnání", v.benchmark_pct != null ? nxPct(v.benchmark_pct, 2) : "—",
       v.benchmark_pct != null ? "BTC karta za stejnou dobu" : "není s čím srovnat", ""],
      ["Kolik dat", v.coverage != null ? Math.round(v.coverage * 100) + " %" : "—",
       "okna má vůbec cenu karty",
       v.coverage != null && v.coverage < 0.8 ? " nx-down" : ""]]);
  } else {
    const due = nxDue(c);
    html += nxTiles([
      ["Okno", (c.window_days != null ? c.window_days : "—") + " d",
       c.adopted ? "běží od chvíle, kdy se to napsalo" : "napsáno dřív, než se spustilo", ""],
      ["Stopka", c.stop_pct != null ? nxMag(c.stop_pct, 0) : "—", "od vstupu", ""],
      ["Pro srovnání", c.benchmark ? String(c.benchmark).slice(0, 8) : "nic",
       c.benchmark ? "BTC karta" : "není s čím srovnat", ""],
      ["Verdikt", due[0], due[1], due[2]]]);
  }
  if (np.claim) {
    html += '<p class="nx-foot">Nexus sliboval: ' + Object.keys(np.claim).map(
      k => esc(k) + " " + esc(String(np.claim[k]))).join(" · ") + "</p>";
  }
  return html;
}
// What their own backtest said about each card BEFORE the room opened, or
// that nothing was measured. The second case is the true one for every room
// on this page and the panel says it in one sentence rather than leaving the
// space blank -- an absent brake that looks like a blank is how a brake stays
// absent.
function nxBacktest(np) {
  const rows = np.backtests || [];
  if (!rows.length) {
    return '<div class="nx-sec">Backtest před spuštěním</div>' +
      '<p class="nx-foot">Žádný. Tenhle room vznikl dřív, než jsme si dali ' +
      "pravidlo backtestovat každou kartu předem (12. 9.). Od té doby se " +
      "každé kartě měří návratnost a Sharpe na jejich vlastním backtestu a " +
      "room se bez toho neotevře.</p>";
  }
  const word = {pass: ["prošlo", " nx-up"], reject: ["neprošlo", " nx-down"],
                unbacktestable: ["nešlo změřit", ""]};
  return '<div class="nx-sec">Backtest před spuštěním</div>' +
    '<div class="nx-table nx-bt"><div class="nx-tr nx-th"><span>Karta</span>' +
    "<span>Výsledek</span><span>Výnos</span><span>Sharpe</span><span>Propad</span></div>" +
    rows.map(b => {
      const said = word[b.verdict] || [b.verdict || "—", ""];
      return '<div class="nx-tr"><span><b>' +
        esc(String(b.title || b.card || "?").slice(0, 34)) + "</b></span>" +
        '<span class="' + said[1].trim() + '">' + esc(said[0]) +
        (b.period ? ' <small>' + esc(b.period) + " d</small>" : "") + "</span><span>" +
        esc(b.return_pct != null ? nxPct(b.return_pct, 1) : "—") + "</span><span>" +
        esc(b.sharpe != null ? Number(b.sharpe).toFixed(2) : "—") + "</span><span>" +
        esc(b.drawdown_pct != null ? nxMag(b.drawdown_pct, 1) : "—") + "</span></div>";
    }).join("") + "</div>";
}
function nxStrategy(nr, np) {
  const nc = (np.clones || [])[0] || null;
  const pills = nxPill(np.status) +
    (np.holds ? '<span class="nx-pill nx-holds-' + esc(np.holds) + '">' +
                esc(NX_HOLDS[np.holds] || np.holds) + " · papír</span>" : "") +
    (nc && nc.trading != null ? '<span class="nx-pill nx-trading-' +
      (nc.trading ? "on" : "off") + '">' +
      (nc.trading ? "obchoduje" : "neobchoduje") + "</span>" : "");
  const sub = esc(nr.id) + " · navrhl Nexus v " + esc(np.origin || "—") +
    (np.since ? " · od " + esc(nxDay(np.since)) : "");
  let html = nxHero(np.title || nr.title || nr.id, pills, sub) + nxStatus(np) +
    nxVerdict(np);
  if (nc) {
    const acts = nc.activity || [];
    const closed = acts.filter(na => na.is_closed).length;
    html += nxTiles([
      ["P&L", nc.pnl != null ? nxSigned(nc.pnl) + " USDC" : "—",
       nc.pnl != null && nc.funded ? nxPct(nc.pnl / nc.funded * 100) + " of what it was given"
                                   : "", nxTone(nc.pnl)],
      ["Balance", nxMoney(nc.balance), nc.locked != null
        ? nxMoney(nc.locked) + " locked · " + nxMoney(nc.available) + " free" : "", ""],
      ["Funded", nxMoney(nc.funded), "USDC", ""],
      ["Trades", acts.length || nc.trades || 0,
       acts.length ? closed + " closed · " + (acts.length - closed) + " open" : "", ""]]) +
      nxBot(nc);
  } else if ((np.legs || []).length) {
    html += nxCardTiles(np);
  }
  html += nxBacktest(np);
  if ((np.legs || []).length) {
    html += nxLegs(np) + nxLegCharts(np) + nxOrders(np);
  } else if (!nc) {
    html += '<p class="nx-foot">Nic nekoupeno a žádný plán k tomu napsaný není.</p>';
  }
  return html + nxSampler(np);
}
function nxPanelOf(id) {
  return ((NX && NX.panels) || {})[id] || {};
}
function nxBotValue(nr) {
  const np = nxPanelOf(nr.id);
  return np.value;
}
// The overview: the account, every strategy with where it stands, and how
// Nexus has answered so far.
// One cell per strategy: what it came to, or when it will be known, or that
// nobody wrote down what would count. The operator reads this column to find
// out which of Nexus's ideas made money, which is the whole question.
function nxScore(nr) {
  const v = nr.verdict, c = nr.criterion;
  if (v) {
    const said = NX_SAID[v.verdict] || [v.verdict, ""];
    return '<b class="' + said[1].trim() + '">' + esc(said[0]) + "</b>" +
      (v.return_pct != null ? " " + esc(nxPct(v.return_pct, 2)) : "");
  }
  if (c) {
    return '<span class="nx-state">čeká ' + (c.window_days != null ? c.window_days : "?") +
      " d</span>";
  }
  return '<span class="nx-state">nikdo nenapsal, co je úspěch</span>';
}
function nxGeneral(np) {
  const every = ((NX && NX.rooms) || []).filter(nr => nr.kind === "strategy");
  const count = status => every.filter(nr => nr.status === status).length;
  // The table lists what is live; the stopped ones are counted, and shown
  // with their reason only when the "Ukončené" group is open.
  const rooms = readStore("qa.showEnded", "0") === "1" ? every
    : every.filter(nr => nr.status !== "stopped");
  const bots = rooms.filter(nr => nr.holds === "bot");
  const inBot = bots.reduce((sum, nr) => sum + (Number(nxBotValue(nr)) || 0), 0);
  const quiet = (np.partial || 0) + (np.failed || 0) + (np.refused || 0);
  const table = rooms.map(nr => '<div class="nx-tr"><span><button type="button" ' +
    'class="nx-pf" data-room="' + esc(nr.id) + '">' + esc(nr.title || nr.id) +
    "</button></span><span>" + esc(NX_HOLDS[nr.holds] || "—") + "</span><span>" +
    nxPill(nr.status) + "</span><span>" + (nr.invested ? esc(nxMoney(nr.invested)) + " USDC"
      : nr.proposed_share != null ? esc(nxShare(nr.proposed_share)) + " proposed" : "—") +
    '</span><span class="' + nxTone(nr.pnl).trim() + '">' +
    (nr.pnl != null ? esc(nxSigned(nr.pnl)) + " USDC"
      : nr.if_bought_pct != null
        ? '<span class="nx-dim">nekoupeno</span> ' + esc(nxPct(nr.if_bought_pct, 2))
        : "—") +
    "</span><span>" + (nr.status === "stopped" && nr.why
      ? '<span class="nx-state" title="' + esc(nr.why) + '">' + esc(nxShort(nr.why, 60)) +
        "</span>" : nxScore(nr)) + "</span></div>").join("");
  return nxHero("Přehled", "", "Každá otázka na Nexuse a každá strategie, co navrhl") +
    nxTiles([
      ["Volné peníze", np.balance != null ? nxMoney(np.balance) : "—",
       np.balance_at ? "USDC, stav k " + nxDay(np.balance_at) : "USDC, papír", ""],
      ["V kartách", np.notional != null ? nxMoney(np.notional) : "—",
       np.book_trades != null ? np.book_trades + " objednávek na účtu" : "", ""],
      ["V botovi", bots.length ? nxMoney(inBot) : "—",
       bots.length ? bots.map(nr => nr.title || nr.id).join(", ") : "žádný bot", ""],
      ["Strategie", every.length, count("running") + " běží · " + count("proposed") +
       " jen návrh" + (count("paused") ? " · " + count("paused") + " pauza" : "") +
       (count("stopped") ? " · " + count("stopped") + " ukončených" : ""), ""]]) +
    '<div class="nx-sec">Strategie</div>' + (rooms.length
      ? '<p class="nx-foot nx-cap">Co Nexus navrhl. <b>Nekoupeno</b> = jen návrh, ' +
        "číslo za tím je, kolik by to dělalo, kdybychom ho koupili. " +
        "<b>Nedá se říct</b> = karta přestala hlásit cenu, takže se nedá spočítat, " +
        "jestli to vyšlo.</p>" +
        '<div class="nx-table nx-strats"><div class="nx-tr nx-th"><span>Strategie</span>' +
        "<span>Drží</span><span>Stav</span><span>Vloženo</span><span>Zisk</span>" +
        "<span>Jak dopadla</span></div>" +
        table + "</div>"
      : '<p class="nx-foot">Každá strategie, co Nexus navrhne, dostane vlastní kartu nahoře.</p>') +
    '<div class="nx-sec">Nexus, všechny otázky</div>' +
    nxTiles([
      ["Zeptali jsme se", np.asked || 0, "", ""],
      ["Odpověděl", np.answered || 0,
       np.asked ? Math.round((np.answered || 0) / np.asked * 100) + " % z toho" : "", ""],
      ["Obvykle to trvá", np.median_seconds != null ? nxSecs(np.median_seconds) : "—", "", ""],
      ["Bez odpovědi", quiet, (np.partial || 0) + " useklých · " + (np.failed || 0) +
       " vzdal · " + (np.refused || 0) + " odmítl", quiet ? " nx-down" : ""]]) +
    '<div class="rely-strip">' + (np.strip || []).map(o =>
      '<i class="sq ' + esc(o) + '" title="' + esc(o) + '"></i>').join("") + "</div>" +
    '<p class="nx-foot rely-legend">' + [["answered", "odpověděl"], ["partial", "useklé"],
      ["failed", "vzdal to"], ["refused", "odmítl"], ["waiting", "čeká se"]].map(
      ([cls, word]) => '<i class="sq ' + cls + '"></i>' + word).join(" &nbsp; ") + "</p>" +
    '<div class="nx-why">' + nxSampler(np) + "</div>";
}
function nxPanel(nr, np) {
  return nr && nr.kind === "strategy" ? nxStrategy(nr, np) : nxGeneral(np);
}
// One card per room across the top: where it stands, what it holds, its name,
// and the one number that says how it is doing.
function nxCard(nr, current) {
  const fresh = nxFresh(nr.id);
  const badge = fresh ? '<span class="nx-badge" title="new since you last looked">' +
    fresh + "</span>" : "";
  const on = nr.id === current ? " on" : "";
  if (nr.kind !== "strategy") {
    const np = nxPanelOf(nr.id);
    return '<button type="button" class="nx-card' + on + '" data-room="' + esc(nr.id) + '">' +
      '<span class="nx-card-top">Everything</span><span class="nx-card-name">Overview</span>' +
      '<span class="nx-card-num">' + esc(String(np.asked || 0)) + " questions to Nexus</span>" +
      badge + "</button>";
  }
  const number = nr.pnl != null
    ? '<span class="nx-card-num' + nxTone(nr.pnl) + '">' + esc(nxSigned(nr.pnl)) +
      " USDC</span>"
    : '<span class="nx-card-num">' + (nr.proposed_share != null
        ? esc(nxShare(nr.proposed_share)) + " of account" : "nothing bought") + "</span>";
  return '<button type="button" class="nx-card' + on + '" data-room="' + esc(nr.id) +
    '" title="' + esc(nr.id) + '"><span class="nx-card-top">' + nxPill(nr.status) +
    (nr.holds ? "<span>" + esc(NX_HOLDS[nr.holds] || nr.holds) + "</span>" : "") +
    '</span><span class="nx-card-name">' + esc(nr.title || nr.id) + "</span>" +
    (nr.status === "stopped" && nr.why
      ? '<span class="nx-card-why">' + esc(nxShort(nr.why, 90)) + "</span>" : number) +
    badge + "</button>";
}

// What arrived since the operator last looked at a room: Nexus's replies and
// our notes, never their own. Kept in this browser only -- a convenience, not
// state, like every other readStore on this page.
function nxFresh(id) {
  const seen = Number(readStore("qa.roomSeen." + id, "0")) || 0;
  return ((NX && NX.threads && NX.threads[id]) || []).filter(nm =>
    (nm.kind === "reply" || nm.kind === "claude_note") && nm.at &&
    Date.parse(nm.at) > seen).length;
}

// The room drawn last, so a redraw can tell a switch of room -- which opens at
// the newest message -- from a refresh, which leaves the reader where they
// were. A redraw lands every few seconds while notes and samples arrive, and a
// thread that jumped each time could not be read.
let NX_SHOWN = null, nxResizing = null;
// The two columns fill the window under the strip, so the composer sits at the
// bottom of the screen and the thread scrolls above it.
function nxFit() {
  const main = document.getElementById("nxMain");
  if (!main || !main.style || typeof main.getBoundingClientRect !== "function") return;
  if ((window.innerWidth || 0) < 1100) { main.style.height = ""; return; }
  const top = main.getBoundingClientRect().top + (window.scrollY || 0);
  main.style.height = Math.max(480, Math.round((window.innerHeight || 0) - top - 18)) + "px";
}

function renderRooms(data) {
  NX = data || { rooms: [], threads: {}, panels: {} };
  const rooms = NX.rooms || [];
  let current = readStore("qa.room", "general");
  if (!rooms.some(nr => nr.id === current)) current = rooms.length ? rooms[0].id : "general";
  const thread = (NX.threads || {})[current] || [];
  if (!document.getElementById("panel-nexus").hidden) {
    const newest = thread.reduce((n, nm) => Math.max(n, Date.parse(nm.at || "") || 0), 0);
    writeStore("qa.roomSeen." + current, newest);
  }
  // [N-0049, N-0050] a stopped room is a record, not a thing to look at every
  // day: it leaves the strip for a folded "Ukončené" group, and says why on
  // its own card when the group is open. The room open right now stays.
  const showEnded = readStore("qa.showEnded", "0") === "1";
  const ended = rooms.filter(nr => nr.status === "stopped");
  const strip = rooms.filter(nr => nr.status !== "stopped" || showEnded ||
                                   nr.id === current);
  document.getElementById("roomList").innerHTML =
    strip.map(nr => nxCard(nr, current)).join("") + (ended.length
      ? '<button type="button" class="nx-card nx-ended" data-ended="1">' +
        '<span class="nx-card-top">' + (showEnded ? "▴ schovat" : "▾ ukázat") +
        '</span><span class="nx-card-name">Ukončené (' + ended.length + ")</span>" +
        '<span class="nx-card-num">nepovedené a zastavené pokusy</span></button>'
      : "");
  const shown = rooms.find(nr => nr.id === current) ||
    { id: "general", title: "General", kind: "general" };
  const chat = document.getElementById("roomChat");
  const panel = document.getElementById("roomPanel");
  const switched = NX_SHOWN !== current;
  const atEnd = !chat.scrollHeight ||
    chat.scrollHeight - chat.scrollTop - chat.clientHeight < 60;
  const chatAt = chat.scrollTop, panelAt = panel.scrollTop;
  nxFit();
  chat.innerHTML = thread.length ? thread.map(nm => nxBubble(nm, current)).join("")
                                 : '<div class="empty">Nothing here yet.</div>';
  chat.scrollTop = switched || atEnd ? chat.scrollHeight : chatAt;
  panel.innerHTML = nxPanel(shown, (NX.panels || {})[current] || {});
  panel.scrollTop = switched ? 0 : panelAt || 0;
  NX_SHOWN = current;
  const total = rooms.reduce((n, nr) => n + nxFresh(nr.id), 0);
  const badge = document.getElementById("nexusN");
  if (badge) { badge.textContent = total ? String(total) : ""; badge.hidden = !total; }
  nxBindComposer(current);
}
window.renderRooms = renderRooms;
window.addEventListener("resize", () => {
  clearTimeout(nxResizing);
  nxResizing = setTimeout(() => {
    if (NX && !document.getElementById("panel-nexus").hidden) renderRooms(NX);
  }, 150);
});

// The one line the tab says about itself: why it is empty, or nothing. It is a
// status, not a mark the operator can clear, so it shows exactly when there is
// something to say and is never revealed unconditionally
// (tests/repo/test_live_server.py counts those).
function nxSay(message) {
  const note = document.getElementById("roomsNote");
  note.textContent = message || "";
  note.hidden = !message;
}

function loadRooms() {
  if (!NX_LOCAL || typeof fetch !== "function") {
    nxSay("The rooms live in the running console, not in this file. " +
          "Start console.cmd and open http://127.0.0.1:8787/.");
    return;
  }
  fetch("/rooms.json", { cache: "no-store" })
    .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
    .then(data => { nxSay(""); renderRooms(data); })
    .catch(e => nxSay("Could not load the rooms: " + e.message));
}

document.getElementById("roomList").addEventListener("click", e => {
  const ended = e.target.closest("[data-ended]");
  if (ended) {
    writeStore("qa.showEnded", readStore("qa.showEnded", "0") === "1" ? "0" : "1");
    renderRooms(NX);
    return;
  }
  const b = e.target.closest("[data-room]");
  if (!b) return;
  writeStore("qa.room", b.dataset.room);
  renderRooms(NX);
});
// A line naming another room -- a pointer, "it opened STR-0003", a strategy in
// General's portfolio -- takes the operator there.
function nxGoInto(e) {
  const go = e.target.closest(".nx-goto, .nx-pf");
  if (!go) return false;
  writeStore("qa.room", go.dataset.room);
  renderRooms(NX);
  return true;
}
document.getElementById("roomPanel").addEventListener("click", nxGoInto);
document.getElementById("roomChat").addEventListener("click", e => {
  if (nxGoInto(e)) return;
  const b = e.target.closest(".nx-more");
  if (!b || !b.previousElementSibling) return;
  const body = b.previousElementSibling;
  body.classList.toggle("nx-clamp");
  b.textContent = body.classList.contains("nx-clamp") ? b.dataset.label : "▴ less";
});

/* The composer: the operator's feedback for the room on screen. It is the
   console's one write, so it goes through every door serve.py keeps -- a
   token asked for at the moment of sending, a JSON body, this machine only. */
let nxReloadWhenDone = false, nxSending = false;

function nxTyping() {
  const draft = document.getElementById("nxDraft");
  return !!(draft && document.activeElement === draft &&
            String(draft.value || "").trim());
}
// A page update never lands under a note being written. The draft would
// survive -- it is stored as it is typed -- but the operator's cursor would not.
function nxReloadIfDue() {
  if (!nxReloadWhenDone || nxSending || nxTyping()) return;
  writeStore("qa.scroll", window.scrollY);
  location.reload();
}
function nxBindComposer(room) {
  const form = document.getElementById("nxCompose");
  const draft = document.getElementById("nxDraft");
  form.hidden = !NX_LOCAL;
  if (form.dataset.room === room) return;
  if (form.dataset.room) writeStore("qa.draft." + form.dataset.room, draft.value || "");
  form.dataset.room = room;
  draft.value = readStore("qa.draft." + room, "");
}
// Asked for at the moment of sending, never baked into the page: a tab left
// open across a console restart would otherwise hold a token the new process
// never issued, and every note would bounce.
function nxPost(room, text) {
  return fetch("/token", { cache: "no-store" })
    .then(r => r.ok ? r.json()
                    : Promise.reject(new Error("the console gave no token (" + r.status + ")")))
    .then(t => fetch("/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-QA-Token": t.token },
      body: JSON.stringify({ room: room, text: text }),
    }))
    .then(r => r.ok ? r.json()
                    : r.json().catch(() => ({})).then(b =>
                        Promise.reject(new Error(b.error || ("HTTP " + r.status)))));
}
// On window so a test can run the page's own send path over a stub fetch and
// hold what it sends against what serve.py accepts.
window.nxPost = nxPost;
document.getElementById("nxDraft").addEventListener("input", e => {
  const room = document.getElementById("nxCompose").dataset.room;
  if (room) writeStore("qa.draft." + room, e.target.value);
});
document.getElementById("nxDraft").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    document.getElementById("nxSend").click();
  }
});
document.getElementById("nxDraft").addEventListener("blur",
  () => setTimeout(nxReloadIfDue, 800));
document.getElementById("nxCompose").addEventListener("submit", e => {
  e.preventDefault();
  const form = document.getElementById("nxCompose");
  const draft = document.getElementById("nxDraft");
  const button = document.getElementById("nxSend");
  const status = document.getElementById("nxSendNote");
  const room = form.dataset.room;
  const text = String(draft.value || "").trim();
  if (!room || !text || nxSending) return;
  nxSending = true;
  button.disabled = true;
  status.textContent = "sending…";
  nxPost(room, text)
    .then(() => {
      draft.value = "";
      writeStore("qa.draft." + room, "");
      status.textContent = "saved ✓ — Claude reads it when you ask";
      loadRooms();
    })
    .catch(err => { status.textContent = "not sent: " + err.message; })
    .finally(() => { nxSending = false; button.disabled = false; nxReloadIfDue(); });
});
if (NX_LOCAL) loadRooms();


/* ---------- the memecoin measurement in full ----------
   A tab of the console from 2026-09-13, after the operator asked for a
   section just for memecoins, got the last block of Stats, and could not find
   it; on this page since V4.

   Green is a gain and red is a loss, everywhere, including the summary --
   they read pictures rather than tables. The MEDIAN is the headline and the
   mean is beside it in small text, because one token returning +1262% drags
   the mean to +46% while half the signals are under water: a hero number that
   says +46% would be a lie told with a true figure.
*/
function pct(v) {
  if (v == null) return `<span class="mc-flat">&mdash;</span>`;
  const cls = v > 0 ? "mc-up" : (v < 0 ? "mc-down" : "mc-flat");
  const sign = v > 0 ? "+" : "";
  return `<span class="${cls}">${sign}${v.toFixed(1)}%</span>`;
}

/* One token, one hourly curve. A gap is a BREAK in the line, never a point
   at zero: half these tokens are too new for any DEX pool, and a flat line
   would say the coin sat still when the truth is that nobody could price it.
   Drawn as inline SVG -- no library reaches this page and none is needed. */
function curveSvg(points) {
  // The 24h shape, inline in a table cell. Hovering a point names the hour
  // and what it was worth then -- a native <title>, so it needs no script
  // and works the moment the page opens.
  const W = 150, H = 30, PAD = 3;
  const read = points.filter(p => p[1] != null);
  if (!read.length) return `<span class="mc-flat">&mdash;</span>`;
  const vals = read.map(p => p[1]);
  const hi = Math.max(...vals, 0), lo = Math.min(...vals, 0);
  const span = (hi - lo) || 1;
  const x = h => PAD + ((h - 1) / 23) * (W - 2 * PAD);   // always 24 hours wide
  const y = v => PAD + (1 - (v - lo) / span) * (H - 2 * PAD);

  // Solid between two hours read back to back, dashed across hours nobody
  // priced -- the shape is a guess there and should look like one.
  const lines = read.slice(1).map((p, i) => {
    const a = read[i];
    return `<line x1="${x(a[0]).toFixed(1)}" y1="${y(a[1]).toFixed(1)}"
      x2="${x(p[0]).toFixed(1)}" y2="${y(p[1]).toFixed(1)}"
      stroke="var(${p[1] >= a[1] ? "--ok" : "--bad"})" stroke-width="1.6"
      stroke-linecap="round"${p[0] - a[0] > 1 ? ' stroke-dasharray="2 3" opacity=".55"' : ""}/>`;
  }).join("");
  // Our own bubble, not the browser's <title>: that one is small, grey,
  // half a second late and cannot be coloured. The wide transparent circle
  // is the hit area -- a 2px dot is not something anyone can aim at.
  const dots = read.map(p =>
    `<g class="mc-pt" data-h="${p[0]}" data-v="${p[1]}">
      <circle cx="${x(p[0]).toFixed(1)}" cy="${y(p[1]).toFixed(1)}" r="7"
        fill="transparent"/>
      <circle cx="${x(p[0]).toFixed(1)}" cy="${y(p[1]).toFixed(1)}" r="2.4"
        fill="var(${p[1] >= 0 ? "--ok" : "--bad"})"/></g>`).join("");
  const zero = y(0);

  return `<svg class="mc-spark" viewBox="0 0 ${W} ${H}" role="img"
    aria-label="return by hour since the signal">
    <line x1="${PAD}" x2="${W - PAD}" y1="${zero.toFixed(1)}" y2="${zero.toFixed(1)}"
      stroke="var(--line)" stroke-width="1" stroke-dasharray="2 3"/>
    ${lines}${dots}
  </svg>`;
}

function memecoinPanel() {
  const fm = (D.stats || {}).fomo;
  if (!fm) return `<p class="blurb">No memecoin signals have been captured
    yet. <code>python scripts/fomo_watch.py capture</code> starts it.</p>`;

  const thr = fm.hit_threshold != null ? fm.hit_threshold : 20;
  const day = (fm.horizons || {})["24h"] || {};
  const first = (fm.horizons || {})["1h"] || {};
  const b = fm.basket || {};
  const rows = (fm.curves || []).map(c => `<tr>
      <td class="mc-sym">${esc(c.symbol || "?")}</td>
      <td class="mc-conv">${c.conviction == null ? "&mdash;" : c.conviction}</td>
      <td class="mc-ret">${pct(c.last)}</td>
      <td class="mc-ret">${pct(c.peak)}</td>
      <td class="mc-g">${curveSvg(c.points)}</td>
    </tr>`).join("");

  // "-- of 0" is what the operator saw and read as broken. It was not: no
  // signal had lived a whole day yet. A figure that cannot exist yet says so.
  const fig = (label, row) => {
    const hit = row.hit_rate == null ? null : Math.round(row.hit_rate * 100);
    return `<div><dt>${label}</dt><dd>${hit == null
      ? `<span class="mc-flat">not yet</span>` : hit + "%"}
      <span class="mc-of">${hit == null ? "no signal is that old"
        : "of " + (row.resolved || 0)}</span></dd></div>`;
  };
  const card = (head, value, sub, cls) => `<div class="mc-card">
      <div class="mc-h">${head}</div>
      <div class="mc-big ${cls || ""}">${value}</div>
      <div class="mc-sub">${sub}</div></div>`;
  const big = v => v == null ? `<span class="mc-flat">&mdash;</span>`
    : `<span class="${v > 0 ? "mc-up" : (v < 0 ? "mc-down" : "mc-flat")}">${
       v > 0 ? "+" : ""}${v.toFixed(1)}%</span>`;

  const best = b.best || {}, worst = b.worst || {}, hc = b.high_conviction || {};
  return `<header class="mc-top">
      <h2>Bought every <code>hot</code> signal the moment it fired &mdash;
        what would it be worth?</h2>
      <div class="mc-grid">
        ${card("P&amp;L, equal stake in every signal", big(b.pnl_pct),
          // [operator 2026-09-14] *"to me nezjaima bez top 5 nechapu proc by
          // to tam melo byt"*. It had a card of its own, which was mine and
          // not asked for. It stays as one line here because it is the only
          // thing on the page that says whether the headline is the signal
          // or one lucky row -- demoted, not deleted.
          `${b.n_priced || 0} signals bought &mdash;
           ${b.pnl_without_top_pct == null ? "&mdash;"
             : pct(b.pnl_without_top_pct)} without the best ${b.top || 5},
           of which ${esc(best.symbol || "?")} ${pct(best.return_pct)}`)}
        ${card("the median signal", big(b.median_pct),
          `${b.winners || 0} up, ${b.losers || 0} down &mdash; worst
           ${esc(worst.symbol || "?")} ${pct(worst.return_pct)}`)}
        ${card(`conviction &ge;&nbsp;${hc.min != null ? hc.min : 70} only`,
          // Once only tradeable coins count, their own high-conviction
          // signals are a handful. A hero number off four rows is the
          // defect this whole panel was rewritten to stop, so below ten it
          // is drawn grey and the count takes its place.
          (hc.n || 0) < 10 ? `<span class="mc-flat">n&nbsp;=&nbsp;${hc.n || 0}</span>`
                           : big(hc.pnl_pct),
          (hc.n || 0) < 10
            ? `too few to mean anything &mdash; they would have returned
               ${pct(hc.pnl_pct)}`
            : `${hc.n} of those signals &mdash; ${pct(hc.median_pct)} median,
               ${hc.pnl_without_top_pct == null ? "&mdash;"
                 : pct(hc.pnl_without_top_pct)} without its best ${b.top || 5}`)}
      </div>
      <dl class="mc-figs">
        <div><dt>signals tracked</dt><dd>${b.tracked || fm.tracked || 0}</dd></div>
        <div><dt>dropped as untradeable</dt><dd>${b.n_untradeable || 0}
          <span class="mc-of">pool under $${b.min_liquidity || 0}</span></dd></div>
        <div><dt>depth not known</dt><dd>${b.n_depth_unknown || 0}
          <span class="mc-of">kept; never quoted</span></dd></div>
        <div><dt>no price when it fired</dt><dd>${b.n_unpriced || 0}
          <span class="mc-of">never in any figure</span></dd></div>
        <div><dt>same price read twice</dt><dd>${b.stale_readings || 0}
          <span class="mc-of">of ${(b.stale_readings || 0) + (b.fresh_readings || 0)} readings</span></dd></div>
        ${fig(`hit &ge;&nbsp;${thr}% at 1 h`, first)}
        ${fig(`hit &ge;&nbsp;${thr}% at 24 h`, day)}
        <div><dt>median at 1 h</dt><dd>${pct(first.median_pct)}</dd></div>
      </dl>
      <p class="blurb">Only coins somebody could actually buy and sell are
      counted &mdash; a pair needs $${b.min_liquidity || 0} of liquidity and
      as much traded in a day, or it is dropped. Half the tokens their signal
      flags are dust ($0.00 to $15 a pool) and they carried the whole of the
      good news. Return is <strong>ours</strong>: the signal's own price
      against each hour after it, never their rolling window.</p>
    </header>
    ${rows ? `<div class="mc-table"><h3>The ${
        (fm.curves || []).length} biggest movers of ${fm.curves_total || 0}
        curves &mdash; by peak, so this table is winners by construction.</h3>
      <table class="mc-list"><thead><tr>
        <th>token</th><th>conviction</th>
        <th>now</th><th>peak after signal</th>
        <th>first 24 hours</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`
    : `<p class="blurb">Tracking signals; none has reached its first
       checkpoint (1h) yet.</p>`}`;
}


document.getElementById("memecoins").innerHTML = memecoinPanel();

/* The hover bubble. Delegated, so it keeps working after a re-render, and
   positioned in viewport coordinates because the panel scrolls. */
(function () {
  const tip = document.getElementById("mcTip");
  const host = document.getElementById("memecoins");
  if (!tip || !host) return;
  const place = e => {
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let left = e.clientX + 16, top = e.clientY - h - 12;
    if (left + w > innerWidth - 8) left = e.clientX - w - 16;
    if (top < 8) top = e.clientY + 18;
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  };
  host.addEventListener("mousemove", e => {
    const pt = e.target.closest(".mc-pt");
    if (!pt) { tip.hidden = true; return; }
    const v = Number(pt.dataset.v);
    tip.innerHTML = `<div class="mc-th">hour ${esc(pt.dataset.h)} after the signal</div>
      <div class="mc-tv ${v > 0 ? "mc-up" : (v < 0 ? "mc-down" : "mc-flat")}">${
        (v > 0 ? "+" : "") + v.toFixed(1)}%</div>`;
    tip.hidden = false;
    place(e);
  });
  host.addEventListener("mouseleave", () => { tip.hidden = true; });
})();


/* ---------- live: the rooms redraw on their own event ----------
   Only when served by scripts/serve.py. A change to the console's own page
   is not this page's business; the rooms are. */
(function live() {
  const dot = document.createElement("span");
  dot.className = "live";
  dot.innerHTML = '<i></i><span>static</span>';
  const meta = document.getElementById("meta");
  if (meta) meta.appendChild(dot);
  const LOCAL = ["127.0.0.1", "localhost", "[::1]"];
  if (!window.EventSource || !LOCAL.includes(location.hostname)) return;
  let src;
  try { src = new EventSource("/events"); } catch (_) { return; }
  const on = () => { dot.className = "live on"; dot.innerHTML = '<i></i><span>live</span>'; };
  src.addEventListener("hello", () => { on(); loadRooms(); });
  src.addEventListener("rooms", () => loadRooms());
  src.onerror = () => { dot.className = "live off";
                        dot.innerHTML = '<i></i><span>reconnecting</span>'; };
  window.addEventListener("beforeunload", () => src.close());
})();
</script>
"""
