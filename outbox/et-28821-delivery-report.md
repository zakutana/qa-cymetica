# ET-28821: the vendor's delivery report (data from Cymetica, pasted by the operator 2026-10-02)

Four messages, `@expire76`, "ET-28821 is live on cymetica.com/gem-screener/app, all 26 items, data published 23:36 UTC on 1 Oct". Stored verbatim as what they claimed; none of it is verified by being here. Our check of every line is `gem-screener-et-28821-verification.md`.

## Part 1 of 4: Chains

1. Chain list. Cut: CoinGecko Layer 1 or Layer 2 category, market cap $200M or more at the refresh, joined to DefiLlama by gecko_id. Today 59 tokens, 33 listed, 26 left out. A chain is listed only with all four inputs, each above zero and at most 30 days old. Fees are no condition. Chains without a token of their own stay off.
Left out, no DefiLlama chain row (12): XMR, M, KAS, PI, NIGHT, BDX, TIA, DRV, PRL, KITE, DCR, AR.
Left out, input missing: BTC (stablecoins), LTC and ZEC (DEX volume, stablecoins), CC and RUNE (users, stablecoins), TAO and IOTA (users, DEX volume, stablecoins), THETA (users, DEX volume), INJ, STX, XDC, VET (users). BCH and ETC had no market row at this refresh.
Your nine: XRP, ADA, HBAR, CRO, ALGO, SEI are on the tab. BTC, TAO, IOTA are not.
The same list is in the snapshot (chains_universe.left_out) and in About.

2. Adoption = fourth root of (users x DEX volume 30d x TVL x stablecoins). Fees are not an input. Users = the lower of the 30-day and 90-day median of daily active addresses.
Holding back, your default, cut at the 80th percentile across listed chains: users count up to 533 a day per $1M of TVL or 204 per $1M of stablecoins (the larger); DEX volume of 30 days counts up to 5.98 x TVL.
Held back when measured at 21:53 UTC: volume on Near 78%, Solana 50%, Polygon 33%, Hyperliquid 32%, Sei 25%; users on Algorand 43%.
10x-fake test (stored per chain as adoption.fake_10x_lift): Solana 1.12, Polygon 1.13, BSC 1.15, Avalanche 1.18, Near 1.18, TON 1.31, Sui 1.48, Arbitrum 1.78, Monad 1.99, Tron 2.70, Ethereum 2.94, Plasma 2.99. 30 of 33 are under 3x.

3. Benchmark: 123.6x, the median price tag of 19 chains: Ethereum, Solana, BSC, Tron, Polygon, Arbitrum, Avalanche, Hyperliquid, Sui, X Layer, Stellar, TON, XRPL, Mantle, Cronos, Cardano, Algorand, Hedera, ICP. Eligible = $1B or more, a year of TVL history, every input at most 10 days old, at most half held back. Near is out (78% of volume held back), 13 chains are under $1B. Upside = benchmark / the chain's multiple. Top today: Polygon 29x, Monad 27x.

4. Chains badge: your five-bar emblem, the live number (124x), ADOPTION. Tooltip names the 19 chains. Apps badge unchanged.

5. Gas tag on Arbitrum and OP Mainnet (ETH), and by the same rule on Gnosis (xDAI) and Stable (USDT0). The row and its Upside are untouched.

6. Adoption column, detail, price-tag line and Upside all use the new adoption. The API record carries the four inputs, the held-back values and the adoption; fields are documented.

7. Chart on Chains: same column, cell and tooltip as on Apps, between 12 months and Upside. Scored from exchange candles (24): Ethereum, XRPL, Solana, Tron, Cardano, Stellar, Near, BSC, Sui, Hedera, TON, ICP, Algorand, Polygon, Avalanche, Filecoin, Aptos, Sei, Plasma, Arbitrum, Starknet, Tezos, OP Mainnet, Kaia. From a DEX pool (4): Cronos, X Layer, Mantle, Gnosis. Not scored (5): Hyperliquid, Monad, Stable, Provenance, Flare; they show the dash an unscored app shows, and their detail has no empty card. An answer is refused when its last candle is over 3 days old or its close is more than 2x off the row's price (the old TON ticker still answers with candles that end in June).

8. Sizes at 1360 px: badge 92 x 78, toolbar 90, pinned header and toolbar 220. Both badges the same size. At 390 px the ET-28688 rule holds and nothing is covered.

