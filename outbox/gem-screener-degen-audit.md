# Gem Screener, audited as a degen

2026-10-15 · snapshot generated 2026-10-14 23:34 UTC (6.3 h old at the tick) · 237 apps, all of them, not a sample · every figure from `python scripts/gem_audit.py tick` and the snapshot API.

## Bottom line

- **The numbers are faithful copies, and the arithmetic holds.**
  - Copies against their sources:

    | Copy | Source | Median off | Rows outside the threshold |
    |---|---|---|---|
    | Supply | CoinGecko | 0.0 % | 0 of 237 |
    | Price | CoinGecko | 3.9 % (the snapshot was 6 h old) | 1 of 237 |
    | 30-day revenue | DefiLlama | 0.2 % | 2 of 237 |
    | Pool liquidity | DexScreener | 2.8 % | 1 of 191 |

  - The upside follows its formula on 237 of 237 rows.
  - Nine derived figures, recomputed on 1,337 rows, have no breach.
  - No pick opens another coin.
  - Growth 6M, recomputed from the page's own daily revenue series, matches on 10 of 10 picks to two decimals, and within 0.5 points on 210 of 229 rows.
- **No number shown on a pick is wrong. The risk is in what the gates let through.** Four of the six Degen gates pass a coin in a way their name does not suggest. Each does what its long rule says, so none is a defect. But a degen who reads "passed all 6 gates" is told less than they think.

## 1. Four gates, as a degen reads them

