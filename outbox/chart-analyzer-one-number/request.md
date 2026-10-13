# Build it Better: Chart Analyzer, a degen layout (draft, not filed)

The operator, 2026-10-13, on the live page for Collector Crypt (CARDS, Solana, 1D): *"vypada strasne ... tolik smeti ke cteni ze to je ultra anti degen friendly"*; two numbers (44% / 53%, and 49 in the gauge) and no way to tell which counts; scrolling down to the setups hides the chart; *"co je what the verdict is made of? kdo to ma cist?"*; then, beside a Binance screenshot: *"na binance je mnohem vic obrazovky vyuzito ... ten filter panel je tak moc hnusny. vygeneruj novy top design pro degeny"*. Goals are theirs; the design is ours, their veto open. It follows their own redesign spec of 2026-10-01 (one screen, no jargon); the page was rebuilt since, with a verdict, and the clutter came back in a new form.

## The pictures

Drawn from real data by `make_mockup.py` (in this folder): the candles, the pool's price, 24h figures, liquidity, market cap, FDV and live trades are GeckoTerminal's for the CARDS/USDC Raydium pool (the pool the live page reads, "LIVE · DEX POOL"), one read at 10:58 UTC; the verdict, the five setups and their study figures, and the two support lines are the live Chart Analyzer page's for CARDS 1D; tier, upside, revenue, tokens out and the Degen meter are the Gem Screener's. The trendline is ours (from the Sep 10 low, the flattest line no later low breaks, log scale).

- `desktop-1920.png`: 1920 x 1080, the main view.
- `desktop-1440.png`: a laptop, 1440 x 900; the same three columns, tighter.
- `layers-1920.png`: the Layers menu open, which replaces today's toggle panel.
- `phone-390.png`: a phone, 390 px; the columns stack, the setups become a strip.
- `mockup.html`: the same page, live in a browser at any width (`?layers` opens the menu).

## Filing

