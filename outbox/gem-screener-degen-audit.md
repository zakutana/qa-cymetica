# Gem Screener, audited as a degen before the next altseason

2026-09-30 · snapshot of 18:50 UTC · 215 apps, all of them, not a sample · every figure is from `python scripts/gem_audit.py tick`, which repeats this on any day.

## Bottom line

- **The data is a faithful copy of public sources.** Market cap, supply, revenue and pool liquidity match CoinGecko, DefiLlama and DexScreener to a median of 0.0 to 0.7 %. The upside is exactly its published formula on 215 of 215 rows. I found no shown number I could call wrong.
- **What the numbers are worth is another matter, and their own backtest says so.** Pre-registered, verdict *inconclusive*: the upside rank has no skill (correlation 0.017, 90 % CI −0.020 to 0.051); coins that passed the pick gates did **21 to 23 % worse than the rest over six months** (90 % CI −62 % to −12 %, 17 coins); 2 of 2,829 coins did 10x; the live track record of the picks is **0 picks tracked**. The Top Picks tab prints one line of this, "Backtest: inconclusive. A shortlist, not a signal.", and the rest one click away.
- **So: a risk screen and a place to start, not a signal.** Do not size on "50x".

## 1. What holds

| Column (all rows) | Against | Median off | Rows off by more than |
|---|---|---|---|
| circulating supply | CoinGecko | 0.0 % | 25 %: 2 of 214 (2Z, PHAR) |
| price | CoinGecko | 0.3 % | 30 %: 0 of 215 |
| 30-day revenue | DefiLlama | 0.7 % | 25 %: 2 of 214 |
| pool liquidity | DexScreener | 0.0 % | 50 %: 0 of 179 |
| benchmark (Hyperliquid) market cap | CoinGecko | 0.4 % | |
| upside = benchmark multiple / own multiple, capped | its own formula | | 0 breaches in 215 |
| altseason composite, 4-week mean, beat/n | its own rules | | 0 breaches |

The two rows beyond 25 % are the world, not a bug: CoinGecko cut PHAR's circulating supply by a fifth today and re-estimated 2Z's.

## 2. Where I would not trust it, worst first

1. **The 50x headline.** 11 apps sit at the cap, hiding 72x to 2,291x; the order among them is gone. The benchmark's 33x is on a market cap with 23 % of its tokens out; its own multiple on all tokens is 143x. The picks have 4 to 14 % out (PHAR 6.8 %, UP 4.3 %, NEST 13.7 %, FXN 13.3 %), so "if all tokens were out" is what a holder gets later: **PHAR 50x → 31x, UP 44x → 8x**. Ask: show the all-tokens-out upside as the headline where fewer than a quarter are out.
2. **Picks that carry their own warnings.** NEST and SOLV have the exit flag "business weakening". NEST and UP **earn less than they emit** (−$213K and −$762K a month after emissions). UP has 81 days of history and is not vetted (the vetting gate lets a young coin through), and is down 54 % in 30 days. PHAR is up 199 % in 30 days at its all-time high, its admin can mint, its owner is a contract that was not scanned, and its level is "6" inside a range of 5 to 9. Ask: a pick with an exit flag, negative earnings after emissions or under 180 days is labelled as such where the pick is shown, not only in its detail.
3. **3 of 10 picks cannot be bought on-chain at $10K.** SOLV (100 % impact), MNDE (64 %), LISTA (96 %) pass the liquidity gate on 24-hour volume, which is exchange volume; their pools hold $20K to $31K. The page does not say which exchange. Ask: say where the liquidity is and how deep.
4. **Supply data is frozen.** The supply behind 168 of 215 rows is **43 hours old, and was 37 hours old six hours ago**: it is not being re-read. Their collector failed 200 CoinGecko market reads and took 186 prices from DefiLlama instead, while CoinGecko answers me for all 215 coins in two 0.4 s calls. The page says so openly (a banner, and "from 43 h ago" on the exchange-volume cards), but the rows show no age. In a fast market this is how a market cap goes wrong by a fifth (PHAR: $4.1M on the page, $3.3M at CoinGecko). Ask: read supply fresh (a CoinGecko key would do) and show the supply age on each row.
5. **A pick's link opens another token.** "Definitive" (EDGE) links to `?coin=EDGE`; the symbol route and the page open **edgeX**, a different token (market cap $182M, not $30M). Four tickers are shared by two apps (EDGE, UP, MET, INDEX). The route accepts a slug, so the link only needs one. **Filed as #140**, with a check.
6. **The altseason panel's headline sentence is a 4-week mean.** "49 % of the top 50 alts beat BTC over 13 weeks" is the mean of the last four weeks; **the latest week is 68 % (34 of 50), up from 22 % three months ago**. A degen watching for the turn sees 49. Ask: show the latest reading beside the mean.
7. **Three of the 50 "alts" are not alts.** A home-equity-loan token ($24B, price 1.03), a tokenised money-market fund (USYC, 1.14) and a euro fund (1.15): each moves under 3 % a month. They cannot beat BTC in a rally (a structural 6-point drag on breadth now) and always beat it in a fall (a 6-point false strength later). Ask: leave assets priced at a currency unit out of the universe.
8. **Sector tags tell nothing apart.** 10 of 12 themes are "Hot now". "Talked about" rests on 460 people and 1,163 messages in seven days and says "too few" for half the themes. Ask: rank, do not tag.
9. **Risk levels are wide and unknowns count as half a risk.** 124 of 215 levels span more than two steps (PHAR 5–9, UP 4–9); an unscanned check counts 0.5. Ask: show the top of the range as the level.
10. **Chain fees are valued after guards that remove most of them.** Their own `guard_cut_share` is over half of the raw fees for 19 of the 21 large chains the benchmark rule turns away (Ethereum 54 %, Stellar 90 %, Tron 92 %, TON 95 %). I did not check how the guards choose what to drop.

