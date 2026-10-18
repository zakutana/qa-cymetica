# Zadání pro Gemini: všechno, co potřebuju, aby se kancelář i vesmír skládaly živě

**Hotovo a sedí:** `U-background`, `U-station-spire-green`, `O-platform-3x3` (8 plošin bez přední je v pořádku). Místnosti `qa`, `manager`, `audit`, `vault`, `lab`, `trading`, `league`, `outsider` už stojí na plošině, jen se mají přegenerovat s nízkými stěnami (níž).

**Ještě chybí:** 23 stanic (oddíl 4), 4 astronauti (oddíl 3), místnosti `design`, `generic`, `lot-add`, plošina `O-platform-4x4` (poslaná vyšla zase 3x3, zadání je zpřesněné).

**Znovu, s nízkými stěnami:** všech 8 místností. Mají stěny vysoké jako třetina místnosti, takže přední místnosti na plošině zakrývají zadní; v tvém obrázku kanceláře jsou stěny nízké a je vidět do všech. Zadání v oddílu 2 to už říká (LOW glass walls). Ke každé přilož `look-office.webp`.

**Jak posílat:** každý obrázek zvlášť sem do chatu a do zprávy napiš jeho jméno. K zadání přilož vzor: ke kanceláři `look-office.webp`, k vesmíru `look-universe.webp`, k astronautům tu úplně první QA místnost, ve které astronauti sedí (nové místnosti jsou prázdné). Když Gemini přidá text, štítky nebo jiný úhel kamery, vygeneruj ho znovu.

---

## Kancelář

### 1. Velká plošina: 1 obrázek

```
O-platform-4x4: The same as the attached platform image (same camera, style, lighting, hull, engines, solar panels, asteroid, nebula) but BIGGER: a 4 by 4 grid of empty floor plates, four rows of four, SIXTEEN plates in total (the attached image has only 3 by 3 -- do not copy that count). Each plate the same shape as in the attached image; the platform fills more of the frame. No rooms, no people, no text, no UI. 16:9, 2560x1440.
```

### 2. Místnosti BEZ lidí: 12 obrázků, stejný úvod

Astronauty do místností přidám sám, tolik, kolik má oddělení lidí, a nechám je chodit. Proto místnosti bez lidí.

```
Same style, camera angle, lighting and colours as the attached image: isometric 3D render, dark navy materials, LOW glass walls only waist high (about one sixth of the room's width, as low as in the attached office picture) with soft mint-green neon edges on top, so the whole inside of the room is seen from above, soft pastel cyan light. ONE single room only, its square floor seen as a diamond whose left and right corners touch the left and right edges of the image, centred, on a flat pure magenta (#FF00FF) background with no shadow on it. NO people, NO astronauts: desks face the back walls and their chairs are empty. No text, no labels, no UI. Square, 2048x2048. The room:
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
The same astronaut as in the attached room image (white space suit, white helmet with a dark visor, small backpack), same camera angle and lighting, ONE figure only, centred, filling about 70% of the image height, on a flat pure magenta (#FF00FF) background with no shadow on it. No text. Square, 1024x1024. The pose:
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
