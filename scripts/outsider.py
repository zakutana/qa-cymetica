"""The outsider, section 6 of the laboratory: record a stranger's run, follow its coins.

    python scripts/outsider.py record FILE.json   validate the agent's JSON, write the run
                                                  and one row per pick (prices read SAFE)
    python scripts/outsider.py track              read every coin pick whose 1/7/28-day
                                                  checkpoint is due (SAFE)
    python scripts/outsider.py report             runs, would-deposit share, score per
                                                  surface over time, coins vs BTC
    python scripts/outsider.py seat TABLE INSTANCE [--confirm]
                                                  ask for a paper seat at an Agent
                                                  Tournaments table; the owner approves it

The run comes from `docs/outsider-prompt.md`, run by `outsider.py run` as its own process outside this repository, once a
day; what it may do with its picks is `qa/outsider.py::actions`. Everything here writes to
`state/outsider.jsonl`, one row per line:

    run         OUT-NNNN: its verdict, would_deposit, a score per surface, its stumbles,
                its fetch count, and the digest that makes the same file one run
    pick        OUT-NNNN-C1 / -K1 / -B1 / -T1 (coin, card, bot, table), with the action;
                a coin carries its Gem Screener price and BTC's, each with its own moment
    checkpoint  a coin read again at 1, 7 or 28 days
    intent / outcome   a seat asked for (rule 9: the intent BEFORE the POST, the outcome
                after; `accepted` only for a 2xx carrying an approve_url)

Prices, confirmed by SAFE reads on 2026-10-11: a coin's is `price.value` (USD per token)
at `price.as_of` from `GET /api/v1/gem-screener/coins/{slug}`; BTC is not in the Gem
Screener (that route answers 404 for it), so BTC's is `BTC.price` at `price_as_of` from
`GET /api/v1/prices`, taken only when `is_real` and not `stale`.

The seat: llms.txt documents `POST /api/v1/agent-tournaments/tables/{id}/seat`
{"instance_id"} with X-API-Key, and "the seat waits until the owner approves at the
returned approve_url". Declared in components.yaml (`agent_tournaments.seat`) with a
closed body. Asked only when THEIR table reads `mode: "paper"`, open, with a free seat
and none of ours, at its tier's published buy-in, under rules whose paper mode is open
and whose paper_note says the buy-in is paper USDC -- and only for a bot that is a paper
clone of ours by our record and by theirs. The owner's click on approve_url is the
operator's: nothing here approves anything.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import crew, outsider  # noqa: E402
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

COIN = "/api/v1/gem-screener/coins/{slug}"
PRICES = "/api/v1/prices"
TOURNAMENTS = "/api/v1/agent-tournaments"
INSTANCE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
LETTER = {"coin": "C", "card": "K", "bot": "B", "tournament": "T"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path() -> Path:
    return state_dir() / "outsider.jsonl"


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


# -- the stranger's own process ------------------------------------------------------------
# 2026-10-11: spawned as a subagent from this repository, the outsider quoted CLAUDE.md's first
# line and our memory index -- a subagent inherits the session's context, so it was not a
# stranger. It runs as its own `claude -p` from a folder OUTSIDE the repository (no CLAUDE.md
# above it, a project memory of its own, empty), and only after a probe in that very process
# showed nothing of ours.
PROMPT = REPO_ROOT / "docs" / "outsider-prompt.md"
PROBE = ("Before you fetch anything, answer only this and use no tool: (1) What do you already "
         "know about Cymetica, EventTrader, Nexus, ET10, or a repository called qa-cymetica? "
         "(2) Besides this message, were you given any project instructions, CLAUDE.md, "
         "memories, an operator's decisions or file paths about it? Quote the first line of "
         "any such thing. Plain text, five lines at most.")
# What only our context could put in its mouth: CLAUDE.md's first line, the memory index's
# first entry, our Telegram handle, the founder's name and handle.
LEAKS = ("Operating rules for qa-cymetica", "Verify a workflow is live", "@EventTraderQABot",
         "Kasian", "DeepHedge", "MEMORY.md")
RUN_TIMEOUT = 1500


def home() -> Path:
    """The stranger's folder, outside the repository."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "cymetica-outsider"


