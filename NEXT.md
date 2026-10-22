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

- [ ] 2026-10-12  Kód pro firmu (session/deep pass, testy napřed): commit.py a záznam běhu (OP-0009); desk H2 čtení (OP-0013); BTC rozpětí verdiktu (T-0039); manifest v cizím commitu (T-0038); body 9 a 11 crew-before-c9.
- [x] 2026-10-12  Clock nedá desku další krok, dokud jeho pracovník běží, a pauzu počítá i od zavření tiketu (T-0040). (hotovo 2026-10-18, deep pass)
- [ ] 2026-10-11  Laborka v3 (docs/laborator-plan.md) postavená, P3, P4, P5, P6, P7 čekají na tahy: v prvním `python scripts/lab.py launch NEX-0137`; outsider až po přihlášení `claude` a `outsider.py probe`. Zbytek výzkumu botů: docs/bots-research-plan.md „Zbývá".
- [x] 2026-10-11  FOMO sběr: 9. 10. 48 557 dotazů na cymetica.com, 39 784 na nezdokumentované /clones/memecoin-terminal/search; REPLY-0030 žádá žádnou zátěž. Denní strop ve fomo_watch (10 000 za den UTC; strop v patrolu přešel do řádku z 18. 10.; hotovo 2026-10-18, 1b636163)
- [ ] 2026-10-18  Z ohlédnutí: strop requestů v patrolu (od 11. 10.); firma nesmí psát kořenové *.py a conftest; outsider bez holého MEMORY.md + state/outsider/ do .gitignore; zámek manifestu; FAIL ověření řekne proč; a2a k MSG-0156 a komentář #156; potvrdit REPLY-0169/0170 a opravit studii.

- [ ] 2026-10-08  Sledovat: #142, #136, #121, #51; FOMO #762 (path_coverage Robinhood 0 → 0,9 do ~13. 10., Solana 0,011). #171/#173/#174 selhávají i po opravě. Liga: od 1. 11. /loop 10m (říjen capped). ET-30676: SaaSHub čeká na review, 3 formuláře u nich; PR awesome-web3 #831 otevřený.

- [ ] 2026-10-13  Requesty (operátor): ET-31278 Gem Screener 4-6 PASS, body 1-3 po snapshotu 14.10. (docs/et-31278-verification.md), pak loga; ET-31466 a ET-31459 dodány 15. 10. (docs/et-3146*-verification.md), ET-31459 body 5/9/10 po změně u stolu; ET-31300 1 FAIL live trades, verdikt jeho.
- [ ] 2026-10-15  Než půjde FAIL (PRE-0279 je drží): #134 ztráta 100 % proti stopu 5 % -- reset papíru nebo auto-resume?; #132/#137 a2a inbox má plných 200 zpráv, číst dál; #46 anonym vidí 37 nástrojů nad úrovní -- zavolat bez klíče. Drží i #201 (FAIL) a #122 (PASS jen při otevřeném US trhu).
- [ ] 2026-10-22  /company kolo 3: spec outbox/company-spec-3 hotový, mock kreslí firmy, produkty, panely, /clear; čeká na push a podání (13 řádků, odkazy připnout na poslední commit). Kolo 2 postaveno; nezakládat: Experiments bez botů, /products bez earned, 11x Gem Screener.
- [ ] 2026-10-15  NEXUS Profit Agent (Nexus přejmenovaný; odpověď končí krokem k zisku; paper 100 obchodujících/200 klonů; auto_resume_after_stop zapnuté na Paper): v laborce změřit, jestli jeho kroky vydělávají -- každý krok jako paper room, verdikt. Souvisí s #134.
- [ ] 2026-10-13  Po sweepu PRE-0274 opravit naše kontroly, než půjde FAIL: #112/#136 (re-ship po fail verdiktu), #192 (čte log před opravou), #93 (přečíst jejich pravidlo), karta v pozici (jen otevřené pozice), FOMO kalibrace (OverflowError); /movers přepojit na /event-cards/movers.
- [x] 2026-10-13  Kontrola #141 počítá denní průměr přes dny, které řádek má (FUL 24 dní); kontrola #202 bere díru vyznačenou v gaps jako jejich opravu (hotovo 2026-10-15, bd46318e, fa106799)
- [x] 2026-10-13  ET-31267 (Supply Analyzer + Supply karta a sloupec v Gem Screeneru, 17 řádků, 4 obrázky): spec zkontrolován, čeká na BB-ACCEPT; po dodání ověřit 17 řádků proti živým datům (HYPE, ARB, PHAR, coiny bez harmonogramu = „—“). (15/17, docs/et-31267-verification.md, MSG-0176; hotovo 2026-10-15)
- [ ] 2026-10-12  Agent Tournaments: ET-31263 ověřit 6 řádků; ET-30773 Results po 18. 10. 16:47 UTC (stůl 2, docs/et-30773-verification.md). 20 botů „flash …“ (17. 10.): na každý nový otevřený flash stůl jeden, dokud nesedí všichni (SEAT-0004/0005), odkaz ke schválení operátorovi.
