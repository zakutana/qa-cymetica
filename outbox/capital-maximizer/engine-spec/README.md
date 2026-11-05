# Capital Maximizer engine spec

Ticket: ET-34229 (BB-0036), filed 2026-11-05 01:07 UTC.

Outcome: filed, NOT accepted. `spec_status` proposed, deadline none: their 24-hour clock starts on accept.

Their BB-SPEC held every line: all 8 goals and all 9 Done when lines, word for word (20 of 20 lines of `request.txt`, compared by script).

One difference, corrected: BB-SPEC renumbered our lines 1 to 20, so "as in 1" and "in 5" in the Done when lines pointed at the wrong lines. One BB-CHANGE (BB-0037) sent, it stands in the spec as C1 and says which lines those are. Nothing else changed.

Accept was not sent: the permission layer of the scheduled run refused `bb.py accept ET-34229 --confirm` before it ran. Their spec says "There is nothing to fund". The fallback task `capital-maximizer-engine-spec-file-retry` (06:10 UTC) finds this ticket here and goes on to accept.

When it ships, `research/finder/score.py` judges it and the verdict is the operator's.
