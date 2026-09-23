"""The laboratory's page, served at /lab and never committed.

Plan v2, V4 (docs/laborator-plan.md), redone after the operator gave the first
version 3/10 on 2026-09-23: "1 room na odvetvi ... musim moc scrollovat,
neprehledne". Four sector rooms -- Karty, Boti, Memecoiny, Fondy -- always in
sight at the top with what each made after costs; the chosen one below as a
ranking of its experiments, the failures folded into an archive, one click
opening an experiment into its chart and four numbers. The conversation with
Nexus, which they said they will hardly read, is behind a button.

Everything here used to be two tabs of the committed console. Every figure
comes from a gitignored diary, so the page is rendered on request by
scripts/serve.py and written nowhere (D2 of the 2026-09-23 review).

What the page reaches: /lab.json (build_lab, below) to redraw in place,
/token and POST /notes -- the one write, through qa.rooms.add_operator_note,
behind the guards serve.py holds -- and /events for "the rooms moved".
build_rooms() is still the one reading of the rooms; scripts/rooms.py and the
sampler's tests stand on it, and lab_view() only regroups it.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
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
                                      **{room: [] for room in store.SECTORS},
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

    from qa.fomo import curves

    # What the room concludes is the report's ($10 into every hot signal,
    # qa/lab_report.py); this is only the list under it -- what the coins
    # DID. Trimmed HERE rather than inside, so the page can say how many it
    # is not showing: a table of winners that does not say it is one is the
    # whole of "looks too promising". And over coins that stayed on one pair:
    # a switched pair is their terminal's bug, not a coin that moved.
    drawn = curves(_pair_clean(rows), limit=None)
    return {"curves": drawn[:40], "curves_total": len(drawn)}


def _pair_clean(rows: list[dict]) -> list[dict]:
    """The memecoin diary without the signals whose readings came back on a
    different pair of the same address (qa.fomo.pair_changed, the report we
    owe them from MSG-0045) -- JUP read at 0.28 and at 1 437 USD is not a
    +500 000 % mover."""
    from qa.fomo import pair_changed

    readings: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("key") and row.get("type") in ("signal", "checkpoint"):
            readings.setdefault(str(row["key"]), []).append(row)
    switched = set()
    for key, found in readings.items():
        ordered = ([r for r in found if r.get("type") == "signal"][:1]
                   + sorted((r for r in found if r.get("type") == "checkpoint"),
                            key=lambda r: str(r.get("at") or "")))
        if pair_changed(ordered):
            switched.add(key)
    return [r for r in rows if str(r.get("key")) not in switched]


def _lab_script():
    spec = importlib.util.spec_from_file_location(
        "lab_for_page", REPO_ROOT / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The view: one room per sector, results first
# ---------------------------------------------------------------------------
# The operator, 2026-09-23, on the first /lab: "proc ma kazda karta svuj
# room? ja myslel ze bude 1 room na odvetvi". So the page draws four sector
# rooms, each a ranking of its experiments; the rooms build_rooms() writes
# per experiment are the rows of those rankings, and their threads sit behind
# the page's conversation button.

SECTOR_NAMES = {"cards": "Karty", "bots": "Boti", "memecoins": "Memecoiny",
                "funds": "Fondy"}
SECTORS = tuple(SECTOR_NAMES)
# Points on a row's small line, and on an opened experiment's chart.
SPARK_POINTS = 40
PATH_POINTS = 160
MOVERS = 40

_DRAWDOWN = re.compile(r"drawdown reached ([\d.]+)%, past the ([\d.]+)%")
_AGAINST = re.compile(r"against the benchmark's ([+\-]?[\d.]+)%")


def _thin(points: list, keep: int) -> list:
    """Evenly spaced points, the first and the last always kept."""
    if len(points) <= keep:
        return list(points)
    step = (len(points) - 1) / (keep - 1)
    return [points[round(i * step)] for i in range(keep)]


def _cz(value: float, digits: int = 1) -> str:
    """-11.78 -> "−11,8": the operator's decimal comma and a real minus."""
    text = f"{abs(value):.{digits}f}".replace(".", ",")
    return ("−" if value < 0 and text.strip("0,") else "") + text


def _signed(value: float, digits: int = 1) -> str:
    return ("+" if value > 0 else "") + _cz(value, digits)


def _level(text: str) -> str:
    """10.00 -> "10", 11.78 -> "11,8"."""
    value = float(text)
    return _cz(value, 0 if value == round(value) else 1)


def _path(panel: dict) -> list[list]:
    """What an experiment is worth, in % since we went in, over time.

    A card: its index rebased on the index we bought at (V2's book), from our
    buy to our sale, so the last point is our result before costs. A bot:
    what their engine booked over what went in. A fund only marked: nothing
    of ours is in it, so no line.
    """
    legs = [leg for leg in panel.get("legs") or [] if leg.get("series")]
    if legs:
        leg = legs[0]
        trades = panel.get("trades") or []
        bought = min((m for m in (_moment(t.get("at")) for t in trades
                                  if t.get("outcome") == "accepted") if m),
                     default=None)
        sold = max((m for m in (_moment(t.get("closed_at")) for t in trades) if m),
                   default=None)
        points = []
        for stamp_, value in leg["series"]:
            when = _moment(stamp_)
            if when is None or not isinstance(value, (int, float)):
                continue
            if (bought and when < bought) or (sold and when > sold):
                continue
            points.append((stamp_, float(value)))
        entry = leg.get("entry")
        base = (float(entry) if isinstance(entry, (int, float)) and entry
                else (points[0][1] if points else None))
        if not base:
            return []
        return [[t, round((v / base - 1.0) * 100.0, 3)] for t, v in points]
    for clone in panel.get("clones") or []:
        funded = clone.get("funded")
        if funded:
            return [[s.get("at"), round(float(s["pnl"]) / float(funded) * 100.0, 3)]
                    for s in clone.get("samples") or []
                    if isinstance(s.get("pnl"), (int, float))]
    return []


def _group(report_room: dict, panel: dict) -> str:
    """live: still running; done: judged or stopped; archive: what the report
    archives -- nothing bought, or not his pick (N-0049/N-0050: a failed
    attempt out of the way, but not deleted)."""
    if report_room.get("archived"):
        return "archive"
    if (panel.get("verdict") or {}).get("verdict") or panel.get("status") == "stopped":
        return "done"
    return "live"


def _reason(group: str, panel: dict) -> str | None:
    """A few Czech words for why it stands where it does -- never the
    verdict's English paragraph (N-0032, N-0034: "kdo to má číst?")."""
    verdict = panel.get("verdict") or {}
    name, why = verdict.get("verdict"), str(verdict.get("why") or "")
    ret = verdict.get("return_pct")
    if group == "archive":
        return "Nexus to nevybral" if panel.get("invested") else "nic se nekoupilo"
    if name == "survived":
        return f"vydělal {_signed(ret)} %" if ret is not None else None
    if name == "refuted":
        found = _DRAWDOWN.search(why)
        if found:
            return (f"propad {_level(found.group(1))} % přes limit "
                    f"{_level(found.group(2))} %")
        found = _AGAINST.search(why)
        if found:
            return f"horší než BTC ({_signed(float(found.group(1)))} %)"
        return f"skončil {_signed(ret)} %" if ret is not None else None
    if name == "inconclusive":
        return ("nelze porovnat s BTC" if "benchmark" in why
                else "málo dat k posouzení")
    clones = panel.get("clones") or []
    if clones and clones[-1].get("trading") is False and panel.get("status") == "running":
        return "zastavil se sám"
    return None


def _experiment(rid: str, sector: str, report_room: dict, panel: dict,
                now: datetime) -> dict:
    group = _group(report_room, panel)
    path = _path(panel)
    legs = panel.get("legs") or []
    first = legs[0] if legs else {}
    clones = panel.get("clones") or []
    tested = next((b for b in panel.get("backtests") or [] if b), None)
    criterion = panel.get("criterion") or {}
    start, window = _moment(criterion.get("at")), criterion.get("window_days")
    ends = (start + timedelta(days=float(window))) if start and window else None
    return {
        "id": rid, "sector": sector, "group": group,
        "title": panel.get("title") or rid, "status": panel.get("status"),
        "verdict": (panel.get("verdict") or {}).get("verdict"),
        "net_pct": report_room.get("net_pct"), "usdc": report_room.get("usdc"),
        "stake": report_room.get("stake_usdc"),
        "reason": _reason(group, panel),
        "path": _thin(path, PATH_POINTS), "spark": _thin(path, SPARK_POINTS),
        "backtest": ({"pct": tested.get("return_pct"), "period": tested.get("period"),
                      "sharpe": tested.get("sharpe"),
                      "pass": tested.get("verdict") == "pass"} if tested else None),
        "left_days": ((ends - now).total_seconds() / 86400.0
                      if ends and group == "live" else None),
        "ends_at": ends.isoformat() if ends else None,
        "opened_at": panel.get("opened_at"), "origin": panel.get("origin"),
        "url": first.get("url"),
        "trading": clones[-1].get("trading") if clones else None,
        "tp": first.get("tp"), "sl": first.get("sl")}


