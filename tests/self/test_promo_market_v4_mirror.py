"""The Promo Market v4 mock: two windows (the owner who posts a brief, the promoter who takes it) over ONE sample.

The mock holds its own state so the operator can click the whole workflow from both sides; none of it may ever reach
cymetica.com. Every write is local, every other write is refused. A brief is a budget in USDC or ET10 covered by the
owner's Cymetica credit: it has no end date, nothing is locked while it hangs, the owner can add funds to it. A
promoter takes it with an X handle and names no amount; the owner looks at the account (a suggestion from the
expected reach is filled in) and sends an offer, which locks it; the promoter accepts it or not; it moves to the
promoter only when the owner approves a post that stayed up 3 days. No visitor, click or new-user number exists in
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
    servers, running = {"market": serve.sample.MARKET}, []
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


def take(m, bid, handle="gemhunter_demo"):
    status, o = call(m["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offer/take", {"handle": handle})
    assert status == 200, o
    return o


def accept(m, bid, oid):
    """The promoter's answer to the owner's amount."""
    return call(m["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{oid}/accept", {})


def agreed(m, bid, amount=12000):
    """Taken, offered by the owner, accepted by the promoter: the offer a post can be registered for."""
    o = take(m, bid)
    assert decide(m, bid, o["id"], amount=amount)[0] == 200
    assert accept(m, bid, o["id"])[0] == 200
    return o


def decide(m, bid, oid, decision="accept", amount=None):
    return call(m["owner"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{oid}", {"decision": decision, "amount": amount})


def results(m, bid):
    return call(m["owner"], "GET", f"/api/v1/promo/briefs/{bid}/results")[1]


def credit(m, cur="ET10"):
    return call(m["owner"], "GET", "/api/v1/promo/mine")[1]["credit"][cur]


def news(m, role):
    return [n["text"] for n in call(m[role], "GET", "/__v4/state?since=0")[1]["news"]]


def test_every_write_is_local_and_any_other_write_is_refused(mock):
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        status, _ = call(mock["owner"], method, "/api/v1/bounty/reports", {})
        assert status == 405, method
    post_brief(mock)       # a local write, with fetch_upstream raising if it ever reaches Cymetica


def test_the_whole_flow_from_both_sides(mock):
    """A brief for 50k ET10 hangs unlocked; a promoter takes it with a handle; the owner sends the suggested 12k, which
    locks; the promoter accepts; the post stays up 3 days; the owner approves and the 12k moves; 38k is still on the
    market."""
    bid = post_brief(mock)
    brief = call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"][0]
    assert (brief["budget"], brief["left"], brief["locked"], brief["currency"], brief["status"]) == (50000, 50000, 0, "ET10", "open")
    assert "days" not in brief and "ends_at" not in brief
    assert credit(mock) == {"free": 200000, "locked": 0}            # a hanging brief locks nothing
    take_url = f"/api/v1/promo/briefs/{bid}/offer/take"
    assert call(mock["promoter"], "POST", take_url, {})[0] == 422                       # no handle, no request
    assert call(mock["promoter"], "POST", take_url, {"handle": "moonfarm_demo"})[0] == 422      # a bought audience never reaches the owner
    assert results(mock, bid)["waiting"] == 0 and sum(n for _, n in results(mock, bid)["filtered_out"]) == 1
    o = take(mock, bid)
    assert (o["state"], o["amount"]) == ("pending", None)           # the promoter names no amount
    assert call(mock["promoter"], "POST", take_url, {"handle": "gemhunter_demo"})[0] == 409     # and asks once
    seen = results(mock, bid)["offers"][0]                           # the owner's side holds the account and the suggestion
    assert results(mock, bid)["waiting"] == 1 and seen["suggest"] == 12000 and seen["reach_lo"] < seen["reach"] < seen["reach_hi"]
    assert any("wants your brief" in t for t in news(mock, "owner")) and news(mock, "promoter") == []
    pay = f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/pay"
    assert call(mock["owner"], "POST", pay, {})[0] == 409            # nothing accepted, nothing to approve
    assert accept(mock, bid, o["id"])[0] == 409                      # and nothing offered, nothing to accept
    status, a = decide(mock, bid, o["id"], amount=seen["suggest"])
    assert status == 200 and (a["state"], a["amount"]) == ("offered", 12000)
    r = results(mock, bid)["brief"]
    assert (r["left"], r["locked"], r["paid"]) == (38000, 12000, 0)  # the offer itself locks it
    assert credit(mock) == {"free": 188000, "locked": 12000}
    assert any("offers you 12,000 ET10" in t for t in news(mock, "promoter"))
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})[0] == 409     # no post before the promoter accepts
    status, a = accept(mock, bid, o["id"])
    assert status == 200 and (a["state"], a["amount"]) == ("approved", 12000)
    assert any("accepted 12,000 ET10" in t for t in news(mock, "owner"))
    assert credit(mock) == {"free": 188000, "locked": 12000}
    # the promoter posts; nothing moves until it has stayed up 3 days AND the owner approves
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": "https://example.com/x"})[0] == 422
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})[0] == 200
    assert call(mock["owner"], "POST", pay, {})[0] == 409
    call(mock["owner"], "POST", "/__v4/skip", {"days": 2})
    assert call(mock["owner"], "POST", pay, {})[0] == 409
    call(mock["owner"], "POST", "/__v4/skip", {"days": 1})
    assert results(mock, bid)["offers"][0]["state"] == "earned"
    assert credit(mock) == {"free": 188000, "locked": 12000}        # three days alone move nothing
    assert any("approve it to pay" in t for t in news(mock, "owner"))
    status, paid = call(mock["owner"], "POST", pay, {})
    assert status == 200 and paid["state"] == "paid"
    r = results(mock, bid)["brief"]
    assert (r["paid"], r["locked"], r["left"], r["status"]) == (12000, 0, 38000, "open")
    assert credit(mock) == {"free": 188000, "locked": 0}
    mine = call(mock["promoter"], "GET", "/api/v1/promo/mine")[1]
    assert [t["offer"]["state"] for t in mine["taken"]["takes"]] == ["paid"] and mine["earned"] == {"ET10": 12000}
    assert call(mock["owner"], "POST", pay, {})[0] == 409            # and it cannot be paid twice


def test_a_brief_in_usdc_is_covered_by_usdc_credit(mock):
    assert call(mock["owner"], "POST", "/api/v1/promo/briefs", {**BRIEF, "currency": "USDC", "budget": 600})[0] == 409      # 500 USDC of credit
    assert call(mock["owner"], "POST", "/api/v1/promo/briefs", {**BRIEF, "currency": "DOGE"})[0] == 422
    bid = post_brief(mock, currency="USDC", budget=200)
    o = take(mock, bid)
    seen = results(mock, bid)["offers"][0]
    assert (seen["currency"], seen["suggest"]) == ("USDC", 30)
    assert decide(mock, bid, o["id"], amount=30)[0] == 200
    assert credit(mock, "USDC") == {"free": 470, "locked": 30} and credit(mock, "ET10") == {"free": 200000, "locked": 0}


def test_nobody_is_given_more_than_the_brief_has_left(mock):
    bid = post_brief(mock, budget=10000)
    o = take(mock, bid)
    assert decide(mock, bid, o["id"], amount=10001)[0] == 409
    assert decide(mock, bid, o["id"], amount=0)[0] == 422
    assert decide(mock, bid, o["id"], amount=10000)[0] == 200
    assert results(mock, bid)["brief"]["status"] == "full"
    assert call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"] == []    # all handed out: it leaves the market
    assert call(mock["owner"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "add_budget", "amount": 5000})[0] == 200
    assert call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"][0]["left"] == 5000     # funds added: open again


def test_add_funds_raises_what_can_be_handed_out_up_to_the_free_credit(mock):
    bid = post_brief(mock)
    add = lambda n: call(mock["owner"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "add_budget", "amount": n})      # noqa: E731
    status, out = add(25000)
    assert status == 200 and (out["budget"], out["left"]) == (75000, 75000)
    assert credit(mock) == {"free": 200000, "locked": 0}            # adding locks nothing
    assert add(125001)[0] == 409 and add(0)[0] == 422
    assert add(125000)[0] == 200
    call(mock["owner"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "cancel"})
    assert add(1)[0] == 409                                         # an ended brief takes no funds


def test_the_promoter_says_no_to_an_offer_and_it_is_unlocked(mock):
    bid = post_brief(mock)
    o = take(mock, bid)
    decide(mock, bid, o["id"], amount=12000)
    assert credit(mock) == {"free": 188000, "locked": 12000}
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/pass", {})[1]["state"] == "declined"
    assert results(mock, bid)["brief"]["left"] == 50000 and credit(mock) == {"free": 200000, "locked": 0}
    assert any("said no to 12,000 ET10" in t and "unlocked" in t for t in news(mock, "owner"))
    assert accept(mock, bid, o["id"])[0] == 409                      # a no is a no
    o = take(mock, bid)                                              # the brief is open for them again
    decide(mock, bid, o["id"], amount=9000)
    assert decide(mock, bid, o["id"], "decline")[1]["state"] == "declined"            # the owner withdraws an unanswered offer
    assert credit(mock) == {"free": 200000, "locked": 0} and any("withdrew the offer of 9,000 ET10" in t for t in news(mock, "promoter"))
    assert accept(mock, bid, o["id"])[0] == 409


def test_the_owner_takes_back_and_the_promoter_passes_only_before_the_post(mock):
    bid = post_brief(mock)
    o = agreed(mock, bid)
    assert decide(mock, bid, o["id"], "decline")[1]["state"] == "declined"            # taken back: unlocked
    assert results(mock, bid)["brief"]["left"] == 50000 and credit(mock) == {"free": 200000, "locked": 0}
    assert any("took back the 12,000 ET10" in t for t in news(mock, "promoter"))
    o = take(mock, bid)                                             # the promoter may ask again
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/pass", {})[1]["state"] == "declined"     # withdrawn while waiting
    o = agreed(mock, bid)
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/pass", {})[0] == 200                     # passed while locked
    assert credit(mock) == {"free": 200000, "locked": 0} and any("passed" in t and "unlocked" in t for t in news(mock, "owner"))
    o = agreed(mock, bid)
    call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})
    assert decide(mock, bid, o["id"], "decline")[0] == 409           # the post is up: neither side walks away
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{o['id']}/pass", {})[0] == 409
    assert credit(mock) == {"free": 188000, "locked": 12000}


def test_cancel_ends_what_is_not_agreed_and_accepted_ones_go_on(mock):
    bid = post_brief(mock)
    mine = agreed(mock, bid)
    other = mock["market"]._offer("onchain_notes_demo")              # another promoter, still waiting
    sent = mock["market"]._offer("defi_digest_demo")                 # and one with an offer out, not answered
    decide(mock, bid, sent["id"], amount=7500)
    assert credit(mock) == {"free": 180500, "locked": 19500}
    call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})
    assert call(mock["owner"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "cancel"})[0] == 200
    assert call(mock["promoter"], "GET", "/api/v1/promo/briefs")[1]["briefs"] == []
    r = results(mock, bid)
    assert {o["id"]: o["state"] for o in r["offers"]} == {mine["id"]: "posted"}       # the waiting one is declined, the accepted one stands
    assert (other["state"], sent["state"]) == ("declined", "declined")
    assert (r["brief"]["status"], r["brief"]["locked"]) == ("cancelled", 12000) and credit(mock) == {"free": 188000, "locked": 12000}
    call(mock["owner"], "POST", "/__v4/skip", {"days": 3})
    assert call(mock["owner"], "POST", f"/api/v1/promo/briefs/{bid}/offers/{mine['id']}/pay", {})[1]["state"] == "paid"   # and is still paid
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offer/take", {"handle": "gemhunter_demo"})[0] == 409


def test_each_side_can_do_only_its_own_part(mock):
    bid = post_brief(mock)
    o = take(mock, bid)
    offer = f"/api/v1/promo/briefs/{bid}/offers/{o['id']}"
    assert call(mock["promoter"], "POST", "/api/v1/promo/briefs", BRIEF)[0] == 403
    assert call(mock["promoter"], "POST", offer, {"decision": "accept", "amount": 50000})[0] == 403     # a promoter cannot name their own amount
    assert call(mock["owner"], "POST", offer + "/accept", {})[0] == 403                                 # nor the owner accept for them
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/offer/check", {"handle": "gemhunter_demo"})[0] == 405     # no account check on the promoter's side
    assert call(mock["promoter"], "POST", offer + "/pay", {})[0] == 403
    assert call(mock["promoter"], "GET", f"/api/v1/promo/briefs/{bid}/results")[0] == 403
    assert call(mock["promoter"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "cancel"})[0] == 403
    assert call(mock["promoter"], "PATCH", f"/api/v1/promo/briefs/{bid}", {"action": "add_budget", "amount": 1})[0] == 403
    assert call(mock["owner"], "POST", f"/api/v1/promo/briefs/{bid}/offer/take", {"handle": "gemhunter_demo"})[0] == 403
    assert call(mock["owner"], "POST", offer + "/pass", {})[0] == 403
    assert call(mock["owner"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})[0] == 403
    assert call(mock["promoter"], "POST", f"/api/v1/promo/briefs/{bid}/posts", {"url": POST})[0] == 409     # no post before the owner accepts


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
