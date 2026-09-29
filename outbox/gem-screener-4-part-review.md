# QA review: the four gem-screener specs as one build (`0a185e8`)

Read against each other and against the live site on 2026-09-29 (snapshot 05:57 UTC; page rendered
at 1200 px; read-only GETs only). Parts 1 to 3 are byte-identical to `3d8719f`, and every file,
function and section they cite exists on `altseason-cycle-2r6d3t`.

| Part | Verdict |
|---|---|
| 1. Altseason panel | **READY WITH NOTES** (copy only) |
| 2. Chain valuation | **READY WITH NOTES** (fees alone do not fix its own Tron example) |
| 3. Sectors tab themes | **READY WITH NOTES** (two items need a home; Part 4 or the build gives it) |
| 4. Degen level + coin detail | **READY WITH NOTES** (three edges, one colour rule, four gaps) |

Nothing is BLOCKED. Filing is: ET-27671 is still open, and a second request for the same app
creates nothing (ET-27886). Part 4's "as it is live today" then means the page after ET-27671.

## Conflicts and recommendations

**Across parts**

1. **"Alts not moving yet" above "already leading".** On the Sectors tab Part 1 will show index ~23
   "Alts not moving yet" (its §9), right above Part 3's themes, where 8 of 12 are tagged "already
   leading" today and breadth reads 68%. The old card said 68% "In between" the day before. Part 1
   allows copy changes: rename `zima` to "No altseason yet", and let its "i" say the old 68% is
   now the breadth row.
2. **Top Picks keeps what Part 3 and Part 4 change.** The Hot sectors cards reuse the theme tags
   ("Memecoins: BTC +10% -> +14%, waiting to run"), and the Degen pick cards show the old flags as
   badges ("REVENUE BOUGHT WITH EMISSIONS", "NEW", "NO HOLDER SHARE", "CLIFF OCT 18 +4%"). The Hot
   sectors cards should come from Part 3's new theme result. The Degen pick cards should get Part 4's
   mini meter; otherwise A.7 deletes the Legend entries these badges still use.
3. **One chain-activity measure.** Part 2's price tag and Part 3's L1/L2 fundament fix the same
   stablecoin weakness. Use one measure for both, or the Chains tab and the L1 row judge the same
   chains differently.
4. **One vocabulary, one meaning.** `insufficient_history` means under 40 weeks in Part 3
   ("méně než 40 týdnů historie") and under six months in Part 4. Carry the threshold with the code.
   "No Czech" should cover the whole `GET /api/v1/gem-screener`, which llms.txt hands to agents:
   today it also carries Czech in the degen gate names, `reliable_fail`, `traj` ("Zážeh",
   "Setrvalý"), `bench_chains.label` ("medián chainů") and the backtest verdict ("NEPRŮKAZNÉ").
   `/coins/{symbol}` is already English with units, which is the model to follow.
5. **Market data.** This morning's snapshot kept 240 of 241 prices from the previous run
   (CoinGecko 429/403 on five batches; the page says so). The four parts add many more calls. Use a
   paid market feed, which every part allows.

**Part 1**

6. "Every past altseason top went above 75" (§7.2) contradicts its own table: P2b (2021-11) = 62.1.
   Say "Both big tops (Jan 2018, May 2021) went above 75."
7. §7.3 "covered N% of the way ... to the last cycle's low 37.9%" is false whenever the 25-point
   minimum span applies. That includes its own example: 60.0 − 37.9 = 22.1 < 25. Say "of a 25-point
   drop" when the span applies.
8. OTHERS.D is "share of the market" in the copy but ranks 11–125 ÷ top 125 in §4.1. Say "of the
   top 125".

**Part 2**

9. **Fees alone keep Tron cheap.** The API already carries fee-based upside (`potential_fees`, at
   today's median of 1,266× fees). On it Tron is still #4 (11.4×, $287M/yr, mostly USDT transfers).
   Canton ($588M/yr at 9×) and Quai hit the 50× cap. As the largest-fee chain, Canton would become
   the "leader" at 9×, and almost nothing would show upside. Discount or drop stablecoin-transfer
   fees, guard against outliers before choosing the leader, and show Tron and Canton before and
   after in the note.
10. The **STABLECOINS column** conflicts with "design unchanged". Show the new measure in that
    column, in the same layout.

**Part 3** (frozen; what the build or Part 4 does)

11. **The links need a home.** About 113 of 177 theme coins are neither an app nor a chain, so they
    have no detail view and no website link: the API holds only symbol, name and logo, and clicking
    DOGE in a theme opens nothing. Put CoinGecko and DEXTools in Part 4's header next to "web ↗" for
    app coins, and on the coin's line in the theme panel for every other coin.
12. Confirmed live: L1 holds BNB and CRO, and L2 holds OKB and MNT.

**Part 4**

13. **Edges overlap.** Timelock 48 h, Real yield 2× and Strength 3M 1× are both green ("X or more")
    and light blue ("A–B includes both ends"). The spec's own example (2× is green) and
    `reference.html` both pick green. Write "24 to under 48 h", "1 to under 2×" and "0.5 to under
    1×". For Price run write "+53% or more, within 10% of the ATH".
14. **Upside and grey.** C.4 keeps Upside's live tier colours, but live shows 52 of 113 Upside
    values in grey (every value up to 2.5×), and D says grey means missing. A.5 freezes the row, so
    D needs an exception: for Upside, grey means little upside.
15. **Reaches you starts from data.** A.2 maps today's automatic "No holder share" flag to a
    report-only check, which would turn a known red into dashed. `reference.html` already makes it
    red when the holder share is under 5%, so say that in B and C.9. For Audit, B says it starts from
    DefiLlama, while C.9 and the reference keep it dashed until the report. Keep it dashed, and use
    DefiLlama as the report's input.
16. **The report must research.** Today's report is "built only from the snapshot's facts"
    (OpenAPI, llms.txt), so it cannot answer Team, Audit or Track record. Part 4 needs a sourced
    research step: a new pipeline with a cost. Say so, or every meter stays dashed (B's "more than
    a third uncertain" warning).
17. **"The range disappears"** after the report (C.9) only holds when nothing is also "not
    scanned", "needs history" or "stale data". Write "narrows to what the report cannot fill".
18. **n/a:** B says it does not widen the range. In `reference.html`, an area whose every check is
    n/a falls back to the fill value (0, 0.5 and 1) and widens the range by the area's weight. Drop
    such an area and rescale the rest to 10.
19. **Dropped tiles need a place.** Today's detail also shows Earned after emissions, Yearly revenue,
    Price vs revenue, Worth at Hyperliquid price, 30x test (a Degen gate) and Revenue growth 6M. C
    does not say where they go. Keep at least the 30x test, in a collapsed row.
20. **FDV overhang goes unseen.** UP has 4% of tokens out (FDV 23× market cap) and no unlock within
    90 days, so Unlocks is green and none of the 18 checks sees the rest. Add FDV ÷ market cap to
    Supply.
21. **Wording:**
    - Acceptance 1, "the Chains tab is unchanged", reads against Part 2. Write "Part 4 changes
      nothing on the Chains tab".
    - The "No data (no stablecoin data)" entry becomes whatever missing-data flag Part 2 leaves.
    - Say whether a chain row keeps today's detail; the 18 checks are app checks.
    - A click on "tradeable here" opens the Legend, not the detail (A.4 vs A.7).
22. Confirmed live: in the detail, the quarter table ends 28 px and the Growth windows table 9 px
    past the panel at 1200 px. C already asks for the fix.
