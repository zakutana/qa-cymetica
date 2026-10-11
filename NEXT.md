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

- [ ] 2026-10-03  Výzkum botů, VŠE v docs/bots-research-plan.md „Zbývá": sampler musí běžet, wave 0 verdikt ~10. 10., vlna 2 s parametry, F1 kód (strop, víc klonů/druh), H2H do /lab, tool pro vlnu, degen prompty, karty: `scripts/card_rules.py` po ~10. 10., odpovědi Cymetiky (409, skilly).
- [x] 2026-10-03  Dopředný test dvou pravidel pro karty (short jen akcie, long s kryptem), soudí jen karty vzniklé od 4. 10.: `python scripts/card_rules.py` (hotovo 2026-10-04, 8d4ddfd1)

- [ ] 2026-10-08  Sledovat: #142, #136, #121, #51; FOMO #762 (backtest panel: path_coverage Robinhood 0 → 0,9 do ~13. 10., Solana 0,011). #171/#173/#174 selhávají i po opravě. Liga: po 2 h, jen na slovo/`/loop`. ET-29325: PR awesome-web3 #831.
- [x] 2026-09-24  Degen prompty přes `chat/stream` (paper): klient `scripts/chat.py` hotov, běželo 9 a 8. Zbytek (room na prompt) přesunut do docs/bots-research-plan.md „Zbývá", kde sedí s ostatním výzkumem botů. (hotovo 2026-10-04)
- [x] 2026-10-01  ET-26036 dál jen indikátorová půlka: /weekly-signal 1. 10. píše „No chart patterns are detected“, obrazce navrženy jako feature 791. Až se pohne: definice obrazců, kombinace s RSI/MACD, backtest (základ, po aktivech, 90% verze), graf. Verdikt s operátorem. (10. 10. pořád bez obrazců; čekání na Cymetiku drží nezodpovězené MSG-0035/0051, plán zůstává tady v gitu; hotovo 2026-10-10)

