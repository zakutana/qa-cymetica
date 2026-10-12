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

- [x] 2026-10-11  Před „zapni laborku“ (C9) nejdřív body 1–8 z docs/crew-before-c9.md (deep pass 11. 10.): špinavý strom bez majitele, zápis „odesláno“ za operátora, cizí BB tikety, hold v jednom Bash volání, zaseknutý tick, push přes testy, poznámka manažera = data, skill. Testy napřed. (hotovo 2026-10-12 na operátorovo slovo; body 9–11 zbývají)
- [ ] 2026-10-12  Firma, body 9 a 11 z docs/crew-before-c9.md: mřížka botů zkouší odmítnutý klon každý tik (a nepropojené klony po timeoutu); outcome() viděl jen falešné CLI, outsider-act exit, metrics bez since, rotace sběrnice. Bod 10 je řádek FOMO níž.
- [ ] 2026-10-11  Firma (docs/crew-plan.md): C0–C8 hotové (627f4a3e). Zbývá C9: start jen na „zapni laborku“ (`claude` přihlášený 11. 10.); první den pak `crew.py status` a `crew.py audit`.
- [ ] 2026-10-11  Laborka v3 (docs/laborator-plan.md) postavená, P3, P4, P5, P6, P7 čekají na tahy: v prvním `python scripts/lab.py launch NEX-0137`; outsider až po přihlášení `claude` a `outsider.py probe`. Zbytek výzkumu botů: docs/bots-research-plan.md „Zbývá".
- [ ] 2026-10-11  FOMO sběr: 9. 10. 48 557 dotazů na cymetica.com, 39 784 na nezdokumentované /clones/memecoin-terminal/search; REPLY-0030 žádá žádnou zátěž. Denní strop ve fomo_watch a denní strop requestů v patrolu (dnes jen špička za minutu). docs/crew-before-c9.md bod 10; bod 9 grid.

- [ ] 2026-10-08  Sledovat: #142, #136, #121, #51; FOMO #762 (path_coverage Robinhood 0 → 0,9 do ~13. 10., Solana 0,011). #171/#173/#174 selhávají i po opravě. Liga jen na slovo/`/loop`. ET-30676: SaaSHub čeká na review, 3 formuláře u nich; PR awesome-web3 #831 otevřený.
- [x] 2026-10-01  ET-26036 dál jen indikátorová půlka: /weekly-signal 1. 10. píše „No chart patterns are detected“, obrazce navrženy jako feature 791. Až se pohne: definice obrazců, kombinace s RSI/MACD, backtest (základ, po aktivech, 90% verze), graf. Verdikt s operátorem. (10. 10. pořád bez obrazců; čekání na Cymetiku drží nezodpovězené MSG-0035/0051, plán zůstává tady v gitu; hotovo 2026-10-10)

