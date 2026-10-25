"""The readings behind the "/account opens its Claim Missing Deposit form when nothing is pending" check.

C01, deep pass 2026-10-18 (3 of 3 readers): the card was found hidden only through one exact text
pattern of a hashed build, a script that could not be read left "hides" False and passed, and
`_calls` counted any `openClaimDepositForm(` that was not a `function` definition -- a method, a
string in the card's own markup, a comment. Each of those was a PASS without a way in. The probes
below are the readers' own.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_account_claim_deposit_reachable import _calls, _hides_when_empty, judge

LIVE = """var pending = data.pending || [];
    var container = document.getElementById('accountPendingDeposits');
    if (pending.length === 0) {
        container.style.display = 'none';
        return;
    }"""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_card_hidden_on_an_empty_list_is_found_however_it_is_written():
    assert _hides_when_empty(LIVE) is True, "the build read on 2026-10-17"
    minified = "const e=document.getElementById('accountPendingDeposits');if(!r.length){e.style.display='none'}"
    assert _hides_when_empty(minified) is True, "a rebuild that minifies"
    flagged = ("var c = document.getElementById(\"accountPendingDeposits\");\n"
               "if (rows.length < 1) { c.hidden = true; }")
    assert _hides_when_empty(flagged) is True, "the hidden property instead of display"
    direct = "if (!list.length) document.getElementById('accountPendingDeposits').classList.add('hidden');"
    assert _hides_when_empty(direct) is True, "no variable at all"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hide_that_is_not_provably_on_an_empty_list_is_unread_and_no_hide_is_none():
    other = ("var c = document.getElementById('accountPendingDeposits');\n"
             "function onError() { c.style.display = 'none'; }")
    assert _hides_when_empty(other) is None, "hidden for some other reason: neither yes nor no"
    assert _hides_when_empty("var c = document.getElementById('accountPendingDeposits'); c.style.display='block';") is False
    assert _hides_when_empty("") is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_a_real_call_of_the_opener_counts():
    assert _calls("function openClaimDepositForm() { form.style.display = 'block'; }") == 0
    assert _calls("const actions = { openClaimDepositForm() { form.style.display = 'block'; } };") == 0, "a method"
    assert _calls("card.innerHTML = '<button onclick=\"openClaimDepositForm()\">Deposit not showing?</button>';") == 0, (
        "a string in the hidden card's own markup")
    assert _calls("// openClaimDepositForm() is wired through data-click\nvar x = 'https://a.b/c';") == 0, "a comment"
    assert _calls("/* openClaimDepositForm(); */ var y = 1;") == 0
    assert _calls("window.openClaimDepositForm = function () {};") == 0, "an assignment is a definition"
    assert _calls("if (location.hash === '#claim') openClaimDepositForm();") == 1
    assert _calls("var u = 'https://x.y/'; if (!pending.length) { openClaimDepositForm(); }") == 1, (
        "a URL's // before the call is not a comment")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_verdict_rests_only_on_what_was_read():
    assert judge(outside=1, calls=0, hides=True, unread=["/x.js"], unplaced=[])[0] == "passed", (
        "a control outside the card is in the page itself")
    assert judge(outside=0, calls=0, hides=True, unread=[], unplaced=[])[0] == "failed"
    assert judge(outside=0, calls=0, hides=False, unread=[], unplaced=[])[0] == "passed"
    assert judge(outside=0, calls=0, hides=False, unread=["/x.js"], unplaced=[])[0] is None, (
        "no hide found, but a script that could not be read may hold it")
    assert judge(outside=0, calls=0, hides=True, unread=["/x.js"], unplaced=[])[0] is None, (
        "a script that could not be read may hold the call that opens it")
    assert judge(outside=0, calls=0, hides=None, unread=[], unplaced=[])[0] is None, "a hide not provably on empty"
    assert judge(outside=0, calls=1, hides=True, unread=[], unplaced=[])[0] == "passed"


# --- A03, deep pass 2026-10-25 (3 of 3 readers) ---------------------------------------------------
# `_hides_when_empty` said False -- "never hidden", a pass -- for hiding it did not recognise
# (`classList.toggle('hidden', !rows.length)`, a lookup through a helper, a card hidden in its own
# markup that a script shows only when rows exist), and `_calls` counted the in-card button's own
# wiring and a call inside `rows.forEach` as a way in. Unrecognised is unread, never "not hidden";
# a way in counts only when it is outside the card that hides.

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_hiding_written_another_way_is_read_as_hiding():
    toggled = ("function load(rows){ const c = document.getElementById('accountPendingDeposits'); "
               "c.classList.toggle('hidden', !rows.length); }")
    assert _hides_when_empty(toggled) is True, "a toggle on the empty test hides it on an empty list"
    helper = "const c = $('accountPendingDeposits'); if (!rows.length) { c.style.display = 'none'; }"
    assert _hides_when_empty(helper) is True, "a lookup through a helper is a lookup"
    ternary = ("var c = document.getElementById('accountPendingDeposits');\n"
               "c.style.display = pending.length ? 'block' : 'none';")
    assert _hides_when_empty(ternary) is True
    flagged = "var c = document.getElementById('accountPendingDeposits'); c.hidden = pending.length === 0;"
    assert _hides_when_empty(flagged) is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_hiding_this_does_not_recognise_is_unread_never_not_hidden():
    for code in (
            "const c = document.getElementById('accountPendingDeposits'); c.classList.toggle('collapsed', !rows.length);",
            "const c = document.getElementById('accountPendingDeposits'); c.className = rows.length ? 'card' : 'card off';",
            "const c = document.getElementById('accountPendingDeposits'); setVisible(c, rows.length > 0);",
            "$('#accountPendingDeposits').toggle(rows.length > 0);",
            "const ID = 'accountPendingDeposits'; byId(ID).hidden = !rows.length;",
            "list.innerHTML = '<div id=\"accountPendingDeposits\" class=\"card\"></div>';"):
        assert _hides_when_empty(code) is None, code
    # A name rebound to another element is that element from there on: the fund modal's own
    # `container` (fundPendingDeposits, served inline on /account 2026-10-25) hides on its empty list.
    rebound = ("var container = document.getElementById('accountPendingDeposits');\n"
               "container.style.display = 'block';\n"
               "function renderPendingDeposits() { const container = document.getElementById('fundPendingDeposits');\n"
               "  if (pending.length === 0) { container.style.display = 'none'; return; } }")
    assert _hides_when_empty(rebound) is False, "another element's hide under the same name"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_hidden_in_its_own_markup_is_hidden_until_a_script_is_read_showing_it():
    from tests.rest.test_account_claim_deposit_reachable import _card_hidden_when_empty, _Openers

    def starts_hidden(markup):
        page = _Openers()
        page.feed(markup)
        return page.card_starts_hidden

    assert starts_hidden('<div class="account-card" id="accountPendingDeposits" style="display: none;">') is True, (
        "the card as served 2026-10-25")
    assert starts_hidden('<div id="accountPendingDeposits" hidden>') is True
    assert starts_hidden('<div class="account-card d-none" id="accountPendingDeposits">') is True
    assert starts_hidden('<div class="account-card" id="accountPendingDeposits" style="display: flex">') is False
    shows = "const c = document.getElementById('accountPendingDeposits'); if (rows.length) { c.style.display = 'block'; }"
    assert _card_hidden_when_empty(shows, starts_hidden=True) is None, "shown by a script, and when is not read"
    assert _card_hidden_when_empty("var x = 1;", starts_hidden=True) is True, "hidden at load and nothing shows it"
    assert _card_hidden_when_empty(shows, starts_hidden=False) is False
    assert _card_hidden_when_empty(LIVE, starts_hidden=True) is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_call_that_runs_only_from_inside_the_card_is_not_a_way_in():
    assert _calls("const actions = { openClaimDepositForm: () => openClaimDepositForm() };") == 0, (
        "the data-click table: the in-card button's own wiring")
    assert _calls("const actions = { openClaimDepositForm: function () { openClaimDepositForm(); } };") == 0
    assert _calls("switch (el.dataset.click) { case 'openClaimDepositForm': openClaimDepositForm(); break; }") == 0
    from tests.rest.test_account_claim_deposit_reachable import _unplaced_calls

    empty = "if (pending.length === 0) { container.style.display = 'none'; return; }\n"
    per_row = (empty + "pending.forEach(function (d) { var b = document.createElement('button');\n"
               "  b.onclick = function () { openClaimDepositForm(d.tx); }; list.appendChild(b); });")
    assert _calls(per_row) == 0 and _unplaced_calls(per_row) == [], (
        "a call per pending row: none when nothing is pending, and nothing left unread")
    assert _calls("if (!rows.length) return;\nrows.map(r => openClaimDepositForm(r));") == 0
    assert _calls("if (!rows.length) return;\nfor (const r of rows) { openClaimDepositForm(r); }") == 0
    assert _unplaced_calls("if (!rows.length) return;\nfor (const r of rows) { openClaimDepositForm(r); }") == []
    # A loop over something that is not the list whose emptiness hides the card may run anyway.
    assert _calls("[1, 2].forEach(k => openClaimDepositForm(k));") == 0
    assert len(_unplaced_calls("[1, 2].forEach(k => openClaimDepositForm(k));")) == 1
    # Still a way in: at load, after the fetch, at the top level.
    assert _calls("document.addEventListener('DOMContentLoaded', () => { if (location.hash === '#claim') "
                  "openClaimDepositForm(); });") == 1
    assert _calls("fetch(u).then(r => r.json()).then(d => { if (!d.pending.length) openClaimDepositForm(); });") == 1
    assert _calls("(function () { if (location.hash === '#claim') openClaimDepositForm(); })();") == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_call_whose_trigger_is_not_read_is_unplaced_never_a_way_in():
    from tests.rest.test_account_claim_deposit_reachable import _unplaced_calls

    for code in ("function maybeOpen() { openClaimDepositForm(); }",
                 "document.getElementById('somewhere').addEventListener('click', () => openClaimDepositForm());",
                 "btn.onclick = function () { openClaimDepositForm(); };",
                 "helpers.later(() => openClaimDepositForm());"):
        assert _calls(code) == 0, code
        assert len(_unplaced_calls(code)) == 1, code
    assert _unplaced_calls("if (location.hash === '#claim') openClaimDepositForm();") == []
    assert _unplaced_calls("const t = { openClaimDepositForm: () => openClaimDepositForm() };") == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unplaced_call_blocks_a_fail_never_a_pass():
    assert judge(outside=0, calls=0, hides=True, unread=[], unplaced=["maybeOpen"])[0] is None, (
        "a call whose trigger was not read may be the way in")
    assert judge(outside=0, calls=0, hides=False, unread=[], unplaced=["maybeOpen"])[0] == "passed", (
        "the card stays: its own button is the way in")
    assert judge(outside=1, calls=0, hides=True, unread=[], unplaced=["maybeOpen"])[0] == "passed"
