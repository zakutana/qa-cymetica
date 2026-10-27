# The Cymetica Quest guide (cymetica.com/quest): our mock

The page the revenue-share flyer sends people to (*THE CYMETICA QUEST GUIDE · START HERE cymetica.com/quest*). Asked
for by the operator on 2026-10-27: a cinematic scroll film in the manner of robinwifhoodcoin.com, opening on the
flyer's picture, four steps, a glass rail that always says which step you are on, as little reading as possible.
Cymetica builds the real page; this folder is the mock it is built from, then a SPEC and a Build it Better request.
The approved plan: `~/.claude/plans/zazzy-swimming-gizmo.md`.

## Open it

`python -m http.server 8797 --bind 127.0.0.1 --directory outbox/quest` (the `quest` entry in `.claude/launch.json`),
then http://127.0.0.1:8797/. Desktop first: the operator set the phone aside on 2026-10-27 ("na mobil zatim kasli");
on a phone the page works but shows deep space under the text, since only the desktop film is rendered.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure, address and what plays under each chapter |
| `render.py` | the film from the /company mock's own 3D Universe (needs `company-mock` on :8793 and Chrome with a GPU); `keys`, `film`, `office`, `gen` |
| `shots.py` | pictures of every chapter at 2000 px and 390 px, and a CPU-throttled scroll timing |
| `tests/test_quest.py` | the rail, the word budget, type size, the palette, one source for every figure (`python -m pytest outbox/quest/tests -o addopts="" -p no:cacheprovider`) |
| `ANTIGRAVITY.md` | the brief for Antigravity (Gemini): the interiors (Quant Lab with the Hero Agent first, then Development, Agent Casino, Promo Market) into `gen/` only |
| `frames/`, `stills/`, `gen/`, `shots/` | made here, never in git |

## Where it stands

- Page, rail, scroll engine and tests: done.
- The space film (hero to the sun and our station, the Agent Casino, the Promo Market, the pull back): rendered from
  the mock, desktop.
- Interiors: placeholders from the mock's 3D office until Antigravity's pictures come. The operator starts it with
  "do what outbox/quest/ANTIGRAVITY.md says"; it makes the Quant Lab picture first and stops; Claude puts it in
  (`render.py gen`), judges it beside its neighbours, then Antigravity makes the rest.
- Then: SPEC.md and build-it-better/request.txt for Cymetica, filed by the operator.
- The prize line is today's terms (up to 5 % / 3 % / 1 %). We asked Cymetica on 2026-10-27 about a Season 0 in ET10
  or a cash prize until revenue starts; their answer changes `QUEST.prize` and nothing else.
