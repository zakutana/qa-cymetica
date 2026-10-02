"""Every real request to their host is timed, and one command lists the bad ones.

2026-09-28: Cymetica asked for "the UTC time of any timeout" to match their
logs. We had 77 since 26 Sep -- in seven diaries and a run record, found by a
one-off script -- and no response time for ~90% of what the evidence store
kept: `response.elapsed` exists only after the client has closed the
response, and `EvidenceStore.capture()` runs inside the transport, before.

So `SafetyTransport` times each request itself -- a success, a timeout, a
body that could not be read -- into `state/timings.jsonl`, and
`scripts/timeouts.py` lists every timeout and every slow answer, with the old
diaries beside it. Only a request that reached the real network is written:
a test's MockTransport, or a guard's negative control, never is. A side
effect on by default fired by accident here before (98 of 137 journal
events came from test runs).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


class _Real(httpx.HTTPTransport):
    """Stands in for the network: an HTTPTransport, so it counts as real."""

    def __init__(self, answer):
        super().__init__()
        self.answer = answer

    def handle_request(self, request):
        if isinstance(self.answer, Exception):
            raise self.answer
        return httpx.Response(self.answer, content=b"{}", request=request)


def _rows(tmp_path):
    p = tmp_path / "timings.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_real_request_is_timed_and_one_command_lists_the_bad_ones(
        tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTransport

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        def client(inner):
            kwargs = {"transport": SafetyTransport(inner, EndpointRegistry.load()),
                      "base_url": "https://cymetica.com"}
            import qa.client as qc
            if qc._GUARD_INSTALLED:
                kwargs["_qa_factory"] = qc._FACTORY_SENTINEL
            return httpx.Client(**kwargs)

        with client(_Real(200)) as c:
            assert c.get("/llms.txt?key=secret").status_code == 200
        with client(_Real(httpx.ReadTimeout("timed out"))) as c:
            with pytest.raises(httpx.ReadTimeout):
                c.get("/openapi-public.json")
        with client(httpx.MockTransport(lambda r: httpx.Response(200))) as c:
            c.get("/not-the-network")
        # Deep pass 2026-10-02 (T09): a request our own guard REFUSES, through a REAL
        # transport, never reached the network and is not timed. If the timing moved above
        # `_check`, it would be written with error SafetyViolation, and `timeouts.py`
        # lists every row with an error -- as the minute of a timeout, to Cymetica.
        from qa.safety import SafetyViolation

        with client(_Real(200)) as c:
            with pytest.raises(SafetyViolation):
                c.post("/api/v1/never-listed-write", json={"x": 1})
    finally:
        CURRENT_TIER.reset(token)

    rows = _rows(tmp_path)
    assert [(r["path"], r["status"], r["error"]) for r in rows] == [
        ("/llms.txt", 200, None), ("/openapi-public.json", None, "ReadTimeout")], rows
    assert all(isinstance(r["ms"], int) and r["at"].endswith("+00:00") for r in rows), rows
    assert "secret" not in json.dumps(rows), "a query string reached the diary"

    # One command: the timeout above, and one from an older diary, in order.
    (tmp_path / "samples.jsonl").write_text(json.dumps(
        {"type": "tick", "at": "2026-01-01T00:00:00+00:00", "ok": False,
         "reads": {"bots": "timeout"}, "seconds": 91.0}) + "\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("timeouts_mod", REPO / "scripts" / "timeouts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # B05, deep pass of 2026-09-30 (3/3): and a slow answer is listed while a
    # fast one is not -- the list goes to Cymetica as "the minute of each
    # timeout", so a healthy request in it is a false claim.
    with (tmp_path / "timings.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": "2026-09-30T00:00:00+00:00", "method": "GET",
                             "path": "/slow-page", "status": 200, "error": None,
                             "ms": 12000}) + "\n")
    listed = mod.collect(since="2026-01-01", slow_s=10.0)
    assert [row[1].split()[0] for row in listed][:1] == ["sampler"], listed
    assert any("/openapi-public.json" in row[1] and "ReadTimeout" in row[2]
               for row in listed), listed
    assert any("/slow-page" in row[1] and "12.0 s" in row[2] for row in listed), (
        "an answer of 12 s was not listed as slow", listed)
    assert not any("/llms.txt" in row[1] for row in listed), (
        "a fast 200 was listed among the timeouts and slow answers", listed)
    assert listed == sorted(listed), "not in time order"
