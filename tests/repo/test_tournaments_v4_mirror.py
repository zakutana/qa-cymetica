"""The v4 local copy of their Agent Tournaments pages (outbox/tournaments-v4/live).

The operator, 2026-10-26: "musis skopirovat presne jejich aktualni verzi jak to maji ted live. chci presne videt jak to
bude vypadat at muzu tunit a davat feedback". So the pages are THEIR live HTML (four saved copies in fixtures/) with
only the v4 changes laid on top, served by a mirror that may only ever read from their platform.

What each test protects:
* the mirror refuses every method but GET and HEAD, and does not touch their platform for it -- a local copy of a
  page with approve and seat buttons must never be able to move money or seats on the real one;
* six seats at every table and no text left that says ten, so the copy never shows a half-changed page;
* the open cards' pot and prizes are six buy-ins, not ten (a card that said 6 seats and $50 would be a wrong picture);
* the seats that stay are the ones that matter (ours, the leader), not the first six in the markup;
* the Live cards, the wallet panel and the Tune panel are present, so a patch that silently stops matching their
  markup fails here instead of showing the operator an unchanged page.
"""
from __future__ import annotations

import http.client
import importlib.util
import re
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import lxml.html as L
import pytest

from qa.marks import SafetyTier, qa

LIVE = Path(__file__).resolve().parents[2] / "outbox" / "tournaments-v4" / "live"
FIX = LIVE / "fixtures"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"v4_{name}", LIVE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


patch = _load("patch")
serve = _load("serve")


def fixture(name: str) -> str:
    return (FIX / f"{name}.html").read_text(encoding="utf-8")


def body_text(doc) -> str:
    for e in doc.xpath("//style|//script|//svg|//head"):
        e.drop_tree()
    return " ".join(doc.text_content().split())


@pytest.fixture(scope="module")
def lobby():
    return L.fromstring(patch.patch_html("lobby", fixture("lobby")))


@pytest.fixture(scope="module")
def table():
    return L.fromstring(patch.patch_html("table", fixture("table15")))


# ---- the mirror only reads --------------------------------------------------------------------------------------

@pytest.fixture()
def server(monkeypatch):
    calls = []

    def fake(path):
        calls.append(path)
        name = {"/agent-tournaments": "lobby"}.get(path)
        if name is None:
            return 404, "text/plain", b"no", {}
        return 200, "text/html; charset=utf-8", fixture(name).encode("utf-8"), {
            "content-security-policy": "default-src 'self'", "content-security-policy-report-only": "x"}

    monkeypatch.setattr(serve, "fetch_upstream", fake)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1], calls
    srv.shutdown()


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_mirror_refuses_every_write_and_does_not_touch_their_platform(server, method):
    port, calls = server
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request(method, "/api/v1/agent-tournaments/seats/1/approve", body=b"{}")
    r = c.getresponse()
    r.read()
    assert r.status == 405
    assert calls == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_get_returns_their_page_with_the_v4_layer_and_without_their_security_headers(server):
    port, calls = server
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", "/agent-tournaments")
    r = c.getresponse()
    body = r.read().decode("utf-8")
    assert r.status == 200 and calls == ["/agent-tournaments"]
    assert "/__v4/v4.js" in body and "/__v4/v4.css" in body
    assert r.getheader("content-security-policy") is None
    assert r.getheader("content-security-policy-report-only") is None


