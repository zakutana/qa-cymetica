# ET-32428 (Build a Company, round 3), the second verdict (2026-10-25)

Verdict: **Pass**. Nexus declared the round finished (REPLY-0206); checked live on 2026-10-25, every item against `SPEC.md`:

- A1/10, buildings: `adGem` in their `u3d.js?v=6add511a` is the mockup's (b0cf54d5) with no diff, `adCasino` too (only what
  follows it differs: their Promo Market, ET-32484); `universe.js` puts them on `slot-2-4` and `slot-4-2` and draws them flat.
  Seen in the built-in browser: a green cut diamond and a magenta/violet chip with the logo over its mast, pink dot on its plate.
- A2, panel: 420 px over the right side, Esc closes it, a 700 px stage puts it over the lower part (56 %).
- B3: the panel reads 77 vetted apps, the same rows as `/gem-screener/app`'s Start view at the same minute
  (source `GET /api/v1/company/map-products/gem-tiers`).
- B4: equals `GET /api/v1/agent-tournaments/lobby`: 10 agents trading, 1 live table, 60 open seats, 100 ET10 PAPER, table 15's
  first six, then "+4 more" to its page, six open-table chips, Go play to `/agent-tournaments`.
- C5, Read: fixed in code (`String(x.id) === String(id)`); no approval was waiting (`/office` approvals 0), so not clicked.
- C6, /clear: placeholder and the cleared line are in the code; and it has run once for real: our `/office` holds
  `chat_cleared_at` 2026-10-22T20:15:51Z with no `/clear` message stored and no manager reply after it.
- C7: the map shows 5 companies (`GET /api/v1/company/universe` returns 5). The dormant test and bot companies are left off.
  That was their own change (REPLY-0197), not our request as REPLY-0206 says. Accepted.
- C8: `GET /api/v1/company/products` with our key: 13 products, one per page, builds counted inside (38), Airdrop Farmer
  among them; visitors sum to 637, not 2,970.
- C9: MADE BY BJ IRONSTAR CAPITAL at the top of both panels; `CO.madeBy` is called only from `prodpanel.js`, so not on the cards.
- Gap, said to them: `/api-docs` has `GET /api/v1/promo/house` (the Promo Market panel) but not the gem-tiers route.

## Note for the verdict (Pass)

```
Pass. Checked live on 25 Oct 2026, item by item against the brief.
1. Gem Screener (the cut diamond) and Agent Casino (the orbital chip) stand on Orbit 2 · slot 4 and Orbit 4 · slot 2 as the mockup draws them, the flat map too.
2. A click opens the 420 px panel, Esc closes it, under 760 px it sits over the lower part.
3. Gem Screener's panel reads 77 vetted apps, the same rows as the Gem Screener page.
4. Agent Casino's panel equals the lobby: 10 agents trading, 1 live table, 60 open seats, 100 ET10 paper, the live table's first six.
5. Read: fixed in code; no approval was waiting to click.
6. /clear: used in the owner's chat on 22 Oct; the stamp is kept and nothing went to NEXUS.
7. Companies are back on the map; leaving off the dormant test and bot companies is accepted.
8. Products: one card per product, builds inside, no closed builds, totals no longer counted per build.
9. MADE BY BJ IRONSTAR CAPITAL in both panels, off the Products cards.
Thank you.
```

## Telegram (Pass)

```
@EventTraderQABot Build a Company round 3 (ET-32428): checked live, I gave the verdict PASS. Both buildings are now the mockup's, both panels match their sources (the Gem Screener page, the lobby), Products shows one card per product, and /clear worked in my chat with nothing sent to NEXUS. Thank you.

One gap: /api-docs lists GET /api/v1/promo/house (the Promo Market panel) but not GET /api/v1/company/map-products/gem-tiers, the source of the Gem Screener panel. Please add it.
```

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
