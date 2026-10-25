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

Every expected FAIL and every expected pass sits inside `verdict_due()` (deep pass 2026-10-25,
C01): an Inconclusive there slips past `pytest.raises(AssertionError)` and is recorded as a SKIP,
and in the test that hosts the `_the_*_readings()` helpers it skipped every reading after it.
tests/repo/test_meta_verdicts_fail_on_inconclusive.py replays each site with one injected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import Inconclusive, SafetyTier, qa, verdict_due

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
    with verdict_due(), pytest.raises(AssertionError, match=A):
        _run_buy_check(monkeypatch, rows, {A: _card(True), B: _card(True)})

    # A buy of A itself that lands is the fix.
    fixed = rows + _buy("TRD-4", A, "17:20:00", 200, "accepted")
    with verdict_due():
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
    with verdict_due(), pytest.raises(AssertionError, match=A):
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
    with verdict_due(), pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Return is measured since the fund's own inception from "
                       "real market prices -- nothing backfilled, no pro-forma, "
                       "no backtest.")
    with verdict_due(), pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Returns are never pro forma: nothing backfilled.")
    # A02, deep pass of 2026-09-22: "nothing" was not a negation, so the
    # denial their page could write next passed as a disclosure.
    with verdict_due(), pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Measured since inception: nothing backfilled or "
                       "pro-forma.")
    with verdict_due(), pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Neither backfilled nor pro-forma.")
    # C07, deep pass of 2026-09-22 evening (3/3): a negation AFTER the word
    # denies it just as well, and read as a disclosure.
    for denial in ("Measured since inception; nothing backfilled; pro-forma "
                   "periods are excluded.",
                   "Pro-forma figures are never used; nothing backfilled.",
                   "Returns exclude any pro-forma stretch."):
        with verdict_due(), pytest.raises(AssertionError, match="discloses no pro-forma"):
            _run_fta_check(denial)

    # B01 (deep pass of 2026-09-24, 3/3): the negation window counted words,
    # three before and four after, and missed a denial one word further off
    # while taking "not" about something else for one. The whole CLAUSE
    # before the mention is read, and after it only a denial that attaches.
    for denial in ("We do not use backtests or any pro-forma data.",
                   "Returns exclude backfilled, backtested and pro-forma figures.",
                   "The return doesn't include any pro-forma stretch.",
                   "Pro-forma months aren't used."):
        with verdict_due(), pytest.raises(AssertionError, match="discloses no pro-forma"):
            _run_fta_check(denial)

    with verdict_due():
        _run_fta_check("Return since inception includes a pro-forma period before "
                       "the first held position: today's composition applied to "
                       "past closes.")
    with verdict_due():
        _run_fta_check("The return includes a pro-forma stretch, not a backtest.")
    # A negation in the sentence before is not a denial of this one.
    with verdict_due():
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
    with verdict_due(), pytest.raises(AssertionError, match="Please try again"):
        _run_clone_check(monkeypatch, rows, twice)
    # Another species cloned AFTER it is not the fix.
    later = rows + _cloned("CLN-0021", RSI, "18:00:00", 200, "accepted")
    with verdict_due(), pytest.raises(AssertionError, match=PCPN):
        _run_clone_check(monkeypatch, later, twice)

    # Refused once, never retried: the advice has not been tested.
    with pytest.raises(Inconclusive):
        _run_clone_check(monkeypatch, rows[:4], {"CLN-0017": AGAIN})

    # A capture that cannot be read is unmeasured, not an empty body.
    with pytest.raises(Inconclusive):
        _run_clone_check(monkeypatch, rows, {"CLN-0017": AGAIN})

    # A refusal with nothing in it fails on its own.
    with verdict_due(), pytest.raises(AssertionError, match="no detail"):
        _run_clone_check(monkeypatch, rows, {"CLN-0017": AGAIN, "CLN-0020": {}})

    # The fixes: the clone is made, or the refusal names its reason.
    made = rows + _cloned("CLN-0030", PCPN, "18:30:00", 200, "accepted")
    with verdict_due():
        _run_clone_check(monkeypatch, made, twice)
    named = rows + _cloned("CLN-0031", PCPN, "18:40:00", 409, "rejected")
    with verdict_due():
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
    # guard, not a red one: verdict_due fails it here (an empty refusal read
    # as an unreadable capture).
    with verdict_due(), pytest.raises(AssertionError, match="no detail") as silent:
        _run_clone_check_on_captures(monkeypatch, one, {
            "ev-CLN-0017": {"encoding": "empty", "value": None}})
    assert "asks for a retry" not in str(silent.value), str(silent.value)

    # A capture that is not there is still unmeasured, not an empty body.
    with pytest.raises(Inconclusive):
        _run_clone_check_on_captures(monkeypatch, one, {})

    # A reason under their own error envelope is a reason.
    with verdict_due():
        _run_clone_check_on_captures(monkeypatch, one, {
            "ev-CLN-0017": {"encoding": "json", "value": {"error": {
                "code": "CLONE_LIMIT", "message": "one paper clone per species"}}}})

    # A refusal that tells the caller NOT to try again does not ask for one,
    # retried or not.
    again = one + _cloned("CLN-0020", PCPN, "17:47:14", 400, "rejected")
    told = {"encoding": "json", "value": {
        "detail": "You already hold a paper clone of this species; do not try again."}}
    with verdict_due():
        _run_clone_check_on_captures(monkeypatch, again, {
            "ev-CLN-0017": told, "ev-CLN-0020": told})

    # And the defect as captured still fails, retry sentence and all.
    asked = {"encoding": "json", "value": AGAIN}
    with verdict_due(), pytest.raises(AssertionError, match="asks for a retry"):
        _run_clone_check_on_captures(monkeypatch, again, {
            "ev-CLN-0017": asked, "ev-CLN-0020": asked})

    # B02 (deep pass of 2026-09-24, 3/3): only the literal "try again" was a
    # retry, so a one-word rewording of the unchanged defect passed -- and
    # "don't hesitate to try again" read as a refusal to retry.
    for reworded in ("Invalid clone request. Please retry.",
                     "Invalid clone request. Please don't hesitate to try again."):
        body = {"encoding": "json", "value": {"detail": reworded}}
        with verdict_due(), pytest.raises(AssertionError, match="asks for a retry"):
            _run_clone_check_on_captures(monkeypatch, again, {
                "ev-CLN-0017": body, "ev-CLN-0020": body})
    # A05: a refusal that names its reason and sends the caller ELSEWHERE is
    # the fix, however often it is met -- not the same retry refused again.
    elsewhere = {"encoding": "json", "value": {"detail": (
        "You already hold a paper clone of this bot. Try again with a "
        "different bot.")}}
    with verdict_due():
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
    with verdict_due(), pytest.raises(AssertionError, match="source_type"):
        _run_docs_check(bad)

    good = _page(_curl("/api/v1/cloned-bots/clone",
                       '{"source_type": "wta_species", "source_id": "s1", '
                       '"paper": true}'),
                 _curl("/api/v1/cloned-bots/abc/fund", '{"amount": 1}'))
    with verdict_due():
        _run_docs_check(good)

    # A missing field on the templated route is found as well.
    with verdict_due(), pytest.raises(AssertionError, match="amount"):
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


