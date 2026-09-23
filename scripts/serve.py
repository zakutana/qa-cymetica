"""Serve the console locally and push it when the state underneath changes.

The published Artifact is a snapshot: correct at the moment it was rendered,
and silent afterwards. Anyone reading it has to wonder whether they are
looking at now or at an hour ago, and that doubt is corrosive on a page whose
whole claim is that its numbers were measured.

So this serves the same file from localhost and watches `state/`. When the
ledger, the journal or a run record changes, it re-renders and tells the open
tab, which reloads itself. Nothing to refresh, nothing to wonder about.

It is deliberately the same `render()` the CLI and the repo-consistency guard
use. A second renderer would be a second truth, and the dashboard drifting
from the ledger is the exact failure that guard exists to catch.

    python scripts/serve.py            # http://127.0.0.1:8787
    python scripts/serve.py --port 9000 --open

What it writes, all of it. dashboard/index.html, which is a projection and
always was. With `--ask`, what the bell needs -- see asker(). With `--sample`,
what scripts/sampler.py reads of their API for the rooms, into the
gitignored state/samples.jsonl -- see collector_loop(). And one row in
state/rooms.jsonl when the operator sends a note from the laboratory's page: through
qa.rooms.add_operator_note, the only writer the page can reach, behind a token
minted at launch, a Host and an Origin naming this machine, and a JSON body.

The laboratory has a page of its own, /lab (scripts/lab_page.py, plan v2 V4),
rendered on request and written nowhere, with its rooms at /rooms.json. Neither
is part of the committed console -- ROOM_FILES says why -- so a note or a
sample never moves dashboard/index.html. Asking for /lab rewrites the
gitignored state/lab/report.json, which is what the page reads.
"""

from __future__ import annotations

import argparse
import hmac
import importlib.util
import json
import queue
import re
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.rooms import RoomError, add_operator_note  # noqa: E402

# What a change to the state means the page is out of date. Poll rather than
# watch: a handful of directories on Windows, once a minute, needs no
# dependency. See POLL_SECONDS for why it is a minute and not a second.
WATCHED = ("state/ledger.json", "state/journal/events.jsonl", "state/bounty.json",
           "state/inventory.json", "state/runs", "dashboard",
           # The renderer itself. Without this the server holds the copy it
           # imported at startup, so every edit to the page is invisible until
           # someone remembers to restart it -- and the tab shows old markup
           # while the file on disk has the new. That is the drift this whole
           # console exists to make impossible.
           "scripts/render.py")

# A tick stats every file under the watched directories -- 173 of them today,
# 2.2 ms, and growing, because state/runs/ gains a record on every pytest
# session. Once a second that was 193 s of CPU a day to notice events that
# arrive a few times an hour: a sweep finishing, a reply pasted. A minute is
# the right order for both. Editing the page itself is the one case that wants
# the old cadence, and `--poll 1` is there for it.
POLL_SECONDS = 60.0

# The words the stalled-page band puts on the page, named here so a test
# can assert THEM rather than any occurrence of "stale" -- the rendered
# page carries that word 51 times from the template itself, which made
# the first version of that assertion unfalsifiable.
STALE_BANNER = "THIS PAGE HAS STOPPED UPDATING"


def _escape(text) -> str:
    """Their error text lands in our markup; it is data, not HTML."""
    from html import escape

    return escape(str(text), quote=True)


def _page_digest(path: Path) -> str | None:
    """The digest the page on disk was rendered from, or None.

    One implementation, in render.py, since 2026-09-20: the pre-commit hook
    asks the same question through `render.py --if-stale`, and two readings of
    "is the page current" is how the two start to differ.
    """
    return _render_module().page_digest(path)


