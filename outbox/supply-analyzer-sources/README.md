# Supply Analyzer: schedules beyond DeFiLlama, and the Supply column

Asked for by the operator on 2026-11-02, in their words: *"podej to jako spec na vylepseni supply analyzera a zatim tam dopis at upravi to zobrazeni v tom sloupci v gem screeneru"* (spelling tidied).

**Open:** `python outbox/supply-analyzer-sources/serve.py`, then http://127.0.0.1:8804/gem-screener/app and http://127.0.0.1:8804/supply-analyzer?symbol=collector-crypt. Their live pages through a GET-only proxy, with `patch.js` and `patch_page.js` inside their scripts and `data.json` (from `build_data.py`) laid on their Supply records, so the columns, card, page and gate read it. The Supply Analyzer page's month chart is not redrawn: it says what the build will do.

`render.py` redraws the three pictures from the running copy.

**request.txt:** 5,227 of 8,000 characters, 28 of 40 lines, 3 of 6 pictures. Followed form: ET-31267, whose line "DeFiLlama only for the future unlock schedule" this replaces.

| | |
|---|---|
| Ticket | not filed: 2026-11-02 14:32 UTC refused, HTTP 429 USAGE_LIMIT, session build limit, resets 18:11 UTC |
| Filed | |
| Accepted, deadline | |
| Shipped | |
| Verdict | |
