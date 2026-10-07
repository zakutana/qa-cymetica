"""A wave of paper bots: one species each, one change of settings, one room each.

    python scripts/wave.py plan                    which species, which settings -- sends nothing
    python scripts/wave.py run --confirm           clone, room, criterion, settings, fund, start

Until 2026-10-05 a wave was a script that lived in no repository (commit 834d81d4
holds only the rows it wrote). It sent no settings, so wave 0's nine bots ran the
platform's stop-loss 5 % / take-profit 15 % and every one was auto-paused after a
single trade, inside an hour; their rooms read `running` for two more days.

This is that script, kept. It does exactly what `launch_bot` in scripts/lab.py does
-- through scripts/clone.py (paper floor, is_paper floors, CLN records) and
qa/rooms.py (room, plan, criterion) -- except that it may clone a species we
already hold: Cymetica lifted the one-clone-per-species rule on Pro (REPLY-0122,
2026-10-04, up to 25 trading and 50 in all).

The order is the point: the clone, then the room with its criterion, THEN the
settings, THEN the money, THEN `enable`. A window never starts before its
criterion (STR-0046, STR-0064..0068). The first thing that goes wrong stops the
wave -- the cap, a refusal, a read-back that differs from what was sent -- because
a wave that carries on after the platform said no is a wave nobody is watching.
Paper only: nothing here can make a live clone.
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

# The one change of wave 2 (plan of 2026-10-05): wide enough that a bot keeps
# trading through a 7-day window instead of leaving after one trade. Inside the
# platform's bounds (stop_loss_pct 1-20, take_profit_pct 5-100).
SETTINGS = {"stop_loss_pct": 15.0, "take_profit_pct": 40.0}
STAKE_USDC = 500.0
WINDOW_DAYS = 7.0
STOP_PCT = 10.0
# The platform's cap on bots trading at once (Telegram, 2026-10-03). A bigger
# wave is refused outright rather than discovered at the 26th clone.
MAX_TRADING = 25
BTC_PROXY = "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161"


def without_trading(species: list[dict], clone_rows: list[dict],
                    samples: list[dict]) -> list[dict]:
    """The species none of our clones is trading right now.

    A species whose latest sample says `is_trading` already runs; a second clone
    beside it would be two experiments on one thing. Read from the sampler's
    latest sample of each instance and from our own clone record (intent holds
    the species, outcome the instance) -- not from a list somebody keeps."""
    latest: dict[str, dict] = {}
    for row in samples:
        if row.get("type") == "sample" and row.get("kind") == "bot":
            key = str(row.get("instance_id"))
            if key not in latest or str(row.get("at")) >= str(latest[key].get("at")):
                latest[key] = row
    trading = {i for i, row in latest.items() if row.get("is_trading") is True}
    species_of: dict[str, str] = {}
    instance_of: dict[str, str] = {}
    for row in clone_rows:
        if row.get("type") == "intent" and row.get("source_id"):
            species_of[row["id"]] = str(row["source_id"]).lower()
        if row.get("type") == "outcome" and row.get("clone_instance_id"):
            instance_of[row["id"]] = str(row["clone_instance_id"])
    running = {species_of[cid] for cid, inst in instance_of.items()
               if inst in trading and cid in species_of}
    return [s for s in species if str(s["id"]).lower() not in running]


def _read_back(changed: dict, sent: dict) -> str | None:
    """None when THEIR answer to the PATCH says what we sent, else what differed.

    Their `settings` are in the PATCH response itself. The `my-clones` list row has
    no `settings` key (the first live read-back, 2026-10-06, found `their_settings`
    None on a bot whose PATCH had answered 15 / 40), so the list is not the place."""
    seen = changed.get("settings")
    if not isinstance(seen, dict):
        return "their answer carried no settings to read back"
    for key, want in sent.items():
        got = seen.get(key)
        try:
            same = float(got) == float(want)
        except (TypeError, ValueError):
            same = False
        if not same:
            return f"{key}: sent {want}, they hold {got}"
    return None


def _recorded_outcome(clone, kind: str, instance: str) -> str | None:
    """What clone.py recorded for its newest `kind` call on this instance.

    `fund()` and `enable()` return their response BODY, not whether it was accepted
    (the same reading `launch_bot` does through `_clone_outcome`). The first live
    wave read `outcome` off the body, found none, and stopped a bot whose 500 USDC
    had already moved."""
    rows = clone.load()
    asked = [row.get("id") for row in rows
             if row.get("type") == "intent" and row.get("kind") == kind
             and row.get("instance_id") == instance]
    if not asked:
        return None
    return next((row.get("outcome") for row in reversed(rows)
                 if row.get("type") == "outcome" and row.get("id") == asked[-1]), None)


def launch_one(bot: dict, *, clone, rooms, lab, settings: dict, stake: float,
               window_days: float, stop_pct: float, name: str) -> dict:
    """One bot, in the order that keeps the criterion ahead of the money."""
    species, bot_name = str(bot["id"]), str(bot.get("name") or bot["id"])
    result = {"species": species, "name": bot_name, "ok": False, "room": None,
              "instance": None, "why": "", "transient": False}

    def attempt(call, *args):
        """(answer, None), or (None, why) when the call raised. Their reads time out
        all day; the first live run (2026-10-05) lost nineteen bots to one
        ReadTimeout that came AFTER an accepted PATCH."""
        try:
            return call(*args) or {}, None
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            result["transient"] = True
            return None, f"{call.__name__} raised: {str(exc)[:200]}"

    made, raised = attempt(clone.clone, bot.get("source_type"), species,
                           f"lab {name} {bot_name}"[:60], None, True)
    if raised:
        result["why"] = raised
        return result
    instance = made.get("clone_instance_id")
    if made.get("outcome") != "accepted" or not instance:
        result["why"] = (f"the paper clone was not accepted (HTTP "
                         f"{made.get('http_status')}, {made.get('outcome')})")
        return result
    result["instance"] = instance
    if made.get("is_paper") is not True:
        result["why"] = (f"they did not confirm {instance} as paper "
                         f"(is_paper={made.get('is_paper')!r}): neither set up, "
                         f"funded nor started")
        return result

    label = "SL {stop_loss_pct:g} / TP {take_profit_pct:g}".format(**settings)
    proposal = lab.note_proposal(
        "bot", species, instance, {"label": label, "settings": dict(settings)},
        f"{name}, {bot_name}: the platform's stop-loss 5 % / take-profit 15 % stopped "
        f"every wave-0 bot after one trade; this one runs {label} for the whole "
        f"window. One change, the same for the whole wave.")
    room = rooms.open_strategy(proposal["id"], f"{name} · {bot_name} {label}"[:rooms.MAX_TITLE],
                               kind="bot", ref=species)["id"]
    result["room"] = room

    def stop(why: str) -> dict:
        result["why"] = why
        try:
            rooms.set_status(room, "stopped", why=why[:400])
        except rooms.RoomError:
            pass
        return result

    rooms.add_link(room, made["id"], why=f"the paper clone of {bot_name} this room runs")
    plan = rooms.set_plan(room, [{"kind": "bot", "ref": instance, "side": "bull",
                                  "share": 1.0}])
    rooms.set_acceptance(
        room, window_days=window_days, stop_pct=stop_pct, legs=plan["legs"],
        benchmark_card=BTC_PROXY, adopted=True,
        why=(f"written before the window opens. {name}: {bot_name} on {label}, "
             f"{stake:g} USDC, {window_days:g} days. Accepted only if it made more than "
             f"it put in, more than the BTC proxy, and drew down no more than "
             f"{stop_pct:g}%. One window is a measurement, not a finding: it counts "
             f"only if it repeats in the next window")[:900])

    changed, raised = attempt(clone.settings, instance, dict(settings), True)
    if raised:
        return stop(f"{raised}; not funded, not started")
    if changed.get("outcome") != "accepted":
        return stop(f"the settings were not accepted ({changed.get('outcome')})")
    differs = _read_back(changed, settings)
    if differs:
        return stop(f"the settings read back wrong -- {differs}; not funded, not started")

    _, raised = attempt(clone.fund, instance, stake, True)
    if raised or _recorded_outcome(clone, "fund", instance) != "accepted":
        return stop(raised or f"funding {instance} was not accepted")
    _, raised = attempt(clone.enable, instance, True)
    if raised or _recorded_outcome(clone, "enable", instance) != "accepted":
        return stop((raised or f"starting {instance} was not accepted")
                    + f"; its {stake:g} stays in the clone")

    rooms.set_status(room, "running",
                     why=(f"{bot_name} cloned on paper as {instance}, set to {label}, "
                          f"funded {stake:g} USDC and started ({name})"))
    result["ok"] = True
    return result


def launch_wave(species: list[dict], *, clone, rooms, lab, settings: dict,
                stake: float, window_days: float, stop_pct: float, name: str) -> list[dict]:
    """The wave, one bot after another, ending at the first one that fails."""
    if len(species) > MAX_TRADING:
        raise SystemExit(f"{len(species)} bots is more than the {MAX_TRADING} the platform "
                         f"lets trade at once")
    done, failed_in_a_row = [], 0
    for bot in species:
        outcome = launch_one(bot, clone=clone, rooms=rooms, lab=lab, settings=settings,
                             stake=stake, window_days=window_days, stop_pct=stop_pct,
                             name=name)
        done.append(outcome)
        if outcome["ok"]:
            failed_in_a_row = 0
            continue
        # A refusal, a non-paper clone or a read-back that differs is the platform
        # (or us) saying no: stop. A call that raised -- a timeout -- is one bot's
        # bad read: carry on, unless three in a row say the platform is not readable.
        failed_in_a_row += 1
        if not outcome["transient"] or failed_in_a_row >= 3:
            break
    return done


RESUME_SPACING_H = 6.0


def _rooms_of(rooms, instance: str) -> list[dict]:
    """Every room whose plan holds this bot: id, status (the newest), species, opened."""
    rows = rooms.load()
    status = {r["room"]: r["status"] for r in rows if r.get("type") == "status"}
    strategy = {r["id"]: r for r in rows if r.get("type") == "strategy"}
    held = {r["room"] for r in rows if r.get("type") == "plan"
            and any(str(leg.get("ref")) == instance for leg in r.get("legs") or [])}
    return [{"id": room, "status": status.get(room), "species": strategy[room].get("ref"),
             "opened": strategy[room].get("at")}
            for room in sorted(held) if room in strategy]


def resume_wave(*, clone, rooms, lab, samples: list[dict], verdicts, now,
                name: str, window_days: float = WINDOW_DAYS,
                stop_pct: float = STOP_PCT, spacing_h: float = RESUME_SPACING_H,
                max_trading: int = MAX_TRADING) -> list[dict]:
    """Start again the bots the platform paused at their first stop-loss or take-profit.

    The platform pauses EVERY clone at the first band it hits, by design (llms.txt,
    Nexus NEX-0124, 2026-10-07), and `toggle-trading` resumes it. Fifteen of the twenty
    wave-2 bots stood still within hours, so the wave was one trade each, not a week.
    A resume is a SECOND window of the SAME configuration -- the repeat the research plan
    wants before any claim about a species -- so nothing is cloned, funded or re-set: the
    bot keeps what it holds. The order is the wave's: the old room stops and is judged,
    then a new proposal, room and criterion, THEN the enable (`launch_one` has the same
    spine), then the room runs.

    [operator 2026-10-07] a bot that ends on its stop-loss three times in a row is thrown
    away instead: its rooms stop and its paper clone is released, never started again.
    A stop that was not a band is a finding and is not touched, and a bot started less
    than `spacing_h` ago is left, so one that hits its band at once cannot loop."""
    rows = clone.load()
    released = {str(r.get("instance_id")) for r in rows
                if r.get("type") == "intent" and r.get("kind") == "release"
                and any(o.get("id") == r.get("id") and o.get("type") == "outcome"
                        and o.get("outcome") == "accepted" for o in rows)}
    candidates = {k: v for k, v in lab.trigger_stops_now(rows, samples).items()
                  if k not in released}
    thrown = lab.discarded_bots(rows, samples)
    latest: dict[str, bool] = {}
    for sample in sorted((s for s in samples if s.get("kind") == "bot"),
                         key=lambda s: str(s.get("at"))):
        latest[str(sample.get("instance_id"))] = sample.get("is_trading") is True
    free = max(0, max_trading - sum(latest.values()))
    results: list[dict] = []
    plan: list[tuple[str, dict]] = []
    # Newest stop first: the ones that stopped most recently keep their settings fresh.
    for instance, stop in sorted(candidates.items(), key=lambda kv: kv[1]["before"], reverse=True):
        result = {"name": instance, "instance": instance, "ok": False, "room": None,
                  "why": "", "transient": False, "discarded": False}
        started = lab.last_accepted_start(rows, instance)
        try:
            ago = (now - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds() / 3600
        except ValueError:
            ago = None
        if instance not in thrown and ago is not None and ago < spacing_h:
            result["why"] = (f"started {ago:.1f} h ago; a bot is resumed at most once in "
                             f"{spacing_h:g} h, so one that hits its band at once cannot loop")
            results.append(result)
            continue
        if instance not in thrown:
            if free <= 0:
                result["why"] = (f"no free slot: the platform lets {max_trading} bots "
                                 f"trade at once, and they do")
                results.append(result)
                continue
            free -= 1
        plan.append((instance, result))

    # Every old room of a bot we act on stops FIRST, and is judged once, together.
    for instance, _ in plan:
        for room in _rooms_of(rooms, instance):
            if room["status"] == "running":
                rooms.set_status(room["id"], "stopped",
                                 why=(f"the platform paused {instance} at its "
                                      f"{candidates[instance].get('reason')}; this window is "
                                      f"over, judged up to the stop"))
    if plan:
        try:
            verdicts()
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            # Their reads time out all day. The old rooms are stopped either way and the
            # next tick judges them; the new windows must not wait on that.
            print(f"  note: judging the old rooms raised ({str(exc)[:160]}); "
                  f"the next tick does it")

    failed_in_a_row = 0
    for instance, result in plan:
        history = _rooms_of(rooms, instance)
        if instance in thrown:
            result["discarded"] = True
            try:
                clone.release(instance, True)
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                result["why"] = f"release raised: {str(exc)[:200]}"
            else:
                if _recorded_outcome(clone, "release", instance) != "accepted":
                    result["why"] = "the platform did not accept the release"
                else:
                    result["why"] = "three stop-losses in a row: thrown away"
            results.append(result)
            continue
        species = str((history[-1] if history else {}).get("species") or "")
        windows = sum(1 for r in rows if r.get("type") == "intent" and r.get("kind") == "enable"
                      and str(r.get("instance_id")) == instance)
        record = next((r["id"] for r in rows if r.get("type") == "outcome"
                       and str(r.get("clone_instance_id")) == instance), None)
        if not species or not record:
            result["why"] = "its species or its clone record is not in our files"
            results.append(result)
            continue
        proposal = lab.note_proposal(
            "bot", species, instance,
            {"label": f"resume {windows}", "settings": {}},
            f"{name}: the platform paused {instance} at its {candidates[instance].get('reason')}, "
            f"as it does every clone at its first band; started again with the same "
            f"settings as window {windows + 1}.")
        room = rooms.open_strategy(proposal["id"], f"{name} · {instance[:8]} resume {windows}"[:rooms.MAX_TITLE],
                                   kind="bot", ref=species)["id"]
        result["room"] = room
        rooms.add_link(room, record, why=f"the paper clone {instance} this room runs again")
        legs = rooms.set_plan(room, [{"kind": "bot", "ref": instance, "side": "bull",
                                      "share": 1.0}])["legs"]
        rooms.set_acceptance(
            room, window_days=window_days, stop_pct=stop_pct, legs=legs,
            benchmark_card=BTC_PROXY, adopted=True,
            why=(f"written before the window opens. {name}: {instance} resumed after its "
                 f"{candidates[instance].get('reason')}, window {windows + 1}, same settings, "
                 f"{window_days:g} days. Accepted only if it made more than it put in, more "
                 f"than the BTC proxy, and drew down no more than {stop_pct:g}%. It counts "
                 f"only if it repeats")[:900])
        try:
            clone.enable(instance, True)
            accepted = _recorded_outcome(clone, "enable", instance) == "accepted"
            why = "" if accepted else "the platform did not accept the start"
            transient = False
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            accepted, why, transient = False, f"enable raised: {str(exc)[:200]}", True
        if not accepted:
            result["why"], result["transient"] = why, transient
            try:
                rooms.set_status(room, "stopped", why=why[:400])
            except rooms.RoomError:
                pass
            results.append(result)
            failed_in_a_row += 1
            if not transient or failed_in_a_row >= 3:
                break
            continue
        rooms.set_status(room, "running", why=f"{instance} resumed after its band (window "
                                              f"{windows + 1}), same settings ({name})")
        result["ok"] = True
        failed_in_a_row = 0
        results.append(result)
    return results


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"wave_{name}", REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _available(clone) -> list[dict]:
    from qa.client import build_client, install_client_guard
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier
    load_dotenv()
    install_client_guard()
    client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(clone.AVAILABLE)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    if response.status_code != 200:
        raise SystemExit(f"{clone.AVAILABLE} answered HTTP {response.status_code}")
    return clone.available_bots(response.json())


def _samples() -> list[dict]:
    from qa.state import state_dir
    target = state_dir() / "samples.jsonl"
    rows = []
    if target.is_file():
        for line in target.read_text(encoding="utf-8").splitlines():
            if '"kind": "bot"' in line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def _resume_cli(args) -> int:
    """`resume`: read the platform's reason for every stop first (a fresh sampler round,
    so `auto_pause_reason` is on our record), list who would resume, and only with
    --confirm start them. Paper only: it calls clone.enable, whose floors are unchanged."""
    from qa import lab, rooms
    clone, lab_script = _sibling("clone"), _sibling("lab")
    _sibling("sampler").main(["once"])
    samples = rooms.load_samples()
    rows = clone.load()
    candidates = lab.trigger_stops_now(rows, samples)
    thrown = lab.discarded_bots(rows, samples)
    print(f"{args.name}: {len(candidates)} bot(s) the platform paused at a band, "
          f"{len([c for c in candidates if c in thrown])} of them to be thrown away "
          f"(three stop-losses in a row)")
    for instance, stop in sorted(candidates.items(), key=lambda kv: kv[1]["before"]):
        print(f"  {instance}  {stop.get('reason')}  {stop.get('profit_pct') or 0:+.1f}%  "
              f"stopped {str(stop['before'])[:16]}"
              f"{'  -> thrown away' if instance in thrown else ''}")
    if not args.confirm:
        print("nothing sent: resume needs --confirm")
        return 0
    done = resume_wave(clone=clone, rooms=rooms, lab=lab, samples=samples,
                       verdicts=lambda: lab_script.verdicts(),
                       now=datetime.now(timezone.utc), name=args.name)
    for row in done:
        mark = "ok  " if row["ok"] else ("GONE" if row.get("discarded") and
                                         "thrown" in row["why"] else "SKIP")
        print(f"  {mark} {row['instance']}  {row['room'] or '-'}  {row['why']}")
    return 0 if all(r["ok"] or r.get("discarded") or "ago" in r["why"] for r in done) else 1


def main() -> int:
    from qa.console import printable
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("plan", "run"):
        one = sub.add_parser(cmd)
        one.add_argument("--name", default="Wave 2")
        one.add_argument("--count", type=int, default=20)
        one.add_argument("--skip", action="append", default=[],
                         help="a species by name, left out (one that is half-launched, "
                              "or running and not yet in the sampler)")
        if cmd == "run":
            one.add_argument("--confirm", action="store_true")
    again = sub.add_parser("resume", help="start again the bots the platform paused at "
                                          "their first stop-loss or take-profit")
    again.add_argument("--name", default="Wave 2")
    again.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    if args.cmd == "resume":
        return _resume_cli(args)

    clone = _sibling("clone")
    chosen = [b for b in without_trading(_available(clone), clone.load(), _samples())
              if str(b.get("name")) not in set(args.skip)][:args.count]
    label = "SL {stop_loss_pct:g} / TP {take_profit_pct:g}".format(**SETTINGS)
    print(f"{args.name}: {len(chosen)} bots, {label}, {STAKE_USDC:g} USDC each, "
          f"{WINDOW_DAYS:g}-day window, criterion written before each starts")
    for bot in chosen:
        print(f"  {bot['source_type']:<16} {bot['id']}  {bot.get('name')}")
    if args.cmd == "plan":
        return 0
    if not args.confirm:
        print("nothing sent: run needs --confirm")
        return 1

    from qa import lab
    from qa import rooms
    outcome = launch_wave(chosen, clone=clone, rooms=rooms, lab=lab, settings=SETTINGS,
                          stake=STAKE_USDC, window_days=WINDOW_DAYS, stop_pct=STOP_PCT,
                          name=args.name)
    for row in outcome:
        print(f"  {'ok  ' if row['ok'] else 'STOP'} {row['name']}  {row['room'] or '-'}  "
              f"{row['instance'] or '-'}  {row['why']}")
    return 0 if outcome and all(row["ok"] for row in outcome) and len(outcome) == len(chosen) else 1


if __name__ == "__main__":
    sys.exit(main())
