"""The casino department: paper bots at paper Agent Casino tables, until the live tables open.

    python scripts/casino.py tick [--confirm]      read our tables, compare, keep the diary; with
                                                   --confirm start what is seated, apply the variants,
                                                   ask the next seats. Its last line says what to do.
    python scripts/casino.py audit --tables 33,40  the comparisons on any tables, nothing written
    python scripts/casino.py handled KEY --how #N  a contradiction dealt with (a report, the spec, ours)
    python scripts/casino.py lapse --table T --instance I   one ask left to run out its 24 hours
    python scripts/casino.py brief                 where it stands
    python scripts/casino.py report                state/casino/report.json, for the /lab page

The comparisons are qa/casino.py; docs/agent-casino-test-2026-11-01.md is the test they came out of.

An ask is `scripts/outsider.py seat`, with its floor. Their OpenAPI makes approving a seat BearerJWT
only, so no key here can do it: `decide: approve N` is the owner's click, in the signed-in Browser
pane. What this writes is declared in components.yaml with a closed body (fill_house, coach, risk,
bot_settings), each read back first by `qa.casino.write_refusal`: a paper USDC table, a seat of ours.

Every write is two records in state/casino.jsonl (rule 9): the intent before the POST, the outcome
after. A failed read is said, never taken for an empty one (rule 8).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import casino  # noqa: E402
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

BASE = "/api/v1/agent-tournaments"
FLASH_TIERS = ("fmicro1h", "fpro1h", "fmicro5h", "fpro5h", "fmicro", "fpro")
SEAT_FIELDS = ("rank", "roi_pct", "trades", "volume_usdc", "pnl_usdc", "bot_state", "bot_state_label",
               "bot_state_reason", "trades_today", "daily_allowance", "allowance_used_up", "qualified")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def path() -> Path:
    return state_dir() / "casino.jsonl"


def load() -> list[dict]:
    target = path()
    if not target.is_file():
        return []
    rows = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _append(record: dict) -> dict:
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": _now().isoformat(timespec="seconds"), **record}
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(f"casino_{name}", REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _client(write: bool = False):
    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    if write:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=60.0)


def _read(client, url: str):
    """The body, or None with the failure said: a failed read is not an empty one."""
    import httpx

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        print(f"  {url}: {type(exc).__name__}: not read")
        return None
    finally:
        CURRENT_TIER.reset(token)
    if response.status_code != 200:
        print(f"  {url}: HTTP {response.status_code}: not read")
        return None
    try:
        return response.json()
    except ValueError:
        print(f"  {url}: not JSON: not read")
        return None


def _post(client, url: str, body: dict | None, kind: str, **fields) -> dict:
    """Rule 9: the intent before the POST, the outcome after. `unknown` may have landed."""
    import httpx

    _append({"type": "intent", "kind": kind, "url": url, "body": body, **fields})
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(url, json=body) if body is not None else client.post(url)
    except httpx.HTTPError as exc:
        never_left = isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))
        return _append({"type": "outcome", "kind": kind, "url": url, "outcome": "not_sent" if never_left else "unknown",
                        "error": f"{type(exc).__name__}: {exc}"[:300], **fields})
    finally:
        CURRENT_TIER.reset(token)
    status = response.status_code
    outcome = "accepted" if 200 <= status < 300 else "rejected" if 400 <= status < 500 else "unknown"
    return _append({"type": "outcome", "kind": kind, "url": url, "outcome": outcome, "http_status": status,
                    "response": (response.text or "")[:300], **fields})


def experiments(rows: list[dict]) -> dict:
    """The experiment of each table, last row wins (one of ours to a table)."""
    return {r.get("table_id"): r for r in rows if r.get("type") == "experiment"}


def adopt(rows: list[dict], my_rows: list[dict]) -> list[dict]:
    """A seat of ours nobody registered (asked by hand) is a coach-on baseline, so nothing is run twice."""
    known = experiments(rows)
    made = []
    for row in my_rows:
        if row.get("table_id") not in known and row.get("status") in ("seated", "pending"):
            made.append(_append({"type": "experiment", "variant": "A", "name": row.get("bot"),
                                 "species": str(row.get("bot") or "").split(" ", 1)[-1], "tier": row.get("tier"),
                                 "table_id": row.get("table_id"), "seat_id": row.get("seat_id"), "by": "adopted"}))
    return made


def start_tables(client, my_rows: list[dict], confirm: bool) -> list:
    """Fill the free seats of the tables we are seated at: they run now. Returns what did not start."""
    waiting = sorted({r.get("table_id") for r in my_rows
                      if r.get("status") == "seated" and r.get("table_status") == "open"})
    left = []
    for table_id in waiting:
        table = _read(client, f"{BASE}/tables/{table_id}")
        seat = next((r.get("seat_id") for r in my_rows if r.get("table_id") == table_id), None)
        why = casino.write_refusal(table, seat)
        if why or not confirm:
            if why:
                print(f"  not started: {why}")
            left.append(table_id)
            continue
        said = _post(client, f"{BASE}/tables/{table_id}/fill-house", None, "fill_house", table_id=table_id)
        print(f"  fill-house {table_id}: {said['outcome']} (HTTP {said.get('http_status')})")
        if said["outcome"] != "accepted":
            left.append(table_id)
    return left


def apply_variants(client, rows: list[dict], tables: dict, confirm: bool) -> None:
    """The one write of a variant, once, when its table runs."""
    applied = {r.get("seat_id") for r in rows if r.get("type") == "outcome" and r.get("kind") == "variant"
               and r.get("outcome") == "accepted"}
    for table_id, row in experiments(rows).items():
        table = tables.get(table_id)
        write = casino.variant_write(str(row.get("variant")))
        seat = casino._my_id(table) if table else None
        if not write or not table or table.get("status") != "running" or seat is None or seat in applied:
            continue
        why = casino.write_refusal(table, seat)
        if why:
            print(f"  variant {row.get('variant')} at {table_id} not applied: {why}")
            continue
        route, body = write
        if not confirm:
            print(f"  would apply variant {row.get('variant')} at {table_id}: {route} {body}")
            continue
        said = _post(client, f"{BASE}/seats/{seat}/{route}", body, "variant", seat_id=seat, table_id=table_id,
                     variant=row.get("variant"))
        print(f"  variant {row.get('variant')} at {table_id}: {route} {body}: {said['outcome']}")


def seat_row(table: dict) -> dict | None:
    """What the diary keeps of our seat at this table: the numbers only."""
    seat = casino._my_id(table)
    if seat is None:
        return None
    rows = table.get("standings") or ((table.get("results") or {}).get("ranked")) or []
    row = next((r for r in rows if isinstance(r, dict) and r.get("seat_id") == seat), {})
    risk, line = table.get("my_risk") or {}, table.get("my_coach_line") or {}
    settings = table.get("my_bot_settings") or {}
    log = table.get("my_tune_log") or []
    kept = {"type": "seat", "table_id": table.get("id"), "seat_id": seat, "status": table.get("status"),
            **{k: row.get(k) for k in SEAT_FIELDS},
            "level": risk.get("level"), "stop": settings.get("stop_loss_pct"), "take": settings.get("take_profit_pct"),
            "size": settings.get("trade_size_pct"), "coach": (table.get("my_coach") or {}).get("on"),
            "idle_line": line.get("idle_line"), "slots_full": line.get("slots_full"),
            "tunes": sum(1 for r in log if isinstance(r, dict) and r.get("kind") == "TUNED"),
            "checks": sum(int(r.get("repeats") or 1) for r in log if isinstance(r, dict) and r.get("kind") == "CHECKED")}
    return kept


def keep_snapshot(rows: list[dict], table: dict) -> dict | None:
    """Written only when something moved: a tick that saw nothing new costs the diary nothing."""
    now = seat_row(table)
    if now is None:
        return None
    last = next((r for r in reversed(rows) if r.get("type") == "seat" and r.get("seat_id") == now["seat_id"]), None)
    same = last is not None and all(last.get(k) == v for k, v in now.items())
    return None if same else _append(now)


def finals(rows: list[dict], tables: dict) -> list:
    """A table that ended since the last tick, once: the seat's end, under its variant."""
    done = {r.get("table_id") for r in rows if r.get("type") == "final"}
    ended = []
    for table_id, row in experiments(rows).items():
        table = tables.get(table_id)
        if not table or table.get("status") != "done" or table_id in done:
            continue
        snap = seat_row(table) or {}
        log = table.get("my_tune_log") or []
        ranked = ((table.get("results") or {}).get("ranked")) or []
        mine = next((r for r in ranked if isinstance(r, dict) and r.get("seat_id") == snap.get("seat_id")), {})
        _append({"type": "final", "table_id": table_id, "variant": row.get("variant"), "species": row.get("species"),
                 "tier": row.get("tier"), "seat_id": snap.get("seat_id"), "roi_pct": mine.get("roi_pct"),
                 "rank": mine.get("rank"), "trades": mine.get("trades"), "volume_usdc": mine.get("volume_usdc"),
                 "pnl_usdc": mine.get("pnl_usdc"), "prize_usdc": mine.get("prize_usdc"), "qualified": mine.get("qualified"),
                 "tunes": snap.get("tunes"), "checks": snap.get("checks"), "gaps": casino.check_gaps(log)})
        ended.append(table_id)
    return ended


