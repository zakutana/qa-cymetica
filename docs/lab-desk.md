# Desk — how money is made on Cymetica

Section 7 of the laboratory. One goal, the operator's (2026-10-11, laborator skill, "Seven sections"): **prove that money can be made on Cymetica** -- if it can, the platform succeeds. The route is ours to choose. A desk step is one Opus agent (`.claude/agents/desk.md`) woken by the tick (`decide: desk`); it reads this file, does ONE thing, and updates this file.

## Rules

- Paper only. Real money is only ever a proposal to the operator, after two windows that earned.
- Our own Build it Better requests and feature requests are filed by the desk itself (`scripts/bb.py`, operator 2026-10-11: "ty muzes sam klidne build it better podavat i ty featury"). A question to Cymetica is a draft the operator sends (CLAUDE.md, "Nové oddělení"; deep pass 2026-10-11), never an a2a of ours; a finding goes through `submit.py`, never prose.
- Before starting anything, read `python scripts/lab.py brief` (what each section tried and knows) and this file: nothing tried is tried again without a stated change.
- A card of the desk's choosing: `python scripts/lab.py desk-card <uuid> --hold <days> --why "..."` (no backtest gate: the desk's judgement is the experiment).
- After a verdict on a desk room: a lesson, `python scripts/lab.py log --lesson --section desk "..."`.
- The outsider's looks are input: `python scripts/outsider.py report` shows what a stranger scored low and why. A surface a stranger would not put money into is a feature or Build it Better request worth filing -- what would make it say yes.
- Only a number about what `desk-card` buys -- the card's own index -- is evidence for a card trade. A Hot basket's hotidx is not the card (2026-10-12, H1).
- Costs: a paper card fill pays nothing (REPLY-0136). Live, the fee is theirs and documented: 0.20 % taker a fill, maker 0, set per card pair (llms.txt Fees, capture 24206e4d, 2026-10-12; REPLY-0047), so 0.4 % a round trip. The slippage is unmeasured: REPLY-0047 gives the fee "before slippage" and no number for it, and the 0.5 % a side in the old 1.4 % is their backtest toggle's stress figure (2 % + 0.5 % a side), never a fill anyone saw. Until a read of what a live buy fills at exists (Next 4), the bar for real money stays 1.4 % a trade, on purpose: money proposed under too low a bar is lost, a hypothesis held back by too high a one waits. Refuted means at or below the fees, 0.4 %; between 0.4 and 1.4 % an edge is undecided on slippage, not failed.
- A worker may not edit `scripts/`, `qa/` or `tests/meta/` (qa/crew.py, `_PROTECTED_FILES`): code the desk needs is a `decision` ticket to the manager, never a workaround.
- A desk room holds its card for the lab too: his room on that card is refused while ours runs and for 30 days after our verdict (`qa/lab_register.py::last_judged`, any section). Beside a room of his means after it, never before.

## From the outsider

(its low scores and their whys land here after each look)

## Hypotheses

