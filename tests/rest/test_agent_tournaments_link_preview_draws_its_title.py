"""The link preview of /agent-tournaments draws the title its page asks for (2026-10-22).

Found while building the Promo Market mockup: the page's og:image is
/og/app/agent-tournaments.png?t=Agent%20Tournaments%3A%2010%20agents.%201%20table.%20Best%20ROI%20wins.&v=4,
and the picture that URL answers carries the headline "Add https://cymetica.com/agent-tournaments to main menu"
-- the title of a Build it Better request, not the page's. So a link to /agent-tournaments posted on X or Telegram
shows a ticket's title as the product's card.

What is measured, without reading the picture's text: the image the page names is fetched twice (it must be the same
picture both times, or nothing can be judged), then once more with its `t` swapped for a sentinel title. If the
sentinel's picture is byte for byte the same, the image does not draw the `t` the page passes, and draws a title from
somewhere else: failed. If it differs, `t` is drawn: passed.

The defect has a second face, a wrong stored title, and that is the fix they made (#217, paid 2026-10-22): the picture
still ignores `t`, but the title stored for it is now the page's. The first version of this check sent that fix to
inconclusive only when the page stopped passing a `t`; the page kept passing one, so the corrected picture read as
"failed" and a FAIL was owed on a defect that is gone (the sweep of 2026-10-23, run-20261023T163916Z-8a403f54).
So a picture that ignores `t` is judged by its text, read by a person: LOOKED holds the sha256 of each picture
somebody read and the title it draws. Read and the same as the page's `t` (punctuation and case aside): passed. Read
and different: failed, the second face. Never read: inconclusive, until somebody looks and adds it.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PAGE = "/agent-tournaments"
HOST = "cymetica.com"
SENTINEL = "QA sentinel title 7f3c"
# sha256 of the picture's bytes (of the file, not qa/evidence.py's content_id) -> the title read off it, and when
LOOKED = {
    "1c683f1a1f919809203231f40fd1265b88493de0d021e080f80ff33c97911886":
        ("Agent Tournaments: 10 agents, 1 table, best ROI wins", "2026-10-23"),
}


def _norm(title: str) -> str:
    return " ".join(re.sub(r"[.,:;!?]", " ", title).casefold().split())


def drawn_title(first: bytes, other: bytes, title: str, looked: dict = LOOKED) -> tuple[str, str, dict]:
    """The verdict on one picture: `first` fetched with the page's `t`, `other` with the sentinel's.

    A picture that changes with `t` draws it: passed. One that does not draws a stored title, judged by the title a
    person read off it: the page's `t` but for punctuation and case passes, another fails; never read, inconclusive.
    """
    if other != first:
        return "passed", (f"the picture changes with t= ({len(first)} bytes for the page's title, {len(other)} for a "
                          "sentinel)"), {}
    sha = hashlib.sha256(first).hexdigest()
    if sha not in looked:
        return "inconclusive", (f"the picture is the same ({len(first)} bytes, sha256 {sha[:12]}) whatever t= says, and "
                                "nobody has read this picture: look at it and add the title it draws to LOOKED"), {"sha256": sha}
    drawn, read_on = looked[sha]
    seen = {"sha256": sha, "title_read": drawn, "read_on": read_on}
    if _norm(drawn) == _norm(title):
        return "passed", (f"the picture ignores t= and draws its stored title {drawn!r} (read {read_on}), which is the "
                          f"page's t={title!r} but for punctuation and case"), seen
    return "failed", (f"the picture ignores t= and draws {drawn!r} (read {read_on}), while the page passes "
                      f"t={title!r}: the preview shows another title"), seen


def _image(client, path: str) -> bytes:
    try:
        response = get_patiently(client, path)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{path} could not be read: {type(exc).__name__}")
    kind = (response.headers.get("content-type") or "").split(";")[0].strip()
    if response.status_code != 200 or not kind.startswith("image/"):
        raise Inconclusive(f"{path} answered HTTP {response.status_code} {kind or 'no content type'}; "
                           "a failed read is not a picture with the wrong title")
    return response.content


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest")
def test_the_agent_tournaments_link_preview_draws_the_title_its_page_passes(rest_anon):
    """The og:image /agent-tournaments names draws its `t` title: it changes with `t`, or a person read the title."""
    try:
        page = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{PAGE} could not be read: {type(exc).__name__}")
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    url = g.share_images(page.text).get("og:image")
    if not url:
        raise Inconclusive(f"{PAGE} names no og:image; a page without a preview is another check's")
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != HOST:
        raise Inconclusive(f"{PAGE} names its og:image on {parsed.netloc}, not on {HOST}")
    query = parse_qsl(parsed.query, keep_blank_values=True)
    title = dict(query).get("t")
    if not title:
        raise Inconclusive(f"{url} passes no t= title any more, so there is nothing to compare: look at the picture")
    path = parsed.path + "?" + parsed.query
    sentinel = parsed.path + "?" + urlencode([(k, SENTINEL if k == "t" else v) for k, v in query])

    first, second = _image(rest_anon, path), _image(rest_anon, path)
    if first != second:
        raise Inconclusive(f"{path} answered two different pictures to two identical reads ({len(first)} and "
                           f"{len(second)} bytes); a byte comparison judges nothing here")
    other = _image(rest_anon, sentinel)
    verdict, reason, seen = drawn_title(first, other, title)
    if verdict == "inconclusive":
        raise Inconclusive(f"{url}: {reason}")
    conclude(Measurement(
        verdict=verdict,
        reason=f"{url}: {reason}",
        left={"title_drawn": int(verdict == "passed")},
        right={"title_drawn": 1},
        population={"og_image": url, "page_title_t": title, "bytes_page_t": len(first), "bytes_sentinel_t": len(other),
                    **seen},
        sources={"page": PAGE, "og_image": url}))
