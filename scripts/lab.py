"""The laboratory: Nexus leads, we execute, measure and remember.

[operator 2026-09-11] *"Moje vize je ze te budu casto posialt pracovat s Nexusem
do laboratore a budete skoumat same nove strategie a hledat ty nejvydelecnejsi.
Ja to budu monitorovat v roomech ktere jsme dne spostavili."* -- and CLAUDE.md's
older rule under it: Nexus supplies the guidance on what to trade, we test the
platform and execute. A strategy of ours never becomes a room.

    python scripts/lab.py status     where we are, and what is due
    python scripts/lab.py truth      their backtests, ranked risk-adjusted
    python scripts/lab.py cycle      finish what is in flight, sample, compare
    python scripts/lab.py ask "..."  one question, with the brakes on
    python scripts/lab.py buy --card ... --usdc ...
    python scripts/lab.py open / close

`truth` is the lane Cymetica themselves told us to start from (Telegram,
2026-09-11): surfaces, then models, then the grounded metrics, ranked by Sharpe
and drawdown rather than by return. Until 2026-09-12 our own floor refused two
of those three tools, so the store held zero calls to the first step of the
loop they recommended.

The brakes live in `qa/lab.py` and are executable: paper only, a cap on
questions and rooms, a share of what is free per experiment, and nothing at all
while a deep pass is running -- that pass is verifying #85, #86 and #87 over
these very answers and trades, and a question asked mid-run changes the subject
of a verdict already on its way to the vendor.

What comes back is DATA. Trading advice is what we asked for and what the
operator told us to act on; anything else in an answer -- going live, retiring
a check, spending without `paper` -- is quoted to them and not acted on.
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import backtests as qa_backtests  # noqa: E402
from qa import lab, rooms  # noqa: E402
from qa.console import printable  # noqa: E402

BASELINE = REPO_ROOT / "audits" / "nexus-baseline.json"
TRUTH_STALE_HOURS = 6
# Their own slugs look like `bt-odiv`; the tool's own example says so.
SLUG_KEYS = ("slug", "strategy", "concept", "id", "name")


def _sibling(name: str):
    """Another script, imported by path: scripts/ is not a package and a lab
    that copied their client would be a second idea of what SAFE means."""
    spec = importlib.util.spec_from_file_location(
        f"lab_{name}", REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _moment(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def pass_in_flight() -> bool:
    """Whether a deep pass is running, from its own notebook."""
    return _sibling("processes").pass_in_flight()


def _nexus_rows() -> list[dict]:
    return _sibling("nexus").load()


def _session_now() -> str | None:
    open_now = lab.open_sessions()
    return open_now[-1] if open_now else None


def _asked_today(rows: list[dict] | None = None) -> int:
    """Questions in the last twenty-four hours, whichever session asked them.

    Counted from the moment the open session began until 2026-09-19, so a new
    session reset the cap -- harmless while a person opened one a day, and the
    whole cap the moment the laboratory became a loop.
    """
    return lab.asked_within(rows if rows is not None else _nexus_rows(), _now())


def _free_cash() -> float | None:
    """What the last recorded account said was free.

    The live floor is paper.py's own book, which refuses an order it cannot
    pay for and refuses outright when the money in the bots cannot be read.
    This is the lab's policy cap on top of it, so the last recorded number is
    the honest input: it is what we know without asking them again.

    Their balances are decimal STRINGS ("89000.96"). This demanded int or
    float until 2026-09-12, so it returned None on every real row and the cap
    above it refused every order the lab ever tried to place. A string that is
    not a number is still unreadable, never a zero.
    """
    paper = _sibling("paper")
    newest = None
    for row in paper.load():
        if row.get("type") == "after" and isinstance(row.get("after"), dict):
            newest = row["after"]
        elif row.get("type") == "after":
            newest = row
    if not isinstance(newest, dict):
        return None
    for key in ("sim_balance_usdc", "balance_usdc", "free_usdc"):
        value = newest.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
    return None


def _closed_on_their_side() -> set[str]:
    """Positions their own record says are no longer open.

    `paper.jsonl` holds OUR orders, so a position closed any other way never
    reaches it. On 2026-09-12 the operator closed a 10 000 USDC paper card on
    their website by hand and `_deployed` went on counting it for the rest of
    the day. The sampler had already written the closure down ten minutes
    later -- nothing read it.

    Read from the sampler's rows on this machine, not from a call: the cap may
    not depend on their API answering. Newest row per position, and only an
    explicit `closed` releases anything. A position with no row is one we have
    learned nothing about, and rule 8's safe direction here is to keep counting
    it -- that understates our headroom, which cannot overspend.
    """
    try:
        from qa.rooms import load_samples

        rows = load_samples()
    except Exception:  # noqa: BLE001 -- unreadable is not "everything closed"
        return set()

    newest: dict[str, tuple[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("kind") != "position":
            continue
        position = row.get("position_id")
        status, at = row.get("status"), str(row.get("at") or "")
        if not isinstance(position, str) or not isinstance(status, str):
            continue
        if at >= newest.get(position, ("", ""))[0]:
            newest[position] = (at, status)
    return {p for p, (_, status) in newest.items() if status == "closed"}


def _deployed() -> float:
    """What is still out in open positions.

    The symmetric reading to `_free_cash`: records on this machine rather than
    a fresh call to them, so the cap does not depend on their API answering. A
    buy is out from the moment its outcome is `accepted` until an accepted
    close names its position -- or until THEIR record says it closed, which is
    the only way a close made anywhere but here becomes visible. An order they
    refused was never out at all.
    """
    rows = _sibling("paper").load()
    intents = {row["id"]: row for row in rows
               if row.get("type") == "intent" and row.get("id")}
    out: dict[str, float] = {}
    for row in rows:
        if row.get("type") != "outcome" or row.get("outcome") != "accepted":
            continue
        intent = intents.get(row.get("id"), {})
        if row.get("kind") == "close" or intent.get("kind") == "close":
            out.pop(str(intent.get("position_id") or row.get("position_id")),
                    None)
            continue
        position = row.get("position_id") or intent.get("position_id")
        usdc = _amount(intent.get("usdc"))
        if usdc is None:
            continue
        # An accepted order with no position id is still money out. Keyed on
        # the ORDER id when they gave us no position, because dropping it
        # silently understates what is deployed and so overstates the headroom
        # under the 60% ceiling. `paper.book()` had exactly this defect and its
        # test records that a missing position_id happens three ways that are
        # nothing to do with a bug on their side.
        out[str(position or f"order:{row.get('id')}")] = usdc
    for position in _closed_on_their_side():
        out.pop(position, None)
    return sum(out.values())


def _amount(value) -> float | None:
    """Their money arrives as a decimal STRING as often as a number.

    `_free_cash` was fixed for this on 2026-09-12 and this function, written
    the same hour twenty lines below it, went on dropping string amounts to
    zero. A value we cannot read is not zero -- it is skipped and the caller
    keeps its own floor.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _archive_diaries() -> list[str]:
    """Put the laboratory's diaries where git can hold them.

    All five are gitignored -- they are written while a sweep may run -- so the
    copy keep.py makes in audits/lab/ is the only one that survives this
    machine. The deep pass calls it too, but its trigger is the operator saying
    "jdu spat", and the data finalises when a session ends, not when they go to
    bed. On 2026-09-12 that gap was every row the laboratory had.

    Best effort on purpose: a failed copy says so and does not take down the
    close that ends the session. A session left open stops the next one.
    """
    try:
        return _sibling("keep").snapshot()
    except Exception as exc:  # noqa: BLE001 -- an archive is not a brake
        print(f"[lab] the diaries were NOT archived: {exc}")
        return []


def _running_experiments() -> int:
    rows = rooms.load()
    states = {}
    for row in rows:
        if row.get("type") == "status" and row.get("room"):
            states[row["room"]] = row.get("status")
    return sum(1 for state in states.values() if state == "running")


# --- the ground-truth lane -------------------------------------------------

def _reader():
    """Their MCP endpoint at SAFE, through nexus.py's own client.

    Not a second client: the tier and the floor under it are the whole of what
    makes a read a read, and two ideas of that is how a lab ends up calling
    something nobody classified.
    """
    from qa.safety import CURRENT_TIER, SafetyTier

    nexus = _sibling("nexus")
    client = nexus._client()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    return nexus, client, token


def _done(client, token):
    from qa.safety import CURRENT_TIER

    client.http.close()
    CURRENT_TIER.reset(token)


