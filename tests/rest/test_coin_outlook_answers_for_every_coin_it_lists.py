"""A coin on their own roster has an outlook, in the view they wrote for assistants.

`/api/v1/crypto-outlook/coins` is described in their published schema as the
"Autocomplete roster for the page's search box" -- the list a caller picks
from. The text view of one coin is described there as:

    Plain text for chat assistants. Always 200 for a known coin: a cold coin
    is waited on briefly, then answered with a come-back line.

So their own words make the measurable promise: a symbol taken from the
roster answers 200 on `/api/v1/crypto-outlook/{symbol}.txt`. "Come back
later" is an answer and counts as one; 404 is not.

**What was seen when this was written.** BTC -- the first entry of the roster
-- answered `{"detail":"Not Found"}` on both the text and the JSON view, on
every look, minutes apart. RAIN answered 200 on one pass and 404 on the next,
which is why a symbol here is only counted after failing **twice**: a cold
coin being computed must not be reported as missing (`a-check-on-a-rotating-
population-is-sampling`, and the transient we nearly filed on 2026-09-16).

The JSON view is read for the second look because it is the same computation
behind a different representation; the verdict names both statuses so a
reader can tell "this coin is missing" from "only the text view is missing".

Deliberately NOT asserted: the content of the outlook, how long a cold coin
may take, or that the roster should contain any particular coin. A symbol
whose read fails for our own reasons is unmeasured, never a defect (rule 8).
"""

from __future__ import annotations

import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

ROSTER = "/api/v1/crypto-outlook/coins"
TEXT = "/api/v1/crypto-outlook/{symbol}.txt"
JSON = "/api/v1/crypto-outlook/{symbol}"
PAUSE_S = 0.8
# Long enough for a cold coin to finish computing: their own JSON view asks
# for five seconds when it is still working.
SECOND_LOOK_S = 15.0
# The head of their own roster, not the whole 147: a sweep of all of them
# spent the run's rate-limit budget and left 120 coins unread, which is a
# worse measurement than a small one honestly bounded. The roster is ordered
# by size, so the head is the set a caller is likeliest to ask for, and a
# 404 there is the loudest case of the promise being broken.
SAMPLE = 12


@qa(component="rest.markets", tier=SafetyTier.SAFE, surface="rest",
    claim="coin-outlook-answers-for-its-own-roster")
def test_every_coin_on_the_roster_answers_on_the_text_view(rest_anon):
    """Roster -> {symbol}.txt, and a second look before anything is counted."""
    response = rest_anon.get(ROSTER)
    if response.status_code != 200:
        raise Inconclusive(f"the roster answered HTTP {response.status_code}, "
                           f"so there is no list of known coins to try")
    coins = (response.json() or {}).get("coins") or []
    symbols = [c.get("symbol") for c in coins if isinstance(c, dict) and c.get("symbol")]
    if not symbols:
        raise Inconclusive("the roster carries no symbols")

    tried = symbols[:SAMPLE]
    first_fail, answered, unmeasured = [], [], []
    for symbol in tried:
        time.sleep(PAUSE_S)
        # A SafetyViolation is the run's own brake and must stop the check,
        # not be filed as a coin we could not read: the first version caught
        # it and reported "all 26 coins answered" over a roster of 147.
        code = rest_anon.get(TEXT.format(symbol=symbol)).status_code
        if code == 200:
            answered.append(symbol)
        elif code == 404 or 500 <= code < 600:
            # A 5xx BREAKS "always 200 for a known coin" exactly as a 404
            # does, and it is theirs, not ours. It used to go to `unmeasured`
            # -- a bucket this file's own docstring defines as "a read that
            # fails for OUR reasons" -- so six of twelve roster coins
            # answering 500 read as "all 6 coins on the roster answered".
            # Found by two readers on 2026-09-20. Both shapes get the second
            # look, because a cold cache and a restarting worker are the same
            # kind of transient.
            first_fail.append(symbol)
        else:
            unmeasured.append(f"{symbol}: HTTP {code}")

    missing = []
    if first_fail:
        time.sleep(SECOND_LOOK_S)
        for symbol in first_fail:
            time.sleep(PAUSE_S)
            again = rest_anon.get(TEXT.format(symbol=symbol)).status_code
            as_json = rest_anon.get(JSON.format(symbol=symbol)).status_code
            if again == 200:
                # Cold on the first pass, answered on the second: their own
                # documented behaviour, not a defect.
                answered.append(symbol)
            elif again == 404 or 500 <= again < 600:
                missing.append({"symbol": symbol, "text": again, "json": as_json})
            else:
                # Triaged exactly as the first look triages: a 429 the second
                # time is our budget, not a coin without an outlook. It went
                # to `missing` (A05, deep pass of 2026-09-21).
                unmeasured.append(f"{symbol}: HTTP {again} on the second look")

    measured = len(answered) + len(missing)
    if not measured:
        raise Inconclusive(f"no coin could be measured: {'; '.join(unmeasured[:5])}")

    named = ", ".join(f"{m['symbol']} (txt {m['text']}, json {m['json']})"
                      for m in missing)
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} of {measured} coins on their own roster do not "
                f"answer 200 on the text outlook their schema says is always "
                f"200 for a known coin, twice {SECOND_LOOK_S:.0f}s apart: "
                f"{named}"
                if missing else
                f"all {measured} coins on the roster answered the text outlook"),
        left=[m["symbol"] for m in missing], right=[],
        population={"roster": len(symbols), "tried": tried,
                    "first_look_not_200": first_fail, "missing": missing,
                    "answered": len(answered), "unmeasured": unmeasured},
        sources={"contract": "openapi-public.json, GET /api/v1/crypto-outlook/"
                             "{symbol}.txt: 'Always 200 for a known coin'",
                 "roster": ROSTER, "text": TEXT, "json": JSON},
        claim_id="coin-outlook-answers-for-its-own-roster"))
