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
    assert judge(outside=1, calls=0, hides=True, unread=["/x.js"])[0] == "passed", (
        "a control outside the card is in the page itself")
    assert judge(outside=0, calls=0, hides=True, unread=[])[0] == "failed"
    assert judge(outside=0, calls=0, hides=False, unread=[])[0] == "passed"
    assert judge(outside=0, calls=0, hides=False, unread=["/x.js"])[0] is None, (
        "no hide found, but a script that could not be read may hold it")
    assert judge(outside=0, calls=0, hides=True, unread=["/x.js"])[0] is None, (
        "a script that could not be read may hold the call that opens it")
    assert judge(outside=0, calls=0, hides=None, unread=[])[0] is None, "a hide not provably on empty"
    assert judge(outside=0, calls=1, hides=True, unread=[])[0] == "passed"
