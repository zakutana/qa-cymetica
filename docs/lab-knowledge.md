# What the laboratory knows, per section

Ten lines a section, newest first. `lab.py log --lesson --section <s>` adds one; correct a line by hand when it stops being true. Read by `lab.py brief`, the desk and the morning report; the outsider never reads it.

## Our cards

- 2026-10-13 · 2026-10-13 · The first own-card buy (cebc34ec, +74.7 % at Sharpe 4.17 over 90 d after fees) was refused HTTP 400 'Basket is not fully priceable right now' though the card read tradeable_now -- a gate pass is not a fill; the known unpriced-card defect (tests/rest/test_a_tradeable_card_can_be_priced.py), retried next tick.

## Nexus cards

- 2026-10-14 · 2026-10-14 · Nexus (NEX-0145) read the whole live listing and says no live card holds a BTC/ETH-only basket, so his 60/40 majors idea has no UUID and no room; the only road is build_custom_event_card (an outward write, off by default here). His 90 d index backtest, 60/40 at 5 % round trip: +25.79 %, Sharpe 3.21, max drawdown 6.97 %. Exit he gives: an ~18 h time-stop, derived from our own +1.4 % at 18 h. Single-sourced, not tested.
- 2026-10-11 · His cards average -0.52 % after fees over 46 tests (13 worked, 32 didn't); sold after 18 h the same cards made +1.38 % on average, 70 % in profit (33 cards).

## Bots

- 2026-10-14 · 2026-10-14 · Nexus (NEX-0145) on Vortex Drain, which won at SL 5 / TP 20: test SL 5 / TP 30 (let winners run), cross-check SL 8 / TP 20, and pair it with Fibonacci Phoenix (mean-reversion, 3,593 trades). Hypotheses, not results; each waits for a free slot under the 50-paper-bot cap.
- 2026-10-14 · 2026-10-14 · 22 bot rooms closed in one tick: 16 returned +0.00 % (the paper bot held nothing -- a paused clone at balance 0, a bot that did not trade, not a refuted strategy), 5 ended on their 5 % stop-loss (Perceptron Oracle -3.15 %, Sent Surfer, Fade the Rally, Corr Catcher, Divergence Dragon -5.00 %), 2 survived with 0 % drawdown (a581e0e0 resumed, +47.06 % in 7 d; Vortex Drain SL 5 / TP 20, +14.80 % in 3 d). Two real winners in 22: a +0.00 % verdict is a bot that never traded and says nothing about its settings.
- 2026-10-13 · 2026-10-13 · The grid is at 84/132 cells and four species' bands (Dread Gauge 5/20 and 10/20, MACD Hunter 10/30, RSI Sniper 10/30) stay untried: the platform refuses a clone past 50 Paper bots including paused ones (21/50 trading), so cells wait for deleted clones, not for ideas.
- 2026-10-12 · 2026-10-12 · Grid ATR Alpha SL 5 / TP 20 measured nothing: its fund failed (HTTP 500), the room was stopped, the fund went through 49 min later outside it, and the verdict read 0 % coverage -- a cell is only a result once a room, a funded clone and an index window overlap.
- 2026-10-11 · Nexus gives a band per species (NEX-0137): Perceptron Oracle 12/30, Fibonacci Phoenix 10/22, MACD Hunter 12/36, RSI Sniper 10/24 -- a closer target for mean-reversion, a wider one for momentum.
- 2026-10-11 · The platform pauses every paper clone at its first stop-loss or take-profit (NEX-0124): without a resume after each pause a week is one trade.
- 2026-10-11 · SL 15 / TP 40 on 20 species (2026-10-06..11): 39 stop-losses to 13 take-profits in 52 runs, 25 % against the band's 27 % break-even -- the entries carried no edge at that band.

## Head-to-head


## Memecoins

- 2026-10-13 · 2026-10-13 · Nexus (NEX-0143) on Hot headlines: the binding constraint is exit-priceability (12 of 13 passers unpriced at exit), not the entry gate; admit only names with a live two-sided book first, then loosen the move-size gate 25-30 % on that priceable subset. Single-sourced, not yet tested here.
- 2026-10-13 · 2026-10-13 · $10 into every hot signal, held 24 h: -30.8 % a trade (n=2723, win 23.7 %); a -10 % stop with a +100 % target still loses -19.2 %. Hot reaches 2x in 24 h 1.7x as often as control (23.4 % vs 13.9 %) and 3x in 72 h 1.9x (14.7 % vs 7.6 %): a real lift, no profit after impact -- 1,366 of 7,629 signals had no price when they fired.
- 2026-10-13 · 2026-10-13 · Hot headlines, crypto entered Hot +24h: +3.69 % a basket (40/68 up) against +1.42 % for crypto not in Hot (299/482 up) -- but the card we would actually buy reads -0.04 % over 725 at +24h (+0.06 % at +6h), so the lift is in the index, not in a tradeable position.
- 2026-10-11 · Hot headlines: crypto that entered Hot was +3.9 % a day later against +1.4 % for crypto not in Hot (65 vs 482 baskets, 62 % up in both).
- 2026-10-11 · $10 into every hot signal, held a day: -30.6 % a trade (2,653 trades); hot reaches 2x in a day 1.6x as often as the control (23.5 % vs 14.9 %) -- a lift, not a profit.

## Outsider


## Desk

- 2026-10-13 · 2026-10-13 · Desk H2, STR-0213 (NEX-0138's SPCX card, bought 17:28 UTC, sold at 24 h): -3.91 % (-22.35 on 570.95, TRD-0122); its verdict read -4.32 %. Overnight it never fell below -1.47 %; the drop sits in the sampler's 08:29-15:48 UTC hole (-0.60 % before, -4.32 % after), which spans the 13:30 UTC open his exit named, so his exit is unread. H2 after two sales: mean -2.22 %, both under the 0.4 % fee line, n=2 of 10, no verdict; all three H2 buys are US-hours stock baskets carrying the overnight gap he advised against.
- 2026-10-13 · 2026-10-13 · Desk H2, STR-0212 (NEX-0138's AI Data-Center card, bought 17:27 UTC within his hour, sold at 24 h): -0.52 % (-2.95 on 570.95, TRD-0121). The sale is H2's number; the verdict's -0.22 % (card leg at its last interval=all point, T-0050) and +1.34 % benchmark (T-0039) are not, and the lab's 17:34 line quoted those (archived, manager T-0077). His own exit, modelled off the sampler's 20-min index points (no fill): +0.00 % at the 10-12 US close, his +2.0/-1.5 bracket never touched, against our -0.52 % over the night.

## Archive

- 2026-10-13 · 2026-10-13 · H2 (his NEX-0138 cards bought within the hour, held 1 d, our exit): AI Data-Center -0.22 %, SPCX -4.32 % against +1.34 % for the benchmark card, both refuted -- n=2, a measurement not a finding; the overnight gap he warned about cost the stock-basket card. (desk; archived 2026-10-13 by manager T-0077: the lab's line, off the rooms' verdicts, which are written before the sale; H2 counts the sale, -0.52 / -3.91 %, and 2 of 10 decides nothing. The Desk section is the desk's alone.)
