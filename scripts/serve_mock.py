"""Serve a mock folder as the operator opens it: python scripts/serve_mock.py outbox/<folder> <port> [--quiet]

Every file with Cache-Control: no-store. A bare http.server sends no such header, and on 2026-10-30 the operator's
browser kept an old index.html under the new CSS ("a co je toto za hnus?"). Their style.css, the fonts and the coin
logos load from their own hosts straight from the page. POST, PUT, PATCH and DELETE are refused: nothing is sent
from a copy. Range is answered, because a video clip seeks only where the server does. A folder with no index.html
lists its files. A mock that assembles its page or proxies their site keeps a serve.py of its own (pitch-cards).
"""

import html
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
         ".svg": "image/svg+xml", ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".mp4": "video/mp4",
         ".webm": "video/webm"}
RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def byte_range(header: str | None, size: int) -> tuple[int, int] | str | None:
    """(first, last) of a usable Range, "unsatisfiable", or None to send the whole file."""
    found = RANGE.match((header or "").strip())
    if not found or not (found.group(1) or found.group(2)):
        return None
    if not found.group(1):
        count = int(found.group(2))
        return (max(0, size - count), size - 1) if count and size else "unsatisfiable"
    first = int(found.group(1))
    last = min(int(found.group(2)), size - 1) if found.group(2) else size - 1
    return (first, last) if first <= last else "unsatisfiable"


def handler_for(root: Path):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def send(self, code, ctype, body, *headers):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Accept-Ranges", "bytes")
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def listing(self, folder: Path):
            names = sorted(p.name + ("/" if p.is_dir() else "") for p in folder.iterdir())
            links = "".join(f'<li><a href="{quote(n)}">{html.escape(n)}</a></li>' for n in names)
            return self.send(200, "text/html; charset=utf-8", f"<!doctype html><ul>{links}</ul>".encode("utf-8"))

        def do_GET(self):
            path = self.path.split("?")[0]
            found = (root / unquote(path).lstrip("/")).resolve()
            if found != root and root not in found.parents:
                return self.send(404, "text/plain; charset=utf-8", b"not here")
            if found.is_dir():
                if not path.endswith("/"):
                    # Without it, the page's relative links resolve one folder too high.
                    return self.send(301, "text/plain; charset=utf-8", b"", ("Location", path + "/"))
                if not (found / "index.html").is_file():
                    return self.listing(found)
                found = found / "index.html"
            if not found.is_file():
                return self.send(404, "text/plain; charset=utf-8", b"not here")
            ctype = TYPES.get(found.suffix.lower()) or mimetypes.guess_type(found.name)[0] or "application/octet-stream"
            body = found.read_bytes()
            wanted = byte_range(self.headers.get("Range"), len(body))
            if wanted == "unsatisfiable":
                return self.send(416, "text/plain; charset=utf-8", b"", ("Content-Range", f"bytes */{len(body)}"))
            if wanted:
                first, last = wanted
                return self.send(206, ctype, body[first:last + 1], ("Content-Range", f"bytes {first}-{last}/{len(body)}"))
            return self.send(200, ctype, body)

        do_HEAD = do_GET

        def refuse(self):
            self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

        do_POST = do_PUT = do_PATCH = do_DELETE = refuse

        def log_message(self, fmt, *args):
            if "--quiet" not in sys.argv:
                # A bad request line never set these: logging it must not lose the 400.
                sys.stderr.write("%s %s\n" % (getattr(self, "command", ""), getattr(self, "path", "")[:120]))

    return Handler


class MockServer(ThreadingHTTPServer):
    # On Windows the default lets a second server bind a port still held, and the old mock keeps answering.
    allow_reuse_address = False


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        raise SystemExit(__doc__.splitlines()[0])
    root, port = Path(args[0]).resolve(), int(args[1])
    if not root.is_dir():
        raise SystemExit(f"{root} is not a folder")
    try:
        server = MockServer(("127.0.0.1", port), handler_for(root))
    except OSError as exc:
        raise SystemExit(f"port {port} is taken: another mock is still running ({exc})") from exc
    print(f"{root.name}: http://127.0.0.1:{port}/  (Ctrl+C stops it)", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
