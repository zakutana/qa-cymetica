"""Play Cymetica's Agent League: enrol one player, answer what is exact arithmetic.

    python scripts/league.py puzzles            open puzzles, and which of them we would answer
    python scripts/league.py join --confirm     enrol ONE API player (refuses if we have one)
    python scripts/league.py answer --puzzle N [--confirm]
    python scripts/league.py tick [--confirm]   answer every open puzzle we can, not yet answered
    python scripts/league.py brief              our player, its answers, the prizes
    python scripts/league.py report             state/league/report.json, for the /lab page

[operator 2026-10-09] "Ucastni se" (their X post: 1,000 / 2,500 / 10,000 ET10 a puzzle, Phase 1,
no user deposits). Two writes, both declared in components.yaml with a closed body --
`agent_league.enrol` and `agent_league.answer` -- and nothing else under /agent-league is ever
written: posting a puzzle of our own (`/problems`) stays default-denied.

What is answered is decided in qa/league.py: only the families that are exact arithmetic on the
puzzle's own snapshot, with a reasoning that is the computation. The rest is left alone.

Every write is two records in state/league.jsonl (rule 9): the intent BEFORE the POST, the outcome
after -- `accepted` only for a 2xx with a body, `rejected` for their 4xx, `unknown` for a call
that may have landed (settled by reading our player, never by assuming), `not_sent` when it never
left. A call that is not `accepted` stops a tick: the next one starts from what they say.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import league  # noqa: E402
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

BASE = "/api/v1/agent-league"
PRIZE_LIMIT = 200   # rows asked of /prizes; its default is the newest 50
PLAYER_NAME = "qa-cymetica"
PLAYER_KIND = "api"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path() -> Path:
    return state_dir() / "league.jsonl"


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
    """Under the lock, the id is taken in the step that writes it (the clone diary's rule)."""
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        if "id" not in record:
            used = [int(r["id"].split("-")[1]) for r in load()
                    if isinstance(r.get("id"), str) and r["id"].startswith("LGE-")]
            record["id"] = f"LGE-{max(used, default=0) + 1:04d}"
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _outcome_of(exc: BaseException) -> str:
    """`not_sent` only when the request cannot have left; a timeout or a cut stream may
    have landed, and that is `unknown` (clone.py's reading, deep pass 2026-10-02)."""
    import httpx

    never_left = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
    if isinstance(exc, httpx.HTTPError) and not isinstance(exc, never_left):
        return "unknown"
    return "not_sent"


def outcome_of(status: int, served) -> str:
    """Rule 9: `accepted` is a 2xx with a body; `rejected` is their 4xx refusal; anything else
    (a 5xx, a 2xx with no body) may have landed and is `unknown` -- which answered_ids counts,
    so a puzzle is never answered twice on a guess (deep pass 2026-10-10, R02)."""
    if 200 <= status < 300 and isinstance(served, dict):
        return "accepted"
    if 400 <= status < 500:
        return "rejected"
    return "unknown"


def _client(write: bool = False):
    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    if write:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=60.0)


def _get(client, url: str, **params):
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        return client.get(url, params=params or None)
    finally:
        CURRENT_TIER.reset(token)


def _json(response):
    try:
        return response.json()
    except ValueError:
        return None


def my_players(client) -> list[dict]:
    response = _get(client, f"{BASE}/me")
    body = _json(response)
    if response.status_code != 200 or not isinstance(body, dict) \
            or not isinstance(body.get("players"), list):
        raise SystemExit(f"{BASE}/me answered HTTP {response.status_code}: a failed read is "
                         f"not an empty one")
    return [p for p in body["players"] if isinstance(p, dict)]


def open_puzzles(client) -> list[dict]:
    response = _get(client, f"{BASE}/puzzles", status="open")
    body = _json(response)
    if response.status_code != 200 or not isinstance(body, dict) \
            or not isinstance(body.get("puzzles"), list):
        raise SystemExit(f"{BASE}/puzzles answered HTTP {response.status_code}")
    return [p for p in body["puzzles"] if isinstance(p, dict)]


def answered_ids(client, player_id, rows: list[dict]) -> set:
    """Puzzles this player has answered: what THEY list, and what our own record says went
    through or may have (an `unknown` counts: the safe side of not knowing)."""
    done = {r.get("puzzle_id") for r in rows if r.get("type") == "outcome"
            and r.get("kind") == "answer" and r.get("outcome") in ("accepted", "unknown")}
    response = _get(client, f"{BASE}/players/{player_id}")
    body = _json(response)
    if response.status_code != 200 or not isinstance(body, dict):
        raise SystemExit(f"{BASE}/players/{player_id} answered HTTP {response.status_code}")
    done |= {r.get("puzzle_id") for r in body.get("recent") or [] if isinstance(r, dict)}
    return {p for p in done if p is not None}


def _capture(response) -> str | None:
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-league").capture(
            response.request, response, SafetyTier.MUTATE) or None
    except Exception:  # noqa: BLE001
        return None


