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
import os
import sys
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
    """Both lanes -- deep (nexus.jsonl) and the sync door (nexus_shallow.jsonl)
    -- because the laboratory acts on an answer whichever door it came
    through. The checks behind #85 and #86 read the deep diary alone."""
    nexus = _sibling("nexus")
    return nexus.load_all() if hasattr(nexus, "load_all") else nexus.load()


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
    # clone.py reads the same account after every transfer into a paper bot
    # (2026-09-22). Its read wins only when it is provably the later one.
    afters = [row for row in _sibling("clone").load()
              if row.get("type") == "after" and _moment(row.get("at")) is not None]
    mine = _moment((newest or {}).get("at")) if isinstance(newest, dict) else None
    if afters:
        # The newest transfer's read of the account failed: what is free
        # after it is unknown, and the balance from before it counts money
        # `_deployed` already counts as sent (RL08, deep pass of 2026-09-24).
        last = max(afters, key=lambda row: _moment(row["at"]))
        if last.get("sim_balance_usdc") is None and (
                mine is None or _moment(last["at"]) > mine):
            return None
    cloned = [row for row in afters if row.get("sim_balance_usdc") is not None]
    if cloned:
        later = max(cloned, key=lambda row: _moment(row["at"]))
        mine = _moment((newest or {}).get("at")) if isinstance(newest, dict) else None
        if newest is None or (mine is not None and _moment(later["at"]) > mine):
            newest = later
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
    # Their simulation can be RESTARTED, and a restart is not a close: the
    # positions are gone rather than closed, so no close of ours and no
    # `closed` row from the sampler will ever release them. On 2026-09-10 the
    # start time moved to 13:31:55 and their own total_trades read 4 against
    # our 6. Read from the snapshots we already take on both sides of every
    # order; an unreadable or absent value releases nothing.
    started = max((moment for moment in
                   (_moment(row.get("sim_started_at")) for row in rows)
                   if moment is not None), default=None)
    out: dict[str, float] = {}
    for row in rows:
        if row.get("type") != "outcome" or row.get("outcome") != "accepted":
            continue
        intent = intents.get(row.get("id"), {})
        when = _moment(row.get("at")) or _moment(intent.get("at"))
        if started is not None and when is not None and when < started:
            continue
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
    # A buy written `unknown` (timeout, 5xx) whose position the sampler reads
    # landed all the same, and its money is out (paper.landed).
    try:
        from qa.rooms import load_samples

        seen: dict[str, dict] = {}
        for sample in sorted((r for r in load_samples() if isinstance(r, dict)
                              and r.get("kind") == "position"),
                             key=lambda r: str(r.get("at") or "")):
            seen[str(sample.get("position_id"))] = sample
    except Exception:  # noqa: BLE001 -- unreadable adds nothing; accepted ones stay
        seen = {}
    for order, position in _sibling("paper").landed(rows, list(seen.values())).items():
        intent = intents.get(order, {})
        when = _moment(intent.get("at"))
        usdc = _amount(intent.get("usdc"))
        if usdc is not None and not (started and when and when < started):
            out[str(position.get("position_id"))] = usdc
    for position in _closed_on_their_side():
        out.pop(position, None)
    return sum(out.values()) + _in_clones()


def _clone_money() -> tuple[float, float]:
    """Practice money moved into our paper clones -- every ACCEPTED transfer
    in clones.jsonl (2026-09-22) -- split into what trades and what is
    PARKED in a clone that does not.

    From records on this machine, like the rest of `_deployed`, so the
    ceiling does not depend on their API answering. The money stays in a
    clone when the bot stops, so nothing here releases it to free cash. But
    a clone we paused (our newest accepted switch is `disable`), or one that
    stopped by itself (the sampler's newest reading, taken after our last
    switch, says `is_trading: false`), exposes nothing: the plan's V2 found
    1 960 USDC sitting in paused bots and counted against the 60% ceiling as
    if it traded. A refused transfer never moved anything.
    """
    rows = _sibling("clone").load()
    went_in = lab.funded(rows)
    outcomes = {row.get("id"): row for row in rows if row.get("type") == "outcome"}
    switched: dict[str, tuple[str, str]] = {}
    for row in rows:
        done = outcomes.get(row.get("id")) or {}
        if (row.get("type") == "intent" and row.get("kind") in ("enable", "disable")
                and done.get("outcome") == "accepted"):
            when = str(done.get("at") or row.get("at") or "")
            instance = str(row.get("instance_id"))
            if when >= switched.get(instance, ("", ""))[0]:
                switched[instance] = (when, row["kind"])
    newest: dict[str, dict] = {}
    for row in rooms.load_samples():
        if row.get("kind") == "bot":
            key = str(row.get("instance_id"))
            if str(row.get("at") or "") >= str(newest.get(key, {}).get("at") or ""):
                newest[key] = row
    # A clone we RELEASED is deleted on their side and nothing came back (refunded 0.0,
    # the practice balance unchanged), so its money is neither free, nor parked, nor
    # exposed: counted as parked it put 3 392 USDC of nothing into the book behind the
    # 60% ceiling and the 0.48% stake (deep pass 2026-10-02, R03).
    released = lab.released(rows)
    active = parked = 0.0
    for instance, amount in went_in.items():
        if instance in released:
            continue
        when, kind = switched.get(instance, ("", None))
        reading = newest.get(instance) or {}
        stopped = (kind == "disable"
                   or (reading.get("is_trading") is False
                       and str(reading.get("at") or "") >= when))
        if stopped:
            parked += amount
        else:
            active += amount
    return active, parked


def _in_clones() -> float:
    """What trades in our paper clones -- the exposed half of `_clone_money`."""
    return _clone_money()[0]


