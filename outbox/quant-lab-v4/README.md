# Quant Lab v4 (mock: left menu, four tabs)

Asked for by the operator on 2026-11-13: a left menu as in the Promo Market; a tab for what the combinations are made of (read about each), Runs with the reactor and clicking back through every run (the old WINNERS text was "humus"), Bots found in any run that open the run they came from, the BLIND stage without its visual bug, a tab for the search running now. Top design, degen friendly: the important figures, as little reading as possible.

**Open:** `python outbox/quant-lab-v4/serve.py`, then http://127.0.0.1:8811/company/app/experiments

- `freeze.py`: company 14's lab as of 2026-11-13 (owner key, GET only), every run's own blind-test rows (the page's read stops at the newest 200, so #19's four winners were out of reach), `/api/v1/skills`, `/api/v1/cloned-bots/available`, their live `quant-lab.js` and `.css`.
- `build.py`: their script with the v4 hooks; BLIND for a profile run (`blind.js`), THE BAR capped to the winners and nearest misses, FOUND names cut before the result; `data/ingredients.json`.
- `index.html`, `v4.css`, `v4.js`: the shell. The rail is their Promo Market `.rail`, rule for rule.

Descriptions in Ingredients come only from their data: skills from `/api/v1/skills` (eli5, example); HELIX from MACD Hunter's live decision source; the other models from the lab's own two variants of each entry rule (stricter, looser) and, for the three with a paper bot, that bot's buy and sell rule; combos from their parts and the rule text (any 2 of 3 agree); Flash signals from their own labels. MITOSIS and TELOMERE have no published rule.

Nothing is sent: every method but GET answers "This is a mock". Live search shows the idle state as it is; "preview a running search" draws a running one from the last run's numbers, marked PREVIEW.

Request: `request.txt` (4,965 of 8,000 characters, 21 of 40 lines), six pictures in `pictures/` (`pictures.py`, 1440 wide). The ingredient texts are theirs to review and write, on the operator's word: *"ty vsechny ingredients at si sami udelaji review"*.

| | |
|---|---|
| Ticket | ET-35147 (BB-0076), filed 2026-11-13 07:19 UTC on the operator's word ("podej spec") |
| Accepted, deadline | 2026-11-13 07:20 UTC (BB-0077), 2026-11-14 07:20 UTC |
| Shipped | |
| Verdict | |
