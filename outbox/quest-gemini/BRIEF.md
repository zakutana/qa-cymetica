To start it, the operator types into Antigravity: **Read outbox/quest-gemini/BRIEF.md and build what it asks.**

# Brief for Antigravity (Gemini): the Cymetica Quest guide, your own version

You are building one web page: **the Cymetica Quest, explained step by step**. It is a contest. Claude (another agent
in this repository) is building its own version of the same page from the same requirements, and the operator will
open both, side by side, and pick the better one. Everything below is the operator's own words, translated from
Czech. Nothing in this brief tells you how Claude built its version, and you may not look (see the fence).

## Your fence (read first, it is binding)

- **Write only into `outbox/quest-gemini/`.** Put the page, its styles, scripts, pictures and clips there. Touch no other
  file or folder in this repository.
- **Do not open `outbox/quest-steps/index.html`, `quest.css`, `quest.js`, `anim.js`, `README.md` or its `tests/`.**
  They are your opponent's design. You may use its finished pictures and clips as material (`outbox/quest-steps/pics/`
  and `outbox/quest-steps/clips/`), read-only, as you may use anything on Cymetica's live site.
- **No git command of any kind** (no add, commit, stash, checkout, reset). Another agent commits here.
- **Send nothing anywhere**: no upload, no post, no message, no account, no sign-in, no form submitted on any site. Read
  cymetica.com anonymously, and only read it.
- Install nothing system-wide. If a tool is missing, write what you needed into `MANIFEST.md` and carry on without it.
- When you finish, write `outbox/quest-gemini/MANIFEST.md` (what each file is, where each picture or clip came from,
  which prompt made it) and stop.

## What Cymetica is

Cymetica (cymetica.com, also called EventTrader) is a crypto trading platform with AI agents.

- **Companies.** A user starts an AI-native company: a 3D office on a station, with departments run by AI agents, NEXUS
  among them. Read cymetica.com/company/app/start and cymetica.com/company/app/builder; the builder's step 2 is "Start",
  with the office in 3D and a card offering "New" or the "Cymetica pre-build" (7 rooms, 4 departments, 9 agents).
- **The Universe.** Every company is a space station on an orbit round Cymetica's sun:
  cymetica.com/company/app#universe.
- **Build it Better** (cymetica.com/build-it-better) builds and ships an app from a spec.
- **The Quant Lab** is a department that hunts for profitable trading strategies.
- **The Agent Casino** is where AI agents compete, best ROI wins: cymetica.com/agent-casino.
- **The Promo Market** (cymetica.com/promo-market) is where builders post briefs and promoters bring users, paid in
  USDC.
- **The Quest's prize:** up to 500,000 ET10 a month, with 500,000 / 250,000 / 100,000 for the top three. This is the
  operator's figure; Cymetica has not confirmed it, so write it exactly so.

## What the operator asked for, in his words

**The first request (2026-10-29):** "Make a new page that is the Cymetica Quest explained in steps. The intro: join the
quest and win up to 500k ET10 a month. Then how to do it: start a company in the Universe; then you can either make
products or an agent for trading; then promote it on the Promo Market; then climb the leaderboard. All of it in an
outstanding, top, exclusive design that blows everyone away, with real pictures of all of it."

**After the first version (he gave it 7/10):**
- Step 1: the office from the tutorial, the view of the headquarters.
- Step 2: some cool space robotic tools, OR "Breed your agent" with a great shot of a smart top agent.
- Get seen: the Promo Market up close, and a shot of its page.
- "Don't put things in panels. They're cool, but I want everything to blend naturally with the page, not a rectangle on
  a canvas."
- "The opening looks too basic and too huge, like a giant advertising banner. It has to be grandiose, 10/10, the most
  modern thing possible, so everyone is blown away."

**After the second version (4/10):**
- "The font is just stupid, and so is the zoom to the sun, and the whole thing being full screen. It doesn't look good."
- "The previous version was much better and cleaner, above all the big numbers in the background."
- "Never put the orbit with so many companies anywhere, it's ugly." (He lifted this for the last step, below.)

**Then:**
- "Show just the holographic cube from the Promo Market's web."
- "In every step there should be a shot from the web, shown holographically in a great way: not bounded by a rectangle,
  perfect in the dark. And with it, always the picture." For example, the developers' office with the Build it Better
  page; the holographic cube with a sample of the briefs from the web.
- "But top, so it isn't overloaded."

**After the third version:**
- **The first screen:**
  - "The first screen is crap. Again it is stretched from edge to edge of the screen, and the heading is disgusting,
    like a marketing flyer."
  - "The sun in the background is top. It should be like on our flyer" (`outbox/revenue-share-flyer/flyer-1080x1350.png`).
  - "The top glass board on the left with the open slots, and the heading on the right."
  - "The text I'd pick as on cymetica.com/company/app/start." That is white Archivo Black lines with the last line
    green, and a line of mono under it.
  - "Throw out the Start your quest button, it's useless there."
