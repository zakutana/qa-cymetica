"""NOTES: the doors around what the Nexus tab serves and, from P2, accepts.

The rooms carry the operator's own notes, so they are served to this machine
by name and to nothing else. The console binds 127.0.0.1, but a page on any
site can resolve a hostname of its own to 127.0.0.1 and then read from it as
if it were same-origin -- DNS rebinding. What such a request cannot fake is the
Host header its browser sends, which names the attacker's domain. So the check
is on the name, and the positive control beside it proves the route itself
works, because a refusal from a broken route would pass the negative half.

In tests/meta and not tests/repo: these are guards, and a red guard is meant to
stop the session.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import shutil
import threading

import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_render import REPO


def _serve_module():
    spec = importlib.util.spec_from_file_location(
        "serve_room_notes", REPO / "scripts" / "serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def console(tmp_path, monkeypatch):
    """A real server on a free port, over a copy of the committed state."""
    state = tmp_path / "state"
    shutil.copytree(REPO / "state", state, ignore=shutil.ignore_patterns("*.lock"))
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    serve = _serve_module()
    live = serve.Live()
    server = serve.SingleServer(("127.0.0.1", 0), serve.make_handler(live))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"port": server.server_address[1], "state": state, "live": live}
    finally:
        server.shutdown()
        server.server_close()


def _get(port: int, path: str, host: str) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        conn.request("GET", path, headers={"Host": host})
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rooms_are_served_to_this_machine_and_refused_to_any_other_name(console):
    port = console["port"]
    for host in (f"127.0.0.1:{port}", f"localhost:{port}"):
        status, body = _get(port, "/rooms.json", host)
        assert status == 200, f"{host}: the rooms route itself does not work ({status})"
        assert "general" in [r["id"] for r in json.loads(body)["rooms"]]

    for host in (f"evil.example:{port}", "evil.example", f"127.0.0.1:{port + 1}", ""):
        status, body = _get(port, "/rooms.json", host)
        assert status == 403, (
            f"Host {host!r} was answered with {status}: a page on another site "
            f"could read the operator's notes through a rebound DNS name")
        assert b"general" not in body
