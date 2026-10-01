# Build request: Gem Screener, changes after ET-28606 (cymetica.com/gem-screener/app)

**For:** the lead agent of the Cymetica SDLC pipeline
**From:** Adam (product owner, Gem Screener)
**Scope:** the open changes to the Gem Screener app after ET-28606. Build or change only what is named; leave the rest of the app as it is.

> **HOW TO READ THIS SPEC**
> 1. **Goals, not methods.** How you build it is your call. Where an item gives a rule or a number, it is a good default, and you may improve it; say what you changed and why in your spec.
> 2. **Every number is read from the live site on 2026-10-01.** They are there so you can check that a change took effect; they are not the requirement.
> 3. **English only**, degen-friendly: the number first, plain short words.
> 4. **Keep the look.** Change only what an item names.

---

## 1. Header

**[1] The logo replaces the title, and links to cymetica.com.** The header of `/gem-screener/app` shows the words "Gem Screener" with "Revenue-driven research" under them (live: an `h1` and a `span`, the header 130 px high, no link anywhere in it). Replace both with the finished horizontal logo: the gem in scanner corners, "Gem Screener", "Revenue-driven AI Research" and "by CyMetica". A click or a tap on it opens https://cymetica.com. The logo carries the tagline, so the old line goes; the wording to show is the logo's "Revenue-driven AI Research".

The logo is ready, as SVG (sharp at any size) and PNG, in the owner's repository: https://github.com/zakutana/gem-screener/tree/91196c2f01a4fa9df438a9de5ad6133eaeba53ab/docs/logo-gem-screener . `svg/gem-screener-logo-A-horizontal.svg` is the one for the page header; the README there gives the colours and the spelling. The page is dark (`#0a0e17`), so use the version made for a dark ground. Do not redraw it, recolour it, or set its words in a font.

What stays: the right side of the header (updated time, apps and chains count, Live) and the tabs. The header must not get taller than it is now, at 1360 px and at 390 px, and the logo must not be cut off or squeezed at either width.

**[2] A favicon.** The page has none (live: no `link rel="icon"` in the head). Use the gem alone from the same folder (`svg/gem-screener-icon-A-small.svg`, made for favicons).

---

## 2. Altseason panel and the sliders

**[3] The altseason panel gets a clear outline.** The panel at the top of Top Picks (live: the five tiles, Expand and the slider sit in a box whose edge is almost the colour of the page, so the tiles and the slider float on the page). Give the panel a visible border, so it reads as one block that is set apart from "Hot sectors" below it. The look otherwise stays.

![The panel today](reference/followup-2/altseason-panel-today.webp)

**[4] One slider style: separate segments.** Today the scale in the altseason panel (0, 35, 70, 100) is one continuous bar whose colours run into each other, and so is the scale in the coin's Chart card (1, 40, 60, 100). The owner wants the style of the reference below: each band is its own rounded segment with a small gap between segments, the band the marker is in is bright and the other bands are dimmed, the marker is a white tick. One component, used in both places (and anywhere else a band scale is drawn), so the same thing never looks different on another page.

![The style the owner wants](reference/followup-2/slider-style-wanted.png)

In the Chart card the bands and their colours stay as they are (below 40 red, 40 to 60 blue, 60 and up green).

![The Chart card slider today](reference/followup-2/chart-card-slider-today.png)

In the altseason panel the first band, "Quiet for alts" (0 to 35), changes from grey to the same blue as the middle band of the Chart card. The other two stay: "Alts are moving" (35 to 70) green, "Top zone" (70 to 100) red. Its labels above the segments and the numbers 0, 35, 70, 100 below stay.

---

## 3. Near misses (Top Picks)

**[5] A logo on every cube, and a gate instead of the "Picks" box.** The "Near misses" lane under the Degen picks (live: six cubes, each with name, place in line, upside and a reason chip, ending in a plain green box that says "Picks"). Two changes:

- **The logo.** Each cube shows the app's round logo (about 28 px) before its name: the same logo the app already shows on the pick's card and in the Apps table, so no new data is needed. The place in line (#1, #2, ...) moves down next to the upside so that the name is not cut off; "Collector Crypt" and "Gains Network" read in full at 1360 px.
- **The gate.** The green "Picks" box becomes an entrance gate: an arch in the page's green with a small gem on its keystone, a softly glowing doorway, a check mark and the word PICKS. It is a little taller than the cubes so that it reads as a gate, and the queue stands on a dashed floor line that runs into it. The doorway pulses slowly and a chevron runs into it; both stand still for a visitor who asks for less motion.

Everything else about the lane stays: the order (biggest upside first), the reason chips, the tooltip card, a click opening the coin, the sideways scroll with the fading right edge.

![The look the owner chose (design A in the full mock)](reference/followup-2/near-misses-gate-chosen.png)

The full mock below also shows a second design (B, a trampoline that throws the first cube up into the picks). **The owner chose A; B is not wanted.** The mock is inspiration, not literal: the arch, the proportions and the motion are yours to improve.

![The two designs that were tried: B on top, A below](reference/followup-2/near-misses-gate-and-trampoline-mock.jpg)

---

## Checklist (one line each; done when all are true)

- [ ] 1 The header shows the logo (not text) with "Revenue-driven AI Research" and "by CyMetica" in it; the old title and the old tagline are gone.
- [ ] 1 A click or a tap on the logo opens https://cymetica.com; it is a real link (keyboard focus works, it has a text alternative such as "Gem Screener by CyMetica").
- [ ] 1 The header is no taller than today's 130 px, and nothing is cut off, at 1360 px and at 390 px.
- [ ] 2 The browser tab shows the gem icon.
- [ ] 3 The altseason panel has a visible border; it reads as one block apart from "Hot sectors".
- [ ] 4 The altseason slider and the Chart card slider are drawn as separate rounded segments with gaps, the marker's band bright and the others dimmed, with a white tick; one shared component.
- [ ] 4 In the altseason panel the "Quiet for alts" band is blue (the Chart card's blue), not grey; the other two bands and all labels are unchanged. The Chart card keeps its three colours.
- [ ] 5 Every near-miss cube shows the app's round logo; the place in line sits next to the upside; no name is cut off at 1360 px.
- [ ] 5 The "Picks" box is a gate (arch, gem on the keystone, glowing doorway, check mark, PICKS); the queue stands on a floor line that runs into it; the motion stops for visitors who ask for less motion; the rest of the lane behaves as before.
