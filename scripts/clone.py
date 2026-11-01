"""Clone one of their bots in paper mode, for the Agent Casino, and keep the record that proves it is paper.

WHY THE PAPER FLAG IS SENT TWICE. Their CloneBotRequest publishes both `is_paper` and `paper`, and says of
`paper`: *"Same as is_paper... omitted = inherits the account's simulation_mode."* Omitted is the dangerous
reading, so both go, both true, and the outcome records `is_paper` as they returned it: their answer, not our
assumption.

SAFETY, twice and independently. The flag is asserted here before a body exists, and qa/safety.py refuses
`cloned_bots.clone` at the transport without a truthy `paper`.

    python scripts/clone.py available
    python scripts/clone.py clone --source-type wta_species --source-id <id> --name "..." --confirm
    python scripts/clone.py list
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.paths import file_lock, state_dir  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

AVAILABLE = "/api/v1/cloned-bots/available"
CLONE = "/api/v1/cloned-bots/clone"
MY_CLONES = "/api/v1/cloned-bots/my-clones"
ACCOUNT = "/api/v1/account/me"

# Their two group keys, and the enum value each maps to. The plural/singular
# mismatch is theirs: `available` returns "perpetual_agents" and
# CloneBotRequest wants "perpetual_agent".
SOURCE_TYPES = {"wta_species": "wta_species",
                "perpetual_agents": "perpetual_agent"}


def _outcome_of(exc: BaseException) -> str:
    """What a POST that raised is, in the journal's words (rule 9).

    `not_sent` only when the request cannot have left: our own guard refused it,
    or the connection was never made. A read timeout, a reset or a cut stream
    came AFTER the request went out, so the platform may have acted on it:
    that is `unknown`, settled by looking at their side, never by assuming it did
    not happen. Every handler here wrote `not_sent` for all of them until the
    deep pass of 2026-10-02 (R02), and every reader then treated a fund or a
    start that had landed as one that never did."""
    import httpx

    never_left = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
    if isinstance(exc, httpx.HTTPError) and not isinstance(exc, never_left):
        return "unknown"
    return "not_sent"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path() -> Path:
    return state_dir() / "clones.jsonl"


def load() -> list[dict]:
    target = path()
    if not target.is_file():
        return []
    out = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _append(record: dict) -> None:
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _next_id(rows: list[dict]) -> str:
    used = [int(r["id"].split("-")[1]) for r in rows
            if isinstance(r.get("id"), str) and r["id"].startswith("CLN-")]
    return f"CLN-{max(used, default=0) + 1:04d}"


def _append_intent(record: dict) -> dict:
    """paper.py's `_append_intent`, for the same reason (C9, review of
    2026-09-23): the id is taken under the lock, in the step that writes it,
    not before a round of network reads another writer can land inside."""
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        record["id"] = _next_id(load())
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def unwrap(payload):
    """Their body, out of the `result` envelope when there is one."""
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload if isinstance(payload, dict) else {}


def clone_rows(payload):
    """Our clones, or None when the body is one we cannot read.

    `my-clones?mode=paper` answers a bare JSON list -- `[]` on this account
    before the first clone -- not an object with a `clones` key. None is the
    unreadable case and stays distinct from the empty one: an absent count
    leaves the after-snapshot unable to show the clone appeared, and a zero
    would claim it did not.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("clones", "bots", "result"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return None


def available_bots(payload) -> list[dict]:
    """Every clonable bot, carrying the source_type its group implies.

    The rows themselves have `source_type: null` -- the type lives in the key
    of the group they arrive under, and CloneBotRequest requires it. Reading
    it off the row would send `null` and blame their 422 on ourselves.
    """
    body = unwrap(payload)
    out = []
    for group, rows in body.items():
        if group not in SOURCE_TYPES or not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                out.append({**row, "source_type": SOURCE_TYPES[group]})
    return out


def startable(row) -> bool:
    """Whether BOTH of their statements say this bot simulates.

    A stricter floor than `fundable`, and deliberately: funding moves an
    amount once, starting a bot delegates spending to it indefinitely. The
    toggle-trading description says "bot will trade 100% on-chain" with no
    paper caveat, while the instance carries `onchain_pct: 100` beside
    `execution_class: "PAPER_SIMULATION"`. Those cannot both be the whole
    truth, and only the object is machine-readable, so the floor reads two of
    its fields and requires them to agree.
    """
    if not isinstance(row, dict):
        return False
    economics = row.get("execution_economics")
    if not isinstance(economics, dict):
        return False
    klass = str(economics.get("execution_class") or "")
    return row.get("is_paper") is True and "PAPER" in klass.upper()


def _snapshot(client) -> dict:
    """Their side, read the same way before and after."""
    out: dict = {"at": _now()}
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        me = client.get(ACCOUNT)
        if me.status_code == 200:
            body = unwrap(me.json())
            sim = body.get("sim_balance") or {}
            out["sim_balance_usdc"] = sim.get("usdc")
            out["simulation_mode"] = body.get("simulation_mode")
            # BOTH pockets, because funding a clone is the one operation
            # where which one moves is the whole question. Their own
            # provisional flags travel with it: balance_usdc read "0.00"
            # under balance_check_status "timeout" on 2026-09-10, and a
            # zero from a read that timed out is not a zero.
            out["balance_usdc"] = body.get("balance_usdc")
            out["balances_provisional"] = body.get("balances_provisional")
            out["balance_check_status"] = body.get("balance_check_status")
        mine = client.get(MY_CLONES, params={"mode": "paper"})
        if mine.status_code == 200:
            # Absent, never zero. A failed or reshaped read counted as 0 is
            # rule 8 inverted, and here it would report a clone that did not
            # appear as a clone that did.
            rows = clone_rows(mine.json())
            if rows is not None:
                out["paper_clones"] = len(rows)
                out["paper_clone_ids"] = [r.get("id") for r in rows
                                          if isinstance(r, dict)]
    finally:
        CURRENT_TIER.reset(token)
    return out


def clone(source_type: str, source_id: str, name: str | None, confirm: bool) -> dict:
    """One clone, recorded as intent then outcome, the account either side."""
    if source_type not in set(SOURCE_TYPES.values()):
        raise SystemExit(
            f"source_type must be one of {sorted(set(SOURCE_TYPES.values()))}, "
            f"which is what CloneBotRequest documents; got {source_type!r}")

    paper = True
    # Asserted before a body exists, because this is the file somebody edits
    # when they want a live clone, and the assertion is what they have to
    # delete on purpose.
    assert paper is True, "this script creates paper clones only"

    body = {"source_type": source_type, "source_id": source_id,
            "paper": paper, "is_paper": paper}
    if name:
        body["custom_name"] = name

    load_dotenv()
    install_client_guard()
    ids = identities()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(ids["trusted"], registry, timeout=60.0)

    before = _snapshot(client)
    clone_id = _next_id(load())
    entry = {"id": clone_id, "type": "intent", "at": _now(),
             "source_type": source_type, "source_id": source_id,
             "custom_name": name, "paper": paper,
             "before": before, "body": body}

    if not confirm:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("\nnothing sent, and nothing recorded. Add --confirm.")
        return entry

    clone_id = _append_intent(entry)["id"]
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(CLONE, json=body)
    except Exception as exc:  # noqa: BLE001
        # Rule 9 says the intent is written before the POST, which means every
        # path out of here owes an outcome. The first run of this script left
        # CLN-0001 as a bare intent because the guard refused an unlisted host
        # -- nothing was sent, and the record could not say so. An intent with
        # no outcome is the shape the journal's own `unknown` exists to avoid.
        _append({"id": clone_id, "type": "outcome", "at": _now(),
                 "outcome": _outcome_of(exc), "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    served, said = _served(response)
    outcome = {
        "id": clone_id, "type": "outcome", "at": _now(),
        "outcome": said,
        "http_status": response.status_code,
        "clone_instance_id": served.get("id"),
        # Theirs, not ours. We asked for paper twice; this is what they say
        # they made, and it is the only reading of the flag that is evidence.
        "is_paper": served.get("is_paper"),
        "is_trading": served.get("is_trading"),
        "response": _recorded(response, served)[:2000],
    }
    _append(outcome)
    _append({"id": clone_id, "type": "after", **_snapshot(client)})
    client.close()

    print(f"{clone_id}: HTTP {response.status_code}, "
          f"clone {served.get('id')}, is_paper {served.get('is_paper')!r}")
    if response.status_code == 200 and served.get("is_paper") is not True:
        print("   WARNING: they did not confirm this clone as paper. Read the "
              "record before doing anything else with it.")
    return outcome


def _served(response) -> tuple[dict, str]:
    """Their answer to a write, read once, and what it makes of the write.

    `accepted` needs a 200 whose body we could read; a 200 whose body is not
    JSON is `unknown` -- they answered, and we cannot say what they made --
    and anything else is `rejected`. Never a raise: this runs after the
    intent is on the record, and rule 9 says every path from there owes an
    outcome. Until the deep pass of 2026-09-11 clone(), fund() and enable()
    each read `response.json()` themselves, and a body that was not JSON left
    the intent bare.
    """
    if response.status_code != 200:
        return {}, "rejected"
    try:
        return unwrap(response.json()), "accepted"
    except ValueError:
        return {"unreadable_body": str(getattr(response, "text", ""))[:300]}, "unknown"


def _recorded(response, served: dict) -> str:
    """The record's `response`: what they said, whatever the status.

    `served` is empty on a refusal, on purpose -- an error body carries no
    instance id or paper flag to read. But until 2026-09-22 the record was
    `json.dumps(served)` on every path, so every refusal read `{}`: CLN-0003's
    401 became "a bare 401 with an empty body" in #89, and CLN-0017's 400
    nearly became a second report built on the same nothing.
    """
    if response.status_code == 200:
        return json.dumps(served)
    try:
        return json.dumps(response.json(), ensure_ascii=False)
    except ValueError:
        return str(getattr(response, "text", ""))


def instance(client, instance_id: str) -> dict:
    """Their current row for one clone, or a refusal. Never our own record."""
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        mine = client.get(MY_CLONES, params={"mode": "paper"})
    finally:
        CURRENT_TIER.reset(token)
    rows = clone_rows(mine.json()) if mine.status_code == 200 else None
    if rows is None:
        raise SystemExit(
            f"{MY_CLONES} answered HTTP {mine.status_code} or a body we could "
            f"not read, so this bot's mode is unknown. Nothing is started on "
            f"an unreadable answer.")
    row = next((r for r in rows if isinstance(r, dict)
                and r.get("id") == instance_id), None)
    if row is None:
        raise SystemExit(f"they do not list {instance_id} as a paper clone.")
    return row


def paper_by_our_record(instance_id: str, rows: list[dict] | None = None) -> bool:
    """Whether OUR record says we made `instance_id` as a paper clone: an
    accepted clone whose outcome carried their `is_paper: true`. A bot we did
    not clone, or one they did not confirm as paper, is not ours to tune."""
    rows = load() if rows is None else rows
    return any(row.get("type") == "outcome" and not row.get("kind")
               and row.get("outcome") == "accepted"
               and str(row.get("clone_instance_id")) == str(instance_id)
               and row.get("is_paper") is True for row in rows)


def main() -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("available", help="every bot they will clone")

    one = sub.add_parser("clone", help="clone one, in paper")
    one.add_argument("--source-type", required=True)
    one.add_argument("--source-id", required=True)
    one.add_argument("--name")
    one.add_argument("--confirm", action="store_true")

    sub.add_parser("list", help="what we have cloned")

    args = parser.parse_args()

    if args.cmd == "available":
        load_dotenv()
        install_client_guard()
        client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=30.0)
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            response = client.get(AVAILABLE)
        finally:
            CURRENT_TIER.reset(token)
        if response.status_code != 200:
            print(f"{AVAILABLE} answered HTTP {response.status_code}")
            return 1
        for bot in available_bots(response.json()):
            print(f"  {bot['source_type']:<17} {bot['id']}  {bot.get('name')}")
        client.close()
        return 0

    if args.cmd == "list":
        chains: dict[str, dict] = {}
        for row in load():
            chains.setdefault(row["id"], {})[row.get("type")] = row
        for cid, chain in sorted(chains.items()):
            out = chain.get("outcome") or {}
            intent = chain.get("intent") or {}
            print(f"  {cid}  {out.get('outcome', 'pending'):<9} "
                  f"is_paper={out.get('is_paper')!r}  "
                  f"{intent.get('custom_name') or ''}")
        return 0

    clone(args.source_type, args.source_id, args.name, args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