# ---- six seats, no ten left ------------------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_table_in_the_lobby_has_six_seats(lobby):
    tables = lobby.xpath('//div[contains(@class,"at-tbl")]')
    assert len(tables) >= 8
    assert {len(t.xpath('./span[contains(@class,"at-seat")]')) for t in tables} == {6}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_text_left_in_any_page_says_ten_seats():
    bad = re.compile(r"\b10 (seats|SEATS|AI agents|agents\.)|\b10th\b|\b10/10\b|same 10 seats", re.I)
    for page, name in (("lobby", "lobby"), ("table", "table15"), ("leaderboard", "leaderboard"), ("how", "how")):
        doc = L.fromstring(patch.patch_html(page, fixture(name)))
        text = body_text(doc)
        assert not bad.search(text), (page, bad.search(text).group(0))
        assert "10 agents trading on Cymetica" in text or page != "lobby"   # a count of agents, not the table size


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lobby_headline_says_six(lobby):
    assert lobby.xpath('//h1[contains(@class,"at-h1")]')[0].text_content().startswith("6 agents.")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_open_cards_pot_and_prizes_are_six_buy_ins(lobby):
    card = lobby.xpath('//a[contains(@class,"at-tcard") and contains(@class,"micro")]')[0]    # $5, ten seats live
    assert card.xpath('.//*[@data-at-pot]')[0].text_content() == "$30"
    assert [b.text_content().split("+")[0] for b in card.xpath('.//div[contains(@class,"at-c3")]//b')] == ["$18", "$9", "$3"]
    assert "6 SEATS LEFT" in card.text_content()
    et = lobby.xpath('//a[contains(@class,"at-tcard") and contains(@class,"et1k")]')[0]       # 1,000 ET10 a seat
    assert et.xpath('.//*[@data-at-pot]')[0].text_content() == "6,000"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_seats_that_stay_are_ours_and_the_leader(lobby):
    card = lobby.xpath('//a[@data-table-id="15"]')[0]
    names = [a.get("title") for a in card.xpath('.//span[contains(@class,"at-ava")][@title]')]
    assert len(names) == 6
    assert "lab Wave 2 Perceptron Oracle" in names and "House Ichimoku Empress" in names
    assert card.xpath('.//span[contains(@class,"at-seat") and contains(@class,"lead")]')


# ---- the table page ---------------------------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_table_page_has_six_seats_and_six_standings_rows(table):
    assert len(table.xpath('//section[contains(@class,"at-o-tbl")]//span[contains(@class,"at-seat")]')) == 6
    rows = table.xpath('//div[contains(@class,"at-lr")]')
    assert len(rows) == 6
    assert any("lab Wave 2 Perceptron Oracle" in r.text_content() for r in rows)
    assert table.xpath('//span[contains(@class,"seats")]/b')[0].text_content() == "6/6"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_race_keeps_only_the_six_lines(table):
    lines = table.xpath('//section[contains(@class,"at-race")]//polyline')
    assert 1 <= len(lines) <= 6


# ---- what v4 adds -----------------------------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_live_cards_the_wallet_panel_and_the_tune_panel_are_there(lobby, table):
    live = lobby.xpath('//*[@id="atLiveV4"]')[0]
    names = [n.text_content() for n in live.xpath('.//span[contains(@class,"at-tname")]')]
    assert [n.split("#")[0].strip() for n in names] == ["Flash 1 h", "Flash 5 h", "Flash 1 d"]
    assert [b.text_content() for b in live.xpath('.//span[contains(@class,"at-buyin")]')] == ["$1", "$1", "$5"]
    assert lobby.xpath('//*[@id="atWalletV4"]')
    assert table.xpath('//*[@data-v4="tune"]')
    assert table.xpath('//*[@data-v4="tune"]//input[@data-v4-sw]')


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_v4_stylesheet_adds_no_colour_of_its_own():
    css = (LIVE / "v4.css").read_text(encoding="utf-8")
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", css), "colours come from their variables"
    assert {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", css)} <= {
        "0,207,255", "0,255,136", "255,68,68", "13,21,32", "59,130,246"}


# ---- the owner's view, in their markup --------------------------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_owner_sees_your_agent_in_the_hero_and_you_on_their_card(lobby):
    me = lobby.xpath('//a[contains(@class,"at-me")]')
    assert me and "#5" in me[0].text_content() and "/6" in me[0].text_content()
    card = lobby.xpath('//a[@data-table-id="15"]')[0]
    assert "mine" in card.get("class").split()
    assert card.xpath('.//span[contains(@class,"at-seat") and contains(@class,"you")]')


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_changelog_says_who_changed_what(table):
    tags = [t.text_content() for t in table.xpath('//section[@id="atChanges"]//*[contains(@class,"v4-who")]')]
    assert tags == ["OWNER", "NEXUS"]       # 23 Oct 20:53 is not in the lock's tune list; 21 Oct 07:56 is


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_race_draws_our_seventeen_trades_as_merged_markers(table):
    marks = table.xpath('//circle[contains(@class,"v4-mk")]')
    merged = [int(t.text_content()) for t in table.xpath('//section[contains(@class,"at-race")]//svg/text')
              if t.text_content().strip().isdigit()]
    single = sum(1 for m in marks if m.get("r") == "5.5")
    assert 2 <= len(marks) < 17
    assert sum(merged) + single == 17