def _parked() -> float:
    """What sits in clones that do not trade: out of free cash, in the book,
    and against no ceiling."""
    return _clone_money()[1]


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

    Not while a deep pass runs (RL03, deep pass of 2026-09-24): audits/lab/
    is tracked, the first tick after midnight UTC closes the day BEFORE the
    tick's own pass guard, and a tree dirtied mid-pass is one the pass's
    preregistration refuses. The pass's step 8 snapshots them itself.
    """
    if pass_in_flight():
        print("[lab] a deep pass is running; its step 8 archives the diaries")
        return []
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
                   starting_capital: float = 1000.0,
                   cite: str | None = None) -> dict:
    """One call to their tool, at SAFE, at their own pace.

    A search makes thousands of these and the store keeps one witness per tool
    whatever we do, so capturing them all would cost a gigabyte to keep one
    file -- hence `cite`, which is off by default and passed only where the
    bytes may one day be cited: the gate that stands between a card and a
    room.

    Until 2026-09-20 this said the promoted case was "re-run through
    `backtest_cited` instead". No such function has ever existed, so nothing
    captured this tool at all: `backtest_event_card_idea` is the one call the
    surface watch has no baseline for, and the whole search rests on it.
    """
    import time as _time

    wait = qa_backtests.next_slot(_PACE, _time.monotonic())
    if wait:
        _time.sleep(wait)
    _PACE.append(_time.monotonic())
    del _PACE[:-qa_backtests.PER_MINUTE]

    nexus, mcp, token = _reader()
    arguments = {
        "constituents": [{"symbol": leg["symbol"], "weight": leg["weight"]}
                         for leg in constituents],
        "period_days": int(period_days),
        "include_fees": bool(include_fees),
        "starting_capital": float(starting_capital)}
    try:
        if cite is None:
            return nexus._inner(mcp.call(BACKTEST_TOOL, arguments)) or {}
        response = mcp.rpc("tools/call",
                           {"name": BACKTEST_TOOL, "arguments": arguments})
        try:
            from qa.evidence import EvidenceStore
            from qa.safety import SafetyTier

            EvidenceStore("script-lab").capture(
                response.request, response, SafetyTier.SAFE, cite)
        except Exception:  # noqa: BLE001 -- a capture we could not write is
            pass             # not a read we did not make
        return nexus._inner(type(mcp).unwrap(response.json())) or {}
    finally:
        _done(mcp, token)


def backtest(constituents, period_days: int = 30, *, why: str = "",
             include_fees: bool = False, call=None, now=None,
             cite: str | None = None) -> dict:
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
                                      include_fees=include_fees,
                                      cite=cite) or {}
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

    # The one limit on how many run is the book's 60% (V5, 2026-09-23): each
    # room takes a fixed share of it, and there is no count cap of ours.
    free, deployed, parked = _free_cash(), _deployed(), _parked()
    book = (free or 0.0) + deployed + parked
    limit = lab.CAPS["total_exposure"] * 100
    out.append(f"{_running_experiments()} experiment(s) running; the only limit "
               f"is {limit:.0f}% of the book"
               + (f", {deployed / book * 100:.1f}% out of {book:.0f}"
                  if free is not None and book else ", the book unreadable"))
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
    # Once a tick has written one down it is in the board's money, and
    # printing it on every status forever was the defect the writer closed.
    recorded = {str(r.get("position_id")) for r in rows
                if r.get("type") == "resolved"}
    for row in resolved:
        if str(row["position_id"]) in recorded:
            continue
        out.append(f"RESOLVED WITHOUT US: {row['position_id']} "
                   f"({row['card_id']}), {row['realized_pnl_usdc']} USDC, "
                   f"{str(row['resolved_at'])[:16].replace('T', ' ')}")
    written = sum(1 for row in resolved if str(row["position_id"]) in recorded)
    if written:
        out.append(f"resolved without us and written down: {written} "
                   f"(`lab.py board` counts them)")
    return "\n".join(out)


def cycle() -> dict:
    """Finish what is in flight, take a sample, and compare their catalogue."""
    did: dict[str, object] = {}
    nexus = _sibling("nexus")

    waiting = lab.outstanding(_nexus_rows())
    finished = []
    for question_id in waiting:
        try:
            # ONE look per cycle. Since REPLY-0019 a deep job at capacity
            # queues for as long as their window stays hot, and `answer`
            # waited fifteen minutes on each -- past the ten a tick may take.
            result = nexus.poll_once(question_id)
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


class Unread(Exception):
    """A read that did not answer -- not an empty answer (rule 8).

    C1 of the 2026-09-23 review: `_history` returned `[]` for any status but
    200, so a failed benchmark read looked like a benchmark with no marks, the
    verdict judged a room on its return alone, and a room that lost to BTC was
    written down as survived, once and for good. Whatever needs this read
    waits for the next call instead."""


def _body(response, what: str) -> dict:
    """A 200's JSON object, or Unread. A 404 is an answer -- they do not know
    it -- and comes back as an empty object; any other status is not."""
    if response.status_code == 404:
        return {}
    if response.status_code != 200:
        raise Unread(f"{what} answered HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise Unread(f"{what} answered HTTP 200 with a body that is not JSON"
                     ) from exc
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise Unread(f"{what} answered a {type(body).__name__}, not an object")
    return body


def _history(client, card: str) -> list[dict]:
    """A card's index history, `[]` when they have none, Unread when the read
    failed."""
    # Without `interval` they answer the last five days, and a verdict is read
    # after its window closed: STR-0005 lost two days of its seven that way.
    response = client.get(INDEX_HISTORY.format(card=card),
                          params={"interval": "all"})
    body = _body(response, f"index-history of {card[:8]}")
    return body.get("points") or body.get("history") or []


def _closes_at(client, card: str) -> str | None:
    """When the card stops trading, from the card itself. After it their index
    stops, so a verdict judges the card up to here (`qa.lab.verdict`). None
    when the card names no close; Unread when the read failed -- judging a
    card that closed on day two over the whole window would come back
    inconclusive, for good."""
    response = client.get(f"/api/v1/event-cards/{card}")
    return _body(response, f"card {card[:8]}").get("trading_closes_at")


def _basket_returns(points: list[tuple], since) -> dict[str, float]:
    """% change of one card's index per UTC day, from `since` on, keyed by
    the day. `points` is already `_at`/float pairs, sorted, from
    `qa.lab._points`.

    Keyed by the DAY, not listed: C4 of the 2026-09-23 review paired two
    rooms' returns by their position in the list, so five days of one card
    were set beside three of another from the wrong day on. A day with no
    point is a day the index did not move -- they record it when it moves --
    so the last value carries forward."""
    closes: dict = {}
    for t, v in points:
        closes[t.date()] = v            # sorted, so the day's last one wins
    if not closes:
        return {}
    day, last, value = min(closes), max(closes), None
    out: dict[str, float] = {}
    while day <= last:
        prior, value = value, closes.get(day, value)
        if prior and day >= since.date():
            out[day.isoformat()] = (value / prior - 1.0) * 100.0
        day += timedelta(days=1)
    return out


def open_book_returns(now=None, history=None, window_days: float = 14.0
                      ) -> dict[str, dict[str, float]]:
    """One return series per RUNNING room, by UTC day, weighted across its
    legs over the days every leg has.

    `history` is `(card) -> list[dict]`, injectable so this needs no network
    to test; the real caller (`book_correlation`) binds it to a live client
    the same way `verdicts()` does. Each room's legs are combined into one
    basket return series -- share-weighted, side-flipped for a bear leg -- so
    two rooms betting the same basket through different legs still read as
    correlated, which is the point of `qa.lab.n_eff`.
    """
    since = (now or _now()) - timedelta(days=window_days)
    rows = rooms.load()
    out: dict[str, dict[str, float]] = {}
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
            try:
                points = lab._points(history(card) if history else [])
            except Unread:
                # A leg we could not read is not a flat leg: the room is left
                # out of the correlation rather than read as a smaller basket.
                per_leg = []
                break
            returns = _basket_returns(points, since)
            if not returns:
                continue
            way = -1.0 if str(leg.get("side")).lower() == "bear" else 1.0
            share = float(leg.get("share") or 1.0)
            per_leg.append((share, {d: way * r for d, r in returns.items()}))
        if not per_leg:
            continue
        days = sorted(set.intersection(*(set(r) for _, r in per_leg)))
        if not days:
            continue
        total_share = sum(share for share, _ in per_leg) or 1.0
        out[room] = {d: sum(share * r[d] for share, r in per_leg) / total_share
                     for d in days}
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


# How often a RUNNING room's index is read for an early verdict. Every tick at
# ten minutes would be a history read per room per tick, up to 125 of them.
EARLY_CHECK_MINUTES = 60


def _early_state_path() -> Path:
    from qa.state import state_dir

    return state_dir() / "lab_early.json"


def _position_book(paper_rows: list[dict], origin: str, card: str,
                   samples: list[dict]) -> dict | None:
    """Our first accepted buy of `card` for `origin`, and what became of it:
    when it filled, at what index (`entry_index`, from the buy's own
    response), and -- once we sold it, or their record shows it closed --
    when, and what it was worth then, per 100 of what went in. None when we
    never held it; the verdict then reads their index alone."""
    intents = {r.get("id"): r for r in paper_rows if r.get("type") == "intent"}
    buy = None
    for row in paper_rows:
        intent = intents.get(row.get("id")) or {}
        if (row.get("type") != "outcome" or row.get("outcome") != "accepted"
                or "close" in (row.get("kind"), intent.get("kind"))
                or not row.get("position_id")):
            continue
        nexus = intent.get("nexus")
        said = nexus.get("id") if isinstance(nexus, dict) else nexus
        if said == origin and str(intent.get("card_id") or "").lower() == \
                str(card).lower():
            buy = (intent, row)
            break
    if buy is None:
        return None
    intent, row = buy
    position, notional = str(row["position_id"]), _amount(intent.get("usdc"))
    try:
        response = json.loads(row.get("response") or "{}")
    except (TypeError, ValueError):
        response = {}
    out = {"position": position, "filled_at": row.get("at") or intent.get("at"),
           "entry_index": (response.get("entry_index")
                           if isinstance(response, dict) else None),
           "closed_at": None, "closed_value": None}
    realized, closed_at = None, None
    for close in paper_rows:
        ask = intents.get(close.get("id")) or {}
        if (close.get("type") == "outcome" and close.get("outcome") == "accepted"
                and "close" in (close.get("kind"), ask.get("kind"))
                and str(ask.get("position_id") or close.get("position_id"))
                == position):
            realized = _amount(close.get("realized_pnl_usdc"))
            closed_at = close.get("at") or ask.get("at")
            break
    if closed_at is None:
        newest = None
        for sample in samples or ():
            if (sample.get("kind") == "position"
                    and str(sample.get("position_id")) == position
                    and (newest is None
                         or str(sample.get("at")) >= str(newest.get("at")))):
                newest = sample
        if newest and newest.get("status") == "closed":
            realized = _amount(newest.get("realized_pnl_usdc"))
            closed_at = newest.get("at")
    if closed_at and realized is not None and notional:
        out["closed_at"] = closed_at
        out["closed_value"] = 100.0 * (1.0 + realized / notional)
    return out


def _room_positions(paper_rows: list[dict], origin: str, cards,
                    theirs: set[str] | frozenset = frozenset()) -> list[str]:
    """Positions our accepted buys opened for this answer's cards and that no
    close of ours has closed -- nor their own record, `theirs`: a card that
    resolved by itself (TRD-0006, 2026-09-19) is not sold again, or its sale
    fails and is owed on every call for good."""
    wanted = {str(c).lower() for c in cards}
    opened, closed = [], set()
    by_id: dict[str, dict] = {}
    for row in paper_rows:
        by_id.setdefault(row.get("id"), {})[row.get("type")] = row
    for chain in by_id.values():
        intent, outcome = chain.get("intent") or {}, chain.get("outcome") or {}
        if intent.get("kind") == "close":
            if outcome.get("outcome") == "accepted" and intent.get("position_id"):
                closed.add(intent["position_id"])
            continue
        nexus = intent.get("nexus")
        said = nexus.get("id") if isinstance(nexus, dict) else nexus
        if (said == origin and str(intent.get("card_id")).lower() in wanted
                and outcome.get("outcome") == "accepted"
                and outcome.get("position_id")):
            opened.append(outcome["position_id"])
    return [p for p in opened if p not in closed and p not in theirs]


def verdicts(now=None) -> list[dict]:
    """Every room whose window has closed and has no verdict yet -- and, once
    an hour, every running room whose own index already settled it early
    (`qa.lab._early`): past its stop, or every leg out at a net loss. Only a
    refutation settles early. Any verdict stops the room, sells the paper
    positions it holds and pauses its bots; what fails is owed to the next
    call."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    moment = _moment(now) if now is not None else _now()
    rows = rooms.load()
    try:
        checked = json.loads(_early_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        checked = {}

    books: dict[str, object] = {}

    def holding(strategy: dict, acceptance: dict) -> list[str]:
        """The room's card positions still open: ours not closed by us, nor
        closed on their side. Both diaries are read once per call, not once
        per room: every settled room is asked on every tick, and V5 lifts the
        room count. Safe within a call -- rooms hold different positions, and
        a room is either owed or due, never both."""
        if not books:
            books["paper"] = _sibling("paper").load()
            books["theirs"] = _closed_on_their_side()
        return _room_positions(
            books["paper"], str(strategy.get("origin")),
            [rooms.leg_ref(leg) for leg in acceptance.get("legs") or []
             if rooms.leg_kind(leg) == "card"],
            books["theirs"])

    # Status first (V2 of the 2026-09-23 plan). A stopped room that never held
    # anything, or held what he did not pick, is archived and never judged; a
    # stopped room that held his pick is judged now, up to its stop.
    archived = lab.archived_rooms(rows, rooms.nexus_answers(),
                                  _sibling("paper").load(),
                                  _sibling("clone").load())
    stops = {str(row.get("room")): row.get("at") for row in rows
             if row.get("type") == "status" and row.get("status") == "stopped"}

    due, owed = [], []
    for strategy in rooms.strategies(rows):
        room = strategy["id"]
        acceptance = rooms.acceptance_of(rows, room)
        if acceptance is None:
            continue
        settled = rooms.verdict_of(rows, room)
        if settled is not None or room in archived:
            # R06, deep pass of 2026-09-21: the verdict is written before the
            # close, so a close that failed has to be owed from here on -- at
            # ANY verdict since C3 (2026-09-23), not only an early one, and
            # for an archived room too. A bot still trading after any verdict
            # is owed its pause too.
            if holding(strategy, acceptance) or _bots_running(
                    acceptance, room, rows):
                owed.append((strategy, acceptance))
            continue
        status = rooms.status_of(rows, room)
        halted = stops.get(room) if status == "stopped" else None
        said = lab.verdict(acceptance, {}, moment, stopped=halted)
        if said["verdict"] != "open":
            due.append((room, acceptance, strategy, True, halted))
            continue
        if status != "running":
            continue
        last = _moment(checked.get(room))
        if last is None or moment - last >= timedelta(minutes=EARLY_CHECK_MINUTES):
            due.append((room, acceptance, strategy, False, None))

    def close_positions(strategy: dict, acceptance: dict, said: dict) -> None:
        """Close what our accepted buys opened for this room's cards, and
        pause the paper bots it runs (2026-09-22; the practice money stays
        in the clone). A fund was never bought, so there is nothing to
        close. Not while a deep pass runs -- it verifies #85-#87 over these
        very trades -- and whatever fails stays owed to the next call."""
        positions = holding(strategy, acceptance)
        bots = _bots_running(acceptance, strategy["id"])
        if not positions and not bots:
            return
        if pass_in_flight():
            said.setdefault("close_failed", []).append(
                "a deep pass is running; the close waits for the next call")
            return
        paper = _sibling("paper")
        for position in positions:
            try:
                entry = paper.close(position, True)
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                said.setdefault("close_failed", []).append(
                    f"{position}: {str(exc)[:160]}")
                continue
            # paper.close RETURNS on a /sell their side refused: it writes the
            # outcome `unknown` and raises only when the POST itself failed
            # (RL02, deep pass of 2026-09-24). What it recorded decides.
            outcome = _paper_outcome(paper, (entry or {}).get("id"))
            if outcome.get("outcome") != "accepted":
                said.setdefault("close_failed", []).append(
                    f"{position}: the sell was not accepted (HTTP "
                    f"{outcome.get('http_status', '?')})")
        for instance in bots:
            clone = _sibling("clone")
            try:
                clone.enable(instance, True, enabled=False)
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                said.setdefault("close_failed", []).append(
                    f"{instance}: {str(exc)[:160]}")
                continue
            if _clone_outcome(clone, "disable", instance) == "accepted":
                said.setdefault("paused", []).append(instance)
            else:
                said.setdefault("close_failed", []).append(
                    f"{instance}: the pause was not accepted")

    def sell_at_exits(room: str, strategy: dict, acceptance: dict, legs: list,
                      series: dict) -> list[dict]:
        """Sell each held card leg whose index, from our fill, crossed its own
        take-profit or stop (`qa.lab.leg_exit`) -- 2026-09-28: 10 of 21 card
        rooms were 5% or more up while held and gave it all back, sold only at
        a verdict. An exit is not a verdict: the room runs on and its window
        judges the leg at that exit. A sale that fails is tried again on the
        next hourly look, the crossing still being in their history."""
        held = set(holding(strategy, acceptance))
        rows_out: list[dict] = []
        for leg in legs:
            ref = rooms.leg_ref(leg)
            if (rooms.leg_kind(leg) != "card" or not ref
                    or (leg.get("tp") is None and leg.get("sl") is None)):
                continue
            book = _position_book(books["paper"], str(strategy.get("origin")),
                                  str(ref), samples)
            if book is None or book["closed_at"] or book["position"] not in held:
                continue
            crossed = lab.leg_exit(series.get(ref), book["entry_index"],
                                   book["filled_at"], leg.get("side"),
                                   leg.get("tp"), leg.get("sl"))
            if crossed is None:
                continue
            row = {"room": room, "position": book["position"], **crossed}
            rows_out.append(row)
            if pass_in_flight():
                row["close_failed"] = [
                    "a deep pass is running; the sale waits for the next call"]
                continue
            paper = _sibling("paper")
            try:
                entry = paper.close(book["position"], True)
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                row["close_failed"] = [f"{book['position']}: {str(exc)[:160]}"]
                continue
            outcome = _paper_outcome(paper, (entry or {}).get("id"))
            if outcome.get("outcome") != "accepted":
                row["close_failed"] = [
                    f"{book['position']}: the sell was not accepted (HTTP "
                    f"{outcome.get('http_status', '?')})"]
                continue
            books["paper"] = paper.load()
            level = leg.get("tp") if crossed["exit"] == "tp" else leg.get("sl")
            rooms.add_claude_note(
                room, (f"Sold {str(ref)[:8]} at his "
                       f"{'take-profit' if crossed['exit'] == 'tp' else 'stop'} "
                       f"({level:+g}%): their index was {crossed['moved']:+.2f}% "
                       f"from our fill at {crossed['at'][:16]}. The room runs "
                       f"on; its window judges the leg at that exit."))
        return rows_out

    retried = []
    for strategy, acceptance in owed:
        said = {"room": strategy["id"], "retry": True}
        close_positions(strategy, acceptance, said)
        if said.get("close_failed"):
            retried.append(said)
    if not due:
        return retried

    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    client = build_client(identity, EndpointRegistry.load(), timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    out = []
    # R08, deep pass of 2026-09-21: every room fetched the same benchmark for
    # itself -- up to 125 identical reads an hour. One read per card per call,
    # and a failed one is remembered as failed for the rest of the call (C1).
    def once(cache: dict, key: str, read):
        if key not in cache:
            try:
                cache[key] = read()
            except Unread as exc:
                cache[key] = exc
            except Exception as exc:  # noqa: BLE001 -- a transport error
                cache[key] = Unread(f"{type(exc).__name__}: {str(exc)[:120]}")
        if isinstance(cache[key], Unread):
            raise cache[key]
        return cache[key]

    histories: dict[str, object] = {}

    def history(card: str) -> list:
        return once(histories, card, lambda: _history(client, card))

    closings: dict[str, object] = {}

    def closes_at(card: str) -> str | None:
        return once(closings, card, lambda: _closes_at(client, card))
    samples: list[dict] | None = None
    funded: dict[str, float] | None = None
    entered: dict[str, str] = {}
    clone_rows: list[dict] = []
    fund_histories: dict[str, object] = {}

    def series_of(leg: dict, acceptance: dict | None = None) -> list:
        """A leg's index, by its kind: a card's from their index-history, a
        bot's and an Arena team's from the sampler's rows on this machine, a
        fund's from get_fund_history. A read that failed raises Unread and
        the verdict waits; only an ANSWER with no points is an empty series,
        which the verdict reads as a gap, never as a loss."""
        nonlocal samples, funded, entered, clone_rows
        kind, ref = rooms.leg_kind(leg), rooms.leg_ref(leg)
        if kind in ("bot", "arena") and samples is None:
            clone_rows = _sibling("clone").load()
            samples, funded = rooms.load_samples(), lab.funded(clone_rows)
            entered = lab.funded_at(clone_rows)
        if kind == "arena":
            # Never through the fall-through below: that would judge BLUE on
            # /event-cards/BLUE. The sampler's newest round that read this
            # team's book failed -> the verdict waits (rule 8), because a
            # window whose last round is missing reads as short of data.
            door = rooms.ARENA_DOOR.format(team=ref)
            tried = [r for r in samples if isinstance(r, dict)
                     and r.get("type") == "tick"
                     and door in (r.get("reads") or {})]
            if tried and tried[-1]["reads"][door] != "ok":
                raise Unread(f"the sampler's newest read of {door} was "
                             f"{tried[-1]['reads'][door]}")
            return lab.arena_series(samples, ref)
        if kind == "bot":
            # A variant (V5) runs on a RESTART of a clone that ran before:
            # measured from that restart, not from the clone's funding.
            restart = lab.bot_restart(clone_rows, ref,
                                      (acceptance or {}).get("at"), samples)
            if restart is not None:
                return lab.bot_series(samples, ref, funded.get(ref),
                                      entry_at=restart["at"],
                                      entry_profit=restart["profit"],
                                      restart=True)
            return lab.bot_series(samples, ref, funded.get(ref),
                                  entry_at=entered.get(str(ref)))
        if kind == "fund":
            return once(fund_histories, ref,
                        lambda: lab.fund_series(_fund_points(ref)))
        return history(ref)
    try:
        for room, acceptance, strategy, closed, halted in due:
            legs = acceptance.get("legs") or []
            try:
                series = {rooms.leg_ref(leg): series_of(leg, acceptance)
                          for leg in legs if rooms.leg_ref(leg)}
                if acceptance.get("benchmark_card"):
                    series[acceptance["benchmark_card"]] = history(
                        acceptance["benchmark_card"])
                closes = {rooms.leg_ref(leg): closes_at(rooms.leg_ref(leg))
                          for leg in legs
                          if rooms.leg_kind(leg) == "card" and rooms.leg_ref(leg)}
            except Unread as exc:
                # Not written, not checked: the next call reads it again. A
                # running room's hourly look just waits; a closed window's
                # verdict is said to be waiting, so the tick shows it.
                if closed:
                    out.append({"room": room, "verdict": "waiting",
                                "why": (f"{exc} -- a failed read is not an empty "
                                        f"one; judged again on the next call")})
                continue
            # Our book on every card leg we hold (the plan's V2): their index
            # rebased on our fill, and what we sold for from the sale on. The
            # index alone is the cross-check, judged beside it.
            start = _moment(acceptance.get("at"))
            until = moment
            if start is not None:
                until = min(moment, start + timedelta(
                    days=float(acceptance.get("window_days") or 0)))
                if _moment(halted) is not None:
                    until = min(until, _moment(halted))
            if not books:
                books["paper"] = _sibling("paper").load()
                books["theirs"] = _closed_on_their_side()
            if samples is None:
                clone_rows = _sibling("clone").load()
                samples, funded = rooms.load_samples(), lab.funded(clone_rows)
                entered = lab.funded_at(clone_rows)
            booked = dict(series)
            for leg in legs:
                ref = rooms.leg_ref(leg)
                if rooms.leg_kind(leg) != "card" or not ref:
                    continue
                book = _position_book(books["paper"], str(strategy.get("origin")),
                                      str(ref), samples)
                if book is not None:
                    booked[ref] = lab.book_series(
                        series.get(ref), book["entry_index"], book["filled_at"],
                        book["closed_at"], book["closed_value"],
                        until=until.isoformat())
            said = lab.verdict(acceptance, booked, moment, closes=closes,
                               stopped=halted)
            if booked != series:
                said["index_return_pct"] = lab.verdict(
                    acceptance, series, moment, closes=closes,
                    stopped=halted).get("return_pct")
            checked[room] = moment.isoformat()
            if said["verdict"] == "open":
                out.extend(sell_at_exits(room, strategy, acceptance, legs, series))
                continue
            rooms.record_verdict(room, said)
            rooms.set_status(
                room, "stopped",
                (f"verdict{' (early)' if said.get('early') else ''}: "
                 f"{said['verdict']} -- {said.get('why', '')}")[:400])
            # The money comes back under the ceiling only when the position is
            # closed; a stopped room alone frees a slot in the count, not the
            # stake. At ANY verdict, early or at the window's end (C3,
            # 2026-09-23: STR-0003's TRD-0006 rode past its verdict until the
            # card resolved by itself): the window is over either way, and a
            # position or a bot left running goes on after nobody judges it.
            close_positions(strategy, acceptance, said)
            out.append({"room": room, **said})
    finally:
        client.close()
        CURRENT_TIER.reset(token)
        try:
            _early_state_path().write_text(json.dumps(checked), encoding="utf-8")
        except OSError:
            pass
    # The closes still owed ride along whatever else came due: they were
    # returned only when nothing was due, and dropped otherwise (RL01).
    return retried + out


def _tally_verdicts(judged: list[dict]) -> dict:
    """What a tick says of verdicts(): how many rooms were JUDGED, which
    wait on a failed read, and every close that failed. A retry of an owed
    close is no verdict (RL01, deep pass of 2026-09-24): counted as one, it
    was news to decide() on every tick while the bot it could not pause kept
    trading unseen."""
    return {
        "verdicts": sum(1 for row in judged
                        if row.get("verdict") not in (None, "waiting")),
        "verdicts_waiting": [f"{row['room']}: {row.get('why', '')}"
                             for row in judged if row.get("verdict") == "waiting"],
        "exits": [f"{row['room']}: {row['position']} "
                  f"{'take-profit' if row['exit'] == 'tp' else 'stop'} "
                  f"({row['moved']:+.2f}%)" for row in judged
                  if row.get("exit") and not row.get("close_failed")],
        "close_failed": [f"{row['room']}: {line}" for row in judged
                         for line in row.get("close_failed") or []]}


def _lane(rows: list[dict], lane: str = "auto") -> tuple[str | None, str]:
    """Which lane a question may take now, or None and why not.

    [operator 2026-09-19] said yes to the fallback Cymetica advised in
    REPLY-0018: while their deep lane is at capacity, ask the sync door
    (POST /api/v1/bounty/qa-agent/ask) instead of stalling the loop. Same
    hourly limit and the same bound; only their deep lane's own wait is
    lifted for it.
    """
    moment = _now()
    if lane == "chat":
        # The NEXUS bar (ask_nexus), asked by name. Not the deep lane's
        # 3-an-hour cap: that is THEIR deep lane's own limit, and it was given
        # to this lane by reuse until the operator asked why one prompt took
        # hours (2026-09-24). get_rate_limits reads 200 a minute for our key;
        # the call is synchronous, so one is in flight at a time anyway.
        return "chat", "asked for by name"
    may, why = lab.may_ask_now(rows, moment)
    if may and lane != "shallow":
        return "deep", ""
    if lane == "deep":
        return None, why
    shallow, why_not = lab.may_ask_now(rows, moment, ignore_backoff=True)
    if not shallow:
        return None, why_not
    return "shallow", (why or "asked for by name")


def ask(question: str, wait: bool = True, lane: str = "auto") -> dict:
    if not str(question or "").strip():
        # NEX-0092: an empty string reached their deep lane and cost an ask.
        raise SystemExit("not asking: the question is empty")
    rows = _nexus_rows()
    may, why = lab.may_ask(pass_in_flight())
    if not may:
        raise SystemExit(f"not asking: {why}")
    chosen, why = _lane(rows, lane)
    if chosen == "chat":
        return _sibling("nexus").ask_chat(question)
    if chosen is None:
        raise SystemExit(f"not asking: {why}")
    if chosen == "shallow":
        print(f"[lab] deep lane: {why} -- asking through qa-agent/ask instead")
        return _sibling("nexus").ask_shallow(question)
    return _sibling("nexus").ask(question, wait=wait)


def cards_question() -> str:
    """The question that feeds one room per pick (2026-09-21; since
    2026-09-22 a pick is a card, a bot to clone on paper or a fund to mark).

    Up to five, each with the thesis it rests on -- and fewer if fewer
    are worth it: the operator, on the plan, "pořád by room měl vzniknout jen
    na základě slibné teorie nebo backtestu". It names the WHOLE ids of what we
    hold (NEX-0058 could not look up two cards we gave by eight characters)
    and why the gate refused his recent picks, since he remembers nothing.
    """
    stored = rooms.load()
    titles = rooms.names(stored)
    holding = []
    for room_id, plan in rooms.plans(stored).items():
        if rooms.status_of(stored, room_id) == "stopped":
            continue
        for leg in plan.get("legs") or []:
            kind, ref = rooms.leg_kind(leg), rooms.leg_ref(leg)
            if not ref:
                continue
            # He knows a bot by its species name, not by our clone's instance.
            holding.append(f"bot {titles.get(room_id, ref)}" if kind == "bot"
                           else f"fund {ref}" if kind == "fund" else str(ref))
    refused = [row for row in lab.load() if row.get("type") == "gate"
               and row.get("verdict") in ("reject", "unknown_card")][-5:]
    what = ("an event card (the whole card UUID, status live and tradeable_now "
            "true), a bot to clone on paper (its exact species name from "
            "/api/v1/cloned-bots/available)")
    what += (", or a fund to mark (its symbol from list_funds -- we watch a "
             "fund, we do not buy one)" if lab.FUND_ROOMS
             else ". No fund: we do not run funds, so name none")
    lines = [
        "Up to five things you would run on paper now, each on its own: "
        + what + ". When to close a card is yours to say, for each card: write "
        "\"hold N days\" (N from "
        f"{lab.HOLD_DAYS_RANGE[0]:g} to {lab.HOLD_DAYS_RANGE[1]:g}, decimals "
        "fine) and we close it at the end of that period, or earlier at its "
        "take-profit or stop, and judge it after fees. A card with no hold "
        "period in that range is not opened. That hold is for a card: a bot "
        f"you name runs on our own {NIGHT_WINDOW_DAYS:g}-day window, so give it "
        "none. For each: side where it has one, take-profit "
        "and stop in percent sized for the period you name, and one line on "
        "the thesis or the backtest it rests on. Fewer is fine if fewer are "
        "worth it -- we open a room for a card only when its own backtest "
        "after fees holds up, so a weak pick costs a slot and a question, "
        "not money.",
    ]
    if holding:
        lines.append("Already held, do not repeat: " + ", ".join(sorted(set(holding))) + ".")
    if refused:
        lines.append("Your recent picks our gate (your backtest_event_card_idea, "
                     "after fees) refused: " + "; ".join(
                         f"{str(r.get('card'))[:8]} ({r.get('origin')}) "
                         f"{str(r.get('why') or r.get('verdict'))[:90]}"
                         for r in refused) + ".")
    lines.append("Name no card, bot or fund you are not proposing: our "
                 "launcher reads every UUID, species name and fund symbol in "
                 "the answer as a pick, unless it sits under a heading that "
                 "rules it out.")
    return " ".join(lines)


def buy(card_id: str, usdc: float, nexus_id: str | None, confirm: bool) -> dict:
    if pass_in_flight():
        raise SystemExit(
            "not buying: a deep pass is running and #87 judges the newest "
            "trade. Wait for it to finish")
    ok, why = lab.affordable(usdc, _free_cash(), _running_experiments(),
                             deployed=_deployed(), parked=_parked())
    if not ok:
        raise SystemExit(f"not buying: {why}")
    print(f"[lab] {why}")
    return _sibling("paper").buy(card_id, usdc, nexus_id, confirm)


# --- the night -------------------------------------------------------------
#
# `lab.py night` itself was removed on 2026-09-21: the laboratory runs
# overnight as `/loop 20m jdi do laborky`. What it walked with stays here,
# because the tick walks with the same.


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

    The one place both callers take their moves from. The night (removed
    2026-09-21) already climbed -- it refills from the register the moment its first queue empties
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


LIVE_CARDS_PAGE = 100
LIVE_SEED_CAP = 6


def live_card_seeds(listing) -> list[dict]:
    """Their live cards as search seeds: crypto legs only, tradeable now, two
    legs at least. Pure, over the body of `GET /api/v1/event-cards`.

    A stock leg their backtest cannot price (crypto only, by its own
    description), and a card that cannot trade is not a question for now.
    """
    out = []
    for card in (listing or {}).get("cards") or []:
        if not isinstance(card, dict) or card.get("has_stock_legs") \
                or card.get("tradeable_now") is not True:
            continue
        legs = [{"symbol": str(leg["symbol"]).upper(),
                 "weight": float(leg["weight"])}
                for leg in card.get("basket") or []
                if isinstance(leg, dict) and leg.get("symbol")
                and leg.get("asset_type") == "crypto"
                and isinstance(leg.get("weight"), (int, float))
                and leg["weight"] > 0]
        if len(legs) >= qa_backtests.MIN_LEGS:
            out.append({"card": str(card.get("id")),
                        "title": str(card.get("title") or "")[:60],
                        "legs": legs[:qa_backtests.MAX_LEGS]})
    return out


def _live_card_seeds() -> list[dict]:
    """One page of their live cards, newest first. Unread is no seeds: the
    refill then climbs from our readings alone, as it always did."""
    try:
        from qa.client import build_client
        from qa.config import identities, load_dotenv
        from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

        load_dotenv()
        ids = identities()
        identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
        client = build_client(identity, EndpointRegistry.load(), timeout=60.0)
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            response = client.get("/api/v1/event-cards", params={
                "status": "live", "limit": LIVE_CARDS_PAGE})
        finally:
            CURRENT_TIER.reset(token)
        return live_card_seeds(response.json()) if response.status_code == 200 else []
    except Exception:  # noqa: BLE001 -- an unread listing is not a dry search
        return []


def night_refill(rows: list[dict] | None = None, limit: int = 8,
                 cap: int = 24, pool: list[str] | None = None,
                 live: list[dict] | None = None) -> list[dict]:
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
    # And their live cards (2026-09-22): our readings alone are deterministic,
    # so once walked the refill handed back only what the register knew --
    # "0 backtest(s), 56 already known" every tick from 21:43 on. Their cards
    # change every day. A few moves each, so one listing cannot drown the climb.
    fresh = [move for seed in (live or [])
             for move in qa_backtests.neighbourhood(
                 seed, pool or symbol_pool(list(live or []) + seeds),
                 cap=LIVE_SEED_CAP)]
    if not seeds:
        return fresh
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
                seed, pool or symbol_pool(seeds), cap=cap)] + fresh


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
# 5.0 until 2026-09-24, and never said to Nexus: his picks were judged on a
# horizon he was not told. Since 2026-10-03 the window of a CARD room is his
# ("hold N days", `lab.hold_periods`), and this number is no longer a card's.
# It stays the window of a BOT room and a variant (launch_bot, bot_variants,
# 2026-10-04 L02): cards_question tells him so ("a bot you name runs on our own
# 3-day window"). 3 days is the horizon of their own card leaderboard
# ("72h Card Performance") and of their degen card prompts.
NIGHT_WINDOW_DAYS = 3.0
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
                half: bool = False, parked: float = 0.0) -> list[float]:
    """What each card of ONE room takes, floored to the cent.

    [operator 2026-09-12] fifty at once, under a ceiling of 60% of the book --
    so a room took the book's 60/50 = 1.2%, split evenly across its cards,
    then 60/125 = 0.48% (2026-09-21). Until 2026-09-19 every CARD took 2% of
    what was free, so a three-card room took six per cent and the ceiling
    stopped the laboratory near a dozen rooms, with thirty-odd experiments
    still owed. Since V5 (2026-09-23) the share is FIXED --
    CAPS["stake_share_of_book"], the same 0.48% -- and no count derives it:
    the 60% ceiling is the only limit on how many run.

    The per-order ceiling (`_stake`, 2% of what is free) still caps each leg:
    near the end of the book, free is 40% of it and 2% of that is less than a
    one-card room's 1.2%. `half` is for a card nobody could backtest.
    """
    import math

    count = max(int(legs), 0)
    if free is None or free <= 0 or count == 0:
        return [0.0] * count
    # Parked money (clones that do not trade) is book too, and exposure not.
    book = free + max(deployed or 0.0, 0.0) + max(parked or 0.0, 0.0)
    share = lab.CAPS["stake_share_of_book"]
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


