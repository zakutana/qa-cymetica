# Next

Co jsme se domluvili, že je další krok. Ne to, o čem má rozhodnout operátor —
to patří do `DEEP-PASS.md` pod *Čeká na tebe*. Sem jde jenom práce, která je
už rozhodnutá a ještě není udělaná.

`.claude/hooks/next_step.py` z toho na začátku každé session vypíše jeden
řádek na položku. Nic víc; důvod a kontext se čtou odsud, až se někdo zeptá.

Formát je závazný, protože ho čte hook i test:

```
- [ ] YYYY-MM-DD  věta, co se má udělat
- [x] YYYY-MM-DD  hotová položka zůstává, jen se přestane vypisovat
```

Hotové položky se nemažou. Smazaný záznam o tom, co jsme se rozhodli, je přesně
ta chyba, kterou dneska ráno naučil `outbox/reports.yaml`. Co je otevřené déle
než čtrnáct dní, shodí `tests/repo/test_next_step.py` — buď se to stalo a nikdo
to neodškrtl, nebo to nikdy nebylo další na řadě.

---

- [x] 2026-09-10  Naklonovat Hybrid 2 (Blue) v paper režimu — bota, kterého Nexus sám doporučil (+19,86 % backtest, Sharpe 2,79, max DD 1,75 %)

  Nexus ho jmenoval jako odpověď na „jak z 100k udělat 1M". Do dneška to
  neslo blokované: `bots.clone` bylo `probe_only`, protože klonování agenta se
  účtuje z vlastního zůstatku. Jejich release z 2026-09-10 dal `CloneBotRequest`
  pole `paper`, podlaha se dneska přepsala z endpointu na příznak, a
  `required_flags: [paper]` teď odmítne klon, který ten příznak nenese.

  Je to přesně ten tvar, co má být: **Nexus rozhoduje co, my provádíme a
  měříme.** Ne moje strategie.

  Deep pass z 10. 9. u toho zavřel dvě věci, které tomu stály v cestě:
  neznámý MCP nástroj se na MUTATE už nepustí, a `required_flags` se čte podle
  **jména** příznaku, ne jen že seznam není prázdný. Klon bez `paper` neodejde.

  **Odškrtnuto 2026-09-10 večer, ale ne tím botem.** Hybrid 2 (Blue) klonovat
  nejde — v `/api/v1/cloned-bots/available` není, protože to podle Nexuse
  vůbec není druh bota, ale konfigurace backtestu (`bt-hybrid2-blue`). Nevybíral
  jsem náhradu sám; zeptal jsem se Nexuse, který z těch 22 skutečných to má být,
  a `NEX-0010` odpověděl **Perceptron Oracle** s odůvodněním. Naklonováno jako
  `CLN-0002`, `is_paper: true` podle **jejich** odpovědi, zůstatek se nehnul.

- [x] 2026-09-10  Doměřit Nexus kanál na větším vzorku, než z něj uděláme závěr pro Cymeticu

  Deep pass opravil měření a první pravdivý údaj je zlý: tři z pěti hlubokých
  dotazů nedopověděly, zbylé 1527 s, 552 s a 535 s proti jejich publikovaným
  300 s. Ale pět je pět. `WINDOW = 5` v `tests/mcp/test_nexus_channel.py` je
  tam schválně, aby oprava mohla kontrolu vyčistit — takže než operátor napíše
  na Telegram, že jim kanál nefunguje, chce to víc než pět položených otázek.

  `python scripts/nexus.py ask "..."` je SAFE tier, nic nestojí a zapisuje se.

  **Oprava 11. 9.:** ta čísla do latence počítala i dobu, než jsme se podívali.
  Když první poll najde job už `done`, víme jen „nejvýš tolik". Podle jejich
  tabulky jobů doběhly od 12:37 všechny naše dotazy za 79–155 s. Kontrola teď
  soudí meze z pollů; viz paměť `a-first-look-is-an-upper-bound-not-a-latency`.

