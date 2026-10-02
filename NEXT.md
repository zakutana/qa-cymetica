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
- [ ] 2026-09-23  Zbytky V3 (memecoiny), detail v plánu pod V3: pravidlo mimo vzorek -- vzor, který si sami napasujeme, dostane datum a soudí se jen na datech po něm. Dnes k němu v kódu není co připnout (stopy jsou sken, NEX-0055/0057 jsou Nexusovy).
- [x] 2026-09-28  V3: hloubka při signálu + strop prodeje ve `stop_study`/`stats`/košíku, přepnuté páry jako rugy, test L553 rozdělen (stop −10 %: −9,1 % → −17,2 %); V4: prořez neciterovaných stránek event-cards po 1 dni (1d419933). (hotovo 2026-09-28, 4bc5baf8)
- [x] 2026-09-23  Bollinger Bandit (klon 36642175) se 23. 9. zastavil sám a důvod není nikde: kontrola proti jejich dokumentované smlouvě + report přes submit.py. Napřed jedno volání `POST /api/v1/backtest-labs/autopsy` (REPLY-0049: `stop_reason` je jen tam a chce run, který klon nemá). (REPLY-0067: zastavil ho vlastní TP/SL; že řádky důvod nenesou, uznali a slíbili opravu -- nahrazeno řádkem níž; hotovo 2026-09-25)
- [x] 2026-09-25  REPLY-0067 slibuje v příštím vydání: řádky my-clones nesou `auto_pause_reason`, `auto_pause_pnl_pct`, `auto_pause_at` a vlastní stop/target, a `GET /api/v1/agents/instances/{id}/events`. Po vydání ověřit na klonech z 24. 9. a Bollinger Bandit; chybí-li, kontrola + report. (ověřeno živě 25. 9.: všech 15 klonů nese důvod, /events vrací časovou osu; hotovo 2026-09-25)
- [x] 2026-09-23  Kontrola: každý `/api/v1/…` z jejich veřejných stránek (creator, head-to-head, `run-backtest`) je v `openapi-public.json`; SAFE, chybějící jedním reportem. Operátor 24.9.: nedávají do dokumentace. (živě chybí 12, podá sweep; hotovo 2026-09-28, 14d13632)