def _render_module():
    spec = importlib.util.spec_from_file_location(
        "render_live", REPO_ROOT / "scripts" / "render.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lab_page_module():
    """scripts/lab_page.py, loaded fresh per request, so an edit to the
    laboratory's page shows on the next reload without a restart."""
    spec = importlib.util.spec_from_file_location(
        "lab_page_live", REPO_ROOT / "scripts" / "lab_page.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fingerprint() -> tuple:
    """Cheap signal that something under state/ moved."""
    marks = []
    for rel in WATCHED:
        path = REPO_ROOT / rel
        if path.is_dir():
            try:
                marks.append((rel, max((p.stat().st_mtime_ns
                                        for p in path.iterdir() if p.is_file()),
                                       default=0)))
            except OSError:
                marks.append((rel, -1))
        else:
            try:
                marks.append((rel, path.stat().st_mtime_ns))
            except OSError:
                marks.append((rel, -1))
    return tuple(marks)


# The Nexus rooms (docs/nexus-rooms-plan.md). Served on their own at
# /rooms.json and NOT part of the payload: the operator's notes and the
# sampler's rows land while a sweep may be running, and anything in the payload
# rewrites the committed dashboard/index.html -- a dirty tree in the middle of
# a run, and a run that can no longer reach level V. Five small files, looked
# at every few seconds: what POLL_SECONDS guards against is stat-ing every run
# record, and none of these is one.
ROOM_FILES = ("rooms.jsonl", "nexus.jsonl", "paper.jsonl", "clones.jsonl",
              "samples.jsonl")
ROOM_POLL_SECONDS = 5.0
ROOMS_EVENT = "rooms:"

# The names this machine answers to. The rooms carry the operator's own notes,
# and a page on any site can point a hostname of its own at 127.0.0.1 and then
# read from it as if it were same-origin -- DNS rebinding. What that request
# cannot fake is the Host header its browser sends.
LOOPBACK_NAMES = ("127.0.0.1", "localhost", "[::1]")


def room_fingerprint() -> tuple:
    """Size and mtime of each room file -- size too, so an append always shows."""
    from qa.state import state_dir

    base = state_dir()
    marks = []
    for name in ROOM_FILES:
        try:
            stat = (base / name).stat()
            marks.append((name, stat.st_mtime_ns, stat.st_size))
        except OSError:
            marks.append((name, -1, -1))
    return tuple(marks)


def room_watch_once(live, last: tuple) -> tuple:
    """One tick of the rooms watcher, without the timer, so a test can run it."""
    now = room_fingerprint()
    if now != last:
        live.notify_rooms()
    return now


def room_watcher(live, stop: threading.Event,
                 every: float = ROOM_POLL_SECONDS) -> None:
    last = room_fingerprint()
    while not stop.wait(every):
        try:
            last = room_watch_once(live, last)
        except Exception as exc:  # noqa: BLE001 -- a bad stat must not kill the thread
            print(f"[rooms] watch failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)


def local_host(header, port: int) -> bool:
    """Was this request addressed to this machine, by a loopback name and our port?"""
    return (header or "").strip().lower() in {f"{n}:{port}" for n in LOOPBACK_NAMES}


# The console's one write path: a note from /lab's rooms. Small, and JSON --
# a cross-site form can send text/plain without asking, but not
# application/json and not a header of our own; the browser asks first with an
# OPTIONS preflight, which this server never answers.
NOTE_MAX_BYTES = 8 * 1024
# How much of a REFUSED body is read and thrown away before answering, so the
# answer survives the close. Past this a caller pushing megabytes at a shut
# door gets the connection dropped instead, which is the right answer to that.
NOTE_DRAIN_MAX_BYTES = 1024 * 1024
TOKEN_HEADER = "X-QA-Token"


def note_token_for(host: str) -> str | None:
    """A token for this launch, or None when notes must stay off.

    Minted fresh at every start, so one that leaked would die with the
    process. None unless the console listens on this machine only: bound to
    0.0.0.0, anything on the network could ask for /token with a loopback Host
    header of its own choosing -- a Host check stops browsers, not curl -- so
    there the console is read-only.
    """
    import secrets

    if host not in ("127.0.0.1", "localhost", "::1"):
        return None
    return secrets.token_urlsafe(32)


class SingleServer(ThreadingHTTPServer):
    """Refuse to share the port. The default is to reuse it, which on Windows
    means two servers can listen at once and the browser gets whichever one
    the OS feels like."""

    allow_reuse_address = False
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        """A client hanging up is routine here, not an error.

        Every live reload abandons an in-flight SSE stream and a keep-alive
        connection, and Windows reports that as WinError 10053. socketserver
        prints a full traceback for it, so the console window filled with
        stack traces that look like a crashed server while it was working
        exactly as designed -- and a real error in the same stream would have
        been invisible among them.

        The stream_events handler already swallows this on the write side;
        this covers the read side, where socketserver reads the next request
        line off a connection the browser has already dropped, outside any
        code of ours.
        """
        kind = sys.exc_info()[1]
        if isinstance(kind, (ConnectionAbortedError, ConnectionResetError,
                             BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class Live:
    """The current page, the current payload hash, and who is listening."""

    def __init__(self) -> None:
        self.render = _render_module()
        self.lock = threading.Lock()
        self.html = ""
        self.payload: dict = {}
        self.digest = ""
        self.error: str | None = None
        self.listeners: list[queue.Queue] = []
        # The rounds this console runs on its own timers, name -> seconds.
        # /status says so, and a lab tick leaves exactly those to it: one
        # writer per diary (plan v2, V4).
        self.collectors: dict[str, float] = {}
        self.rebuild()

    def rebuild(self) -> bool:
        """Re-render. Returns True if what the page shows actually changed."""
        try:
            # Re-import first: a change to render.py is a change to the page,
            # and serving from a module frozen at startup would show markup
            # that no longer matches the file.
            self.render = _render_module()
            payload = self.render.build_payload()
            html = self.render.render(payload)
            digest = self.render.payload_hash(payload)
            error = None
        except Exception as exc:  # noqa: BLE001 -- a broken render must not kill the server
            payload, html, digest = self.payload, self.html, self.digest
            error = f"{type(exc).__name__}: {exc}"

        if error:
            # Every time, not only when the message changes. On 2026-09-08 the
            # same JournalError repeated once a minute for two hours -- a
            # module this process imported before ALLOWED_EVENT_KEYS grew two
            # keys -- and because `changed` compares the error with the
            # PREVIOUS error, an identical failure read as "nothing moved". No
            # log line, no notification, and a page serving a two-hour-old
            # truth. A repeating failure is not a quiet one.
            print(f"[serve] REBUILD FAILED, page is frozen at "
                  f"{(self.payload or {}).get('generated_at')}: {error}",
                  file=sys.stderr)

        with self.lock:
            changed = digest != self.digest or error != self.error
            self.payload, self.html, self.digest, self.error = payload, html, digest, error
        if changed and not error:
            # render.out_path() honours QA_STATE_DIR, so a test run writes into
            # its own temp tree and can never overwrite the committed page.
            target = self.render.out_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            # Against the page ON DISK, not against `changed`. `changed` asks
            # whether the open tab should be told something, and on a fresh
            # process the answer is always yes because self.digest starts
            # empty -- so starting the console rewrote a byte-identical page
            # with a new `generated_at`, git status came up dirty, and
            # prereg.py refuses a dirty tree. The digest is embedded in the
            # page it describes, so the file can answer for itself.
            if _page_digest(target) != digest:
                target.write_text(html, encoding="utf-8")
        return changed

    def serve_html(self) -> str:
        """The page, and a band across it when it has stopped being rebuilt.

        The last good page is the right thing to keep serving -- a blank tab
        during a bad fold helps nobody. What was wrong until 2026-09-08 is that
        it was served silently: the console showed 39 findings and three rows
        as STILL REPRODUCIBLE for two hours after they had been verified fixed,
        and the operator found it by disbelieving their own dashboard.

        The server window is not where anyone looks. The page is, so the page
        says it.
        """
        with self.lock:
            html, error, payload = self.html, self.error, self.payload
        if not error or not html:
            return html
        frozen = (payload or {}).get("generated_at") or "an unknown time"
        band = (
            '<div style="position:sticky;top:0;z-index:99999;padding:.6rem 1rem;'
            'background:#5a1111;color:#ffd7d7;font:600 13px/1.5 ui-monospace,'
            'monospace;border-bottom:1px solid #ff6b6b">'
            f'{STALE_BANNER} &mdash; frozen at {_escape(frozen)}. '
            f'Every rebuild since has failed: {_escape(error)} '
            '&middot; restart the console to pick up changed modules.'
            '</div>')
        marker = "<body>"
        if marker in html:
            return html.replace(marker, marker + band, 1)
        return band + html

    def notify(self) -> None:
        with self.lock:
            listeners = list(self.listeners)
            digest = self.digest
        for q in listeners:
            q.put(digest)

    def notify_rooms(self) -> None:
        """The rooms moved. Their own event: the tab redraws one panel, the page
        does not reload, and a note being typed is not thrown away."""
        with self.lock:
            listeners = list(self.listeners)
        for q in listeners:
            q.put(ROOMS_EVENT + str(time.time_ns()))

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self.lock:
            self.listeners.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.listeners:
                self.listeners.remove(q)


def asker(stop: threading.Event, every: float) -> None:
    """Ask their bug tracker whether anything moved, on a timer.

    The watcher below is a delivery mechanism: it notices that a file on this
    machine changed and pushes the redrawn page to the open tab. It never goes
    near the network, so on its own the console can only ever show you an
    answer that something else already fetched -- which meant sitting in front
    of a page waiting for a bell that, by construction, could not ring.

    This is the half that fetches. One read-only GET of our own filed reports,
    the same call scripts/bounty.py makes, at SAFE tier. When a report's
    status has actually changed it writes one event and a new snapshot, the
    watcher sees state/bounty.json move within a tick, and the bell lights on
    its own.

    Two things it deliberately does not do. It does not run checks: a bell is
    news that THEY moved, and whether their claim is true is a question only
    an admissible run may answer. And it does not touch the CHECK axis at all,
    so nothing here can mark anything verified.

    It does write, which is the honest cost: after a change your tree is dirty
    until you commit, and a run started in that window cannot reach level V.
    Off by default for exactly that reason.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "bounty_poll", REPO_ROOT / "scripts" / "bounty.py")
    bounty = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bounty)

    while not stop.wait(every):
        poll_once(bounty)


def poll_once(bounty) -> None:
    """One tick: read their tracker, then read their inbox. Both, always.

    The two are independent surfaces and each guards itself. They were once
    chained -- the inbox read was appended after the tracker block's `continue`
    statements -- so an expired key on my-reports also stopped a2a replies from
    being noticed, which is precisely the "a reply sat there until somebody
    thought to look" state the inbox read exists to end. Three triage agents
    found that on 2026-09-07.

    A function rather than a loop body so it can be exercised without a timer.
    """
    _poll_tracker(bounty)
    _poll_inbox(bounty)


def _poll_tracker(bounty) -> None:
    try:
        before = bounty._last_status_by_report()
        # refresh_our_reports, not fetch_our_reports: the latter appends the
        # journal event and returns the rows without writing state/bounty.json,
        # and the bell reads the vendor's status out of that file. Recording
        # the change and leaving the page saying the old thing is the failure
        # this whole option exists to remove.
        snapshot = bounty.refresh_our_reports()
        after = bounty._last_status_by_report()
    except Exception as exc:  # noqa: BLE001 -- a bad read must not kill the server
        print(f"[ask] read failed, leaving the page as it was: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return

    klass = (snapshot or {}).get("klass")
    if klass != "ok":
        # Rule 8: a failed read is not an empty read. bounty.py has already
        # recorded that we looked and could not see; say so here rather than
        # letting silence read as "nothing has changed".
        print(f"[ask] could not read their tracker ({klass}); "
              f"the page keeps what it had")
        return

    moved = {k: (before.get(k), v) for k, v in after.items() if before.get(k) != v}
    if moved:
        for report_id, (was, now) in sorted(moved.items()):
            print(f"[ask] #{report_id}: {was or '-'} -> {now}")
        print(f"[ask] {len(moved)} report(s) moved -- re-fold to take it in: "
              f"python scripts/ledger.py --events-only")


def _poll_inbox(bounty) -> None:
    """The other surface they answer on.

    A question sent to /a2a/send is replied to in the inbox and nowhere else.
    """
    try:
        inbox = bounty.fetch_inbox()
    except Exception as exc:  # noqa: BLE001 -- a bad read must not kill the server
        print(f"[ask] inbox read failed, leaving the page as it was: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return
    if inbox["klass"] != "ok":
        # Rule 8 again: silence here would be indistinguishable from a vendor
        # who simply has not replied.
        print(f"[ask] could not read the a2a inbox ({inbox['klass']}); "
              f"that is not an empty inbox")
        return
    for message in inbox["new"]:
        if message["auto"]:
            continue
        first = (message["text"] or "").strip().splitlines()
        print(f"[ask] a2a reply {message['msg_id']} at {message['at']}")
        print(f"      {bounty._printable(first[0] if first else '')[:100]}")


def collector_loop(name: str, script: str, stop: threading.Event,
                   every: float, collectors: dict) -> None:
    """One of the laboratory's read-only rounds on this console's timer:
    scripts/<script>.py's run(), GET only, into its own gitignored diary.
    Listed in `collectors` while it runs, so /status can tell a lab tick to
    leave that round to us -- and taken off the list if the script cannot
    even load, so the tick does the round itself instead of nobody doing it.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            f"{script}_serve", REPO_ROOT / "scripts" / f"{script}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 -- say it, do not take the server down
        collectors.pop(name, None)
        print(f"[{name}] did not load, so the lab tick keeps doing it: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return
    try:
        module.run(stop, every)
    finally:
        collectors.pop(name, None)


def watcher(live: Live, stop: threading.Event, every: float = POLL_SECONDS) -> None:
    last = _fingerprint()
    while not stop.wait(every):
        now = _fingerprint()
        if now == last:
            continue
        last = now
        if live.rebuild():
            print(f"[serve] state moved -> re-rendered, payload {live.digest[:16]}")
            live.notify()


def make_handler(live: Live, note_token: str | None = None):
    """The request handler. `note_token` None means /lab's rooms are read-only."""
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # quiet; the watcher already narrates
            pass

        def _send(self, body: bytes, ctype: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            # A live page must never be served from cache.
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler's name
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                with live.lock:
                    html, error = live.html, live.error
                if error and not html:
                    self._send(f"render failed: {error}".encode("utf-8"),
                               "text/plain; charset=utf-8", 500)
                    return
                # serve_html, not html: a page that has stopped being rebuilt
                # carries a band saying so. Serving `html` here is what let a
                # frozen console look healthy for two hours on 2026-09-08.
                self._send(live.serve_html().encode("utf-8"),
                           "text/html; charset=utf-8")
                return

            if path == "/payload.json":
                with live.lock:
                    body = json.dumps(live.payload, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return

            if path == "/status":
                with live.lock:
                    body = json.dumps({"digest": live.digest, "error": live.error,
                                       "listeners": len(live.listeners),
                                       "collectors": dict(live.collectors)}
                                      ).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return

            if path == "/token":
                self.send_token()
                return

            if path == "/rooms.json":
                self.send_rooms()
                return

            if path == "/lab":
                self.send_lab()
                return

            if path == "/events":
                self.stream_events()
                return

            self._send(b"not found", "text/plain; charset=utf-8", 404)

        def _drain(self) -> None:
            """Swallow an unread request body so the answer can be read.

            Closing a socket while the caller's bytes are still arriving makes
            Windows discard the response and hand the CALLER
            ConnectionAbortedError 10053 instead of our status -- a refusal
            nobody can read is a refusal that did not happen. So a refused body
            is read and thrown away. It is never decoded and never parsed,
            which is what "a refused body is never parsed" was protecting;
            reading bytes to drop them is not reading a note.

            Bounded, because the length is the caller's claim: past the cap a
            client pushing megabytes at a shut door gets its connection
            dropped, which is the right answer to that.
            """
            if getattr(self, "_body_gone", False):
                return
            self._body_gone = True
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return
            left = min(max(length, 0), NOTE_DRAIN_MAX_BYTES)
            while left > 0:
                chunk = self.rfile.read(min(left, 64 * 1024))
                if not chunk:
                    return
                left -= len(chunk)

        def _refuse(self, payload: dict, status: int) -> None:
            """A refusal that reaches the caller: drain first, then answer."""
            self._drain()
            self._json(payload, status)

        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, must-revalidate")
            # A page elsewhere could try <script src="/token">; nosniff stops
            # the browser running JSON as script at all.
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _refusal(self, need_origin: bool) -> tuple[int, str] | None:
            """Why a token or a note is refused, or None. The doors, in order."""
            if note_token is None:
                return 403, "notes are off: this console listens beyond this machine"
            host = (self.headers.get("Host") or "").strip().lower()
            if not local_host(host, self.server.server_address[1]):
                return 403, "not addressed to this machine"
            origin = (self.headers.get("Origin") or "").strip().lower()
            if need_origin and not origin:
                return 403, "a note must say where it comes from"
            if origin and origin != f"http://{host}":
                return 403, "a note from another site"
            return None

        def send_token(self) -> None:
            """This launch's token -- to a page on this machine, asked for by name.

            Handed out rather than written into the page, so a tab left open
            across a restart never holds one the new process did not issue.
            Another site may make this request; it cannot read the answer.
            """
            refused = self._refusal(need_origin=False)
            if refused:
                self._json({"error": refused[1]}, refused[0])
                return
            self._json({"token": note_token})

        def do_POST(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler's name
            """A note from the operator. Every door is shut until proven open.

            Refusals come before the body is read, so a refused body is never
            parsed and the connection is not reused.
            """
            self.close_connection = True
            if self.path.split("?", 1)[0] != "/notes":
                self._refuse({"error": "not found"}, 404)
                return
            refused = self._refusal(need_origin=True)
            if refused is None:
                sent = (self.headers.get(TOKEN_HEADER) or "").encode("utf-8")
                if not hmac.compare_digest(sent, note_token.encode("utf-8")):
                    refused = (403, "no valid token")
            if refused:
                self._refuse({"error": refused[1]}, refused[0])
                return
            kind = (self.headers.get("Content-Type") or "").split(";", 1)[0]
            if kind.strip().lower() != "application/json":
                self._refuse({"error": "a note is sent as application/json"}, 415)
                return
            try:
                length = int(self.headers.get("Content-Length") or "")
            except ValueError:
                self._refuse({"error": "a note says how long it is"}, 411)
                return
            if length < 0 or length > NOTE_MAX_BYTES:
                self._refuse({"error": f"a note is at most {NOTE_MAX_BYTES} bytes"}, 413)
                return
            # Once this runs the body is consumed, and a later refusal must not
            # try to drain it again: reading Content-Length more bytes that
            # nobody is sending is a handler that hangs until the caller times
            # out, which is how the first version of the drain turned a flake
            # into a deterministic stall.
            self._body_gone = True
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._refuse({"error": "a note is JSON"}, 400)
                return
            if (not isinstance(body, dict) or set(body) != {"room", "text"}
                    or not all(isinstance(body[k], str) for k in body)):
                self._refuse({"error": "a note is exactly {room, text}"}, 400)
                return
            try:
                row = add_operator_note(body["room"], body["text"])
            except RoomError as exc:
                self._refuse({"error": str(exc)}, 400)
                return
            live.notify_rooms()
            self._json({"id": row["id"], "at": row["at"]}, 201)

        def send_lab(self) -> None:
            """The laboratory's page (V4): rendered now, written nowhere -- it
            reads gitignored diaries, which is why it is not the committed
            console. To this machine by name, like the rooms it carries."""
            if not local_host(self.headers.get("Host"),
                              self.server.server_address[1]):
                self._send(b"the laboratory is served to this machine only",
                           "text/plain; charset=utf-8", 403)
                return
            try:
                html = _lab_page_module().render_lab()
            except Exception as exc:  # noqa: BLE001 -- a broken page must not kill the server
                self._send(f"the laboratory's page failed: {type(exc).__name__}: "
                           f"{exc}".encode("utf-8"), "text/plain; charset=utf-8", 500)
                return
            self._send(html.encode("utf-8"), "text/html; charset=utf-8")

        def send_rooms(self) -> None:
            """The rooms on /lab -- to this machine by name, to nothing else."""
            if not local_host(self.headers.get("Host"),
                              self.server.server_address[1]):
                self._send(b'{"error": "the rooms are served to this machine only"}',
                           "application/json; charset=utf-8", 403)
                return
            try:
                body = json.dumps(_lab_page_module().build_rooms(),
                                  ensure_ascii=False)
            except Exception as exc:  # noqa: BLE001 -- a broken view must not kill the server
                self._send(json.dumps({"error": f"{type(exc).__name__}: {exc}"})
                           .encode("utf-8"), "application/json; charset=utf-8", 500)
                return
            self._send(body.encode("utf-8"), "application/json; charset=utf-8")

        def stream_events(self) -> None:
            """Server-sent events. One line per change, plus a keepalive.

            SSE rather than a WebSocket on purpose: it is one HTTP response,
            the browser reconnects by itself, and it needs no library on
            either end.
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            q = live.subscribe()
            try:
                with live.lock:
                    current = live.digest
                self.wfile.write(f"event: hello\ndata: {current}\n\n".encode("utf-8"))
                self.wfile.flush()
                while True:
                    try:
                        item = q.get(timeout=15)
                        if item.startswith(ROOMS_EVENT):
                            payload = (f"event: rooms\n"
                                       f"data: {item[len(ROOMS_EVENT):]}\n\n")
                        else:
                            payload = f"event: changed\ndata: {item}\n\n"
                    except queue.Empty:
                        payload = ": keepalive\n\n"
                    self.wfile.write(payload.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                live.unsubscribe(q)

    return Handler


def _already_ours(url: str) -> bool:
    """Is the thing on that port this same server, or a stranger?

    Checked rather than assumed: opening a browser at whatever happens to hold
    port 8787 would be a small betrayal of the one promise this page makes,
    which is that what you are looking at is our measurement.
    """
    import urllib.request

    try:
        with urllib.request.urlopen(url.rstrip("/") + "/status", timeout=2) as r:
            return "digest" in json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 -- anything at all means "not ours"
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--open", action="store_true", help="open a browser tab")
    parser.add_argument("--poll", type=float, default=POLL_SECONDS, metavar="SECONDS",
                        help=f"how often to look for a change "
                             f"(default {POLL_SECONDS:g}; use 1 while editing "
                             f"scripts/render.py)")
    parser.add_argument("--ask", type=float, default=0, metavar="MINUTES",
                        help="also ask their bug tracker this often, so the "
                             "bell can light on its own (e.g. --ask 15). "
                             "Writes when a report moves, which dirties the "
                             "tree; off by default")
    parser.add_argument("--sample", type=float, default=0, metavar="MINUTES",
                        help="also read their API for /lab's rooms this often "
                             "(e.g. --sample 10): our bot and our card "
                             "positions, GET only, into the gitignored "
                             "state/samples.jsonl; off by default")
    parser.add_argument("--fomo", type=float, default=0, metavar="MINUTES",
                        help="also watch FOMO Radar's `hot` signal this often "
                             "(e.g. --fomo 10): capture new signals and "
                             "checkpoint due ones, GET only, into the "
                             "gitignored state/fomo_signals.jsonl; off by "
                             "default")
    parser.add_argument("--hot", type=float, default=0, metavar="MINUTES",
                        help="also go round the Hot headlines this often "
                             "(e.g. --hot 20), GET only, into the gitignored "
                             "state/hot_watch.jsonl; off by default. While it "
                             "runs a lab tick leaves the round to the console")
    args = parser.parse_args(argv)
    if args.poll <= 0:
        parser.error("--poll must be greater than zero")
    if args.ask and args.ask < 1:
        parser.error("--ask is in minutes; anything under 1 is hammering them")
    if args.sample and args.sample < 1:
        parser.error("--sample is in minutes; anything under 1 is hammering them")
    if args.fomo and args.fomo < 1:
        parser.error("--fomo is in minutes; anything under 1 is hammering them")
    if args.hot and args.hot < 1:
        parser.error("--hot is in minutes; anything under 1 is hammering them")

    live = Live()
    if live.error:
        print(f"[serve] first render failed: {live.error}", file=sys.stderr)
        return 1

    stop = threading.Event()
    thread = threading.Thread(target=watcher, args=(live, stop, args.poll), daemon=True)
    thread.start()
    threading.Thread(target=room_watcher, args=(live, stop), daemon=True).start()

    if args.ask:
        threading.Thread(target=asker, args=(stop, args.ask * 60),
                         daemon=True).start()

    url = f"http://{args.host}:{args.port}/"
    note_token = note_token_for(args.host)

    # Asked BEFORE binding, not after a failed bind. ThreadingHTTPServer sets
    # allow_reuse_address, which on Windows lets a second process bind a port
    # that is already listening -- so the bind succeeds, two servers answer at
    # random, and the launcher looks like it worked. Double-clicking twice is
    # the normal way that happens, so it has to be handled here rather than in
    # an except branch that never runs.
    if _already_ours(url):
        print(f"[serve] already running at {url} -- opening that instead")
        webbrowser.open(url)
        return 0

    try:
        server = SingleServer((args.host, args.port),
                              make_handler(live, note_token=note_token))
    except OSError as exc:
        print(f"[serve] cannot listen on {args.host}:{args.port}: {exc}", file=sys.stderr)
        print("[serve] something else holds that port; try --port 8788",
              file=sys.stderr)
        return 1
    # Started only once this process holds the port: a second launch opens the
    # tab of the first and returns above, and must not leave a second sampler
    # reading their API beside the first one's.
    # Listed before each thread starts, and taken off by collector_loop if its
    # script cannot load: a lab tick reads the list on /status and leaves
    # exactly these rounds to this console.
    for name, script, minutes in (("sample", "sampler", args.sample),
                                  ("fomo", "fomo_watch", args.fomo),
                                  ("hot", "hot_watch", args.hot)):
        if minutes:
            live.collectors[name] = minutes * 60
            threading.Thread(target=collector_loop,
                             args=(name, script, stop, minutes * 60,
                                   live.collectors), daemon=True).start()
    rows = sum(live.payload.get("display_counts", {}).values())
    print(f"[serve] {url}  {rows} rows, payload {live.digest[:16]}")
    print(f"[serve] watching {', '.join(WATCHED)} every {args.poll:g}s")
    print("[serve] notes from /lab: "
          + ("on, from this machine only" if note_token else
             "OFF -- this console listens beyond this machine"))
    if args.ask:
        print(f"[serve] asking their tracker every {args.ask:g} min -- the bell "
              f"can light without you")
    else:
        print("[serve] not asking their tracker; the bell only moves after a "
              "sweep (--ask 15 to change that)")
    print(f"[serve] reading their API for /lab's rooms every {args.sample:g} min"
          if args.sample else
          "[serve] not reading their API for /lab's rooms (--sample 10 to change that)")
    print(f"[serve] watching FOMO Radar's hot signal every {args.fomo:g} min"
          if args.fomo else
          "[serve] not watching FOMO Radar (--fomo 10 to change that)")
    print(f"[serve] going round the Hot headlines every {args.hot:g} min"
          if args.hot else
          "[serve] not watching the Hot headlines (--hot 20 to change that)")
    print(f"[serve] the laboratory: {url}lab")
    print("[serve] the open tab reloads itself when the state moves. Ctrl-C to stop.")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] stopping")
    finally:
        stop.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
