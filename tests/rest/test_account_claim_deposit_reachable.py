"""/account opens its "Claim Missing Deposit" form when nothing is pending.

The form's own words: "If your deposit wasn't detected automatically, paste the transaction hash below."
Read 2026-10-17 from the public page and the scripts it loads (anonymously): the only control that opens it,
`data-click="openClaimDepositForm"` ("Deposit not showing? Submit tx hash"), sits inside the Pending
Deposits card `#accountPendingDeposits`, and the page script's loadAccountPendingDeposits hides that card
(`container.style.display = 'none'`) whenever /api/v1/funding/pending-deposits answers no rows. A deposit the
platform never detected leaves no pending row, so the form cannot be opened from /account in the one case
it is for. The Deposit dialog's "Sent a deposit but don't see it? Scan all networks" is a different,
automatic scan (POST /api/v1/funding/deposit/full-scan), not this form.

Failed when every control that opens the form is inside that card AND a script the page loads hides the
card on an empty pending list. Passes when a control outside the card, or a script call, opens the form, or
when no loaded script hides the card on an empty list any more. NOT asserted: which of these they choose,
or anything about a logged-in view (the page and its scripts are the same for everyone). Inconclusive when
the page, the form, its control or the card can no longer be found, when a verdict would rest on a script
that could not be read, or when a script hides the card but not provably on an empty list (C01, deep pass
2026-10-18: one exact text pattern was the only reading, and an unread script passed). SAFE: anonymous GETs of the page and
its own scripts; nothing they serve is called.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PAGE = "/account"
CARD = "accountPendingDeposits"
FORM = "claimDepositForm"
OPENER = "openClaimDepositForm"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Openers(HTMLParser):
    """Every element that opens the form, and whether the pending card encloses it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.openers: list[bool] = []          # True = inside the card
        self.ids: set[str] = set()
        self.scripts: list[str] = []
        self.inline: list[str] = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if a.get("data-click") == OPENER or OPENER + "(" in (a.get("onclick") or ""):
            self.openers.append(any(i == CARD for _, i in self.stack) or a.get("id") == CARD)
        if tag == "script":
            if a.get("src"):
                self.scripts.append(a["src"])
            else:
                self._in_script = True
        if tag not in VOID:
            self.stack.append((tag, a.get("id")))

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False
        for k in range(len(self.stack) - 1, -1, -1):  # close up to the matching open tag
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break

    def handle_data(self, data):
        if self._in_script:
            self.inline.append(data)


def _text(client, path: str) -> str | None:
    try:
        r = get_patiently(client, path)
    except httpx.HTTPError:
        return None
    return r.text if r.status_code == 200 else None


_LOOKUP = r"document\.(?:getElementById\(\s*['\"]" + CARD + r"['\"]\s*\)|querySelector\(\s*['\"]#" + CARD + r"['\"]\s*\))"
_HIDE = (r"\s*(?:\.style\.display\s*=\s*['\"]none['\"]|\.hidden\s*=\s*(?:true|!0)"
         r"|\.classList\.add\(\s*['\"](?:hidden|d-none|is-hidden)['\"]|\.setAttribute\(\s*['\"]hidden['\"])")
# A test that the list is empty, written out or minified: `.length === 0`, `.length < 1`, `!rows.length`.
_EMPTY = re.compile(r"\.length\s*(?:===?\s*0|<\s*1|<=\s*0)\b|!\s*[\w$.]+\.length\b")
_EMPTY_REACH = 160     # how far before the hide its condition may stand


def _hides_when_empty(js: str) -> bool | None:
    """True: a script hides the card under a test that the pending list is empty. False: nothing
    hides the card at all. None: something hides it, but not provably on an empty list -- neither a
    pass nor a defect.

    C01, deep pass 2026-10-18: one exact pattern of the hashed build (`.length === 0) {
    container.style.display = 'none'`) was the only reading, so a minified rebuild or `.hidden = true`
    read as "never hidden" and passed."""
    js = js or ""
    names = set(re.findall(r"([\w$]+)\s*=\s*" + _LOOKUP, js))
    targets = [re.escape(n) for n in names] + [_LOOKUP]
    hides = [m for t in targets for m in re.finditer(r"(?<![\w$.])" + t + _HIDE, js)]
    if not hides:
        return False
    if any(_EMPTY.search(js[max(0, m.start() - _EMPTY_REACH):m.start()]) for m in hides):
        return True
    return None


