"""NVR: the unfired-mechanism report must know every mechanism there is.

`scripts/never_fired.py` answers the question that found three dead mechanisms
on 2026-09-06 -- `stale_from`, the obligations block and `selector_full`, two
of them broken, none of them noticed by 289 passing guards. The report is only
worth reading if its list of what the code can produce is the code's list. A
vocabulary that quietly falls behind turns the report into reassurance, which
is the same failure one layer up.

So this derives each vocabulary from the source INDEPENDENTLY -- constants
imported from where they are defined, the two literal lists scanned out of the
modules that contain them -- and never asks never_fired.py what it thinks the
vocabulary is. Add a state, a verdict, an event type, a refusal or an
obligation without adding it there, and this turns red.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

from qa.fold import CHECK_STATES, FILING_STATES
from qa.marks import SafetyTier, qa
from qa.measure import VERDICTS
from qa.state import EVENT_TYPES

REPO = Path(__file__).resolve().parent.parent.parent


def _never_fired():
    path = REPO / "scripts" / "never_fired.py"
    spec = importlib.util.spec_from_file_location("never_fired_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _block_reasons_in_source() -> set[str]:
    """Every string qa/state.py can name as a reason a run is refused."""
    source = (REPO / "qa" / "state.py").read_text(encoding="utf-8")
    return set(re.findall(r'blocks_[rv]\.append\(\s*"([a-z_]+)"', source))


def _obligation_keys_in_source() -> set[str]:
    """The keys of the dict qa/fold.py::_obligations returns."""
    tree = ast.parse((REPO / "qa" / "fold.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_obligations":
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Dict):
                    return {k.value for k in inner.value.keys
                            if isinstance(k, ast.Constant)}
    raise AssertionError("qa/fold.py no longer has an _obligations returning a dict")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_report_names_every_mechanism_the_code_can_produce():
    """Six vocabularies, each held against where it is actually defined."""
    mod = _never_fired()
    vocabs = {v["name"]: set(v["symbols"]) for v in mod.vocabularies()}

    expected = {
        "check states": set(CHECK_STATES),
        "filing states": set(FILING_STATES),
        "verdicts": set(VERDICTS),
        "journal events": set(EVENT_TYPES),
        "run refusals": _block_reasons_in_source(),
        "obligations": _obligation_keys_in_source(),
    }

    assert set(vocabs) == set(expected), (
        "the report's vocabularies are not the ones this test knows how to "
        f"check: {sorted(set(vocabs) ^ set(expected))}"
    )
    for name, want in expected.items():
        assert want, f"{name}: derived nothing from the source, so this " \
                     f"assertion would pass over an empty report"
        assert vocabs[name] == want, (
            f"{name}: the report and the source disagree.\n"
            f"  missing from the report: {sorted(want - vocabs[name])}\n"
            f"  in the report, not in the source: {sorted(vocabs[name] - want)}"
        )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_mechanism_with_no_occurrences_is_printed_first():
    """The zeros are the output. Everything else is context for them.

    Rendered off a fabricated vocabulary rather than the live one, so the test
    does not depend on which of our mechanisms happens to be unfired today --
    the report going all-green must not be able to retire its own guard.
    """
    from collections import Counter

    mod = _never_fired()
    fake = [{"name": "test states", "over": "nothing",
             "symbols": ("USED", "NEVER_USED"),
             "seen": Counter({"USED": 3}), "last": {"USED": "2026-09-07"}}]

    out = mod.render(fake)
    head = out.split("\n\n")[0]
    assert "NEVER FIRED" in head and "NEVER_USED" in head, out
    assert "USED" in out.split("test states")[-1], "the full table is missing"

    zeros = mod.render(fake, zeros_only=True)
    assert "NEVER_USED" in zeros and "test states" in zeros
    # The table is what --zeros omits, so look for the table's own header
    # rather than for a digit: the summary line always carries counts, so
    # `"3" not in zeros` failed on a vocabulary that happened to have three
    # symbols and blamed it on the counts being printed.
    assert "test states  (nothing)" not in zeros, \
        "--zeros printed the per-vocabulary table it exists to omit"

    quiet = mod.render([{"name": "test states", "over": "nothing",
                         "symbols": ("USED",), "seen": Counter({"USED": 1}),
                         "last": {}}])
    assert "NEVER FIRED" not in quiet and "every mechanism has fired" in quiet


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_obligation_that_was_raised_and_cleared_still_counts():
    """The report's weakest line, and the day it was caught out.

    Obligations were counted off the CURRENT ledger, so one raised and paid
    between two runs of the report left no trace. On 2026-09-07 `reverify`
    fired for the first time in the project's life, was cleared four hours
    later by a level-V run, and the report went on saying it had never fired --
    right about what it measured and wrong about the world.

    Both axes keep their history in the row's transitions, so the pairs a row
    has ever been in are reconstructable, and the obligations that are pure
    functions of those two states are reconstructable with them.

    The fixture below is a row that is now quiet: PASSING beside FIX_CLAIMED,
    owing nothing today, having owed a re-verify yesterday.
    """
    mod = _never_fired()

    quiet_now = {
        "id": "CYM-a",
        "first_seen": {"at": "2026-09-05T00:00:00+00:00"},
        "check": {"state": "PASSING"},
        "filing": {"state": "FIX_CLAIMED", "reports": [{"report_id": 46}]},
        "obligations": {"reverify": False, "repair_check": False,
                        "reopen": [], "retractions": [], "disputed": []},
        "transitions": [
            {"axis": "check", "from": "UNVERIFIED", "to": "REPRODUCING",
             "at": "2026-09-05T01:00:00+00:00"},
            {"axis": "filing", "from": "NOT_RAISED", "to": "RAISED",
             "at": "2026-09-05T02:00:00+00:00"},
            # They claim a fix while our check still fails: reverify is owed
            # from here...
            {"axis": "filing", "from": "RAISED", "to": "FIX_CLAIMED",
             "at": "2026-09-05T03:00:00+00:00"},
            # ...until a run of ours agrees.
            {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
             "at": "2026-09-05T04:00:00+00:00"},
        ],
    }

    seen, _ = mod._obligations({"findings": {"CYM-a": quiet_now}}, events=[])
    assert seen.get("reverify"),         "an obligation raised and cleared between two reports left no trace"
    assert not seen.get("repair_check"),         "repair_check never held for this row and must not be invented"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_rejection_counts_from_the_journal_not_from_today():
    """`disputed` is not a pure function of the two axes, so it reads events.

    A report they marked invalid while our check was failing owed a decision at
    that moment, whatever the row looks like now.
    """
    mod = _never_fired()

    row = {
        "id": "CYM-a",
        "first_seen": {"at": "2026-09-05T00:00:00+00:00"},
        "check": {"state": "PASSING"},
        "filing": {"state": "REPLIED", "reports": [{"report_id": 46}]},
        "obligations": {"disputed": []},
        "transitions": [
            {"axis": "check", "from": "UNVERIFIED", "to": "REPRODUCING",
             "at": "2026-09-05T01:00:00+00:00"},
            {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
             "at": "2026-09-05T09:00:00+00:00"},
        ],
    }
    ledger = {"findings": {"CYM-a": row}}

    rejected_while_failing = [{"type": "vendor_status", "report_id": 46,
                               "status": "invalid",
                               "at": "2026-09-05T05:00:00+00:00"}]
    rejected_after_passing = [{"type": "vendor_status", "report_id": 46,
                               "status": "invalid",
                               "at": "2026-09-05T11:00:00+00:00"}]

    assert mod._obligations(ledger, rejected_while_failing)[0].get("disputed"),         "a rejection we were still reproducing owed a decision at the time"
    assert not mod._obligations(ledger, rejected_after_passing)[0].get("disputed"),         "a rejection that arrived after our own check agreed owes nothing"
