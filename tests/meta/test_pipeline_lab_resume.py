"""What a loop tick has to be told before it can decide anything.

[operator 2026-09-13] *"chci at je genericky ne ze v nem pisu lab-0004 chci
nejaky komand co budu pokazde stejny psat a ty sam si zrcis co jdes delat
proste zjistis kde jsi skoncil a pojracujes v pruzkuku"*

So the prompt they type never changes and never names a session. `lab.py
resume` is the one call that answers "where did I stop", and `due()` is the
part of it that can be wrong in a way nobody notices: a tick that is told
nothing is due does nothing, and looks exactly like a tick with nothing to do.

Ordered by what a tick should reach for first. Time-gated work expires -- a
checkpoint not taken at its horizon is a hole in the measurement that cannot
be filled later -- so it outranks a sweep, which is only ever cheaper to do
tomorrow.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa.marks import SafetyTier, qa

from qa import lab

NOW = datetime(2026, 9, 13, 13, 0, tzinfo=timezone.utc)


def _signal(key: str, hours_ago: float) -> dict:
    return {"type": "signal", "key": key,
            "at": (NOW - timedelta(hours=hours_ago)).isoformat()}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_ripe_checkpoint_is_the_first_thing_a_tick_is_told():
    """The only work here that expires. Everything else waits."""
    # Just past its sixth hour, so hour 6 is ripe and the five before it are
    # gone for good -- since 2026-09-13 a horizon is offered only while it is
    # still near, or resolve() would file the current price under an hour it
    # was never read at.
    rows = [_signal("0xa:2026-09-13T06", hours_ago=6.2)]
    out = lab.due(now=NOW, fomo_rows=rows, tournament={}, open_findings=0)
    assert out, "a ripe checkpoint produced no item at all"
    assert "fomo_watch" in out[0]["run"], out
    assert out[0]["why"].startswith("1 memecoin"), out[0]["why"]

    # And a signal whose marks have all gone by is not endless work.
    stale = [_signal("0xb:2026-09-13T00", hours_ago=12.9)]
    out = lab.due(now=NOW, fomo_rows=stale, tournament={}, open_findings=0)
    assert not any("fomo_watch" in i["run"] for i in out), out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_ripe_is_not_nothing_to_do():
    """The failure this exists to prevent: a tick told 'nothing due' stops,
    and stopping looks identical to having finished. There is always the
    exploration the operator asked the loop to continue."""
    rows = [_signal("0xa:2026-09-13T12", hours_ago=0.2)]
    out = lab.due(now=NOW, fomo_rows=rows, tournament={}, open_findings=0)
    assert out, "a quiet tick must still be handed the standing work"
    assert any("search" in item["run"] for item in out), out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unentered_open_round_is_named_and_an_entered_one_is_not():
    live = {"round": {"round_anchor": "2026-09-11", "entries_open": True},
            "my_entries": []}
    out = lab.due(now=NOW, fomo_rows=[], tournament=live, open_findings=0)
    assert any("movers" in item["run"] for item in out), out

    entered = {**live, "my_entries": [{"round_anchor": "2026-09-11"}]}
    out = lab.due(now=NOW, fomo_rows=[], tournament=entered, open_findings=0)
    assert not any("movers" in item["run"] for item in out), out

    # A round whose entries have closed is not something a tick can act on,
    # even unentered -- their entries_close_at landed 2026-09-13.
    shut = {"round": {"round_anchor": "2026-09-11", "entries_open": False},
            "my_entries": []}
    out = lab.due(now=NOW, fomo_rows=[], tournament=shut, open_findings=0)
    assert not any("movers" in item["run"] for item in out), out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_finding_owed_a_verification_outranks_exploration():
    """Their fix is a claim until a level-V run says otherwise (rule 7), and
    a claim left unverified is the one thing here with a deadline of theirs
    rather than ours."""
    out = lab.due(now=NOW, fomo_rows=[], tournament={}, open_findings=3)
    assert "verify" in out[0]["run"], out
    assert "3" in out[0]["why"], out[0]["why"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_item_carries_a_command_and_a_reason():
    """A tick that cannot see WHY something is due re-derives it, wrongly."""
    rows = [_signal("0xa:2026-09-13T06", hours_ago=25.0)]
    live = {"round": {"round_anchor": "2026-09-11", "entries_open": True},
            "my_entries": []}
    for item in lab.due(now=NOW, fomo_rows=rows, tournament=live,
                        open_findings=2):
        assert item["run"] and item["why"], item
        assert not item["run"].startswith(" "), item