def _bot_catalogue() -> list[dict] | None:
    """Every bot they will clone -- GET /api/v1/cloned-bots/available, read
    through clone.py's own reader so the source_type each row needs comes
    from the group it arrives under. None when unread: an unread catalogue
    is not an empty one, and the answer's bots wait for the next tick."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    clone = _sibling("clone")
    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    client = build_client(identity, EndpointRegistry.load(), timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(clone.AVAILABLE)
        if response.status_code != 200:
            return None
        return clone.available_bots(response.json())
    except Exception:  # noqa: BLE001 -- unread, not empty
        return None
    finally:
        CURRENT_TIER.reset(token)
        client.close()


def _fund_tool(tool: str, arguments: dict):
    """One of their four read-only fund tools, on /mcp/v1 with no key -- the
    advisor connector's own terms, so no shadow account is needed (the
    keyed identity answers NO_SHADOW_ACCOUNT there)."""
    from qa.config import identities, load_dotenv
    from qa.client import build_mcp_client
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    load_dotenv()
    client = build_mcp_client(identities()["anon"], EndpointRegistry.load())
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        answer = client.call(tool, arguments)
    finally:
        CURRENT_TIER.reset(token)
        client.http.close()
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


def _fund_catalogue() -> list[str] | None:
    """The symbols list_funds hands out, or None when it could not be read."""
    try:
        funds = _fund_tool("list_funds", {"limit": 100}).get("funds")
    except Exception:  # noqa: BLE001 -- unread, not empty
        return None
    if not isinstance(funds, list):
        return None
    return [str(row["symbol"]) for row in funds
            if isinstance(row, dict) and row.get("symbol")]


FUND_POINTS = 400  # their maximum; the default of 80 clips the series


def _fund_points(symbol: str) -> list[dict]:
    """get_fund_history for one fund, `[{t, v}]`, the whole of what they keep
    (points=400). Raises when unread, so a failed read is never an empty
    series (rule 8)."""
    said = _fund_tool("get_fund_history", {"symbol": symbol, "points": FUND_POINTS})
    if "points" not in said:
        # A rate limit came back as an error on 2026-09-19, and bare text
        # arrives here as {}: an answer, not a history, and not an empty one.
        raise RuntimeError(str(said.get("code") or said.get("error")
                               or "no points in the answer")[:120])
    return said.get("points") or []


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
                # Gross: `qa.lab.gate` charges the live round trip itself.
                readings.append(backtest(basket, period, include_fees=False,
                                         why=f"gate {card[:8]}",
                                         cite="backtest.event_card_idea"))
            except qa_backtests.BacktestError:
                continue
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                # "could be priced (need >= 80%)" is their answer: crypto legs
                # only, by the tool's own description. Read as "unread" it was
                # retried every tick for good (NEX-0063's stock card).
                if "could be priced" in str(exc):
                    continue
                return {"verdict": "unread",
                        "why": f"their backtest did not answer ({exc})"}
    return lab.gate(readings)


def _fresh(row: dict, since: datetime | None) -> bool:
    """Whether an answer is inside the launch window. One whose time cannot
    be read is NOT: `nexus.py record --at` takes free text, and reading
    that as now launched an answer of any age (RL05, deep pass of
    2026-09-24) -- rule 8 on the side that spends."""
    if since is None:
        return True
    when = _moment(row.get("at"))
    return when is not None and when >= since


def night_promote(since: datetime | None = None, only: str | None = None) -> dict:
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
      * `affordable` decides whether there is money for it at all: 60% of
        the book is the only limit on how many run. The day's cap of 25 new
        rooms went in V5 (2026-09-23) -- it was "a ceiling, not a quota",
        and the gate above is the bar it deferred to;
      * nothing at all while a deep pass runs, because it is verifying #85,
        #86 and #87 over these very trades.

    ONE ROOM PER CARD (2026-09-21). An answer naming five cards is five
    strategies; each card that passes the gate opens its own room, plan,
    criterion and order. The operator, on the plan: a room is still only for
    a promising theory or backtest -- so the gate above is the bar, and the
    money is the only ceiling. A card that could not be READ, or cannot
    be traded right now, decides nothing and holds nothing back: it is tried
    again on the next tick, and the answer's other cards open meanwhile (NEX-
    0052's counterexample once parked its pick for 27 ticks).

    Returns what it did and, for everything it did not, why -- so the morning
    reads a reason rather than a silence.
    """
    if pass_in_flight():
        return {"rooms": 0, "orders": 0, "held": ["a deep pass is running"]}

    # `only`: one answer read again by hand (`lab.py launch NEX-...`), fresh or not and read or
    # not -- for an answer a launcher that could not act on it had already marked read (NEX-0137).
    answers = [row for row in _nexus_rows() if row.get("type") == "answer"
               and (str(row.get("id")) == only if only else _fresh(row, since))]
    if not answers:
        return {"rooms": 0, "orders": 0, "held": []}

    stored = rooms.load()
    decided = lab.gates()
    paper = _sibling("paper")
    opened, placed, held = 0, 0, []
    # Answers are read ONCE (V5, 2026-09-23): an answer whose every pick was
    # decided is marked read and skipped from then on. `pending` holds the
    # answers with something still waiting -- a card unread or not tradeable
    # yet, a gate or catalogue that did not answer, money not there yet, a
    # deep pass -- and those are read again on the next tick.
    already = lab.answers_read() - {only}
    pending: set[str] = set()

    def later(origin: str, line: str) -> None:
        held.append(line)
        pending.add(origin)
    bought: set[str] = set()
    # Cards a room not yet stopped already holds. `bought` alone lasted one
    # call, so the next tick bought a card a running room held -- two
    # experiments that are one (R09, deep pass of 2026-09-19).
    held_by: dict[str, str] = {}
    for room_id, plan in rooms.plans(stored).items():
        if rooms.status_of(stored, room_id) == "stopped":
            continue
        for leg in plan.get("legs") or []:
            if leg.get("card"):
                held_by.setdefault(str(leg["card"]).lower(), room_id)

    # A room opened from a whole answer (before 2026-09-21) spends the answer;
    # a room opened for one card spends that card of it, and its other cards
    # may still open their own.
    # A bot or fund room (2026-09-22) holds one thing of its answer, keyed by
    # `ref`, and is no more a whole-answer room than a card room is.
    whole_linked = {str(row.get("origin")) for row in stored
                    if row.get("type") == "strategy"
                    and rooms.room_key(row) is None}
    card_linked = {(str(row.get("origin")), str(row.get("card")).lower())
                   for row in stored
                   if row.get("type") == "strategy" and row.get("card")}
    ref_linked = {(str(row.get("origin")), str(row.get("ref")).lower())
                  for row in stored
                  if row.get("type") == "strategy" and row.get("ref")}
    # A species or a fund a room not yet stopped already holds, by any answer.
    live_refs: dict[tuple[str, str], str] = {}
    for row in rooms.strategies(stored):
        if row.get("ref") and rooms.status_of(stored, row["id"]) != "stopped":
            live_refs.setdefault((str(row.get("kind")), str(row["ref"]).lower()),
                                 row["id"])
    # A band he names for a bot (NEX-0137): what runs at which band, and which species the
    # operator's rule threw away -- read once, and only when an answer names a band.
    band_state: dict[str, dict] = {}

    def bands_running() -> dict[tuple[str, str], str]:
        if "running" not in band_state:
            band_state["running"] = _bands_running(stored, _sibling("clone").load())
        return band_state["running"]

    def thrown_species() -> dict[str, str]:
        if "thrown" not in band_state:
            band_state["thrown"] = _thrown_species(_sibling("clone").load(),
                                                   rooms.load_samples())
        return band_state["thrown"]
    catalogues: dict[str, list | None] = {}

    def catalogue(kind: str):
        """Their bot or fund catalogue, read once per call and only when an
        answer is actually being read."""
        if kind not in catalogues:
            try:
                catalogues[kind] = (_bot_catalogue() if kind == "bot"
                                    else _fund_catalogue())
            except Exception:  # noqa: BLE001 -- unread, not empty
                catalogues[kind] = None
        return catalogues[kind]
    capped = False

    def launch_cards(origin: str, text, named: list[str], species) -> None:
        """The answer's cards, each its own room -- as it has been since
        2026-09-21. A `return` here leaves the answer's bots and funds to
        be read after it."""
        nonlocal opened, placed, capped
        # Asked again here, not only on entry: a pass started while this call
        # walked earlier answers verifies #85-#87 over the next order.
        if pass_in_flight():
            later(origin, f"{origin}: a deep pass is running")
            capped = True
            return
        ruled_out = lab.ruled_out_cards(text)
        picked = set(lab.picked_cards(text, species))
        for card in named:
            if card in ruled_out:
                held.append(f"{origin}/{card[:8]}: he named it only to rule "
                            f"it out -- not a proposal")
            elif card not in picked:
                held.append(f"{origin}/{card[:8]}: named, but not on the line "
                            f"that declares his pick -- not a proposal")
        named = [c for c in named if c not in ruled_out and c in picked]
        if not named:
            return
        # His exits, per card, onto the leg before the criterion is written
        # (V2, 2026-09-23). Forward only: a room already open keeps its own.
        exits = lab.exit_levels(text, named)
        # And how long to hold it, from him (2026-10-03, the operator: "to musi rict
        # nexus"): a card with no hold period is not opened, whatever else he said of it.
        holds = lab.hold_periods(text, named)
        spent = ("reject", "unknown_card")
        named = [c for c in named if (origin, c) not in card_linked]
        if all(decided.get((origin, card), {}).get("verdict") in spent
               for card in named):
            return  # decided on an earlier tick, and nothing in it may run

        chosen: dict[str, dict] = {}
        for card in named:
            # Nexus repeats its favourite card across answers, and "fifty
            # experiments" meant fifty different things.
            if card in bought:
                continue
            if card == BTC_PROXY:
                # STR-0008 (NEX-0059): a room on the card every room is
                # judged against could only ever tie it.
                held.append(f"{origin}/{card[:8]}: it is the benchmark itself "
                            f"-- a room on it measures nothing against it")
                continue
            if card in held_by:
                held.append(f"{origin}/{card[:8]}: already held in "
                            f"{held_by[card]} -- not a second experiment")
                continue
            if holds.get(card) is None:
                # None is "none stated" and also "one stated outside the range he was told"
                # (qa.lab.hold_periods does not clamp it): a window he did not name is not
                # written into the criterion as his.
                held.append(f"{origin}/{card[:8]}: he named no usable hold period "
                            f"({lab.HOLD_DAYS_RANGE[0]:g} to {lab.HOLD_DAYS_RANGE[1]:g} "
                            f"days) -- when to close is his to say, so it is not "
                            f"opened; the next question demands one")
                continue
            prior = decided.get((origin, card))
            if prior and prior.get("verdict") in spent:
                continue
            try:
                live = _card_live(card)
            except Exception as exc:  # noqa: BLE001 -- unread is not absent
                later(origin, f"{origin}/{card[:8]}: the card could not be "
                              f"read ({exc}) — the next tick tries again")
                continue
            if live is None:
                # Which of the two a 404 was cannot be told from here: a card
                # Nexus invented (#91), or the id of something that is not a
                # card -- his answers carry run ids and species ids too
                # (NEX-0010, NEX-0015). R06, deep pass of 2026-09-19: this
                # used to say "invented", and the brief reads it back to him.
                said = {"verdict": "unknown_card",
                        "why": ("their API knows no card by this id: a card "
                                "Nexus invented (#91), or an id of something "
                                "that is not a card")}
                decided[(origin, card)] = lab.note_gate(origin, card, said)
                held.append(f"{origin}: {card[:8]} -- their API knows no card "
                            f"by this id (invented, #91, or not a card at "
                            f"all) -- not bought")
                continue
            if live.get("tradeable") is False:
                later(origin, f"{origin}/{card[:8]}: not tradeable now — the "
                              f"next tick tries again")
                continue
            if prior is None:
                said = _gate(card, live.get("legs") or [])
                if said["verdict"] == "unread":
                    later(origin, f"{origin}/{card[:8]}: {said['why']} — the "
                                  f"next tick tries again")
                    continue
                prior = decided[(origin, card)] = lab.note_gate(
                    origin, card, said)
            if prior["verdict"] == "reject":
                held.append(f"{origin}/{card[:8]}: their backtest rejects it — "
                            f"{prior.get('why')}")
                continue
            chosen[card] = {**prior, "title": live.get("title") or ""}
        # One room per card that passed (2026-09-21). A card that is waiting --
        # unreadable, not tradeable yet -- no longer holds the others back:
        # each is its own room now, so there are no legs to keep together, and
        # it is tried again on the next tick under the same answer.
        for card, gate_row in chosen.items():
            # MONEY FIRST, and nothing consumed before it answers: a room opened
            # ahead of a refusal spends its card for the morning too.
            free, deployed, parked = _free_cash(), _deployed(), _parked()
            untested = gate_row["verdict"] == "unbacktestable"
            stake = _leg_stakes(free, deployed, 1, half=untested,
                                parked=parked)[0]
            ok, why = lab.affordable(stake, free, _running_experiments(),
                                     deployed=deployed, parked=parked)
            if not ok or stake <= 0:
                later(origin, f"{origin}/{card[:8]}: {why or 'no stake'} — "
                              f"left for the morning")
                capped = True
                break
            name = gate_row["title"] or f"{origin}: {card[:8]}"
            try:
                room = rooms.open_strategy(origin, name[:rooms.MAX_TITLE],
                                           card=card)["id"]
                # The leg is the laboratory's READING of his answer -- bull --
                # because his answers carry no machine-readable side. The
                # criterion takes it, or `qa.lab.verdict` has nothing to score.
                levels = exits.get(card) or {}
                plan = rooms.set_plan(room, [{"card": card, "side": "bull",
                                              "share": 1.0, **levels}])
                said_levels = (f"his take-profit {levels.get('tp')} % and stop "
                               f"{levels.get('sl')} % are on the leg"
                               if levels.get("tp") or levels.get("sl")
                               else "he named no take-profit or stop")
                # A room with no criterion is one no verdict can ever reach.
                # The window is OURS, not his -- `adopted` says so; the leg's
                # exits are his when he named them. Where he named a stop, it
                # governs and ours (10% from the PEAK) is left off: a replay of
                # 22 card rooms on 2026-09-28 found ours throwing out rooms his
                # would have held into profit (STR-0010, -0013, -0025).
                his_stop = levels.get("sl") is not None
                rooms.set_acceptance(
                    room, window_days=holds[card],
                    stop_pct=None if his_stop else NIGHT_STOP_PCT,
                    legs=plan["legs"], benchmark_card=BTC_PROXY,
                    why=(f"opened unattended from {origin}, one room for this "
                         f"card; the window is his, {holds[card]:g} days -- he named "
                         f"when to close it; "
                         + ("the room stop is his leg stop, ours is off; "
                            if his_stop else
                            f"the room stop is ours, {NIGHT_STOP_PCT:g}% from "
                            f"the peak; ")
                         + f"{said_levels}. Backtest: "
                         f"{card[:8]} {gate_row.get('why')}"
                         + (" -- NOT backtested, half stake" if untested
                            else ""))[:900],
                    adopted=True)
            except rooms.RoomError as exc:
                held.append(f"{origin}/{card[:8]}: {exc}")
                continue
            opened += 1
            card_linked.add((origin, card))

            # paper.py refuses with SystemExit (its books unreadable, their
            # side refusing). Uncaught, it left the room with a criterion and
            # no position and took every later answer of the call with it
            # (R01, deep pass of 2026-09-19).
            try:
                result = paper.buy(card, stake, origin, True) or {}
                refused = None
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                result, refused = {}, str(exc)[:200]
            # An order counts only when it was ACCEPTED: TRD-0010 came back
            # HTTP 500 "Buy failed" with no position (#117), and the tick said
            # "1 order" all the same. paper.buy always names an outcome; a
            # result without one is not an accepted order either (C04, deep
            # pass of 2026-09-21: only the test stubs ever omitted it).
            if result.get("outcome") == "accepted":
                bought.add(card)
                placed += 1
                status, why_status = "running", f"opened by the laboratory from {origin}"
            else:
                reason = refused or (f"HTTP {result.get('http_status')}, no "
                                     f"position returned")
                held.append(f"{origin}/{card[:8]}: the paper order was "
                            f"{'refused' if refused else 'not accepted'} "
                            f"({reason})")
                status = "stopped"
                # A stopped room that held nothing is archived and never
                # judged (V2), so this says so rather than promising a verdict
                # (RL07, deep pass of 2026-09-24).
                code = result.get("http_status")
                # paper.buy refuses before sending (its book, the guidance)
                # or raises "did not complete" after a POST that timed out.
                sent_unknown = ("did not complete" in refused if refused
                                else not (isinstance(code, int) and 400 <= code < 500))
                if not sent_unknown:
                    why_status = (f"the paper order did not land ({reason}), so "
                                  f"nothing is at stake here; a room that held "
                                  f"nothing is archived and not judged")
                else:
                    # A timeout or a 5xx may have landed (paper.landed); the
                    # book and the ceiling count it once their positions do.
                    why_status = (f"the paper order's outcome is unknown ({reason}); "
                                  f"if it landed, the book counts it once their "
                                  f"positions list it, and this room is not judged")
            try:
                rooms.set_status(room, status, why=why_status)
            except rooms.RoomError as exc:
                held.append(f"{room}: {exc}")

    def launch_bot(origin: str, bot: dict, band: dict | None = None) -> None:
        """One bot he named, cloned on paper through clone.py -- its paper
        flag, its is_paper floors and its CLN record, none of them ours to
        repeat -- funded with half a stake (a bot has no backtest) and
        started. Its room's leg is the clone's instance; the room opens
        before the clone, as a card's does before its order, so a clone that
        fails leaves a stopped room saying why rather than a silence.

        With a `band` he named (NEX-0137), the clone is set to it before the
        money, and read back, as wave.py does; a species we already own is no
        reason to hold it -- that band is a setting nothing of ours measured."""
        nonlocal opened, capped
        name, species = str(bot.get("name")), str(bot.get("id"))
        tag = f"{origin}/{name}"
        label = lab.band_label(band) if band else None
        if (origin, species.lower()) in ref_linked:
            return
        if band is None:
            owner = live_refs.get(("bot", species.lower()))
            if owner:
                held.append(f"{tag}: already cloned in {owner} -- not a second "
                            f"experiment")
                return
            cloned = _species_cloned().get(species.lower())
            if cloned:
                held.append(f"{tag}: {cloned} -- not cloned again")
                return
        else:
            thrown = thrown_species().get(species.lower())
            if thrown:
                held.append(f"{tag} {label}: its clone {thrown[:8]} ended on three stop-losses "
                            f"in a row and was thrown away (the operator's rule, 2026-10-07); "
                            f"bringing the species back is the operator's call")
                return
            owner = bands_running().get((species.lower(), label))
            if owner:
                held.append(f"{tag}: {owner} already runs it at {label} -- not a second "
                            f"experiment")
                return
        if pass_in_flight():
            later(origin, f"{tag}: a deep pass is running")
            capped = True
            return
        free, deployed, parked = _free_cash(), _deployed(), _parked()
        stake = _leg_stakes(free, deployed, 1, half=True, parked=parked)[0]
        ok, why = lab.affordable(stake, free, _running_experiments(),
                                 deployed=deployed, parked=parked)
        if not ok or stake <= 0:
            later(origin, f"{tag}: {why or 'no stake'} — left for the morning")
            capped = True
            return
        key = f"bot:{name}"
        if (origin, key) not in decided:
            decided[(origin, key)] = lab.note_gate(origin, key, {
                "verdict": "unbacktestable",
                "why": "their backtest prices a basket of coins, not a bot"})
        try:
            title = f"{name} {label}" if label else name
            room = rooms.open_strategy(origin, title[:rooms.MAX_TITLE],
                                       kind="bot", ref=species)["id"]
        except rooms.RoomError as exc:
            held.append(f"{tag}: {exc}")
            return
        opened += 1
        ref_linked.add((origin, species.lower()))
        live_refs[("bot", species.lower())] = room
        if label:
            bands_running()[(species.lower(), label)] = room
        clone = _sibling("clone")

        def stop(why: str) -> None:
            held.append(f"{tag}: {why}")
            try:
                rooms.set_status(room, "stopped", why=why[:400])
            except rooms.RoomError as exc:
                held.append(f"{room}: {exc}")

        try:
            made = clone.clone(bot.get("source_type"), species,
                               f"lab {name}"[:60], origin, True) or {}
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            return stop(f"the paper clone was refused ({str(exc)[:160]})")
        instance = made.get("clone_instance_id")
        if made.get("outcome") != "accepted" or not instance:
            return stop(f"the paper clone was not accepted (HTTP "
                        f"{made.get('http_status')}, {made.get('outcome')}), "
                        f"so nothing runs here")
        if made.get("is_paper") is not True:
            return stop(f"they did not confirm {instance} as paper "
                        f"(is_paper={made.get('is_paper')!r}), so it is "
                        f"neither funded nor started")
        try:
            rooms.add_link(room, made["id"],
                           why=f"the paper clone of {name} this room runs")
            plan = rooms.set_plan(room, [{"kind": "bot", "ref": instance,
                                          "side": "bull", "share": 1.0}])
            rooms.set_acceptance(
                room, window_days=NIGHT_WINDOW_DAYS, stop_pct=NIGHT_STOP_PCT,
                legs=plan["legs"], benchmark_card=BTC_PROXY,
                why=(f"opened unattended from {origin}, one room for the bot "
                     f"{name}, cloned on paper as {instance}; "
                     + (f"the band is his, {label}, set on the clone before it is "
                        f"funded; the window and the room stop are the laboratory's "
                        f"defaults. " if label else
                        f"the window and the stop are the laboratory's defaults, "
                        f"not numbers Nexus gave. ")
                     + f"Judged on what it made against what went "
                     f"in -- NOT backtested, half stake")[:900],
                adopted=True)
        except (rooms.RoomError, KeyError) as exc:
            return stop(f"the room could not be written ({exc})")
        if band:
            # The settings before the money, then read back from their answer (wave.py's order
            # and its reader): a bot funded on the species' defaults would be measured under
            # his name on a band he did not give.
            try:
                changed = clone.settings(instance, dict(band), True) or {}
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                return stop(f"setting {label} on {instance} was refused "
                            f"({str(exc)[:160]}); not funded, not started")
            if changed.get("outcome") != "accepted":
                return stop(f"setting {label} on {instance} was not accepted "
                            f"({changed.get('outcome')}); not funded, not started")
            differs = _sibling("wave")._read_back(changed, band)
            if differs:
                return stop(f"{label} read back wrong on {instance} -- {differs}; "
                            f"not funded, not started")
        try:
            clone.fund(instance, stake, True)
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            return stop(f"funding {instance} was refused ({str(exc)[:160]})")
        if _clone_outcome(clone, "fund", instance) != "accepted":
            return stop(f"funding {instance} was not accepted")
        try:
            clone.enable(instance, True)
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            return stop(f"starting {instance} was refused ({str(exc)[:160]}); "
                        f"its {stake:.2f} stays in the clone")
        if _clone_outcome(clone, "enable", instance) != "accepted":
            return stop(f"starting {instance} was not accepted; its "
                        f"{stake:.2f} stays in the clone")
        try:
            rooms.set_status(room, "running", why=(
                f"cloned on paper from {origin}: {name} as {instance}"
                + (f", set to {label}" if label else "")
                + f", funded {stake:.2f} USDC (half stake, not backtested) and started"))
        except rooms.RoomError as exc:
            held.append(f"{room}: {exc}")

    def launch_fund(origin: str, symbol: str, text) -> None:
        """One fund he named, MARKED and not bought: create_aib_fund spends
        real money and has no paper switch. A room, a leg, a criterion, no
        order of any kind -- and a notional stake that no ceiling counts. It
        takes a slot among the running experiments, because it is one. A fund
        whose history is empty has nothing to be judged on and opens nothing.

        Since V5 (2026-09-23) no count holds it back: it spends nothing, so
        the book's ceiling cannot see it, and the 125-experiment cap that
        did went. One room per fund while it runs (`live_refs`) is what
        keeps one fund from being marked twice."""
        nonlocal opened
        tag = f"{origin}/{symbol}"
        if (origin, symbol.lower()) in ref_linked:
            return
        owner = live_refs.get(("fund", symbol.lower()))
        if owner:
            held.append(f"{tag}: already marked in {owner}")
            return
        key = f"fund:{symbol}"
        if decided.get((origin, key), {}).get("verdict") == "no_series":
            return
        try:
            points = lab.fund_series(_fund_points(symbol))
        except Exception as exc:  # noqa: BLE001 -- unread is not empty
            later(origin, f"{tag}: its history could not be read "
                          f"({str(exc)[:120]}) — the next tick tries again")
            return
        if not points:
            decided[(origin, key)] = lab.note_gate(origin, key, {
                "verdict": "no_series",
                "why": "get_fund_history returned no points, so there is "
                       "nothing to judge it on"})
            held.append(f"{tag}: their history of it is empty -- nothing to "
                        f"judge it on, so no room")
            return
        notional = _leg_stakes(_free_cash(), _deployed(), 1,
                               parked=_parked())[0]
        try:
            room = rooms.open_strategy(origin, symbol, kind="fund",
                                       ref=symbol)["id"]
        except rooms.RoomError as exc:
            held.append(f"{tag}: {exc}")
            return
        opened += 1
        ref_linked.add((origin, symbol.lower()))
        live_refs[("fund", symbol.lower())] = room
        levels = lab.exit_levels(text, [symbol]).get(symbol) or {}
        try:
            plan = rooms.set_plan(room, [{"kind": "fund", "ref": symbol,
                                          "side": "bull", "share": 1.0,
                                          **levels}])
            rooms.set_acceptance(
                room, window_days=NIGHT_WINDOW_DAYS, stop_pct=NIGHT_STOP_PCT,
                legs=plan["legs"], benchmark_card=BTC_PROXY,
                why=(f"opened unattended from {origin}, one room for the fund "
                     f"{symbol}: marked, not bought -- no order of any kind, "
                     f"a notional {notional:.2f} USDC counted in no ceiling. "
                     f"Judged on their get_fund_history; the window and the "
                     f"stop are the laboratory's defaults, not numbers Nexus "
                     f"gave")[:900],
                adopted=True)
            rooms.set_status(room, "running", why=(
                f"marked, not bought -- no order; a notional {notional:.2f} "
                f"USDC from {origin}, counted in no ceiling"))
        except rooms.RoomError as exc:
            held.append(f"{room}: {exc}")

    # The answers that opened a room on this call: `decide: answer NEX-...`
    # wakes the manager for them (V6), and for nothing an answer only named.
    answered: list[str] = []
    for answer in answers:
        if capped:
            break
        origin = str(answer.get("id") or "")
        if not origin or origin in whole_linked or origin in already:
            continue
        before = opened
        text = answer.get("text")
        # Every id the answer names; whether it EXISTS is asked of their API
        # below, not of what our own sampler happened to have seen.
        named = lab.proposed_cards(text, ())["unknown"]
        bots_listed = catalogue("bot")
        funds_listed = catalogue("fund")
        # A catalogue that did not answer is not one that lists nothing: the
        # answer may name a bot or a fund we could not recognise, so it is
        # read again rather than marked read.
        if bots_listed is None or funds_listed is None:
            pending.add(origin)
        species: set[str] = set()
        if bots_listed:
            # A species id is a bot's, not a card nobody can find (#91).
            species = {str(b.get("id")).lower() for b in bots_listed}
            named = [c for c in named if c not in species]
        bots = lab.proposed_bots(text, bots_listed or [])
        # Every species name, so a line naming two gives neither a band.
        bands = lab.bot_bands(text, [str(b.get("name")) for b in bots_listed or []
                                     if b.get("name")])
        # Fund rooms are off (lab.FUND_ROOMS): a fund he names is read and left alone.
        funds = (lab.proposed_funds(text, funds_listed or [])
                 if lab.FUND_ROOMS else [])
        if not (named or bots or funds):
            held.append(f"{origin}: names no card, bot or fund we can act on; "
                        f"the morning reads it")
        else:
            if named:
                launch_cards(origin, text, named, species)
            for bot in bots:
                if capped:
                    break
                launch_bot(origin, bot, bands.get(str(bot.get("name"))))
            for symbol in funds:
                if capped:
                    break
                launch_fund(origin, symbol, text)
        if opened > before:
            answered.append(origin)
        if origin not in pending:
            lab.note_answer_read(origin)
    return {"rooms": opened, "orders": placed, "held": held,
            "answered": answered}