def _slugs(payload, found: set[str]) -> set[str]:
    """Every strategy concept named anywhere in their catalogue."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in SLUG_KEYS and isinstance(value, str) and value.strip():
                if value.startswith("bt-") or "_" in value or "-" in value:
                    found.add(value.strip())
            else:
                _slugs(value, found)
    elif isinstance(payload, list):
        for item in payload:
            _slugs(item, found)
    elif isinstance(payload, str):
        for word in payload.replace(",", " ").split():
            if word.startswith("bt-") and len(word) > 4:
                found.add(word.strip(".;:()'\""))
    return found


def _metrics(payload) -> dict:
    """Sharpe, return, drawdown, win rate and trades, wherever they sit.

    Their own wording is that a concept with no runs "returns a note, never a
    fabricated number", so a missing key here is left missing: qa/lab.py::rank
    sorts those out rather than treating them as zero.
    """
    out: dict[str, float] = {}
    wanted = {
        "sharpe": ("sharpe", "sharpe_ratio"),
        "total_return": ("total_return", "roi", "return_pct", "total_return_pct"),
        "max_drawdown": ("max_drawdown", "max_dd", "drawdown", "max_drawdown_pct"),
        "win_rate": ("win_rate", "win_rate_pct", "winrate"),
        "trades": ("trades", "trade_count", "n_trades"),
    }

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                low = str(key).lower()
                for name, keys in wanted.items():
                    if low in keys and isinstance(value, (int, float)):
                        out.setdefault(name, float(value))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return out


LEADERBOARD = "/api/v1/backtest/leaderboard"


def truth(limit: int = 12) -> list[dict]:
    """Their backtests, ranked the way risk is ranked: Sharpe, then drawdown.

    Three reads, in the order Cymetica's own guide gives (Telegram,
    2026-09-11), and the first one is not the numbers: `list_backtest_surfaces`
    is a MAP -- five surfaces, each with the REST paths that answer it and the
    auth they need. The numbers are on `/api/v1/backtest/leaderboard`, which it
    names and marks `auth: none`. Reading the map first is what stopped this
    from being a guess about where the ranking lives; the first version of this
    function looked for slugs inside the map and found two words.

    `get_strategy_returns` then cross-checks the top of the ranking. Their own
    promise is that a concept with no backtest rows "returns a note, never a
    fabricated number", so a missing metric stays missing here too.
    """
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.evidence import EvidenceStore
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    store = EvidenceStore("script-lab")
    nexus, mcp, token = _reader()
    try:
        surfaces = nexus._inner(mcp.call("list_backtest_surfaces", {}))
    finally:
        _done(mcp, token)
    named = [s.get("id") for s in (surfaces or {}).get("surfaces", [])
             if isinstance(s, dict)]
    print(f"[truth] their map names {len(named)} surface(s): {', '.join(named)}")

    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    rest = build_client(identity, EndpointRegistry.load(), timeout=30.0)
    guard = CURRENT_TIER.set(SafetyTier.SAFE)
    evidence: list[str] = []
    rows: list[dict] = []
    try:
        response = rest.get(LEADERBOARD)
        try:
            evidence.append(store.capture(response.request, response,
                                          SafetyTier.SAFE, "backtest.leaderboard"))
        except Exception:  # noqa: BLE001 -- a capture we could not write is not a read we did not make
            pass
        for bot in (response.json() or {}).get("bots", []):
            if not isinstance(bot, dict):
                continue
            drawdown = bot.get("max_drawdown_pct")
            rows.append({
                "strategy": bot.get("slug") or bot.get("name"),
                "name": bot.get("name"),
                "sharpe": bot.get("sharpe_ratio"),
                "total_return": bot.get("headline_return_pct"),
                "over": bot.get("headline_period"),
                # Theirs is signed; risk is compared by size, and the sign is
                # not information once the column is called a drawdown.
                "max_drawdown": abs(drawdown) if isinstance(
                    drawdown, (int, float)) else None,
                "win_rate": bot.get("win_rate"),
                "trades": bot.get("total_trades"),
                "clones": bot.get("total_clones"),
            })
    finally:
        rest.close()
        CURRENT_TIER.reset(guard)

    ranked = lab.rank(rows)[:limit]

    # Cross-check the front-runners against the tool that reports only real
    # backtest_results rows. A disagreement between their own two readings of
    # one strategy is a finding, not a rounding error: an agent ranking
    # candidates gets a different order depending which door it knocked on.
    #
    # The slug differs between the two surfaces as well -- the leaderboard says
    # `cryptobull-blue` and the tool wants `bt-cryptobull-blue` and refuses the
    # other with "unknown strategy". Both forms are tried, so a naming
    # convention is not reported as a missing strategy.
    nexus, mcp, token = _reader()
    try:
        for row in ranked[:5]:
            slug = str(row.get("strategy") or "")
            if not slug:
                continue
            for candidate in (slug, f"bt-{slug}") if not slug.startswith("bt-") \
                    else (slug,):
                payload = nexus._inner(mcp.call("get_strategy_returns",
                                                {"strategy": candidate}))
                measured = _metrics(payload)
                if measured:
                    row["cross_check"] = {"slug": candidate, **measured}
                    break
                row["cross_check"] = {"slug": candidate,
                                      "said": str(payload)[:160]}
            theirs = row.get("cross_check") or {}
            if isinstance(theirs.get("sharpe"), (int, float)) and isinstance(
                    row.get("sharpe"), (int, float)):
                gap = abs(theirs["sharpe"] - row["sharpe"])
                if gap > 0.05:
                    row["disagrees_by"] = round(gap, 4)
    finally:
        _done(mcp, token)

    lab.note_truth(ranked, evidence)
    return ranked


def surface() -> dict:
    """Their tool catalogue now, against the snapshot taken before the upgrade.

    `changed` is new on 2026-09-12. This compared `t["name"]` and nothing else,
    so every change that keeps a tool's name -- a renamed parameter, a new
    required one, a moved default -- left it silent, and the operator asked
    outright how it was possible we would not notice. The comparison is
    `qa/surface.py`, one reader shared with the patrol.
    """
    from qa import surface as shapes

    _nexus, client, token = _reader()
    try:
        listed = client.tools_list()
    finally:
        _done(client, token)
    names = sorted({t.get("name") for t in listed if isinstance(t, dict)
                    and t.get("name")})
    lab.note_surface(names)
    before = []
    try:
        before = json.loads(BASELINE.read_text(encoding="utf-8"))["tools"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        pass
    moved = shapes.tools_drift(before, listed)
    return {"now": names, **moved}


# --- their backtest, asked once ---------------------------------------------

BACKTEST_TOOL = "backtest_event_card_idea"
_PACE: list[float] = []


def card_baskets() -> list[dict]:
    """Their own cards as the sampler recorded them, newest basket each.

    The sampler already writes `basket: [{"symbol": "BTC", "weight": 0.9962}]`
    for every card it sees, which is exactly the shape their backtest takes --
    so the search starts from THEIR cards rather than from anything of ours,
    which is also what CLAUDE.md requires of where a strategy comes from.

    A card whose basket is a single coin is dropped: their tool takes two legs
    at least, and a one-coin card IS that coin, which the index history already
    tells us about.
    """
    newest: dict[str, dict] = {}
    for row in _samples():
        if row.get("type") != "card" or not row.get("card_id"):
            continue
        legs = [leg for leg in (row.get("basket") or [])
                if isinstance(leg, dict) and leg.get("symbol")]
        if len(legs) < qa_backtests.MIN_LEGS:
            continue
        newest[str(row["card_id"])] = {
            "card": str(row["card_id"]), "title": row.get("title") or "",
            "legs": legs}
    return list(newest.values())


def _samples() -> list[dict]:
    """The sampler's rows, read straight off the file it appends to."""
    from qa.state import state_dir

    target = state_dir() / "samples.jsonl"
    if not target.is_file():
        return []
    out = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _backtest_call(constituents, period_days: int, include_fees: bool = False,
                   starting_capital: float = 1000.0) -> dict:
    """One call to their tool, at SAFE, at their own pace.

    No evidence capture: a search makes thousands of these and the store keeps
    one witness per tool whatever we do, so capturing them all would cost a
    gigabyte to keep one file. A candidate that gets PROMOTED -- one we put to
    Nexus or trade on -- is re-run through `backtest_cited` instead, where the
    bytes are worth keeping because a verdict may one day cite them.
    """
    import time as _time

    wait = qa_backtests.next_slot(_PACE, _time.monotonic())
    if wait:
        _time.sleep(wait)
    _PACE.append(_time.monotonic())
    del _PACE[:-qa_backtests.PER_MINUTE]

    nexus, mcp, token = _reader()
    try:
        return nexus._inner(mcp.call(BACKTEST_TOOL, {
            "constituents": [{"symbol": leg["symbol"], "weight": leg["weight"]}
                             for leg in constituents],
            "period_days": int(period_days),
            "include_fees": bool(include_fees),
            "starting_capital": float(starting_capital)})) or {}
    finally:
        _done(mcp, token)


def backtest(constituents, period_days: int = 30, *, why: str = "",
             include_fees: bool = False, call=None, now=None) -> dict:
    """Their answer for one basket over one window, asked at most once.

    The register is consulted BEFORE the call, which is the whole of
    [operator 2026-09-12] *"at se netestuje to co uz bylo"*: a question already
    answered recently enough to still be true is answered from the file.
    `include_fees` is part of the fingerprint, so a reading after fees is a
    different question from one before them, and neither answers the other.
    """
    fp = qa_backtests.fingerprint(constituents, period_days, include_fees)
    known = qa_backtests.already(fp, now=now)
    if known:
        return {"cached": True, **known}
    answer = (call or _backtest_call)(constituents, period_days,
                                      include_fees=include_fees) or {}
    row = qa_backtests.record(constituents, period_days, answer, why=why,
                              include_fees=include_fees, now=now)
    return {"cached": False, **row}


def graded_pairs() -> list[dict]:
    """Every closed experiment beside the backtest number we ranked it on.

    The link between the two is the room's own basket: its plan names cards,
    each card's basket is in the sampler's rows, and the register holds what
    that basket scored. Where the register never saw it, the pair is dropped
    rather than filled with a zero -- the same rule as everywhere else here.
    """
    room_rows = rooms.load()
    baskets = {seed["card"]: seed["legs"] for seed in card_baskets()}
    register = qa_backtests.load()
    out = []
    for strategy in rooms.strategies(room_rows):
        room = strategy["id"]
        said = rooms.verdict_of(room_rows, room)
        if not said:
            continue
        plan = (rooms.plans(room_rows).get(room) or {}).get("legs") or []
        sharpes = []
        for leg in plan:
            legs = baskets.get(str(leg.get("card")))
            if not legs:
                continue
            try:
                fp = qa_backtests.fingerprint(legs, 30)
            except qa_backtests.BacktestError:
                continue
            rows = [r for r in register if r.get("fp") == fp
                    and r.get("s") is not None]
            if rows:
                sharpes.append(float(rows[-1]["s"]))
        if not sharpes:
            continue
        out.append({"room": room, "sharpe": sum(sharpes) / len(sharpes),
                    "verdict": said.get("verdict")})
    return out


def symbol_pool(seeds: list[dict]) -> list[str]:
    """Every coin their own cards are made of. Nothing from outside them."""
    return sorted({str(leg["symbol"]).upper() for seed in seeds
                   for leg in seed.get("legs") or [] if leg.get("symbol")})


def search(seeds: list[dict], pool: list[str] | None = None, cap: int = 12,
           *, call=None, now=None, out=None) -> dict:
    """Walk the neighbourhood of each of their baskets, asking each thing once.

    This composes baskets, and composing is where the rule bites: a basket we
    put together is a MEASUREMENT, never a proposal. The road from "the
    backtest found it" to "it is on paper" runs through a question to Nexus and
    a room opened from his answer -- CLAUDE.md, and the reason nothing in here
    can reach an order or a room.
    """
    moves = [move for seed in seeds
             for move in qa_backtests.neighbourhood(seed, pool, cap)]
    return {**search_moves(moves, call=call, now=now, out=out),
            "seeds": len(seeds)}


def search_moves(moves: list[dict], *, call=None, now=None, out=None) -> dict:
    """Ask each prepared basket once, whatever assembled the queue.

    Split out of `search` so the hand-run command can walk a queue that is
    their cards PLUS the climb from the register (`search_queue`), rather than
    only the cards. The walking itself never differed between the two callers;
    only what they were willing to put in front of it did.
    """
    did = {"asked": 0, "from_register": 0, "failed": 0, "seeds": 0}
    for move in moves or []:
        try:
            said = backtest(move["legs"], move["period"], why=move["why"],
                            call=call, now=now)
        except qa_backtests.BacktestError:
            # A basket their tool would refuse is not a failed reading; it is
            # a question that was never a question.
            continue
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            did["failed"] += 1
            if out:
                out(f"  {move['why']}: {exc}")
            continue
        did["from_register" if said["cached"] else "asked"] += 1
        if out and not said["cached"]:
            out(f"  {move['why']:56} sharpe {said['s']}  ret {said['r']}%")
    return did


# --- the loop --------------------------------------------------------------

