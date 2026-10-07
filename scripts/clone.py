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

from qa.client import (McpError, build_client, build_mcp_client,  # noqa: E402
                       install_client_guard)
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

AVAILABLE = "/api/v1/cloned-bots/available"
CLONE = "/api/v1/cloned-bots/clone"
MY_CLONES = "/api/v1/cloned-bots/my-clones"
PREFIX_FUND = "/api/v1/cloned-bots/{id}/fund"
PREFIX_RELEASE = "/api/v1/cloned-bots/{id}"
TOGGLE = "/api/v1/cloned-bots/{id}/toggle-trading"
SETTINGS = "/api/v1/cloned-bots/{id}/settings"
ACCOUNT = "/api/v1/account/me"

# What a settings PATCH may carry: the grid of plan v2's V5 -- the exits, the
# sizing, the AI's floor and which markets the bot may trade -- and nothing
# else. components.yaml declares exactly these (`closed_body`), so the
# transport refuses the rest at MUTATE whoever builds the body.
#
# Left out on purpose, each for its own reason:
#   is_trading    a START through a second door, past enable()'s floor and its
#                 rule that a stopped bot is not started again as the same
#                 experiment;
#   onchain_pct, arb_strategy_enabled, strategy_override, perpetual_markets,
#   custom_markets, catalog_watchlist
#                 where and how its money moves, not how a strategy is tuned;
#   name, avatar  nothing a verdict could tell apart.
# Bounds are theirs (update_bot_settings: "stop_loss_pct (1-20),
# take_profit_pct (5-100), max_position_pct (1-50) ... min_ai_confidence 0-1",
# max_open_positions "0 = unlimited"), checked here so a typo is not spent as
# a 422 against them.
SETTING_BOUNDS = {"stop_loss_pct": (1.0, 20.0), "take_profit_pct": (5.0, 100.0),
                  "max_position_pct": (1.0, 50.0), "min_ai_confidence": (0.0, 1.0),
                  "max_open_positions": (0, None)}
MARKET_TOGGLES = frozenset({"event_card_trading_enabled", "arena_trading_enabled",
                            "catalog_trading_enabled", "tge_trading_enabled"})
# The two market lists, switched OFF and never opened: "NONE" is what their
# page sends for no boxes. A clone that never saved them (null) trades the
# BTC/ETH 5-min epochs while the page draws both unchecked (2026-09-28), so
# a bot meant for one market has to say NONE to the others.
MARKETS_OFF = frozenset({"perpetual_markets", "custom_markets"})
SAFE_SETTINGS = frozenset(SETTING_BOUNDS) | MARKET_TOGGLES | MARKETS_OFF

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
                 "outcome": _outcome_of(exc), "error": f"{type(exc).__name__}: {exc}"})
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
                 "outcome": _outcome_of(exc),
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


def _served_delete(response) -> tuple[dict, str]:
    """DELETE's answer, read once. 204 No Content is the ordinary shape for a
    delete that worked -- `_served`'s 200-only floor would read it as a
    refusal -- so any 2xx is accepted whether or not it carries a body, and
    only reads the body when there is one to read."""
    if not (200 <= response.status_code < 300):
        return {}, "rejected"
    try:
        return unwrap(response.json()), "accepted"
    except ValueError:
        return {}, "accepted"


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


