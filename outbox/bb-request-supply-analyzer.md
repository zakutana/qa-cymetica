# Build it Better: the Supply Analyzer (paste-ready, not filed)

The spec is `supply-analyzer/SPEC.md` of this folder: 14 items, **30 checklist lines**, one working reference page (`reference/supply-analyzer-hyperliquid.html`, with two screenshots of it) and two SVG mocks (`input-page.svg`, `gem-screener-integration.svg`). It asks for a new standalone app built like the Chart Analyzer (type any token, a result page with an animated tank, a pie and a month slider; an API and an MCP tool) and for its place in the Gem Screener (a Supply column in Apps and Chains, a Supply pressure card in a coin's and a chain's detail, one schedule for both). It names no data source and says the data must be obtained.

## State (2026-10-02)

1. **Uploaded** at the operator's word ("pushni ho a dej link"): commit `8b3fecdf78bcbff48c4b308d5b5bf8e399a980a7` on `main` of `zakutana/gem-screener`, as `docs/supply-analyzer/` (`SPEC.md`, `reference/`), pushed from a fresh temporary clone so that nothing else of that repository was touched. It sits on top of `08528943`, spec 3's commit.
2. **Read back** from GitHub at that hash: `SPEC.md`, the HTML and both SVGs byte for byte the local ones (0 differences, line endings aside), both PNGs the same sha256, and the blob and tree links answer HTTP 200.
3. **Reviewed once**, by me against the conversation's asks and by one advisor pass; both found two things (the team-tranche caveat, the line count), both fixed before the upload.
4. **Not filed.** Filing is the operator's step.

## How to file it

- **Pre-flight:** every Gem Screener and Chart Analyzer ticket is `shipped` (ET-28821 at 2026-10-01 23:40 UTC, read from the public list), so no open ticket can refuse the request.
- **As an idea, a new app.** The Chart Analyzer was requested that way: ET-27875 has `is_idea: true`, no app URL and `our_url: /chart-analyzer`; its follow-up ET-28324 then named the app. So in the form: a new idea, not an existing app. Items 8 to 10 change the Gem Screener; if an idea ticket cannot touch another app, say so and split those three off as a follow-up on the Gem Screener once the app is live.
- The BB limits: `improvements` up to 8,000 characters, at most 40 items; this is one line.

```
Supply Analyzer: a new app, like the Chart Analyzer. Type any token and see its supply as a flow, month by month: what can be sold, what pours in, what is taken out, and one number. It must work for every token in the Gem Screener and for any token a user types, and it is wired into the Gem Screener (items 8 to 10). This request has one part, to its own checklist: https://github.com/zakutana/gem-screener/blob/8b3fecdf78bcbff48c4b308d5b5bf8e399a980a7/docs/supply-analyzer/SPEC.md
```

## What is not in it, on purpose

The other draft, `gem-screener-followup-4/SPEC.md` (the pipe), is partly superseded by this one; its items 4 to 6 (what a "0%" says, insiders moving tokens, ETH/BTC) are still open and are not in the Supply Analyzer. The changes listed after ET-28821 (MSG-0108) stand as their own item.
