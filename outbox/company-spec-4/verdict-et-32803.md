# ET-32803 (Build a Company, round 4), what goes out (2026-10-26)

Verdict recommended: **Fail**, for three things; everything else checked passes. Read live on 2026-10-26 (08:11 to 09:00 UTC) in the owner's signed-in
browser, nothing changed (no Resume, no Save), plus `GET` reads with our key. Nexus's three progress posts: REPLY-0218, 0219, 0220.

## What was checked

- A units: Headquarters "0.00 of 5 in the 5-hour window", Tasks has a Units column ("not measured" or "0.76 u"). Pass.
- A3, N, J: Products tab = tiles (initials, name, "no line in the Universe yet", people, revenue brought "—"), 10 products, 644 people, new users and
  revenue "not measured yet" (as Nexus said). Pass. The line editor and the logo upload were not clicked.
- F: each department row has its own switch ("Resume Cymetica QA" and so on), Command has none, rows say "Paused: the company is paused". Pass (the
  switch itself was not pressed).
- I: the paused company's station is steel and unlit on the map. Pass. The washed-colour fix: Nexus itself says it cannot confirm it.
- L: MADE BY BJ IRONSTAR CAPITAL on the Airdrop Farmer panel, MADE BY · CYMETICA on the Promo Market panel. Pass.
- P: orbits are lanes of dust, plates only for Cymetica, ours and the products, and the entry page has the same lanes. Pass.
- Q: the Promo airship circles the Promo Market cube. Pass (its banner is thin from the first look).
- H: board in the Universe, display only, three open places ("pays 5% · takes $10,000 in 30 days", "All 3 slots are open. Be the first.", "Who gets
  a slot"). Pass as a sketch. Not checked: the pulse, the full leaderboard.
- O: a "Quality: high" button on the Universe. No frame-rate numbers (Nexus says so). Not checked.
- E: paused chip "paused · 0/40 turns" and the window in units. The running / waiting / next-pass states cannot be checked while the company is paused
  and we did not resume it.

## What fails

1. **K, the Airdrop Farmer building is not the mockup's.** Live: a straw hat with a sprout on a green drum with rope bands on a dark octagonal base, one
   amber light, no face. Mockup (item K): a round head of green woven willow with two glowing warm white eyes, a ring of small amber lights in wooden
   collars, walnut pegs, the straw hat with a lime-and-gold sprout. (Round 3 failed for the same kind of thing.)
2. **M, ten of the seventeen pictures in the Settings skin row are broken images.** `/static/company/shots/station-armillary-gold.webp` and nine more
   (`helix`, `sail`, `array`, `arcology`, `pylon`, `rift`, `tesseract`, `nautilus`, `vortex`) answer 404; the seven old ones answer 200. The row is also
   pictures, not the line icons of item M.
3. **C, the Supervisor is much narrower than asked.** Only cancelling exact duplicate tasks (Nexus says so). The engine layer that learns from every
   company's chats is not mentioned, and the company layer (a review of processes, charters and setup, with safe changes listed and undoable, and what
   changes a department left as an approval) is not there; the Audit tab shows the weekly audit with "0 tips last week" and no list of changes.

## Note for the verdict

```
Fail on three points; the rest of round 4 passes (read live on 26 Oct, signed in, nothing changed).
1. K: the Airdrop Farmer building is not the mockup's. Live: a straw hat with a sprout on a green drum with rope bands on a dark octagonal base, one amber light, no face. The mockup: a round head of green woven willow with two glowing warm white eyes, a ring of small amber lights in wooden collars, walnut pegs, the straw hat with a lime-and-gold sprout. Code: outbox/company-live/u3d.js, adFarmer, in the pinned mockup.
2. M: in Settings, ten of the seventeen station pictures are broken images: /static/company/shots/station-armillary-gold.webp, -helix-, -sail-, -array-, -arcology-, -pylon-, -rift-, -tesseract-, -nautilus-, -vortex- answer 404 (the seven old ones answer 200). Item M also asks for one row of line icons that never take the colour, not pictures.
3. C: the Supervisor only cancels exact duplicate tasks. Item C asks for the engine layer that learns from every company's chats, and a company layer in the Audit tab that reviews processes, charters and setup, applies safe changes with a one-click undo and leaves what changes a department as an approval. The Audit tab shows no list of changes.
Not checked, and not part of this verdict: the per-department switch itself, the running and next-pass states of the countdown, the pulse on the revenue board, the full leaderboard, the logo upload and the line editor.
```

## Telegram

```
@EventTraderQABot ET-32803 (Build a Company round 4): thank you for the three updates. We checked the live site signed in, changing nothing, and gave the verdict FAIL on three points; the rest passes (units, Products tiles, the per-department switches, the dark paused station, MADE BY plates, dust lanes and plates, the Promo airship, the revenue board as a display, the Quality button). Please fix:

1. K: the Airdrop Farmer building is not the mockup's (a hat on a green drum with no face; the mockup is a round willow head with two glowing eyes, a ring of amber lights, walnut pegs and the straw hat). Code: outbox/company-live/u3d.js, adFarmer.
2. M: in Settings ten of the seventeen station pictures are broken images (/static/company/shots/station-armillary-gold.webp and nine more answer 404). Item M also asks for one row of line icons that never take the colour.
3. C: the Supervisor only cancels exact duplicate tasks. Item C asks for the engine layer and a company layer in the Audit tab (processes, charters, setup, safe changes with one-click undo, department changes left as an approval). If you consider the narrower version final, please say so plainly.

We could not check the running and next-pass states of the countdown, the pulse, or the logo upload and the line editor, because they need the company to run or a save. Please tell us if you want us to resume the company for a test.
```
