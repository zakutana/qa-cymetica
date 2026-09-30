# Předání z cloudové session (2026-09-30) do lokálu

Větev `claude/determined-ramanujan-u8lwzx`, přes 30 commitů před `main`, nic za `main` (jde slít rychle dopředu). Podle CLAUDE.md se commituje do `main`; push dělá operátor po `/code-review`.

## Udělat lokálně

1. Větev slít do `main`. Před pushem `/code-review` nad `qa/state.py` (`record_digest`, `record_digests`: hash run záznamu nezávislý na CRLF/LF), `scripts/ledger.py`, `tests/meta/test_pipeline_tamper.py`, `tests/meta/test_pipeline_render.py` (výstup harnessu přes soubor, ne stdout).
2. `python scripts/render.py` (dashboard v cloudu záměrně nevykreslen, `stats` by degradoval; sweep je commit d2ec6d61). `tests/repo`: 8 testů bylo červených jen v cloudu, lokálně mají být zelené.
3. Podat dva nepodané řádky (B04 a 27 ztracených řádků ET-27671) a re-reporty: v cloudu chybí `.env`.
4. `pyproject.toml`: chybí `requests`; `requires-python` říká >=3.11, ale `scripts/prereg.py:104` potřebuje 3.12.
5. Ranní přehled laborky je publikovaný na https://claude.ai/artifact/DhhHhqc4kVQV6ydaXwe1B5. Adresa je zapsaná v `state/lab/` (gitignorováno), takže lokálně: `python scripts/lab.py morning --published https://claude.ai/artifact/DhhHhqc4kVQV6ydaXwe1B5`, jinak by lokál publikoval nový.

## Gem Screener a Cymetica

- Verdikty ET-28378 (části 2, 3, 1 pass, část 4 fail) jsou dané, poznámka i Telegram poslané. Text: `et28378-verdict.md`. Výtky operátora: `et28378-complaints.md`.
- Nový Build it Better request: `bb-request-gem-screener-followup.md` (jen nová přání, 22 řádků). Operátor ho podává ve web formuláři, po první chybě „too many requests" za hodinu. Pak zkontrolovat BB-SPEC řádek po řádku proti `gem-screener-followup-requirements.md`.
- Vendor slíbil opravit z poznámek ET-28378, ET-28319 a ET-27875 (2026-09-30 ráno). Board ve 07:30 beze změny. Jejich report ověřit proti našim poznámkám, ne brát jako fakt.
- Odložené na příkaz operátora: míra „Hot now" u sektorů (`et28378-complaints.md`).