def _code(js: str) -> str:
    """The script without its comments: block comments, and a `//` line comment that is not a URL's."""
    js = re.sub(r"/\*.*?\*/", " ", js or "", flags=re.S)
    return re.sub(r"(?<![:'\"\\])//[^\n]*", " ", js)


def _calls(js: str) -> int:
    """Calls of the opener: not its definition (`function f(`, a method `f() {`, `f = function`,
    `f: function`), not a mention inside a string (the card's own markup), not a comment (C01)."""
    n = 0
    code = _code(js)
    for m in re.finditer(r"(?<![\w$])" + OPENER + r"\s*\(", code):
        before = code[max(0, m.start() - 12):m.start()]
        after = code[m.end():m.end() + 80]
        if re.search(r"function\s*$", before) or re.search(r"[\"'`]\s*$", before):
            continue
        if re.match(r"[^()]*\)\s*\{", after):      # `openClaimDepositForm() {` declares a method
            continue
        line = code[code.rfind("\n", 0, m.start()) + 1:m.start()]
        if line.count("'") % 2 or line.count('"') % 2 or line.count("`") % 2:
            continue                                # inside a string literal on this line
        n += 1
    return n


def judge(outside: int, calls: int, hides: bool | None, unread: list[str]) -> tuple[str | None, str]:
    """(verdict, why): "passed", "failed", or None for inconclusive.

    A control outside the card is in the page itself and needs no script. Every other verdict rests
    on what the scripts do not contain -- no call, no hide -- so it needs every script read: one that
    could not be read may hold either (C01, deep pass 2026-10-18)."""
    if outside:
        return "passed", "a control outside the pending card opens the form"
    if calls:
        return "passed", f"a script calls {OPENER}"
    if unread:
        return None, (f"{len(unread)} script(s) the page loads could not be read ({unread[:3]}); a call of "
                      f"{OPENER} or the card's hiding may be in them")
    if hides is None:
        return None, (f"a script hides #{CARD}, but not provably when the pending list is empty; read the "
                      f"script before calling it either way")
    if hides:
        return "failed", "hidden"
    return "passed", "no loaded script hides the pending card when nothing is pending"


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest")
def test_the_claim_form_opens_when_nothing_is_pending(rest_anon):
    """Every control that opens Claim Missing Deposit sits in a card the page hides when nothing is pending:
    failed. Any other way in, or a card that stays: passed."""
    html = _text(rest_anon, PAGE)
    if html is None:
        raise Inconclusive(f"{PAGE} did not answer a page")
    page = _Openers()
    page.feed(html)
    if FORM not in page.ids or CARD not in page.ids or not page.openers:
        raise Inconclusive(f"{PAGE} no longer has the form #{FORM}, the card #{CARD} or a control "
                           f"calling {OPENER}")
    scripts = [s for s in page.scripts if s.startswith("/") and not s.startswith("//")][:40]
    bodies = {s: _text(rest_anon, s) for s in scripts}
    read = {s: b for s, b in bodies.items() if b is not None}
    if not read:
        raise Inconclusive(f"none of the {len(scripts)} scripts {PAGE} loads could be read")
    js = "\n".join(list(read.values()) + page.inline)
    outside = page.openers.count(False)
    script_calls = _calls(js)
    hides = _hides_when_empty(js)
    unread = sorted(set(scripts) - set(read))
    population = {"controls": len(page.openers), "controls_outside_card": outside,
                  "script_calls": script_calls, "card_hidden_when_empty": hides,
                  "scripts_read": len(read), "scripts_unread": unread}
    verdict, why = judge(outside, script_calls, hides, unread)
    if verdict is None:
        raise Inconclusive(why)
    reachable = verdict == "passed"
    conclude(Measurement(
        verdict=verdict,
        reason=(why if reachable else
                f"all {len(page.openers)} control(s) that open Claim Missing Deposit sit inside #{CARD}, "
                f"which the page script hides when the pending list is empty: an undetected deposit "
                f"leaves nothing pending, so the form cannot be opened"),
        left={"ways_to_open_with_nothing_pending": 0 if not reachable else 1},
        right={"ways_to_open_with_nothing_pending": 1},
        population=population,
        sources={"page": PAGE, "scripts": scripts}))
