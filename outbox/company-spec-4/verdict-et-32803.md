# ET-32803 (Build a Company, round 4), what goes out (2026-10-26)

Verdict recommended: **Fail**, because the look of the mockup is binding (line 2 of the request) and the build drew its own look in seven places.
Read live on 2026-10-26 (08:11 to 09:30 UTC): my own reads in the owner's signed-in browser (nothing changed) and the owner's screenshots from
his own screen with a graphics card (mine has none, so my first read of the 3D was too generous: it passed P and H, and it was wrong). Nexus's
three progress posts: REPLY-0218, 0219, 0220.

## What passes

- A units: Headquarters "0.00 of 5 in the 5-hour window", Tasks has a Units column ("not measured" or "0.76 u").
- A3, N, J: Products tiles with logo or initials, name, Universe line, people, a 30-day line; a side panel with people per day, "Upload a logo" and the
  70-character "In the Universe" line with Save; revenue brought, new users and visit sources say "not measured yet", as Nexus said.
- L: MADE BY BJ IRONSTAR CAPITAL, and MADE BY · CYMETICA on Cymetica's buildings.
- Q: the Promo airship circles the Promo Market cube. I: the paused company's station is steel and unlit.
- Quality is not in the spec as a button; E and the countdown could not be checked while the company is paused (not resumed).

## What fails

1. **K, the Airdrop Farmer building is not the mockup's.** Live: a straw hat with a sprout on a green drum with rope bands on a dark octagonal base,
   one amber light, no face. Mockup: a round head of green woven willow with two glowing warm white eyes, a ring of small amber lights in wooden
   collars, walnut pegs, the straw hat with a lime-and-gold sprout.
2. **M, the ten new skins.** (a) In Settings ten of the seventeen pictures are broken images: `/static/company/shots/station-armillary-gold.webp` and nine
   more answer 404, the seven old ones 200. (b) The ten are not the mockup's: the live site has no `stations-a.js` to `stations-e.js` (404); its own
   `stations.js` (46 KB for all seventeen, against 38 KB for the seven plus 125 KB for the ten in the mockup) draws ten ships under the same names,
   and the owner sees different ships. (c) The row is pictures, not the line icons of item M.
3. **F, the department switch.** The new switch overlaps the row's badge ("0 ET10"), and switching a department does not light or darken its room: only the
   text on its wall changes. The spec says its lamp, neon and floor light go out and the name is dimmed.
4. **P, the orbits and the sky.** The map still has the broad soft glowing ring lines; the mockup draws no line at all, only lanes of dust. The sky and its colours
   differ from the drawing too. The entry page (`/company/app/start`) has the same fault: two screenshots from the owner's screen show thin dotted lanes of dust in
   the mockup and broad soft glowing bands in the build.
5. **H, the revenue-share board.** A small flat panel with "Open" rows, and a text that expands, not the big frosted-glass board turned away like a
   cockpit panel with big place numerals; it stands elsewhere than drawn. (Display only is fine, as Nexus said.)
6. **C, the Supervisor** only cancels exact duplicate tasks. Item C asks for the engine layer that learns from every company's chats in the background, and a
   company layer in the Audit tab that reviews processes, charters and setup with safe changes listed and undoable. The Audit tab shows 0 tips and no list.
7. **O, the "Quality: high / low" button sits on the Universe.** It belongs in Settings, if it is offered at all; nobody asked for a button on the map.

## Note for the verdict

