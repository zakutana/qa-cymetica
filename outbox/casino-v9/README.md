# Agent Casino v9 (mock and spec)

Asked for by the operator from 2026-11-05 to 2026-11-07, scored on his eye; final review 2026-11-07 (*"jinak uz mi vse prijde dobre"*), spec prepared 2026-11-08 on his "Yes, prepare it". Filing is his word.

**Open:** `python scripts/serve_mock.py outbox/casino-v9 8843`, then http://127.0.0.1:8843/ (table page: /table.html). The clocks run from the snapshot time (data.js `readAt`, 2026-11-07 16:19 UTC).

**request.txt:** about 6,500 of 8,000 characters, 34 of 40 lines, 6 of 6 pictures (`pictures/`, shot by Playwright from the mock at 1440 px and 390 px).

**Form followed:** ET-33881 (SOURCE folder, MUST STAY AS DRAWN, pictures) with ET-33648's casino voice (goals with the table numbers that show them).

**File:**
```bash
python scripts/bb.py file --app-url https://cymetica.com/agent-casino --improvements-file outbox/casino-v9/request.txt --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/casino-v9/pictures/picture-1-lobby.webp --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/casino-v9/pictures/picture-2-live-now.webp --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/casino-v9/pictures/picture-3-open-and-finished.webp --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/casino-v9/pictures/picture-4-your-agents.webp --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/casino-v9/pictures/picture-5-table.webp --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/casino-v9/pictures/picture-6-phone.webp --confirm
```

| | |
|---|---|
| Ticket | ET-34608 (BB-0045), on the operator's "Yes, file it" |
| Filed | 2026-11-08 20:08 UTC; BB-SPEC back, not accepted. Their spec note: deposits, withdrawals and anything that signs a transaction are out of scope for an automatic build, a BB-CHANGE sends it to a human-reviewed slot (goal 1, the live tables, is that) |
| Accepted, deadline | 2026-11-08 20:13 UTC (BB-0050), deadline 2026-11-09 20:13 UTC; goal 1 in the human-reviewed slot (C1) |
| Shipped | 2026-11-10 07:55 UTC (BB-SHIPPED), 11 h 40 min after the deadline. Check: docs/et-34608-verification.md |
| Verdict | FAIL sent 2026-11-10 on the operator's word (BB-0059, verdict-note.txt); second FAIL after the new build the same day (BB-0065, verdict-note-2.txt, 7 pass, 3 fail, 3 not read); ticket back to funded |
