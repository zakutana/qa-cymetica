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
card on an empty pending list (or its own markup hides it and no script shows it). Passes when a control
outside the card, or a script call that runs with nothing pending from outside the card, opens the form,
or when no loaded script hides the card on an empty list any more. NOT asserted: which of these they
choose, or anything about a logged-in view (the page and its scripts are the same for everyone).
Inconclusive when the page, the form, its control or the card can no longer be found, when a verdict would
rest on a script that could not be read, when a script hides the card but not provably on an empty list or
changes how it shows in a way not read, when the card is hidden in its markup and a script shows it under
a condition not read, or when a call of the opener runs from something not read (C01, deep pass
2026-10-18: one exact text pattern was the only reading, and an unread script passed; A03, deep pass
2026-10-25: unrecognised hiding read as "never hidden", and the in-card button's own wiring or a call per
pending row counted as a way in). SAFE: anonymous GETs of the page and its own scripts; nothing they serve
is called.
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
_HIDE_CLASSES = {"hidden", "d-none", "is-hidden"}


class _Openers(HTMLParser):
    """Every element that opens the form, and whether the pending card encloses it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.openers: list[bool] = []          # True = inside the card
        self.ids: set[str] = set()
        self.scripts: list[str] = []
        self.inline: list[str] = []
        self.card_starts_hidden = False        # the card's own markup hides it before any script runs
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if a.get("id") == CARD:
            style = (a.get("style") or "").lower()
            self.card_starts_hidden = ("hidden" in a
                                       or bool(re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", style))
                                       or bool(set((a.get("class") or "").split()) & _HIDE_CLASSES))
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


# Any lookup of the card by its id: `document.getElementById('X')`, `querySelector('#X')`, or a helper
# such as `$('X')` / `byId("#X")` (A03, deep pass 2026-10-25: a helper's lookup read as "never hidden").
_LOOKUP = r"(?:[\w$]+\s*\.\s*)*[\w$]+\(\s*['\"]#?" + CARD + r"['\"]\s*\)"
_HIDE_CLASS = r"['\"](?:hidden|d-none|is-hidden)['\"]"
_HIDE = re.compile(r"\s*(?:\.style\.display\s*=\s*['\"]none['\"]|\.hidden\s*=\s*(?:true|!0)\b"
                   r"|\.classList\.add\(\s*" + _HIDE_CLASS + r"|\.setAttribute\(\s*['\"]hidden['\"])")
_SHOW = re.compile(r"\s*(?:\.style\.display\s*=\s*['\"](?!none['\"])[\w-]*['\"]|\.hidden\s*=\s*(?:false|!1)\b"
                   r"|\.classList\.remove\(\s*" + _HIDE_CLASS + r"\s*\)|\.removeAttribute\(\s*['\"]hidden['\"]\s*\))")
# A write whose value carries its own condition: `.hidden = EXPR`, `.style.display = COND ? A : B`,
# `.classList.toggle('hidden', EXPR)`.
_VALUE = re.compile(r"\s*(?:\.hidden\s*=(?!=)\s*(?P<flag>[^;\n]+)|\.style\.display\s*=(?!=)\s*(?P<display>[^;\n]+)"
                    r"|\.classList\.toggle\(\s*" + _HIDE_CLASS + r"\s*,\s*(?P<toggle>[^;\n]+?)\)\s*(?:;|\n|$))")
# Anything else that can change whether the card shows: read, it is not "never hidden" (A03).
_TOUCH = re.compile(r"\s*(?:\.style\.(?:display|visibility|cssText|opacity|setProperty)\b|\.style\s*=(?!=)"
                    r"|\.hidden\s*=(?!=)|\.classList\.(?:add|remove|toggle|replace)\(|\.className\s*=(?!=)"
                    r"|\.(?:set|remove|toggle)Attribute\(|\.remove\(\s*\)|\.replaceWith\(|\.outerHTML\s*=(?!=)"
                    r"|\.(?:hide|show|toggle|fadeOut|fadeIn|slideUp|slideDown|css|addClass|removeClass|toggleClass"
                    r"|attr|prop)\()")
# A test that the list is empty, written out or minified: `.length === 0`, `.length < 1`, `!rows.length`.
_EMPTY = re.compile(r"\.length\s*(?:===?\s*0|<\s*1|<=\s*0)\b|!\s*[\w$.]+\.length\b")
_NOT_EMPTY = re.compile(r"\.length\s*(?:>\s*0|>=\s*1|!==?\s*0)?\s*$")
_EMPTY_REACH = 160     # how far before the hide its condition may stand
_KEYWORDS = {"if", "while", "for", "switch", "catch", "return", "typeof", "void", "await", "in", "of", "new",
             "delete", "case", "do", "else", "yield", "with"}


def _code(js: str) -> str:
    """The script without its comments: block comments, and a `//` line comment that is not a URL's."""
    js = re.sub(r"/\*.*?\*/", " ", js or "", flags=re.S)
    return re.sub(r"(?<![:'\"\\])//[^\n]*", " ", js)


