# Next

Co jsme se domluvili, že je další krok, a ještě to není hotové. Píše se v tahu, kdy je to domluvené, kvůli `/clear`. Session start vypíše počet a první řádek. Hotové se smaže (git to drží).

```
- [ ] YYYY-MM-DD  věta, co se má udělat
```

---

- [ ] 2026-11-02  Supply Analyzer request hotový (outbox/supply-analyzer-sources), podání odmítnuto: limit buildů do 18:11 UTC. Operátor řekl podat, po 18:11 UTC znovu `bb.py file` s jeho obrázkem; připomenout.
- [ ] 2026-11-03  Gem Screener ET-33759: pass poslán na slovo operátora (04:39 UTC), v poznámce #287 a karta near miss pod obrazovkou. Sedm bodů z MSG-0302 přečteno v 05:55 UTC: 6 sedí; smajlík u Jupiteru a Hyperliquidu pořád "how is not checked yet", přečíst znovu po refreshi v 07:35 UTC, když nesedí, podat bug. Tokenizace je jeho. Bugy #255 až #288 hlídá sweep.
- [ ] 2026-11-01  Pitch Cards ET-33678: druhá stavba 3. 11., verdikt operátorův (návrh FAIL, outbox/pitch-cards/1-build-it-better/verdict-fail-2.txt: pitche nedělá Nexus, real peníze, odkazy, řazení, graf). Ověření docs/et-33678-verification.md. Agent Casino do live stolů: `casino` přes /loop, bugy podat. ET-33648 přijat, termín 2. 11. 15:27 UTC. Round 3 řádky 2, 5, 6, verdikt jeho. ET-31263 6 řádků; ET-30773 (docs/et-30773-verification.md).
- [ ] 2026-10-13  Requesty: ET-31278 Gem Screener 4-6 PASS, body 1-3 po snapshotu 14.10. (docs/et-31278-verification.md), pak loga; ET-31466 a ET-31459 dodány 15. 10. (docs/et-3146*-verification.md), ET-31459 body 5/9/10 po změně u stolu; ET-31300 1 FAIL live trades, verdikt jeho.
- [ ] 2026-10-22  ET-32803 (kolo 4) Shipped, Fail čeká: zbývá I (hrad modrý, pyramida fialová i v 6adfa1b7), N (Products), C (engine vrstva není); zpráva k I neodeslána (outbox/company-spec-4/verdict-et-32803.md). Quant Lab hledání = ET-32976 (building): až shipped, verdikt náš.
- [ ] 2026-10-27  Promo Market: v2 = ET-32929 živá (3 odchylky, verdikt operátorův). v3 = ET-33031, nasazeno 27. 10.; neověřeno, dokud nebude otevřený brief: stránka briefu, nabídky, Promoters, hover grafu, Made by v Universu. Verdikt dává operátor.
- [ ] 2026-10-15  Než půjde FAIL (`hold` ve filed.json): #134 ztráta 100 % proti stopu 5 %: reset papíru nebo auto-resume? (kontrola zahodí každého zastaveného bota); #132/#137 a2a inbox má plných 200 zpráv, číst dál; #201 FAIL; #122 PASS jen při otevřeném US trhu.
- [ ] 2026-10-22  #46: Cymetica odpověděla, že nástroje jsou vidět, ale bez klíče je nejde zavolat, což náš report nabídl uznat jako vadu dokumentace. Doporučení: vést tak a FAIL už neposílat. Slovo operátora: „#46 jako dokumentace“.
- [ ] 2026-10-25  #112/#136: kontrola termínů soudí i naše vlastní opožděné žádosti a FAIL by znovu otevřel zaplacené zářijové reporty. Zadrženo; doporučení soudit jen žádosti cizích lidí („omez kontrolu“). #93: dokumentace si odporuje, doporučení nový report („podej nový“).
- [ ] 2026-10-25  Quant Lab v2 (outbox/quant-lab-v2) je hotový pro Build it Better; slovo operátora „pošli quant lab“. Spec 4 zkrácený pod limit (7 967 z 8 000); podává operátor.
- [ ] 2026-10-18  Dluh k #156: a2a k MSG-0156 a komentář na reportu; potvrdit REPLY-0169/0170.
- [ ] 2026-11-01  Po předělání: 16 řádků ve filed.json nemá kontrolu (šla s laborkou); běžný sweep vypíše k ruční kontrole 2, `--all` všech 16. Smazat `.claude/hooks/protect_state.py` (prázdný), až žádná session nedrží starý seznam hooků.
- [ ] 2026-11-02  Prošvihlý bug: `test_a_spec_written_after_their_fix_keeps_every_line_and_change` padá od 15. 10. a nikdy nebyl podán (143 řádků žádosti, ET-32483 ztracen). Posoudit, čí je, a podat přes submit.py. První `sweep --all` projede i dalších 36 kontrol bez řádku.
- [ ] 2026-11-02  Sezónní body: od 5. 11. přečíst /api/v1/company/14/season-breakdown. Gem Screener má 5 až 25 lidí denně; zůstane-li active_users a visitors 0 i po 3 dnech sezóny, napsat kontrolu a podat bug.
- [ ] 2026-11-02  #234, #242, #249 čekají na stůl po jejich opravě (ed351dbc, 1. 11. 21:40 UTC): stoly 27 a 31 končí 2. 11. 10:18 UTC, 48 v 19:01, 66 v 19:37. #249 chce stůl ZAČATÝ po opravě a 40 kol, #242 40 hrajících míst nebo vynechané kolo. Pak `sweep --only 234 --only 242 --only 249`.
- [ ] 2026-11-03  Sweep bez casina dluží 9 FAILů (#252, #255, #264, #273, #274, #278, #283, #285, #286), neposlány: jejich opravy podle Cymetiky naskočí až po obnovení 07:35 UTC (Gem Screener) a po denním přepočtu (Supply Analyzer). Po 07:40 UTC `sweep --only` těch devíti; co pořád padá, přečíst v jejich datech a poslat FAIL. #252 hlásí Pitch Cards a Capital Maximizer (3 a 4 použití, 0 lidí): jejich vlastní použití, nebo stejná vada? Rozhodnout před FAILem.