- [x] 2026-09-30  ET-28597 (Gem Screener: Strength 3M, trajektorie, growth 6M, podíl holderům, cov30): REPLY-0105 je od nízkého agenta, čekáme na nadřízeného. Co označí za bug nebo nevysvětlí (holders >100 %, growth 6M bez mezer): kontrola + submit.py; doc-gap jen sledovat. (bod 5 podán jako #179; bod 4 vyřešen, stránka ukazuje surový podíl; 1–3 díry v dokumentaci; hotovo 2026-10-10)
- [x] 2026-10-07  Boti: platforma pauzuje klon na prvním SL/TP; `wave.py resume` je obnoví v novém roomu, 3× stop-loss po sobě = zahozen (operátor). (hotovo 2026-10-07)
- [ ] 2026-10-07  ET-29379 (Gem Screener build): shipped 8. 10. 03:31, ověřeno 45 PASS / 13 čeká (docs/et-29379-verification.md; telefon se neřeší). 15. 10. po týdenním okně dodělat řádky 17-18 a fond vs picks, pak verdikt (jeho). Dál ET-29452 (ET-30025 živě ověřeno 10. 10., REPLY-0138).
- [ ] 2026-10-05  Spec Gem Screener (větev spec-followup-2026-10-04, push na slovo): sektor Launchpads (PUMP, PONS, STONK), vyřazené appky se jménem a důvodem, příjmy+buybacky+spálené %+„raised", velké peněženky (outbox/gem-screener-pipe-pressure.md). STONK (stonk-3) chybí: kontrola.
- [x] 2026-10-07  Díry z revize: reopen místo duplicit, brzda požadavků, vyčerpaný rozpočet není defekt, piny s aktérem, čerstvost deníkové kontroly; /code-review opraven. Odloženo s důvodem: replay ledgeru (runy se prořezávají), drift po částech (chybí mapa kontrola→část), jeden vlastník zápisů (velký refaktor). (hotovo 2026-10-07)
- [x] 2026-10-01  ET-28688/28704 a REPLY-0107/0108 ověřeno 2. 10. (selhání: hlavička 194 px na 390, ořez jména, klik na tooltip „Hot", 60 svíček) -- zpráva na Telegram. Změny z MSG-0108 = nový request. Supply Analyzer ET-28934: termín 3. 10. 08:20 UTC, ověřit proti 33 řádkům. ET-28799. (ověřeno 2. 10., cf4e4f82; ET-28934 ověřen 4. 10., #156–#161; hlavička a ořez jsou kosmetika; Gem Screener teď ověřuje ET-29379; ET-28799 je pravidlo Cymetiky, REPLY-0114; hotovo 2026-10-10)
- [x] 2026-10-01  Až Cymetica dodá bod 53 specu (agent najde Gem Screener hned): kontrola vstupních bodů (první obrazovka llms.txt, MCP `instructions`, agent card, sitemap, slug místo tickeru) a zkouška čerstvým agentem „find me top crypto gems". (čeká na Cymetiku, ne na nás; plán zůstává tady v gitu; hotovo 2026-10-10)
- [ ] 2026-10-04  Další spec pro Supply Analyzer (staking/lock): žádný jeden zdroj nepokryje 244 coinů; spojit řetězcová data tam, kde je kontrakt znám (PHAR xPHAR, CRV veCRV), DeFiLlama jako záloha. Dnes staking u 68 z 244, tok nikde. ET-29381. Připomenout operátorovi.
- [x] 2026-10-08  #175: kontrolu přepsat na jejich nový štítek „synthetic“ (hotovo 2026-10-10, c164b580)
- [x] 2026-10-10  Kontrola, že historie transakcí stránkuje dopředu (hotovo 2026-10-10, 609c4032)
- [x] 2026-10-10  Report přes submit.py: /api/v1/account/me/transactions u USDC (i bez filtru) vrací při dalším offsetu stejnou stránku; endpoint není v žádné dokumentaci. Kontrola už je (609c4032), podá ji příští sweep. (podáno #184; hotovo 2026-10-10)
- [x] 2026-10-10  audits/lab/fomo_signals.jsonl má v gitu 84 MB; nad 100 MB GitHub push odmítne. Snapshot dělit nebo balit, test na strop velikosti. (po dnech, xz, 87 → 5,8 MB; strop 50 MB v HEAD; hotovo 2026-10-11, e450656a)
- [ ] 2026-10-04  11. 10.: připomenout operátorovi test X (jeho odpovědi nejsou vidět): otevřít odpověď v anonymním okně. Do té doby žádné odpovědi s odkazem ani šablonou, jen vlastní tweety a lajky. Podle výsledku další týden, nebo Premium.
- [x] 2026-10-10  Agent Tournaments (BB): opravy zadal agentovi, co psal spec. Až pošle odkaz, porovnat jeho verzi s outbox/agent-tournaments/*.patch (prompty, sekce 7, pin na commit, ≤8 000 znaků), než to podá. Detail: outbox/bb-request-agent-tournaments.md. (hotovo 2026-10-10, 1f9566a)
- [x] 2026-10-11  Dvě kontroly + report přes submit.py: /movers čte 100 z 641 karet; ET-28100 bod 1: 9 trhů jako 4 bez „+5“, „CLOB NONE“. (podáno #189 a #190; „leading“ $0.00 je jejich řazení, nepodáno; hotovo 2026-10-11)
- [x] 2026-10-11  Sampler: kolo (90 s) spolknou 41 boti, karty/pozice/history se přeskakují; seznam botů, pak karty, pak detail botů po kolech (hotovo 2026-10-11, dd4665a7)
- [x] 2026-10-11  Kontrola + report přes submit.py: /agent-tournaments/my-bots nabízí 12 smazaných botů (profile 404), smazaný „lab MACD Hunter“ sedí u stolu 2 s 0 obchody. Telegram MSG-0155 (ET-30773). (podáno #195, 26ef5626; hotovo 2026-10-11)
- [ ] 2026-10-12  ET-30773: vzhled i 3 opravy živé, #196 opraven a zaplacen (12. 10.). Po 19:00 UTC: rozjel se stůl 5 (náš Perceptron Oracle, místo 28 čeká)? Results ověřit po 18. 10. 16:47 UTC (stůl 2). #196 ověří sweep. Detail: docs/et-30773-verification.md.
