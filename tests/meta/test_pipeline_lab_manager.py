"""One file for how the laboratory manager improves, from the operator's feedback.

[operator 2026-10-05] *"mas jako manager laborky nejakou soubor kde si pises
imprvmenty jak lepe runovat laborky podle mych feedbacku?"* and, on hearing it was
three places (the diary, memory files, NEXT.md): *"tak to pekne sjednot ne at je to
na jednom miste tvezlepsovani jako managera laborky"*.

`docs/lab-manager.md` is that file. The diary keeps the raw lines the morning report
reads; every `feedback` and `acted` entry is ALSO written there, so a feedback cannot
be given and left in one place only -- which is how today's was missing for a week.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
FILE = REPO / "docs" / "lab-manager.md"


def _lab(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("QA_LAB_MANAGER_FILE", str(tmp_path / "lab-manager.md"))
    import qa.state
    importlib.reload(qa.state)
    import qa.lab
    importlib.reload(qa.lab)
    return qa.lab, tmp_path / "lab-manager.md"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_feedback_and_acted_reach_the_manager_file_and_nothing_else_does(
        tmp_path, monkeypatch):
    lab, target = _lab(tmp_path, monkeypatch)
    for kind in ("log", "lesson", "next", "telegram"):
        lab.note_entry("LAB-0001", f"a {kind} line", kind=kind)
    assert not target.exists(), "only feedback and acted belong in the file"

    lab.note_entry("LAB-0001", "ja te nechapu ze porad prodelavas na event cartach",
                   kind="feedback")
    lab.note_entry("LAB-0001", "event cards are no longer the first thing a tick reaches for",
                   kind="acted")
    text = target.read_text(encoding="utf-8")
    assert re.search(r"- \d{4}-\d{2}-\d{2} · feedback · ja te nechapu ze porad "
                     r"prodelavas na event cartach", text)
    assert re.search(r"· acted · event cards are no longer", text)
    assert any(r["kind"] == "feedback" for r in lab.entries()), \
        "the diary keeps writing: the morning report reads it"

    # A test that isolates its state and says nothing about the manager's file
    # must not reach the real one (2026-10-06: "a feedback" landed in docs/).
    monkeypatch.delenv("QA_LAB_MANAGER_FILE")
    other = lab.manager_path()
    assert other != FILE and str(other).startswith(str(tmp_path)), other
    monkeypatch.setenv("QA_LAB_MANAGER_FILE", str(target))

    target.write_text("# x\n\n## Open improvements\n\n- first thing\n- second thing\n\n"
                      "## Log\n\n- 2026-10-05 · feedback · y\n", encoding="utf-8")
    assert lab.manager_open_lines() == ["first thing", "second thing"]
    _a_lesson_of_a_section_is_what_that_section_knows(lab, tmp_path, monkeypatch)
    _the_outsider_is_validated_and_its_picks_become_paper_actions()
    _the_outsiders_coins_are_measured_against_btc_and_only_when_due()
    _the_outsider_run_is_recorded_with_prices_read_once(tmp_path)
    _a_seat_is_asked_only_at_a_paper_table_and_never_on_a_dry_run(tmp_path)
    _the_outsider_runs_only_as_a_proven_stranger(tmp_path / "stranger-proof")


def _the_outsider_runs_only_as_a_proven_stranger(tmp_path):
    """2026-10-11: spawned as a subagent from this repository, the outsider quoted our
    CLAUDE.md's first line and our memory index -- it was not a stranger. So it runs as its
    own `claude -p` process from a folder outside the repository, and only after a probe in
    that process showed nothing of ours: a probe that is not logged in, that fails, or that
    quotes any of our markers is not independence. Until a passing probe is on record the
    tick never wakes the outsider."""
    tmp_path.mkdir()
    out = _outsider_script("outsider")
    clean = "I know nothing about Cymetica. I was given no project files or rules."
    assert out.independent(clean, 0) == (True, "")
    for leak in ("# Operating rules for qa-cymetica", "a memory: Verify a workflow is live",
                 "the handle @EventTraderQABot", "its founder Kasian (@DeepHedge)"):
        ok, why = out.independent(f"I know this: {leak}", 0)
        assert not ok and why, leak
    assert out.independent("Not logged in · Please run /login", 1)[0] is False
    assert out.independent(clean, 2)[0] is False, "a failed run passed as a probe"
    rows = [{"type": "probe", "at": "2026-10-11T10:00:00+00:00", "ok": False}]
    assert out.proven(rows) is False
    assert out.proven(rows + [{"type": "probe", "at": "2026-10-11T11:00:00+00:00",
                               "ok": True}]) is True
    assert out.proven(rows + [{"type": "probe", "at": "2026-10-11T11:00:00+00:00",
                               "ok": True},
                              {"type": "probe", "at": "2026-10-11T12:00:00+00:00",
                               "ok": False}]) is False, "the newest probe decides"
    assert out.home().resolve().parts[:len(REPO.resolve().parts)] != REPO.resolve().parts, (
        "the stranger's folder is inside the repository, under its CLAUDE.md")


def _a_lesson_of_a_section_is_what_that_section_knows(lab, tmp_path, monkeypatch):
    """Laboratory v3, P2 ([operator 2026-10-11] "zaznam at nedels stejne veci a udrzujes si a
    vyvojis pamet"): what we know is kept per section, in one file the manager may also correct
    by hand -- `docs/lab-knowledge.md`, ten lines a section at most. A lesson logged for a
    section goes under its heading, newest first; the eleventh pushes the oldest into the
    archive at the bottom with its section and date, never out of the file. A lesson with no
    section stays in the diary only, and a section that does not exist is refused."""
    knowledge = tmp_path / "lab-knowledge.md"
    monkeypatch.setenv("QA_LAB_KNOWLEDGE_FILE", str(knowledge))
    lab.note_entry("LAB-0001", "a lesson about nothing in particular", kind="lesson")
    assert not knowledge.exists(), "a lesson with no section went into the knowledge file"
    try:
        lab.note_entry("LAB-0001", "x", kind="lesson", section="funds")
    except lab.LabError:
        pass
    else:
        raise AssertionError("a lesson for a section that does not exist was taken")

    for n in range(1, 12):
        lab.note_entry("LAB-0001", f"bots lesson {n}", kind="lesson", section="bots")
    lab.note_entry("LAB-0001", "his cards fade after a day", kind="lesson", section="cards")
    known = lab.knowledge()
    assert known["bots"] == [f"bots lesson {n}" for n in range(11, 1, -1)], known["bots"]
    assert known["cards"] == ["his cards fade after a day"]
    assert known["outsider"] == [], "a section with nothing learned is empty, not missing"
    text = knowledge.read_text(encoding="utf-8")
    archive = text.split("## Archive", 1)[1]
    assert "bots lesson 1" in archive and "(bots)" in archive, archive
    assert text.index("## Bots") < text.index("## Archive")
    # The manager corrects a line by hand; what the file says is what is known.
    knowledge.write_text(text.replace("bots lesson 11", "15/40 hits its stop 3x as often"),
                         encoding="utf-8")
    assert lab.knowledge()["bots"][0] == "15/40 hits its stop 3x as often"
    # The diary keeps every lesson, with its section, for the morning report.
    assert [r.get("section") for r in lab.entries() if r["kind"] == "lesson"][-1] == "cards"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_repository_file_has_its_sections_and_at_most_ten_open_lines():
    assert FILE.is_file(), "docs/lab-manager.md is the one place; it must exist"
    text = FILE.read_text(encoding="utf-8")
    for heading in ("## Open improvements", "## How the manager goes wrong",
                    "## Feedback and what changed"):
        assert heading in text, heading
    section = text.split("## Open improvements", 1)[1].split("\n## ", 1)[0]
    open_lines = [ln for ln in section.splitlines() if ln.startswith("- ")]
    assert len(open_lines) <= 10, "ten open lines, like NEXT.md: more is a backlog nobody reads"


# -- Laboratory v3, P6: the outsider (section 6) ----------------------------------------
# Helpers called from the manager test above: tests/meta grows only by replacement (the
# patrol's ceiling of 824), and the outsider is the laboratory manager's newest section.
# Once a day an agent with none of our memory discovers Cymetica, says whether it would put
# money in and picks; we validate its JSON, turn its picks into paper actions, follow its
# coins against BTC, and let it ask for a tournament seat only at a table THEY call paper.

_CARD = "3f2b1c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
_SURFACES = (("Gem Screener", 8), ("Agent Tournaments", 6), ("Agent League", 3),
             ("Event cards", 5), ("Bots", 4), ("Nexus", 7))


def _outsider_run(**over) -> dict:
    run = {"verdict": "The Gem Screener made me look twice; the rest is paper for now.",
           "would_deposit": True,
           "surfaces": [{"name": n, "score": s, "why": f"{n} because"} for n, s in _SURFACES],
           "picks": {"coins": [{"slug": "uniswap", "why": "cheap against its revenue"},
                               {"slug": "nosuchcoin", "why": "a typo of mine"}],
                     "cards": [{"id": _CARD.upper(), "hold_days": 3, "why": "momentum"}],
                     "bots": [{"species": "MACD Hunter", "stop_loss_pct": 10,
                               "take_profit_pct": 30, "why": "best backtest"}],
                     "tournament": {"table_id": "2", "why": "a cheap paper seat"}},
           "stumbles": [{"where": "/agent-tournaments/how-it-works", "what": "404"}],
           "fetches": 31}
    run.update(over)
    return run


def _outsider_script(name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        f"outsider_{name}", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _the_outsider_is_validated_and_its_picks_become_paper_actions():
    """validate() normalises a good run and names EVERY problem of a bad one; actions() is
    what the laboratory may do: its card bought on paper at HALF stake with no backtest gate
    (the stranger's judgement, not gate-and-stranger), its bot cloned on paper at its band,
    its coin watched against BTC, and a seat only as a wish the operator approves."""
    from qa import outsider

    run = outsider.validate(_outsider_run())
    assert run["picks"]["cards"][0]["id"] == _CARD, "a card id is kept in their lower case"
    assert run["scores"]["Gem Screener"] == 8 and run["scores"]["Nexus"] == 7, run["scores"]
    assert run["fetches"] == 31 and run["would_deposit"] is True
    assert outsider.validate(run) == run, "validating a validated run changes nothing"
    # A surface it never scored is said, never filled in.
    partial = outsider.validate(_outsider_run(surfaces=[{"name": "gem screener", "score": 9,
                                                          "why": "x"}]))
    assert partial["scores"]["Gem Screener"] == 9 and partial["scores"]["Agent League"] is None

    bad = _outsider_run(
        would_deposit="yes", fetches=41,
        surfaces=[{"name": "Gem Screener", "score": 11, "why": "x"},
                  {"name": "Gem Screener", "score": 3, "why": "twice"}],
        picks={"coins": [{"slug": f"c{n}", "why": "x"} for n in range(6)],
               "cards": [{"id": "3f2b1c4d", "hold_days": 0, "why": "x"},
                         {"id": _CARD, "hold_days": True, "why": "x"}],
               "bots": [{"species": "", "stop_loss_pct": 25, "take_profit_pct": 2, "why": "x"}],
               "tournament": {"table_id": "2/../seat", "why": "x"}})
    try:
        outsider.validate(bad)
    except outsider.OutsiderError as exc:
        problems = list(exc.problems)
        assert str(exc).count("\n") >= len(problems) - 1, "one exception names them all"
    else:
        raise AssertionError("a run with eleven problems was accepted")
    said = " | ".join(problems)
    for expected in ("would_deposit", "fetches", "41", "score", "twice", "coins", "6",
                     "whole UUID", "hold_days", "species", "stop_loss_pct", "take_profit_pct",
                     "table_id"):
        assert expected in said, (expected, said)
    assert len(problems) >= 11, problems
    for missing in ("verdict", "picks", "fetches"):
        broken = _outsider_run()
        del broken[missing]
        try:
            outsider.validate(broken)
        except outsider.OutsiderError as exc:
            assert missing in str(exc)
        else:
            raise AssertionError(f"a run without {missing} was accepted")

    acts = outsider.actions(run)
    by: dict = {}
    for act in acts:
        by.setdefault(act["kind"], act)
    card = by["card"]
    assert card["card_id"] == _CARD and card["hold_days"] == 3
    assert card["half"] is True and card["backtest_gate"] is False and card["paper"] is True, card
    assert by["bot"]["paper"] is True and by["bot"]["species"] == "MACD Hunter"
    assert by["bot"]["settings"] == {"stop_loss_pct": 10, "take_profit_pct": 30}
    assert by["coin"]["slug"] == "uniswap" and by["coin"]["benchmark"] == "BTC"
    assert by["coin"]["horizons_days"] == [1, 7, 28]
    assert by["tournament"]["table_id"] == "2" and by["tournament"]["approval"] == "operator"
    assert all(a["section"] == "outsider" for a in acts)
    assert [a["kind"] for a in acts].count("coin") == 2
    sitting_out = outsider.actions(_outsider_run(
        picks=dict(_outsider_run()["picks"], tournament={"table_id": None, "why": "no"})))
    assert "tournament" not in {a["kind"] for a in sitting_out}, "no table, no wish"


def _the_outsiders_coins_are_measured_against_btc_and_only_when_due():
    """A coin's return since its pick at 1, 7 and 28 days, against BTC over the same span.
    None where the day has not come, where nothing priced it, where the price is another
    moment's (a snapshot that did not move, a read half a day late) -- never a zero."""
    from datetime import datetime, timedelta, timezone

    from qa import outsider

    t0 = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)

    def iso(t):
        return t.isoformat(timespec="seconds")

    def px(value, at):
        return {"value": value, "as_of": iso(at)}

    pick = {"type": "pick", "id": "OUT-0001-C1", "run": "OUT-0001", "kind": "coin",
            "slug": "uniswap", "at": iso(t0), "price": px(100.0, t0 - timedelta(hours=2)),
            "btc": px(80000.0, t0)}
    blind = dict(pick, id="OUT-0001-C2", slug="nosuchcoin", price=None, unpriced="HTTP 404")
    one = {"type": "checkpoint", "pick": "OUT-0001-C1", "horizon": "1d",
           "at": iso(t0 + timedelta(days=1, hours=1)),
           "price": px(110.0, t0 + timedelta(days=1)),
           "btc": px(80800.0, t0 + timedelta(days=1, hours=1))}

    now = t0 + timedelta(days=2)
    said = outsider.coin_returns([pick, blind], [one], now)
    got = said["OUT-0001-C1"]["returns"]
    assert got["1d"]["coin_pct"] == _approx(10.0)
    assert got["1d"]["btc_pct"] == _approx(1.0)
    assert got["1d"]["vs_btc_pts"] == _approx(9.0)
    assert got["7d"] is None and got["28d"] is None
    assert said["OUT-0001-C1"]["status"]["7d"] == "not due"
    assert all(v is None for v in said["OUT-0001-C2"]["returns"].values()), "unpriced is None"

    # A snapshot that did not move since the pick is not a 0 % day.
    frozen = dict(one, price=dict(pick["price"]))
    assert outsider.coin_returns([pick], [frozen], now)["OUT-0001-C1"]["returns"]["1d"] is None
    # A read past the day's slack files another moment under day 1: the reader drops it.
    late = dict(one, at=iso(t0 + timedelta(days=1, hours=13)))
    assert outsider.coin_returns([pick], [late], now)["OUT-0001-C1"]["returns"]["1d"] is None
    # No BTC at the checkpoint: the comparison is unpriced, not a coin return alone.
    nobtc = dict(one, btc=None)
    assert outsider.coin_returns([pick], [nobtc], now)["OUT-0001-C1"]["returns"]["1d"] is None
    # A day that passed with no read is a gap, and a gap stays one.
    gone = outsider.coin_returns([pick], [], t0 + timedelta(days=3))["OUT-0001-C1"]
    assert gone["returns"]["1d"] is None and gone["status"]["1d"] == "missed"

    # The writer offers a checkpoint only inside its slack; the same rule the reader holds.
    assert [label for _p, label in outsider.due([pick], [], t0 + timedelta(days=1, hours=1))] \
        == ["1d"]
    assert outsider.due([pick], [one], t0 + timedelta(days=1, hours=2)) == []
    assert outsider.due([pick], [], t0 + timedelta(days=1, hours=13)) == [], "gone is gone"
    assert [label for _p, label in outsider.due([pick], [one], t0 + timedelta(days=7))] == ["7d"]
    assert outsider.due([blind], [], t0 + timedelta(days=1, hours=1)) == [], \
        "a coin unpriced at its pick has no return to follow"

    # What their two answers say, read the same way every time.
    assert outsider.coin_price({"slug": "uniswap", "price": {"value": 7.55, "as_of": "x"}})[0] \
        == {"value": 7.55, "as_of": "x"}
    assert outsider.coin_price({"price": {"value": None}})[0] is None
    assert outsider.coin_price({"price": 7.55})[0] is None, "a bare number has no moment"
    btc = {"BTC": {"price": 83006.5, "is_real": True, "stale": False,
                   "price_as_of": "2026-10-11T13:51:56Z"}}
    assert outsider.btc_price(btc)[0] == {"value": 83006.5, "as_of": "2026-10-11T13:51:56Z"}
    assert outsider.btc_price({"BTC": dict(btc["BTC"], stale=True)})[0] is None
    assert outsider.btc_price({"BTC": dict(btc["BTC"], is_real=False)})[0] is None
    assert outsider.btc_price({})[0] is None


def _approx(value):
    import pytest

    return pytest.approx(value, abs=1e-6)


def _price_handler(seen: list, uni_price: float = 7.55, uni_as_of: str = "2026-10-11T11:29:38Z",
                   btc_as_of: str = "2026-10-11T13:51:56Z"):
    import httpx

    def handler(request):
        seen.append((request.method, request.url.path))
        if request.method != "GET":
            raise AssertionError(f"{request.method} {request.url.path}: the outsider only reads")
        if request.url.path == "/api/v1/gem-screener/coins/uniswap":
            return httpx.Response(200, json={
                "slug": "uniswap", "symbol": "UNI", "name": "Uniswap",
                "price": {"value": uni_price, "unit": "USD per token", "as_of": uni_as_of}})
        if request.url.path.startswith("/api/v1/gem-screener/coins/"):
            return httpx.Response(404, json={"detail": "No coin with symbol"})
        if request.url.path == "/api/v1/prices":
            return httpx.Response(200, json={"BTC": {
                "asset": "BTC", "price": 83006.5, "is_real": True, "stale": False,
                "source": "real-time", "price_as_of": btc_as_of}})
        return httpx.Response(404, json={})
    return handler


def _the_outsider_run_is_recorded_with_prices_read_once(tmp_path):
    """`record` writes one run row OUT-NNNN and one row per pick, each coin with its Gem
    Screener price and BTC's at the same moment; a slug they do not know is an unpriced
    pick and a stumble, not a dropped one; the same file twice is one run. `track` writes a
    checkpoint only when one is due."""
    import json
    from datetime import datetime, timedelta

    from qa import outsider
    from qa.client import build_mock_client

    script = _outsider_script("outsider")
    source = tmp_path / "outsider-run.json"
    source.write_text("```json\n" + json.dumps(_outsider_run()) + "\n```\n", encoding="utf-8")

    seen: list = []
    client = build_mock_client(_price_handler(seen))
    try:
        written = script.record(source, client)
        again = script.record(source, client)
    finally:
        client.close()
    rows = script.load()
    runs = [r for r in rows if r["type"] == "run"]
    picks = [r for r in rows if r["type"] == "pick"]
    assert [r["id"] for r in runs] == ["OUT-0001"], runs
    assert again.get("already") == "OUT-0001", "the same file recorded twice is one run"
    assert runs[0]["verdict"].startswith("The Gem Screener") and runs[0]["fetches"] == 31
    assert runs[0]["scores"]["Gem Screener"] == 8 and runs[0]["would_deposit"] is True
    assert written["run"]["id"] == "OUT-0001"
    kinds = sorted(p["kind"] for p in picks)
    assert kinds == ["bot", "card", "coin", "coin", "tournament"], kinds
    assert all(p["run"] == "OUT-0001" for p in picks)
    uni = next(p for p in picks if p["kind"] == "coin" and p["slug"] == "uniswap")
    assert uni["price"] == {"value": 7.55, "as_of": "2026-10-11T11:29:38Z"}, uni
    assert uni["btc"]["value"] == 83006.5 and uni["action"]["kind"] == "coin"
    typo = next(p for p in picks if p["kind"] == "coin" and p["slug"] != "uniswap")
    assert typo["price"] is None and "404" in typo["unpriced"], typo
    assert any("nosuchcoin" in s["where"] for s in runs[0]["stumbles"]), runs[0]["stumbles"]
    card = next(p for p in picks if p["kind"] == "card")
    assert card["action"]["half"] is True and card["action"]["backtest_gate"] is False
    assert [m for m, _p in seen if m != "GET"] == []
    assert sum(1 for _m, p in seen if p == "/api/v1/prices") == 1, "BTC read once per record"
    # The validator's refusal reaches the command, and nothing is written.
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(_outsider_run(fetches=99)), encoding="utf-8")

    def deaf(request):
        raise AssertionError(f"{request.url.path} was read for a run that was refused")

    client = build_mock_client(deaf)
    try:
        script.record(broken, client)
    except outsider.OutsiderError:
        pass
    else:
        raise AssertionError("a run over its fetch cap was recorded")
    finally:
        client.close()
    assert len(script.load()) == len(rows)

    # track: nothing is due yet; a day later the coin is read, BTC once, and only once.
    at = datetime.fromisoformat(uni["at"])
    seen.clear()
    client = build_mock_client(_price_handler(
        seen, uni_price=8.0, uni_as_of=(datetime.fromisoformat("2026-10-11T11:29:38+00:00")
                                        + timedelta(days=1)).isoformat(),
        btc_as_of=(datetime.fromisoformat("2026-10-11T13:51:56+00:00")
                   + timedelta(days=1, hours=1)).isoformat()))
    try:
        assert script.track(client, now=at + timedelta(hours=3)) == []
        assert seen == [], "nothing due, nothing read"
        first = script.track(client, now=at + timedelta(days=1, hours=1))
        second = script.track(client, now=at + timedelta(days=1, hours=2))
    finally:
        client.close()
    assert [(c["pick"], c["horizon"]) for c in first] == [(uni["id"], "1d")], first
    assert second == [], "a checkpoint is written once"
    said = outsider.coin_returns(
        [r for r in script.load() if r["type"] == "pick"],
        [r for r in script.load() if r["type"] == "checkpoint"],
        at + timedelta(days=1, hours=2))
    assert said[uni["id"]]["returns"]["1d"]["coin_pct"] == _approx((8.0 / 7.55 - 1) * 100)

    # The diary is written by a laboratory tick: outside git (a dirty tree costs a run its
    # level V) and copied into audits/lab/ like the other diaries.
    import subprocess

    assert subprocess.run(["git", "check-ignore", "-q", "--no-index", "state/outsider.jsonl"],
                          cwd=REPO).returncode == 0, "state/outsider.jsonl is not gitignored"
    assert "outsider.jsonl" in _outsider_script("keep").DIARIES, \
        "nothing copies outsider.jsonl into audits/lab/"