On the form, "I have a link" with `https://cymetica.com/chart-analyzer`, the block below in "What should it do better?", one item per line, and the four PNGs as pictures (the form takes six). After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to the Chart Analyzer redesign of 2026-10-01: upgrade the live page itself, not a new page beside it; it keeps its name, logo and copy, and the template lines about rebuilding someone else's app do not apply. Goals, not methods. Figures are from Collector Crypt (CARDS, Solana, 1D) on 2026-10-13; the pool figures in the pictures (price, 24h, liquidity, trades) are GeckoTerminal's at 10:58 UTC, so they may differ slightly from your own feed. The four attached pictures are the template and the spirit is the requirement: shape, proportions and wording are yours to improve. Colours stay the site's: cyan, green, red, blue and the slate-blue neutrals; no purple, orange, amber, yellow or plain gray.
1. The page uses the whole window, as an exchange does, not a centred column with empty margins. At 1440 x 900 and at 1920 x 1080 the price, the chart, the verdict, the setups and the key levels are all on the first screen without scrolling, and the chart is the largest thing on it.
2. A coin bar replaces today's header: logo, name, pair, DEX and chain; the live price with its 24h change; 24h high, 24h low, 24h volume, pool liquidity, market cap and FDV; on the right a Gem Screener chip (tier and upside, linking to the coin), Ask your AI, Share and + New. The "Give this to your AI agent" bar above the tool becomes the Ask your AI button.
3. Three columns under it: verdict, key levels and fundamentals on the left; the chart in the middle; setups and live trades on the right. On a phone they stack: verdict, chart, setups as a swipeable strip, key levels.
4. One headline, never two numbers. Today the page shows "44% / 53%" and, lower, a gauge "49" ("older method"); by the page's own words the verdict does not apply to this pool, and the gauge did not sort charts on history it had not seen. The verdict card shows one word (EDGE UP, EDGE DOWN, NO EDGE or NO VERDICT) and one line why; for a DEX pool: "The study measured exchange candles; this pool was not in it". The study's figures for charts like it go in the (i) tooltip, labelled as the study's.
5. Under the word, one line read at a glance: the setups on the chart by the textbook (▲3 ▼2) and whether any beats the average chart in the study ("none beats the average chart, ↑45% ↓51%").
6. The 1-100 gauge leaves the first screen; it lives in "How it's measured" with its own caveat.
7. The chart toolbar is one row, as on an exchange: timeframes (1H 4H 1D 5D 1W 2W 1M), range (90 180 All Fit), Candles ▾ (Candles, Hollow, Heikin-Ashi, Line, Bars), Layers ▾ with the number switched on, Log, Replay, Full screen. Today's two rows of toggles, the candle style row, the ATR row, the volume profile row and the overlay row all go into those two menus.
8. Layers ▾ opens one panel in three columns (Levels, Signals, Indicators), each line a checkbox with its line colour beside it; ATR's length, colour and thickness on its line; Volume profile Off / Total / Delta there. The legend under the chart goes: the colours are in the menu, and the chart's top left carries O H L C, EMA 20, SMA 50 and volume, as on an exchange.
9. On the chart: support and resistance as lines with their price tagged on the axis (S1 0.152, S2 0.102), the trendline, the averages, volume at the bottom, the scored window shaded, pattern markers numbered on the candle they were confirmed on, and the live price tagged on the axis.
10. The setups panel lists the setups on the chart now, one row each: a checkbox that shows or hides it on the chart, the textbook direction (▲ or ▼), name, kind and age ("Pattern · 1 candle ago"), and one bar with the two tested-on figures (rose 10% first, fell 10% first). The average chart's pair closes the list for comparison. Built-on figures and sample sizes are in the row's tooltip.
11. Selecting a setup lights it on the chart, which stays in view: its marker glows and a small card beside it gives the name, when it was confirmed, the textbook direction and the two figures in plain words ("about the average chart").
12. Where the textbook name and the measured figures disagree, words say so; a bearish pattern is never shown green without them.
13. Key levels: price, 30-day high, trendline, supports and, on a wide screen, EMA 20 and SMA 50, each with its distance from the price in %.
14. Fundamentals, for a coin the Gem Screener knows: tier, upside, revenue 30 days, tokens out, the Degen meter and a link to the coin.
15. Live trades of the same pool: price (green buy, red sell), size in $, time UTC, newest first, a faint bar for size so a whale stands out, and the last 15 minutes bought against sold above it.
16. Weekly Signal, where it cannot be computed, is one grey line ("needs 42 weeks of candles"), not a paragraph.
17. The method is explained once: "How it's measured", closed by default (the study, built-on and tested-on years, the old score, the public ledger, what "rose first" means). Today it stands in four places, "The study" is linked twice, and the verdict says twice in a row that the study measured exchange candles.
18. Every number shows only the digits it needs: the chart's title reads "LAST 197 DAYS", not "LAST 196.99767960241462 DAYS".
Done when:
[ ] 1 At 1440 x 900 and 1920 x 1080 the coin bar, verdict, chart, setups and key levels are on screen without scrolling, and the page uses the full width.
[ ] 2 The coin bar shows the live price, 24h change, high, low, volume, pool liquidity, market cap, FDV and the Gem Screener chip.
[ ] 3 At 390 px the chart stays visible while a setup is selected, and only the setups strip scrolls sideways.
[ ] 4 The first screen has one verdict word and one line; no "44% / 53%" and no gauge on it; a DEX pool reads no verdict, and why.
[ ] 7 The toolbar is one row; every toggle of today's panel is in Candles ▾ or Layers ▾; no legend under the chart.
[ ] 8 Layers ▾ shows each layer with its colour, in three groups.
[ ] 10 A setup row is name, kind and age, and one bar with two figures; built-on figures are in its tooltip.
[ ] 11 Selecting a setup highlights it on the chart while both are on screen.
[ ] 13 Each key level shows its distance from the price.
[ ] 15 The live trades list moves as the pool trades.
[ ] 17 "How it's measured" exists once, closed by default; no sentence of the verdict appears twice.
[ ] 18 No number on the page carries more digits than it needs.
```