def restart_refusal(instance_id: str, rows: list[dict] | None = None,
                    samples: list[dict] | None = None,
                    planned: bool = False) -> str | None:
    """Why this clone may not be started now, or None -- from our own record
    and the sampler's rows on this machine, before anything is asked of them.

    V2 of the 2026-09-23 plan: a bot that stopped is never started again as
    the same experiment -- CLN-0007 restarted a halted Perceptron Oracle on
    2026-09-11 and its record ran on as one experiment across two starts.

    V5 narrows it and keeps its reason. REPLY-0049: one paper clone per
    species per account (a second is 409 ALREADY_CLONED), so the settings grid
    is walked in time on the species' one clone, and a clone that ran before
    may start again ONLY as a new variant -- each step accepted, in order:

        our pause  ->  a settings change after it  ->  no room running on it

    so every start measures one setting. And never after a stop that was not
    ours (`qa.lab.bot_stops`: their guard, or unexplained): that stop is a
    finding to report, not a variant to run over.

    `planned=True` is the laboratory asking BEFORE it opens a variant's room
    and sends the PATCH: the same reading, with the settings change taken as
    the next step rather than required already -- one reading for both, so
    the tick cannot open a room enable() would then refuse."""
    rows = load() if rows is None else rows
    answered = {row.get("id"): row.get("outcome") for row in rows
                if row.get("type") == "outcome"}
    # File order is the order they were sent in: every chain is appended
    # intent-first by this module, under its lock.
    # A stop that was not ours is read FIRST, from the sampler, whatever our own
    # record says about how the bot was started: an enable that came back rejected,
    # unknown or not_sent may still have started it, and the sampler saw it trade
    # and stop at a loss. This used to come after `a first start` returned, so such
    # a bot was open to a restart (deep pass 2026-10-02, R01).
    from qa import lab
    from qa import rooms

    samples = rooms.load_samples() if samples is None else samples
    every = [stop for stop in lab.bot_stops(rows, samples)
             if stop["instance"] == str(instance_id)]
    # A stop at one of the two bands WE configured (`their_trigger`: the platform
    # pauses every clone at its first stop_loss or take_profit, by design, and
    # toggle-trading resumes it -- llms.txt, Nexus NEX-0124, 2026-10-07) is not a
    # finding. Every other stop that was not ours still is.
    theirs = [stop for stop in every if stop["cause"] not in ("ours", "their_trigger")]
    if theirs:
        stop = theirs[-1]
        return (f"{instance_id} stopped by itself ({stop['cause']}, between "
                f"{stop['after']} and {stop['before']}); a stop that was not "
                f"ours is a finding, and the bot is never started again")
    if str(instance_id) in lab.trigger_stops_now(rows, samples):
        # Stopped at its band and not started since: a resume is a second window of the
        # same configuration. No pause of ours and no settings change are needed -- the
        # bot stopped by itself and the settings are the point -- but the old room must
        # have stopped, so the window never starts before its own criterion.
        running = room_running(instance_id)
        if running:
            return (f"{running} is running on {instance_id}; a resume starts only in a "
                    f"room of its own, after that one stops")
        return None
    # An enable that may have landed (unknown) counts as a start: the safe side of
    # not knowing is to treat the bot as started once already. Every other step
    # needs the platform's yes.
    steps = [row["kind"] for row in rows
             if row.get("type") == "intent"
             and row.get("kind") in ("enable", "disable", "settings", "indicators")
             and str(row.get("instance_id")) == str(instance_id)
             and (answered.get(row.get("id")) == "accepted"
                  or (row.get("kind") == "enable"
                      and answered.get(row.get("id")) == "unknown"))]
    if "enable" not in steps:
        return None      # a first start: enable()'s paper floor is the rest
    since = steps[len(steps) - 1 - steps[::-1].index("enable") + 1:]
    if "disable" not in since:
        return (f"{instance_id} was started once already, and a bot that has "
                f"been started is never started again as the same experiment: "
                f"a new variant needs our own pause first, then a settings "
                f"change after it")
    after_pause = since[since.index("disable") + 1:]
    # A change of the settings OR of an indicator's parameters is a new variant
    # (2026-10-03: indicators are the one lever on the algorithm a key reaches).
    if not ({"settings", "indicators"} & set(after_pause)) and not planned:
        return (f"{instance_id} is paused by us, but no accepted settings "
                f"or indicator change follows the pause, so a start now would "
                f"run the same settings again -- the same experiment, not a "
                f"new variant")
    running = room_running(instance_id)
    if running:
        return (f"{running} is running on {instance_id}; a variant starts only "
                f"in a room of its own, after that one stops")
    return None


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
    if enabled:
        refused = restart_refusal(instance_id)
        if refused:
            raise SystemExit(refused)
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
             # What it had made before this start, off the same row (V5): a
             # variant restarts a clone that ran before, and its verdict is
             # measured from here, not from the clone's first funding.
             "bot_profit_usdc": row.get("total_profit_usdc"),
             # Whether it was trading when we asked: a pause that finds it already
             # stopped is not what stopped it (`qa.lab.bot_stops`, R04).
             "their_is_trading": row.get("is_trading"),
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
                 "outcome": _outcome_of(exc), "error": f"{type(exc).__name__}: {exc}"})
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