def _a_seat_is_asked_only_at_a_paper_table_and_never_on_a_dry_run(tmp_path):
    """`seat TABLE INSTANCE [--confirm]`: llms.txt documents POST
    /api/v1/agent-tournaments/tables/{id}/seat {"instance_id"} (X-API-Key) and that the seat
    waits for the owner at the returned approve_url. Declared with a closed body: one key
    goes, nothing else under /agent-tournaments is written. Refused unless THEIR table says
    paper and open, and the bot is a paper clone of ours; a dry run sends nothing and writes
    nothing; a confirmed one is an intent before the POST and an outcome after (rule 9)."""
    import json

    import httpx
    import pytest

    from qa import outsider
    from qa.client import build_mock_client
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier, SafetyTransport, \
        SafetyViolation

    base = "https://cymetica.com/api/v1/agent-tournaments"

    class Inner(httpx.BaseTransport):
        def handle_request(self, request):
            raise AssertionError("the request reached the network")

    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    rule = registry.match("/api/v1/agent-tournaments/tables/2/seat", "POST")
    assert rule is not None and rule.closed_body is True and \
        rule.executable_params == frozenset({"instance_id"}), rule
    transport = SafetyTransport(Inner(), registry)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for url, body in ((f"{base}/tables/2/seat", {"instance_id": "inst-1", "buyin_usdc": 50}),
                          (f"{base}/tables/2/seat?mode=live", {"instance_id": "inst-1"}),
                          (f"{base}/seats/7/leave", {}),
                          (f"{base}/tables", {"tier": "micro"})):
            with pytest.raises(SafetyViolation):
                transport.handle_request(httpx.Request("POST", url, json=body))
        with pytest.raises(AssertionError, match="reached the network"):
            transport.handle_request(httpx.Request(
                "POST", f"{base}/tables/2/seat", json={"instance_id": "inst-1"}))
    finally:
        CURRENT_TIER.reset(token)

    rules = {"modes": {"paper": "open", "live": "not_open"},
             "paper_note": "Paper tables run on your paper account: the buy-in comes from "
                           "your paper USDC and prizes are paid to it. No real money moves.",
             "tiers": [{"tier": "pro", "buyin_usdc": 50.0}, {"tier": "micro", "buyin_usdc": 5.0}]}
    table = {"id": 2, "mode": "paper", "tier": "pro", "status": "open", "seats_free": 8,
             "my_seat": None, "buyin_usdc": 50.0}
    assert outsider.seat_refusal("2", table, rules) is None
    for wrong, why in ((dict(table, mode="live"), "mode"), (dict(table, mode=None), "mode"),
                       (dict(table, status="running"), "open"),
                       (dict(table, my_seat={"seat_id": 4}), "seat"),
                       (dict(table, seats_free=0), "free"),
                       (dict(table, id=3), "table"),
                       (dict(table, buyin_usdc=500.0), "buy-in")):
        said = outsider.seat_refusal("2", wrong, rules)
        assert said and why in said, (wrong, said)
    assert outsider.seat_refusal("2", table, dict(rules, modes={"paper": "closed"}))
    assert outsider.seat_refusal("2", table, dict(rules, paper_note="Live buy-ins."))

    clones = tmp_path / "clones.jsonl"
    clones.write_text(json.dumps({"type": "outcome", "outcome": "accepted",
                                  "clone_instance_id": "inst-1", "is_paper": True}) + "\n",
                      encoding="utf-8")

    def handler_for(table_body, posted: list):
        def handler(request):
            path = request.url.path
            if request.method == "POST":
                posted.append(path)
                return httpx.Response(200, json={
                    "seat_id": 9, "status": "pending",
                    "approve_url": "https://cymetica.com/agent-tournaments/approve/abc"})
            if path.endswith("/agent-tournaments/rules"):
                return httpx.Response(200, json=rules)
            if path.endswith("/agent-tournaments/tables/2"):
                return httpx.Response(200, json=table_body)
            if path.endswith("/cloned-bots/my-clones"):
                return httpx.Response(200, json=[{
                    "id": "inst-1", "is_paper": True,
                    "execution_economics": {"execution_class": "PAPER_SIMULATION"}}])
            return httpx.Response(404, json={})
        return handler

    script = _outsider_script("outsider")
    posted: list = []
    client = build_mock_client(handler_for(table, posted))
    try:
        assert script.seat("2", "inst-1", confirm=False, client=client) == 0
    finally:
        client.close()
    assert posted == [] and not [r for r in script.load() if r.get("kind") == "seat"], \
        "a dry run sent or wrote something"

    for live in (dict(table, mode="live"), dict(table, status="running")):
        client = build_mock_client(handler_for(live, posted), registry=registry)
        try:
            assert script.seat("2", "inst-1", confirm=True, client=client) != 0
        finally:
            client.close()
    assert posted == [] and not [r for r in script.load() if r.get("kind") == "seat"]
    # A bot that is not a paper clone of ours is not seated, whatever the table says.
    client = build_mock_client(handler_for(table, posted), registry=registry)
    try:
        assert script.seat("2", "someone-elses", confirm=True, client=client) != 0
    finally:
        client.close()
    assert posted == []

    client = build_mock_client(handler_for(table, posted), registry=registry)
    try:
        assert script.seat("2", "inst-1", confirm=True, client=client) == 0
        assert script.seat("2", "inst-1", confirm=True, client=client) != 0, \
            "one seat per owner per table: the second ask is refused by our own record"
    finally:
        client.close()
    assert posted == ["/api/v1/agent-tournaments/tables/2/seat"], posted
    seat_rows = [r for r in script.load() if r.get("kind") == "seat"]
    assert [r["type"] for r in seat_rows] == ["intent", "outcome"], seat_rows
    assert seat_rows[0]["id"] == seat_rows[1]["id"] and seat_rows[0]["body"] == \
        {"instance_id": "inst-1"}
    assert seat_rows[1]["outcome"] == "accepted" and \
        seat_rows[1]["approve_url"].endswith("/approve/abc")

    # Our seat gone from their table -- the owner left it by hand (2026-10-11, table 5) --
    # ends the earlier ask: a new one may go. Still standing, or a table that lists no
    # standings at all, and the earlier ask still holds.
    # C01, deep pass 2026-10-15: an OPEN table answers `standings: []` (present, empty), so an
    # empty list cannot say our seat is gone -- that would allow a second ask.
    for standings, allowed in (([{"seat_id": 9, "bot": "x"}], False), (None, False), ([], False),
                               ([{"seat_id": 3, "bot": "theirs"}], True)):
        body = dict(table, standings=standings) if standings is not None else table
        client = build_mock_client(handler_for(body, posted), registry=registry)
        try:
            said = script.seat("2", "inst-1", confirm=False, client=client)
        finally:
            client.close()
        assert (said == 0) == allowed, (standings, said)
    assert script.outcome_of(200, {"seat_id": 1}) == "unknown", "no approve_url, no acceptance"
    assert script.outcome_of(422, {"detail": "x"}) == "rejected"
    assert script.outcome_of(502, None) == "unknown"
