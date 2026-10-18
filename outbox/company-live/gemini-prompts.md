# Zadání pro Gemini: všechno, co potřebuju, aby se kancelář i vesmír skládaly živě

## Co ještě potřebuju: 40 obrázků, pak už nic

1. **Místnosti: 12** (oddíl 2). Těch 9, co máš, znovu s nízkými stěnami (`qa`, `manager`, `audit`, `vault`, `lab`, `trading`, `league`, `outsider`, `development`) a 3 nové (`design`, `generic`, `lot-add`).
2. **Astronauti: 4** (oddíl 3): `A-sit`, `A-stand`, `A-walk`, `A-wave`.
3. **Plošina 4x4: 1** (oddíl 1), pro firmy s víc než pěti odděleními.
4. **Stanice do vesmíru: 23** (oddíl 4).

**Nejdřív jen jednu místnost, `O-room-qa`.** Postavím ji mezi ostatní; když bude sedět, pošli zbytek.

**Hotovo:** `U-background`, `U-station-spire-green`, `O-platform-3x3` (rovnám ji sám).

Všude stejná kamera: izometrická, bez perspektivy (orthographic). Proto to v zadáních stojí výslovně. Perspektiva u plošiny byla to, co místnosti naklánělo.

**Jak posílat:** každý obrázek zvlášť sem do chatu a do zprávy napiš jeho jméno. K zadání přilož vzor: ke kanceláři `look-office.webp`, k vesmíru `look-universe.webp`, k astronautům tu úplně první QA místnost, ve které astronauti sedí (nové místnosti jsou prázdné). Když Gemini přidá text, štítky nebo jiný úhel kamery, vygeneruj ho znovu.

---

## Kancelář

### 1. Velká plošina: 1 obrázek

```
O-platform-4x4: The same as the attached platform image (same style, lighting, hull, engines, solar panels, asteroid, nebula) but BIGGER: a 4 by 4 grid of empty floor plates, four rows of four, SIXTEEN plates in total (the attached image has only 3 by 3 -- do not copy that count). ORTHOGRAPHIC isometric camera, NO perspective: parallel edges stay parallel and every plate is exactly the same size and shape, the far ones as big as the near ones. The platform fills most of the frame. No rooms, no people, no text, no UI. 16:9, 2560x1440.
```

### 2. Místnosti BEZ lidí: 12 obrázků, stejný úvod

Astronauty do místností přidám sám, tolik, kolik má oddělení lidí, a nechám je chodit. Proto místnosti bez lidí.

```
Same style, camera angle, lighting and colours as the attached image: isometric 3D render with an ORTHOGRAPHIC camera (no perspective: every wall edge that is vertical stays vertical), dark navy materials, LOW glass walls only waist high (about one sixth of the room's width, as low as in the attached office picture) with soft mint-green neon edges on top, so the whole inside of the room is seen from above, soft pastel cyan light. ONE single room only, its square floor seen as a diamond whose left and right corners touch the left and right edges of the image, centred, on a flat pure magenta (#FF00FF) background with no shadow on it. NO people, NO astronauts: desks face the back walls and their chairs are empty. No text, no labels, no UI. Square, 2048x2048. The room:
```

```
O-room-qa: rows of dark server racks with small blinking lights, two desks with monitors showing code.
```
```
O-room-manager: a round holographic dais with stacked cyan rings and a glowing white-cyan sphere, concentric light rings on the floor.
```
```
O-room-audit: two retro white consoles with green screens, one desk with a monitor, a white printer, a plant.
```
```
O-room-vault: a round armoured vault door in the back wall, glass cases with stacks of green coins and stacks of blue coins, soft green light.
```
```
O-room-lab: white lab machines with floating green holographic screens, small canisters, two desks.
```
```
O-room-trading: two desks with several monitors showing green and red candlestick charts, a long chart screen on the back wall.
```
```
O-room-league: two desks with monitors and a round table with a cyan hologram of a tournament bracket.
```
```
O-room-outsider: a small lounge with a sofa, a big wall screen showing a website, one desk.
```
```
O-room-development: three desks with monitors, two server racks.
```
```
O-room-design: desks with large drawing tablets, a mood board wall with colour swatches.
```
```
O-room-generic: an office with two desks with monitors, a plant and a wall screen.
```
```
O-lot-add: no room and no walls: an empty floor plate with a cyan holographic ring pad with a grid inside, dashed white lines round it.
```

### 3. Astronauti (pracovníci): 4 obrázky, stejný úvod

```
The same astronaut as in the attached room image (white space suit, white helmet with a dark visor, small backpack), same camera angle and lighting, ORTHOGRAPHIC camera (no perspective), ONE figure only, centred, filling about 70% of the image height, on a flat pure magenta (#FF00FF) background with no shadow on it. No text. Square, 1024x1024. The pose:
```