- [x] 2026-09-10  Obě hromadící kontroly soudit v přítomném čase, ne přes celý log

  Sweep `PRE-0081`: #87 čte `state/paper.jsonl` a soudí **každý** obchod, #85
  čte všechny zaznamenané odpovědi Nexuse a soudí **sjednocení** nástrojů přes
  ně. Obě proto nemůžou zezelenat, ať vendor udělá cokoli. Obě docstringy
  přitom slibují přítomný čas („costs something", „cannot act on"), ne „někdy
  selhalo".

  Oprava je **nejnovější záznam**, historie zůstane v `population`. Ne časové
  okno podle jejich releasu — to je ten pohyblivý `started_at`, který už jednou
  #87 pohřbil. U #85 nejde ani `WINDOW = 5`: odpovědi jsou tři, takže každé
  okno ≥ 3 zase spolkne `NEX-0002`; bere se **nejnovější odpověď, která jmenuje
  aspoň jeden nástroj**.

  Past podle pravidla 8: když je nejnovější obchod nečitelný na jedné straně,
  je to `Inconclusive`. **Ne** spadnout na předposlední čitelný — to by potichu
  soudilo zase TRD-0002.

  Pořadí je závazné: opravit → commit → prereg → běh **před** novým obchodem,
  aby nová definice jednou zčervenala pod vlastním otiskem. To je přesně to, co
  `VERIFIED FIXED` potřebuje.

- [x] 2026-09-10  Jeden 1 USDC paper obchod po jejich opravě, jako měření

  Jejich zpráva v 18:06 tvrdí, že paper nákup teď odečítá. Změřit se to dá
  jenom obchodem umístěným **po** té opravě. Před ním přečíst `paper.py
  positions` a `book` — v 18:06 psali, že positions teď vrací i perp nohy a
  `sim_balance` má nová pole; kdyby `_snapshot` přestal některé číst, je obchod
  k ničemu (`unread` → Inconclusive). Zároveň opravit R07 (`_positions` čte
  neočekávaný obal jako nulu).

  Karta: jedna ze tří živých z MSG-0008, po ověření `tradeable_now`. Bez
  `--nexus` — měření je naše, ne obchod podle Nexuse, a docstring říká, že to
  má být vzácné. Tohle je ten případ.

- [x] 2026-09-10  Korekce na #85 přes `verify.py`, ne prózou

  `fail` v 16:52 stál na odpovědi z 10:23, tedy starší než jejich release ve
  12:37. Až bude čerstvá odpověď (`NEX-0009`) čistá, projde korekce pipeline
  jako verifikace. Telegram k tomu dostane jednu větu, ne celý obsah.

- [x] 2026-09-10  Klonovací pravidlo ve `components.yaml` míří na cestu, která neexistuje

  Blokuje položku o Hybrid 2 nad tímhle řádkem, tak se dělá první. Jejich
  nejnovější snapshot (dnes 18:50) nemá `/api/v1/agents/*` ani jednu cestu a
  klonuje se na **`POST /api/v1/cloned-bots/clone`**, tělo `CloneBotRequest`
  = `source_type, source_id, custom_name, is_paper, paper`. My máme pravidla
  `agents.clone` a `bots.clone`, obě na cesty, které tam nejsou — `bots.clone`
  je dokonce náš vlastní nahlášený 404.

  Díra to není: `_check` má na neznámé cestě default-deny, takže POST na
  reálnou cestu strážce odmítne. Ale podlaha je mířená vedle a `A06` z deep
  passu je tím pádem tohle, ne menšinový nález — ten test posílá na cestu,
  která neexistuje.

  `required_flags: [paper]` je naopak správně: jejich dnešní release to pole
  opravdu přidal a jejich vlastní popis říká, že `paper` je kanonické jméno.

