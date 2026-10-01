# Gem Screener: wishes for the next Build it Better request (goals, not methods)

Collected in conversation, 2026-10-01. Not filed, not sent: they go into the operator's next request when there is one. Item 1 is the operator's position ("chains should not be taken from the DefiLlama revenue list"; "the better list is defillama.com/chains"); the goal wording and the source split are ours, the operator's veto is open.

## 1. Chains: which chains are listed
Goal: the Chains tab lists the L1 and L2 chains a degen would look for. The list is every chain whose native token is in CoinGecko's "Layer 1" or "Layer 2" category above a market-cap cut; each is joined by `gecko_id` to DefiLlama's chain list (the data behind defillama.com/chains) for TVL, users and stablecoins. A chain with no DefiLlama row or no such data stays listed and shows "no data"; fees above a floor are not a condition for being listed.

Seen, 2026-10-01 (snapshot 13:42 UTC; CoinGecko and DefiLlama read the same evening):
- The tab has 26 chains. Of CoinGecko's top 40 Layer 1 coins, 17 have a DefiLlama chain row and are not on the tab: BTC, XRP, ZEC, ADA, BCH, LTC, CC, HBAR, TAO, CRO, ETC, ALGO, STABLE, VET, XDC, FLR, SEI. Seven more have no DefiLlama row (XMR, M, KAS, PI, NIGHT, BDX, TIA): they would show "no data".
- IOTA is rank 49 of CoinGecko's Layer 1 ($258M) and has a DefiLlama row (TVL $2.0M, `gecko_id` iota, plus "IOTA EVM", $0.7M); it is not on the tab. Sui is rank 17 and is on the tab.
- DefiLlama `/v2/chains`: 468 chains, 316 with a `gecko_id`, fields chainId, cmcId, gasTokenGeckoId, gecko_id, name, tokenSymbol, tvl. No field says L1 or L2, so DefiLlama alone cannot give the "L1 and L2" list; CoinGecko's two categories do. L2BEAT and CoinMarketCap tags not looked at.
- The Layer 2 category is noisy below the top (first is OKB, X Layer's token; the 100th is under $1M), hence the market-cap cut.

## 2. Chains: the default view hides 11 of 26 without saying so
Seen: "Vetted only" shows 15; "All by upside" shows 26. Sui (rank 11 of 26 in All) is hidden by default for `far_below_peak` ("Not vetted: post-crash"); nothing on the page says that chains are hidden or how many.
Goal: the default view says how many chains it hides and why, in one short line, and a hidden chain such as Sui can be found from the page itself.

## 3. Chains: adoption without fees
The operator's position, already item 13 of ET-28606: "Yearly activity fees say what users paid, not how many use the chain." A cheap chain with many users is not less adopted than an expensive one.
Seen, 2026-10-01: the live adoption is the geometric mean of the chain's yearly fees and its daily users valued at a reference fee, adoption = sqrt(fees × users × ref_fee_per_user_day × 365), `ref_fee_per_user_day` = 1.2016. Recomputed on Avalanche, Polygon, Aptos, Ethereum, Starknet and Solana: equal to the page's `adoption.value` to the dollar. So fees still carry half the weight: at the same users, a chain with fees 10× cheaper gets about 3.2× less adoption. Ethereum has about 4× Sui's users (520K against 131K a day) and about 15× its adoption ($608M against about $40M).
Goal (operator, 2026-10-01: TVL, volume and active users must count, and it must not be fakeable): a chain's adoption, its price-tag line and its Upside do not depend on what a transaction costs there, and no single input can be inflated cheaply to lift them.

Proposal, a good default the builder may improve (say what changed and why):
- **Inputs per chain, from DefiLlama.** U = active addresses a day, the lower of the 30-day and the 90-day median (a campaign spike counts only once it lasts). V = DEX volume over 30 days. T = TVL without the chain's own token and without double counting (TVL in its own token rises with the price it is meant to judge). S = stablecoins on the chain.
- **Rule against faking: cheap signals count only as far as expensive ones back them.** Addresses and volume are cheap to fake (bots, airdrop farming, wash trading), and cheapest on cheap chains; TVL and stablecoins cost real money. So U counts at most up to the 80th percentile, across the listed chains, of users per dollar of T, and the same against S; V counts at most up to the 80th percentile of 30-day turnover V/T. The 80th percentile is a starting point.
- **Index.** Real adoption = (U × V × T × S)^(1/4) with the capped U and V: a geometric mean, so no input carries a chain on its own.
- **No fees.** A fee in dollars is gas times the token's price, so it rises with the price it is compared with, and it marks cheap chains down. Fees may stay as a column, never as a factor.
- **No Metcalfe (users squared).** It squares fake addresses, and across today's chains market cap grows with users at a power of about 0.4, not 2: with n² every small chain would look many times too cheap.
- **Upside.** Not one benchmark chain's multiple: a fair-value line fitted across all listed chains at each refresh (log market cap against log adoption), and a chain's Upside is its distance to that line. A chain missing an input shows it as missing and stays off the line.

Tried on the page's own data, 2026-10-01, the 22 chains that have all four inputs (TVL there still includes the chain's own token; the page does not split it):
- Order: Ethereum, Solana, BSC, Tron, Polygon, Arbitrum, Avalanche, Hyperliquid L1, Monad, Sui, X Layer, Plasma, OP Mainnet, Stellar, Near, Aptos, TON, Mantle, Starknet, Linea, ICP, Filecoin.
- The caps cut users on Filecoin (−98 %), TON (−80 %), Near and ICP (−77 %), Aptos (−43 %), Sui (−39 %), Tron (−25 %), Polygon (−15 %); volume on Near (−76 %), Solana (−48 %), Polygon (−32 %), Hyperliquid L1 (−27 %).
- Faking 10× the users and 10× the DEX volume lifts the index ×1.3 on Sui, ×2.1 on Monad, ×1.0 on Near; without the caps ×3.2; today's users-and-fees measure ×3.2, or ×10 if the fake transactions also pay fees.
- How well each explains market cap across the 22 (log-log R², slope): this index 0.46 (0.57); TVL alone 0.47 (0.65); stablecoins 0.39 (0.43); users 0.34 (0.40); DEX volume 0.41 (0.50); fees alone 0.27 (0.30); today's measure 0.59 (0.86, 20 chains). Today's measure fits best partly because fees and own-token TVL move with the token's price: the price explaining itself.