def _run_tradeability_check(rest_cards, mcp_cards, listing=None, reason=CLOSED):
    """The check whole: REST answered from `rest_cards` (id -> tradeable_now),
    the listing from the same unless given, MCP from `mcp_cards` (id ->
    tradeable_now, or an Exception to raise); a closed card says `reason`."""
    from qa.client import McpError

    check = _load("tests/mcp/test_card_tradeability_agrees_across_surfaces.py",
                  "tradeability_check_under_test")

    def card(cid, now):
        return {"id": cid, "status": "live", "tradeable_now": now,
                "trading_blocked_reason": None if now else reason}

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

    with verdict_due(), pytest.raises(AssertionError, match=a[:8]) as said:
        _run_tradeability_check({a: False, b: False}, {a: True, b: False})
    # A06 (deep pass of 2026-09-24, 3/3): the docstring says the reason names
    # BOTH read times, because the pair can straddle a market open or close;
    # one time, taken before the first read, was all it carried.
    assert "REST read at" in str(said.value) and "tool read at" in str(said.value), (
        str(said.value))
    assert "can be traded that the trade gate refuses" in str(said.value)
    # The other direction is the same disagreement -- and its reason says
    # THAT direction, not the first one (deep pass 2026-09-24, A06 again).
    with verdict_due(), pytest.raises(AssertionError, match=b[:8]) as other:
        _run_tradeability_check({a: False, b: True}, {a: False, b: False})
    assert "cannot be traded that the trade gate accepts" in str(other.value), (
        str(other.value))

    # Agreement with a card closed on both is the gate working.
    with verdict_due():
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
    # Deep pass 2026-10-11, A02: the two guards behind a pass, each reached. Two cards closed on
    # both and a third unread is no pass (every single-card case above raised before the guard);
    # and while US markets are shut, cards closed only by their date never exercised the gate.
    with pytest.raises(Inconclusive, match="could not be read"):
        _run_tradeability_check({a: False, b: False, c: False}, {a: False, b: False, c: McpError("x", {})})
    with pytest.raises(Inconclusive, match="market-hours gate"):
        _run_tradeability_check({a: False, b: False}, {a: False, b: False},
                                reason="This card's window has ended.")

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
    # #181 answered (ET-30731, 2026-10-10): the catalogue still carries the one -pro template, but
    # now publishes `clob_symbols` and `clob_fallback`, and the page sends a symbol outside the list
    # to the fallback. Read the rule they publish, or the check keeps failing a defect they fixed.
    ruled = dict(body, clob_symbols=["ET10", "SBIO"], clob_fallback="/exchange?q={sym}")
    assert dict(default_tab_paths(ruled))["clob"] == "/exchange?q=BTC", (
        "a symbol outside clob_symbols opens the published fallback, not the -pro terminal")
    assert dict(default_tab_paths(dict(ruled, default_symbol="ET10")))["clob"] == "/exchange/et10-pro", (
        "a symbol the CLOB lists still opens its own terminal")
    assert dict(default_tab_paths(dict(body, clob_symbols=["ET10"])))["clob"] == "/exchange/btc-pro", (
        "a list with no fallback published leaves the template, so the 404 is still seen")
    assert dict(default_tab_paths(dict(ruled, clob_symbols=[])))["clob"] == "/exchange?q=BTC", (
        "an empty list is a list: no symbol has a terminal")
    assert dict(default_tab_paths(dict(ruled, default_symbol="btc")))["clob"] == "/exchange?q=btc", (
        "the symbol is matched as the page matches it, exactly")
    assert dict(default_tab_paths(ruled))["chart"] == "/chart-analyzer?symbol=BTC&tf=1d", (
        "only the CLOB tab has a fallback")

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

    # And a coin's supply figures on its Crypto dashboard (2026-10-11), held as a helper below
    # rather than a test of its own: tests/meta has a counted ceiling.
    _the_crypto_supply_readings()

    # And the launchpad token lists (2026-10-11), held the same way.
    _the_launchpad_list_readings()

    # And the four checks of the afternoon of 2026-10-11 (/movers, the clone summary line, the
    # Agent Tournaments routes in the OpenAPI, the idea template after a BB-CHANGE), the same way.
    _the_movers_page_readings()
    _the_clone_summary_readings()
    _the_tournament_route_readings()
    _the_idea_template_readings()

    # And the two Build it Better documentation checks of the evening of 2026-10-11 (the routes
    # llms.txt names against the OpenAPI, the place it gives for the request token), the same way.
    _the_build_it_better_route_readings()
    _the_request_token_place_readings()

    # And the bots Agent Tournaments offers for a seat (the evening of 2026-10-11), the same way.
    _the_tournament_bot_readings()

    # And whether a table knows the seats our key owns (2026-10-15, ET-31459), the same way.
    _the_tournament_own_seat_readings()

    # And Build a Company's charter cap and heartbeat (2026-10-15, ET-31466), the same way.
    _the_company_charter_cap_readings()
    _the_company_heartbeat_readings()

    # And the Agent Tournaments link preview's title (#217, repaired 2026-10-23), the same way.
    _the_link_preview_title_readings()

    # And a free Agent Tournaments table at each buy-in (2026-10-12), the same way.
    _the_free_table_readings()

    # And the Build a Company routes in the OpenAPI (2026-10-12), the same way.
    _the_company_route_readings()

    # And #93's documented GETs, read against the auth note on their own line (2026-10-25).
    _the_documented_get_auth_note_readings()

    # And the cards our OPEN positions point at (2026-10-25), the same way.
    _the_open_position_card_readings()

    # And a clone's perpetual markets against the live 5-minute markets (2026-10-13).
    from tests.rest.test_a_clone_trades_only_live_epoch_markets import dead_markets, live_symbols
    live = live_symbols({"markets": [{"symbol": s} for s in
                                     ("BTC", "ETH", "NVDA", "AAPL", "GOOG", "VAIX", "SBIO")]})
    nine = ["BTC", "ETH", "VAIX", "SBIO", "ET10", "ETLP", "CYM42", "TBIG", "TBIGS"]
    assert dead_markets(nine, live) == ["ET10", "ETLP", "CYM42", "TBIG", "TBIGS"]
    assert dead_markets(["BTC", "NVDA"], live) == []
    assert live_symbols({"markets": []}) == [] and live_symbols(None) == [], "no list is unread"
    assert live_symbols({"markets": [{"symbol": "btc"}, {"price": 1}]}) == ["BTC"]

    # And the account history pages forward (2026-10-10): with currency=USDC, and with no filter
    # past the first page, every offset answered the same 100 rows while has_more said true.
    from tests.rest.test_account_history_pages_forward import page_repeats
    first = [{"id": i} for i in range(100)]
    assert page_repeats(first, first, has_more=True) is True, "the same page again was read as the next one"
    assert page_repeats(first, [{"id": i} for i in range(100, 200)], has_more=True) is False
    assert page_repeats(first, [{"id": i} for i in range(99, 199)], has_more=True) is False, (
        "an overlap of one row, added between the reads, is not a repeat")
    assert page_repeats(first, first, has_more=False) is None, "no next page was promised"
    assert page_repeats([], [], has_more=True) is None, "an empty first page has nothing to repeat"
    # Deep pass 2026-10-10, B02: the captured defect with one row added between the reads
    # (99 of 100 ids again) is still a repeat, and so is an empty page that has_more promised.
    assert page_repeats(first, [{"id": 999}] + first[:99], has_more=True) is True, "99 of 100 again"
    assert page_repeats(first, [], has_more=True) is True, "has_more promised rows that never came"

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

    with verdict_due(), pytest.raises(AssertionError, match="122"):
        _run_filing_check(monkeypatch, clean + masked)
    with verdict_due():
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
    with verdict_due():
        _run_filing_check(monkeypatch, before + clean)
    with pytest.raises(Inconclusive, match="122"):
        _run_filing_check(monkeypatch, before + clean[:10])
    # ...while one after it still fails, however many clean ones surround it.
    with verdict_due(), pytest.raises(AssertionError, match="123"):
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
    with verdict_due(), pytest.raises(AssertionError, match=PRIV) as failed:
        _run_paper_book_check(monkeypatch, rows)
    assert "7.650006" in str(failed.value) and "88598.91" in str(failed.value), (
        str(failed.value))

    # A buy of the refused card that lands is the fix.
    with verdict_due():
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


