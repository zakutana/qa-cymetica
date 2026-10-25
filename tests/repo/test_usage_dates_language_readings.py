"""The readings behind the "/usage dates and zone names follow the page's language" check.

Written before the check (2026-10-25), from usage-page.js as /usage served it that day: its date helpers
format with `new Date(iso).toLocaleString([], opts)` and `d.toLocaleDateString([], {...})`. An empty locale
list means "the browser's language", not the page's (`<html lang="en">`), so a visitor whose browser is set
to Czech reads "so 17:00 SEČ", "po 19." and "26. 10." on an English page, while the same code in an
English browser draws "Sat 5:00 PM GMT+1".

Each reading below is a way the vendor could fix it (they must pass, whichever they pick), a way the same
defect could be rebuilt (it must still fail), or a shape the check cannot decide (inconclusive, never a
pass). The memory "a check encodes the fix its author imagined" is why the fixes come first.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_usage_dates_follow_the_pages_language import judge, script_facts

# The helpers and the two inline calls as usage-page.js?v=20261025-2 has them.
LIVE = """
    function usd0(v) { return '$' + Math.round(num(v)).toLocaleString('en-US'); }
    function loc(opts, iso) { try { return new Date(iso).toLocaleString([], opts); } catch (e) { return ''; } }
    function hm(iso) { return loc({ hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }, iso); }
    function dayHm(iso) { return loc({ weekday: 'short', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }, iso); }
    function mdShort(iso) { return loc({ month: 'short', day: 'numeric' }, iso); }
    function daysHtml(snap) {
        return snap.history.map(function (h, i) {
            var d = new Date(h.day + 'T12:00:00Z');
            var lab = d.toLocaleDateString([], { weekday: 'short', day: 'numeric', timeZone: 'UTC' });
            return lab;
        });
    }
