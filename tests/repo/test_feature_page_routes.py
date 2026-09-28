"""The routes a feature page of theirs names are held against openapi-public.json.

NEXT.md, agreed 2026-09-23 with the operator's word of 2026-09-24 ("vydávají
stránky a do dokumentace je nedávají"): a check that every `/api/v1/...` the
creator page, the head-to-head page and the page that names `run-backtest`
call is a path of `/openapi-public.json`. The check is
tests/rest/test_feature_pages_name_documented_routes.py; this holds its reader
and its verdicts on pages written here, in the shapes the three live pages
use (read 2026-09-28): inline `fetch()` with a concatenated id, a
`<span class="method">` beside a `<span class="endpoint-path">`, a `<code>`
around a path, a `curl` with the host in front, and the push plumbing every
page carries, the home page included.

The trap it is written against (memory `extract-from-text-anchor-on-markup`):
a tag next to a path must never become part of it -- the noun in a failure
line goes to the vendor verbatim.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = "/openapi-public.json"

SPEC = {"paths": {
    "/api/v1/head-to-head": {"post": {}},
    "/api/v1/head-to-head/sides": {"get": {}},
    "/api/v1/creator/links": {"post": {}},
    "/api/v1/creator/{username}/links": {"get": {}},
    "/api/v1/creator/reddit-leads/{lead_id}/reply": {"post": {}},
    "/api/v1/creator/priority-tweet/{tweet_id}/posted": {"post": {}},
    "/api/v1/backtest-labs/run": {"post": {}},
    "/api/v1/backtest/leaderboard": {"get": {}},
}}

CHROME = ("<script>fetch('/api/v1/push/vapid-key').then(function (r) {"
          " return r.json(); }); var SUB = '/api/v1/push/subscribe';</script>")
HOME = ('<html><head><script src="/static/js/auth.js?v=20260921-1"></script>'
        + CHROME + '</head><body><a href="/h2h">H2H</a></body></html>')

H2H = ('<html><head><script src="/static/js/auth.js?v=20260921-1"></script>'
       + CHROME + """</head><body><script>
  fetch('/api/v1/head-to-head/sides', { credentials: 'same-origin' }).then(function (r) {
    if (r.status === 401 || r.status === 403) { show(); }
  });
  fetch('/api/v1/head-to-head', { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
</script></body></html>""")

CREATOR = ('<html><head><script src="/static/js/bb_community_kit.js?v=2"></script>'
           + CHROME + """</head><body><script>
function leadApi(card) { return card.getAttribute('data-api') || '/api/v1/creator/reddit-leads/'; }
fetch('/api/v1/creator/priority-tweet/' + id + '/posted', { method: 'POST', credentials: 'same-origin' });
fetch('/api/v1/creator/links/' + current.slug, { method: 'PATCH', credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_url: url }) });
fetch('/api/v1/creator/links', { method: 'POST', credentials: 'same-origin' });
</script></body></html>""")
KIT = "fetch(`/api/v1/creator/${username}/links`).then(function (r) { return r.json(); });"

BACKTEST_API = ('<html><head>' + CHROME + """</head><body>
<td><code>GET /api/v1/backtest/leaderboard</code>, <code>/equity</code></td>
<div class="endpoint-header">
  <span class="method post">POST</span>
  <span class="endpoint-path">/api/v1/backtest/bots/{slug}/run-backtest</span>
  <span class="endpoint-desc">Run backtest</span>
</div>
<pre><code># Authenticated request
curl -H "Authorization: Bearer $EVENTTRADER_API_KEY" \\
  https://cymetica.com/api/v1/backtest/bots/your-bot-slug/run-backtest</code></pre>
