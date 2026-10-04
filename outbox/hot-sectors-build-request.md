# Build it Better request: Gem Screener "Hot sectors" redesign (DRAFT, not submitted)

Where: https://cymetica.com/build-it-better (form) or `POST /api/v1/build-it-better/requests`.
Gate (read from the live board 2026-10-04): `request_gate: nexus_build_plan`, `min_et10: null`. A paid Nexus plan files requests (Pro is $20 USDC a month; Free cannot). The old "100+ ET10" gate is gone.
A request is public: the board returns `improvements` text anonymously. Nothing private goes in it.
Builder cannot open local files, so the text below is self-contained. The full CSS/HTML spec is `hot-sectors-spec.md`, the mockup `hot-sectors-redesign.html`.

## Form fields
- **App URL:** https://cymetica.com/gem-screener/app
- **Improvements:** (paste the block below)

```
Gem Screener, Top Picks tab: redesign the "Hot sectors" block and the "Gem Screener Top Picks (CyMetica-managed)" fund bar under it. Goals, not methods: how you build it is your call.

Why: today these two elements are plain text lines. Next to the Altseason Index panel above and the Degen Picks funnel below they look unfinished, and a visitor cannot read them in three seconds.

Goals:
1. One framed panel, same visual weight and frame style as the Altseason Index, holding the sector cards and the Top Picks fund bar.
2. Each sector card reads name, then number, then action: the sector name large, the HOT pill, the fund's return since launch as the biggest text on the card, and a clear "Fund" button.
3. The two trend arrows get words next to the icon ("Already leading", "Beaten down but turning"); the existing tooltips stay.
4. The Top Picks fund bar becomes the flagship of the panel: same anatomy as a card, one size larger, with the one solid button in the block.
5. Sectors tab, bubble chart: with a mouse (a device that can hover) one click on a bubble opens that sector's detail panel, since the hover already shows the card. On touch keep today's two steps: the first tap shows the card, the second opens the detail (ET-28990 #3). The chart caption "Click a bubble for the sector" must match whichever behaviour a visitor gets.
6. Apps and Chains tabs, "The year in a chart" (Top 10 by upside: their year): make it follow the filter above it (Vetted only, Degen picks, All by upside). Today it is fixed: switching the filter changes the project list (for example 76, 7 and 114 projects on Apps) but the chart and its caption stay "Top 10 by upside of 88 vetted". It should redraw for the selected filter, with the title and caption saying what it now shows (for Degen picks, the 7 picks).
7. Sectors tab, Memecoins row: the small rocket that links to the launchpad becomes a clearly visible call to action, a chip reading "Launch your own memecoin" with a rocket disc and an external-link arrow, in yellow (a dark chip with a yellow outline, yellow rocket disc and yellow label), so that it stands out as the one marketing element on the page. The requester knows the palette rule says "no amber, orange or yellow": this is an explicit, deliberate exception for this one chip only, requested by the owner of the request. Under 560px the chip shows "Launch" and keeps the full name as its accessible name.
8. Apps and Chains tabs, "Your fund picks": replace the low-key bar under the filters with a tray that appears (one short entrance plus a brief highlight, reduced motion respected) as soon as the first project is ticked, and that never scrolls out of view: on desktop it sticks to the top of the table, right under the sticky header, when the visitor scrolls down; on phones it docks to the bottom of the window. It shows a progress ring "N of 30", the picked projects as chips with logos, a clear button "Launch a fund with these N", and "Clear". At 30 the ring turns the caution blue, a line says "30 is the limit: remove one to add another", and the remaining + buttons are disabled. The tray must never cover table rows (bottom padding) and works at 390px.
9. Degen meter (Top Picks cards and Apps table): keep what it measures (a risk level 1 to 10, higher is riskier) and make the scale readable: on cards a full-width bar labelled "Degen meter", the value "4/10" at the end of the fill and no band word above it (no "Spicy" label), end labels "Blue chip" and "Casino", empty segments faintly tinted by their zone, and the existing tooltip; in the table the compact bar followed by "N/10".

Hard rules:
- Honest colour. The stage (hot, emerging, fading, falling) colours only the card edge and the pill. The return colours only its own number, green or red by the existing rounding rule. A hot sector whose fund is down still shows a red negative number with a real minus sign. Never hide, mute, reorder by return, or invent data (no made-up sparklines).
- Keep every existing state and text: no fund yet, new with no return yet, loading.
- Phone (390px): cards stack, no horizontal scroll, nothing pushed off screen; the flagship becomes name, number, then a full-width button.
- Accessibility: no interactive element nested in another, visible keyboard focus, AA contrast, tooltips on hover, focus and tap, reduced motion respected.
- Use the page's own colours and fonts and the data it already loads. No new data source.
```

## Check before submitting
- The account is on a paid Nexus plan (our key reads Pro from `/nexus/usage`; confirm before filing).
- Filing costs allowance (0.5 unit per the page) and starts a public ticket with a 24 h clock. That is the operator's decision to take.
