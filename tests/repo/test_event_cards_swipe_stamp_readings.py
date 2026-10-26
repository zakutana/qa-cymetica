"""The readings behind the "an Event Card's swipe stamp names what the swipe does" check.

Written before the check (2026-10-26), from event-cards.js?v=20261022-1 as /events served it that day: the card
builder labels the left stamp `ec-stamp--skip` with the text 'SELL'; dragging a card left fades that stamp in
(`else if (curX < -20) { skipStamp.style.opacity = ratio; ... }`); letting go past the threshold runs
`animateSwipe(el, 'skip')` -- the card leaves, nothing is sold, no sheet opens. Seen the same day in a browser at
390 px, signed out, every non-GET aborted: held 220 px left the stamp read SELL at opacity 1 with the card's
`ec-card--glow-skip`; released, the deck moved to the next card and no sheet was open.

Each reading below is a way the vendor could fix it (it must pass, whichever they pick), a way the same defect
could be rebuilt (it must still fail), or a shape the check cannot decide (inconclusive, never a pass).
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_event_cards_swipe_stamp_names_what_the_swipe_does import judge, script_facts

# The three places as event-cards.js?v=20261022-1 has them (comments kept, as served).
BUILD = """
        /* Direction labels (Tinder-style stamp) */
        var bullLabel = document.createElement('div');
        bullLabel.className = 'ec-stamp ec-stamp--bull';
        bullLabel.textContent = 'BUY';
        el.appendChild(bullLabel);

        var skipLabel = document.createElement('div');
        skipLabel.className = 'ec-stamp ec-stamp--skip';
        skipLabel.textContent = 'SELL';
        el.appendChild(skipLabel);
"""
FIND = """
        var bullStamp = el.querySelector('.ec-stamp--bull');
        var skipStamp = el.querySelector('.ec-stamp--skip');
"""
DRAG = """
            var ratio = Math.min(Math.abs(curX) / SWIPE_PX, 1);
            if (curX > 20) {
                bullStamp.style.opacity = ratio;
                skipStamp.style.opacity = 0;
            } else if (curX < -20) {
                skipStamp.style.opacity = ratio;
                bullStamp.style.opacity = 0;
            } else {
                bullStamp.style.opacity = 0;
                skipStamp.style.opacity = 0;
            }
"""
RELEASE = """
            var dir = curX >= 0 ? 'right' : 'left';
            if (swiped && (Math.abs(curX) > 60)) {
                /* right = bull (fly off + open Buy), left = skip (fly off). */
                if (dir === 'right') {
                    animateSwipe(el, 'bull');
                    openBuySheet(card);
                } else {
                    animateSwipe(el, 'skip');
                }
            } else {
                snapBack(el, bullStamp, skipStamp);
            }
"""
LIVE = BUILD + FIND + DRAG + RELEASE


def _verdict(js: str) -> str | None:
    return judge([script_facts(js)])[0]


def _with(old: str, new: str, js: str = LIVE) -> str:
    assert old in js, old
    return js.replace(old, new)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_script_as_served_on_2026_10_26_fails():
    facts = script_facts(LIVE)
    assert facts["stamps"] == {"bull": "BUY", "skip": "SELL"}
    assert facts["drag"] == {"right": "bull", "left": "skip"}
    assert facts["release"]["left"] == {"action": "skip", "sheets": []}
    assert facts["release"]["right"] == {"action": "bull", "sheets": ["openBuySheet"]}
    verdict, why, sides = judge([facts])
    assert verdict == "failed"
    assert "SELL" in why and "skip" in why
    assert sides["right"]["consistent"] is True, "BUY on a right swipe that buys is right"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_defect_rebuilt_in_other_shapes_still_fails():
    assert _verdict(_with("skipLabel.textContent = 'SELL'", 'skipLabel.textContent = "SHORT"')) == "failed"
    assert _verdict(_with("skipLabel.textContent = 'SELL'", "skipLabel.innerText = 'Sell'")) == "failed", "any case"
    markup = _with(BUILD, """
        el.innerHTML += '<div class="ec-stamp ec-stamp--bull">BUY</div><div class="ec-stamp ec-stamp--skip">SELL</div>';
