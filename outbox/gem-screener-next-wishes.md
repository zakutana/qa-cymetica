# Gem Screener: wishes for the next Build it Better request (goals, not methods)

Collected in conversation, 2026-10-01. Not filed, not sent: they go into the operator's next request when there is one. Item 1 is the operator's position ("chains should not be taken from the DefiLlama revenue list"; "the better list is defillama.com/chains"); the goal wording and the source split are ours, the operator's veto is open.

## 1. Chains: which chains are listed
Goal: the Chains tab lists the L1 and L2 chains a degen would look for. The list is every chain whose native token is in CoinGecko's "Layer 1" or "Layer 2" category above a market-cap cut; each is joined by `gecko_id` to DefiLlama's chain list (the data behind defillama.com/chains) for TVL, fees, users and stablecoins. A chain with no DefiLlama row or no such data stays listed and shows "no data"; fees above a floor are not a condition for being listed.

Seen, 2026-10-01 (snapshot 13:42 UTC; CoinGecko and DefiLlama read the same evening):
- The tab has 26 chains. Of CoinGecko's top 40 Layer 1 coins, 17 have a DefiLlama chain row and are not on the tab: BTC, XRP, ZEC, ADA, BCH, LTC, CC, HBAR, TAO, CRO, ETC, ALGO, STABLE, VET, XDC, FLR, SEI. Seven more have no DefiLlama row (XMR, M, KAS, PI, NIGHT, BDX, TIA): they would show "no data".
- IOTA is rank 49 of CoinGecko's Layer 1 ($258M) and has a DefiLlama row (TVL $2.0M, `gecko_id` iota, plus "IOTA EVM", $0.7M); it is not on the tab. Sui is rank 17 and is on the tab.
- DefiLlama `/v2/chains`: 468 chains, 316 with a `gecko_id`, fields chainId, cmcId, gasTokenGeckoId, gecko_id, name, tokenSymbol, tvl. No field says L1 or L2, so DefiLlama alone cannot give the "L1 and L2" list; CoinGecko's two categories do. L2BEAT and CoinMarketCap tags not looked at.
- The Layer 2 category is noisy below the top (first is OKB, X Layer's token; the 100th is under $1M), hence the market-cap cut.

## 2. Chains: the default view hides 11 of 26 without saying so
Seen: "Vetted only" shows 15; "All by upside" shows 26. Sui (rank 11 of 26 in All) is hidden by default for `far_below_peak` ("Not vetted: post-crash"); nothing on the page says that chains are hidden or how many.
Goal: the default view says how many chains it hides and why, in one short line, and a hidden chain such as Sui can be found from the page itself.
