"""CLONE: the source_type is in the key, and the paper flag is theirs to confirm.

`GET /api/v1/cloned-bots/available` returns two groups, `wta_species` and
`perpetual_agents`, and every row inside them carries `source_type: null`.
CloneBotRequest requires that field and its enum is singular --
`perpetual_agent`. So the type lives in the key of the group, and reading it
off the row sends null and makes their 422 look like their bug.

The second thing pinned here is that `is_paper` in the RECORD is whatever they
returned, never what we asked for. We send `paper` and `is_paper` both true
because their schema publishes both names and we cannot tell from outside
which one the server reads; the evidence that it worked is their answer, and
copying our own request into the outcome would turn an assumption into a
record that looks like a measurement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _clone(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "clone_under_test", REPO / "scripts" / "clone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Their real shape, from the 20:0x read: groups, null source_type on the rows.
AVAILABLE = {
    "wta_species": [
        {"id": "dd206f68", "name": "MACD Hunter", "source_type": None},
        {"id": "70a47f2a", "name": "RSI Sniper", "source_type": None},
    ],
    "perpetual_agents": [
        {"id": "e1251539", "name": "Liquidation Hunter", "source_type": None},
    ],
    "total_count": 3,
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_source_type_comes_from_the_group_not_from_the_row(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)

    bots = {b["name"]: b["source_type"] for b in mod.available_bots(AVAILABLE)}
    assert bots == {"MACD Hunter": "wta_species",
                    "RSI Sniper": "wta_species",
                    # Singular. Their group key is plural and their enum is
                    # not, and sending the key straight through is a 422 we
                    # would have read as their defect.
                    "Liquidation Hunter": "perpetual_agent"}

    # `total_count` is not a group of bots, and neither is anything else they
    # add later. An unknown key is skipped, not guessed at.
    assert len(mod.available_bots({**AVAILABLE, "featured": [{"id": "x"}]})) == 3

    # The result envelope, which buy() in paper.py already unwraps elsewhere.
    assert len(mod.available_bots({"result": AVAILABLE})) == 3


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_my_clones_is_a_bare_list_and_an_empty_one_is_not_an_absent_one(
        tmp_path, monkeypatch):
    """`GET /api/v1/cloned-bots/my-clones?mode=paper` answers `[]`, not an
    object with a `clones` key. Read as a dict it yields nothing, the count
    goes absent, and the after-snapshot cannot show the clone appeared --
    which is the whole evidence that the clone is paper and exists.

    The distinction that matters is the one this repo keeps making: zero
    clones is an answer, and a body we could not read is not.
    """
    mod = _clone(tmp_path, monkeypatch)

    assert mod.clone_rows([]) == []
    assert mod.clone_rows([{"id": "c1"}]) == [{"id": "c1"}]
    assert mod.clone_rows({"clones": [{"id": "c1"}]}) == [{"id": "c1"}]
    assert mod.clone_rows({"result": [{"id": "c1"}]}) == [{"id": "c1"}]
    assert mod.clone_rows({"nothing": "we know"}) is None
    assert mod.clone_rows(None) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_source_type_their_schema_does_not_publish_is_refused(
        tmp_path, monkeypatch):
    """Before the request, so a typo is not spent as a 422 against them.

    A negative control that must not need the thing it tests: until the deep
    pass of 2026-09-11 a refusal that stopped raising let this test build a
    mutate-enabled client and POST a real paper clone. The client it would get
    now fails on being built, so a broken refusal fails here and sends nothing.
    """
    mod = _clone(tmp_path, monkeypatch)
    _no_client(mod, monkeypatch)
    with pytest.raises(SystemExit, match="source_type must be one of"):
        mod.clone("perpetual_agents", "e1251539", None, None, confirm=True)


def _no_client(mod, monkeypatch):
    """A second barrier for a negative control: building a client fails."""
    def refuse(*args, **kwargs):
        raise AssertionError("the refusal did not hold: a live client was built")
    monkeypatch.setattr(mod, "build_client", refuse)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_guidance_that_was_never_answered_is_refused(tmp_path, monkeypatch):
    """A clone naming a Nexus answer that does not exist claims their
    guidance for our own decision. Marked ours is fine; borrowed is not.
    Behind the same second barrier as the source-type refusal."""
    mod = _clone(tmp_path, monkeypatch)
    _no_client(mod, monkeypatch)
    (tmp_path / "nexus.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match="no recorded answer"):
        mod.clone("wta_species", "dd206f68", None, "NEX-9999", confirm=True)

    ours = mod._guidance(None)
    assert ours["id"] is None and "ours" in ours["note"]


def _offline(mod, monkeypatch, client):
    """clone.py with every door to their server replaced by `client`."""
    for name, value in (("load_dotenv", lambda: None),
                        ("install_client_guard", lambda: None),
                        ("identities", lambda: {"trusted": None}),
                        ("build_client", lambda *a, **k: client),
                        ("_snapshot", lambda c: {}),
                        ("_capture", lambda *a, **k: None)):
        monkeypatch.setattr(mod, name, value)


class _Response:
    def __init__(self, status, body=None, readable=True):
        self.status_code, self._body, self._readable = status, body, readable
        self.text = "<html>bad gateway</html>"

    def json(self):
        if not self._readable:
            raise ValueError("not JSON")
        return self._body


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_200_we_cannot_read_still_gets_its_outcome(tmp_path, monkeypatch):
    """R04, deep pass of 2026-09-11. Rule 9: the intent is written before the
    POST, so every path after it owes an outcome. clone(), fund() and enable()
    read `response.json()` on any 200, unguarded, so a 200 whose body is not
    JSON raised after the intent and left it bare -- the shape the comment on
    CLN-0001 in the same function says must not happen. It is `unknown` now:
    they answered, and we cannot say what they made."""
    import ast

    mod = _clone(tmp_path, monkeypatch)

    class Client:
        def post(self, *args, **kwargs):
            return _Response(200, readable=False)

        def close(self):
            pass

    _offline(mod, monkeypatch, Client())
    mod.clone("wta_species", "dd206f68", None, None, confirm=True)
    rows = mod.load()
    outcome = [r for r in rows if r.get("type") == "outcome"]
    assert len(outcome) == 1, f"the intent was left without an outcome: {rows}"
    assert (outcome[0]["outcome"], outcome[0]["http_status"]) == ("unknown", 200)

    tree = ast.parse((REPO / "scripts" / "clone.py").read_text(encoding="utf-8"))
    for fn in (n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name in ("clone", "fund", "enable")):
        direct = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                  and getattr(c.func, "attr", None) == "json"
                  and getattr(getattr(c.func, "value", None), "id", None) == "response"]
        assert not direct, (
            f"{fn.name}() reads response.json() itself at line(s) {direct}, after "
            f"the POST; a body that is not JSON would leave its intent bare")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_switched_on_keeps_its_record_when_the_reread_fails(tmp_path, monkeypatch):
    """R05, deep pass of 2026-09-11. After toggle-trading answered 200, a
    failed my-clones re-read raised "Nothing is started on an unreadable
    answer" about a bot that had just been started, and the after row and
    client.close() never ran -- on the one call that keeps spending after we
    stop watching. The after row now says the re-read failed."""
    mod = _clone(tmp_path, monkeypatch)
    row = {"id": "b1", "is_paper": True, "is_trading": False,
           "current_balance_usdc": 550.0,
           "execution_economics": {"execution_class": "PAPER_SIMULATION"}}
    seen = {"gets": 0, "closed": False}

    class Client:
        def get(self, path, params=None):
            seen["gets"] += 1
            return _Response(200, [row]) if seen["gets"] == 1 else _Response(503)

        def post(self, *args, **kwargs):
            return _Response(200, {"id": "b1", "is_trading": True})

        def close(self):
            seen["closed"] = True

    _offline(mod, monkeypatch, Client())
    mod.enable("b1", confirm=True)
    rows = mod.load()
    after = [r for r in rows if r.get("type") == "after"]
    assert len(after) == 1, f"the switched-on bot has no after row: {rows}"
    assert "failed" in str(after[0].get("reread")), after[0]
    assert after[0].get("their_is_trading") is None
    assert seen["closed"], "the client was left open"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_route_whose_credential_is_declared_by_security_is_not_public():
    """V10, deep pass of 2026-09-11, triage 3/3. credential_gap() read only
    header parameters, so a route whose auth is declared through openapi
    `security` had none and was skipped as public -- move fund's credential
    there without x-api-key and the check passes. The check's failure
    sentence also asserted a live "401 with an empty body" that no branch
    measures."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cloned_surface", REPO / "tests" / "rest" / "test_cloned_bots_surface.py")
    surface = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(surface)

    schemes = {"APIKeyHeader": {"type": "apiKey", "in": "header", "name": "x-api-key"},
               "HTTPBearer": {"type": "http", "scheme": "bearer"}}
    paths = {
        "/api/v1/cloned-bots/clone": {"post": {"security": [{"APIKeyHeader": []}]}},
        "/api/v1/cloned-bots/{instance_id}/fund": {"post": {"security": [{"HTTPBearer": []}]}},
        "/api/v1/cloned-bots/available": {"get": {}},
    }
    gap = surface.credential_gap(paths, schemes)
    assert "POST /api/v1/cloned-bots/clone" in gap["accepts"]
    assert "POST /api/v1/cloned-bots/{instance_id}/fund" in gap["refuses"], (
        "a route authenticated through `security` without the api key was "
        "read as public")
    assert "GET /api/v1/cloned-bots/available" not in {**gap["accepts"], **gap["refuses"]}

    source = (REPO / "tests" / "rest" / "test_cloned_bots_surface.py").read_text(encoding="utf-8")
    assert "401 with an empty body\"" not in source.split("def test_one_credential")[1].split("conclude(")[1], (
        "the failure sentence still asserts a live 401 the check never measures")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hidden_route_says_cannot_start_only_when_it_is_the_one_that_starts():
    """V11, deep pass of 2026-09-11, triage 3/3. Any undocumented route got
    the sentence "an agent ... cannot start it through any documented
    endpoint" -- an undocumented DELETE beside a documented toggle would have
    sent that false claim about starting."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cloned_surface_hidden", REPO / "tests" / "rest" / "test_cloned_bots_surface.py")
    surface = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(surface)

    delete = [{"path": "/api/v1/cloned-bots/{instance_id}", "methods": "DELETE"}]
    settings = [{"path": "/api/v1/cloned-bots/{instance_id}/settings", "methods": "PATCH"}]
    assert "cannot start" not in surface.hidden_reason(delete)
    assert "DELETE /api/v1/cloned-bots/{instance_id}" in surface.hidden_reason(delete)
    assert "cannot start" in surface.hidden_reason(settings)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_a_405_counts_as_a_route_that_exists():
    """The check over their clone surface claims existence and never absence.

    A GET against a path FastAPI routes for another method answers 405 and
    names the method in `Allow`; that is positive evidence the router matched.
    A 404 is not evidence -- an unrouted path and a path that simply has no
    GET look identical from outside -- so a 404 must never reach the verdict.

    Every audit claim this repository has had rejected at triage asserted an
    absence, which is why the direction is pinned by a test rather than left
    to whoever next edits the check.
    """
    from tests.rest.test_cloned_bots_surface import served_but_undocumented

    documented = {"/api/v1/cloned-bots/{instance_id}/fund",
                  "/api/v1/cloned-bots/{instance_id}/go-live"}
    probed = {
        "/api/v1/cloned-bots/abc": "DELETE",
        "/api/v1/cloned-bots/abc/settings": "PATCH",
        "/api/v1/cloned-bots/abc/fund": "POST",
        # 404 under GET. Says nothing either way, and must not be reported.
        "/api/v1/cloned-bots/abc/indicators": None,
    }
    hidden = served_but_undocumented(probed, documented)

    assert [h["path"] for h in hidden] == [
        "/api/v1/cloned-bots/{instance_id}",
        "/api/v1/cloned-bots/{instance_id}/settings"], (
        "a 404 was counted as a missing route, or the uuid was compared "
        "against their {instance_id} template without being normalised")
    assert [h["methods"] for h in hidden] == ["DELETE", "PATCH"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_funding_asks_the_platform_whether_the_bot_is_paper(tmp_path, monkeypatch):
    """The floor for `fund` cannot be a flag, because there is no flag.

    `FundBotRequest` has exactly one property, `amount`. So the transport's
    required_flags floor -- which reads a truthy `paper` out of the body --
    has nothing to read, and the thing that makes funding safe is a property
    of the INSTANCE rather than of the request.

    That leaves the enforcement here, and it has to ask THEM. Reading
    `is_paper` off our own clones.jsonl would let a bot that went live after
    we recorded it be funded from a record that predates the change, which is
    the same shape as judging a fix by a trade placed before it shipped.

    Neither absent nor false may pass: absent is a read we could not
    interpret, and this is the money side, where an unreadable answer is a
    refusal.
    """
    mod = _clone(tmp_path, monkeypatch)

    assert mod.fundable({"id": "c1", "is_paper": True}) is True
    for row in ({"id": "c1", "is_paper": False},
                {"id": "c1", "is_paper": None},
                {"id": "c1"},
                {},
                None):
        assert mod.fundable(row) is False, row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_starting_a_bot_needs_both_of_their_paper_statements(tmp_path, monkeypatch):
    """Enabling autonomous trading is the one call that keeps spending.

    `toggle-trading` carries no body at all -- `enabled` is a query parameter
    -- so required_flags has nothing to read, and its own description says
    "When enabled, bot will trade 100% on-chain" with no paper caveat. The
    instance says something else: `onchain_pct: 100` beside
    `execution_class: "PAPER_SIMULATION"`. The description and the object
    disagree, and only the object is machine-readable.

    So the floor reads BOTH of the object's statements. `is_paper` alone is
    the weaker reading and it is the one that would let a bot whose execution
    class had changed be started anyway -- and unlike a single order, a
    started bot keeps trading after we stop watching.
    """
    mod = _clone(tmp_path, monkeypatch)

    live = {"id": "b1", "is_paper": True,
            "execution_economics": {"execution_class": "PAPER_SIMULATION"}}
    assert mod.startable(live) is True

    for row in (
            # Their two statements, disagreeing. Either one saying live is a
            # refusal; agreement is the only thing that starts a bot.
            {"id": "b1", "is_paper": False,
             "execution_economics": {"execution_class": "PAPER_SIMULATION"}},
            {"id": "b1", "is_paper": True,
             "execution_economics": {"execution_class": "LIVE_ONCHAIN"}},
            # Absent is not permission, on the side that keeps spending.
            {"id": "b1", "is_paper": True, "execution_economics": {}},
            {"id": "b1", "is_paper": True},
            {"id": "b1"},
            {},
            None):
        assert mod.startable(row) is False, row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_clone_record_is_not_written_into_the_paper_trade_log(
        tmp_path, monkeypatch):
    """#87 groups every id in paper.jsonl into intent/outcome/after and reads
    a balance off the intent. A clone landing there is an accepted row with no
    notional, judged as a paper buy that debited nothing."""
    mod = _clone(tmp_path, monkeypatch)
    assert mod.path().name == "clones.jsonl"
    assert mod._next_id([]) == "CLN-0001"
    assert mod._next_id([{"id": "CLN-0003"}, {"id": "TRD-0009"}]) == "CLN-0004"
