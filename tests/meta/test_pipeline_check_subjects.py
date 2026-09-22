"""Which case a vendor check judges -- driven whole, offline, on stub clients.

Three checks written on 2026-09-21 were each one line away from a false pass,
and every one of the three was the same shape: the check judged a case, not
THE case its report is about (R03, R09, R10 and the audit's A01-A03, deep pass
of 2026-09-21). A helper test would not have seen it: the subject is chosen
inside the test function, so the whole function is what runs here, with the
network replaced by stubs.

Not in test_pipeline_check_quality.py: that file judges each reconciliation
claim against a captured source, one parametrised rule at a time; these are
decisions made in Python inside a single check, with no capture to read.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Response:
    def __init__(self, status: int, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class _Rest:
    """GET only, answered from a map of path -> (status, body)."""

    def __init__(self, answers: dict):
        self.answers, self.asked = answers, []

    def get(self, path, **_):
        self.asked.append(path)
        status, body = self.answers.get(path, (404, {}))
        return _Response(status, body)


# --------------------------------------------------------------- #117 -------

A, B = "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161", "b0b0b0b0-0000-4000-8000-000000000001"


def _buy(trade_id, card, at, status, outcome):
    return [{"id": trade_id, "type": "intent", "card_id": card, "usdc": 1000.0,
             "at": f"2026-09-21T{at}+00:00"},
            {"id": trade_id, "type": "outcome", "http_status": status,
             "outcome": outcome, "response": "Buy failed" if status >= 500 else ""}]


def _card(tradeable: bool):
    return (200, {"status": "live", "tradeable_now": tradeable,
                  "trading_blocked_reason": None if tradeable else "market closed",
                  "basket": []})


def _run_buy_check(monkeypatch, rows, cards):
    check = _load("tests/rest/test_a_tradeable_card_takes_a_paper_buy.py",
                  "paper_buy_check_under_test")
    monkeypatch.setattr(check, "_paper", lambda: type("P", (), {
        "load": staticmethod(lambda: rows)})())
    rest = _Rest({f"/api/v1/event-cards/{card}": answer
                  for card, answer in cards.items()})
    check.test_a_card_that_reads_tradeable_now_takes_a_paper_buy(rest)
    return rest


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_that_failed_and_was_never_tried_again_still_fails_117(monkeypatch):
    """A01, deep pass of 2026-09-21 (3/3). After R03 the subject was the card
    of the NEWEST 5xx buy, so card A answering 500, card B answering 500, and
    B then accepted, passed #117 with A never tried again -- against the
    docstring's own "a card nobody tries again stays failed". Every card whose
    newest buy is a 5xx is judged."""
    rows = (_buy("TRD-1", A, "17:01:28", 500, "unknown")
            + _buy("TRD-2", B, "17:05:00", 500, "unknown")
            + _buy("TRD-3", B, "17:09:00", 200, "accepted"))
    with pytest.raises(AssertionError, match=A):
        _run_buy_check(monkeypatch, rows, {A: _card(True), B: _card(True)})

    # A buy of A itself that lands is the fix.
    fixed = rows + _buy("TRD-4", A, "17:20:00", 200, "accepted")
    _run_buy_check(monkeypatch, fixed, {A: _card(True), B: _card(True)})

    # A card that no longer reads tradeable cannot show the defect or its fix.
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, rows, {A: _card(False), B: _card(True)})

    # A card that cannot be read is unmeasured (rule 8), never a pass.
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, rows, {A: (503, {}), B: _card(True)})

    # A stated refusal on the failed card is the gate working, not the fix.
    refused = rows + _buy("TRD-5", A, "17:30:00", 400, "refused")
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, refused, {A: _card(True), B: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_buy_is_judged_by_what_the_card_said_when_it_was_placed_117(
        monkeypatch):
    """A03, deep pass of 2026-09-22: the contract is tradeable_now AT the
    buy, and the check could only read it today. paper.py now records the
    card's own gate in the intent; a 5xx on a card that read NOT tradeable
    then is the gate's business, however it reads now, and one that read
    tradeable then fails even if it has since shut."""
    shut_then = _buy("TRD-1", A, "17:01:28", 500, "unknown")
    shut_then[0]["card_before"] = {"tradeable_now": False,
                                   "trading_blocked_reason": "market closed"}
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, shut_then, {A: _card(True)})

    open_then = _buy("TRD-1", A, "17:01:28", 500, "unknown")
    open_then[0]["card_before"] = {"tradeable_now": True,
                                   "trading_blocked_reason": None}
    with pytest.raises(AssertionError, match=A):
        _run_buy_check(monkeypatch, open_then, {A: _card(False)})

    # C09, deep pass of 2026-09-22 evening (3/3): paper.py records a card it
    # could not read at the buy as {"http_status": 503}. That was taken as
    # "the buy predates recording the card" and judged on today's read --
    # a false sentence, and a fail that may blame a card shut at the time.
    unread_then = _buy("TRD-1", A, "17:01:28", 500, "unknown")
    unread_then[0]["card_before"] = {"at": "2026-09-21T17:01:27+00:00",
                                     "http_status": 503}
    with pytest.raises(Inconclusive, match="could not be read"):
        _run_buy_check(monkeypatch, unread_then, {A: _card(True)})


# --------------------------------------------------------------- #116 -------

class _Mcp:
    def __init__(self, methodology: str, inception: str, ret: float = -19.05):
        self.methodology, self.inception, self.ret = methodology, inception, ret

    def call(self, name, args):
        if name == "get_fund_methodology":
            return {"result": {"methodology": {"returns": self.methodology}}}
        return {"result": {"fund": {"inception_date": self.inception,
                                    "return_since_inception_pct": self.ret,
                                    "last_composition_change": "2026-08-17"}}}


HISTORY = {"/api/v1/fta-fund/history": (200, {
    "inception": "2026-08-09",
    "points": [{"t": "2026-08-21", "v": 100.0}, {"t": "2026-09-20", "v": 119.05}]})}


def _run_fta_check(methodology: str, inception: str = "2026-07-26"):
    check = _load("tests/mcp/test_fta_crypto_return_starts_where_its_record_does.py",
                  "fta_check_under_test")
    check.test_the_fta_crypto_return_starts_where_its_own_record_does(
        _Mcp(methodology, inception), _Rest(HISTORY))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_denial_of_a_pro_forma_stretch_is_not_a_disclosure_of_one_116():
    """A03, deep pass of 2026-09-21 (3/3). R09 made the fix a DISCLOSURE, and
    a regex looked for "pro forma" anywhere: "nothing backfilled, no
    pro-forma, no backtest" denies the stretch and was read as disclosing it,
    so the rewording passed with the return still starting 14 days early."""
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Return is measured since the fund's own inception from "
                       "real market prices -- nothing backfilled, no pro-forma, "
                       "no backtest.")
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Returns are never pro forma: nothing backfilled.")
    # A02, deep pass of 2026-09-22: "nothing" was not a negation, so the
    # denial their page could write next passed as a disclosure.
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Measured since inception: nothing backfilled or "
                       "pro-forma.")
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Neither backfilled nor pro-forma.")
    # C07, deep pass of 2026-09-22 evening (3/3): a negation AFTER the word
    # denies it just as well, and read as a disclosure.
    for denial in ("Measured since inception; nothing backfilled; pro-forma "
                   "periods are excluded.",
                   "Pro-forma figures are never used; nothing backfilled.",
                   "Returns exclude any pro-forma stretch."):
        with pytest.raises(AssertionError, match="discloses no pro-forma"):
            _run_fta_check(denial)

    _run_fta_check("Return since inception includes a pro-forma period before "
                   "the first held position: today's composition applied to "
                   "past closes.")
    # A negation in the sentence before is not a denial of this one.
    _run_fta_check("No backfill. Pro-forma: the stretch before the first "
                   "position applies today's composition to past closes.")

    with pytest.raises(Inconclusive):
        _run_fta_check("")


# ------------------------------------------------- a refused clone says why -

PCPN, RSI = "23441934-8475-4aa0-bbff-75c03ecd3284", "70a47f2a-e1d5-40dc-9c01-bd9b9a2d3c80"
AGAIN = {"detail": "Invalid clone request. Please try again."}
OPENAPI_CLONE = (200, {"paths": {"/api/v1/cloned-bots/clone": {"post": {
    "responses": {"200": {}, "422": {}}}}}})


def _cloned(clone_id, source, at, status, outcome):
    return [{"id": clone_id, "type": "intent", "source_type": "wta_species",
             "source_id": source, "paper": True, "at": f"2026-09-22T{at}+00:00"},
            {"id": clone_id, "type": "outcome", "http_status": status,
             "outcome": outcome, "evidence_id": f"ev-{clone_id}",
             # What the record said until 2026-09-22 -- never read: the check
             # takes the body from the capture.
             "response": "{}"}]


def _run_clone_check(monkeypatch, rows, bodies):
    check = _load("tests/rest/test_a_refused_clone_says_why.py",
                  "refused_clone_check_under_test")
    monkeypatch.setattr(check, "_clones", lambda: type("C", (), {
        "load": staticmethod(lambda: rows)})())
    monkeypatch.setattr(check, "their_body",
                        lambda attempt: bodies.get(attempt["id"]))
    check.test_a_refused_paper_clone_says_why(
        _Rest({"/openapi-public.json": OPENAPI_CLONE}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clone_refusal_that_asks_for_the_retry_it_refuses_fails(monkeypatch):
    """CLN-0017 and CLN-0020: the same paper clone, refused twice with "Please
    try again". Judged per source by its newest attempt -- the #117 lesson: a
    different species cloned afterwards is not the fix -- and on their body
    from the capture, never on our record's `response`, which read `{}`."""
    rows = (_cloned("CLN-0017", PCPN, "13:39:02", 400, "rejected")
            + _cloned("CLN-0014", RSI, "13:39:30", 200, "accepted")
            + _cloned("CLN-0020", PCPN, "17:47:14", 400, "rejected"))
    twice = {"CLN-0017": AGAIN, "CLN-0020": AGAIN}
    with pytest.raises(AssertionError, match="Please try again"):
        _run_clone_check(monkeypatch, rows, twice)
    # Another species cloned AFTER it is not the fix.
    later = rows + _cloned("CLN-0021", RSI, "18:00:00", 200, "accepted")
    with pytest.raises(AssertionError, match=PCPN):
        _run_clone_check(monkeypatch, later, twice)

    # Refused once, never retried: the advice has not been tested.
    with pytest.raises(Inconclusive):
        _run_clone_check(monkeypatch, rows[:4], {"CLN-0017": AGAIN})

    # A capture that cannot be read is unmeasured, not an empty body.
    with pytest.raises(Inconclusive):
        _run_clone_check(monkeypatch, rows, {"CLN-0017": AGAIN})

    # A refusal with nothing in it fails on its own.
    with pytest.raises(AssertionError, match="no detail"):
        _run_clone_check(monkeypatch, rows, {"CLN-0017": AGAIN, "CLN-0020": {}})

    # The fixes: the clone is made, or the refusal names its reason.
    made = rows + _cloned("CLN-0030", PCPN, "18:30:00", 200, "accepted")
    _run_clone_check(monkeypatch, made, twice)
    named = rows + _cloned("CLN-0031", PCPN, "18:40:00", 409, "rejected")
    _run_clone_check(monkeypatch, named, {**twice, "CLN-0031": {
        "detail": "You already hold a paper clone of this species."}})


