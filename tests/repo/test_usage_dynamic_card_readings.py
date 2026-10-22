"""The readings behind the "/usage Dynamic plan card takes a cookie session as signed in" check.

Written before the check (2026-10-22), from the card's script as /usage served it that day: `load()`
returns "Log in to see your forecast and switch." whenever `tok()` -- `window.getAuthToken()`, a read of
stored bearer tokens -- is empty, before /api/v1/nexus/dynamic is ever asked, and auth.js clears those
stored tokens whenever the et_session cookie is present. So a signed-in visitor is told to log in.

Each reading below is a way the vendor could fix it (they must pass, whichever they pick), a way the same
defect could be rebuilt (it must still fail), or a shape the check cannot decide (inconclusive, never a
pass). The memory "a check encodes the fix its author imagined" is why the fixes come first.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_usage_dynamic_card_takes_a_cookie_session import card_facts, judge

# window.getAuthToken as the page defines it: stored bearer tokens, nothing else.
HELPERS = """
window.getAuthToken = function() {
    return localStorage.getItem('accessToken')
        || localStorage.getItem('access_token')
        || sessionStorage.getItem('auth_token');
};
window.hasSession = window.hasSession || function() {
    try { if (window.getAuthToken()) return true; } catch (e) {}
    return window.hasSessionCookie();
};
"""

HEAD = """(function () {
  'use strict';
  var API = '/api/v1/nexus/dynamic';
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return c; }); }
  function tok() { try { return typeof window.getAuthToken === 'function' ? window.getAuthToken() : null; } catch (e) { return null; } }
  function call(method, path, body) {
    var h = {}; var t = tok(); if (t) h['Authorization'] = 'Bearer ' + t;
    return fetch(API + path, { method: method, credentials: 'same-origin', headers: h })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, status: r.status, j: j }; }); });
  }
  function render(d) { var body = document.getElementById('nxd-body'); body.innerHTML = esc(d.forecast && d.forecast.with_fee_usd); }
