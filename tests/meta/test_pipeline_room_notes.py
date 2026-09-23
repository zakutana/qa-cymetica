"""NOTES: the doors around what the Nexus tab serves and accepts.

The rooms carry the operator's own notes, so they are served to this machine
by name and to nothing else. The console binds 127.0.0.1, but a page on any
site can resolve a hostname of its own to 127.0.0.1 and then read from it as
if it were same-origin -- DNS rebinding. What such a request cannot fake is the
Host header its browser sends, which names the attacker's domain.

POST /notes is the console's first write path, and every door around it is
held here:

  * a token minted at launch, handed out at /token to this machine only and
    never written into any page, so no page served before a restart can hold
    a stale one and nothing on disk can leak it;
  * Host and Origin both naming this machine;
  * a JSON body, which no cross-site form can send without a preflight the
    server never answers;
  * exactly {room, text}, into a room that exists, 1..4000 characters;
  * and notes off entirely when the console listens beyond this machine.

Each refusal is asserted by the file NOT existing afterwards -- a negative
control that does not need the writer it tests -- and a positive control
beside them proves the writer works, because a refusal from a broken route
would pass every negative half.

In tests/meta and not tests/repo: these are guards, and a red guard is meant to
stop the session.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import shutil
import subprocess
import threading

import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_render import REPO

TOKEN = "test-token-" + "x" * 32


def _serve_module():
    spec = importlib.util.spec_from_file_location(
        "serve_room_notes", REPO / "scripts" / "serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start(tmp_path, monkeypatch, note_token):
    """A real server on a free port, over a copy of the committed state."""
    state = tmp_path / "state"
    # The committed state, which the rooms' two files are not. Copying this
    # machine's rooms.jsonl too broke every assertion here the moment real
    # rooms were written to it (2026-09-11): "nothing is written" found a file.
    shutil.copytree(REPO / "state", state, ignore=shutil.ignore_patterns(
        "*.lock", "rooms.jsonl", "samples.jsonl"))
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    serve = _serve_module()
    live = serve.Live()
    server = serve.SingleServer(("127.0.0.1", 0),
                                serve.make_handler(live, note_token=note_token))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, {"port": server.server_address[1], "state": state,
                    "live": live, "serve": serve}


@pytest.fixture
def console(tmp_path, monkeypatch):
    server, info = _start(tmp_path, monkeypatch, TOKEN)
    try:
        yield info
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def exposed(tmp_path, monkeypatch):
    """The same console as started with --host 0.0.0.0: it holds no token."""
    server, info = _start(tmp_path, monkeypatch, None)
    try:
        yield info
    finally:
        server.shutdown()
        server.server_close()


def _request(port: int, method: str, path: str, headers: dict,
             body: bytes | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def _get(port: int, path: str, host: str, origin: str | None = None):
    headers = {"Host": host}
    if origin:
        headers["Origin"] = origin
    status, _, body = _request(port, "GET", path, headers)
    return status, body


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_page_is_served_to_this_machine_with_its_note_box(console):
    """/lab (plan v2, V4): the laboratory's page, rendered on request. It
    carries the rooms' composer, since a note from it is the one write the
    page may make; like the rooms, it is served to this machine by name."""
    port = console["port"]
    status, body = _get(port, "/lab", f"127.0.0.1:{port}")
    page = body.decode("utf-8")
    assert status == 200, page[:300]
    assert "<title>Laboratoř</title>" in page
    assert 'id="compose"' in page and 'fetch("/notes"' in page.replace("'", '"')
    assert (console["state"] / "lab" / "report.json").is_file(), (
        "the page drew products that no report was written for")
    status, _ = _get(port, "/lab", f"evil.example:{port}")
    assert status == 403, "the laboratory went to a host that is not this machine"
    # The view it redraws from, the same doors.
    status, body = _get(port, "/lab.json", f"127.0.0.1:{port}")
    assert status == 200 and [s["key"] for s in json.loads(body)["sectors"]] == [
        "cards", "bots", "memecoins", "funds"]
    status, _ = _get(port, "/lab.json", f"evil.example:{port}")
    assert status == 403, "the laboratory's data went to a host that is not this machine"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_console_says_which_rounds_it_is_collecting(console):
    """One writer per diary: a lab tick asks /status which rounds the console
    runs on its timers and leaves exactly those to it."""
    port = console["port"]
    console["live"].collectors.update({"fomo": 1200.0, "hot": 0})
    status, body = _get(port, "/status", f"127.0.0.1:{port}")
    assert status == 200
    assert json.loads(body)["collectors"] == {"fomo": 1200.0, "hot": 0}


def _post_note(port: int, payload, **over):
    """A note the way the page sends one, with any header replaced or removed."""
    host = f"127.0.0.1:{port}"
    headers = {"Host": host, "Origin": f"http://{host}",
               "Content-Type": "application/json", "X-QA-Token": TOKEN}
    headers.update(over)
    headers = {k: v for k, v in headers.items() if v is not None}
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    status, _, raw = _request(port, "POST", "/notes", headers, body)
    return status, raw


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_note_at_any_shut_door_is_refused_and_nothing_is_written(console):
    port, stored = console["port"], console["state"] / "rooms.jsonl"
    good = {"room": "general", "text": "proč ne víc?"}
    cases = [
        ("no token", good, {"X-QA-Token": None}, 403),
        ("a wrong token", good, {"X-QA-Token": "guess"}, 403),
        ("no Origin", good, {"Origin": None}, 403),
        ("a foreign Origin", good, {"Origin": "http://evil.example"}, 403),
        ("a rebound Host", good, {"Host": f"evil.example:{port}",
                                  "Origin": f"http://evil.example:{port}"}, 403),
        ("a form post", good, {"Content-Type": "text/plain"}, 415),
        ("a body over 8 KB", {"room": "general", "text": "x" * 9000}, {}, 413),
        ("a body that is not JSON", b"room=general&text=hi", {}, 400),
        ("a key the browser may not set", {**good, "type": "claude_note"}, {}, 400),
        ("an unknown room", {"room": "STR-9999", "text": "hi"}, {}, 400),
        ("an empty note", {"room": "general", "text": "   "}, {}, 400),
        ("a note over 4000 characters", {"room": "general", "text": "x" * 4001}, {}, 400),
    ]
    wrong = []
    for label, payload, over, expected in cases:
        status, _ = _post_note(port, payload, **over)
        if status != expected:
            wrong.append(f"{label}: {status}, expected {expected}")
    assert not wrong, "doors that did not refuse as they should:\n  " + "\n  ".join(wrong)
    assert not stored.exists(), "a refused note still reached rooms.jsonl"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_big_body_is_refused_with_a_status_and_not_a_dropped_socket(console):
    """A refusal the caller cannot read is a refusal that did not happen.

    The test above used to fail about one run in six with
    ConnectionAbortedError 10053 on the CLIENT's read -- no status at all --
    because the handler refused before reading the body ("a refused body is
    never parsed", its own docstring) and then closed, and Windows discards a
    response when a socket closes with inbound bytes still pending. Draining
    the body first fixed it: ten consecutive runs of the pair that used to
    flake, clean. The proof it is the same path is an intermediate bug on the
    way -- a drain that also ran after the body had ALREADY been read turned
    the flake into a deterministic timeout, which nothing else in the handler
    could have done.

    What THIS test pins is narrower, and says so rather than claiming the
    flake: a body far past the cap comes back as a status at every door and
    none of it is written. It passes with the drain removed, so it is not the
    guard for the drain; the guard for the drain is the test above no longer
    flaking.
    """
    port, stored = console["port"], console["state"] / "rooms.jsonl"
    big = {"room": "general", "text": "x" * 256_000}

    status, _ = _post_note(port, big, **{"X-QA-Token": None})
    assert status == 403, "the refusal never reached a caller mid-send"
    status, _ = _post_note(port, big, **{"Origin": "http://evil.example"})
    assert status == 403
    status, _ = _post_note(port, big)
    assert status == 413, "past the size cap, with the body still arriving"
    assert not stored.exists(), "a drained body still reached rooms.jsonl"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_note_through_every_door_lands_once_and_as_the_operators(console):
    """The positive control. Without it every refusal above could be a 500."""
    port, stored = console["port"], console["state"] / "rooms.jsonl"
    status, raw = _post_note(port, {"room": "general", "text": "proč ne víc?"})
    assert status == 201, raw
    assert json.loads(raw)["id"] == "N-0001"
    rows = [json.loads(line) for line in stored.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    assert [(r["type"], r["room"], r["text"]) for r in rows] == [
        ("operator_note", "general", "proč ne víc?")]

    status, body = _get(port, "/rooms.json", f"127.0.0.1:{port}")
    notes = [m for m in json.loads(body)["threads"]["general"]
             if m["kind"] == "operator_note"]
    assert [(m["id"], m["read"]) for m in notes] == [("N-0001", False)]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_token_is_handed_only_to_this_machine_and_never_written(console):
    port = console["port"]
    status, headers, body = _request(port, "GET", "/token",
                                     {"Host": f"127.0.0.1:{port}"})
    assert status == 200 and json.loads(body)["token"] == TOKEN
    assert headers.get("X-Content-Type-Options") == "nosniff", (
        "without nosniff a page could try to load the token as a script")

    for host, origin in ((f"evil.example:{port}", None),
                         (f"127.0.0.1:{port}", "http://evil.example")):
        status, body = _get(port, "/token", host, origin)
        assert status == 403 and TOKEN.encode() not in body, (host, origin, status)

    _, page = _get(port, "/", f"127.0.0.1:{port}")
    assert TOKEN.encode() not in page, "the token is in the served page"
    written = console["state"] / "dashboard" / "index.html"
    assert written.exists(), "the console wrote no page, so this half proves nothing"
    assert TOKEN not in written.read_text(encoding="utf-8"), "the token is on disk"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_notes_are_off_when_the_console_listens_beyond_this_machine(exposed):
    serve = exposed["serve"]
    assert serve.note_token_for("0.0.0.0") is None
    assert serve.note_token_for("192.168.1.5") is None
    one, two = serve.note_token_for("127.0.0.1"), serve.note_token_for("localhost")
    assert one and two and one != two, "a token must be minted fresh at each launch"
    # The same host, twice: two launches on one machine. Comparing two HOSTS
    # let a token derived from the host name pass -- identical across every
    # restart and predictable -- which is the opposite of "minted fresh"
    # (P11, deep pass of 2026-09-11, triage 3/3).
    again = serve.note_token_for("127.0.0.1")
    assert again != one, "the token is the same on the same host: it is not minted"
    assert len(one) >= 32 and len(again) >= 32, "a short token can be guessed"

    port = exposed["port"]
    status, _ = _post_note(port, {"room": "general", "text": "hi"})
    assert status == 403
    status, _ = _get(port, "/token", f"127.0.0.1:{port}")
    assert status == 403
    assert not (exposed["state"] / "rooms.jsonl").exists()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_writers_at_once_never_share_a_note_id(tmp_path, monkeypatch):
    """The browser and the CLI write the same file. The id is taken inside the
    lock, or two notes get one id and a read mark covers the wrong one."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa import rooms

    errors = []

    def write(kind: str, n: int) -> None:
        try:
            for i in range(n):
                if kind == "operator":
                    rooms.add_operator_note("general", f"operator {i}")
                else:
                    rooms.add_claude_note("general", f"claude {i}")
        except Exception as exc:  # noqa: BLE001 -- surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(kind, 15))
               for kind in ("operator", "claude", "operator", "claude")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    assert not errors, errors
    ids = [r["id"] for r in rooms.load()]
    assert len(ids) == 60, f"{60 - len(ids)} note(s) lost between two writers"
    assert len(set(ids)) == 60, "two writers were handed the same note id"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_browser_reaches_the_operators_writer_and_no_other():
    """Two writers on purpose, and the page can reach exactly one of them.

    The set of writers is read from qa/rooms.py itself -- every function that
    appends -- so a writer added later is covered without anyone remembering
    to list it here.
    """
    import ast

    rooms_tree = ast.parse((REPO / "qa" / "rooms.py").read_text(encoding="utf-8"))
    writers = {fn.name for fn in ast.walk(rooms_tree)
               if isinstance(fn, ast.FunctionDef) and fn.name != "_append"
               and any(isinstance(c, ast.Call) and getattr(c.func, "id", None) == "_append"
                       for c in ast.walk(fn))}
    assert {"add_operator_note", "add_claude_note"} <= writers, writers

    serve_tree = ast.parse((REPO / "scripts" / "serve.py").read_text(encoding="utf-8"))
    used = ({n.attr for n in ast.walk(serve_tree) if isinstance(n, ast.Attribute)}
            | {n.id for n in ast.walk(serve_tree) if isinstance(n, ast.Name)}
            | {a.name for n in ast.walk(serve_tree) if isinstance(n, ast.ImportFrom)
               for a in n.names})
    assert "add_operator_note" in used, (
        "the note endpoint no longer writes through add_operator_note")
    reachable = sorted((writers - {"add_operator_note"}) & used)
    assert not reachable, f"serve.py can reach writers the browser must not: {reachable}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rooms_and_the_samples_stay_out_of_git():
    """Written while a sweep may run, so never part of the tree it checks."""
    for rel in ("state/rooms.jsonl", "state/samples.jsonl"):
        proc = subprocess.run(["git", "check-ignore", "-q", rel], cwd=str(REPO))
        assert proc.returncode == 0, (
            f"{rel} is not gitignored: a note typed during a sweep would dirty "
            f"the tree, and the run could no longer reach level V")