def keep_findings(rows: list[dict], found: list[dict]) -> list[dict]:
    """A contradiction goes in the diary once per table and key; what is new is what nobody has handled."""
    seen = {(r.get("key"), r.get("table_id"), r.get("seat_id")) for r in rows if r.get("type") == "found"}
    for item in found:
        if (item.get("key"), item.get("table_id"), item.get("seat_id")) not in seen:
            _append({"type": "found", **item})
    return casino.new_keys(found, rows)


def ask_next(client, rows: list[dict], tables_open: list[dict], my_seats: list[dict] | None, running: int) -> int:
    """The next round: a new species if one is left, then one ask per free table. Returns the asks made.
    With no room at any table there is no round, and no clone waiting for one. `my_seats` is what
    names the bots already seated: unread, no bot is chosen, as a bot at two tables shares its settings."""
    if running >= casino.MAX_RUNNING or not tables_open or my_seats is None:
        return 0
    outsider, clone = _sibling("outsider"), _sibling("clone")
    body = _read(client, f"{BASE}/my-bots")
    bots = casino.for_the_casino((body or {}).get("bots") or [])
    if body is None:
        return 0
    if not any(r.get("type") == "clone_refused" for r in rows):
        offered = _read(client, "/api/v1/cloned-bots/available")
        wanted = casino.next_species(clone.available_bots(offered) if offered is not None else [], (body.get("bots") or []))
        if wanted:
            name = f"casino {wanted.get('name')}"
            try:
                made = clone.clone(wanted["source_type"], wanted["id"], name, None, True)
            except SystemExit as exc:
                _append({"type": "clone_refused", "name": name, "why": str(exc)[:300]})
                made = None
            if made:
                body = _read(client, f"{BASE}/my-bots") or body
                bots = casino.for_the_casino(body.get("bots") or [])
                print(f"  cloned {name}")
    seated = casino.seated_instances(my_seats)
    spent = {r.get("instance_id") for r in rows if r.get("type") == "spent"
             and str(r.get("at", ""))[:10] == _now().date().isoformat()}
    asked = 0
    for ask in casino.next_asks(rows, bots, tables_open, seated, spent, running):
        code = outsider.seat(str(ask["table_id"]), str(ask["instance_id"]), True, client=client)
        if code == 0:
            _append({"type": "experiment", "by": "tick", **ask})
            asked += 1
        else:
            print(f"  seat for {ask['name']} at {ask['table_id']} refused (exit {code})")
    return asked


