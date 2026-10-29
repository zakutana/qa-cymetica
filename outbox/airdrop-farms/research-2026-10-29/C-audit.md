# Airdrop Farmer audit: the 45 farms listed on 2026-10-29

Input: `cym-farms.json` / `cym-raw.json` (generated 2026-10-29T13:56Z; Cymetica's own checks stamped 28-29 Oct). Auditor: Sonnet 5.5, 2026-10-29.

## Result in four lines

* **24 keep with the chip right** (13 solid evidence, 11 thin). **6 keep but the chip is wrong, stale or understated** (GenLayer stale; Cian, Firelight, Ekiden unproven; YieldFi, NUVA understated). **15 drop.** (24 + 6 + 15 = 45.)
* Drops: 1 token already live (Plume Vaults); 7 where the page Cymetica cites shows the programme ended or is not a points programme (Valantis, Avant, Dano, Estate, R25, Byreal, Mellow); 1 token already issued behind a KYC wall (Noon); 6 where nothing current backs the chip (Curvance, Yuzu, NodeDAO, SEKAI, Zoo, SyncSwap).
* **Heat is not community talk.** `mentions_7d` is 0 for all 45; heat is TVL size plus 7-day TVL change. Of the 5 highest heats, 3 are drops (Valantis, R25, Plume). The community-hot farms sit low (Variational 0, GenLayer 0).
* No farm launched a spot token in the last 14 days. GenLayer started pre-market trading on 27 Oct (not spot). Four look-alike tokens appeared on DEXes (listed at the end).

## Legend

* **Token live?** Searched CoinGecko (full coin list, local match), DexScreener (name + symbol search, token address), DefiLlama `/protocols` (symbol), then the project's own docs. A name hit counts only if the site/handle/contract matches; collisions are named.
* **Talked about now:** hot = on airdrops.io "Hot" list and/or in 2+ October roundups (airdrops.io best-airdrops 21 Sep/12 Oct, Coinlaunch 20 Oct, Bitrue 13 Oct); some = real news in the last 30 days or an active tracker listing; obscure = at most one relevant item. I counted Google News RSS (`when:30d`) myself because Cymetica's matcher reports 0 for everyone.
* **Evidence grade:** **solid** = dated first-party or tracker page from the last 3 months that agrees with another source; **thin** = one source, undated, or only the page Cymetica cites; **absence** = I could not find a programme (not proof there is none; each states what I opened).
* AIO = airdrops.io/<slug>/ (date = the page's own "updated"), CG = CoinGecko, DS = DexScreener, DL = DefiLlama, G/C/F/A/E = our 24 Oct research files in `outbox/airdrop-farms/research/`.

## Table (ordered by Cymetica heat)

| # | Farm (chip, heat) | Token live? | Programme running? | Talked about now? | KYC? | Chip right? | Verdict | Sources |
|---|---|---|---|---|---|---|---|---|
| 1 | Upshift (POINTS LIVE, 48) | No. DL symbol "-", CG none, DS shows only the upUSDC receipt | Yes. Season 2 ongoing, no end date, Season 1 rewards paid at end of S2. [points](https://app.upshift.finance/points). Cymetica's agent really deposits here | obscure (no roundup, 0 relevant news; only TVL +21 % in 7 d) | No KYC; US residents excluded (Cymetica attestation) | right | **keep** (solid) | AIO upshift (18 Jul); DL; DS; C-evm |
| 2 | Valantis (POINTS LIVE, 42) | No | **No.** The page Cymetica read says "As of June 4th, 2026, all 260M Weekly Points have been distributed"; AIO says "This airdrop has ended". [page](https://docs.valantis.xyz/valantis-points.md) | obscure (0 news) | n/a | **wrong** | **drop: programme ended 4 Jun 2026** (heat 42 = 2nd highest) | docs.valantis.xyz; AIO valantis (18 Jul); E |
| 3 | OnRe (POINTS LIVE, 34) | No. ONyc is the receipt (CG onyc, rank 242) | Yes per AIO: daily points 1x-4x, no end date; no 2026 confirmation in docs. [docs](https://docs.onre.finance/onyc-in-defi/onre-points-program.md) | obscure | **Contested:** AIO says KYC at account setup; Cymetica's route note says minting is open to anyone | right | **keep** (thin-solid), say KYC is unresolved | AIO onre (18 Jul); CG; E |
| 4 | R25 (POINTS LIVE, 34) | No | **No evidence.** What Cymetica read is the string "24 Guard Points" (a security feature). Site and docs show only rcUSD / rcUSDp yield products; search found no points or airdrop | obscure (0 relevant news) | unknown (RWA) | **wrong (false positive)** | **drop: no rewards programme** (absence: read r25.xyz, the Sui launch post and DL's R25 pages, one search; docs.r25.xyz returned only its title, so it is unread) | r25.xyz; sui.io blog; DL RWA page |
| 5 | Plume Vaults (POINTS LIVE, 33) | **YES.** PLUME $0.0159, rank 269, mcap $108 M (CG plume); DS Ethereum pair since Feb 2025 on plumenetwork.xyz, Solana pair created 12 Oct (liq $21.6 M) | No. Plume Points Season 2 earning closed 31 Mar 2026; Season 2 claim closed 3 Sep; Nest vaults have no active points | some (Fidelity nBND vault, 5 Oct) | wallet screening, US persons excluded, World ID | **wrong** | **drop: token live (PLUME)** | AIO plume-network (26 Oct); CG; DS |
| 6 | Bitfi (POINTS LIVE, 31) | No (bfBTC/bfUSD receipts; DS "BITFI" hits are other coins) | Probably. Docs: points programme live; bfBTC quests ended 31 Dec 2025, bfUSD continues. I could not read the app's points page | obscure (0 news) | none found | plausible | **keep** (thin) | C-evm; bitfi.one footer link |
| 7 | Cian Protocol (TOKEN CONFIRMED, 31) | No (CG "CIAN" hits are Binancians etc.) | Docs: "Voyage points will be converted into CIAN tokens", no dates, no 2026 post found. [page](https://docs.cian.app/point-system/cian-voyage-points.md) | obscure (news search all sports; 0 relevant) | none found | **weak:** a conversion promise, not a dated token; DL lists 0 audits | **keep** (thin); relabel POINTS LIVE | docs.cian.app; thegrid.id profile; DL |
| 8 | Mellow Protocol (POINTS LIVE, 31) **agent deposits real USDC** | No (CG "mellow" = Mellow Man memecoin) | **Doubtful, with a control.** Cited page is headed "Legacy architecture ... earlier generation". The same fetcher that shows "Mellow points" on Lido's stRATEGY page (closed to deposits) and EarnETH page shows **no points of any kind** on the EarnUSD deposit page ([page](https://stake.lido.fi/earn/usd/deposit)), which is the vault our agent uses; it also excludes US persons. Not proven absent (the app's Rewards tab is JavaScript) | obscure | no KYC; US persons excluded | **wrong / unproven** | **drop (priority, route is live)**. Relabel SPECULATIVE until a points page for EarnUSD exists | stake.lido.fi/earn/usd + /strategy; docs.mellow.finance; C-evm |
| 9 | Symbiotic (POINTS LIVE, 30) | No. Look-alike "SYBT / Symbiotic" on Base (FDV $775 M, liq $147 k, created 21 Sep, no site) is not theirs | Yes. Docs have a Points Program page; DropsTab point farming active since 11 Jun 2024, no end. AIO page is stale (Apr 2025) | obscure (0 relevant news) | No | right | **keep** (solid) | docs.symbiotic.fi; G; DS |
| 10 | Theo (POINTS LIVE, 29) | No. thUSD/thBILL are receipts; THQ = Theoriq, unrelated | Yes. thUSD Points Program (post dated 25 Jun, header 6 Oct); AIO 30 Sep, three vaults open | obscure | **Yes for minting:** wallet whitelisted via sales contact, KYC article (Cymetica's own route note) | right | **keep**, flag KYC | AIO theo-network (30 Sep); theo.xyz |
| 11 | Curvance (POINTS LIVE, 29) | No. CG `curvance` has no price | **Unproven.** Cited page sits under `old-dev-doc-pages`, no dates; current docs/blog/homepage show no points (24 Oct reading); AIO is Feb 2025 | obscure | No | **unproven** | **drop (absence)**. Reopen if the app's Rewards tab shows a season | docs.curvance.com; blog; C-evm |
| 12 | Arcus (POINTS LIVE, 29) | No. CG `arcus-network` is a namesake (Arc chain, arcusnetwork.io); pTokens are products | Yes. Season 1 since 1 Oct, 250 k points/week, Wednesdays 3pm ET, to end H1 2027 | **hot** (airdrops.io Hot #5, best-airdrops #3; $5 B volume, Robinhood Wallet news) | No KYC; not available US/UK/CA; perps need invite code | right | **keep** | AIO arcus (12 Oct); NEWS |
| 13 | Rysk Finance (POINTS LIVE, 28) | No | Likely. 1 M points/week since Aug-Sep 2025, ~24 M by 30 May 2026 (CoinLaunch); no token plan announced; no first-party page opened | obscure | none found | plausible | **keep** (thin) | coinlaunch.space/rysk; app nav |
| 14 | Saturn (TOKEN CONFIRMED, 27) | No. STRN TGE planned Q4 2026 (foundation, 25 Sep). A "STRN / Saturn Fnd" pair on Base created 28 Oct (liq $122 k, FDV $123 k, no site) is a look-alike | Yes. Season 2 Orbital Points, Aug to 8 Dec 2026, up to 5 % of supply | some (allocation checker, KuCoin flash) | **Yes:** direct mint needs KYC + approved wallet (Cymetica's route note); US/EEA/OFAC geo-blocked | right | **keep**, flag KYC + geo | AIO saturn-credit (25 Sep); KuCoin 25 Sep; C-evm |
| 15 | Avant Protocol (TOKEN CONFIRMED, 27) | No. AVANT claim "not live", TGE "To be announced" (slipped past the mid-Sep target) | **No.** Season 1 "Completed", point accrual ended 15 May 2026, no Season 2 anywhere. [page](https://docs.avantprotocol.com/avant-season-1-airdrop.md) | obscure | "compliance checks" at claim | chip true but nothing left to farm | **drop: no running programme** | docs.avantprotocol.com; Bitrue 13 May / 31 Aug |
| 16 | Yuzu Money (POINTS LIVE, 27) | No (yzUSD etc. are products) | **Unproven.** App has a "Points" page I could not read; docs are password-protected | obscure | KYC/KYB reported by third parties (Cymetica's own route note) | unproven | **drop (absence + KYC)** | app.yuzu.money; C-evm |
| 17 | Noon (TOKEN CONFIRMED, 27) | Token **already issued**: NOON minted 30 Jun 2025, distributed monthly to points holders; DS 0 pairs for the address, CG none; AIO says "trading on Uniswap" (unconfirmed) | Seasons + monthly NOON pool ([rewards](https://docs.noon.capital/4.-usdnoon/rewards.md)); AIO: public-beta points ended | obscure | **Yes:** whitelisted parties, USD 1 M minimum (Cymetica's own route note) | **wrong** (not a future token) | **drop: KYC wall, token already distributing** | docs.noon.capital; DS; AIO noon (16 Oct) |
| 18 | Firelight (POINTS LIVE, 26) | No | **Unproven.** FAQ asks "What can be done with Firelight Points?" and never answers; early-contribution FXRP rewards via Merkl exist | some (launch, 50 M XRP, XAO DAO deploy 23 Oct) | none found; but it screens wallets against OFAC/blacklists | unproven | **keep** (thin), with a flag: not an exploit (gate 5 holds). On 9 Oct Firelight reversed a compliance blacklist that had unstaked funds and blocked wallets (117,500 FXRP, dozens of addresses, compensation pledged; single CMC AI summary). CryptoSlate also reports a lock-up and a growing withdrawal queue (undated) | firelight.finance; CMC top-stories 10 Oct; CryptoSlate; NEWS |
| 19 | Nado (POINTS → INK, 26) | No. INK not launched (CG `ink-4` is cPen's unrelated INK; a "NADO" pair on Base created 28 Oct is a look-alike) | Yes. Season 2 since 21 May; $100 k/week USDT0 pool; points convert to INK at the Ink TGE | **hot** (airdrops.io Hot #14, Coinlaunch 20 Oct) | No (restricted persons excluded) | right | **keep** | AIO nado (28 Aug); docs.nado.xyz |
| 20 | Exponent (POINTS LIVE, 25) | No (XPN in development) | Points exist (API docs "User points"); the $200 k v2 campaign (30 days from late May) is over | obscure | No | right | **keep** (thin) | AIO exponent (18 Jul); docs |
| 21 | Hylo (POINTS LIVE, 24) | No (hyUSD / xSOL are receipts) | Yes. Season 1 XP since 5 Dec 2025, no end date | some ($1 M round led by Solana Ventures, 20-24 Oct) | No | right | **keep** (solid) | AIO hylo (26 Oct); NEWS |
| 22 | Decibel (TGE Q4 2026, 24) | No | Yes. Amps Season 1 live on mainnet; Tria Grand Prix 16 Oct to 16 Jan | some (USDCBL stablecoin, encrypted mempool) | No | right (date is "expected"; docs say Amps feed the TGE) | **keep** | AIO decibel (16 Oct); NEWS |
| 23 | Pacifica (POINTS LIVE, 24) | No | Yes. Season 1 weekly snapshots Thursday 00:00 UTC since Sep 2025, no end | some (Coinlaunch 20 Oct, best-airdrops "recheck pending") | No; invite codes | right | **keep** | AIO pacifica (23 Jul); A |
| 24 | Neutral Trade (POINTS LIVE, 24) | No (the TMX airdrop in Oct news is TermMax's, a different token) | Yes per AIO (NT points, undated) | obscure | No | right | **keep** (thin) | AIO neutral-trade (24 Jul); NEWS |
| 25 | NodeDAO (POINTS LIVE, 23) | No | **Dormant.** The only points mention is a one-line "NodePoints + EigenLayer Points"; newest dated item on the site is 18 Aug 2023 | obscure | No | **wrong** | **drop: dormant** | nodedao.com; G |
| 26 | Estate Protocol (POINTS LIVE, 23) | No | **No.** Cited page is the Elite Investor NFT programme, paid in USDC, capped at $100 k/month; no points, airdrop or TGE | obscure | unknown | **wrong** | **drop: not a points programme** | [page](https://docs.estateprotocol.com/whitepaper/elite-investor-rewards-program.md) |
| 27 | Ink network (POINTS → INK, 22) | No. TGE not happened; the Jul-Sep window passed (AIO 12 Oct) | Yes via Kraken, Nado, Tydro; no Ink-owned programme page | **hot** (airdrops.io Hot #7) | INK goes through Kraken Drops = KYC'd Kraken clients | right | **keep as watch** (a chain, no deposit route) | AIO ink-chain (7-12 Oct); theblock.co |
| 28 | StackingDAO (POINTS LIVE, 22) | No (CG: only stSTX receipts) | Active per AIO, undated; app has a Points tab | obscure | No | right | **keep** (thin) | AIO stackingdao (24 Jul) |
| 29 | Vena Finance (TOKEN CONFIRMED, 22) | No. CG `vena-protocol` is an unrelated project (venaprotocol.com, @VenaHub) | Docs: points convert to $VENA at TGE, biweekly, undated | obscure | none found | plausible | **keep** (thin); DL lists 0 audits, TVL $9.2 M, listed May 2026 | docs.vena.finance; DS; DL |
| 30 | Byreal (POINTS LIVE, 21) | No | **No.** Byreal's site and docs show no points; the cited page is an AI-agent skill that farms xStocks' partner points | obscure | n/a | **wrong** (subject is xStocks) | **drop** | [page](https://docs.byreal.io/byreal-agent-stack/what-is-byreal-ai-agent/xstocks-points-farming.md); byreal.io |
| 31 | YieldFi (POINTS LIVE, 21) | No | Yes. YieldCrumbs/YieldFi Points; AIO "Confirmed", tokens at TGE | obscure | No | understated (should be TOKEN CONFIRMED) | **keep** | AIO yieldfi (30 Sep) |
| 32 | Antarctic (TOKEN CONFIRMED, 20) | No (ATTX announced Sep 2025; CG none) | Yes per AIO (daily settlement 08:00 UTC, upd 18 Jul); docs: "AX Points are not a token" | obscure | none found | roughly right | **keep** (thin) | AIO antarctic; chainwire 19 Sep 2025 |
| 33 | StableHodl (POINTS LIVE, 20) | No | Unproven: docs say points "might be one criterion" for airdrops, no dates | obscure | No | unproven | **keep** (thin); TVL $6.4 M is at the $5 M line | docs.stablehodl.com |
| 34 | SyncSwap (TOKEN CONFIRMED, 19) | No | **Unproven.** Loyalty page is undated, ySYNC is historic; SYNC "planned", no official airdrop (Bankless: unconfirmed) | obscure | No | **wrong** (not confirmed) | **drop (absence)** | docs.syncswap.xyz; bankless.com/airdrops/syncswap |
| 35 | Zoo Finance (POINTS LIVE, 18) | No | **Unproven.** Cited page is yield-token docs ("YT Points" for bribe vaults), not an airdrop programme; TVL -9 % | obscure | No | unproven | **drop (absence)** | doc.zoofi.io; zoofi.io |
| 36 | Dano Finance (TOKEN CONFIRMED, 17) | DANO already issued as the reward (policy ID in docs); no CG/DS market | **No.** Cited campaign ran 24 May to 31 Dec 2025 | obscure | n/a | **wrong** | **drop: programme ended 10 months ago** | [page](https://docs.dano.finance/news/fixed-pool-lending-early-adopter-rewards-program.md) |
| 37 | Steer Protocol (POINTS LIVE, 14) | No | Unproven: docs nav says "Points Program Active", terms in a PDF; site footer © 2025; TVL -12 % | obscure | No | unproven | **keep** (thin) | docs.steer.finance; steer.finance |
| 38 | NUVA (POINTS LIVE, 14) | No (nvPRIME etc. are products) | Yes: first-party "NUVA Points accrue in parallel"; AirdropAlert 15 Oct: airdrop confirmed | some (Animoca / Franklin Templeton, 8-9 Oct) | AML screening and geo-block, not identity-gated | understated | **keep** | nuva.finance; C-evm |
| 39 | Endur (POINTS LIVE, 12) | No (xSTRK etc. are receipts) | Season 2 is "~6 months, 7.5 M points", no calendar dates; may already be over | obscure | No | unproven | **keep** (thin); TVL -14 % | [docs](https://docs.endur.fi/docs/community/endur-season-2.md) |
| 40 | Strata (POINTS LIVE, 8) | No. CG placeholder; "STRATA" pairs on Base and Robinhood created 29 Oct (liq $9 k) are look-alikes | Yes: Season 1 points (AIO 18 Jul). **TVL -43 % in 7 d**; jrUSDe depegged in Oct per Aave governance post | obscure | No | right | **keep with a warning** | AIO strata; Aave ARFC thread; DL |
| 41 | Variational (TGE Q4 2026, **0**) | No. CG `variational` no price; Base look-alike (liq $31 k) | Yes. Weekly points to end of Q4, 150 k/week; VAR TGE Q4 2026 per own docs; 32 % genesis airdrop | **hot** (airdrops.io Hot #13, best-airdrops #2, Coinlaunch) | US/Canada excluded; access code; KYC only for referral payouts >= $4,000; **ToS bans unauthorised bots** | right | **keep; heat is wrong** | docs.variational.io; AIO (5 Oct); A |
| 42 | GenLayer (TESTNET, **0**) | Not spot. **GEN pre-market on Aspecta Futures since 27 Oct** ($1.49, FDV $152 M); Base look-alike GEN (liq $156 k) | Season 1 snapshot 25 Oct; **registration closed 26 Oct**; Season 2 began 26 Oct, points carry over, "does not guarantee" an allocation | **hot** (airdrops.io ticker, 6 news items in 7 d) | none stated | **wrong / stale** | **wrong chip: keep as a watch, relabel "TGE near, registration closed"**. A new wallet cannot join the Season 1 drop | AIO genlayer (26 Oct); coingabbar; bitrue |
| 43 | Push Chain (TESTNET, 0) | PC not live. Legacy PUSH (same org, push.org) trades at $0.001, mcap $97 k | Yes. Season 3 on Donut testnet; $PC airdrop confirmed in tokenomics (guides: 10 % of 10 B), no date | some | No | right | **keep** | AIO push-chain; CG; usethebitcoin |
| 44 | Ekiden (TESTNET, 0) | No | XP programme page exists; one tracker says mainnet launch confirmed 10 Sep 2026 (single source) | obscure | No | possibly stale | **keep** (thin) | docs.ekiden.fi; coinstats listing |
| 45 | SEKAI (TESTNET, 0) | No | **No programme.** Cymetica's own route note: the devnet publishes no points programme | obscure | No | **wrong** | **drop** | testnet.sekai.fi; F |

## Farms to drop (15)

| Why | Farms |
|---|---|
| Token already live | Plume Vaults |
| Cited page shows programme ended or not a points programme | Valantis (ended 4 Jun), Avant (accrual ended 15 May), Dano (ended 31 Dec 2025), Estate (USDC NFT rewards), Mellow (legacy page; EarnUSD shows no points), Byreal (xStocks' points), R25 ("Guard Points") |
| Token already distributing, behind KYC | Noon |
| Nothing current backs the chip (absence, reopen if Cymetica shows a page) | Curvance, Yuzu Money, NodeDAO, SEKAI, Zoo Finance, SyncSwap |

Priority: **Mellow**. It is one of only two farms where Cymetica's agent actually moves USDC (the other is Upshift).

Wrong chip on farms worth keeping: GenLayer (registration closed, pre-market live); Cian (TOKEN CONFIRMED has no date); Firelight (POINTS LIVE unproven); YieldFi and NUVA (airdrop confirmed, chip says only POINTS LIVE); Ekiden (mainnet maybe launched).

## Heat that looks wrong

Heat = talk + money + momentum, and **talk is 0 for all 45** (`mentions_7d` 0 everywhere, while Hylo, Decibel, GenLayer, NUVA, Endur all had news in the last 7 days). What is left is TVL size and 7-day TVL change.

Too high for what is there:
* Valantis 42 (programme ended), R25 34 (no programme), Plume Vaults 33 (token live), Mellow 31 (legacy), Cian 31, Bitfi 31 (nobody discusses them), Curvance 29, Avant 27, Yuzu 27, Noon 27.
* Upshift 48 is first only because TVL rose 21 % in a week; no roundup lists it.

Too low for what is hot:
* Variational 0: DefiLlama has no TVL for it (open interest is $941 M), so money and momentum show "-". It is #13 on airdrops.io Hot and #2 in their best-airdrops list.
* GenLayer 0: testnets have no money or momentum by construction; it is the news of the week (registration closed, pre-market).
* Arcus 29 (rank 11), Nado 26 (19), Pacifica 24 (23), Ink 22 (27) are the other community-hot farms, mid-table.

Ranking vs community: it does not match. Of the farms the trackers push this month (Variational, Arcus, Nado, Pacifica, GenLayer, Ink) none is in the top 10 and two are at the bottom.

## Look-alike tokens seen on DexScreener (not the projects')

STRN "Saturn Fnd" (Base, 28 Oct, liq $122 k) · NADO (Base, 28 Oct, liq $77 k) · GEN (Base, 21 Oct, liq $156 k, FDV $157 k vs pre-market $152 M) · STRATA (Base + Robinhood, 29 Oct) · SYBT "Symbiotic" (Base, 21 Sep, FDV $775 M) · VARIATIONA (Base, 21 Jun). None carries the project's site or handle. Worth a warning on the page next to any farm whose TGE is near.

## Method and limits

* WebSearch used: 20 of 30. Everything else: CoinGecko API (full coin list + markets), DexScreener API, DefiLlama `/protocols` + `/hacks`, Google News RSS, airdrops.io pages, project docs.
* DefiLlama `/hacks` (1,328 entries, newest 28 Oct): no entry for any of the 45 (name and id match).
* CoinGecko throttled single-coin lookups after about 10 calls; a few detail checks were skipped (cited where it matters).
* airdrops.io lags (its own dates are often 18 Jul or 24 Jul, bulk stamps). A "keep (thin)" row rests on that or on Cymetica's own cited page.
* Not opened: the apps' own Rewards screens (JavaScript), X/Twitter, Discord, Cymetica's PDFs. Absence rows say what was opened.
* Firelight incident rests on one CMC AI summary; the CryptoSlate lock-up article's date was not read.
* Web content treated as data. No page tried to instruct me.
