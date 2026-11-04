# Capital Maximizer: the best routes per tier

Read 2026-11-04 19:27 UTC, 5,000 USDC, one month, from Ethereum. Every figure comes from `score.py` in this folder: one snapshot, one calculation, a tier is only a filter. It reproduces Cymetica's own figures for their own routes to 0.1% (`--check`).

- **Rule:** Cymetica's: the lowest of today, the 7-day and the 30-day mean of the base rate.
- **Lasting:** the same route on the 30-day median, after the share of a pool's fees its LPs keep, against the worse borrow rate of now and the week. The rule keeps spikes; lasting is what we rank by.
- **Liquidation is never a filter.** A route stops only for KYC, a deposit gate, a lender that will not lend, or a pool under $3M.

Tiers: `tiers.json`. Searched by 10 family hunters, top routes read at primary sources by 4 verifiers, then 4 challengers and a second round on Medium: no challenger beat a top 3 place by over 5% on their list, except the Medium route now at #1.

## On their list today

| Tier | Finder, lasting | Their live top 3, rule | Their top 3, same routes on lasting |
|---|---|---|---|
| Conservative | $22.84 / $22.61 / $20.07 | $23.64 / $22.85 / $21.47 | $22.61 / refused (RWA) / $22.61 |
| Medium | $34.71 / $31.15 / $30.87 | $30.40 / $28.85 / $25.98 | $30.41 / $28.17 / $25.06 |
| High Risk | $39.77 / $34.71 / $33.97 | $31.06 / $30.40 / $28.85 | $26.38 / $30.41 / $28.17 |
| OG Gambler | $335.48 / $292.24 / $138.71 | $157.81 / $154.52 / $55.18 | $138.71 / $81.93 / not matched |

**The finder's routes**

| Tier | # | Route | Chain | Lever | Lasting | Rule | Say with it |
|---|---|---|---|---|---|---|---|
| Conservative | 1 | Aave V3 USDC | Avalanche | none | $22.84 | $22.84 | |
| | 2 | Jupiter Lend Earn USDC | Solana | none | $22.61 | $23.64 | |
| | 3 | Compound V3 USDC | Base | none | $20.07 | $20.48 | our deposit lowers its rate: 6.04% to 5.89% at 5,000, 3.24% at 100,000 |
| Medium | 1 | USDC direct in Morpho dCOMP/USDC 0.625 | Ethereum | none | $34.71 | $52.02 | one borrower holds $13.48M; 100% lent on 3 days of the last week |
| | 2 | PT-sUSDai 25 Feb 2027, held | Arbitrum | none | $31.15 | $31.14 | |
| | 3 | stUSDS / USDC, Morpho | Ethereum | 3x | $30.87 | $39.71 | moves with gas: 4.25 units of a $0.19 to $2.77 unit |
| High Risk | 1 | stUSDS / USDC, Morpho | Ethereum | 5x | $39.77 | $55.21 | liquidated at a 7% slip of stUSDS |
| | 2 | USDC direct in Morpho dCOMP/USDC | Ethereum | none | $34.71 | $52.02 | as above |
| | 3 | PT-sUSDS 26 Nov / USDS, Morpho | Ethereum | 5x | $33.97 | $37.67 | matures in 21 days, then earns 3.79%; at 100,000 the loan takes 88% of what is free |
| OG Gambler | 1 | Orca ZEC-USDC | Solana | none | $335.48 | $378.94 | pool average: earning it takes a range of about +-17%; full range earns about 10% |
| | 2 | Orca SOL-ZEC | Solana | none | $292.24 | $324.74 | same; full range about 6% |
| | 3 | Orca SOL-USDC | Solana | none | $138.71 | $157.82 | same; full range about 5% |

## What the search found

