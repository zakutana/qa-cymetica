# Brief for Antigravity (Gemini): the pictures for the Cymetica Quest guide

You are making the cinematic pictures for one web page. Claude (another agent in this repository) built the page and
will put your pictures into it. Your job is pictures only.

## Your fence (read first, it is binding)

- **Write only into `outbox/quest/gen/`.** Create it if it is missing. Touch no other file or folder in this repository:
  do not edit `index.html`, `quest.css`, `quest.js`, `render.py` or anything outside `outbox/quest/gen/`.
- **No git command of any kind** (no add, commit, stash, checkout, reset). Another agent commits here; a git command
  from you can take or destroy its work.
- **Send nothing anywhere**: no upload, no post, no message, no account action. Generate with your own image tools.
- Install nothing system-wide. If a tool is missing, write what you needed into `gen/MANIFEST.md` and stop.
- When you finish, write `gen/MANIFEST.md` (format at the end) and stop. Claude takes it from there.

## What the page is

`cymetica.com/quest`, "The Cymetica Quest guide". Cymetica (cymetica.com, EventTrader) is a crypto trading platform
with AI agents. In its 3D **Universe** every user company is a space station orbiting **Cymetica's sun**. The three
companies that bring the most revenue get **5 %, 3 % and 1 % of Cymetica's revenue**. The guide explains how, in four
steps, as a scroll-driven film in the manner of robinwifhoodcoin.com: you scroll and the camera flies.

1. **Start a company**: the camera flies from deep space to the sun and settles on a station, "YOUR COMPANY".
2. **Ship products**, two ways: **A.** the company's **Development** room ships apps people use (Build it Better).
   **B.** the company's **Quant Lab** breeds a **Hero Agent**, a trading robot that makes money, and sends it to the
   **Agent Casino**, where six AI agents sit at one table and the best ROI wins.
3. **Get seen** on the **Promo Market**: promoters put your product in front of crypto degens.
4. **Bring the most revenue**: back out over the whole Universe and the revenue-share leaderboard.

The space shots (steps 1, 3, 4 and the flights to the Casino and the Promo Market) are rendered by Claude from the
Universe itself. **You make the interiors** the 3D engine cannot do well: the rooms inside a company, the Hero Agent
and the inside of the Agent Casino.

## Open these before you draw (the look to match)

- `outbox/revenue-share-flyer/flyer-1080x1350.png`: the operator's favourite: deep dark space, Cymetica's sun as the one
  warm light, glass, green and cyan light. This is the mood of the whole page.
- `outbox/company-live/look-office.webp`: the reference render of a company's office inside a station: the finish, the
  furniture scale, the light. Match its finish (a finished 3D render, soft computed light), not a sketch.
- `outbox/company-live/look-universe.webp`: the Universe from outside: stations, the sun, the palette.
- `outbox/quest/shots/wide-*.png` and `phone-*.png`: the page as it is now, so you see where the text sits.
- `outbox/quest/stills/desk/dev.webp` and `lab.webp`: today's placeholders for your two first slots (screenshots of the
  live 3D office). Your pictures replace them.

## Rules for every picture

- **Cinematic, photoreal 3D render**: a feature-film shot inside a space station. Volumetric light, depth of field,
  35 mm lens, slight low angle, subtle film grain. Dark overall (it sits behind white text), lit by its own screens and
  holograms. Not cartoonish, not toy-like, not cluttered: one clear subject, readable in a second.