| Id | Hypothesis | Test | Status | Result |
|---|---|---|---|---|
| H1 | Crypto cards that just entered Hot keep rising: +3.9 % a day later against +1.4 % for crypto not in Hot (65 vs 482 baskets, Hot reading 2026-10-11 08:09) | the crypto cards' own day after a Hot entry, from the diary's 197 crypto card histories; above 1.4 %, each new crypto entry bought with `--hold 1`, ten before a verdict; at or below 0.4 % (the fees alone), refuted; between, it waits for the slippage read (Costs) | blocked on code (T-0006), 2026-10-12 | The +3.9 % is the basket's hotidx; the card is what we buy. Cards' own day after a Hot entry: -0.04 % over 725, about 197 of them crypto. For crypto cards to have done +3.88 %, stock cards would have lost 1.5 % a day while stock baskets gained 0.4-1 %. The basket's +24 h was seen for only 65 of 401 crypto entries. No room opened. |
| H2 | His picks, our exit: Nexus's cards sold after 18 h made +1.38 % on average (70 % in profit, 33 cards) against -0.52 % at his own holds | the bull cards he names, bought by the desk with `--hold 1` within the hour of his answer (after his room when the lab opens one); the floor is 1 day, so 24 h, not 18; ten before a verdict. First its premise at our exit (T-0030), decided here before the read: the same rooms at 24 h against their benchmark, the BTC proxy -- at or above 1.4 % and above it, on to ten; at or below 0.4 %, or not above it, no more 1-day buys, and an 18 h exit is asked for only if 18 h clears both (`HOLD_DAYS_RANGE`, the operator's veto); between and above it, on, undecided on slippage; under 20 rooms read at 24 h, undecided | running, 2 of 10 (STR-0212, STR-0213); premise read asked (T-0030), 2026-10-12 | The +1.38 % is gross: the 18 h figure has carried no cost since 2026-10-08 (lab_page.py, `CARD_ROUND_TRIP_PCT` 0). It clears the documented 0.4 % fees by about 1 point and is undecided on slippage (Costs), not on a line. NEX-0138 (16:54 UTC) named 3. ce0c9e32 he called bear for 18 h: desk-card buys bull only, and STR-0191 holds it bull since 10-10, so skipped. e22876b3 (AI Data-Center stocks) and 2a6f5562 (SAIB SPCX) the lab left unopened, his holds being under a day (about 6 h; to the next open), so no pair: the desk bought both at 17:27 UTC, 570.95 USDC each (TRD-0116, TRD-0117). Both trade US hours only; the 1-day exit carries the overnight gap he warned against. Nobody has read the 33 at 24 h, our exit, or against the market on the same days: a +1.38 % in days the BTC proxy rose as much is drift, not his picks (T-0030). |
| H3 | Exact puzzles of the Agent League pay 1,000 ET10 each with no market risk | count what `GET /api/v1/agent-league/prizes` credits for LGE-0022..0025 once they resolve | refuted as written, 2026-10-12 | 8,000 ET10 credited to us, not 26,000: 10 prize records, 8 credited (10-09 16:29 to 10-10 15:05), 2 capped (T-0027, Bugs' read of `/agent-league/prizes` through our client, 18:40 UTC). A puzzle pays its one best answer (exactness at least 0.9), and the League's 50,000 ET10 a month was full by 2026-10-11 07:30: every record since is `capped`, `credited_at` null. One other agent holds 28 of the 36 credited. A race under a cap, not risk-free money. The "0 ET10 credited" before was our own read seeing the newest 50 of 90 records (a69917e9). An ET10's dollar worth and whether it can be withdrawn: unread. The ceiling for us is a share of 50,000 ET10 a month, if the cap resets. Parked (Next 5). |
| H4 | An app that tells an agent the moment a card enters Hot would make H1 tradeable for everyone | a Build it Better request for it, filed by the desk, once H1 has ten trades | waiting on H1 -- an alert helps only if the card moves with its basket | -- |

## Running

| Room | Card | Hold | Stake | Opened | For |
|---|---|---|---|---|---|
| STR-0212 | e22876b3 AI Data-Center & Compute Buildout | 1 d, bull | 570.95 USDC (TRD-0116) | 2026-10-12 17:27 UTC | H2 |
| STR-0213 | 2a6f5562 SAIB: SPCX (SpaceX) | 1 d, bull | 570.95 USDC (TRD-0117) | 2026-10-12 17:28 UTC | H2 |

## Next

1. H2: the verdicts of STR-0212 and STR-0213 (due from 2026-10-13 17:28 UTC), a lesson each; then every Nexus answer naming bull cards, bought with `--hold 1` within the hour.
2. H2's premise: when T-0030's read lands, apply the rule in H2's Test, written before the read; until then H2 goes on as it is.
3. H1: when `hot_watch.py report` prints the card line per class (T-0006), decide off the crypto card's own +24 h: above 1.4 %, buy each new crypto entry's card with `--hold 1`; at or below 0.4 %, H1 is refuted and H4 goes with it; between, it waits on 4.
4. Slippage, the one unmeasured part of the live cost: what a live buy of a desk stake (570.95 USDC) would fill at, placing nothing -- code, asked of the manager (T-0022): the card's book, else each leg's market-order preview. If their API has neither, a feature request for a card-buy preview, filed only after a card payload and the `/buy` answer have been read and carry no quote; a question to Cymetica last.
5. H3, parked: reopened only when two things are read -- what `capped` means (lost, or paid when the cap resets: T-0027's draft, the manager's to carry) and what an ET10 is worth (`GET /api/v1/features/bidding/rules` carries `et10_price_usd`, public; no desk tool reads it).

## Sent to Cymetica

(none sent. T-0015's draft on the League's prize rule went to no one: the manager found the terms in the prizes body itself, and Bugs read them, T-0027.)
