# Build it Better: Gem Screener, changes after ET-28688 (paste-ready, not filed)

The spec is `gem-screener-followup-3/SPEC.md` of this folder: 26 items, 76 checklist lines, one asset (`assets/benchmark-badge-adoption.svg`) and three references (`reference/benchmark-badge-preview.svg`, `reference/app-detail-mock.svg`, `reference/top-picks-mock.svg`). It covers the Chains tab (which chains it lists, what a chain's adoption is, the benchmark and its badge, the chart column and card), a clean-up of what the owner reads in a coin's and a chain's detail, revenue and dilution kept apart with Dilution as the seventh gate, the Top Picks page (the gates drawn, the near-misses lane, the Hot sectors and pick cards), the Sectors table, a Launchpad link on Memecoins, links that open in a new tab and the size of the badges. Not in it: the colour of the warnings (item 7 of ET-28688; their answer of 2026-10-01, REPLY-0114: the question stays open with their team) and the altseason universe without assets priced at a currency unit (item 35 of ET-28606; fixed and published at 19:32 UTC, REPLY-0113).

Made from `gem-screener-next-wishes.md` (the working notes and the numbers behind it).

## State (2026-10-01, evening)

1. **Uploaded** at the operator's word ("tak to pushni a dej mi ten spec"): commit `08528943b1131743f29d918e6996a13368133d4c` on `main` of `zakutana/gem-screener`, as `docs/followup-ET-28688/` (`SPEC.md`, `assets/`, `reference/`), pushed from a fresh temporary clone so that nothing else of that repository was touched. It replaced `4d77a668` (24 items) and `e53ac518` (23 items), which stay valid addresses.
2. **Checked:** the five files read back from GitHub at that hash are byte for byte this folder's (0 differences; line endings aside), and the blob link answers HTTP 200. This is the final-reviewed spec: 26 items, 76 checklist lines.
3. **Filed and accepted** as ET-28821 (BB-ACCEPT 2026-10-01 20:41 UTC, deadline 2026-10-02 20:41 UTC). To verify the build, read the 76 checklist lines of the SPEC.md at this hash against the live page.
4. **Not re-checked in the final review (2026-10-01):** the chain numbers of items 1 to 6 (adoption order, Upside list, held-back shares, 59/47 tokens) were computed that morning and not recomputed on the 19:32 UTC snapshot; the Chart Analyzer coverage of item 7 (292 symbols, 33 of 42 tokens) was not re-read after ET-28704; the "item N of ET-28688 / ET-28606" references were not re-opened. Left as it was on purpose: `declining_trend` stays in the Vetted gate (it removes 45 apps, 7 only for it, none of them a pick).
5. (history) **Not filed.** Filing is the operator's step. ET-28688 and ET-28704 shipped on 2026-10-01 at 19:41 UTC (PASS at 19:44), so nothing blocks it; a request after a shipped ticket opens a follow-up ticket.

```
This request has one part, to its own checklist: https://github.com/zakutana/gem-screener/blob/08528943b1131743f29d918e6996a13368133d4c/docs/followup-ET-28688/SPEC.md
```