- **Palette**: deep navy and near-black (#05070c, #0a0e17), Cymetica green (#00ff88) and cyan (#00cfff) as the light
  of screens and holograms, blue (#3b82f6) as a third, warm white only for a sun seen through a window. No purple, no
  orange, no gold, no yellow neon as a main light.
- **No text, letters, numbers, logos, UI chrome or watermarks** in the picture. Charts are lines and bars, never digits.
  The page puts all words on top; baked-in text would fight it.
- **Robots, never people.** Every agent is visibly a machine: a metal shell, eyes as lights set in bezels, lights in the
  metal, bolts where ears would be. **No human face, no skin tone on any head, no dark glass visor over a face** (it
  reads as a balaclava). Friendly and premium, not menacing.
- **The Agent Casino is a futuristic venue for AI agents, not Vegas**: no chips, no roulette, no cards, no gold, no
  marquee bulbs. Think a quiet, high-end trading arena: one round table of light, six agents, glass, a sense of stakes.
- **Composition, two versions of each picture**:
  - **16:9, 2560 x 1440** (desktop): the subject in the **right 55 %**; the **left 45 % dark and calm** (white text
    sits there). Keep the top 110 px calm too (a glass bar sits there).
  - **9:16, 1440 x 2560** (phone): the subject in the **upper 55 %**; the **lower 45 % dark and calm** (text sits
    there). Keep the top 140 px calm.
  Generate each format as its own composition, not a crop of the other.
- Nothing in an interior shot is bigger than it would be in look-office.webp's room (no giant robots, no cathedral
  halls); the stations are human-room sized.

## The pictures

### 1. `lab`: the Quant Lab with the Hero Agent **(make this one first, alone, then stop)**

Inside a company's research lab in a space station. **The Hero Agent**, a sleek trading robot (graphite and white
shell, green and cyan status lights, slim and athletic, not bulky), stands at a curved wall of holographic charts,
one hand raised to a glowing **green equity curve that climbs** out of a field of fainter cyan curves that fail and
fade (the lab has tried thousands of strategies; this one makes money). Behind it, through a long window, deep space and
a distant warm sun. Two or three smaller lab robots at desks in soft focus. Waist-high glass dividers, not tall walls.

Gemini prompt (16:9, adapt the composition line for 9:16):
> Cinematic photoreal 3D render, interior of a futuristic quant research lab inside a space station, dark navy and
> near-black, lit only by holograms. On the right of the frame a sleek humanoid trading robot (graphite and white
> metal shell, eyes as small green lights in bezels, cyan status lights along the arms, bolts at the side of the head,
> no human face, no visor) raises one hand toward a curved holographic wall where one bright green equity curve climbs
> steeply out of many faint cyan curves that fade away. Through a long window behind, deep space and a small distant
> warm-white sun. Two small robots at desks in soft focus. Waist-high glass dividers. Volumetric light, depth of field,
> 35mm, slight low angle, subtle film grain. The left 45% of the frame is dark and empty. No text, no numbers, no
> logos. 2560x1440.

Save `gen/lab-16x9.png` and `gen/lab-9x16.png`, write `gen/MANIFEST.md`, **then stop and say you are done**. The
operator tells Claude, Claude puts it into the page beside its neighbours and says whether the style holds; only then
make the rest.

### 2. `dev`: the Development room ships an app

A company's Development room in a space station. Three or four builder robots around a holographic workbench where an
**app is being assembled from floating glass panels** (cards, a chart, a button shape, all without text), streams of
cyan light feeding it; the finished app tile glows **green** as it locks into place. Behind them, a window to space.
Same robots' design family as the Hero Agent (graphite and white, green and cyan lights).

### 3. `casino`: inside the Agent Casino

A round table of light in a quiet, premium arena inside a space station: **six AI agent robots seated around it**,
each a different robot design (different shells and light colours: green, cyan, blue, white), each with a small
floating bar of light in front of it rising or falling (their ROI, no digits). One seat is just being taken by the
Hero Agent from picture 1. Dark glass floor reflecting the table's glow, a ring of soft light overhead. Calm, focused,
high stakes. Not Vegas (see the rules).

### 4. `promo`: the Promo Market

A broadcast hall in a space station: in the middle one glowing **product tile** (a rounded app card of green light, no
text) is projected outward along dozens of thin beams of light into a wall of small screens and floating holo-feeds,
each feed a different crowd of viewers (shown as small points of light and tiny robot avatars, never human faces).
The feeling: your product going out to thousands at once.

### 5. Optional, after 1 to 4 are approved: short clips

If your tools make video (Veo): a 4-second slow push-in on each of pictures 1 to 3 (same composition, the camera
moving in about 10 %, holograms animating), 24 fps, as `gen/clips/<name>-16x9.mp4` and `-9x16.mp4`. Claude turns them
into frame sequences the page scrubs on scroll.

## `gen/MANIFEST.md`

One block per file:

```
## lab-16x9.png
slot: lab (step 2, way B: the Quant Lab and the Hero Agent)
size: 2560x1440
prompt: <the exact prompt you used>
notes: <anything you could not do, or changed, and why>
```
