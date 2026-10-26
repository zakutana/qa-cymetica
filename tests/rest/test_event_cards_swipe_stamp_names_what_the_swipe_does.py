"""/events: the stamp an Event Card shows while it is dragged names what letting go does (2026-10-26).

Found 2026-10-26 while drawing the deck for a phone (outbox/event-card-mobile): dragging a card LEFT fades in a
red stamp that reads SELL, and letting go past the threshold SKIPS the card -- it flies off, the next card comes,
no Sell sheet opens and nothing is sold. Seen in a browser at 390 px, signed out, every non-GET aborted: held 220 px
left the stamp read SELL at opacity 1 on a card with `ec-card--glow-skip`; released, the deck moved on to the next
card with no sheet open. The keyboard hint on /events/{id} agrees with the release, not the stamp: "← Skip".

Why, read anonymously from what the page serves: event-cards.js builds the left stamp as
`skipLabel.className = 'ec-stamp ec-stamp--skip'; skipLabel.textContent = 'SELL';`, shows it while
`curX < -20` (`skipStamp.style.opacity = ratio`), and on release runs `if (dir === 'right') { animateSwipe(el,
'bull'); openBuySheet(card); } else { animateSwipe(el, 'skip'); }` -- whose own comment says "left = skip (fly
off)". The right side is consistent: BUY, and a right swipe opens the Buy sheet.

**The rule.** A stamp that names a trade (SELL, SHORT, BEAR / BUY, LONG, BULL) shows only on the side whose
release makes that trade or opens its sheet. A stamp that names no trade (SKIP, PASS, NEXT, an icon) is never
wrong here, and neither is a side that shows no stamp.

VERDICTS. failed: a drag shows a stamp naming a trade and letting go on that side neither makes it nor opens its
sheet. passed: on both sides the stamp shown names no trade, names the trade the release makes, or no stamp shows.
inconclusive: /events cannot be read; no script it loads builds a stamp with readable text; no drag handler that
shows a stamp, or no release that says what a side does, can be found; the stamp's text is computed; two scripts
build stamps that disagree.

NOT asserted: how the stamps look or where on the card they sit (on a phone the left stamp slides off the screen
with the card); the Buy sheet; the Back, Skip, Watch, Buy and Sell buttons, which do what they say.
SAFE: anonymous GETs of the page and the scripts it loads.
"""

from __future__ import annotations

import re

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently
from tests.rest.test_usage_dynamic_card_takes_a_cookie_session import MAX_SCRIPTS, _mask, _Page, _text

PAGE = "/events"
ORIGIN = "https://cymetica.com"

SELL = {"SELL", "SHORT", "BEAR"}
BUY = {"BUY", "LONG", "BULL"}
SELLS = re.compile(r"sell|short|bear", re.I)
BUYS = re.compile(r"buy|long|bull", re.I)

# `x.className = '... ec-stamp--skip ...'` -- the label's text is set on the same variable just after.
LABEL = re.compile(r"([\w$]+)\.className\s*=\s*(['\"])[^'\"]*?\bec-stamp--([\w-]+)\b[^'\"]*\2")
TEXT_OF = r"(?<![\w$.]){v}\.(?:textContent|innerText|innerHTML)\s*=\s*"
LITERAL = re.compile(r"(['\"`])((?:\\.|(?!\1)[^\\])*)\1\s*(?:[;,)}\n]|$)")
# The stamps written as markup: `<div class="ec-stamp ec-stamp--skip">SELL</div>`.
MARKUP = re.compile(r"class\s*=\s*\\?[\"'][^\"']*?\bec-stamp--([\w-]+)\b[^\"']*\\?[\"'][^>]*>([^<]*)<")
FIND = re.compile(r"([\w$]+)\s*=\s*[\w$.]+\.querySelector\(\s*(['\"])\.ec-stamp--([\w-]+)\2\s*\)")
# `if (curX > 20) {...}` / `else if (curX < -20) {...}`: which stamp a drag to that side fades in.
DRAG = re.compile(r"if\s*\(\s*[\w$.]+\s*(>|<)\s*(-?)\s*\d+(?:\.\d+)?\s*\)\s*\{([^{}]*)\}")
OPACITY = re.compile(r"([\w$]+)\.style\.opacity\s*=\s*([^;}\n]+)")
# `if (dir === 'right') {...} else {...}`: what letting go on each side does.
RELEASE = re.compile(r"if\s*\(\s*[\w$]+\s*===?\s*(['\"])(right|left)\1\s*\)\s*\{([^{}]*)\}\s*else\s*\{([^{}]*)\}")
SWIPE = re.compile(r"animateSwipe\s*\(\s*[\w$]+\s*,\s*(['\"])([\w-]+)\1")
SHEET = re.compile(r"\b(open\w*Sheet)\s*\(")