def safe_settings(changes) -> dict:
    """The PATCH body, or a refusal naming the field -- before anything else."""
    if not isinstance(changes, dict) or not changes:
        raise SystemExit("a settings PATCH with nothing in it changes nothing")
    unsafe = sorted(set(changes) - SAFE_SETTINGS)
    if unsafe:
        raise SystemExit(
            f"{', '.join(unsafe)}: not a field the laboratory may PATCH. It "
            f"walks {', '.join(sorted(SAFE_SETTINGS))}; is_trading is enable()'s, "
            f"and where the money goes is not a setting we tune")
    body = {}
    for key, value in changes.items():
        if key in MARKET_TOGGLES:
            if not isinstance(value, bool):
                raise SystemExit(f"{key} is true or false, not {value!r}")
        elif key in MARKETS_OFF:
            if value != "NONE":
                raise SystemExit(f"{key} may only be switched off (\"NONE\"), "
                                 f"not {value!r}: opening a market is where "
                                 f"money goes, not a setting we tune")
        else:
            low, high = SETTING_BOUNDS[key]
            integer = key == "max_open_positions"
            if isinstance(value, bool) or not isinstance(
                    value, int if integer else (int, float)):
                raise SystemExit(f"{key} is a number, not {value!r}")
            if value < low or (high is not None and value > high):
                raise SystemExit(f"{key} {value} is outside their bounds "
                                 f"{low}-{high if high is not None else ''}")
        body[key] = value
    return body


def paper_by_our_record(instance_id: str, rows: list[dict] | None = None) -> bool:
    """Whether OUR record says we made `instance_id` as a paper clone: an
    accepted clone whose outcome carried their `is_paper: true`. A bot we did
    not clone, or one they did not confirm as paper, is not ours to tune."""
    rows = load() if rows is None else rows
    return any(row.get("type") == "outcome" and not row.get("kind")
               and row.get("outcome") == "accepted"
               and str(row.get("clone_instance_id")) == str(instance_id)
               and row.get("is_paper") is True for row in rows)


def room_running(instance_id: str) -> str | None:
    """The strategy room now RUNNING on this instance, if any. Its settings
    are what that room measures, so they hold still while it runs."""
    from qa import rooms

    stored = rooms.load()
    for room, plan in rooms.plans(stored).items():
        if any(rooms.leg_kind(leg) == "bot"
               and str(rooms.leg_ref(leg)) == str(instance_id)
               for leg in plan.get("legs") or []) \
                and rooms.status_of(stored, room) == "running":
            return room
    return None


