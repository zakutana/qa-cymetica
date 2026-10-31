"""The readings under the Quant Lab winner-text check (2026-10-31), on the texts as our company 14 and
/how-it-fits.txt served them that evening: how-it-fits says a winner of any long rule, Blue and paid
included, starts a blank paper bot with the winning entry threshold; the lab's own `cannot_tune` and
`what_it_does_not_do` still say the Blue set-ups cannot become paper bots, premium models are never
equipped, and a changed entry threshold is reported only."""

from qa.marks import SafetyTier, qa
from tests.rest.test_quant_lab_winner_text_agrees_with_how_it_fits import denials, judge, promises

DOC = (
    "A winner is started as a blank paper bot that trades the rule that won: the model's own buy and sell "
    "conditions (with the winning entry threshold) on closed 1-hour candles of the market, and the winning "
    "stop-loss and take-profit as exits on each position. Step 5 of the worked example below shows this. It "
    "needs no equipped model, so it holds for all 16 rules, paid models included (the lab never buys one). The "
    "exception is a short rule: the blank bot is long-only on the spot lane, so a win for stockbear_red, "
    "cryptobull_red or hybrid2_red is reported on the search card with the note short rules excluded and "
    "starts no bot.\n"
    "Head-to-head itself does not change or optimize any bot.\n")

THRESHOLD = ("A result that won with a changed entry threshold is reported only, not started as a paper bot: "
             "a paper bot cannot run a changed entry rule yet.")
ENTRY_ROW = {"what": "Starting a paper bot from a changed entry rule", "feasibility": "build_medium",
             "build_size": "medium",
             "why": "a paper bot cannot run a changed entry rule yet, so such a result is reported only.",
             "line": "Needs a medium build: a paper bot cannot run a changed entry rule yet, so such a result is "
                     "reported only."}
PREMIUM_ROW = {"what": "Premium models (prion, synapse, telomere)", "feasibility": "not_possible",
               "build_size": None, "why": "the platform sells these, so the lab never equips them for you.",
               "line": "Not possible: the platform sells these, so the lab never equips them for you."}
SETUPS_ROW = {"what": "Cymetica bot set-ups as paper bots (cryptobull_blue, cryptobull_red, hybrid2_blue, "
                      "hybrid2_red, stockbear_red, stockbull_blue)", "feasibility": "not_possible",
              "build_size": None,
              "why": "they are backtest set-ups for Cymetica's own bots, not catalog models, so they can be "
                     "searched but not equipped.",
              "line": "Not possible: they are backtest set-ups for Cymetica's own bots, not catalog models, so "
                      "they can be searched but not equipped."}
WEIGHTS_ROW = {"what": "Signal weights", "feasibility": "build_large", "build_size": "large",
               "why": "none of the 16 replayed bot models has weights.",
               "line": "Needs a large build: none of the 16 replayed bot models has weights."}
SEEN = {"what_it_does_not_do": ["It does not trade real money: every clone it starts is a paper bot.", THRESHOLD],
        "cannot_tune": [WEIGHTS_ROW, ENTRY_ROW, PREMIUM_ROW, SETUPS_ROW]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_how_it_fits_promises_both():
    assert set(promises(DOC)) == {"every_long_rule", "entry_threshold"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_served_that_evening_denies_both():
    found = denials(SEEN)
    assert len(found["entry_threshold"]) == 2
    assert [d.split(":")[0] for d in found["every_long_rule"]] == [
        "Premium models (prion, synapse, telomere)",
        "Cymetica bot set-ups as paper bots (cryptobull_blue, cryptobull_red, hybrid2_blue, hybrid2_red, "
        "stockbear_red, stockbull_blue)"]
    verdict, conflicts = judge(promises(DOC), found)
    assert verdict == "failed" and set(conflicts) == {"every_long_rule", "entry_threshold"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_fix_in_the_lab_text_passes():
    """The lab's lines rewritten to what how-it-fits says; a Red-only "not possible" may stay."""
    red = {**SETUPS_ROW, "what": "Short (Red) set-ups as paper bots (cryptobull_red, hybrid2_red, stockbear_red)",
           "why": "the blank paper bot is long-only, so short rules are excluded."}
    fixed = {"what_it_does_not_do": SEEN["what_it_does_not_do"][:1], "cannot_tune": [WEIGHTS_ROW, red]}
    assert judge(promises(DOC), denials(fixed)) == ("passed", {})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_half_a_fix_still_fails():
    """The sentence dropped from what_it_does_not_do, the cannot_tune row and the set-ups row left."""
    half = {"what_it_does_not_do": SEEN["what_it_does_not_do"][:1], "cannot_tune": [ENTRY_ROW, SETUPS_ROW]}
    verdict, conflicts = judge(promises(DOC), denials(half))
    assert verdict == "failed" and set(conflicts) == {"every_long_rule", "entry_threshold"}
    premium_only = {"what_it_does_not_do": [], "cannot_tune": [PREMIUM_ROW]}
    assert judge(promises(DOC), denials(premium_only))[0] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_how_it_fits_back_to_the_old_answer_is_not_judged():
    """If how-it-fits stops promising the bridge, there is no promise to hold the lab's text against."""
    old = ("We state this on the page as a gap: the blank bot already runs indicator rules live on 1-hour "
           "candles, and the bridge from the lab to it is not built yet.\n")
    assert promises(old) == {}
    assert judge(promises(old), denials(SEEN)) == (None, {})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_other_reported_only_sentences_are_not_an_entry_threshold_denial():
    other = {"what_it_does_not_do": ["A short (Red) rule is reported only, with the note short rules excluded."],
             "cannot_tune": [{"what": "5-minute bars", "feasibility": "build_medium",
                              "line": "Needs a medium build: the search stays on hourly bars."}]}
    assert denials(other) == {}
