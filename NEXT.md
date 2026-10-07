# Next

Co jsme se domluvili, že je další krok. Ne to, o čem má rozhodnout operátor —
to patří do `DEEP-PASS.md` pod *Čeká na tebe*. Sem jde jenom práce, která je
už rozhodnutá a ještě není udělaná.

`.claude/hooks/session_start.py` z toho na začátku každé session vypíše počet
otevřených a první z nich; celé se čtou odsud. Otevřených je nejvýš deset, po
nejvýš 300 znacích (plán v2, V7) -- detail patří tam, kde je práce.

Formát je závazný, protože ho čte hook i test:

```
- [ ] YYYY-MM-DD  věta, co se má udělat
- [x] YYYY-MM-DD  hotová položka se přestane vypisovat (hotovo YYYY-MM-DD)
```

Datum vpředu je den DOHODY. Kdo položku odškrtne, připíše na konec
`(hotovo YYYY-MM-DD)` -- od toho dne se počítá týden, po kterém ji krok 10b
deep passu smaže (git ji drží dál). Bez razítka se počítá od dohody, takže
zmizí dřív, ne později. Co je otevřené déle než čtrnáct dní, shodí
`tests/repo/test_next_step.py` — buď se to stalo a nikdo to neodškrtl, nebo to
nikdy nebylo další na řadě.

---

- [x] 2026-09-23  Plán v2 (`docs/laborator-plan.md`): otevřená fáze V11 (čeká na ranní vydání), stav v tabulce plánu. Po prvním dni smyčky ověřit řádky `answer_read` (V5). Nákladová kritéria V6 zrušil operátor 25. 9. (limity hlídá sám). (V5: 11 řádků answer_read; V11: acted se v dalším přehledu ukáže; hotovo 2026-09-30)
- [x] 2026-09-23  Zbytky V3 a V4, část: `console.cmd --fomo 1` se stropem quote za kolo (60 za minutu intervalu), C6 prozkoumáno (kód beze změny). Horizonty zůstaly hodinové kvůli [operator 2026-09-13]; detail v plánu. (hotovo 2026-10-01)
- [ ] 2026-10-03  Výzkum botů, VŠE v docs/bots-research-plan.md „Zbývá": sampler musí běžet, wave 0 verdikt ~10. 10., vlna 2 s parametry, F1 kód (strop, víc klonů/druh), H2H do /lab, tool pro vlnu, degen prompty, karty: `scripts/card_rules.py` po ~10. 10., odpovědi Cymetiky (409, skilly).
- [x] 2026-10-03  Dopředný test dvou pravidel pro karty (short jen akcie, long s kryptem), soudí jen karty vzniklé od 4. 10.: `python scripts/card_rules.py` (hotovo 2026-10-04, 8d4ddfd1)

- [ ] 2026-09-28  Sledovat: verdikty STR-0064–0068; bot STR-0069 (obchod mimo karty = kontrola + report); #142 Chart Analyzer; #136, #121, skill_ids #51 (fail poslán, čeká na jejich opravu); ET-28378/28319/27875 po řádku; BB-SPEC Gem Screeneru; #175 po opravě kontroly změřit znovu.
- [x] 2026-09-26  #132: qa_answer k A2A-0013 vs Telegram, pak PRE+ledger. (A2A-0013 dostala jen kopii z Telegramu, ale kontrola soudí 5 nejnovějších -- A2A-0026..0030 dostaly šetření do hodiny; PRE-0208 V, pass poslán na #132 i #137; hotovo 2026-09-30)
- [x] 2026-09-24  Degen prompty přes `chat/stream` (paper): klient `scripts/chat.py` hotov, běželo 9 a 8. Zbytek (room na prompt) přesunut do docs/bots-research-plan.md „Zbývá", kde sedí s ostatním výzkumem botů. (hotovo 2026-10-04)
- [x] 2026-09-21  ET-26036: čekáme na obrazcovou TA (REPLY-0042 ji slibuje; verdikt zůstává fail, MSG-0038). (znovu přečteno lovem 1. 10., beze změny, pokračuje řádkem níž; hotovo 2026-10-01)
- [ ] 2026-10-01  ET-26036 dál jen indikátorová půlka: /weekly-signal 1. 10. píše „No chart patterns are detected“, obrazce navrženy jako feature 791. Až se pohne: definice obrazců, kombinace s RSI/MACD, backtest (základ, po aktivech, 90% verze), graf. Verdikt s operátorem.

