"""Place one paper trade on an event card, and keep the chain that proves it.

The operator's question when this was designed: when the paper balance goes
from 100,000 to 1,000,000, will we be able to prove it, and does the proof come
from our own records or from their transaction history? Both, and neither is
sufficient alone. Their history shows the money moved and cannot show whose
decision it was. Ours shows the decision and could have been typed by anyone.
What makes either believable is the third thing: the request and response
records, addressed by the hash of their own bytes.

So every trade here is written as a chain, and each link names the one before
it:

    the guidance   which question was asked, their job id for it, the words
    the order      the card, the notional, `paper`, and the guidance it acts on
    their answer   HTTP status, their position id, the evidence id
    the account    their balance and position count, read before and after

The reason it is built before the first order rather than after the first
million: a chain cannot be assembled backwards. There is no way to prove in
December whose idea a trade in September was.

    python scripts/paper.py buy --card <id> --usdc 1 --nexus NEX-0002
    python scripts/paper.py buy --card <id> --usdc 1 --confirm
    python scripts/paper.py positions
    python scripts/paper.py book
    python scripts/paper.py proof

THE BOOK IS THE CONSTRAINT. Their paper balance does not move when a position
opens -- finding #87 -- so nothing on their side stops an agent deploying
500,000 against a 100,000 bankroll. A campaign that cannot run out of money
cannot be measured, because a strategy that would have lost everything looks
exactly like one that doubled. `book()` computes what is left from their own
position rows and `buy` refuses an order it cannot pay for.

WHOSE DECISION IT IS. CLAUDE.md's tagged decision of 2026-09-10: Cymetica's
own AI supplies the guidance, we test and execute. `--nexus NEX-000N` names the
recorded answer an order acts on, and the chain carries it. An order placed
without one is ours, is marked so, and should be rare enough to notice.

SAFETY. `paper` is sent explicitly and asserted here before the request is
built, and qa/safety.py refuses the request again at the transport since
2026-09-10 -- two independent readings, because this account's
`simulation_mode` is False and the platform resolves an absent flag against
it. That is a live order. Neither check is the other's backup: this one can be
edited out by someone working on this file, and the transport one cannot.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

BUY = "/api/v1/event-cards/{card_id}/buy"
SELL = "/api/v1/event-cards/{card_id}/sell"
POSITIONS = "/api/v1/event-cards/positions"
ACCOUNT = "/api/v1/account/me"
SUMMARY = "/api/v1/portfolio/summary"

# Their cap is unresolved -- they said 20/hour, the header advertises 60 -- and
# submit.py and verify.py each took the stricter reading separately. This is
# the third copy, and it is a copy on purpose: a shared constant would make one
# script's pause depend on another's judgement.
PAUSE_SECONDS = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path() -> Path:
    return state_dir() / "paper.jsonl"


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
            if isinstance(r.get("id"), str) and r["id"].startswith("TRD-")]
    return f"TRD-{max(used, default=0) + 1:04d}"


def _capture(response, tier: SafetyTier = SafetyTier.MUTATE) -> str | None:
    """The evidence id, or None with the reason -- never a raise.

    verify.py's shape, and for its reason: a capture that raises between the
    request and the record leaves an intent nothing can settle. The caller
    writes the outcome either way and says the capture failed.
    """
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-paper").capture(
            response.request, response, tier) or None
    except Exception:  # noqa: BLE001
        return None


def _snapshot(client) -> dict:
    """Their side of the account, read the same way before and after.

    Three numbers from two endpoints, because one of them is already known to
    disagree with itself: sim_balance.total_trades reads 0 against 39 position
    rows. Recording all three is what lets a later reader see which one moved.
    """
    out: dict = {"at": _now()}
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        me = client.get(ACCOUNT)
        out["evidence_account"] = _capture(me, SafetyTier.SAFE)
        if me.status_code == 200:
            sim = (me.json() or {}).get("sim_balance") or {}
            out["sim_balance_usdc"] = sim.get("usdc")
            out["sim_total_trades"] = sim.get("total_trades")
            # The number their 18:06 message of 2026-09-10 claims a close
            # books, and the one nothing here had ever read. Recorded on both
            # sides of every order from now on, so the claim is measurable
            # without a second trip.
            out["sim_total_pnl"] = sim.get("total_pnl")
            out["sim_started_at"] = sim.get("started_at")
            out["simulation_mode"] = (me.json() or {}).get("simulation_mode")
        rows = client.get(POSITIONS)
        out["evidence_positions"] = _capture(rows, SafetyTier.SAFE)
        held = None
        if rows.status_code == 200:
            # Rule 8 in the other direction from _positions: here an
            # unreadable body must leave `positions` ABSENT, so the check
            # reads `unread` and says Inconclusive. Writing 0 would be the
            # `(x or 0)` that turned a failed read into a passing verdict on
            # the row that decides #87.
            try:
                held = position_rows(rows.json())
            except UnreadableBody:
                held = None
        if held is not None:
            out["positions"] = len(held)
            out["paper_positions"] = sum(1 for p in held if p.get("is_paper"))
            out["notional_usdc"] = round(
                sum(float(p.get("notional_usdc") or 0) for p in held), 2)
    finally:
        CURRENT_TIER.reset(token)
    return out


def _guidance(nexus_id: str | None) -> dict:
    """The advice this order acts on, from the recorded answer."""
    if not nexus_id:
        return {"id": None, "job_id": None, "note": "no recorded guidance; "
                "this order is ours, not Cymetica's"}
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "nexus_for_paper", REPO_ROOT / "scripts" / "nexus.py")
    nexus = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nexus)
    rows = nexus.load()
    answer = next((r for r in rows
                   if r.get("id") == nexus_id and r.get("type") == "answer"), None)
    if answer is None:
        raise SystemExit(
            f"{nexus_id} is not a recorded Nexus answer. `python "
            f"scripts/nexus.py list` shows what has been asked and answered; "
            f"an order may not cite guidance that was never given.")
    question = next((r for r in rows
                     if r.get("id") == nexus_id and r.get("type") == "question"), {})
    return {"id": nexus_id, "job_id": answer.get("job_id"),
            "asked": question.get("question"),
            "answered_in_seconds": answer.get("waited_seconds"),
            "advice": (answer.get("text") or "")[:2000]}


# What we started with. Their headline number never moves (#87), so this is
# nominal: the book is what makes it mean something.
BANKROLL = 100000.0


class UnreadableBody(ValueError):
    """A 200 whose shape this reader does not recognise.

    Distinct from an empty book on purpose. `(body or {}).get("positions") or
    []` collapsed the two, and of all the ways to be wrong about a book, "no
    positions are deployed" is the worst: it frees the entire bankroll and
    `affordable()` waves through the order that should have been refused.
    """


def position_rows(payload) -> list[dict]:
    """Their position rows, out of whichever envelope they arrived in.

    `buy()` in this same file already unwraps `payload["result"]`, so the
    envelope is known to exist on this platform -- it simply has not appeared
    on this endpoint yet, in 41 captures. That is a fact about today's data
    and their platform ships several times a day, which is the whole argument
    for reading the shape rather than assuming it.
    """
    for body in (payload, (payload or {}).get("result")
                 if isinstance(payload, dict) else None):
        if isinstance(body, dict) and isinstance(body.get("positions"), list):
            return body["positions"]
    raise UnreadableBody(
        f"a 200 from {POSITIONS} carried no positions list, in a body shaped "
        f"{sorted(payload)[:6] if isinstance(payload, dict) else type(payload).__name__}. "
        f"An unreadable book is not an empty one")


def _positions(client) -> list[dict]:
    """Their position rows, which are the only working half of the scoreboard."""
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(POSITIONS)
        if response.status_code != 200:
            raise SystemExit(
                f"their positions endpoint answered HTTP {response.status_code}; "
                f"the book cannot be computed and no order will be sent on a "
                f"failed read.")
        try:
            return position_rows(response.json())
        except UnreadableBody as exc:
            raise SystemExit(
                f"{exc}. No order will be sent on a book that could not be "
                f"read: reading it as zero deployed would free the whole "
                f"bankroll.")
    finally:
        CURRENT_TIER.reset(token)


def book(positions: list[dict], rows: list[dict] | None = None,
         clone_capital: float | None = None) -> dict:
    """Our own accounting of the campaign, from their position rows.

    Their paper balance does not move when a position opens, so no number they
    publish says what a campaign has left. This is that number, and only the
    arithmetic is ours: every value in it comes off their own rows.

    A position that is no longer open stops being deployed capital and its
    proceeds return to cash -- without that the book leaks, and after enough
    round trips a campaign would refuse to trade with a bankroll it still has.

    `clone_capital` is money funded into paper bots, which is deployed and not
    cash: the bot spends it on its own schedule and we cannot recall it by
    deciding not to trade. It is passed in rather than read here because it
    comes off THEIR my-clones rows, and `None` -- a balance we could not read
    -- deliberately changes nothing, since the direction that frees money we
    have already handed over is the dangerous one.
    """
    rows = load() if rows is None else rows
    chains: dict[str, dict] = {}
    for row in rows:
        chains.setdefault(row["id"], {})[row.get("type")] = row

    by_position = {p.get("position_id"): p for p in positions}
    deployed = 0.0
    value = 0.0
    realised = 0.0
    open_count = 0
    unaccounted = 0
    unaccounted_usdc = 0.0
    for chain in chains.values():
        intent, outcome = chain.get("intent") or {}, chain.get("outcome") or {}
        if outcome.get("outcome") != "accepted":
            continue
        held = by_position.get(outcome.get("position_id"))
        if held is None:
            # Accepted by them and not in their positions. This said it was
            # "worth noticing rather than quietly dropping" and then dropped
            # it: no counter, no field, no print, and the capital went back to
            # cash so `affordable` would authorise spending it twice. Reachable
            # without any bug on their side -- pagination, a filter, or the lag
            # between acceptance and listing.
            #
            # Rule 8's shape applied to a row: an accepted order we cannot
            # account for is UNACCOUNTED, and its money stays committed. The
            # safe direction is to hold capital we cannot see, never to
            # release it.
            unaccounted += 1
            unaccounted_usdc += float(intent.get("usdc") or 0)
            continue
        if str(held.get("status")) == "open":
            deployed += float(intent.get("usdc") or 0)
            value += float(held.get("current_value_usdc") or 0)
            open_count += 1
        else:
            realised += float(held.get("realized_pnl_usdc") or 0)

    in_bots = float(clone_capital or 0)
    deployed += in_bots
    cash = BANKROLL - deployed - unaccounted_usdc + realised
    return {"bankroll": BANKROLL, "deployed": round(deployed, 6),
            "in_bots": round(in_bots, 6),
            "cash": round(cash, 6), "value": round(value, 6),
            "realised": round(realised, 6),
            # Money in a bot is still ours -- their /withdraw route brings it
            # back -- so it leaves cash and stays in equity. `value` keeps
            # meaning positions at their index and nothing else.
            "equity": round(cash + value + in_bots, 6), "open": open_count,
            "unaccounted": unaccounted,
            "unaccounted_usdc": round(unaccounted_usdc, 6)}


def clone_capital(client) -> float | None:
    """USDC sitting in our paper bots, from THEIR my-clones rows.

    None when the read failed or came back in a shape we do not know. A bot
    balance we cannot read must not be counted as zero: that is the direction
    that frees money we have already handed over, and `affordable` would then
    authorise spending it a second time.
    """
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get("/api/v1/cloned-bots/my-clones",
                              params={"mode": "paper"})
    except Exception:  # noqa: BLE001
        return None
    finally:
        CURRENT_TIER.reset(token)
    if response.status_code != 200:
        return None
    try:
        rows = response.json()
    except ValueError:
        return None
    if not isinstance(rows, list):
        return None
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            return None
        try:
            total += float(row.get("current_balance_usdc") or 0)
        except (TypeError, ValueError):
            return None
    return round(total, 6)


def affordable(usdc: float, positions: list[dict],
               rows: list[dict] | None = None,
               in_bots: float | None = None) -> tuple[bool, str]:
    """Whether the book can pay for this order.

    Their side will accept it either way -- it has accepted every order we
    have sent and debited nothing. If we accept it too then the campaign has
    no downside, and a strategy that would have lost the bankroll looks
    exactly like one that doubled it.
    """
    state = book(positions, rows, clone_capital=in_bots)
    stranded = (f" A further {state['unaccounted_usdc']:.2f} is unaccounted: "
                f"{state['unaccounted']} accepted order(s) they did not list, "
                f"held as spent because money we cannot see is not money we "
                f"have." if state["unaccounted"] else "")
    if usdc <= state["cash"]:
        return True, f"{state['cash']:.2f} USDC uncommitted{stranded}"
    return False, (
        f"the book has {state['cash']:.2f} USDC uncommitted and this order "
        f"wants {usdc:.2f}. {state['deployed']:.2f} is already in "
        f"{state['open']} open position(s).{stranded} Their paper balance will "
        f"accept this order anyway; that is finding #87, and it is why this "
        f"refusal is here rather than there.")


def buy(card_id: str, usdc: float, nexus_id: str | None, confirm: bool) -> dict:
    """One order, recorded as intent then outcome, with the account either side."""
    if usdc <= 0:
        raise SystemExit("an order needs a positive notional")

    paper = True
    # Asserted here, before a body exists, because this is the file somebody
    # edits when they want to place a live order and the assertion is what
    # they have to delete on purpose.
    assert paper is True, "this script places paper orders only"

    guidance = _guidance(nexus_id)
    body = {"amount_usdc": float(usdc), "paper": paper}

    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    ids = identities()
    client = build_client(ids["trusted"], registry, timeout=60.0)

    try:
        before = _snapshot(client)
        held = _positions(client)
        can, why = affordable(float(usdc), held,
                              in_bots=clone_capital(client))
        print(f"[book] {why}")
        if not can:
            raise SystemExit(
                f"refused by our own book: {why}")
        if before.get("simulation_mode") is True:
            print("[paper] note: the account is in simulation_mode, so every "
                  "order is paper whatever this sends")
        entry = {"id": _next_id(load()), "type": "intent", "at": _now(),
                 "card_id": card_id, "usdc": float(usdc), "paper": paper,
                 "nexus": guidance, "before": before, "body": body}

        if not confirm:
            print(json.dumps({k: v for k, v in entry.items() if k != "nexus"},
                             ensure_ascii=False, indent=1))
            print(f"\nguidance: {guidance['id'] or 'NONE -- this order would be ours'}")
            print("nothing sent (--confirm to place it)")
            return entry

        # Intent first. A POST that times out still leaves the order on the
        # record, which is the whole of rule 9 and the reason a2a survives a
        # timeout.
        _append(entry)
        token = CURRENT_TIER.set(SafetyTier.MUTATE)
        try:
            response = client.post(BUY.format(card_id=card_id), json=body)
        except Exception as exc:  # noqa: BLE001
            _append({"id": entry["id"], "type": "outcome", "at": _now(),
                     "outcome": "unknown", "error": f"{type(exc).__name__}: {exc}"})
            raise SystemExit(
                f"{entry['id']}: the order did not complete ({type(exc).__name__}). "
                f"The intent is on the record; read their positions before "
                f"retrying, because the order may have landed.")
        finally:
            CURRENT_TIER.reset(token)

        evidence_id = _capture(response)
        payload = {}
        try:
            payload = response.json() or {}
        except ValueError:
            payload = {}
        inner = payload.get("result") if isinstance(payload.get("result"), dict) else payload
        position_id = (inner or {}).get("position_id") or (inner or {}).get("id")
        accepted = 200 <= response.status_code < 300 and bool(position_id)

        _append({"id": entry["id"], "type": "outcome", "at": _now(),
                 "outcome": "accepted" if accepted else "unknown",
                 "http_status": response.status_code,
                 "position_id": position_id, "evidence_id": evidence_id,
                 "response": json.dumps(payload, ensure_ascii=False)[:1200]})

        time.sleep(PAUSE_SECONDS)
        after = _snapshot(client)
        _append({"id": entry["id"], "type": "after", "at": _now(), **after})

        moved = None
        try:
            moved = round(float(before.get("sim_balance_usdc") or 0)
                          - float(after.get("sim_balance_usdc") or 0), 2)
        except (TypeError, ValueError):
            pass
        print(f"{entry['id']}: HTTP {response.status_code}, position "
              f"{position_id or '(none returned)'}")
        print(f"   paper balance {before.get('sim_balance_usdc')} -> "
              f"{after.get('sim_balance_usdc')}  (moved {moved})")
        print(f"   positions {before.get('positions')} -> {after.get('positions')}")
        return entry
    finally:
        client.close()


def close(position_id: str, confirm: bool) -> dict:
    """Close one paper position, and read whether the money comes back.

    The other half of the book, and until 2026-09-10 the untested one. #87
    established that a buy DEBITS; nothing here had ever called `/sell`, so
    whether a close CREDITS rested entirely on their telegram message of that
    evening: *"a paper close returns the proceeds and books total_pnl."* A
    book that debits and never credits reads every strategy as losing money,
    and it would take weeks of campaign to notice.

    Written into the same log as a buy, because it is the same campaign and
    `book()` reads both -- but tagged `kind: "close"`, since to #87's reader
    the three rows under one id are otherwise indistinguishable from a buy,
    and the wrong way round: the balance goes up and the position count goes
    down.
    """
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=60.0)

    try:
        held = _positions(client)
        target = next((p for p in held
                       if p.get("position_id") == position_id), None)
        if target is None:
            raise SystemExit(
                f"they do not list {position_id}, so what closing it should "
                f"return cannot be established. Nothing is sent against a "
                f"position we cannot read.")
        if target.get("is_paper") is not True:
            raise SystemExit(
                f"{position_id} is not a paper position by their own reading "
                f"(is_paper={target.get('is_paper')!r}). This script closes "
                f"paper positions only.")
        if target.get("status") == "closed":
            raise SystemExit(f"{position_id} is already closed.")

        card_id = target.get("card_id")
        # `paper` travels even though the position already carries it: the
        # transport floor reads the BODY, and required_flags on
        # event_cards.sell is what stops an absent flag resolving against
        # simulation_mode.
        body = {"position_id": position_id, "fraction": 1.0, "paper": True}
        before = _snapshot(client)
        entry = {"id": _next_id(load()), "type": "intent", "at": _now(),
                 "kind": "close", "card_id": card_id,
                 "position_id": position_id,
                 "notional_usdc": target.get("notional_usdc"),
                 "unrealized_pnl_usdc": target.get("unrealized_pnl_usdc"),
                 "paper": True, "before": before, "body": body}

        if not confirm:
            print(json.dumps(entry, ensure_ascii=False, indent=1))
            print("\nnothing sent (--confirm to close it)")
            return entry

        _append(entry)
        token = CURRENT_TIER.set(SafetyTier.MUTATE)
        try:
            response = client.post(SELL.format(card_id=card_id), json=body)
        except Exception as exc:  # noqa: BLE001
            _append({"id": entry["id"], "type": "outcome", "at": _now(),
                     "kind": "close", "outcome": "unknown",
                     "error": f"{type(exc).__name__}: {exc}"})
            raise SystemExit(
                f"{entry['id']}: the close did not complete "
                f"({type(exc).__name__}). The intent is on the record; read "
                f"their positions before retrying, it may have landed.")
        finally:
            CURRENT_TIER.reset(token)

        evidence_id = _capture(response)
        try:
            payload = response.json() or {}
        except ValueError:
            payload = {}
        inner = (payload.get("result")
                 if isinstance(payload.get("result"), dict) else payload)
        _append({"id": entry["id"], "type": "outcome", "at": _now(),
                 "kind": "close",
                 "outcome": ("accepted" if 200 <= response.status_code < 300
                             else "unknown"),
                 "http_status": response.status_code,
                 "realized_pnl_usdc": (inner or {}).get("realized_pnl_usdc"),
                 "proceeds_usdc": (inner or {}).get("proceeds_usdc"),
                 "evidence_id": evidence_id,
                 "response": json.dumps(payload, ensure_ascii=False)[:1200]})

        time.sleep(PAUSE_SECONDS)
        after = _snapshot(client)
        _append({"id": entry["id"], "type": "after", "at": _now(),
                 "kind": "close", **after})

        def _moved(key):
            try:
                return round(float(after.get(key)) - float(before.get(key)), 6)
            except (TypeError, ValueError):
                return None

        print(f"{entry['id']}: HTTP {response.status_code}, closed "
              f"{position_id}")
        print(f"   paper balance {before.get('sim_balance_usdc')} -> "
              f"{after.get('sim_balance_usdc')}  "
              f"(credited {_moved('sim_balance_usdc')})")
        print(f"   total_pnl     {before.get('sim_total_pnl')} -> "
              f"{after.get('sim_total_pnl')}  (moved {_moved('sim_total_pnl')})")
        print(f"   positions     {before.get('positions')} -> "
              f"{after.get('positions')}")
        return entry
    finally:
        client.close()


def proof() -> int:
    """The chain, and whether the three records agree.

    This is the answer to "will we be able to prove it": not one number, but
    our order beside their position beside their balance, each with the
    evidence that carries their own bytes.
    """
    rows = load()
    if not rows:
        print("no paper trade recorded yet")
        return 0

    by_id: dict[str, dict] = {}
    for row in rows:
        by_id.setdefault(row["id"], {})[row.get("type")] = row

    print(f"{'trade':9} {'guidance':10} {'usdc':>7} {'position':>12} "
          f"{'balance moved':>14}  agrees")
    print("-" * 74)
    disagreements = 0
    for trade_id in sorted(by_id):
        chain = by_id[trade_id]
        intent, outcome, after = (chain.get("intent") or {},
                                  chain.get("outcome") or {},
                                  chain.get("after") or {})
        before = intent.get("before") or {}
        want = float(intent.get("usdc") or 0)
        try:
            moved = round(float(before.get("sim_balance_usdc") or 0)
                          - float(after.get("sim_balance_usdc") or 0), 2)
        except (TypeError, ValueError):
            moved = None
        grew = ((after.get("positions") or 0) - (before.get("positions") or 0)) == 1
        agrees = (outcome.get("outcome") == "accepted" and grew
                  and moved is not None and abs(moved - want) < 0.01)
        if not agrees:
            disagreements += 1
        print(f"{trade_id:9} {str((intent.get('nexus') or {}).get('id')):10} "
              f"{want:>7.2f} {str(outcome.get('position_id'))[:12]:>12} "
              f"{str(moved):>14}  {'yes' if agrees else 'NO'}")

    print()
    if disagreements:
        print(f"{disagreements} trade(s) where our record, their position count "
              f"and their balance do not tell the same story. That is the "
              f"finding, not the bookkeeping.")
    else:
        print("every trade agrees across our record, their positions and their "
              "balance.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    order = sub.add_parser("buy", help="go bull on one card, in paper")
    order.add_argument("--card", required=True)
    order.add_argument("--usdc", type=float, required=True)
    order.add_argument("--nexus", help="the recorded Nexus answer this acts on")
    order.add_argument("--confirm", action="store_true",
                       help="actually place it; without this nothing is sent")

    shut = sub.add_parser("close", help="close one paper position, in full")
    shut.add_argument("--position-id", required=True)
    shut.add_argument("--confirm", action="store_true")

    sub.add_parser("positions", help="their side of the account, read now")
    sub.add_parser("book", help="what the campaign has, by our own reckoning")
    sub.add_parser("proof", help="the chain, and whether it agrees")

    args = parser.parse_args(argv)
    load_dotenv()

    if args.cmd == "buy":
        buy(args.card, args.usdc, args.nexus, args.confirm)
        return 0
    if args.cmd == "close":
        close(args.position_id, args.confirm)
        return 0

    if args.cmd == "proof":
        return proof()
    if args.cmd == "book":
        install_client_guard()
        ids = identities()
        client = build_client(ids["trusted"], EndpointRegistry.load(), timeout=30.0)
        try:
            state = book(_positions(client),
                         clone_capital=clone_capital(client))
        finally:
            client.close()
        print(f"  bankroll   {state['bankroll']:>14,.2f}")
        print(f"  deployed   {state['deployed']:>14,.2f}   in {state['open']} open position(s)")
        print(f"  realised   {state['realised']:>14,.2f}")
        print(f"  cash       {state['cash']:>14,.2f}   available to trade")
        print(f"  positions  {state['value']:>14,.6f}   at their current index")
        print(f"  EQUITY     {state['equity']:>14,.6f}")
        gain = state["equity"] - state["bankroll"]
        print(f"             {gain:>+14,.6f}   since the campaign opened")
        return 0

    install_client_guard()
    ids = identities()
    client = build_client(ids["trusted"], EndpointRegistry.load(), timeout=30.0)
    try:
        snap = _snapshot(client)
    finally:
        client.close()
    for key in sorted(snap):
        print(f"{key:22} {snap[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
