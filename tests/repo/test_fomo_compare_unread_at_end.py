"""Hot against control counts only paths read to the end of the readout's window (deep pass 2026-10-25,
M04).

`qa/fomo.py::compare` judged every closed window on the peak over what was READ, so a path the loop
stopped reading partway (the console closed, a round skipped) counted as a miss: its peak over twelve
hours set against a 24 h question. `stop_study` (RM05, `unread_at_end`) and `ten_dollars`
(`unread_at_24h`) have left such paths out since 2026-09-24; `compare`, which the hot/control readouts
and tests/rest/test_fomo_calibration_reproduces.py stand on, did not. Left out uniformly -- a partial
path with an early hit too: keeping the hits seen early and dropping the misses not yet seen is the
open-window bias the docstring already names.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa import fomo
from qa.marks import SafetyTier, qa

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
NOW = T0 + timedelta(days=10)


def _path(token, prices_by_hour, at=T0):
    key = f"{token}:{at:%Y-%m-%dT%H}"
    rows = [{"type": "signal", "key": key, "at": at.isoformat(), "token_address": token,
             "price_usd": 1.0}]
    for hours, price in prices_by_hour.items():
        rows.append({"type": "checkpoint", "key": key, "horizon": f"{hours:g}h",
                     "at": (at + timedelta(hours=hours)).isoformat(), "price_usd": price})
    return rows


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_path_read_partway_is_left_out_not_counted_a_miss():
    rows = (_path("whole", {h: 1.2 for h in range(1, 25)})                 # read to 24 h, a miss
            + _path("stopped", {h: 1.1 for h in range(1, 13)})             # read to 12 h only
            + _path("early", {1: 1.1, 3: 2.5, 6: 1.4})                     # a hit, then nothing
            + _path("delisted", {**{h: 1.3 for h in range(1, 24)}, 24: None}))  # read at 24 h, no price
    said = fomo.compare(rows, multiple=2.0, within_hours=24.0, now=NOW, require_depth=False)
    hot = said["hot"]
    assert hot["excluded"].get("unread_at_end") == 2, (
        f"two paths the loop stopped reading were judged on a part of the window: {hot}")
    assert (hot["n"], hot["hits"]) == (2, 0), hot


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_end_is_the_readouts_own_and_the_study_rows_reach_it():
    """At 6 h the 12-hour path is whole; at 72 h a path is whole only with the study's 72 h reading."""
    rows = _path("twelve", {h: 1.1 for h in range(1, 13)})
    six = fomo.compare(rows, multiple=1.5, within_hours=6.0, now=NOW, require_depth=False)
    assert (six["hot"]["n"], six["hot"]["excluded"].get("unread_at_end")) == (1, 0), six["hot"]

    key = rows[0]["key"]
    study = [{"type": "study", "group": "hot", "key": key, "horizon": f"{h}h",
              "at": (T0 + timedelta(hours=h)).isoformat(), "price_usd": 1.0}
             for h in range(30, 73, 6)]
    whole = _path("long", {h: 1.1 for h in range(1, 25)})
    long_key = whole[0]["key"]
    whole += [{"type": "study", "group": "hot", "key": long_key, "horizon": f"{h}h",
               "at": (T0 + timedelta(hours=h)).isoformat(), "price_usd": 1.0}
              for h in range(30, 73, 6)]
    three = fomo.compare(rows + study[:-1] + whole, multiple=3.0, within_hours=72.0, now=NOW,
                         require_depth=False)
    assert three["hot"]["n"] == 1 and three["hot"]["excluded"].get("unread_at_end") == 1, three["hot"]
