"""A held card leg is judged at the window's end, not at the last coarse point inside it (T-0050).

The card half of T-0036/T-0039. `scripts/lab.py::verdicts` reads a card leg's index through
`series_of -> history(ref) -> _history`, which asks `interval=all`: 114 points over 44 days for
e22876b3 (median gap 9.5 h, max 10.5 h) and 272 for 2a6f5562 (median 2.9 h, max 86 h). Our own
book on the leg (`qa.lab.book_series`) is the fill point plus those points, with no point at the
window's end, because the sale comes AFTER the verdict (`record_verdict`, then `close_positions`).
So a held leg exits at the last `all` point inside its window, and `qa.lab.verdict` is
inconclusive when that point is under 19.2 h after the fill (COVERAGE_FLOOR 0.8).

Read live through our client on 2026-10-12 at about 21:20 UTC, for the first two US-hours stock
cards bought by the desk (STR-0212/0213, filled 17:27/17:28, judged from 2026-10-13 17:27 UTC):

    card       interval   points since the fill   (what the last 24 h will hold)
    e22876b3   all        1  (21:15)
    e22876b3   5d         9
    e22876b3   1d         47 (5 min)
    2a6f5562   all        2  (19:26, 21:15)
    2a6f5562   5d         9
    2a6f5562   1d         47
    sampler    default    27 each since the fill (state/samples.jsonl, 17:29 .. 21:02)

so the same window holds 1-2 points on the `all` read, 9 on `5d`, 47 on `1d` and 27 in our own
sampler rows. The sampler's rows for held cards (`scripts/sampler.py:369-380`, the default
interval) are not used by the verdict at all. The same series also feeds `sell_at_exits`, so a
take-profit or a stop crossed on a coarse stretch is noticed up to a gap late.

The fix is the session's, one function with T-0039's (`_history` is one function; `qa/` and
`scripts/` are closed to workers): read the finest interval that reaches back to the window's
start (1d / 5d / 30d / all by the window's age), never `all` for a window the finer read covers,
and say when no read covers it. Two things it must carry:

  * `tests/meta/test_pipeline_lab_loop.py::test_a_verdict_reads_the_whole_index_history_not_the_
    last_five_days` pins `_history(client, card)` asking `interval == "all"` with no window. The
    fix changes that call's contract on purpose; the test moves with it (a session edit, not a
    worker's), and so do the older fixtures that patch `_history` as `lambda client, c: ...`.
  * `formula_fingerprint()` moves with it; verdicts already written stand.

This test fakes THEIR side only (`qa.client.build_client`), not `_history`, so it holds whatever
signature the fix gives `_history`. Their answers follow the live shape: `all` is sparse and
reaches back 44 days; `1d` / `5d` / `30d` are dense and reach back that far from the read; no
interval means five days. A 1-day room, a held leg, no sale yet, read an hour after it closed
(verdicts() is run at ~20-min ticks). The index rises 100 -> 120 over the window, so the leg is
+20% gross at its end: the last `all` point inside sits 9 h before the end, a coverage of 62.5%.

Strict xfail: it fails on the ASSERTION today (the verdict is inconclusive) and turns red the day
the fix lands, when the marker must go. The control beside it passes now and must keep passing: the
same room read on a dense series is judged at +20%.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
CARD = "e22876b3-a32b-469e-8136-71ecf8b82ffb"
GAP_H = 9.5            # median gap of the `all` read for e22876b3 (max 10.5 h)
STALE_H = 9.0          # how long before the window's end the last `all` point sits
LOOKBACK_D = {"1d": 1, "5d": 5, "30d": 30, "all": 44}


def _scripts_lab(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)
    import qa.rooms

    importlib.reload(qa.rooms)
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_card_leg", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(tmp_path, name, rows):
    (tmp_path / name).write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _theirs(fill, end, now, dense_all):
    """A fake of their index-history: the index is 100 at the fill and rises to 120 at `end`."""
    def index(at):
        return 100.0 + 20.0 * (at - fill).total_seconds() / (end - fill).total_seconds()

    def points(first, step, last):
        out, at = [], first
        while at <= last:
            out.append({"t": at.isoformat(), "index": index(at)})
            at += step
        return out

    class Response:
        status_code = 200

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    class Client:
        asked: list = []

        def close(self):
            pass

        def get(self, path, params=None, **_):
            assert path.endswith(f"/event-cards/{CARD}/index-history"), path
            interval = (params or {}).get("interval") or "5d"
            self.asked.append(interval)
            back = now - timedelta(days=LOOKBACK_D[interval])
            if interval == "all" and not dense_all:
                # Sparse, and the last point inside the window sits STALE_H before its end.
                last = end - timedelta(hours=STALE_H)
                steps = int((last - back).total_seconds() // (GAP_H * 3600))
                return Response({"interval": interval, "points": points(
                    last - timedelta(hours=GAP_H * steps), timedelta(hours=GAP_H), last)})
            step = timedelta(minutes=5 if interval == "1d" else 30)
            return Response({"interval": interval, "points": points(back, step, now)})

    return Client()


def _one_day_room_with_a_held_leg(scripts_lab, tmp_path, monkeypatch, dense_all):
    import qa.rooms as qa_rooms

    _write(tmp_path, "nexus.jsonl", [
        {"type": "answer", "id": "NEX-0001", "at": "2026-10-12T17:00:00+00:00",
         "text": "Buy " + CARD + " bull, sized small. " + "reasoning. " * 40}])
    room = qa_rooms.open_strategy("NEX-0001", "one card, one day, held")
    qa_rooms.set_acceptance(room["id"], 1, None, "one day", legs=[
        {"card": CARD, "side": "bull", "share": 1.0, "tp": None, "sl": None}])
    qa_rooms.set_status(room["id"], "running", "bought on paper")
    start = datetime.fromisoformat(qa_rooms.acceptance_of(qa_rooms.load(), room["id"])["at"])
    fill = start + timedelta(seconds=34)
    _write(tmp_path, "paper.jsonl", [
        {"id": "TRD-0001", "type": "intent", "at": fill.isoformat(), "card_id": CARD,
         "usdc": 570.95, "paper": True, "nexus": {"id": "NEX-0001"}},
        {"id": "TRD-0001", "type": "outcome", "at": fill.isoformat(), "outcome": "accepted",
         "http_status": 200, "position_id": "P-1",
         "response": json.dumps({"entry_index": 100.0})}])
    end = start + timedelta(days=1)
    now = end + timedelta(hours=1)
    theirs = _theirs(fill, end, now, dense_all)
    monkeypatch.setattr("qa.client.build_client", lambda *a, **k: theirs)
    monkeypatch.setattr(scripts_lab, "_closes_at", lambda client, card: None)
    sold = []
    real_sibling, paper = scripts_lab._sibling, scripts_lab._sibling("paper")

    def sell(position, confirm):
        # What paper.close leaves behind: the sale's own intent and outcome rows.
        sold.append(position)
        with open(tmp_path / "paper.jsonl", "a", encoding="utf-8") as diary:
            diary.write(json.dumps({"id": "TRD-0002", "type": "outcome", "at": now.isoformat(),
                                    "outcome": "accepted", "http_status": 200}) + "\n")
        return {"id": "TRD-0002"}

    paper.close = sell
    monkeypatch.setattr(scripts_lab, "_sibling",
                        lambda name: paper if name == "paper" else real_sibling(name))
    return room["id"], now, theirs, sold


@pytest.mark.xfail(strict=True, reason="a held card leg exits at the last `interval=all` point inside "
                   "its window, 9 h stale and 62.5% covered, so the verdict is inconclusive (T-0050)")
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_held_card_leg_is_judged_at_the_end_of_its_window_not_at_a_coarse_point(
        tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, now, theirs, sold = _one_day_room_with_a_held_leg(
        scripts_lab, tmp_path, monkeypatch, dense_all=False)

    said = scripts_lab.verdicts(now=now)

    (verdict,) = [s for s in said if s.get("room") == room]
    # Today: inconclusive at 62% -- "the index covers 62% of the window", a gap read as unfit.
    assert verdict["verdict"] == "survived", (verdict, theirs.asked)
    assert verdict["coverage"] >= 0.95, verdict
    (leg,) = verdict["legs"]
    # +20% at the window's end; the last `all` point inside would have said +12.5%.
    assert leg["gross_return_pct"] == pytest.approx(20.0, abs=0.5), leg


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_control_the_same_room_on_a_dense_series_is_judged_at_its_end(tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    room, now, theirs, sold = _one_day_room_with_a_held_leg(
        scripts_lab, tmp_path, monkeypatch, dense_all=True)

    said = scripts_lab.verdicts(now=now)

    (verdict,) = [s for s in said if s.get("room") == room]
    assert verdict["verdict"] == "survived", (verdict, theirs.asked)
    (leg,) = verdict["legs"]
    assert leg["gross_return_pct"] == pytest.approx(20.0, abs=0.5), leg
    assert sold == ["P-1"], "the verdict sells the position after it is written"