def _the_crypto_supply_readings():
    """The readings behind the Crypto dashboard supply check (2026-10-11): HBAR, IOTA and ICP as
    captured fail it, a coin whose circulating supply was withheld does not, and a figure within
    the stated tolerances is not a defect."""
    from tests.rest.test_a_coins_supply_figures_can_all_be_true import supply_contradiction

    hbar = {"price": 0.0923, "market_cap": 4059900322.0, "fdv": 92275172.36,
            "circulating_supply": 43997753873.97, "total_supply": 50000000000.0,
            "max_supply": 1000000000.0, "pct_issued": 1.0, "flags": []}
    broken = supply_contradiction(hbar)
    assert set(broken) == {"circulating_over_max", "total_over_max", "fdv_under_market_cap"}, broken
    assert broken["circulating_over_max"] == 43.998 and broken["total_over_max"] == 50.0
    icp = {"market_cap": 1725493408.0, "fdv": 1452611805.4, "circulating_supply": 557358242.9,
           "total_supply": 555123004.0, "max_supply": 469213710.0, "flags": []}
    assert set(supply_contradiction(icp)) == {"circulating_over_max", "total_over_max", "fdv_under_market_cap"}
    iota = {"market_cap": 221428838.0, "fdv": 142733838.9, "circulating_supply": 4311998930.6,
            "total_supply": 4831556199.0, "max_supply": 2779530283.0, "flags": []}
    assert "fdv_under_market_cap" in supply_contradiction(iota)

    # CHZ has the same relation as ICP and IS withheld: the dashboard already knows, nothing to judge.
    chz = {"market_cap": 163492876.0, "fdv": 137708331.5, "circulating_supply": None,
           "total_supply": 9444481889.0, "max_supply": 8888888888.0, "flags": ["circulating_supply"]}
    assert supply_contradiction(chz) is None, "a withheld circulating supply was judged"

    # ETH: FDV 1.5% under the market cap because its total is net of burns; inside the tolerance.
    eth = {"market_cap": 306623046415.0, "fdv": 301871251577.0, "circulating_supply": 122124805.0,
           "total_supply": 120232214.0, "max_supply": None, "flags": []}
    assert supply_contradiction(eth) is None, "ETH's 1.5% was read as a defect"
    # A max a hair under the total (GRT, 0.03%) is rounding between two reads, not a contradiction.
    grt = {"market_cap": 1e9, "fdv": 1.2e9, "circulating_supply": 9e9, "total_supply": 10799706720.0,
           "max_supply": 10796188903.0, "flags": []}
    assert supply_contradiction(grt) is None
    # No maximum, nothing missing is a number: not judged, never a pass by guessing.
    assert supply_contradiction({"market_cap": 1e9, "fdv": 1.1e9, "total_supply": 5e9, "flags": []}) is None
    assert supply_contradiction({"market_cap": None, "fdv": None, "max_supply": 1e9, "total_supply": 5e9,
                                 "flags": []}) == {"total_over_max": 5.0}
    assert supply_contradiction(None) is None
    # Deep pass 2026-10-11, B03: a 200 without the figures is not a dashboard judged, and a second
    # look that could not read the coin leaves the first look's contradiction standing, unsettled.
    from tests.rest.test_a_coins_supply_figures_can_all_be_true import judgeable, second_look

    assert judgeable(hbar) and judgeable(eth), "a coin with two figures of a relation is judged"
    assert not judgeable(None) and not judgeable({"flags": []}), "a renamed `stats` counted as judged"
    assert not judgeable(chz), "a withheld coin is not judged"
    assert second_look(hbar) == "confirmed" and second_look(eth) == "cleared"
    assert second_look(None) == "unread", "a failed second read cleared the first look's contradiction"


def _the_launchpad_list_readings():
    """The readings behind the two launchpad list checks (2026-10-11): an unfiltered token list that
    is a 200 with no rows while a chain lists some fails, a 422 or any row passes, a read that is
    not a 200 is not judged; a discovery feed that lists a launch the REST list keeps internal fails,
    one that lists only public launches or an address in neither list does not."""
    from tests.rest.test_launchpad_discovery_tool_hides_what_rest_keeps_internal import leaked_internal
    from tests.rest.test_launchpad_tokens_list_without_a_chain_is_not_empty import empty_while_filtered_lists

    named = {4663: 1, 5042: 5}
    assert empty_while_filtered_lists(200, [], named) is True, "200 [] beside a chain that lists launches"
    assert empty_while_filtered_lists(200, [{"address": "0x1"}], named) is False
    assert empty_while_filtered_lists(422, {"detail": "chain_id required"}, named) is False, (
        "an honest refusal that names the parameter is not an empty list")
    assert empty_while_filtered_lists(500, None, named) is None and empty_while_filtered_lists(200, {}, named) is None
    assert empty_while_filtered_lists(200, [], {4663: 0, 5042: 0}) is None, "no chain lists anything: nothing to compare"

    public, internal = ["0xRUG"], ["0xRUG", "0xNXTEST", "0xGTEST"]
    assert leaked_internal(["0xrug", "0xNXTEST", "0xgtest"], public, internal) == ["0xgtest", "0xnxtest"]
    assert leaked_internal(["0xRUG"], public, internal) == [], "the public launch is the feed's to list"
    assert leaked_internal(["0xYOUNG"], public, internal) == [], "an address in neither list is not judged"
    assert leaked_internal([], public, internal) == []
    # Deep pass 2026-10-11: a 422 that names something else never measured the no-chain answer (C08);
    # a leak the second look could not read is unsettled, not cleared (C06, rule 8).
    assert empty_while_filtered_lists(422, {"detail": [{"loc": ["query", "limit"], "msg": "<= 20"}]},
                                      named) is None, "a 422 for another parameter was read as the honest refusal"
    from tests.rest.test_launchpad_discovery_tool_hides_what_rest_keeps_internal import settle

    first = {4663: {"leaked": ["0xnxtest"]}, 5042: {"leaked": []}}
    assert settle(first, {}) == ({}, [4663]), "a second look that read nothing cleared the first look's leak"
    assert settle(first, {4663: {"leaked": ["0xnxtest"]}}) == ({4663: {"leaked": ["0xnxtest"]}}, [])
    assert settle(first, {4663: {"leaked": []}}) == ({}, []), "gone on the second read: a moment, not a leak"