def lab_view(rooms: dict, report: dict, channel: dict, fomo: dict | None,
             now: datetime | None = None) -> dict:
    """What /lab draws, joined in one place so a test can hold all of it:
    the four sectors with the report's figures, every experiment as a row of
    its sector's ranking, the Nexus line, the paper account, the threads for
    the conversation drawer and the memecoin movers. Pure."""
    moment = now or datetime.now(timezone.utc)
    products = report.get("products") or {}
    by_id = {r.get("id"): r for r in report.get("rooms") or []}
    panels = rooms.get("panels") or {}
    experiments = []
    for room in rooms.get("rooms") or []:
        rid = room.get("id")
        report_room = by_id.get(rid) or {}
        sector = report_room.get("product")
        if room.get("kind") != "strategy" or sector not in SECTOR_NAMES:
            continue
        experiments.append(_experiment(rid, sector, report_room,
                                       panels.get(rid) or {}, moment))
    general = panels.get("general") or {}
    in_bots = sum(float((panels.get(e["id"], {}).get("clones") or [{}])[-1]
                        .get("balance") or 0)
                  for e in experiments
                  if e["sector"] == "bots" and e["group"] != "archive")
    return {
        "generated_at": report.get("generated_at"),
        "sectors": [{"key": key, "name": name, **(products.get(key) or {})}
                    for key, name in SECTOR_NAMES.items()],
        "experiments": experiments,
        "nexus": {**(report.get("nexus") or {}),
                  **{k: (channel or {}).get(k) for k in
                     ("median_seconds", "measured", "failed", "refused")}},
        "account": {"free": general.get("balance"),
                    "in_cards": general.get("notional"),
                    "in_bots": round(in_bots, 2) or None,
                    "at": general.get("balance_at"), "stale": general.get("stale")},
        "threads": rooms.get("threads") or {},
        "movers": ((fomo or {}).get("curves") or [])[:MOVERS],
        "movers_total": (fomo or {}).get("curves_total") or 0,
    }


def build_lab(now=None) -> dict:
    """The view, now: the report rewritten (state/lab/report.json), the rooms,
    Nexus's channel and the memecoin diary. What /lab embeds and /lab.json
    answers."""
    moment = now or datetime.now(timezone.utc)
    return lab_view(build_rooms(), _lab_script().write_report(moment),
                    _nexus_channel(), _fomo_stats() or {}, now=moment)


def render_lab(data: dict | None = None) -> str:
    data = data if data is not None else build_lab()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", blob)


