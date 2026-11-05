"""The Promo Market v4 mock: two windows (the owner who posts a brief, the promoter who offers on it) over ONE sample.

The mock holds its own state so the operator can click the whole workflow from both sides; none of it may ever reach
cymetica.com. Every write is local, every other write is refused. A brief is a budget the owner hands out in offers
(a promoter asks, the owner sets the amount, the promoter accepts, the rest stays in the brief); it has no end date
and is paid for a post that stayed up 3 days and nothing else: no visitor, click or new-user number exists in
anything it answers.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from qa.paths import REPO_ROOT

LIVE = REPO_ROOT / "outbox" / "promo-market-v4" / "live"
BRIEF = {"name": "Gem Screener", "path": "/gem-screener", "budget": 50000, "currency": "ET10", "say_line": "Find the gem before CT does."}
POST = "https://x.com/gemhunter_demo/status/1"


def _load(name):
    for k in ("patch", "sample", "serve"):
        sys.modules.pop(k, None)
    sys.path.insert(0, str(LIVE))
    try:
        spec = importlib.util.spec_from_file_location(f"pm4_{name}", LIVE / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(LIVE))


@pytest.fixture
def mock(monkeypatch):
    serve = _load("serve")

    def no_upstream(path):
        raise AssertionError(f"the mock reached for cymetica.com: {path}")

    monkeypatch.setattr(serve, "fetch_upstream", no_upstream)
    serve.sample.MARKET.reset()
    servers, running = {}, []
    for role in ("owner", "promoter"):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        srv.role = role
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        servers[role] = f"http://127.0.0.1:{srv.server_address[1]}"
        running.append(srv)
    yield servers
    for srv in running:
        srv.shutdown()
        srv.server_close()


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw.decode("utf-8", "replace")}


def post_brief(m, **over):
    status, out = call(m["owner"], "POST", "/api/v1/promo/briefs", {**BRIEF, **over})
    assert status == 200, out
    return out["brief"]["id"]


def offer(m, bid, ask, handle="gemhunter_demo"):
    assert call(m["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offer/check", {"handle": handle})[1]["ok"]
    return call(m["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offer/take", {"ask": ask})


def decide(m, bid, oid, decision="approve", amount=None):
    return call(m["owner"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{oid}", {"decision": decision, "amount": amount})


def results(m, bid):
    return call(m["owner"], "GET", f"/api/v1/promo/briefs/{bid}/results")[1]


def test_every_write_is_local_and_any_other_write_is_refused(mock):
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        status, _ = call(mock["owner"], method, "/api/v1/bounty/reports", {})
        assert status == 405, method
    post_brief(mock)       # a local write, with fetch_upstream raising if it ever reaches Cymetica


def test_the_operators_example_from_both_sides(mock):
    """A brief for 50k ET10; the promoter asks for 50k; the owner gives 10k; the promoter accepts; 40k stays."""
    bid = post_brief(mock)
    brief = call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"][0]
    assert (brief["budget"], brief["left"], brief["currency"], brief["status"]) == (50000, 50000, "ET10", "open")
    assert "days" not in brief and "ends_at" not in brief
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offer/check", {"handle": "moonfarm_demo"})[1]["ok"] is False
    status, o = offer(mock, bid, 50000)
    assert status == 200 and o["state"] == "pending"
    assert results(mock, bid)["waiting"] == 1
    status, countered = decide(mock, bid, o["id"], amount=10000)
    assert status == 200 and (countered["state"], countered["amount"], countered["ask"]) == ("countered", 10000, 50000)
    assert results(mock, bid)["brief"]["left"] == 40000          # the 10k is set aside, the 40k is still on the market
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/respond", {"accept": True})[1]["state"] == "approved"
    assert call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"][0]["left"] == 40000    # and it hangs on
    # the promoter posts; nothing is payable until it has stayed up 3 days
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})[0] == 200
    pay = f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/pay"
    assert call(mock["owner"], "POST", pay, {})[0] == 409
    call(mock["owner"], "POST", "/__v4/skip", {"days": 2})
    assert call(mock["owner"], "POST", pay, {})[0] == 409
    call(mock["owner"], "POST", "/__v4/skip", {"days": 1})
    status, paid = call(mock["owner"], "POST", pay, {})
    assert status == 200 and paid["state"] == "paid"
    r = results(mock, bid)
    assert (r["brief"]["paid"], r["brief"]["left"]) == (10000, 40000)
    taken = call(mock["promoter"], "GET", "/api/v1/promo/mine")[1]["taken"]["takes"]
    assert [t["offer"]["state"] for t in taken] == ["paid"]


def test_a_promoter_who_declines_the_owners_amount_gives_it_back(mock):
    bid = post_brief(mock)
    _, o = offer(mock, bid, 50000)
    decide(mock, bid, o["id"], amount=10000)
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/respond", {"accept": False})[1]["state"] == "declined"
    assert results(mock, bid)["brief"]["left"] == 50000


def test_nobody_can_be_given_or_ask_for_more_than_is_left(mock):
    bid = post_brief(mock, budget=10)
    assert offer(mock, bid, 11)[0] == 422
    _, first = offer(mock, bid, 6, "gemhunter_demo")
    _, second = offer(mock, bid, 6, "onchain_notes_demo")
    assert decide(mock, bid, first["id"])[0] == 200
    assert decide(mock, bid, second["id"])[0] == 409          # 4 are left, 6 are asked
    assert decide(mock, bid, second["id"], amount=4)[0] == 200
    assert call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"] == []    # nothing left: it leaves the market


def test_cancel_closes_what_is_left_and_agreed_ones_go_on(mock):
    bid = post_brief(mock)
    _, agreed = offer(mock, bid, 100, "gemhunter_demo")
    _, waiting = offer(mock, bid, 100, "onchain_notes_demo")
    decide(mock, bid, agreed["id"])
    assert call(mock["owner"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "cancel"})[0] == 200
    assert call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"] == []
    states = {o["id"]: o["state"] for o in results(mock, bid)["offers"]}
    assert states == {agreed["id"]: "approved"}                 # the waiting one is declined, the agreed one stands


def test_only_the_owner_pays_and_only_the_promoter_offers(mock):
    bid = post_brief(mock)
    assert call(mock["promoter"], "POST", "/api/v1/promo/briefs", BRIEF)[0] == 403
    assert call(mock["owner"], "POST", f"/api/v1/promo/briefs/{bid}/offer/take", {"ask": 5})[0] == 403
    assert call(mock["promoter"], "GET", f"/api/v1/promo/briefs/{bid}/results")[0] == 403
    assert call(mock["promoter"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "cancel"})[0] == 403
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/1/pay", {})[0] == 403


def test_nothing_it_answers_counts_a_visitor_a_click_or_a_new_user(mock):
    sample = _load("sample")
    sample.MARKET.seed("approved")
    bid = sample.MARKET.brief["id"]
    for role, path in (("owner", f"/api/v1/promo/briefs/{bid}/results"), ("owner", "/api/v1/promo/mine"), ("promoter", "/api/v1/promo/mine"),
                       ("promoter", "/api/v1/promo/briefs"), ("promoter", f"/api/v1/promo/briefs/{bid}"),
                       ("promoter", "/api/v1/promo/how-counted")):
        text = json.dumps(sample.answer(role, path)).lower()
        for word in ("visitor", "click", "tracked_url", "per_user", "new_user", "per_visitor"):
            assert word not in text, (path, word)


def test_an_amount_in_et10_is_never_filed_under_usdc(mock):
    bid = post_brief(mock)
    text = json.dumps(results(mock, bid))
    assert "_usdc" not in text and "ET10" in text


def test_the_script_is_added_once_at_the_end_of_their_closure(monkeypatch):
    patch = _load("patch")
    monkeypatch.setattr(patch, "JS_ANCHORS", ())
    closure = "(function () {\n  function a() {}\n" + patch.TAIL + "\n"
    out = patch.patch_js(closure)
    assert out.count("/* promo market v4 */") == 1 and out.index("/* promo market v4 */") < out.index("route(false);")
    with pytest.raises(patch.AnchorMissing):
        patch.patch_js("(function () { route(false); })();")