def _the_movers_page_readings():
    """The readings behind the /movers check (2026-10-11): the script's one request for 100 cards
    is read as one page, a request built to page through the listing is unread (C05, 2026-10-18),
    and a card of the true top ten that the page never reads is named on its board."""
    from tests.rest.test_movers_page_ranks_every_card import board_script, card_requests, outside_the_page

    script = ("var el = document.getElementById('pm-gainers'); function load() { var cards = "
              "fetch('/api/v1/event-cards/?limit=100', { credentials: 'same-origin' }).then(function (r) {});")
    page = f"<html><script>var x = 1;</script><script>{script}</script></html>"
    assert board_script(page) == script, "the board's script is found by its element id"
    assert board_script("<script>fetch('/api/v1/event-cards/')</script>") is None
    assert card_requests(script) == (["/api/v1/event-cards/?limit=100"], False)
    assert card_requests("fetch('/api/v1/event-cards/?limit=100&offset=' + off, {})")[1] is True, (
        "a request built per offset pages through the listing")
    assert card_requests("fetch(`/api/v1/event-cards/?limit=100&offset=${o}`)")[1] is True
    assert card_requests("fetch('/api/v1/movers/products')") == ([], False), "another source is not read"
    # Deep pass 2026-10-11, C07: paging is an offset whose value is built, not a URL that looks like one.
    assert card_requests("fetch('/api/v1/event-cards/?limit=100&offset=0')")[1] is False, (
        "a literal offset 0 is still one page")
    assert card_requests("fetch('/api/v1/event-cards/?limit=' + n)")[1] is None, (
        "a URL built some other way: which cards it reads cannot be read from the text")
    # C05, deep pass 2026-10-18: a built offset passed when the script held `total`, `next` or
    # `.length <` anywhere -- a fixed two-page loop beside an unrelated `total` passed having read 200
    # of 641 cards, and no card at all. Which offsets a loop reaches is not in its text: unread.
    from tests.rest.test_movers_page_ranks_every_card import unread_from_text

    two = ("for (const o of [0, 100]) fetch('/api/v1/event-cards/?limit=100&offset=' + o); "
           "const total = rows.length; el.id = 'pm-gainers';")
    urls, pages = card_requests(two)
    assert pages is True and unread_from_text(urls, pages), "a built offset is never credited from text"
    full = ("let o = 0; while (o < total) { fetch('/api/v1/event-cards/?limit=100&offset=' + o); o += 100; }")
    assert unread_from_text(*card_requests(full)), "nor a loop that looks right: the check does not run it"
    assert unread_from_text(*card_requests(script)) is None, "a literal request is one page, read below"
    assert unread_from_text([], False), "a script that fetches no listing"
    assert unread_from_text(*card_requests("fetch('/api/v1/event-cards/?limit=' + n)"))
    from tests.rest.test_movers_page_ranks_every_card import adds_nothing

    assert adds_nothing({"c1", "c2"}, [{"id": "c1"}, {"id": "c2"}]) is True, (
        "a listing that ignores offset answered the same page again, read as more of the listing")
    assert adds_nothing({"c1"}, [{"id": "c1"}, {"id": "c3"}]) is False and adds_nothing({"c1"}, []) is False

    card = lambda i, cur: {"id": f"c{i}", "title": f"card {i}", "index_base": "100.0", "current_index": str(cur)}
    every = [card(i, 100 + (i - 50) * 0.5) for i in range(100)] + [card(900, 16.08), card(901, 154.91)]
    first = every[:100]
    missed = outside_the_page(first, every)
    assert [r["id"] for r in missed["losers"]] == ["c900"] and [r["id"] for r in missed["gainers"]] == ["c901"], (
        "Corteva's -83.92% and Moderna's +54.91% shape: outside the first page, top of their boards")
    assert outside_the_page(every, every) == {"gainers": [], "losers": []}, "a page that reads every card"
    assert outside_the_page(first, every + [card(902, 0), {"id": "c903", "index_base": 0, "current_index": 5}])[
        "losers"] == missed["losers"], "a card with no index or no base has no move and is not ranked"

    # 2026-10-25, re-pointed: since ET-30860 (#189) the page reads `/api/v1/event-cards/movers?limit=10`
    # and draws its boards from that answer's gainers + losers + most_active. The check said "HTTP 200
    # without a card list" from 2026-10-15 on, because it looked for `cards`/`items` only.
    check = _load("tests/rest/test_movers_page_ranks_every_card.py", "movers_check_under_test")
    check.PAUSE_S = 0
    board = ("var el = document.getElementById('pm-gainers'); function load() { var cards = "
             "fetch('/api/v1/event-cards/movers?limit=10', { credentials: 'same-origin' }); }")
    listing = [card(i, 100 + (i - 12) * 3.0) for i in range(25)]
    ranked = sorted(listing, key=lambda c: float(c["current_index"]))

    class _Page(_Response):
        def __init__(self, status, text):
            super().__init__(status, None)
            self.text = text

    class _Site:
        def __init__(self, *movers):
            self.movers = list(movers)

        def get(self, path, params=None, headers=None):
            params = params or {}
            if path == check.PAGE:
                return _Page(200, f"<html><script>{board}</script></html>")
            if path == "/api/v1/event-cards/movers":
                return _Response(200, self.movers.pop(0) if len(self.movers) > 1 else self.movers[0])
            if path == check.LISTING and str(params.get("limit")) == "500":
                return _Response(422, {"detail": "limit"})
            if path == check.LISTING:
                start = int(params.get("offset") or 0)
                return _Response(200, {"cards": listing[start:start + int(params["limit"])], "total": 25})
            return _Response(404, {})

    def movers(gainers, losers):
        return {"total": 25, "ranked": 25, "gainers": gainers, "losers": losers, "most_active": []}

    whole = movers(ranked[::-1][:10], ranked[:10])
    with verdict_due():  # the true top tens: passes
        check.test_the_movers_boards_rank_every_card_of_the_listing(_Site(whole))
    short = movers(ranked[::-1][1:11], ranked[:10])  # the biggest gainer left off the board
    with verdict_due(), pytest.raises(AssertionError, match="gainers"):
        check.test_the_movers_boards_rank_every_card_of_the_listing(_Site(short, short))
    # A card at the edge of a board that rotated between the two reads of /movers is not a miss.
    edge = movers(ranked[::-1][:9] + [ranked[::-1][10]], ranked[:10])  # the 11th where the 10th is
    with verdict_due(), pytest.raises(AssertionError, match="gainers"):
        check.test_the_movers_boards_rank_every_card_of_the_listing(_Site(edge, edge))
    with verdict_due():
        check.test_the_movers_boards_rank_every_card_of_the_listing(_Site(edge, whole))


def _the_clone_summary_readings():
    """The readings behind the clone summary check (2026-10-11): nine perpetual markets printed as
    four with no count fails, a list set to 'NONE' printed as a market fails, a line that names
    them all or counts the rest passes, a clone with nothing switched on is right to say nothing."""
    from tests.rest.test_a_clone_summary_names_what_it_trades import summary_misstates, switched_on

    nine = {"perpetual_markets": "BTC,ETH,VAIX,SBIO,ET10,ETLP,CYM42,TBIG,TBIGS", "custom_markets": None,
            "arena_trading_enabled": False}
    cut = "This bot trades: BTC/ETH/VAIX/SBIO 5-min epochs (paper)"
    got = summary_misstates(nine, cut)
    assert got["perpetual_left_out"]["left_out"] == ["ET10", "ETLP", "CYM42", "TBIG", "TBIGS"]
    assert summary_misstates(nine, "This bot trades: BTC/ETH/VAIX/SBIO +5 5-min epochs (paper)") == {}, (
        "a count that covers the rest is a fix")
    assert summary_misstates(nine, "This bot trades: BTC, ETH, VAIX, SBIO, ET10, ETLP, CYM42, TBIG, TBIGS "
                                   "5-min epochs (paper)") == {}, "every market named is a fix"
    assert summary_misstates(nine, "This bot trades: BTC/ETH/VAIX/SBIO +4 5-min epochs")["perpetual_left_out"], (
        "a count that is not the number left out is not a count of them")
    off = {"perpetual_markets": "NONE", "custom_markets": "NONE", "arena_trading_enabled": True}
    assert switched_on(off) == {"perpetual": [], "clob": []}
    assert summary_misstates(off, "This bot trades: CLOB NONE · Arena headline assets (paper)") == {
        "off_named_as_a_market": ["custom_markets", "perpetual_markets"]}
    assert summary_misstates(off, "This bot trades: Arena headline assets (paper)") == {}
    nothing = {"perpetual_markets": None, "custom_markets": None}
    assert summary_misstates(nothing, "This bot trades: nothing yet — turn on a market below") == {}
    assert switched_on({"perpetual_markets": None, "custom_markets": "BTC,ETH"})["perpetual"] == ["BTC", "ETH"], (
        "no perpetual list means the CLOB list, their rule's fallback")
    assert summary_misstates(nine, None) is None and summary_misstates(None, cut) is None, "unread, not judged"
    # Deep pass 2026-10-11, B04: a count is its own list's. Nine perpetual and nine CLOB markets, four of
    # each named, the "+5" only on the CLOB part: the 2026-10-10 perpetual defect, passed on the CLOB's count.
    both = dict(nine, custom_markets="AAA,BBB,CCC,DDD,EEE,FFF,GGG,HHH,III")
    pooled = summary_misstates(both, "This bot trades: BTC/ETH/VAIX/SBIO 5-min epochs · CLOB AAA/BBB/CCC/DDD +5 (paper)")
    assert list(pooled) == ["perpetual_left_out"], pooled
    assert summary_misstates(both, "This bot trades: BTC/ETH/VAIX/SBIO +5 5-min epochs · CLOB AAA/BBB/CCC/DDD +5 "
                                   "(paper)") == {}, "each list counted in its own part is a fix"


