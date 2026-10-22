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

NOT asserted: which title the picture shows. The defect has a second face, a wrong stored title; this check reads the
first. If the page stops passing a `t` at all (a fix that corrects the stored title instead), there is nothing to
compare and the check is inconclusive, never passed: that fix needs a look at the picture.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PAGE = "/agent-tournaments"
HOST = "cymetica.com"
SENTINEL = "QA sentinel title 7f3c"


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
    """The og:image /agent-tournaments names changes when its `t` title changes."""
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
    ignored = other == first
    conclude(Measurement(
        verdict="failed" if ignored else "passed",
        reason=(f"{url} draws the same picture ({len(first)} bytes) whatever t= says: with t={title!r} and with "
                f"t={SENTINEL!r} the bytes are identical, so the title the page passes is not the title shown"
                if ignored else
                f"the picture changes with t= ({len(first)} bytes for the page's title, {len(other)} for a sentinel)"),
        left={"t_ignored": int(ignored)},
        right={"t_ignored": 0},
        population={"og_image": url, "page_title_t": title, "bytes_page_t": len(first), "bytes_sentinel_t": len(other)},
        sources={"page": PAGE, "og_image": url}))
