"""The floors under a seat at a table: paper USDC only, a paper clone of ours, one ask per bot and table."""

from __future__ import annotations

import json

import httpx
import pytest

from qa import casino as floors
from qa.paths import state_dir
from qa.safety import SafetyViolation

RULES = {"modes": {"paper": "open", "live": "not_open"},
         "paper_note": "the buy-in comes from your paper USDC and prizes are paid to it",
         "tiers": [{"tier": "fmicro", "buyin_usdc": 5.0, "currency": "USDC"},
                   {"tier": "et100", "buyin_usdc": None, "currency": "ET10"}]}


def _table(**over):
    return {"id": 40, "mode": "paper", "currency": "USDC", "status": "open", "seats_free": 3,
            "tier": "fmicro", "buyin_usdc": 5.0, "my_seat": None, **over}


@pytest.fixture
def casino(script):
    return script("casino")


def test_a_paper_usdc_table_with_a_free_seat_may_be_asked():
    assert floors.seat_refusal("40", _table(), RULES, instance_id="bot") is None


@pytest.mark.parametrize("over", [{"mode": "live"}, {"currency": "ET10"}, {"currency": None}, {"status": "running"},
                                  {"seats_free": 0}, {"id": 41}, {"buyin_usdc": 50.0}, {"tier": "et100"}])
def test_every_other_table_is_refused(over):
    assert floors.seat_refusal("40", _table(**over), RULES, instance_id="bot")


def test_an_unread_table_or_rules_is_refused():
    assert floors.seat_refusal("40", None, RULES)
    assert floors.seat_refusal("40", _table(), None)


def test_one_seat_per_bot_per_table(casino):
    rows = [{"id": "SEAT-0001", "type": "intent", "kind": "seat", "table_id": "40", "instance_id": "bot"},
            {"id": "SEAT-0001", "type": "outcome", "kind": "seat", "outcome": "accepted", "seat_id": 9}]
    assert casino.asked_before("40", rows, instance_id="bot") == "SEAT-0001"
    assert casino.asked_before("40", rows, instance_id="other") is None
    assert casino.asked_before("41", rows, instance_id="bot") is None
    # their table lists its seats and ours is not among them: it was left
    assert casino.asked_before("40", rows, {"standings": [{"seat_id": 7}]}, instance_id="bot") is None
    # an open table serves no standings while our seat waits: that says nothing
    assert casino.asked_before("40", rows, {"standings": []}, instance_id="bot") == "SEAT-0001"


def test_a_refused_ask_blocks_nothing(casino):
    rows = [{"id": "SEAT-0001", "type": "intent", "kind": "seat", "table_id": "40", "instance_id": "bot"},
            {"id": "SEAT-0001", "type": "outcome", "kind": "seat", "outcome": "rejected"}]
    assert casino.asked_before("40", rows, instance_id="bot") is None


def test_only_a_paper_clone_of_ours_is_seated(script):
    clone = script("clone")
    rows = [{"type": "outcome", "outcome": "accepted", "clone_instance_id": "ours", "is_paper": True},
            {"type": "outcome", "outcome": "accepted", "clone_instance_id": "live", "is_paper": False},
            {"type": "outcome", "outcome": "rejected", "clone_instance_id": "no", "is_paper": True},
            {"type": "outcome", "kind": "fund", "outcome": "accepted", "clone_instance_id": "fund", "is_paper": True}]
    assert clone.paper_by_our_record("ours", rows)
    for other in ("live", "no", "fund", "unknown"):
        assert not clone.paper_by_our_record(other, rows)
    assert clone.startable({"is_paper": True, "execution_economics": {"execution_class": "PAPER_SIMULATION"}})
    assert not clone.startable({"is_paper": True, "execution_economics": {"execution_class": "LIVE"}})
    assert not clone.startable({"is_paper": False, "execution_economics": {"execution_class": "PAPER_SIMULATION"}})
    assert not clone.startable({"is_paper": True})


class Client:
    def __init__(self, post):
        self.post = post


def test_a_guard_refusal_at_the_post_leaves_an_outcome_and_blocks_nothing(casino):
    def refused(url, json=None):
        raise SafetyViolation("MUTATE against unlisted host")

    said = casino._send_seat(Client(refused), "/seat", {"instance_id": "bot"}, "40", instance_id="bot")
    assert said["outcome"] == "not_sent"
    rows = casino.load()
    assert [r["type"] for r in rows] == ["intent", "outcome"]
    assert casino.asked_before("40", rows, instance_id="bot") is None


def test_a_timeout_at_the_post_may_have_landed(casino):
    def lost(url, json=None):
        raise httpx.ReadTimeout("no answer")

    assert casino._send_seat(Client(lost), "/seat", {"instance_id": "bot"}, "40", instance_id="bot")["outcome"] == "unknown"
    assert casino.asked_before("40", casino.load(), instance_id="bot") == "SEAT-0001"


def _offered(*names):
    return {"wta_species": [{"id": n, "name": n} for n in names]}


def test_a_clone_they_refuse_is_skipped_and_the_next_species_is_tried(casino, monkeypatch, capsys):
    calls = []

    class Clone:
        @staticmethod
        def available_bots(payload):
            return [{**row, "source_type": "wta_species"} for row in payload["wta_species"]]

        @staticmethod
        def clone(source_type, source_id, name, confirm):
            calls.append(source_id)
            return {"outcome": "rejected", "http_status": 409, "response": "ALREADY_CLONED"}

    monkeypatch.setattr(casino, "_clone_script", lambda: Clone)
    monkeypatch.setattr(casino, "_read", lambda client, url: {"bots": []} if "my-bots" in url else _offered("one", "two"))
    table = [{"id": 40, "tier": "fmicro"}]
    casino.ask_next(None, casino.load(), table, [], 0)
    assert calls == ["one"]
    assert "cloned" not in capsys.readouterr().out
    casino.ask_next(None, casino.load(), table, [], 0)
    assert calls == ["one", "two"], "a species they refused is asked again, and the ones behind it never"


def test_a_timeout_while_cloning_does_not_kill_the_tick(casino, monkeypatch):
    class Clone:
        @staticmethod
        def available_bots(payload):
            return [{**row, "source_type": "wta_species"} for row in payload["wta_species"]]

        @staticmethod
        def clone(source_type, source_id, name, confirm):
            raise httpx.ReadTimeout("no answer")

    monkeypatch.setattr(casino, "_clone_script", lambda: Clone)
    monkeypatch.setattr(casino, "_read", lambda client, url: {"bots": []} if "my-bots" in url else _offered("one"))
    assert casino.ask_next(None, casino.load(), [{"id": 40, "tier": "fmicro"}], [], 0) == 0
    assert not any(r.get("type") == "clone_refused" for r in casino.load()), "a timeout is not a refusal"


def test_seat_rows_stay_readable_with_their_text(casino):
    casino._append({"type": "note", "text": "a b"})
    assert casino.load()[-1]["text"] == "a b"
    assert json.loads((state_dir() / "casino.jsonl").read_text(encoding="utf-8").splitlines()[-1])["text"] == "a b"