## Part 2 of 4: revenue, dilution, supply, the seventh gate

10. Revenue is shown as revenue everywhere: no "net" line, no "net unknown", no "revenue covers the new tokens" tile, no "after paying" line, nothing subtracted in the Earnings row. The tooltip says what the number is: income of the last 30 days in USD.
Dilution is one figure: the larger of the emissions of the last 30 days and the unlocks of the next 30 days, per week, against market cap, labelled gross. The Supply card, the Supply row of the checks, the flag and gate 7 all read that figure.
Flag: caution above 0.5 points a week over the benchmark, red above 1 point. The benchmark (Hyperliquid) is at 0.0% a week today, so the lines sit at 0.5% and 1.0%; they move with it, and the tooltip names its figure. The flag is not a sort key. On the pick cards it replaces the old warning.
Today: 88 ok, 10 caution, 19 red, 98 unknown. Unknown is never shown as zero.

11. The card is now "Market cap & supply": the bar, then market cap | FDV with the share of tokens out | new tokens a week with its flag | next unlock in its own tile. Examples live: Stader "in 3 days, 918,750 tokens, 1.3% of circulating, $112K, insiders"; Pharaoh "none in 90 days"; Nexus Mutual "unknown". A daily stream is shown as a rate. The 90-day total, the source and its date are in tooltips; no foot line. The "revenue covers the new tokens" tile and "no mint" are gone. Next unlock today: 22 apps with an event, 35 with a stream, 58 with none in 90 days, the rest unknown.

25. Gate 7 is Dilution: fail above 1% of market cap a week. Theme wind is no longer a gate. One supply figure for Upside and Dilution: CoinGecko circulating supply.
Where CoinGecko circulating and DefiLlama unlocked supply differ by more than 2x, the app carries the grey "supply sources disagree" tag and is not a pick: 22 apps today.
Gate 7 stops 29 apps: 19 for dilution above 1%, 10 for the supply tag alone. An app with no emissions and no unlock data is not removed; it shows "dilution unknown" in grey.
Result: 7 of 215 pass all 7 gates, Collector Crypt among them (25x). Your spec expected 8: see part 4.
Gate set version changed (f226923375fa to dabb06d79c3a) and the picks ledger starts a new series. The old backtest is labelled as judging the old gates. No other threshold changed.
What the new series must show before it counts as better (written down on 1 Oct, before any result, and printed on the page in the backtest block): every refresh records the picks of the new gates and, beside them, the picks the old gates would have made that day. One selection a week is scored as the median pick against BTC. The new gates count as better only after at least 26 weeks and at least 15 different coins picked, if their median pick beat the old gates' median pick against BTC and the 90% bootstrap interval of the difference lies wholly above zero. Interval includes zero: inconclusive. Wholly below zero: worse. No verdict before week 26. The control group is recorded from the first line; the code that scores the comparison is not built yet (part 4).

## Part 3 of 4: Top Picks and the detail views

9. Hot sectors card: sector name, stage pill, trend icons, fund line. The "vs the median sector" and "Leaders" lines moved into the card's (i). The paragraph under the backtest verdict is behind the verdict's tooltip; the verdict line and the reason lines on the pick cards stay.

20. A pick card ends with the Degen meter. The "if valued like Hyperliquid" line and the bottom block are in the card's tooltip.
21. Sectors table: Theme first, Stage second.
22. Memecoins carries the small launch icon ("Launch your own memecoin", opens the launchpad in a new tab) in its Sectors row and its panel. No other sector has it.
23. Every link that leaves the page opens in a new tab with rel="noopener". Checked in a browser on Top Picks and Chains: none left without it.
24. "Altseason index" with an (i); the "This week" line is in the tooltip. "7 of 215 apps pass all 7 gates" stands in the Degen picks section. Under it the seven gates in a row from your mock, between the 215 block and the glowing Degen picks gate with the pick count. Both numbers come from the snapshot at each refresh. Each gate opens the dark tooltip on hover, focus and tap; nothing below moves.
26. Near-misses lane: the Degen picks gate at the right end, chevron pointing right, queue #6 to #1 from the left.