def release(instance_id: str, confirm: bool) -> dict:
    """Delete a paper clone -- documented (`DELETE /api/v1/cloned-bots/
    {instance_id}`, 2026-09-24) but never called until this room hit the
    platform's cap of five paper bots with all five stopped: V2's rule (a
    bot that halted is never restarted as the same experiment) means a
    stopped bot can only ever be released, never reused, so without this the
    fifth slot is permanent. Refused, in order, before a client exists:

      * not confirmed;
      * our record never made this instance as a paper clone
        (`paper_by_our_record`) -- not ours to delete;
      * a room of ours is RUNNING on it (`room_running`) -- that snapshot is
        still evidence of an open investigation, closed by `rooms.py status`
        first, never destroyed by a release.

    And read from them, after a client exists:

      * their row does not say paper twice over right now (`startable`,
        enable()'s and settings()'s floor) -- deleting an instance that went
        live would destroy real state, not a practice one.
    """
    if not confirm:
        raise SystemExit("pass confirm=True to actually release the clone")
    if not paper_by_our_record(instance_id):
        raise SystemExit(
            f"{instance_id} is not a paper clone by our record (no accepted "
            f"clone of ours whose outcome said is_paper true), so it is not "
            f"ours to delete")
    running = room_running(instance_id)
    if running:
        raise SystemExit(
            f"{running} is running on {instance_id}; stop that room first "
            f"(rooms.py status) -- a release is not a pause")

    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=60.0)

    row = _instance(client, instance_id)
    if not startable(row):
        economics = row.get("execution_economics") or {}
        raise SystemExit(
            f"{instance_id} does not read as paper on both of their "
            f"statements now (is_paper={row.get('is_paper')!r}, "
            f"execution_class={economics.get('execution_class')!r}). "
            f"Nothing is deleted on an instance we cannot confirm is "
            f"practice money.")

    before = _snapshot(client)
    entry = {"type": "intent", "at": _now(), "kind": "release",
             "instance_id": instance_id, "their_is_paper": True, "before": before}
    release_id = _append_intent(entry)["id"]
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.delete(PREFIX_RELEASE.format(id=instance_id))
    except Exception as exc:  # noqa: BLE001
        _append({"id": release_id, "type": "outcome", "at": _now(),
                 "kind": "release", "outcome": _outcome_of(exc),
                 "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    evidence = _capture(response)
    served, said = _served_delete(response)
    _append({"id": release_id, "type": "outcome", "at": _now(), "kind": "release",
             "outcome": said, "http_status": response.status_code,
             "evidence_id": evidence, "response": _recorded(response, served)[:2000]})
    after = _snapshot(client)
    _append({"id": release_id, "type": "after", "kind": "release", **after})
    client.close()

    print(f"{release_id}: HTTP {response.status_code}, released {instance_id}, "
          f"outcome {said}")
    return {"id": release_id, "instance_id": instance_id, "outcome": said,
            "http_status": response.status_code}


def settings(instance_id: str, changes: dict, confirm: bool) -> dict:
    """Change a paper clone's settings -- one variant of the grid (V5).

    The paper floor was written before its first caller (B7 of the 2026-09-23
    review was dropped only because nothing sent the PATCH yet). A PATCH to
    /settings carries no `paper` -- their schema rejects unknown fields by
    name -- so the transport's required_flags has nothing to read, and the
    floor is here, three times, every one before the request:

      * the body carries only SAFE_SETTINGS (the transport holds the same
        list, `closed_body` in components.yaml);
      * OUR record made this instance as a paper clone, and no room of ours
        is running on it -- a variant is a new room, never a change under the
        one being measured;
      * THEIR row says paper twice over, is_paper and execution_class
        (`startable`, enable()'s floor), read from them now.
    """
    body = safe_settings(changes)
    if not paper_by_our_record(instance_id):
        raise SystemExit(
            f"{instance_id} is not a paper clone by our record (no accepted "
            f"clone of ours whose outcome said is_paper true), so its settings "
            f"are not ours to change")
    running = room_running(instance_id)
    if running:
        raise SystemExit(
            f"{running} is running on {instance_id}, and its settings are what "
            f"it measures: a variant is a new room, opened after this one stops")

    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=60.0)

    row = _instance(client, instance_id)
    if not startable(row):
        economics = row.get("execution_economics") or {}
        raise SystemExit(
            f"{instance_id}: they say is_paper={row.get('is_paper')!r} and "
            f"execution_class={economics.get('execution_class')!r}. Both must "
            f"say paper before its settings change -- the PATCH carries no "
            f"flag for the transport to read, so this is the floor.")

    before = _snapshot(client)
    change_id = _next_id(load())
    entry = {"id": change_id, "type": "intent", "at": _now(), "kind": "settings",
             "instance_id": instance_id, "body": body,
             "their_is_paper": row.get("is_paper"),
             "their_execution_class":
                 (row.get("execution_economics") or {}).get("execution_class"),
             "their_settings": row.get("settings"),
             "before": before}

    if not confirm:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("\nnothing sent, and nothing recorded. Add --confirm.")
        return entry

    change_id = _append_intent(entry)["id"]
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.patch(SETTINGS.format(id=instance_id), json=body)
    except Exception as exc:  # noqa: BLE001
        _append({"id": change_id, "type": "outcome", "at": _now(),
                 "kind": "settings", "outcome": _outcome_of(exc),
                 "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    served, said = _served(response)
    _append({"id": change_id, "type": "outcome", "at": _now(), "kind": "settings",
             "outcome": said, "http_status": response.status_code,
             "evidence_id": _capture(response),
             "response": _recorded(response, served)[:1200]})
    reread = "ok"
    try:
        after_row = _instance(client, instance_id)
    except SystemExit as exc:
        after_row, reread = {}, f"failed: {exc}"
    try:
        _append({"id": change_id, "type": "after", "at": _now(),
                 "kind": "settings", "reread": reread,
                 "their_is_paper": after_row.get("is_paper"),
                 "their_is_trading": after_row.get("is_trading"),
                 "their_settings": after_row.get("settings"),
                 **_snapshot(client)})
    finally:
        client.close()
    print(f"{change_id}: HTTP {response.status_code}, settings of {instance_id} "
          f"-> {json.dumps(body)}")
    return {"id": change_id, "outcome": said, **served}


# The parameters of the indicators a clone runs, and the bounds we hold them to. Skills and models
# cannot be equipped with an API key (their routes want a browser session, NEX-0121), so these are
# the one lever on a clone's algorithm a key reaches: MCP `update_bot_indicators`, "Override one
# indicator's parameters on one of YOUR clones". Names are the ones `get_bot_indicators` reports
# (2026-10-03): RSI period/overbought/oversold, MACD fast/slow/signal, Bollinger period/std_dev.
# `stochastic` is documented by the tool but its parameter names are not read yet, so it is not
# walked. The bounds are ours, wide enough to be a real change and narrow enough that a typo is
# not a setting: (low, high, integer?).
INDICATOR_PARAMS = {
    "rsi": {"period": (2, 100, True), "overbought": (50, 95, False), "oversold": (5, 50, False)},
    "macd": {"fast": (2, 50, True), "slow": (5, 120, True), "signal": (2, 50, True)},
    "ema": {"period": (2, 400, True)},
    "sma": {"period": (2, 400, True)},
    "bollinger": {"period": (5, 100, True), "std_dev": (0.5, 4.0, False)},
    "atr": {"period": (2, 100, True)},
}
GET_INDICATORS = "get_bot_indicators"
SET_INDICATORS = "update_bot_indicators"


def _inverted(name: str, params: dict) -> str | None:
    """The cross-field rule `params` breaks -- the indicator as it would RUN, not as one call spells it --
    or None. Only fields that are present and plain numbers are compared."""
    def number(key):
        value = params.get(key)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    if name == "rsi":
        high, low = number("overbought"), number("oversold")
        if high is not None and low is not None and high <= low:
            return f"rsi.overbought={high} must be above rsi.oversold={low}"
    if name == "macd":
        fast, slow = number("fast"), number("slow")
        if fast is not None and slow is not None and fast >= slow:
            return f"macd.fast={fast} must be below macd.slow={slow}"
    return None


def safe_indicator(indicator, params) -> dict:
    """The parameters to send, or a refusal naming the field -- before anything is built.

    The cross-field rules are judged here on what the call says; `indicators()` judges them again
    against what the clone runs now, because a call that names one field leaves the other as it is."""
    name = str(indicator or "").strip().lower()
    if name == "stochastic":
        raise SystemExit("stochastic: documented by the tool, but its parameter names are not read yet "
                         "(`get_bot_indicators` on a clone that runs it names them), so it is not walked")
    if name not in INDICATOR_PARAMS:
        raise SystemExit(f"{indicator!r} is not an indicator the laboratory tunes; it walks "
                         f"{', '.join(sorted(INDICATOR_PARAMS))}")
    if not isinstance(params, dict) or not params:
        raise SystemExit(f"an indicator change with nothing in it changes nothing ({name})")
    bounds = INDICATOR_PARAMS[name]
    out = {}
    for key, value in params.items():
        if key not in bounds:
            raise SystemExit(f"{name}: {key!r} is not a parameter of it; known: {', '.join(sorted(bounds))}")
        low, high, integer = bounds[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            raise SystemExit(f"{name}.{key} must be a plain number, got {value!r}")
        if integer and float(value) != int(value):
            raise SystemExit(f"{name}.{key} must be a whole number, got {value!r}")
        if not low <= value <= high:
            raise SystemExit(f"{name}.{key}={value} is outside {low}..{high}")
        out[key] = int(value) if integer else value
    broken = _inverted(name, out)
    if broken:
        raise SystemExit(broken)
    return out


def _descend(payload):
    """Their envelope is {success, tool, result:{...}} in places; the answer is inside."""
    node = payload
    for _ in range(4):
        if isinstance(node, dict) and isinstance(node.get("result"), (dict, str)):
            node = node["result"]
        else:
            break
    return node


def _effective(read, indicator: str) -> dict:
    """The effective parameters of one indicator in a `get_bot_indicators` answer, or {}."""
    node = _descend(read)
    for item in (node.get("indicators") or []) if isinstance(node, dict) else []:
        if isinstance(item, dict) and str(item.get("name") or "").lower() == indicator:
            effective = item.get("effective")
            return effective if isinstance(effective, dict) else {}
    return {}


def _refusal_they_decoded(exc: McpError) -> bool:
    """True when the McpError carries an answer THEY decoded and it was a no: a tool error (HTTP 200
    with `result.isError`) or a JSON-RPC `error` object. `McpClient.raw()` also raises McpError, with
    no payload at all, for a body that is not JSON at ANY HTTP status -- a gateway page after the
    request reached them -- and that says nothing about whether the change landed (rule 9)."""
    payload = exc.payload if isinstance(exc.payload, dict) else {}
    result = payload.get("result")
    return (isinstance(payload.get("error"), dict) and bool(payload["error"])) or (
        isinstance(result, dict) and result.get("isError") is True)


def indicators(instance_id: str, indicator: str, params: dict, confirm: bool) -> dict:
    """Change the parameters of one indicator on a paper clone -- one variant, as `settings()` is.

    The MCP tool has no `paper` argument, so the transport can hold only what the call says (exactly
    three arguments, a documented indicator, plain numbers -- qa/safety.py, own_clone_write). Floors
    here, every one before the request:

      * the parameters are inside INDICATOR_PARAMS;
      * OUR record made this instance as a paper clone, and no room of ours is running on it -- a
        variant is a new room, never a change under the one being measured;
      * THEIR row says paper twice over, is_paper and execution_class (`startable`).

    Rule 9: the intent is written before the call and every path out owes an outcome. `accepted` needs
    `success: true`; `rejected` only a refusal they decoded (a tool error, a JSON-RPC error object);
    anything else that may have landed -- a body that is not JSON, a 200 without `success: true`, a
    read timeout -- is `unknown`. The clone's indicators are read back afterwards (except after a
    transport failure) and whether they now say what we asked is RECORDED, not assumed.

    Before the intent, the cross-field rules (macd fast < slow, rsi overbought > oversold) are judged on
    the indicator as it would RUN: the fields the call names over the ones the clone runs now.
    """
    name = str(indicator or "").strip().lower()
    body = {"indicator": name, "params": safe_indicator(name, params)}
    if not paper_by_our_record(instance_id):
        raise SystemExit(
            f"{instance_id} is not a paper clone by our record (no accepted clone of ours whose outcome "
            f"said is_paper true), so its indicators are not ours to change")
    running = room_running(instance_id)
    if running:
        raise SystemExit(
            f"{running} is running on {instance_id}, and its indicators are what it measures: a variant "
            f"is a new room, opened after this one stops")

    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    ids = identities()
    rest = build_client(ids["trusted"], registry, timeout=60.0)
    mcp = build_mcp_client(ids["trusted"], registry)

    row = _instance(rest, instance_id)
    if not startable(row):
        economics = row.get("execution_economics") or {}
        raise SystemExit(
            f"{instance_id}: they say is_paper={row.get('is_paper')!r} and "
            f"execution_class={economics.get('execution_class')!r}. Both must say paper before its "
            f"indicators change -- the call carries no flag for the transport to read, so this is the floor.")

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        read_before = mcp.call(GET_INDICATORS, {"instance_id": instance_id})
    finally:
        CURRENT_TIER.reset(token)
    # A call that names one field leaves the other as the clone runs it, so the cross-field rules are
    # judged on the whole indicator as it would run (deep pass 2026-10-04, R01): `fast=40` on a clone
    # running slow=26 is a MACD that never crosses. Before the intent, so a refusal leaves no record.
    effective_before = _effective(read_before, name)
    broken = _inverted(name, {**effective_before, **body["params"]})
    if broken:
        raise SystemExit(
            f"{broken}: the change names {', '.join(sorted(body['params']))}, and {instance_id} runs "
            f"{json.dumps(effective_before)} now. Nothing was sent.")
    before = _snapshot(rest)
    change_id = _next_id(load())
    entry = {"id": change_id, "type": "intent", "at": _now(), "kind": "indicators",
             "instance_id": instance_id, "body": body,
             "their_is_paper": row.get("is_paper"),
             "their_execution_class": (row.get("execution_economics") or {}).get("execution_class"),
             "their_effective_before": effective_before, "before": before}
    if not confirm:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("\nnothing sent, and nothing recorded. Add --confirm.")
        return entry

    change_id = _append_intent(entry)["id"]
    arguments = {"instance_id": instance_id, "indicator_name": name, "params": body["params"]}
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    lost = None
    try:
        answer = mcp.call(SET_INDICATORS, arguments)
    except McpError as exc:
        if _refusal_they_decoded(exc):
            # They answered, and the answer was a refusal: a tool error is HTTP 200 with isError set.
            _append({"id": change_id, "type": "outcome", "at": _now(), "kind": "indicators",
                     "outcome": "rejected", "error": str(exc)[:600]})
            raise SystemExit(f"{change_id}: refused by them: {str(exc)[:300]}")
        # A body that is not JSON, at any HTTP status (a gateway page after the request reached
        # them): the change may have landed, so it is `unknown` (rule 9) and the read-back below
        # settles it -- never `rejected` (deep pass 2026-10-04, L04).
        answer, lost = None, f"{type(exc).__name__}: {exc}"[:600]
    except Exception as exc:  # noqa: BLE001
        _append({"id": change_id, "type": "outcome", "at": _now(), "kind": "indicators",
                 "outcome": _outcome_of(exc), "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        CURRENT_TIER.reset(token)

    # `accepted` needs `success: true`; a 200 that does not say so is read like `_served()` reads a 200
    # it cannot read: they answered and we cannot say what they made -- `unknown`, not `rejected`.
    inner = _descend(answer)
    said = ("accepted" if lost is None and isinstance(inner, dict) and inner.get("success") is True
            else "unknown")
    _append({"id": change_id, "type": "outcome", "at": _now(), "kind": "indicators", "outcome": said,
             **({"error": lost} if lost is not None else
                {"response": json.dumps(inner, ensure_ascii=False, default=str)[:1200]})})
    reread, effective = "ok", {}
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        effective = _effective(mcp.call(GET_INDICATORS, {"instance_id": instance_id}), name)
    except Exception as exc:  # noqa: BLE001
        reread = f"failed: {type(exc).__name__}: {exc}"
    finally:
        CURRENT_TIER.reset(token)
    matches = bool(effective) and all(effective.get(k) == v for k, v in body["params"].items())
    try:
        _append({"id": change_id, "type": "after", "at": _now(), "kind": "indicators", "reread": reread,
                 "their_effective": effective, "effective_matches": matches, **_snapshot(rest)})
    finally:
        rest.close()
        mcp.http.close()
    print(f"{change_id}: {said}, {name} of {instance_id} -> {json.dumps(body['params'])}; "
          f"read back {'matches' if matches else 'DOES NOT MATCH'}")
    return {"id": change_id, "outcome": said, "effective_matches": matches}


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

    algo = sub.add_parser("indicators", help="change the parameters of one indicator on a paper "
                          "clone (one variant; refused while its room runs)")
    algo.add_argument("--instance-id", required=True)
    algo.add_argument("--indicator", required=True, help=f"one of {', '.join(sorted(INDICATOR_PARAMS))}")
    algo.add_argument("--set", action="append", default=[], metavar="PARAM=NUMBER")
    algo.add_argument("--confirm", action="store_true")

    tune = sub.add_parser("settings", help="change a paper clone's settings "
                          "(one variant; refused while its room runs)")
    tune.add_argument("--instance-id", required=True)
    tune.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                      help=f"one of {', '.join(sorted(SAFE_SETTINGS))}")
    tune.add_argument("--confirm", action="store_true")

    gone = sub.add_parser("release", help="delete a stopped paper clone, to "
                          "free one of the five slots")
    gone.add_argument("--instance-id", required=True)
    gone.add_argument("--confirm", action="store_true")

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

    if args.cmd == "settings":
        changes = {}
        for pair in args.set:
            key, _, value = pair.partition("=")
            changes[key] = json.loads(value)
        settings(args.instance_id, changes, args.confirm)
        return 0

    if args.cmd == "indicators":
        changes = {}
        for pair in args.set:
            key, _, value = pair.partition("=")
            changes[key] = json.loads(value)
        indicators(args.instance_id, args.indicator, changes, args.confirm)
        return 0

    if args.cmd == "fund":
        fund(args.instance_id, args.amount, args.confirm)
        return 0

    if args.cmd == "release":
        release(args.instance_id, args.confirm)
        return 0

    clone(args.source_type, args.source_id, args.name, args.nexus,
          args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