def status() -> str:
    rows = lab.load()
    nexus_rows = _nexus_rows()
    out = []

    open_now = lab.open_sessions(rows)
    if open_now:
        out.append(f"session {open_now[-1]} is OPEN -- close it when you stop, "
                   f"or the next one inherits an unfinished night")
    last = lab.last_close(rows)
    if last:
        when = str(last.get("at"))[:16].replace("T", " ")
        kind = "night" if last.get("mode") == "night" else "session"
        out.append(f"last {kind} {last.get('session')} closed {when}")
        if kind == "night":
            # What the night did, in the morning, before anything else is read:
            # this is the only place a night that was blocked all the way
            # through is distinguishable from a night that found nothing.
            did = last.get("did") or {}
            skipped = did.get("skipped") or {}
            out.append(f"  the night: {did.get('backtests', 0)} backtest(s), "
                       f"{did.get('asked', 0)} asked, "
                       f"{did.get('answered', 0)} answered, "
                       f"{did.get('cycles', 0)} cycle(s) over "
                       f"{did.get('ticks', 0)} tick(s); ended "
                       f"{did.get('stopped', '?')}")
            for reason in ("pass", "backoff", "cap"):
                if skipped.get(reason):
                    out.append(f"  held off:  {skipped[reason]} tick(s) by "
                               f"{reason}")
            for question in did.get("questions") or []:
                out.append(f"  asked:   {question.get('id')} about "
                           f"{question.get('about')}")
            for problem in (did.get("errors") or [])[:3]:
                out.append(f"  failed:  {problem}")
        for lesson in last.get("lessons") or []:
            out.append(f"  learned: {lesson}")
        for item in last.get("next") or []:
            out.append(f"  next:    {item}")

    waiting = lab.outstanding(nexus_rows)
    recent = [r for r in nexus_rows if r.get("type") == "question"][-5:]
    answered = {r.get("id") for r in nexus_rows if r.get("type") == "answer"}
    healthy = sum(1 for r in recent if r.get("id") in answered)
    out.append(f"Nexus: {healthy} of the last {len(recent)} questions answered"
               + (f"; {len(waiting)} still outstanding ({', '.join(waiting[:3])})"
                  if waiting else ""))

    snapshot = lab.last_truth(rows)
    if snapshot:
        age = (_now() - (_moment(snapshot.get("at")) or _now())).total_seconds()
        out.append(f"ground truth ranked {age / 3600:.0f} h ago, "
                   f"{len(snapshot.get('ranked') or [])} concept(s)")
    else:
        out.append("ground truth: never pulled -- `lab.py truth`")

    known = lab.last_surface(rows)
    if known:
        out.append(f"their catalogue: {len(known.get('tools') or [])} tools at "
                   f"{str(known.get('at'))[:16].replace('T', ' ')}")

    room_rows = rooms.load()
    for strategy in rooms.strategies(room_rows):
        room = strategy["id"]
        acceptance = rooms.acceptance_of(room_rows, room)
        said = rooms.verdict_of(room_rows, room)
        name = rooms.names(room_rows).get(room, room)
        if said:
            out.append(f"{room} {name}: {said['verdict']} "
                       f"({said.get('why', '')[:70]})")
        elif acceptance:
            state = lab.verdict(acceptance, {}, _now())
            when = state.get("closes_at") or "now"
            out.append(f"{room} {name}: criterion {acceptance['window_days']}d"
                       + (" (adopted)" if acceptance.get("adopted") else "")
                       + (f", window closes {when[:16].replace('T', ' ')}"
                          if state["verdict"] == "open"
                          else " -- VERDICT DUE: `lab.py verdicts`"))
        else:
            out.append(f"{room} {name}: no criterion -- `lab.py adopt {room}` "
                       f"before it can run")

    out.append(f"{_running_experiments()} experiment(s) running, "
               f"{lab.CAPS['running_experiments']} is the cap")
    if pass_in_flight():
        out.append("a deep pass is running: no questions and no orders until "
                   "it finishes")

    # Cached, not recomputed: N_eff needs one live call per open leg, and
    # `status` stays a local read like the rest of this function. `cycle`
    # refreshes it; this shows the newest reading and its age.
    said = lab.last_n_eff(rows)
    if said and "n_eff" in said:
        age = (_now() - (_moment(said.get("at")) or _now())).total_seconds()
        out.append(f"N_eff {said['n_eff']:.1f} of {said['n']} open "
                   f"(⍴={said['rho']:.2f}), {age / 3600:.0f} h old")

    # Purely local: paper.jsonl and the sampler's own samples, both diaries
    # already on this disk. The last unmeasured link of "bet -> resolves ->
    # paid" -- a card resolving on its own, never through our `close`.
    from qa.rooms import load_samples

    resolved = lab.resolved_without_us(_sibling("paper").load(), load_samples())
    for row in resolved:
        out.append(f"RESOLVED WITHOUT US: {row['position_id']} "
                   f"({row['card_id']}), {row['realized_pnl_usdc']} USDC, "
                   f"{str(row['resolved_at'])[:16].replace('T', ' ')}")
    return "\n".join(out)


def cycle() -> dict:
    """Finish what is in flight, take a sample, and compare their catalogue."""
    did: dict[str, object] = {}
    nexus = _sibling("nexus")

    waiting = lab.outstanding(_nexus_rows())
    finished = []
    for question_id in waiting:
        try:
            result = nexus.answer(question_id)
            finished.append({question_id: result.get("status")})
        except (Exception, SystemExit) as exc:  # one bad poll is not the cycle
            # SystemExit included: nexus.answer raises it for a question it
            # cannot find or one already answered, and a night must survive
            # both.
            finished.append({question_id: f"poll failed: {exc}"})
    did["polled"] = finished

    try:
        _sibling("sampler").main(["once"])
        did["sampled"] = True
    except Exception as exc:  # noqa: BLE001
        did["sampled"] = f"failed: {exc}"

    try:
        did["catalogue"] = surface()
    except Exception as exc:  # noqa: BLE001
        did["catalogue"] = f"failed: {exc}"

    try:
        did["n_eff"] = book_correlation()
    except Exception as exc:  # noqa: BLE001
        did["n_eff"] = f"failed: {exc}"

    lab.note_cycle(did)
    return did


INDEX_HISTORY = "/api/v1/event-cards/{card}/index-history"
# A card whose basket is one coin is that coin's index. Their own sampler rows
# name the basket; these three were >= 99% BTC on 2026-09-11, and the
# acceptance records WHICH was used, so a verdict can be re-read later.
BTC_PROXY = "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161"


def _history(client, card: str) -> list[dict]:
    response = client.get(INDEX_HISTORY.format(card=card))
    if response.status_code != 200:
        return []
    body = response.json() or {}
    return body.get("points") or body.get("history") or []


def _basket_returns(points: list[tuple], since) -> list[float]:
    """Daily % change of one card's index, from `since` on. `points` is
    already `_at`/float pairs, sorted, from `qa.lab._points`."""
    inside = [(t, v) for t, v in points if t >= since]
    if len(inside) < 2:
        return []
    out = []
    for (t0, v0), (t1, v1) in zip(inside, inside[1:]):
        if v0:
            out.append((v1 / v0 - 1.0) * 100.0)
    return out


def open_book_returns(now=None, history=None, window_days: float = 14.0
                      ) -> dict[str, list[float]]:
    """One aligned return series per RUNNING room, weighted across its legs.

    `history` is `(card) -> list[dict]`, injectable so this needs no network
    to test; the real caller (`book_correlation`) binds it to a live client
    the same way `verdicts()` does. Each room's legs are combined into one
    basket return series -- share-weighted, side-flipped for a bear leg -- so
    two rooms betting the same basket through different legs still read as
    correlated, which is the point of `qa.lab.n_eff`.
    """
    since = (now or _now()) - timedelta(days=window_days)
    rows = rooms.load()
    out: dict[str, list[float]] = {}
    for strategy in rooms.strategies(rows):
        room = strategy["id"]
        if rooms.status_of(rows, room) != "running":
            continue
        plan = (rooms.plans(rows).get(room) or {}).get("legs") or []
        if not plan:
            continue
        per_leg = []
        for leg in plan:
            card = leg.get("card")
            if not card:
                continue
            points = lab._points(history(card) if history else [])
            returns = _basket_returns(points, since)
            if not returns:
                continue
            way = -1.0 if str(leg.get("side")).lower() == "bear" else 1.0
            share = float(leg.get("share") or 1.0)
            per_leg.append((share, [way * r for r in returns]))
        if not per_leg:
            continue
        length = min(len(r) for _, r in per_leg)
        if length == 0:
            continue
        total_share = sum(share for share, _ in per_leg) or 1.0
        out[room] = [sum(share * r[i] for share, r in per_leg) / total_share
                     for i in range(length)]
    return out


