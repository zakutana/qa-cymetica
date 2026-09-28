"""BOOK: the campaign has to be able to lose.

Their paper balance does not move when a paper position is opened (#87), so
nothing on their side stops an agent deploying 500,000 against a 100,000
bankroll. A campaign that cannot run out of money cannot be measured: a
strategy that would have lost everything looks exactly like one that doubled,
because the only number that ever moves is the count of positions.

So the constraint lives here. `scripts/paper.py` keeps its own book -- what we
started with, what we deployed, what those positions are worth from THEIR
position rows -- and refuses an order the book cannot pay for. That refusal is
the whole reason the campaign means anything, so it gets a test rather than a
comment, and the test is what fails if somebody later makes the cap advisory.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _paper(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "paper_under_test", REPO / "scripts" / "paper.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _trade(mod, trade_id, usdc, position_id="p1"):
    mod._append({"id": trade_id, "type": "intent", "usdc": usdc,
                 "card_id": "c1", "paper": True,
                 "before": {"sim_balance_usdc": "100000.00"}})
    mod._append({"id": trade_id, "type": "outcome", "outcome": "accepted",
                 "position_id": position_id, "http_status": 200})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_book_counts_what_is_deployed_and_what_it_is_worth(tmp_path, monkeypatch):
    """Equity is cash we have not deployed plus what the positions are worth.

    Both halves matter. Counting only cash would say a fully deployed book is
    broke; counting only positions would ignore what is left to trade with.
    The position values are THEIRS -- current_value_usdc off their own rows --
    so the only thing we contribute is the arithmetic.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 6000.0, "p1")
    _trade(mod, "TRD-0002", 4000.0, "p2")

    positions = [
        {"position_id": "p1", "current_value_usdc": 6600.0, "status": "open"},
        {"position_id": "p2", "current_value_usdc": 3500.0, "status": "open"},
    ]
    book = mod.book(positions)

    assert book["deployed"] == 10000.0
    assert book["cash"] == 90000.0, "cash is what has not been committed"
    assert book["value"] == 10100.0
    assert book["equity"] == 100100.0, "up 100 on a 100k bankroll"
    assert book["open"] == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_closed_position_returns_its_money_to_the_book(tmp_path, monkeypatch):
    """A position that is no longer open is no longer deployed.

    Without this the book leaks: every closed trade would keep its notional
    counted as committed forever, and after enough round trips the campaign
    would refuse to trade with a bankroll it still has.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 6000.0, "p1")
    positions = [{"position_id": "p1", "current_value_usdc": 6600.0,
                  "status": "closed", "realized_pnl_usdc": 600.0}]

    book = mod.book(positions)
    assert book["deployed"] == 0.0, "a closed position is not deployed capital"
    assert book["cash"] == 100600.0, "the proceeds come back, gain and all"
    assert book["equity"] == 100600.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capital_they_accepted_and_do_not_list_is_still_spent(tmp_path, monkeypatch):
    """An order we cannot see is not an order that did not happen.

    `book()` skipped any accepted order whose `position_id` was absent from
    their positions endpoint, with a comment saying such a row was "worth
    noticing rather than quietly dropping" -- and nothing noticed: no counter,
    no field, no print. The capital went back to cash and `affordable()` would
    authorise spending it a second time.

    Reachable three ways that have nothing to do with a bug on their side:
    pagination, a filter, and the lag between an order being accepted and the
    position appearing. Two readers of three reproduced it; the third could not
    construct it against today's captures, which is a statement about today's
    data and not about the arithmetic.

    Rule 8's shape, applied to a row rather than a read: an accepted order we
    cannot account for is UNACCOUNTED, and the safe direction is to hold its
    capital rather than to release it.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 30000.0, "p1")
    _trade(mod, "TRD-0002", 60000.0, "p2")

    # Only one of the two comes back from their endpoint.
    listed = [{"position_id": "p1", "current_value_usdc": 30000.0,
               "status": "open"}]
    state = mod.book(listed)

    assert state["unaccounted"] == 1, (
        f"an accepted order absent from their positions must be counted, not "
        f"skipped: {state}")
    assert state["unaccounted_usdc"] == 60000.0, (
        f"and its notional named, so a reader knows how much is unexplained: "
        f"{state}")
    assert state["cash"] == 10000.0, (
        f"its capital is committed until we can see it: 100000 - 30000 - 60000. "
        f"Releasing it lets the same money be spent twice: {state}")

    ok, why = mod.affordable(50000.0, listed)
    assert ok is False, (
        f"the book authorised an order the unaccounted capital cannot cover: {why}")
    assert "unaccounted" in why.lower() or "60000" in why, (
        f"the refusal must say WHY the money is unavailable, or it reads as a "
        f"book that lost track: {why}")

    # And when their endpoint lists everything, nothing is unaccounted and the
    # arithmetic is exactly as before -- this must not tax the ordinary case.
    both = listed + [{"position_id": "p2", "current_value_usdc": 60000.0,
                      "status": "open"}]
    full = mod.book(both)
    assert full["unaccounted"] == 0 and full["cash"] == 10000.0, full

    # An order whose outcome is UNKNOWN -- a timeout, a 5xx, a 2xx with no
    # position id -- may have landed. It is found by the card: a position of
    # its card that no accepted order claims is that order's, and its money
    # is deployed. The book released it and the room was stopped as "nothing
    # at stake" (deep pass 2026-09-27, L01, 3/3). A 4xx is their refusal and
    # nothing landed; nor did an unknown with no unclaimed position of its card.
    mod._append({"id": "TRD-0003", "type": "intent", "usdc": 5000.0,
                 "card_id": "C2", "paper": True})
    mod._append({"id": "TRD-0003", "type": "outcome", "outcome": "unknown",
                 "error": "ReadTimeout: timed out"})
    mod._append({"id": "TRD-0004", "type": "intent", "usdc": 7000.0,
                 "card_id": "c3", "paper": True})
    mod._append({"id": "TRD-0004", "type": "outcome", "outcome": "unknown",
                 "http_status": 409})
    landed = both + [{"position_id": "p9", "card_id": "c2", "status": "open",
                      "current_value_usdc": 5100.0},
                     {"position_id": "p8", "card_id": "c3", "status": "open",
                      "current_value_usdc": 7000.0}]
    state = mod.book(landed)
    assert state["deployed"] == 95000.0 and state["cash"] == 5000.0, (
        f"a timed-out order whose position they list is money out: {state}")
    assert state["value"] == 95100.0 and state["open"] == 3, state
    assert mod.landed(mod.load(), landed) == {"TRD-0003": landed[2]}, (
        "a 409 refusal was taken for an order that landed")
    assert mod.book(both)["cash"] == 10000.0, (
        "an unknown order with no position of its card was held as spent")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_the_book_cannot_pay_for_is_refused(tmp_path, monkeypatch):
    """The refusal that makes the campaign mean something.

    Their side will accept this order -- it accepted every one we have sent,
    and debited nothing. If we accept it too, the campaign has no downside and
    no measurement. `affordable` is the gate, and it is a hard refusal rather
    than a warning because a warning in a loop is a warning nobody reads.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 95000.0, "p1")
    positions = [{"position_id": "p1", "current_value_usdc": 95000.0,
                  "status": "open"}]

    ok, why = mod.affordable(6000.0, positions)
    assert ok is False

    # The figure, computed here rather than matched as a substring. `"5000" in
    # why` was satisfied by the rendered `95000.00` deployed figure, so a
    # refusal that dropped the uncommitted number entirely still passed -- true
    # for cash 5000.00, 4999.50, 1.00 and 0.00 alike. Three readers reproduced
    # it by deleting the clause. A number that appears inside another number is
    # not a number this test read.
    cash = f"{mod.book(positions)['cash']:.2f}"
    assert cash == "5000.00", f"the fixture no longer leaves 5000.00: {cash}"
    stripped = why.replace("95000.00", "").replace("95,000.00", "")
    assert cash in stripped or "5,000.00" in stripped, (
        f"the refusal has to say what is actually left, and {cash} appears in "
        f"it only as part of the deployed figure: {why}"
    )
    assert f"{6000.0:.2f}" in why, (
        f"the refusal has to say what was asked for, or a reader cannot tell "
        f"how far over the order was: {why}")

    ok, why = mod.affordable(4999.0, positions)
    assert ok is True, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_cap_is_not_advisory(tmp_path, monkeypatch):
    """The gate runs before the order, on the path the order takes.

    The whole value of the book is that it says no, and the docstring used to
    say this reads the source "on purpose: behaviour can be preserved while the
    gate is moved somewhere it never runs" -- while the assertion was textual
    proximity, which is exactly what cannot see a move. Three readers each
    defeated it: relocate the `affordable`/`raise` pair to just after
    `client.post(...)`, or into the `if not confirm:` branch, and both tokens
    stay inside the 600-character window with the check green and a confirmed
    order never checked against the book. One of them made it pass with no gate
    in `buy()` at all, by adding a dead helper later in the file containing
    both words.

    So it is read as a tree instead of as a string: the call, the refusal it
    raises, and the POST must be statements of ONE block, in that order. That
    is what "before the order, unconditionally" means, and it is a property a
    relocation cannot preserve.
    """
    import ast

    source = (REPO / "scripts" / "paper.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    buy = next((n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "buy"), None)
    assert buy is not None, "scripts/paper.py no longer defines buy()"

    def calls(node, name: str) -> bool:
        return any(isinstance(c, ast.Call) and (
                   getattr(c.func, "id", None) == name
                   or getattr(c.func, "attr", None) == name)
                   for c in ast.walk(node))

    # The one block holding all three. Statement lists are searched rather than
    # the whole function, because "in the same block" is the property that
    # stops the gate being moved into a branch the confirmed path skips.
    def holds_both(block) -> bool:
        gate = next((i for i, s in enumerate(block) if calls(s, "affordable")), None)
        post = next((i for i, s in enumerate(block) if calls(s, "post")), None)
        # Distinct statements: an enclosing block "contains" both only because
        # one nested statement holds them, which says nothing about order.
        return gate is not None and post is not None and gate != post

    blocks = [b for b in ([buy.body] + [
        child.body for child in ast.walk(buy)
        if isinstance(child, (ast.Try, ast.If, ast.With, ast.For, ast.While))])
        if holds_both(b)]
    assert blocks, (
        "no single block of buy() holds both the book check and the POST, so "
        "the gate is on a different path from the order -- which is the move "
        "this test exists to catch, not a refactor to wave through"
    )

    for block in blocks:
        gate = next(i for i, s in enumerate(block) if calls(s, "affordable"))
        post = next(i for i, s in enumerate(block) if calls(s, "post"))
        assert gate < post, (
            f"buy() consults the book at statement {gate} and posts the order "
            f"at {post}: the platform has already accepted it by the time our "
            f"own refusal is computed"
        )
        # The refusal is the book's answer and nothing else: `if not can:` over
        # a raise, where `can` is what affordable() returned. Until the deep
        # pass of 2026-09-11 any statement holding a Raise counted, so
        # `if not can and not confirm:` -- the cap gone advisory for every
        # confirmed order -- stayed green, and so would any other raise that
        # happens to sit between the two (buy() now has one, for an
        # unreadable bot balance). Three readers reproduced it.
        stmt = block[gate]
        target = stmt.targets[0] if isinstance(stmt, ast.Assign) else None
        answer = (target.elts[0] if isinstance(target, ast.Tuple) and target.elts
                  else target)
        assert isinstance(answer, ast.Name), (
            "buy() does not keep affordable()'s verdict in a name, so what "
            "refuses the order cannot be tied to the book's answer")

        def refuses(s) -> bool:
            return (isinstance(s, ast.If)
                    and isinstance(s.test, ast.UnaryOp)
                    and isinstance(s.test.op, ast.Not)
                    and isinstance(s.test.operand, ast.Name)
                    and s.test.operand.id == answer.id
                    and any(isinstance(n, ast.Raise) for n in ast.walk(s)))

        refusal = next((i for i, s in enumerate(block)
                        if gate < i < post and refuses(s)), None)
        assert refusal is not None, (
            f"nothing between the book check and the POST is `if not "
            f"{answer.id}:` over a raise, so the book's answer decorates the "
            f"order instead of stopping it -- or stops it only on some paths")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capital_moved_into_a_bot_is_deployed_not_cash(tmp_path, monkeypatch):
    """The book counted money it had already given away.

    2026-09-10: 1,000 USDC was funded into a paper clone, and `book()` went
    on reporting 99,998 uncommitted because it reads event-card positions and
    nothing else. Their own practice balance had already dropped to 99,000.96
    -- so the platform knew, and our constraint did not.

    That is the same defect as `test_capital_they_accepted_and_do_not_list_is
    _still_spent`, one layer out: money we cannot see in positions is still
    money we do not have. It matters more here, because the whole reason the
    book exists is that their paper balance will accept an order the bankroll
    cannot cover (#87), so the book is the only thing that can run out.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 2.0, "p1")
    positions = [{"position_id": "p1", "current_value_usdc": 2.0,
                  "status": "open", "notional_usdc": 2.0}]

    loose = mod.book(positions)
    held = mod.book(positions, clone_capital={"moved": 1000.0, "worth": 1000.0})

    assert held["cash"] == loose["cash"] - 1000.0, (
        "capital sitting in a bot is not available to trade; the bot spends "
        "it on its own schedule and we cannot recall it by deciding not to")
    assert held["deployed"] == loose["deployed"] + 1000.0
    # Equity is unchanged: the money still exists, it is somewhere else.
    assert round(held["equity"], 6) == round(loose["equity"], 6)

    # A bot's loss is not cash: 1,000 went in and it is worth 800. Cash is
    # what did not go in; equity is down the 200. Cash was 99,200 and equity
    # never moved (deep pass 2026-09-27, L02, 3/3).
    lost = mod.book(positions, clone_capital={"moved": 1000.0, "worth": 800.0})
    assert lost["cash"] == loose["cash"] - 1000.0, lost
    assert round(lost["equity"], 6) == round(loose["equity"] - 200.0, 6), lost
    assert lost["in_bots"] == 800.0, lost

    # `None` here is "not given" -- the default of every caller that holds no
    # bot -- and changes nothing. An UNREADABLE bot balance is a different
    # case, and until the deep pass of 2026-09-11 buy() passed it in as this
    # one, freeing the money in bots. It is now refused before the book is
    # asked: test_an_order_is_refused_when_the_money_in_bots_cannot_be_read.
    assert mod.book(positions, clone_capital=None)["cash"] == loose["cash"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capital_in_a_bot_is_what_went_in_and_what_it_made(tmp_path, monkeypatch):
    """Not the bot's free balance.

    2026-09-11: their fix of #94 debits a bot's stake on entry, so
    `current_balance_usdc` stopped holding what sits in open positions. Our
    bot was funded 1,000, lost 50 and had 400 open; my-clones said 550, the
    book counted 550 in bots, and 400 committed inside the bot read as ours
    to spend. What is ours in a bot does not depend on how they book a stake:
    what we moved in, by our own accepted transfers, plus what it has made
    or lost. A bot we hold no transfer for, or a row we cannot read, is not a
    number -- the order is refused rather than the money freed.
    """
    mod = _paper(tmp_path, monkeypatch)
    records = [
        {"id": "CLN-0003", "type": "intent", "kind": "fund", "instance_id": "b1", "amount": 1.0},
        {"id": "CLN-0003", "type": "outcome", "kind": "fund", "outcome": "rejected"},
        {"id": "CLN-0004", "type": "intent", "kind": "fund", "instance_id": "b1", "amount": 1.0},
        {"id": "CLN-0004", "type": "outcome", "kind": "fund", "outcome": "accepted"},
        {"id": "CLN-0005", "type": "intent", "kind": "fund", "instance_id": "b1", "amount": 999.0},
        {"id": "CLN-0005", "type": "outcome", "kind": "fund", "outcome": "accepted"},
    ]
    ours = {"id": "b1", "current_balance_usdc": 550.0, "total_profit_usdc": -50.0}
    assert mod.capital_in_bots([ours], records) == {"moved": 1000.0, "worth": 950.0}, (
        "the capital in a bot is what went in plus what it made, not the "
        "balance left after its open stakes were taken out")
    assert mod.capital_in_bots([], records) == {"moved": 0.0, "worth": 0.0}
    assert mod.capital_in_bots([dict(ours, id="b2")], records) is None, (
        "a bot we have no record of cloning has no capital we can state")
    assert mod.capital_in_bots([dict(ours, total_profit_usdc="n/a")], records) is None
    assert mod.capital_in_bots(["not a row"], records) is None
    # `or 0` reads a missing or null field the same as a legitimate zero --
    # not "n/a", so it raises nothing, and not caught above. A row we cannot
    # read must be refused, not silently scored as having made nothing: a bot
    # down 50 whose field never arrived must not book as flat.
    assert mod.capital_in_bots(
        [dict(ours, total_profit_usdc=None)], records) is None, (
        "a null total_profit_usdc read as zero, not as unreadable")
    no_field = {"id": "b1", "current_balance_usdc": 550.0}
    assert mod.capital_in_bots([no_field], records) is None, (
        "a missing total_profit_usdc read as zero, not as unreadable")

    # A bot WE cloned whose funding was refused holds nothing of ours: it is
    # 0, not unknown. As None it refused every later card order for good, and
    # nothing releases a clone (deep pass 2026-09-27, L03, 3/3). A transfer
    # whose outcome is unknown is still unknown.
    cloned = records + [
        {"id": "CLN-0006", "type": "intent", "source_type": "bot"},
        {"id": "CLN-0006", "type": "outcome", "outcome": "accepted",
         "clone_instance_id": "b3"},
        {"id": "CLN-0007", "type": "intent", "kind": "fund", "instance_id": "b3", "amount": 240.0},
        {"id": "CLN-0007", "type": "outcome", "kind": "fund", "outcome": "rejected"}]
    bare = {"id": "b3", "total_profit_usdc": 0.0}
    assert mod.capital_in_bots([ours, bare], cloned) == {"moved": 1000.0, "worth": 950.0}
    pending = cloned + [
        {"id": "CLN-0008", "type": "intent", "kind": "fund", "instance_id": "b3", "amount": 240.0},
        {"id": "CLN-0008", "type": "outcome", "kind": "fund", "outcome": "unknown"}]
    assert mod.capital_in_bots([ours, bare], pending) is None, (
        "a transfer that may have landed was read as none")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_is_refused_when_the_money_in_bots_cannot_be_read(tmp_path, monkeypatch):
    """buy() handed an unreadable bot balance to the book as `None`, and the
    book reads `None` as no bots: the money in them came back as cash. The
    client here refuses every POST itself, so if the refusal ever breaks the
    test fails on that and nothing leaves this machine."""
    mod = _paper(tmp_path, monkeypatch)
    posted = []

    class Client:
        def post(self, *args, **kwargs):
            posted.append(args)
            raise AssertionError("an order went out on an unreadable book")

        def close(self):
            pass

    monkeypatch.setattr(mod, "install_client_guard", lambda: None)
    monkeypatch.setattr(mod, "identities", lambda: {"trusted": None})
    monkeypatch.setattr(mod, "build_client", lambda *a, **k: Client())
    monkeypatch.setattr(mod, "_guidance", lambda nexus_id: {"id": None})
    monkeypatch.setattr(mod, "_snapshot", lambda client: {})
    monkeypatch.setattr(mod, "_positions", lambda client: [])
    monkeypatch.setattr(mod, "clone_capital", lambda client: None)

    with pytest.raises(SystemExit) as refused:
        mod.buy("card-1", 10.0, None, confirm=True)
    assert "bot" in str(refused.value), refused.value
    assert posted == []
    assert mod.load() == [], "an intent was written for an order that was refused"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_records_what_the_card_said_about_itself_before_it(
        tmp_path, monkeypatch):
    """A03, deep pass of 2026-09-22: #117's contract is tradeable_now at the
    moment of the buy, and nothing recorded it -- the check could only read
    the card days later. The intent carries the card's own gate, read just
    before, and an unread card is recorded as unread, not as tradeable."""
    mod = _paper(tmp_path, monkeypatch)
    answers = {"/api/v1/event-cards/card-1": (200, {
        "status": "live", "tradeable_now": True,
        "trading_blocked_reason": None}),
        "/api/v1/event-cards/card-2": (503, {})}

    class Response:
        def __init__(self, status, body):
            self.status_code, self._body = status, body

        def json(self):
            return self._body

    class Client:
        def get(self, path, **kwargs):
            return Response(*answers.get(path, (404, {})))

        def post(self, *args, **kwargs):
            raise AssertionError("a dry run posted")

        def close(self):
            pass

    monkeypatch.setattr(mod, "install_client_guard", lambda: None)
    monkeypatch.setattr(mod, "identities", lambda: {"trusted": None})
    monkeypatch.setattr(mod, "build_client", lambda *a, **k: Client())
    monkeypatch.setattr(mod, "_guidance", lambda nexus_id: {"id": None})
    monkeypatch.setattr(mod, "_snapshot", lambda client: {})
    monkeypatch.setattr(mod, "_positions", lambda client: [])
    monkeypatch.setattr(mod, "clone_capital", lambda client: 0.0)
    monkeypatch.setattr(mod, "affordable", lambda *a, **k: (True, "ok"))

    entry = mod.buy("card-1", 10.0, None, confirm=False)
    assert entry["card_before"]["tradeable_now"] is True, entry
    unread = mod.buy("card-2", 10.0, None, confirm=False)
    assert "tradeable_now" not in unread["card_before"], unread
    assert unread["card_before"]["http_status"] == 503


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_takes_its_id_when_it_is_written_not_before(
        tmp_path, monkeypatch):
    """C9 of the 2026-09-23 review. `buy` numbered its intent from the file
    and then read their book and the card over the network before writing it,
    so a second writer -- the tick's launch beside an operator's `lab.py buy`
    -- could append the same TRD number in between, and every reader keyed on
    the id (`_deployed`, the board, the closes) would join two orders into
    one. The id is now taken under the file's lock, in the step that writes."""
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 10.0, "p0")

    class Response:
        def __init__(self, status, body):
            self.status_code, self._body = status, body
            self.request = None
            self.headers = {}
            self.text = json.dumps(body)

        def json(self):
            return self._body

    class Client:
        def get(self, path, **kwargs):
            # Another writer lands its order while ours reads the card.
            mod._append({"id": "TRD-0002", "type": "intent", "usdc": 5.0,
                         "card_id": "other", "paper": True})
            return Response(200, {"status": "live", "tradeable_now": True})

        def post(self, *args, **kwargs):
            return Response(200, {"position_id": "p9"})

        def close(self):
            pass

    monkeypatch.setattr(mod, "install_client_guard", lambda: None)
    monkeypatch.setattr(mod, "identities", lambda: {"trusted": None})
    monkeypatch.setattr(mod, "build_client", lambda *a, **k: Client())
    monkeypatch.setattr(mod, "_guidance", lambda nexus_id: {"id": None})
    monkeypatch.setattr(mod, "_snapshot", lambda client: {})
    monkeypatch.setattr(mod, "_positions", lambda client: [])
    monkeypatch.setattr(mod, "clone_capital", lambda client: 0.0)
    monkeypatch.setattr(mod, "affordable", lambda *a, **k: (True, "ok"))
    monkeypatch.setattr(mod, "_capture", lambda *a, **k: None)
    monkeypatch.setattr(mod, "PAUSE_SECONDS", 0)

    said = mod.buy("card-1", 10.0, None, confirm=True)
    assert said["id"] == "TRD-0003", said["id"]
    intents = [r["id"] for r in mod.load() if r.get("type") == "intent"]
    assert len(intents) == len(set(intents)), f"an id was taken twice: {intents}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_200_in_an_unexpected_wrapper_is_not_an_empty_book(tmp_path, monkeypatch):
    """R07, from the 2026-09-10 deep pass, confirmed by the sweep after it.

    `(response.json() or {}).get("positions") or []` reads a body shaped
    `{"result": {"positions": [...]}}` as ZERO positions -- and `buy()` in the
    same file already unwraps `payload["result"]`, so the platform is known to
    use that envelope somewhere. Zero positions is the most dangerous possible
    misreading here: the book computes the whole bankroll as free and
    `affordable()` waves through an order that should have been refused.

    Two readers rejected this at triage because all 41 captured responses have
    the flat shape. That is a fact about today's data, not about the function
    -- and their platform ships several times a day.
    """
    mod = _paper(tmp_path, monkeypatch)

    flat = {"positions": [{"notional_usdc": 5.0, "is_paper": True}]}
    wrapped = {"result": flat}
    assert mod.position_rows(flat) == flat["positions"]
    assert mod.position_rows(wrapped) == flat["positions"], (
        "the result envelope is the shape buy() already unwraps in this same "
        "file; reading it as no positions frees the whole bankroll")

    # An empty book is a legitimate answer and must stay one.
    assert mod.position_rows({"positions": []}) == []

    # Anything else is a read this function cannot interpret, and the one
    # thing it must not do is answer "nothing is deployed".
    for body in ({"data": {"rows": []}}, [], "positions", None):
        with pytest.raises(mod.UnreadableBody):
            mod.position_rows(body)