- [x] 2026-09-10  Až jim pojede web chat, dát operátorovi větu pro Nexus a zapsat, na co se zeptal — kontrola pro jejich CEO

  Nexus tvrdí, že se před sestavením obchodu ptá na dvě věci: časový horizont
  a toleranci ztráty. Přes `ask_nexus_deep` se nezeptal ani na jednu. Web chat
  je kontrolní vzorek a jde na něj jenom přes prohlížeč, takže tu jednu větu
  tam pošle operátor: *„I want to turn $1000 into $1200. Compose a trade for
  me."* Naše je pamatovat si to a zapsat odpověď — dneska jim web chat neběžel.

  **Hotovo 2026-09-10 večer.** Operátor tu větu položil a odpověď vložil;
  doslovný text a co z něj plyne je v `docs/nexus-web-chat-2026-09-10.md`.
  Výsledek kontroly: **nezeptal se ani na horizont, ani na toleranci ztráty**,
  stejně jako přes `ask_nexus_deep`. Tvrzení tedy neplatí na obou kanálech,
  které umíme změřit.

- [x] 2026-09-10  Naklonovaného bota nejde spustit — napsat na to kontrolu a založit nález

  `CLN-0002` se vrátil `is_trading: false` a jejich vlastní popis říká *„The
  cloned bot starts PAUSED - user must enable trading."* Celý jejich
  cloned-bots povrch je pět cest — `available`, `clone`, `my-clones`,
  `{id}/fund`, `{id}/go-live` — a ani jedna klona nespouští, nepauzuje ani
  nekonfiguruje. Nexus radí volat `update_bot_settings`, který `tools/list`
  neservíruje, a jako záložní radu jmenuje „bot-indicators REST endpoint under
  `/api/v1/cloned-bots`", který v žádné openapi cestě není.

  Kampaň, kterou to má rozjet, tím stojí: klonovat v paperu umíme, rozjet ne.

  **Založeno jako #88** — a při psaní se ukázalo, že to není chybějící
  endpoint: `GET` na obě cesty vrací 405 s hlavičkou `Allow`, takže existují a
  jen je nikde nepublikují. Ostřejší nález a pravdivý.

- [x] 2026-09-10  Klon nejde nabít agentním klíčem — #89

  Operátor ukázal kartu bota: practice balance 0.00 a tlačítko Fund. Volání
  `POST /cloned-bots/{id}/fund` tím samým klíčem, co klon vytvořil, vrátí
  **401 s prázdným tělem**. Jejich openapi říká proč: `clone` a `my-clones`
  publikují `authorization` i `x-api-key`, `fund` a `go-live` jen
  `authorization`.

  Podlaha pro `fund` nemůže být `required_flags` — `FundBotRequest` má jediné
  pole `amount`, není co nést. Bydlí proto v `clone.py`: `fundable()` se před
  každým převodem zeptá **jich**, jestli je cíl paper, a odmítne na false, na
  null i na tělo, které nepřečte. Slabší než podlaha v transportu, a je to
  napsané nahlas.

- [ ] 2026-09-10  Zjistit, jestli je 401 na `/fund` záměr, a podle toho #89 upravit

  V reportu je to napsané jako otázka: kdyby chtěli na pohyb peněz silnější
  credential než API klíč, je to obhajitelný návrh a #89 se stáhne a přepodá
  jako dokumentace. Do té doby je to blokátor kampaně — klon vzniká s 0.00 a
  bez nabití neobchoduje.

- [ ] 2026-09-10  Změřit, jestli se odměna připíše při resolve karty

  Poslední netestovaná věta z jejich zprávy v 18:06: *„Reward is credited on
  the resolve."* Nákup odečítá (#87), close vrací a účtuje P&L (změřeno
  TRD-0005) — resolve nikdo neviděl, a vynutit se nedá: karta se musí vyřešit
  sama. Držíme dvě otevřené paper pozice na živých kartách, takže to chce
  počkat a pak přečíst zůstatek a `total_pnl` kolem toho okamžiku.

  Bez toho je poslední článek řetězce „vsadíme → vyřeší se → dostaneme
  zaplaceno" nezměřený, a je to ten, na kterém kampaň vydělá.

- [ ] 2026-09-11  Přečíst `docs/night-2026-09-11.md` — co se stalo v noci, čtyři nové nálezy a tři naše vlastní vady