TEMPLATE = r"""<!doctype html>
<html lang="cs">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Laboratoř</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* [hidden] first: a class with display set must never beat it. */
[hidden] { display: none !important; }

/* One set of tokens, light and dark, the console's own surfaces. Sector hues
   are the reference categorical slots in the order that passes the dataviz
   validator on both surfaces (blue, amber, violet, pink); they mark identity
   only -- a tab's edge, a dot -- and never colour a number. Green and red
   are for money: a gain and a loss. */
:root {
  --bg:#f3f5f4; --surface:#ffffff; --surface-2:#eef1f0; --surface-3:#e4e9e7;
  --line:#d9dfdd; --line-soft:#e8ecea;
  --text:#0f1719; --text-dim:#56676a; --text-faint:#8a999a;
  --ok:#17803d; --ok-bg:#17803d17; --bad:#b3261e; --bad-bg:#b3261e14;
  --accent:#0d6b66;
  --c-cards:#2a78d6; --c-bots:#eda100; --c-memecoins:#4a3aa7; --c-funds:#e87ba4;
  --shadow:0 1px 2px rgba(15,23,25,.06), 0 8px 24px rgba(15,23,25,.06);
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#0b1113; --surface:#121b1d; --surface-2:#18231f; --surface-3:#1f2c2e;
    --line:#243436; --line-soft:#1b282a;
    --text:#e6eeec; --text-dim:#98aaa9; --text-faint:#687a7b;
    --ok:#4ec97a; --ok-bg:#4ec97a1c; --bad:#f2685e; --bad-bg:#f2685e1c;
    --accent:#4ecfc4;
    --c-cards:#3987e5; --c-bots:#c98500; --c-memecoins:#9085e9; --c-funds:#d55181;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.25);
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg:#0b1113; --surface:#121b1d; --surface-2:#18231f; --surface-3:#1f2c2e;
  --line:#243436; --line-soft:#1b282a;
  --text:#e6eeec; --text-dim:#98aaa9; --text-faint:#687a7b;
  --ok:#4ec97a; --ok-bg:#4ec97a1c; --bad:#f2685e; --bad-bg:#f2685e1c;
  --accent:#4ecfc4;
  --c-cards:#3987e5; --c-bots:#c98500; --c-memecoins:#9085e9; --c-funds:#d55181;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.25);
  color-scheme: dark;
}

* { box-sizing: border-box; }
html, body { margin: 0; }
body { background: var(--bg); color: var(--text); font: 15px/1.45 var(--sans);
  -webkit-font-smoothing: antialiased; }
button { font: inherit; color: inherit; }
.up { color: var(--ok); } .down { color: var(--bad); } .flat { color: var(--text-faint); }

.app { max-width: 1480px; margin: 0 auto; padding: 20px 28px 36px;
  display: flex; flex-direction: column; gap: 14px; }

/* ---------- the bar across the top ---------- */
.top { display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; }
.brand h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -.015em; }
.brand p { margin: 2px 0 0; font-size: 13px; color: var(--text-dim); }
.brand p b { color: var(--text); font-weight: 600; }
.brand .warn { color: var(--bad); font-weight: 600; }
.top-r { display: flex; align-items: center; gap: 10px; }
.btn { display: inline-flex; align-items: center; gap: 6px; font-size: 14px;
  padding: 7px 14px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--surface); color: var(--text); cursor: pointer; text-decoration: none; }
.btn:hover { border-color: var(--text-faint); }
.btn:focus-visible, .sec:focus-visible, .row:focus-visible, .seg button:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px; }
.live { font: 12px var(--mono); color: var(--text-faint); display: inline-flex;
  align-items: center; gap: 6px; }
.live i { width: 7px; height: 7px; border-radius: 50%; background: var(--text-faint); }
.live.on i { background: var(--ok); } .live.off i { background: var(--bad); }

/* ---------- the four sector rooms, always in sight ---------- */
.sectors { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.sec { position: relative; text-align: left; cursor: pointer; background: var(--surface);
  border: 1px solid var(--line); border-radius: 14px; padding: 13px 16px 12px 20px;
  display: flex; flex-direction: column; gap: 1px; min-width: 0;
  transition: border-color .15s, box-shadow .15s, transform .15s; }
.sec::before { content: ""; position: absolute; left: 0; top: 12px; bottom: 12px;
  width: 4px; border-radius: 0 4px 4px 0; background: var(--hue); }
.sec:hover { border-color: var(--text-faint); }
.sec[aria-selected="true"] { border-color: var(--hue); box-shadow: 0 0 0 1px var(--hue), var(--shadow); }
.sec-name { font-size: 12.5px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--text-dim); }
.sec-val { font-size: 30px; font-weight: 700; line-height: 1.15; letter-spacing: -.015em;
  white-space: nowrap; }
.sec-mid { font-size: 14px; font-weight: 600; color: var(--text-dim); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.sec-foot { font-size: 12.5px; color: var(--text-faint); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }

.nexus { margin: 0; font-size: 14px; color: var(--text-dim); line-height: 1.6; }
.nexus b { color: var(--text); font-variant-numeric: tabular-nums; }
.nexus b.up { color: var(--ok); }
.nexus .ar { color: var(--text-faint); margin: 0 3px; }
.nexus small { color: var(--text-faint); font-size: 12.5px; }
.nx-tag { display: inline-block; font-size: 11.5px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--text-dim); background: var(--surface-2);
  border-radius: 6px; padding: 1px 7px; margin-right: 4px; }

/* ---------- a room: its number, then its ranking ---------- */
.room { background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
  padding: 20px 22px 14px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: var(--shadow); border-top: 3px solid var(--hue); }
.room-head { display: flex; align-items: flex-end; gap: 22px; flex-wrap: wrap; }
.hero { font-size: 52px; font-weight: 700; line-height: .95; letter-spacing: -.025em;
  white-space: nowrap; }
.hero-side { display: flex; flex-direction: column; gap: 5px; padding-bottom: 3px; min-width: 0; }
.hero-l1 { font-size: 15px; color: var(--text-dim); }
.hero-l1 b { color: var(--text); font-weight: 600; }
.hero-l1 b.up { color: var(--ok); } .hero-l1 b.down { color: var(--bad); }
.hero-l2 { font-size: 14px; color: var(--text-dim); display: flex; align-items: center;
  gap: 8px; flex-wrap: wrap; }
.hero-l2 small { color: var(--text-faint); font-size: 12.5px; }
.conf { display: inline-block; padding: 2px 10px; border-radius: 999px; font-weight: 600;
  font-size: 13px; background: var(--surface-2); color: var(--text-dim); }
.conf.up { background: var(--ok-bg); color: var(--ok); }
.conf.down { background: var(--bad-bg); color: var(--bad); }

.bar { display: flex; align-items: center; justify-content: space-between; gap: 12px;
  flex-wrap: wrap; }
.seg { display: inline-flex; gap: 3px; padding: 3px; border-radius: 999px;
  background: var(--surface-2); }
.seg button { border: 0; background: none; color: var(--text-dim); padding: 6px 15px;
  border-radius: 999px; cursor: pointer; font-size: 14px; }
.seg button:hover { color: var(--text); }
.seg button[aria-selected="true"] { background: var(--surface); color: var(--text);
  font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.18); }
.seg .n { margin-left: 6px; color: var(--text-faint); font-variant-numeric: tabular-nums;
  font-weight: 500; }
.bar-hint { font-size: 12.5px; color: var(--text-faint); }

.board { list-style: none; margin: 0; padding: 0; }
.row { display: grid; grid-template-columns: 26px minmax(0, 1fr) 110px 88px 80px 132px 250px 14px;
  align-items: center; gap: 12px; padding: 8px 10px; border-radius: 10px; cursor: pointer;
  min-height: 46px; }
.board > li + li.row { border-top: 1px solid var(--line-soft); }
.row:hover, .row.open { background: var(--surface-2); }
.row.open { border-radius: 10px 10px 0 0; }
.rk { font: 500 13px var(--mono); color: var(--text-faint); text-align: right; }
.nm { font-weight: 600; font-size: 15px; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.val { font-size: 18px; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums;
  white-space: nowrap; }
.usd { font-size: 13.5px; text-align: right; font-variant-numeric: tabular-nums;
  white-space: nowrap; }
.bt, .st { display: flex; gap: 6px; min-width: 0; overflow: hidden; }
.chev { color: var(--text-faint); font-size: 16px; }
.chip { font-size: 12.5px; padding: 2px 9px; border-radius: 999px; background: var(--surface-3);
  color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 100%; }
.chip.up { background: var(--ok-bg); color: var(--ok); }
.chip.down { background: var(--bad-bg); color: var(--bad); }
.spark { width: 110px; height: 28px; display: block; overflow: visible; }
.sp-zero { stroke: var(--line); stroke-width: 1; }
.sp-none { color: var(--text-faint); }
.more { align-self: flex-start; border: 0; background: none; color: var(--accent);
  cursor: pointer; font-size: 14px; font-weight: 600; padding: 4px 10px; }
.empty { margin: 0; padding: 26px 10px; color: var(--text-faint); font-size: 15px; }

/* An opened experiment: its line over time, and four numbers beside it. */
.detail { background: var(--surface-2); border-radius: 0 0 10px 10px; padding: 6px 14px 16px 48px;
  margin-bottom: 6px; }
.dt { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr); gap: 22px;
  align-items: start; }
.dt-chart { margin: 0; min-width: 0; }
.dt-chart svg { width: 100%; height: auto; display: block; overflow: visible; }
.dt-empty { padding: 30px 0; color: var(--text-faint); }
.ax text { font: 11.5px var(--sans); fill: var(--text-faint); }
.ax line { stroke: var(--line-soft); stroke-width: 1; }
.ax .zero { stroke: var(--line); }
.lvl { stroke-width: 1.5; stroke-dasharray: 5 4; }
.lvl-tp { stroke: var(--ok); } .lvl-sl { stroke: var(--bad); }
.lvl-t { font: 600 11.5px var(--sans); }
.xh { stroke: var(--text-faint); stroke-width: 1; }
.tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.tile { background: var(--surface); border: 1px solid var(--line-soft); border-radius: 10px;
  padding: 10px 12px; min-width: 0; }
.tile span { display: block; font-size: 12.5px; color: var(--text-dim); }
.tile b { display: block; font-size: 22px; font-weight: 700; line-height: 1.25;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile i { display: block; font-style: normal; font-size: 12.5px; color: var(--text-faint);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meter { height: 6px; border-radius: 3px; background: var(--surface-3); margin-top: 7px;
  overflow: hidden; }
.meter s { display: block; height: 100%; background: var(--accent); border-radius: 3px; }
.dt-facts { margin: 12px 0 0; font-size: 13px; color: var(--text-dim); }
.dt-links { display: flex; gap: 16px; margin-top: 8px; font-size: 14px; flex-wrap: wrap; }
.dt-links a, .linkish { color: var(--accent); text-decoration: none; background: none;
  border: 0; padding: 0; cursor: pointer; font-weight: 600; }

/* ---------- the memecoin room ---------- */
.m-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.filt { margin: 0; font-size: 12.5px; color: var(--text-faint); }
.movers h3 { margin: 4px 0 8px; font-size: 15px; }
.movers h3 small { font-weight: 400; color: var(--text-faint); font-size: 12.5px; margin-left: 6px; }
.mc-list { width: 100%; border-collapse: collapse; }
.mc-list th { text-align: left; font-size: 12px; font-weight: 600; color: var(--text-faint);
  text-transform: uppercase; letter-spacing: .05em; padding: 4px 10px; }
.mc-list th:nth-child(3), .mc-list th:nth-child(4) { text-align: right; }
.mc-list td { padding: 3px 10px; border-top: 1px solid var(--line-soft); }
.mc-sym { font-weight: 600; }
.mc-conv { color: var(--text-dim); font-variant-numeric: tabular-nums; }
.mc-ret { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.mc-up { color: var(--ok); } .mc-down { color: var(--bad); } .mc-flat { color: var(--text-faint); }
.mc-g { width: 170px; }
.mc-spark { display: block; width: 150px; height: 30px; overflow: visible; }
.mc-pt { cursor: crosshair; }

/* Our own bubble -- the browser's title tooltip is small, grey and late. */
.tip { position: fixed; z-index: 80; pointer-events: none; background: var(--surface);
  border: 1px solid var(--line); border-radius: 10px; padding: 8px 12px;
  box-shadow: var(--shadow); min-width: 120px; }
.tip-h { font-size: 12px; color: var(--text-dim); }
.tip-v { font-size: 22px; font-weight: 700; line-height: 1.2; }

/* ---------- the conversation, behind its button ---------- */
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(560px, 100vw);
  background: var(--surface); border-left: 1px solid var(--line); z-index: 60;
  display: flex; flex-direction: column; box-shadow: -18px 0 40px rgba(0,0,0,.28); }
.dr-head { display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 14px 18px 10px; }
.dr-head h2 { margin: 0; font-size: 17px; }
.dr-scope { display: flex; gap: 6px; flex-wrap: wrap; padding: 0 18px 10px;
  border-bottom: 1px solid var(--line); }
.dr-scope button { border: 1px solid var(--line); background: none; border-radius: 999px;
  padding: 3px 11px; font-size: 13px; cursor: pointer; color: var(--text-dim); }
.dr-scope button[aria-pressed="true"] { background: var(--surface-3); color: var(--text);
  border-color: var(--text-faint); }
.thread { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 14px 18px 18px;
  display: flex; flex-direction: column; gap: 10px; }
.th-room { font-size: 12px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;
  letter-spacing: .05em; margin-top: 8px; }
.compose { flex: none; display: flex; flex-direction: column; gap: 6px; padding: 12px 18px 14px;
  border-top: 1px solid var(--line); background: var(--surface-2); }
.compose textarea { width: 100%; resize: vertical; min-height: 3.2em; font: inherit;
  color: var(--text); background: var(--surface); border: 1px solid var(--line);
  border-radius: 8px; padding: .5rem .65rem; }
.send { display: flex; justify-content: space-between; align-items: center; gap: 10px;
  font-size: 12.5px; color: var(--text-dim); }
.send button { padding: 6px 16px; border-radius: 999px; border: 0; background: var(--accent);
  color: var(--surface); font-weight: 600; cursor: pointer; }
.send button:disabled { opacity: .5; cursor: default; }
.nx-msg { border: 1px solid var(--line); border-radius: 12px; padding: .6rem .8rem;
  background: var(--surface); max-width: 94%; align-self: flex-start; }
.nx-msg.nx-ours { align-self: flex-end; background: var(--surface-2); }
.nx-msg.nx-op { align-self: flex-end; border-color: var(--accent); }
.nx-msg.nx-cl { background: var(--surface-2); }
.nx-msg.nx-sys { align-self: center; border: 0; background: none; padding: 0 .6rem;
  color: var(--text-faint); font-size: 12.5px; text-align: center; }
.nx-msg.nx-failed, .nx-msg.nx-refused { border-color: var(--bad); }
.nx-h { font-size: 12px; color: var(--text-dim); margin-bottom: .3rem; }
.nx-h b { color: var(--text); }
.nx-s { font-size: 12.5px; color: var(--text-dim); font-style: italic; }
.nx-b { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14px; }
.nx-b.nx-clamp { max-height: 7.5em; overflow: hidden;
  -webkit-mask-image: linear-gradient(#000 60%, transparent); mask-image: linear-gradient(#000 60%, transparent); }
.nx-b code { font-family: var(--mono); font-size: .9em; background: var(--surface-2);
  padding: 0 .2em; border-radius: 3px; }
.nx-more, .nx-goto { background: none; border: 0; color: var(--accent); cursor: pointer;
  padding: 0; font-size: 12.5px; }
.nx-gist { margin: 0 0 .4rem; padding: .35rem .6rem; border-left: 3px solid var(--accent);
  background: var(--surface-2); border-radius: 0 6px 6px 0; font-size: 13.5px; }
.nx-tick { color: var(--ok); margin-left: .3rem; }

@media (max-width: 1180px) {
  .row { grid-template-columns: 22px minmax(0, 1fr) 90px 80px 120px 14px; }
  .row .usd, .row .st { display: none; }
  .dt { grid-template-columns: 1fr; }
  .m-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .app { padding: 14px 16px 28px; }
  .sectors { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sec-val { font-size: 24px; }
  .hero { font-size: 40px; }
  .row { grid-template-columns: minmax(0, 1fr) 76px 12px; gap: 8px; }
  .row .rk, .row .sp, .row .bt { display: none; }
  .detail { padding-left: 12px; }
  .top-r .live { display: none; }
  .mc-g { width: auto; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>

<div class="app" id="app">
  <header class="top">
    <div class="brand">
      <h1>Laboratoř</h1>
      <p id="account">Papírové obchody podle Nexuse · čísla po poplatcích</p>
    </div>
    <div class="top-r">
      <span class="live" id="live"><i></i><span>statická</span></span>
      <button class="btn" type="button" id="chatBtn">💬 Konverzace</button>
      <a class="btn" href="/">← Konzole</a>
    </div>
  </header>
  <nav class="sectors" id="sectors" role="tablist" aria-label="Odvětví"></nav>
  <p class="nexus" id="nexus"></p>
  <main class="room" id="room"></main>
</div>

<aside class="drawer" id="drawer" hidden aria-label="Konverzace">
  <div class="dr-head"><h2 id="drTitle">Konverzace</h2>
    <button class="btn" type="button" id="drClose">Zavřít ✕</button></div>
  <div class="dr-scope" id="drScope"></div>
  <div class="thread" id="thread"></div>
  <form class="compose" id="compose">
    <textarea id="draft" rows="2" maxlength="4000"
      placeholder="Poznámka pro Clauda k tomuhle roomu — přečte si ji, až mu napíšeš „přečti si to“."></textarea>
    <div class="send"><span id="sendNote">Ctrl+Enter odešle</span>
      <button type="submit" id="send">Poslat</button></div>
  </form>
</aside>
<div class="tip" id="tip" hidden></div>

<script id="data" type="application/json">__DATA__</script>
<script>
let V = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g,
  c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const stamp = t => t ? String(t).replace("T", " ").slice(0, 16) : "";
// localStorage is a convenience here, never state.
function readStore(key, dflt) {
  try { const v = localStorage.getItem(key); return v === null ? dflt : v; }
  catch (_) { return dflt; }
}
function writeStore(key, value) {
  try { localStorage.setItem(key, String(value)); } catch (_) {}
}
const LOCAL = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
const SECTORS = ["cards", "bots", "memecoins", "funds"];
const GROUPS = [["live", "Běží"], ["done", "Vyhodnoceno"], ["archive", "Archiv"]];
const EMPTY = {live: "Teď tu nic neběží.", done: "Zatím nic vyhodnoceného.",
               archive: "Archiv je prázdný."};
const TOP = 10;

/* ---------- numbers, the way the operator reads them ----------
   A decimal comma, a real minus, a space before %, and as many decimals as
   the size of the number needs. The page names its shapes -- `lp.` a sector,
   `le.` an experiment, `lb.` its backtest, `ln.` the Nexus line, `la.` the
   account -- and tests/meta/test_pipeline_lab_page.py holds every one against
   what lab_view() writes, in both directions. */
// A number never breaks across a line: no-break spaces between its thousands
// and before its unit ("1 414 $" once wrapped as "1 414" / "$" on a phone).
const NB = " ";
function num(v, digits) {
  const n = Number(v), fixed = Math.abs(n).toFixed(digits), parts = fixed.split(".");
  return (n < 0 && Number(fixed) !== 0 ? "−" : "") +
    parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, NB) + (parts[1] ? "," + parts[1] : "");
}
function places(v) { const a = Math.abs(v); return a >= 100 ? 0 : a >= 10 ? 1 : 2; }
function pctText(v, digits) {
  if (v == null || isNaN(v)) return "—";
  const d = digits == null ? places(v) : digits;
  return (v > 0 && Number(Math.abs(v).toFixed(d)) !== 0 ? "+" : "") + num(v, d) + NB + "%";
}
function usdText(v) {
  if (v == null || isNaN(v)) return "—";
  const d = Math.abs(v) >= 100 ? 0 : 2;
  return (v > 0 && Number(Math.abs(v).toFixed(d)) !== 0 ? "+" : "") + num(v, d) + NB + "$";
}
function money(v) { return v == null || isNaN(v) ? "—" : num(v, Math.abs(v) >= 100 ? 0 : 2) + NB + "$"; }
function tone(v) { return v == null || isNaN(v) ? "flat" : v > 0 ? "up" : v < 0 ? "down" : "flat"; }
function plural(n, one, few, many) { return n === 1 ? one : (n >= 2 && n <= 4) ? few : many; }
function day(iso) {
  const d = new Date(iso);
  return isNaN(d) ? "" : d.getDate() + ". " + (d.getMonth() + 1) + ".";
}
function clock(iso) {
  const d = new Date(iso);
  return isNaN(d) ? "" : day(iso) + " " + String(d.getHours()).padStart(2, "0") + ":" +
    String(d.getMinutes()).padStart(2, "0");
}
function leftText(v) {
  if (v == null) return "";
  if (v <= 0) return "vyhodnocení dnes";
  if (v < 1) return "zbývá " + Math.max(1, Math.round(v * 24)) + " h";
  return "zbývá " + Math.round(v) + " d";
}
function chip(cls, text) { return `<span class="chip ${cls}">${text}</span>`; }

function sectorOf(key) {
  return (V.sectors || []).find(lp => lp.key === key) || {key: key, name: key};
}

/* ---------- the top: the account and the four rooms ---------- */
function accountLine(la) {
  if (!la || la.free == null) return "Papírové obchody podle Nexuse · čísla po poplatcích";
  return `Papírový účet: <b>${money(la.free)}</b> volné · ${money(la.in_cards)} v kartách · ` +
    `${money(la.in_bots)} v botech` + (la.at ? ` <span class="flat">(${clock(la.at)})</span>` : "") +
    (la.stale ? ' · <span class="warn">⚠ data z API jsou stará</span>' : "");
}
function sectorTab(lp, on) {
  const meme = lp.key === "memecoins";
  const mid = meme
    ? (lp.n ? `${num(lp.n, 0)} obchodů po 10 $` : "zatím žádný obchod")
    : lp.usdc != null ? `<span class="${tone(lp.usdc)}">${usdText(lp.usdc)}</span>`
                         + ` <span class="flat">z ${money(lp.stake_usdc)}</span>`
    : (lp.running ? "zatím bez výsledku" : "zatím nic");
  const foot = meme ? `${num(lp.running || 0, 0)} ještě čeká na celý den`
    : `${lp.n || 0} ${plural(lp.n || 0, "pokus", "pokusy", "pokusů")} · ${lp.running || 0} běží`;
  return `<button class="sec" role="tab" type="button" aria-selected="${on}"
      data-sector="${esc(lp.key)}" style="--hue:var(--c-${esc(lp.key)})">
    <span class="sec-name">${esc(lp.name)}</span>
    <span class="sec-val ${tone(lp.net_pct)}">${pctText(lp.net_pct)}</span>
    <span class="sec-mid">${mid}</span>
    <span class="sec-foot">${foot}</span></button>`;
}
function nexusLine(ln) {
  if (!ln || ln.questions == null) return "";
  const ar = '<span class="ar">→</span>';
  const took = ln.median_seconds != null
    ? ` · odpovídá za ~${Math.max(1, Math.round(ln.median_seconds / 60))} min` +
      ` <small>(změřeno ${ln.measured}×)</small>` : "";
  const quiet = (ln.failed || ln.refused)
    ? ` · <small>${ln.failed || 0} bez odpovědi, ${ln.refused || 0} odmítl</small>` : "";
  return `<span class="nx-tag">Nexus</span> <b>${ln.questions}</b> otázek ${ar} ` +
    `<b>${ln.answered}</b> odpovědí ${ar} <b>${ln.picks}</b> nápadů ${ar} ` +
    `<b>${ln.gate_pass}</b> z ${ln.gated} prošlo backtestem ${ar} ` +
    `<b class="${ln.survived ? "up" : ""}">${ln.survived}</b> vyšlo` +
    (ln.refuted ? `, ${ln.refuted} nevyšlo` : "") + took + quiet;
}

/* ---------- a room's number: how sure, in words ---------- */
function confidence(lp) {
  if (!lp.wilson) return ["flat", "málo dat na jistotu"];
  if (lp.wilson[0] > 0.5) return ["up", "spíš vydělává"];
  if (lp.wilson[1] < 0.5) return ["down", "spíš prodělává"];
  return ["flat", "zatím nerozhodnuto"];
}
function band(lp) {
  return lp.wilson
    ? `<small>${Math.round(lp.wilson[0] * 100)}–${Math.round(lp.wilson[1] * 100)} % pokusů v plusu, 95 % jistota</small>`
    : `<small>méně než ${lp.min_n} ${plural(lp.min_n, "pokus", "pokusy", "pokusů")}</small>`;
}
function roomHead(lp) {
  if (!lp.n) {
    return `<div class="room-head"><div class="hero flat">—</div><div class="hero-side">
      <div class="hero-l1">zatím žádný výsledek</div>
      <div class="hero-l2">${lp.running || 0} běží · číslo přijde, až skončí první okno</div>
      </div></div>`;
  }
  const [ct, cw] = confidence(lp);
  return `<div class="room-head">
    <div class="hero ${tone(lp.net_pct)}">${pctText(lp.net_pct)}</div>
    <div class="hero-side">
      <div class="hero-l1">průměr na pokus, po poplatcích` +
        (lp.usdc != null ? ` · celkem <b class="${tone(lp.usdc)}">${usdText(lp.usdc)}</b>` +
                           ` z ${money(lp.stake_usdc)} vložených` : "") + `</div>
      <div class="hero-l2">${lp.wins} z ${lp.n} v plusu
        <span class="conf ${ct}">${cw}</span>${band(lp)}</div>
    </div></div>`;
}

/* ---------- one experiment, one row ---------- */
const VERDICT = {survived: ["up", "✓ vyšlo"], refuted: ["down", "✗ nevyšlo"],
                 inconclusive: ["", "? nedá se říct"]};
const STATUS = {paused: "pauza", proposed: "návrh", stopped: "zastaveno"};
function btChip(lb) {
  if (!lb || lb.pct == null) return chip("", "bez backtestu");
  return chip(lb.pass ? "up" : "down", "backtest " + pctText(lb.pct, 0));
}
function stateChips(le) {
  if (le.group === "done") {
    const v = VERDICT[le.verdict] || ["", STATUS[le.status] || "ukončeno"];
    return chip(v[0], v[1]) + (le.reason ? chip("", esc(le.reason)) : "");
  }
  if (le.group === "archive") return chip("", esc(le.reason || "v archivu"));
  const out = [];
  // A bot that stopped by itself says so once, in its reason.
  if (le.trading != null && !le.reason) {
    out.push(chip(le.trading ? "up" : "", le.trading ? "obchoduje" : "stojí"));
  }
  if (le.reason) out.push(chip("down", esc(le.reason)));
  if (STATUS[le.status]) out.push(chip("", STATUS[le.status]));
  if (le.left_days != null) out.push(chip("", leftText(le.left_days)));
  return out.join("");
}
function spark(points) {
  if (!points || points.length < 2) return '<span class="sp-none">—</span>';
  const W = 110, H = 28, P = 3;
  const ts = points.map(p => Date.parse(p[0])), vs = points.map(p => p[1]);
  const t0 = Math.min(...ts), t1 = Math.max(...ts);
  const lo = Math.min(0, ...vs), hi = Math.max(0, ...vs), span = (hi - lo) || 1;
  const x = t => P + (t1 > t0 ? (t - t0) / (t1 - t0) : 0) * (W - 2 * P);
  const y = v => P + (1 - (v - lo) / span) * (H - 2 * P);
  const d = ts.map((t, i) => (i ? "L" : "M") + x(t).toFixed(1) + " " + y(vs[i]).toFixed(1)).join(" ");
  const last = vs[vs.length - 1], col = last >= 0 ? "var(--ok)" : "var(--bad)";
  const z = y(0).toFixed(1);
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" aria-hidden="true">
    <line class="sp-zero" x1="${P}" x2="${W - P}" y1="${z}" y2="${z}"/>
    <path d="${d} L${x(ts[ts.length - 1]).toFixed(1)} ${z} L${x(ts[0]).toFixed(1)} ${z}Z"
      fill="${col}" opacity=".12"/>
    <path d="${d}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round"
      stroke-linecap="round"/>
    <circle cx="${x(ts[ts.length - 1]).toFixed(1)}" cy="${y(last).toFixed(1)}" r="3.2"
      fill="${col}" stroke="var(--surface)" stroke-width="2"/></svg>`;
}
function row(le, rank, open) {
  return `<li class="row${open ? " open" : ""}" data-id="${esc(le.id)}" tabindex="0"
      role="button" aria-expanded="${open}">
    <span class="rk">${rank}</span>
    <span class="nm" title="${esc(le.title)}">${esc(le.title)}</span>
    <span class="sp">${le.group === "archive" ? '<span class="sp-none">—</span>' : spark(le.spark)}</span>
    <span class="val ${tone(le.net_pct)}">${pctText(le.net_pct)}</span>
    <span class="usd ${tone(le.usdc)}">${le.usdc == null ? "" : usdText(le.usdc)}</span>
    <span class="bt">${btChip(le.backtest)}</span>
    <span class="st">${stateChips(le)}</span>
    <span class="chev" aria-hidden="true">${open ? "▾" : "›"}</span></li>` +
    (open ? detail(le) : "");
}

/* ---------- an opened experiment ---------- */
const CHARTS = {};
function niceStep(span) {
  const raw = span / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / mag;
  return (n >= 5 ? 10 : n >= 2 ? 5 : n >= 1 ? 2 : 1) * mag;
}
function chart(le) {
  const pts = le.path || [];
  if (pts.length < 2) {
    return `<figure class="dt-chart"><div class="dt-empty">${le.sector === "funds"
      ? "Fond jen sledujeme, nic se v něm nekoupilo — čára tu zatím není."
      : "Zatím žádný průběh."}</div></figure>`;
  }
  const W = 640, H = 210, L = 50, R = 84, T = 10, B = 26;
  const ts = pts.map(p => Date.parse(p[0])), vs = pts.map(p => p[1]);
  const marks = vs.concat([0], le.tp != null ? [le.tp] : [], le.sl != null ? [le.sl] : []);
  let lo = Math.min(...marks), hi = Math.max(...marks);
  const padV = (hi - lo) * 0.08 || 1; lo -= padV; hi += padV;
  const t0 = Math.min(...ts), t1 = Math.max(...ts);
  const x = t => L + (t1 > t0 ? (t - t0) / (t1 - t0) : 0) * (W - L - R);
  const y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const step = niceStep(hi - lo), digits = step < 1 ? 1 : 0;
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v);
  const last = vs[vs.length - 1], col = last >= 0 ? "var(--ok)" : "var(--bad)";
  const d = ts.map((t, i) => (i ? "L" : "M") + x(t).toFixed(1) + " " + y(vs[i]).toFixed(1)).join(" ");
  const level = (v, cls, word) => v == null ? "" :
    `<line class="lvl ${cls}" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>
     <text class="lvl-t ${cls === "lvl-tp" ? "up" : "down"}" x="${W - R + 6}" y="${(y(v) + 4).toFixed(1)}"
       fill="currentColor">${word} ${pctText(v, 0)}</text>`;
  CHARTS[le.id] = {W: W, L: L, R: R, T: T, B: B, H: H, ts: ts, vs: vs,
                   x0: t0, x1: t1, lo: lo, hi: hi};
  return `<figure class="dt-chart"><svg viewBox="0 0 ${W} ${H}" data-chart="${esc(le.id)}"
      role="img" aria-label="${esc(le.title)}: ${pctText(last)} od nákupu">
    <g class="ax">${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}"
        y2="${y(v).toFixed(1)}"${Math.abs(v) < step / 1000 ? ' class="zero"' : ""}/>
      <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${pctText(v, digits)}</text>`).join("")}
      <text x="${L}" y="${H - 6}">${day(pts[0][0])}</text>
      <text x="${W - R}" y="${H - 6}" text-anchor="end">${day(pts[pts.length - 1][0])}</text></g>
    ${level(le.tp, "lvl-tp", "cíl")}${level(le.sl, "lvl-sl", "stop")}
    <path d="${d} L${x(t1).toFixed(1)} ${y(0).toFixed(1)} L${x(t0).toFixed(1)} ${y(0).toFixed(1)}Z"
      fill="${col}" opacity=".10"/>
    <path d="${d}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round"
      stroke-linecap="round"/>
    <circle cx="${x(ts[ts.length - 1]).toFixed(1)}" cy="${y(last).toFixed(1)}" r="4.5"
      fill="${col}" stroke="var(--surface)" stroke-width="2"/>
    <line class="xh" x1="0" x2="0" y1="${T}" y2="${H - B}" visibility="hidden"/>
    <circle class="xd" r="4.5" cx="0" cy="0" fill="${col}" stroke="var(--surface)"
      stroke-width="2" visibility="hidden"/>
    <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/>
  </svg></figure>`;
}
function detail(le) {
  const lb = le.backtest;
  const now = le.stake != null && le.usdc != null ? le.stake + le.usdc : null;
  const tiles = [
    ["Vloženo", money(le.stake), le.sector === "bots" ? "do bota" : "papírové peníze"],
    ["Teď", money(now), now == null ? "" : "po poplatcích"],
    ["Výsledek", `<span class="${tone(le.net_pct)}">${pctText(le.net_pct)}</span>`,
     le.usdc == null ? "" : `<span class="${tone(le.usdc)}">${usdText(le.usdc)}</span>`],
    ["Backtest", lb && lb.pct != null
       ? `<span class="${lb.pass ? "up" : "down"}">${pctText(lb.pct, 0)}</span>` : "—",
     lb && lb.pct != null ? `za ${lb.period} d · Sharpe ${num(lb.sharpe, 1)}`
                          : "tohle se otestovat nedá"],
  ];
  const facts = [le.origin ? `nápad ${esc(le.origin)}` : "",
                 le.opened_at ? `otevřeno ${day(le.opened_at)}` : "",
                 le.ends_at ? `vyhodnocení ${day(le.ends_at)}` : ""].filter(Boolean);
  if (le.tp != null || le.sl != null) {
    facts.push(`cíl ${pctText(le.tp, 0)} · stop ${pctText(le.sl, 0)}`);
  }
  return `<li class="detail" data-for="${esc(le.id)}"><div class="dt">
    ${chart(le)}
    <div class="dt-side">
      <div class="tiles">${tiles.map(([k, v, s]) =>
        `<div class="tile"><span>${k}</span><b>${v}</b><i>${s}</i></div>`).join("")}</div>
      <p class="dt-facts">${facts.join(" · ")}</p>
      <div class="dt-links">${le.url ? `<a href="${esc(le.url)}" target="_blank"
          rel="noopener">Karta na Cymetice ↗</a>` : ""}
        <button type="button" class="linkish" data-chat="${esc(le.id)}">💬 Konverzace k tomuhle</button></div>
    </div></div></li>`;
}

/* ---------- the memecoin room ----------
   V3's answer is the headline: $10 into every hot signal, held a day, after
   costs. Under it the operator's own list from 2026-09-13/14 -- one list,
   the graph as its column, our own coloured bubble. */
function pct(v) {
  if (v == null) return `<span class="mc-flat">—</span>`;
  return `<span class="${v > 0 ? "mc-up" : v < 0 ? "mc-down" : "mc-flat"}">${pctText(v, 1)}</span>`;
}
/* One token, one hourly curve. A gap is a BREAK in the line, never a point at
   zero: an hour nobody could price is drawn dashed, as the guess it is. */
function curveSvg(points) {
  const W = 150, H = 30, PAD = 3;
  const read = (points || []).filter(p => p[1] != null);
  if (!read.length) return `<span class="mc-flat">—</span>`;
  const vals = read.map(p => p[1]);
  const hi = Math.max(...vals, 0), lo = Math.min(...vals, 0), span = (hi - lo) || 1;
  const x = h => PAD + ((h - 1) / 23) * (W - 2 * PAD);   // always 24 hours wide
  const y = v => PAD + (1 - (v - lo) / span) * (H - 2 * PAD);
  const lines = read.slice(1).map((p, i) => {
    const a = read[i];
    return `<line x1="${x(a[0]).toFixed(1)}" y1="${y(a[1]).toFixed(1)}"
      x2="${x(p[0]).toFixed(1)}" y2="${y(p[1]).toFixed(1)}"
      stroke="var(${p[1] >= a[1] ? "--ok" : "--bad"})" stroke-width="1.8"
      stroke-linecap="round"${p[0] - a[0] > 1 ? ' stroke-dasharray="2 3" opacity=".55"' : ""}/>`;
  }).join("");
  // The wide transparent circle is the hit area: a 2px dot is not a target.
  const dots = read.map(p =>
    `<g class="mc-pt" data-h="${p[0]}" data-v="${p[1]}">
      <circle cx="${x(p[0]).toFixed(1)}" cy="${y(p[1]).toFixed(1)}" r="8" fill="transparent"/>
      <circle cx="${x(p[0]).toFixed(1)}" cy="${y(p[1]).toFixed(1)}" r="2.6"
        fill="var(${p[1] >= 0 ? "--ok" : "--bad"})"/></g>`).join("");
  const zero = y(0).toFixed(1);
  return `<svg class="mc-spark" viewBox="0 0 ${W} ${H}" role="img"
    aria-label="výnos po hodinách od signálu">
    <line x1="${PAD}" x2="${W - PAD}" y1="${zero}" y2="${zero}" stroke="var(--line)"
      stroke-width="1"/>${lines}${dots}</svg>`;
}
const DROPPED = [["unpriced", "bez ceny při signálu"], ["depth_unknown", "neznámá hloubka"],
                 ["too_thin", "moc tenký pool na 10 $"], ["pair_changed", "přepnutý pár"],
                 ["unread_at_24h", "nepřečteno po 24 h"]];
function moversTable() {
  const all = V.movers || [];
  if (!all.length) return `<p class="empty">Zatím žádný signál nemá za sebou první hodinu.</p>`;
  const open = readStore("lab.movers", "0") === "1";
  const shown = open ? all : all.slice(0, TOP);
  const rows = shown.map(c => `<tr>
      <td class="mc-sym">${esc(c.symbol || "?")}</td>
      <td class="mc-conv">${c.conviction == null ? "—" : num(c.conviction, 0)}</td>
      <td class="mc-ret">${pct(c.last)}</td>
      <td class="mc-ret">${pct(c.peak)}</td>
      <td class="mc-g">${curveSvg(c.points)}</td></tr>`).join("");
  return `<div class="movers"><h3>Největší pohyby<small>${shown.length} z ${num(V.movers_total || 0, 0)}
      · seřazené podle vrcholu, takže jsou to vítězové z principu, ne průměr</small></h3>
    <table class="mc-list"><thead><tr><th>token</th><th>conviction</th><th>teď</th>
      <th>vrchol</th><th>prvních 24 h</th></tr></thead><tbody>${rows}</tbody></table>
    ${all.length > TOP ? `<button type="button" class="more" data-movers>${open ? "Méně ▴"
      : `Všech ${all.length} ▾`}</button>` : ""}</div>`;
}
function memeRoom(lp) {
  const [ct, cw] = confidence(lp);
  const hc = lp.conviction_70 || {};
  const ex = lp.excluded || {};
  const otherFees = (lp.fees || []).filter(f => f.fee_pct !== lp.fee_pct);
  const others = otherFees.map(f => pctText(f.net_pct, 1)).join(" / ");
  const otherWhat = "při " + otherFees.map(f => num(f.fee_pct, 1) + " %").join(" / ") + " za stranu";
  const dropped = DROPPED.filter(([k]) => ex[k]).map(([k, w]) => `${num(ex[k], 0)} ${w}`);
  const could = lp.could_buy_share == null ? null : Math.round(lp.could_buy_share * 100);
  const tiles = [
    ["Stihli bychom koupit", could == null ? "—" : could + " %",
     `z ${num(lp.signals || 0, 0)} signálů`,
     could == null ? "" : `<div class="meter"><s style="width:${could}%"></s></div>`],
    [`Jen conviction ≥ ${num(hc.min || 70, 0)}`,
     `<span class="${tone(hc.net_pct)}">${pctText(hc.net_pct, 1)}</span>`,
     `${num(hc.n || 0, 0)} ${plural(hc.n || 0, "obchod", "obchody", "obchodů")}`, ""],
    // [operator 2026-09-14] *"to me nezjaima bez top 5 nechapu proc by
    // to tam melo byt"*. So there is no "without the best five" figure; what
    // says whether the headline is the signal or one lucky coin is the
    // median beside it -- the trade in the middle, which no outlier moves.
    ["Typický obchod (medián)", `<span class="${tone(lp.median_pct)}">${pctText(lp.median_pct, 1)}</span>`,
     "polovina dopadne hůř", ""],
    ["Jiný poplatek", others || "—", otherFees.length ? otherWhat : "", ""],
  ];
  return `<div class="room-head">
      <div class="hero ${tone(lp.net_pct)}">${pctText(lp.net_pct, 1)}</div>
      <div class="hero-side">
        <div class="hero-l1">na obchod, když dáš <b>10 $ do každého hot signálu</b> a držíš den
          · ${num(lp.fee_pct, 0)} % poplatek za stranu</div>
        <div class="hero-l2">${num(lp.n || 0, 0)} obchodů · ${num(lp.wins || 0, 0)} v plusu
          <span class="conf ${ct}">${lp.wilson && lp.wilson[1] < 0.5 ? "většina prodělá" : cw}</span>${band(lp)}</div>
      </div></div>
    <div class="m-tiles">${tiles.map(([k, v, s, extra]) =>
      `<div class="tile"><span>${k}</span><b>${v}</b><i>${s}</i>${extra}</div>`).join("")}</div>
    ${dropped.length ? `<p class="filt">Vynecháno, protože by se nedalo koupit nebo změřit:
      ${dropped.join(" · ")}. Tyhle coiny nejsou v žádném čísle.</p>` : ""}
    ${moversTable()}`;
}

/* ---------- the room on screen ---------- */
let SECTOR = readStore("lab.sector", "cards");
if (!SECTORS.includes(SECTOR)) SECTOR = "cards";
let OPEN = readStore("lab.open", "");
function mine() { return (V.experiments || []).filter(le => le.sector === SECTOR); }
function groupNow(counts) {
  const saved = readStore("lab.group." + SECTOR, "");
  if (saved && counts[saved]) return saved;
  return (GROUPS.find(([g]) => counts[g]) || ["live"])[0];
}
function ordered(list, group) {
  const net = le => le.net_pct == null ? -Infinity : le.net_pct;
  return list.slice().sort(group === "archive"
    ? (a, b) => String(b.id).localeCompare(String(a.id))
    : (a, b) => net(b) - net(a));
}
function renderRoom() {
  const room = document.getElementById("room");
  const lp = sectorOf(SECTOR);
  room.setAttribute("style", "--hue:var(--c-" + SECTOR + ")");
  room.setAttribute("aria-label", lp.name || SECTOR);
  if (SECTOR === "memecoins") { room.innerHTML = memeRoom(lp); return; }
  const list = mine();
  const counts = {};
  GROUPS.forEach(([g]) => { counts[g] = list.filter(le => le.group === g).length; });
  if (lp.archived != null) counts.archive = Math.max(counts.archive, lp.archived);
  const group = groupNow(counts);
  const rows = ordered(list.filter(le => le.group === group), group);
  const all = readStore("lab.all." + SECTOR + "." + group, "0") === "1";
  const shown = all ? rows : rows.slice(0, TOP);
  room.innerHTML = roomHead(lp) +
    `<div class="bar"><div class="seg" role="tablist">${GROUPS.map(([g, w]) =>
      `<button type="button" role="tab" data-group="${g}" aria-selected="${g === group}">${w}` +
      `<span class="n">${counts[g]}</span></button>`).join("")}</div>
     <span class="bar-hint">${group === "archive" ? "nevydařené pokusy — nic se nemaže"
       : "seřazeno podle výsledku po poplatcích · klik = detail"}</span></div>` +
    (shown.length ? `<ol class="board">${shown.map((le, i) =>
       row(le, i + 1, le.id === OPEN)).join("")}</ol>` : `<p class="empty">${EMPTY[group]}</p>`) +
    (rows.length > TOP ? `<button type="button" class="more" data-all>${all ? "Méně ▴"
       : `Všech ${rows.length} ▾`}</button>` : "");
}
function renderAll() {
  document.getElementById("account").innerHTML = accountLine(V.account);
  document.getElementById("sectors").innerHTML =
    SECTORS.map(k => sectorTab(sectorOf(k), k === SECTOR)).join("");
  document.getElementById("nexus").innerHTML = nexusLine(V.nexus);
  renderRoom();
}
function labShow(sector, group) {
  if (SECTORS.includes(sector)) { SECTOR = sector; writeStore("lab.sector", sector); }
  if (group) writeStore("lab.group." + SECTOR, group);
  renderAll();
  if (CHAT && SECTORS.includes(CHAT)) labChat(SECTOR);
}
function labOpen(id) {
  OPEN = id || "";
  writeStore("lab.open", OPEN);
  const le = (V.experiments || []).find(e => e.id === OPEN);
  if (le) {
    SECTOR = le.sector;
    writeStore("lab.sector", SECTOR);
    writeStore("lab.group." + SECTOR, le.group);
  }
  renderAll();
}
window.labShow = labShow;
window.labOpen = labOpen;

/* ---------- the conversation: closed until asked for ----------
   The operator, 2026-09-23: they will hardly ever read it, maybe glance at it
   out of curiosity. A sector's conversation is every experiment's thread in
   it, oldest first, plus the notes written to the sector itself. */
let CHAT = null;
const NX_OUTCOME = {partial: "useknuté — přišla jen první věta",
                    failed: "bez odpovědi — přestali jsme čekat",
                    refused: "odmítl ještě před začátkem",
                    waiting: "čeká se na Nexuse…"};
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
  return (s / 3600).toFixed(1).replace(".", ",") + " h";
}
function nxBubble(nm) {
  const at = nm.at ? " · " + esc(clock(nm.at)) : "";
  if (nm.kind === "question") {
    const long = String(nm.text || "").length > 300;
    return `<div class="nx-msg nx-ours"><div class="nx-h"><b>Claude → Nexus</b>${at} · ` +
      `${esc(nm.id)}</div><div class="nx-b${long ? " nx-clamp" : ""}">${nxText(nm.text)}</div>` +
      (long ? `<button class="nx-more" type="button">▾ celé</button>` : "") + "</div>";
  }
  if (nm.kind === "reply") {
    const text = nm.text || "";
    const took = nm.seconds != null ? " · za " + nxSecs(nm.seconds) : "";
    const note = NX_OUTCOME[nm.outcome];
    const long = text.length > 500;
    return `<div class="nx-msg nx-${esc(nm.outcome || "answered")}">` +
      `<div class="nx-h"><b>Nexus</b>${at}${took}</div>` +
      (note ? `<div class="nx-s">${esc(note)}</div>` : "") +
      (nm.gist ? `<div class="nx-gist">${nxText(nm.gist)}</div>` : "") +
      (text ? `<div class="nx-b${long ? " nx-clamp" : ""}">${nxText(text)}</div>` : "") +
      (long ? `<button class="nx-more" type="button">▾ celá odpověď</button>` : "") + "</div>";
  }
  if (nm.kind === "operator_note") {
    return `<div class="nx-msg nx-op"><div class="nx-h"><b>Ty</b>${at}` +
      `<span class="nx-tick" title="${nm.read ? "Claude přečetl" : "uloženo, zatím nepřečteno"}">` +
      `${nm.read ? "✓✓" : "✓"}</span></div><div class="nx-b">${nxText(nm.text)}</div></div>`;
  }
  if (nm.kind === "claude_note") {
    return `<div class="nx-msg nx-cl"><div class="nx-h"><b>Claude</b>` +
      `${nm.re ? " · k " + esc(nm.re) : ""}${at}</div><div class="nx-b">${nxText(nm.text)}</div></div>`;
  }
  return `<div class="nx-msg nx-sys">${esc(nm.text || "")}${at}</div>`;
}
function chatItems(room) {
  const T = V.threads || {};
  if (!SECTORS.includes(room)) return (T[room] || []).map(nm => [room, nm]);
  const items = (T[room] || []).map(nm => [room, nm]);
  (V.experiments || []).filter(le => le.sector === room)
    .forEach(le => (T[le.id] || []).forEach(nm => items.push([le.id, nm])));
  return items.sort((a, b) => String(a[1].at || "").localeCompare(String(b[1].at || "")));
}
function chatName(room) {
  if (room === "general") return "Celá konverzace s Nexusem";
  if (SECTORS.includes(room)) return sectorOf(room).name;
  const le = (V.experiments || []).find(e => e.id === room);
  return le ? le.title : room;
}
function renderChat() {
  const titles = {};
  (V.experiments || []).forEach(le => { titles[le.id] = le.title; });
  let last = null;
  const html = chatItems(CHAT).map(([room, nm]) => {
    const head = room !== last && titles[room] && SECTORS.includes(CHAT)
      ? `<div class="th-room">${esc(titles[room])}</div>` : "";
    last = room;
    return head + nxBubble(nm);
  }).join("");
  document.getElementById("thread").innerHTML =
    html || `<p class="empty">Tady zatím nikdo nic nenapsal.</p>`;
  document.getElementById("drTitle").textContent = "Konverzace · " + chatName(CHAT);
  const scopes = [[SECTOR, sectorOf(SECTOR).name], ["general", "Celá s Nexusem"]];
  if (!SECTORS.includes(CHAT) && CHAT !== "general") scopes.push([CHAT, "jen tenhle pokus"]);
  document.getElementById("drScope").innerHTML = scopes.map(([k, w]) =>
    `<button type="button" data-scope="${esc(k)}" aria-pressed="${k === CHAT}">${esc(w)}</button>`).join("");
}
function labChat(room) {
  CHAT = room || SECTOR;
  document.getElementById("drawer").hidden = false;
  renderChat();
  bindComposer(CHAT);
  // Like any chat: the newest at the bottom, and the bottom in view.
  const thread = document.getElementById("thread");
  thread.scrollTop = thread.scrollHeight || 0;
}
function closeChat() {
  document.getElementById("drawer").hidden = true;
  CHAT = null;
}
window.labChat = labChat;

/* The composer: the operator's note for the room in the drawer. It is the
   page's one write, so it goes through every door serve.py keeps -- a token
   asked for at the moment of sending, a JSON body, this machine only. */
let sending = false;
function bindComposer(room) {
  const form = document.getElementById("compose"), draft = document.getElementById("draft");
  form.hidden = !LOCAL;
  if (form.dataset.room === room) return;
  if (form.dataset.room) writeStore("lab.draft." + form.dataset.room, draft.value || "");
  form.dataset.room = room;
  draft.value = readStore("lab.draft." + room, "");
  document.getElementById("sendNote").textContent = "Uloží se do: " + chatName(room) + " · Ctrl+Enter odešle";
}
// Asked for at the moment of sending, never baked into the page: a tab left
// open across a console restart would otherwise hold a token nobody issued.
function nxPost(room, text) {
  return fetch("/token", {cache: "no-store"})
    .then(r => r.ok ? r.json()
                    : Promise.reject(new Error("konzole nedala token (" + r.status + ")")))
    .then(t => fetch("/notes", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-QA-Token": t.token},
      body: JSON.stringify({room: room, text: text}),
    }))
    .then(r => r.ok ? r.json()
                    : r.json().catch(() => ({})).then(b =>
                        Promise.reject(new Error(b.error || ("HTTP " + r.status)))));
}
// On window so a test can run the page's own send path over a stub fetch and
// hold what it sends against what serve.py accepts.
window.nxPost = nxPost;

/* ---------- live: the numbers and the rooms redraw on their own ---------- */
function refresh() {
  if (!LOCAL || typeof fetch !== "function") return;
  fetch("/lab.json", {cache: "no-store"})
    .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
    .then(view => { V = view; renderAll(); if (CHAT) renderChat(); })
    .catch(() => {});
}

/* ---------- wiring ---------- */
document.getElementById("sectors").addEventListener("click", e => {
  const b = e.target.closest("[data-sector]");
  if (b) labShow(b.dataset.sector);
});
document.getElementById("room").addEventListener("click", e => {
  if (e.target.closest("a")) return;
  const g = e.target.closest("[data-group]");
  if (g) { labShow(SECTOR, g.dataset.group); return; }
  const chat = e.target.closest("[data-chat]");
  if (chat) { labChat(chat.dataset.chat); return; }
  if (e.target.closest("[data-all]")) {
    const key = "lab.all." + SECTOR + "." + readStore("lab.group." + SECTOR, "live");
    writeStore(key, readStore(key, "0") === "1" ? "0" : "1");
    renderRoom();
    return;
  }
  if (e.target.closest("[data-movers]")) {
    writeStore("lab.movers", readStore("lab.movers", "0") === "1" ? "0" : "1");
    renderRoom();
    return;
  }
  if (e.target.closest(".detail")) return;
  const r = e.target.closest(".row");
  if (r) labOpen(r.dataset.id === OPEN ? "" : r.dataset.id);
});
document.getElementById("room").addEventListener("keydown", e => {
  const r = e.target.closest && e.target.closest(".row");
  if (r && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    labOpen(r.dataset.id === OPEN ? "" : r.dataset.id);
  }
});
document.getElementById("chatBtn").addEventListener("click", () =>
  CHAT ? closeChat() : labChat(SECTOR));
document.getElementById("drClose").addEventListener("click", closeChat);
document.getElementById("drScope").addEventListener("click", e => {
  const b = e.target.closest("[data-scope]");
  if (b) labChat(b.dataset.scope);
});
document.getElementById("thread").addEventListener("click", e => {
  const b = e.target.closest(".nx-more");
  if (!b || !b.previousElementSibling) return;
  const body = b.previousElementSibling;
  body.classList.toggle("nx-clamp");
  b.textContent = body.classList.contains("nx-clamp") ? "▾ celé" : "▴ méně";
});
document.addEventListener("keydown", e => { if (e.key === "Escape" && CHAT) closeChat(); });
document.getElementById("draft").addEventListener("input", e => {
  const room = document.getElementById("compose").dataset.room;
  if (room) writeStore("lab.draft." + room, e.target.value);
});
document.getElementById("draft").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    document.getElementById("send").click();
  }
});
document.getElementById("compose").addEventListener("submit", e => {
  e.preventDefault();
  const form = document.getElementById("compose"), draft = document.getElementById("draft");
  const button = document.getElementById("send"), note = document.getElementById("sendNote");
  const room = form.dataset.room, text = String(draft.value || "").trim();
  if (!room || !text || sending) return;
  sending = true;
  button.disabled = true;
  note.textContent = "posílám…";
  nxPost(room, text)
    .then(() => {
      draft.value = "";
      writeStore("lab.draft." + room, "");
      note.textContent = "uloženo ✓ — Claude si to přečte, až mu řekneš „přečti si to“";
      refresh();
    })
    .catch(err => { note.textContent = "neodešlo: " + err.message; })
    .finally(() => { sending = false; button.disabled = false; });
});

/* The bubble over a memecoin's hour and over an experiment's line. */
(function hover() {
  const tip = document.getElementById("tip"), room = document.getElementById("room");
  const place = e => {
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let left = e.clientX + 16, top = e.clientY - h - 12;
    if (left + w > window.innerWidth - 8) left = e.clientX - w - 16;
    if (top < 8) top = e.clientY + 18;
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  };
  const show = (e, head, value) => {
    tip.innerHTML = `<div class="tip-h">${head}</div>` +
      `<div class="tip-v ${tone(value)}">${pctText(value)}</div>`;
    tip.hidden = false;
    place(e);
  };
  const quiet = () => {
    tip.hidden = true;
    const svgs = room.querySelectorAll ? room.querySelectorAll("svg[data-chart]") : [];
    Array.prototype.forEach.call(svgs, svg => {
      const xh = svg.querySelector(".xh"), xd = svg.querySelector(".xd");
      if (xh) xh.setAttribute("visibility", "hidden");
      if (xd) xd.setAttribute("visibility", "hidden");
    });
  };
  room.addEventListener("mousemove", e => {
    const pt = e.target.closest && e.target.closest(".mc-pt");
    if (pt) { show(e, `${esc(pt.dataset.h)}. hodina po signálu`, Number(pt.dataset.v)); return; }
    const svg = e.target.closest && e.target.closest("svg[data-chart]");
    const c = svg && CHARTS[svg.dataset.chart];
    if (!c) { quiet(); return; }
    // The crosshair finds the time: the reader aims at a moment, not at a line.
    const box = svg.getBoundingClientRect();
    const at = c.x0 + ((e.clientX - box.left) / box.width * c.W - c.L) /
               (c.W - c.L - c.R) * (c.x1 - c.x0);
    let best = 0;
    c.ts.forEach((t, i) => { if (Math.abs(t - at) < Math.abs(c.ts[best] - at)) best = i; });
    const px = c.L + (c.x1 > c.x0 ? (c.ts[best] - c.x0) / (c.x1 - c.x0) : 0) * (c.W - c.L - c.R);
    const py = c.T + (1 - (c.vs[best] - c.lo) / (c.hi - c.lo)) * (c.H - c.T - c.B);
    const xh = svg.querySelector(".xh"), xd = svg.querySelector(".xd");
    xh.setAttribute("x1", px); xh.setAttribute("x2", px); xh.setAttribute("visibility", "visible");
    xd.setAttribute("cx", px); xd.setAttribute("cy", py); xd.setAttribute("visibility", "visible");
    show(e, clock(new Date(c.ts[best]).toISOString()) + " · od nákupu", c.vs[best]);
  });
  room.addEventListener("mouseleave", quiet);
})();

(function live() {
  const dot = document.getElementById("live");
  const say = (cls, word) => { dot.className = "live " + cls; dot.innerHTML = `<i></i><span>${word}</span>`; };
  if (!window.EventSource || !LOCAL) return;
  let src;
  try { src = new EventSource("/events"); } catch (_) { return; }
  src.addEventListener("hello", () => { say("on", "živě"); refresh(); });
  src.addEventListener("rooms", refresh);
  src.onerror = () => say("off", "připojuji znovu");
  window.addEventListener("beforeunload", () => src.close());
})();

renderAll();
</script>
"""
