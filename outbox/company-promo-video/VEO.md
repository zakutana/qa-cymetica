# Cymetica Quest: promo video for Google Veo 3.1

## One video, one generation (8 s, nothing to join)

Veo 3.1 makes at most 8 seconds per generation. This is the whole idea in one: **Frames to Video**, first frame
`shots/02-universe.png`, last frame `shots/11-endcard.png`, 16:9, 8 s, this prompt:

```
Start on this galaxy: glowing low-poly space stations riding cyan orbit rings around a colossal golden plasma star. The camera glides in toward the star; the star pulses and fires three brilliant cyan arcs of light, each carrying a glowing dollar sign, to three stations, which flare green as they are hit. A pane of frosted glass slides in over the scene and the shot settles exactly on the final frame: the slogan, the three percentages and the button, perfectly sharp and still. Premium sci-fi 3D render, strong bloom, cinematic. Audio: dark synthwave building to a bass drop on the final frame. A calm, confident male narrator says: "Stop paying fees. Start earning them. Build a company, take a top-three seat. Cymetica Quest."
```

## The long cut (8 shots, joined in Flow)

8 shots × 8 s ≈ 64 s, 16:9, 1080p. Images are in `shots/` (made from our mockup by `shots.py`).

**How:** in Flow (or Gemini → Veo 3.1), for each shot choose **Frames to Video**, upload the shot's image as the **first frame**
(shot 4: **Ingredients to Video** with its three images), paste the prompt, 16:9, 8 s. Join the 8 clips in Flow's Scenebuilder or
CapCut. Veo garbles text that moves, so every prompt keeps text still; the end card's text comes from the image itself.
If the narrator's voice differs between clips, mute Veo's audio and lay the full voiceover (below) over the whole cut once.

## Voiceover (the whole script)

```
Every trade on Cymetica pays a fee.
What if those fees paid you?
Found a company. AI departments grind for you, twenty-four seven.
Ship products. They land in the Universe.
Creators shill them on Promo Market. You pay per real user.
Revenue rolls in. Climb the leaderboard.
The top three take a cut of every fee on Cymetica. All three seats are open.
Stop paying fees. Start earning them. Cymetica Quest.
```

Voice: deep, calm, confident male narrator, close mic. Music, one track under all of it: dark cinematic synthwave, 105 BPM,
building from a sub-bass hum to a drop at shot 7, resolving on the end card.

## Shot 1 · Every fee · first frame `shots/01-sun.png`

```
Cinematic slow push-in on a colossal golden plasma star made of tangled filaments of gold, orange, electric-blue and white light, sparks spraying from its surface, thin rings of cyan light orbiting it on a dark teal-black space background with a faint nebula. The camera dollies forward slowly, the star breathes and pulses, lens flares bloom. Premium sci-fi 3D render, crisp, high contrast, soft bloom. Audio: a deep sub-bass hum building, a distant cosmic whoosh. A calm, confident male narrator says: "Every trade on Cymetica pays a fee."
```

## Shot 2 · The flip · first frame `shots/02-universe.png`

```
Wide orbital view of a galaxy of glowing low-poly space stations in green, cyan, blue, red and pink, riding concentric cyan orbit rings around a golden plasma star. The stations slowly orbit. The star pulses once and sends bright cyan streams of light racing along the rings, and three stations light up with a green glow. The camera slowly rises and turns around the galaxy. Premium sci-fi 3D render, bloom. Audio: a rising synth arpeggio. A calm, confident male narrator says: "What if those fees paid you?"
```

## Shot 3 · Launch · first frame `shots/03-office.png`

```
A futuristic cross-shaped station of glass-walled rooms built on an asteroid floating in deep space. Inside the rooms small astronaut-like AI agents sit at desks with glowing monitors. One by one the rooms light up cyan as the agents start working, screens flicker on, solar panels glint. The camera orbits slowly around the station and drifts closer. Premium sci-fi 3D render, soft bloom. Audio: soft UI chimes and keyboard clicks over a synth beat that kicks in. A calm, confident male narrator says: "Found a company. AI departments grind for you, twenty-four seven."
```

## Shot 4 · Build · Ingredients `shots/04-gem.png`, `shots/05-casino.png`, `shots/06-farmer.png`

```
On glowing cyan orbit rings in space, three products materialize one after another in bursts of light particles: a giant floating cut emerald-green diamond turning slowly over a green ring, a neon magenta and violet ring station like a spinning poker chip with a hologram above it, and a polished gold robot head wearing a straw hat with a small sprout, its warm white eyes blinking. The camera glides past each one in turn. Premium sci-fi 3D render, bloom. Audio: three punchy materialize hits on the beat. A calm, confident male narrator says: "Ship products. They land in the Universe."
```

## Shot 5 · Promote · first frame `shots/07-promo.png`

```
A tall cyan spire on a hexagonal platform projects a floating holographic cube of glowing ads in magenta and amber, with scan lines and a light glitch; two searchlights sweep the sky above it. Small glowing ad cards fly out of the cube in every direction like posts going viral, leaving trails of light across the orbits. The camera pushes up toward the hologram. Premium sci-fi 3D render, bloom. Audio: whooshes and a buzz of digital chatter. A calm, confident male narrator says: "Creators shill them on Promo Market. You pay per real user."
```

## Shot 6 · Earn and climb · first frame `shots/09-leaderboard.png`

```
A frosted glass leaderboard panel floats in front of a galaxy of glowing stations orbiting a golden plasma star. The panel and every word and number on it stay perfectly still and sharp; light glides across the glass, glowing green particles rise behind it like revenue flowing in, and the galaxy turns slowly in the background. The camera pushes in slowly. Premium sci-fi UI, cinematic depth of field. Audio: rising tension and soft coin-like ticks. A calm, confident male narrator says: "Revenue rolls in. Climb the leaderboard."
```

## Shot 7 · Take a seat · first frame `shots/10-seats-open.png`

```
A galaxy of glowing stations on cyan orbit rings around a golden plasma star, a frosted glass panel at the left whose text stays perfectly still and sharp. The star fires three brilliant cyan arcs of light, each carrying a glowing dollar sign, to three stations on the orbits, one after another, and each station flares with light as it is hit. The camera slowly pulls back to reveal the whole galaxy. Premium sci-fi 3D render, strong bloom. Audio: a heavy bass drop and a triumphant synth chord. A calm, confident male narrator says: "The top three take a cut of every fee on Cymetica. All three seats are open."
```

## Shot 8 · End card · first and last frame `shots/11-endcard.png`

```
Hold on this exact frame. Behind a pane of frosted glass the golden plasma star swirls gently and its rings of light turn slowly, a single soft sheen of light sweeps across the glass, stars twinkle. All text and the button stay perfectly still, sharp and unchanged. Audio: the music resolves on a final hit. A calm, confident male narrator says: "Stop paying fees. Start earning them. Cymetica Quest."
```
