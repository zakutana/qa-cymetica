"""STATS: the two things the operator reads the page for, each checked.

2026-09-11, the operator on the Stats tab: only Rewards and Defects fixed said
anything at a glance; the rest was a table and a paragraph. They wanted to see
how reliable Nexus is next to Telegram -- which to them is the channel that
always answers -- and they said they read pictures, not text. And on the
Findings tab every bug's name was its whole description.

Two derivations came out of that and both are pinned here, because a picture
is only as honest as the numbers under it.

  * NEXUS was not on the panel at all. Its row now counts every question once,
    by what actually happened to it, and the typical time is taken ONLY over
    questions we watched from the start. The rest have an upper bound at best
    -- see tests/meta/test_pipeline_nexus.py and the memory
    `a-first-look-is-an-upper-bound-not-a-latency`, which is what reporting a
    pickup delay as their latency cost us once already.
  * A finding's HEADLINE is the name of the check that found it, humanised.
    The check's name is the invariant in a few words, which is exactly "what
    are you testing"; the measured sentence stays underneath as the detail.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_render import _committed_payload, _render


def _question(qid, t0, accepted=True, polls=(), answer=None, gave_up=False):
    rows = [{"id": qid, "type": "question", "at": t0.isoformat(),
             "accepted": accepted}]
    for offset, status in polls:
        rows.append({"id": qid, "type": "poll", "status": status,
                     "at": (t0 + timedelta(seconds=offset)).isoformat()})
    if answer is not None:
        last = polls[-1][0] if polls else 0
        rows.append({"id": qid, "type": "answer", "text": answer,
                     "at": (t0 + timedelta(seconds=last)).isoformat()})
    if gave_up:
        rows.append({"id": qid, "type": "gave_up", "status": "running",
                     "at": (t0 + timedelta(seconds=600)).isoformat()})
    return rows


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_row_counts_each_question_by_what_happened_to_it(
        tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    t0 = datetime.fromisoformat("2026-09-11T05:00:00+00:00")
    full = "x" * 400
    rows = (
        # watched from the start: running at 100 s, done at 130 s
        _question("NEX-1", t0, polls=((100, "running"), (130, "done")),
                  answer=full)
        # asked, looked at once, fourteen minutes later: an upper bound only
        + _question("NEX-2", t0, polls=((800, "done"),), answer=full)
        # our loop gave up on it
        + _question("NEX-3", t0, polls=((60, "running"),), gave_up=True)
        # refused before an investigation started -- QUERY_RESTRICTED
        + _question("NEX-4", t0, accepted=False)
        # finalised "done" with only an opening sentence -- their NEX-0009
        + _question("NEX-5", t0, polls=((50, "running"), (70, "done")),
                    answer="I'll verify the actual surface first.")
    )
    (tmp_path / "nexus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    channel = _render()._nexus_channel()

    assert [q["outcome"] for q in channel["questions"]] == [
        "answered", "answered", "failed", "refused", "partial"]
    assert (channel["asked"], channel["answered"], channel["partial"],
            channel["failed"], channel["refused"]) == (5, 2, 1, 1, 1)
    # Only NEX-1 and NEX-5 were watched: midpoints 115 s and 60 s. NEX-2's
    # 800 s is when we looked, and must not drag the typical time to 8 min.
    assert channel["measured"] == 2
    assert channel["median_seconds"] == 87.5, channel["median_seconds"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_row_is_empty_not_invented_when_nothing_was_asked(
        tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    channel = _render()._nexus_channel()
    assert channel["asked"] == 0 and channel["questions"] == []
    assert channel["median_seconds"] is None, (
        "no watched question is no typical time, not a zero")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_finding_headline_says_what_is_tested_in_a_few_words():
    render = _render()
    assert render._headline({
        "id": "CYM-a_bot_counts_the_stakes_it_has_open",
        "checks": ["tests/rest/test_clone_books_its_open_positions.py"
                   "::test_a_bot_counts_the_stakes_it_has_open"],
    }) == "A bot counts the stakes it has open"
    assert render._headline({
        "checks": ["tests/pinned/test_documented_404.py"
                   "::test_documented_path_is_served[/api/v1/vaix/prices]"],
    }) == "Documented path is served: /api/v1/vaix/prices"
    # Old rows carry no check; their id is the only name they have.
    assert render._headline({"id": "CYM-anon-tool-surface", "checks": []}) \
        == "Anon tool surface"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_finding_on_the_page_has_a_short_headline(monkeypatch):
    """Shorter than the sentence it heads, or it is not a headline."""
    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    findings = _committed_payload(_render())["findings"]
    assert findings, "no committed rows, so this proves nothing"
    long = [(f["id"], f.get("headline")) for f in findings
            if not f.get("headline") or len(f["headline"]) > 90]
    assert not long, f"headlines missing or longer than 90 characters: {long[:5]}"