```
FAIL. We asked for the look exactly as in our mockup (line 2 of the request: "The look of the mockup is binding"). In seven places the build shows a look of its own. We want the exact look as we drew it, not an interpretation and not an improvement. Where your backend cannot do something, change the design as little as it takes and name the change (BB-CHANGE), but do not redesign.
Everything you need is available at the pinned commit, nothing is missing. The whole mockup folder with the code and the pictures (index.html, start.html, u3d.js, stations.js, stations-a.js to stations-e.js, uvboard.js, uvpanel.css, look-universe.webp, look-office.webp): https://github.com/zakutana/qa-cymetica/tree/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-live . Open it as a page: https://rawcdn.githack.com/zakutana/qa-cymetica/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-live/index.html (the entry page: .../company-live/start.html). The ten station skins with their build spec: https://github.com/zakutana/qa-cymetica/tree/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-skins . The brief: https://github.com/zakutana/qa-cymetica/blob/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-spec-4/SPEC.md
What differs (read live on 26 Oct, plus the owner's screenshots):
1. K: the Airdrop Farmer building. Live: a straw hat with a sprout on a green drum with rope bands on a dark octagonal base, one amber light, no face. Mockup: a round head of green woven willow, two glowing warm white eyes, a ring of small amber lights in wooden collars, walnut pegs, the straw hat with a lime-and-gold sprout (outbox/company-live/u3d.js, adFarmer).
2. M: in Settings ten of the seventeen station pictures are broken images (/static/company/shots/station-armillary-gold.webp and nine more answer 404); the ten ships are not the mockup's (the live site has no stations-a.js to stations-e.js, its own stations.js draws ten different ships under the same names); the row is pictures, not line icons.
3. F: the department switch overlaps the row's badge, and switching a department does not light or darken its room, only the text on its wall changes (spec: lamp, neon and floor light out, name dimmed).
4. P: the map and the entry page (/company/app/start) still have broad soft glowing ring lines (the mockup has none, only thin lanes of dust), and the sky differs.
5. H: the revenue board is a small flat panel with "Open" rows, not the big frosted-glass board with large place numerals, and it stands elsewhere than drawn.
6. C: the Supervisor only cancels exact duplicate tasks; the engine layer (learning from every company's chats) and the company layer in the Audit tab (processes, charters, setup, safe changes with undo) are missing.
7. O: a "Quality: high / low" button sits on the Universe map; it belongs in Settings, if offered at all.
Passes: A units, Products tiles with panel, logo upload and Universe line (N, J), MADE BY plates (L), the Promo airship (Q), the dark paused station (I). Not checked: the countdown while running, the revenue board's pulse, the leaderboard.
```

## Telegram

```
@EventTraderQABot ET-32803 (Build a Company round 4): thank you for the three updates. We checked the live site and gave the verdict FAIL. We want the look exactly as we drew it in the mockup (line 2 of the request: the look of the mockup is binding), not an interpretation and not an improvement. In seven places the build shows a look of its own. Where your backend cannot do something, change the design as little as it takes and tell us, but please do not redesign.

All the material is available, nothing is missing: the whole mockup folder with the code and the pictures (index.html, start.html, u3d.js, stations.js, stations-a.js to stations-e.js, uvboard.js, uvpanel.css, look-universe.webp, look-office.webp): https://github.com/zakutana/qa-cymetica/tree/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-live ; the ten station skins and their build spec: https://github.com/zakutana/qa-cymetica/tree/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-skins ; the brief: https://github.com/zakutana/qa-cymetica/blob/a19d80ba3545a093f7cb434f46aea23776343004/outbox/company-spec-4/SPEC.md . If anything does not open or looks incomplete on your side, tell us and we will send it another way.

What differs:

1. K: the Airdrop Farmer building is a hat on a green drum with no face; the mockup is a round willow head with two glowing eyes, a ring of amber lights, walnut pegs and the straw hat (outbox/company-live/u3d.js, adFarmer).
2. M: ten of the seventeen station pictures in Settings are broken images (/static/company/shots/station-armillary-gold.webp and nine more answer 404), and the ten ships are not ours: please use the mockup's code (stations-a.js to stations-e.js in outbox/company-live) as the request says. The row should be line icons.
3. F: the department switch overlaps the row's badge, and switching does not light or darken the room, only the text on its wall changes.
4. P: the map and the entry page (/company/app/start) still have broad soft glowing ring lines; the mockup has none, only thin lanes of dust. The sky differs too.
5. H: the revenue board should be the big frosted-glass board from the mockup, standing where it is drawn, not a small flat panel.
6. C: only duplicate tasks are cancelled. Item C asks for the engine layer and the company layer in the Audit tab. If the narrower version is final, please say so plainly.
7. O: the "Quality" button belongs in Settings, not on the Universe map.

Passing: units, Products tiles with panel and logo upload, the Universe line, MADE BY plates, the Promo airship, the dark paused station. We could not check the countdown while running or the board's pulse.

Please rebuild the seven points to the mockup and tell us when they are live; we will check them again the same way.
```
