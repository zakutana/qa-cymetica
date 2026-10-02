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
import json
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
    # NEX-9999 was asked and never answered -- a question row with no answer
    # row beside it, not merely an empty diary. Matching by id alone (the
    # `type == "answer"` filter dropped) would find this question and hand
    # it back as if it were guidance.
    (tmp_path / "nexus.jsonl").write_text(json.dumps(
        {"type": "question", "id": "NEX-9999",
         "at": "2026-09-24T10:00:00+00:00", "question": "which bot?"}) + "\n",
        encoding="utf-8")
    with pytest.raises(SystemExit, match="no recorded answer"):
        mod.clone("wta_species", "dd206f68", None, "NEX-9999", confirm=True)
    with pytest.raises(SystemExit, match="no recorded answer"):
        mod._guidance("NEX-9999")

    ours = mod._guidance(None)
    assert ours["id"] is None and "ours" in ours["note"]

    # An answer from the shallow lane is recorded guidance too, for a card
    # order as for a clone: paper.py read the deep diary alone, so a card pick
    # from nexus_shallow.jsonl opened a room and then was refused as "not a
    # recorded Nexus answer" (deep pass 2026-09-27, L04, 3/3).
    (tmp_path / "nexus_shallow.jsonl").write_text(json.dumps(
        {"type": "answer", "id": "NEX-0094", "at": "2026-09-24T10:00:00+00:00",
         "text": "Buy card x."}) + "\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "paper_guidance", REPO / "scripts" / "paper.py")
    paper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(paper)
    assert paper._guidance("NEX-0094")["id"] == "NEX-0094"
    with pytest.raises(SystemExit, match="not a recorded Nexus answer"):
        paper._guidance("NEX-9999")


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
def test_a_refusal_is_recorded_in_their_words(tmp_path, monkeypatch):
    """CLN-0017, 2026-09-22 13:39 UTC: a paper clone refused HTTP 400, and the
    record said `"response": "{}"`. NEXT.md then planned a report about a
    refusal "with an empty body". The capture held
    `{"detail": "Invalid clone request. Please try again."}` -- `_served`
    returned `{}` for every status but 200, and that `{}` is what went into
    the record.

    The same line wrote CLN-0003 on 2026-09-10: `/fund` refused 401 and the
    record said `{}`, so #89 told Cymetica the refusal was "a bare 401 with an
    empty body". It carried `UNAUTHORIZED` and "Valid JWT token required".

    The fields read off a SUCCESS stay empty on a refusal -- an error body
    carries no instance id -- but `response` is what they said, whatever the
    status."""
    import ast

    mod = _clone(tmp_path, monkeypatch)
    said = {"detail": "Invalid clone request. Please try again."}

    class Client:
        def post(self, *args, **kwargs):
            return _Response(400, said)

        def close(self):
            pass

    _offline(mod, monkeypatch, Client())
    mod.clone("wta_species", "23441934", None, None, confirm=True)
    outcome = [r for r in mod.load() if r.get("type") == "outcome"]
    assert len(outcome) == 1, outcome
    row = outcome[0]
    assert (row["outcome"], row["http_status"]) == ("rejected", 400)
    assert row["clone_instance_id"] is None and row["is_paper"] is None
    assert "Invalid clone request" in row["response"], (
        f"their refusal was recorded as {row['response']!r}, not in their words")

    # Nested, as /fund answered on 2026-09-10, and a body that is not JSON.
    nested = {"detail": {"error": {"code": "UNAUTHORIZED",
                                   "message": "Valid JWT token required"}}}
    assert "Valid JWT token required" in mod._recorded(_Response(401, nested), {})
    assert "bad gateway" in mod._recorded(_Response(502, readable=False), {})

    # And fund() and enable() write theirs through the same door: none of the
    # three may put `json.dumps(served)` into a record again.
    tree = ast.parse((REPO / "scripts" / "clone.py").read_text(encoding="utf-8"))
    for fn in (n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name in ("clone", "fund", "enable")):
        dumped = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                  and getattr(c.func, "attr", None) == "dumps"
                  and any(getattr(a, "id", None) == "served" for a in c.args)]
        assert not dumped, (
            f"{fn.name}() records json.dumps(served) at line(s) {dumped}: "
            f"`served` is empty on a refusal, so the record loses their words")


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

    # A02, deep pass of 2026-09-22 evening (3/3): a header name is not
    # case-sensitive, and their own ApiKeyAuth scheme is named "X-API-Key".
    # Compared as written, a route declaring the key through that scheme read
    # as publishing only `authorization` -- a false fail on #89's row.
    theirs = {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}}
    gap = surface.credential_gap({"/api/v1/cloned-bots/{instance_id}/fund": {
        "post": {"security": [{"ApiKeyAuth": []}]}}}, theirs)
    assert "POST /api/v1/cloned-bots/{instance_id}/fund" in gap["accepts"], gap
    gap = surface.credential_gap({"/api/v1/cloned-bots/{instance_id}/fund": {
        "post": {"parameters": [{"in": "header", "name": "X-API-Key"}]}}}, {})
    assert "POST /api/v1/cloned-bots/{instance_id}/fund" in gap["accepts"], gap

    # C03 (deep pass of 2026-09-24): read the first check's first conclude(
    # only, and only with the closing quote -- so the claim could come back
    # in the check that feeds #89's row since the split, or mid-sentence, and
    # stay green. Every string in every test_one_credential* check, the
    # docstring's history aside, in any spelling.
    import ast
    import re

    source = (REPO / "tests" / "rest" / "test_cloned_bots_surface.py").read_text(encoding="utf-8")
    claim = re.compile(r"401\s+(?:with\s+an\s+empty\s+body|and\s+no\s+body)", re.I)
    checks = [node for node in ast.parse(source).body
              if isinstance(node, ast.FunctionDef)
              and node.name.startswith("test_one_credential")]
    assert len(checks) >= 2, [c.name for c in checks]
    for check in checks:
        doc = ast.get_docstring(check, clean=False)
        said = [n.value for n in ast.walk(check)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value != doc and claim.search(n.value)]
        assert not said, (check.name, said,
                          "a failure sentence asserts a live 401 the check "
                          "never measures")


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

    # V04, deep pass of 2026-09-19 (2/3): a documented PATH was the end of the
    # question, so an undocumented METHOD on it -- PATCH served where their
    # document names only GET -- passed. Read against their methods when the
    # document gives them.
    with_methods = {"/api/v1/cloned-bots/{instance_id}/settings": {"GET"},
                    "/api/v1/cloned-bots/{instance_id}/fund": {"POST"}}
    hidden = served_but_undocumented(
        {"/api/v1/cloned-bots/abc/settings": "GET, PATCH",
         "/api/v1/cloned-bots/abc/fund": "POST"}, with_methods)
    assert [(h["path"], h["methods"]) for h in hidden] == [
        ("/api/v1/cloned-bots/{instance_id}/settings", "PATCH")], hidden


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_undocumented_method_on_a_documented_path_is_reported_as_what_it_is():
    """A13, deep pass of 2026-09-21, driven through the whole check.

    (1) V04 made an undocumented METHOD on a documented path a finding, but
    the sentence stayed the one written for paths: "none of those paths is in
    /openapi-public.json" -- false of a path their document lists, and it goes
    on their tracker. (2) The probe is a GET, so a path whose GET is served
    answers 200, names nothing, and a PATCH beside it was never compared.
    OPTIONS is a read method at every tier; its 405 is the same router
    evidence, so it is asked when the GET named nothing. Nothing but GET and
    OPTIONS may leave this stub -- it has no other verb.

    Considered folding into test_only_a_405_counts_as_a_route_that_exists;
    that one drives served_but_undocumented() alone, and neither half of this
    is reachable without the probe loop and the reason together.
    """
    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    spec = importlib.util.spec_from_file_location(
        "cloned_surface_methods", REPO / "tests" / "rest" / "test_cloned_bots_surface.py")
    surface = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(surface)

    class _Answer:
        def __init__(self, status, body=None, allow=None):
            self.status_code, self._body = status, body
            self.headers = {"allow": allow} if allow else {}

        def json(self):
            return self._body

    class _Rest:
        def __init__(self, documented, gets, options):
            self.documented, self.gets, self.options_ = documented, gets, options
            self.asked = []

        def get(self, path, params=None):
            self.asked.append(("GET", path))
            if path == surface.OPENAPI:
                return _Answer(200, {"paths": self.documented})
            if path.endswith("/my-clones"):
                return _Answer(200, [{"id": "abc"}])
            return self.gets.get(path) or _Answer(404)

        def options(self, path, **kwargs):
            self.asked.append(("OPTIONS", path))
            return self.options_.get(path) or _Answer(404)

    def run(rest):
        CURRENT_MEASUREMENT.set(None)
        try:
            surface.test_every_cloned_bot_route_they_serve_is_one_they_document(rest)
            verdict = "passed"
        except AssertionError:
            verdict = "failed"
        except Inconclusive:
            verdict = "inconclusive"
        measured = CURRENT_MEASUREMENT.get()
        CURRENT_MEASUREMENT.set(None)  # not this meta test's own record
        return verdict, (measured.reason if measured else "")

    base = "/api/v1/cloned-bots/abc"
    # (1) Their document lists POST on /fund; the router also names DELETE.
    rest = _Rest({"/api/v1/cloned-bots/{instance_id}/fund": {"post": {}}},
                 {f"{base}/fund": _Answer(405, allow="POST, DELETE")}, {})
    verdict, reason = run(rest)
    assert verdict == "failed", (verdict, reason)
    assert "none of those paths" not in reason, (
        f"a path their document lists was reported as missing from it: {reason}")
    assert "DELETE" in reason and "POST" in reason, reason
    assert "cannot start" not in reason, reason

    # (2) A served GET on /settings answers 200; the PATCH beside it is only
    # seen by asking OPTIONS.
    rest = _Rest({"/api/v1/cloned-bots/{instance_id}/settings": {"get": {}}},
                 {f"{base}/settings": _Answer(200, {"is_trading": False})},
                 {f"{base}/settings": _Answer(405, allow="PATCH")})
    verdict, reason = run(rest)
    assert verdict == "failed" and "PATCH" in reason, (verdict, reason)
    assert {verb for verb, _ in rest.asked} <= {"GET", "OPTIONS"}, rest.asked

    # A path absent from their document still reads as one.
    rest = _Rest({"/api/v1/cloned-bots/{instance_id}/fund": {"post": {}}},
                 {f"{base}/settings": _Answer(405, allow="PATCH")}, {})
    verdict, reason = run(rest)
    assert verdict == "failed" and "none of those paths" in reason, reason
    assert "cannot start" in reason, reason

    # And an OPTIONS that names nothing leaves the check where it was.
    rest = _Rest({"/api/v1/cloned-bots/{instance_id}/settings": {"get": {}}},
                 {f"{base}/settings": _Answer(200, {})},
                 {f"{base}/settings": _Answer(200)})
    assert run(rest)[0] == "inconclusive"


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_we_started_once_is_never_started_again(tmp_path, monkeypatch):
    """The plan's V2 (review of 2026-09-23): a bot that stopped -- paused by
    us, halted by their guard, or for no reason anyone can read -- is never
    re-enabled. CLN-0007 restarted Perceptron Oracle on 2026-09-11 after it
    had halted, and its record then ran on as one experiment across two
    starts. A new experiment is a new clone. Refused before any client is
    built, so nothing is asked of their side; a pause is still allowed."""
    mod = _clone(tmp_path, monkeypatch)
    mod._append({"id": "CLN-0001", "type": "intent", "kind": "enable",
                 "instance_id": "inst-1"})
    mod._append({"id": "CLN-0001", "type": "outcome", "kind": "enable",
                 "outcome": "accepted", "http_status": 200})

    class Reached(Exception):
        pass

    def no_client(*a, **k):
        raise Reached("a client was built")
    monkeypatch.setattr(mod, "build_client", no_client)

    with pytest.raises(SystemExit, match="never started again"):
        mod.enable("inst-1", True)
    # The first start of another bot, and a pause of this one, go on to their
    # side as before.
    with pytest.raises(Reached):
        mod.enable("inst-2", True)
    with pytest.raises(Reached):
        mod.enable("inst-1", True, enabled=False)


