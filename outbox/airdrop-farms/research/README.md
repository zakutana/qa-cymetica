# Airdrop farms research, 2026-10-24

Every place a user can farm an airdrop today, set against Cymetica's live list
(`GET /api/v1/airdrop-farm/farms`, 49 farms, generated 2026-10-24T07:38Z).
Seven researchers, one segment each; their tables with sources are A-G below.
Marks: **✓** = I read the project's own page or a primary market source myself;
**T** = tracker or third-party only (airdrops.io, DropsTab), not re-checked.

## 1. Their list, checked

**Token already live**, against their own gate line 1 "No token live yet":

| Farm | Token | Evidence |
|---|---|---|
| Fables | FABLES | ✓ DexScreener: Robinhood Chain pair since 2026-10-20, $631k liquidity, $255k 24h volume; points ended 2026-10-19 (A, C, D, G) |
| Zircuit Staking | ZRC | ✓ DexScreener: Ethereum pools since 2024 (24h volume 0 today); G: trading since 2024-09-28 |
| Travala.com | AVA | ✓ CoinGecko `concierge-io`, rank 691 |
| Sonic SVM | SONIC | ✓ CoinGecko `sonic-svm`, rank 1330 |
| INFINIT | IN | ✓ CoinGecko `infinit`, rank 950 |
| Rivalz Network, Dill, Joltify | RIZ, DL, JOLT | T (F) |
| Noon | NOON | T, medium: token minted 2025-06-30, no priced market found (G) |

**Dead or not an airdrop** (F, T): Stroom, Avitus, Yuzu, Fewcha, Zoom Manor,
ODX (site refuses connections), Nebula Lending, Spindle Finance (domain for
sale); Coincamps pays USDT. Only 9 of the 22 free farms have a campaign that
started in 2026.

**Chips and heat come from headlines matched by name.** Read in each farm's
`evidence` array (✓):

- Axis **TOKEN CONFIRMED**: "Axis Robotics price today, AXIS to USD" (a
  different project, CoinMarketCap/CryptoSlate). Axis's own points
  ("Coordinates") are real; no token is confirmed.
- Ink network **TOKEN CONFIRMED**: "Fire Country Musical Guest INK…" (TV).
- Tempo network **POINTS LIVE**: "Tempo Guard Kiki Rice Named to 2026 WNBA
  All-Rookie Team - Toronto Tempo".
- Fables **POINTS LIVE**: "Royal Fables Season 16 - The Heirloom Series".
- The same matches fill `news.n7`/`n30`, which feed heat.

**Chains** (Robinhood Chain, Arc, Ink, Tempo) are in the list although gate
line 4 says "not an exchange, bridge, chain".

## 2. Missing, filtered

Kept only rows with a recent source and that pass our spec's gate (no exploit,
usable from one wallet). Size is DefiLlama TVL unless noted.

**Trading venues** (their gate drops exchanges; our spec item 8 includes them):

| Project | Why it is a farm | Size | Mark |
|---|---|---|---|
| Variational | $VAR "will be launched in Q4 2026", 32% airdropped by points; weekly points until end of Q4 2026 | OI $941M | ✓ docs |
| Extended | points 98% issued; final Arc competition to ~2026-11-03 | $114M | T |
| Nado (Ink) | Season 2, points convert to INK | $51M | T |
| Arcus (Robinhood Chain) | token confirmed by dYdX Labs, 250k points a week | $64M | T |
| Pacifica | points live, API trading allowed | OI $64M | T |
| RISEx, Decibel, Hibachi, TxFlow | points live, no token | $21-36M | T |

**Prediction markets:** Polymarket, POLY confirmed by its CMO 2025-10-24
("There will be a token, there will be an airdrop"), no date, no points, rewards
in USDC; $374M (✓ Blockworks). Predict.fun, $11.6M, weekly points (T).

**Deposit farms:**

| Project | Why | TVL | Mark |
|---|---|---|---|
| Upshift | Season 2 points, token unconfirmed | $395M | T |
| Theo thUSD | thUSD Points Program (Liquid, Core, Boost) | $132M | ✓ theo.xyz article (Jul 2026; still running unverified) |
| Tydro (Ink, Aave) | "Points" on Ink's own app list; counts toward INK | $130M | ✓ inkonchain.com |
| Saturn | STRN confirmed, Season 2 to 2026-12-08; **geo-blocks US and EEA** | $155M | T |
| OnRe, Exponent, Hylo, Felix, Strata, 3Jane, NUVA | points live, no token | $7-295M | T (OnRe, Hyperbeat, Project 0 low) |

**Free farms with funded teams:** GenLayer ($7.5M; **registration closes
2026-10-26**), Rialo ($20M), Ritual ($25M), Push Chain, Orbinum, Ekiden,
Elysium (all T, F).

**Consumer:** Jumper/LI.FI (JUMP expected Q4 2026), OpenSea (SEA confirmed,
TGE postponed 2026-03-16) (T, B).

**Left out on purpose:** Ostium (exploit 2026-07-15, $23.75M), Makina (exploit
2026-01-20), Loopscale (merged into Orca), Abstract (shuts down 2026-12-15),
tokens already live (MegaETH, Lighter, edgeX, Backpack, Paradex, GRVT, Aster,
Katana, Monad, Plasma, Berachain…). Variational's terms ban unauthorised bots:
an agent there needs their consent first.

## 3. Scale

DefiLlama lists 279 tokenless protocols over $5M (excluding CEX, chains,
bridges); many are not farms (37 risk curators, exchange staking). Researchers
found about 16 EVM deposit farms with live points, 34 trading venues, 24
non-EVM farms, 29 consumer programmes, 12 chains and 25 funded free farms. All
but a handful are absent from the 49.

## Method and limits

Seven Sonnet researchers on 2026-10-24, each writing A-G here. The shared
WebSearch pool ran out midway for all of them; the rest is project docs,
DefiLlama, CoinGecko, DexScreener, Galxe's API and airdrops.io. airdrops.io lags
(it still lists Lighter and edgeX as live) and contradicted its own page four
times, so a **T** row is a lead, not a fact.

- [A-trading.md](A-trading.md), [B-consumer.md](B-consumer.md),
  [C-evm-deposit.md](C-evm-deposit.md), [D-chains.md](D-chains.md),
  [E-non-evm.md](E-non-evm.md), [F-free.md](F-free.md),
  [G-verify-trackers.md](G-verify-trackers.md)
