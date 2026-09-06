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
        try:
            before = bounty._last_status_by_report()
            snapshot = bounty.fetch_our_reports()
            after = bounty._last_status_by_report()
        except Exception as exc:  # noqa: BLE001 -- a bad read must not kill the server
            print(f"[ask] read failed, leaving the page as it was: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        klass = (snapshot or {}).get("klass")
        if klass != "ok":
            # Rule 8: a failed read is not an empty read. bounty.py has
            # already recorded that we looked and could not see; say so here
            # rather than letting silence read as "nothing has changed".
            print(f"[ask] could not read their tracker ({klass}); "
                  f"the page keeps what it had")
            continue

        moved = {k: (before.get(k), v) for k, v in after.items() if before.get(k) != v}
        if moved:
            for report_id, (was, now) in sorted(moved.items()):
                print(f"[ask] #{report_id}: {was or '-'} -> {now}")
            print(f"[ask] {len(moved)} report(s) moved -- re-fold to take it in: "
                  f"python scripts/ledger.py --events-only")


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
    parser.add_argument("--poll", type=float, default=POLL_SECONDS, metavar="SECONDS",
                        help=f"how often to look for a change "
                             f"(default {POLL_SECONDS:g}; use 1 while editing "
                             f"scripts/render.py)")
    parser.add_argument("--ask", type=float, default=0, metavar="MINUTES",
                        help="also ask their bug tracker this often, so the "
                             "bell can light on its own (e.g. --ask 15). "
                             "Writes when a report moves, which dirties the "
                             "tree; off by default")
    args = parser.parse_args(argv)
    if args.poll <= 0:
        parser.error("--poll must be greater than zero")
    if args.ask and args.ask < 1:
        parser.error("--ask is in minutes; anything under 1 is hammering them")

    live = Live()
    if live.error:
        print(f"[serve] first render failed: {live.error}", file=sys.stderr)
        return 1

    stop = threading.Event()
    thread = threading.Thread(target=watcher, args=(live, stop, args.poll), daemon=True)
    thread.start()

    if args.ask:
        threading.Thread(target=asker, args=(stop, args.ask * 60),
                         daemon=True).start()

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
    print(f"[serve] watching {', '.join(WATCHED)} every {args.poll:g}s")
    if args.ask:
        print(f"[serve] asking their tracker every {args.ask:g} min -- the bell "
              f"can light without you")
    else:
        print("[serve] not asking their tracker; the bell only moves after a "
              "sweep (--ask 15 to change that)")
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
