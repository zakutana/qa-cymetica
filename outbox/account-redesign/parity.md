# /account (My Balances): what the live page has, and where the redesign puts it

Read 2026-10-17 from the live page's own code (`/account` HTML and `page-script.e2561648e3d33fa3.js`), not from a logged-in view (the pane was not signed in). "Ours" says what our account shows today; a section hidden for us still gets its redesigned place.

| # | Live part (rule) | Ours | Redesign |
|---|---|---|---|
| 1 | Actions: Deposit (dialog), Withdraw (dialog), Buy ET10 → /exchange-crypto, Buy ETLP → /exchange-crypto-etlp, Swap → /swap, Agent Tournaments → /agent-tournaments | all | header action bar |
| 2 | Live Buying Power: intro, up to 4 chains with capacity > 0 ("<chain> buying power $X"; tooltip: wallet USDC/USDT/native, "limited to your spendable account USDC"), note | Solana $22.70, Ethereum $7.52, Base $0.26 | Balances tab, side card |
| 3 | Positions: "Explain these numbers" switch (Position / Trading balance / Withdrawable now, why withdrawable can be smaller), sync note | yes | Balances tab: explain toggle, sync chip in header |
| 4 | Cash: USDC always; USDT only when not an explicit zero; each with trading-balance / withdrawable / pending-buyer-liquidity note and "Move $X to trading balance" / "Move back to withdrawable" | USDC $22.70, notes hidden (no difference), no move button (0 available) | Balances tab: cash cards with the three numbers and the move buttons |
| 5 | Tokens: ETH and ET10 always; VAIX (native + wVAIX note), SBIO, ETLP ("@ $1.00 issuance"), TBIG, TBIGS, DSCI, DESCI, ORBI only above zero; tUSDC only in paper mode; quantity only, full precision in a tooltip | ETH, ET10, ETLP, TBIG, TBIGS, DSCI, DESCI, ORBI | Balances tab: token tiles |
| 6 | Fund Shares: THF (link /fund-performance) only above zero; AIB Funds from AIB-* holdings; Vault Shares: CYM42 always (link /fund/cymetica-42) | CYM42 0 | Balances tab |
| 7 | Exchange Holdings: holdings except ET10RWD and AIB-*, qty, "≈ $value (NAV / last trade)", trade link, withdraw link | none (only ET10RWD) | Balances tab, hidden when empty |
| 8 | Event Card Positions: "N open · All positions → · Event Cards →"; Card (link /events/id), Side (BULL/BEAR · PAPER), Stake, Value, Unrealized P&L, Status, Opened; Open group, "Showing N of M / Show K more / Show fewer", closed rows behind a toggle | 27 open, 88 closed | Card positions tab |
| 9 | Paper trading banner, paper mode only: Sim USDC, Sim Trades, Sim P&L, Reset Balance (confirm: reset to $1,000), Enable Real Trading | hidden (live) | banner under the header in paper mode |
| 10 | Owed to You, only with obligations: totals per currency, rows (amount, reason, date), note | hidden | Activity tab |
| 11 | Pending Deposits, only with pending: chain + amount, confirmations bar or status; "Deposit not showing? Submit tx hash" → Claim Missing Deposit (7 chains, 0x + 64 hex, Verify & Claim, Cancel) | hidden | Activity tab |
| 12 | Valuation: total, "All Tokens / VSB Only" filter, groups Cash, Tokens, Fund Shares, Vault Shares, Positions (paper ones only in paper mode), Clone Bots; zero rows hidden; "Discovering tokens..." | $20,345.28 | Valuation tab, and its total + split in the top band |
| 13 | AI Agent Microfunds, only with unrefunded entries: Browse all →; Recorded backing, Verified in fund custody, Revenue Received, Active Positions; entries (#id title, status, Backed + verified / not yet verified, Received / cap with a bar), link /feature/id | 1 entry, $12.59 | Earnings tab |
| 14 | Yield Term PILOT, pilot users only: target, risk, subscriptions, amount 50-1000, accept, Subscribe | unknown (pilot list) | Earnings tab, behind the preview switch |
| 15 | ET10 Revenue LIVE: Earned so far $x.xxxxxx, last accrual flash, ET10RWD explanation, Transactions and /earn links | $1.020442 | Earnings tab + top tile |
| 16 | Revenue Share, only when earned / pending / features are not all zero: Claimable, Total Earned, Features, View Dashboard, Claim Rewards (when pending) | hidden | Earnings tab |
| 17 | Token Revenue, only when something: Total Received, ET10 / SBIO / VAIX pending, payouts (Date, Token, Amount, Status, Tx) | hidden | Earnings tab |
| 18 | Reward Delivery: daily / weekly / every two weeks / every 30 days, Save, next delivery, gas note | weekly, next 2026-10-20 | Earnings tab |
| 19 | Telegram notifications: connect (open bot, code, verify), connected as, five kinds, Send test, Disconnect | status not readable with our key | Settings tab |
| 20 | Recent Orders: count; Pair, Side, Type, Price, Qty, Status, Time (last 20) | not readable with our key | Activity tab |
| 21 | API Keys: Bring Your Own Agent · API docs; Name, Key, Trade, Created, Revoke; create (name, allow trading) shows the key once | not readable with our key | Settings tab |
| 22 | My AI agents: your available USDC; Agent, Trust, Agent USDC, amount + Fund agent / Pull back; empty text + link | none; $22.70 available | Settings tab |
| 23 | All Users (Admin), admins only | hidden | unchanged, admins only |
| 24 | Deposit dialog: Send Crypto / Buy with Card; 11 networks; accepted assets; address + copy + chain warning; scan all networks; fees; token, amount picks, wallet balance; MetaMask / Coinbase / WalletConnect; QR; card: Transak / Coinbase, amount picks, fee, you receive | n/a | dialog |
| 25 | Withdraw dialog: 13 assets, available, wVAIX note, amount + MAX, minimum $1.00, destination check, 6 networks (VAIX Ethereum only), fees and you receive, ETA, emailed code, Queued → Bridging → Done | n/a | dialog |
| 26 | Swap dialog: in the page markup (`window.openSwapModal`), but nothing on /account calls it (none of the 22 scripts the page loads does); Actions → Swap is a link to /swap | n/a | Swap stays the link to /swap |

Not on the live page, so not in the redesign: a transactions list (the page only links to Transactions).

`render.py` checks every row above in three preview states (our account, paper mode, every section) and exits non-zero when one goes missing.

## Proposed changes (marked PROPOSED on the page, or the layout itself)

The operator, 2026-10-17: *"pochopitelne muzes navrhnout i upravy pokud uvidis v necem nynejsim nesmysl nebo bug nebo neco co by byl jasny upgrade k lepsimu"*.

1. **One holdings table.** Positions (on-chain boxes, quantity only) and Valuation (ledger table, value and share) list the same assets twice, far apart. Here one table: position from the chain, price, value from the ledger, share; groups with subtotals; the explain switch keeps its three definitions. Valuation's "All Tokens / VSB Only" filter stays.
2. **The tx-hash claim is reachable when it is needed.** Live: "Deposit not showing? Submit tx hash" sits inside the Pending Deposits block, which is hidden when nothing is pending; a deposit that was never detected leaves nothing pending, so the claim form cannot be opened from /account in exactly that case (the Deposit dialog's "Scan all networks" is a different, automatic scan). Here the pending block and its link are always in Activity.
3. **A microfund with no cap** reads "no cap", not "Received $0.00 / $0.00".
4. **Live buying power** gets a Deposit button: its own note says deposit to raise it.
5. **Tabs and a top band** instead of one long page: total value and its split, buying power, open cards, ET10 revenue, microfunds, each a click to its tab. The long explanations move into tooltips; the parts that show only with data keep their rules.
