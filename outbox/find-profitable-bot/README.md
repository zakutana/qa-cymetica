# "Find me a profitable bot" (draft, not filed)

Build it Better request for the Quant Lab doing the search for the owner (2026-10-25), in the Pro plan. Text: `build-it-better/improvements.txt`
(3,211 characters of the form's 8,000, 9 lines; since 2026-10-25 evening it also extends the live Experiments page,
`/company/app/experiments`, ET-32479's list of paper clones: count against the plan's cap, a link to each bot's configuration, the held-back result,
and a memory of every combination tried, the operator's "it is a research lab"). App: `https://cymetica.com/company/app` (the Quant Lab is a department of Build a Company; the
platform pieces it needs are owner-only API routes on the cloned bots; the one button on `/my-agents` is a later second door). The operator files it.
The first draft put the button on My Agents; the operator said the button was only a picture and the Quant Lab department should do it, so the
request was rewritten around the department (same four-step design, same conditions).

Its design is Nexus's own (REPLY-0216, MSG-0248): every bot model with a backtest setup x every market with enough history, a small grid of
settings on the earlier part, ranked on a held-back period the search never saw with a much higher bar, the top few handed back as ready
paper clones. Nexus said it is not built, no price, no date, no roadmap statement. We add: Pro plan only, results that show their sign and
trade count, the held-back period never shown to the search, every combination tried counted, an owner-only API for the Quant Lab
department, a visible tag on the 19 models that have a backtest setup, and capacity (25 clones per run for the whole platform is too small).

2026-10-25, MSG-0249 / REPLY-0217: Nexus has no roadmap entry, no date and no plan tier for the button, and says to file a Build it Better request;
the button's page is `/my-bots`, which is the same page as `/my-agents` (title "My Agents", checked), `/agents` the fallback. So the draft's app stays
`/my-agents`. When the operator files it, its ET number goes here and the verdict is ours.

Checked with our key on 2026-10-25 (GET only): `GET /api/v1/cloned-bots/{id}/optimizations` answers for all 70 of our clones, levers and
bounds as Nexus described, Auto-optimize off on all; 7 of the 70 are trading and none has a proposal yet.