- [x] 2026-09-22  Po PRE-0159 (úroveň V): podat report AIB-Privacy (řádek NOT RAISED YET) přes `submit.py --only`. #117/#119/#123: `correction_owed` dál neposílat, dokud kontroly soudí zápisy před opravou -- nejdřív nový zápis (`paper.py buy` a4a5b71e, klon), pak `verify.py`. (AIB-Privacy podán jako #126; #117 a #126 ověřeny novými nákupy a pass poslán; zbytek řádkem níž; hotovo 2026-09-25)
- [x] 2026-09-25  #119: `correction_owed` neposílat, chce nový pokus o klon (`clone.py clone`), pak `verify.py --only`. (#123: kontrola soudí jen podání po jejich opravě, rozhodne po 12 čistých, 1196cd3a.) (CLN-0066: 409 ALREADY_CLONED s důvodem, PRE-0166 VERIFIED FIXED, pass poslán; hotovo 2026-09-25)
- [x] 2026-09-24  Boti head-to-head po dávkách (operátor 24. 9. večer: „všechny otestuj“): 27. 9. uzavřít STR-0044/0046, pozastavit je a pustit další dávku (Divergence Dragon a perpetual agenti); vylepšené boty Cymetiky přidat, až půjdou poznat přes API. (STR-0046 +0,54 % vs benchmark +0,96 %, všichni čtyři na TP; 2. dávka STR-0064–0068, room na bota, 10 soubojů; hotovo 2026-09-28)
- [x] 2026-09-28  Karty: prodej na jeho TP/stopu, a kde dal stop, náš 10 % od špičky neplatí (8e389c0b, aa3ade39). (hotovo 2026-09-28)
- [ ] 2026-09-28  Sledovat: verdikty STR-0064–0068; bot STR-0069 (obchod mimo karty = kontrola + report); #134 na prvním stop-lossu; #142 Chart Analyzer; #136, #121, skill_ids #51 (fail poslán, čeká na jejich opravu); ET-28378/28319/27875 po řádku; BB-SPEC Gem Screeneru.
- [x] 2026-09-25  Creator reply queue: uříznuté odpovědi, špatné štítky, prázdný `link_slug` (MSG-0061/62). (REPLY-0069: opraveno u nich, ověřeno živě -- 0 z 200 nových draftů uříznutých, 462/503 přeštítkované; report se nepodává; hotovo 2026-09-25)
- [x] 2026-09-25  Opravit dvě naše kontroly, obě padají falešně, nic se nezakládá: fund leaderboard (`rows_of` čte po jejich ET-27387 návratnost jako index) a BB-SPEC na ET-26924 (neumí stažené BB-CHANGE). Test napřed, pak běh. (hotovo 2026-09-26, 18d130af, PRE-0184 obě prošly)
- [x] 2026-09-26  #132: qa_answer k A2A-0013 vs Telegram, pak PRE+ledger. (A2A-0013 dostala jen kopii z Telegramu, ale kontrola soudí 5 nejnovějších -- A2A-0026..0030 dostaly šetření do hodiny; PRE-0208 V, pass poslán na #132 i #137; hotovo 2026-09-30)
- [x] 2026-09-26  Hlídat kredit Nexuse: tick čte `GET /api/v1/nexus/usage` (items, týden/5 h) a /lab ho ukazuje; k tomu počet odmítnutí „Hourly deep-answer limit“ za hodinu z nexus.jsonl -- ten limit v /usage není. Test napřed. (hotovo 2026-09-28, d3aba435)
- [ ] 2026-09-24  Degen prompty přes `POST /api/v1/chat/stream`: účet paper (simulation_mode=True 30. 9.); ET-28541: nástroje rozhodují samy, žádné potvrzení neschvalovat, clone/arena z chatu odmítnuty, prompt 7 dělá VEŘEJNOU kartu -- vynechat. Chybí klient pro chat/stream (SSE), room na prompt.
- [x] 2026-09-22  Arena: čtení ceny podílu BLUE/RED pro verdikt (`series_of` dnes vrací mezeru). NEX-0076: podíl se nevyplácí, má cenu na CLOB 0,01–1 $; zdroj `get_arena_orderbook` (nejdřív do `components.yaml`) nebo `GET /api/v1/arena/market`. (hotovo 2026-09-28, da3d540e)
- [x] 2026-09-21  ET-26036: čekáme na obrazcovou TA (REPLY-0042 ji slibuje; verdikt zůstává fail, MSG-0038). (znovu přečteno lovem 1. 10., beze změny, pokračuje řádkem níž; hotovo 2026-10-01)
- [ ] 2026-10-01  ET-26036 dál jen indikátorová půlka: /weekly-signal 1. 10. píše „No chart patterns are detected“, obrazce navrženy jako feature 791. Až se pohne: definice obrazců, kombinace s RSI/MACD, backtest (základ, po aktivech, 90% verze), graf. Verdikt s operátorem.

- [x] 2026-09-21  Laborka: verdikty STR-0006/0007 (kritérium naše výchozí, ne jeho TP/SL); při 6 uzavřených verdiktech `lab.py grade` -- předpovídá brána? (obě vyvrácené; grade: řazení podle Sharpe nepředpovídá nic, obě poloviny 0 %; LAB-0028; hotovo 2026-09-30)
- [x] 2026-09-28  Hot blok v `lab.py brief`: kolik vstupů projde NEX-0055/0057 za sledované hodiny, a při „skoro nic" číslo pro Nexuse (hotovo 2026-09-28, f1439d97)

