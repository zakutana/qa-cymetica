# ET-28378, what goes out (2026-09-30)

Board: part 2 pass, part 3 pass, part 1 pass, part 4 "Not yet: fail" with the note below.
If the board takes only one verdict for the whole request: "Not yet: fail" with the same note.
Wishes (design, adoption for chains, Pro-only report, table width, tooltips everywhere) go into the new request, not into this note. Source: `et28378-verify.md`, `et28378-complaints.md`.

## Note for part 4 (board)

```
Not built, or not as specified:
1. The Degen meter is one colour, in the row and in the detail. Spec A.1: segments green 1-3, light blue 4-6, red 7-10, as in the reference. The detail bar is also far narrower than the reference (216 of 783 px).
2. 4 of 18 checks never run for any app (hidden supply, insider flow, whales, team). 196 of 215 ranges are wider than two levels (91%).
3. Check circles use the old light tooltip, not the C.5 card (icon, verdict pill, value, context, source and date). Some tooltips are still the browser's own.
4. The Supply card contradicts the page: Pharaoh (PHAR) reads "0.0% of the float a week" and "No new tokens in 30 days", while emissions are $1.26M and net revenue +$1.1M. Curve is the same.
5. Trajectory stepper: "Ignition" has no colour. Spec C.8: the colour of the Trend check (light blue).
6. The Legend still lists flags no row shows any more (Micro, New, Post-crash, Declining, No trend, Stale data, Thin liquidity, Cliff, % in 90d). Spec A.11.
7. "The bet" was renamed "The thesis"; spec 4 keeps the names it has today.
Also open, as you listed: the Curve emission mismatch and Legend entries over 8 words. The Audit set comes from the DefiLlama list, not as the spec says.
```

## Telegram

```
@EventTraderQABot ET-28378, verdicts. Part 2 pass. Part 3 pass; note: ecosystem and BTCfi themes not built, "Waiting to run" and "Lagging and still falling" not seen on a live row. Part 1 pass; note: OTHERS.D break date 05-25 against 05-11 in the spec, two reads "not available", two source licences open. Part 4 not yet: the list is on the board. The rest (design and a few product questions) we send as a new Build it Better request. Thanks for listing the gaps up front.
```
