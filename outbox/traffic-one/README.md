# One Traffic page (mock)

**For Cymetica:** the request is [request.txt](request.txt); every figure behind it is in [FINDINGS.md](FINDINGS.md); the pictures are in [pictures/](pictures/). The page is your own /traffic with `<main>` replaced: your styles (`theirs.css`, `theirs-mine.css`), your Chart.js settings, your API responses (`snapshot/`, read 2026-11-06 09:26 UTC). Every number in it is from your APIs; nothing is invented.

Asked for by the operator on 2026-11-06: *"z toho vseho udelame 1 stranku. bude tam simple a advanced view. nesmis opominout zadne data ktera tam maji ted"*. Basic approved the same day.

**Open:** `python scripts/serve_mock.py outbox/traffic-one 8844`, then http://127.0.0.1:8844/ (`?view=advanced` opens Advanced). Rebuild with `python outbox/traffic-one/build.py` (`--snap` re-reads your APIs first).

- **Basic** (picture 1): the six tiles and Visitors over time, Volume generated, Apps, and Your traffic (Page views per day, People per day by page, Your apps).
- **Advanced** (picture 2): everything else from /traffic, /traffic/mine and /app-usage.
- **Range switch** (picture 3): every range is in memory, the chip answers at once, a panel still waiting says Loading. Measured 23-56 ms here.
- **Tooltips** (picture 4) on every tile and column head.

**request.txt:** see the numbers after `bb.py` checks it.

| | |
|---|---|
| Ticket | ET-34607, filed 2026-11-08 19:54 UTC (BB-0043), spec accepted 2026-11-08 19:55 UTC (BB-0044), deadline 2026-11-09 19:55 UTC |
| Filed | |
| Accepted, deadline | |
| Shipped | |
| Verdict | |
