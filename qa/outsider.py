"""Section 6 of the laboratory: the outsider.

Once a day an AI trading agent with none of our memory (`docs/outsider-prompt.md`, its own process,
WebFetch and WebSearch only) discovers Cymetica from cymetica.com and its llms.txt,
scores each surface on "would I put money here", says whether it would deposit, and
picks. Its run arrives as one JSON object; `scripts/outsider.py` records it in
`state/outsider.jsonl` and follows its coins. Plan: `docs/laborator-plan.md`, section 6
and phase P6.

Pure: nothing here reads a file or makes a call.

* `validate(run)` -- the run normalised, or `OutsiderError` naming EVERY problem at once
  (an agent's run costs up to 40 fetches; a refusal that names one problem per attempt
  would cost a run per problem).
* `actions(run)` -- what the laboratory may do with its picks. Its card is bought on
  paper at HALF stake WITHOUT our backtest gate: the number we measure is the stranger's
  judgement, not gate-and-stranger. Its bot is cloned on paper at its own band; its
  coin is watched against BTC at 1, 7 and 28 days; its table is a wish whose seat the
  operator approves at their approve_url.
* `due` / `coin_returns` -- the coin checkpoints: the writer offers one only inside its
  slack and the reader drops a read outside it, one rule both sides (`qa/fomo.py`'s
  shape, at a daily scale). A missing observation is None, never a zero.
* `seat_refusal` -- the tournament floor, read off THEIR table and rules.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone

SECTION = "outsider"
MAX_FETCHES = 40
MAX_PICKS = 5
MAX_STUMBLES = 20
MAX_TEXT = 600
HORIZONS_DAYS = (1, 7, 28)
# The six surfaces its prompt asks it to judge, by these names, so a score can be
# followed over time. Matched without regard to case; anything else it scores is kept
# under its own name.
SURFACES = ("Gem Screener", "Agent Tournaments", "Agent League", "Event cards", "Bots",
            "Nexus")
SCORE_RANGE = (0, 10)
HOLD_DAYS = (1, 14)
STOP_LOSS = (1, 20)
TAKE_PROFIT = (5, 100)

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# A Gem Screener slug or ticker, one path segment: what goes into
# /api/v1/gem-screener/coins/{slug} can never carry a slash, a dot-dot or a query.
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")
TABLE = re.compile(r"^[A-Za-z0-9-]{1,64}$")


class OutsiderError(ValueError):
    """A run the laboratory cannot use, with every reason at once."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__(f"{len(self.problems)} problem(s) in the outsider's run:\n"
                         + "\n".join(f"  - {p}" for p in self.problems))


# -- validate ---------------------------------------------------------------------------

def _text(value, where: str, problems: list[str], required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value.strip()):
        problems.append(f"{where} must be a non-empty string, got {value!r}"[:200])
        return ""
    return value.strip()[:MAX_TEXT]


def _number(value, where: str, bounds: tuple, problems: list[str], whole: bool = False):
    """A plain number inside `bounds`. A bool is an int in Python and is not a number
    here; nor is NaN, a string, or 0.5 where a whole number of days is asked."""
    lo, hi = bounds
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and lo <= value <= hi \
        and (not whole or float(value).is_integer())
    if not ok:
        kind = "a whole number" if whole else "a number"
        problems.append(f"{where} must be {kind} from {lo} to {hi}, got {value!r}"[:200])
        return None
    return int(value) if whole else value


def _canonical(name: str) -> str:
    for known in SURFACES:
        if name.casefold() == known.casefold():
            return known
    return name


def _list(value, where: str, problems: list[str], cap: int) -> list:
    if not isinstance(value, list):
        problems.append(f"{where} must be a list, got {type(value).__name__}")
        return []
    if len(value) > cap:
        problems.append(f"{where}: {len(value)} given, at most {cap}")
    return value


