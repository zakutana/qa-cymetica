"""Serve a mock folder as the operator opens it: python scripts/serve_mock.py outbox/<folder> <port> [--quiet]

Every file with Cache-Control: no-store. A bare http.server sends no such header, and on 2026-10-30 the operator's
browser kept an old index.html under the new CSS ("a co je toto za hnus?"). Their style.css, the fonts and the coin
logos load from their own hosts straight from the page. POST, PUT, PATCH and DELETE are refused: nothing is sent
from a copy.
"""

import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
         ".svg": "image/svg+xml", ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".mp4": "video/mp4"}


def handler_for(root: Path):
    class Handler(BaseHTTPRequestHandler):
        def send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            rel = self.path.split("?")[0].lstrip("/") or "index.html"
            found = (root / rel).resolve()
            if found.is_dir():
                found = found / "index.html"
            if not found.is_file() or root not in found.parents:
                return self.send(404, "text/plain; charset=utf-8", b"not here")
            ctype = TYPES.get(found.suffix.lower()) or mimetypes.guess_type(found.name)[0] or "application/octet-stream"
            return self.send(200, ctype, found.read_bytes())

        do_HEAD = do_GET

        def refuse(self):
            self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

        do_POST = do_PUT = do_PATCH = do_DELETE = refuse

        def log_message(self, fmt, *args):
            if "--quiet" not in sys.argv:
                sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))

    return Handler


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        raise SystemExit(__doc__.splitlines()[0])
    root, port = Path(args[0]).resolve(), int(args[1])
    if not root.is_dir():
        raise SystemExit(f"{root} is not a folder")
    print(f"{root.name}: http://127.0.0.1:{port}/  (Ctrl+C stops it)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), handler_for(root)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
