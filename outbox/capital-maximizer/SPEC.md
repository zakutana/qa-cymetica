# Capital Maximizer: build spec

A new Cymetica product. The user puts in USDC and picks a risk. Cymetica's engine finds the best strategies across all of DeFi and every chain and runs the one the user picks. The user watches the position and exits any time, back to their wallet.

The design is in this folder: open `mock.html` (see README.md). The pictures in `pictures/` are the target look. **The design is a proposal for the look only.**
- **Every number in it is made up:** rates, profits, leverage limits, platform and pool counts, TVLs. The mockup's arithmetic only keeps its screens consistent with each other; it is not a model to copy.
- **Every text in it is an example:** headings, labels, buttons, step lines, tooltips. Write your own copy everywhere.

| Picture | What it shows |
|---|---|
| `pictures/01-risk.jpg` | Step 1: the four risk tiers |
| `pictures/02-amount.jpg` | Step 2: one amount of USDC |
| `pictures/03-finding.jpg` | Step 3 while it searches: the scan |
| `pictures/04-top3-high.jpg` | Step 3: the top 3 strategies as skill trees (High Risk) |
| `pictures/05-top3-og.jpg` | The same for OG Gambler |
| `pictures/06-top3-conservative.jpg` | The same for Conservative (a three-vault split) |
| `pictures/07-plan.jpg` | Step 4: the picked strategy, leverage, START |
| `pictures/08-positions.jpg` | Positions: an open route, its value, liquidation gauge, EXIT |
| `pictures/09-exit-confirm.jpg` | EXIT asks first |
| `pictures/10-exit-unwinding.jpg` | EXIT: the route's tree playing backwards into the wallet |
| `pictures/11-exit-wallet.jpg` | EXIT done: what is back in the wallet |
| `pictures/12-platforms.jpg` | Platforms: every supported platform, filtered by kind and chain |
| `pictures/13-logo.jpg` | The logo |

---

## 1. What we ask of Cymetica

**The engine is the product.** Build a top engine that searches for the best possible strategies for all four risk tiers (Conservative, Medium, High Risk, OG Gambler) across the whole of DeFi and every chain. It never stops searching, and it has to be unbeatable. You are an AI-native company: the user picks a risk and an amount and relies on you for the rest. We expect top quality only.

- **Always up to date.** Rates, platforms, chains and strategies are refreshed continuously, and new platforms and new kinds of strategy are adopted as they appear. A strategy shown to the user reflects the market now.
- **The most modern strategies, and your own.** Your own algorithms and strategies are welcome. Our research lists the families we know of (leveraged LST/LRT loops, Pendle PT loops and YT, funding and basis carry, perp leverage and perp LPs, concentrated LP, leveraged farming, restaking, BTCfi, stablecoin yield stacks). It is a floor, not a ceiling.
- **Cross-chain.** One strategy may run its legs on several chains. USDC moves between them; the mockup uses Circle CCTP as the example. Every screen shows the whole path, for example `Ethereum → Arbitrum`, never just one chain.
- **Platforms and chains are your call.** We hand over our research in `research/` (`platforms-review.md` and `platforms-proposed.json`): 62 platforms we would use on 21 chains, the strategy map with the data feeds each strategy needs, the rules we would change, and what we would leave out and why, with sources for every platform. Use it as input. Decide what goes in. Build **your own verification layer** that decides which platforms pass and which do not, and add your own platforms and chains.
- **One hard rule: no KYC platform, ever.** That means no venue, pool or token that asks the user, or the product on the user's behalf, for identity. Our research found Falcon (USDf) and Solstice (USX) failing this.

---

## 2. The look: build exactly as drawn

Build the layout, the parts, the colours and the motion exactly as drawn. The operator considers this design top and does not want it changed. Use the site's fonts (Archivo Black for headings and big numbers, JetBrains Mono for labels and figures, Inter for body text and buttons) and palette: base `#0a0e17`, panels `#0d1520`, lines `#1e3050`, green `#00ff88`, cyan `#00cfff`, red `#ff4444`, blue `#3b82f6`. Show only what is drawn.

**The words are yours.** Every text quoted below and in the pictures is only an example of what goes in that place. Write your own copy everywhere, in English: headings, labels, buttons, step lines, tooltips, chips. For example, `AUDITED DEFI ONLY` and `AI RE-CHECKS EVERY 6 H` should say what your verification and your engine actually do. What is binding is the look: where each part sits, how it is drawn, its colours and its motion.

**Colour rule:** a profit is always green. Red is only for a loss, liquidation and EXIT. OG Gambler's tier card keeps a red frame and a red name; its number is green.

### Header (every screen)
- The logo (picture 13, Hologram Dollar): three chip-edged hexagon layers projecting a chip-ringed dollar hologram on a beam. It is `logos/logo-12.svg`.
- "CAPITAL **MAXIMIZER**" (MAXIMIZER green) over "BY CYMETICA".
- Three tabs in one control: **Maximize**, **Positions** (with the number of open positions) and **Platforms** (with the number of platforms).

### Maximize: four steps on a rail
A fine line with four hexagon nodes, **Risk · Amount · Strategies · Plan**. The current step is filled green, done steps are outlined green, and the line between done steps is lit.

**1 · Risk (picture 1).** Four cards in a row. Each card has:
- a hexagon emblem: shield, sprout, flame or die;
- a 4-bar risk meter;
- the tier name and one short line;
- **MAX PROFIT / MONTH** as a big multiplier with its %;
- LEVERAGE and ASSETS;
- "Choose →".

On hover a card lifts and its fine gradient frame lights. Under the cards, one dim line says what "max profit" assumes and where the rates come from, with the detail behind an (i).

