# Build it Better: next request for gem-screener (draft, not sent)

Operator's text, 2026-09-29, verbatim (four parts at `2054d2b`, which applies the QA review below;
it replaced `0a185e8` and, before that, a three-part text at `3d8719f`). File it only
when ET-27671 has shipped: while it is open, a second request for the same app returns ET-27671's
status and creates nothing (2026-09-27, MSG-0085 / ET-27886). Needs `build-it-better.key`, which is
not in a cloud session.

```
This request has four parts — do all four, each to its own checklist:
1. Altseason panel: https://github.com/zakutana/gem-screener/blob/2054d2b/docs/altseason-panel/SPEC.md
2. Chain valuation (Chains tab): https://github.com/zakutana/gem-screener/blob/2054d2b/docs/chains-valuation/SPEC.md
3. Sectors tab themes: https://github.com/zakutana/gem-screener/blob/2054d2b/docs/sectors-tab/SPEC.md
4. Degen level in the Apps row and the redesigned coin detail: https://github.com/zakutana/gem-screener/blob/2054d2b/docs/degen-level-detail/SPEC.md
```

Before filing: the spec check (`test_a_spec_written_after_their_fix_keeps_every_line_and_change`)
found ET-27671's spec had lost 27 request lines and one BB-CHANGE. Re-run it against the shipped
build first. The QA review of the four specs is `outbox/gem-screener-4-part-review.md`.