"""


def _verdict(js: str, unread=(), overrides=False) -> str | None:
    facts = script_facts(js)
    if overrides:
        facts = {**facts, "overrides": True}
    return judge([facts], list(unread))[0]


def _one(call: str) -> str | None:
    """The verdict on a script that holds exactly one date call, written as `call`."""
    return _verdict("function f(iso, locale, opts) {\n  var d = new Date(iso);\n  return " + call + ";\n}\n")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_script_as_served_on_2026_10_25_fails():
    assert _verdict(LIVE) == "failed"
    facts = script_facts(LIVE)
    bad = [c for c in facts["calls"] if c["kind"] in ("default", "browser")]
    assert len(bad) == 2, "the loc() helper and the day-column call; the number format is not a date"
    assert {c["call"] for c in bad} == {"toLocaleString", "toLocaleDateString"}
    assert not any("usd0" in c["context"] for c in facts["calls"]), "Math.round(...).toLocaleString('en-US') is a number"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_defect_rebuilt_in_other_shapes_still_fails():
    assert _one("d.toLocaleString(undefined, opts)") == "failed", "undefined is the browser's language"
    assert _one("d.toLocaleString(void 0, opts)") == "failed"
    assert _one("d.toLocaleString({ hour: 'numeric' })") == "failed", "a missing locale: the options object is the first argument"
    assert _one("d.toLocaleDateString()") == "failed", "no argument at all (the bare call nexus-subscription.js makes)"
    assert _one("d.toLocaleTimeString([], opts)") == "failed"
    assert _one("d.toLocaleString(navigator.language, opts)") == "failed"
    assert _one("d.toLocaleString([navigator.language], opts)") == "failed"
    assert _one("d.toLocaleString(navigator.languages[0], opts)") == "failed"
    assert _one("d.toLocaleString(navigator.language || 'en-US', opts)") == "failed", "still the browser's, whenever it is set"
    assert _one("new Intl.DateTimeFormat([], opts).format(d)") == "failed"
    assert _one("Intl.DateTimeFormat(undefined, opts).format(d)") == "failed"
    assert _one("d?.toLocaleString([], opts)") == "failed", "optional chaining"
    through = ("var L = navigator.language;\nfunction f(iso, opts) { return new Date(iso).toLocaleString(L, opts); }")
    assert _verdict(through) == "failed", "the browser language passed through a variable"
    minified = 'function a(e,t){try{return new Date(e).toLocaleString([],t)}catch(n){return""}}'
    assert _verdict(minified) == "failed", "minified one-liner"
    options_only = "function f(iso) { return new Date(iso).toLocaleString([], {hour:'numeric'}); }"
    assert _verdict(options_only) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_fix_the_vendor_might_choose_passes():
    assert _one("d.toLocaleString('en-US', opts)") == "passed"
    assert _one("d.toLocaleString('en', opts)") == "passed"
    assert _one("d.toLocaleString(['en-US'], opts)") == "passed", "a one-item list"
    assert _one("d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })") == "passed"
    assert _one("d.toLocaleString(document.documentElement.lang, opts)") == "passed", "the page's own lang"
    assert _one("d.toLocaleString(document.documentElement.lang || 'en-US', opts)") == "passed"
    assert _one("d.toLocaleString(window.EventTraderI18n.getLanguage(), opts)") == "passed", "the site's i18n language"
    assert _one("d.toLocaleString(EventTraderI18n.lang, opts)") == "passed"
    assert _one("d.toLocaleString(document.documentElement.getAttribute('lang'), opts)") == "passed"
    assert _one("new Intl.DateTimeFormat('en-US', opts).format(d)") == "passed"
    assert _one("Intl.DateTimeFormat(document.documentElement.lang, opts).format(d)") == "passed"
    const = "var LOCALE = 'en-US';\nfunction f(iso, opts) { return new Date(iso).toLocaleString(LOCALE, opts); }"
    assert _verdict(const) == "passed", "a constant"
    page = ("var LANG = document.documentElement.lang || 'en';\n"
            "function f(iso, opts) { return new Date(iso).toLocaleString(LANG, opts); }")
    assert _verdict(page) == "passed", "a variable holding the page's language"
    function = ("function pageLang() { return document.documentElement.lang || 'en'; }\n"
                "function f(iso, opts) { return new Date(iso).toLocaleString(pageLang(), opts); }")
    assert _verdict(function) == "passed", "a function that returns it"
    helper = ("function loc(locale, opts, iso) { return new Date(iso).toLocaleString(locale, opts); }\n"
              "function hm(iso) { return loc('en-US', { hour: 'numeric' }, iso); }\n"
              "function md(iso) { return loc(document.documentElement.lang, { day: 'numeric' }, iso); }")
    assert _verdict(helper) == "passed", "the locale is a parameter, every caller of the helper passes one"
    number_only = "function usd0(v) { return '$' + Math.round(v).toLocaleString(); }\nvar d = new Date(); d.toLocaleDateString('en-US');"
    assert _verdict(number_only) == "passed", "a bare number format is not a date"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_helper_whose_caller_forgets_the_locale_still_fails():
    helper = ("function loc(locale, opts, iso) { return new Date(iso).toLocaleString(locale, opts); }\n"
              "function hm(iso) { return loc('en-US', { hour: 'numeric' }, iso); }\n"
              "function md(iso) { return loc(undefined, { day: 'numeric' }, iso); }")
    assert _verdict(helper) == "failed", "one caller of the helper passes undefined"
    short = ("function loc(locale, opts, iso) { return new Date(iso).toLocaleString(locale, opts); }\n"
             "function md(iso) { return loc(); }")
    assert _verdict(short) == "failed", "a caller that passes nothing"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_number_format_is_not_a_date_but_a_date_option_makes_a_string_one():
    assert _verdict("var s = Math.round(x).toLocaleString();") is None, "a number alone: no date call is left"
    assert _verdict("var s = (12345.6).toLocaleString([]);") is None
    assert _verdict("var s = when.toLocaleString([], { weekday: 'short', hour: 'numeric' });") == "failed", \
        "date keys in the options make it a date even when the receiver is unknown"
    facts = script_facts("var s = Math.round(x).toLocaleString('en-US');\nvar t = new Date(x).toLocaleString('en-US');")
    assert len(facts["calls"]) == 1 and facts["calls"][0]["kind"] == "explicit"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_text_that_only_looks_like_a_call_does_not_count():
    commented = ("// d.toLocaleString([], opts) was the old one\n"
                 "/* new Date(x).toLocaleDateString() */\n"
                 "function f(iso, opts) { return new Date(iso).toLocaleString('en-US', opts); }")
    assert _verdict(commented) == "passed", "comments"
    in_string = ("var note = 'call d.toLocaleString([]) in the browser';\n"
                 "function f(iso, opts) { return new Date(iso).toLocaleString('en-US', opts); }")
    assert _verdict(in_string) == "passed", "a string"
    assert _verdict("var x = 1;") is None, "no formatting call at all"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_shapes_the_check_cannot_decide_are_inconclusive_never_a_pass():
    assert _one("d.toLocaleString(locales[x], opts)") is None, "a locale the script computes some other way"
    assert _one("d.toLocaleString('cs-CZ', opts)") is None, "pinned to another language: a different defect"
    assert _one("d.toLocaleString(lang, opts)") is None, "an identifier nothing in the script defines"
    param_no_callers = "function f(iso, locale, opts) { return new Date(iso).toLocaleString(locale, opts); }"
    assert _verdict(param_no_callers) is None, "a parameter nothing calls"
    assert _verdict(LIVE, unread=["/static/js/auth.js"]) is None, "a script the page loads could not be read"
    assert _verdict("function f(iso) { return new Date(iso).toLocaleString('en-US'); }", overrides=True) is None, \
        "something rewrites Date.prototype.toLocale*String page-wide"
    assert judge([], [])[0] is None, "no script draws the page"
    fixed_mixed = ("var L = 'en-US'; if (x) { L = navigator.language; }\n"
                   "function f(iso, opts) { return new Date(iso).toLocaleString(L, opts); }")
    assert _verdict(fixed_mixed) is None, "a variable that is the page's in one branch and the browser's in another"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_prototype_override_is_seen_in_any_script():
    assert script_facts("Date.prototype.toLocaleString = function () { return 'x'; };")["overrides"] is True
    assert script_facts("Object.defineProperty(Date.prototype, 'toLocaleDateString', { value: f });")["overrides"] is True
    assert script_facts("var o = Date.prototype.toLocaleString;")["overrides"] is False, "a read is not an override"
    assert script_facts(LIVE)["overrides"] is False
