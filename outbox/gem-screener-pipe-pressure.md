# Gem Screener: what Ran Neuner's "pressure in the pipe" would add (wishes for the request after ET-28821)

From the interview of Ran Neuner (Crypto Banter) by Raoul Pal (Journey Man), pasted by the operator on 2026-10-01 with the question: would we improve anything in the Gem Screener because of it. **Not filed, not sent.** These are goals, not methods, for the next Build it Better request once ET-28821 (spec 3, due 2026-10-02 20:41 UTC) is delivered. The operator can veto them; the numbers have to be read again on the snapshot of the day the request goes out.

Read on 2026-10-01: the live snapshot of 19:32 UTC (215 apps); the Collector Crypt detail as a visitor sees it, in the browser; DefiLlama `/protocols` and `/overview/fees?dataType=dailyHoldersRevenue` at about 21:40 UTC; Cymetica `GET /api/v1/crypto/alerts/kinds`.

## His method against the screener

He values a token as the **pressure in a pipe**. The width of the pipe is the supply that can actually be sold: not the FDV, but what is circulating, minus what is staked or locked, minus what has not been emitted yet. The pressure is the buying that is forced into the pipe, mostly buybacks paid from real revenue. His filter: is it a network, is the network growing, is there real revenue, does the value go back to holders? A protocol whose fee switch is *not yet* on is, to him, the most underpriced case. On top of that, his agents watch team wallets, and his reading of the cycle starts from ETH/BTC and OTHERS/BTC.