def _bots_running(acceptance: dict, room: str | None = None,
                  stored: list[dict] | None = None) -> list[str]:
    """The criterion's bot legs that our own record says we started and have
    not paused since: the newest ACCEPTED switch of each, per clones.jsonl.

    With `room`, only the clones that room still OWNS -- none a later room
    runs on. Since V5 a clone's next setting runs in a new room on the same
    clone, so the newest switch may be the variant's start; read against the
    settled room before it, that start looked like its bot "still trading
    after its verdict" and the next tick paused the variant. Ownership, not
    time: the verdict's stop, its pause and the variant's start are stamped
    to the second and can share one."""
    wanted = [rooms.leg_ref(leg) for leg in acceptance.get("legs") or []
              if rooms.leg_kind(leg) == "bot"]
    if room is not None and wanted:
        owner: dict[str, str] = {}
        rows_ = rooms.load() if stored is None else stored
        # A room still running outranks a stopped one, whatever the numbers
        # (deep pass 2026-09-24, R03): STR-0045 was stopped holding Trend
        # Titan while STR-0044, lower, ran on it, and by number alone the
        # stopped room's close would have paused STR-0044's bot.
        def rank(held_by: str) -> tuple[int, int]:
            live = rooms.status_of(rows_, held_by) != "stopped"
            return (1 if live else 0, rooms.number(held_by))
        for row in rows_:
            if row.get("type") != "acceptance" or not row.get("room"):
                continue
            for leg in row.get("legs") or []:
                if rooms.leg_kind(leg) == "bot":
                    ref, held_by = str(rooms.leg_ref(leg)), str(row["room"])
                    if ref not in owner or rank(held_by) >= rank(owner[ref]):
                        owner[ref] = held_by
        wanted = [ref for ref in wanted if owner.get(str(ref), room) == room]
    if not wanted:
        return []
    rows = _sibling("clone").load()
    outcomes = {row.get("id"): row.get("outcome") for row in rows
                if row.get("type") == "outcome"}
    switched: dict[str, str] = {}
    for row in rows:
        # An enable that may have landed (a read timeout is `unknown`) counts as
        # running, so a verdict still pauses the bot; only a disable needs the
        # platform's yes (deep pass 2026-10-02, R02).
        said = outcomes.get(row.get("id"))
        if (row.get("type") == "intent"
                and row.get("kind") in ("enable", "disable")
                and (said == "accepted"
                     or (row.get("kind") == "enable" and said == "unknown"))):
            switched[str(row.get("instance_id"))] = row["kind"]
    return [ref for ref in wanted if switched.get(str(ref)) == "enable"]


