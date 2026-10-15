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

## 3. Defects, gaps, improvements

**Defects: none new.**
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

## 4. Not checked this time

- The browser pass: the page's default view, the backtest line, the altseason panel, cards and load time.
- On-chain holder concentration, wash trading and what an audit actually covers, as before.
- From the tick only: the altseason headline shows the 4-week mean breadth (62), while the latest week is 56.

## 5. To repeat

`python scripts/gem_audit.py tick` redoes every number here in about a minute and says what moved. The core checks (`tests/rest/test_gem_screener_*`) ran today: 10 passed and 1 failed, the one in section 3. `/gem-audit` is the whole procedure.
