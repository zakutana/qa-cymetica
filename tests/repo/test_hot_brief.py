"""The Hot block of `lab.py brief`: does anything pass NEX-0055 at all?

NEXT.md, agreed 2026-09-21: the brief carries how many Hot entries pass
Nexus's rule, over what stretch, and -- when almost nothing does -- says so
with the number, so the laboratory can take that number to him. The pass
counts are the ones `hot_watch.reading()` already stores; nothing here
re-derives them. What is new is the denominator: the hours the watch could
have SEEN an entry, not the calendar between the first and the last round
(on 2026-09-27 the diary held 167 rounds over 6.4 days, a third of a
20-minute cadence).
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa import hot
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _module():
    spec = importlib.util.spec_from_file_location(
        "hot_watch_brief", REPO / "scripts" / "hot_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _round(minutes, hot_rows=()):
    return {"type": "round", "at": (T0 + timedelta(minutes=minutes)).isoformat(),
            "ok": True, "errors": [],
            "hot": None if hot_rows is None else list(hot_rows), "wire": []}


def _rules(n55=2, n57=13, unobserved=12, closed=0):
    none = {"open": 0, "skipped_overlap": 1, "mean_net": None, "t": None}
    out = {"NEX-0055": {**none, "entries": n55, "unobserved": n55, "n": 0,
                        "skipped_overlap": 0,
                        "verdict": "not yet: 0 of 100 trades"}}
    for v in "abcd":
        out[f"NEX-0057{v}"] = {**none, "entries": n57, "unobserved": unobserved,
                               "n": closed,
                               "verdict": f"not yet: {closed} of 100 trades"}
    return out


def _reading(**kw):
    """The shape `lab.note_hot_reading` stored on 2026-09-27 19:32."""
    said = {"rounds": 167, "first": "2026-09-21T08:52:26+00:00",
            "last": "2026-09-27T19:24:07+00:00",
            "entries": {"crypto": 195, "stocks": 306},
            "follow": {}, "control": {}, "cards": {}, "rules": _rules()}
    said.update(kw)
    return said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_watched_hours_count_only_the_stretches_an_entry_could_be_seen_in():
    """Two covered steps of 20 minutes, a 160-minute hole, one more covered
    step, then a failed hot read: 1.0 h. The hole and the blind round are not
    watching, exactly as `entries()` does not call an entry across them."""
    rows = [_round(0), _round(20), _round(40), _round(200), _round(220),
            _round(240, hot_rows=None)]

    assert hot.watched_hours(rows) == 1.0
    assert hot.watched_hours([]) == 0.0
    assert _module().reading(rows)["watched_hours"] == 1.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_almost_nothing_passing_is_said_with_the_number_for_nexus():
    """The stored reading of 2026-09-27: 2 and 13 of 195 crypto entries. Over
    48 watched hours, 13 a day at best puts his 100 trades about 15 days out;
    NEX-0055 alone about 100. Past ALMOST_NOTHING_DAYS it is said, with the
    number. The 12 unobserved are ours -- no round priced the exit -- and are
    said apart, never as his rule's fault."""
    mod = _module()
    lines = mod.say_passing(_reading(watched_hours=48.0))
    text = "\n".join(lines)

    assert "NEX-0055 2 (1.0%)" in text, text
    assert "NEX-0057a/b/c/d 13 (6.7%)" in text, text
    assert "of 195 crypto entries" in text, text
    assert "48 h watched" in text, text
    # 13 per 2 watched days is 6.5 a day, 100 trades ~15 d: under the bar.
    assert "ALMOST NOTHING" not in text, text

    sparse = "\n".join(mod.say_passing(_reading(watched_hours=240.0)))
    # 13 per 10 watched days: ~77 d to his 100 trades -- past the bar.
    assert "ALMOST NOTHING PASSES" in sparse, sparse
    assert "~77 watched d" in sparse, sparse
    assert "12 of 13" in sparse and "ours" in sparse, sparse


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_reading_stored_before_watched_hours_gives_counts_and_no_pace():
    """Every reading already in the notebook lacks `watched_hours`. The counts
    stand, over the window first..last, and the line says which -- but no
    pace and no verdict: on 2026-09-28 the diary's 7.2-day window held 35
    watched hours, and the window put his 100 trades 56 days away where the
    watched hours put them 11. The window would send him a false "almost
    nothing"."""
    mod = _module()
    text = "\n".join(mod.say_passing(_reading()))

    assert "6.4 d window" in text, text
    assert "ALMOST NOTHING" not in text, text
    assert "pace unknown" in text, text
    # Nothing passing at all is the plainest case of almost nothing.
    none = "\n".join(mod.say_passing(_reading(rules=_rules(0, 0, 0))))
    assert "ALMOST NOTHING PASSES" in none, none
    assert mod.say_passing({}) == []
