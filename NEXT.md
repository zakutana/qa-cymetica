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

- [x] 2026-10-12  Kód pro firmu: commit.py a záznam běhu (OP-0009), BTC rozpětí verdiktu (T-0039), manifest v cizím commitu (T-0038), bod 9 a 11 crew-before-c9 bez dvou kusů níž (hotovo 2026-10-25, 4403c058, 30bd74ce, acd8d749, 7e8f64f7)
- [ ] 2026-10-12  Kód pro firmu, zbytek: desk H2 čtení (OP-0013, až firma poběží); bod 9 b/d (uvolnit doběhlé klony, jeho výběry napřed) a rotace deníků z bodu 11.
- [x] 2026-10-12  Clock nedá desku další krok, dokud jeho pracovník běží, a pauzu počítá i od zavření tiketu (T-0040). (hotovo 2026-10-18, deep pass)
- [ ] 2026-10-11  Laborka v3 (docs/laborator-plan.md) postavená, P3, P4, P5, P6, P7 čekají na tahy: v prvním `python scripts/lab.py launch NEX-0137`; outsider až po přihlášení `claude` a `outsider.py probe`. Zbytek výzkumu botů: docs/bots-research-plan.md „Zbývá".
- [x] 2026-10-11  FOMO sběr: 9. 10. 48 557 dotazů na cymetica.com, 39 784 na nezdokumentované /clones/memecoin-terminal/search; REPLY-0030 žádá žádnou zátěž. Denní strop ve fomo_watch (10 000 za den UTC; strop v patrolu přešel do řádku z 18. 10.; hotovo 2026-10-18, 1b636163)
- [x] 2026-10-18  Z ohlédnutí: strop requestů v patrolu, firma nesmí psát kořenové *.py a conftest, outsider bez holého MEMORY.md, zámek manifestu, FAIL ověření řekne proč (hotovo 2026-10-25, bff9b1e9, b2870d78, 2f259031, 98e3bda9, dc34427b)
- [ ] 2026-10-18  Z ohlédnutí, zbytek: a2a k MSG-0156 a komentář #156; potvrdit REPLY-0169/0170 a opravit studii.

- [x] 2026-10-08  Sledovat #142, #136, #121, #51, #171-#174, FOMO #762, ligu od 1. 11., SaaSHub a PR awesome-web3 #831: hlídání, ne práce (hotovo 2026-10-25: reporty hlídá ledger, FOMO stojí od 16. 10., liga je v Čeká na tebe, SaaSHub a PR #831 čekají na ně)

- [ ] 2026-10-13  Requesty (operátor): ET-31278 Gem Screener 4-6 PASS, body 1-3 po snapshotu 14.10. (docs/et-31278-verification.md), pak loga; ET-31466 a ET-31459 dodány 15. 10. (docs/et-3146*-verification.md), ET-31459 body 5/9/10 po změně u stolu; ET-31300 1 FAIL live trades, verdikt jeho.
- [ ] 2026-10-15  Než půjde FAIL (PRE-0279 je drží): #134 ztráta 100 % proti stopu 5 % -- reset papíru nebo auto-resume?; #132/#137 a2a inbox má plných 200 zpráv, číst dál; #46 anonym vidí 37 nástrojů nad úrovní -- zavolat bez klíče. Drží i #201 (FAIL) a #122 (PASS jen při otevřeném US trhu).
- [ ] 2026-10-22  ET-32803 (kolo 4) Shipped, Fail čeká: zbývá I (hrad modrý, pyramida fialová i v 6adfa1b7), N (Products), C (engine vrstva není); zpráva k I neodeslána (outbox/company-spec-4/verdict-et-32803.md). Quant Lab hledání = ET-32976 (building): až shipped, verdikt náš.
- [ ] 2026-10-27  Promo Market: v2 = ET-32929 živá (3 odchylky, verdikt operátorův; karta a stránka briefu až s otevřeným briefem). v3 request hotový: outbox/promo-market-v3/build-it-better/request.txt (6 242 znaků, odkazy na 1cee6f7e); podává operátor na build-it-better jako vylepšení appky na /creator-dashboard, jak ET-32929. Pak ověřit stavbu proti obrázkům.
- [ ] 2026-10-15  NEXUS Profit Agent: v laborce změřit, jestli jeho kroky vydělávají -- každý krok jako paper room, verdikt. Souvisí s #134. Klony s Auto-optimize jsou živé (REPLY-0214/0215; trasy ověřené): ověřit hold-out na paper klonu modelu s backtestem (5 z 39), papírový test (REPLY-0213).
- [x] 2026-10-13  Po sweepu PRE-0274 opravit naše kontroly: #112/#136 první dodání, #93 trasa s JWT, karta v pozici jen otevřené, /movers na /event-cards/movers; FOMO už 25927115; #192 beze změny, PASS přijat 16. 10. (hotovo 2026-10-25, 4ba0ff36, f0098d59, f0f1a37c, 81185fc1)
- [ ] 2026-10-25  Z deep passu: připnout s důvodem 8 opravených kontrol (CHECK CHANGED, #217 mezi nimi) a poslat, co pak dluží; v deníku umět označit neodeslaný koncept (6 z týdne + MSG-0252, 0255); 17 řádků s dluhem opravy kontroly opravit nebo vyřadit; clone.py: chyba po odeslání je unknown.
- [ ] 2026-10-12  Agent Casino v4 = ET-32932: čeká na BB-CHANGE o penězích (outbox/tournaments-v4/bb-change-money.txt), pak BB-SPEC porovnat a BB-ACCEPT. Dál: ET-31263 6 řádků; ET-30773 Results (docs/et-30773-verification.md); 20 botů „flash“: na každý otevřený stůl jeden (SEAT-0004/0005) -- 2026-10-27 smazáno na pokyn operátora (zůstali jen 3 nejlepší podle zisku), k obsazení stolů by se klonovali znovu.
