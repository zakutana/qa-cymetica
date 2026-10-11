# Build it Better: the Supply card and the Supply Analyzer page (draft, not filed)

On the form: "It exists" with the app `https://cymetica.com/supply-analyzer` (the Gem Screener card is the same data, so one request covers both). Text: the block below, one item per line. Pictures (the form takes at most 6): `mockup.png` from this folder. Filing is the operator's step; the request token shows once.

```
Supply card (Gem Screener coin detail) and the Supply Analyzer page: replace today's card with five numbers on top, as in the attached mockup (real HYPE, ARB and PHAR figures from your API, Oct 10). Goals, not methods: how you build it is your call.
One source per number, never two side by side: circulating supply, price and market cap from CoinGecko only (on PHAR it matches the chain: total 534.09M minus 498.56M held by xPHAR = 35.53M, CoinGecko's figure); DeFiLlama only for the future unlock schedule.
Tile 1, Circulating: "222.4M of 1.00B", a bar, "22.2% of max supply is out".
Tile 2, Market cap -> FDV: "$18.7B -> $83.9B" and "FDV 4.5x the market cap" (FDV = max supply x price, total supply when there is no max). Red at 3x or more, green at 1.5x or less.
Tile 3, Dilution, 12 months: new tokens in the next 12 months from published schedules and emissions, divided by circulating supply, as one number ("+53.5%"), with "9.9M new HYPE a month · vesting" and, when there are buybacks, "net of buybacks: +48.9%". Red at 25% or more, green under 5%.
Tile 4, Buybacks & burns: tokens bought back a month with their dollar value, and burns; or "None" with "no buybacks or burns found".
Next unlock row: the date, the days to go, the whole amount of that day summed over its recipients, its share of circulating supply, and who gets it. ARB on Oct 16 is 92.6M (Team, Contributors & Advisors 56.1M, Investors 36.5M); today the page shows only 56.1M. With no published schedule: "No schedule published" and the known emissions.
No estimates in place of missing data: when a schedule is not published, nothing is assumed (the "typical inflow" goes), and the card says so in one line.
Remove from the card: the 1-10 pressure score and its band, the "+51% to +66%" range and ESTIMATE, the sellable pile, the pie and its slices, "What we could not measure", the method paragraph and "SUPPLY SOURCES DISAGREE". The sources go into one (i) tooltip next to SUPPLY.
The Gem Screener card has no slider; "Open in Supply Analyzer" leads to it.
Supply Analyzer page: the same four tiles and next-unlock row on top, then a month slider over a stepped chart of tokens out (circulating plus scheduled unlocks and emissions, minus burns) from today to the end of the schedule, with a dot on each unlock day. Under it, for the chosen month: % of max supply out, new since today, bought back since today, market cap at today's price.
Colours from the site palette only (cyan, green, red, blue, slate), as in the mockup.
```