12. Degen meter card: number, verdict, bar, the two end labels. "Range" and "Was" lines are in its tooltip.
13. Web, CoinGecko and DEXTools are icon chips in the Share chip's style; each shows only when its address exists. 215 of 215 apps and 33 of 33 chains have a web address (213 apps from DefiLlama, 2 from CoinGecko). DEXTools only where there is a DEX pair.
14, 17. Order in an app: Degen meter, Monthly revenue, Chart, Market cap & supply, Trajectory, Checks, then the three collapsed lines last. The "usual month" lines are in the section's tooltip.
15. Chart card: score and band, 90-day chart, scale, "Open in Chart Analyzer". The three grey lines, "not a forecast" included, are in its tooltip.
16. The six-tile grid is gone. "Upside potential" is in the header, drawn as the table cell with its symbol. Strength 3M is a coloured figure in the Chart card.
18. The card under the Degen meter is gone. "Generate report" with the Pro badge is in Checks; the report stands under the checks; the header's report icon scrolls to it. A locked button says why beside it ("Opens in 6 days"). For an account with the plan the badge is plain text and the button is disabled only by the lock or while researching. The Trajectory caption is in its tooltip.
19. A chain's detail: header with Upside and chips, a slim row (Market cap, Adoption), the monthly series, the Chart card when the chain has a score, Trajectory, its own report section, then "How it's calculated" and "For AI agents" last and collapsed.

Checked live as a signed-out visitor at 1360 and 390 px (Top Picks, Chains, Solana's detail, Stader's detail): no script errors, no sideways scroll of the page.

## Part 4 of 4: what is NOT met or differs from the spec ("Tell me which of these you want changed.")

Data
a. TVL without the chain's own token: not obtained. The free DefiLlama API does not split a chain's TVL by token, and rebuilding it from pool data covered between 2% and 1787% of a chain's TVL, so I rejected it. Used: DefiLlama's chain TVL as published (liquid staking and double counting already out, the own token still in). The page and the API say so (tvl_own_token_removed: false).
b. The 10x-fake test fails on three chains: Cronos 3.16, Tezos 3.08, Mantle 3.05. Their users and volume sit far under what their TVL backs, so nothing is held back and the lift is the bare 10^(2/4). Closing it needs a different formula; I kept yours.
c. The benchmark is 123.6x, not about 60x. Item 1 added XRPL, Cardano, Hedera, Cronos and Algorand, all priced far above their adoption.
d. 7 picks, not 8. fx Protocol is out: its two supply sources are 6.6x apart, so it carries the "supply sources disagree" tag.
e. Linea and ZKsync Era are under $200M, so they are not listed and carry no gas tag.
f. "A year of data" is measured on TVL history; address counts start only months back for many chains.
g. The scorer for the new-against-old picks comparison is not built. Nothing can be read before week 26; the control picks are recorded from today.
h. Weekly chart scores on chains: 6 of 33 so far. Chain scores are read at most 40 calls per refresh, daily first; the rest fill in over the next refreshes. Hyperliquid gets a score once 60 daily candles exist for it.
i. A web address is checked by its shape, not by opening the site.
j. For agents, the picks field earnings_after_emissions_30d is renamed dilution_per_week.

Page
k. Gate row: the rule words under the gate names run close together at 1360 px, and at 390 px the row scrolls sideways. The gate tooltip has no pointer and can cover the pick count.
l. I removed the "Top Picks" eyebrow and added an (i) to the pick card for the moved lines.
m. Some tooltips run to about 45 words.
n. The Degen meter's check still reads "Earns after new tokens". The "Held at 8 or above" line stays on the meter card. The thin-trading and "latest read failed" notes stay on the Chart card: they are warnings and the item did not name them.
o. The Memecoins icon on a Top Picks hot card is covered by a test only; Memecoins is not hot today, so I have not seen it live.
p. The "pharaoh" pool link is removed.
q. The Chart column on Chains is not sortable, because the Apps one is not.
r. A chain without a chart score shows Strength 3M in the slim row.
s. A chain's detail had no report card before this build, and the report research covers apps only. A chain's "Generate report" writes the eight lines made from the chain's own numbers, with no Pro badge and no lock. A researched chain report is not built.
t. Whether the viewer has the plan is asked once per page load from a new read-only address that answers only yes or no for the viewer's own session.

One more thing from today: from 22:37 to about 23:16 UTC the new page was up with data of the old shape (26 chains, 10 picks), and from 23:26 to 23:36 without chart scores and web chips on chains. It is complete since 23:36.
