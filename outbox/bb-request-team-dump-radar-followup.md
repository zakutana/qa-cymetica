# Build it Better: Team Dump Radar follow-up (draft, not sent)

Operator's asks of 2026-09-29 (logos, a one-time user-entered team-address check that is never
stored, more exchanges) plus the QA additions. Send after the ET-28203 verdict. ET-28203 is shipped, so
the app has no open request and the form accepts a follow-up. Needs the operator's Build it Better key.

```
@EventTraderQABot Team Dump Radar (ET-28203) follow-up request, one build, each line its own check:
1. Logos: show each coin's logo on the tiles, the detail screen and the share card, with the coloured initial badge as the fallback when a logo is missing.
2. One-time check for coins without known team wallets: on a grey coin's detail screen the visitor can paste team wallet addresses and get a one-time result (what those wallets sent to exchanges in the window, with the Proof links). Nothing the visitor enters is stored, and it never changes the coin's light or the grid. The result carries the label "Based on addresses you entered, not verified as the team", it has no share card, and it says "sent to exchange", never "dumping". Rate limited.
3. More exchanges: count a deposit address as an exchange when it sweeps into a tagged exchange hot wallet, and use more label sources than Etherscan's public tags, so that exchanges such as Bithumb are found. Every exchange figure says "at least", with the untagged share shown next to it (the COTI fact line today reads "153M COTI sent to exchanges in 13d" with no "at least").
4. Coverage in plain sight: the header says "6 of 500 coins verified" (the real count), and the "does not do" list says why the others are grey (not on Ethereum, no team wallets we can prove, stablecoin or wrapped).
5. More chains than Ethereum: 286 of the top 500 are grey only because they are not on Ethereum.
6. Optional: for grey coins, a separate low-confidence marker from public signals that need no team identification (a top holder sending to an exchange, an unlock within 30 days, a new mint). Worded "large holder", never "team", and never a red or green light.
```

Why the wording of line 2: a visitor-entered list can name any wallets, so a result built from it must
never look like the official light or be shareable as one (spec trust rules 19 and 20).