def _the_tournament_route_readings():
    """The readings behind the Agent Tournaments OpenAPI check (2026-10-11): the llms.txt entry
    as read that day names seven routes, five of them relative to the first full one; an OpenAPI
    with none of them misses all seven, one with all of them (any parameter names) misses none."""
    from tests.rest.test_agent_tournaments_routes_are_in_the_openapi import missing_from, tournament_routes

    line = ("- [Agent Tournaments](https://cymetica.com/agent-tournaments?utm_source=llms&utm_medium=agent) — "
            "10-seat, 7-day tables for cloned bots. `GET https://cymetica.com/api/v1/agent-tournaments/rules`, "
            "`/lobby?mode=paper|live`, `/tables/{id}`, `/tables/{id}/prompt?kind=own|clone` (no auth); "
            "`GET /my-bots`, `POST /tables/{id}/seat` {\"instance_id\"} (X-API-Key: the seat waits until the "
            "owner approves at the returned approve_url), `POST /seats/{id}/leave`")
    other = "- [Gem Screener](x) — `GET /api/v1/gem-screener/status`, `/coins/{symbol}`"
    routes = tournament_routes(f"{other}\n{line}\n")
    p = "/api/v1/agent-tournaments"
    assert routes == sorted([f"{p}/rules", f"{p}/lobby", f"{p}/tables/{{}}", f"{p}/tables/{{}}/prompt",
                             f"{p}/my-bots", f"{p}/tables/{{}}/seat", f"{p}/seats/{{}}/leave"]), routes
    assert missing_from(routes, {"paths": {"/api/v1/gem-screener/status": {}}}) == routes
    described = {"paths": {f"{p}/rules": {}, f"{p}/lobby": {}, f"{p}/tables/{{table_id}}": {},
                           f"{p}/tables/{{table_id}}/prompt": {}, f"{p}/my-bots": {},
                           f"{p}/tables/{{table_id}}/seat": {}, f"{p}/seats/{{seat_id}}/leave": {}}}
    assert missing_from(routes, described) == [], "any parameter name is the same route"
    assert tournament_routes(other) == [], "a line without a full tournament route lends none of its paths"


def _the_company_charter_cap_readings():
    """The readings behind the charter-cap check (2026-10-15): the creation form's textarea as
    served that day caps at 1,500; a name field's maxlength is not a charter's; the OpenAPI's cap
    is read through its anyOf with null."""
    from tests.rest.test_company_charter_cap_agrees_with_its_docs import charter_caps, documented_cap

    served = ('<input class="bc-d-name" maxlength="60" required value="x">'
              '<textarea class="bc-d-charter" rows="3" maxlength="1500">')
    assert charter_caps(served) == [1500], "only the charter field's cap counts"
    assert charter_caps('<textarea class="co-charter-edit">') == [], "an uncapped field holds no number"
    # C09, deep pass 2026-10-18: only a literal maxlength="N" was read, so a cap kept at 1,500 through a
    # constant or el.maxLength was "not judged" and the check passed on the other script.
    from tests.rest.test_company_charter_cap_agrees_with_its_docs import unresolved_caps

    templated = 'const CHARTER_MAX = 1500;\nrow.innerHTML = `<textarea class="bc-d-charter" maxlength="${CHARTER_MAX}">`;'
    assert charter_caps(templated) == [1500], "a template constant the same script defines"
    assert charter_caps("const ta = row.querySelector('.bc-d-charter'); ta.maxLength = 1500;") == [1500], (
        "the property set on the charter's element")
    assert charter_caps("charterBox.setAttribute('maxlength', '1500');") == [1500]
    assert charter_caps("nameInput.maxLength = 60;") == [], "a field that is not a charter"
    unknown = '<textarea class="bc-d-charter" maxlength="${window.LIMITS.charter}">'
    assert charter_caps(unknown) == [] and unresolved_caps(unknown) == ["${window.LIMITS.charter}"], (
        "a cap whose number is not in the script is unread, never absent")
    assert unresolved_caps(served) == [] and unresolved_caps(templated) == []
    spec = {"components": {"schemas": {"DepartmentIn": {"properties": {"charter": {
        "anyOf": [{"type": "string", "maxLength": 2000}, {"type": "null"}]}}}}}}
    assert documented_cap(spec) == 2000
    assert documented_cap({}) is None


def _the_company_heartbeat_readings():
    """The readings behind the heartbeat check (2026-10-15): company 13 paused, a pass promised for
    20:16:01 and at 20:16:42 the last pass still 19:41:17 is a broken promise; a pass at or after
    the promised time, or a second read that promises nothing, keeps it; no promise is not judged."""
    from tests.rest.test_company_heartbeat_keeps_its_promise import broken_promise

    first = {"last_pass_at": "2026-10-15T19:41:17.902544Z", "next_pass_at": "2026-10-15T20:16:01.373188Z"}
    second = {"last_pass_at": "2026-10-15T19:41:17.902544Z", "next_pass_at": "2026-10-15T20:16:42.429390Z"}
    assert broken_promise(first, second) is True
    ran = {"last_pass_at": "2026-10-15T20:16:02Z", "next_pass_at": "2026-10-15T20:18:02Z"}
    assert broken_promise(first, ran) is False, "a pass after the promised time keeps it"
    assert broken_promise(first, {"last_pass_at": "2026-10-15T19:41:17Z", "next_pass_at": None}) is False
    assert broken_promise({"next_pass_at": None}, second) is None, "nothing promised, nothing judged"
    # 2026-10-16, REPLY-0179: their fix gives a paused company next_pass_at null. That is the honest
    # heartbeat the docstring asked for, so it passes; a running company that promises nothing is
    # still not judged (the first version sent both to inconclusive, so no fix could ever clear it).
    from tests.rest.test_company_heartbeat_keeps_its_promise import unpromised

    assert unpromised({"next_pass_at": None}, {"state": "paused", "can_run": False}) == "passed"
    assert unpromised({"next_pass_at": None}, {"state": "running", "can_run": True}) is None
    assert unpromised(first, {"state": "paused", "can_run": False}) is None, "a promise is judged by its pass"


def _the_link_preview_title_readings():
    """The readings behind the link preview check (#217, 2026-10-23): a picture that changes with t= draws it; their
    fix, a picture that ignores t= but whose stored title a person read as the page's (commas for full stops, a small
    b), passes; the defect as filed, a ticket's title in the picture, fails; a picture nobody read is not judged."""
    import hashlib

    from tests.rest.test_agent_tournaments_link_preview_draws_its_title import drawn_title

    t = "Agent Tournaments: 10 agents. 1 table. Best ROI wins."
    fixed, filed = b"picture as of 2026-10-23", b"picture as of 2026-10-22"
    looked = {hashlib.sha256(fixed).hexdigest(): ("Agent Tournaments: 10 agents, 1 table, best ROI wins", "2026-10-23"),
              hashlib.sha256(filed).hexdigest(): ("Add https://cymetica.com/agent-tournaments to main menu", "2026-10-22")}
    assert drawn_title(b"drawn with t", b"drawn with the sentinel", t, looked)[0] == "passed"
    assert drawn_title(fixed, fixed, t, looked)[0] == "passed", "their fix: the stored title is the page's"
    assert drawn_title(filed, filed, t, looked)[0] == "failed", "the defect as filed: a ticket's title"
    assert drawn_title(b"never read", b"never read", t, looked)[0] == "inconclusive"


def _the_tournament_own_seat_readings():
    """The readings behind the own-seat check (2026-10-15): table 13 as read that day, seat 57 ours
    (its bot-settings answered our key 200) and `mine` false with `my_seat` null, is unrecognised;
    either field naming it is enough; an owned seat no table lists is unread, never a pass."""
    from tests.rest.test_agent_tournaments_table_knows_its_owner import unrecognised

    read = {"id": 13, "my_seat": None,
            "seats": [{"seat_id": 57, "mine": False}, {"seat_id": 58, "mine": False}]}
    missed, unread = unrecognised([read], {57})
    assert [m["seat_id"] for m in missed] == [57] and unread == []
    by_flag = {"id": 13, "my_seat": None, "seats": [{"seat_id": 57, "mine": True}]}
    assert unrecognised([by_flag], {57}) == ([], []), "mine true alone recognises the seat"
    by_seat = {"id": 13, "my_seat": {"seat_id": 57}, "seats": [{"seat_id": 57, "mine": False}]}
    assert unrecognised([by_seat], {57}) == ([], []), "my_seat naming it alone recognises it"
    wrong = {"id": 13, "my_seat": {"seat_id": 58}, "seats": [{"seat_id": 57, "mine": False}]}
    assert [m["seat_id"] for m in unrecognised([wrong], {57})[0]] == [57], "another seat is not ours"
    assert unrecognised([read], {99}) == ([], [99]), "an owned seat no table lists is unread"
    assert unrecognised([read], set()) == ([], [])


