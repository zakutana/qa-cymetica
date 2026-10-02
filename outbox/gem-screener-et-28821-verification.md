# ET-28821: our check of the delivery against the 76 checklist lines

Read 2026-10-02 05:00 UTC: the live snapshot of 2026-10-01 23:35 UTC (215 apps, 33 chains), `/api/v1/gem-screener/` (coins, picks), `/openapi-public.json`, `/llms.txt`, and the live page in a browser as a signed-out visitor at 1360 and 390 px. Their report is stored as `et-28821-delivery-report.md`; nothing in it counted until measured here. Read-only; nothing was clicked that starts work on their side.

**Result: 50 of 76 lines measured and met, 6 differ, 20 not looked at.** "Not looked at" is not "met".

## What differs (6 lines)

| Line | What we measured |
|---|---|
| 2 · TVL without the chain's own token | Not done, their item a (`tvl_own_token_removed: false` on all 33 chains). Disclosed |
| 2 · a 10x fake lifts adoption by less than 3x | 30 of 33 do; Cronos 3.16, Tezos 3.08, Mantle 3.05 do not. We recomputed all 33 from their own caps and got the stored values. Disclosed (b) |
| 19 · a chain's Generate report follows the rules of item 18 | It has no Pro badge and no lock, and writes eight lines from the chain's numbers. Disclosed (s) |
| 24 · the row of gates looks exactly like the mock | At 1360 px the rule words under the gate names sit 3 to 4 px apart; the mock does not crowd them. Disclosed (k) |
| 24 · the gate tooltip says the rule in plain words | **Not disclosed.** Every gate tooltip is cut at about 250 characters with "…". Gate 7 stops at "Hyperliquid, the benchmark…": the benchmark's figure, "no data passes" and the 2x rule are cut. Vetted stops at "and still…" |
| 25 · 8 picks of 215 | 7. fx Protocol carries the "supply sources disagree" tag (ratio 6.643 recomputed). The spec's own rule, disclosed (d) |

## What held, recomputed (not their word)

- **Chains (1).** 59 tokens, 33 listed, 26 left out: 12 with no DefiLlama row, 12 with a missing input, 2 with no market row. Every missing input matches what they stated. All 33 have four inputs above zero, none older than 30 days. BTC, TAO and IOTA are off; XRP, ADA, HBAR, CRO, ALGO and SEI are on.
- **Adoption (2).** Fourth root of the four inputs, worst gap 7e-8 over 33 chains. The 80th percentile recomputed from the listed chains: 533 and 204 users per $1M, 5.99 DEX turnover, all equal to theirs. Held back (Near volume 78%, Solana 50%, Polygon 33%, Algorand users 43%) follows the caps.
- **Benchmark (3).** The 19 eligible chains recomputed from their own rule give 123.607, the same members. Upside = benchmark ÷ (market cap ÷ adoption) on all 33. The other field, `median_mult` 64.465, is the median over all 33 priced chains, not the benchmark.
- **Dilution (10, 25).** Levels recounted from the apps: 88 ok, 10 caution, 19 red, 98 unknown, as stated. `week_pct` equals the larger of emissions and unlocks, per week, over market cap, for every app that has it. The 22 apps with the supply tag recounted. 7 picks, gate set version `dabb06d79c3a`, Collector Crypt among them (24.7x).
- **Chart (7).** 24 exchange candles, 4 DEX pools, 5 not scored, as stated; weekly 6 of 33.
- **Web chips (13).** 215 of 215 apps and 33 of 33 chains have an address (213 DefiLlama, 2 CoinGecko); DEXTools on 179 apps.
- **Page.** Badges 92 x 78 on both tabs, pinned header and toolbar 220 px, 56 x 48 at 390 px; the Chains badge reads "124x ADOPTION" and names the 19 chains. Stader's detail (Upside in the header, Degen meter without its two lines, Monthly revenue, Chart with Strength 3M, "Market cap & supply" with "in 3 days · 918,750 tokens · 1.3% of circulating · $111K · insiders", Trajectory, Checks, "Generate report · Pro · Opens in 6 days", then the three collapsed lines) and Solana's detail (the slim row, the monthly series, the Chart card, its own report section) are in the order asked. None of the old lines ("net", "covers the new tokens", "no mint", "DeFiLlama · Oct", "Range", "Was … at the last report", "the usual month", "Not a forecast", "Growth per month") is on the page. Every link that leaves the page, on Top Picks, Apps, Chains and the two details, has `target="_blank"` and `rel="noopener"`. Sectors has Theme first and Stage second; the launch icon is on the Memecoins row and its panel only, and opens https://cymetica.com/launchpad in a new tab. The lane runs #6 to #1 into the Degen picks gate. No sideways scroll of the page at either width.
- **Our own audit** (`gem_audit.py tick`) runs on the new build: 0 breaches in 1225 recomputed rows, 0 picks that open another coin.

## Not in their part 4 (for them)

1. **The gate tooltips are cut** (above).
2. **The agent-facing docs did not follow the build.** `/llms.txt` has no word on dilution (0 mentions of `dilution`, `dilution_per_week`, `supply`, `next_unlock`); `/openapi-public.json` has them. Both still document `earnings_after_emissions_30d` (revenue minus emissions) and `revenue_bought_with_emissions`, and the coin record still returns them (Pharaoh: 1,172,802 USD), the very subtraction item 10 removed from the page. The new `GET /api/v1/gem-screener/report-access` (answers `{"can_ask":false,"reason":"sign_in"}` to a visitor) is in neither document.
3. **The first two ledger cohorts were recorded before the build was complete**: 22:47 UTC with 7 picks and 23:00 UTC with 8, both tagged with the new gates version, while their own note says the page had data of the old shape until 23:16 and no chart scores until 23:36. The series that must run 26 weeks starts on those lines.
4. **Stader's tile reads "emissions 30d: $0" beside "+0.3% new tokens a week"**; the figure comes from the unlocks. Minor.

## Not looked at (20 lines), and why

- Needs a Pro account, which we do not have: a Pro account is never refused for its plan (item 18); the report icon scrolling to the report (18).
- Hover text not read: the tooltips of the Hot sectors card, Degen meter, Monthly revenue, Chart card, pick card and Upside (items 9, 12, 14, 15, 20, 16); the benchmark's figure in the flag tooltip (10).
- Drawing, not measured: the five-bar emblem (4); the word BENCHMARK at 8 px or more, no control covered at 390 px (8); the chevron and the dashed floor of the lane (26); Upside drawn as the table cell (16).
- Not opened: Monad's detail without an empty card, a Chains Chart column header sorting as on Apps (7); a stream or "unknown" in the unlock tile, a red flag on Pharaoh (11); the Memecoins icon on a hot Top Picks card (22; they say it is covered by a test only); the 26-week criteria printed in the backtest block (25); the "not a sort key" line (10); in-page links behaving as before (23).

## What to answer on part 4 (decided, the veto is open)

Accept as disclosed: a, b, c, d, e, f, h, i, o, p, q, r. They follow the spec's own rules or the Apps column, or are what the data allows.
Ask for a change: **k** (the crowded words and the tooltip over the pick count), **m** (tooltips to about 25 words, number first), **n** (rename "Earns after new tokens" to a revenue name, and move "Held at 8 or above" into the meter's tooltip: both are the mixing and the small grey line the spec removed), **j** with the docs (item 2 above), **t** (document `report-access`), **g** (build the scorer; say by which date), and our three: the cut tooltips, the first ledger cohorts, and the unlock tile label.