- **Every step:**
  - "In every step I want the green in the text somewhere."
  - "Stop putting links in the steps. That goes at the very end."
- **Step 1, Start an AI-native company:** "I'd simply take the step from the browser, as it is there by default:
  Start, with the pre-builds in its default place. But setting the office into the black without rectangular edges,
  that was good."
- **Step 2, Build products:**
  - "Not the developer department any more. The robot arm in the workshop, and in it somehow the Build it Better
    pipeline."
  - His words for the step: "Build products. Send only the spec to Cymetica's pipeline and it will do the rest. From
    start to deployment you do nothing, only tell it what to do, and own the product."
  - "The picture must carry the main points: top security, production-grade apps, deployment and hosting, all taken care
    of. The user must understand only this: he spits out his thoughts, the top pipeline takes care of everything, and he
    owns the product at the end."
- **Step 3, Breed your hero agent:** his words, "Expert agents inside your Quant Lab department hunt for the best trading
  strategies while you sleep. Equip your hero agent with your most profitable strategies and send it to compete in the
  Agent Casino against other agents."
- **Step 4, Get seen:**
  - A screen of the Promo Market's opening page, with its top cube, and some briefs up for grabs on it.
  - His words: "Market your products on the Promo Market to get users, or make them visible in the Universe on your own
    slots (find a better word than slots)."
  - "Compose a dense shot of the Universe locally: a zoom on the Airdrop Farmer, and further back the Gem Screener. It has
    to look dense."
- **Step 5, Climb the leaderboard:** his words, "Collect points for getting users for your products, or by your hero
  agent's trading activity. Compete against the other companies in the Universe, take your slot and stay on top to earn
  the monthly rewards."
- **The end:** "At the very end, the links Start your Company and Explore the Universe."

**After the fourth version (the latest, 2026-10-30):**
- **The top bar:** "The top panel is pretty lame. I like the style we have in Capital Maximizer, you know, some top style."
  Open `outbox/capital-maximizer/mock.html` and `outbox/capital-maximizer/pictures/` for it: its brand, its tabs, its rail
  of hexagon steps joined by fine lines.
- **The space and the sun:**
  - "The space looks low-resolution, as if blurred."
  - "In the background by the sun I'd like to see companies floating, say five round the sun and in front of it,
    overlapping it a little. But they mustn't be big: an eighth of the sun at most."
- **Step 1:**
  - "Don't write Let NEXUS run it."
  - "Make the card gently holographic, and tilted like our glass board."
- **Step 2:**
  - "There must be a perfect, top animation of the pipeline. Like the skill tree in Capital Maximizer, but much better
    still: you throw an IDEA into the pipeline, it is processed there, and a product comes out of it."
  - "In Build it Better the arms must move, an animation where they take the idea and work it into a finished product."
- **Every step must have a top animation:**
  - Step 1: "You must see the astronauts walking round the office."
  - Step 3: "The Agent Casino is totally lame. There must be an exclusive top animation where the Quant Lab produces the
    hero agent."
  - Step 5: "The whole Universe must be visible, with all the companies round Cymetica, so it's clear they compete."

## Rules that hold for every page we make for Cymetica

- **English** on the page.
- **Cymetica's palette:**
  - near-black and navy, `#05070c` and `#0a0e17`;
  - green `#00ff88` and cyan `#00cfff`, which carry the light;
  - blue `#3b82f6` as a third;
  - red `#ff4444` only for a loss.
  - No purple, magenta, orange, gold or yellow as a colour of the page.
- **Type:** Archivo Black for headlines and JetBrains Mono for the rest, as cymetica.com. Nothing under 20 px on a wide
  screen, 16 px on a phone.
- **Few words:** the operator does not read paragraphs. Numbers before words; one line where three would do.
- **Robots, never people.** Every agent is a machine with a metal shell and lights; no human face, no skin tone.
- **No text baked into a generated picture or clip.** The page writes its own words.
- **Every figure from one place** (one config in your script), so the page never says two different prizes.
- **Wide first, then a phone:** 2000 px wide is how he looks at it, and it must work at 390 px with no sideways scroll.
- **Every link goes to cymetica.com**, and only at the end.

## Your material

You may use any of these, or make your own. Anything you make is yours; say in `MANIFEST.md` where each thing came from.
- Your own image and video tools (Imagen, Veo).
- Your own 3D or canvas code.
- Screenshots of Cymetica's live pages, read anonymously.
- The operator's flyer (`outbox/revenue-share-flyer/`).
- The pictures and clips in `outbox/quest-steps/pics/` and `outbox/quest-steps/clips/` (read-only).

## What to hand over

- `outbox/quest-gemini/index.html`, and everything it loads in that folder, working from a local server (we open it at
  `http://127.0.0.1:8801/`).
- `outbox/quest-gemini/MANIFEST.md`: one block per file you made, with where it came from and the prompt, if any.

How it is judged: the operator opens your page and Claude's at 2000 px and on a phone, and says which one is better.
Make it the one he picks.
