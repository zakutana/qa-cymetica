# Zadání pro Gemini: kousky, ze kterých se kancelář i vesmír poskládají živě

Proč po kouskách: z celého obrázku se nedá přidat 50 firem ani nové oddělení. Z jednotlivých kousků to stránka složí sama, pro jakýkoli počet firem a oddělení, a na kousky dá živé štítky, barvy stavu a klikání.

**Jak posílat:** každý obrázek zvlášť sem do chatu a do zprávy napiš jeho jméno (např. `U-station-spire-green`). K zadáním pro kancelář přilož jako vzor `look-office.webp`, k zadáním pro vesmír `look-universe.webp`. Když Gemini přidá text, štítky nebo změní úhel kamery, vygeneruj ho znovu. Magentové pozadí odstraním.

**Pořadí:** začni zkouškou, tj. `O-platform-3x3`, `O-room-qa`, `U-background` a `U-station-spire-green`. Až uvidíme, že sedí, dodělej zbytek.

---

## Kancelář

### Plošiny (pozadí kanceláře): 2 obrázky

```
O-platform-3x3: Same scene, style, camera angle and lighting as the attached image, but with every room removed: the space platform with nine empty dark floor plates in a 3x3 grid (all nine, the front corner plate too, every plate the same size), the hull with its small lights under the plates, the engines, the solar panels, the asteroid underneath, the teal nebula with stars. No rooms, no walls, no people, no text, no labels, no UI panels. 16:9, 2560x1440, the platform centred and filling about 70% of the width.
```
```
O-platform-4x4: The same as O-platform-3x3 but with sixteen empty floor plates in a 4x4 grid, each plate the same size as in O-platform-3x3. 16:9, 2560x1440, the platform centred and filling about 80% of the width.
```

### Místnosti: jedna na obrázek, stejný úvod

Na začátek každého zadání dej tenhle úvod a za něj řádek místnosti:

```
Same style, camera angle, lighting and colours as the attached image: isometric 3D render, camera at the front-left corner looking down about 35 degrees, dark navy materials, glass walls with soft mint-green neon edges, soft pastel cyan light. ONE single room only: its square floor plate seen as a diamond whose left and right corners touch the left and right edges of the image, centred, on a flat pure magenta (#FF00FF) background with no shadow on it. No text, no labels, no UI. Square, 1536x1536, PNG. The room:
```

```
O-room-manager: a round holographic dais with stacked cyan rings and a glowing white-cyan sphere, concentric light rings on the floor, one astronaut standing.
```
```
O-room-audit: two retro white consoles with green screens, a desk with a monitor and a seated astronaut, a white printer, a plant.
```
```
O-room-vault: a round armoured vault door in the back wall, glass cases with stacks of green coins and stacks of blue coins, soft green light.
```
```
O-room-qa: rows of dark server racks with small blinking lights, two desks with monitors, two astronauts working.
```
```
O-room-lab: white lab machines with floating green holographic screens, small canisters, two astronauts in white suits.
```
```
O-room-trading: two desks with several monitors showing green and red candlestick charts, a long chart screen on the back wall, two astronauts.
```
```
O-room-league: desks with monitors and a round table with a cyan hologram of a tournament bracket, two astronauts.
```
```
O-room-outsider: a small lounge with a sofa, a big wall screen showing a website, one astronaut.
```
```
O-room-development: desks with monitors, two server racks, two astronauts coding.
```
```
O-room-design: desks with large drawing tablets, a mood board wall with colour swatches, two astronauts.
```
```
O-room-generic: an empty office: two desks with monitors, a plant, a wall screen, one astronaut.
```
```
O-lot-add: no room and no walls: an empty floor plate with a cyan holographic ring pad with a grid inside, dashed white lines round it.
```

---

## Vesmír

### Pozadí: 1 obrázek

```
U-background: Same scene, style, camera angle and lighting as the attached image, but with every station and every label removed: only Cymetica's glowing core in the middle with its rings, the seven concentric orbit lines, the teal nebula and the stars. No stations, no text, no labels, no UI panels. 16:9, 2560x1440, the orbits centred and filling about 90% of the width.
```

### Stanice: 6 tvarů × 4 barvy = 24 obrázků, stejný úvod

```
Same style, camera angle, lighting and colours as the stations in the attached image: a single space station on a square base platform with solar panels on its sides and small glowing thrusters under it, seen from the same angle as the image, centred, filling about 80% of the image, on a flat pure magenta (#FF00FF) background with no shadow on it. No text, no labels, no orbit lines. Square, 1024x1024, PNG. The station:
```

Tvary (za úvod dej tvar a barvu, např. „spire, its hull painted green“):

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

Barvy (trup natřený touto barvou): `green`, `cyan`, `blue`, `red`. Jména: `U-station-<tvar>-<barva>`, např. `U-station-ziggurat-red`.
