"""A Gem Screener link posted on X shows a card, not a placeholder (2026-10-02).

The operator posted https://cymetica.com/gem-screener/app in a tweet. The card came
out as a grey placeholder with no image. The page's own tags name the image:
`og:image` and `twitter:image` are both /static/images/og-default.png, and that file
answers 404 -- while the sibling page /gem-screener names a dynamic image
(/og/app/gem-screener.png) that does answer, as a 1200 x 630 PNG.

This holds what any redesign has to keep true: every image a Gem Screener page names
for its link preview answers 200 and is an image.

NOT asserted: how the card looks, or which image it is -- only that there is one.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PAGES = ["/gem-screener", "/gem-screener/app"]
HOST = "cymetica.com"
MIN_IMAGE_BYTES = 2000


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_gem_screener_link_preview_has_an_image_that_answers(rest_anon):
    """Every `og:image` / `twitter:image` the Gem Screener pages name answers 200
    with an image of some size."""
    judged, broken = [], []
    for page in PAGES:
        try:
            response = get_patiently(rest_anon, page, headers={"Accept": "text/html"})
        except httpx.HTTPError as exc:
            raise Inconclusive(f"{page} could not be read: {type(exc).__name__}")
        if response.status_code != 200:
            raise Inconclusive(f"{page} answered HTTP {response.status_code}; a failed read is not a page without an image")
        named = g.share_images(response.text)
        if not named:
            broken.append({"page": page, "tag": None, "url": None, "why": "names no preview image"})
            continue
        for tag, url in sorted(named.items()):
            parsed = urlparse(url)
            if parsed.netloc and parsed.netloc != HOST:
                raise Inconclusive(f"{page} names {tag} on {parsed.netloc}, not on {HOST}; this check reads only their own host")
            path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            try:
                image = get_patiently(rest_anon, path)
            except httpx.HTTPError as exc:
                raise Inconclusive(f"{url} could not be read: {type(exc).__name__}")
            kind = (image.headers.get("content-type") or "").split(";")[0].strip()
            row = {"page": page, "tag": tag, "url": url, "status": image.status_code,
                   "content_type": kind, "bytes": len(image.content)}
            judged.append(row)
            if image.status_code != 200:
                broken.append(dict(row, why=f"answers HTTP {image.status_code}"))
            elif not kind.startswith("image/"):
                broken.append(dict(row, why=f"answers {kind or 'no content type'}, not an image"))
            elif len(image.content) < MIN_IMAGE_BYTES:
                broken.append(dict(row, why=f"is {len(image.content)} bytes"))
    conclude(Measurement(
        verdict="failed" if broken else "passed",
        reason=("; ".join(f"{b['page']} {b['tag']} {b['url']} {b['why']}" for b in broken[:4])
                if broken else
                f"all {len(judged)} preview images named by {len(PAGES)} pages answer 200 as images"),
        left={"images_broken": len(broken), "images_read": len(judged)},
        right={"images_broken": 0},
        population={"broken": broken, "read": judged},
        sources={"pages": ", ".join(PAGES)}))
