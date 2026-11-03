# The Cymetica Quest page: run it as it is

This folder is the finished page, complete. Nothing else is needed.

**Run it:** in this folder, `python serve.py 8800`, then open http://127.0.0.1:8800/. Any real web server works too, but it must answer HTTP Range requests (the clips seek to their loop point; Python's stock `http.server` does not answer them, which is why `serve.py` exists). `serve.py` sends no-cache, so an edit shows on reload.

**Put it on the site:** copy the folder's files to be served at `/quest` as they are (paths are relative):

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js`, `anim.js`, `outlines.js` | the page, its look, its figures and links (`QUEST` in quest.js), the animations and the clip player |
| `pics/` | every picture it loads (posters of the clips, the sky, the sun, products, agents, the board) |
| `clips/*.mp4`, `clips/*.webm` | the six clips it plays, each in H.264 and VP9; the page takes the first the browser can play |
| `scenes/tools.html` | the Build it Better scene (three.js) the workshop clip was drawn from |
| `llms.txt` | the page for AI agents: publish it at `/quest/llms.txt`, list it first in `/llms.txt` and in `/.well-known/agent.json` (the page's head already points to it) |

Fonts come from Google Fonts (Archivo Black, Inter, JetBrains Mono, Rajdhani); nothing else is fetched from outside.

**What to change when you build it in (and only this):**

1. The three prizes, the pool, the top bar's "up to" figure and the step 5 board's rows come from `GET /api/v1/company/season` (`prizes_et10`, `rows`) instead of the numbers in `quest.js` (`QUEST.prizes`, `QUEST.pool`, `QUEST.board`). The board's companies and points in the file are placeholders.
2. Keep `llms.txt`'s figures in step with the same API.

**What not to change:** the look, the type, the colours, the motion, the order, the words. The page was judged by eye at 1920 px, 1440, 1280, 1024 and on a phone (390), in Firefox and Chrome. It loads 1.9 MB first; the clips load as their steps come near and are fetched in the background after that (about 30 MB in all, one format each).

Source of the clips: `record.py` films them from the live pages; `slim.py` and `keycheck.py` shrink them without a visible loss. You do not need them to run the page.
