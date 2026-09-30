# ET-28378, the operator's complaints, checked live 2026-09-30 (running list)

Read-only. Spec = `docs/degen-level-detail/SPEC.md` (spec 4) and its reference screenshots.

| # | Complaint | Holds? | Evidence |
|---|---|---|---|
| 1 | Degen column in the Apps table is one colour | yes | Spec A.1: "green 1-3, light blue 4-6, red 7-10" per segment position, as in the reference screenshot. Live: every filled segment takes the level's band colour (level 6: six light-blue segments; level 7: seven red). |
| 2 | Degen level in the detail is one colour and too narrow | yes | Same rule for the strip (reference: 8/10 = three green, three blue, two red, one dashed). Live CRV: the bar is 216 px inside a 783 px strip, all filled segments light blue. The reference bar runs the full width of the card with "Blue chip" and "Casino" at its ends. |
| 3 | Chart card has no Daily / Weekly switch | no, by spec | The switch is there where a weekly score exists (CRV shows Daily / Weekly buttons). Spec C.3: "only when the coin has a weekly score, otherwise a plain Daily tag". Only about 7 of 214 apps have one. The coin in the screenshot has none. |
| 4 | Copy button next to "Open in Chart Analyzer" | not in the spec | "Open in Chart Analyzer" is a real link with contract, chain and timeframe (CRV: `?contract=0xd533...&chain=ethereum&tf=1d`). Copy comes from the vendor's own change note ("Copy buttons in the detail for what an AI agent needs"). Spec C.3 lists only the link. |

More to come from the operator.