def _funded() -> dict[str, float]:
    """What went into each clone: accepted transfers in clones.jsonl -- the
    base a bot's index is measured against (`qa.lab.bot_series`). One
    reading, `qa.lab.funded`, shared with the board."""
    return lab.funded(_sibling("clone").load())


def _instance_species(rows: list[dict]) -> dict[str, str]:
    """Our clone record's instance -> the species it is a clone of, lower case."""
    asked = {row.get("id"): str(row.get("source_id") or "").lower() for row in rows
             if row.get("type") == "intent" and not row.get("kind") and row.get("source_id")}
    return {str(row["clone_instance_id"]): asked[row.get("id")] for row in rows
            if row.get("type") == "outcome" and not row.get("kind")
            and row.get("clone_instance_id") and row.get("id") in asked}


def _bands_running(stored: list[dict], rows: list[dict]) -> dict[tuple[str, str], str]:
    """(species, "SL 12 / TP 30") -> the room not yet stopped whose bot runs at that band.

    The band is what our clone record says their side ACCEPTED on the instance, field by
    field, the newest settings change winning -- wave.py's, a variant's or a launch's alike."""
    accepted = {row.get("id") for row in rows if row.get("type") == "outcome"
                and row.get("kind") == "settings" and row.get("outcome") == "accepted"}
    held: dict[str, dict] = {}
    for row in rows:
        if (row.get("type") == "intent" and row.get("kind") == "settings"
                and row.get("id") in accepted):
            body = row.get("body") or {}
            for field in lab.BOT_BAND_BOUNDS:
                if field in body:
                    held.setdefault(str(row.get("instance_id")), {})[field] = body[field]
    out: dict[tuple[str, str], str] = {}
    plans = rooms.plans(stored)
    for row in rooms.strategies(stored):
        if row.get("kind") != "bot" or rooms.status_of(stored, row["id"]) == "stopped":
            continue
        for leg in (plans.get(row["id"]) or {}).get("legs") or []:
            band = held.get(str(rooms.leg_ref(leg))) or {}
            if rooms.leg_kind(leg) == "bot" and all(f in band for f in lab.BOT_BAND_BOUNDS):
                out.setdefault((str(row.get("ref")).lower(), lab.band_label(band)), row["id"])
    return out