## 3. The ten picks

| Pick | Upside / if all out | Tokens out | $10K impact | Level (range) | After emissions, 30 d | Exit flag | Price 30 d |
|---|---|---|---|---|---|---|---|
| PHAR | 50 / 31 | 6.8 % | 2.7 % | 6 (5–9) | +$1.21M | | +199 % |
| NEST | 48 / 28 | 13.7 % | 2.6 % | 6 (6–8) | −$213K | weakening | −8 % |
| UP | 44 / 8 | 4.3 % | 1.2 % | 6 (4–9) | −$762K | | −54 % |
| SOLV | 18 / 45 | 57 % | 100 % (exchange) | 5 (4–6) | +$1.23M | weakening | +47 % |
| FXN | 8.5 / 4.9 | 13 % | 1.2 % | 5 (4–6) | +$187K | | +38 % |
| MNDE | 7.5 / 25 | 78 % | 64 % (exchange) | 3 (1–5) | unknown | | +31 % |
| KNC | 7.4 / 28 | 87 % | 2.4 % | 6 (4–8) | unknown | | +21 % |
| O | 7.1 / 4.9 | 16 % | 0.8 % | 4 (3–5) | unknown | | +1 % |
| LISTA | 4.5 / 10 | 54 % | 96 % (exchange) | 3 (3–5) | +$481K | | +28 % |
| EDGE | 4.2 / 4.9 | 27 % | 2.8 % | 6 (4–8) | unknown | | +61 % |

## 4. What changed today

Their 18:50 refresh delivered what they said it would: the Team check runs on **72** apps (49 before), Audit on **214** (171), hidden supply 113, insider flow 97; wide level ranges 131 → 124; the picks grew from 8 to 10 (KNC and O are new). The supply age did not move. The fixes from the ET-28378 answer were checked live earlier (`outbox/et28378-recheck.md`).

## 5. Not checked

On-chain holder concentration beyond their own flags; whether DEX volume is wash trading; what an audit actually covers; the MCP tool; the fund's performance; behaviour in a fast market (the snapshot is six hours old, prices two). Load time is in `outbox/gem-screener-load-time.md`.

## 6. Defects and improvements

**Defects** (a shown thing wrong): the pick link (#140, filed). Earlier, separate: routes missing from `/openapi-public.json` (#138) and the Build it Better log cutting at 8,000 characters (#139).

**Improvements** (goals for the next Build it Better request, nothing filed): items 1, 2, 3, 4, 6, 7, 8 and 9 of section 2 as written there. They fit the draft in `outbox/bb-request-gem-screener-followup.md` (25 lines today; limit 40).

## 7. To repeat

`python scripts/gem_audit.py tick` redoes every number here in about a minute and says what moved. Six core checks hold the parts a redesign will not change (numbers against their sources, a pick opens the coin it names, the upside formula, the altseason rules); they run in every sweep. `/gem-audit` is the whole procedure, including the browser pass.