def watched_asks(rows: list[dict], my_agents: dict) -> list:
    """Asks left on purpose to lapse: they wait for no click, and the round does not count them."""
    watch = {r.get("seat_id") for r in rows if r.get("type") == "lapse_watch"}
    return [s for s in my_agents.get("approve_all_ids") or [] if s in watch]


def cmd_lapse(table_id: str, instance_id: str) -> int:
    """One ask left to run out its 24 hours, to see what a lapsed ask reads as (round 3, line 2; the
    check agent-tournaments-lapsed-ask-does-not-read-pending)."""
    outsider = _sibling("outsider")
    client = _client(write=True)
    try:
        code = outsider.seat(table_id, instance_id, True, client=client)
    finally:
        client.close()
    said = next((r for r in reversed(outsider.load()) if r.get("type") == "outcome" and r.get("kind") == "seat"), {})
    if code == 0:
        _append({"type": "lapse_watch", "table_id": int(table_id), "seat_id": said.get("seat_id"),
                 "instance_id": instance_id})
    return code


def read_world(client) -> tuple[dict | None, list | None]:
    lobby = _read(client, f"{BASE}/lobby")
    mine = _read(client, f"{BASE}/my-seats")
    return lobby, (mine or {}).get("seats") if isinstance(mine, dict) else None