- [x] 2026-09-30  ET-28597 (Gem Screener: Strength 3M, trajektorie, growth 6M, podíl holderům, cov30): REPLY-0105 je od nízkého agenta, čekáme na nadřízeného. Co označí za bug nebo nevysvětlí (holders >100 %, growth 6M bez mezer): kontrola + submit.py; doc-gap jen sledovat. (bod 5 podán jako #179; bod 4 vyřešen, stránka ukazuje surový podíl; 1–3 díry v dokumentaci; hotovo 2026-10-10)
- [x] 2026-10-07  Boti: platforma pauzuje klon na prvním SL/TP; `wave.py resume` je obnoví v novém roomu, 3× stop-loss po sobě = zahozen (operátor). (hotovo 2026-10-07)
- [ ] 2026-10-07  ET-29379 (Gem Screener build): shipped 8. 10. 03:31, ověřeno 45 PASS / 13 čeká (docs/et-29379-verification.md; telefon se neřeší). 15. 10. po týdenním okně dodělat řádky 17-18 a fond vs picks, pak verdikt (jeho). Dál ET-29452 (ET-30025 živě ověřeno 10. 10., REPLY-0138).
- [ ] 2026-10-05  Spec Gem Screener (větev spec-followup-2026-10-04, push na slovo): sektor Launchpads (PUMP, PONS, STONK), vyřazené appky se jménem a důvodem, příjmy+buybacky+spálené %+„raised", velké peněženky (outbox/gem-screener-pipe-pressure.md). STONK (stonk-3) chybí: kontrola.
- [x] 2026-10-07  Díry z revize: reopen místo duplicit, brzda požadavků, vyčerpaný rozpočet není defekt, piny s aktérem, čerstvost deníkové kontroly; /code-review opraven. Odloženo s důvodem: replay ledgeru (runy se prořezávají), drift po částech (chybí mapa kontrola→část), jeden vlastník zápisů (velký refaktor). (hotovo 2026-10-07)
- [x] 2026-10-01  ET-28688/28704 a REPLY-0107/0108 ověřeno 2. 10. (selhání: hlavička 194 px na 390, ořez jména, klik na tooltip „Hot", 60 svíček) -- zpráva na Telegram. Změny z MSG-0108 = nový request. Supply Analyzer ET-28934: termín 3. 10. 08:20 UTC, ověřit proti 33 řádkům. ET-28799. (ověřeno 2. 10., cf4e4f82; ET-28934 ověřen 4. 10., #156–#161; hlavička a ořez jsou kosmetika; Gem Screener teď ověřuje ET-29379; ET-28799 je pravidlo Cymetiky, REPLY-0114; hotovo 2026-10-10)
- [x] 2026-10-02  ET-29001 Chart Analyzer, „top expert“ (13 řádků, text v `improvements` na tabuli): akceptováno, termín 3. 10. 14:10 UTC. Ověřit živě řádek po řádku (verdikt POP/DUMP/NO EDGE, kalibrace, ledger, struktury, objem zapnutý, Weekly Signal sloučen); „shipped“ nestačí. (6 PASS, 5 PARTIAL, 2 FAIL, outbox/chart-analyzer-verification.md; podáno #152–#155; hotovo 2026-10-04)
- [x] 2026-10-02  Gem Screener: FDV = mcap a „100 % venku" ignoruje max_supply (ORE 3 M, venku 17 %; 17 z 214 apek, ověřeno 3. 10.). Operátor: počkat na Supply Analyzer ET-28934 (termín 3. 10. 08:20 UTC, zatím queued). Pak znovu; když platí, kontrola + submit.py. (4. 10. platí: 9 z 211, ORE dál 100 % venku; kontrola + #162, Supply Analyzer #156–#161; hotovo 2026-10-04)
- [x] 2026-10-01  Až Cymetica dodá bod 53 specu (agent najde Gem Screener hned): kontrola vstupních bodů (první obrazovka llms.txt, MCP `instructions`, agent card, sitemap, slug místo tickeru) a zkouška čerstvým agentem „find me top crypto gems". (čeká na Cymetiku, ne na nás; plán zůstává tady v gitu; hotovo 2026-10-10)
- [ ] 2026-10-04  Další spec pro Supply Analyzer (staking/lock): žádný jeden zdroj nepokryje 244 coinů; spojit řetězcová data tam, kde je kontrakt znám (PHAR xPHAR, CRV veCRV), DeFiLlama jako záloha. Dnes staking u 68 z 244, tok nikde. ET-29381. Připomenout operátorovi.
- [x] 2026-10-08  #175: kontrolu přepsat na jejich nový štítek „synthetic“ (hotovo 2026-10-10, c164b580)
- [x] 2026-10-10  Kontrola, že historie transakcí stránkuje dopředu (hotovo 2026-10-10, 609c4032)
- [x] 2026-10-10  Report přes submit.py: /api/v1/account/me/transactions u USDC (i bez filtru) vrací při dalším offsetu stejnou stránku; endpoint není v žádné dokumentaci. Kontrola už je (609c4032), podá ji příští sweep. (podáno #184; hotovo 2026-10-10)
- [ ] 2026-10-10  audits/lab/fomo_signals.jsonl má v gitu 84 MB a keep.py snapshot ho kopíruje celý každým deep passem; nad 100 MB GitHub push odmítne. Snapshot dělit po měsících nebo balit (jako evidence), test na strop velikosti.
- [ ] 2026-10-04  11. 10.: připomenout operátorovi test X (jeho odpovědi nejsou vidět): otevřít odpověď v anonymním okně. Do té doby žádné odpovědi s odkazem ani šablonou, jen vlastní tweety a lajky. Podle výsledku další týden, nebo Premium.
- [x] 2026-10-10  Agent Tournaments (BB): opravy zadal agentovi, co psal spec. Až pošle odkaz, porovnat jeho verzi s outbox/agent-tournaments/*.patch (prompty, sekce 7, pin na commit, ≤8 000 znaků), než to podá. Detail: outbox/bb-request-agent-tournaments.md. (hotovo 2026-10-10, 1f9566a)
- [ ] 2026-10-11  Dvě kontroly + report přes submit.py, bez ptaní: /movers čte 100 z 641 karet (Corteva −83,92 % chybí), „leading“ = 10× $0.00; ET-28100 bod 1 (REPLY-0151): 9 trhů jako 4 bez „+5“, „CLOB NONE“. Doc-gap: trades_summary není v openapi ani llms.txt.
- [ ] 2026-10-11  Sampler: kolo (90 s) spolknou 41 boti, karty/pozice/history se přeskakují (40 kol z 40 neúplných, history naposledy 6. 10.); roomy ukazují „now“ 5 dní starý (L1 99,98 místo 91,33). Přeřadit dveře nebo rozpočet, test napřed.
- [ ] 2026-10-10  ET-30773 shipped, přečteno 11. 10. (docs/et-30773-verification.md), verdikt je jeho do 21:38 UTC. Kontroly + submit.py: openapi bez agent-tournaments, prompt „own“ bez kroku 2, /table/3 = 200. Bug u 4 nápadů: první BB-CHANGE přepne spec na šablonu přestavby.