- [x] 2026-09-21  Laborka: verdikty STR-0006/0007 (kritérium naše výchozí, ne jeho TP/SL); při 6 uzavřených verdiktech `lab.py grade` -- předpovídá brána? (obě vyvrácené; grade: řazení podle Sharpe nepředpovídá nic, obě poloviny 0 %; LAB-0028; hotovo 2026-09-30)

- [x] 2026-09-29  `qa/fomo.py::curves()` pořád čte syrový `return_pct`, ne `_no_pair_gain` -- stejná třída jako B03 (deep pass 2026-09-28), ale kreslí čáru, ne buňku tabulky; žádné hlasování ho tento pass nejmenovalo. (čára platí po přepnutí páru nejvýš 0 %, test napřed; hotovo 2026-09-30)
- [x] 2026-09-29  `scripts/lab_page.py::lab_view`'s `in_bots` sčítá jen `clones[-1]["balance"]` na room bota, takže dávkový room podhodnotí ostatní klony; našlo se při A02 (deep pass 2026-09-28), žádné hlasování ho nejmenovalo. (sčítá všechny klony roomu, test napřed; hotovo 2026-09-30)
- [ ] 2026-09-30  ET-28597 (Gem Screener: Strength 3M, trajektorie, growth 6M, podíl holderům, cov30): REPLY-0105 je od nízkého agenta, čekáme na nadřízeného. Co označí za bug nebo nevysvětlí (holders >100 %, growth 6M bez mezer): kontrola + submit.py; doc-gap jen sledovat.
- [ ] 2026-10-07  Boti: platforma pauzuje klon na prvním SL/TP (NEX-0124, llms.txt), obnoví ho toggle-trading. `bot_stops`/`restart_refusal` to berou za „their_guard" a nikdy nerestartují: SL/TP je naše pásmo, ne nález. Test napřed, pak nové okno (room + kritérium dřív).
- [ ] 2026-10-05  Spec Gem Screener (větev spec-followup-2026-10-04, push na slovo): sektor Launchpads (PUMP, PONS, STONK), vyřazené appky se jménem a důvodem, příjmy+buybacky+spálené %+„raised", velké peněženky (outbox/gem-screener-pipe-pressure.md). STONK (stonk-3) chybí: kontrola.
- [x] 2026-10-07  Díry z revize: reopen místo duplicit, brzda požadavků, vyčerpaný rozpočet není defekt, piny s aktérem, čerstvost deníkové kontroly; /code-review opraven. Odloženo s důvodem: replay ledgeru (runy se prořezávají), drift po částech (chybí mapa kontrola→část), jeden vlastník zápisů (velký refaktor). (hotovo 2026-10-07)
- [x] 2026-10-01  Gem Screener request: operátorův agent doplní bod 53 do specu na GitHubu a vrátí nový hash; ten dosadit do outbox/bb-request-gem-screener-followup.md (platí 3ef7f0cf BEZ bodu 53), ověřit, že je spec shodný s outbox/gem-screener-followup-SPEC.md. Pak podání a BB-SPEC. (hash c7bd4767 dosazen a ověřen, 0 rozdílů; zbývá podání a BB-SPEC, ten je v řádku „Sledovat"; hotovo 2026-10-01)
- [ ] 2026-10-01  ET-28688/28704 a REPLY-0107/0108 ověřeno 2. 10. (selhání: hlavička 194 px na 390, ořez jména, klik na tooltip „Hot", 60 svíček) -- zpráva na Telegram. Změny z MSG-0108 = nový request. Supply Analyzer ET-28934: termín 3. 10. 08:20 UTC, ověřit proti 33 řádkům. ET-28799.
- [x] 2026-10-02  ET-29001 Chart Analyzer, „top expert“ (13 řádků, text v `improvements` na tabuli): akceptováno, termín 3. 10. 14:10 UTC. Ověřit živě řádek po řádku (verdikt POP/DUMP/NO EDGE, kalibrace, ledger, struktury, objem zapnutý, Weekly Signal sloučen); „shipped“ nestačí. (6 PASS, 5 PARTIAL, 2 FAIL, outbox/chart-analyzer-verification.md; podáno #152–#155; hotovo 2026-10-04)
- [x] 2026-10-02  Gem Screener: FDV = mcap a „100 % venku" ignoruje max_supply (ORE 3 M, venku 17 %; 17 z 214 apek, ověřeno 3. 10.). Operátor: počkat na Supply Analyzer ET-28934 (termín 3. 10. 08:20 UTC, zatím queued). Pak znovu; když platí, kontrola + submit.py. (4. 10. platí: 9 z 211, ORE dál 100 % venku; kontrola + #162, Supply Analyzer #156–#161; hotovo 2026-10-04)
- [ ] 2026-10-01  Až Cymetica dodá bod 53 specu (agent najde Gem Screener hned): kontrola vstupních bodů (první obrazovka llms.txt, MCP `instructions`, agent card, sitemap, slug místo tickeru) a zkouška čerstvým agentem „find me top crypto gems".
- [x] 2026-10-01  Async a2a kontrola: inbox bez `limit` vrací jen 50 nejnovějších (PRE-0214: nejstarší 26. 9.); `limit=100` funguje, nezdokumentovaný. Číst s `limit` a zprávu starší než nejstarší vrácenou soudit jako nejistou, ne chybějící. Test napřed. (limit=200 je jejich maximum, plná stránka = nejisté, test napřed, PRE-0226; hotovo 2026-10-02)
- [x] 2026-10-01  Nexus znovu vybral druh, který už máme naklonovaný (NEX-0109: Fibonacci Phoenix, CLN-0011 uvolněn 28. 9.), a tick ho drží „not cloned again“. Nastavení (watchlist UNI,ZEC, stop −8, TP +12) pustit jako variantu v novém roomu na našem klonu (settings PATCH + enable). Test napřed. (opraven hlídač: uvolněný klon se nepočítá jako vlastněný, test napřed; watchlist se nepouští, clone.py ho z PATCH vyloučil záměrně a odpověď je stará přes 24 h; hotovo 2026-10-02)
- [ ] 2026-10-04  Další spec pro Supply Analyzer (staking/lock): žádný jeden zdroj nepokryje 244 coinů; spojit řetězcová data tam, kde je kontrakt znám (PHAR xPHAR, CRV veCRV), DeFiLlama jako záloha. Dnes staking u 68 z 244, tok nikde. ET-29381. Připomenout operátorovi.
- [ ] 2026-10-04  11. 10.: připomenout operátorovi test X (jeho odpovědi nejsou vidět): otevřít odpověď v anonymním okně. Do té doby žádné odpovědi s odkazem ani šablonou, jen vlastní tweety a lajky. Podle výsledku další týden, nebo Premium.
- [x] 2026-09-30  Po cloudové session: číst outbox/cloud-handover.md (render.py, /code-review nad qa/state.py, 2 nepodané řádky, adresa ranního přehledu, pyproject requests + py3.12, Gem Screener request). (B04 podán jako #138; „ztracené řádky" ET-27671 byla naše kontrola, opravena, a z ní #139 -- log BB useká na 8000 znaků; /code-review a Gem Screener request jsou operátorovy; hotovo 2026-09-30)
