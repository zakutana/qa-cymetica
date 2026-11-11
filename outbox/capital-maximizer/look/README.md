# Capital Maximizer: the look of the top 3 cards and the Leverage route

**For Cymetica.** This folder is your live `/capital-maximizer` page with our look on top. Every figure in it is your engine's
(read from your API when the page opens); only the drawing changed. Build the look exactly as these files draw it.

| File | What it is |
|---|---|
| `patch.css` | Every style of the new cards, the chips, Details, the Leverage route band, the phone layout. Your tokens only (cyan, green, red). |
| `patch.js` | Replaces your `card()` and `renderLev()`, and `notesHtml()` for the Plan screen; adds `lkChips()` (the chips), `lkDetails()` (the fold), `lkFit()` (one scale for the three trees). It runs inside your script, just before `boot(0)`, and uses your own helpers (`tree`, `stepsHtml`, `esc`, `usd`, `signed`, `pct`). |
| `serve.py` | The copy: it serves your page and passes every GET to cymetica.com. It also makes **six edits to your `capital-maximizer.js?v=20261110-2`**, listed in `EDITS` at its top: the borrow node of a levered pool gets its own row and the edge from the pool goes through the diamond (bug #345); the apex sits under the borrow; a plate can be 214 wide (was 150); a vault name keeps 30 letters without its date (was cut at 22); a stake step with no rate shows no rate (bug #344, "+NaN%"); the leverage diamond is 36 wide so "4.25x" sits inside it. |
| `pictures/` | Shot from the copy at 1440 px and 390 px on 11 Nov 2026. |

The figures in the pictures are a snapshot of 11 Nov. "LIQUIDATED AT ETH down 1.3%" and the red mark on the −20 % to +20 %
scale show your current value, which is wrong (bug #343): they take the fixed value.

Filed 2026-11-11 09:50 UTC as **ET-34914** (`request.txt`, BB-0071), the numbering correction as BB-CHANGE C1 (`change-c1.txt`, BB-0072), accepted on the operator's word (BB-0073).

Run it: `python outbox/capital-maximizer/look/serve.py`, then open http://127.0.0.1:8848/capital-maximizer?tier=og
(`?tier=` is only the copy's shortcut to a tier's top 3; it is not part of the request). Nothing is sent from the copy:
every method but GET is refused, and the live stream is left out.