# --- the settings PATCH: the paper floor before its first caller (V5, B7) ----

PAPER_ROW = {"id": "inst-1", "is_paper": True, "is_trading": False,
             "execution_economics": {"execution_class": "PAPER_SIMULATION"}}


def _ours(mod, instance="inst-1", is_paper=True, outcome="accepted"):
    """Our clone record: the clone that made `instance`, as clone() writes it."""
    cid = mod._next_id(mod.load())
    mod._append({"id": cid, "type": "intent", "source_type": "wta_species",
                 "source_id": "sp-1", "paper": True})
    mod._append({"id": cid, "type": "outcome", "outcome": outcome,
                 "http_status": 200, "clone_instance_id": instance,
                 "is_paper": is_paper})


class _Tripwire:
    """Their side, where a PATCH or a toggle that is actually sent is the
    failure. `rows` is what my-clones answers; `sent` fills only in a positive
    control, which passes the answer it wants."""

    def __init__(self, rows=None, status=200, patch=None, post=None,
                delete=None):
        self.rows, self.status, self.patch_answer = rows, status, patch
        self.post_answer = post
        self.delete_answer = delete
        self.sent = []

    def get(self, path, params=None):
        return _Response(self.status, self.rows)

    def patch(self, path, json=None, **kwargs):
        if self.patch_answer is None:
            raise AssertionError(f"a settings PATCH was sent: {path} {json}")
        self.sent.append((path, json))
        return self.patch_answer

    def post(self, path, json=None, params=None, **kwargs):
        if self.post_answer is None:
            raise AssertionError(f"a toggle was sent: {path} {params}")
        self.sent.append((path, params))
        return self.post_answer

    def delete(self, path, **kwargs):
        if self.delete_answer is None:
            raise AssertionError(f"a DELETE was sent: {path}")
        self.sent.append((path,))
        return self.delete_answer

    def close(self):
        pass


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_settings_patch_carries_only_the_fields_the_grid_walks(
        tmp_path, monkeypatch):
    """B7 of the 2026-09-23 review was dropped only because nothing sent the
    PATCH; V5 adds the caller, so the floor comes first.

    The transport's MUTATE branch never reads `executable_params` -- it is a
    PROBE declaration -- so what a PATCH may carry is `SAFE_SETTINGS` in
    clone.py, checked before a client exists. `is_trading` is left out on
    purpose: `is_trading: true` is a START through a second door, past
    `enable()`'s two-statement floor and its never-restart rule. The arb, the
    on-chain share and the market lists are not ours to move at all.

    Refused before anything is built: a refusal that broke would otherwise
    reach their side (`_no_client`)."""
    import yaml

    mod = _clone(tmp_path, monkeypatch)
    _no_client(mod, monkeypatch)
    _ours(mod)

    grid = {"stop_loss_pct", "take_profit_pct", "max_position_pct",
            "max_open_positions", "min_ai_confidence"}
    assert grid <= mod.SAFE_SETTINGS, mod.SAFE_SETTINGS
    unsafe = {"is_trading", "arb_strategy_enabled", "onchain_pct",
              "strategy_override", "catalog_watchlist", "custom_avatar_url",
              "name"}
    assert not (unsafe & mod.SAFE_SETTINGS), unsafe & mod.SAFE_SETTINGS
    # 2026-09-28: the two market lists may be switched OFF and nothing else.
    # A clone that never saved them (null) trades BTC/ETH 5-min epochs while
    # their page draws both boxes unchecked, so a pure event-card bot needs
    # "NONE" said out loud -- the value their own page sends for no boxes.
    assert {"perpetual_markets", "custom_markets"} <= mod.SAFE_SETTINGS
    for key in ("perpetual_markets", "custom_markets"):
        assert mod.safe_settings({key: "NONE"}) == {key: "NONE"}
        for opened in ("BTC", "BTC,ETH", "", None, True, ["BTC"]):
            with pytest.raises(SystemExit, match=key):
                mod.safe_settings({key: opened})

    raw = yaml.safe_load((REPO / "components.yaml").read_text(encoding="utf-8"))
    rule = next(e for e in raw["endpoints"] if e["id"] == "cloned_bots.settings")
    # Both sets: the transport's closed-body wall lets through executable |
    # inert, so an inert_params entry would widen the PATCH past this list
    # (deep pass 2026-09-24, G05).
    assert (set(rule["executable_params"]) | set(rule.get("inert_params") or [])
            == set(mod.SAFE_SETTINGS)), (
        "components.yaml and clone.py disagree about what a PATCH may carry")

    for changes, said in (({"is_trading": True}, "is_trading"),
                          ({"onchain_pct": 0}, "onchain_pct"),
                          ({"arb_strategy_enabled": True}, "arb_strategy"),
                          ({"stop_loss_pct": 5, "name": "x"}, "name"),
                          ({}, "nothing"),
                          ({"stop_loss_pct": 35}, "stop_loss_pct"),
                          ({"take_profit_pct": 1}, "take_profit_pct"),
                          ({"min_ai_confidence": 1.5}, "min_ai_confidence"),
                          ({"max_open_positions": -1}, "max_open_positions"),
                          ({"event_card_trading_enabled": "yes"},
                           "event_card_trading_enabled")):
        with pytest.raises(SystemExit, match=said):
            mod.settings("inst-1", changes, confirm=True)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_settings_patch_needs_our_paper_record_theirs_and_no_running_room(
        tmp_path, monkeypatch):
    """A PATCH to /settings carries no `paper` -- their schema rejects unknown
    fields by name -- so the transport's required_flags has nothing to read.
    The floor is enable()'s, and one more: the instance must be a PAPER clone
    by OUR record (an accepted clone whose outcome said is_paper true), and by
    THEIR row now (is_paper and execution_class agreeing, `startable`). And a
    room running on it holds its settings still: a variant is a new room, and
    changing the one being measured would judge two settings as one.

    Every refusal is proved against a tripwire whose `patch` raises."""
    mod = _clone(tmp_path, monkeypatch)
    change = {"stop_loss_pct": 8}

    # Not a clone of ours at all, and one our record does not call paper.
    _no_client(mod, monkeypatch)
    with pytest.raises(SystemExit, match="our record"):
        mod.settings("inst-1", change, confirm=True)
    _ours(mod, instance="inst-live", is_paper=False)
    with pytest.raises(SystemExit, match="our record"):
        mod.settings("inst-live", change, confirm=True)
    _ours(mod, instance="inst-refused", outcome="rejected")
    with pytest.raises(SystemExit, match="our record"):
        mod.settings("inst-refused", change, confirm=True)

    # Ours and paper, but a room is running on it.
    _ours(mod)
    import qa.rooms as qa_rooms
    rows = [{"type": "strategy", "id": "STR-0001", "origin": "NEX-0001",
             "title": "bot", "kind": "bot", "ref": "sp-1", "at": "2026-09-23T00:00:00+00:00"},
            {"type": "plan", "room": "STR-0001", "legs": [
                {"kind": "bot", "ref": "inst-1", "side": "bull", "share": 1.0}],
             "at": "2026-09-23T00:00:01+00:00"},
            {"type": "status", "room": "STR-0001", "status": "running",
             "why": "x", "at": "2026-09-23T00:00:02+00:00"}]
    (tmp_path / qa_rooms.path().name).write_text(
        "".join(__import__("json").dumps(r) + "\n" for r in rows), encoding="utf-8")
    with pytest.raises(SystemExit, match="STR-0001"):
        mod.settings("inst-1", change, confirm=True)
    with open(tmp_path / qa_rooms.path().name, "a", encoding="utf-8") as handle:
        handle.write(__import__("json").dumps(
            {"type": "status", "room": "STR-0001", "status": "stopped",
             "why": "window closed", "at": "2026-09-23T00:00:03+00:00"}) + "\n")

    # Their row: not paper, a live execution class, unreadable, not listed.
    for rows_, status in (([{**PAPER_ROW, "is_paper": False}], 200),
                          ([{**PAPER_ROW, "execution_economics":
                             {"execution_class": "LIVE_ONCHAIN"}}], 200),
                          (None, 503),
                          ([], 200)):
        _offline(mod, monkeypatch, _Tripwire(rows_, status))
        with pytest.raises(SystemExit):
            mod.settings("inst-1", change, confirm=True)
    assert not [r for r in mod.load() if r.get("kind") == "settings"], (
        "a refused PATCH left a record")

    # The positive control: all three agree, and the chain is written.
    wire = _Tripwire([PAPER_ROW], 200, patch=_Response(200, {"success": True}))
    _offline(mod, monkeypatch, wire)
    mod.settings("inst-1", change, confirm=True)
    assert wire.sent == [("/api/v1/cloned-bots/inst-1/settings", change)], wire.sent
    chain = [r for r in mod.load() if r.get("kind") == "settings"]
    assert [r["type"] for r in chain] == ["intent", "outcome", "after"], chain
    assert chain[0]["body"] == change and chain[0]["their_is_paper"] is True
    assert chain[1]["outcome"] == "accepted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_release_needs_our_paper_record_theirs_and_no_running_room(
        tmp_path, monkeypatch):
    """DELETE carries no body at all -- one door further than toggle-trading
    -- so required_flags has nothing to read either. The floor is three
    checks, the same shape as settings()'s: our record made this instance as
    a paper clone, no room of ours is RUNNING on it (a stopped room's bot is
    exactly what release exists to free), and their row says paper twice over
    right now (`startable`).

    Every refusal is proved against a tripwire whose `delete` raises."""
    mod = _clone(tmp_path, monkeypatch)

    # Not a clone of ours at all, and one our record does not call paper.
    _no_client(mod, monkeypatch)
    with pytest.raises(SystemExit, match="our record"):
        mod.release("inst-1", confirm=True)
    _ours(mod, instance="inst-live", is_paper=False)
    with pytest.raises(SystemExit, match="our record"):
        mod.release("inst-live", confirm=True)

    # Not confirmed at all -- refused before our record is even read.
    with pytest.raises(SystemExit, match="confirm"):
        mod.release("inst-1", confirm=False)

    # Ours and paper, but a room is RUNNING on it: release is not a pause.
    _ours(mod)
    import qa.rooms as qa_rooms
    import json as _json
    rows = [{"type": "strategy", "id": "STR-0001", "origin": "NEX-0001",
             "title": "bot", "kind": "bot", "ref": "sp-1", "at": "2026-09-23T00:00:00+00:00"},
            {"type": "plan", "room": "STR-0001", "legs": [
                {"kind": "bot", "ref": "inst-1", "side": "bull", "share": 1.0}],
             "at": "2026-09-23T00:00:01+00:00"},
            {"type": "status", "room": "STR-0001", "status": "running",
             "why": "x", "at": "2026-09-23T00:00:02+00:00"}]
    (tmp_path / qa_rooms.path().name).write_text(
        "".join(_json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    with pytest.raises(SystemExit, match="STR-0001"):
        mod.release("inst-1", confirm=True)

    # Stopped: a release is exactly what closes out a stopped room's bot.
    with open(tmp_path / qa_rooms.path().name, "a", encoding="utf-8") as handle:
        handle.write(_json.dumps(
            {"type": "status", "room": "STR-0001", "status": "stopped",
             "why": "window closed", "at": "2026-09-23T00:00:03+00:00"}) + "\n")

    # Their row: not paper, a live execution class, unreadable, not listed.
    for rows_, status in (([{**PAPER_ROW, "is_paper": False}], 200),
                          ([{**PAPER_ROW, "execution_economics":
                             {"execution_class": "LIVE_ONCHAIN"}}], 200),
                          (None, 503),
                          ([], 200)):
        _offline(mod, monkeypatch, _Tripwire(rows_, status))
        with pytest.raises(SystemExit):
            mod.release("inst-1", confirm=True)
    assert not [r for r in mod.load() if r.get("kind") == "release"], (
        "a refused DELETE left a record")

    # The positive control: all three agree, and a 204 with no body is
    # accepted -- the ordinary shape for a delete that worked.
    wire = _Tripwire([PAPER_ROW], 200, delete=_Response(204, None))
    _offline(mod, monkeypatch, wire)
    said = mod.release("inst-1", confirm=True)
    assert wire.sent == [("/api/v1/cloned-bots/inst-1",)], wire.sent
    assert said["outcome"] == "accepted" and said["http_status"] == 204
    chain = [r for r in mod.load() if r.get("kind") == "release"]
    assert [r["type"] for r in chain] == ["intent", "outcome", "after"], chain
    assert chain[0]["their_is_paper"] is True
    assert chain[1]["outcome"] == "accepted" and chain[1]["http_status"] == 204


def _switch(mod, kind, instance="inst-1", outcome="accepted", body=None):
    """One of clone.py's own chains on `instance`: enable, disable, settings."""
    cid = mod._next_id(mod.load())
    mod._append({"id": cid, "type": "intent", "kind": kind,
                 "instance_id": instance, **({"body": body} if body else {})})
    mod._append({"id": cid, "type": "outcome", "kind": kind,
                 "outcome": outcome, "http_status": 200})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_started_clone_starts_again_only_as_a_new_variant(tmp_path, monkeypatch):
    """V5 of plan v2 (REPLY-0049): one paper clone per species per account, so
    a species' settings are walked in time on its ONE clone -- which means
    starting a clone that has run before. V2's rule stays the floor: a bot
    that stopped is not started again as the SAME experiment. It may start
    again only as a new one, and only in this order, each step accepted:

        our pause  ->  a settings change after it  ->  no room running on it

    and never after a halt that was not ours (their guard, or unexplained):
    what stopped it is a finding, not a variant.

    Every refusal is proved from our record before a client exists
    (`_no_client`), so a floor that broke fails here and toggles nothing."""
    mod = _clone(tmp_path, monkeypatch)
    _ours(mod)
    _switch(mod, "enable")

    _no_client(mod, monkeypatch)
    # Started, never paused: V2's refusal, in its own words.
    with pytest.raises(SystemExit, match="never started again"):
        mod.enable("inst-1", True)
    # A settings change BEFORE our pause changes the experiment that ran.
    _switch(mod, "settings", body={"stop_loss_pct": 5.0})
    _switch(mod, "disable")
    with pytest.raises(SystemExit, match="settings"):
        mod.enable("inst-1", True)
    # Paused by us, and the change after it was refused by them.
    _switch(mod, "settings", outcome="rejected", body={"stop_loss_pct": 5.0})
    with pytest.raises(SystemExit, match="settings"):
        mod.enable("inst-1", True)

    # Paused by us, an accepted change after it -- but a room runs on it.
    _switch(mod, "settings", body={"stop_loss_pct": 5.0})
    import qa.rooms as qa_rooms
    import json as _json
    running = [{"type": "strategy", "id": "STR-0002", "origin": "NEX-0001",
                "title": "bot", "kind": "bot", "ref": "sp-1",
                "at": "2026-09-23T00:00:00+00:00"},
               {"type": "plan", "room": "STR-0002", "legs": [
                   {"kind": "bot", "ref": "inst-1", "side": "bull", "share": 1.0}],
                "at": "2026-09-23T00:00:01+00:00"},
               {"type": "status", "room": "STR-0002", "status": "running",
                "why": "x", "at": "2026-09-23T00:00:02+00:00"}]
    (tmp_path / qa_rooms.path().name).write_text(
        "".join(_json.dumps(r) + "\n" for r in running), encoding="utf-8")
    with pytest.raises(SystemExit, match="STR-0002"):
        mod.enable("inst-1", True)
    (tmp_path / qa_rooms.path().name).write_text("", encoding="utf-8")

    # A halt that was not ours: the sampler saw it stop at a loss before our
    # pause reached it. Never restarted, whatever came after.
    samples = tmp_path / qa_rooms.samples_path().name
    halted = [{"type": "sample", "kind": "bot", "instance_id": "inst-1",
               "at": "2026-09-22T20:00:00+00:00", "is_trading": False,
               "total_profit_usdc": "-24.02"}]
    samples.write_text("".join(_json.dumps(r) + "\n" for r in halted),
                       encoding="utf-8")
    stamped = [dict(r, at="2026-09-22T13:38:30+00:00") if r.get("kind") == "enable"
               else dict(r, at="2026-09-22T21:00:00+00:00") for r in mod.load()]
    mod.path().write_text("".join(_json.dumps(r) + "\n" for r in stamped),
                          encoding="utf-8")
    with pytest.raises(SystemExit, match="their_guard"):
        mod.enable("inst-1", True)
    # And a halt nobody can explain -- stopped at a profit, not by us -- is
    # never restarted either; only a their-guard halt was seeded, so a
    # filter narrowed to their_guard passed (deep pass 2026-09-24, G06, 3/3).
    samples.write_text("".join(_json.dumps({**r, "total_profit_usdc": "3.1"}) + "\n"
                               for r in halted), encoding="utf-8")
    with pytest.raises(SystemExit, match="unexplained"):
        mod.enable("inst-1", True)
    samples.write_text("", encoding="utf-8")

    # All four hold: the floor lets it through to their side, where the
    # two-statement paper floor and the toggle follow as for a first start.
    wire = _Tripwire([{**PAPER_ROW, "total_profit_usdc": "3.5",
                       "current_balance_usdc": "243.5"}], 200,
                     post=_Response(200, {**PAPER_ROW, "is_trading": True}))
    _offline(mod, monkeypatch, wire)
    mod.enable("inst-1", True)
    assert wire.sent == [("/api/v1/cloned-bots/inst-1/toggle-trading",
                          {"enabled": "true"})], wire.sent
    intent = [r for r in mod.load() if r.get("kind") == "enable"
              and r.get("type") == "intent"][-1]
    # Item 5 of V5: the variant's verdict starts at this restart, so the
    # restart records what the bot had made so far, off the same row.
    assert intent["bot_profit_usdc"] == "3.5", intent
    assert intent["bot_balance_usdc"] == "243.5", intent

    # And once more: the variant just started, so the next start needs its
    # own pause and its own change again.
    _no_client(mod, monkeypatch)
    with pytest.raises(SystemExit, match="never started again"):
        mod.enable("inst-1", True)

    # Deep pass 2026-10-02, R02 then R01. A write that fails AFTER it may have left
    # (a read timeout, a stream cut) is `unknown`, never `not_sent` -- rule 9; only a
    # refusal before the network (the guard, a connection never made) is `not_sent`.
    # And a start we cannot prove did not happen is still a start: the sampler saw
    # the bot trade and stop at a loss, which is their guard's stop and a finding,
    # whatever our own record says about the enable.
    import httpx
    from qa.safety import SafetyViolation

    class _Drops(_Tripwire):
        def __init__(self, failure, rows):
            super().__init__(rows, 200)
            self.failure = failure

        def post(self, path, json=None, params=None, **kwargs):
            raise self.failure

    _ours(mod, instance="inst-2")
    for failure, outcome in ((SafetyViolation("refused before the network"), "not_sent"),
                             (httpx.ConnectError("never connected"), "not_sent"),
                             (httpx.ReadTimeout("slow after the request left"), "unknown"),
                             (httpx.RemoteProtocolError("peer closed"), "unknown")):
        # Each attempt needs the floor open: a restart after an unknown start is
        # refused, so a fresh instance per case.
        instance = f"inst-{outcome}-{type(failure).__name__}"
        _ours(mod, instance=instance)
        _offline(mod, monkeypatch, _Drops(failure, [{**PAPER_ROW, "id": instance}]))
        with pytest.raises(type(failure)):
            mod.enable(instance, True)
        last = [r for r in mod.load() if r.get("type") == "outcome"
                and r.get("kind") == "enable"][-1]
        assert last["outcome"] == outcome, (type(failure).__name__, last)

    # inst-2: an enable the platform may have taken (unknown), then the sampler's
    # trading-then-stopped-at-a-loss. restart_refusal read only ACCEPTED enables and
    # returned `a first start` before it ever looked at the sampler.
    _switch(mod, "enable", instance="inst-2", outcome="unknown")
    samples.write_text("".join(_json.dumps(r) + "\n" for r in (
        {"type": "sample", "kind": "bot", "instance_id": "inst-2",
         "at": "2026-10-02T10:00:00+00:00", "is_trading": True},
        {"type": "sample", "kind": "bot", "instance_id": "inst-2",
         "at": "2026-10-02T12:00:00+00:00", "is_trading": False,
         "total_profit_usdc": "-23.85"})), encoding="utf-8")
    assert "their_guard" in (mod.restart_refusal("inst-2") or ""), (
        "a bot their guard stopped was open to a restart because our enable was not accepted")
    # A start that never reached them is still a first start: nothing to refuse.
    _ours(mod, instance="inst-4")
    _switch(mod, "enable", instance="inst-4", outcome="not_sent")
    assert mod.restart_refusal("inst-4") is None
    samples.write_text("", encoding="utf-8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_transport_holds_a_settings_patch_to_its_declared_fields():
    """The second, independent floor: at MUTATE the transport refuses a
    settings PATCH carrying a field components.yaml does not declare -- so
    somebody who edits SAFE_SETTINGS in clone.py still meets the wall, and
    `is_trading` or `onchain_pct` never reach their side from any caller."""
    import httpx

    from qa.safety import (CURRENT_TIER, EndpointRegistry, SafetyTransport,
                           SafetyViolation)

    class Inner(httpx.BaseTransport):
        def handle_request(self, request):
            raise AssertionError("the request reached the network")

    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    transport = SafetyTransport(Inner(), registry)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for body in ({"is_trading": True}, {"onchain_pct": 0},
                     {"stop_loss_pct": 8, "arb_strategy_enabled": True}):
            request = httpx.Request(
                "PATCH", "https://cymetica.com/api/v1/cloned-bots/inst-1/settings",
                json=body)
            with pytest.raises(SafetyViolation, match="not declared"):
                transport.handle_request(request)
        fine = httpx.Request(
            "PATCH", "https://cymetica.com/api/v1/cloned-bots/inst-1/settings",
            json={"stop_loss_pct": 8})
        with pytest.raises(AssertionError, match="reached the network"):
            transport.handle_request(fine)
    finally:
        CURRENT_TIER.reset(token)