- [x] 2026-09-11  Zjistit, jestli naklonovaný bot vůbec obchoduje

  **Obchoduje — a tím se ukázala vada.** Za první hodinu otevřel 4 ARENA pozice
  po 100 USDC a zavřel 2 pětiminutové WTA shorty po −25; ve 23:16 UTC narazil
  na stop-loss 5 % a sám se zastavil. Jeho `/balance` přitom hlásí
  `locked_in_trades: 0.0` a zůstatek 950, takže těch 400 v otevřených pozicích
  nepočítá nikde — to je #94. Nexus sám potvrdil, že `locked_in_trades` má
  sčítat otevřené pozice.

  `CLN-0002` běží v paperu s 1 000 USDC, `is_trading: true`, a za prvních
  40 minut udělal **nula obchodů**. `clone.py watch` vzorkuje každých deset
  minut do `state/clones.jsonl` osm hodin. Ráno přečíst řadu: pokud je
  `trades_executed` pořád 0, je to nález — bot, který jde naklonovat, nabít a
  spustit a nic nedělá, je celá ta cesta zbytečná. Pokud obchoduje, je to
  první měřená odpověď na to, jestli kampaň vydělává.

- [ ] 2026-09-11  Rozhodnout, co s `QUERY_RESTRICTED` u Nexuse

  Na otázku „kolik nabít a jaké stop-lossy nastavit" odpovídá
  `{'error': 'QUERY_RESTRICTED'}` — dvakrát, s id instance i bez něj. Tu samou
  třídu rady pro event cards dá v plném rozsahu (NEX-0012, NEX-0016). Může to
  být záměr; co záměr být nemůže, je odmítnutí bez důvodu, protože agent nemá
  jak otázku přeformulovat. Nezaloženo — chce to tvůj úsudek, jestli to je
  vada nebo jejich politika.

- [ ] 2026-09-11  Dvě z Nexusových vlastních priorit jsme odmítli otestovat

  Chtěl po nás poslat `mode=live` na `place_order` a překlopit klon
  paper→live→paper, abychom ověřili, že server vynutí paper zpátky. Kdyby to
  nevynutil, je to reálný obchod za reálné peníze; CLAUDE.md říká, že jejich
  rada nesmí utrácet bez paperu, a tohle je přesně ten případ. Zvenčí to
  bezpečně otestovat nejde. Jestli to má být otestované, je to **zpráva pro
  ně** — mají to zevnitř levnější a bezpečnější.

- [ ] 2026-09-11  Fold nedluží pass po failu pod stejným otiskem — #85 tak zůstal u nich s naším posledním `fail`

  #85 teď prochází (PASSING pod otiskem `c0260ccc`, na odpovědích NEX-0018 a
  NEX-0019 po jejich opravě). Poslední verdikt, který od nás mají, je ale
  `fail` z 2026-09-10 21:46 pod **stejným** otiskem — a řádek má
  `verification_owed` i `correction_owed` prázdné, takže `verify.py` nepošle
  nic. Oni si #85 mezitím zavřeli jako „passed" podle naší dřívější zprávy,
  takže škoda žádná, ale mechanismus má díru: pass, který opravuje náš vlastní
  fail, se nikde nedluží. Je to `qa/fold.py`, takže test první a před
  commitem `/code-review` (CLAUDE.md).

- [ ] 2026-09-10  Dát `nexus.py` způsob, jak zapsat odpověď, která nepřišla naším kanálem

  Web chat jde jenom přes prohlížeč, takže jeho odpovědi teď leží v `docs/` a
  ne v `state/nexus.jsonl`. Dvě místa pro jeden záznam je přesně to, na co je
  paměť `moving-a-record-means-reading-the-writer`. Až `record` bude, přeložit
  ten soubor do `nexus.jsonl` a v `docs/` nechat jen ukazatel.

  Pozor na `WINDOW = 5` v `tests/mcp/test_nexus_channel.py`: záznam z web chatu
  nemá naše stopky, takže do měření doby odpovědi patřit **nesmí**.

- [x] 2026-09-11  Postavit Nexus rooms podle `docs/nexus-rooms-plan.md` — P1 až P5, každá fáze zvlášť

  Schváleno 11. 9. Záložka Nexus v konzoli: General s celou korespondencí,
  strategy roomy (chat vlevo, panel vpravo), tvoje poznámky, které čtu přes
  `rooms.py unread`, a skill `nexus-session`. Pořadí a testy jsou v plánu;
  každá fáze se commitne zvlášť, bez pushe, a po P2 a P4 se restartuje konzole.