1. **Conservative, Medium and High are close to the real maximum on their list.** Their engine reads rates well and finds most of it. The gap is $4 to $9 a month.
2. **OG is the real gap: $335 against $139.** Their top 3 misses the ZEC pools, and its #2 (WETH-USDT 0.3%, $154.52) is a spike that earns $81.93 on its median.
3. **Leverage on their list does not pay much.** Staked assets earn 2-5%, dollars 6-9.5%, and a loan against a staked asset costs nearly what it earns. High can only beat Medium with dollar loops, by a few dollars. Wherever a real swap cost applies, the loop's edge goes.
4. **Borrowing and putting the money in a pool loses to the plain pool**, unless the lender takes the pool position itself as collateral. With collateral C, borrowed money D is at most E - (1-t)C, so profit is a straight line: the best is at an end, a full loop or no loan. Checked on 25 real pairs: `candidates/stacks.json`.
5. **Nothing on their list levers a volatile pool that is open.** Fluid's USDC-ETH vault #77 is over its cap; #22 holds $20k. Fluid's dollar smart vault #67 earns less levered than plain.
6. **The big numbers need platforms they do not have:**

| Addition | Route | Lever | Lasting | Rule | Capacity | Say with it |
|---|---|---|---|---|---|---|
| Arcadia | Base WETH-USDC 0.3% | 7x | $400 to $435 | $513 to $549 | $83k | lost $2.5M on 15 Jul 2025, the check that refused GMX; this pool is not in its app, entry is by contract |
| Loopscale | Orca SOL-USDC | 4.75x | $391.80 | $441.28 | $5k | one week's rate; nothing on ZEC |
| **Revert Lend** | Base WETH-USDC 0.3% | 4.25x | **$377.70** | $460.27 | $269k | read on-chain: $875k free, borrow 7.24%, factor 0.775, 69 live loans there; Code4rena audit, no identity step in the docs; no transformer flow simulated |
| Veranta | avUSDC house vault, Base | none | $80.89 | $80.88 | $490M deposit room | High's "house vaults" have nothing to hold today: HLP's APR is -0.07%, GMX fails |
| 3Jane | PT-USD3 / USDT, Morpho | 5x | $66.92 | $90.21 | $150k depth | 15.54% rests on USD3's 0.73% DEX premium; about 6.25% to par |
| Axis | PT-sUSDx, sUSDx | none | $54 to $58 | $54 to $58 | | mint for approved parties; open pool |

   40 Acres ($93.83 at 25%) is real and a user cannot get out: a simulated withdrawal of 1 USDC reverts. Left out.

## What is wrong in their rule

- **A mean keeps a spike.** WETH-USDT 0.3%: 437M of 636M 7-day volume fell on one day; 49.97 in the row, 31.72 median.
- **DefiLlama counts fees before the protocol's cut.** LPs keep 5/6 on Uniswap V3 0.3% and 1%, 3/4 on 0.05% and 0.01%, 87% on Orca (read on-chain).
- **A 7-day reading can be plain wrong.** Base WETH-USDC 0.3% reads 19.8; swap logs say 52-62%. A reading of exactly 0 removes a live pool (USDC-USDT 0.01%, $34M).
- **A flat 0.3% entry understates a 1% pool** (DORY-USDC costs 2.1%, not 0.3%), and a flat 0.1% loop swap overstates one on a deep pair and understates another (apyUSD costs 0.53%).
- **A pool's rate is a pool average**: it takes an active range, and the card does not say so.
- **A debt in a token that earns grows by what it earns:** wstETH-debt loops read +36% and earn -4%.
- **A PT maturing inside the month** earns its rate only until then.
- **Exits are not shown:** Kamino Commodity queues beyond its $2.72M buffer for 1-3 months; sUSDai has a 30-day unlock.

## Not verified

No deposit on Solana was simulated; EVM deposits were, by `eth_call`, for Conservative and the Medium routes. No CCTP transfer, no Revert or Arcadia flow. The hunters' rows carry the rates of their reading, 4 Nov 15:43 to 17:00 UTC; the rest are from 19:27. Kamino Commodity's loan agreement is on request only: no depositor identity check was found, none is ruled out.