def book_correlation(now=None) -> dict:
    """`lab.n_eff` over the real open book -- one live call per open leg."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    client = build_client(identity, EndpointRegistry.load(), timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        returns = open_book_returns(
            now=now, history=lambda card: _history(client, card))
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    said = lab.n_eff(returns)
    if "n_eff" in said:
        lab.note_n_eff(said)
    return said


def adopt(room: str, window_days: float = 7.0, stop_pct: float = 5.0,
          benchmark: str | None = BTC_PROXY) -> dict:
    """Take over a room that was already running, from now on.

    Nothing retroactive. A criterion written today cannot judge a week that has
    already happened -- it would be a criterion fitted to the numbers, which is
    the one thing preregistration exists to prevent. So the window starts now,
    the verdict reads only what comes after, and the row says `adopted` so
    nobody later mistakes it for a criterion written in advance.
    """
    return rooms.set_acceptance(
        room, window_days=window_days, stop_pct=stop_pct, benchmark_card=benchmark,
        adopted=True,
        why=(f"adopted {_now().isoformat(timespec='minutes')}: the room was "
             f"already running, so the window starts now and nothing before it "
             f"is judged"))


def verdicts(now=None) -> list[dict]:
    """Every room whose window has closed and has no verdict yet."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    rows = rooms.load()
    due = []
    for strategy in rooms.strategies(rows):
        room = strategy["id"]
        acceptance = rooms.acceptance_of(rows, room)
        if acceptance is None or rooms.verdict_of(rows, room) is not None:
            continue
        said = lab.verdict(acceptance, {}, now or _now())
        if said["verdict"] == "open":
            continue
        due.append((room, acceptance))
    if not due:
        return []

    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    client = build_client(identity, EndpointRegistry.load(), timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    out = []
    try:
        for room, acceptance in due:
            cards = [leg.get("card") for leg in acceptance.get("legs") or []]
            if acceptance.get("benchmark_card"):
                cards.append(acceptance["benchmark_card"])
            series = {card: _history(client, card) for card in cards if card}
            said = lab.verdict(acceptance, series, now or _now())
            rooms.record_verdict(room, said)
            rooms.set_status(
                room, "stopped",
                f"verdict: {said['verdict']} -- {said.get('why', '')}"[:400])
            out.append({"room": room, **said})
    finally:
        client.close()
        CURRENT_TIER.reset(token)
    return out


def ask(question: str, wait: bool = True) -> dict:
    rows = _nexus_rows()
    may, why = lab.may_ask(_asked_today(rows), pass_in_flight())
    if may:
        may, why = lab.may_ask_now(rows, _now())
    if not may:
        raise SystemExit(f"not asking: {why}")
    return _sibling("nexus").ask(question, wait=wait)


def buy(card_id: str, usdc: float, nexus_id: str | None, confirm: bool) -> dict:
    if pass_in_flight():
        raise SystemExit(
            "not buying: a deep pass is running and #87 judges the newest "
            "trade. Wait for it to finish")
    ok, why = lab.affordable(usdc, _free_cash(), _running_experiments(),
                             deployed=_deployed())
    if not ok:
        raise SystemExit(f"not buying: {why}")
    print(f"[lab] {why}")
    return _sibling("paper").buy(card_id, usdc, nexus_id, confirm)


# --- the night -------------------------------------------------------------

BREAKS_IT = (
    "Their own backtest ranks {slug} at Sharpe {sharpe} with a max drawdown of "
    "{dd}% over {over}. What BREAKS it? Name the market condition it fails in, "
    "the kind of event card that would make it fail fastest, and one number we "
    "could watch that turns bad BEFORE the drawdown does. If the ranking "
    "itself is measured over too short a window to mean anything, say that "
    "instead -- we would rather drop a candidate than trade a statistic."
)


def _candidates(ranked: list[dict], already: set[str]) -> list[str]:
    """The ranked concepts we have not asked about tonight, best first."""
    out = []
    for row in ranked:
        slug = str(row.get("strategy") or "").strip()
        if slug and slug not in already and slug not in out:
            out.append(slug)
    return out


def _night_question(ranked: list[dict], slug: str) -> str:
    row = next((r for r in ranked if r.get("strategy") == slug), {})
    return BREAKS_IT.format(slug=slug, sharpe=row.get("sharpe", "?"),
                            dd=row.get("max_drawdown", "?"),
                            over=row.get("over", "an unstated window"))


def _night_backoff():
    """How long their own failure asked us to stay away."""
    return lab.backoff_until(_nexus_rows(), _now())


def night_moves() -> list[dict]:
    """Everything worth asking their backtest tonight, in one flat queue.

    Built once, deterministically, so a night that ends mid-queue is a night
    the next one resumes rather than restarts -- and so a tick can take a
    bounded bite without holding the walk's state in its head.
    """
    seeds = card_baskets()
    pool = symbol_pool(seeds)
    return [move for seed in seeds
            for move in qa_backtests.neighbourhood(seed, pool, cap=24)]


def search_queue(seeds: list[dict], rows: list[dict] | None = None,
                 *, pool_from_cards: bool = True,
                 cap: int = 12, limit: int = 8) -> list[dict]:
    """Every basket worth asking about: their cards, AND what scored well.

    The one place both callers take their moves from. `night()` already
    climbed -- it refills from the register the moment its first queue empties
    -- but the hand-run `lab.py search` walked only `card_baskets()`, which is
    finite and small (seven cards the sampler has seen with two legs or more).
    So the second sweep of 2026-09-13 came back **0 asked, 32 already known**,
    which looks identical to a finished search and is really a queue nobody
    refilled. The operator asked that afternoon why so few backtests had run.

    Order matters: the cards first, because they are THEIR baskets and
    CLAUDE.md says a strategy starts from their side, then the climb from what
    measured well. A register with nothing in it yet leaves just the cards,
    which is what a first run should be.
    """
    universe = symbol_pool(seeds)
    queue = [move for seed in seeds
             for move in qa_backtests.neighbourhood(seed, universe, cap)]
    seen = {move.get("fp") for move in queue if move.get("fp")}
    # THEIR whole card universe, not just the symbols already winning -- see
    # night_refill on why the pool is the difference between a climb and a
    # collapse.
    # `pool_from_cards=False` is the NEGATIVE CONTROL, not an option anything
    # calls: a test that shows the wide pool reaches a symbol has to show the
    # narrow one does not, or it is asserting a coincidence. L05, deep pass of
    # 2026-09-13 -- the first version of that test could not see the pool at
    # all, and reverting the fix left it green.
    for move in night_refill(rows=rows, limit=limit, cap=cap,
                             pool=universe if pool_from_cards else None):
        if move.get("fp") and move["fp"] in seen:
            continue
        seen.add(move.get("fp"))
        queue.append(move)
    return queue


def night_refill(rows: list[dict] | None = None, limit: int = 8,
                 cap: int = 24, pool: list[str] | None = None) -> list[dict]:
    """The next round, seeded by what actually scored — not by where we began.

    `night_moves()` is the neighbourhood of THEIR cards, and it is finite: 168
    moves, 30 a tick, a tick every two minutes. Six ticks. Twelve minutes of a
    fourteen-hour night, and then the night had nothing left to do but wait for
    dawn — against the operator's *"celou noc backtesty nonstop"* and against
    the phase's own written criterion of thousands.

    A refill is not the same queue again. It takes the best readings the
    register holds and walks THEIR neighbourhoods, so each round starts from
    what measured well rather than from the card we happened to begin with.
    That is the difference between a night that repeats itself and one that
    climbs.

    Nothing here proposes a trade. A basket is a question for their backtest,
    and the road from "this measured well" to "this goes in paper" still runs
    through Nexus -- CLAUDE.md, and the rule the whole laboratory is built on.
    """
    rows = qa_backtests.load() if rows is None else rows
    seeds = []
    for row in qa_backtests.best(rows, limit=limit):
        legs = [{"symbol": str(pair[0]).upper(), "weight": float(pair[1])}
                for pair in (row.get("legs") or [])
                if isinstance(pair, (list, tuple)) and len(pair) == 2]
        if len(legs) >= qa_backtests.MIN_LEGS:
            seeds.append({"legs": legs,
                          "title": str(row.get("why") or "")[:60]})
    if not seeds:
        return []
    # The pool is what `add` and `drop` may substitute FROM. Left to the seeds
    # alone it is the winners' own symbols, and the climb can then only
    # reshuffle them: on 2026-09-13 all twenty of the top twenty readings
    # contained KSM, and its share of new readings went 27/65 -> 49/69 in the
    # hours after this refill was first wired in. The more baskets tested
    # around one symbol, the more surely the best observed Sharpe is that
    # symbol's noise -- the deflated-Sharpe argument Nexus made to us about
    # stockbull-blue, on our own side of the glass. A caller that knows the
    # wider universe (their cards) passes it.
    return [move for seed in seeds
            for move in qa_backtests.neighbourhood(
                seed, pool or symbol_pool(seeds), cap=cap)]


# What the night writes as a criterion when it opens a room unattended. Ours,
# not Nexus's: his answers rarely carry a machine-readable window or stop, and
# a room with no criterion is one no verdict can ever reach. Written with
# `adopted=True` so nobody reads them as numbers he gave.
#
# The stop is a DRAWDOWN, so it is positive: `qa.lab.verdict` compares it with
# `peak - value`. It was -10.0 until 2026-09-19, which every drawdown of zero
# or more exceeds -- every room the night ever opened would have been refuted
# at its first verdict, whatever it earned. It never fired only because the
# night never launched anything.
NIGHT_WINDOW_DAYS = 5.0
NIGHT_STOP_PCT = 10.0


def _stake(free: float | None) -> float:
    """One experiment's size, FLOORED to the cent.

    `round()` was the first version and it rounds UP: on the balance actually
    in state/paper.jsonl -- 89000.96 -- it produced 1780.02 against a ceiling of
    1780.0192, so `affordable` refused, and the refusal read "1780 is more than
    2% of the 89001 free (1780)" because both sides round for display. Every
    order of every night, deterministically, since `_free_cash` does not move
    while nothing is bought. Only a balance whose 2% lands exactly on a cent
    escaped it, and 100000.00 does, which is why no fixture saw it.

    A stake is money. Asking for a cent more than the cap allows is asking for
    more than the cap allows.
    """
    import math

    if not free or free <= 0:
        return 0.0
    return math.floor(free * lab.CAPS["share_of_free_cash"] * 100) / 100


def _leg_stakes(free: float | None, deployed: float, legs: int,
                half: bool = False) -> list[float]:
    """What each card of ONE room takes, floored to the cent.

    [operator 2026-09-12] fifty at once, under a ceiling of 60% of the book --
    so a room may take the book's 60/50 = 1.2%, split evenly across its cards.
    Until 2026-09-19 every CARD took 2% of what was free, so a three-card room
    took six per cent and the ceiling stopped the laboratory near a dozen
    rooms, with thirty-odd experiments still owed.

    The per-order ceiling (`_stake`, 2% of what is free) still caps each leg:
    near the end of the book, free is 40% of it and 2% of that is less than a
    one-card room's 1.2%. `half` is for a card nobody could backtest.
    """
    import math

    count = max(int(legs), 0)
    if free is None or free <= 0 or count == 0:
        return [0.0] * count
    book = free + max(deployed or 0.0, 0.0)
    share = lab.CAPS["total_exposure"] / lab.CAPS["running_experiments"]
    each = min(book * share / count, _stake(free))
    if half:
        each /= 2
    return [math.floor(each * 100) / 100] * count


CARD_PATH = "/api/v1/event-cards/{card}"


def _card_live(card: str) -> dict | None:
    """What their API says a card holds, right now -- or None if it does not
    know the card at all.

    #91 was a card Nexus invented; its door answered 404. So a card an answer
    names is read here before anything is backtested or bought, and a 404 is
    the ONLY thing read as "does not exist". Any other failure raises: a card
    we could not read is not a card that is missing (rule 8), and the next tick
    reads it again.
    """
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    client = build_client(identity, EndpointRegistry.load(), timeout=20.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(CARD_PATH.format(card=card))
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        body = response.json()
    finally:
        client.close()
        CURRENT_TIER.reset(token)
    if not isinstance(body, dict):
        raise RuntimeError("the card's body is not an object")
    legs = []
    for item in body.get("basket") or []:
        if not isinstance(item, dict) or not item.get("symbol"):
            continue
        try:
            weight = float(item.get("weight"))
        except (TypeError, ValueError):
            continue
        if weight > 0:
            legs.append({"symbol": str(item["symbol"]).upper(),
                         "weight": weight})
    legs.sort(key=lambda leg: -leg["weight"])
    tradeable = body.get("tradeable_now")
    return {"legs": legs[:qa_backtests.MAX_LEGS],
            "tradeable": tradeable if isinstance(tradeable, bool) else None,
            "title": str(body.get("title") or "")}


def _gate(card: str, legs: list[dict]) -> dict:
    """Their backtest of one card's basket, after fees, over the gate's
    windows -- read through the register, so a card is never priced twice --
    and the verdict `qa.lab.gate` draws from it.

    "unread" when their backtest did not answer: that is neither a pass nor a
    rejection, and the caller leaves the answer for the next tick.
    """
    readings = []
    basket = [leg for leg in legs or [] if leg.get("symbol")]
    if len(basket) >= qa_backtests.MIN_LEGS:
        total = sum(float(leg["weight"]) for leg in basket) or 1.0
        basket = [{"symbol": leg["symbol"],
                   "weight": float(leg["weight"]) / total} for leg in basket]
        for period in lab.GATE["periods"]:
            try:
                readings.append(backtest(basket, period, include_fees=True,
                                         why=f"gate {card[:8]}"))
            except qa_backtests.BacktestError:
                continue
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                return {"verdict": "unread",
                        "why": f"their backtest did not answer ({exc})"}
    return lab.gate(readings)


def night_promote(since: datetime | None = None) -> dict:
    """Launch what Nexus endorsed tonight, on paper, under the day's brakes.

    [operator 2026-09-12] *"Jasne ze v noci muze spoustet."* The night used to
    research and place nothing -- a narrowing that lived in a plan they do not
    read, and three reviewers said so on the same day.

    It launches down ONE road, the only one CLAUDE.md allows: a room opens from
    a whole Nexus answer, never from a basket of ours, however well it
    backtested. The search finds candidates; the question makes them his; his
    answer is what may be acted on.

    The refusals, each one a finding we already paid for:

      * a card their API does not know is reported and not bought (#91 --
        Nexus invented one, with a live-looking index; its door said 404);
      * a card their own backtest prices at a loss after fees, or at a Sharpe
        under half, gets no room (`qa.lab.gate`) -- [operator 2026-09-19], the
        promising ones become rooms. The numbers go on the record, so the next
        question can tell Nexus how his idea measured;
      * an answer that names no card proposes nothing (NEX-0026 was the best
        answer we have had and named none);
      * ten new rooms a rolling day, and `affordable` decides the size and
        whether there is room at all;
      * nothing at all while a deep pass runs, because it is verifying #85,
        #86 and #87 over these very trades.

    A card that could not be READ, or cannot be traded right now, decides
    nothing: the answer waits for the next tick whole.

    Returns what it did and, for everything it did not, why -- so the morning
    reads a reason rather than a silence.
    """
    if pass_in_flight():
        return {"rooms": 0, "orders": 0, "held": ["a deep pass is running"]}

    answers = [row for row in _nexus_rows() if row.get("type") == "answer"
               and (since is None or (_moment(row.get("at")) or _now()) >= since)]
    if not answers:
        return {"rooms": 0, "orders": 0, "held": []}

    stored = rooms.load()
    linked = {str(row.get("origin")) for row in stored
              if row.get("type") == "strategy"}
    today = lab.rooms_within(stored, _now())
    cap = lab.CAPS["new_rooms_per_day"]
    decided = lab.gates()
    paper = _sibling("paper")
    opened, placed, held = 0, 0, []
    bought: set[str] = set()

    for answer in answers:
        origin = str(answer.get("id") or "")
        if not origin or origin in linked:
            continue
        # Every id the answer names; whether it EXISTS is asked of their API
        # below, not of what our own sampler happened to have seen.
        named = lab.proposed_cards(answer.get("text"), ())["unknown"]
        if not named:
            held.append(f"{origin}: names no card we can act on; the morning "
                        f"reads it")
            continue
        spent = ("reject", "unknown_card")
        if all(decided.get((origin, card), {}).get("verdict") in spent
               for card in named):
            continue  # decided on an earlier tick, and nothing in it may run
        if today + opened >= cap:
            held.append(f"{origin}: {today + opened} room(s) opened in the last "
                        f"24 h and the cap is {cap} a day — the next day takes "
                        f"the rest")
            break

        chosen: dict[str, dict] = {}
        waiting = False
        for card in named:
            # Nexus repeats its favourite card across answers, and "fifty
            # experiments" meant fifty different things.
            if card in bought:
                continue
            prior = decided.get((origin, card))
            if prior and prior.get("verdict") in spent:
                continue
            try:
                live = _card_live(card)
            except Exception as exc:  # noqa: BLE001 -- unread is not absent
                held.append(f"{origin}/{card[:8]}: the card could not be read "
                            f"({exc}) — the next tick tries again")
                waiting = True
                continue
            if live is None:
                said = {"verdict": "unknown_card",
                        "why": "their API does not know this card (#91)"}
                decided[(origin, card)] = lab.note_gate(origin, card, said)
                held.append(f"{origin}: {card[:8]} is a card their API does "
                            f"not know (#91) — not bought")
                continue
            if live.get("tradeable") is False:
                held.append(f"{origin}/{card[:8]}: not tradeable now — the next "
                            f"tick tries again")
                waiting = True
                continue
            if prior is None:
                said = _gate(card, live.get("legs") or [])
                if said["verdict"] == "unread":
                    held.append(f"{origin}/{card[:8]}: {said['why']} — the next "
                                f"tick tries again")
                    waiting = True
                    continue
                prior = decided[(origin, card)] = lab.note_gate(
                    origin, card, said)
            if prior["verdict"] == "reject":
                held.append(f"{origin}/{card[:8]}: their backtest rejects it — "
                            f"{prior.get('why')}")
                continue
            chosen[card] = {**prior, "title": live.get("title") or ""}
        if waiting or not chosen:
            continue

        # MONEY FIRST, and nothing consumed before it answers. Opening the room
        # ahead of this put the origin in `linked` on a refusal, which meant a
        # night that could afford nothing still spent every answer it touched --
        # `open_strategy` then refuses the morning too. The room's stakes are
        # fixed here, from the book as it stands when the room opens.
        cards = list(chosen)
        free, deployed = _free_cash(), _deployed()
        whole = _leg_stakes(free, deployed, len(cards))
        halved = _leg_stakes(free, deployed, len(cards), half=True)
        untested = [c for c in cards if chosen[c]["verdict"] == "unbacktestable"]
        stakes = [halved[i] if card in untested else whole[i]
                  for i, card in enumerate(cards)]
        ok, why = lab.affordable(stakes[0], free, _running_experiments(),
                                 deployed=deployed)
        if not ok or stakes[0] <= 0:
            held.append(f"{origin}: {why or 'no stake'} — left whole for the "
                        f"morning")
            continue

        tested = "; ".join(f"{c[:8]} {chosen[c].get('why')}" for c in cards)
        name = (chosen[cards[0]]["title"] or f"{origin}: {cards[0][:8]}")
        try:
            room = rooms.open_strategy(origin, name[:rooms.MAX_TITLE])["id"]
            # The legs are the laboratory's READING of his answer -- every card
            # it names, bull, evenly -- because his answers carry no machine-
            # readable split. The criterion takes them, or `qa.lab.verdict` has
            # nothing to score and every room ends inconclusive.
            plan = rooms.set_plan(
                room, [{"card": c, "side": "bull",
                        "share": round(1.0 / len(cards), 6)} for c in cards])
            # A room with no criterion is one no verdict can ever reach:
            # `verdicts()` skips it and `_running_experiments()` cannot see it,
            # so the position would never be graded and never close. The window
            # and the stop are OURS, not his -- `adopted` says so on the row.
            rooms.set_acceptance(
                room, window_days=NIGHT_WINDOW_DAYS, stop_pct=NIGHT_STOP_PCT,
                legs=plan["legs"], benchmark_card=BTC_PROXY,
                why=(f"opened unattended from {origin}; the window, the stop "
                     f"and the even split are the laboratory's defaults, not "
                     f"numbers Nexus gave. Backtest: {tested}"
                     + (f". NOT backtested: {', '.join(c[:8] for c in untested)}"
                        f" -- half stake" if untested else ""))[:900],
                adopted=True)
        except rooms.RoomError as exc:
            held.append(f"{origin}: {exc}")
            continue
        opened += 1

        in_room = 0
        for card, stake in zip(cards, stakes):
            free = _free_cash()
            ok, why = lab.affordable(stake, free, _running_experiments(),
                                     deployed=_deployed())
            if not ok or stake <= 0:
                held.append(f"{origin}/{card[:8]}: {why or 'no stake'}")
                break
            paper.buy(card, stake, origin, True)
            bought.add(card)
            placed += 1
            in_room += 1
        if in_room:
            try:
                rooms.set_status(room, "running",
                                 why=f"opened by the laboratory from {origin}")
            except rooms.RoomError as exc:
                held.append(f"{room}: {exc}")
    return {"rooms": opened, "orders": placed, "held": held}


def _night_search(moves: list[dict]) -> dict:
    """One bite of the queue. The register answers what it already knows."""
    did = {"asked": 0, "known": 0, "failed": 0}
    for move in moves:
        try:
            said = backtest(move["legs"], move["period"], why=move["why"])
        except qa_backtests.BacktestError:
            continue
        except (Exception, SystemExit):  # noqa: BLE001
            did["failed"] += 1
            continue
        did["known" if said["cached"] else "asked"] += 1
    return did


def _night_ask(slug: str, question: str) -> dict:
    """One question, put down and left with their side.

    `wait=False` on purpose: waiting blocks for up to fifteen minutes, which
    would carry a tick past both the deadline and the deep-pass check it made
    on the way in. The next cycle picks the answer up. The one straddle left --
    a poll in flight when a pass starts -- is under a minute wide and not worth
    a lock.
    """
    return _sibling("nexus").ask(question, wait=False)


def _lessons(did: dict, ranked: list[dict]) -> list[str]:
    """At most three, drawn from what was counted rather than from opinion."""
    out = []
    if did.get("backtests"):
        out.append(f"walked {did['backtests']} backtest(s), "
                   f"{did.get('already_known', 0)} already in the register")
    if did["asked"]:
        out.append(f"asked Nexus {did['asked']} question(s); "
                   f"{did['answered']} came back by dawn")
    if did["skipped"]["pass"]:
        out.append(f"{did['skipped']['pass']} of {did['ticks']} ticks did "
                   f"nothing: a deep pass was in flight")
    if did["skipped"]["backoff"]:
        out.append(f"{did['skipped']['backoff']} tick(s) waited out a backoff "
                   f"their own failure asked for")
    if ranked and len(out) < lab.MAX_LESSONS:
        best = ranked[0]
        out.append(f"their best-ranked concept was {best.get('strategy')} "
                   f"(sharpe {best.get('sharpe')}, over {best.get('over')})")
    if not out:
        out.append("the night ran and found nothing worth a line")
    return out[:lab.MAX_LESSONS]


def night(until: str, *, clock=None, sleep=None, actions=None, out=print) -> dict:
    """Research until an hour the operator names, then stop.

    One process, started by them, with its end written into it -- not a
    scheduler. [operator 2026-09-12] *"ne zadene schedulery automaticke
    nechci"*. Nothing here trades, files or commits: the night measures and
    asks, the morning acts on what it found. That is not only prose -- the
    doors it can reach are the four in `actions`, and none of them is a hand
    that spends.

    What it does with the hours: picks up answers that are still in flight,
    samples the running experiments, re-ranks their backtests when the snapshot
    goes stale, and asks Nexus what breaks the best candidates -- one question
    at a time, two hours apart, twelve at most. `--no-wait` on the ask is
    deliberate: waiting on their side blocks for up to fifteen minutes, which
    would carry a tick past both the deadline and the deep-pass check it made
    on the way in. The next tick picks the answer up.

    The clock is read every loop rather than counted down, so a laptop that
    slept still stops at the hour it was given.
    """
    clock = clock or (lambda: datetime.now().astimezone())
    sleep = sleep or time.sleep
    started = clock()
    due = lab.deadline(until, started)
    # Every door is a name resolved here, not inside a lambda: a mistyped
    # default would otherwise surface at three in the morning, on their machine.
    actions = actions or {
        "pass": pass_in_flight, "backoff": _night_backoff, "cycle": cycle,
        "truth": functools.partial(truth, limit=8), "ask": _night_ask,
        "search": _night_search, "moves": night_moves,
        "refill": night_refill,
        "promote": functools.partial(night_promote, since=started),
        "asked_today": _asked_today,
    }

    session = lab.open_session(mode="night", until=due.isoformat())["session"]
    did = {"ticks": 0, "cycles": 0, "truths": 0, "asked": 0, "answered": 0,
           "backtests": 0, "already_known": 0, "refills": 0,
           "rooms": 0, "orders": 0, "held": [],
           "errors": [], "stopped": "deadline",
           "skipped": {"pass": 0, "backoff": 0, "cap": 0, "too soon": 0,
                       "nothing to ask about": 0},
           "questions": []}
    queue = list((actions.get("moves") or (lambda: []))())
    # The cap is a rolling day's, so what the day already asked counts: a
    # night started after a day of loop ticks does not get a fresh 24.
    state: dict = {"asked": int((actions.get("asked_today")
                                 or (lambda: 0))() or 0),
                   "candidates": [], "hold_until": None,
                   "pending": len(queue)}
    ranked: list[dict] = []
    asked_about: set[str] = set()

    out(f"laboratory night {session}: research only, no orders, no filings.")
    out(f"  started {started.isoformat(timespec='minutes')}")
    out(f"  ends    {due.isoformat(timespec='minutes')} "
        f"({(due - started).total_seconds() / 3600:.1f} h from now)")
    out(f"  at most {lab.CAPS['questions_per_day'] - state['asked']} more "
        f"question(s) today ({lab.CAPS['questions_per_day']} a rolling day), "
        f"at least {lab.NIGHT['ask_seconds'] // 60} min apart, and their own "
        f"backoff on top. Ctrl-C stops it.")

    crashed: BaseException | None = None
    try:
        while clock() < due:
            now = clock()
            did["ticks"] += 1
            state["pass_running"] = bool(actions["pass"]())
            state["hold_until"] = actions["backoff"]()
            plan = lab.night_tick(state, now)
            if plan["skipped"]:
                did["skipped"][plan["skipped"]] = \
                    did["skipped"].get(plan["skipped"], 0) + 1

            for step in plan["do"]:
                try:
                    if step == "search":
                        size = lab.NIGHT["search_batch"]
                        bite, queue = queue[:size], queue[size:]
                        got = actions["search"](bite) or {}
                        did["backtests"] += got.get("asked", 0)
                        did["already_known"] += got.get("known", 0)
                        if not queue:
                            # The first queue is finite -- 168 moves, six ticks,
                            # twelve minutes of a fourteen-hour night. Refill
                            # from what has actually scored, so the night climbs
                            # instead of stopping. An empty refill (nothing
                            # measured yet, or nothing clean) ends the search
                            # honestly rather than looping on nothing.
                            queue = list((actions.get("refill")
                                          or (lambda: []))())
                            did["refills"] += 1 if queue else 0
                        state["pending"] = len(queue)
                        if got.get("asked") and out:
                            out(f"  {now.strftime('%H:%M')} {got['asked']} "
                                f"backtest(s), {len(queue)} left to walk")
                    elif step == "cycle":
                        done = actions["cycle"]() or {}
                        state["last_cycle"] = now
                        did["cycles"] += 1
                        # A cycle is what brings an answer back, so launching
                        # is checked straight after one and nowhere else.
                        launched = (actions.get("promote")
                                    or (lambda: {}))() or {}
                        did["rooms"] += launched.get("rooms", 0)
                        did["orders"] += launched.get("orders", 0)
                        did["held"].extend(launched.get("held", [])[:3])
                        if launched.get("orders"):
                            out(f"  {now.strftime('%H:%M')} "
                                f"{launched['orders']} paper order(s) from "
                                f"{launched['rooms']} new room(s)")
                        did["answered"] = sum(
                            1 for row in _nexus_rows()
                            if row.get("type") == "answer"
                            and (_moment(row.get("at")) or started) >= started)
                    elif step == "truth":
                        ranked = actions["truth"]() or ranked
                        state["last_truth"] = now
                        did["truths"] += 1
                        state["candidates"] = _candidates(ranked, asked_about)
                    elif step == "ask":
                        slug = state["candidates"][0]
                        said = actions["ask"](
                            slug, _night_question(ranked, slug)) or {}
                        asked_about.add(slug)
                        state["candidates"] = state["candidates"][1:]
                        state["last_ask"] = now
                        state["asked"] += 1
                        did["asked"] += 1
                        did["questions"].append(
                            {"at": now.isoformat(timespec="minutes"),
                             "about": slug, "id": said.get("id")})
                        out(f"  {now.strftime('%H:%M')} asked about {slug} "
                            f"({said.get('id') or 'no id'})")
                except (Exception, SystemExit) as exc:  # one bad step is not the night
                    did["errors"].append(f"{step}: {exc}")
                    out(f"  {now.strftime('%H:%M')} {step} failed: {exc}")

            remaining = (due - clock()).total_seconds()
            if remaining <= 0:
                break
            sleep(min(lab.NIGHT["tick_seconds"], remaining))
    except KeyboardInterrupt:
        did["stopped"] = "interrupted"
        out("\n  stopped by hand; closing the session so the morning is clean")
    except (Exception, SystemExit) as exc:  # noqa: BLE001
        # A tick reads files another process writes, so a half-written line is
        # an exception rather than a keyboard. The session is closed either
        # way -- one left open makes the morning refuse to start the next
        # night -- and the traceback still reaches their terminal below.
        did["stopped"] = f"crashed: {exc}"
        crashed = exc
        out(f"\n  the night stopped on an error: {exc}")

    queue =[f"{q['id']}: worth a room if the answer is concrete ({q['about']})"
             for q in did["questions"] if q.get("id")][:lab.MAX_NEXT]
    lab.close_session(session, _lessons(did, ranked), queue, did=did)
    _archive_diaries()
    out(f"\n{session} closed after {did['ticks']} tick(s): {did['asked']} "
        f"asked, {did['answered']} answered, {did['cycles']} cycle(s). "
        f"`lab.py status` has it in the morning.")
    if crashed is not None:
        raise crashed
    return did



# --- the loop tick ---------------------------------------------------------
#
# [operator 2026-09-19] *"jak zadam /loop 20m jdi do laborky tak ty budes
# pracovat samostatne"*. The night already did the work they described --
# search nonstop, pick answers up, launch on paper from a concrete one -- as ONE
# process with an hour written into it. A tick is the same work cut into
# twenty-minute pieces by a /loop: what the night held in memory lives in
# state/lab_tick.json between them, the session is the UTC day, and the
# question is left to whoever runs the tick, because it is composed from the
# diary and a template cannot read one.

TICK = {
    "search_bite": 2 * lab.NIGHT["search_batch"],  # two minutes at their 30/min
    # An answer older than this is not launched unattended: Nexus's advice is
    # about a market that has moved on, and the six-day-old ones in the diary
    # would otherwise all be launched by the first tick.
    "answers_hours": 24,
}
TICK_STATE = "lab_tick.json"


def _tick_state_path() -> Path:
    from qa.state import state_dir

    return state_dir() / TICK_STATE


def _load_tick_state() -> dict:
    """Where the last tick stopped. Lost or unreadable, it is rebuilt: the
    walk reseeds and the register answers what was already asked, so a lost
    file costs one tick of register hits, not a repeated backtest."""
    try:
        state = json.loads(_tick_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _save_tick_state(state: dict) -> None:
    target = _tick_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)


def _day_counts(rows: list[dict], session: str, opened: dict) -> dict:
    """What a session did, counted off the diaries rather than remembered."""
    start = _moment(opened.get("at")) or _now()
    ticks = [r for r in rows if r.get("type") == "tick"
             and r.get("session") == session]
    nexus_rows = _nexus_rows()

    def since(row):
        return (_moment(row.get("at")) or start) >= start

    gates = [r for r in rows if r.get("type") == "gate" and since(r)]
    return {
        "ticks": len(ticks),
        "backtests": sum(int(t.get("backtests") or 0) for t in ticks),
        "asked": sum(1 for r in nexus_rows
                     if r.get("type") == "question" and since(r)),
        "answered": sum(1 for r in nexus_rows
                        if r.get("type") == "answer" and since(r)),
        "rooms": sum(1 for r in rooms.load()
                     if r.get("type") == "strategy" and since(r)),
        "passed": sum(1 for g in gates if g.get("verdict") == "pass"),
        "rejected": sum(1 for g in gates if g.get("verdict") == "reject"),
    }


def _close_day(rows: list[dict], session: str, opened: dict) -> dict:
    counts = _day_counts(rows, session, opened)
    lessons = [
        f"{counts['ticks']} tick(s), {counts['backtests']} backtest(s), "
        f"{counts['asked']} question(s) to Nexus ({counts['answered']} "
        f"answered), {counts['rooms']} new room(s); the gate passed "
        f"{counts['passed']} card(s) and rejected {counts['rejected']}"]
    lessons += [e["text"] for e in lab.entries(rows, session, "lesson")
                ][-(lab.MAX_LESSONS - 1):]
    nextup = [e["text"] for e in lab.entries(rows, session, "next")
              ][-lab.MAX_NEXT:]
    return lab.close_session(session, lessons, nextup, did=counts)


def _day_session(moment: datetime) -> str:
    """Today's session: the one open for this UTC day, or a new one. Any
    session left open from an EARLIER day is closed first, with what it
    counted and what was written as a lesson -- a loop has no last tick to
    close it with. A night is left alone; it closes itself at its hour."""
    rows = lab.load()
    today = moment.astimezone(timezone.utc).date().isoformat()
    opened = {str(r.get("session")): r for r in rows
              if r.get("type") == "session" and r.get("state") == "open"}
    current = None
    for session in lab.open_sessions(rows):
        row = opened.get(session, {})
        if row.get("mode") == "night":
            continue
        day = str(row.get("day") or str(row.get("at") or "")[:10])
        if day == today:
            current = current or session
            continue
        _close_day(rows, session, row)
    if current is None:
        current = lab.open_session(
            mode="loop", day=today,
            note="the laboratory's day, opened by its first tick")["session"]
    return current


def _fomo_round() -> dict:
    """One round of the memecoin watch: new hot signals, and every checkpoint
    that came due -- the one thing a skipped tick loses for good."""
    watch = _sibling("fomo_watch")
    client = watch._client()
    try:
        said = watch.tick(client)
    finally:
        client.close()
    capture, resolve = said.get("capture") or {}, said.get("resolve") or {}
    return {"added": capture.get("added", 0),
            "checked": resolve.get("checked", 0),
            "failed": len(capture.get("errors") or [])}


def _sample_round() -> dict:
    """One sampler round -- our positions and the cards our plans name --
    because `_deployed`, the verdicts and what resolved without us all read
    what it writes, and the console that used to run it is not always up."""
    sampler = _sibling("sampler")
    client = sampler._client()
    try:
        written = sampler.tick(client, every=1200.0)
    finally:
        client.close()
    last = written[-1] if written else {}
    return {"rows": max(len(written) - 1, 0), "ok": bool(last.get("ok"))}


def _record_resolved() -> list[dict]:
    from qa.rooms import load_samples

    return lab.note_resolved(
        lab.resolved_without_us(_sibling("paper").load(), load_samples()))


def _tick_doors() -> dict:
    """Every door a tick reaches. None of them asks Nexus: the question is
    composed from the diary by whoever runs the tick, through `lab.py ask`,
    which holds the day's cap and the pace."""
    return {
        "pass": pass_in_flight,
        "night": lambda: lab.night_running() is not None,
        "asked_today": _asked_today,
        "fomo": _fomo_round,
        "sample": _sample_round,
        "cycle": cycle,
        "promote": lambda: night_promote(
            since=_now() - timedelta(hours=TICK["answers_hours"])),
        "truth": functools.partial(truth, limit=8),
        "search": _night_search,
        "moves": night_moves,
        "refill": night_refill,
        "verdicts": verdicts,
    }


def _say_tick(said: dict, out) -> None:
    if not out:
        return
    at = str(said.get("at") or _now().isoformat())[11:16]
    if said.get("skipped"):
        out(f"tick {said['session']} {at}: held -- a {said['skipped']} is "
            f"running; memecoins only ({said.get('fomo')})")
        return
    fomo = said.get("fomo") or {}
    out(f"tick {said['session']} {at}: {said['backtests']} backtest(s) "
        f"({said['known']} already known), "
        f"{'answers picked up' if said['cycled'] else 'no cycle due'}, "
        f"{said['rooms']} room(s) / {said['orders']} order(s), "
        f"{said['verdicts']} verdict(s), memecoins +{fomo.get('added', 0)} "
        f"signal(s) / {fomo.get('checked', 0)} checkpoint(s)")
    for line in said.get("held") or []:
        out(f"  held:  {line}")
    if said.get("resolved"):
        out(f"  resolved without us, written down: {said['resolved']}")
    out("  question: may go now -- `lab.py brief`, then `lab.py ask --no-wait`"
        if said.get("may_ask") else f"  question: not now -- {said.get('why')}")
    for problem in said.get("errors") or []:
        out(f"  failed: {problem}")


def tick(*, now: datetime | None = None, actions: dict | None = None,
         out=print) -> dict:
    """One step of the laboratory, for a /loop: read where the last stopped,
    do what is due, write down what it did.

    Order by what EXPIRES: the memecoin checkpoints first (the price at +6h is
    gone at +7h), and they run even while a deep pass or a night holds
    everything else. Then the night's own clocks -- answers every half hour
    and a launch straight after, the ranking every six, a bite of the search
    every tick -- then the verdicts that came due and any position that
    resolved without us. It asks nothing; it says whether a question may go.
    """
    moment = now or _now()
    doors = {**_tick_doors(), **(actions or {})}
    said: dict = {"at": moment.isoformat(timespec="seconds"), "session": None,
                  "skipped": "", "fomo": None, "sample": None, "cycled": False,
                  "truth": False, "backtests": 0, "known": 0,
                  "refilled": False, "rooms": 0, "orders": 0, "held": [],
                  "verdicts": 0, "resolved": 0, "errors": []}

    def attempt(name, call, *args):
        try:
            return call(*args)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 -- one door is not the tick
            said["errors"].append(f"{name}: {exc}"[:300])
            return None

    said["session"] = _day_session(moment)
    said["fomo"] = attempt("fomo", doors["fomo"])
    if doors["pass"]():
        said["skipped"] = "pass"
    elif doors["night"]():
        said["skipped"] = "night"
    if said["skipped"]:
        said.update(may_ask=False, why=f"a {said['skipped']} is running")
        lab.note_tick(said)
        _say_tick(said, out)
        return said

    said["sample"] = attempt("sample", doors["sample"])
    state = _load_tick_state()
    queue = list(state.get("queue") or [])
    if not queue and not state.get("seeded"):
        queue = list(attempt("moves", doors["moves"]) or [])
        state["seeded"] = True
    if not queue:
        queue = list(attempt("refill", doors["refill"]) or [])
        said["refilled"] = bool(queue)

    clocks = {"last_cycle": lab._at(state.get("last_cycle")),
              "last_truth": lab._at(state.get("last_truth")),
              "pending": len(queue), "candidates": [], "asked": 0}
    for step in lab.night_tick(clocks, moment)["do"]:
        if step == "search":
            bite = TICK["search_bite"]
            chunk, queue = queue[:bite], queue[bite:]
            got = attempt("search", doors["search"], chunk) or {}
            said["backtests"] += got.get("asked", 0)
            said["known"] += got.get("known", 0)
            if not queue:
                queue = list(attempt("refill", doors["refill"]) or [])
                said["refilled"] = said["refilled"] or bool(queue)
        elif step == "cycle":
            attempt("cycle", doors["cycle"])
            state["last_cycle"] = moment.isoformat()
            said["cycled"] = True
            launched = attempt("promote", doors["promote"]) or {}
            said["rooms"] += launched.get("rooms", 0)
            said["orders"] += launched.get("orders", 0)
            said["held"] = list(launched.get("held") or [])[:6]
        elif step == "truth":
            attempt("truth", doors["truth"])
            state["last_truth"] = moment.isoformat()
            said["truth"] = True

    said["verdicts"] = len(attempt("verdicts", doors["verdicts"]) or [])
    said["resolved"] = len(attempt("resolved", _record_resolved) or [])

    may, why = lab.may_ask(int(doors["asked_today"]() or 0), False)
    if may:
        may, why = lab.may_ask_now(_nexus_rows(), moment)
    said.update(may_ask=may, why=why)
    state["queue"] = queue
    _save_tick_state(state)
    lab.note_tick(said)
    _say_tick(said, out)
    return said


def board_rows() -> list[dict]:
    """`qa.lab.board` over the diaries on this machine -- no call to them, so
    it answers while their API is down, from the sampler's newest readings."""
    from qa.rooms import load_samples

    return lab.board(_nexus_rows(), lab.load(), rooms.load(),
                     _sibling("paper").load(), load_samples())


def _board_line(row: dict) -> str:
    if row["pnl_pct"] is not None:
        money = (f"{row['pnl_pct']:+6.1f}%  {row['pnl_usdc']:+.2f} on "
                 f"{row['stake_usdc']:.0f} USDC")
    elif row["room"]:
        money = "  not priced yet"
    else:
        money = "  no room"
    room = row["room"] or "-"
    title = (row.get("title") or "")[:34]
    said = f", verdict {row['verdict']}" if row.get("verdict") else ""
    gates = "; ".join(f"{str(g['card'])[:8]} {g['verdict']}: {g.get('why')}"
                      for g in row["gates"] if g.get("verdict") != "pass")
    return (f"  {money:32} {room:9} {row['origin']:9} {title:34} "
            f"{row.get('status') or ''}{said}" + (f"\n      {gates}" if gates
                                                 else ""))


def brief() -> str:
    """Everything a question to Nexus should carry, in one read.

    Nexus remembers nothing between questions (laborator, section 7), so our
    record is his memory: what the day may still spend, how his proposals did
    -- the rejected ones with the numbers that rejected them -- what their own
    ranking says, and what measured well on our side. The last is a QUESTION
    for him and never a proposal: CLAUDE.md, who decides what to trade.
    """
    now = _now()
    nexus_rows = _nexus_rows()
    asked = lab.asked_within(nexus_rows, now)
    free, deployed = _free_cash(), _deployed()
    today = lab.rooms_within(rooms.load(), now)
    may, why = lab.may_ask(asked, pass_in_flight())
    if may:
        may, why = lab.may_ask_now(nexus_rows, now)
    out = [f"questions: {asked} of {lab.CAPS['questions_per_day']} in the last "
           f"24 h -- " + ("the next may go now" if may else f"not now: {why}")]
    if free is None:
        out.append("book: unreadable -- nothing can be launched on it")
    else:
        book = free + deployed
        out.append(f"book: {free:.0f} USDC free, {deployed:.0f} out "
                   f"({deployed / book * 100 if book else 0:.1f}% of "
                   f"{book:.0f}; the ceiling is "
                   f"{lab.CAPS['total_exposure'] * 100:.0f}%), "
                   f"{_running_experiments()} of "
                   f"{lab.CAPS['running_experiments']} experiments running, "
                   f"{today} of {lab.CAPS['new_rooms_per_day']} new rooms today")

    rows = board_rows()
    out.append("")
    out.append("his proposals, best earner first (what to tell him):")
    for row in rows[:12]:
        out.append(_board_line(row))
    if not rows:
        out.append("  none has come to anything yet")

    last = lab.last_truth()
    if last and last.get("ranked"):
        out.append("")
        out.append(f"their own ranking, {str(last.get('at'))[:16]} (read the "
                   f"window before comparing):")
        for row in last["ranked"][:5]:
            out.append(f"  {str(row.get('strategy')):24} sharpe "
                       f"{row.get('sharpe')}  over {row.get('over')}")

    best = qa_backtests.best(qa_backtests.load())[:5]
    out.append("")
    out.append("what measured well on OUR side -- a question for him, never a "
               "proposal:")
    for row in best:
        legs = " + ".join(f"{s} {w * 100:.0f}%" for s, w in row["legs"])
        out.append(f"  sharpe {row['s']}  ret {row['r']}%  over {row['p']} "
                   f"d  {legs[:60]}")
    if not best:
        out.append("  nothing in the register yet")
    return "\n".join(out)


def cmd_resume() -> int:
    """Everything a loop tick needs, in one call, so the prompt never has to
    name a session or a task.

    [operator 2026-09-13] the command they type is always the same; the tick
    works out for itself where it stopped. `status` already says where we are;
    what it does not say is what has gone RIPE since, which is the half a tick
    acts on.
    """
    from qa.state import state_dir

    print(status())
    notebook = lab.load()
    last = lab.last_tick(notebook)
    if last:
        print(f"last tick {str(last.get('at'))[:16].replace('T', ' ')} "
              f"({last.get('session')}): {last.get('backtests', 0)} "
              f"backtest(s), {last.get('rooms', 0)} room(s), "
              f"{last.get('verdicts', 0)} verdict(s); question "
              + ("may go" if last.get("may_ask") else
                 f"held -- {last.get('why')}"))
    today = [s for s in lab.open_sessions(notebook)]
    for entry in lab.entries(notebook, today[-1] if today else None)[-6:]:
        print(f"  diary [{entry.get('kind')}] {entry.get('text')}")
    print()

    fomo_rows = []
    try:
        fomo_path = state_dir() / "fomo_signals.jsonl"
        if fomo_path.exists():
            fomo_rows = [json.loads(line) for line in
                         fomo_path.read_text(encoding="utf-8").splitlines()
                         if line.strip()]
    except (OSError, ValueError) as exc:
        # Rule 8 in miniature: say the diary could not be read rather than
        # letting a tick treat it as a diary with nothing in it.
        print(f"  WARNING: the fomo diary could not be read ({exc}); "
              f"treating its checkpoints as UNKNOWN, not as none")

    tournament = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "movers_for_resume", REPO_ROOT / "scripts" / "movers.py")
        movers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(movers)
        from qa.safety import CURRENT_TIER, SafetyTier
        client = movers._client()
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            tournament = movers.round_state(client)
        finally:
            CURRENT_TIER.reset(token)
            client.close()
    except Exception as exc:  # noqa: BLE001 -- one dead read is not the tick
        print(f"  WARNING: the tournament could not be read ({exc})")

    try:
        register = len(qa_backtests.load())
    except Exception:  # noqa: BLE001
        register = None
    print(f"backtest register: {register} reading(s)")

    print()
    print("reach for, most perishable first:")
    for item in lab.due(fomo_rows=fomo_rows, tournament=tournament):
        print(f"  {item['run']}")
        print(f"      {item['why']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="where we are, and what is due")
    sub.add_parser("resume", help="one call: where we stopped and what to reach for first -- what a loop tick reads")
    truth_cmd = sub.add_parser("truth", help="their backtests, ranked")
    truth_cmd.add_argument("--limit", type=int, default=12)
    sub.add_parser("cycle", help="finish what is in flight, sample, compare")
    bt = sub.add_parser("backtest", help="their backtest for one basket, once")
    bt.add_argument("--card", help="seed from a card the sampler has seen")
    bt.add_argument("--legs", help="SYMBOL:WEIGHT,SYMBOL:WEIGHT (2-20)")
    bt.add_argument("--period", type=int, default=30,
                    choices=qa_backtests.PERIODS)
    bt.add_argument("--fees", action="store_true",
                    help="their round-trip estimate: 2%% fee + 0.5%% slippage")
    bt.add_argument("--why", default="", help="what this reading is for")
    sub.add_parser("seeds", help="their cards, as the sampler recorded them")
    sub.add_parser("grade", help="did our own ranking predict the verdicts?")
    walk = sub.add_parser("search", help="walk around their baskets, once each")
    walk.add_argument("--cap", type=int, default=12,
                      help="questions per seed; the space is combinatorial")
    walk.add_argument("--card", help="one card only, by the start of its id")
    walk.add_argument("--top", type=int, default=8,
                      help="how many of the best readings to print at the end")
    adopt_cmd = sub.add_parser("adopt", help="take over a room already running")
    adopt_cmd.add_argument("room")
    adopt_cmd.add_argument("--window-days", type=float, default=7.0)
    adopt_cmd.add_argument("--stop-pct", type=float, default=5.0)
    adopt_cmd.add_argument("--no-benchmark", action="store_true")
    sub.add_parser("verdicts", help="close every window that has come due")
    sub.add_parser("surface", help="their catalogue against the baseline")
    ask_cmd = sub.add_parser("ask", help="one question to Nexus, with brakes")
    ask_cmd.add_argument("question")
    ask_cmd.add_argument("--no-wait", action="store_true")
    buy_cmd = sub.add_parser("buy", help="one paper order, with brakes")
    buy_cmd.add_argument("--card", required=True)
    buy_cmd.add_argument("--usdc", type=float, required=True)
    buy_cmd.add_argument("--nexus", help="the answer it acts on, NEX-NNNN")
    buy_cmd.add_argument("--confirm", action="store_true")
    sub.add_parser("tick", help="one step of the laboratory -- what a /loop runs")
    sub.add_parser("brief", help="what the next question to Nexus should carry")
    board_cmd = sub.add_parser(
        "board", help="his proposals and what each earned, best first")
    board_cmd.add_argument("--top", type=int, default=20)
    log_cmd = sub.add_parser(
        "log", help="one line of today's diary: done, learned (--lesson) or "
                    "to pick up (--next)")
    log_cmd.add_argument("text")
    kind = log_cmd.add_mutually_exclusive_group()
    kind.add_argument("--lesson", action="store_const", const="lesson",
                      dest="kind")
    kind.add_argument("--next", action="store_const", const="next", dest="kind")
    night_cmd = sub.add_parser(
        "night", help="research until an hour you name, then stop")
    night_cmd.add_argument("--until", required=True, metavar="HH:MM",
                           help="on YOUR clock, not UTC; at most 14 h away")
    open_cmd = sub.add_parser("open", help="start a session")
    open_cmd.add_argument("--mode", default="session",
                          choices=["session", "night"])
    close_cmd = sub.add_parser("close", help="end it, with what it learned")
    close_cmd.add_argument("--lesson", action="append", default=[])
    close_cmd.add_argument("--next", action="append", default=[], dest="nextup")
    args = parser.parse_args(argv)

    printable()

    if args.cmd == "resume":
        return cmd_resume()
    if args.cmd == "status":
        print(status())
    elif args.cmd == "truth":
        ranked = truth(limit=args.limit)
        for row in ranked:
            gap = row.get("disagrees_by")
            print(f"  {str(row.get('strategy', '?')):28} "
                  f"sharpe {row.get('sharpe', '-'):>6} "
                  f"ret {row.get('total_return', '-'):>7} "
                  f"dd {row.get('max_drawdown', '-'):>6}  "
                  f"over {str(row.get('over', '?')):16}"
                  + (f"  THEIR TOOL SAYS SHARPE "
                     f"{row['cross_check'].get('sharpe')} (off by {gap})"
                     if gap else "")
                  + (f"   {row['unranked']}" if row.get("unranked") else ""))
        windows = {str(r.get("over")) for r in ranked if r.get("over")}
        if len(windows) > 1:
            print(f"\n  NOT ONE SCALE: these rows are measured over "
                  f"{', '.join(sorted(windows))}. A Sharpe over 24 hours and a "
                  f"Sharpe over six months are not the same number, and this "
                  f"table sorts them together -- read the column.")
    elif args.cmd == "cycle":
        print(json.dumps(cycle(), ensure_ascii=False, indent=1, default=str))
    elif args.cmd == "grade":
        pairs = graded_pairs()
        said = qa_backtests.grade(pairs)
        print(f"  {said['verdict']}: {said['why']}")
        for pair in pairs:
            print(f"    {pair['room']}  ranked sharpe {pair['sharpe']:.2f}  "
                  f"-> {pair['verdict']}")
        # How Nexus's own proposals did is the other half of the same question,
        # and the rooms already carry it: every one of them opened from an
        # answer of his.
        room_rows = rooms.load()
        tally: dict[str, int] = {}
        for strategy in rooms.strategies(room_rows):
            said_room = rooms.verdict_of(room_rows, strategy["id"])
            key = (said_room or {}).get("verdict") or "still open"
            tally[key] = tally.get(key, 0) + 1
        print("  his proposals so far: "
              + ", ".join(f"{n} {k}" for k, n in sorted(tally.items())))
    elif args.cmd == "seeds":
        for seed in card_baskets():
            legs = " + ".join(f"{leg['symbol']} {leg['weight'] * 100:.1f}%"
                              for leg in seed["legs"])
            print(f"  {seed['card'][:8]}  {seed['title'][:52]:54} {legs}")
    elif args.cmd == "search":
        seeds = card_baskets()
        if args.card:
            seeds = [s for s in seeds if s["card"].startswith(args.card)]
            if not seeds:
                raise SystemExit(f"no card starting {args.card}; `lab.py seeds`")
        # Their cards AND the climb from what has already scored. Without the
        # second half this command goes permanently quiet after one pass --
        # every later sweep asks only what the register already holds.
        queue = search_queue(seeds, cap=args.cap)
        did = search_moves(queue, out=print)
        print(f"\n{len(seeds)} card seed(s), {len(queue)} basket(s) walked: "
              f"{did['asked']} asked, {did['from_register']} already known, "
              f"{did['failed']} failed")
        ranked = qa_backtests.best(qa_backtests.load())[:args.top]
        if ranked:
            print("\nbest readings held, risk-adjusted:")
        for row in ranked:
            legs = " + ".join(f"{s} {w * 100:.0f}%" for s, w in row["legs"])
            print(f"  sharpe {row['s']:>7}  ret {row['r']:>8}%  "
                  f"dd {row['d']:>7}%  {row['p']:>3} d  {legs[:46]:48} "
                  f"{(row.get('why') or '')[:34]}")
    elif args.cmd == "backtest":
        if args.card:
            seed = next((s for s in card_baskets()
                         if s["card"].startswith(args.card)), None)
            if seed is None:
                raise SystemExit(f"no card starting {args.card}; `lab.py seeds`")
            legs, why = seed["legs"], args.why or f"card {seed['title'][:60]}"
        elif args.legs:
            legs = []
            for part in args.legs.split(","):
                symbol, _, weight = part.partition(":")
                legs.append({"symbol": symbol.strip(),
                             "weight": float(weight or 1)})
            why = args.why
        else:
            raise SystemExit("--card or --legs")
        try:
            said = backtest(legs, args.period, why=why)
        except qa_backtests.BacktestError as exc:
            raise SystemExit(str(exc))
        where = "from the register" if said["cached"] else "asked just now"
        print(f"  {said['fp']}  over {said['p']} d, {where}")
        print(f"    return {said['r']}%  sharpe {said['s']}  "
              f"drawdown {said['d']}%  points {said['pts']}")
        if said.get("lost"):
            print(f"    they could not price: {', '.join(said['lost'])} -- "
                  f"this is a different basket from the one asked for")
    elif args.cmd == "adopt":
        record = adopt(args.room, window_days=args.window_days,
                       stop_pct=args.stop_pct,
                       benchmark=None if args.no_benchmark else BTC_PROXY)
        print(f"{args.room}: criterion written, window {record['window_days']} "
              f"day(s), stop {record['stop_pct']}%, benchmark "
              f"{record.get('benchmark_card') or 'none'}")
    elif args.cmd == "verdicts":
        said = verdicts()
        if not said:
            print("no window has come due")
        for row in said:
            print(f"  {row['room']}: {row['verdict']} -- {row.get('why', '')}")
    elif args.cmd == "surface":
        print(json.dumps(surface(), ensure_ascii=False, indent=1))
    elif args.cmd == "ask":
        print(json.dumps(ask(args.question, wait=not args.no_wait),
                         ensure_ascii=False, indent=1, default=str)[:2000])
    elif args.cmd == "buy":
        print(json.dumps(buy(args.card, args.usdc, args.nexus, args.confirm),
                         ensure_ascii=False, indent=1, default=str)[:2000])
    elif args.cmd == "tick":
        tick()
    elif args.cmd == "brief":
        print(brief())
    elif args.cmd == "board":
        rows = board_rows()
        for row in rows[:args.top]:
            print(_board_line(row))
        if not rows:
            print("no proposal of his has come to anything yet")
    elif args.cmd == "log":
        session = _day_session(_now())
        record = lab.note_entry(session, args.text, kind=args.kind or "log")
        print(f"{session}: {record['kind']} written")
    elif args.cmd == "night":
        # The caps are a rolling day's since 2026-09-19, so an open session no
        # longer carries counters a night could inherit -- and the loop's day
        # session is open all day by design. Two nights at once still walk
        # one queue twice.
        running = lab.night_running()
        if running:
            raise SystemExit(f"{running[0]} is a night running until "
                             f"{running[1]}; one at a time")
        try:
            night(args.until)
        except lab.LabError as exc:  # a bad hour is a typo, not a traceback
            raise SystemExit(str(exc))
    elif args.cmd == "open":
        record = lab.open_session(mode=args.mode)
        print(f"{record['session']} open ({record['mode']})")
    elif args.cmd == "close":
        session = _session_now()
        if session is None:
            raise SystemExit("no session is open")
        record = lab.close_session(session, args.lesson, args.nextup)
        archived = _archive_diaries()
        print(f"{record['session']} closed: {len(args.lesson)} lesson(s), "
              f"{len(args.nextup)} next, {len(archived)} diary file(s) archived")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
