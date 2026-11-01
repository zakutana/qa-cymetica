"""A mock is served uncached and read-only, from its own folder and nowhere else."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest


@pytest.fixture
def served(script, tmp_path):
    root = tmp_path / "mock"
    root.mkdir()
    (root / "index.html").write_text("<h1>mock</h1>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside", encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), script("serve_mock").handler_for(root.resolve()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
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
