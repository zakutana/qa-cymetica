# Gem Screener four parts (ET-28378), checked live 2026-09-30

Read-only: the page at 1360 px (Playwright), the API, llms.txt. The vendor listed its own gaps up front; the numbers below are mine.

## Verdict advice

| Part | Advice | Why |
|---|---|---|
| 2 Chain valuation | pass | 8 of 8. `bench_chains` and `coins/TRX` carry the benchmark, the rule, 5 chains that may lead and 22 that cannot, each with a reason. |
| 3 Sectors themes | pass with note | Table and column order as specified. Tags "Waiting to run" and "Lagging and still falling" not on any live row (vendor says so). Ecosystem and BTCfi themes not built. Pair links on 125 of 177. Survivorship stated on the page. |
| 1 Altseason panel | pass with note | Panel on both tabs (28 / "No altseason yet", five tiles, slider). Endpoint answers, `acceptance.verdict` = fail 4 of 5 (share of weeks at or above T is 10.2 percent against a 10 percent limit), same as the reference. OTHERS.D break date 05-25 against 05-11 in the spec. Two reads "not available". Licence terms of two sources open. |
| 4 Degen level, Chart, detail | Not yet: fail | See below. |

## Part 4, what does not hold

- Four checks never run for any app: hidden supply, insider flow, whales, team (vendor: five, counting reaches-you beyond the 5 percent rule).
- Level range wider than two levels: 196 of 215 apps (91 percent); vendor says 195 of 214. Levels bunch at 4 to 6 (3:4, 4:34, 5:69, 6:78, 7:25, 8:5).
- Checks run: admin key 107, timelock 59, admin powers 169, reaches-you 99, audit 65, track record 60.
- Audit set is taken from the DefiLlama list, not what the spec says.
- Curve emission mismatch (0.0 percent of float a week against 2.8M USD of 30-day emissions): vendor knows, not fixed.
- New Legend entries not all at 8 words or fewer: vendor knows.
- "The bet" is now "The thesis" in the report (3 hits in `coins/AAVE/degen-report`), in the API and in llms.txt. Spec 4 keeps the names it has today ("The bet") and nowhere says "thesis". Minor, but a change the spec did not ask for.
- Chart column: 174 daily scores, 7 weekly, 14 thin; no open-candle scores in the daily set.
- Report states outdated, 7-day refresh, generating and the Ask button: not seen live (vendor says so).

## Not checked

Part 3 pair links landing on the right pair; supply section text; Legend word counts entry by entry; tablet layout.
