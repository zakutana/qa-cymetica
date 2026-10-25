"""/usage: dates and zone names follow the page's language, not the browser's (2026-10-25).

Seen on 2026-10-25 by the operator, in a signed-in session in a browser whose `navigator.language` is "cs",
on https://cymetica.com/usage with `<html lang="en">`, the footer language "English" and no stored language
choice: the tank caption read "refills so 17:00 SEČ" (Saturday, Central European Time; their own drawing
for the redesign says "refills Sat 4:00 PM UTC"), the daily columns "po 19." ... "so 24.", the day header
"PÁ 23. 10.", item times "23:12 SELČ" and the plan cards "this period ends 26. 10." / "until 26. 10." (day
before month, where English reads "Oct 26"). Everything else on the page was English. The old page did it
too (`Resets so 18:00` on 2026-10-22); the redesign made it more visible.

Why, read anonymously from what the page serves (the same for everyone): /static/js/usage-page.js formats
with `new Date(iso).toLocaleString([], opts)` (the `loc()` helper behind `hm`, `dayHm`, `dayName`, `mdShort`)
and `d.toLocaleDateString([], {...})` (the daily columns), with `timeZoneName: 'short'`. An empty locale list
means "the browser's language", not the page's. Node, with the same options and `cs-CZ`, answers
"so 17:00 SEČ", "19:12 SELČ", "26. 10." and "pá 23." -- the strings above -- and `en-US` the English ones.
Other calls in the same file already pass 'en-US'.

**The rule.** A date or time that /usage draws is formatted in the page's language: the formatting call
passes a locale (a literal English locale, the page's `<html lang>`, the site's i18n language, or a
variable or helper parameter that holds one), or goes through a helper that does. A call that formats a
date or time with no locale, `[]`, `undefined`, `void 0`, an options object in the locale's place, or
`navigator.language(s)` -- also behind `||` -- uses the browser's language, which is the defect.

VERDICTS. failed: such a call in a script that draws the page. passed: every date or time formatting call in
those scripts passes an explicit locale, whichever way the vendor does it. inconclusive: /usage or its
`#ug-root` script cannot be read; any same-origin script the page loads could not be read (it may rewrite
`Date.prototype`); something rewrites `Date.prototype.toLocale*String` or `Intl.DateTimeFormat` page-wide;
no date or time formatting call is left to read (hand-built dates, or the feature is gone: a pass here
would be a pass on nothing); a locale this check cannot resolve (`locales[x]`, a parameter nothing calls, a
variable that is the page's in one branch and the browser's in another) or a literal for another language.

Which calls count. `toLocaleDateString`, `toLocaleTimeString` and `Intl.DateTimeFormat` always;
`toLocaleString` when its receiver is a Date (`new Date(...)`, `Date.parse`, or a variable assigned one) or
its options hold a date key (weekday, day, month, year, hour, minute, timeZone, ...). A number's
`toLocaleString` is not a date.

Which scripts decide. The one that draws the page (it names `#ug-root`): usage-page.js. Two other scripts
the page loads format with the same empty list or none -- nexus-usage.js (`toLocaleDateString([], ...)`)
and nexus-subscription.js (`toLocaleDateString()` for "Access continues until") -- but we did not see either
draw on /usage (nexus-usage.js is the usage data layer usage-page.js calls; the subscription panel is the
header's, closed by default), so they are recorded in the population and do not decide the verdict.

NOT asserted: what the page shows a visitor whose browser is English; the numbers formatted with 'en-US';
the footer's language switch; whether the vendor wants the dates in the browser's language and the text in
English (a design choice they can make by changing the text, not the dates).
SAFE: anonymous GETs of the page and the scripts it loads.
"""

from __future__ import annotations

import re

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently
from tests.rest.test_usage_dynamic_card_takes_a_cookie_session import (
    MAX_SCRIPTS, _Page, _match, _mask, _skip_ws, _split_top, _statement_end, _text)

PAGE = "/usage"
ROOT = "ug-root"
OPEN, CLOSE = "([{", ")]}"

