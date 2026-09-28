"""A read that fails once must not fail differently the second time.

`EvidenceStore.capture()` calls `response.read()` to write the body into the
manifest, inside `SafetyTransport.handle_request` -- before httpx's own
`Client.send()` gets to do its normal `response.read()` on the same object.
The first read usually wins and caches `_content`, so the second is a free
cache hit. On 2026-09-28, a sweep's `test_public_page_reads_are_documented`
crashed twice in a row on `httpx.StreamConsumed` -- not the real failure:
`capture()`'s `except Exception: response_body = b""` had swallowed a broken
first read and left `_content` unset, so `Client.send()`'s second attempt hit
a raw stream that had already started iterating and could not start again.
The report of a crash named no line in `qa/evidence.py` at all; `StreamConsumed`
is what a second read against a stream a first, hidden failure already began
looks like from the outside.
"""

from __future__ import annotations

import httpx

from qa.evidence import EvidenceStore
from qa.marks import SafetyTier, qa


class _BreaksOnce(httpx.SyncByteStream):
    """A body that raises the moment anything tries to iterate it."""

    def __iter__(self):
        raise httpx.ReadError("connection reset mid-body")

    def close(self) -> None:
        pass


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_broken_first_read_does_not_poison_the_second(tmp_path):
    request = httpx.Request("GET", "https://cymetica.com/agentbook")
    response = httpx.Response(200, stream=_BreaksOnce(), request=request)

    store = EvidenceStore("run-broken-read", root=tmp_path)
    # capture() must swallow the read failure -- it already did -- and must
    # leave `response` in a state a second, real read can still succeed on.
    store.capture(request, response, SafetyTier.SAFE, "test.rule")

    assert response.read() == b"", (
        "the caller's own read after capture() raised -- the same "
        "StreamConsumed a narrow sweep hit twice in a row on 2026-09-28, "
        "reported at the caller's line with no mention of evidence capture"
    )
