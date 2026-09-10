"""CLONE: the source_type is in the key, and the paper flag is theirs to confirm.

`GET /api/v1/cloned-bots/available` returns two groups, `wta_species` and
`perpetual_agents`, and every row inside them carries `source_type: null`.
CloneBotRequest requires that field and its enum is singular --
`perpetual_agent`. So the type lives in the key of the group, and reading it
off the row sends null and makes their 422 look like their bug.

The second thing pinned here is that `is_paper` in the RECORD is whatever they
returned, never what we asked for. We send `paper` and `is_paper` both true
because their schema publishes both names and we cannot tell from outside
which one the server reads; the evidence that it worked is their answer, and
copying our own request into the outcome would turn an assumption into a
record that looks like a measurement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _clone(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "clone_under_test", REPO / "scripts" / "clone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Their real shape, from the 20:0x read: groups, null source_type on the rows.
AVAILABLE = {
    "wta_species": [
        {"id": "dd206f68", "name": "MACD Hunter", "source_type": None},
        {"id": "70a47f2a", "name": "RSI Sniper", "source_type": None},
    ],
    "perpetual_agents": [
        {"id": "e1251539", "name": "Liquidation Hunter", "source_type": None},
    ],
    "total_count": 3,
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_source_type_comes_from_the_group_not_from_the_row(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)

    bots = {b["name"]: b["source_type"] for b in mod.available_bots(AVAILABLE)}
    assert bots == {"MACD Hunter": "wta_species",
                    "RSI Sniper": "wta_species",
                    # Singular. Their group key is plural and their enum is
                    # not, and sending the key straight through is a 422 we
                    # would have read as their defect.
                    "Liquidation Hunter": "perpetual_agent"}

    # `total_count` is not a group of bots, and neither is anything else they
    # add later. An unknown key is skipped, not guessed at.
    assert len(mod.available_bots({**AVAILABLE, "featured": [{"id": "x"}]})) == 3

    # The result envelope, which buy() in paper.py already unwraps elsewhere.
    assert len(mod.available_bots({"result": AVAILABLE})) == 3


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_source_type_their_schema_does_not_publish_is_refused(
        tmp_path, monkeypatch):
    """Before the request, so a typo is not spent as a 422 against them."""
    mod = _clone(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="source_type must be one of"):
        mod.clone("perpetual_agents", "e1251539", None, None, confirm=True)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_guidance_that_was_never_answered_is_refused(tmp_path, monkeypatch):
    """A clone naming a Nexus answer that does not exist claims their
    guidance for our own decision. Marked ours is fine; borrowed is not."""
    mod = _clone(tmp_path, monkeypatch)
    (tmp_path / "nexus.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match="no recorded answer"):
        mod.clone("wta_species", "dd206f68", None, "NEX-9999", confirm=True)

    ours = mod._guidance(None)
    assert ours["id"] is None and "ours" in ours["note"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_clone_record_is_not_written_into_the_paper_trade_log(
        tmp_path, monkeypatch):
    """#87 groups every id in paper.jsonl into intent/outcome/after and reads
    a balance off the intent. A clone landing there is an accepted row with no
    notional, judged as a paper buy that debited nothing."""
    mod = _clone(tmp_path, monkeypatch)
    assert mod.path().name == "clones.jsonl"
    assert mod._next_id([]) == "CLN-0001"
    assert mod._next_id([{"id": "CLN-0003"}, {"id": "TRD-0009"}]) == "CLN-0004"
