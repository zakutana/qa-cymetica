# Chart Analyzer: notes for the operator's next spec (collected 2026-10-01, not filed)

The operator will write a new Chart Analyzer spec himself and asked for these remarks to be kept ("zapamatuj si pripominky"). They come from the Gem Screener work of 2026-10-01. Numbers are from the live page's snapshot (`chart_meta`, fetched 13:38 UTC) and from the public API. A different request, the redesign (`chart-analyzer-redesign/SPEC.md`, 13 points, accepted), is already in hand; this is not a copy of it.

## What the score is worth
- The study, `chart_meta.study` v2 of 2026-10-01 (`GET /api/v1/chart-analyzer/study`): `daily_higher_rose_more_often: false` and `weekly_higher_rose_more_often: false`. High scores did not rise more often, daily or weekly. The Apps card says so: "Not a forecast. On held-out data, high scores did not rise more often."
- Said at the time: "the study is not a topic for now" (operator, in the chains spec). It is a topic for this spec.

## Coverage
- The study measured Binance spot candles of 292 pairs (`GET /api/v1/chart-analyzer/symbols`, `count: 292`).
- All 178 apps that have a daily score are scored from DEX pool candles (GeckoTerminal, chosen by contract address), and every one of them reads `coverage.coin = not_in_study`: **0 of 178 are covered by the study.** No Apps score is something the study measured.
- Of 42 chain tokens tried, 33 are among the 292 symbols (SOL, ETH, BNB, SUI, TRX, AVAX, ADA, TAO, HBAR, SEI, IOTA, ...); not: CRO, FLR, HYPE, MNT, MON, OKB, QUAI, TON, XDC. Spec 3 of the Gem Screener (item 7) puts the Chart column and card on Chains, scored by symbol, so what this spec changes about scoring or coverage reaches that item.

## Gaps in what the Gem Screener shows
- Of 215 apps: 178 scored; no contract 11, no candles 10, too little history 9, no pool 6, collecting 1. Weekly scores: 3. Thin trading flagged: 13.
- `chart_meta.calls` at the 13:38 UTC refresh: 2 batch calls, 15 single calls, **15 single calls failed**, 0 waited on a 429; the read took 126 s. Why every single call failed is not known: an observation to look into, not a finding.

## The API as it is (public OpenAPI, 2026-10-01)
`GET /api/v1/chart-analyzer/analyze` takes `symbol`, `contract`, `chain`, `timeframe`, `include_candles`, `closed_only`; also `POST /analyze`, `POST /batch`, `GET /batch/gem-screener`, `GET /gem-screener/coins`, `GET /symbols`, `GET /chains`, `POST /upload`, `GET /format`, `GET /study`.
