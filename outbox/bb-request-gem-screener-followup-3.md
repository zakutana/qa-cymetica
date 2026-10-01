# Build it Better: Gem Screener, changes after ET-28688 (paste-ready, not filed)

The spec is `gem-screener-followup-3/SPEC.md` of this folder: 23 items, 64 checklist lines, one asset (`assets/benchmark-badge-adoption.svg`) and two references (`reference/benchmark-badge-preview.svg`, `reference/app-detail-mock.svg`). It covers the Chains tab (which chains it lists, what a chain's adoption is, the benchmark and its badge, the chart column and card) and a clean-up of what the owner reads: the coin's and the chain's detail, the Top Picks page, the Sectors table and the size of the badges. Not in it, because they are in hand: the orange for warnings (item 7 of ET-28688) and the altseason universe without assets priced at a currency unit (item 35 of ET-28606; their answer of 2026-10-01, REPLY-0111: fixed under ET-28688).

Made from `gem-screener-next-wishes.md` (the working notes and the numbers behind it).

## State (2026-10-01, evening)

1. **Uploaded** at the operator's word: commit `e53ac518ac00cfea0f5717ee1a348a534b514658` on `main` of `zakutana/gem-screener`, as `docs/followup-ET-28688/` (`SPEC.md`, `assets/`, `reference/`), pushed from a clean temporary checkout so that nothing else of that repository was touched.
2. **Checked:** the four files read back from GitHub are byte for byte this folder's (0 differences; line endings aside), and the blob link answers HTTP 200.
3. **Not filed.** Filing is the operator's step. A request after a ticket has shipped opens a follow-up ticket; ET-28688 is still building (deadline 2026-10-02 10:23 UTC, a second build, ET-28704, runs beside it), so this waits for it to ship unless the operator decides otherwise.

```
This request has one part, to its own checklist: https://github.com/zakutana/gem-screener/blob/e53ac518ac00cfea0f5717ee1a348a534b514658/docs/followup-ET-28688/SPEC.md
```