def validate(run) -> dict:
    """The run, normalised; or OutsiderError naming every problem.

    Normalised: strings stripped and cut to MAX_TEXT, surface names canonical, card ids
    in lower case, `scores` built (each of SURFACES, None where it gave none). Keys it was
    not asked for are dropped. Validating a validated run returns it unchanged."""
    problems: list[str] = []
    if not isinstance(run, dict):
        raise OutsiderError([f"the run must be one JSON object, got {type(run).__name__}"])
    for key in ("verdict", "would_deposit", "surfaces", "picks", "stumbles", "fetches"):
        if key not in run:
            problems.append(f"{key} is missing")

    verdict = _text(run.get("verdict"), "verdict", problems) if "verdict" in run else ""
    deposit = run.get("would_deposit")
    if "would_deposit" in run and not isinstance(deposit, bool):
        problems.append(f"would_deposit must be true or false, got {deposit!r}"[:200])
    fetches = run.get("fetches")
    if "fetches" in run:
        fetches = _number(fetches, "fetches", (0, MAX_FETCHES), problems, whole=True)

    surfaces, seen = [], set()
    for i, item in enumerate(_list(run.get("surfaces", []), "surfaces", problems, 20)):
        where = f"surfaces[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} must be an object")
            continue
        name = _canonical(_text(item.get("name"), f"{where}.name", problems))
        if name and name.casefold() in seen:
            problems.append(f"{where}: {name!r} is scored twice")
        seen.add(name.casefold())
        score = _number(item.get("score"), f"{where}.score ({name})", SCORE_RANGE, problems)
        why = _text(item.get("why"), f"{where}.why", problems)
        surfaces.append({"name": name, "score": score, "why": why})
    scores = {name: None for name in SURFACES}
    scores.update({s["name"]: s["score"] for s in surfaces if s["name"]})

    picks_in = run.get("picks") if isinstance(run.get("picks"), dict) else {}
    if "picks" in run and not isinstance(run.get("picks"), dict):
        problems.append("picks must be an object")
    coins, cards, bots = [], [], []
    for i, item in enumerate(_list(picks_in.get("coins", []), "picks.coins", problems,
                                   MAX_PICKS)):
        where = f"picks.coins[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} must be an object")
            continue
        slug = item.get("slug")
        if not isinstance(slug, str) or not SLUG.match(slug.strip()):
            problems.append(f"{where}.slug must be a Gem Screener slug (letters, digits, "
                            f"- and _), got {slug!r}"[:200])
            slug = ""
        coins.append({"slug": slug.strip(), "why": _text(item.get("why"), f"{where}.why",
                                                         problems)})
    for i, item in enumerate(_list(picks_in.get("cards", []), "picks.cards", problems,
                                   MAX_PICKS)):
        where = f"picks.cards[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} must be an object")
            continue
        card = item.get("id")
        card = card.strip().lower() if isinstance(card, str) else card
        if not isinstance(card, str) or not UUID.match(card):
            problems.append(f"{where}.id is not a whole UUID, got {item.get('id')!r}"[:200])
            card = ""
        days = _number(item.get("hold_days"), f"{where}.hold_days", HOLD_DAYS, problems,
                       whole=True)
        cards.append({"id": card, "hold_days": days,
                      "why": _text(item.get("why"), f"{where}.why", problems)})
    for i, item in enumerate(_list(picks_in.get("bots", []), "picks.bots", problems,
                                   MAX_PICKS)):
        where = f"picks.bots[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} must be an object")
            continue
        bots.append({
            "species": _text(item.get("species"), f"{where}.species", problems),
            "stop_loss_pct": _number(item.get("stop_loss_pct"), f"{where}.stop_loss_pct",
                                     STOP_LOSS, problems),
            "take_profit_pct": _number(item.get("take_profit_pct"),
                                       f"{where}.take_profit_pct", TAKE_PROFIT, problems),
            "why": _text(item.get("why"), f"{where}.why", problems)})
    for kind, rows, key in (("coins", coins, lambda r: r["slug"].casefold()),
                            ("cards", cards, lambda r: r["id"]),
                            ("bots", bots, lambda r: (r["species"].casefold(),
                                                      r["stop_loss_pct"],
                                                      r["take_profit_pct"]))):
        keys = [key(r) for r in rows]
        twice = sorted({str(k) for k in keys if keys.count(k) > 1 and k})
        if twice:
            problems.append(f"picks.{kind}: picked twice: {', '.join(twice)}"[:200])

    table = picks_in.get("tournament", {"table_id": None, "why": ""})
    if not isinstance(table, dict):
        problems.append("picks.tournament must be an object")
        table = {}
    table_id = table.get("table_id")
    if isinstance(table_id, int) and not isinstance(table_id, bool):
        table_id = str(table_id)
    if table_id is not None and (not isinstance(table_id, str) or not TABLE.match(table_id)):
        problems.append(f"picks.tournament.table_id must be a table id or null, got "
                        f"{table.get('table_id')!r}"[:200])
        table_id = None
    tournament = {"table_id": table_id,
                  "why": _text(table.get("why") or "", "picks.tournament.why", problems,
                               required=False)}

    stumbles = []
    for i, item in enumerate(_list(run.get("stumbles", []), "stumbles", problems,
                                   MAX_STUMBLES)):
        if not isinstance(item, dict):
            problems.append(f"stumbles[{i}] must be an object")
            continue
        stumbles.append({"where": _text(item.get("where"), f"stumbles[{i}].where", problems),
                         "what": _text(item.get("what"), f"stumbles[{i}].what", problems),
                         **({"by": item["by"]} if isinstance(item.get("by"), str) else {})})

    if problems:
        raise OutsiderError(problems)
    return {"verdict": verdict, "would_deposit": deposit, "surfaces": surfaces,
            "scores": scores,
            "picks": {"coins": coins, "cards": cards, "bots": bots, "tournament": tournament},
            "stumbles": stumbles, "fetches": fetches}


