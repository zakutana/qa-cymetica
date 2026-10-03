"""The morning report: every day at 7:00, what the night did in the lab.

Plan v2, V11 (docs/laborator-plan.md), pin 7 in the laborator skill: a short
page every morning at seven -- the deep pass in a few lines, then the lab by
room, what changed overnight, what the manager does today -- at one address,
readable on a phone, and the operator's feedback on it acted on and named in
the next one. No new scheduler: the overnight /loop's first tick from 06:40
says the report is due, and a session started after 07:00 without one makes
it at once.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa import morning
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
LOCAL = timezone(timedelta(hours=2))


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=LOCAL)


def _case_the_report_is_due_from_six_forty_until_it_is_made_that_day():
    assert not morning.due(_at(24, 6, 39), {})
    assert morning.due(_at(24, 6, 40), {})
    assert morning.due(_at(24, 6, 40), {"made_on": "2026-09-23"})
    assert not morning.due(_at(24, 9, 0), {"made_on": "2026-09-24"})


def _case_after_seven_a_missing_report_is_missing():
    assert not morning.missing(_at(24, 6, 59), {})
    assert morning.missing(_at(24, 7, 0), {"made_on": "2026-09-23"})
    assert not morning.missing(_at(24, 7, 30), {"made_on": "2026-09-24"})


DEEP = """# Deep pass — 2026-09-22 večer

Spuštěn na tvůj `/deep-pass`.

## Co se stalo

* **34 nálezů:** 10 z code review.

## Opraveno

* **Bezpečnostní brána pustila živý příkaz dvěma dveřmi (C01, 3/3).**
  * vnořený bod se nepočítá
* **Kontrola #119 měla tři díry.** Prázdné tělo.
* **Naše vlastní:** `open_checks` bral za plný běh i běh zastavený.

## Co odešlo Cymetice

* **2 ověření `pass`:** #111 a #120.

## Čeká na tebe