CALL = re.compile(r"(?:\?\.|\.)\s*(toLocaleString|toLocaleDateString|toLocaleTimeString)\s*\("
                  r"|(?<![\w$.])(?:new\s+)?Intl\s*\.\s*(DateTimeFormat)\s*\(")
# What a locale argument can say about the page's language / the browser's.
PAGE_LANG = re.compile(r"\.lang\b|getAttribute\(\s*['\"]lang['\"]\s*\)|\bEventTraderI18n\b|\bi18n\b|getLang|getLocale"
                       r"|currentLang|pageLang|uiLang|htmlLang", re.I)
BROWSER_LANG = re.compile(r"\bnavigator\s*\.\s*(?:languages?|userLanguage|browserLanguage|systemLanguage)\b")
DATE_KEYS = re.compile(r"\b(?:weekday|era|year|month|day|hour|minute|second|dateStyle|timeStyle|timeZone"
                       r"|timeZoneName|hour12|hourCycle)\s*:")
DATE_VALUE = re.compile(r"\bnew\s+Date\b|\bDate\s*\.\s*(?:parse|now|UTC)\b")
LITERAL = re.compile(r"""(['"`])([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*)\1""")
OVERRIDES = (re.compile(r"\bDate\s*\.\s*prototype\s*(?:\.\s*[\w$]+|\[[^\]]*\])\s*=(?!=)"),
             re.compile(r"\b(?:defineProperty|defineProperties|assign)\s*\(\s*Date\s*\.\s*prototype"),
             re.compile(r"\bIntl\s*\.\s*DateTimeFormat\s*=(?!=)"),
             re.compile(r"\b(?:defineProperty|defineProperties|assign)\s*\(\s*Intl\b"))
MAX_DEPTH = 5


# ------------------------------------------------------------------ reading JS without running it

def _split_args(code: str, m: str, a: int, b: int) -> list[tuple[str, str]]:
    """The arguments between a and b (the text inside a call's parentheses), cut at top-level commas:
    (code, mask) pieces, index for index."""
    cuts, depth, start = [], 0, a
    for k in range(a, b):
        if m[k] in OPEN:
            depth += 1
        elif m[k] in CLOSE:
            depth -= 1
        elif m[k] == "," and depth == 0:
            cuts.append((start, k))
            start = k + 1
    cuts.append((start, b))
    return [(code[s:e], m[s:e]) for s, e in cuts]


def _trim(code: str, m: str) -> tuple[str, str]:
    lead = len(code) - len(code.lstrip())
    code, m = code[lead:], m[lead:]
    return code.rstrip(), m[:len(code.rstrip())]


def _receiver_start(m: str, end: int) -> int:
    """Where the expression a `.method(` is called on begins, scanning back from the dot at `end`."""
    k = end
    while k > 0:
        ch = m[k - 1]
        if ch in CLOSE:
            depth, j = 0, k - 1
            while j >= 0:
                if m[j] in CLOSE:
                    depth += 1
                elif m[j] in OPEN:
                    depth -= 1
                if depth == 0:
                    break
                j -= 1
            k = max(j, 0)
        elif ch.isalnum() or ch in "_$.":
            k -= 1
        else:
            break
    return k