def _thrown_species(rows: list[dict], samples: list[dict]) -> dict[str, str]:
    """Species -> the instance of ours the operator's rule threw away (three stop-losses in a
    row, `qa.lab.discarded_bots`). Their "zahod a uz ho nechci videt" (2026-10-07) was said of
    a bot; whether it covers the species is theirs to say, so a band Nexus names for it is held
    and said, never launched."""
    species = _instance_species(rows)
    return {species[inst]: inst for inst in sorted(lab.discarded_bots(rows, samples))
            if inst in species}


def _species_cloned() -> dict[str, str]:
    """Every species our clone record has already asked for, lower-case id ->
    why the launch leaves it alone: a clone we own (accepted, whoever opened
    it, paused or not), or one their API refused -- unless the refusal was
    the account's cap on bots (`lab.capacity_refusal`), which says nothing
    about the species and no longer holds once a bot is paused or released.

    R01/R06, deep pass of 2026-09-22: the launch knew only the rooms, so
    STR-0001's Perceptron (CLN-0002) was cloned again and refused with a 400
    (CLN-0017), and a refusal left nothing that stopped the next answer
    naming the species from spending a room on the same refusal. A clone
    whose outcome was never recorded is left alone too: we do not know it
    did not land."""
    rows = _sibling("clone").load()
    outcomes = {row.get("id"): row for row in rows
                if row.get("type") == "outcome" and not row.get("kind")}
    # NEXT 2026-10-01 (NEX-0109): CLN-0011 was released on 2026-09-28 ("Bot
    # deleted") and the tick went on saying "we already own a clone of it" --
    # a clone whose release they ACCEPTED is gone, and the species is free.
    released = lab.released(rows)
    out: dict[str, str] = {}
    for row in rows:
        species = str(row.get("source_id") or "").lower()
        if row.get("type") != "intent" or row.get("kind") or not species:
            continue
        result = outcomes.get(row.get("id")) or {}
        if result.get("outcome") == "accepted":
            if str(result.get("clone_instance_id")) in released:
                out.pop(species, None)      # owned once, deleted since
                continue
            out[species] = (f"we already own a clone of it ({row.get('id')}, "
                            f"{result.get('clone_instance_id')})")
        elif lab.capacity_refusal(result):
            # The account's cap on bots, not a verdict on the species (L06, 2026-10-04):
            # it is lifted by pausing or releasing one, so it is tried again.
            continue
        elif species not in out:
            out[species] = (f"their API refused to clone it ({row.get('id')}, "
                            f"HTTP {result.get('http_status')}, "
                            f"{result.get('outcome') or 'no outcome recorded'})")
    return out


def _paper_outcome(paper, entry_id) -> dict:
    """The outcome row paper.py wrote for one of its intents, or {} -- a
    close returns its intent, not whether their side accepted it."""
    if not entry_id:
        return {}
    return next((row for row in reversed(paper.load())
                 if row.get("type") == "outcome" and row.get("id") == entry_id), {})


def _clone_outcome(clone, kind: str, instance: str) -> str | None:
    """What clone.py recorded for its newest `kind` call on this instance --
    fund() and enable() return their body, not whether it was accepted."""
    rows = clone.load()
    asked = [row.get("id") for row in rows
             if row.get("type") == "intent" and row.get("kind") == kind
             and row.get("instance_id") == instance]
    if not asked:
        return None
    return next((row.get("outcome") for row in reversed(rows)
                 if row.get("type") == "outcome" and row.get("id") == asked[-1]),
                None)


def bot_variants() -> dict:
    """The next setting of every paper bot of ours whose last room has its
    verdict (V5 of plan v2) -- the tick door that walks the grid in TIME.

    REPLY-0049: one active paper clone per species per account, so a
    species' settings run one after another on its ONE clone. For a clone
    of ours whose rooms are all stopped, the newest with a verdict, and which
    WE paused (a halt of theirs, or an unexplained one, is never restarted --
    `clone.restart_refusal`), the next variant of `qa.lab.variants()`:

        a proposal of ours (OUR-NNNN)  ->  a NEW room from it, its criterion
        ->  clone.settings() (the paper floor; refused while a room runs,
            and this one is not running yet)
        ->  clone.enable() (starts again only after our pause and that
            accepted change)  ->  the room running

    Money: nothing new moves -- the clone's parked money becomes exposure,
    and 60% of the book is the one limit asked of it (`restart_affordable`).
    A step that fails stops the room with the reason and leaves the bot
    paused; the variant is spent (`tried_variants`), so the next tick
    proposes the next one rather than the same refusal every tick.

    A species' variants run one at a time, so they are one experiment's
    exposure at any moment: correlated rooms count as one by construction.

    Two clones are left alone, with a held line: one we RELEASED (deleted on
    their side; a variant of it is a room `clone.settings()` kills) and one
    with an indicator change on record (a settings PATCH cannot undo it)."""
    if pass_in_flight():
        return {"rooms": 0, "orders": 0, "held": ["variants: a deep pass is running"]}
    clone = _sibling("clone")
    rows = clone.load()
    stored = rooms.load()
    samples = rooms.load_samples()
    went_in = lab.funded(rows)
    deleted = lab.released(rows)
    overridden = lab.indicator_changed(rows)
    thrown = lab.discarded_bots(rows, samples)
    intents = {row.get("id"): row for row in rows
               if row.get("type") == "intent" and not row.get("kind")}
    ours: dict[str, tuple[str, str]] = {}
    for row in rows:
        if (row.get("type") == "outcome" and not row.get("kind")
                and row.get("outcome") == "accepted" and row.get("is_paper") is True
                and row.get("clone_instance_id")):
            intent = intents.get(row.get("id")) or {}
            ours[str(row["clone_instance_id"])] = (
                str(row.get("id")), str(intent.get("source_id") or ""))
    on_clone: dict[str, list[str]] = {}
    for room_id, plan in rooms.plans(stored).items():
        for leg in plan.get("legs") or []:
            if rooms.leg_kind(leg) == "bot":
                on_clone.setdefault(str(rooms.leg_ref(leg)), []).append(room_id)
    titles = rooms.names(stored)
    opened, started, held = 0, 0, []

    for instance, (cid, species) in ours.items():
        rooms_here = sorted(on_clone.get(instance) or [], key=rooms.number)
        if not rooms_here or not species:
            continue            # no room ever ran on it: nothing to vary from
        if any(rooms.status_of(stored, r) != "stopped" for r in rooms_here):
            continue            # one at a time: a room still holds the clone
        last = rooms_here[-1]
        name = titles.get(rooms_here[0]) or species[:8]
        tag = f"{name} ({instance[:8]})"
        if rooms.verdict_of(stored, last) is None:
            # Stopped without a verdict. A variant of ours whose restart never
            # ran (its PATCH or its start refused) measured nothing and holds
            # nothing back; any other room is still owed its verdict.
            opened_from = next((s.get("origin") for s in rooms.strategies(stored)
                                if s["id"] == last), None)
            criterion = rooms.acceptance_of(stored, last) or {}
            if not (lab.is_ours(opened_from) and lab.bot_restart(
                    rows, instance, criterion.get("at"), samples) is None):
                continue
        # After the verdict gate (a held line only where a variant WAS about to be proposed)
        # and before `restart_refusal`, which counts an indicator change as a variant step.
        if instance in deleted:
            # L03, 2026-10-04: released clones passed everything above, so each tick wrote
            # an OUR-NNNN proposal and opened a room that clone.settings() then killed.
            held.append(f"variants: {tag}: released on their side (deleted) -- "
                        f"nothing is left to vary")
            continue
        if instance in overridden:
            # L05, 2026-10-04: a settings PATCH cannot reset an indicator override, so a
            # settings variant would run with that override still on.
            held.append(f"variants: {tag}: an indicator change is on record for it and a "
                        f"settings change cannot undo it -- a settings variant would not "
                        f"be the settings alone")
            continue
        if instance in thrown:
            # [operator 2026-10-07] three stop-losses in a row: not varied again. The wave
            # tool's `resume` releases such a clone; the walk only leaves it alone.
            held.append(f"variants: {tag}: three stop-losses in a row -- thrown away, "
                        f"not varied again")
            continue
        refused = clone.restart_refusal(instance, rows, samples, planned=True)
        if refused:
            held.append(f"variants: {tag}: {refused}"[:300])
            continue
        variant = lab.next_variant(lab.tried_variants(instance))
        if variant is None:
            continue            # the grid is walked; the clone stays parked
        amount = went_in.get(instance) or 0.0
        ok, why = lab.restart_affordable(amount, _free_cash(), _deployed(),
                                         _parked())
        if not ok:
            held.append(f"variants: {tag}: {why}")
            continue
        proposal = lab.note_proposal(
            "bot", species, instance, variant,
            why=(f"the next setting of the grid for {name} on its one paper "
                 f"clone, after {last} had its verdict"))
        origin = proposal["id"]
        try:
            room = rooms.open_strategy(
                origin, f"{name} · {variant['label']}"[:rooms.MAX_TITLE],
                kind="bot", ref=species)["id"]
        except rooms.RoomError as exc:
            held.append(f"variants: {tag}: {exc}")
            continue
        opened += 1

        def stop(why: str) -> None:
            held.append(f"variants: {tag}: {why}"[:300])
            try:
                rooms.set_status(room, "stopped", why=why[:400])
            except rooms.RoomError as exc:
                held.append(f"{room}: {exc}")

        try:
            rooms.add_link(room, cid, why=f"the paper clone of {name} this "
                                          f"variant runs on")
            plan = rooms.set_plan(room, [{"kind": "bot", "ref": instance,
                                          "side": "bull", "share": 1.0}])
            rooms.set_acceptance(
                room, window_days=NIGHT_WINDOW_DAYS, stop_pct=NIGHT_STOP_PCT,
                legs=plan["legs"], benchmark_card=BTC_PROXY,
                why=(f"OUR variant {origin} of {name} ({variant['label']}), "
                     f"on its one paper clone {instance} after {last}'s "
                     f"verdict; settings {json.dumps(variant['settings'])}. "
                     f"Judged from its restart on what the bot held then; "
                     f"the window and the stop are the laboratory's "
                     f"defaults")[:900],
                adopted=True)
        except (rooms.RoomError, KeyError) as exc:
            stop(f"the room could not be written ({exc})")
            continue
        try:
            clone.settings(instance, variant["settings"], True)
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            stop(f"the settings PATCH was refused ({str(exc)[:160]}); the bot "
                 f"stays paused")
            continue
        if _clone_outcome(clone, "settings", instance) != "accepted":
            stop("the settings PATCH was not accepted; the bot stays paused")
            continue
        try:
            clone.enable(instance, True)
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            stop(f"starting it again was refused ({str(exc)[:160]}); its "
                 f"settings changed and it stays paused")
            continue
        if _clone_outcome(clone, "enable", instance) != "accepted":
            stop("starting it again was not accepted; it stays paused")
            continue
        started += 1
        try:
            rooms.set_status(room, "running", why=(
                f"our variant {variant['label']} of {name}, started again on "
                f"{instance} after an accepted settings change"))
        except rooms.RoomError as exc:
            held.append(f"{room}: {exc}")
    return {"rooms": opened, "orders": started, "held": held}


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
    # Hot against control (fomo_watch.py report), into the diary this often.
    "fomo_reading_hours": 6,
    # The Hot headlines study (hot_watch.py report), the same way.
    "hot_reading_hours": 6,
    # Their surface against the shape we agreed (processes.py surface_drift),
    # cached for the session start, which no longer scans (plan v2, V7).
    "surface_hours": 6,
}
TICK_STATE = "lab_tick.json"


# A tick that catches up after a pause takes more than ten minutes (the
# first after 1.5 h took over ten), and a /loop at ten fires again meanwhile.
# Past this, a marker is a tick that died, not one still working.
TICK_STALE_MINUTES = 45


def _tick_marker() -> Path:
    from qa.state import state_dir

    return state_dir() / "lab_tick.running"


def tick_exclusive(*, now: datetime | None = None, actions: dict | None = None,
                   out=print) -> dict:
    """`tick`, unless another one is still running. Two ticks walk the same
    answers and would place two paper orders for one proposal."""
    moment = now or _now()
    marker = _tick_marker()
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        held = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        held = None
    since = lab._at((held or {}).get("at"))
    if since is not None and moment - since < timedelta(minutes=TICK_STALE_MINUTES):
        out(f"tick skipped -- another tick is running since {since.isoformat()[11:16]} "
            f"(pid {held.get('pid')}); it will finish the work")
        # That tick decides; this firing has nothing to wake the manager for.
        out(lab.decide_line([]))
        return {"busy": True, "since": since.isoformat()}
    marker.write_text(json.dumps({"pid": os.getpid(), "at": moment.isoformat()}),
                      encoding="utf-8")
    try:
        return tick(now=now, actions=actions, out=out)
    finally:
        try:
            marker.unlink()
        except OSError:
            pass


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
    closed = lab.close_session(session, lessons, nextup, did=counts)
    # The day's diaries finalise here, and nobody is watching this close: the
    # night archived its own on the way out, and since it was removed
    # (2026-09-21) this is the close the laboratory's writing ends at.
    _archive_diaries()
    return closed


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


def _hot_round() -> dict:
    """One round of the Hot headlines watch. Hot has no history, so a round
    that does not happen is a moment nobody can read again."""
    watch = _sibling("hot_watch")
    client = watch._client()
    try:
        said = watch.tick(client)
    finally:
        client.close()
    capture, resolve = said.get("capture") or {}, said.get("resolve") or {}
    return {"ok": bool(capture.get("ok")), "hot": capture.get("hot", 0),
            "headlines": capture.get("headlines", 0),
            "cards": resolve.get("cards", 0)}


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


def _tracker_round() -> dict:
    """Their tracker and their a2a inbox, read the way the console's --ask
    reads them (`serve.py::poll_once`): each writes to the journal only what
    changed, so a quiet round writes nothing. [operator 2026-09-25]: they
    answer within the hour, and a round that waits for a sweep does not."""
    bounty = _sibling("bounty")
    ours = bounty.refresh_our_reports() or {}
    inbox = bounty.fetch_inbox() or {}
    # A failed read is said, as a door's error, so the first one is a gap
    # (deep pass 2026-09-25, C02: nothing read the klass, and a tracker unread
    # on every tick -- the missing-wallet morning -- was silent).
    unread = [f"{what} unread ({said.get('klass')})"
              for what, said in (("their tracker", ours), ("their inbox", inbox))
              if said.get("klass") != "ok"]
    if unread:
        raise RuntimeError("; ".join(unread))
    return {"tracker": ours.get("klass"), "inbox": inbox.get("klass"),
            "new": len(inbox.get("new") or [])}


def _vendor_news() -> dict:
    from qa.state import read_events

    return lab.vendor_news(read_events())


def _morning_due() -> bool:
    from qa import morning as qa_morning

    return qa_morning.due(datetime.now().astimezone(), load_morning(), ticks=lab.tick_times())