def _the_tournament_bot_readings():
    """The readings behind the Agent Tournaments bot check (2026-10-11): a bot in our clone list
    is known without asking; one whose profile answers 404 is offered but gone (lab MACD Hunter,
    deleted 2026-09-28, offered with trading: true); one that answers 200 exists; one that could
    not be read is unread, never gone."""
    from tests.rest.test_agent_tournaments_offers_only_bots_that_exist import offered_but_gone

    offered = [{"instance_id": "aaa", "name": "lab Wave 2 MACD Hunter", "trading": False},
               {"instance_id": "996cd23e", "name": "lab MACD Hunter", "trading": True},
               {"instance_id": "ccc", "name": "a live clone", "trading": True},
               {"instance_id": "ddd", "name": "unreadable", "trading": False}]
    gone, unread = offered_but_gone(offered, {"aaa"}, {"996cd23e": 404, "ccc": 200, "ddd": 503})
    assert [b["name"] for b in gone] == ["lab MACD Hunter"] and unread == ["ddd"]
    assert offered_but_gone(offered[:1], {"aaa"}, {}) == ([], []), "a known bot needs no profile"
    assert offered_but_gone(offered, {"aaa", "996cd23e", "ccc", "ddd"}, {}) == ([], [])
    # A row that names no instance is not judged, and says so (deep pass 2026-10-11, C01):
    # /my-bots renaming the key passed "all 53 bots exist" having judged none.
    renamed = [{"id": "996cd23e", "name": "lab MACD Hunter", "trading": True}]
    assert offered_but_gone(renamed, set(), {}) == ([], ["no instance_id: 'lab MACD Hunter'"])


def _the_company_route_readings():
    """The readings behind the Build a Company routes check (2026-10-12): the entry as read that
    day names nine routes relative to its ticked URL, `POST /` being the URL and `pause|resume`
    two; an OpenAPI with all nine misses none, one without the company paths misses all, a route
    on the wrong method is missing, and a line without the ticked URL lends none of its paths."""
    from tests.rest.test_company_routes_are_in_the_openapi import company_routes, missing_from

    line = ("- [Build a Company](https://cymetica.com/company?utm_source=llms&utm_medium=agent) — "
            "Feature #911: one company per account. Owner-only API `https://cymetica.com/api/v1/company`: "
            "`GET /templates`, `POST /`, `GET /mine`, `POST /{id}/message` {\"text\"}, "
            "`GET /{id}/messages?after=`, `POST /{id}/approvals/{aid}` {\"decision\",\"note\"}, "
            "`POST /{id}/pause|resume`, `GET /{id}/audits`. MCP: company_status")
    routes = company_routes(line)
    p = "/api/v1/company"
    assert routes == sorted([("GET", f"{p}/templates"), ("POST", p), ("GET", f"{p}/mine"),
                             ("POST", f"{p}/{{}}/message"), ("GET", f"{p}/{{}}/messages"),
                             ("POST", f"{p}/{{}}/approvals/{{}}"), ("POST", f"{p}/{{}}/pause"),
                             ("POST", f"{p}/{{}}/resume"), ("GET", f"{p}/{{}}/audits")]), routes
    described = {"paths": {p: {"post": {}}, f"{p}/templates": {"get": {}}, f"{p}/mine": {"get": {}},
                           f"{p}/{{company_id}}/message": {"post": {}},
                           f"{p}/{{company_id}}/messages": {"get": {}},
                           f"{p}/{{company_id}}/approvals/{{approval_id}}": {"post": {}},
                           f"{p}/{{company_id}}/pause": {"post": {}},
                           f"{p}/{{company_id}}/resume": {"post": {}},
                           f"{p}/{{company_id}}/audits": {"get": {}}}}
    assert missing_from(routes, described) == [], "any parameter name is the same route"
    assert len(missing_from(routes, {"paths": {"/api/v1/other": {"get": {}}}})) == 9
    wrong = dict(described["paths"], **{f"{p}/mine": {"post": {}}})
    assert missing_from(routes, {"paths": wrong}) == [("GET", f"{p}/mine")], "a wrong method passed"
    assert company_routes(line.replace("`https://cymetica.com/api/v1/company`", "the company API")) == [], (
        "a line without the ticked URL lent its relative paths to the company")


def _the_free_table_readings():
    """The readings behind the free-table check (2026-10-12): Pro #5 at 10 of 10 with one seat
    pending and Pro #2 running left the Pro buy-in with no free seat while Micro #1 had ten; a
    tier with one open table that has a free seat passes; a table with no seats_free is unread,
    never full; a live table does not lend the paper lobby its seats."""
    from tests.rest.test_agent_tournaments_always_has_a_free_table import (
        tiers_without_a_free_table, waiting_to_start)

    tiers = [{"tier": "micro"}, {"tier": "pro"}]
    seen = [{"id": 2, "tier": "pro", "mode": "paper", "status": "running", "seats_free": 0},
            {"id": 5, "tier": "pro", "mode": "paper", "status": "open", "seats_free": 0,
             "seats_taken": 10, "seated": 9,
             "seats": [{"status": "pending"}] + [{"status": "seated"}] * 9},
            {"id": 1, "tier": "micro", "mode": "paper", "status": "open", "seats_free": 10}]
    without, unread = tiers_without_a_free_table(tiers, seen, "paper")
    assert [w["tier"] for w in without] == ["pro"] and unread == [], without
    assert [t["id"] for t in without[0]["tables"]] == [2, 5] and without[0]["tables"][1]["pending"] == 1
    assert waiting_to_start(seen, "paper") == [5]
    opened = seen + [{"id": 6, "tier": "pro", "mode": "paper", "status": "open", "seats_free": 10}]
    assert tiers_without_a_free_table(tiers, opened, "paper") == ([], []), "a new Pro table was missed"
    renamed = [dict(t, seats_free=None, free=t["seats_free"]) for t in seen]
    assert tiers_without_a_free_table(tiers, renamed, "paper") == ([], ["micro", "pro"]), (
        "a renamed seats_free failed a tier unseen")
    live = seen + [{"id": 9, "tier": "pro", "mode": "live", "status": "open", "seats_free": 10}]
    assert [w["tier"] for w in tiers_without_a_free_table(tiers, live, "paper")[0]] == ["pro"], (
        "a live table lent the paper lobby a free seat")
    assert tiers_without_a_free_table(tiers, [], "paper")[0][0]["tables"] == [], (
        "a buy-in with no table at all has no free table")


def _the_documented_get_auth_note_readings():
    """#93 (2026-10-25): the check failed on `/api/v1/cloned-bots/backtest/quote` from PRE-0274 on,
    and a FAIL went out 2026-10-21. llms.txt's own line for that route says "(session JWT)" -- the
    capture of 10-21 says it too -- and its 401 body says "Valid JWT token required". The check's
    claim is a 401 on a route listed WITHOUT an auth note, so a route whose own line documents a
    session JWT, and names no API key, is named and not judged; one that names the key is."""
    import json as _json

    class _Doc:
        def __init__(self, status, body):
            self.status_code, self._body = status, body
            self.text = body if isinstance(body, str) else _json.dumps(body)

        def json(self):
            return self._body

    class _Key:
        def __init__(self, answers):
            self.answers = answers

        def get(self, path, **_):
            return _Doc(*self.answers.get(path, (404, {"detail": "Not Found"})))

    check = _load("tests/rest/test_documented_gets_accept_the_agent_key.py", "documented_gets_under_test")
    quote = ("- [GET /api/v1/cloned-bots/backtest/quote](/api/v1/cloned-bots/backtest/quote): Cost "
             "confirmation before a run (session JWT): free runs remaining, BRRR required")
    me = "- [GET /api/v1/account/me](/api/v1/account/me): Your account"
    summary = "- [GET /api/v1/rewards/summary](/api/v1/rewards/summary): Your reward totals"
    keyed = ("- [GET /api/v1/creator/rewards](/api/v1/creator/rewards): Your own post-reward ledger "
             "(session or X-API-Key)")
    stats = ("- [GET /api/v1/build-stats](/api/v1/build-stats): commits and development sessions, each "
             "series with its own period")
    jwt = (401, {"detail": {"error": {"code": "UNAUTHORIZED", "message": "Valid JWT token required"}}})
    bare = (401, {"detail": "Not authenticated"})

    def run(lines, answers):
        rest = _Key({"/llms.txt": (200, "\n".join(lines)), "/api/v1/account/me": (200, {}), **answers})
        check.test_every_documented_get_accepts_the_key_its_own_document_issues(rest)

    with verdict_due():
        run([quote, me], {"/api/v1/cloned-bots/backtest/quote": jwt})  # documented session JWT: passes
    with verdict_due(), pytest.raises(AssertionError) as caught:
        run([quote, me, summary], {"/api/v1/cloned-bots/backtest/quote": jwt, "/api/v1/rewards/summary": bare})
    assert "/api/v1/rewards/summary" in str(caught.value) and "backtest/quote" not in str(caught.value).split(
        "NOT in the verdict")[0], "the route with no auth note is the defect; the documented one is not"
    with verdict_due(), pytest.raises(AssertionError, match="creator/rewards"):
        run([me, keyed], {"/api/v1/creator/rewards": bare})  # its note names the key: judged
    with verdict_due(), pytest.raises(AssertionError, match="build-stats"):
        run([me, stats], {"/api/v1/build-stats": bare})  # "sessions" in prose is not an auth note