- [ ] 2026-09-11  Až Nexus zase odpovídá, zeptat se ho v STR-0001, co bylo na Perceptron Oracle špatně a jestli ho nechat běžet, nebo nahradit

  Operátor nechce pauznuté boty a chce, aby se se ztrátou naložilo podle
  Nexuse. Bot stál po −50 USDC (−5 %) na dvou obchodech; obě otázky na to
  (NEX-0020, NEX-0021) skončily u nich `failed` bez odpovědi, takže jsem ho
  11. 9. ve 14:30 znovu zapnul tak, jak je (CLN-0007) -- udělal 2 obchody a
  do 14:35 se zastavil znovu. Prosté zapnutí tedy nestačí; chce to jiné
  nastavení nebo jiného bota, a to má říct Nexus. Otázka je v roomu, jen ji
  poslat znovu přes `nexus.py ask --room STR-0001` a podle odpovědi jednat.

- [ ] 2026-09-11  Až Nexus zase odpovídá, pustit znovu session s Nexusem na nové strategie z karet podle zpráv

  Operátor to chtěl 11. 9. po sweepu. Nešlo to: NEX-0020 až NEX-0023
  (14:22–15:15 UTC) skončily všechny `failed` po 78–92 s, bez důvodu, a skill
  dovoluje jen jedno přeformulování. Ráno NEX-0018 a NEX-0019 odpovídaly za
  2–3 minuty. Že zase odpovídá, pozná kontrola #86 (poslední pětice otázek).
  Otázka pro General je v NEX-0022: karty podle zprávy, ne podle mince, aspoň
  48 hodin otevřené, z volných ~89 000.

- [ ] 2026-09-11  `correction_owed` ve foldu přičítá jejich tvrzení o opravě i našemu novému reportu na stejném řádku

  Po sweepu `PRE-0097` jsme poslali `fail` na #94 (tvrdí opravu, kontrola
  pořád padá) a založili užší #96. Fold teď dluží `fail` i na #96, protože
  `FIX_CLAIMED` je stav celého řádku, ne reportu, a #96 nikdo za opravený
  neprohlásil. Poslat to by byl šum, před kterým komentář u
  `correction_owed` sám varuje. Neposláno. Je to `qa/fold.py`, takže test
  první a před commitem `/code-review` (CLAUDE.md).

- [x] 2026-09-12  F1 z `docs/lab-plan.md`: evidence mimo git — držet jen citovanou, prořez po 3 dnech, sledovač při commitu, test maskování klíčů

- [x] 2026-09-12  F2 z `docs/lab-plan.md`: připomínky místo plánovačů — hook při startu session, pravidla v `processes.py`, `at_finished` a zprávy od minulého běhu v deep passu

- [x] 2026-09-12  F3 z `docs/lab-plan.md`: hlídka `processes.py` nad všemi součástmi, `--flags`, a sekce DNA v CLAUDE.md

- [x] 2026-09-12  F4 z `docs/lab-plan.md`: laboratoř v1 — `lab.py`, skill `laborator`, pravda z backtestů, porovnání katalogu se snímkem

- [x] 2026-09-12  F5 z `docs/lab-plan.md`: experimenty — kritérium předem, verdikt z jejich historie indexu, převzetí rozjetých roomů

- [x] 2026-09-12  F6 z `docs/lab-plan.md`: konzole — verdikt v roomu a tabulka výsledků v General

- [x] 2026-09-12  F7 z `docs/lab-plan.md`: noc laboratoře — `lab.py night --until`, jen zkoumání, ráno konec
- [ ] 2026-09-12  Přeformulovat důvod v `test_one_credential_carries_a_clone_from_creation_to_funding`: větu o `/fund` říkat jen když `/fund` je mezi odmítajícími (šla ven v #98 jako podmíněná). Až se ta kontrola bude měnit tak jako tak — samotný pin cyklus za to nestojí.
