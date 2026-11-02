"""A mock is served uncached and read-only, from its own folder and nowhere else."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from qa.paths import REPO_ROOT


@pytest.fixture
def served(script, tmp_path):
    root = tmp_path / "mock"
    root.mkdir()
    (root / "index.html").write_text("<h1>mock</h1>", encoding="utf-8")
    (root / "my pic.txt").write_text("spaced", encoding="utf-8")
    (root / "clip.webm").write_bytes(bytes(range(100)))
    (root / "sub").mkdir()
    (root / "sub" / "index.html").write_text("sub page", encoding="utf-8")
    (root / "bare").mkdir()
    (root / "bare" / "mock.html").write_text("bare page", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside", encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), script("serve_mock").handler_for(root.resolve()))
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_a_page_is_served_with_no_store(served):
    with urllib.request.urlopen(f"{served}/") as response:
        assert response.read() == b"<h1>mock</h1>"
        assert response.headers["Cache-Control"] == "no-store"


def test_a_write_is_refused(served):
    request = urllib.request.Request(f"{served}/index.html", data=b"{}", method="POST")
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 403


def test_a_path_outside_the_folder_is_not_served(served):
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(f"{served}/..%2Fsecret.txt")
    assert caught.value.code == 404
    request = urllib.request.Request(f"{served}/x")
    request.selector = "/../secret.txt"
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 404


def test_a_range_gets_its_bytes_so_a_clip_can_seek(served):
    request = urllib.request.Request(f"{served}/clip.webm", headers={"Range": "bytes=10-19"})
    with urllib.request.urlopen(request) as response:
        assert response.status == 206
        assert response.read() == bytes(range(10, 20))
        assert response.headers["Content-Range"] == "bytes 10-19/100"
        assert response.headers["Accept-Ranges"] == "bytes"
    request = urllib.request.Request(f"{served}/clip.webm", headers={"Range": "bytes=90-"})
    with urllib.request.urlopen(request) as response:
        assert response.read() == bytes(range(90, 100))
    request = urllib.request.Request(f"{served}/clip.webm", headers={"Range": "bytes=-5"})
    with urllib.request.urlopen(request) as response:
        assert response.read() == bytes(range(95, 100))


def test_a_range_past_the_end_is_refused(served):
    request = urllib.request.Request(f"{served}/clip.webm", headers={"Range": "bytes=500-"})
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 416


def test_a_folder_without_its_slash_is_redirected_so_its_relative_links_work(served):
    with urllib.request.urlopen(f"{served}/sub") as response:
        assert response.url.endswith("/sub/")
        assert response.read() == b"sub page"


def test_a_folder_with_no_index_lists_its_files(served):
    with urllib.request.urlopen(f"{served}/bare/") as response:
        assert b"mock.html" in response.read()


def test_an_encoded_name_is_decoded(served):
    with urllib.request.urlopen(f"{served}/my%20pic.txt") as response:
        assert response.read() == b"spaced"


def test_an_encoded_traversal_is_not_served(served):
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(f"{served}/%2e%2e/secret.txt")
    assert caught.value.code == 404


def test_a_second_server_on_a_held_port_says_so(script):
    module = script("serve_mock")
    first = module.MockServer(("127.0.0.1", 0), module.handler_for(REPO_ROOT))
    try:
        with pytest.raises(OSError):
            module.MockServer(("127.0.0.1", first.server_address[1]), module.handler_for(REPO_ROOT))
    finally:
        first.server_close()


def test_a_bad_request_line_is_answered(script, served):
    import socket

    host, port = served.removeprefix("http://").split(":")
    with socket.create_connection((host, int(port)), timeout=5) as sock:
        sock.sendall(b"GARBAGE\r\n\r\n")
        assert b"400" in sock.recv(200)