def _the_open_position_card_readings():
    """The position check (2026-10-25): PRE-0274 failed it on a CLOSED position whose card had been
    deleted. llms.txt documents the route as "Your open card positions", and its rows carry `status`
    (open 33, closed 90 on 2026-10-25). A closed row has nothing to price or close; only open
    positions are judged, a row whose status does not read is named, and none open is nothing."""
    check = _load("tests/rest/test_build_recipes.py", "position_cards_under_test")
    pos = lambda card, status: {"card_id": card, "status": status}  # noqa: E731

    def run(rows, cards):
        rest = _Rest({check.POSITIONS: (200, {"positions": rows}),
                      **{check.CARD.format(card_id=c): (200, {"id": c}) for c in cards}})
        check.test_every_card_we_hold_a_position_in_still_resolves(rest)
        return rest

    with verdict_due():
        asked = run([pos("live", "open"), pos("deleted", "closed")], ["live"])
    assert check.CARD.format(card_id="deleted") not in asked.asked, "a closed row's card is not probed"
    with verdict_due(), pytest.raises(AssertionError, match="gone"):
        run([pos("live", "open"), pos("gone", "open")], ["live"])
    with pytest.raises(Inconclusive):
        run([pos("deleted", "closed")], [])
    with pytest.raises(Inconclusive):
        run([{"card_id": "gone"}], [])  # no status: not known to be open

    class _Drops(_Rest):  # 2026-10-25: a card read died on RemoteProtocolError mid-probe
        def get(self, path, **kw):
            if path == check.CARD.format(card_id="flaky"):
                raise ConnectionError("Server disconnected without sending a response.")
            return super().get(path, **kw)

    with pytest.raises(Inconclusive):
        check.test_every_card_we_hold_a_position_in_still_resolves(_Drops({
            check.POSITIONS: (200, {"positions": [pos("flaky", "open")]})}))


def _the_idea_template_readings():
    """The readings behind the idea-template check (2026-10-11): ET-30773's log as read that day
    switches to the rebuild wording after its BB-CHANGE and fails; an idea whose post-change spec
    keeps the new-app wording passes; an idea with no BB-CHANGE, or not an idea, is not judged."""
    from tests.rest.test_build_it_better_spec_keeps_the_request import idea_after_a_change, spec_template

    first = ("BB-SPEC for Agent Tournaments\n\nWhat we will build: Agent Tournaments, a new page on EventTrader that "
             "does what you described. Each line is a check you can run on the live page:\n  1. Build it.\n"
             "Look and branding: ... never anyone else's logos, copy or trademarks.")
    regen = ("BB-SPEC for Agent Tournaments\n\nWhat we will build: a page on EventTrader that does the job you use "
             "Agent Tournaments for, with these changes. Each line is a check you can run on the live page:\n"
             "  1. Build it.\nLook and branding: ... never Agent Tournaments's logos, copy or trademarks.")
    assert spec_template(first) == {"kind": "new", "forbids": None}
    assert spec_template(regen) == {"kind": "rebuild", "forbids": "Agent Tournaments"}
    log = lambda *ms: [{"kind": k, "at": at, "body": b} for k, at, b in ms]  # noqa: E731
    record = {"ticket": "ET-30773", "app_name": "Agent Tournaments", "is_idea": True,
              "messages": log(("BB-REQUEST", "2026-10-10T21:31:57.059708+00:00", "Agent Tournaments: ..."),
                              ("BB-SPEC", "2026-10-10T21:31:57.067933+00:00", first),
                              ("BB-CHANGE", "2026-10-10T21:34:47.136273+00:00", "C1"),
                              ("BB-SPEC", "2026-10-10T21:34:47.142562+00:00", regen))}
    got = idea_after_a_change(record)
    assert got["switched"] and got["example"]["forbids"] == "Agent Tournaments"
    assert [b["kind"] for b in got["before"]] == ["new"] and [a["kind"] for a in got["after"]] == ["rebuild"]
    kept = dict(record, messages=record["messages"][:3] + log(("BB-SPEC", "2026-10-10T21:34:47.142562+00:00",
                                                               first)))
    assert idea_after_a_change(kept)["switched"] is False, "the new-app wording after the change is the fix"
    assert idea_after_a_change(dict(record, messages=record["messages"][:2])) is None, "no BB-CHANGE: not judged"
    assert idea_after_a_change(dict(record, messages=record["messages"][:3])) is None, "no spec after it yet"
    assert idea_after_a_change(dict(record, is_idea=False)) is None, "a rebuild request may say 'the job you use'"
    # Deep pass 2026-10-11, C02 and C03: a post-change spec in neither wording is unread, never "keeps the
    # new-app wording"; and an idea whose record did not read may be the newest, so no verdict rests on the rest.
    from tests.rest.test_build_it_better_spec_keeps_the_request import newest_verdict

    reworded = dict(record, messages=record["messages"][:3] + log(("BB-SPEC", "2026-10-10T21:34:47.142562+00:00",
                                                                   "BB-SPEC, worded some third way")))
    vague = idea_after_a_change(reworded)
    assert vague["switched"] is False and vague["unread_wording"] is True
    assert newest_verdict([vague], [])[0] == "inconclusive", "a spec neither template reads was passed"
    assert newest_verdict([idea_after_a_change(kept)], [])[0] == "passed"
    assert newest_verdict([got], [])[0] == "failed"
    assert newest_verdict([got], ["ET-31000 (HTTP 503)"])[0] == "inconclusive", (
        "an unread idea may be the newest: the frozen history was judged in its place")


_BB_SECTION = """\
## Build it Better

Name a financial app, agree a scope, and a better version is built in the open.

- MCP tools: `bb_search_rebuilt_apps`, `bb_file_request`, `bb_withdraw_request`
- REST: `GET /api/v1/build-it-better/apps`, `GET /api/v1/build-it-better/requests`,
  `GET /api/v1/build-it-better/requests/{ticket}`, `POST /api/v1/build-it-better/requests`
  (X-API-Key; NEXUS build plan, or >=100 ET10 only while plans are off), `POST
  .../requests/{ticket}/accept|change|verdict|withdraw` (request token in the body)
- Limits: `improvements` up to 8,000 characters. `POST .../requests/{ticket}/withdraw` takes back
  your own request while it is requested or funded.
- Traffic and likes, no key: `GET /api/v1/build-it-better/apps/stats`
- Real-time: `wss://cymetica.com/ws/build-it-better` (public). Sends
  `{"type":"hello","channel":"build-it-better"}` on connect.
- Pages: https://cymetica.com/build-it-better?utm_source=llms , https://cymetica.com/build-it-better/api

## Feature Leaderboard

- REST: `GET /api/v1/features/leaderboard?sort=top`, `POST /api/v1/features/{feature_id}/bid` (auth)
"""