- [x] 2026-09-29  `qa/fomo.py::curves()` pořád čte syrový `return_pct`, ne `_no_pair_gain` -- stejná třída jako B03 (deep pass 2026-09-28), ale kreslí čáru, ne buňku tabulky; žádné hlasování ho tento pass nejmenovalo. (čára platí po přepnutí páru nejvýš 0 %, test napřed; hotovo 2026-09-30)
- [x] 2026-09-29  `scripts/lab_page.py::lab_view`'s `in_bots` sčítá jen `clones[-1]["balance"]` na room bota, takže dávkový room podhodnotí ostatní klony; našlo se při A02 (deep pass 2026-09-28), žádné hlasování ho nejmenovalo. (sčítá všechny klony roomu, test napřed; hotovo 2026-09-30)
- [ ] 2026-09-30  ET-28597 (Gem Screener: Strength 3M, trajektorie, growth 6M, podíl holderům, cov30): REPLY-0105 je od nízkého agenta, čekáme na nadřízeného. Co označí za bug nebo nevysvětlí (holders >100 %, growth 6M bez mezer): kontrola + submit.py; doc-gap jen sledovat.
- [ ] 2026-09-30  Altseason Retail: po pondělním razítku 5. 10. má řádek „Top crypto app" dostat skóre (psali „scored from the next weekly close"), průměr ze 4 řádků místo 3. Ověřit na stránce; když ne, otázka na Cymetiku.
- [x] 2026-10-01  Gem Screener request: operátorův agent doplní bod 53 do specu na GitHubu a vrátí nový hash; ten dosadit do outbox/bb-request-gem-screener-followup.md (platí 3ef7f0cf BEZ bodu 53), ověřit, že je spec shodný s outbox/gem-screener-followup-SPEC.md. Pak podání a BB-SPEC. (hash c7bd4767 dosazen a ověřen, 0 rozdílů; zbývá podání a BB-SPEC, ten je v řádku „Sledovat"; hotovo 2026-10-01)
- [ ] 2026-10-01  Ověřit živě ET-28688 (17 bodů + 390 px) a ET-28704 (13 bodů CA); REPLY-0107/0108. ET-28821 zavřen; změny z MSG-0108 chtějí jako nový request. Supply Analyzer ET-28934 přijat 2. 10. 08:20, termín 3. 10. 08:20 UTC: ověřit proti 33 řádkům specu 5f113b9 (outbox/bb-request-supply-analyzer.md). ET-28799.
- [ ] 2026-10-01  Až Cymetica dodá bod 53 specu (agent najde Gem Screener hned): kontrola vstupních bodů (první obrazovka llms.txt, MCP `instructions`, agent card, sitemap, slug místo tickeru) a zkouška čerstvým agentem „find me top crypto gems".
- [ ] 2026-10-01  Async a2a kontrola: inbox bez `limit` vrací jen 50 nejnovějších (PRE-0214: nejstarší 26. 9.); `limit=100` funguje, nezdokumentovaný. Číst s `limit` a zprávu starší než nejstarší vrácenou soudit jako nejistou, ne chybějící. Test napřed.
- [ ] 2026-10-01  Nexus znovu vybral druh, který už máme naklonovaný (NEX-0109: Fibonacci Phoenix, CLN-0011 uvolněn 28. 9.), a tick ho drží „not cloned again“. Nastavení (watchlist UNI,ZEC, stop −8, TP +12) pustit jako variantu v novém roomu na našem klonu (settings PATCH + enable). Test napřed.
- [x] 2026-09-30  Po cloudové session: číst outbox/cloud-handover.md (render.py, /code-review nad qa/state.py, 2 nepodané řádky, adresa ranního přehledu, pyproject requests + py3.12, Gem Screener request). (B04 podán jako #138; „ztracené řádky" ET-27671 byla naše kontrola, opravena, a z ní #139 -- log BB useká na 8000 znaků; /code-review a Gem Screener request jsou operátorovy; hotovo 2026-09-30)