def _send(client, kind: str, url: str, body: dict, **intent_fields) -> dict:
    """One write: the intent first, then the POST, then the outcome -- always an outcome."""
    intent = _append({"type": "intent", "kind": kind, "at": _now(), "url": url, "body": body,
                      **intent_fields})
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(url, json=body)
    except Exception as exc:  # noqa: BLE001
        _append({"id": intent["id"], "type": "outcome", "kind": kind, "at": _now(),
                 "outcome": _outcome_of(exc), "error": f"{type(exc).__name__}: {exc}"[:300],
                 **{k: v for k, v in intent_fields.items() if k == "puzzle_id"}})
        raise
    finally:
        CURRENT_TIER.reset(token)
    served = _json(response)
    outcome = {"id": intent["id"], "type": "outcome", "kind": kind, "at": _now(),
               "outcome": outcome_of(response.status_code, served),
               "http_status": response.status_code, "evidence_id": _capture(response),
               "response": served if isinstance(served, dict) else (response.text or "")[:300],
               **{k: v for k, v in intent_fields.items() if k == "puzzle_id"}}
    _append(outcome)
    return outcome


# -- commands ---------------------------------------------------------------------------

def cmd_puzzles() -> int:
    client = _client()
    try:
        players = my_players(client)
        done = answered_ids(client, players[0].get("id"), load()) if players else set()
        puzzles = open_puzzles(client)
    finally:
        client.close()
    print(f"{len(puzzles)} open puzzle(s); our players: {[p.get('id') for p in players] or 'none'}")
    for puzzle in sorted(puzzles, key=lambda p: str(p.get("closes_at"))):
        why = league.refusal(puzzle, done)
        print(f"  {puzzle.get('id'):>4}  {puzzle.get('prize_et10'):>6} ET10  "
              f"{puzzle.get('family'):<22} closes {str(puzzle.get('closes_at'))[:16]}  "
              f"{'WOULD ANSWER' if why is None else 'left alone: ' + why[:70]}")
    return 0


def cmd_join(confirm: bool) -> int:
    client = _client(write=confirm)
    try:
        players = my_players(client)
        if players:
            print(f"we already have a player: {[(p.get('id'), p.get('name')) for p in players]}. "
                  f"One player: nothing sent.")
            return 0
        body = {"name": PLAYER_NAME, "kind": PLAYER_KIND}
        if not confirm:
            print(json.dumps(body) + "\nnothing sent: join needs --confirm")
            return 0
        outcome = _send(client, "enrol", f"{BASE}/players", body)
    finally:
        client.close()
    print(f"{outcome['id']}: {outcome['outcome']} (HTTP {outcome['http_status']}) "
          f"{json.dumps(outcome['response'], ensure_ascii=False)[:300]}")
    return 0 if outcome["outcome"] == "accepted" else 1


def _answer_one(client, player_id, puzzle: dict, confirm: bool) -> dict | None:
    body = league.answer_body(puzzle, player_id)
    print(f"  puzzle {puzzle['id']} ({puzzle['family']}, {puzzle.get('prize_et10')} ET10): "
          f"{body['answer']['value']:.4f}")
    for factor in body["reasoning"]["factors"]:
        print(f"      {factor['name']}")
    if not confirm:
        return None
    outcome = _send(client, "answer", f"{BASE}/puzzles/{puzzle['id']}/answers", body,
                    puzzle_id=puzzle["id"], player_id=player_id, family=puzzle["family"])
    said = outcome["response"] if isinstance(outcome["response"], dict) else {}
    print(f"      -> {outcome['id']} {outcome['outcome']} (HTTP {outcome['http_status']}), "
          f"explained={said.get('explained')}")
    return outcome


def cmd_answer(puzzle_id: int, confirm: bool) -> int:
    client = _client(write=confirm)
    try:
        players = my_players(client)
        if not players:
            raise SystemExit("no player yet: python scripts/league.py join --confirm")
        player = players[0].get("id")
        response = _get(client, f"{BASE}/puzzles/{puzzle_id}")
        puzzle = _json(response)
        if response.status_code != 200 or not isinstance(puzzle, dict):
            raise SystemExit(f"{BASE}/puzzles/{puzzle_id} answered HTTP {response.status_code}")
        why = league.refusal(puzzle, answered_ids(client, player, load()))
        if why:
            print(f"puzzle {puzzle_id}: not answered -- {why}")
            return 1
        outcome = _answer_one(client, player, puzzle, confirm)
    finally:
        client.close()
    if outcome is None:
        print("nothing sent: answer needs --confirm")
        return 0
    return 0 if outcome["outcome"] == "accepted" and (outcome["response"] or {}).get("explained") is True else 1


