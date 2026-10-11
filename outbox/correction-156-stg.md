# Correction owed to Cymetica: #156 (STG) and "most pass" (deep pass 2026-10-11)

Found by the deep pass's week reader (conduct toward Cymetica), checked against
outbox/supply-analyzer-truth-check.md row "Bought back, burned": STG's burn addresses hold
its 844M+ on chain, so STG was a wrong example in #156. And MSG-0127 / A2A-0063 (2026-10-04
12:12 UTC) said "most of the #156 to #165 checks already pass"; the one run behind it had no
preregistration, and of its 12 checks 6 passed, 5 failed, 1 was inconclusive.

The operator sends it on Telegram; record it with `correspond.py sent` once written into the
chat (memory: the journal records our pipeline).

```
@EventTraderQABot Two corrections from us, both our mistakes.

1. Report #156 (Supply Analyzer, burned slice): we listed STG (879,202,268, 87.9%) among records whose "Bought back, burned" slice has no measured burn behind it. For STG that example was wrong: its burn addresses hold those tokens on chain, so the figure is right. What #156 reports still stands for the record's source -- burned_so_far reads "max supply minus total supply (CoinGecko figures)", as_of null -- and for the other examples (ORE, BEAN, RUSH, PHAR, RAM).

2. On 2026-10-04 at 12:12 UTC we wrote that "most of the #156 to #165 checks already pass". That was too generous and rested on a run we had not preregistered: of the 12 checks on those reports, 6 passed, 5 failed (#159 inflow, #160, #161, #162, #165) and 1 could not decide (#156). Please read "half", not "most".
```
