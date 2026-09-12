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
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

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


def _asked_this_session(rows: list[dict] | None = None) -> int:
    """Questions since this session opened -- the cap is per session, and a
    count over the whole file would close the laboratory after eight questions
    for ever."""
    notebook = lab.load()
    session = _session_now()
    if session is None:
        return 0
    opened = None
    for row in notebook:
        if row.get("type") == "session" and row.get("session") == session:
            opened = _moment(row.get("at"))
    if opened is None:
        return 0
    asked = 0
    for row in rows if rows is not None else _nexus_rows():
        if row.get("type") != "question":
            continue
        when = _moment(row.get("at"))
        if when and when >= opened:
            asked += 1
    return asked


def _free_cash() -> float | None:
    """What the last recorded account said was free.

    The live floor is paper.py's own book, which refuses an order it cannot
    pay for and refuses outright when the money in the bots cannot be read.
    This is the lab's policy cap on top of it, so the last recorded number is
    the honest input: it is what we know without asking them again.
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
        if isinstance(value, (int, float)):
            return float(value)
    return None


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
    """Their tool catalogue now, against the snapshot taken before the upgrade."""
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
        before = [t["name"] for t in
                  json.loads(BASELINE.read_text(encoding="utf-8"))["tools"]]
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        pass
    return {"now": names, "new": sorted(set(names) - set(before)),
            "gone": sorted(set(before) - set(names))}


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
        out.append(f"last session {last.get('session')} closed {when}")
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
        except Exception as exc:  # noqa: BLE001 -- one bad poll is not the cycle
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
    may, why = lab.may_ask(_asked_this_session(), pass_in_flight())
    if not may:
        raise SystemExit(f"not asking: {why}")
    return _sibling("nexus").ask(question, wait=wait)


def buy(card_id: str, usdc: float, nexus_id: str | None, confirm: bool) -> dict:
    if pass_in_flight():
        raise SystemExit(
            "not buying: a deep pass is running and #87 judges the newest "
            "trade. Wait for it to finish")
    ok, why = lab.affordable(usdc, _free_cash(), _running_experiments())
    if not ok:
        raise SystemExit(f"not buying: {why}")
    print(f"[lab] {why}")
    return _sibling("paper").buy(card_id, usdc, nexus_id, confirm)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="where we are, and what is due")
    truth_cmd = sub.add_parser("truth", help="their backtests, ranked")
    truth_cmd.add_argument("--limit", type=int, default=12)
    sub.add_parser("cycle", help="finish what is in flight, sample, compare")
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
    open_cmd = sub.add_parser("open", help="start a session")
    open_cmd.add_argument("--mode", default="session",
                          choices=["session", "night"])
    close_cmd = sub.add_parser("close", help="end it, with what it learned")
    close_cmd.add_argument("--lesson", action="append", default=[])
    close_cmd.add_argument("--next", action="append", default=[], dest="nextup")
    args = parser.parse_args(argv)

    printable()

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
    elif args.cmd == "open":
        record = lab.open_session(mode=args.mode)
        print(f"{record['session']} open ({record['mode']})")
    elif args.cmd == "close":
        session = _session_now()
        if session is None:
            raise SystemExit("no session is open")
        record = lab.close_session(session, args.lesson, args.nextup)
        print(f"{record['session']} closed: {len(args.lesson)} lesson(s), "
              f"{len(args.nextup)} next")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