<p>Strategy labs live under <code>/api/v1/backtest-labs/*</code>; the board is
/api/v1/backtest/leaderboard?period=30&amp;limit=5.</p>
</body></html>""")


def _check():
    spec = importlib.util.spec_from_file_location(
        "feature_pages_under_test",
        REPO / "tests" / "rest" / "test_feature_pages_name_documented_routes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _site(spec=SPEC, **over):
    """What each path answers: (status, text). A value of None times out."""
    site = {SPEC_PATH: (200, json.dumps(spec)), "/": (200, HOME),
            "/h2h": (200, H2H), "/expire76": (200, CREATOR),
            "/static/js/bb_community_kit.js": (200, KIT),
            "/backtest/api": (200, BACKTEST_API)}
    site.update(over)
    return site


def _client(site, seen=None):
    """The guarded client over a transport that answers locally: a read that
    became a write is refused by the guard and reaches no one."""
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    def answer(request):
        if seen is not None:
            seen.append((request.method, request.url.path))
        said = site.get(request.url.path, (404, "not found"))
        if said is None:
            raise httpx.ReadTimeout("timed out", request=request)
        status, text = said
        return httpx.Response(status, text=text)

    return build_client(identities()["anon"], EndpointRegistry.load(),
                        base_url="https://cymetica.com",
                        inner=httpx.MockTransport(answer))


def _verdict(site) -> tuple[str, str]:
    check = _check()
    try:
        check.test_every_route_a_feature_page_names_is_in_the_public_openapi(
            _client(site))
    except AssertionError as failed:
        return "failed", str(failed)
    except Inconclusive as unsure:
        return "inconclusive", str(unsure)
    return "passed", ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_route_is_read_from_the_text_and_no_tag_becomes_part_of_it():
    """Every shape the live pages use, and what each is read as. A `<code>`,
    a `<span>` or a `</code>` beside a path is a boundary, never a character
    of it; a query string is not part of a route; an id concatenated in is a
    slot; a literal ending in `/` with nothing after it, or `/*`, names a
    family of routes rather than one."""
    check = _check()
    named = check.routes_named(BACKTEST_API)
    assert set(named) == {"/api/v1/backtest/leaderboard",
                          "/api/v1/backtest/bots/{slug}/run-backtest",
                          "/api/v1/backtest/bots/your-bot-slug/run-backtest",
                          "/api/v1/backtest-labs/", "/api/v1/push/vapid-key",
                          "/api/v1/push/subscribe"}, named
    for path in named:
        assert not set(path) & set("<>\"'` ?&#"), f"markup inside a route: {path!r}"
    # The method stated beside it, across the tags between them; none where
    # the page states none -- a bare fetch is not read as a GET.
    assert named["/api/v1/backtest/bots/{slug}/run-backtest"] == {"POST"}
    assert named["/api/v1/backtest/leaderboard"] == {"GET"}
    assert named["/api/v1/push/vapid-key"] == set()

    creator = check.routes_named(CREATOR)
    assert creator == {"/api/v1/creator/reddit-leads/": set(),
                       "/api/v1/creator/priority-tweet/{id}/posted": {"POST"},
                       "/api/v1/creator/links/{slug}": {"PATCH"},
                       "/api/v1/creator/links": {"POST"},
                       "/api/v1/push/vapid-key": set(),
                       "/api/v1/push/subscribe": set()}, creator
    assert set(check.routes_named(KIT)) == {"/api/v1/creator/{username}/links"}
    assert set(check.routes_named("see &lt;code&gt;/api/v1/a/&lt;id&gt;/b&lt;/code&gt;")) \
        == {"/api/v1/a/{id}/b"}, "an escaped placeholder is a slot, escaped markup is not"
    assert check.routes_named("") == {}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_route_the_spec_lacks_fails_by_its_own_name():
    """Two routes these pages name and the spec does not publish: PATCH on a
    single creator link (`/creator/links` is published; `/creator/links/{x}`
    is not, and `/creator/{username}/links` is another route), and
    run-backtest -- written once as a template and once with an example slug,
    which is the same route and said once. The push plumbing every page
    carries, the home page included, is not the feature's. The home page's
    own script and the sitewide one on each page are not fetched."""
    seen = []
    verdict, reason = _verdict_seen(_site(), seen)
    assert verdict == "failed", reason
    assert "PATCH /api/v1/creator/links/{slug}" in reason, reason
    assert "POST /api/v1/backtest/bots/{slug}/run-backtest" in reason, reason
    for noise in ("your-bot-slug", "push", "head-to-head", "reddit-leads",
                  "priority-tweet", "backtest-labs", "leaderboard", "<", "code"):
        assert noise not in reason.split("\n")[0], (noise, reason)
    assert ("GET", "/static/js/bb_community_kit.js") in seen
    assert not [p for m, p in seen if p == "/static/js/auth.js"], seen
    assert {m for m, _ in seen} == {"GET"}, seen


def _verdict_seen(site, seen):
    check = _check()
    try:
        check.test_every_route_a_feature_page_names_is_in_the_public_openapi(
            _client(site, seen))
    except AssertionError as failed:
        return "failed", str(failed)
    except Inconclusive as unsure:
        return "inconclusive", str(unsure)
    return "passed", ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_route_published_passes_and_a_stated_method_is_held_too():
    whole = {"paths": {**SPEC["paths"],
                       "/api/v1/creator/links/{slug}": {"patch": {}},
                       "/api/v1/backtest/bots/{slug}/run-backtest": {"post": {}}}}
    assert _verdict(_site(whole)) == ("passed", "")

    # The path is published, the method the page states is not.
    no_patch = {"paths": {**whole["paths"],
                          "/api/v1/creator/links/{slug}": {"delete": {}}}}
    verdict, reason = _verdict(_site(no_patch))
    assert verdict == "failed" and "PATCH /api/v1/creator/links/{slug}" in reason, reason
    assert "run-backtest" not in reason.split("\n")[0], reason


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_or_empty_read_is_inconclusive_never_a_defect():
    """Rule 8. Their document unread or not JSON, the home page unread (the
    chrome cannot be told from the feature), a page that did not answer, a
    page-specific script that timed out, a page that names no route at all
    -- none is a pass and none is a gap. A gap on a page that WAS read still
    fails when another page was not: a fail needs only the reads it stands on."""
    whole = {"paths": {**SPEC["paths"],
                       "/api/v1/creator/links/{slug}": {"patch": {}},
                       "/api/v1/backtest/bots/{slug}/run-backtest": {"post": {}}}}
    cases = {
        "spec 503": _site(whole, **{SPEC_PATH: (503, "busy")}),
        "spec not json": _site(whole, **{SPEC_PATH: (200, "<html>oops")}),
        "spec timed out": _site(whole, **{SPEC_PATH: None}),
        "spec no paths": _site({"paths": {}}),
        "home 500": _site(whole, **{"/": (500, "boom")}),
        "page 404": _site(whole, **{"/h2h": (404, "gone")}),
        "script timed out": _site(whole, **{"/static/js/bb_community_kit.js": None}),
        "page names nothing": _site(whole, **{"/backtest/api": (200, HOME)}),
    }
    for name, site in cases.items():
        verdict, reason = _verdict(site)
        assert verdict == "inconclusive", (name, verdict, reason)

    verdict, reason = _verdict(_site(SPEC, **{"/h2h": (502, "bad gateway")}))
    assert verdict == "failed" and "run-backtest" in reason, reason
