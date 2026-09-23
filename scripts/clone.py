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
PREFIX_FUND = "/api/v1/cloned-bots/{id}/fund"
TOGGLE = "/api/v1/cloned-bots/{id}/toggle-trading"
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


def fundable(row) -> bool:
    """Whether THEY currently say this clone is paper.

    The floor for funding, and it has to live here: FundBotRequest carries
    one property, `amount`, so there is no flag for the transport to read.
    What makes the transfer harmless is a property of the instance.

    Asked of them rather than of our own record. A bot that went live after
    we wrote clones.jsonl would still read as paper there, which is the same
    mistake as judging a fix by a trade placed before it shipped. And absent
    is not permission: on the money side an answer we could not read is a
    refusal, not a default.
    """
    return isinstance(row, dict) and row.get("is_paper") is True


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
        out["evidence_account"] = _capture(me, SafetyTier.SAFE)
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
        out["evidence_clones"] = _capture(mine, SafetyTier.SAFE)
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


def _guidance(nexus_id: str | None) -> dict:
    """The recorded answer this clone acts on."""
    if not nexus_id:
        return {"id": None, "note": "no recorded guidance; this clone is "
                "ours, not Cymetica's"}
    rows = []
    # Both of his doors: the laboratory acts on an answer from the sync lane
    # (nexus_shallow.jsonl) as it does on a deep one, and a clone it launches
    # from one must still name it.
    for src in (state_dir() / "nexus.jsonl", state_dir() / "nexus_shallow.jsonl"):
        if not src.is_file():
            continue
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
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
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
                 "outcome": "not_sent", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    evidence = _capture(response)
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
        "evidence_id": evidence,
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