def cmd_tick(confirm: bool) -> int:
    client = _client(write=confirm)
    try:
        lobby, my_seats = read_world(client)
        if not isinstance(lobby, dict) or not isinstance(lobby.get("my_agents"), dict):
            print("the lobby or our owner block could not be read: nothing is judged on a failed read")
            print("decide: quiet")
            return 1
        rows = load()
        my_rows = [r for r in lobby["my_agents"].get("rows") or [] if isinstance(r, dict)]
        adopt(rows, my_rows)
        unstarted = start_tables(client, my_rows, confirm)
        if confirm and not unstarted and any(r.get("table_status") == "open" and r.get("status") == "seated" for r in my_rows):
            lobby, my_seats = read_world(client)
            lobby = lobby if isinstance(lobby, dict) else {"my_agents": {"rows": my_rows}}
            my_rows = [r for r in (lobby.get("my_agents") or {}).get("rows") or [] if isinstance(r, dict)]
        rows = load()
        wanted = {r.get("table_id") for r in my_rows} | {
            t for t in experiments(rows) if t not in {r.get("table_id") for r in rows if r.get("type") == "final"}}
        tables = {t: _read(client, f"{BASE}/tables/{t}") for t in sorted(x for x in wanted if x is not None)}
        tables = {k: v for k, v in tables.items() if isinstance(v, dict)}
        for table_id, table in tables.items():
            bot = experiments(rows).get(table_id, {}).get("instance_id") or (table.get("my_bot_settings") or {}).get("instance_id")
            if bot and table.get("your_trades") and any(r.get("kind") == "TUNED" for r in table.get("my_tune_log") or []):
                activity = _read(client, f"/api/v1/cloned-bots/{bot}/activity") or {}
                table["your_trades"] = casino.with_close_times(table["your_trades"], activity.get("items") or [])
        apply_variants(client, rows, tables, confirm)

        five = any(casino.FIVE_RULE in str((t.get("my_coach_line") or {}).get("line")) for t in tables.values())
        if five and not any(r.get("type") == "said_five" for r in rows):
            _append({"type": "said_five"})
        five = five or any(r.get("type") == "said_five" for r in rows)

        now = _now()
        found: list[dict] = []
        for table in tables.values():
            keep_snapshot(rows, table)
            found += casino.contradictions(table, now=now, five_rule=five)
            for row in table.get("standings") or []:
                if isinstance(row, dict) and row.get("seat_id") == casino._my_id(table) and row.get("allowance_used_up"):
                    spent = experiments(rows).get(table.get("id"), {}).get("instance_id")
                    if spent:
                        _append({"type": "spent", "instance_id": spent})
        found += casino.stale_asks(my_seats or [], lobby.get("my_agents"))
        new = keep_findings(rows, found)
        ended = finals(rows, tables)
        # An idle line, or a state that is not trading ("Paused: stop-loss hit"): the page is looked at.
        idle_now = [t for t, table in tables.items() if table.get("status") == "running" and (
            (seat_row(table) or {}).get("idle_line") or (seat_row(table) or {}).get("bot_state") not in (None, "trading"))]
        idle_seen = {r.get("table_id") for r in rows if r.get("type") == "idle_seen"}
        fresh_idle = [t for t in idle_now if t not in idle_seen]
        for table_id in fresh_idle:
            _append({"type": "idle_seen", "table_id": table_id,
                     "line": (seat_row(tables[table_id]) or {}).get("idle_line")})

        running = [t for t in tables.values() if t.get("status") == "running"]
        watched = watched_asks(load(), lobby["my_agents"])
        asks = int(lobby["my_agents"].get("asks") or 0) - len(watched)
        if confirm and not new and not asks and not unstarted:
            taken = {r.get("table_id") for r in my_rows} | {r.get("table_id") for r in load() if r.get("type") == "lapse_watch"}
            free = [t for t in lobby.get("open_tables") or [] if isinstance(t, dict) and t.get("tier") in FLASH_TIERS
                    and t.get("id") not in taken]
            live = len({r.get("table_id") for r in my_rows if r.get("table_id") not in
                        {w.get("table_id") for w in load() if w.get("type") == "lapse_watch"}})
            asks += ask_next(client, load(), free, my_seats, live)
    finally:
        client.close()

    _append({"type": "tick", "running": len(running), "asks": asks, "new": len(new)})
    write_report(load(), len(running))
    print(f"tables: {len(running)} running, {len(tables) - len(running)} other; asks {asks}; new contradictions {len(new)}")
    if watched:
        print(f"  left to lapse, never approved: seats {watched}")
    for item in new:
        print(f"  new  {item.get('key')}  table {item.get('table_id')}: {item.get('what')}")
    print(casino.decide(new, asks, unstarted, [*ended, *fresh_idle], [t.get("ends_at") for t in running], _now()))
    return 0