def _label_text(code: str, var: str, start: int) -> tuple[bool, str | None]:
    """(found, text) for the label held in `var`, set within a few hundred characters of its class name.
    found and None: the text is computed, which this check cannot read."""
    m = re.compile(TEXT_OF.format(v=re.escape(var))).search(code, start, start + 400)
    if not m:
        return False, None
    lit = LITERAL.match(code, m.end())
    if not lit:
        return True, None
    return True, re.sub(r"<[^>]*>", "", lit.group(2)).strip()


def script_facts(js: str) -> dict:
    """The stamps one script builds, which one a drag to each side shows, and what a release on each side does."""
    code = _mask(js, comments_only=True)
    stamps: dict[str, str | None] = {}
    for m in LABEL.finditer(code):
        found, text = _label_text(code, m.group(1), m.end())
        if found:
            stamps[m.group(3)] = text
    for m in MARKUP.finditer(code):
        stamps.setdefault(m.group(1), m.group(2).strip())
    held = {m.group(1): m.group(3) for m in FIND.finditer(code)}
    drag: dict[str, str | None] = {}
    for m in DRAG.finditer(code):
        side = "right" if m.group(1) == ">" and not m.group(2) else ("left" if m.group(1) == "<" and m.group(2) else None)
        if side is None or side in drag:
            continue
        shown = [held.get(v) for v, val in OPACITY.findall(m.group(3))
                 if val.strip().strip("'\"") not in ("0", "0.0", "") and v in held]
        if any(OPACITY.findall(m.group(3))) and all(v in held for v, _ in OPACITY.findall(m.group(3))):
            drag[side] = shown[0] if shown else None
    release: dict[str, dict] = {}
    m = next((r for r in RELEASE.finditer(code) if SWIPE.search(r.group(3)) or SWIPE.search(r.group(4))), None)
    if m:
        named, other = m.group(2), ("left" if m.group(2) == "right" else "right")
        for side, body in ((named, m.group(3)), (other, m.group(4))):
            act = SWIPE.search(body)
            release[side] = {"action": act.group(2) if act else None, "sheets": SHEET.findall(body)}
    return {"stamps": stamps, "drag": drag, "release": release}


def _side(f: dict, side: str) -> dict:
    """One side: the stamp a drag shows, the trade it names, what the release does, and whether they agree.
    consistent None: this side cannot be decided."""
    out = {"stamp": None, "names": None, "release": f["release"].get(side), "consistent": True, "why": ""}
    mod = f["drag"].get(side)
    if mod is None:
        out["why"] = "no stamp shows"
        return out
    if mod not in f["stamps"] or f["stamps"][mod] is None:
        out.update(consistent=None, why=f"the ec-stamp--{mod} stamp's text is computed or not found")
        return out
    text = f["stamps"][mod]
    out["stamp"] = text
    word = text.strip().upper()
    out["names"] = "sell" if word in SELL else ("buy" if word in BUY else None)
    if out["names"] is None:
        out["why"] = f"the stamp {text!r} names no trade"
        return out
    rel = out["release"]
    if not rel or (rel["action"] is None and not rel["sheets"]):
        out.update(consistent=None, why=f"what letting go on the {side} does could not be found")
        return out
    pattern = SELLS if out["names"] == "sell" else BUYS
    makes = bool(rel["action"] and pattern.search(rel["action"])) or any(pattern.search(s) for s in rel["sheets"])
    out["consistent"] = makes
    out["why"] = (f"the stamp {text!r} and the release ({rel['action']}, {rel['sheets'] or 'no sheet'}) agree" if makes
                  else f"dragging a card {side} shows the stamp {text!r}, but letting go runs animateSwipe "
                       f"{rel['action']!r}{' and ' + ', '.join(rel['sheets']) if rel['sheets'] else ' and opens no sheet'}")
    return out