def _skip_string(code: str, i: int) -> int:
    """The index just past the string literal that opens at `i`."""
    j = i + 1
    while j < len(code) and code[j] != code[i]:
        j += 2 if code[j] == "\\" else 1
    return j + 1


def _open_brackets(code: str, pos: int) -> list[int]:
    """Where each `(`, `[` and `{` still open at `pos` stands, outermost first; strings skipped."""
    stack, i = [], 0
    while i < pos:
        ch = code[i]
        if ch in "'\"`":
            i = _skip_string(code, i)
            continue
        if ch in "([{":
            stack.append(i)
        elif ch in ")]}" and stack:
            stack.pop()
        i += 1
    return stack


def _block_end(code: str, pos: int) -> int:
    """Where the innermost `{ }` block around `pos` closes (the end of the script at the top level)."""
    blocks = [at for at in _open_brackets(code, pos) if code[at] == "{"]
    if not blocks:
        return len(code)
    depth, i = 0, blocks[-1]
    while i < len(code):
        ch = code[i]
        if ch in "'\"`":
            i = _skip_string(code, i)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(code)


def _card_references(code: str) -> tuple[list[tuple[int, int]], int]:
    """Every place the script takes hold of the card -- a lookup, or a name bound to one while that
    name still holds it (to the end of the block it was bound in, or the next assignment to the name:
    the fund modal's own `container` is another element) -- and how many mentions of the card's id are
    not a lookup at all (a constant, a selector, markup the script draws: unread)."""
    lookups = [(m.start(), m.end()) for m in re.finditer(_LOOKUP, code)]
    refs = list(lookups)
    for bind in re.finditer(r"(?<![\w$.])([\w$]+)\s*=\s*" + _LOOKUP, code):
        name = re.escape(bind.group(1))
        rebound = re.compile(r"(?<![\w$.])" + name + r"\s*=(?!=)").search(code, bind.end())
        stop = min(rebound.start() if rebound else len(code), _block_end(code, bind.start()))
        refs += [(u.start(), u.end()) for u in re.finditer(r"(?<![\w$.])" + name + r"(?![\w$])", code)
                 if bind.end() <= u.start() < stop]
    stray = sum(1 for m in re.finditer(re.escape(CARD), code) if not any(a <= m.start() < b for a, b in lookups))
    return refs, stray


def _ternary(expr: str) -> tuple[str, str, str] | None:
    m = re.fullmatch(r"\s*\(?(.+?)\?\s*(['\"])(.*?)\2\s*:\s*(['\"])(.*?)\4\s*\)?\s*", expr)
    return (m.group(1), m.group(3), m.group(5)) if m else None


def _reading(code: str, start: int, end: int) -> str:
    """What one reference does to the card: "empty" (hides it under a test that the list is empty),
    "other" (hides it, not provably then), "show", "unknown" (changes how it shows in a way not read,
    or hands it to a function), or "none" (reads it, fills it)."""
    after = code[end:end + 240]
    if _SHOW.match(after):
        return "show"
    if _HIDE.match(after):
        return "empty" if _EMPTY.search(code[max(0, start - _EMPTY_REACH):start]) else "other"
    value = _VALUE.match(after)
    if value:
        if value.group("display") is not None:
            split = _ternary(value.group("display"))
            if split is None:
                return "unknown"
            cond, yes, no = split
            if _EMPTY.search(cond):
                return "empty" if yes == "none" else "other" if no == "none" else "show"
            if _NOT_EMPTY.search(cond.strip()):
                return "empty" if no == "none" else "other" if yes == "none" else "show"
            return "unknown"
        expr = value.group("flag") if value.group("flag") is not None else value.group("toggle")
        return "empty" if _EMPTY.search(expr) else "unknown"
    if _TOUCH.match(after):
        return "unknown"
    call = re.search(r"(function\s+)?([\w$.]+)\s*\((?:[^()]*,)?\s*$", code[max(0, start - 80):start])
    if (call and not call.group(1) and call.group(2).split(".")[-1] not in _KEYWORDS
            and re.match(r"\s*[,)]", after)):
        return "unknown"                       # `setVisible(card, ...)`: what it does is not read
    return "none"


def _card_readings(js: str) -> tuple[list[str], int]:
    code = _code(js)
    refs, stray = _card_references(code)
    return [_reading(code, a, b) for a, b in refs], stray