| His test | The screener today | What is missing |
|---|---|---|
| Real revenue, and is it growing | The Real revenue gate ($100K in 30 days), Revenue 30d, P/S, the Growing gate, Trajectory, Strength 3M | Nothing. Users are not counted for apps; revenue is harder to fake, so this is fine |
| Value goes back to holders (the fee switch) | "To holders" (DefiLlama's holders revenue as a share of revenue), the "No holder share" tag below 5%, the report's "Holders share" check | A zero that the source does not track reads as 0% and "Bad" (Collector Crypt). "Switch announced" and "no plan" look the same |
| The width of the pipe | Market cap on the circulating supply, FDV, "if all tokens were out", the tokens-out bar; spec 3 adds unlocks and the Dilution gate | Staked or locked own tokens: no field and no figure |
| The pressure in the pipe (buybacks) | Buybacks sit inside "To holders" as a share of revenue | No figure for how hard the token is bought against its market cap |
| Team wallets moving tokens | The "Insider flow" check ("insiders moving tokens to sell"), a *Later* check run on 98 of 215 apps and not counted in the level | No alert. Cymetica's new alerts have 16 kinds and none of them is on-chain |
| The cycle: ETH/BTC, OTHERS/BTC | The Altseason index reads BTC.D (support broken), OTHERS.D (trend broken), breadth, BTC heat, retail and volume | ETH/BTC is nowhere on the panel or in the snapshot |

## Wishes, most useful first

### 1. How hard the token is bought: "to holders" as a share of market cap a week, beside Dilution
**Goal:** a degen sees how much the protocol pays into its own token, in the same unit as the Dilution figure of spec 3 (% of market cap a week), and sees whether that money **buys in the market** (buybacks, burns) or **is paid out** (to stakers or lockers). The two figures stand side by side and are **never netted**: spec 3 keeps Dilution gross (items 10 and 25), and that stays as it is.

- Both inputs are already in the snapshot: `holders30d` and `mcap`. The kind of money comes from DefiLlama, which labels the holders-revenue streams for 74 of the 99 apps that have holders revenue: 31 are buybacks or burns only, 26 are payouts only, 11 are both and 6 are other.
- Live, to holders against new tokens, each as % of market cap a week: Hyperliquid 0.07 against 0 (buyback and burn); Pump 0.21 against 0.35 (buyback); PancakeSwap 0.14 against 0.04 (buyback and burn); Lighter 0.06 against 0 (buyback); GMX 0.10 against 0 (both).
- Pharaoh reads 13.2 against 7.2, because its two supply sources disagree eightfold (spec 3 item 25 already tags that case). Read with care.
- Netting buybacks off Dilution becomes possible later for the 57 apps whose holders money is of one kind. It is **not** asked here.

### 2. The narrow pipe: own tokens that are staked
**Goal:** the Supply card ("Market cap & supply" after spec 3) shows what share of the tokens out is staked in the protocol's own contracts. Figure 1 is also shown against the part that is not staked, because that is the part that can be sold.

- DefiLlama `/protocols` carries `staking` (own tokens staked) for 68 of the 215 apps. Picks: GMX 59% of market cap, Pharaoh 21%, KyberSwap 16%. Large apps: Olympus 97%, Venice 74%, Pendle 57%, Curve 54%, Sky 44%.
- **GMX in one line:** 0.10% of market cap a week goes to holders, which is 0.25% a week of the part that is not staked (about 13% a year).
- Above 100% the two sources count supply differently (Neverland 341%, xExchange 214%, Resupply 109%). Those rows read "unknown", never a number.

### 3. A zero the source does not track says "not tracked", and "switch announced" is told apart from "no plan"
**Goal:** "To holders" never reads 0% or "Bad" when the source itself says that it does not measure the figure. A 0% pick also says whether a fee switch or a buyback is announced, voted or live.

- **Collector Crypt.** Live, its detail shows *Holders share · Bad · 0.0% of revenue to holders*, and the report adds the red line *"Almost no revenue reaches holders."* DefiLlama's own methodology for it says the holders revenue is the CARDS the team buys back on the open market, and *"Currently 0: tracking is disabled until the buyback hub wallet is officially confirmed."* It is the only app of the 215 whose DefiLlama methodology says this. (Searched for "currently 0", "disabled", "not tracked", "untracked", "not included", "excluded" and "no buyback"; Synthetix matched too, but its note only says that some rewards are not included.)
- What is there today: the "To holders" tooltip already warns, in general, that a zero at DefiLlama sometimes just means that DefiLlama does not track buybacks, and the page's rule is that "—" means DefiLlama does not list a figure. The ask is narrower. When the source's own methodology marks the zero as untracked, the check and the report line read grey, "not tracked", and not "Bad · 0.0%".
- **The source exists and is free.** DefiLlama's own Token Rights data (`https://api.llama.fi/token-rights`; on the site it is the "Token Rights and Value Accrual" block of a token page such as https://defillama.com/token/PUMP) holds, per protocol, Fee Switch Status (ON or OFF), the primary Value Accrual (buybacks, revenue share, deflationary), Buybacks, Burns, Dividends and a dated detail text. It joins to the screener by `DefiLlama ID`, which is the app's `key`. Read 2026-10-02: 114 protocols, 52 of the 215 apps covered (40 switch ON, 12 OFF). Of the 7 picks, Meteora (ON, buybacks), GMX (ON) and Solv (OFF) are covered; Collector Crypt, KyberSwap, o1.exchange and Definitive are not. Meteora is the case: the page shows 0% to holders, while its record says a share of trading fees goes to discretionary buybacks. 13 apps show under 5% or no figure to holders although their record says the switch is ON or names a value accrual. An app with no record stays "unknown", never "no".
- **6 of the 11 picks have 0% or no figure to holders:** Collector Crypt, Meteora, KyberSwap, Solv, o1.exchange and fx Protocol. Their Upside is measured against Hyperliquid, and the page itself says that Hyperliquid returns about 100% to holders, "that is why its multiple is so high". The Degen report already fills "Holders share". The goal is that it says, with a link and a date, whether a switch or a buyback is announced, voted or live, so that 0% splits into "switch announced" and "no plan".

### 4. An alert when insiders move tokens
**Goal:** any coin on the screener can be watched for its team, treasury and investor wallets sending tokens to an exchange, or to a fresh wallet that then does so. The alert gives the amount as % of circulating supply. A pick's card carries a flag when such an alert fired in the last 7 days.

- Today: `GET /api/v1/crypto/alerts/kinds` lists 16 kinds (price, 24h and 7d change, market cap, volume, crowd emotion, belief strength, buzz, mentions), checked every 600 s; none of them is on-chain. "Insider flow" is a *Later* check on 98 of 215 apps. The screener already holds holder lists for 142 apps and contract scans for 169, so some of the wallets are known.
- Ran's own case: his agents watch team wallets, including hops through fresh wallets, and caught a team moving tokens while the price fell 10%.

### 5. ETH/BTC on the Altseason panel, as a fact row
**Goal:** ETH/BTC and its trend line stand on the panel as a **fact, not scored**, until a backtest shows that it adds something. The stablecoins fact is treated the same way today. ETH/BTC is the first chart that both Ran and Raoul open: ETH breaking out after nine years is their sign of product-market fit. The panel already has OTHERS.D, the alts-against-the-market line that he draws as OTHERS/BTC.

## Where it goes and how it looks
![The pipe on a coin's detail: Curve, 54% staked, 0.11% a week of new tokens in, 0.06% a week to holders](gem-screener-pipe-pressure/reference/pipe-mock.svg)

**One picture, four numbers, in the "Market cap & supply" card that spec 3 item 11 builds.** The mock is inspiration, not literal, and uses the page's own colours. Red in is the new tokens a week, the Dilution figure of item 25, gross. Green in is what goes to holders a week (wish 1). The hatched part is staked (wish 2). The thickness of an arrow follows its number (about 60 px per 1% a week). The example is Curve, snapshot 19:32 UTC: market cap $601M, staked $322M (54%), new tokens 0.11% a week, to holders 0.06% a week, all of it payouts.

- **No data is a grey dashed pipe with no arrows**, never a zero (wish 3, Collector Crypt).
- **Not a new gate.** The page reads "0% to holders" as a warning ("the token may never earn the upside"). Ran reads a fee switch that is not on yet as the best case. A gate would take one side. After spec 3's Dilution gate 8 picks remain, and 6 of them show 0% or no figure to holders (Collector Crypt, Solv Protocol, fx Protocol, KyberSwap, o1.exchange, Meteora), so it would also decide the list. The "No holder share" tag stays a tag, and the numbers are shown. Once the pre-registered series of item 25 exists, a gate can be asked for on its data.
- **Rows and pick cards get nothing new** (items 9 and 20 take text off them). The tooltip of the Dilution flag names the to-holders figure in one line.
- **The insider alert (wish 4) fills the existing "Insider flow" check**, a Later check that runs on 98 of 215 apps and does not count in the Degen level. It does not enter the picks.

**Tried on ten random apps (2026-10-02): 4 vetted, 3 not vetted, 3 picks; snapshot of 1 Oct 23:35 UTC and DefiLlama's public data.** The pipe could be drawn in full for 2 of 10 (Stader, and up with its "supply sources disagree" tag). Pieces: the width (tokens out) for 10; a figure to holders for 6, and a shown 0% for 4, where the zero can be untracked as with Collector Crypt; new tokens a week known for 4, unknown for 6 (no emissions or unlock data); staked tokens recorded for 1 (KyberSwap, 16% of market cap), and for the other 9 "none recorded" cannot tell none from missing; a Token Rights record for 1 (Meteora). So the pipe is a display of what is known, with grey for the rest, as designed above, and for most apps it will be partial. The 3 picks sampled (Definitive, Meteora, KyberSwap) have none a complete pipe.

## Where the data can be had besides DefiLlama (read 2026-10-01; the build chooses and pays)
DefiLlama is the base because it is free, its methods are open on GitHub, and it has the longest tail: the picks are $4M to $175M apps, where the paid sources cover the least. No single paid source has all of it.

| Need (wish) | Source | Price read | Note |
|---|---|---|---|
| Fee switch and value accrual (3) | DefiLlama Token Rights | Free, `api.llama.fi/token-rights` | 114 protocols, 52 of our 215 apps. On the site its Token Usage and Unlocks tabs need a subscription |
| Buybacks and burns (1) | Tokenomist | Pro $69/month, API from $249.95/month (promo, regularly $749.95) | 600+ tokens. Hyperliquid and Lighter are visible; for Collector Crypt it shows "--" |
| Buybacks (1) | Artemis | API from about $500/month (checked earlier the same day for the Chains wishes) | Has a BUYBACKS metric (seen on Hyperliquid); coverage not counted |
| Unlocks (spec 3's Dilution) | Tokenomist | as above | **Collector Crypt is covered**: 45.01% unlocked, next unlock 2026-10-29. The screener shows "dilution unknown" for it, because DefiLlama has no unlock data for it |
| Team, treasury and investor wallets (4) | Arkham | Intel API since 2026-02-17; price on request | Entity labels across 16 chains; alerts on treasury and investor deposits to exchanges |
| Flows by holder group (4) | Nansen | API Pro from $49/month (credits) | The `flows` endpoint gives whale, public figure, smart money, top 100 holders and exchange, across 24 chains; it has no team segment |
| Fundamentals in one standard (1) | Token Terminal | Pro $350/month, API priced on request | Revenue, earnings, users, supply; no buybacks metric found |

## Not taken from the talk
- Network effects as a judgement. It cannot be measured from the data the page has; revenue growth already stands in for it.
- Valuing an L1 by what switching it off would destroy. It cannot be measured.
- A trading bot. He says theirs did not work.
- "Who benefits from event X" (his Arbitrum after Robinhood Chain): that is research for Nexus or the Degen report, not a column.

## His coins on the screener (facts, not advice)
- Collector Crypt, his pick: a Degen pick here, 27x Upside on $12.4M of revenue a month, with the untracked zero of wish 3.
- Lighter, his switch from Hyperliquid: listed, not a pick (not vetted, not cheap, too big).
- Hyperliquid is the Apps benchmark.
- Zcash has no app revenue; it is not on Chains today, and spec 3 item 1 brings it in if its four inputs exist.

## Correction to our own spec 3
Item 25 says that buybacks are not netted off because "the data does not separate them from payouts to holders". DefiLlama labels the holders streams for 74 of the 99 apps with holders revenue (above). The requirement, gross dilution, is still right, but the reason given was incomplete. **Not sent:** the build is due in under a day and nothing in it changes.
