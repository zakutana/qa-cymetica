"""The sampler keeps our own record of the benchmark every running room is judged against (OP-0018, 5).

Their index-history windows all end at now, so what a read can say about a moment drifts coarser
as the moment ages: the BTC proxy's 5d read covered STR-0212/0213's buy (2026-10-12 17:27) only
until 2026-10-17 17:27, then 30d at ~3 h a point. The sampler had a record of the proxy only from
2026-09-11 to 09-23, while a plan named it. So it follows the `benchmark_card` of every RUNNING
room the way it follows a held card -- described, and its index points written once each -- and
that record outlives the five days any later read can give. The verdict itself still reads live.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
BTC = "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161"
STOPPED = "5e7a5e7a-0000-4000-8000-000000000001"
PROPOSED = "0b0b0b0b-0000-4000-8000-000000000002"
LEG = "e22876b3-a32b-469e-8136-71ecf8b82ffb"


def _sampler(state_dir: Path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(state_dir))
    spec = importlib.util.spec_from_file_location(
        "sampler_benchmark_under_test", REPO / "scripts" / "sampler.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _room(room, benchmark, status, at="2026-10-12T17:27:00+00:00"):
    rows = [{"type": "strategy", "id": room, "origin": "NEX-0001", "title": room, "at": at},
            {"type": "acceptance", "room": room, "window_days": 1.0, "stop_pct": 10.0,
             "legs": [{"card": LEG, "side": "bull", "share": 1.0}],
             "benchmark_card": benchmark, "adopted": True, "why": "test", "at": at}]
    if status:
        rows.append({"type": "status", "room": room, "status": status, "why": "test", "at": at})
    return rows


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_benchmark_of_a_running_room_is_followed_like_a_held_card(tmp_path, monkeypatch):
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    sampler = _sampler(tmp_path, monkeypatch)
    rows = (_room("STR-0001", BTC, "running") + _room("STR-0002", STOPPED, "stopped")
            + _room("STR-0003", PROPOSED, None))
    (tmp_path / "rooms.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows),
                                          encoding="utf-8")

    followed = sampler.follow()
    assert followed["benchmarks"] == [BTC], (
        "only a RUNNING room's benchmark is ours to follow", followed)

    seen = []
    points = {"interval": "5d", "points": [{"t": "2026-10-12T17:00:00+00:00", "index": 100.0},
                                           {"t": "2026-10-12T17:30:00+00:00", "index": 100.4}]}

    def answer(request):
        seen.append((request.method, request.url.path))
        path = request.url.path
        if path == f"/api/v1/event-cards/{BTC}/index-history":
            return httpx.Response(200, json=points)
        if path == f"/api/v1/event-cards/{BTC}":
            return httpx.Response(200, json={"id": BTC, "title": "Bitcoin", "status": "live",
                                             "basket": [{"symbol": "BTC", "weight": 0.999}]})
        return httpx.Response(404, json={"detail": "not found"})
    client = build_client(identities()["anon"], EndpointRegistry.load(),
                          base_url="https://cymetica.com", inner=httpx.MockTransport(answer))

    first = sampler.tick(client, every=600)
    assert {method for method, _ in seen} == {"GET"}, seen
    paths = {path for _, path in seen}
    assert f"/api/v1/event-cards/{BTC}/index-history" in paths, paths
    assert not any(STOPPED in p or PROPOSED in p for p in paths), (
        "a stopped or proposed room's benchmark was read", paths)
    (index,) = [r for r in first if r["type"] == "index" and r["card_id"] == BTC]
    assert [p[1] for p in index["points"]] == [100.0, 100.4]
    (card,) = [r for r in first if r["type"] == "card" and r["card_id"] == BTC]
    assert card["basket"] == [{"symbol": "BTC", "weight": 0.999}], (
        "the proxy's basket is what makes it BTC; a change to it must be on record")

    # Written once: the next round adds only the point that is new.
    points["points"].append({"t": "2026-10-12T18:00:00+00:00", "index": 100.9})
    again = sampler.tick(client, every=600)
    (index,) = [r for r in again if r["type"] == "index" and r["card_id"] == BTC]
    assert index["points"] == [["2026-10-12T18:00:00+00:00", 100.9]], index