def _hides_when_empty(js: str) -> bool | None:
    """True: a script hides the card under a test that the pending list is empty. False: no script
    changes whether the card shows, or one only shows it. None: something hides it but not provably on
    an empty list, or changes how it shows in a way this does not read -- neither a pass nor a defect.

    C01, deep pass 2026-10-18: one exact pattern of the hashed build (`.length === 0) {
    container.style.display = 'none'`) was the only reading, so a minified rebuild or `.hidden = true`
    read as "never hidden" and passed. A03, deep pass 2026-10-25: anything else it did not recognise --
    `classList.toggle('hidden', !rows.length)`, a lookup through a helper -- still read "never hidden"."""
    kinds, stray = _card_readings(js or "")
    if "empty" in kinds:
        return True
    if "other" in kinds or "unknown" in kinds or stray:
        return None
    return False


def _card_hidden_when_empty(js: str, starts_hidden: bool) -> bool | None:
    """`_hides_when_empty`, with the card's own markup: a card hidden before any script runs stays
    hidden when nothing shows it, and a script that shows it shows it under a condition this does not
    read (A03: a card hidden by default that a script showed only when rows existed read "never
    hidden")."""
    said = _hides_when_empty(js)
    if said is not False or not starts_hidden:
        return said
    kinds, _ = _card_readings(js or "")
    return None if "show" in kinds else True


# What a call of the opener runs from, read from the brackets around it (A03, deep pass 2026-10-25:
# the in-card button's own wiring and a call inside `rows.forEach` counted as ways in).
_LOOPS = {"forEach", "map", "filter", "reduce", "reduceRight", "some", "every", "each", "flatMap", "find",
          "findIndex"}
_DEFERRED = {"then", "catch", "finally", "setTimeout", "setInterval", "requestAnimationFrame",
             "requestIdleCallback", "queueMicrotask", "ready", "onReady", "whenReady"}
_PAGE_EVENTS = {"DOMContentLoaded", "load", "pageshow", "hashchange", "popstate", "readystatechange"}


def _match_back(text: str, close: int) -> int:
    depth = 0
    for k in range(close, -1, -1):
        depth += {")": 1, "(": -1}.get(text[k], 0)
        if depth == 0:
            return k
    return 0


def _emptied(code: str) -> set[str]:
    """The names whose emptiness the script tests: `!pending.length`, `rows.length === 0`."""
    return (set(re.findall(r"!\s*(?:[\w$]+\.)*([\w$]+)\.length\b", code))
            | set(re.findall(r"([\w$]+)\.length\s*(?:===?\s*0|<\s*1|<=\s*0)\b", code)))


def _function_value(before: str) -> str | None:
    """What a function expression is the value of, from the text before it: an argument (the call
    it is passed to decides), a key named for the opener (the data-click dispatch table: the in-card
    button's own wiring), or anything else (assigned, `x.onclick = `: run from wherever, unread)."""
    b = re.sub(r"\basync\s*$", "", before.rstrip()).rstrip()
    if not b or b[-1] in "(,":
        return None
    key = re.search(r"['\"]?([\w$]+)['\"]?\s*:\s*$", b)
    if key:
        return "card" if key.group(1) == OPENER else "unknown"
    return "unknown"


def _bracket(code: str, at: int, call: int, emptied: set[str]) -> str | None:
    """What one open bracket around a call says: "rows" (a loop over the list whose emptiness hides
    the card: never runs with nothing pending), "card" (the in-card control's own wiring), "unknown",
    or None (runs whenever what encloses it runs)."""
    head = code[max(0, at - 300):at]
    if code[at] == "[":
        return None
    if code[at] == "(":
        callee = re.search(r"([\w$]+)\s*$", head)
        name = callee.group(1) if callee else None
        if name is None or name in _KEYWORDS:
            return None                         # grouping, an IIFE, a condition
        if name in _LOOPS:
            subject = re.search(r"([\w$]+)\s*\.\s*" + name + r"\s*$", head)
            return "rows" if subject and subject.group(1) in emptied else "unknown"
        if name == "addEventListener":
            event = re.match(r"\(\s*['\"](\w+)['\"]", code[at:at + 80])
            if event and event.group(1) in _PAGE_EVENTS:
                return None
            if re.search(r"data-click|dataset\.click|['\"]" + OPENER + r"['\"]", code[at:call]):
                return "card"
            return "unknown"                    # a handler on an element this does not place
        return None if name in _DEFERRED else "unknown"
    h = head.rstrip()
    if h.endswith("=>"):
        return _arrow_value(h)
    if h.endswith(")"):
        before = h[:_match_back(h, len(h) - 1)].rstrip()
        keyword = re.search(r"([\w$]+)\s*$", before)
        keyword = keyword.group(1) if keyword else ""
        if keyword in ("if", "switch", "catch", "with"):
            return None
        if keyword in ("for", "while"):
            subject = re.search(r"\b(?:of|in)\s+(?:[\w$]+\.)*([\w$]+)\s*\)\s*$|([\w$]+)\.length\b", h)
            name = subject and (subject.group(1) or subject.group(2))
            return "rows" if name in emptied else "unknown"
        fn = re.search(r"function\s*\*?\s*([\w$]*)\s*$", before)
        if fn:
            if fn.group(1):
                return "card" if fn.group(1) == OPENER else "unknown"   # named: called from wherever
            return _function_value(before[:fn.start()])
        return "card" if keyword == OPENER else "unknown"            # a method `name(...) {`
    if re.search(r"\bdo\s*$", h):
        return "unknown"
    return None                                 # else, try, finally, an object literal, a bare block


