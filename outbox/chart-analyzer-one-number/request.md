# Build it Better: Chart Analyzer, a chartist for degens (draft, not filed)

The operator, 2026-10-13, on the live page for Collector Crypt (CARDS, Solana, 1D): *"vypada strasne ... tolik smeti ke cteni ze to je ultra anti degen friendly"*; two numbers (44% / 53%, and 49 in the gauge) and no way to tell which counts; scrolling down to the setups hides the chart; *"co je what the verdict is made of? kdo to ma cist?"*; beside a Binance screenshot: *"na binance je mnohem vic obrazovky vyuzito ... ten filter panel je tak moc hnusny. vygeneruj novy top design pro degeny"*. After the first mock: *"ja chci nekde na prvni pohled hned videt jestli je chart proste bullish nebo bearish ... kde smeruje"* and *"podstata toho chart analyzeru je ze ho otevru a misto grafu za nim sedi expert top chartista ktery mi vse sdeli pro max degena easy info"*; *"muzes cokoliv, chci at je to perfektni produkt pro degeny"*. Goals are theirs; the design is ours, their veto open. It follows their redesign spec of 2026-10-01 (one screen, no jargon); the page was rebuilt since, with a verdict, and the clutter came back in a new form.

## The pictures

Drawn from real data by `make_mockup.py` (in this folder): the candles (1H, 4H, 1D), the pool's price, 24h figures, liquidity, market cap, FDV and live trades are GeckoTerminal's for the CARDS/USDC Raydium pool (the pool the live page reads, "LIVE · DEX POOL"), read at 10:58 UTC; the verdict, the five setups and their study figures, and the two support lines are the live Chart Analyzer page's for CARDS 1D; tier, upside, revenue, tokens out, the Degen meter and the guardians are the Gem Screener's. Ours, as defaults the builder may improve: the trendline (from the Sep 10 low, the flattest line no later low breaks, log scale); a timeframe's trend (close above a rising 20-bar EMA = up, below a falling one = down, else sideways; today 1H down, 4H down, 1D up, 1W up); the lean (one point per textbook signal on the chart, setups and timeframes: 5 bullish, 4 bearish); and the chartist's sentences, written from those figures only.

- `desktop-1920.png`: 1920 x 1080, the main view.
- `desktop-1440.png`: a laptop, 1440 x 900; the same three columns, tighter.
- `layers-1920.png`: the Layers menu open, which replaces today's toggle panel.
- `phone-390.png`: a phone, 390 px; the chartist first, then the chart, the setups as a strip.
- `mockup.html`: the same page, live in a browser at any width (`?layers` opens the menu).

## Filing

