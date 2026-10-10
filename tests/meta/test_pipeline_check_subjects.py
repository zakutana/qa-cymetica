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

    # B01 (deep pass of 2026-09-24, 3/3): the negation window counted words,
    # three before and four after, and missed a denial one word further off
    # while taking "not" about something else for one. The whole CLAUSE
    # before the mention is read, and after it only a denial that attaches.
    for denial in ("We do not use backtests or any pro-forma data.",
                   "Returns exclude backfilled, backtested and pro-forma figures.",
                   "The return doesn't include any pro-forma stretch.",
                   "Pro-forma months aren't used."):
        with pytest.raises(AssertionError, match="discloses no pro-forma"):
            _run_fta_check(denial)

    _run_fta_check("Return since inception includes a pro-forma period before "
                   "the first held position: today's composition applied to "
                   "past closes.")
    _run_fta_check("The return includes a pro-forma stretch, not a backtest.")
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

    # B02 (deep pass of 2026-09-24, 3/3): only the literal "try again" was a
    # retry, so a one-word rewording of the unchanged defect passed -- and
    # "don't hesitate to try again" read as a refusal to retry.
    for reworded in ("Invalid clone request. Please retry.",
                     "Invalid clone request. Please don't hesitate to try again."):
        body = {"encoding": "json", "value": {"detail": reworded}}
        with pytest.raises(AssertionError, match="asks for a retry"):
            _run_clone_check_on_captures(monkeypatch, again, {
                "ev-CLN-0017": body, "ev-CLN-0020": body})
    # A05: a refusal that names its reason and sends the caller ELSEWHERE is
    # the fix, however often it is met -- not the same retry refused again.
    elsewhere = {"encoding": "json", "value": {"detail": (
        "You already hold a paper clone of this bot. Try again with a "
        "different bot.")}}
    _run_clone_check_on_captures(monkeypatch, again, {
        "ev-CLN-0017": elsewhere, "ev-CLN-0020": elsewhere})


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
        # B04 (deep pass of 2026-09-24, 3/3): no space after -d, and the
        # `=` form -- neither judged nor counted.
        f"curl -X POST https://cymetica.com{fund} -d'{{\"x\": 1}}'",
        f"curl -X POST https://cymetica.com{fund} --data='{{\"x\": 1}}'",
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

    with pytest.raises(AssertionError, match=a[:8]) as said:
        _run_tradeability_check({a: False, b: False}, {a: True, b: False})
    # A06 (deep pass of 2026-09-24, 3/3): the docstring says the reason names
    # BOTH read times, because the pair can straddle a market open or close;
    # one time, taken before the first read, was all it carried.
    assert "REST read at" in str(said.value) and "tool read at" in str(said.value), (
        str(said.value))
    assert "can be traded that the trade gate refuses" in str(said.value)
    # The other direction is the same disagreement -- and its reason says
    # THAT direction, not the first one (deep pass 2026-09-24, A06 again).
    with pytest.raises(AssertionError, match=b[:8]) as other:
        _run_tradeability_check({a: False, b: True}, {a: False, b: False})
    assert "cannot be traded that the trade gate accepts" in str(other.value), (
        str(other.value))

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

    # The other card-state check, merged here (the tests/meta ceiling): a
    # card's index does not move further in one step than its basket can.
    # d23b4cf2 on 2026-09-25: TRX/XTZ/ENJ, +142.3 % between two points three
    # minutes apart; 97b827ad, 97 % BCH, -85.2 % in nine and a half.
    from datetime import datetime, timezone

    from tests.rest.test_a_card_index_moves_with_its_basket import (
        jumps, large_cap_share)
    # Their own ranks that day: the first version cut at 100 and never
    # judged this card, because XTZ is 133.
    alchemy = [{"symbol": "TRX", "weight": 0.4879, "market_cap_rank": 8},
               {"symbol": "XTZ", "weight": 0.472, "market_cap_rank": 133},
               {"symbol": "ENJ", "weight": 0.0402, "market_cap_rank": 448}]
    assert large_cap_share(alchemy) > 0.9
    assert large_cap_share([{"symbol": "PEPE", "weight": 1.0,
                             "market_cap_rank": 400}]) == 0.0, (
        "a small-cap basket can do what the rule forbids; it is not judged")
    assert large_cap_share([{"symbol": "X", "weight": 1.0}]) == 0.0, (
        "a leg with no rank is not large-cap by default")
    since = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
    path = [{"t": "2026-09-25T10:27:07+00:00", "index": 100.436996},
            {"t": "2026-09-25T10:30:21+00:00", "index": 243.39287},
            {"t": "2026-09-25T10:32:20+00:00", "index": 243.461983}]
    found = jumps(path, since)
    assert [j["change_pct"] for j in found] == [142.3], found
    # Before the window: history, not judged -- so a fix can show.
    assert jumps(path, datetime(2026, 9, 25, 11, 0, tzinfo=timezone.utc)) == []
    # A big move spread over a gap longer than a step is not one step.
    assert jumps([path[0], {"t": "2026-09-25T12:30:00+00:00", "index": 150.0}],
                 since) == []
    # Down counts the same as up, and the ordinary day does not. The step as
    # their thinned history served it at 14:40 -- 13 min 24 s, where the
    # first version's 15-minute limit had already missed it at 14:32.
    assert jumps([{"t": "2026-09-25T13:19:54+00:00", "index": 100.704329},
                  {"t": "2026-09-25T13:33:18+00:00", "index": 14.925121}],
                 since)[0]["change_pct"] == -85.2
    assert jumps([{"t": "2026-09-25T13:19:54+00:00", "index": 100.704329},
                  {"t": "2026-09-25T14:05:00+00:00", "index": 14.925121}],
                 since), "thinned to 45 minutes, it is still one step"
    assert jumps([{"t": "2026-09-25T13:19:54+00:00", "index": 100.0},
                  {"t": "2026-09-25T13:29:25+00:00", "index": 108.0}], since) == []
    # A history with nothing to judge is not a card that did not move: no
    # step, so the check counts it unread (deep pass 2026-09-25, A04).
    from tests.rest.test_a_card_index_moves_with_its_basket import steps
    assert steps([], since) == [] and steps([{"ts": 1, "value": 2}] * 3, since) == []
    assert len(steps(path, since)) == 2

    # And a settled card's index is its value at resolution (2026-10-10): 6fb50de3 read
    # 100.42 at its resolution_at_utc, 2026-10-08 09:06, and settled at 203.16 -- the
    # step 99.80 -> 203.23 came 26 hours after trading closed.
    from tests.rest.test_a_settled_card_stops_at_its_resolution import (
        MAX_DRIFT_PCT, drift_after_resolution)
    hist = [{"t": "2026-10-08T08:59:33+00:00", "index": 100.42},
            {"t": "2026-10-09T11:28:40+00:00", "index": 99.80316},
            {"t": "2026-10-09T11:59:14+00:00", "index": 203.233801}]
    settled = {"id": "6fb50de3", "status": "settled", "current_index": 203.162223,
               "contract_spec": {"resolution_at_utc": "2026-10-08T09:06:53.220722+00:00"}}
    seen = drift_after_resolution(settled, hist)
    assert seen["at_resolution"] == 100.42 and round(seen["drift_pct"], 1) == 102.3, seen
    assert seen["points_after"] == 2 and abs(seen["drift_pct"]) > MAX_DRIFT_PCT
    held = drift_after_resolution(dict(settled, current_index=100.5), hist)
    assert abs(held["drift_pct"]) < MAX_DRIFT_PCT, "a card that stopped at resolution was failed"
    # Unread, never agreement: no resolution time, no point near it, no current index.
    assert drift_after_resolution(dict(settled, contract_spec={}), hist) is None
    assert drift_after_resolution(settled, hist[1:]) is None, "no point at or before resolution"
    assert drift_after_resolution(settled, [{"t": "2026-10-08T04:00:00+00:00", "index": 100.0}]
                                  + hist[1:]) is None, "a point five hours before is not the close"
    assert drift_after_resolution(dict(settled, current_index=None), hist) is None

    # And the trading station's default tabs open for its default symbol (2026-10-10:
    # /api/v1/station/apps defaults to BTC with the CLOB tab, /exchange/{sym_lower}-pro, and
    # /exchange/btc-pro answered 404 -- the tab and the "Trade BTC on the CLOB" button).
    from tests.rest.test_the_station_opens_its_default_tabs import default_tab_paths
    body = {"default_symbol": "BTC", "default_tabs": ["chart", "clob", "screener", "gone"],
            "apps": [{"id": "chart", "url": "/chart-analyzer?symbol={sym}&tf=1d", "takes_symbol": True},
                     {"id": "clob", "url": "/exchange/{sym_lower}-pro", "takes_symbol": True},
                     {"id": "screener", "url": "/gem-screener", "takes_symbol": False}]}
    paths = default_tab_paths(body)
    assert paths == [("chart", "/chart-analyzer?symbol=BTC&tf=1d"), ("clob", "/exchange/btc-pro"),
                     ("screener", "/gem-screener"), ("gone", None)], paths
    assert default_tab_paths({"default_tabs": ["chart"], "apps": body["apps"]}) == [], (
        "a station with no default symbol has nothing to fill in, so nothing is judged")

    # And the backtest leaderboard's synthetic label where it lives now (#175, 2026-10-10): on the
    # trade list's own response (`is_synthetic`, `data_kind`), no longer on each trade.
    from tests.rest.test_backtest_leaderboard_ranks_backtests_on_historical_data import synthetic_in
    real = {"trades": [{"symbol": "BTC"}] * 3, "is_synthetic": False, "data_kind": "historical"}
    fake = {"trades": [{"symbol": "BTC"}] * 3, "is_synthetic": True, "data_kind": "synthetic"}
    old = {"trades": [{"symbol": "BTC", "is_synthetic": True}, {"symbol": "ETH", "is_synthetic": False}]}
    assert synthetic_in(real) == (0, True), "a list labelled historical holds no synthetic trade"
    assert synthetic_in(fake) == (3, True), "a list labelled synthetic makes every trade in it synthetic"
    assert synthetic_in(dict(fake, is_synthetic=None)) == (3, True), "data_kind alone says synthetic"
    assert synthetic_in(old) == (1, True), "the per-trade flag of 2026-10-04 is still read"
    assert synthetic_in({"trades": [{"symbol": "BTC"}]}) == (0, False), "no label anywhere is not a clean list"

    # And the account history pages forward (2026-10-10): with currency=USDC, and with no filter
    # past the first page, every offset answered the same 100 rows while has_more said true.
    from tests.rest.test_account_history_pages_forward import page_repeats
    first = [{"id": i} for i in range(100)]
    assert page_repeats(first, first, has_more=True) is True, "the same page again was read as the next one"
    assert page_repeats(first, [{"id": i} for i in range(100, 200)], has_more=True) is False
    assert page_repeats(first, [{"id": i} for i in range(50, 150)], has_more=True) is False, (
        "an overlap from a row added between reads is not a repeat")
    assert page_repeats(first, first, has_more=False) is None, "no next page was promised"
    assert page_repeats([], [], has_more=True) is None, "an empty first page has nothing to repeat"

    # And a fund's: the launcher's paper-only sentence and a profile's live
    # invest offer, read from what a visitor sees -- the markup as served on
    # 2026-09-25, tags and a comment in the way.
    from tests.mcp.test_community_funds_are_paper_or_live_not_both import (
        launcher_says_paper_only, offers_live_invest, visible_text)
    launcher = ('<h4>Community funds</h4><!-- note --><p>Paper trading only</p>'
                '<p>The index, terminal and management are real-time. '
                'Buying in is simulated.</p>')
    assert launcher_says_paper_only(visible_text(launcher))
    assert not launcher_says_paper_only(visible_text(
        "<h4>Community funds</h4><p>Take real USDC.</p>")), "a corrected launcher"
    profile = '<a href="/fund/apply?invest=X">Invest in 8830Dfe9 now &mdash; it&#39;s LIVE &rarr;</a>'
    assert offers_live_invest(visible_text(profile)) == "Invest in 8830Dfe9 now — it's LIVE"
    assert offers_live_invest(visible_text("<p>Paper fund. Buy in (simulated).</p>")) is None
    assert offers_live_invest(visible_text("<!-- Invest in X now, it's LIVE -->")) is None, (
        "a comment is not what a visitor reads")

    # And the leaderboard against list_funds, read off the row markup served
    # on 2026-09-25.
    from tests.mcp.test_fund_performance_page_matches_the_api import (
        disagreements, rows_of)
    def tr(rank, name, sleeve, status, index, ret):
        return (f'<tr class="{status}"><td class="rk">{rank:02d}</td>'
                f'<td class="fund"><a href="/x">{name}</a></td>'
                f'<td class="sleeve">{sleeve}<span class="dir">long</span></td>'
                f'<td class="status"><span class="st {status}">{status}</span></td>'
                f'<td class="num" id="fp-x-rk-index">${index}</td>'
                f'<td class="num" id="fp-x-rk-return"><span class="pos">{ret}%</span></td></tr>')
    page = (tr(1, "Privacy", "Community AIB", "live", "154.02", "+121.83")
            + tr(2, "M&amp;A Ripple Fund", "M&amp;A Ripple", "live", "115.98", "+15.98")
            + tr(3, "Power", "Managed AIB", "live", "0.01", "+3.17"))
    rows = rows_of(page)
    assert [r["name"] for r in rows] == ["Privacy", "M&A Ripple Fund", "Power"]
    api = [{"name": "Privacy", "sleeve": "Community AIB", "status": "live",
            "index_price_usd": 154.018645, "return_since_inception_pct": 121.83},
           {"name": "M&A Ripple Fund", "sleeve": "M&A Ripple", "status": "live",
            "index_price_usd": 115.978, "return_since_inception_pct": 15.98},
           {"name": "Power", "sleeve": "Managed AIB", "status": "live",
            "index_price_usd": 0.01031653, "return_since_inception_pct": 3.17}]
    assert disagreements(rows, api) == [], "a cent of rounding is not a disagreement"
    moved = [dict(api[0], index_price_usd=160.0)] + api[1:]
    assert any("index" in d for d in disagreements(rows, moved))
    # A figure on one side only disagrees too (deep pass 2026-09-25, A08).
    unpriced = [dict(api[0], index_price_usd=None)] + api[1:]
    assert any("index" in d for d in disagreements(rows, unpriced)), \
        "the page's $154.02 over an API null passed"
    extra = api + [{"name": "Hidden", "sleeve": "Managed AIB", "status": "live",
                    "index_price_usd": 1.0, "return_since_inception_pct": 50.0}]
    assert any("not on the page" in d for d in disagreements(rows, extra))
    assert any("order" in d for d in disagreements(list(reversed(rows)), api))
    # FTA Fund -- Stocks: no profile link and no ids on its cells. The first
    # version read those by id, missed the row, and reported the fund absent.
    fta = ('<tr class="standing"><td class="rk">17</td><td class="fund">FTA Fund — Stocks</td>'
           '<td class="sleeve">FTA<span class="dir">short</span></td>'
           '<td class="status"><span class="st standing">standing</span></td>'
           '<td class="num">$187.31</td><td class="num"><span class="neg">-2.30%</span></td></tr>')
    (row,) = rows_of(fta)
    assert (row["name"], row["status"], row["index"], row["return"]) == (
        "FTA Fund — Stocks", "standing", 187.31, -2.3), row
    # 2026-09-26: after their ET-27387 the index cell is `td.num.idx`. The
    # first version matched class="num" exactly, missed it and read the
    # RETURN as the index -- 53 false disagreements on 27 rows.
    idx = ('<tr class="live"><td class="rk">01</td><td class="fund"><a href="/x">Privacy</a></td>'
           '<td class="sleeve">Community AIB<span class="dir">long</span></td>'
           '<td class="status"><span class="st live">live</span></td>'
           '<td class="num idx" id="fp-x-rk-index">$152.50</td>'
           '<td class="num" id="fp-x-rk-return"><span class="pos">+119.65%</span></td></tr>')
    (row,) = rows_of(idx)
    assert (row["index"], row["return"]) == (152.5, 119.65), row

    # And what their pages read: a template stays a template, an action is
    # never a candidate, plumbing is not, and a templated doc path covers it.
    from tests.discovery.test_public_page_reads_are_documented import (
        called_paths, candidates, documented_patterns)
    js = ('fetch("/api/v1/fta-fund/history"); fetch(`/api/v1/aib/${sym}/buy`);'
          ' fetch("/api/v1/btc-pool/enter"); fetch("/api/v1/rst/csrf-token");'
          ' fetch("/api/v1/event-cards/abc/index-history"); fetch("/api/v1/headlines/")')
    names = called_paths(js)
    assert "/api/v1/aib/{x}/buy" in names and "/api/v1/headlines" in names
    doc = documented_patterns({"paths": {"/api/v1/event-cards/{card_id}/index-history": {}}})
    assert candidates(names, doc) == ["/api/v1/fta-fund/history", "/api/v1/headlines"]
    # A rate limit or a 5xx is no answer about a path, never a refusal
    # (deep pass 2026-09-25, A02).
    from types import SimpleNamespace

    from tests.discovery.test_public_page_reads_are_documented import _unanswered
    assert [_unanswered(SimpleNamespace(status_code=s)) for s in (429, 503, 401, 404, 200)] \
        == [True, True, False, False, False]