def cmd_audit(ids: list[int]) -> int:
    client = _client()
    try:
        tables = {t: _read(client, f"{BASE}/tables/{t}") for t in ids}
        lobby, my_seats = read_world(client)
        board = _read(client, f"{BASE}/leaderboard?window=all")
        everything = {}
        if isinstance(lobby, dict) and isinstance(board, dict):
            for row in lobby.get("tables") or []:
                if isinstance(row, dict) and row.get("status") == "done":
                    everything[row.get("id")] = _read(client, f"{BASE}/tables/{row.get('id')}")
    finally:
        client.close()
    now = _now()
    for table_id, table in tables.items():
        found = casino.contradictions(table, now=now, five_rule=True) if isinstance(table, dict) else None
        print(f"table {table_id}: {'not read' if found is None else len(found)}")
        for item in found or []:
            print(f"  {item['key']}: {item['what']}")
    for item in casino.stale_asks(my_seats or [], (lobby or {}).get("my_agents") if isinstance(lobby, dict) else None):
        print(f"my-seats: {item['what']}")
    if everything:
        for item in casino.leaderboard_vs_tables(board, [t for t in everything.values() if isinstance(t, dict)]):
            print(f"leaderboard: {item['what']}")
    return 0


def summary(rows: list[dict], running: int | None = None) -> list[str]:
    """The /lab lines: numbers first, in English."""
    finals_ = [r for r in rows if r.get("type") == "final"]
    species = {r.get("species") for r in rows if r.get("type") == "experiment"}
    last_tick = next((r for r in reversed(rows) if r.get("type") == "tick"), {})
    live = running if running is not None else last_tick.get("running", "?")
    first = f"{live} tables running, {len(finals_)} finished, {len(species)} bots tried"
    gaps = [g for r in finals_ for g in r.get("gaps") or []]
    tunes = sum(int(r.get("tunes") or 0) for r in finals_)
    checks = sum(int(r.get("checks") or 0) for r in finals_)
    second = f"Coach: {tunes} tunes, {checks} checks" + (f", a check every {sum(gaps) / len(gaps):.0f} min" if gaps else "")
    by = casino.roi_by_variant(rows)
    third = ("ROI by variant: " + ", ".join(f"{v} {x['mean_roi']:+g} % (n={x['n']})" for v, x in sorted(by.items()))
             if by else "ROI by variant: no finished seat yet")
    found = {r.get("key") for r in rows if r.get("type") == "found"}
    handled = {r.get("key") for r in rows if r.get("type") == "handled"}
    fourth = f"Contradictions: {len(found - handled)} open, {len(found & handled)} dealt with"
    return [first, second, third, fourth]


def write_report(rows: list[dict], running: int | None = None) -> Path:
    target = state_dir() / "casino" / "report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"title": "Agent Casino", "lines": summary(rows, running),
                                  "at": _now().isoformat(timespec="seconds")}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    return target


def cmd_brief() -> int:
    rows = load()
    for line in summary(rows):
        print(line)
    handled = {r.get("key"): r.get("how") for r in rows if r.get("type") == "handled"}
    for row in rows:
        if row.get("type") == "found" and row.get("key") not in handled:
            print(f"  open  {row.get('key')}  table {row.get('table_id')}: {row.get('what')}")
    return 0


def cmd_report() -> int:
    print(f"-> {write_report(load())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    tick = sub.add_parser("tick")
    tick.add_argument("--confirm", action="store_true")
    audit = sub.add_parser("audit")
    audit.add_argument("--tables", required=True)
    done = sub.add_parser("handled")
    done.add_argument("key")
    done.add_argument("--how", required=True)
    lapse = sub.add_parser("lapse")
    lapse.add_argument("--table", required=True)
    lapse.add_argument("--instance", required=True)
    sub.add_parser("brief")
    sub.add_parser("report")
    args = parser.parse_args(argv)
    if args.cmd == "tick":
        return cmd_tick(args.confirm)
    if args.cmd == "lapse":
        return cmd_lapse(args.table, args.instance)
    if args.cmd == "audit":
        return cmd_audit([int(x) for x in args.tables.split(",") if x.strip()])
    if args.cmd == "handled":
        _append({"type": "handled", "key": args.key, "how": args.how})
        return 0
    return {"brief": cmd_brief, "report": cmd_report}[args.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