def judge(scripts: list[dict]) -> tuple[str | None, str, dict]:
    """(verdict, why, sides): "failed", "passed", or None for inconclusive, over the script_facts of every script
    the page loads."""
    built = [f for f in scripts if f["stamps"]]
    if not built:
        return None, f"no script {PAGE} loads builds a swipe stamp (ec-stamp--*) with readable text", {}
    if any(f != built[0] for f in built[1:]):
        return None, f"{len(built)} scripts build swipe stamps and disagree; which one runs is not ours to guess", {}
    f = built[0]
    if not f["drag"]:
        return None, "no drag handler that shows a stamp was found", {}
    sides = {side: _side(f, side) for side in ("left", "right")}
    wrong = [s for s in ("left", "right") if sides[s]["consistent"] is False]
    if wrong:
        s = sides[wrong[0]]
        rel = s["release"]
        return "failed", (f"{s['why']}: the card is {'skipped' if rel['action'] == 'skip' else rel['action']}, "
                          f"nothing is {'sold' if s['names'] == 'sell' else 'bought'}"), sides
    unknown = [s for s in ("left", "right") if sides[s]["consistent"] is None]
    if unknown:
        return None, sides[unknown[0]]["why"], sides
    return "passed", "; ".join(f"{s}: {sides[s]['why']}" for s in ("left", "right")), sides


def _path(src: str) -> str | None:
    if src.startswith(ORIGIN + "/"):
        return src[len(ORIGIN):]
    return src if src.startswith("/") and not src.startswith("//") else None


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_event_cards_swipe_stamp_names_what_the_swipe_does(rest_anon):
    """The stamp a dragged Event Card shows names what letting go on that side does."""
    try:
        page = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{PAGE} could not be read: {type(exc).__name__}")
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    html = _Page()
    html.feed(page.text)
    srcs = [p for p in (_path(s) for s in html.srcs) if p][:MAX_SCRIPTS]
    first = [s for s in srcs if "event" in s.lower()]
    bodies = {s: _text(rest_anon, s) for s in first}
    scripts = [(f"inline script {k + 1} of {len(html.inline)}", js) for k, js in enumerate(html.inline)]
    scripts += [(s, b) for s, b in bodies.items() if b is not None]
    if not any("ec-stamp" in js for _, js in scripts):
        rest = {s: _text(rest_anon, s) for s in srcs if s not in bodies}
        bodies.update(rest)
        scripts += [(s, b) for s, b in rest.items() if b is not None]
    unread = sorted(s for s, b in bodies.items() if b is None)
    facts = [(label, script_facts(js)) for label, js in scripts]
    verdict, why, sides = judge([f for _, f in facts])
    built = [(label, f) for label, f in facts if f["stamps"]]
    population = {
        "scripts_that_build_stamps": [label for label, _ in built],
        "stamps": built[0][1]["stamps"] if built else {},
        "drag_shows": built[0][1]["drag"] if built else {},
        "release_does": built[0][1]["release"] if built else {},
        "sides": sides,
        "scripts_read": len(scripts), "scripts_unread": unread,
        "page_date": page.headers.get("date"),
    }
    if verdict is None:
        if unread and not built:
            why = f"{why}; {len(unread)} script(s) could not be read ({unread[:3]})"
        raise Inconclusive(why)
    left = sides.get("left") or {}
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{why}. On {PAGE} a visitor who drags a card left reads {left.get('stamp')!r} on it and, letting "
                f"go, has skipped the card instead" if verdict == "failed" and left.get("consistent") is False else why),
        left={"left_drag_stamp": left.get("stamp")},
        right={"left_release": left.get("release")},
        population=population,
        sources={"page": f"{PAGE} (the script tags)", "scripts": [label for label, _ in built] or srcs}))
