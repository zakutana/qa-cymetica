"""A wave of paper bots, launched by one tool instead of a hand-made script.

2026-10-05: wave 0 (nine bots, 2026-10-03) was started by a script that is in no
repository -- commit 834d81d4 holds only its rows. It sent no settings, so every bot
ran the platform's stop-loss 5 % / take-profit 15 %: all nine were auto-paused after
ONE trade each, inside an hour, and their rooms read `running` for two more days.
`scripts/wave.py` is that script, kept, and every case here names a way the
hand-made one could fail.

The clone module is always a fake: a test that proves a brake by letting a clone
through is the defect it exists to stop. Each case runs in its own state directory.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
SPECIES = [{"id": f"{i:08x}-0000-4000-8000-000000000000", "name": f"Bot {i}",
            "source_type": "wta_species"} for i in range(1, 6)]
SETTINGS = {"stop_loss_pct": 15.0, "take_profit_pct": 40.0}


def _wave(tmp_path, monkeypatch, case):
    state = tmp_path / case
    state.mkdir()
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    import qa.state
    importlib.reload(qa.state)
    import qa.lab
    importlib.reload(qa.lab)
    import qa.rooms
    importlib.reload(qa.rooms)
    spec = importlib.util.spec_from_file_location(
        f"scripts_wave_{case}", REPO / "scripts" / "wave.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, qa.rooms, qa.lab


class FakeClone:
    """What clone.py would do, recorded. `refuse_at` is the index of the clone
    they refuse; `drift` makes the settings read-back differ from what was sent;
    `not_paper` is the index they do not confirm as paper; `settings_time_out`
    the instances whose settings call raises after the PATCH was accepted."""

    def __init__(self, rooms, refuse_at=None, drift=False, not_paper=None,
                 settings_time_out=(), reject=None):
        self.settings_time_out = set(settings_time_out)
        self.reject = reject or {}
        self.rooms, self.calls, self.rows = rooms, [], []
        from qa.state import state_dir
        self.record = state_dir() / "clones.jsonl"
        self.refuse_at, self.drift, self.not_paper = refuse_at, drift, not_paper
        self.n = 0

    def _acceptance_exists(self, instance):
        legs = [r for r in self.rooms.load() if r.get("type") == "plan"
                and any(leg.get("ref") == instance for leg in r.get("legs", []))]
        return bool(legs) and any(
            a.get("room") == legs[-1]["room"] for a in self.rooms.load()
            if a.get("type") == "acceptance")

    def clone(self, source_type, source_id, name, nexus_id, confirm):
        index = self.n
        self.n += 1
        self.calls.append(("clone", source_id))
        if index == self.refuse_at:
            return {"outcome": "rejected", "http_status": 409}
        with open(self.record, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"id": f"CLN-{index:04d}", "type": "intent"}) + "\n")
        return {"id": f"CLN-{index:04d}", "outcome": "accepted", "http_status": 200,
                "clone_instance_id": f"inst-{index}",
                "is_paper": False if index == self.not_paper else True}

    def settings(self, instance, changes, confirm):
        self.calls.append(("settings", instance))
        if int(instance.split("-")[1]) in self.settings_time_out:
            # 2026-10-05: the PATCH was accepted, then the re-read of their row
            # timed out and the exception left clone.py as a bare ReadTimeout.
            raise TimeoutError("The read operation timed out")
        sent = dict(changes)
        if self.drift:
            sent["stop_loss_pct"] = 5.0
        # As the real PATCH answers: `settings` in the response body. The my-clones
        # row they would be re-read from has none (2026-10-06).
        return {"id": f"SET-{instance}", "outcome": "accepted", "settings": sent}

    def load(self):
        return self.rows

    def _answer(self, kind, instance):
        """What the real fund() and enable() do: record intent and outcome, and
        RETURN THEIR RESPONSE BODY -- which carries no `outcome`. The first live
        wave read `outcome` off that body; a fake that returned it hid the bug."""
        from datetime import datetime, timezone
        number = len(self.rows) + 1
        at = datetime.now(timezone.utc).isoformat()    # clone.py stamps every row
        self.rows.append({"id": f"{kind.upper()}-{number}", "type": "intent",
                          "kind": kind, "instance_id": instance, "at": at})
        outcome = self.reject.get(kind, "accepted")
        self.rows.append({"id": f"{kind.upper()}-{number}", "type": "outcome",
                          "kind": kind, "outcome": outcome, "at": at})
        return {"id": instance, "is_paper": True}

    def fund(self, instance, amount, confirm):
        self.calls.append(("fund", instance))
        assert self._acceptance_exists(instance), (
            "funded before its room had a criterion: the window must never start "
            "before the criterion is written (STR-0046, STR-0064..0068)")
        return self._answer("fund", instance)

    def enable(self, instance, confirm, enabled=True):
        self.calls.append(("enable", instance))
        assert self._acceptance_exists(instance), (
            "started before its room had a criterion")
        return self._answer("enable", instance)

    def release(self, instance, confirm):
        self.calls.append(("release", instance))
        return self._answer("release", instance)


def _run(wave, rooms, lab, fake, species=SPECIES):
    return wave.launch_wave(species, clone=fake, rooms=rooms, lab=lab,
                            settings=SETTINGS, stake=500.0, window_days=7.0,
                            stop_pct=10.0, name="Wave 2")


def _statuses(rooms):
    out = {}
    for r in rooms.load():
        if r.get("type") == "status":
            out[r["room"]] = r["status"]
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_is_funded_and_started_only_with_its_criterion_and_its_settings(
        tmp_path, monkeypatch):
    """The three things the hand-made wave 0 got wrong, one bot at a time.

    Order: twice the gains or losses of a bot went uncounted because it traded
    before its room had a window (STR-0046, STR-0064..0068); FakeClone.fund and
    .enable assert the room's acceptance is on the record when they are called.
    Settings: wave 0 sent none and ran on 5 % / 15 % defaults, so a read-back that
    differs from what was sent leaves the bot unfunded, unstarted, its room stopped
    with the reason. Paper: a clone they do not call paper is never touched."""
    wave, rooms, lab = _wave(tmp_path, monkeypatch, "order")
    fake = FakeClone(rooms)
    result = _run(wave, rooms, lab, fake)
    assert [r["ok"] for r in result] == [True] * len(SPECIES)
    assert [c[0] for c in fake.calls if c[1] == "inst-0"] == ["settings", "fund", "enable"]
    assert set(_statuses(rooms).values()) == {"running"}
    assert len([r for r in rooms.load() if r.get("type") == "acceptance"]) == len(SPECIES)

    wave, rooms, lab = _wave(tmp_path, monkeypatch, "drift")
    fake = FakeClone(rooms, drift=True)
    result = _run(wave, rooms, lab, fake, SPECIES[:2])
    assert not result[0]["ok"] and "settings" in result[0]["why"]
    assert len(result) == 1, "a drifting read-back stops the wave, it is not retried"
    assert not any(c[0] in ("fund", "enable") for c in fake.calls)
    assert list(_statuses(rooms).values()) == ["stopped"]

    wave, rooms, lab = _wave(tmp_path, monkeypatch, "paper")
    fake = FakeClone(rooms, not_paper=0)
    result = _run(wave, rooms, lab, fake, SPECIES[:2])
    assert not result[0]["ok"] and "paper" in result[0]["why"]
    assert not any(c[0] in ("settings", "fund", "enable") for c in fake.calls)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_stops_a_wave_and_what_only_stops_one_bot(tmp_path, monkeypatch):
    """REPLY-0122 said 25 trading / 50 total; on 2026-10-08 the sampler read 34 of ours
    trading at once, so the cap we hold is the 50 (deep pass, R01). A refusal means the cap (or
    something we did not foresee): the rest is not attempted. A read that times
    out is one bot's problem -- the first live run (2026-10-05) lost nineteen bots
    to one ReadTimeout that came AFTER an accepted PATCH -- so that bot stops with
    the reason and the wave goes on; three in a row say the platform is not
    readable and end it. A wave larger than the cap is refused outright."""
    wave, rooms, lab = _wave(tmp_path, monkeypatch, "refused")
    fake = FakeClone(rooms, refuse_at=2)
    result = _run(wave, rooms, lab, fake)
    assert [r["ok"] for r in result] == [True, True, False]
    assert len([c for c in fake.calls if c[0] == "clone"]) == 3

    wave, rooms, lab = _wave(tmp_path, monkeypatch, "timeout")
    fake = FakeClone(rooms, settings_time_out={1})
    result = _run(wave, rooms, lab, fake)
    assert [r["ok"] for r in result] == [True, False, True, True, True]
    assert "timed out" in result[1]["why"]
    assert ("fund", "inst-1") not in fake.calls and ("enable", "inst-1") not in fake.calls
    assert _statuses(rooms)[result[1]["room"]] == "stopped"

    wave, rooms, lab = _wave(tmp_path, monkeypatch, "three")
    fake = FakeClone(rooms, settings_time_out={0, 1, 2, 3})
    result = _run(wave, rooms, lab, fake)
    assert len(result) == 3 and not any(r["ok"] for r in result)
    assert len([c for c in fake.calls if c[0] == "clone"]) == 3

    # IN A ROW: a bot that goes through resets the count (deep pass 2026-10-08, T13).
    wave, rooms, lab = _wave(tmp_path, monkeypatch, "apart")
    fake = FakeClone(rooms, settings_time_out={0, 2, 3})
    result = _run(wave, rooms, lab, fake)
    assert [r["ok"] for r in result] == [False, True, False, False, True], result

    for kind in ("fund", "enable"):
        wave, rooms, lab = _wave(tmp_path, monkeypatch, f"reject-{kind}")
        fake = FakeClone(rooms, reject={kind: "rejected"})
        result = _run(wave, rooms, lab, fake)
        assert [r["ok"] for r in result] == [False], (
            f"a {kind} the platform rejected stops the wave: the body they send back "
            f"says nothing, only the record does")
        assert _statuses(rooms)[result[0]["room"]] == "stopped"

    wave, rooms, lab = _wave(tmp_path, monkeypatch, "cap")
    fake = FakeClone(rooms)
    many = [{"id": f"{i:08x}-0000-4000-8000-000000000000", "name": f"B{i}",
             "source_type": "wta_species"} for i in range(1, 52)]
    with pytest.raises(SystemExit, match="50"):
        _run(wave, rooms, lab, fake, many)
    assert fake.calls == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_species_already_trading_are_left_out_of_the_wave(tmp_path, monkeypatch):
    """A species whose latest sample is `is_trading` already runs: a second
    clone beside it would be two experiments on one thing. Found through the
    sampler's latest read and our own clone record, not through a list we keep."""
    wave, rooms, lab = _wave(tmp_path, monkeypatch, "trading")
    clone_rows = [
        {"id": "CLN-9", "type": "intent", "source_id": SPECIES[0]["id"]},
        {"id": "CLN-9", "type": "outcome", "outcome": "accepted",
         "clone_instance_id": "live-1"}]
    samples = [
        {"type": "sample", "kind": "bot", "instance_id": "live-1",
         "is_trading": False, "at": "2026-10-05T10:00:00+00:00"},
        {"type": "sample", "kind": "bot", "instance_id": "live-1",
         "is_trading": True, "at": "2026-10-05T14:00:00+00:00"}]
    kept = wave.without_trading(SPECIES, clone_rows, samples)
    assert SPECIES[0] not in kept and len(kept) == len(SPECIES) - 1
    # The LATEST sample, not any: a clone that traded and has stopped leaves its species
    # free (deep pass 2026-10-08, T12) -- and file order is not time order.
    stopped_since = [samples[1], dict(samples[0], at="2026-10-05T18:00:00+00:00")]
    assert SPECIES[0] in wave.without_trading(SPECIES, clone_rows, stopped_since)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_paused_at_its_band_resumes_in_a_room_of_its_own(tmp_path, monkeypatch):
    """2026-10-07: the platform pauses every clone at its first stop_loss or take_profit,
    and fifteen of twenty wave-2 bots stood still. `wave.py resume` starts them again as a
    SECOND window of the same configuration: the old room stops and is judged first, the
    new room and its criterion are on the record BEFORE the enable, and nothing is cloned,
    funded or re-set. [operator 2026-10-07] three stop-losses in a row and the bot is
    thrown away instead -- released, never resumed; a take-profit in between breaks the run.
    A stop that was not a band is a finding and is left alone -- also when a band stop came
    after it -- and so is a bot that was started less than six hours ago. A clone we
    released holds no slot, whatever its last reading said (deep pass 2026-10-08: R02, R07,
    T08, T09)."""
    from datetime import datetime, timezone

    wave, rooms, lab = _wave(tmp_path, monkeypatch, "resume")
    fake = FakeClone(rooms)
    now = datetime(2026, 10, 7, 18, 0, tzinfo=timezone.utc)
    marks = {}   # instance -> readings

    def bot(name, species, starts, readings):
        """One bot of ours: its clone, its enables, its running room, its readings."""
        record = [{"id": f"CLN-{name}", "type": "intent", "kind": None, "source_id": species},
                  {"id": f"CLN-{name}", "type": "outcome", "outcome": "accepted",
                   "clone_instance_id": name, "is_paper": True},
                  {"id": f"FND-{name}", "type": "intent", "kind": "fund",
                   "instance_id": name, "amount": 500.0},
                  {"id": f"FND-{name}", "type": "outcome", "outcome": "accepted"}]
        for number, at in enumerate(starts):
            record += [{"id": f"EN-{name}-{number}", "type": "intent", "kind": "enable",
                        "instance_id": name, "at": at},
                       {"id": f"EN-{name}-{number}", "type": "outcome",
                        "outcome": "accepted", "at": at}]
        fake.rows += record
        with open(fake.record, "a", encoding="utf-8") as handle:
            handle.writelines(json.dumps(r) + "\n" for r in record)
        room = f"STR-{len(rooms.load()) + 100:04d}"
        with open(rooms.path(), "a", encoding="utf-8") as handle:
            handle.writelines(json.dumps(r) + "\n" for r in (
                {"type": "strategy", "id": room, "origin": "OUR-9000", "title": name,
                 "kind": "bot", "ref": species, "at": "2026-10-06T04:00:00+00:00"},
                {"type": "plan", "room": room, "legs": [
                    {"kind": "bot", "ref": name, "side": "bull", "share": 1.0}],
                 "at": "2026-10-06T04:00:01+00:00"},
                {"type": "status", "room": room, "status": "running", "why": "x",
                 "at": "2026-10-06T04:00:02+00:00"}))
        marks[name] = readings
        return room

    def reading(at, trading, profit, reason=None):
        return {"type": "sample", "kind": "bot", "is_trading": trading, "at": at,
                "total_profit_usdc": profit, "auto_pause_reason": reason}

    def stopped(at, reason, profit):
        return [reading(at[:11] + "00:30:00+00:00", True, "0"), reading(at, False, profit, reason)]

    old = {
        "sl": bot("sl", "sp-1", ["2026-10-06T04:00:00+00:00"],
                  stopped("2026-10-06T05:00:00+00:00", "stop_loss", "-75")),
        "tp": bot("tp", "sp-2", ["2026-10-06T04:00:00+00:00"],
                  stopped("2026-10-06T05:00:00+00:00", "take_profit", "225")),
        "three": bot("three", "sp-3", [f"2026-10-0{d}T04:00:00+00:00" for d in (1, 2, 3)],
                     [r for d in (1, 2, 3) for r in stopped(
                         f"2026-10-0{d}T05:00:00+00:00", "stop_loss", "-75")]),
        "guard": bot("guard", "sp-4", ["2026-10-06T04:00:00+00:00"],
                     stopped("2026-10-06T05:00:00+00:00", "risk_engine", "-5")),
        "soon": bot("soon", "sp-5", ["2026-10-07T16:00:00+00:00"],
                    stopped("2026-10-07T17:00:00+00:00", "stop_loss", "-75")),
        # Halted at a loss with no band, traded again without an enable of ours, then
        # stopped at its stop-loss: the first stop is a finding, so no resume and no room.
        "mixed": bot("mixed", "sp-6", ["2026-10-06T04:00:00+00:00"],
                     [reading("2026-10-06T04:30:00+00:00", True, "0"),
                      reading("2026-10-06T05:00:00+00:00", False, "-5"),
                      reading("2026-10-06T06:00:00+00:00", True, "-5"),
                      reading("2026-10-06T07:00:00+00:00", False, "-80", "stop_loss")]),
        # Released by us while its last reading said it traded: it is gone and holds no slot.
        "gone": bot("gone", "sp-7", ["2026-10-06T04:00:00+00:00"],
                    [reading("2026-10-06T04:30:00+00:00", True, "0")]),
    }
    released = [{"id": "REL-gone", "type": "intent", "kind": "release", "instance_id": "gone"},
                {"id": "REL-gone", "type": "outcome", "kind": "release", "outcome": "accepted"}]
    fake.rows += released
    samples = [row | {"instance_id": name} for name, rows_ in marks.items() for row in rows_]
    verdicts = []

    # With room for one bot to trade, one resumes, the other is told why not, the one
    # thrown away needs no slot, and the released one takes none.
    def judging_times_out():
        raise TimeoutError("The read operation timed out")   # their reads do, all day
    first = wave.resume_wave(clone=fake, rooms=rooms, lab=lab, samples=samples, now=now,
                             verdicts=judging_times_out, name="Wave 2", max_trading=1)
    by_first = {r["name"]: r for r in first}
    assert sum(1 for k in ("sl", "tp") if by_first[k]["ok"]) == 1, by_first
    waiting = next(k for k in ("sl", "tp") if not by_first[k]["ok"])
    assert "slot" in by_first[waiting]["why"], by_first[waiting]
    assert by_first["three"]["discarded"], "a bot to throw away needs no slot"
    first_calls = list(fake.calls)
    fake.calls.clear()

    done = wave.resume_wave(clone=fake, rooms=rooms, lab=lab, samples=samples, now=now,
                            verdicts=lambda: verdicts.append(
                                ({r["room"] for r in rooms.load() if r.get("type") == "status"
                                  and r["status"] == "stopped"},
                                 [c for c in fake.calls if c[0] == "enable"])),
                            name="Wave 2")

    by = {r["name"]: r for r in done}
    assert "three" not in by, "a released bot is not released again"
    by = {**by_first, **{k: v for k, v in by.items() if v["ok"]}}
    assert by["sl"]["ok"] and by["tp"]["ok"], by
    assert by["three"]["discarded"] and not by["three"]["ok"]
    assert "guard" not in by, "a stop that was not a band is a finding, not a candidate"
    assert not by["mixed"]["ok"] and "finding" in by["mixed"]["why"] and not by["mixed"]["room"], (
        by["mixed"])
    assert not by["soon"]["ok"] and "6" in by["soon"]["why"], by["soon"]
    calls = first_calls + fake.calls
    assert [c for c in calls if c[0] in ("clone", "fund", "settings")] == [], (
        "a resume clones, funds and re-sets nothing: the bot keeps what it holds")
    assert ("release", "three") in calls and ("enable", "three") not in calls
    assert [c for c in calls if c[0] == "release"] == [("release", "three")], "released once"
    assert sorted(c for c in calls if c[0] == "enable") == [("enable", "sl"), ("enable", "tp")]
    # The old rooms were stopped and judged BEFORE the new windows opened: no enable of
    # this run had been sent when the judging ran (T08).
    stopped_then, enabled_then = verdicts[0] if verdicts else (set(), None)
    assert len(verdicts) == 1 and enabled_then == [], verdicts
    assert {old["sl"], old["tp"], old["three"]} <= stopped_then, verdicts
    assert old["guard"] not in stopped_then and old["soon"] not in stopped_then
    assert old["mixed"] not in stopped_then, "a finding's room is not stopped by a resume"
    # The new room of each resumed bot: a criterion first (the fake asserts it at enable),
    # same window as the wave, running at the end; the first run's room is left alone.
    status = {}
    for row in rooms.load():
        if row.get("type") == "status":
            status[row["room"]] = row["status"]
    new_rooms = [by["sl"]["room"], by["tp"]["room"]]
    assert all(status[r] == "running" for r in new_rooms) and set(new_rooms).isdisjoint(old.values())
    assert status[old["guard"]] == "running" and status[old["soon"]] == "running"
    assert status[old["mixed"]] == "running"
    criteria = [r for r in rooms.load() if r.get("type") == "acceptance" and r["room"] in new_rooms]
    assert [(c["window_days"], c["stop_pct"], c["adopted"]) for c in criteria] == [(7.0, 10.0, True)] * 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_benchmark_and_the_settings_are_the_ones_agreed():
    """The BTC proxy is the laboratory's own; the wave's one change is inside the
    platform's bounds (stop_loss_pct 1-20, take_profit_pct 5-100) and is the plan
    of 2026-10-05."""
    wave_text = (REPO / "scripts" / "wave.py").read_text(encoding="utf-8")
    lab_text = (REPO / "scripts" / "lab.py").read_text(encoding="utf-8")
    ours = re.search(r'BTC_PROXY\s*=\s*"([0-9a-f-]{36})"', wave_text)
    theirs = re.search(r'BTC_PROXY\s*=\s*"([0-9a-f-]{36})"', lab_text)
    assert ours and theirs and ours.group(1) == theirs.group(1)
    stop = float(re.search(r'"stop_loss_pct":\s*([0-9.]+)', wave_text).group(1))
    take = float(re.search(r'"take_profit_pct":\s*([0-9.]+)', wave_text).group(1))
    assert 1.0 <= stop <= 20.0 and 5.0 <= take <= 100.0
    assert (stop, take) == (15.0, 40.0)