# `claude` on PATH, else the newest one the desktop app keeps: one computation, shared
# with the company's workers (docs/crew-plan.md).
claude_exe = crew.claude_exe


def independent(output: str, code: int) -> tuple[bool, str]:
    """Whether a probe's answer is a stranger's: it ran (exit 0, logged in) and it quotes
    nothing only our context could have given it. Pure."""
    text = str(output or "")
    if code != 0 or "Not logged in" in text or "/login" in text:
        return False, f"the probe did not run (exit {code}): {text.strip()[:160]}"
    leaked = [marker for marker in LEAKS if marker.lower() in text.lower()]
    if leaked:
        return False, f"it quoted context of ours: {', '.join(leaked)}"
    return True, ""


proven = outsider.proven


def _claude(prompt: str, system: str | None, tools: str, timeout: int) -> tuple[str, int]:
    exe = claude_exe()
    if not exe:
        return "no claude executable on this machine", 127
    folder = home()
    folder.mkdir(parents=True, exist_ok=True)
    args = [exe, "-p", prompt, "--model", "sonnet", "--allowedTools", tools]
    if system:
        args += ["--append-system-prompt", system]
    try:
        done = subprocess.run(args, cwd=str(folder), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"timed out after {timeout} s", 124
    return (done.stdout or "") + (done.stderr or ""), done.returncode


def probe() -> dict:
    """Ask a fresh stranger process what it knows of us, before any fetch, and record it."""
    output, code = _claude(PROBE, None, "", 300)
    ok, why = independent(output, code)
    return _append({"type": "probe", "at": _now(), "ok": ok, "why": why,
                    "answer": output.strip()[:600]})


def _prompt_body() -> str:
    text = PROMPT.read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text


def run(client) -> dict:
    """One look: the stranger, in its own process, from `begin`; its JSON saved and recorded.
    Refused unless the newest probe passed."""
    if not proven(load()):
        raise SystemExit("no passing independence probe on record: `outsider.py probe` first")
    output, code = _claude("begin", _prompt_body(), "WebFetch,WebSearch", RUN_TIMEOUT)
    if code != 0:
        raise SystemExit(f"the stranger's run failed (exit {code}): {output.strip()[:300]}")
    start, end = output.find("{"), output.rfind("}")
    if start < 0 or end <= start:
        raise SystemExit(f"its answer holds no JSON object: {output.strip()[:300]}")
    target = state_dir() / "outsider" / f"run-{_now().replace(':', '')}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output[start:end + 1], encoding="utf-8")
    return record(target, client)


def _next(rows: list[dict], prefix: str) -> str:
    used = [int(r["id"].split("-")[1]) for r in rows
            if isinstance(r.get("id"), str) and re.match(rf"^{prefix}-\d+$", r["id"])]
    return f"{prefix}-{max(used, default=0) + 1:04d}"


def _write(lines: list[dict]) -> None:
    target = path()
    with open(target, "a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def _append(record: dict, prefix: str | None = None) -> dict:
    """One row. Under the lock the id is taken in the step that writes it."""
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        if prefix and "id" not in record:
            record["id"] = _next(load(), prefix)
        _write([record])
    return record


def _client(write: bool = False, trusted: bool = False):
    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    if write:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    ids = identities()
    identity = ids["trusted"] if trusted and ids["trusted"].present else ids["anon"]
    return build_client(identity, registry, timeout=60.0)


def _get(client, url: str, **params):
    """A SAFE read: the response, or None when the request itself failed."""
    import httpx

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        return client.get(url, params=params or None)
    except httpx.HTTPError as exc:
        print(f"  {url}: {type(exc).__name__}: a failed read, not an empty one")
        return None
    finally:
        CURRENT_TIER.reset(token)


def _json(response):
    if response is None:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _btc(client) -> tuple[dict | None, str | None]:
    response = _get(client, PRICES)
    if response is None or response.status_code != 200:
        return None, f"{PRICES} answered {getattr(response, 'status_code', 'nothing')}"
    return outsider.btc_price(_json(response))


def _coin(client, slug: str) -> tuple[dict | None, str | None, dict | None, bool]:
    """(price, why unpriced, their body, settled). `settled` is False for a read that
    failed or a status we do not understand: a moment that may be read again."""
    response = _get(client, COIN.format(slug=slug))
    if response is None:
        return None, "the read failed", None, False
    body = _json(response)
    if response.status_code == 404:
        detail = body.get("detail") if isinstance(body, dict) else None
        return None, f"HTTP 404: {str(detail or 'not in the snapshot')[:160]}", body, True
    if response.status_code != 200 or not isinstance(body, dict):
        return None, f"HTTP {response.status_code}", None, False
    price, why = outsider.coin_price(body)
    return price, why, body, True


# -- record ---------------------------------------------------------------------------

def parse(text: str):
    """The agent's answer: one JSON object, alone or inside a ```json fence."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    try:
        return json.loads(fenced.group(1) if fenced else text)
    except json.JSONDecodeError as exc:
        raise outsider.OutsiderError([f"the run is not one JSON object: {exc}"]) from None


def record(source, client) -> dict:
    """Validate the run in `source`, read its coins' prices and BTC's (once), and write
    the run row and one row per pick. Refused runs write nothing and read nothing."""
    source = Path(source)
    run = outsider.validate(parse(source.read_text(encoding="utf-8-sig")))
    digest = outsider.digest(run)
    known = next((r for r in load() if r.get("type") == "run"
                  and r.get("digest") == digest), None)
    if known:
        return {"already": known["id"], "run": known, "picks": []}

    at = _now()
    acts = outsider.actions(run)
    by_kind: dict[str, list[dict]] = {}
    for act in acts:
        by_kind.setdefault(act["kind"], []).append(act)

    stumbles = list(run["stumbles"])
    picks: list[dict] = []
    coins = run["picks"]["coins"]
    btc, btc_why = _btc(client) if coins else (None, None)
    for coin, act in zip(coins, by_kind.get("coin", [])):
        price, why, body, _settled = _coin(client, coin["slug"])
        if why and why.startswith("HTTP 404"):
            stumbles.append({"where": COIN.format(slug=coin["slug"]),
                             "what": f"its coin pick does not resolve: {why}"[:600],
                             "by": "record"})
        body = body if isinstance(body, dict) else {}
        picks.append({"type": "pick", "kind": "coin", "at": at, "asked": coin["slug"],
                      "slug": body.get("slug") or coin["slug"], "name": body.get("name"),
                      "symbol": body.get("symbol"), "price": price, "btc": btc,
                      "unpriced": why or (None if price is None or btc else btc_why),
                      "why": coin["why"], "action": act})
    for card, act in zip(run["picks"]["cards"], by_kind.get("card", [])):
        picks.append({"type": "pick", "kind": "card", "at": at, "card_id": card["id"],
                      "hold_days": card["hold_days"], "why": card["why"], "action": act})
    for bot, act in zip(run["picks"]["bots"], by_kind.get("bot", [])):
        picks.append({"type": "pick", "kind": "bot", "at": at, "species": bot["species"],
                      "stop_loss_pct": bot["stop_loss_pct"],
                      "take_profit_pct": bot["take_profit_pct"], "why": bot["why"],
                      "action": act})
    for act in by_kind.get("tournament", []):
        picks.append({"type": "pick", "kind": "tournament", "at": at,
                      "table_id": act["table_id"], "why": act["why"], "action": act})

    run_row = {"type": "run", "at": at, "verdict": run["verdict"],
               "would_deposit": run["would_deposit"], "scores": run["scores"],
               "surfaces": run["surfaces"], "stumbles": stumbles, "fetches": run["fetches"],
               "tournament": run["picks"]["tournament"],
               "picks": {k: len(run["picks"][k]) for k in ("coins", "cards", "bots")},
               "digest": digest, "source": source.name}
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        rows = load()
        known = next((r for r in rows if r.get("type") == "run"
                      and r.get("digest") == digest), None)
        if known:
            return {"already": known["id"], "run": known, "picks": []}
        run_row["id"] = _next(rows, "OUT")
        count: dict[str, int] = {}
        for pick in picks:
            count[pick["kind"]] = count.get(pick["kind"], 0) + 1
            pick["id"] = f"{run_row['id']}-{LETTER[pick['kind']]}{count[pick['kind']]}"
            pick["run"] = run_row["id"]
        _write([run_row, *picks])
    return {"run": run_row, "picks": picks}


def cmd_record(source: str) -> int:
    client = None
    try:
        # Validated before any client exists: a refused run reads nothing.
        outsider.validate(parse(Path(source).read_text(encoding="utf-8-sig")))
        client = _client()
        written = record(source, client)
    except outsider.OutsiderError as exc:
        print(f"not recorded -- {exc}")
        return 2
    finally:
        if client is not None:
            client.close()
    if written.get("already"):
        print(f"already recorded as {written['already']}: nothing written")
        return 0
    run = written["run"]
    print(f"{run['id']}: would deposit {run['would_deposit']}, {run['fetches']} fetches")
    print(f"  {run['verdict']}")
    for name, score in run["scores"].items():
        print(f"  {name:<18} {'-' if score is None else score}")
    for pick in written["picks"]:
        extra = ""
        if pick["kind"] == "coin":
            extra = (f" {pick['price']['value']} USD at {pick['price']['as_of']}"
                     if pick["price"] else f" unpriced: {pick['unpriced']}")
        print(f"  {pick['id']} {pick['kind']}{extra}")
    print("actions:")
    print(json.dumps([p["action"] for p in written["picks"]], ensure_ascii=False, indent=1))
    return 0


# -- track ----------------------------------------------------------------------------

def track(client, now: datetime | None = None) -> list[dict]:
    """A checkpoint row for every coin pick whose 1/7/28-day read is due now. A read that
    failed writes nothing (the next tick inside the slack reads it again); their 404 is
    an answer and is written, unpriced."""
    moment = now or datetime.now(timezone.utc)
    rows = load()
    todo = outsider.due([r for r in rows if r.get("type") == "pick"],
                        [r for r in rows if r.get("type") == "checkpoint"], moment)
    if not todo:
        return []
    btc, btc_why = _btc(client)
    if btc is None:
        print(f"  BTC unread ({btc_why}): no checkpoint written, the next tick asks again")
        return []
    written = []
    for pick, horizon in todo:
        price, why, _body, settled = _coin(client, pick["slug"])
        if not settled:
            print(f"  {pick['id']} {horizon}: {why}; asked again next tick")
            continue
        row = {"type": "checkpoint", "pick": pick["id"], "run": pick.get("run"),
               "slug": pick["slug"], "horizon": horizon,
               "at": moment.isoformat(timespec="seconds"), "price": price, "btc": btc,
               "unpriced": why}
        written.append(_append(row))
    return written


def cmd_track() -> int:
    client = _client()
    try:
        written = track(client)
    finally:
        client.close()
    for row in written:
        said = (f"{row['price']['value']} USD" if row["price"]
                else f"unpriced: {row['unpriced']}")
        print(f"  {row['pick']} {row['slug']} {row['horizon']}: {said}")
    print(f"{len(written)} checkpoint(s) written")
    return 0


# -- report ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def cmd_report() -> int:
    rows = load()
    runs = [r for r in rows if r.get("type") == "run"]
    if not runs:
        print("no outsider run recorded yet")
        return 0
    yes = sum(1 for r in runs if r.get("would_deposit") is True)
    print(f"{len(runs)} run(s), would deposit {yes}/{len(runs)} "
          f"({yes / len(runs) * 100:.0f} %), last {runs[-1].get('at', '')[:10]}")
    print("score per surface (mean; oldest -> newest, last 10):")
    for name, said in outsider.surface_scores(runs).items():
        series = " ".join("-" if s is None else f"{s:g}" for _id, s in said["series"][-10:])
        print(f"  {name:<18} {'-' if said['mean'] is None else said['mean']:>5}  {series}")
    picks = [r for r in rows if r.get("type") == "pick"]
    returns = outsider.coin_returns(picks, [r for r in rows if r.get("type") == "checkpoint"],
                                    datetime.now(timezone.utc))
    if returns:
        print("coins since the pick, vs BTC (percentage points):")
        for days in outsider.HORIZONS_DAYS:
            name = outsider.label(days)
            read = [v["returns"][name] for v in returns.values() if v["returns"][name]]
            print(f"  {name:>3}: n {len(read)}, coin {_mean([r['coin_pct'] for r in read])} %, "
                  f"BTC {_mean([r['btc_pct'] for r in read])} %, "
                  f"lead {_mean([r['vs_btc_pts'] for r in read])} pts")
        for pid, said in returns.items():
            cells = []
            for days in outsider.HORIZONS_DAYS:
                name = outsider.label(days)
                got = said["returns"][name]
                cells.append(f"{name} {got['vs_btc_pts']:+.1f}" if got
                             else f"{name} {said['status'][name]}")
            print(f"  {pid} {said['slug']}: " + ", ".join(cells))
    other = [p for p in picks if p.get("kind") in ("card", "bot", "tournament")]
    if other:
        counted = {k: sum(1 for p in other if p["kind"] == k) for k in ("card", "bot",
                                                                         "tournament")}
        print(f"other picks: {counted['card']} card(s), {counted['bot']} bot(s), "
              f"{counted['tournament']} table wish(es) -- measured as laboratory rooms")
    return 0


# -- seat -----------------------------------------------------------------------------

def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"outsider_{name}", REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outcome_of(status: int, served) -> str:
    """Rule 9: `accepted` is a 2xx carrying the approve_url the owner needs; `rejected`
    their 4xx; anything else may have landed and is `unknown`, which our record counts
    as a seat asked for until their table says otherwise."""
    if 200 <= status < 300 and isinstance(served, dict) \
            and isinstance(served.get("approve_url"), str) and served["approve_url"]:
        return "accepted"
    if 400 <= status < 500:
        return "rejected"
    return "unknown"


def _outcome_of(exc: BaseException) -> str:
    """`not_sent` only when the request cannot have left (clone.py's reading)."""
    import httpx

    never_left = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
    if isinstance(exc, httpx.HTTPError) and not isinstance(exc, never_left):
        return "unknown"
    return "not_sent"


def _capture(response) -> str | None:
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-outsider").capture(
            response.request, response, SafetyTier.MUTATE) or None
    except Exception:  # noqa: BLE001
        return None


def asked_before(table_id: str, rows: list[dict]) -> str | None:
    """A seat intent of ours at this table that went through or may have: one with no
    outcome, or with `accepted` / `unknown`. One seat per owner per table."""
    outcomes = {r.get("id"): r for r in rows if r.get("type") == "outcome"
                and r.get("kind") == "seat"}
    for intent in rows:
        if intent.get("type") != "intent" or intent.get("kind") != "seat" \
                or str(intent.get("table_id")) != str(table_id):
            continue
        said = outcomes.get(intent.get("id"))
        if said is None or said.get("outcome") in ("accepted", "unknown"):
            return intent.get("id")
    return None


def _send(client, url: str, body: dict, **fields) -> dict:
    intent = _append({"type": "intent", "kind": "seat", "at": _now(), "url": url,
                      "body": body, **fields}, prefix="SEAT")
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(url, json=body)
    except Exception as exc:  # noqa: BLE001
        _append({"id": intent["id"], "type": "outcome", "kind": "seat", "at": _now(),
                 "table_id": fields.get("table_id"), "outcome": _outcome_of(exc),
                 "error": f"{type(exc).__name__}: {exc}"[:300]})
        raise
    finally:
        CURRENT_TIER.reset(token)
    served = _json(response)
    served = served if isinstance(served, dict) else None
    outcome = {"id": intent["id"], "type": "outcome", "kind": "seat", "at": _now(),
               "table_id": fields.get("table_id"),
               "outcome": outcome_of(response.status_code, served),
               "http_status": response.status_code, "evidence_id": _capture(response),
               "approve_url": (served or {}).get("approve_url"),
               "seat_id": (served or {}).get("seat_id"),
               "response": served if served is not None else (response.text or "")[:300]}
    return _append(outcome)


def seat(table_id: str, instance_id: str, confirm: bool, client=None) -> int:
    """Ask for a seat at a paper table for one of our paper clones. 0 = asked (or, dry,
    would be asked); anything else = refused, with the reason printed. A dry run makes
    its SAFE reads and writes nothing."""
    table_id, instance_id = str(table_id), str(instance_id)
    if not outsider.TABLE.match(table_id) or not INSTANCE.match(instance_id):
        print(f"refused: {table_id!r} / {instance_id!r} is not a table id and a bot id")
        return 2
    earlier = asked_before(table_id, load())
    if earlier:
        print(f"refused: {earlier} already asked for a seat at table {table_id} (it went "
              f"through or may have); one seat per owner per table")
        return 1
    clone = _sibling("clone")
    if not clone.paper_by_our_record(instance_id):
        print(f"refused: {instance_id} is not a paper clone of ours by our record "
              f"(state/clones.jsonl); only our own paper bots are seated")
        return 1
    own = client is None
    client = client if client is not None else _client(write=confirm, trusted=True)
    try:
        rules = _get(client, f"{TOURNAMENTS}/rules")
        table = _get(client, f"{TOURNAMENTS}/tables/{table_id}")
        rules_body = _json(rules) if rules is not None and rules.status_code == 200 else None
        table_body = _json(table) if table is not None and table.status_code == 200 else None
        why = outsider.seat_refusal(table_id, table_body, rules_body)
        if why:
            print(f"refused: {why}")
            return 1
        try:
            theirs = clone._instance(client, instance_id)
        except SystemExit as exc:
            print(f"refused: {exc}")
            return 1
        if not clone.startable(theirs):
            economics = theirs.get("execution_economics") or {}
            print(f"refused: they say {instance_id} is_paper={theirs.get('is_paper')!r}, "
                  f"execution_class={economics.get('execution_class')!r}; both must say paper")
            return 1
        body = {"instance_id": instance_id}
        url = f"{TOURNAMENTS}/tables/{table_id}/seat"
        print(f"table {table_id}: {table_body.get('tier')} paper, buy-in "
              f"{table_body.get('buyin_usdc')} paper USDC, {table_body.get('seats_free')} "
              f"seats free\n  POST {url} {json.dumps(body)}")
        if not confirm:
            print("nothing sent: seat needs --confirm")
            return 0
        outcome = _send(client, url, body, table_id=table_id, instance_id=instance_id,
                        table={k: table_body.get(k) for k in ("mode", "tier", "status",
                                                               "buyin_usdc", "capital_usdc")})
    finally:
        if own:
            client.close()
    print(f"{outcome['id']}: {outcome['outcome']} (HTTP {outcome['http_status']})")
    if outcome.get("approve_url"):
        print(f"the owner approves the seat here: {outcome['approve_url']}")
    return 0 if outcome["outcome"] == "accepted" else 1


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("file")
    sub.add_parser("track")
    sub.add_parser("report")
    sit = sub.add_parser("seat")
    sit.add_argument("table_id")
    sit.add_argument("instance_id")
    sit.add_argument("--confirm", action="store_true")
    sub.add_parser("probe", help="is a fresh `claude -p` outside the repository a stranger?")
    sub.add_parser("run", help="one look by the stranger, recorded (needs a passing probe)")
    args = parser.parse_args(argv)
    if args.cmd == "probe":
        said = probe()
        print(f"probe: {'a stranger' if said['ok'] else 'NOT a stranger -- ' + said['why']}")
        return 0 if said["ok"] else 1
    if args.cmd == "run":
        client = _client()
        try:
            written = run(client)
        except outsider.OutsiderError as exc:
            print(f"not recorded -- {exc}")
            return 2
        finally:
            client.close()
        if written.get("already"):
            print(f"already recorded as {written['already']}")
            return 0
        print(f"{written['run']['id']}: would deposit {written['run']['would_deposit']}, "
              f"{len(written['picks'])} pick(s) -- next: python scripts/lab.py outsider-act "
              f"{written['run']['id']}")
        return 0
    if args.cmd == "record":
        return cmd_record(args.file)
    if args.cmd == "track":
        return cmd_track()
    if args.cmd == "report":
        return cmd_report()
    return seat(args.table_id, args.instance_id, args.confirm)


if __name__ == "__main__":
    sys.exit(main())