def cmd_tick(confirm: bool) -> int:
    client = _client(write=confirm)
    try:
        players = my_players(client)
        if not players:
            print("no player yet: python scripts/league.py join --confirm")
            return 1
        player = players[0].get("id")
        done = answered_ids(client, player, load())
        sent = 0
        for puzzle in sorted(open_puzzles(client), key=lambda p: str(p.get("closes_at"))):
            if league.refusal(puzzle, done) is not None:
                continue
            outcome = _answer_one(client, player, puzzle, confirm)
            if outcome is None:
                continue
            sent += 1
            done.add(puzzle["id"])
            said = outcome["response"] if isinstance(outcome["response"], dict) else {}
            if outcome["outcome"] != "accepted" or said.get("explained") is not True:
                print("stopped: an answer that was not accepted and explained ends the tick")
                return 1
    finally:
        client.close()
    print(f"{sent} answer(s) sent" if confirm else "nothing sent: tick needs --confirm")
    return 0


def summary() -> dict:
    """Our player as THEY say it, our own record beside it, the prizes credited to us."""
    client = _client()
    try:
        players = my_players(client)
        if not players:
            return {"player": None, "lines": ["not enrolled yet"], "answers": 0}
        pid = players[0].get("id")
        response = _get(client, f"{BASE}/players/{pid}")
        body = _json(response) if response.status_code == 200 else None
        theirs = body if isinstance(body, dict) else None
        # The list answers the newest 50 records unless asked for more (T-0018; REPLY-0182 names
        # `?limit=200`). 200 is its ceiling (422 above) and offset/page/player_id are ignored, so
        # a full window may be cut: our totals then read as unread, never as all of it.
        response = _get(client, f"{BASE}/prizes", limit=PRIZE_LIMIT)
        body = _json(response) if response.status_code == 200 else None
        prizes = body.get("prizes") if isinstance(body, dict) else None
    finally:
        client.close()
    seen = ([p for p in prizes if isinstance(p, dict) and p.get("player_id") == pid]
            if isinstance(prizes, list) else None)
    cut = isinstance(prizes, list) and len(prizes) >= PRIZE_LIMIT
    mine = None if cut else seen
    rows = load()
    sent = sum(1 for r in rows if r.get("type") == "outcome" and r.get("kind") == "answer"
               and r.get("outcome") == "accepted")
    et10 = (sum(float(p.get("amount_et10") or 0) for p in mine if p.get("status") == "credited")
            if mine is not None else None)
    return {"player": pid, "lines": summary_lines(sent, theirs, mine, seen if cut else None),
            "answers": (theirs or {}).get("answers", sent),
            "mean_score": (theirs or {}).get("mean_score"), "et10_credited": et10,
            "prizes": len(mine) if mine is not None else None}


def summary_lines(sent: int, theirs: dict | None, mine: list | None,
                  cut: list | None = None) -> list[str]:
    """The three /lab lines. `theirs` None: their player record did not answer; `mine` None: the
    prize list did not answer. Rule 8: an unread figure is said, never printed as 0 (R03).
    `cut`: the list came back full to its 200-row ceiling, so these are only ours among it."""
    # Theirs counts SCORED answers; an answer is scored when its puzzle resolves.
    if theirs is None:
        first = f"{sent} answers sent, scored: unread (their player record did not answer)"
        second = "division: unread"
    else:
        first = f"{sent} answers sent, {theirs.get('answers', 0)} scored, mean score {theirs.get('mean_score')}"
        second = f"{theirs.get('division_name')}, {theirs.get('points')} points"
    if mine is None and cut is not None:
        capped = sum(1 for p in cut if p.get("status") == "capped")
        third = (f"ET10 credited: unread (the prize list stops at its newest {PRIZE_LIMIT} rows; "
                 f"older prizes cannot be read)"
                 + (f", {capped} capped among them (the monthly cap: not paid)" if capped else ""))
    elif mine is None:
        third = "ET10 credited: unread (the prize list did not answer)"
    else:
        et10 = sum(float(p.get("amount_et10") or 0) for p in mine if p.get("status") == "credited")
        capped = sum(1 for p in mine if p.get("status") == "capped")
        third = (f"{et10:g} ET10 credited" + (f", {len(mine)} prize(s)" if mine else "")
                 + (f", {capped} capped (the monthly cap: not paid)" if capped else ""))
    return [first, second, third]


def cmd_brief() -> int:
    said = summary()
    print(f"player {said['player']}")
    for line in said["lines"]:
        print(f"  {line}")
    return 0


def cmd_report() -> int:
    said = summary()
    target = state_dir() / "league" / "report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"title": "Agent League", "lines": said["lines"],
                                  "at": _now()}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"-> {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("puzzles")
    sub.add_parser("brief")
    sub.add_parser("report")
    join = sub.add_parser("join")
    join.add_argument("--confirm", action="store_true")
    answer = sub.add_parser("answer")
    answer.add_argument("--puzzle", type=int, required=True)
    answer.add_argument("--confirm", action="store_true")
    tick = sub.add_parser("tick")
    tick.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return {"puzzles": cmd_puzzles, "brief": cmd_brief, "report": cmd_report,
            "join": lambda: cmd_join(args.confirm),
            "answer": lambda: cmd_answer(args.puzzle, args.confirm),
            "tick": lambda: cmd_tick(args.confirm)}[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
