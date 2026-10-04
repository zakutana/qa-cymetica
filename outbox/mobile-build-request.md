# Build it Better request: Gem Screener on a phone (DRAFT, not submitted)

Second request, separate from `hot-sectors-build-request.md` so the desktop changes are not held up by the larger mobile work.
Where: https://cymetica.com/build-it-better (form) or `POST /api/v1/build-it-better/requests`.
Gate (live board 2026-10-04): a paid Nexus plan (`request_gate: nexus_build_plan`). The request is public.
Reference for the builder: mockup `mobile-apps-chains-redesign.png`, spec `mobile-apps-chains-spec.md` (the builder cannot open local files, so the block below is self-contained).

## Form fields
- **App URL:** https://cymetica.com/gem-screener/app
- **Improvements:** (paste the block below)

```
Gem Screener on a phone (640 px wide and below). Goals, not methods: how you build it is your call.

Why: on a phone the Apps, Chains and Sectors tabs are hard to use. The first pick is more than a thousand pixels down, behind a large chart; the pick table is wider than the screen so nine of twelve columns are off to the right; the Sectors chart is a box that pans sideways and up and down inside the page; the pinned header and filters take almost half the screen.

Goals:
1. Every tab shows its picks on the first screen. Charts open on request (a clear "Year in a chart" / "Rotation map" control), fit the screen and never pan inside the page.
2. Apps and Chains: one card per project, readable without sideways scrolling. The card face shows the Degen meter, Upside, Revenue 30d, Market Cap and Trajectory; the other columns sit behind a "more" control. Sorting and filters stay one tap away (one control, one sheet).
3. Sectors: sectors as cards grouped by stage, each with 3M and 1M against the median sector and the fundamentals. The first tap on a bubble shows its card and the second opens the sector, as it does today.
4. The pinned header plus filters take at most 110 px. Every tap target is at least 44 px.

Hard rules:
- Desktop layout (above 640 px) must remain exactly as it is today: no change to its CSS, DOM order or behaviour. All phone rules apply at 640 px and below only.
- No new data and no change to any number or label that exists today. Negative numbers keep their minus sign; colour is never the only cue; nothing loops; reduced motion respected.
- The pick checkboxes and the fund tray keep working on a phone.
```

## Check before submitting
- Filing costs allowance and starts a public 24 h ticket: the operator's decision.
- If both requests are filed, file the desktop one first; the two touch different layouts but the same page.