# ------------------------------------ a filed report is answered as filed -

def _filed(key, minute, status, then_created=None, day="2026-09-24"):
    """One submission as submit.py journals it: intent, outcome, and -- when
    the POST said 5xx and the report exists anyway -- the reconciled one.
    After their fix of #123 (2026-09-23 02:41 UTC) unless `day` says not."""
    at = f"{day}T10:{minute:02d}:00+00:00"
    rows = [{"type": "filing_intent", "key": key, "at": at}]
    if status >= 500:
        rows.append({"type": "filing_outcome", "key": key, "http_status": status,
                     "outcome": "unknown", "report_id": None, "at": at})
        if then_created:
            rows.append({"type": "filing_outcome", "key": key, "outcome": "accepted",
                         "report_id": then_created, "reconciled_from": "my-reports",
                         "at": at})
    else:
        rows.append({"type": "filing_outcome", "key": key, "http_status": status,
                     "outcome": "accepted", "report_id": 100 + minute, "at": at})
    return rows


def _run_filing_check(monkeypatch, events):
    check = _load("tests/rest/test_a_filed_report_is_answered_as_filed.py",
                  "filed_report_check_under_test")
    monkeypatch.setattr(check, "read_events", lambda: events)
    check.test_a_report_the_server_creates_is_answered_as_created()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_report_created_behind_a_500_fails_and_a_clean_run_of_twelve_passes(
        monkeypatch):
    """#110, #113 and #122: POST /api/v1/bounty/reports answered HTTP 500 and
    the report existed anyway, found only by reconciling against my-reports.
    Three of about thirteen, so it is intermittent: judged over the newest
    twelve submissions, a masked success among them fails, twelve clean ones
    pass, fewer and none masked is not enough to say."""
    clean = [row for n in range(12) for row in _filed(f"k{n}", n, 200)]
    masked = _filed("k-late", 30, 500, then_created=122)

    with pytest.raises(AssertionError, match="122"):
        _run_filing_check(monkeypatch, clean + masked)
    _run_filing_check(monkeypatch, masked + [
        row for n in range(12) for row in _filed(f"k{n}", 40 + n, 200)])
    with pytest.raises(Inconclusive):
        _run_filing_check(monkeypatch, clean[:10])
    # A 500 whose report does NOT exist is an honest failure, not this defect.
    honest = _filed("k-down", 30, 500)
    with pytest.raises(Inconclusive):
        _run_filing_check(monkeypatch, clean[:20] + honest)
    # B06 (deep pass of 2026-09-24, 3/3): ...and sent again under the same
    # key, answered 201 with its id. The first status and the last id made
    # "500 and created anyway" out of two honest answers -- a false fail on a
    # FIX_CLAIMED row. Masked is a 5xx whose report RECONCILING found.
    resent = honest + [{"type": "filing_intent", "key": "k-down",
                        "at": "2026-09-22T10:31:00+00:00"},
                       {"type": "filing_outcome", "key": "k-down", "http_status": 201,
                        "outcome": "accepted", "report_id": 131,
                        "at": "2026-09-22T10:31:00+00:00"}]
    # Not the defect; and a 500 among the newest twelve is not a clean
    # twelve either, so it waits rather than failing.
    with pytest.raises(Inconclusive):
        _run_filing_check(monkeypatch, clean + resent)

    # 2026-09-25: their record of #123 says fixed_at 2026-09-23T02:41:50
    # ("Fixed in 3299e580b, live"), and the window still held #122 from the
    # night before, so the row read "still fails" on evidence older than the
    # fix. What came before the fix is history, named and never judged.
    before = _filed("k-old", 55, 500, then_created=122, day="2026-09-22")
    _run_filing_check(monkeypatch, before + clean)
    with pytest.raises(Inconclusive, match="122"):
        _run_filing_check(monkeypatch, before + clean[:10])
    # ...while one after it still fails, however many clean ones surround it.
    with pytest.raises(AssertionError, match="123"):
        _run_filing_check(monkeypatch, before + clean + _filed(
            "k-new", 50, 500, then_created=123))


