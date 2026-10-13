# Build it Better: Chart Analyzer -- one number, the chart always in view (draft, not filed)

The operator, 2026-10-13, on the live page for Collector Crypt (CARDS, Solana, 1D): *"vypada strasne ... tolik smetimke cteni ze to je ultra anti degen friendly"*; two numbers (44% / 53%, and 49 in the gauge) with no way to tell which counts; scrolling down to tick the setups that glow on the chart hides the chart; and *"co je what the verdict is made of? kdo to ma cist?"*. Read live the same day. This follows their own redesign spec of 2026-10-01 (one screen, no jargon); the page was rebuilt since, with a verdict, and the clutter came back in a new form. Goals are theirs; the wording below is ours, their veto open.

Filing is the operator's step, on the form ("I have a link": `https://cymetica.com/chart-analyzer`), the block below in "What should it do better?". After filing, check the BB-SPEC line by line, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to the Chart Analyzer redesign: upgrade the live page itself, not a new page beside it; it keeps its name, logo and copy, and the template lines about rebuilding someone else's app do not apply. Goals, not methods. Figures are from the live page for Collector Crypt (CARDS, Solana, 1D) on 2026-10-13.
1. One headline number, never two. Today a degen sees "44% / 53%" (the verdict) and, further down, "49" (the gauge, "older method") and cannot tell which counts. The page itself says neither applies here: the verdict is "NO EDGE by rule" because the study measured exchange candles, not this DEX pool, and the 1-100 score "did not sort charts" on history it had not seen. The headline says only what holds: for a chart the study did not measure, "No verdict: the study measured exchange candles, not DEX pools", one line; for a chart it did, the verdict and its one pair of figures.
2. The study's figures for a chart type this asset is not, and the old 1-100 gauge, are not headline material: the gauge goes to the "How it is measured" section (item 5) with its own caveat, and the all-assets figures (45% / 51%) appear only labelled "all charts in the study, not this asset".
3. The same sentence is not said twice. Today the verdict block says the study measured exchange candles and that this asset's candles were not in it, in two paragraphs one under the other.
4. The chart stays in view while the setups are read: on a desktop the chart is fixed beside or above the setup cards while they scroll, so ticking a setup shows it on the chart at once; on a phone the cards sit under the chart in a strip, not a page below it.
5. One section explains the method, closed by default: "How it is measured", holding the study link, the built-on and tested-on figures, the old score, the public ledger and what "rose first" means. Today the same explanation stands in four places: the line under "What the verdict is made of", "What the number is made of", the "How the number is made" panel and "The numbers", with "The study" linked twice.
6. A setup card is one line of words and one pair of figures: its name, and "rose first 44%, fell first 50%" on the years it was tested on (the years it was built on, and the sample sizes such as 103,001, in its tooltip). A card never carries two paragraphs of statistics.
7. A setup's colour says what was measured, and the card says so in words. Today "Bearish engulfing after a rise" is green with a rising bar and "Bullish engulfing after a drop" is red; the reason is in a tooltip only. The card carries "bearish pattern, but history says up" or "bullish pattern, but history says down" where the two disagree.
8. A line that does not apply is not shown as a paragraph. The Weekly Signal explanation ("Needs at least 42 completed weeks of candles ... Not computable here", six lines) becomes one grey line, or nothing, when it cannot be computed for this chart.
Done when:
[ ] 1 The first screen has one headline number or one sentence, not two numbers.
[ ] 1 For a DEX-pool chart the headline says in one line that the study did not measure it, and shows no 44% / 53%.
[ ] 2 The 1-100 gauge is not on the first screen; it and its caveat are in "How it is measured".
[ ] 3 No sentence of the verdict block appears twice.
[ ] 4 At 1440 x 900 the chart and the setup cards are visible together; scrolling the cards does not scroll the chart away.
[ ] 4 At 390 px the chart is visible while a setup is selected.
[ ] 5 The explanation of the method exists once, closed by default; "The study" is linked once.
[ ] 6 A setup card is its name and one pair of tested-on figures; built-on figures and sample sizes are in its tooltip.
[ ] 7 Where a pattern's name and its measured direction disagree, the card says so in words.
[ ] 8 With Weekly Signal not computable, its text is one short grey line or absent.
```
