"""One click on a Sectors-chart bubble does what the chart's caption says (2026-10-04).

The Sectors tab's bubble chart ("Which sectors are starting to rise and which are
fading") says under itself "Click a bubble for the sector." The operator clicked the
AI bubble with a mouse: the first click did nothing he could see, the second opened
the sector's panel. Reproduced the same morning in a browser at 1398 px, by real
clicks: after click 1 the dark card was pinned (`#tip.open`) and the panel stayed
shut (`#themeBody` hidden); after click 2 the panel showed "AI".

The served script says why. A capture-phase click listener, commented "ET-28990 #3:
a click or tap on a hot-sector card or a point of the Sectors chart pins the same
dark card hover and Tab show; a second click on the same one opens its detail",
takes `#themeScatter g.pt`, stops the event and pins the card; only when the same
point is clicked again does it let the click through to the bubble's own
`openThemePanel`. That two-step is deliberate, and on a touch screen, which has no
hover, it is the only way to see the card. With a mouse the card is already on
screen from the hover, so the first click changes nothing a visitor can see, and
the caption promises the opposite.

What is held: the caption and the first click agree. It clears either way --
the caption saying what one click does, or the first-click card held to touch
(a hover/pointer media query, the event's pointer type, a touch probe).

What this can and cannot prove. It reads the served page through our client, so
it judges the code every browser is sent, not a browser running it. It fails only
on the mechanism found today, beside a one-click caption. A rewrite it cannot
read -- the listener gone, the renderer or its caption moved -- is INCONCLUSIVE,
never a pass, because whether one click then opens the sector is a question for a
browser. It does not read which way a hover gate points, and it did not tap a
touch screen.

SAFE: one GET, anonymous.
"""

from __future__ import annotations

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PAGE = "/gem-screener/app?view=sectors"


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_one_click_on_a_sectors_bubble_does_what_the_caption_says(rest_anon):
    """The Sectors chart's caption and what its first click does agree: a caption that
    promises one click is not served beside a listener that pins the hover card on the
    first click on every device."""
    try:
        response = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{PAGE} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {response.status_code}; a failed read is not "
                           f"a page whose chart does what it says")
    said = g.sector_click_promise(response.text)
    if said["verdict"] == "unread":
        raise Inconclusive(f"{PAGE}: {said['why']}")
    broken = said["verdict"] == "two_clicks"
    conclude(Measurement(
        verdict="failed" if broken else "passed",
        reason=(f'the Sectors chart caption says "{said["caption"]}", and a capture-phase click '
                f"listener (ET-28990 #3) pins the hover card on the first click on a bubble and stops "
                f"the event on every device, so with a mouse the panel opens on the second click"
                if broken else f"{said['why']}: \"{said['caption']}\""),
        left={"caption": said["caption"],
              "first_click_on_a_bubble": ("pins the hover card and stops the event, no hover or "
                                          "pointer gate" if broken else "held to touch, or not promised")},
        right={"caption": "says what one click does",
               "first_click_on_a_bubble": "opens the sector where hover already shows the card"},
        population={"caption": said["caption"], "first_click_listener": said["interceptor"]},
        sources={"page": PAGE}))
