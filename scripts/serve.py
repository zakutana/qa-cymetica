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

Read-only with respect to state: it renders, and the only file it writes is
dashboard/index.html, which is a projection and always was.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import queue
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# What a change to the state means the page is out of date. Poll rather than
# watch: three directories on Windows, once a second, costs nothing and needs
# no dependency.
WATCHED = ("state/ledger.json", "state/journal/events.jsonl", "state/bounty.json",
           "state/inventory.json", "state/runs", "dashboard",
           # The desk, not the state. Pasting a reply into inbox/ changes
           # nothing the fold has seen -- the words are attached to no finding
           # until thread.py makes them an event -- so without these two the
           # page went on looking exactly as it had, and a reply could sit
           # there for a day. Watching them lights the "unfiled" marker within
           # a second. It still does not file anything: this server is
           # read-only with respect to state, and a filing state that moved
           # because a watcher noticed a file is the whole class of change
           # this project was rebuilt to prevent.
           "inbox", "outbox",
           # The renderer itself. Without this the server holds the copy it
           # imported at startup, so every edit to the page is invisible until
           # someone remembers to restart it -- and the tab shows old markup
           # while the file on disk has the new. That is the drift this whole
           # console exists to make impossible.
           "scripts/render.py")

POLL_SECONDS = 1.0


def _render_module():
    spec = importlib.util.spec_from_file_location(
        "render_live", REPO_ROOT / "scripts" / "render.py")
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
        self.rebuild()

    def rebuild(self) -> bool:
        """Re-render. Returns True if what the page shows actually changed."""
        try:
            # Re-import first: a change to render.py is a change to the page,
            # and serving from a module frozen at startup would show markup
            # that no longer matches the file.
            self.render = _render_module()
            payload = self.render.build_payload(allow_stale_head=True)
            html = self.render.render(payload)
            digest = self.render.payload_hash(payload)
            error = None
        except Exception as exc:  # noqa: BLE001 -- a broken render must not kill the server
            payload, html, digest = self.payload, self.html, self.digest
            error = f"{type(exc).__name__}: {exc}"

        with self.lock:
            changed = digest != self.digest or error != self.error
            self.payload, self.html, self.digest, self.error = payload, html, digest, error
        if changed and not error:
            # render.out_path() honours QA_STATE_DIR, so a test run writes into
            # its own temp tree and can never overwrite the committed page.
            target = self.render.out_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")
        return changed

    def notify(self) -> None:
        with self.lock:
            listeners = list(self.listeners)
            digest = self.digest
        for q in listeners:
            q.put(digest)

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self.lock:
            self.listeners.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.listeners:
                self.listeners.remove(q)


def watcher(live: Live, stop: threading.Event) -> None:
    last = _fingerprint()
    while not stop.wait(POLL_SECONDS):
        now = _fingerprint()
        if now == last:
            continue
        last = now
        if live.rebuild():
            print(f"[serve] state moved -> re-rendered, payload {live.digest[:16]}")
            live.notify()


def make_handler(live: Live):
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
                self._send(html.encode("utf-8"), "text/html; charset=utf-8")
                return

            if path == "/payload.json":
                with live.lock:
                    body = json.dumps(live.payload, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return

            if path == "/status":
                with live.lock:
                    body = json.dumps({"digest": live.digest, "error": live.error,
                                       "listeners": len(live.listeners)}).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return

            if path == "/events":
                self.stream_events()
                return

            self._send(b"not found", "text/plain; charset=utf-8", 404)

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
                        digest = q.get(timeout=15)
                        payload = f"event: changed\ndata: {digest}\n\n"
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
    args = parser.parse_args(argv)

    live = Live()
    if live.error:
        print(f"[serve] first render failed: {live.error}", file=sys.stderr)
        return 1

    stop = threading.Event()
    thread = threading.Thread(target=watcher, args=(live, stop), daemon=True)
    thread.start()

    url = f"http://{args.host}:{args.port}/"

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
        server = SingleServer((args.host, args.port), make_handler(live))
    except OSError as exc:
        print(f"[serve] cannot listen on {args.host}:{args.port}: {exc}", file=sys.stderr)
        print("[serve] something else holds that port; try --port 8788",
              file=sys.stderr)
        return 1
    rows = sum(live.payload.get("display_counts", {}).values())
    print(f"[serve] {url}  {rows} rows, payload {live.digest[:16]}")
    print(f"[serve] watching {', '.join(WATCHED)} every {POLL_SECONDS:g}s")
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