MORNING_LINE = ("  ranní přehled je na řadě -- `python scripts/lab.py morning`, "
                "pak ho publikovat (laborator skill, Ranní přehled)")

CONSOLE_STATUS = "http://127.0.0.1:8787/status"


def _console_collects() -> set[str]:
    """The rounds the console on this machine is doing on its own timers
    (serve.py --fomo, --hot, --sample), as its /status says. One writer per
    diary (plan v2, V4): a tick leaves those rounds to it, and does them
    itself when the console is closed or does not answer -- a checkpoint
    nobody took is gone for good."""
    import urllib.request

    try:
        with urllib.request.urlopen(CONSOLE_STATUS, timeout=2) as response:
            said = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 -- no console is the ordinary case
        return set()
    collectors = said.get("collectors") if isinstance(said, dict) else None
    return {str(k) for k, v in (collectors or {}).items() if v}


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
        "morning": _morning_due,
        "console": _console_collects,
        "fomo": _fomo_round,
        "sample": _sample_round,
        "cycle": cycle,
        "promote": lambda: night_promote(
            since=_now() - timedelta(hours=TICK["answers_hours"])),
        "truth": functools.partial(truth, limit=8),
        "search": _night_search,
        "moves": night_moves,
        "refill": lambda: night_refill(live=_live_card_seeds()),
        "verdicts": verdicts,
        "variants": bot_variants,
        "fomo_reading": lambda: _sibling("fomo_watch").reading(),
        "hot": _hot_round,
        "hot_reading": lambda: _sibling("hot_watch").reading(),
        "surface_drift": lambda: _sibling("processes").surface_drift(),
        "tracker": _tracker_round,
        "vendor": _vendor_news,
        "credit": lambda: _sibling("nexus").credit(),
    }


def _say_tick(said: dict, out) -> None:
    if not out:
        return
    at = str(said.get("at") or _now().isoformat())[11:16]
    if said.get("skipped"):
        out(f"tick {said['session']} {at}: held -- a {said['skipped']} is "
            f"running; memecoins and Hot only ({said.get('fomo')}, "
            f"{said.get('hot')})")
        if said.get("morning_due"):
            out(MORNING_LINE)
        out(lab.decide_line(said.get("decide") or []))
        return
    fomo = said.get("fomo") or {}
    hot_ = said.get("hot") or {}
    memecoins = ("memecoins by the console" if fomo.get("by") == "console"
                 else f"memecoins +{fomo.get('added', 0)} signal(s) / "
                      f"{fomo.get('checked', 0)} checkpoint(s)")
    hot_said = ("Hot by the console" if hot_.get("by") == "console"
                else f"Hot {'round' if hot_.get('ok') else 'round FAILED'} "
                     f"(+{hot_.get('headlines', 0)} headline(s), "
                     f"{hot_.get('cards', 0)} card(s))")
    out(f"tick {said['session']} {at}: {said['backtests']} backtest(s) "
        f"({said['known']} already known), "
        f"{'answers picked up' if said['cycled'] else 'no cycle due'}, "
        f"{said['rooms']} room(s) / {said['orders']} order(s), "
        f"{said['verdicts']} verdict(s), "
        + (f"{said['variants']} bot variant(s) started, "
           if said.get("variants") else "")
        + f"{memecoins}, {hot_said}"
        + (", samples by the console"
           if (said.get("sample") or {}).get("by") == "console" else ""))
    for line in said.get("held") or []:
        out(f"  held:  {line}")
    if said.get("held_older"):
        out(f"  held:  +{said['held_older']} older reason(s) not shown -- "
            f"still retried every tick")
    for line in said.get("verdicts_waiting") or []:
        out(f"  verdict waits:  {line}")
    for line in said.get("exits") or []:
        out(f"  sold at his level:  {line}")
    for line in said.get("close_failed") or []:
        out(f"  close failed:  {line}")
    if said.get("resolved"):
        out(f"  resolved without us, written down: {said['resolved']}")
    decided = said.get("decide") or []
    if "hunt sweep" in decided and said.get("vendor_lines"):
        out(f"  their side moved: {', '.join(said['vendor_lines'])}")
    if "question" in decided:
        out("  question: due -- `lab.py brief`, then `lab.py ask --no-wait`")
    elif said.get("may_ask"):
        out(f"  question: their pace allows one, not due -- nothing new since "
            f"the last, and one goes every {lab.QUESTION_HOURS:g} h")
    else:
        out(f"  question: not now -- {said.get('why')}")
    if said.get("morning_due"):
        out(MORNING_LINE)
    for problem in said.get("errors") or []:
        out(f"  failed: {problem}")
    out(lab.decide_line(decided))


def tick(*, now: datetime | None = None, actions: dict | None = None,
         out=print) -> dict:
    """One step of the laboratory, for a /loop: read where the last stopped,
    do what is due, write down what it did.

    Order by what EXPIRES: the memecoin checkpoints first (the price at +6h is
    gone at +7h), and they run even while a deep pass or a night holds
    everything else. Then the night's own clocks -- answers every half hour
    and a launch straight after, the ranking every six, a bite of the search
    every tick -- then the verdicts that came due and any position that
    resolved without us. It asks nothing; its last line, `decide: ...`, says
    what needs the manager -- and `none` that nothing does (plan v2, V6).
    """
    moment = now or _now()
    doors = {**_tick_doors(), **(actions or {})}
    said: dict = {"at": moment.isoformat(timespec="seconds"), "session": None,
                  "skipped": "", "fomo": None, "hot": None, "sample": None,
                  "credit": None, "cycled": False,
                  "truth": False, "backtests": 0, "known": 0,
                  "refilled": False, "rooms": 0, "orders": 0, "held": [],
                  "verdicts": 0, "variants": 0, "resolved": 0, "errors": []}

    def attempt(name, call, *args):
        try:
            return call(*args)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 -- one door is not the tick
            said["errors"].append(f"{name}: {exc}"[:300])
            return None

    said["session"] = _day_session(moment)
    # The morning report (V11) has no scheduler: this tick says it is due.
    said["morning_due"] = bool(attempt("morning", doors.get("morning", lambda: False)))
    collecting = attempt("console", doors.get("console", set)) or set()

    def collect(name):
        """A round the console is doing is its own; one writer per diary."""
        if name in collecting:
            return {"by": "console"}
        return attempt(name, doors[name])

    said["fomo"] = collect("fomo")
    # Before the hold, like the memecoins: it only reads their headlines and
    # card histories, so it touches nothing a deep pass verifies (#85-#87 are
    # over Nexus answers and our trades), and Hot has no history -- a round
    # skipped is a moment lost.
    said["hot"] = collect("hot")
    if doors["pass"]():
        said["skipped"] = "pass"
    elif doors["night"]():
        said["skipped"] = "night"
    if said["skipped"]:
        said.update(may_ask=False, why=f"a {said['skipped']} is running")
        _decide(said, moment)
        lab.note_tick(said)
        _say_tick(said, out)
        return said

    said["sample"] = collect("sample")
    # After the hold: these reads append to the journal a deep pass verifies.
    said["tracker"] = collect("tracker")
    # Nexus's credit (NEXT 2026-09-26), onto this tick's row for /lab. After
    # the hold, not beside the memecoins: /usage always answers the present,
    # so a reading a pass skips is not lost. A read that fails comes back
    # unread rather than raised, so it never wakes the manager as a gap.
    said["credit"] = lab.credit_to_keep(attempt("credit", doors["credit"]),
                                        lab.load())
    news = attempt("vendor", doors["vendor"]) or {}
    said["vendor_seq"] = news.get("seq")
    # Narrowed to what came after the last sweep in _decide, and not kept.
    said["vendor_items"] = list(news.get("items") or [])
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
    steps = list(lab.night_tick(clocks, moment)["do"])
    # A question in flight is polled on every tick, not on the half-hour
    # clock: an answer that took three minutes used to wait up to thirty more
    # before anything could launch from it.
    if "cycle" not in steps and lab.outstanding(_nexus_rows(), moment):
        steps.insert(0, "cycle")
    for step in steps:
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
        elif step == "truth":
            attempt("truth", doors["truth"])
            state["last_truth"] = moment.isoformat()
            said["truth"] = True

    # The launch is looked at on EVERY tick, not only after a cycle: an answer
    # can come back through its own poll (`nexus.py answer`) between two
    # cycles, and it is launched by the next tick rather than the next half
    # hour. Cheap when nothing is new -- decided answers are skipped.
    launched = attempt("promote", doors["promote"]) or {}
    said["rooms"] += launched.get("rooms", 0)
    said["orders"] += launched.get("orders", 0)
    said["answered"] = list(launched.get("answered") or [])
    # The newest six: the launch lists oldest answer first, and the first six
    # were the same four answers all night while NEX-0063's reason sat unseen.
    every = list(launched.get("held") or [])
    said["held"] = every[-6:]
    # And how many that cut, said: NEX-0078 slid off unannounced (2026-09-23).
    said["held_older"] = len(every) - len(said["held"])

    judged = list(attempt("verdicts", doors["verdicts"]) or [])
    # A verdict that waits on a failed read is not a verdict (C1): counted
    # apart, and named with the read that failed. A close that failed is
    # said, and decide() reads it (RL01).
    said.update(_tally_verdicts(judged))
    # After the verdicts, whose close pauses a judged bot: its next setting
    # starts on the same clone (V5, REPLY-0049), in a room of ours.
    varied = attempt("variants", doors["variants"]) or {}
    said["rooms"] += varied.get("rooms", 0)
    said["variants"] = varied.get("orders", 0)
    # Before the launch's, not after: a variant's refusal is the same line
    # every tick (a bot that stopped by itself is never restarted), and
    # twelve of them took all six lines, so why NEX-0109 opened nothing was
    # never on screen (2026-10-01).
    every = list(varied.get("held") or []) + every
    said["held"] = every[-6:]
    said["held_older"] = len(every) - len(said["held"])
    # Every gap-class line, not the newest six: decide() reads these, and a
    # line cut from the six was never news -- the gate writes an unknown
    # card once and only once (RL04, deep pass of 2026-09-24).
    said["gap_held"] = [line for line in every if lab.GAP_HELD.search(str(line))]
    said["resolved"] = len(attempt("resolved", _record_resolved) or [])

    last_reading = lab._at(state.get("last_fomo_reading"))
    if last_reading is None or (moment - last_reading).total_seconds() >= \
            TICK["fomo_reading_hours"] * 3600:
        reading = attempt("fomo_reading", doors["fomo_reading"])
        if reading is not None:
            lab.note_fomo_reading(reading)
            state["last_fomo_reading"] = moment.isoformat()

    last_hot = lab._at(state.get("last_hot_reading"))
    if last_hot is None or (moment - last_hot).total_seconds() >= \
            TICK["hot_reading_hours"] * 3600:
        reading = attempt("hot_reading", doors["hot_reading"])
        if reading is not None:
            lab.note_hot_reading(reading)
            state["last_hot_reading"] = moment.isoformat()

    last_scan = lab._at(state.get("last_surface_scan"))
    if last_scan is None or (moment - last_scan).total_seconds() >= \
            TICK["surface_hours"] * 3600:
        if attempt("surface_drift", doors["surface_drift"]) is not None:
            state["last_surface_scan"] = moment.isoformat()

    # The deep pass returned above; what is left is theirs (V5, 2026-09-23):
    # the hour's asks, their bound of outstanding jobs, their backoff.
    rows = _nexus_rows()
    may, why = lab.may_ask_now(rows, moment)
    if not may and lab.may_ask_now(rows, moment, ignore_backoff=True)[0]:
        may, why = True, (f"through the shallow lane -- the deep one is "
                          f"held: {why}")
    said.update(may_ask=may, why=why)
    _decide(said, moment, rows)
    state["queue"] = queue
    _save_tick_state(state)
    lab.note_tick(said)
    _say_tick(said, out)
    return said


def _decide(said: dict, moment: datetime, nexus_rows: list[dict] | None = None) -> None:
    """What the manager is woken for (V6), written onto the tick's own record
    so the next tick can read when the last hunt was."""
    earlier = [row for row in lab.load() if row.get("type") == "tick"][-200:]
    rows = _nexus_rows() if nexus_rows is None else nexus_rows
    said["decide"] = lab.decide(said, earlier, lab.last_question_at(rows), moment,
                                local_hour=moment.astimezone().hour)
    items = said.pop("vendor_items", None) or []
    said["vendor_lines"] = (lab.news_since(items, earlier)
                            if "hunt sweep" in said["decide"] else [])


def board_rows() -> list[dict]:
    """`qa.lab.board` over the diaries on this machine -- no call to them, so
    it answers while their API is down, from the sampler's newest readings."""
    from qa.rooms import load_samples

    return lab.board(_nexus_rows(), lab.load(), rooms.load(),
                     _sibling("paper").load(), load_samples(),
                     _sibling("clone").load())


REPORT = Path("lab") / "report.json"


def report_path() -> Path:
    from qa.state import state_dir

    return state_dir() / REPORT


def write_report(now: datetime | None = None) -> dict:
    """`state/lab/report.json`, the one file the /lab page reads (V4): what
    each product earned after costs, from the diaries on this machine --
    nothing fetched, so it answers while their API is down."""
    from qa import lab_report
    from qa.rooms import load_samples

    said = lab_report.report(
        _nexus_rows(), lab.load(), rooms.load(), _sibling("paper").load(),
        load_samples(), _sibling("clone").load(),
        _sibling("fomo_watch").load(), now=now or _now())
    _write_text(report_path(), json.dumps(said, ensure_ascii=False, indent=1))
    return said


MORNING = Path("lab") / "morning.json"
MORNING_PAGE = Path("lab") / "morning.html"


def _morning_file(rel: Path) -> Path:
    from qa.state import state_dir

    return state_dir() / rel


def load_morning() -> dict:
    """The morning report's own record: the day it was last published, its
    address, and the report it showed -- what the next one compares against."""
    try:
        said = json.loads(_morning_file(MORNING).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return said if isinstance(said, dict) else {}


def _write_text(target: Path, text: str) -> None:
    """Whole or not at all, whoever else is writing the same file.

    /lab and /lab.json on the console's threaded server, the tick and the
    morning page all write report.json, and all did it through ONE
    `report.json.tmp` -- on Windows a replace while another writer held that
    tmp raised PermissionError, a 500 on the page or a failed tick (R03, deep
    pass of 2026-09-24). Each writer has its own tmp, and a replace that
    meets another writer's open handle waits a moment and tries again."""
    import threading
    import time

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.{os.getpid()}."
                           f"{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            tmp.replace(target)
            return
        except PermissionError:
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05)


