"""A body that could not be read reaches the caller as the failure it was.

`EvidenceStore.capture()` calls `response.read()` to write the body into the
manifest, inside `SafetyTransport.handle_request` -- before httpx's own
`Client.send()` gets to do its normal `response.read()` on the same object.

Twice wrong on 2026-09-28. In the morning a sweep crashed on
`httpx.StreamConsumed`: `capture()`'s `except Exception: response_body = b""`
had swallowed a broken first read and left `_content` unset, so the client's
second read met a stream already started. The fix cached an empty body
instead -- and so turned every failed body read into a 200 with nothing in it.
At 14:56 UTC a read timeout while downloading /openapi-public.json reached
its check as "200 with a malformed body", and that went to Cymetica as their
defect (MSG-0089); they could not reproduce it, because it was ours. Rule 8:
a failed read is not an empty read. The read error itself goes up.
"""

from __future__ import annotations

import httpx
import pytest

from qa.evidence import EvidenceStore
from qa.marks import SafetyTier, qa


class _BreaksOnce(httpx.SyncByteStream):
    """A body that raises the moment anything tries to iterate it."""

    def __iter__(self):
        raise httpx.ReadTimeout("the read operation timed out mid-body")

    def close(self) -> None:
        pass


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_body_that_could_not_be_read_is_never_an_empty_answer(tmp_path):
    request = httpx.Request("GET", "https://cymetica.com/openapi-public.json")
    response = httpx.Response(200, stream=_BreaksOnce(), request=request)
    store = EvidenceStore("run-broken-read", root=tmp_path)
    with pytest.raises(httpx.ReadTimeout):
        store.capture(request, response, SafetyTier.SAFE, "test.rule")

    # End to end, through the guard, the way a check meets it: the timeout,
    # not StreamConsumed and not a 200 with an empty body.
    from qa.client import build_mock_client
    from qa.safety import CURRENT_TIER

    client = build_mock_client(
        lambda req: httpx.Response(200, stream=_BreaksOnce(), request=req),
        evidence=EvidenceStore("run-broken-read-2", root=tmp_path))
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        with pytest.raises(httpx.ReadTimeout):
            client.get("/openapi-public.json")
    finally:
        CURRENT_TIER.reset(token)
        client.close()
