"""Clone one of their bots in paper mode, and keep the chain that proves it.

The order Nexus recommends is one kind of execution; a bot that trades on its
own is another, and this is that one. Same principle as `scripts/paper.py`:
CyMetica's AI decides WHAT, we execute and measure, and the record has to be
assembled forwards because it cannot be assembled backwards.

    the guidance   which recorded Nexus answer named this bot, and its job id
    the intent     source_type, source_id, the paper flags, the account before
    their answer   HTTP status, the clone id, is_paper as THEY returned it
    the account    balance and clone count, read before and after

WHY A SEPARATE FILE FROM paper.jsonl. The #87 check groups every id in that
file into intent/outcome/after chains and reads `sim_balance_usdc` off the
intent, so a clone landing there would be judged as a paper buy that debited
nothing -- an accepted row with no notional. Two records that answer different
questions do not share a log just because they share a shape.

WHY THE PAPER FLAG IS SENT TWICE. Their CloneBotRequest publishes both
`is_paper` and `paper`, and says of `paper`: *"Same as is_paper (canonical
name shared with the event-card endpoints). true = paper clone, false = live
clone, omitted = inherits the account's simulation_mode."* Omitted is the
dangerous reading and this account's simulation_mode has been False. Which of
the two the server reads is not a question we can settle from outside, so both
go, both true, and the outcome records `is_paper` as they returned it -- their
answer, not our assumption.

SAFETY, twice and independently. The flag is asserted here before a body
exists, and qa/safety.py refuses `cloned_bots.clone` at the transport without
a truthy `paper`. Neither is the other's backup: this one can be edited out by
somebody working in this file, the transport one cannot.

    python scripts/clone.py available
    python scripts/clone.py clone --source-type wta_species --source-id <id> \
        --name "..." --nexus NEX-0010 --confirm
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
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

AVAILABLE = "/api/v1/cloned-bots/available"
CLONE = "/api/v1/cloned-bots/clone"
MY_CLONES = "/api/v1/cloned-bots/my-clones"
ACCOUNT = "/api/v1/account/me"

# Their two group keys, and the enum value each maps to. The plural/singular
# mismatch is theirs: `available` returns "perpetual_agents" and
# CloneBotRequest wants "perpetual_agent".
SOURCE_TYPES = {"wta_species": "wta_species",
                "perpetual_agents": "perpetual_agent"}


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


def _capture(response, tier: SafetyTier = SafetyTier.MUTATE) -> str | None:
    """The evidence id, or None -- never a raise. paper.py's shape and reason:
    a capture that raises between the request and the record leaves an intent
    nothing can settle."""
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-clone").capture(
            response.request, response, tier) or None
    except Exception:  # noqa: BLE001
        return None


def unwrap(payload):
    """Their body, out of the `result` envelope when there is one."""
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload if isinstance(payload, dict) else {}


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


def _snapshot(client) -> dict:
    """Their side, read the same way before and after."""
    out: dict = {"at": _now()}
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        me = client.get(ACCOUNT)
        out["evidence_account"] = _capture(me, SafetyTier.SAFE)
        if me.status_code == 200:
            body = unwrap(me.json())
            sim = body.get("sim_balance") or {}
            out["sim_balance_usdc"] = sim.get("usdc")
            out["simulation_mode"] = body.get("simulation_mode")
        mine = client.get(MY_CLONES, params={"mode": "paper"})
        out["evidence_clones"] = _capture(mine, SafetyTier.SAFE)
        if mine.status_code == 200:
            body = unwrap(mine.json())
            rows = body.get("clones") or body.get("bots")
            # Absent, never zero. A failed or reshaped read that counts as 0
            # is rule 8 inverted, and here it would report a clone that did
            # not appear as a clone that did.
            if isinstance(rows, list):
                out["paper_clones"] = len(rows)
    finally:
        CURRENT_TIER.reset(token)
    return out


def _guidance(nexus_id: str | None) -> dict:
    """The recorded answer this clone acts on."""
    if not nexus_id:
        return {"id": None, "note": "no recorded guidance; this clone is "
                "ours, not Cymetica's"}
    rows = []
    src = state_dir() / "nexus.jsonl"
    if src.is_file():
        for line in src.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    answer = next((r for r in rows if r.get("id") == nexus_id
                   and r.get("type") == "answer"), None)
    question = next((r for r in rows if r.get("id") == nexus_id
                     and r.get("type") == "question"), None)
    if answer is None:
        raise SystemExit(
            f"{nexus_id} has no recorded answer; a clone naming guidance that "
            f"does not exist is worse than one marked as ours")
    return {"id": nexus_id, "job_id": answer.get("job_id"),
            "asked": (question or {}).get("question", ""),
            "advice": (answer.get("text") or "")[:2000]}


def clone(source_type: str, source_id: str, name: str | None,
          nexus_id: str | None, confirm: bool) -> dict:
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

    guidance = _guidance(nexus_id)
    body = {"source_type": source_type, "source_id": source_id,
            "paper": paper, "is_paper": paper}
    if name:
        body["custom_name"] = name

    load_dotenv()
    install_client_guard()
    ids = identities()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    client = build_client(ids["trusted"], registry, timeout=60.0)

    before = _snapshot(client)
    clone_id = _next_id(load())
    entry = {"id": clone_id, "type": "intent", "at": _now(),
             "source_type": source_type, "source_id": source_id,
             "custom_name": name, "paper": paper, "nexus": guidance,
             "before": before, "body": body}

    if not confirm:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("\nnothing sent, and nothing recorded. Add --confirm.")
        return entry

    _append(entry)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(CLONE, json=body)
    finally:
        CURRENT_TIER.reset(token)

    evidence = _capture(response)
    served = unwrap(response.json()) if response.status_code == 200 else {}
    outcome = {
        "id": clone_id, "type": "outcome", "at": _now(),
        "outcome": "accepted" if response.status_code == 200 else "rejected",
        "http_status": response.status_code,
        "clone_instance_id": served.get("id"),
        # Theirs, not ours. We asked for paper twice; this is what they say
        # they made, and it is the only reading of the flag that is evidence.
        "is_paper": served.get("is_paper"),
        "is_trading": served.get("is_trading"),
        "evidence_id": evidence,
        "response": json.dumps(served)[:2000],
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


def main() -> int:
    # Reconfigures stdout/stderr to UTF-8; it does not transcode a string,
    # and using it as `print(printable(text))` prints None. cp1250 is the
    # console default on this workspace and their bot names are not all ASCII.
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("available", help="every bot they will clone")

    one = sub.add_parser("clone", help="clone one, in paper")
    one.add_argument("--source-type", required=True)
    one.add_argument("--source-id", required=True)
    one.add_argument("--name")
    one.add_argument("--nexus", help="the NEX-000N answer that named this bot")
    one.add_argument("--confirm", action="store_true")

    sub.add_parser("list", help="what we have cloned")

    args = parser.parse_args()

    if args.cmd == "available":
        load_dotenv()
        install_client_guard()
        client = build_client(identities()["trusted"],
                              EndpointRegistry.load(), timeout=30.0)
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            response = client.get(AVAILABLE)
        finally:
            CURRENT_TIER.reset(token)
        if response.status_code != 200:
            print(f"{AVAILABLE} answered HTTP {response.status_code}")
            return 1
        for bot in available_bots(response.json()):
            print(f"  {bot['source_type']:<17} {bot['id']}  "
                  f"{bot.get('name')}")
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

    clone(args.source_type, args.source_id, args.name, args.nexus,
          args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