**2 · Amount (picture 2).** One centred card:
- the picked tier as a pill with "Change";
- one huge amount input with a USDC token;
- quick amounts 500, 1,000, 5,000, 25,000 and 100,000;
- **MAX PROFIT THIS MONTH** in big green;
- the button **FIND TOP 3 STRATEGIES**.

**3 · Finding (picture 3).** For about 2.5 s:
- a radar on hexagon rings with the logos of the supported platforms, which light up as a sweep passes;
- counters for PLATFORMS, CHAINS, POOLS READ, ROUTES BUILT and TOP STRATEGIES;
- a ticker of the pools being read.

**3 · Your top 3 (pictures 4–6).** Three cards side by side. The best one carries **TOP PICK** and a green frame. Each card has:
- **A rank hexagon, the strategy's name and its venue.**
- **A skill tree flowing top to bottom.**
  - The USDC root at the top.
  - A Circle CCTP node (dashed hexagon) when the route leaves the home chain.
  - One hexagon per protocol step with its logo and a small plate: protocol, action and rate, with borrow rates in red.
  - A leverage diamond with − and + buttons.
  - At the bottom, the apex hexagon with the max-profit %.
  - The links are fine 1.5 px lines with light particles running along them.
  - On reveal the nodes grow in order from the root.
  - Each node carries a step number.
- **The numbered steps, under the tree**, with the user's own amounts, for example "1 Move 5,000 USDC to Arbitrum · Circle CCTP", "5 Borrow 5,000 USDC against it · Aave −3.54%/yr" and "6 Buy more weETH, repeat to 2.0× · 10,000 USD in weETH".
- **The footer:**
  - **MAX PROFIT / MONTH** in big green dollars;
  - RETURN as × and %;
  - LEVERAGE;
  - LIQUIDATION in red;
  - **CHAINS** as the whole path (`Ethereum → Arbitrum`);
  - **SELECT STRATEGY**.
- − and + re-compute everything on the card.

**4 · Plan (picture 7).**
- The picked strategy's tree, laid out left to right, with the same numbered steps beside it.
- Under it, a bar with:
  - LEVERAGE as a slider with a diamond thumb, which re-computes everything;
  - LIQUIDATION;
  - **MAX PROFIT / MONTH**;
  - a big green **START**, with chips for how often the engine re-checks the route and for its chain path.
- START opens the position and moves to Positions.

### Positions (pictures 8–11)
A strip with **IN THE POOLS**, **OPEN ROUTES** and **RETURNED TO WALLET**, then one card per position:

- **The route:** tier emblem, name, venue, chain path and chips.
- **IN THE POOL:** one big number in white, or red when the position is below what was put in. Under it the result in $ and % (green up, red down), a line of the value over time with a dashed line at the amount put in, and how long it has been open.
- **The liquidation gauge:** a semicircle from red through cyan to green, with a needle. A big number such as **6%** sits over "ETH CAN FALL BEFORE LIQUIDATION". It is a distance, never written with a minus sign. A route that cannot be liquidated reads SAFE / NO LIQUIDATION.
- **A big red EXIT** with a slow shine, and "everything back to your wallet".

**EXIT:**
1. **It asks first (picture 9):** "Close this position?", with YOU GET BACK (USDC), RESULT ($ and %), one line saying everything returns to the wallet and the route stops earning, and CANCEL or **YES, EXIT**.
2. **The tree plays backwards (picture 10).** The position's own skill tree empties node by node: repay the loan, withdraw the collateral, swap back to USDC, move it home with CCTP. Each link drains as its node empties, and the light flows back to the root, which is the wallet and lights up green. IN THE POOL counts down while IN YOUR WALLET counts up. Underneath, a progress panel shows STEP n / N, the %, a lit bar with one diamond per step, and the current action with its amount.
3. **Done (picture 11):** EXIT COMPLETE, the wallet, the amount now in the wallet in USDC (big green), the result against the amount put in, and DONE. The card then turns into a closed card showing what came back.

### Platforms (picture 12)
- **A strip:** PLATFORMS, TVL, CHAINS, IN THE FINDER TODAY, and a chip naming the cross-chain rail.
- **Filters:** by kind (Lending, Liquid staking, DEX, Yield…) and by chain. The rarer chains sit behind a "+N".
- **One small tile per platform:** its logo in a hexagon, the name, how many chains it runs on, its kind, its TVL, and a check that it passed **your verification layer**. A dot marks the platforms the engine uses today. Hover shows the rest: chains, record, and what the engine uses the platform for.
- **About 50 tiles fit on one screen**, so the list stays short at a glance.

---

## 3. The numbers: yours, one model, everywhere

All numbers in the mockup are made up. In the build, every figure comes from your engine on live data, and one strategy shows **the same number on every screen**: the tier card, the amount screen, the top 3 card, the plan, and the position when it opens. Tuning the leverage re-computes everything shown. The (i) says what "max profit / month" assumes.

---

## 4. Done when

- [ ] Every screen matches its picture in layout, parts, colours and motion. The texts are your own.
- [ ] The engine searches continuously for all four tiers and shows the top 3 per tier, from live data, across chains, each with its whole chain path.
- [ ] No KYC platform anywhere.
- [ ] The Platforms tab shows your verified set and what your verification checks.
- [ ] One strategy shows the same number on every screen, and leverage tuning re-computes it.
- [ ] EXIT asks, unwinds the route, and lands everything in the user's wallet.

## Files

- `mock.html`: the page and its styles.
- `cm-ui.js`: the screens, the skill trees, Positions and EXIT.
- `cm-core.js`: the mockup's arithmetic (illustrative).
- `data.js`: example data.
- `pictures/`: the target pictures, 1440 px.
- `logos/logo-12.svg`: the logo.
- `research/`: our platform and chain research (input, not binding).