class Script:
    """One script, comments blanked (strings kept) and a fully masked twin, index for index."""

    def __init__(self, js: str) -> None:
        self.js = js
        self.code = _mask(js, comments_only=True)
        self.m = _mask(js)
        self.defs = self._definitions()

    # -- functions ---------------------------------------------------------------------------
    def _definitions(self) -> list[dict]:
        code, m, found, seen = self.code, self.m, [], set()

        def add(name: str, params_open: int, arrow: bool) -> None:
            params_end = _match(m, params_open)
            if params_end is None or params_open in seen:
                return
            after = _skip_ws(m, params_end + 1)
            if arrow:
                if not m.startswith("=>", after):
                    return
                after = _skip_ws(m, after + 2)
            if after < len(m) and m[after] == "{":
                end = _match(m, after)
                span = None if end is None else (after + 1, end)
            else:
                end = _statement_end(m, after)
                span = None if end is None else (after, end)
            if span is None:
                return
            seen.add(params_open)
            params = [re.split(r"[=\s]", p.strip())[0] for p in code[params_open + 1:params_end].split(",") if p.strip()]
            found.append({"name": name, "params": params, "a": span[0], "b": span[1]})

        for f in re.finditer(r"([\w$]+)\s*[:=]\s*(?:async\s+)?function\b\s*[\w$]*\s*\(", m):
            add(f.group(1), f.end() - 1, False)
        for f in re.finditer(r"(?:\bvar|\blet|\bconst)\s+([\w$]+)\s*=\s*(?:async\s*)?\(", m):
            add(f.group(1), f.end() - 1, True)
        for f in re.finditer(r"\bfunction\s*([\w$]*)\s*\(", m):
            add(f.group(1), f.end() - 1, False)
        return found

    def innermost(self, pos: int) -> dict | None:
        inside = [d for d in self.defs if d["a"] <= pos < d["b"]]
        return min(inside, key=lambda d: d["b"] - d["a"]) if inside else None

    # -- names -------------------------------------------------------------------------------
    def assignments(self, name: str) -> list[str]:
        """The right-hand side of every `name = ...` in the script (declarations and plain assignments)."""
        out = []
        for a in re.finditer(r"(?<![\w$.])" + re.escape(name) + r"\s*=(?![=>])", self.m):
            end = _statement_end(self.m, a.end())
            end = len(self.m) if end is None else end
            parts = _split_args(self.code, self.m, a.end(), end)
            out.append(_trim(*parts[0])[0].rstrip(";").strip())
        return out

    def call_sites(self, name: str) -> list[int]:
        """Index of the `(` of every call of `name(` that is not its definition."""
        sites = []
        for c in re.finditer(r"(?<![\w$.])" + re.escape(name) + r"\s*\(", self.m):
            if re.search(r"\bfunction\s*$", self.m[:c.start()]):
                continue
            sites.append(c.end() - 1)
        return sites

    # -- the locale argument -----------------------------------------------------------------
    def classify(self, code: str, m: str, depth: int = 0, at: int | None = None) -> tuple[str, str]:
        """("default" | "browser" | "explicit" | "unknown", why) for one locale argument."""
        code, m = _trim(code, m)
        if depth > MAX_DEPTH:
            return "unknown", "too many steps to follow"
        if not code or re.fullmatch(r"undefined|void\s*0", code):
            return "default", "no locale given" if not code else code
        for op in ("||", "??"):
            pieces = _split_top(code, m, op)
            if len(pieces) > 1:
                return self.classify(pieces[0][0], pieces[0][1], depth + 1, at)
        if code.startswith("[") and _match(m, 0) == len(m) - 1:
            parts = _split_args(code, m, 1, len(m) - 1)
            first = _trim(*parts[0])
            return ("default", "an empty list") if not first[0] else self.classify(first[0], first[1], depth + 1, at)
        if code.startswith("{"):
            return "default", "an options object where the locale goes"
        lit = LITERAL.fullmatch(code)
        if lit:
            tag = lit.group(2)
            if tag.lower().startswith("en"):
                return "explicit", f"the literal {tag!r}"
            return "unknown", f"the literal {tag!r}, another language"
        if re.fullmatch(r"[\w$]+", code):
            kind = self._identifier(code, depth, at)
            if kind is not None:
                return kind
        call = re.fullmatch(r"([\w$]+)\s*\(\s*\)", code)
        if call:
            for d in self.defs:
                if d["name"] == call.group(1):
                    body = self.code[d["a"]:d["b"]]
                    if PAGE_LANG.search(body) and not BROWSER_LANG.search(body):
                        return "explicit", f"{call.group(1)}() answers the page's language"
                    if BROWSER_LANG.search(body) and not PAGE_LANG.search(body):
                        return "browser", f"{call.group(1)}() answers navigator.language"
                    return "unknown", f"{call.group(1)}() could not be read to a language"
        if PAGE_LANG.search(code):
            return "explicit", f"the page's language ({code[:60]})"
        if BROWSER_LANG.search(code):
            return "browser", f"the browser's language ({code[:60]})"
        return "unknown", f"a locale this check cannot read: {code[:60]}"

    def _identifier(self, name: str, depth: int, at: int | None) -> tuple[str, str] | None:
        """A name: a parameter of the function around the call (judged at every caller), or a variable
        (judged by what it is assigned). None when the script defines neither."""
        fn = self.innermost(at) if at is not None else None
        if fn and name in fn["params"]:
            if not fn["name"]:
                return "unknown", f"{name} is a parameter of an anonymous function"
            index, kinds = fn["params"].index(name), []
            for site in self.call_sites(fn["name"]):
                close = _match(self.m, site)
                if close is None:
                    continue
                args = _split_args(self.code, self.m, site + 1, close)
                if index >= len(args) or (len(args) == 1 and not args[0][0].strip()):
                    kinds.append(("default", f"{fn['name']}() called without it"))
                else:
                    kinds.append(self.classify(args[index][0], args[index][1], depth + 1, site))
            if not kinds:
                return "unknown", f"{name} is a parameter of {fn['name']}(), which nothing calls"
            for kind in ("browser", "default"):
                hit = next((k for k in kinds if k[0] == kind), None)
                if hit:
                    return hit[0], f"a caller of {fn['name']}() passes {hit[1]}"
            if all(k[0] == "explicit" for k in kinds):
                return "explicit", f"every caller of {fn['name']}() passes one ({kinds[0][1]})"
            return "unknown", f"a caller of {fn['name']}() passes a locale this check cannot read"
        values = self.assignments(name)
        if not values:
            return None
        names = {self.classify(v, _mask(v), depth + 1)[0] for v in values}
        if "explicit" in names and names & {"browser", "default"}:
            return "unknown", f"{name} is the page's language in one place and the browser's in another"
        for kind in ("browser", "default"):
            if kind in names:
                return kind, f"{name} = {values[0][:60]}"
        if names == {"explicit"}:
            return "explicit", f"{name} = {values[0][:60]}"
        return "unknown", f"{name} = {values[0][:60]}"

    # -- the calls ---------------------------------------------------------------------------
    def is_date_receiver(self, start: int, end: int, options: str) -> bool:
        recv = self.m[start:end]
        if re.search(r"\bDate\b", recv) or DATE_KEYS.search(options):
            return True
        if re.fullmatch(r"[\w$]+", recv):
            return any(DATE_VALUE.search(v) for v in self.assignments(recv))
        return False

    def calls(self) -> list[dict]:
        out = []
        for c in CALL.finditer(self.m):
            method = c.group(1) or ("Intl." + c.group(2))
            open_at = c.end() - 1
            close = _match(self.m, open_at)
            line = self.js.count("\n", 0, c.start()) + 1
            around = sorted((d for d in self.defs if d["a"] <= c.start() < d["b"]), key=lambda d: d["b"] - d["a"])
            context = next((d["name"] for d in around if d["name"]), "(top level)")
            if close is None:
                out.append({"line": line, "call": method, "context": context, "locale": "", "kind": "unknown",
                            "why": "the call never closes"})
                continue
            args = _split_args(self.code, self.m, open_at + 1, close)
            if c.group(1) == "toLocaleString":
                if not self.is_date_receiver(_receiver_start(self.m, c.start()), c.start(),
                                             " ".join(a[0] for a in args[1:] or args)):
                    continue
            kind, why = self.classify(args[0][0], args[0][1], 0, c.start())
            out.append({"line": line, "call": method, "context": context,
                        "locale": " ".join(_trim(*args[0])[0].split())[:80], "kind": kind, "why": why})
        return out

    def overrides(self) -> bool:
        return any(p.search(self.m) for p in OVERRIDES)


