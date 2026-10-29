# D-news: what changed in airdrop farming, 2026-10-15 to 2026-10-29, and November 2026

Written 2026-10-29 ~15:30 UTC. "App" = the Airdrop Farmer list in `cym-farms.json` (45 farms, generated 2026-10-29T13:56Z). Compared against the 24 Oct research (`outbox/airdrop-farms/research/README.md`, 49 farms).

Marks, as in the 24 Oct README: **✓** = I read a primary page or a market source myself (CoinGecko API, DexScreener API, DefiLlama API, the project's own docs). **T** = airdrops.io or another tracker only; a lead, not a fact. Almost all of list 2 is **T**, because the projects' own sites were not reachable or not worth a call; read it as leads.

## Headline

1. **GenLayer is the one app farm with a closure in the window.** Final Season 1 snapshot 25 Oct, registration closed 26 Oct, so the farm is shut to anyone not already registered. The TGE is not announced. The app still shows it as TESTNET (route "tasks"; its own why_not_run already says an agent cannot farm it). The other tracker pages I read for app farms (Hylo, Decibel, Plume, Variational, Saturn, Upshift, Pacifica, Symbiotic, Arcus, Nado, Ink) show no closure in the window.
2. **No app farm launched a token** (DefiLlama protocol records carry no token symbol or gecko_id for the DeFi entries; CoinGecko has no priced token for Variational, GenLayer, Curvance, Avant, Strata; Push Chain, Ekiden, SEKAI have no CoinGecko entry; INK has no TGE per a web search today: the July-September estimate lapsed, the mint date waits on audits). **Limit:** about 30 deposit farms (Theo, Mellow, Bitfi, OnRe, R25, StackingDAO...) have no tracker page and their own season ends were not read; lag of hours is possible.
3. **Fables and Axis Robotics were in the 24 Oct list and are not in today's 45.** The list was rebuilt rather than trimmed (Zircuit, Travala, Sonic SVM, INFINIT, Tempo, Robinhood Chain and Arc are also gone). So the app dropped what had launched; what it lacks is every farm below.

---

## List 1. Token launches (TGE) and claims in the window: these stop being farms

| Name | Ticker | Date | What happened | Chain | App lists it? | Source / mark |
|---|---|---|---|---|---|---|
| **GenLayer** | GEN | Snapshot 2026-10-25 23:59 UTC; registration closed 2026-10-26; **TGE not announced** | Not a TGE yet. Farm is closed: only registered wallets can claim (Discord role, or 150+ points plus an accepted contribution/XP). Token and public network move to Arbitrum (from ZKsync). 20% unlocks at claim, then 20% monthly. A pre-TGE AMA with the Foundation CEO is set for "a Friday 13:30 UTC" (calendar date not given). airdrops.io header says "Claim live" but its own page says claims open at TGE, date TBA: do not trust the header. | Arbitrum | **YES** (chip TESTNET, route tasks) | T airdrops.io/genlayer (updated 26 Oct); T coingabbar.com/en/genlayer-airdrop-arbitrum-migration-bradbury-token-launch-date (23 Oct); CoinGecko `genlayer` exists with no price ✓ (not live) |
| **Cambria** | RSGP | **2026-10-29 15:00 UTC** (TGE; 4th date after three slips) | Token live on Base. First hour: **-64 %**, price $0.00244, FDV $3.3M, liquidity $248k, 24h volume $529k. Points ("Royal Favor"), loot chests and charters convert to RSGP; allocations land in linked wallets. An incentivized testnet is planned for the day after TGE. Genesis opt-in closed 8 Oct. | Base (also Ethereum, Robinhood Chain USDG) | NO | ✓ DexScreener (Aerodrome RSGP/USDC on Base, read 15:20 UTC); T airdrops.io/cambria (28 Oct); egamers.io `?p=126351` (26 Oct) |
| **Axis Robotics** | AXIS | **2026-10-21** (claim portal 12:00 UTC; snapshot 18 Oct) | Live and falling: $0.1436, mcap $23.7M, 24h volume $151M today; $0.2748 on 23 Oct (about -48 % in six days). 10 % of the community sale unlocked at TGE, 6-month cliff, then 6 months linear. Unclaimed, unlocked tokens must be claimed by **2027-01-21 12:00 UTC**. Season 2 started 23 Oct (see list 2). | Base | NO (was listed 24 Oct, dropped since) | ✓ CoinGecko `axis-robotics`; T airdrops.io/axis-robotics (26 Oct); coingabbar.com/en/axis-robotics-airdrop-season-2-launch-with-60m-tokens (23 Oct) |
| **Fables** | FABLES (PROLOGUE redeems at about 37.68 per FABLES) | Points ended **2026-10-19**; snapshot block 91,198,392 on 2026-10-17 20:09 UTC; trading since about 20 Oct | Claims open on claim.fables.fi, deadline **2026-11-21 00:00 UTC**. $0.0622, mcap $2.4M, 24h volume $796k. Claim needs a little ETH on Robinhood Chain. | Robinhood Chain | NO (was listed 24 Oct, dropped since) | ✓ CoinGecko `fables`; ✓ 24 Oct README (DexScreener); T airdrops.io/fables (21 Oct) |
| **The Hood** | HOOD | TGE **2026-10-20**; claim opened 2026-10-26 | Telegram Mini App game (TON). Registration was 25-30 Sep and eligibility fixed then; claim via @Hoodappbot until **2026-10-31 23:00 UTC**. No market read of my own (a CoinGecko `the-hood` id shows a $6k mcap; I did not verify it is this project). | TON | NO | T airdrops.io/the-hood (26 Oct) |
| **predict.fun** | PREDICT | **Claims open 2026-10-30 09:00 UTC** (tomorrow) | Season 1 Predict Points convert to PREDICT; allocation reveal the same day. Launch-day form deadline (29 Oct 09:00 UTC) has passed; later forms are paid in weekly batches until 27 Nov. **Security incident 27 Oct: about 400k USDT in unauthorised transfers; the page says hold off new deposits until the team gives an all-clear.** predict.fun/points confirms a "$PREDICT airdrop" in its page metadata (Season 2 is to "run up your PP ahead of the next $PREDICT airdrop") but shows no date and no results yet; the 30 Oct date is airdrops.io only. | not stated on the page | NO | T airdrops.io/predict-fun (updated 29 Oct); ✓ predict.fun/points (metadata only) |
| **Extended** | EXT | Weekly points **ended** (docs, read today); 69,235,805 of 70M points issued at 6 Oct; **final distribution follows the Final Arc competition** | Not a TGE yet. Points farming is closed except the competition (airdrops.io: 6 Oct to 3 Nov). The docs: points "may be taken into account in connection with a future token distribution"; no ratio, no claim process, no date confirmed. airdrops.io expects EXT shortly after the programme ends. | Starknet / EVM | NO | ✓ docs.extended.exchange/extended-resources/points-program.md; T airdrops.io/extended (23 Oct) |
| **Monolith** | swanUSD, SWAN | TGE **2026-10-22 16:00 UTC** | swanUSD market and the SWAN pool (100,000 SWAN, split equally among qualifiers) launched together. Qualification is still open: see list 2. | Ethereum | NO | ✓ DexScreener (swanUSD/USDC pair created 22 Oct 16:20 UTC, $1.00, liquidity $81k); T airdrops.io/monolith (23 Oct) |

**Closed in the window, not TGEs** (claims or snapshots that ended; a farmer who missed them cannot recover):

| Name | Date | What | App? | Source |
|---|---|---|---|---|
| **StandX** | yield and deposits ended 2026-10-15; perps Reduce-Only 20 Oct; eligibility checker live 26 Oct | The farm stopped; there is no token, a one-time **DUSD airdrop** replaces it. Claim DUSD by **31 Dec 2026 08:00 UTC**; close positions before 15 Jan 2027; redeem/swap DUSD by 31 Jan 2027. BNB Chain. | NO | T airdrops.io/standx (26 Oct) |
| Surf (Cyber) | airdrop 2026-10-19, snapshot 20 Oct | $35k PONS to opened SurfBoards, $15k PONS draw; $15M raise (Pantera). Over. | NO | T airdrops.io/surf (19 Oct) |
| Pharos (PROS) | claim closed 2026-10-25 11:00 UTC | PROS token live since April; the claim page shows "Claim Ended". Season of AI dev programme (5,000 PROS) runs to 12 Nov. | NO (R25, which the app lists, runs on Pharos) | T airdrops.io/pharos (26 Oct) |
| Meteora (MET) | Season 2 claims closed 2026-10-21 | Only Referral Staking (USDC from DLMM fees, monthly cycles) is left. From Cycle 4, stakers need at least $10 of eligible DLMM fees in the cycle or forfeit it. | NO | T airdrops.io/meteora (28 Oct) |
| Katana (KAT) | Blast-wallet snapshot completed 2026-10-26 | Wallets active on Katana get a boost (formula unpublished). **An Abstract checkpoint is coming, time unconfirmed.** | NO | T airdrops.io/katana-network (27 Oct) |
| edgeX (EDGE) | Basic Mystery Boxes had to be opened before 2026-10-29 08:00 UTC | Token live since 31 Mar 2026 (so no longer a farm). Pro Boxes expected next week. | NO | T airdrops.io/edgex (28 Oct) |
| Mint Blockchain | withdraw deadline 2026-10-20 | Chain shut down 17 Apr 2026; funds had to leave by 20 Oct. | NO | T airdrops.io/mint |

Outside the window, but they explain what the trackers still show as "Claim live": Concrete (CT, TGE 30 Sep), Canopy (CNPY, listed TGE 7 Sep), Collector Crypt (CARDS, TGE 29 Aug 2025, quarterly rounds), River (RIVER, Season 6 claims open 5 Oct, deadline 31 Dec 2026).

**Not launched, despite rumour:** Polymarket (POLY: CMO confirmed a token on 24 Oct 2025; no date, no snapshot; airdrops.io 30 Sep), OpenSea (SEA: confirmed, TGE postponed 16 Mar 2026), Base (no token, closed its Guild in October), Robinhood Chain (no token), Tempo (no token), MetaMask (Season 2 "coming soon"), Circle Arc (ARC genesis mint of 10B done; Circle says no airdrop; any ARC claim site is a scam). Ink (INK): "no TGE date announced", but Nado now has an `ink_airdrop` API endpoint and a Merkle-proof Foundation Rewards contract, so a distribution looks near (T airdrops.io/ink, 7 Oct; airdrops.io/nado, 28 Aug).

---

## List 2. New farms, programmes and seasons started in the window

Window start 2026-10-15. "Funding" = what the user must put in (plus the project's raise where the tracker states it). KYC "not stated" means the tracker says nothing, not that none exists. App column is for the project by name.

### Worth a look (funded team, or free, or a clear reward pool)

| Name | Type | Chain | What the user does | KYC? | Funding (user / project) | Started | App? | Source |
|---|---|---|---|---|---|---|---|---|
| **HertzFlow Season 3** | Points ("Merits") for perps + vault | BNB Chain | Trade perps (closed trades only; 10 USDT minimum collateral per position); deposit USD1 in the Vault and hold 90 days for the WLFI bonus; swap in Spot Swap; refer. Merits convert to the airdrop at TGE; no ticker, no date. | not stated | USDT collateral + USD1 + BNB gas; project raise not stated | 19 Oct, ends **14 Dec** (S2 closed 19 Oct) | NO | T airdrops.io/hertzflow (21 Oct) |
| **Nullmask Season One** | Points for a privacy pool; MASK reward | Ethereum, Base, BNB Chain, Robinhood Chain (Solana "next"; payout to a Solana wallet) | Deposit ETH/BNB/SOL/USDT/USDC/USDG into the private balance, hold (1 point per day per $100), withdraw at least $100 (1 point per $10 withdrawn), refer for 10 %. | Not stated; deposits are compliance-screened and flagged wallets earn 0. No geo-block stated. | Your own deposit (private balance) | 19 Oct, 90 days to about 17 Jan 2027 | NO | The Block press release (sponsored, 19 Oct) ✓ points only; T airdrops.io/nullmask (23 Oct) for "100M MASK, 10 % of supply" |
| **Axis Robotics Season 2** | Points ("trajectories") on a token that already trades | Base | Sign in (email, Google, X or wallet), do robotics-data tasks, sign each trajectory on-chain; points settle in 2-week epochs; 60M AXIS (6 % of supply) pool. Conversion rate still being finalised. | not stated | none, a little ETH for gas | 23 Oct | NO | T coingabbar (23 Oct); airdrops.io/axis-robotics |
| **Monolith / swanUSD** | Stake-and-hold campaign, 100,000 SWAN pool split equally | Ethereum | Gate first: hold a partner position (veCRV, vlCVX, yCRV, sdCRV, vlSDT or staked INV) in the same wallet. Then deposit ETH/wstETH, mint swanUSD, stake to sSwanUSD, keep at least 1,000 sSwanUSD for 7 consecutive days inside the window. | not stated | ETH collateral for 1,000+ swanUSD, plus a partner-protocol stake you may not have | 22 Oct to **19 Nov** | NO | ✓ DexScreener (pair 22 Oct); T airdrops.io/monolith |
| **Metric** | Weekly points | BNB Chain, Ethereum, Robinhood Chain | Swap, provide liquidity, curate public pools, update Chainlink/Pyth oracles, refer. Weeks close Wednesdays 00:00 UTC. | not stated | real funds + gas | public app **15 Oct** | NO | T airdrops.io/metric (20 Oct) |
| **Titan Exchange** | Testnet points, waitlist | Canton | Join waitlist with a wallet signature, claim test USDC, enable trading, place a perp order (250 points for sign-up + first trade); weekly testnet points. No token announced. | not stated | **free** (test USDC) | listed 16 Oct | NO | T airdrops.io/titan-exchange |
| **Kalos V2** | Testnet points | Elysium testnet (chain ID 99801) | Claim free test HYPE, set a username, trade NFTs, mint on Drops, social posts, daily check-in, refer. 50,000 points a day pool. Token airdrop not confirmed. | not stated | **free** | V2 live Oct 2026 | NO | T airdrops.io/kalos (22 Oct) |
| **Elysium** (Kinetiq's Hyperliquid L2) | Testnet, speculative | Elysium testnet | Faucet test HYPE, bridge HyperEVM to Elysium, launch/buy on testnet launchpads. $1.75M seed (Maven 11). No token. Testnet live since 22 Sep. | not stated | **free** | testnet 22 Sep (page updated 20 Oct) | NO (the app has SEKAI, Push Chain, Ekiden for testnets) | T airdrops.io/elysium |
| **Jumper Exchange: infiniFi Chapter** | Seasonal quests; JUMP token expected Q4 2026 | multi-chain | Trade perps on Jumper Perps (weekly xPerps), swaps/bridges earn XP. Perps opened to everyone in Oct. | not stated | real funds | chapter 22 Oct to **21 Nov** | NO | T airdrops.io/jumper-exchange (26 Oct) |
| **Cambria incentivized testnet** | Testnet, post-TGE | Base | Planned for 30 Oct (the day after the RSGP TGE); no terms published. | not stated | ? | 30 Oct (planned) | NO | T airdrops.io/cambria (28 Oct) |
| **Optimum TurboCards** | Soulbound NFT mint, speculative (no token, no points announced) | Ethereum | Follow on X, join Discord, connect wallet, enter an access code to mint 1 of 999. $11M seed (1kx). | not stated | free, gas only | first code drop **23 Oct**, more over about a week | NO | T airdrops.io/optimum |
| **USD.AI Season 3** | Points on a live token (CHIP); Season 2 claims live | Arbitrum | Hold qualifying positions (7 % minimum-yield "CHIP Hurdle Rate" added, referral boosts dropped). Claim Season 2 CHIP before **31 Jan 2027**; Solana farmers had to link an EVM wallet by 25 Oct (passed). $13.4M raised. | not stated | real funds | S3 began **15 Oct** | NO | T airdrops.io/usd-ai (22 Oct) |
| **Phoenix (Ellipsis Labs): Frontier Traders Season 1** | Trading rewards; no token or points announced, airdrop unconfirmed | Solana | Register on Frontier, trade perps with USDC, $10,000 volume unlocks referrals. $44.3M raised. | **KYC required for Frontier rewards**; restricted-country residents cannot claim | USDC | running to **11 Nov** (start not stated; page updated 22 Oct) | NO | T airdrops.io/phoenix |
| **Arcus** (Season 1) | Points | Robinhood Chain | Spot stock tokens (boosted), perps with an invite code, 250k points a week; unavailable in US/CA/UK. | not stated | real funds | Season 1 began 1 Oct (outside the window; already in the app) | **YES** | T airdrops.io/arcus (12 Oct) |

### Smaller or weaker (all T)

| Name | Type | Chain | What the user does | KYC? | Funding | Started | App? | Source |
|---|---|---|---|---|---|---|---|---|
| PERPTools | Points (Season 2), perp DEX on Orderly | Orderly Network | Deposit USDC, trade perps/spot, refer. Airdrop "confirmed" in body, "unconfirmed" in badge; TGE targeted late Q4. $8M raised. | not stated | USDC | S2 2 Oct (outside window) | NO | airdrops.io/perptools (19 Oct) |
| TxFlow | Points, perp DEX | own L1 | $50 (community) or $500 (new-user campaign) minimum USDC deposit; trade weekly. Season 1 to Q1 2027 at latest. | not stated | $50-$500 | 12 Oct (outside window) | NO | airdrops.io/txflow (19 Oct) |
| Valdora | Points | ZIGChain | Deposit USDC in vaults, stake ZIG; strategic round led by ZigLabs. | not stated | USDC / ZIG | 13 Oct (outside window) | NO | airdrops.io/valdora |
| Papertrade | Loss-mints-token perp DEX; PAPER cannot be sold or transferred | HyperEVM | Min 10 USDC + 1 USDC activation; realized losses mint PAPER, stake for USDC fees. | not stated | 10 USDC+ (you lose it by design) | 10 Oct (outside window) | NO | airdrops.io/papertrade (20 Oct) |
| TermiX | Points + Kaito creator campaign | Base, BSC, Robinhood Chain | Register client/provider agents on agent.family, settle $1+ jobs; $1M seed (YZi Labs). KOL-post rewards paused 27 Oct; no third-party audit of its escrow proxy. | not stated | $0.01-0.05 gas; $1+ for jobs | Kaito Epoch 3 opened 24 Oct | NO | airdrops.io/termix (27 Oct) |
| AllScale | Points (AS Points) | BSC | Passkey wallet, deposit USDT/USDC, create invoices/claim links, daily login, refer. About $6.5M raised. | not stated | stablecoins | listed 22 Oct | NO | airdrops.io/allscale |
| SmartX | Waitlist leaderboard | Base, BSC, Ethereum, Robinhood Chain, Solana | Take trader test, verify email, post result card on X. $500K (YZi Labs EASY Residency S4). Round 2 live. | not stated | **free** | Round 2 live 23 Oct | NO | airdrops.io/smartx |
| XStable | Points (tracks "coming soon") | Solana (+Sui) | Deposit USDC/USDT/SOL, trade gold/silver/FX. Several $M from 10+ investors (Sep 2026). | not stated | small deposit | 13 Oct page | NO | airdrops.io/xstable |
| Soei | Social posting, $SOEI planned | none announced | Connect X, post about SOEI up to twice a day. No deposit. | human check only | **free** | marked New 28 Oct | NO | airdrops.io/soei |
| Nous Research | speculative (no token, no points) | Solana (Psyche) | Hermes Agent / Portal use; Series B $90M in Oct 2026 (about $160M total). Nothing to farm confirmed. | not stated | about $10 top-up | page 12 Oct | NO | airdrops.io/nous-research |

Funding news only: Hylo raised $1M led by Solana Ventures in October (app lists Hylo; Season 1 XP "still running as of October 2026", no end date, no token); Ritual published official tokenomics (50M RITUAL = 0.5 % airdrop to past Infernet/Frenrug/Discord users, bots removed; no mainnet date; no task left to do).

---

## List 3. Deadlines, snapshots and season ends: 30 Oct to mid-December

Times are UTC unless stated. "App?" = the app lists that project.

### Next 48 hours

| Date | Name | What happens | App? | Source |
|---|---|---|---|---|
| Fri 30 Oct, 09:00 | predict.fun | PREDICT claims open; allocation reveal; **security incident 27 Oct, ~400k USDT, hold off deposits**. After claims open you have one month to choose a claim method; unclaimed is forfeited. | NO | T airdrops.io/predict-fun (29 Oct) |
| Fri 30 Oct, 23:59 Paris | ACI | Season 1 of the Sepolia testnet airdrop ends (extended). No TGE date. | NO | T airdrops.io/aci (19 Oct) |
| Fri 30 Oct | Cambria | Incentivized testnet planned the day after TGE. | NO | T airdrops.io/cambria |
| any day | GenLayer | TGE undated. A pre-TGE AMA with the Foundation CEO ("a Friday, 13:30 UTC") was announced in an article dated Fri 23 Oct, so it may already have happened; not determinable from the source. | **YES** | T coingabbar (23 Oct) |
| Sat 31 Oct, 23:00 | The Hood | HOOD claim in @Hoodappbot closes. | NO | T airdrops.io/the-hood |
| Sat 31 Oct | BULK | SOL staking stops earning AURA points; afterwards AURA comes only from trading and referrals. TGE not announced; 30 % of supply goes to users. | NO | T airdrops.io/bulk (27 Oct) |

### November

| Date | Name | What happens | App? | Source |
|---|---|---|---|---|
| Mon 2 Nov | Reya | Waitlist users get a 100 RCP bonus by this date. Token confirmed, no TGE date; Reya v2 live since 28 Sep; Ethereum; $19M raised. | NO | T airdrops.io/reya-network (27 Oct) |
| Tue 3 Nov | Extended | Final Arc trading competition ends; the **final points distribution follows it** (weekly distributions already ended); EXT launch expected shortly after. | NO | ✓ docs (points page); T airdrops.io/extended for the date |
| Sun 8 Nov | Hibachi | Points programme ends. $HEAT ticker confirmed, no TGE date; hints of rewards afterwards. Arbitrum + Base, $5M seed (Dragonfly, Electric). | NO | T airdrops.io/hibachi (27 Oct) |
| Wed 11 Nov | Phoenix (Solana perps) | Frontier Traders Season 1 ends. KYC required for rewards. | NO | T airdrops.io/phoenix (22 Oct) |
| Thu 12 Nov | Pharos | Season of AI developer programme ends (5,000 PROS). | NO | T airdrops.io/pharos |
| November, day not stated | Perpl | Extended mPoints programme ends in November; MON paid within a week after (base pool $500k or $900k guaranteed: page contradicts itself). Monad, $9.25M (Dragonfly). | NO | T airdrops.io/perpl (22 Oct) |
| about Fri 13 Nov (my arithmetic) | Monolith | Last day to *start* holding 1,000+ sSwanUSD if you want 7 consecutive days before the window closes. | NO | T airdrops.io/monolith |
| Thu 19 Nov | Monolith | 28-day qualification window ends. | NO | T airdrops.io/monolith |
| Fri 20 Nov (last full day) | Fables | Claim closes **21 Nov 00:00 UTC**. | NO | T airdrops.io/fables (21 Oct) |
| Sat 21 Nov | Jumper | infiniFi Chapter ends. JUMP is "expected Q4 2026", no date. | NO | T airdrops.io/jumper-exchange |
| Mon 23 Nov | TermiX | Kaito Epoch 3 winners due. | NO | T airdrops.io/termix |
| Wed 25 Nov | Treehouse (TREE) | Season 2 claim window closes (opened 29 Apr; snapshot 25 Apr; claims at gaiafoundation.xyz; the docs page does not say who is eligible or what happens to the rest). | NO | ✓ docs.treehouse.finance/protocol/tree-token/airdrop-details-s2/key-information |
| Fri 27 Nov | predict.fun | Weekly batch payouts for late-submitted claim forms end. | NO | T airdrops.io/predict-fun |
| about Mon 30 Nov | predict.fun | One month from claims opening: pick a claim method or forfeit (airdrops.io: "one month from the opening of claims"). | NO | T |

### Q4 with no date, and early December

| Date | Name | What happens | App? | Source |
|---|---|---|---|---|
| "Q4 2026", no day | **Variational** (VAR) | TGE scheduled Q4 2026 (page contradicts itself: FAQ says no date). Weekly points 150,000 until TGE. Terms require a signed ToS; Omni not for US/Canada; access code needed; referral payouts of $4,000+ need KYC. Their docs say the trading API is not available. | **YES** (chip TGE Q4 2026) | T airdrops.io/variational (5 Oct); app's own why_not_run |
| "Q4 2026", no day | **Decibel** (Aptos) | TGE expected Q4 2026; "no private round, no VC allocation". | **YES** | T airdrops.io/decibel (16 Oct) |
| "Q4 2026", no day | Jumper (JUMP) | See above. | NO | T |
| not announced, signals of imminence | **Ink (INK) / Nado** | Nado's API exposes `ink_airdrop` and a Merkle-proof rewards contract; Ink teased an "Ink weather update". Eligibility not published; airdrops.io lists KYC as required. | **YES** (both) | T airdrops.io/ink (7 Oct), airdrops.io/nado (28 Aug) |
| soon, time unconfirmed | Katana | Abstract checkpoint. | NO | T airdrops.io/katana-network |
| Tue 8 Dec | **Saturn** (STRN) | Season 2 ends (closes shortly before TGE if earlier); TGE Q4 2026 unspecified. Per the 24 Oct research it geo-blocks the US and EEA; the app notes direct minting needs KYC. | **YES** (chip TOKEN CONFIRMED) | T airdrops.io/saturn-credit (25 Sep); 24 Oct README |
| Mon 14 Dec | HertzFlow | Season 3 ends; only USD1 Vault deposits made inside the window count for the WLFI bonus. | NO | T airdrops.io/hertzflow |
| Tue 15 Dec | Abstract | Chain shuts down (24 Oct README; the Cambria and Katana moves fit). | NO | 24 Oct README |
| Thu 31 Dec | River | Season 6 point claims forfeited after this date. | NO | T airdrops.io/river |
| 17 Jan / 21 Jan 2027 | Nullmask / Axis | Season One ends about 17 Jan; unclaimed AXIS expires 21 Jan 12:00 UTC. | NO | as above |

---

## Method and limits

- 16 of the 35 WebSearch calls were used. Generic sweeps ("TGE November 2026", "snapshot November 2026", "points programme launched October 2026", "HODLer Airdrops October 2026", "airdrops this week") returned nothing from the window; project-name searches worked. News outlets (The Block, CoinDesk, Decrypt, Blockworks) returned no article from 15-29 Oct for any of the above.
- Dead or empty sources: DropsTab (404), CryptoRank (403), DefiLlama airdrops page (403) and `/raises` (402), CoinMarketCap airdrop page (empty), Binance announcements (empty), docs.predict.fun (DNS failure), airdropalert.com home (no list). Everything marked T therefore leans on airdrops.io, which lags and contradicted itself again (GenLayer "Claim live", Canopy "Ongoing" and "(Ended)", Variational TGE date).
- DefiLlama (`api.llama.fi/protocols`) and CoinGecko (`/coins/list`, `/simple/price`) were read directly with curl. A CoinGecko coin id with no price is a placeholder, not a launch (Variational, GenLayer, Jumper, OpenSea, Polymarket, Curvance, Avant, Strata, Cambria before TGE, predict-fun). `vena-protocol` ($9.8k mcap) and `the-hood` ($6k mcap) are probably not the projects in question and were not used.
- One older oddity, not a window event: DefiLlama shows a live PLUME token on "Plume Mainnet" (CoinGecko `plume`), while the app lists "Plume Vaults" as POINTS LIVE. The vault points are a separate programme, but the chain's token is not "no token yet".
- DexScreener was read for Cambria RSGP (Base) and swanUSD (Ethereum). Do not confuse Monolith's SWAN with `swan-chain`, which is a different project.
- The Nullmask airdrop is airdrops.io's claim; the Block press release (sponsored) mentions only points, and one DropsTab page says no airdrop is officially announced. MASK already trades (CoinGecko `nullmask`, $0.0317, mcap $18.6M, 24h volume $720k), so it fails the app's own "no token live yet" gate.
- Not checked (time): airdrops.io project sitemaps 1-4 (800 URLs, 163 with a lastmod from 15 Oct) were scanned by slug and about 55 pages read; sitemaps 5-19 (older entries) were not. A site-wide refresh on 26 Oct touched many pages, so lastmod is not "new".