# --------------------------- a paper buy is judged against the paper book ---

PRIV = "5d91bf43-a597-47b0-9abe-5c7f52618bbd"
OTHER = "30015006-abff-44b6-bdb0-f659faf4f3f4"
SHORT = '{"detail": "Insufficient USDC balance: you have 7.650006."}'


def _paper_buy(trade_id, card, at, status, response="", *, sim="88598.91",
               mode=True, paper=True, usdc=480.36, tradeable=True,
               before=True):
    intent = {"id": trade_id, "type": "intent", "card_id": card, "usdc": usdc,
              "paper": paper, "at": f"2026-09-23T{at}+00:00",
              "body": {"amount_usdc": usdc, "paper": paper},
              "card_before": {"tradeable_now": tradeable,
                              "trading_blocked_reason":
                                  None if tradeable else "market closed"}}
    if before:
        intent["before"] = {"simulation_mode": mode, "sim_balance_usdc": sim}
    return [intent, {"id": trade_id, "type": "outcome", "http_status": status,
                     "outcome": "accepted" if status == 200 else "unknown",
                     "response": response, "evidence_id": trade_id.lower()}]


def _run_paper_book_check(monkeypatch, rows):
    check = _load("tests/rest/test_a_paper_buy_is_judged_against_the_paper_book.py",
                  "paper_book_check_under_test")
    monkeypatch.setattr(check, "_paper", lambda: type("P", (), {
        "load": staticmethod(lambda: rows)})())
    check.test_a_paper_buy_is_not_refused_for_money_the_paper_book_holds()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_paper_buy_refused_for_a_balance_it_is_not_spending_fails(monkeypatch):
    """2026-09-23 05:59 and 06:00 UTC: a paper buy of 480.36 on AIB-Privacy
    (tradeable_now true), account in simulation_mode with 88,598.91 paper
    USDC, came back 409 "Insufficient USDC balance: you have 7.650006." twice,
    while a paper buy of another card a minute later was accepted. The
    subject is every card refused that way, by its newest buy -- another
    card's accepted buy is not the fix (A01's lesson, #117)."""
    rows = (_paper_buy("TRD-0039", PRIV, "05:59:13", 409, SHORT)
            + _paper_buy("TRD-0040", PRIV, "06:00:24", 409, SHORT)
            + _paper_buy("TRD-0041", OTHER, "06:01:16", 200, usdc=5.0))
    with pytest.raises(AssertionError, match=PRIV) as failed:
        _run_paper_book_check(monkeypatch, rows)
    assert "7.650006" in str(failed.value) and "88598.91" in str(failed.value), (
        str(failed.value))

    # A buy of the refused card that lands is the fix.
    _run_paper_book_check(monkeypatch, rows + _paper_buy(
        "TRD-0050", PRIV, "09:00:00", 200))
    # A04 (deep pass of 2026-09-24, 3/3): ...when it is bigger than the
    # balance the refusal quoted. A 5 USDC buy the wrong 7.65 also covers
    # lands whether or not they fixed anything, and passed as the fix.
    with pytest.raises(Inconclusive):
        _run_paper_book_check(monkeypatch, rows + _paper_buy(
            "TRD-0052", PRIV, "09:00:00", 200, usdc=5.0))

    # Short on paper too: the refusal is true, not this defect.
    with pytest.raises(Inconclusive):
        _run_paper_book_check(monkeypatch, _paper_buy(
            "TRD-1", PRIV, "05:59:13", 409, SHORT, sim="300.00"))
    # A card shut at the buy, a live account, a live order, or a buy with no
    # book recorded before it: nothing about the paper book can be read.
    for shape in ({"tradeable": False}, {"mode": False}, {"paper": False},
                  {"before": False}):
        with pytest.raises(Inconclusive):
            _run_paper_book_check(monkeypatch, _paper_buy(
                "TRD-1", PRIV, "05:59:13", 409, SHORT, **shape))
    # No buy ever refused for balance: nothing to judge, never a pass.
    with pytest.raises(Inconclusive):
        _run_paper_book_check(monkeypatch,
                              _paper_buy("TRD-0041", OTHER, "06:01:16", 200))
    # A different refusal on the newest buy of the struck card is unmeasured.
    with pytest.raises(Inconclusive):
        _run_paper_book_check(monkeypatch, rows + _paper_buy(
            "TRD-0051", PRIV, "09:00:00", 409,
            '{"detail": "New purchases are closed for this index."}'))