""")
    assert _verdict(markup) == "failed", "the stamps written as markup"
    minified = ('var b=document.createElement("div");b.className="ec-stamp ec-stamp--bull",b.textContent="BUY";'
                'var s=document.createElement("div");s.className="ec-stamp ec-stamp--skip",s.textContent="SELL";'
                'var B=e.querySelector(".ec-stamp--bull"),S=e.querySelector(".ec-stamp--skip");'
                'if(x>20){B.style.opacity=r;S.style.opacity=0}else if(x<-20){S.style.opacity=r;B.style.opacity=0}'
                'var d=x>=0?"right":"left";if(d==="right"){animateSwipe(e,"bull");openBuySheet(c)}else{animateSwipe(e,"skip")}')
    assert _verdict(minified) == "failed", "minified"
    left_first = _with("""if (dir === 'right') {
                    animateSwipe(el, 'bull');
                    openBuySheet(card);
                } else {
                    animateSwipe(el, 'skip');
                }""", """if (dir === 'left') {
                    animateSwipe(el, 'skip');
                } else {
                    animateSwipe(el, 'bull');
                    openBuySheet(card);
                }""")
    assert _verdict(left_first) == "failed", "the release written left branch first"
    wrong_right = _with("bullLabel.textContent = 'BUY'", "bullLabel.textContent = 'SELL'",
                        _with("skipLabel.textContent = 'SELL'", "skipLabel.textContent = 'SKIP'"))
    assert _verdict(wrong_right) == "failed", "a right stamp naming a trade the right swipe does not make"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_fix_the_vendor_might_choose_passes():
    for word in ("SKIP", "Skip", "PASS", "NEXT", "NOPE", "✕", ""):
        assert _verdict(_with("skipLabel.textContent = 'SELL'", f"skipLabel.textContent = '{word}'")) == "passed", word
    sells = _with("animateSwipe(el, 'skip');\n                }", "animateSwipe(el, 'bear');\n                    openSellSheet(card);\n                }")
    assert _verdict(sells) == "passed", "keep the word, make a left swipe sell"
    sheet_only = _with("animateSwipe(el, 'skip');\n                }", "animateSwipe(el, 'skip');\n                    openSellSheet(card);\n                }")
    assert _verdict(sheet_only) == "passed", "a left swipe that opens the Sell sheet"
    no_left_stamp = _with("""            } else if (curX < -20) {
                skipStamp.style.opacity = ratio;
                bullStamp.style.opacity = 0;
            }""", "            }")
    assert _verdict(no_left_stamp) == "passed", "no stamp shows on a left drag: nothing is mislabelled"
    hidden = _with("skipStamp.style.opacity = ratio;", "skipStamp.style.opacity = 0;")
    assert _verdict(hidden) == "passed", "the left stamp kept but never shown"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_the_check_cannot_decide_is_inconclusive():
    assert judge([])[0] is None, "no script read"
    assert _verdict(FIND + DRAG + RELEASE) is None, "no stamp text found: the stamps were rebuilt some other way"
    assert _verdict(BUILD + FIND + RELEASE) is None, "no drag handler that shows a stamp"
    assert _verdict(BUILD + FIND + DRAG) is None, "no release that says what a left swipe does"
    unknown = _with("skipLabel.textContent = 'SELL'", "skipLabel.textContent = label(dir)")
    assert _verdict(unknown) is None, "the text is computed; this check cannot read it"
    two = judge([script_facts(LIVE), script_facts(_with("skipLabel.textContent = 'SELL'", "skipLabel.textContent = 'SKIP'"))])
    assert two[0] is None, "two scripts that disagree: which one runs is not ours to guess"
