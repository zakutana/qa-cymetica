"""READ: a source that did not answer must not become a measured value.

The audit closed "absence is verification" on the STATE axis -- the fold will
not close a row it did not run. This file closes the same hole one layer down,
on the READ axis, where it survived and where every one of 2026-09-05's four
self-inflicted errors happened.

All four were the same shape. A check read something, got nothing usable back,
and carried the nothing forward into a comparison as if it were data:

  1. my-reports was called without the credential it requires. The 401 body
     has no `reports` key, `.get("reports") or []` produced [], and the check
     reported "we cannot see our own reports" -- a finding about the vendor
     manufactured entirely out of our own missing header.

  2. The trust ladder took the caller's tier from the name of OUR config
     variable (QA_TRUSTED_KEY -> "trusted") and reported over-serving. The
     platform assigns ALLIED. Report #54, correctly rejected as invalid.

  3. list_clob_pairs was counted with len(pairs) on a default call. The same
     object states total=569, limit=200, offset=0. Report #52 went out saying
     "200 vs 568" -- a page size presented to the vendor as a catalogue size.

  4. The pagination check that replaced (3) keyed rows on "symbol", which no
     pair carries. Every row read None, the two pages "overlapped" on that one
     None, and it reported a pagination defect that does not exist.

Each is a one-line mistake, and that is the point: they are not going to be
prevented by being more careful. The readers in qa/measure.py make the absent
case raise instead of return, so the mistake becomes Inconclusive with a
reason rather than a verdict. These are the four shapes, held down.
"""

from __future__ import annotations

import pytest

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import (MissingData, collection_size, field_of_every,
                        required)

# Verbatim shapes, so this file fails if any of them stops being handled.
UNAUTHORIZED = {"detail": "Authentication required. Provide Bearer token or "
                          "X-API-Key header."}
CLOB_PAGE = {"pairs": [{"pair": "SBIO/USDC", "enabled": True},
                       {"pair": "VAIX/USDC", "enabled": True}],
             "total": 569, "limit": 200, "offset": 0}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_absent_field_raises_instead_of_reading_as_a_value():
    """Incident 1: a 401 body has no `reports`, and [] is not zero reports."""
    with pytest.raises(MissingData) as caught:
        required(UNAUTHORIZED, "reports", "GET /api/v1/bounty/my-reports")
    message = str(caught.value)
    assert "reports" in message and "my-reports" in message, message
    # It must say what the body DID carry, or the reader is just a crash.
    assert "detail" in message, message

    # And it must be Inconclusive, never a failure: a missing field is our
    # inability to measure, not a defect in the thing being measured.
    assert isinstance(caught.value, Inconclusive)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_field_holding_none_is_not_a_missing_field():
    """The distinction `.get()` cannot make, and the reason this exists."""
    assert required({"total": None}, "total", "where") is None
    with pytest.raises(MissingData):
        required({}, "total", "where")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_page_size_cannot_be_read_as_collection_size():
    """Incident 3: the response states its own total; len() states ours."""
    assert collection_size(CLOB_PAGE, "total", "pairs", "list_clob_pairs") == 569

    # A response with no stated total cannot be sized by counting it.
    with pytest.raises(MissingData) as caught:
        collection_size({"pairs": CLOB_PAGE["pairs"]}, "total", "pairs", "list_clob_pairs")
    assert "total" in str(caught.value)

    # Nor can one whose numbers contradict each other.
    with pytest.raises(MissingData):
        collection_size({"pairs": [1, 2, 3], "total": 2}, "total", "pairs", "x")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_key_no_row_carries_cannot_be_compared():
    """Incident 4: keying on `symbol` gave 569 Nones and one false finding."""
    with pytest.raises(MissingData) as caught:
        field_of_every(CLOB_PAGE["pairs"], "symbol", "list_clob_pairs")
    message = str(caught.value)
    assert "2 of 2" in message, message
    # Naming the keys that ARE there is what turns this into a fix.
    assert "pair" in message, message

    assert field_of_every(CLOB_PAGE["pairs"], "pair", "x") == ["SBIO/USDC", "VAIX/USDC"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_partially_present_key_is_refused_as_a_whole():
    """The dangerous middle case: some rows answer, some do not.

    Silently dropping the absent ones shrinks the population without saying
    so, which is how a comparison ends up being right about a subset and
    presented as being right about everything.
    """
    rows = [{"pair": "A/USDC"}, {"pair": None}, {"pair": "C/USDC"}]
    with pytest.raises(MissingData) as caught:
        field_of_every(rows, "pair", "list_clob_pairs")
    assert "1 of 3" in str(caught.value)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_empty_rows_are_not_an_empty_answer():
    """Zero rows can mean zero things, or a read that failed. Say which."""
    with pytest.raises(MissingData):
        field_of_every([], "pair", "list_clob_pairs")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_path_is_not_a_substring():
    """Incident 5, same family: comparing structured things as text.

    /api/v1/account occurs inside /api/v1/account/me. The pinned 404 check
    asked `path in document`, so after the vendor renamed three paths on
    2026-09-04 it went on reporting them as still documented and still broken.
    Two days of a red row and a re-report, #59, about a fix that had shipped
    before it was written. Their own note said to grep EXACT, which is exactly
    the distinction that was missing.
    """
    from tests.pinned.test_documented_404 import documents_the_path, successors

    renamed = "documented: /api/v1/account/me and /api/v1/agentbook/posts"
    assert not documents_the_path(renamed, "/api/v1/account")
    assert not documents_the_path(renamed, "/api/v1/agentbook/post")
    assert documents_the_path(renamed, "/api/v1/account/me")

    # The check must still be able to fail: a path that IS documented, exactly,
    # has to read as documented however it is punctuated around.
    for around in ("GET /api/v1/account.", "`/api/v1/account`",
                   "/api/v1/account)", "see /api/v1/account\n"):
        assert documents_the_path(around, "/api/v1/account"), around

    # And a rename has to be reported as a rename, not as a disappearance.
    assert successors(renamed, "/api/v1/account") == {"/api/v1/account/me"}
    assert successors("nothing here", "/api/v1/account") == set()
