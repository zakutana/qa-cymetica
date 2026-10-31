# Prove It (mock): rules for when Nexus may use your money

Asked for by the operator on 2026-10-31: a page where a user sets, per product, the bar a product must clear before Nexus
may put the user's charged money into it ("Nexus, for event cards: when you prove a combination is profitable 70% of the
time, invest my money, 100%"), for products he does not understand too, and for products Cymetica has not launched yet.

**Open:** `python outbox/prove-it/serve.py` (the `prove-it` entry in `.claude/launch.json`), then
http://127.0.0.1:8802/prove-it. `?mode=sim` opens the simulated month.

## How it is built

Their live `/themes/performance` page, read anonymously and cached 60 s, with only its `<main class="tp-wrap">` replaced
by `main.html`; their header, chat bar, footer and inline styles stay. Our content uses their classes (`tp-table`,
`tp-tabs`, `tp-leg`, `tp-hold`, the "Give this to your AI agent" card, and `/fund-performance`'s label rows, copied into
`pi.css`). The first take was a standalone page in their palette; the operator: "ten tvuj template defaultni claude
vzhled". Every method except GET is refused by `serve.py`.

## The decisions (ours, veto open)

* **A sentence in, a rule card out.** The user writes in his words; Nexus fills four lines (What, Proof, Money, Stop) and
  only those count. A prompt alone can be read any way, and Nexus would be judging its own claim. The shape is their
  Quant Lab rule (`window_days, min_trades, min_return_pct, max_drawdown_pct, repeats, capital_usd, handoff`), lifted from
  paper bots to every product.
* **"70%" becomes 70% of trades won and up after fees, over 30 trades at least.** 70% of 10 trades is a coin flip 17
  times in 100; of 30, 2 times. Many small wins can still lose money.
* **Only proof after the rule counts**, on paper, on the pick Nexus names before trading; a new pick restarts the count.
  A backtest or a past week never opens the gate: their Quant Lab tried 6,480 combinations, 10 reached the blind test,
  0 cleared; 9 of their 18 funds are up and 9 down.
* **Money moves by itself once proven**, up to the rule's cap and never above the "Nexus may use" total; every rule has a
  stop (Nexus's default when the user gives none) that sells and sends the product back to paper. Stop all sells
  everything. Nexus never withdraws and never edits a saved rule.
* **New products**: an "anything new" rule gets each launch a row by itself, on paper from day 1, small cap.
* **Not understood products** get Nexus's suggested rule, taken with one tap.

## Numbers

`data.js` is written by `refresh.py` (GET only): event cards live total, `/api/v1/themes/performance`, the ranked table
of `/fund-performance` (the MCP `list_funds` is a POST, default-denied in `qa/safety.py`), Airdrop Farmer farms, and our
company 14's Quant Lab results. The balance ($1,000) is an example. The simulated month comes from one model
(`simulate()` in `pi.js`): themes open on day 28, funds open on day 14 and hit their stop on day 24, event cards end mix
#1 at 60% won and get no money, bots stay at 0 cleared; day 30 reads $980 = $779 cash + $201 in play.