def fund(instance_id: str, amount: float, confirm: bool) -> dict:
    """Move practice money into a paper clone, and record which pocket moved.

    A clone arrives with a practice balance of 0.00, so it cannot trade until
    it is funded -- their UI card shows exactly that beside a Fund button.
    """
    if amount <= 0:
        raise SystemExit("a transfer needs a positive amount")

    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=60.0)

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        mine = client.get(MY_CLONES, params={"mode": "paper"})
    finally:
        CURRENT_TIER.reset(token)
    rows = clone_rows(mine.json()) if mine.status_code == 200 else None
    if rows is None:
        raise SystemExit(
            f"{MY_CLONES} answered HTTP {mine.status_code} or a body we could "
            f"not read, so whether this bot is paper is unknown. Nothing is "
            f"funded on an unreadable answer.")
    target = next((r for r in rows if isinstance(r, dict)
                   and r.get("id") == instance_id), None)
    if not fundable(target):
        raise SystemExit(
            f"{instance_id} is not listed as a paper clone by them "
            f"(is_paper={None if target is None else target.get('is_paper')!r}). "
            f"FundBotRequest carries no paper flag, so this is the only floor "
            f"there is and it does not bend.")

    before = _snapshot(client)
    fund_id = _next_id(load())
    body = {"amount": float(amount)}
    entry = {"id": fund_id, "type": "intent", "at": _now(), "kind": "fund",
             "instance_id": instance_id, "amount": float(amount),
             "their_is_paper": True, "before": before, "body": body}

    if not confirm:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("\nnothing sent, and nothing recorded. Add --confirm.")
        return entry

    fund_id = _append_intent(entry)["id"]
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(PREFIX_FUND.format(id=instance_id), json=body)
    except Exception as exc:  # noqa: BLE001
        _append({"id": fund_id, "type": "outcome", "at": _now(), "kind": "fund",
                 "outcome": "not_sent",
                 "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    evidence = _capture(response)
    served, said = _served(response)
    _append({"id": fund_id, "type": "outcome", "at": _now(), "kind": "fund",
             "outcome": said,
             "http_status": response.status_code, "evidence_id": evidence,
             "response": _recorded(response, served)[:2000]})
    after = _snapshot(client)
    _append({"id": fund_id, "type": "after", **after})
    client.close()

    def _delta(key):
        try:
            return round(float(after.get(key)) - float(before.get(key)), 6)
        except (TypeError, ValueError):
            return None

    print(f"{fund_id}: HTTP {response.status_code}, funded {amount} to "
          f"{instance_id}")
    print(f"   practice balance moved {_delta('sim_balance_usdc')}")
    print(f"   real balance moved     {_delta('balance_usdc')}  "
          f"(their read was {before.get('balance_check_status')!r})")
    return served


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


def _instance(client, instance_id: str) -> dict:
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


def enable(instance_id: str, confirm: bool, enabled: bool = True) -> dict:
    """Start a paper bot trading, and record what they said it was first.

    The one call here that keeps spending after we stop watching, so the
    floor reads both of their statements about the instance and refuses
    unless they agree. See `startable`.

    `enabled=False` pauses it -- the laboratory's close of a bot room
    (2026-09-22). Stopping a bot spends nothing, so it needs only that they
    list it as ours; it keeps the same intent/outcome/after chain, as kind
    "disable". The practice money stays in the clone.
    """
    kind = "enable" if enabled else "disable"
    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=60.0)

    row = _instance(client, instance_id)
    if enabled and not startable(row):
        economics = row.get("execution_economics") or {}
        raise SystemExit(
            f"{instance_id}: they say is_paper="
            f"{row.get('is_paper')!r} and execution_class="
            f"{economics.get('execution_class')!r}. Both must say paper "
            f"before a bot is told to trade on its own -- toggle-trading "
            f"carries no flag for the transport to read, so this is the only "
            f"floor there is.")

    before = _snapshot(client)
    run_id = _next_id(load())
    entry = {"id": run_id, "type": "intent", "at": _now(), "kind": kind,
             "instance_id": instance_id,
             "their_is_paper": row.get("is_paper"),
             "their_execution_class":
                 (row.get("execution_economics") or {}).get("execution_class"),
             "bot_balance_usdc": row.get("current_balance_usdc"),
             "before": before,
             "sizing": "ours -- Nexus answered QUERY_RESTRICTED to the sizing "
                       "question (NEX-0013, NEX-0014), so no recorded guidance "
                       "stands behind this amount"}

    if not confirm:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("\nnothing sent, and nothing recorded. Add --confirm.")
        return entry

    run_id = _append_intent(entry)["id"]
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(TOGGLE.format(id=instance_id),
                               params={"enabled": "true" if enabled else "false"})
    except Exception as exc:  # noqa: BLE001
        _append({"id": run_id, "type": "outcome", "at": _now(), "kind": kind,
                 "outcome": "not_sent", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    served, said = _served(response)
    _append({"id": run_id, "type": "outcome", "at": _now(), "kind": kind,
             "outcome": said,
             "http_status": response.status_code,
             "evidence_id": _capture(response),
             "response": _recorded(response, served)[:1200]})
    # The bot may be running by now, so a re-read that fails must not end
    # the record: until the deep pass of 2026-09-11 it raised "Nothing is
    # started on an unreadable answer" about a bot just started, and the
    # after row and client.close() were skipped.
    reread = "ok"
    try:
        after_row = _instance(client, instance_id)
    except SystemExit as exc:
        after_row, reread = {}, f"failed: {exc}"
    try:
        _append({"id": run_id, "type": "after", "at": _now(), "kind": kind,
                 "reread": reread,
                 "their_is_trading": after_row.get("is_trading"),
                 "their_is_paper": after_row.get("is_paper"),
                 "bot_balance_usdc": after_row.get("current_balance_usdc"),
                 **_snapshot(client)})
    finally:
        client.close()
    if reread != "ok":
        print(f"   WARNING: switched {'on' if enabled else 'off'}, then {reread}. "
              f"Read their my-clones "
              f"before doing anything else with it.")

    print(f"{run_id}: HTTP {response.status_code}, "
          f"is_trading now {after_row.get('is_trading')!r}, "
          f"is_paper {after_row.get('is_paper')!r}, "
          f"bot balance {after_row.get('current_balance_usdc')}")
    return served


def watch(instance_id: str, every: int, until: int) -> int:
    """Sample our bot on a timer -- now one round of the console's sampler.

    A bot that is enabled and then read once tells you whether it was
    enabled; whether it TRADES needs a series. This wrote that series into
    clones.jsonl until 2026-09-11, and that file is committed: every ten
    minutes of a night's sampling dirtied the tree, and a run started in that
    window could not reach level V. It goes through scripts/sampler.py now,
    into the gitignored state/samples.jsonl beside the console's own samples
    -- one series, one writer -- so it follows every bot our records say we
    cloned, of which `instance_id` must be one. SAFE, GET only.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sampler_for_watch", REPO_ROOT / "scripts" / "sampler.py")
    sampler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sampler)
    if instance_id not in sampler.follow()["bots"]:
        raise SystemExit(f"{instance_id} is not a bot our records say we cloned; "
                         f"the sampler follows only those.")
    rounds = sampler.run(None, float(every), until=float(until))
    print(f"{rounds} round(s) written to state/samples.jsonl")
    return 0


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

    money = sub.add_parser("fund", help="move practice money into a paper clone")
    money.add_argument("--instance-id", required=True)
    money.add_argument("--amount", type=float, required=True)
    money.add_argument("--confirm", action="store_true")

    go = sub.add_parser("enable", help="start a paper bot trading")
    go.add_argument("--instance-id", required=True)
    go.add_argument("--confirm", action="store_true")

    eye = sub.add_parser("watch", help="sample a running bot on a timer")
    eye.add_argument("--instance-id", required=True)
    eye.add_argument("--every", type=int, default=600)
    eye.add_argument("--until", type=int, default=28800)

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

    if args.cmd == "watch":
        return watch(args.instance_id, args.every, args.until)

    if args.cmd == "enable":
        enable(args.instance_id, args.confirm)
        return 0

    if args.cmd == "fund":
        fund(args.instance_id, args.amount, args.confirm)
        return 0

    clone(args.source_type, args.source_id, args.name, args.nexus,
          args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