def _run_clone_check_on_captures(monkeypatch, rows, captured):
    """The check with the REAL their_body, reading captures from a stub store
    keyed by evidence id -- `_run_clone_check` stubs their_body itself, and a
    captured empty body never reaches the check as `{}` (C08)."""
    check = _load("tests/rest/test_a_refused_clone_says_why.py",
                  "refused_clone_check_on_captures")
    monkeypatch.setattr(check, "_clones", lambda: type("C", (), {
        "load": staticmethod(lambda: rows)})())

    class Store:
        @staticmethod
        def load(evidence_id, root=None):
            if evidence_id not in captured:
                raise OSError(evidence_id)
            return {"response": {"body": captured[evidence_id]}}
    monkeypatch.setattr(check, "EvidenceStore", Store)
    check.test_a_refused_paper_clone_says_why(
        _Rest({"/openapi-public.json": OPENAPI_CLONE}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clone_refusal_is_read_the_way_it_was_captured(monkeypatch):
    """A04 and C08, deep pass of 2026-09-22 evening (3/3 each), and R04 (2/3).

    An empty 400 is captured as {"encoding": "empty", "value": null}, so the
    real their_body returned None and the docstring's "no detail at all --
    fail" went inconclusive as an unreadable capture. A reason under a key
    other than `detail` read as no reason. The no-detail breach went out with
    the retry sentence it does not fit. And "do not try again" read as asking
    for a retry, so a fix that names its reason would have failed."""
    one = _cloned("CLN-0017", PCPN, "13:39:02", 400, "rejected")

    # Inconclusive is a skip, so an unmeasured result would read as a skipped
    # guard, not a red one: caught and failed here.
    try:
        with pytest.raises(AssertionError, match="no detail") as silent:
            _run_clone_check_on_captures(monkeypatch, one, {
                "ev-CLN-0017": {"encoding": "empty", "value": None}})
    except Inconclusive as exc:
        pytest.fail(f"an empty refusal read as an unreadable capture: {exc}")
    assert "asks for a retry" not in str(silent.value), str(silent.value)

    # A capture that is not there is still unmeasured, not an empty body.
    with pytest.raises(Inconclusive):
        _run_clone_check_on_captures(monkeypatch, one, {})

    # A reason under their own error envelope is a reason.
    _run_clone_check_on_captures(monkeypatch, one, {
        "ev-CLN-0017": {"encoding": "json", "value": {"error": {
            "code": "CLONE_LIMIT", "message": "one paper clone per species"}}}})

    # A refusal that tells the caller NOT to try again does not ask for one,
    # retried or not.
    again = one + _cloned("CLN-0020", PCPN, "17:47:14", 400, "rejected")
    told = {"encoding": "json", "value": {
        "detail": "You already hold a paper clone of this species; do not try again."}}
    _run_clone_check_on_captures(monkeypatch, again, {
        "ev-CLN-0017": told, "ev-CLN-0020": told})

    # And the defect as captured still fails, retry sentence and all.
    asked = {"encoding": "json", "value": AGAIN}
    with pytest.raises(AssertionError, match="asks for a retry"):
        _run_clone_check_on_captures(monkeypatch, again, {
            "ev-CLN-0017": asked, "ev-CLN-0020": asked})


# ------------------------------------ /api-docs examples carry what they need -

CLONE_SPEC = {
    "paths": {
        "/api/v1/cloned-bots/clone": {"post": {"requestBody": {"content": {
            "application/json": {"schema": {
                "$ref": "#/components/schemas/CloneBotRequest"}}}}}},
        "/api/v1/cloned-bots/{instance_id}/fund": {"post": {"requestBody": {
            "content": {"application/json": {"schema": {
                "required": ["amount"], "properties": {"amount": {}}}}}}}},
    },
    "components": {"schemas": {"CloneBotRequest": {
        "required": ["source_type", "source_id"],
        "properties": {"source_type": {}, "source_id": {}, "paper": {},
                       "is_paper": {}, "custom_name": {}}}}},
}


def _page(*blocks):
    return "".join(f'<div class="code-block" style="x">{b}</div><p>prose</p>'
                   for b in blocks)


def _curl(path, body, method="POST"):
    return (f"curl -X {method} https://cymetica.com{path} \\\n"
            f"  -H \"X-API-Key: $KEY\" \\\n  -d '{body}'\n"
            f'<span style="c"># Response:</span>\n{{"ok": true}}')


class _Page:
    def __init__(self, status, text=None, body=None):
        self.status_code, self.text, self._body = status, text, body

    def json(self):
        return self._body


def _run_docs_check(page, spec=CLONE_SPEC, page_status=200, spec_status=200):
    check = _load(
        "tests/discovery/test_api_docs_examples_carry_what_their_routes_require.py",
        "docs_examples_check_under_test")

    class Rest:
        def get(self, path, **_):
            if path == "/api-docs":
                return _Page(page_status, text=page)
            return _Page(spec_status, body=spec)
    check.test_every_request_example_on_api_docs_carries_what_its_route_requires(Rest())


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_api_docs_example_missing_a_required_field_fails():
    """/api-docs on 2026-09-22: the clone example sends bot_id and is_paper,
    and CloneBotRequest requires source_type and source_id. A route reached
    through a template ({instance_id}) is matched too, and a span inside the
    block -- their markup -- does not break the body."""
    bad = _page(_curl("/api/v1/cloned-bots/clone",
                      '{"bot_id": "bot_abc123", "is_paper": true}'),
                _curl("/api/v1/cloned-bots/abc/fund", '{"amount": 1}'))
    with pytest.raises(AssertionError, match="source_type"):
        _run_docs_check(bad)

    good = _page(_curl("/api/v1/cloned-bots/clone",
                       '{"source_type": "wta_species", "source_id": "s1", '
                       '"paper": true}'),
                 _curl("/api/v1/cloned-bots/abc/fund", '{"amount": 1}'))
    _run_docs_check(good)

    # A missing field on the templated route is found as well.
    with pytest.raises(AssertionError, match="amount"):
        _run_docs_check(_page(_curl("/api/v1/cloned-bots/abc/fund", '{"x": 1}')))

    # A route the schema does not publish is not judged; alone, nothing is.
    with pytest.raises(Inconclusive):
        _run_docs_check(_page(_curl("/api/v1/wta/markets/m1/bet", '{"x": 1}')))

    # No example found, or a document that cannot be read: nothing measured.
    with pytest.raises(Inconclusive):
        _run_docs_check("<p>curl -X POST https://cymetica.com/api/v1/"
                        "cloned-bots/clone -d '{\"bot_id\": 1}'</p>")
    with pytest.raises(Inconclusive):
        _run_docs_check(bad, spec_status=503)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_way_a_curl_can_be_written_is_read():
    """A06 (3/3) and R06 (2/3), deep pass of 2026-09-22 evening. The reader
    took only `curl -X METHOD https://... -d '{...}'`: a quoted URL -- two on
    their page that day -- `--data`, a double-quoted body, or `-X` after the
    URL were neither judged nor counted, while the pass line said all
    examples hold."""
    check = _load(
        "tests/discovery/test_api_docs_examples_carry_what_their_routes_require.py",
        "docs_examples_spellings")
    fund = "/api/v1/cloned-bots/abc/fund"
    spellings = [
        f"curl -X POST \"https://cymetica.com{fund}\" -d '{{\"x\": 1}}'",
        f"curl https://cymetica.com{fund} -X POST --data '{{\"x\": 1}}'",
        f"curl -X POST https://cymetica.com{fund} -d \"{{\\\"x\\\": 1}}\"",
        f"curl https://cymetica.com{fund} --data-raw '{{\"x\": 1}}'",
    ]
    for spelled in spellings:
        found = check.examples(_page(spelled))
        assert len(found) == 1, (spelled, found)
        said = check.judge(_page(spelled), CLONE_SPEC)
        assert said["breaches"] and said["breaches"][0]["missing"] == ["amount"], (
            spelled, said)

    # Counted when unpublished, as the docstring says.
    said = check.judge(_page(
        "curl -X POST \"https://cymetica.com/api/v1/ai_trading_agent/prompt-assets\" "
        "-d '{\"q\": 1}'"), CLONE_SPEC)
    assert said["unpublished"] == ["POST /api/v1/ai_trading_agent/prompt-assets"], said


# ------------------------------- a card's tradeability, REST against MCP -----

CLOSED = "US equity markets are closed -- this card holds stocks."


def _run_tradeability_check(rest_cards, mcp_cards, listing=None):
    """The check whole: REST answered from `rest_cards` (id -> tradeable_now),
    the listing from the same unless given, MCP from `mcp_cards` (id ->
    tradeable_now, or an Exception to raise)."""
    from qa.client import McpError

    check = _load("tests/mcp/test_card_tradeability_agrees_across_surfaces.py",
                  "tradeability_check_under_test")

    def card(cid, now):
        return {"id": cid, "status": "live", "tradeable_now": now,
                "trading_blocked_reason": None if now else CLOSED}

    rows = listing if listing is not None else [card(c, v) for c, v in rest_cards.items()]
    answers = {check.LIST: (200, {"cards": rows, "us_market_open": False})}
    for cid, now in rest_cards.items():
        answers[check.CARD.format(id=cid)] = (200, card(cid, now))

    class Mcp:
        def call(self, tool, args):
            said = mcp_cards[args["query"]]
            if isinstance(said, Exception):
                raise said
            return {"success": True, "result": {"cards": [
                {"id": args["query"], "status": "live", "tradeable_now": said}]}}

    check.test_a_card_is_tradeable_on_every_surface_or_on_none(Mcp(), _Rest(answers))
    return McpError


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_that_is_closed_on_rest_and_open_on_mcp_fails():
    """2026-09-22 23:20 UTC, US markets closed: 21 of 25 stock cards read
    tradeable_now false on GET /api/v1/event-cards/{id} and true through the
    get_event_card_info tool Nexus reads -- so NEX-0078 recommended a70b8d5e
    as "verified live and tradeable" when REST, the one trade gate, refused
    it. Judged only where one surface reads the card closed: with every card
    open on both, the case this is about was not exercised."""
    a, b, c = (f"{n:08x}-0000-4000-8000-000000000000" for n in (1, 2, 3))

    with pytest.raises(AssertionError, match=a[:8]):
        _run_tradeability_check({a: False, b: False}, {a: True, b: False})
    # The other direction is the same disagreement.
    with pytest.raises(AssertionError, match=b[:8]):
        _run_tradeability_check({a: False, b: True}, {a: False, b: False})

    # Agreement with a card closed on both is the gate working.
    _run_tradeability_check({a: False, b: False}, {a: False, b: False})

    # Every card open on both: the closed case was not exercised.
    with pytest.raises(Inconclusive):
        _run_tradeability_check({a: True, b: True}, {a: True, b: True})
    # A tool that cannot answer is unread, never agreement.
    from qa.client import McpError
    with pytest.raises(Inconclusive):
        _run_tradeability_check({a: False}, {a: McpError("tool error", {})})
    # A card the tool no longer returns is unread too.
    with pytest.raises(Inconclusive):
        _run_tradeability_check({c: False}, {c: None})
