"""Serves this page on 127.0.0.1:8800 for the operator's look (.claude/launch.json quest-steps). Python's own
http.server, but with HTTP/1.1 and Range requests: a clip seeks (data-loop-from, the loop point of a cross-fade) only
where the server answers a Range, and the stock server answered every one with the whole file from byte 0.

    python outbox/quest-steps/serve.py [port]
"""
import functools
import http.server
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Ranged(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def send_head(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not rng.startswith('bytes=') or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        a, _, b = rng[6:].partition('-')
        try:
            start = int(a) if a else max(0, size - int(b))
            end = min(size - 1, int(b)) if (b and a) else size - 1
        except ValueError:
            return super().send_head()
        if start >= size or start > end:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        f = open(path, 'rb')
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        f.seek(start)
        return _Slice(f, end - start + 1)

    def copyfile(self, source, outputfile):
        if isinstance(source, _Slice):
            left = source.left
            while left > 0:
                chunk = source.f.read(min(left, 1 << 16))
                if not chunk:
                    break
                outputfile.write(chunk)
                left -= len(chunk)
            return
        super().copyfile(source, outputfile)


class _Slice:
    def __init__(self, f, left):
        self.f, self.left = f, left

    def close(self):
        self.f.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8800
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Ranged, directory=str(HERE)))
    print(f'quest-steps on http://127.0.0.1:{port}/', flush=True)
    srv.serve_forever()