On the form, "I have a link" with `https://cymetica.com/chart-analyzer`, the block below in "What should it do better?", one item per line, and the four PNGs as pictures (the form takes six). After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to the Chart Analyzer redesign of 2026-10-01: upgrade the live page itself, not a new page beside it; it keeps its name, logo and copy, and the template lines about rebuilding someone else's app do not apply. Goals, not methods. Figures: Collector Crypt (CARDS, Solana, 1D), 2026-10-13; the pool figures in the pictures are GeckoTerminal's at 10:58 UTC and may differ slightly from your feed. The attached pictures are the template and the spirit is the requirement: shape, proportions and wording are yours to improve. Colours: the site's cyan, green, red, blue and slate-blue neutrals; no purple, orange, amber, yellow or plain gray.
The idea: opening the page is like sitting next to a top chartist. At first glance a degen knows where the chart is heading, what to watch and how far to trust it; the chart and the details are there for whoever wants them.
1. Full window, as an exchange does, not a centred column. At 1440 x 900 and 1920 x 1080 the chartist panel, the chart, the setups and the key levels are on the first screen without scrolling; the chart is the biggest thing on it.
2. Coin bar: logo, name, pair, DEX, chain; live price and 24h change; 24h high, low, volume, pool liquidity, market cap, FDV; a Gem Screener chip (tier, upside, link), Ask your AI (it replaces the "Give this to your AI agent" bar), Share, + New.
3. Three columns: chartist and fundamentals left; the chart in the middle; setups, key levels and live trades right. On a phone: chartist, chart, setups as a swipeable strip, key levels.
4. Chartist panel, top left: one big trend word with an arrow (UPTREND ↗, DOWNTREND ↘, SIDEWAYS →), and a short qualifier when the short timeframes disagree ("short-term pullback").
5. Under it a lean gauge from bearish to bullish with one line, "Leans bullish: 5 bullish vs 4 bearish signals on the chart now", counting the textbook signals the page already finds (setups and timeframe trends), labelled as what the chart shows, not a forecast.
6. A trend chip per timeframe, 1H 4H 1D 1W: up, down or sideways. A good default: close above a rising 20-bar EMA is up, below a falling one is down, else sideways.
7. Three or four short sentences in a chartist's voice, from the page's own facts only: the trend and its levels, the latest pattern, the level to watch and what a close beyond it opens, the buy and sell flow. Plain words and numbers, no price targets, no promises; rewritten as candles close.
8. The edge, last in the panel: the verdict word (EDGE UP, EDGE DOWN, NO EDGE or NO VERDICT) and one line why; for a DEX pool "the study measured exchange candles, not this pool"; the study's figures in its (i). Today "44% / 53%" and a gauge "49" head the page although, by the page's own words, the first does not apply to this pool and the second did not sort charts; neither stays on the first screen, and the 1-100 gauge moves to "How it's measured".
9. "Ask the chartist": a box under the panel that asks NEXUS about this chart, with the chart's facts as context.
10. One-row chart toolbar: timeframes, range (90 180 All Fit), Candles ▾, Layers ▾ (with the number switched on), Log, Replay, Full screen. Every toggle of today's panel moves into the two menus; the legend under the chart goes, and the chart's top left carries O H L C, EMA 20, SMA 50 and volume.
11. Layers ▾ is one panel in three groups (Levels, Signals, Indicators), each line a checkbox with its line colour; ATR settings and Volume profile Off / Total / Delta on their own lines.
12. On the chart: support and resistance with prices tagged on the axis, the trendline, the averages, volume at the bottom, the scored window shaded, numbered pattern markers on their candles, the live price tagged.
13. Setups, right: one row each with a show/hide checkbox, the textbook direction (▲ ▼), name, kind and age, and one bar with the tested-on pair (rose 10% first, fell 10% first); the average chart's pair closes the list; built-on figures and sample sizes in the tooltip. Where name and figures disagree, words say so.
14. Selecting a setup lights it on the chart, which stays in view, with a small card: name, when, textbook direction, the two figures in plain words.
15. Key levels: price, 30-day high, trendline, supports and, on wide screens, EMA 20 and SMA 50, each with its distance in % and a bell: alert me when the price crosses it.
16. Fundamentals, for a coin the Gem Screener knows: tier, upside, revenue 30 days, tokens out, Degen meter, and the six guardians (Rug power, Holders paid, Liquidity, Price run, Security, Team) as chips.
17. Live trades of the same pool: price (green buy, red sell), size, time UTC, newest first, a faint size bar so a whale stands out, and the last 15 minutes bought against sold.
18. One "How it's measured", closed by default (today the method stands in four places, "The study" is linked twice and the verdict repeats itself). Weekly Signal, when not computable, is one grey line. Numbers carry only the digits they need ("LAST 197 DAYS", not "196.99767960241462").
Done when:
[ ] 1 At 1440 x 900 and 1920 x 1080 the coin bar, chartist panel, chart, setups and key levels are on screen without scrolling, at full width.
[ ] 3 At 390 px the chartist panel comes first, and the chart stays visible while a setup is selected.
[ ] 4 The panel opens with one trend word and an arrow, matching the 1D chip.
[ ] 5 The lean gauge and its line count signals the page lists, and say they are not a forecast.
[ ] 6 Four timeframe chips show up, down or sideways by one stated rule.
[ ] 7 The chartist's sentences quote only figures the page shows, and change when a candle closes.
[ ] 8 No "44% / 53%" and no 1-100 gauge on the first screen; a DEX pool reads NO VERDICT and why.
[ ] 9 A question in "Ask the chartist" is answered about this chart.
[ ] 10 The toolbar is one row; every toggle of today's panel is in Candles ▾ or Layers ▾; no legend under the chart.
[ ] 13 A setup row is one line of words and one bar with two figures.
[ ] 14 Selecting a setup highlights it on the chart while both are visible.
[ ] 15 A bell on a key level sets an alert that fires when the price crosses it.
[ ] 17 The live trades list moves as the pool trades.
[ ] 18 "How it's measured" exists once; no verdict sentence appears twice; no number carries needless digits.
```