def _the_build_it_better_route_readings():
    """The readings behind the Build it Better routes check (2026-10-11): the section as read that
    day names eight routes, four of them as `.../requests/{ticket}/accept|change|verdict|withdraw`;
    an OpenAPI with every one but withdraw misses exactly withdraw, one with it misses none (any
    parameter names), a route on the wrong method is missing, another section's routes are not read."""
    from tests.rest.test_build_it_better_routes_are_in_the_openapi import (
        build_it_better_section, missing_from, named_routes)

    p = "/api/v1/build-it-better"
    routes = named_routes(_BB_SECTION)
    assert routes == sorted([
        ("GET", f"{p}/apps"), ("GET", f"{p}/requests"), ("GET", f"{p}/requests/{{}}"), ("POST", f"{p}/requests"),
        ("POST", f"{p}/requests/{{}}/accept"), ("POST", f"{p}/requests/{{}}/change"),
        ("POST", f"{p}/requests/{{}}/verdict"), ("POST", f"{p}/requests/{{}}/withdraw"),
        ("GET", f"{p}/apps/stats")]), routes
    assert "Feature Leaderboard" not in build_it_better_section(_BB_SECTION), "the next section is not read"
    assert not any("features" in path for _, path in routes), "the leaderboard's routes are another section's"
    assert not any("ws/" in path or "hello" in path for _, path in routes), "a socket and a JSON line are not routes"
    op = lambda *methods: {m: {} for m in methods}  # noqa: E731
    described = {"paths": {
        f"{p}/apps": op("get"), f"{p}/apps/stats": op("get"), f"{p}/requests": op("get", "post"),
        f"{p}/requests/{{ticket}}": op("get"), f"{p}/requests/{{ticket}}/accept": op("post"),
        f"{p}/requests/{{ticket}}/change": op("post"), f"{p}/requests/{{ticket}}/verdict": op("post")}}
    assert missing_from(routes, described) == [("POST", f"{p}/requests/{{}}/withdraw")], (
        "the day's reading: every route but withdraw")
    described["paths"][f"{p}/requests/{{ticket_id}}/withdraw"] = op("post")
    assert missing_from(routes, described) == [], "any parameter name is the same route"
    wrong = {"paths": dict(described["paths"], **{f"{p}/requests/{{ticket}}/withdraw": op("get")})}
    wrong["paths"].pop(f"{p}/requests/{{ticket_id}}/withdraw")
    assert missing_from(routes, wrong) == [("POST", f"{p}/requests/{{}}/withdraw")], "a path on another method is missing"
    assert missing_from(routes, {"paths": {}}) == routes
    assert named_routes("## Feature Leaderboard\n\n- REST: `GET /api/v1/features/leaderboard`") == [], (
        "no Build it Better section: nothing named")
    assert named_routes("## Build it Better\n\nNo routes here, see `bb_file_request`.") == []


def _the_request_token_place_readings():
    """The readings behind the request token check (2026-10-11): llms.txt writes '(request token in
    the body)' for accept|change|verdict|withdraw while the OpenAPI declares an x-bb-token header
    on accept, change and verdict and nothing token-shaped in a body: it fails on those three and
    leaves withdraw unread; naming the header, declaring a body token, or naming both passes."""
    from tests.rest.test_build_it_better_token_place_is_documented_one_way import (
        disagreements, llms_token_sentence, openapi_token_places)

    p = "/api/v1/build-it-better/requests/{ticket}"
    header = {"name": "x-bb-token", "in": "header", "required": False, "schema": {"type": "string"}}
    key = {"name": "x-api-key", "in": "header", "required": False, "schema": {"type": "string"}}

    def spec(change_body=None, verdict_body=None, withdraw=False, **extra):
        post = lambda body=None: dict(  # noqa: E731
            {"parameters": [{"name": "ticket", "in": "path"}, header, key]},
            **({"requestBody": {"content": {"application/json": {"schema": body}}}} if body else {}))
        paths = {f"{p}/accept": {"post": post()},
                 f"{p}/change": {"post": post(change_body or {"$ref": "#/components/schemas/BBChangeIn"})},
                 f"{p}/verdict": {"post": post(verdict_body or {"$ref": "#/components/schemas/BBVerdictIn"})}}
        if withdraw:
            paths[f"{p}/withdraw"] = {"post": post()}
        schemas = {"BBChangeIn": {"properties": {"changes": {"type": "string"}}},
                   "BBVerdictIn": {"properties": {"verdict": {"type": "string"}, "note": {"type": "string"}}}}
        schemas.update(extra)
        return {"paths": paths, "components": {"schemas": schemas}}

    said = llms_token_sentence(_BB_SECTION)
    assert said["ops"] == ["accept", "change", "verdict", "withdraw"], said
    assert said["phrase"] == "request token in the body" and said["places"] == {"body"}, said
    assert said["per_op"] == {o: {"body"} for o in said["ops"]}, "each op the sentence names states the place"
    got = disagreements(said, spec())
    assert got["mismatched"] == {"accept": ["header"], "change": ["header"], "verdict": ["header"]}, got
    assert got["unread"] == ["withdraw"], "a route the OpenAPI does not describe is the routes check's"
    assert openapi_token_places(spec(), "accept") == {"places": {"header"}, "header": "x-bb-token", "body_fields": []}
    assert openapi_token_places(spec(), "withdraw") is None

    named_header = llms_token_sentence(_BB_SECTION.replace("(request token in the body)",
                                                           "(X-BB-Token header)"))
    assert named_header["places"] == {"header"}
    assert disagreements(named_header, spec())["mismatched"] == {}, "naming the header is the fix"
    both = llms_token_sentence(_BB_SECTION.replace("(request token in the body)",
                                                   "(the X-BB-Token header, or request_token in the body)"))
    assert both["places"] == {"body", "header"} and disagreements(both, spec())["mismatched"] == {}, (
        "naming both places is a fix")
    # The other fix: the OpenAPI takes the token in a body. accept has no body, so it stays a mismatch.
    token_body = {"properties": {"changes": {"type": "string"}, "request_token": {"type": "string"}}}
    both_ways = spec(change_body=token_body, verdict_body={"anyOf": [token_body, {"type": "null"}]})
    assert openapi_token_places(both_ways, "change")["places"] == {"header", "body"}
    assert openapi_token_places(both_ways, "verdict")["body_fields"] == ["request_token"]
    assert disagreements(said, both_ways)["mismatched"] == {"accept": ["header"]}, (
        "per route: the routes with a body token are right, accept has none")
    no_header = {"paths": {f"{p}/accept": {"post": {"parameters": [{"$ref": "#/components/parameters/Tok"}]}}},
                 "components": {"parameters": {"Tok": header}}}
    assert openapi_token_places(no_header, "accept")["places"] == {"header"}, "a $ref'd parameter is read"
    assert disagreements(said, spec(withdraw=True))["mismatched"].get("withdraw") == ["header"], (
        "withdraw is judged the day it is described")
    silent = llms_token_sentence(_BB_SECTION.replace(" (request token in the body)", ""))
    assert silent["places"] == set() and disagreements(silent, spec())["mismatched"] == {}, (
        "a line that states no place contradicts nothing")
    split = llms_token_sentence(_BB_SECTION.replace(
        "(request token in the body)", "(X-BB-Token header)").replace(
        "`POST .../requests/{ticket}/withdraw` takes back", "`POST .../requests/{ticket}/withdraw` (request token in the body) takes back"))
    assert split["per_op"]["withdraw"] == {"header", "body"} and split["per_op"]["accept"] == {"header"}, (
        "a later line about one route adds its own place to that route only")
    assert disagreements(split, spec(withdraw=True))["mismatched"] == {}, "header is among withdraw's places"
    assert llms_token_sentence("## Build it Better\n\nSee `bb_file_request`.") is None
    # Deep pass 2026-10-11, C04 and C05: the place is what the words after the route say about the
    # TOKEN. Outside a parenthesis it is still said; a parenthesis about the body but not the token
    # says nothing of the token's place.
    dashed = llms_token_sentence(_BB_SECTION.replace(" (request token in the body)",
                                                     " -- the request token goes in the body"))
    assert dashed["places"] == {"body"}, "a place said outside a parenthesis was read as none"
    assert disagreements(dashed, spec())["mismatched"] == {"accept": ["header"], "change": ["header"],
                                                           "verdict": ["header"]}
    shape = llms_token_sentence(_BB_SECTION.replace("(request token in the body)", "(JSON body {changes})"))
    assert shape["places"] == set(), "a body shape that names no token was read as the token's place"
    assert llms_token_sentence(_BB_SECTION.replace("## Build it Better", "## Something else")) is None