"""
TAIL = """
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { load(); }); else load();
})();
"""


def _card(load_body: str, head: str = HEAD) -> str:
    return head + "  function load(msg) {\n    var body = document.getElementById('nxd-body'); if (!body) return;\n" + \
        load_body + "\n  }" + TAIL


LIVE_LOAD = """
    if (!tok()) {
      fetch('/api/v1/nexus/plans', { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) {
        var plan = j.dynamic || {};
        body.innerHTML = (plan.available ? 'terms' : '<p class="nxd-note">The Dynamic plan is not open yet.</p>') +
          '<p class="nxd-note">Log in to see your forecast and switch.</p>';
      }).catch(function () { body.innerHTML = ''; });
      return;
    }
    call('GET', '').then(function (r) {
      if (!r.ok) { body.innerHTML = '<p class="nxd-note">' + esc(r.j.detail) + '</p>'; return; }
      render(r.j);
    });"""
LIVE = _card(LIVE_LOAD)


def _verdict(script: str, helpers: str = HELPERS, unread=()) -> str | None:
    return judge([card_facts(script, script + helpers)], list(unread))[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_card_as_served_on_2026_10_22_fails():
    assert _verdict(LIVE) == "failed"
    facts = card_facts(LIVE, LIVE + HELPERS)
    assert facts["failing"] and "!tok()" in facts["failing"][0]["condition"].replace(" ", "")
    assert "Log in to see your forecast" in facts["failing"][0]["branch"], "the branch it judged is the one shown"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_defect_rebuilt_in_other_shapes_still_fails():
    minified = ('!function(){"use strict";var a="/api/v1/nexus/dynamic";function c(){try{return"function"==typeof '
                'window.getAuthToken?window.getAuthToken():null}catch(n){return null}}function f(e,t){var o={},r=c();'
                'return r&&(o.Authorization="Bearer "+r),fetch(a+t,{method:e,credentials:"same-origin",headers:o})}'
                'function l(){var e=document.getElementById("nxd-body");if(e){if(!c())return void fetch("/api/v1/nexus/plans",'
                '{credentials:"same-origin"}).then(function(n){return n.json()}).then(function(n){e.innerHTML='
                '"<p>Log in to see your forecast and switch.</p>"});f("GET","").then(function(n){e.innerHTML=n})}}l()}();')
    assert _verdict(minified) == "failed", "minified, braceless `if(!c())return void ...`"
    positive = _card("""
    if (tok()) { call('GET', '').then(function (r) { render(r.j); }); }
    else { body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; }""")
    assert _verdict(positive) == "failed", "the server asked only when a token exists, signed out otherwise"
    no_else = _card("""
    if (tok()) { call('GET', '').then(function (r) { render(r.j); }); }""")
    assert _verdict(no_else) == "failed", "no token: the card is never asked for and stays 'Loading'"
    variable = _card("""
    var t = tok();
    if (!t) { body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; return; }
    call('GET', '').then(function (r) { render(r.j); });""")
    assert _verdict(variable) == "failed", "the token read into a variable first"
    direct = _card("""
    if (!window.getAuthToken()) { body.innerHTML = '<p>Sign in to switch.</p>'; return; }
    call('GET', '').then(function (r) { render(r.j); });""")
    assert _verdict(direct) == "failed", "getAuthToken called directly, other words"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_fix_the_vendor_might_choose_passes():
    session_too = _card("""
    if (!tok() && !(window.hasSession && window.hasSession())) {
      body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; return;
    }
    call('GET', '').then(function (r) { render(r.j); });""")
    assert _verdict(session_too) == "passed", "the gate also asks the page's own session helper"
    ask_first = _card("""
    call('GET', '').then(function (r) {
      if (r.status === 401) { body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; return; }
      render(r.j);
    });""")
    assert _verdict(ask_first) == "passed", "no gate: the server's 401 decides, as nexus-usage.js does"
    no_message = _card("""
    call('GET', '').then(function (r) {
      if (!r.ok) { body.innerHTML = esc(r.j.detail); return; }
      render(r.j);
    });""")
    assert _verdict(no_message) == "passed", "no gate and no sign-in text at all"
    inside = _card("""
    if (!tok()) {
      if (window.hasSessionCookie()) { call('GET', '').then(function (r) { render(r.j); }); return; }
      body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; return;
    }
    call('GET', '').then(function (r) { render(r.j); });""")
    assert _verdict(inside) == "passed", "the token gate's own branch tests the session"
    asks_anyway = _card("""
    if (!tok()) {
      call('GET', '').then(function (r) {
        if (!r.ok) { body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; return; }
        render(r.j);
      });
      return;
    }
    call('GET', '').then(function (r) { render(r.j); });""")
    assert _verdict(asks_anyway) == "passed", "the token gate's branch asks the server anyway"
    harmless = _card("""
    if (!tok()) console.debug('cookie session');
    call('GET', '').then(function (r) { render(r.j); });""")
    assert _verdict(harmless) == "passed", "a token test that decides nothing"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_helper_that_learns_the_session_passes_unless_it_answers_empty():
    head_cookie = HEAD.replace(
        "function tok() { try { return typeof window.getAuthToken === 'function' ? window.getAuthToken() : null; } catch (e) { return null; } }",
        "function tok() { var t = window.getAuthToken(); return t || (window.hasSessionCookie() ? 'cookie' : null); }")
    assert head_cookie != HEAD
    assert _verdict(_card(LIVE_LOAD, head=head_cookie)) == "passed", "the card's own helper falls back to the cookie"
    head_empty = HEAD.replace(
        "function tok() { try { return typeof window.getAuthToken === 'function' ? window.getAuthToken() : null; } catch (e) { return null; } }",
        "function tok() { return window.getAuthToken() || (window.hasSession() ? '' : null); }")
    assert _verdict(_card("""
    if (!tok()) { body.innerHTML = '<p>Log in to see your forecast and switch.</p>'; return; }
    call('GET', '').then(function (r) { render(r.j); });""", head=head_empty)) is None, (
        "'' for a session is still falsy under `!`: neither a pass nor the defect")
    page_cookie = HELPERS.replace(
        "|| sessionStorage.getItem('auth_token');",
        "|| sessionStorage.getItem('auth_token') || (window.hasSessionCookie() ? 'cookie' : null);")
    assert page_cookie != HELPERS
    assert _verdict(LIVE, helpers=page_cookie) == "passed", "the page's getAuthToken falls back to the cookie"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_cannot_be_read_is_never_a_verdict():
    assert judge([], [])[0] is None, "no script draws the card"
    assert _verdict(LIVE, unread=["/static/js/x.js"]) is None, "an unread script may redefine the helper"
    assert _verdict(_card("""
    call('GET', '').then(function (r) { render(r.j); });""").replace("/api/v1/nexus/dynamic", "/api/v1/other")) is None, (
        "a script that never names the dynamic endpoint is not the card's")
    ternary = _card("""
    tok() ? call('GET', '').then(function (r) { render(r.j); })
          : (body.innerHTML = '<p>Log in to see your forecast and switch.</p>');""")
    assert _verdict(ternary) is None, "it says log in, and nothing this check reads decides when"
    cut = LIVE[:LIVE.index("      return;\n    }") + len("      return;")]
    assert _verdict(cut) is None, "a script cut off inside the gate: its branch never closes"