| Gate | Rule as written | What gets through today |
|---|---|---|
| **Liquid** | "$10K buy ≤ 3% slip". The long rule adds: or 24-hour volume of at least $2M. | 2 of 10 picks pass on volume alone. **SOLV:** a $10K buy moves the price 111.6 %; its main pool holds $17,915 and traded $583 in 24 h. **GMX:** 12.7 %, pool $157,502. Neither can be bought on EventTrader (the coin's own `trade_note`). GMX carries no warning at all. |
| **Dilution** | "1% of market cap a week at most… No data passes." | **5 of 10 picks have no dilution figure** (STONK, CARDS, BNKR, PONS, EDGE). Each says "dilution unknown". At its limit the gate allows about 52 % new tokens a year; the benchmark itself runs at 1.03 % a week. SOLV passes at 0.71 % a week (about 37 % a year), marked caution. |
| **Real revenue** | "Revenue of the last 30 days is at least $100K." | **AERO:** $8.11M of revenue against $11.80M of emissions, so −$3.68M a month after emissions. Its coin carries `revenue_bought_with_emissions: true`, yet `risks: []`, and the pick's warnings name only "the business is no longer growing". |
| **Growing** | "Revenue still grows over six months. A bigger business may slip: over $10M up to 5% a month, over $1M up to 2% a month." | 5 of 10 picks pass Growing and carry the warning "the business is no longer growing": their 30-day revenue is 25–46 % of its 1-year high. **BNKR** passes at −0.24 % a month with a fit r² of 0.00. On DefiLlama's series read 6 h later it is −3.93 %, which fails. On a flat, noisy series the gate is a coin toss. |

## 2. The ten picks

| Pick | Upside / if all tokens out | $10K impact | Liquid on | Level (range) | Earnings after emissions, 30 d | Exit flags | Price 30 d |
|---|---|---|---|---|---|---|---|
| STONK | 44 / 190 | 1.0 % | pool | 4 (1–6) | unknown | theme lagging BTC | −47 % |
| SOLV | 15 / 39 | **111.6 %** | **volume** | 5 (5–5) | +$1.27M | business weakening | −21 % |
| CARDS | 12 / 24 | 0.5 % | pool | 4 (3–5) | unknown | | +126 % |
| BNKR | 12 / 51 | 1.0 % | pool | 3 (2–5) | unknown | business weakening | +34 % |
| PONS | 11 / 45 | 0.6 % | pool | 4 (1–8) | unknown | business weakening, theme lagging | −48 % |
| PUMP | 7.3 / 18 | 0.9 % | pool | 3 (3–3) | +$66.5M | theme lagging BTC | +30 % |
| MET | 5.5 / 13 | 1.2 % | pool | 3 (2–4) | +$6.07M | business weakening | +70 % |
| GMX | 5.1 / 22 | **12.7 %** | **volume** | 4 (2–6) | +$3.69M | | +12 % |
| EDGE | 4.9 / 5.8 | 3.0 % | pool | 5 (3–7) | unknown | | +49 % |
| AERO | 2.6 / 5.7 | 0.05 % | pool | 4 (3–5) | **−$3.68M** | business weakening | +59 % |

Seven of the ten carry an exit flag; two are young (79 and 91 days of revenue).

## 3. The browser pass (2026-10-15, 05:55–06:10 UTC)

| Where | Read | Holds? |
|---|---|---|
| Top Picks | 10 cards: degen meters, growth lines (+518 / +17 / +27 / +23 % a month), "30x would be above…" notes, near misses (6) | yes, every one against the snapshot |
| Top Picks | "Backtest of the old gates: inconclusive. A shortlist, not a signal." | shown without a click |
| Altseason panel | index 32 = ⅔ × 24.2 + ⅓ × 48.3; breadth 56 %, 4-week mean 62 % (56, 68, 68, 56), 3 months ago 58 %; BTC.D "5 % of a 25-point drop" (60.21 → 58.93); tops 100 / 95 / 79 | yes |
| Altseason panel | **two "retail" figures**: tile RETAIL 20/100 "asleep" (retail-v4, 19.7), and "retail by dollar volume 48/100" under euphoria (47.7, the v3 figure, which is what the index uses) | **no: same label, two numbers** |
| Altseason panel | their own acceptance checks: index `fail` (10.2 % of weeks at the top zone against a 10 % limit); retail-v4 `fail` (B1, B2) | not shown on the page |
| Apps tab | default view "Vetted only"; 237 apps, 34 chains | |
| Apps tab, SUPPLY column | "Dilution, 12 months": new tokens of the next 12 months / circulating, **red at 25 % or more**. SOLV +32.1 % red, AERO +24.3 %, PUMP +17.8 %, MET +5.5 %, GMX +1.3 %, five picks "—" (no schedule) | the column is right; see the defect below |
| Sectors | 12 stages against the 1M / 3M rule | yes, 12 of 12 |
| Sectors | "Hot right now" names 3 (AI, RWA, L2); the table has 4 HOT (also DeFi lending, 1M +3 %) | a wording gap |
| Sectors / Top Picks | SOLV's card says "Infrastructure theme already leads"; the Sectors table has Infrastructure FADING ("already leading" is how the hot panel names HOT) | a wording gap |
| Chains | 24 vetted; TON shown as "GRAM" | yes: CoinGecko renamed it "Gram (prev. Toncoin)" |
| Coin detail (SOLV) | guardians: Holders paid red, Security red (exploit 2026-03-06, $2.7M), Thin liquidity caution ("exchanges carry it"), Team not checked (HTTP 403) | yes, against `degen_level.checks` |
| Coin detail (SOLV) | "Next unlock **Oct 19 · in 5 days**" read on Oct 15; the coin API says 2026-10-18 04:10 UTC | **no**, see below |
| Loading | cold: 8.4 s to DOMContentLoaded, 577 kB transferred (2.9 MB HTML); warm: TTFB 0.86 s, 0.95 s; slowest call `/supply-analyzer/batch/gem-screener` 2.2 s; no console errors | |

## 4. Defects, gaps, improvements

**Defects** (each needs a check and a report; see the end of this section):
1. **Two "Dilution" lines that disagree.**
   - On the same page, the Dilution gate passes up to 1 % of market cap a week, about 52 % a year. The SUPPLY column, labelled "Dilution, 12 months", turns red at 25 % a year.
   - SOLV is red at +32.1 % on the row and passes the Dilution gate in Degen picks.
   - This is the page against itself, the same class as "hot" meaning two things (filed earlier, fixed).
2. **"Retail" is two different numbers on the altseason panel.**
   - The tile shows 20/100 "asleep" (retail-v4). The euphoria line shows 48/100 (the older measure), and that older measure is the one the index uses.
3. **Kinetiq's next unlock contradicts its own record.**
   - The coin API's `unlocks.next_cliff` puts 12.9M KNTQ on 2026-10-27, while the same record's `next30_tokens` (from 10-08) is 0.
   - The Supply Analyzer, which the coin detail reads, puts the same 12.9M on 2026-11-28.
   - It is 1 of 17 rows with a cliff. On 9 of the others the two sources sit up to 21 h apart, which moves the shown date by one day (SOLV: Oct 18 in the coin API, Oct 19 on the page).
4. **The unlock countdown is a day stale.**
   - "In N days" is counted from the Supply Analyzer's refresh (2026-10-14 11:07 UTC), not from the moment it is read: 0.8 days long on 17 of 17 rows.
   - SOLV reads "Oct 19 · in 5 days" on Oct 15.

**Our side:**
- The run-rate check (#141) reads red on one row, FUL: 24 of its last 30 days have revenue, and it is annualised as a day's average × 365, which is the page's own wording since the coverage fix.
- The error is in our check, which still averages over 30 calendar days. It needs correcting; nothing is owed by them.

**Documentation gaps** (to pass on):
- **Growth 6M on rows with gaps.** Ten rows disagree with a recompute from their own series by more than 2 points. Examples: SPK 108.5 against 80.0, and SUDO −1.2 against +17.2. Each counts 26 weeks where only 18 are complete. How missing days enter the weekly sums is not written down. None of the ten is a pick.
- **"Share to holders" shows 100 %** for MOR, DUST and RAM, where DefiLlama's holders revenue is larger than its total. The source is inconsistent, and the page clips the figure without saying so.

**Improvements** (goals for the next Build it Better request; nothing is filed):
1. **Liquid:** a pick row says where its liquidity is and what a $10K buy does in the main pool. A pick that passes on off-chain volume alone is labelled that way.
2. **Dilution:** "unknown" is shown as unknown on the gate, not as a pass.
3. **Real revenue:** a coin whose emissions exceed its revenue says so in `risks` and in the pick's warnings.
4. **Growing:** a pass on a fit with r² near 0 is not called growth, and the 30-day fall shows beside the pass.
5. **Altseason:** the panel says, where it shows the index, that its own acceptance checks read `fail`, the way Top Picks shows its backtest.
6. **Sectors:** "Hot right now" names every HOT sector, and "already leads" is kept for HOT.

**Filing is held.**
- The four defects above need a check each and an admissible run.
- Every preregistered run aborts today on `tests/meta`: an operator quote in `scripts/company.py` (2026-10-13) is not pinned by hash.
- Adding the pin is the operator's call (CLAUDE.md, `[operator DATE]`).

## 5. Not checked this time

On-chain holder concentration, wash trading and what an audit actually covers, as before.

## 6. To repeat

`python scripts/gem_audit.py tick` redoes every number here in about a minute and says what moved. The core checks (`tests/rest/test_gem_screener_*`) ran today: 10 passed and 1 failed, the one in section 3. `/gem-audit` is the whole procedure.