def _call_sites(js: str) -> list[tuple[str, str]]:
    """Every call of the opener, as (kind, the code before it): "way_in" when nothing around it
    keeps it from running with nothing pending; "rows" or "card" when it runs only from a pending row
    or from the card's own control; "unknown" when it runs from something this does not read.

    Not a call: its definition (`function f(`, a method `f() {`, `f = function`, `f: function`), a
    mention inside a string (the card's own markup), a comment (C01)."""
    sites = []
    code = _code(js)
    emptied = _emptied(code)
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
        kinds = [_bracket(code, at, m.start(), emptied) for at in _open_brackets(code, m.start())]
        prefix = code[:m.start()].rstrip()
        if prefix.endswith("=>"):                  # the body of a concise arrow
            kinds.append(_arrow_value(prefix))
        statement = code[max(code.rfind(";", 0, m.start()), code.rfind("{", 0, m.start()),
                              code.rfind("}", 0, m.start())) + 1:m.start()]
        if re.search(r"\bcase\s*['\"]" + OPENER + r"['\"]\s*:", statement):
            kinds.append("card")
        kind = next((k for k in ("rows", "card", "unknown") if k in kinds), "way_in")
        sites.append((kind, " ".join(code[max(0, m.start() - 70):m.end()].split())))
    return sites


def _arrow_value(prefix: str) -> str | None:
    """What an arrow function (`prefix` ends with its `=>`) is the value of."""
    params = prefix[:-2].rstrip()
    if params.endswith(")"):
        return _function_value(params[:_match_back(params, len(params) - 1)])
    bare = re.search(r"[\w$]+\s*$", params)
    return _function_value(params[:bare.start()] if bare else params)


def _calls(js: str) -> int:
    """Calls of the opener that are a way in: run with nothing pending, from outside the card."""
    return sum(1 for kind, _ in _call_sites(js) if kind == "way_in")


def _unplaced_calls(js: str) -> list[str]:
    """Calls of the opener run from something this does not read (a named function, a click handler
    on an element it does not place): neither a way in nor proof there is none."""
    return [where for kind, where in _call_sites(js) if kind == "unknown"]


def judge(outside: int, calls: int, hides: bool | None, unread: list[str], *,
          unplaced: list[str]) -> tuple[str | None, str]:
    """(verdict, why): "passed", "failed", or None for inconclusive.

    A control outside the card is in the page itself and needs no script. Every other verdict rests
    on what the scripts do not contain -- no call, no hide -- so it needs every script read: one that
    could not be read may hold either (C01, deep pass 2026-10-18). A call whose trigger was not read
    may be the way in, so it stops a failure; it cannot make a pass (A03, deep pass 2026-10-25)."""
    if outside:
        return "passed", "a control outside the pending card opens the form"
    if calls:
        return "passed", f"a script calls {OPENER} with nothing pending, from outside the card"
    if unread:
        return None, (f"{len(unread)} script(s) the page loads could not be read ({unread[:3]}); a call of "
                      f"{OPENER} or the card's hiding may be in them")
    if hides is None:
        return None, (f"a script hides #{CARD}, but not provably when the pending list is empty, or changes "
                      f"how it shows in a way this does not read; read the script before calling it either way")
    if hides:
        if unplaced:
            return None, (f"{len(unplaced)} call(s) of {OPENER} run from something this does not read "
                          f"({unplaced[:2]}); one may open the form with nothing pending")
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
    unplaced = _unplaced_calls(js)
    hides = _card_hidden_when_empty(js, page.card_starts_hidden)
    unread = sorted(set(scripts) - set(read))
    population = {"controls": len(page.openers), "controls_outside_card": outside,
                  "script_calls": script_calls, "script_calls_unplaced": unplaced[:5],
                  "card_starts_hidden": page.card_starts_hidden, "card_hidden_when_empty": hides,
                  "scripts_read": len(read), "scripts_unread": unread}
    verdict, why = judge(outside, script_calls, hides, unread, unplaced=unplaced)
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
