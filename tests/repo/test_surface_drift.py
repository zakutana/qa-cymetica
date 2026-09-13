"""Their side, watched — because until 2026-09-12 nothing watched it.

[operator 2026-09-12] *"Dyt jsem ti rikal ze system ma byl self imprived self
optimized tak jak je mozne ze by sis toho nevsim?"* — asked after being told
that a change to Cymetica's backtest API would not be noticed.

They were right, and the proof arrived in the same hour. The DNA built the day
before finds every skill, script and hook and measures what each one did. All of
it points at **us**. The one mechanism aimed at the vendor, `lab.py surface`,
compared tool NAMES and nothing else, and only ran when a laboratory session
happened to run.

So when Cymetica fixed #97 that afternoon, the evidence of the fix —
`period.label`, `headline_period` — was **already in responses we had captured
that morning**. We had the bytes on disk. We learned about it from a Telegram
message the operator pasted.

Two kinds of change, both read from captures we already make:

  * **the contract** — a tool's parameters, defaults and required set. A rename
    here breaks a call we make, silently, at three in the morning.
  * **the shape** — which fields a response carries. A field that appears is how
    a fix announces itself before anybody writes to us; a field that vanishes is
    how a check starts measuring nothing.

Each rule below fires in one direction and stays silent in the other, for the
reason `test_reminders.py` says: a warning that is on from the first day is a
warning nobody reads.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
BASELINE = REPO / "audits" / "nexus-baseline.json"


def _processes():
    spec = importlib.util.spec_from_file_location(
        "processes_for_surface", REPO / "scripts" / "processes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tool(name, properties=None, required=None, description="x"):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object",
                            "properties": properties or {},
                            "required": required or []}}


PERIOD = {"period_days": {"type": "integer", "default": 30},
          "constituents": {"type": "array"}}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_parameter_that_moved_is_named_not_just_a_tool_that_vanished():
    """The old comparison read `t["name"]` and nothing else. Every one of these
    four changes leaves the name list identical."""
    from qa import surface

    before = [_tool("backtest_event_card_idea", PERIOD, ["constituents"])]

    same = surface.tools_drift(before, [_tool("backtest_event_card_idea", PERIOD,
                                              ["constituents"])])
    assert same["changed"] == [] and same["new"] == [] and same["gone"] == []

    renamed = surface.tools_drift(before, [_tool(
        "backtest_event_card_idea",
        {"window_days": {"type": "integer", "default": 30},
         "constituents": {"type": "array"}}, ["constituents"])])
    assert len(renamed["changed"]) == 1, renamed
    moved = renamed["changed"][0]
    assert moved["tool"] == "backtest_event_card_idea"
    assert "period_days" in str(moved) and "window_days" in str(moved)

    retyped = surface.tools_drift(before, [_tool(
        "backtest_event_card_idea",
        {"period_days": {"type": "string", "default": 30},
         "constituents": {"type": "array"}}, ["constituents"])])
    assert retyped["changed"], "a parameter that changed type is a broken call"

    now_required = surface.tools_drift(before, [_tool(
        "backtest_event_card_idea", PERIOD, ["constituents", "period_days"])])
    assert now_required["changed"], "a newly required parameter breaks our call"

    redefaulted = surface.tools_drift(before, [_tool(
        "backtest_event_card_idea",
        {"period_days": {"type": "integer", "default": 90},
         "constituents": {"type": "array"}}, ["constituents"])])
    assert redefaulted["changed"], (
        "a changed default silently changes what our numbers mean")

    # And the old behaviour is kept, not replaced.
    added = surface.tools_drift(before, [*before, _tool("brand_new_tool")])
    assert added["new"] == ["brand_new_tool"] and added["changed"] == []
    assert surface.tools_drift(before, [])["gone"] == ["backtest_event_card_idea"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_field_that_appears_in_their_answer_is_how_a_fix_announces_itself():
    """#97, exactly: `period` and `headline_period` appeared in answers we had
    already captured, and nothing looked.

    Driven through `shape_drift`, which is what the reminder actually runs
    (`processes.surface_drift` -> `drift_against` -> here). It used to drive
    `fields_drift`, a helper with no caller anywhere outside this file -- so
    gutting the appeared half of the mechanism left the check that claims "#97,
    exactly" green, and `shape_drift`'s criterion is the stricter one: a field
    counts as appeared only if EVERY recent answer now carries it and none did
    before. Asserting the loose helper while the strict one ships is a claim
    about a path the announcement never takes. 3/3, deep pass of 2026-09-13.
    """
    from qa import surface

    before = {"strategy": "x", "latest_metrics": {"sharpe_ratio": 5.1}}
    after = {"strategy": "x",
             "latest_metrics": {"sharpe_ratio": 5.1,
                                "period": {"hours": 476, "label": "19.8 days"}},
             "leaderboard": {"headline_period": "48h"}}

    was, now = surface.fields(before), surface.fields(after)
    stored = {"always": sorted(was), "seen": sorted(was)}
    current = {"always": sorted(now), "seen": sorted(now)}

    drift = surface.shape_drift(stored, current)
    appeared = " ".join(drift["appeared"])
    assert "latest_metrics.period.label" in appeared, drift
    assert "leaderboard.headline_period" in appeared, drift
    assert drift["vanished"] == []

    # One line per call, which is the form the reminder prints.
    said = surface.drift_against({"get_strategy_returns": stored},
                                 {"get_strategy_returns": current})
    assert said and "get_strategy_returns" in said[0], said
    assert "period" in " ".join(said), said

    back = surface.shape_drift(current, stored)
    assert back["vanished"] and not back["appeared"], (
        "a field that stops being sent is a check that starts measuring nothing")

    assert surface.shape_drift(current, current) == {"appeared": [],
                                                     "vanished": []}

    # A field that comes and goes is their design, not their change -- the
    # distinction `fields_drift` cannot make and the reminder depends on.
    sometimes = {"always": sorted(was), "seen": sorted(now)}
    assert surface.shape_drift(stored, sometimes) == {"appeared": [],
                                                      "vanished": []}, (
        "a field present in only some answers is weather, and a warning that "
        "fires on the weather is one nobody reads")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_reading_a_shape_does_not_depend_on_how_many_rows_came_back():
    """A listing that returns 14 bots today and 15 tomorrow has not changed
    shape. Keyed on paths, not on positions, or every poll is a drift."""
    from qa import surface

    one = {"bots": [{"slug": "a", "sharpe_ratio": 1.0}]}
    many = {"bots": [{"slug": "a", "sharpe_ratio": 1.0},
                     {"slug": "b", "sharpe_ratio": 2.0},
                     {"slug": "c", "sharpe_ratio": 3.0}]}
    assert surface.fields(one) == surface.fields(many)

    deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}}
    assert len(surface.fields(deep)) < 12, "a payload cannot make this unbounded"

    assert surface.fields(None) == set()
    assert surface.fields([1, 2, 3]) == set()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_data_used_as_keys_is_not_a_field():
    """Their `/headlines` answer keys a map by ticker: `items[].gains.EFOI`,
    `.IBN`, `.PFH`. Those are DATA. Read as fields they drift on every poll,
    and the stored shape grows by one path per ticker they have ever listed."""
    from qa import surface

    tickers = {"items": [{"gains": {"EFOI": 1.2, "IBN": 0.3, "PFH": -0.4,
                                    "DVHGF": 2.0}}]}
    paths = surface.fields(tickers)
    assert "items[].gains{}" in paths, sorted(paths)
    assert not [p for p in paths if "EFOI" in p or "DVHGF" in p], sorted(paths)

    # A record is not a map: few keys, and they read like names.
    record = {"bot": {"slug": "x", "sharpe_ratio": 1.0, "total_trades": 5}}
    assert "bot.slug" in surface.fields(record)
    assert "bot{}" not in surface.fields(record)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_a_field_that_was_always_there_can_vanish():
    """Their orderbook carries `arbitrage.buy_chain` when an arbitrage exists
    and not otherwise. Comparing one capture against one capture calls that a
    drift every time the market is quiet, and a warning that fires on the
    weather is one nobody reads.

    So a field has to have been in EVERY recent answer to count as vanished,
    and in NONE of them to count as appeared."""
    from qa import surface

    stored = {"always": ["a", "b", "c"], "seen": ["a", "b", "c", "sometimes"]}

    quiet = surface.shape_drift(stored, {"always": ["a", "b"],
                                         "seen": ["a", "b", "sometimes"]})
    assert quiet == {"appeared": [], "vanished": ["c"]}, quiet

    flicker = surface.shape_drift(stored, {"always": ["a", "b", "c"],
                                           "seen": ["a", "b", "c"]})
    assert flicker == {"appeared": [], "vanished": []}, (
        "an optional field going missing is the weather, not a change")

    fixed = surface.shape_drift(stored, {
        "always": ["a", "b", "c", "period"],
        "seen": ["a", "b", "c", "sometimes", "period"]})
    assert fixed == {"appeared": ["period"], "vanished": []}, fixed

    # Never seen before is not a drift: it is a first sighting.
    assert surface.shape_drift({}, {"always": ["a"], "seen": ["a"]}) == {
        "appeared": [], "vanished": []}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_before_snapshot_carries_the_schemas_it_is_compared_against():
    """`audits/nexus-baseline.json` is the "before" for an upgrade their CEO
    says lands within days. It held names and truncated descriptions, with the
    schemas only by reference into the evidence store — which prunes at three
    days and keeps one witness per call. The before side was days from being
    unreadable."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    tools = baseline.get("tools") or []
    assert len(tools) > 50, f"only {len(tools)} tools in the snapshot"

    with_schema = [t for t in tools if isinstance(t.get("inputSchema"), dict)]
    assert len(with_schema) == len(tools), (
        f"{len(tools) - len(with_schema)} tools carry no schema, so a changed "
        f"parameter cannot be seen against this snapshot")

    named = {t["name"]: t for t in tools}
    idea = named.get("backtest_event_card_idea")
    assert idea, "the tool the laboratory's whole search stands on is not here"
    props = (idea["inputSchema"].get("properties") or {})
    assert "constituents" in props and "period_days" in props, sorted(props)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_reminder_names_a_drift_and_is_silent_without_one():
    mod = _processes()
    now = __import__("datetime").datetime(2026, 9, 12, 20, 0,
                                          tzinfo=__import__("datetime").timezone.utc)
    facts = {"unpushed": 0, "last_pass": now.isoformat(), "week_last": now.isoformat(),
             "open_next": [], "plan_phases": []}

    quiet = mod.reminders({**facts, "surface_drift": []}, now)
    assert not [line for line in quiet if "Cymetic" in line or "změnil" in line], quiet

    loud = mod.reminders({**facts, "surface_drift": [
        "backtest_event_card_idea: period_days -> window_days",
        "GET /api/v1/backtest/leaderboard: + bots[].headline_period"]}, now)
    said = " ".join(loud)
    assert "period_days" in said and "headline_period" in said, loud


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_acknowledging_a_shape_remembers_what_was_seen_before(tmp_path,
                                                              monkeypatch):
    """`--update` must not forget, or an intermittent field never settles.

    `seen` is the memory: every field this call has EVER carried, and the thing
    `shape_drift` uses to tell "their design" from "their change". A plain
    `calls.update(seen)` replaced that memory with a 48-hour sample, so a field
    that comes and goes oscillated for ever -- vanished, acknowledged,
    appeared, acknowledged -- in the FIRST line of every session start, which
    is the line the operator is told to trust.

    `always` is the opposite kind of claim: it is about the present, so the
    newest reading replaces it.
    """
    module = _processes()
    stored = {"calls": {"GET /cards": {"always": ["id", "name"],
                                       "seen": ["id", "name", "sometimes"]}}}
    fresh = {"GET /cards": {"always": ["id", "name", "extra"],
                            "seen": ["id", "name", "extra"]}}

    merged = module.merge_shapes(stored.get("calls"), fresh)

    assert merged["GET /cards"]["seen"] == ["extra", "id", "name", "sometimes"], (
        "acknowledging a shape forgot a field the call had carried before")
    assert merged["GET /cards"]["always"] == ["extra", "id", "name"], (
        "always is a claim about the present and takes the newest reading")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_published_window_still_says_what_we_transcribed():
    """Their label, against the number we judge #86 by.

    `scripts/nexus.py::PUBLISHED_MINUTES` is `(1, 5)` because their
    `ask_nexus_deep` description said "typically takes 1-5 minutes" on
    2026-09-10, and the check that measures the channel quotes that sentence
    to them as the contract they broke. Nothing reconciled the two:
    `qa/surface.py` deliberately does not watch descriptions, because they
    reword prose. So a relabel to 5-15 minutes would have sent a FAIL to their
    tracker for an answer inside their own published window. B02, deep pass of
    2026-09-12, triage 3/3.

    And it reads THEIR words, not our copy of them. It took the description
    out of `audits/surface.json`, which is rewritten only when the operator
    runs `surface --update`, which is only prompted by `tools_drift`, which
    compares parameter shape and deliberately not descriptions -- so the
    relabel this test exists to catch produced no drift, no update, no change
    to the file, and a green here. The same incident, one level further back.
    A01, deep pass of 2026-09-13, triage 3/3: it now reads the newest capture
    of tools/list and falls back to the acknowledged copy only when there is
    no recent capture at all.

    Here rather than in tests/meta on purpose. A red there aborts the suite
    and issues no live request, which would mean the vendor rewording a
    sentence -- and the operator then doing exactly what the reminder tells
    them, `processes.py surface --update` -- kills every check we run. This is
    a disagreement between our transcription and their current words, which is
    repository consistency, and it wants fixing rather than stopping.
    """
    from tests.mcp.test_nexus_channel import _nexus, their_published_window

    theirs = their_published_window()
    if theirs is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no capture of tools/list and no acknowledged copy "
                   "carries a readable window for ask_nexus_deep, and a label "
                   "we could not read is not a label that moved",
            sources={"live": "the newest captured tools/list",
                     "fallback": "audits/surface.json"}))
        return

    conclude(Measurement(
        verdict="passed" if theirs == _nexus().PUBLISHED_MINUTES else "failed",
        reason=(f"their tool publishes {theirs[0]}-{theirs[1]} min and "
                f"scripts/nexus.py judges by "
                f"{_nexus().PUBLISHED_MINUTES[0]}-"
                f"{_nexus().PUBLISHED_MINUTES[1]}: re-transcribe "
                f"PUBLISHED_MINUTES and re-pin the check, or a verdict on #86 "
                f"quotes a window they no longer publish"
                if theirs != _nexus().PUBLISHED_MINUTES else
                f"their label and our transcription agree at "
                f"{theirs[0]}-{theirs[1]} min"),
        left={"their_label": list(theirs)},
        right={"transcribed": list(_nexus().PUBLISHED_MINUTES)},
        sources={"surface": "audits/surface.json",
                 "transcription": "scripts/nexus.py::PUBLISHED_MINUTES"}))
