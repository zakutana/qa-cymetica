# Cymetica Quest (request)

Asked for by the operator on 2026-11-03: *"ok vse pushni a priprav spec"*, then, in the same hour, *"a dopis tam at udelaji i verzi pro agenty v pozadi, takove to llms.txt ... at to navnadi i prichozi agenty"* (goals 11 and 12).

The page is our mock `outbox/quest-steps` (http://127.0.0.1:8800/ from the `quest-steps 8800` terminal), 16 takes, the pictures are shot from it. The form follows ET-33759 (Gem Screener, 2026-11-02, accepted and shipped, verdict pass): a plain first line, Why, MUST STAY AS DRAWN, numbered goals that name their picture, Done when with `[ ]` lines, the pictures as design URLs.

**request.txt:** 5,824 of 8,000 characters, 27 of 40 lines, 5 of 6 pictures. Its SOURCE line hands over the whole finished page (`outbox/quest-steps`, with HANDOVER.md, the six clips and llms.txt); the operator, 2026-11-03: *"to je finalni edice"*. Nothing of it reaches them until it is pushed.

| Picture | Shows |
|---|---|
| 1 | the first screen at 1920 px: headline, keys, Monthly prizes, the bar |
| 2 | steps 1 and 2 stacked |
| 3 | steps 3 and 4 stacked |
| 4 | step 5 and the two doors stacked (the board is an example and stays as drawn; so are the prizes: no live data in the page, the operator 2026-11-03) |
| 5 | the phone, first screen and step 2 side by side |

Figures in the request were read on 2026-11-03: GET /api/v1/company/season (prizes_et10 [50000, 30000, 10000], qualify_points 100, what_counts), /quest answers 404, /llms.txt and /.well-known/agent.json answer 200, the builder gate's "Pro plan or higher" and the ET10 fee read from their builder.js.

File it (the operator's word):

```
python scripts/bb.py file --app-url https://cymetica.com/quest --app-name "Cymetica Quest" --improvements-file outbox/quest-request/request.txt --design-url https://raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/quest-request/pictures/picture-1-first-screen.webp --design-url .../picture-2-steps-1-2.webp --design-url .../picture-3-steps-3-4.webp --design-url .../picture-4-step-5-and-doors.webp --design-url .../picture-5-phone.webp --confirm
```

(the dots stand for the same raw.githubusercontent.com/zakutana/qa-cymetica/main/outbox/quest-request/pictures/ prefix). Never move or rename this folder after it is filed: the request points at these raw URLs.

| | |
|---|---|
| Ticket | ET-xxxxx (not filed yet) |
| Filed | |
| Accepted, deadline | |
| Shipped | |
| Verdict | |