def digest(run: dict) -> str:
    """One run's identity: the same JSON recorded twice is one run."""
    import hashlib

    return hashlib.sha256(json.dumps(validate(run), sort_keys=True,
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


# -- what the laboratory may do ---------------------------------------------------------

def proven(rows: list[dict]) -> bool:
    """Whether the newest independence probe on record passed (scripts/outsider.py `probe`):
    only then may the stranger run. Pure, so the laboratory's tick can ask it without
    reaching the process that runs the stranger."""
    probes = [r for r in rows or () if r.get("type") == "probe"]
    if not probes:
        return False
    return max(probes, key=lambda r: str(r.get("at") or "")).get("ok") is True


def actions(run) -> list[dict]:
    """Every pick as an action the laboratory may take, all on paper, in section 6.

    The card's `half` and `backtest_gate` are explicit, never defaults: a caller that
    reads an absent key as "no" would buy at full stake behind our gate, which is the
    gate-and-stranger number this section exists not to measure."""
    run = validate(run)
    picks = run["picks"]
    out = []
    for coin in picks["coins"]:
        out.append({"kind": "coin", "action": "watch", "section": SECTION,
                    "slug": coin["slug"], "horizons_days": list(HORIZONS_DAYS),
                    "benchmark": "BTC", "why": coin["why"]})
    for card in picks["cards"]:
        out.append({"kind": "card", "action": "paper_buy", "section": SECTION,
                    "card_id": card["id"], "hold_days": card["hold_days"],
                    "paper": True, "half": True, "backtest_gate": False,
                    "why": card["why"]})
    for bot in picks["bots"]:
        out.append({"kind": "bot", "action": "paper_clone", "section": SECTION,
                    "species": bot["species"], "paper": True,
                    "settings": {"stop_loss_pct": bot["stop_loss_pct"],
                                 "take_profit_pct": bot["take_profit_pct"]},
                    "why": bot["why"]})
    table = picks["tournament"]
    if table["table_id"] is not None:
        out.append({"kind": "tournament", "action": "seat_wish", "section": SECTION,
                    "table_id": table["table_id"], "approval": "operator",
                    "why": table["why"]})
    return out


# -- their two prices -------------------------------------------------------------------

def _positive(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and value > 0


def coin_price(body) -> tuple[dict | None, str | None]:
    """`GET /api/v1/gem-screener/coins/{slug}` -> (`{"value", "as_of"}`, None), or
    (None, why). The price is `price.value` (USD per token) at `price.as_of`, the
    snapshot's moment, which can be hours before the read (2026-10-11: read 13:52, as_of
    11:29). A price with no moment cannot be put on a span, so it is not a price here."""
    price = body.get("price") if isinstance(body, dict) else None
    if not isinstance(price, dict):
        return None, "no price object in their answer"
    if not _positive(price.get("value")):
        return None, f"price.value is {price.get('value')!r}"
    if not isinstance(price.get("as_of"), str) or not price["as_of"]:
        return None, "price.as_of is missing"
    return {"value": price["value"], "as_of": price["as_of"]}, None


def btc_price(body) -> tuple[dict | None, str | None]:
    """`GET /api/v1/prices` -> BTC as `{"value", "as_of"}`. BTC is not in the Gem
    Screener (its coin route answers 404), so this is the one Cymetica figure for it:
    `BTC.price` at `price_as_of`, taken only when `is_real` is true and `stale` false
    (their `last-real` fallback is a quote from up to a day before)."""
    row = body.get("BTC") if isinstance(body, dict) else None
    if not isinstance(row, dict):
        return None, "no BTC row in their prices"
    if row.get("is_real") is not True or row.get("stale") is not False:
        return None, f"BTC is_real={row.get('is_real')!r} stale={row.get('stale')!r}"
    if not _positive(row.get("price")):
        return None, f"BTC price is {row.get('price')!r}"
    as_of = row.get("price_as_of") or row.get("timestamp")
    if not isinstance(as_of, str) or not as_of:
        return None, "BTC price_as_of is missing"
    return {"value": row["price"], "as_of": as_of}, None


# -- the checkpoints --------------------------------------------------------------------

def _at(value) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def label(days: int) -> str:
    return f"{days}d"


def slack(days: int) -> timedelta:
    """How late a checkpoint may still be read: half its horizon, never more than two
    days. The laboratory ticks only when the operator starts it, so a day-1 read can be
    late; past the slack it would file another moment's price under day 1, and it stays
    a gap instead (`qa/fomo.py`: an hour that has gone is gone)."""
    return timedelta(days=min(days / 2.0, 2.0))


def _coin_picks(pick_rows) -> list[dict]:
    return [r for r in pick_rows or [] if isinstance(r, dict) and r.get("type") == "pick"
            and r.get("kind") == "coin"]


def _done(price_rows) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for row in price_rows or []:
        if isinstance(row, dict) and row.get("type") == "checkpoint" and row.get("pick"):
            out.setdefault(str(row["pick"]), {}).setdefault(str(row.get("horizon")), row)
    return out


def due(pick_rows, price_rows, now) -> list[tuple[dict, str]]:
    """(pick, label) for every coin checkpoint that is ripe, inside its slack and not yet
    read. A coin with no price, or no BTC, at its pick has nothing to return from against
    BTC and is never due."""
    moment = _at(now)
    done = _done(price_rows)
    out = []
    for pick in _coin_picks(pick_rows):
        at = _at(pick.get("at"))
        if at is None or moment is None or not isinstance(pick.get("price"), dict) \
                or not isinstance(pick.get("btc"), dict):
            continue
        for days in HORIZONS_DAYS:
            name = label(days)
            if name in done.get(str(pick.get("id")), {}):
                continue
            ripe = at + timedelta(days=days)
            if ripe <= moment < ripe + slack(days):
                out.append((pick, name))
    return out


def _span_ok(first: dict | None, second: dict | None, days: int) -> bool:
    """The two prices are `days` apart by their own moments, within the slack: a
    snapshot that did not move, or one frozen for most of the span, is another moment's
    price and not this horizon's."""
    if not isinstance(first, dict) or not isinstance(second, dict):
        return False
    a, b = _at(first.get("as_of")), _at(second.get("as_of"))
    if a is None or b is None or not (_positive(first.get("value"))
                                      and _positive(second.get("value"))):
        return False
    span = b - a
    return timedelta(days=days) - slack(days) <= span <= timedelta(days=days) + slack(days)


def _pct(first: dict, second: dict) -> float:
    return (float(second["value"]) / float(first["value"]) - 1.0) * 100.0


def coin_returns(pick_rows, price_rows, now) -> dict:
    """Per coin pick: its return since the pick at 1, 7 and 28 days, BTC's over the same
    span, and the coin's lead over BTC in percentage points. None where the day has not
    come (`not due`), where it is due and not read yet (`open`), where it passed unread
    (`missed`), where the read came after the slack (`late`), and where a price or
    BTC's is missing or from another moment (`unpriced`). Never a zero for any of them."""
    moment = _at(now)
    done = _done(price_rows)
    out = {}
    for pick in _coin_picks(pick_rows):
        pid = str(pick.get("id"))
        at = _at(pick.get("at"))
        returns, status = {}, {}
        for days in HORIZONS_DAYS:
            name = label(days)
            returns[name] = None
            row = done.get(pid, {}).get(name)
            ripe = at + timedelta(days=days) if at else None
            if row is None:
                if ripe is None or moment is None:
                    status[name] = "unpriced"
                elif moment < ripe:
                    status[name] = "not due"
                elif moment < ripe + slack(days):
                    status[name] = "open"
                else:
                    status[name] = "missed"
                continue
            read = _at(row.get("at"))
            if ripe is None or read is None or not (ripe <= read < ripe + slack(days)):
                status[name] = "late"
                continue
            coin0, coin1 = pick.get("price"), row.get("price")
            btc0, btc1 = pick.get("btc"), row.get("btc")
            if not (_span_ok(coin0, coin1, days) and _span_ok(btc0, btc1, days)):
                status[name] = "unpriced"
                continue
            coin, btc = _pct(coin0, coin1), _pct(btc0, btc1)
            returns[name] = {"coin_pct": round(coin, 6), "btc_pct": round(btc, 6),
                             "vs_btc_pts": round(coin - btc, 6), "read_at": row.get("at")}
            status[name] = "read"
        out[pid] = {"slug": pick.get("slug"), "run": pick.get("run"), "at": pick.get("at"),
                    "returns": returns, "status": status}
    return out


# -- the tournament seat ----------------------------------------------------------------

def seat_refusal(table_id: str, table, rules, instance_id: str | None = None) -> str | None:
    """Why a seat may NOT be asked for at this table, or None.

    A seat of ours already at the table refuses only the SAME bot again (their rules: one owner
    may seat several DIFFERENT bots at a paper table, one copy of each; the operator, 2026-10-28:
    five different bots at one table). Called without a bot, the old floor holds: any seat of ours
    refuses.

    Read off THEIR table (`GET /api/v1/agent-tournaments/tables/{id}`) and rules
    (`/rules`), never off the lobby -- `/lobby?mode=paper` is filtered by the very
    thing being asked. Their table carries no field for the buy-in's currency: what says
    the buy-in is paper is the table's own `mode: "paper"` together with the rules'
    `paper_note` ("the buy-in comes from your paper USDC"). So both are required, the
    paper mode must be open, the table open with a free seat and none of ours, and its
    `buyin_usdc` the one its tier publishes."""
    if not isinstance(table, dict) or not isinstance(rules, dict):
        return "their table or rules could not be read; nothing is asked on an unread answer"
    if str(table.get("id")) != str(table_id):
        return f"they answered table {table.get('id')!r} for table {table_id!r}"
    if table.get("mode") != "paper":
        return (f"table {table_id} reads mode={table.get('mode')!r}; a seat is asked only "
                f"where their table says paper")
    modes = rules.get("modes") if isinstance(rules.get("modes"), dict) else {}
    if modes.get("paper") != "open":
        return f"their rules say paper tables are {modes.get('paper')!r}, not open"
    note = str(rules.get("paper_note") or "")
    if "paper usdc" not in note.casefold():
        return ("their rules no longer say a paper table's buy-in comes from paper USDC "
                f"(paper_note: {note[:120]!r}); the buy-in is not known to be paper")
    if table.get("status") != "open":
        return f"table {table_id} is {table.get('status')!r}, not open"
    free = table.get("seats_free")
    if not isinstance(free, int) or isinstance(free, bool) or free < 1:
        return f"table {table_id} has {free!r} seats free"
    if table.get("my_seat") is not None and instance_id is None:
        return f"we already hold a seat at table {table_id}: {table.get('my_seat')!r}"
    buyin = table.get("buyin_usdc")
    tiers = [t for t in rules.get("tiers") or [] if isinstance(t, dict)
             and t.get("tier") == table.get("tier")]
    if not _positive(buyin) or not tiers or tiers[0].get("buyin_usdc") != buyin:
        return (f"table {table_id}'s buy-in {buyin!r} is not the {table.get('tier')!r} "
                f"tier's published buy-in")
    return None


# -- the report -------------------------------------------------------------------------

def surface_scores(run_rows) -> dict:
    """Per surface, its scores in run order and their mean: how the stranger's
    impression moves from one run to the next. A surface it did not score is left out
    of that run's mean, never counted as 0."""
    runs = [r for r in run_rows or [] if isinstance(r, dict) and r.get("type") == "run"]
    runs.sort(key=lambda r: str(r.get("at")))
    names = list(SURFACES) + sorted({n for r in runs for n in (r.get("scores") or {})
                                     if n not in SURFACES})
    out = {}
    for name in names:
        series = [(r.get("id"), (r.get("scores") or {}).get(name)) for r in runs]
        given = [s for _id, s in series if _positive(s) or s == 0]
        out[name] = {"series": series,
                     "mean": round(sum(given) / len(given), 2) if given else None,
                     "n": len(given)}
    return out
