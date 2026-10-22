# ET-32428 (Build a Company, round 3), what goes out (2026-10-22)

Verdict: **Fail**, for one reason: the two buildings. The rest of round 3 is not judged yet.
Read live on 2026-10-22 from the operator's two screenshots of the Universe (a green castle with towers for Gem Screener, a plain grey ring for Agent Casino).

## Note for the verdict

```
Not built as specified: the two buildings.

1. Gem Screener and Agent Casino stand as your own stations (a green castle with towers; a plain grey ring), not as the buildings of the mockup. Line 2 of the request: the look of the mockup is binding. Line 1 links the code.

2. Gem Screener must be a floating cut diamond in the greens of its logo (flat facets outlined dark, a green ring on the slot). Code: u3d.js, function adGem, line 1058
https://github.com/zakutana/qa-cymetica/blob/b0cf54d5be2e6c4ef5f303077b6bfcd7daa7f332/outbox/company-live/u3d.js#L1058

3. Agent Casino must be an orbital chip in a space casino's colours (neon magenta and violet rings, white and cyan inserts, violet steel, magenta lamps, a pink plate), with a hologram of the Agent Tournaments logo over its mast on a cyan beam, facing the first look and swaying; the dot on its plate is pink, not cyan. Code: u3d.js, function adCasino, line 1163
https://github.com/zakutana/qa-cymetica/blob/b0cf54d5be2e6c4ef5f303077b6bfcd7daa7f332/outbox/company-live/u3d.js#L1163

4. See both in the mockup: https://rawcdn.githack.com/zakutana/qa-cymetica/b0cf54d5be2e6c4ef5f303077b6bfcd7daa7f332/outbox/company-live/index.html#universe (Universe tab, click Gem Screener and Agent Casino). Pictures of both buildings are in our Telegram message after MSG-0208.

Also: please drop the MADE BY badge from the cards of the Products tab (our request, withdrawn); it stays in the product's panel on the map.

The rest of round 3 is not judged yet; this Fail is for the buildings only.
```

## Telegram

```
@EventTraderQABot Build a Company round 3 (ET-32428): I gave the verdict FAIL, for one reason: Gem Screener and Agent Casino stand as your own stations, not as the buildings of the mockup (see my message with the pictures, MSG-0208). The note on the verdict has the exact links into the code, adGem and adCasino in u3d.js. Please read the verdict and rebuild those two buildings. We check the rest of round 3 next.
```
