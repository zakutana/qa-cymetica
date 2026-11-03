# ET-33496 Quant Lab, checked 3 Nov 2026 (script v=6ae928b7), company 14, signed in

| # | Item | Result |
|---|---|---|
| 1 | Blind-test panel keeps the newest blind search after an empty one | PASS: #15 shown with "Search #16 found nothing new" beside it |
| 2 | FAILED counts every failed search, reason in tooltip | PASS: 4 (#5, #7, #9, #14), plain reasons |
| 3 | Search now finishes | PASS: #15 ran 04:13 to 04:43 (30 min, they said 11), no error, 4,752 jobs |
| 4 | Failed run does not count in TRIED | PASS: 6,480 after #14; 11,232 after #15 (tooltip says re-tests count: 125) |
| 5 | First paint shows "Loading", not zeros | PASS: tiles read "…", panel "Loading the lab…" |
| 6 | "Found nothing new" on an immediate second search | PASS: #16 done in 18 s, nothing_new true, label on the page |
| 7 | Run date on every blind-test row | PASS |
| 8 | RUNS list, click replays that run | PASS: 10 runs, clicking #3 loaded its rows, z 4.02, 1,728 tried |
| 9 | Models shortlisted per run, best of each model | PASS: #15 shortlisted StockBot Blue, Hybrid 2 Blue, Helix, Crispr, Prion |

Open question, not a failure: #15 reports 4,752 new combinations and only 125 re-tests, though #10 had already tried the same 4,752; the page adds all 4,752 to TRIED.