def script_facts(js: str) -> dict:
    """What one script does with the browser's language: every date or time formatting call, how its locale
    reads, and whether the script rewrites the platform's formatters."""
    s = Script(js)
    return {"calls": s.calls(), "overrides": s.overrides(), "draws_page": ROOT in js}


def judge(drawn: list[dict], unread: list[str]) -> tuple[str | None, str]:
    """(verdict, why): "failed", "passed", or None for inconclusive. `drawn` is script_facts of every
    script that draws the page; the caller sets `overrides` on each if ANY script the page loads does."""
    if unread:
        return None, (f"{len(unread)} script(s) /usage loads could not be read ({unread[:3]}); one may "
                      f"rewrite Date.prototype")
    if not drawn:
        return None, f"no script /usage loads draws #{ROOT}"
    if any(f["overrides"] for f in drawn):
        return None, "a script the page loads rewrites Date.prototype.toLocale*String or Intl.DateTimeFormat"
    calls = [c for f in drawn for c in f["calls"]]
    if not calls:
        return None, "the script draws the page but holds no date or time formatting call to read"
    bad = [c for c in calls if c["kind"] in ("default", "browser")]
    if bad:
        c = bad[0]
        return "failed", (f"{len(bad)} of {len(calls)} date or time formatting calls use the browser's language: "
                          f"line {c['line']} {c['call']}({c['locale']}) in {c['context']}()")
    unknown = [c for c in calls if c["kind"] == "unknown"]
    if unknown:
        c = unknown[0]
        return None, (f"a date or time formatting call this check cannot decide: line {c['line']} "
                      f"{c['call']}({c['locale']}): {c['why']}")
    return "passed", f"all {len(calls)} date and time formatting calls pass an explicit locale"