```
A-sit: sitting on an office chair at a desk, seen from behind and a little from the left, typing; draw only the astronaut and the chair, no desk.
```
```
A-stand: standing, facing the camera's left, arms down.
```
```
A-walk: a walk cycle: four frames side by side in one wide image (4096x1024), the astronaut walking towards the camera's left, each frame the same size and on the same ground line.
```
```
A-wave: standing, facing the camera, waving one hand.
```

---

## Vesmír

### 4. Stanice: 23 zbývajících, stejný úvod

```
Same style, camera angle, lighting and colours as the attached station image: a single space station on a square base platform with solar panels on its sides and small glowing thrusters under it, centred, filling about 80% of the image, on a flat pure magenta (#FF00FF) background with no shadow on it. No text, no labels, no orbit lines. Square, 2048x2048. The station:
```

Tvary:

```
spire: a tower of stacked glass decks with lit windows and an antenna on top
```
```
biodome: a short drum of decks with a glass dome on top and plants inside
```
```
ziggurat: stepped tiers getting smaller towards the top, a light beam from the top
```
```
ring: a spindle of disc decks with a big wheel around it on four spokes
```
```
starship: a horizontal ship hull with a nose, a bridge and three engines
```
```
vault: an armoured block with a round door and a satellite dish
```

Za tvar napiš barvu trupu („its hull painted red“). Barvy: `green`, `cyan`, `blue`, `red`. Jméno: `U-station-<tvar>-<barva>`. Spire green už máme, zbývá 23.

---

## 5. Úkol pro Gemini: ať kancelář postaví sám jako HTML

Vlož celé, přilož `look-office.webp`. Výsledek (HTML soubor) pošli sem: otevřu ho a ukážu ti ho vedle našeho.

```
Build ONE self-contained HTML file (inline CSS and JavaScript; you may load three.js 0.160.0 from https://cdn.jsdelivr.net/npm/three@0.160.0/ and the Google Fonts "JetBrains Mono" and "Archivo Black"; nothing else from outside). Opened in Chrome it must look like the attached picture, live, at 60 frames a second.

The scene: the office of a company run by AI agents, on a floating platform in space, seen from above at an angle with an isometric camera. A dark navy platform of square floor plates on a rocky asteroid, thrusters glowing blue, solar panels, small rocks drifting, a nebula and stars behind. On the plates, glass rooms with LOW, waist-high walls and soft mint-green neon edges, soft pastel cyan light, so the inside of every room is seen.

Build it from this data, kept as a JavaScript array at the top of the file so it can be changed:
const departments = [
  { name: 'Cymetica QA', kind: 'qa', experts: 2, status: 'working', next: '21:00', et10: 1000 },
  { name: 'Laboratory', kind: 'lab', experts: 2, status: 'idle', next: 'in 2 h', et10: 0 },
  { name: 'Trading desk', kind: 'trading', experts: 2, status: 'waiting', next: 'needs you', et10: 0 },
  { name: 'Outsider', kind: 'lounge', experts: 1, status: 'idle', next: 'tomorrow', et10: 0 },
  { name: 'Agent League', kind: 'league', experts: 1, status: 'working', next: '12:00', et10: 0 }
];

- One room per department, each on its own plate, furnished by its kind. qa: dark server racks with blinking lights, desks with code on the monitors. lab: white lab machines, floating green holographic screens, small canisters. trading: desks with green and red candlestick charts, a long chart screen on the back wall. lounge: a sofa, a coffee table, a big wall screen. league: a round table with a cyan hologram of a tournament bracket.
- Three fixed rooms: the Manager in the middle plate (a round holographic dais, stacked cyan rings, a glowing white sphere), the Weekly Audit (retro white consoles with green screens, a printer, a plant), the Vault (a round armoured door, glass cases of green and blue coin stacks).
- One empty plate, "Add department": a cyan holographic ring with a grid inside, dashed lines round it.
- In each room as many astronauts as it has experts (white suits, white helmets with dark visors): sitting at a desk and typing while the room is working, walking between desks while it is idle.
- A label over each room: its name, its status, its next run. A working room glows soft cyan, a waiting one soft red, an idle one not at all. Over the Manager a badge: "N NEED YOU" in red while any room waits, else "ALL CLEAR".
- Hover a room: it lights up and a tooltip shows its numbers. Click it: a side panel slides in with its details.
- Add a department to the array and a room appears on the next free plate; with more than five departments the platform grows from 3 x 3 to 4 x 4 plates.
- Drag to turn the view a little, the mouse wheel to zoom.

Colours: only background #0a0e17, green #00ff88, cyan #00cfff, red #ff4444, blue #3b82f6, white and navy. No orange, no purple, no gold, no plain grey. All text in English. Answer with the HTML file only.
```
