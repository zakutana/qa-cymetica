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
    already captured, and nothing looked."""
    from qa import surface

    before = {"strategy": "x", "latest_metrics": {"sharpe_ratio": 5.1}}
    after = {"strategy": "x",
             "latest_metrics": {"sharpe_ratio": 5.1,
                                "period": {"hours": 476, "label": "19.8 days"}},
             "leaderboard": {"headline_period": "48h"}}

    drift = surface.fields_drift(surface.fields(before), surface.fields(after))
    appeared = " ".join(drift["appeared"])
    assert "latest_metrics.period.label" in appeared, drift
    assert "leaderboard.headline_period" in appeared, drift
    assert drift["vanished"] == []

    back = surface.fields_drift(surface.fields(after), surface.fields(before))
    assert back["vanished"] and not back["appeared"], (
        "a field that stops being sent is a check that starts measuring nothing")

    assert surface.fields_drift(surface.fields(after),
                                surface.fields(after)) == {
        "appeared": [], "vanished": []}


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