* **ET-26036: verdikt dál čeká na obrazcovou TA.** Beze změny.
"""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_deep_pass_is_two_lines_what_we_fixed_and_what_went_to_them():
    """The operator, 2026-09-26, on the report: "30 z 31 skutečných nálezů je
    jako co? bugy v cymetice?" -- the fixes are OURS and must say so; the
    process figures (claims, checks audited, readers) are not wanted; and
    "Čeká na tebe" goes: nothing waits on them."""
    said = morning.deep_pass(DEEP)
    assert said["title"] == "Deep pass — 2026-09-22 večer"
    assert [line["kind"] for line in said["lines"]] == ["fixed", "sent"]
    fixed, sent = said["lines"]
    assert fixed["count"] == 3, "nested bullets are not fixes of their own"
    assert "našich" in fixed["text"] and "Cymetic" in fixed["text"], fixed
    assert "`" not in sent["text"] and "#111" in sent["text"]
    # A pass that writes its count in the lead is read by that count.
    counted = morning.deep_pass(DEEP.replace(
        "* **Bezpečnostní brána", "* **30 z 31 skutečných nálezů (44 tvrzení: 34 z auditu).** x\n* **Bezpečnostní brána"))
    assert counted["lines"][0]["count"] == 30
    # A report number is not a count, and "nothing" is none (R05, 3/3):
    # "#133" read as 133 fixes, "Nic." as one.
    named = morning.deep_pass("# T\n## Opraveno\n- **#133 ověřen, pass poslán.**\n")
    assert named["lines"][0]["count"] == 1, named
    nothing = morning.deep_pass("# T\n## Opraveno\n- **Nic.** noc bez oprav\n")
    assert nothing["lines"][0]["count"] == 0, nothing
    assert sent["text"] and len(sent["text"]) <= 140
    assert morning.deep_pass("")["lines"] == [], "no pass on record is no lines"
    # 2026-10-01, the operator: "opraveno 14, ale vubec nemam paru ceho se to
    # tyka". The fixed line says WHAT: each fix's lead, or for a pass that
    # leads with its count, the words after that count.
    assert "Bezpečnostní brána pustila živý příkaz" in fixed["text"], fixed
    assert "Kontrola #119 měla tři díry" in fixed["text"], fixed
    what = morning.deep_pass(
        "# T\n## Opraveno\n- **14 z 28 tvrzení skutečných, vše opraveno.** Gem audit: "
        "nová identita market cap; lab stránka sčítá všechny boty. Další věta.\n"
        "- **0b:** FOMO watch jede po minutě.\n")
    text = what["lines"][0]["text"]
    assert "Gem audit: nová identita market cap" in text and "FOMO watch" in text, text
    assert "14 z 28" not in text, "the count is the tag's, not the words'"
    long_one = morning.deep_pass("# T\n## Opraveno\n- **3 věci.** " + "slovo " * 200)
    assert len(long_one["lines"][0]["text"]) <= morning.DEEP_LINE, "an unbounded line"
    # 2026-10-03, the operator, on a line cut in the middle ("... ET-29001 1..."): every fix is
    # its own item, whole, and a long one is cut at a word, never in the middle of one.
    items = what["lines"][0]["items"]
    assert items == ["Gem audit: nová identita market cap; lab stránka sčítá všechny boty.",
                     "0b: FOMO watch jede po minutě."], items
    wordy = morning.deep_pass("# T\n## Opraveno\n- **Dlouhá oprava " + "slovíčko " * 60 + "**")
    cut = wordy["lines"][0]["items"][0]
    assert len(cut) <= morning.ITEM_LINE and cut.endswith("…") and not cut[:-1].endswith("slov"), cut
    # What the page may not say: code names, backticks, file names, run ids.
    assert morning.jargon("Opravil jsem `restart_refusal` v scripts/clone.py") == [
        "`", "restart_refusal", "`", ".py"], morning.jargon("Opravil jsem `restart_refusal` v scripts/clone.py")
    assert morning.jargon("Bot se už znovu nespustí, když ho zastavila jejich ochrana.") == []
    # T08, deep pass 2026-10-04: the promise is "no code name or file name", but only .py names,
    # snake_case and run ids were caught. A file of ANY kind we keep, and a camelCase name from
    # the page's own scripts, is code to someone who reads this in Czech and is not a programmer.
    for code in ("reports-cs.yaml", "DEEP-PASS.md", "report.json", "events.jsonl", "morning.html",
                 "console.cmd", "console.sh", "lab.yml", "labShow", "restartRefusal"):
        assert morning.jargon(f"Opraveno v {code} a hotovo.") == [code], (
            code, morning.jargon(f"Opraveno v {code} a hotovo."))
    for plain in ("Gem Screener a Build it Better.", "Cena v eToro a iOS aplikaci vzrostla.",
                  "Stránka OpenAI a GitHub ukazují Nexus.", "Přesně 3.5 % z 12.000 USDC.",
                  "Konec věty. Další věta začíná velkým písmenem."):
        assert morning.jargon(plain) == [], (plain, morning.jargon(plain))

    # And what happened with Cymetica overnight, which the report lacked:
    # sweeps run, bugs we filed, what they fixed, what we verified.
    since = "2026-09-25T20:00:00+00:00"
    events = [
        {"type": "filing_outcome", "outcome": "accepted", "report_id": 131,
         "at": "2026-09-26T03:40:00+00:00"},
        {"type": "filing_outcome", "outcome": "accepted", "report_id": 99,
         "at": "2026-09-20T03:40:00+00:00"},
        {"type": "vendor_status", "report_id": 131, "status": "pending",
         "at": "2026-09-26T03:41:00+00:00"},
        {"type": "vendor_status", "report_id": 131, "status": "paid",
         "at": "2026-09-26T05:00:00+00:00"},
        {"type": "vendor_status", "report_id": 132, "status": "pending",
         "at": "2026-09-26T05:10:00+00:00"},
        # Paid is accepted, not fixed (qa/fold.py): #130 and #132 were paid
        # and still reproduced, and the report called them fixed (R02, 3/3).
        {"type": "vendor_status", "report_id": 132, "status": "paid",
         "at": "2026-09-26T21:30:00+00:00"},
        {"type": "vendor_status", "report_id": 128, "status": "fixed",
         "at": "2026-09-26T06:00:00+00:00"},
        {"type": "verification_outcome", "outcome": "accepted", "verdict": "pass",
         "report_id": 113, "at": "2026-09-25T23:20:00+00:00"},
        {"type": "verification_outcome", "outcome": "unknown", "verdict": "pass",
         "report_id": 114, "at": "2026-09-25T23:20:00+00:00"}]
    # A sweep that RAN preregistered its run; a tick that only decided one
    # counted, and the operator's own /qa-sweep did not (R06, 3/3).
    registered = ["2026-09-26T00:05:00+00:00", "2026-09-26T17:03:34+00:00",
                  "2026-09-25T10:00:00+00:00"]
    # The operator, 2026-10-01: every report number says what it is about.
    titles = {131: "A" * 300, 128: "Fixed thing", 113: "Verified thing", 99: "old"}
    theirs = morning.cymetica(events, registered, since, titles)
    assert {k: v for k, v in theirs.items() if k != "titles"} == {
        "sweeps": 2, "filed": [131], "fixed": [128], "verified": [113],
        "failing": []}, theirs
    assert theirs["titles"] == {131: "A" * (morning.TITLE_LINE - 1) + "…",
                                128: "Fixed thing", 113: "Verified thing"}, theirs["titles"]
    assert morning.cymetica(events, registered, since)["titles"] == {}, "no titles known"
    # Our tracker copy keeps only the newest reports; an older one is named by
    # the finding the ledger filed it for, and the tracker's own title wins.
    tracker = [{"id": 140, "title": "Tracker title"}, {"id": None, "title": "x"}]
    ledger = {"findings": {
        "CYM-a": {"title": "Old finding", "filing": {"reports": [
            {"report_id": 51}, {"report_id": 140}]}},
        "CYM-b": {"title": "Second", "filing": {"reports": [{"report_id": 51}]}},
        "CYM-c": {"title": "", "filing": {"reports": [{"report_id": 7}]}},
        "CYM-d": {"title": "No filing"}}}
    # The operator, 2026-10-03: the report is Czech and plain ("zapominas ze ma byt vse degen
    # friendly ... uplne srozumitelne o co jde"). A report is named by its own Czech line; the
    # tracker's English title and the check's message are never shown, and one with no Czech
    # line says so in Czech instead of falling back to English.
    czech = {140: "Česky o stošestnáctce", 51: "Česky o jedenapadesátce"}
    none = morning.NO_CZECH
    assert morning.titles_from(tracker, ledger, czech) == {**czech, 7: none}
    assert morning.titles_from(tracker, ledger, {140: "Česky"}) == {140: "Česky", 51: none, 7: none}
    assert morning.titles_from(tracker, ledger) == {140: none, 51: none, 7: none}
    assert any(ch in morning.NO_CZECH for ch in "ěščřžýáíéůú"), "the placeholder is not Czech"

    # 2026-10-01: a pass on #132 at 16:00 and our correction (fail) on it at
    # 00:10 the same night -- the report said "the fix holds: #132". The
    # newest verdict sent decides; a fail is said as one.
    events += [
        {"type": "verification_outcome", "outcome": "accepted", "verdict": "pass",
         "report_id": 132, "at": "2026-09-26T16:00:00+00:00"},
        {"type": "verification_outcome", "outcome": "accepted", "verdict": "fail",
         "report_id": 132, "at": "2026-09-27T00:10:00+00:00"},
        {"type": "verification_outcome", "outcome": "accepted", "verdict": "fail",
         "report_id": 56, "at": "2026-09-27T00:10:00+00:00"}]
    theirs = morning.cymetica(events, registered, since)
    assert (theirs["verified"], theirs["failing"]) == ([113], [56, 132]), theirs


def _report(net: float, rooms: list[dict], questions: int = 80) -> dict:
    sector = {"n": 2, "net_pct": net, "usdc": net * 5, "stake_usdc": 500.0,
              "wins": 1, "wilson": None, "min_n": 5, "running": 2, "archived": 0}
    return {"generated_at": "x",
            "products": {"cards": sector, "bots": dict(sector, net_pct=1.0),
                         "memecoins": dict(sector, net_pct=-19.8),
                         "funds": dict(sector, net_pct=None, n=0)},
            "nexus": {"questions": questions, "answered": 50, "picks": 30,
                      "gated": 30, "gate_pass": 20, "survived": 0, "refuted": 1,
                      "inconclusive": 2, "running": 7},
            "rooms": rooms}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_overnight_names_what_moved_since_the_last_report():
    before = _report(-3.2, [
        {"id": "STR-1", "title": "ZEC rally", "product": "cards", "verdict": None,
         "net_pct": 2.0},
        {"id": "STR-2", "title": "SOL doubles", "product": "cards", "verdict": None,
         "net_pct": -1.0}])
    now = _report(-4.2, [
        {"id": "STR-1", "title": "ZEC rally", "product": "cards", "verdict": None,
         "net_pct": 2.5},
        {"id": "STR-2", "title": "SOL doubles", "product": "cards",
         "verdict": "refuted", "net_pct": -3.1},
        {"id": "STR-3", "title": "FLOW recovery", "product": "cards",
         "verdict": None, "net_pct": None}], questions=85)
    lines = morning.overnight(now, before)
    text = " | ".join(lines)
    assert "Nový pokus: FLOW recovery" in text
    # Which product it was, so "nevyšlo" is not read as one kind of thing
    # (the operator, 2026-10-01: "to sou event karty?").
    assert "✗ nevyšlo (Karty): SOL doubles" in text
    assert "Karty −3,2 % → −4,2 %" in text
    assert "Nexus: +5 otázek" in text
    assert len(lines) <= morning.MAX_OVERNIGHT
    assert morning.overnight(now, None) == [], "no earlier report, nothing to compare"
    # Deep pass 2026-10-02 (T12): the other direction. Bots (1,0 % both times) and
    # Memecoiny (-19,8 % both times) did not move, so naming them as news is the
    # report saying something false; and a move under MOVE_PP is not one either.
    assert "Boti" not in text and "Memecoiny" not in text, text
    nudged = _report(-3.2 + morning.MOVE_PP / 2, [])
    assert not [line for line in morning.overnight(nudged, _report(-3.2, []))
                if line.startswith("Karty")], "a move under MOVE_PP was named"
    over = _report(-3.2 + morning.MOVE_PP + 0.1, [])
    assert [line for line in morning.overnight(over, _report(-3.2, []))
            if line.startswith("Karty")], "a move past MOVE_PP was not named"


def _entry(kind, text, at):
    return {"type": "entry", "kind": kind, "text": text, "at": at, "session": "LAB-1"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_report_carries_the_feedback_acted_on_and_a_ready_telegram_block():
    """Pin 7: the operator gives feedback on the report as the lab's manager;
    what the manager changed because of it is named in the next one. And a
    message for Cymetica is ready to paste, opening with our handle (CLAUDE.md,
    2026-09-13)."""
    notebook = [
        _entry("feedback", "chci vidět víc botů", "2026-09-23T20:00:00+00:00"),
        _entry("acted", "boti mají vlastní room nahoře", "2026-09-23T21:00:00+00:00"),
        _entry("acted", "staré, už hlášené", "2026-09-22T21:00:00+00:00"),
        _entry("telegram", "memecoin terminal switches pairs", "2026-09-23T22:00:00+00:00"),
        _entry("next", "otestovat MACD s jiným stopem", "2026-09-23T23:00:00+00:00"),
        _entry("next", "zeptat se Nexuse na fondy", "2026-09-23T23:01:00+00:00")]
    since = "2026-09-23T05:00:00+00:00"
    assert morning.acted(notebook, since) == ["boti mají vlastní room nahoře"]
    assert morning.telegram(notebook, since) == (
        "@EventTraderQABot memecoin terminal switches pairs")
    assert morning.today(notebook, since) == ["otestovat MACD s jiným stopem",
                                              "zeptat se Nexuse na fondy"]
    assert morning.telegram(notebook, "2026-09-24T00:00:00+00:00") is None
    # R05 (deep pass of 2026-09-24, 3/3): "what the manager does today" took
    # the newest three `next` lines ever written, so a night that wrote none
    # showed days-old plans as today's -- live on 09-24, the newest was from
    # 09-23 04:14. Since the last report, like its neighbours.
    assert morning.today(notebook, "2026-09-24T00:00:00+00:00") == []


def _view():
    return morning.build(
        _report(-4.2, []), {"made_at": "2026-09-23T05:00:00+00:00",
                            "snapshot": _report(-3.2, [])},
        DEEP, [_entry("acted", "boti mají vlastní room", "2026-09-23T21:00:00+00:00"),
               _entry("telegram", "@EventTraderQABot ahoj", "2026-09-23T22:00:00+00:00")],
        _at(24, 6, 45))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_is_one_short_czech_page_in_the_artifact_shape():
    page = importlib.util.spec_from_file_location(
        "morning_page", REPO / "scripts" / "morning.py")
    module = importlib.util.module_from_spec(page)
    page.loader.exec_module(module)
    html = module.render(_view())
    assert "<title>Ranní přehled laborky</title>" in html[:8192]
    for tag in ("html", "body", "!doctype", "head"):
        assert not re.search(rf"<{tag}[\s>]", html, re.I), (
            f"the publish skeleton supplies <{tag}>")
    for words in ("Deep pass", "Karty", "Boti", "Memecoiny", "Fondy", "Přes noc",
                  "Dnes", "Podle tvé zpětné vazby", "boti mají vlastní room",
                  "@EventTraderQABot ahoj", "Cymetica", "Sweep"):
        assert words in html, f"{words!r} is not on the page"
    # The lab's figures are totals since it began, said so (the operator,
    # 2026-10-01: "jsou celkove za celou dobu nebo prez noc?"); overnight is
    # the section below it.
    assert "celkem od začátku" in html
    # Every report number carries what it is about, one line (same day).
    many = dict(_view(), cymetica={
        "sweeps": 11, "filed": [138], "fixed": [136], "verified": [135],
        "failing": [132],
        "titles": {138: "Feature pages call routes missing from the OpenAPI",
                   136: "Builds ship late", 135: "Matchups read running",
                   132: "Async a2a gets no investigation"}})
    page_html = module.render(many)
    assert "Sweep: 11" in page_html, "the sweep count is one short line"
    # Each fix is a line of its own under the count, never one run-on paragraph.
    listed = module.render(dict(_view(), deep_pass={"title": "T", "lines": [
        {"kind": "fixed", "count": 2, "text": "chyb v našich nástrojích",
         "items": ["Jedna oprava.", "Druhá oprava."]}]}))
    assert '<ul class="sub"><li>Jedna oprava.</li><li>Druhá oprava.</li></ul>' in listed, listed[-1800:]
    # Deep pass 2026-10-02 (T15): "short" is a number. The page reads 227 words; the
    # operator does not read long ones (CLAUDE.md, 2026-09-13), so a render that grows
    # past 400 visible words, with or without the titled report lines, fails here.
    for shown in (html, page_html):
        prose = re.sub(r"<(script|style)\b.*?</\1>", " ", shown, flags=re.S | re.I)
        assert len(re.sub(r"<[^>]+>", " ", prose).split()) <= 400, "the page is not short"
    for line in ("#138 — Feature pages call routes missing from the OpenAPI",
                 "#136 — Builds ship late", "#135 — Matchups read running",
                 "#132 — Async a2a gets no investigation"):
        assert line in page_html, line
    # Nothing waits on the operator (2026-09-26), and the Nexus line says what
    # the numbers are: went to paper, lost, earned, still running.
    assert "Čeká na tebe" not in html
    assert "na papír" in html and "prodělalo" in html and "ještě běží" in html
    # Each figure is his rooms' own count, not gate passes minus verdicts:
    # 20 - 0 - 1 would have said 19 running (R07, 3/3).
    assert "7 ještě běží" in html and "2 bez závěru" in html, html
    assert "−4,2" in html and "Karty −3,2 % → −4,2 %" in html
    # Both themes, the artifact contract's way.
    assert ':root:not([data-theme="light"])' in html and ':root[data-theme="dark"]' in html
    assert re.search(r"body\s*\{[^}]*background", html), "the body paints its own ground"
    # The Telegram block is a code block with a copy button, never a quote
    # (CLAUDE.md, asked 2026-09-20).
    assert "<pre" in html and "navigator.clipboard" in html


def _case_lab_py_morning_builds_the_page_and_published_records_the_day(
        tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.rooms
    import qa.state
    from qa import lab

    importlib.reload(qa.state)
    importlib.reload(lab)
    importlib.reload(qa.rooms)
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_morning", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.main(["morning"]) == 0
    page = tmp_path / "lab" / "morning.html"
    assert page.is_file() and "Ranní přehled laborky" in page.read_text(encoding="utf-8")
    state = json.loads((tmp_path / "lab" / "morning.json").read_text(encoding="utf-8"))
    assert not state.get("made_on"), "made only once it is published"
    assert morning.due(datetime.now().astimezone().replace(hour=7), state)

    assert module.main(["morning", "--published", "https://claude.ai/code/artifact/x"]) == 0
    state = json.loads((tmp_path / "lab" / "morning.json").read_text(encoding="utf-8"))
    today = datetime.now().astimezone().date().isoformat()
    assert state["made_on"] == today and state["url"] == "https://claude.ai/code/artifact/x"
    assert state["snapshot"]["products"], "the next report compares against this one"


def _case_the_lab_notebook_takes_feedback_acted_and_telegram_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state
    from qa import lab

    importlib.reload(qa.state)
    importlib.reload(lab)
    for kind in ("feedback", "acted", "telegram"):
        assert lab.note_entry("LAB-0001", f"a {kind}", kind=kind)["kind"] == kind


# Folded on the deep pass of 2026-10-04 (tests/meta grows only by replacement): four functions became two.


def _fresh_dir(tmp_path, i):
    """A state directory of its own for each folded case."""
    path = tmp_path / f"case{i}"
    path.mkdir()
    return path


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_report_is_due_from_six_forty_and_a_missing_one_is_missing_after_seven():
    _case_the_report_is_due_from_six_forty_until_it_is_made_that_day()
    _case_after_seven_a_missing_report_is_missing()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_lab_py_morning_builds_the_page_and_the_notebook_takes_what_the_day_wrote(tmp_path, monkeypatch):
    _case_lab_py_morning_builds_the_page_and_published_records_the_day(_fresh_dir(tmp_path, 0), monkeypatch)
    _case_the_lab_notebook_takes_feedback_acted_and_telegram_lines(_fresh_dir(tmp_path, 1), monkeypatch)