def morning_page(now_local: datetime | None = None) -> Path:
    """Plan v2, V11: build this morning's report into state/lab/morning.html
    for the session to publish. Not yet "made" -- that is `--published`, so a
    publish that failed is still due."""
    from qa import morning as qa_morning

    moment = now_local or datetime.now().astimezone()
    report = write_report()
    state = load_morning()
    deep = REPO_ROOT / "DEEP-PASS.md"
    import re

    from qa.state import read_events

    registered = []
    for pre in sorted((REPO_ROOT / "state" / "preregistrations").glob("PRE-*.md")):
        found = re.search(r"^\s*Registered\s+(\S+)", pre.read_text(encoding="utf-8"), re.M)
        if found:
            registered.append(found.group(1))
    # What each report is about, from our copy of their tracker (the
    # operator, 2026-10-01: the report numbers must say what they are).
    titles = {}
    try:
        from qa.state import state_dir
        rows, ledger = [], {}
        try:
            copy = json.loads((state_dir() / "bounty.json").read_text(encoding="utf-8"))
            rows = copy.get("reports") or copy.get("items") or []
        except (OSError, ValueError, AttributeError):
            pass
        try:
            ledger = json.loads((state_dir() / "ledger.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        # Each report is named by its own Czech line (outbox/reports-cs.yaml), never by the
        # tracker's English title (the operator, 2026-10-03).
        czech = {}
        try:
            import yaml

            czech = (yaml.safe_load((REPO_ROOT / "outbox" / "reports-cs.yaml").read_text(
                encoding="utf-8")) or {}).get("reports") or {}
        except (OSError, ValueError, ImportError):
            czech = {}
        titles = qa_morning.titles_from(rows, ledger, czech)
    except Exception:  # noqa: BLE001 -- a title is a nicety; the report still builds
        titles = {}
    view = qa_morning.build(
        report, state, deep.read_text(encoding="utf-8") if deep.is_file() else "",
        lab.load(), moment, events=read_events(), registered=registered,
        titles=titles)
    page = _morning_file(MORNING_PAGE)
    _write_text(page, _sibling("morning").render(view))
    state["pending"] = {"built_at": _now().isoformat(timespec="seconds"),
                        "snapshot": report}
    _write_text(_morning_file(MORNING), json.dumps(state, ensure_ascii=False))
    return page


def morning_published(url: str, now_local: datetime | None = None) -> dict:
    """The report went out at `url`: today is made, and what it showed is
    what tomorrow's compares against."""
    moment = now_local or datetime.now().astimezone()
    state = load_morning()
    pending = state.pop("pending", None) or {}
    state.update(made_on=moment.date().isoformat(),
                 made_at=_now().isoformat(timespec="seconds"), url=url,
                 snapshot=pending.get("snapshot") or write_report())
    _write_text(_morning_file(MORNING), json.dumps(state, ensure_ascii=False))
    return state


def _board_line(row: dict) -> str:
    if row["pnl_pct"] is not None:
        money = (f"{row['pnl_pct']:+6.2f}%  {row['pnl_usdc']:+.2f} on "
                 f"{row['stake_usdc']:.0f} USDC")
        if row.get("priced", 0) < row.get("positions", 0):
            money += f" ({row['priced']} of {row['positions']} priced)"
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
    free, deployed, parked = _free_cash(), _deployed(), _parked()
    today = lab.rooms_within(rooms.load(), now)
    may, why = lab.may_ask(pass_in_flight())
    if may:
        may, why = lab.may_ask_now(nexus_rows, now)
    out = [f"questions: {asked} in the last 24 h, no cap of ours -- "
           + ("the next may go now" if may else f"not now: {why}")]
    if free is None:
        out.append("book: unreadable -- nothing can be launched on it")
    else:
        book = free + deployed + parked
        out.append(f"book: {free:.0f} USDC free, {deployed:.0f} out "
                   f"({deployed / book * 100 if book else 0:.1f}% of "
                   f"{book:.0f}; the ceiling is "
                   f"{lab.CAPS['total_exposure'] * 100:.0f}%, the only limit), "
                   f"{_running_experiments()} experiment(s) running, "
                   f"{today} new room(s) today"
                   + (f"; {parked:.0f} parked in bots that do not trade"
                      if parked else ""))

    # His rows only: ours are put to him below as questions, and listing one
    # here credited our setting to him (deep pass 2026-09-25, C05).
    rows = [row for row in board_rows() if not lab.is_ours(row.get("origin"))]
    out.append("")
    out.append("his proposals, best earner first (what to tell him):")
    for row in rows[:12]:
        out.append(_board_line(row))
    if not rows:
        out.append("  none has come to anything yet")

    # Our own lane (V5): every room of ours that runs is put to him as a
    # question -- would he run this setting, or another? -- never as a
    # proposal of his, and never ranked above his picks (the board above).
    stored = rooms.load()
    titles = rooms.names(stored)
    ours = [s for s in rooms.strategies(stored) if lab.is_ours(s.get("origin"))
            and rooms.status_of(stored, s["id"]) == "running"]
    if ours:
        out.append("")
        out.append("OUR rooms running -- each a question for him, never a "
                   "proposal: would he run this setting, or which instead?")
        for strategy in ours:
            out.append(f"  {strategy['id']}  {strategy['origin']}  "
                       f"{titles.get(strategy['id'])}")

    # Every stop of a paper bot of ours, and its cause (V2, 2026-09-23): two
    # halted by themselves and nobody noticed. An unexplained one is a check
    # and a report, and a question for him.
    stops = lab.bot_stops(_sibling("clone").load(), rooms.load_samples())
    if stops:
        out.append("")
        out.append("paper bots that stopped, and why (a halt that was not ours "
                   "is never started again; after our pause, only as a new "
                   "setting in a room of ours):")
        for stop in stops[-8:]:
            pct = stop.get("profit_pct")
            out.append(f"  {stop['instance'][:8]}  {stop['cause']:11}  between "
                       f"{str(stop['after'])[:16]} and {str(stop['before'])[:16]}"
                       + (f", at {pct:+.2f}% on what went in"
                          if pct is not None else ""))

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
        # Say the unit. The search asks with include_fees FALSE (backtest()'s
        # default; only the gate passes True), so these are gross. On
        # 2026-09-21 they went to Nexus unlabelled beside the sentence "no
        # room opens without your own backtest after fees", he reproduced the
        # same basket after fees at half the return, and wrote a section of
        # his answer about two engines disagreeing. They did not disagree.
        fees = "after fees" if row.get("fees") else "FEES OFF (gross)"
        out.append(f"  sharpe {row['s']}  ret {row['r']}%  over {row['p']} "
                   f"d  {fees}  {legs[:60]}")
    if not best:
        out.append("  nothing in the register yet")

    reading = lab.last_fomo_reading()
    if reading:
        out.append("")
        out.append(f"memecoins -- does their `hot` predict a pump? "
                   f"({str(reading.get('at'))[:16]}, hot against a control "
                   f"from the same feed):")
        for line in _sibling("fomo_watch").say_reading(reading):
            out.append(f"  {line}")

    hot_reading = lab.last_hot_reading()
    if hot_reading:
        watch = _sibling("hot_watch")
        out.append("")
        # First whether his rule lets anything through at all (NEXT.md
        # 2026-09-21): when almost nothing does, that number is the question.
        out.append(f"Hot headlines -- does anything pass NEX-0055? "
                   f"({str(hot_reading.get('at'))[:16]}):")
        out.extend(f"  {line}" for line in watch.say_passing(hot_reading))
        out.append("  and does a basket that just entered Hot keep rising?")
        for line in watch.say_reading(hot_reading):
            out.append(f"  {line}")
    out.append("")
    out.append("what we know about Nexus -- read before writing to him:")
    out.extend(f"  - {line}" for line in NEXUS_KNOWN)
    return "\n".join(out)


# What the laboratory has learned about Nexus himself. It lived in
# laborator/SKILL.md, loaded on every firing of the loop, while only a question
# needs it (plan v2, V6); this is where it grows now.
NEXUS_KNOWN = (
    "The deep lane falls over: NEX-0020..0025 all failed in 78-92 s on "
    "2026-09-11. `lab.py ask` waits out the backoff their failure asked for.",
    "It refuses sizing questions about bots with QUERY_RESTRICTED -- a filter "
    "on the question's WORDING (REPLY-0031), not a boundary: the same advice "
    "for event cards comes in full. Rephrase once, more generally, never more.",
    "It recommends tools the caller cannot reach (update_bot_settings, "
    "identify_address live in its own toolbelt, not on /mcp/v1 -- #85). Check "
    "every tool name against tools/list before acting.",
    "It has named a card that does not exist (#91), with a live-looking index "
    "and 90-day metrics. The launch reads every card live; a 404 is not bought.",
    "Same for a fund (NEX-0089): AIB-CRYPTO-LONG, with a live-looking index "
    "138.44 and a NAV/share, is not in list_funds. `launch_fund` reads the "
    "history live too, so it opened nothing -- but a watch-only pick is not "
    "self-verifying the way a room with an order is; read `_fund_catalogue()` "
    "before repeating one of his fund symbols anywhere else.",
    "It quotes internal source paths (#92). Their disclosure problem, not a "
    "licence to read them.",
    "It will refuse its own best number, with good reasons (stockbull-blue at "
    "sharpe 5.11: 24 h is one regime-day). Do not assume it is promotional. "
    "Its leading indicator: N_eff = N / (1 + (N-1)*rho) over the open book; "
    "backtest over the longest history, which #99 says is silently truncated.",
    "Its numbers come from get_strategy_returns, not the leaderboard (it said "
    "CryptoBull Blue 5.16 where the leaderboard says 4.69).",
    "It cannot read the movers tournament (GET /universe/movers/tournament is "
    "not on its key), so its tournament picks are a blind ranking.",
    "A proposal is concrete only if it names what to buy, clone or mark: the "
    "whole card id, the bot's exact species name, the fund's symbol. NEX-0002 "
    "answered at length and named none.",
    "His species roster is narrower than ours: NEX-0108 confirmed only "
    "Divergence Dragon and RSI Sniper (wta_species) from a '10-species "
    "roster' he can read, and could not verify Liquidation Hunter, Delta "
    "Hunter, Sent Surfer or Corr Catcher -- all perpetual_agent, real and "
    "clonable on GET /cloned-bots/available. Don't expect him to confirm a "
    "perpetual_agent species by name; ask what he'd do with it, not whether "
    "it exists.",
)


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
    # What the manager still owes the operator's feedback, from docs/lab-manager.md.
    for owed in lab.manager_open_lines():
        print(f"  manager owes: {owed}")
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
    again_cmd = sub.add_parser("rejudge-costs", help="judge again, without the 1.4%% round trip, "
                                                     "every card verdict it was charged on")
    again_cmd.add_argument("--confirm", action="store_true")
    sub.add_parser("surface", help="their catalogue against the baseline")
    sub.add_parser("ask-cards", help="ask Nexus for up to five cards, with brakes")
    launch_cmd = sub.add_parser(
        "launch", help="read one answer of his again and open what it names, read or not")
    launch_cmd.add_argument("answer", help="NEX-NNNN")
    ask_cmd = sub.add_parser("ask", help="one question to Nexus, with brakes")
    ask_cmd.add_argument("question")
    ask_cmd.add_argument("--no-wait", action="store_true")
    ask_cmd.add_argument("--lane", default="auto",
                         choices=["auto", "deep", "shallow", "chat"],
                         help="auto: deep, or qa-agent/ask while deep is full; "
                              "chat: the NEXUS bar (ask_nexus)")
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
    sub.add_parser("report", help="state/lab/report.json -- what each product "
                                  "earned after costs, for the /lab page")
    morning_cmd = sub.add_parser(
        "morning", help="build this morning's report (state/lab/morning.html) "
                        "for the session to publish; --published URL records it")
    morning_cmd.add_argument("--published", metavar="URL")
    log_cmd = sub.add_parser(
        "log", help="one line of today's diary: done, learned (--lesson) or "
                    "to pick up (--next)")
    log_cmd.add_argument("text")
    kind = log_cmd.add_mutually_exclusive_group()
    kind.add_argument("--lesson", action="store_const", const="lesson",
                      dest="kind")
    kind.add_argument("--next", action="store_const", const="next", dest="kind")
    # The morning report's loop (V11): their feedback, what was changed
    # because of it, and a message for Cymetica the report carries ready.
    kind.add_argument("--feedback", action="store_const", const="feedback",
                      dest="kind")
    kind.add_argument("--acted", action="store_const", const="acted", dest="kind")
    kind.add_argument("--telegram", action="store_const", const="telegram",
                      dest="kind")
    open_cmd = sub.add_parser("open", help="start a session")
    open_cmd.add_argument("--mode", default="session", choices=["session"])
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
    elif args.cmd == "rejudge-costs":
        # 2026-10-08: paper fills pay nothing (REPLY-0136), and the operator asked for every
        # result in the laboratory to be counted again that way. A new verdict row per room,
        # the newest wins everywhere it is read; the charged one stays in the diary.
        stored = rooms.load()
        changed = 0
        for room in sorted({r.get("room") for r in stored if r.get("type") == "verdict"}):
            again = lab.rejudged_without_cost(rooms.verdict_of(stored, room),
                                              rooms.acceptance_of(stored, room))
            if again is None:
                continue
            changed += 1
            was = again["was"]
            print(f"  {room}: {was['verdict']} {was['return_pct']:+.2f}% -> "
                  f"{again['verdict']} {again['return_pct']:+.2f}%")
            if args.confirm:
                rooms.record_verdict(room, again)
        print(f"{changed} verdict(s) judged again"
              + ("" if args.confirm else " -- nothing written: --confirm writes them"))
    elif args.cmd == "verdicts":
        said = verdicts()
        if not said:
            print("no window has come due")
        for row in said:
            if row.get("exit"):
                # A leg sold at his take-profit or stop is not a verdict.
                print(f"  {row['room']}: sold {row['position']} at his "
                      f"{'take-profit' if row['exit'] == 'tp' else 'stop'} "
                      f"({row['moved']:+.2f}% from our fill)")
                for line in row.get("close_failed") or []:
                    print(f"      sale failed: {line}")
                continue
            # A retry of an owed close carries no verdict (RL01).
            print(f"  {row['room']}: {row.get('verdict', 'close owed')} -- "
                  f"{row.get('why', '')}")
            for line in row.get("close_failed") or []:
                print(f"      close failed: {line}")
    elif args.cmd == "surface":
        print(json.dumps(surface(), ensure_ascii=False, indent=1))
    elif args.cmd == "ask":
        print(json.dumps(ask(args.question, wait=not args.no_wait,
                             lane=args.lane),
                         ensure_ascii=False, indent=1, default=str)[:2000])
    elif args.cmd == "ask-cards":
        said = ask(cards_question(), wait=False)
        print(f"{said.get('id')}: asked for up to five cards")
    elif args.cmd == "launch":
        print(json.dumps(night_promote(only=args.answer), ensure_ascii=False, indent=1,
                         default=str))
    elif args.cmd == "buy":
        print(json.dumps(buy(args.card, args.usdc, args.nexus, args.confirm),
                         ensure_ascii=False, indent=1, default=str)[:2000])
    elif args.cmd == "tick":
        tick_exclusive()
    elif args.cmd == "brief":
        print(brief())
    elif args.cmd == "morning":
        if args.published:
            state = morning_published(args.published)
            print(f"  published {state['made_on']} at {state['url']}")
        else:
            page = morning_page()
            url = load_morning().get("url")
            print(f"  built {page}")
            print(f"  publish it {'to ' + url + ' (Artifact read, then publish with url)' if url else 'as a new Artifact'}"
                  f", then: python scripts/lab.py morning --published <url>")
    elif args.cmd == "report":
        said = write_report()
        for name, product in said["products"].items():
            net = product["net_pct"]
            print(f"  {name:10} n={product['n']:<3} "
                  + (f"{net:+.2f}%" if net is not None else "  -   ")
                  + f"  running {product['running']}")
        print(f"  -> {report_path()}")
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