# ------------------------------------------------------------------ the page

@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest")
def test_usage_dates_and_zone_names_follow_the_pages_language(rest_anon):
    """Every date or time /usage draws is formatted in the page's language, not the browser's."""
    try:
        page = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{PAGE} could not be read: {type(exc).__name__}")
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    html = _Page()
    html.feed(page.text)
    lang = re.search(r"<html\b[^>]*\blang=[\"']([^\"']+)", page.text)
    srcs = [s for s in html.srcs if s.startswith("/") and not s.startswith("//")][:MAX_SCRIPTS]
    bodies = {s: _text(rest_anon, s) for s in srcs}
    unread = sorted(s for s, b in bodies.items() if b is None)
    scripts = [(f"inline script {k + 1} of {len(html.inline)}", js) for k, js in enumerate(html.inline)]
    scripts += [(s, b) for s, b in bodies.items() if b is not None]
    facts = [(label, script_facts(js)) for label, js in scripts]
    rewritten = any(f["overrides"] for _, f in facts)
    drawn = [(label, {**f, "overrides": rewritten}) for label, f in facts if f["draws_page"]]
    verdict, why = judge([f for _, f in drawn], unread)

    calls = [{"script": label, **c} for label, f in drawn for c in f["calls"]]
    bad = [c for c in calls if c["kind"] in ("default", "browser")]
    also = {label: sum(1 for c in f["calls"] if c["kind"] in ("default", "browser"))
            for label, f in facts if not f["draws_page"] and any(c["kind"] in ("default", "browser") for c in f["calls"])}
    population = {
        "html_lang": lang.group(1) if lang else None,
        "scripts_that_draw_the_page": [label for label, _ in drawn],
        "date_calls": [{k: c[k] for k in ("script", "line", "call", "context", "locale", "kind", "why")}
                       for c in calls],
        "calls_in_the_browsers_language": len(bad),
        "other_scripts_with_calls_in_the_browsers_language": also,
        "scripts_read": len(scripts), "scripts_unread": unread,
        "page_date": page.headers.get("date"),
    }
    if verdict is None:
        raise Inconclusive(why)
    failed = verdict == "failed"
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{why}. On {PAGE} (<html lang={population['html_lang']!r}>) the script that draws the page "
                f"formats dates with an empty locale list or none, which means the browser's language, so a "
                f"visitor whose browser is not English reads weekday names, zone names and day-month order in "
                f"that language on an English page"
                if failed else why),
        left={"date_calls_in_the_browsers_language": len(bad)},
        right={"date_calls_in_the_browsers_language": 0},
        population=population,
        sources={"page": f"{PAGE} (<html lang> and the script tags)", "scripts": srcs}))
