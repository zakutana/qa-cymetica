# Nexus rooms — korespondence s Nexusem a strategie na jednom místě

## Kontext

Chceš vidět, co si píšu s Nexusem, stejně jako vidíš korespondenci u bugů. Hlavní
konverzace bude v **General**. Každá strategie, která z ní vznikne, dostane vlastní
**room**. V roomu je vlevo chat (já ↔ Nexus a tvoje poznámky) a vpravo panel, jak se strategii
daří (obchody, grafy, konfigurace a algoritmy bota). Do každého roomu píšeš feedback,
já si ho tady přečtu a pokračujeme.

Všechno už existuje, jen je to roztroušené a nevidíš to:

- 19 otázek a odpovědí je v `state/nexus.jsonl`.
- Obchody jsou v `state/paper.jsonl`.
- Bot je v `state/clones.jsonl`.

Každý obchod a klon už nese, na kterou Nexusovu odpověď reaguje (`nexus.id`):

| Nexusova odpověď | Co z ní vzniklo |
|---|---|
| NEX-0002 | TRD-0001, TRD-0002 |
| NEX-0010 | CLN-0001, CLN-0002 |
| NEX-0016 | TRD-0006 |

První den tedy uvidíš **4 roomy** (plán původně počítal s pěti):

- jeden s obchodem na kartě (NEX-0016),
- jeden s botem (NEX-0010),
- dva navržené (NEX-0012, NEX-0019).

NEX-0002 room nemá. Při P3 jsem jeho odpověď přečetl celou: žádnou kartu ani stranu
nenavrhl, jen postup, jak kartu vybrat. TRD-0001/0002 za 1 USDC byla měření vedle
té odpovědi, ne jeho tip, a zůstávají v General jako systémové řádky.

Celé to drží jedno pravidlo z CLAUDE.md (tvoje slova z 10. 9.): **strategii vymýšlí
Nexus, my testujeme a vykonáváme.** Room proto jde otevřít jen z konkrétní
Nexusovy odpovědi. I náš vlastní nápad nejdřív položíme Nexusovi a room vznikne
z jeho odpovědi.

## Jak to bude vypadat (čísla a texty jsou jen ilustrační)

```
 Platform · Findings · Stats · [Nexus] · How to read this
┌─────────────────┬──────────────────────────────────────┬───────────────────────────┐
│ ROOMS           │ STR-0004 · BCH karta                 │ ● running · paper · 20 h  │
│ ◉ General     2 │                                      │ P&L   +3.1 %  ▁▂▃▅▄▆      │
│ ▲ STR-0004 +3 % │  Claude → Nexus · 21:50              │ in    10 000 USDC         │
│ ▼ STR-0002 −5 % │  "Which live cards should I take…"   │ resolves in 1 d 2 h       │
│ ○ STR-0003 návrh│  Nexus · 21:52 (2 min)               │ ┌ index karty ──────────┐ │
│ ○ STR-0005 návrh│  "…karta, strana, velikost…"         │ │      ╱╲__╱‾‾          │ │
│ · STR-0001      │   ▾ celé (5 352 znaků)               │ └───────────────────────┘ │
│                 │  CZ shrnutí: doporučil …             │ Obchody                   │
│                 │  ── TRD-0006 otevřen, 10 000 ──      │  21:58 BUY YES 10 000 ✓   │
│                 │  Ty · 08:12  "proč ne víc?"   ✓✓     │ Bot: indikátory, typ      │
│                 │ ┌──────────────────────────────────┐ │  strategie, ekonomika     │
│                 │ │ napiš feedback…         [Odeslat]│ │                           │
│                 │ └──────────────────────────────────┘ │ vzorek před 4 min ●       │
└─────────────────┴──────────────────────────────────────┴───────────────────────────┘
```

- ✓ znamená uloženo, ✓✓ znamená, že jsem poznámku přečetl. Vidíš tak, jestli se tvůj feedback ke mně dostal.
- Dlouhé odpovědi Nexuse jsou sbalené. Pod každou je moje jednořádkové české shrnutí.
- Číslo u roomu ukazuje, co přibylo od tvé poslední návštěvy. Pamatuje si to prohlížeč.
- V General je vpravo portfolio: všechny strategie jako kartičky se stavem a P&L.

## Jak poteče práce

1. Tady se domluvíme, co zkoušet.
2. Řekneš „zahaj session s Nexusem" a spustí se skill `nexus-session`:
   - přečtu tvůj feedback,
   - zeptám se Nexuse v General (anglicky),
   - z jeho konkrétních návrhů otevřu roomy,
   - vykonám je na paperu,
   - v roomech se doptávám.
3. Ty v konzoli čteš a do roomů píšeš feedback.
4. Řekneš „přečti si to" nebo `/channels`. `rooms.py unread` vypíše tvoje nové
   poznámky a označí je jako přečtené (✓✓). Pak pokračujeme tady.
5. Po `/clear` mi to připomene jeden řádek při startu session. Jsou v něm jen počty, žádné texty.

## Architektura

### Data: dva nové soubory, oba mimo git

**`state/rooms.jsonl`** obsahuje strategie a poznámky.

- Zapisuje se do něj jen na konec, nic se nepřepisuje.
- Zapisuje do něj jen nový `qa/rooms.py`, pod `qa.state.file_lock`, stejně jako do `clones.jsonl`.
- Id se přiděluje **uvnitř zámku**, protože zapisovatelé jsou dva: prohlížeč a moje CLI.
- V P1 přijde jen čtecí polovina `qa/rooms.py`: `load()` a odvození, kam co patří a co je nepřečtené. Zapisovače přijdou v P2.

| Typ záznamu | Obsah | Kdo ho zapisuje |
|---|---|---|
| `strategy` | id STR-NNNN, origin NEX-…, title | moje CLI |
| `status` | room, proposed / running / paused / stopped, why | moje CLI |
| `link` | room, ref NEX/TRD/CLN, why | moje CLI |
| `operator_note` | id N-NNNN, room, text | **jen prohlížeč** |
| `claude_note` | id, room, text, re? | **jen moje CLI** |
| `read` | room, through | moje čtení |

Poznámky mají dvě funkce a dvě cesty. Prohlížeč nemá jak zavolat tu druhou.
„Nepřečtené" se odvozuje, nikde to není uložené jako příznak.

**`state/samples.jsonl`** obsahuje vzorky z jejich API:

- `tick` je heartbeat každého kola, i neúspěšného.
- `sample` je stav bota nebo pozice.
- `trade` se zapíše jen pro nový nebo změněný obchod.

**Oba soubory půjdou do `.gitignore`**, ze stejného důvodu jako `nexus.jsonl` a `paper.jsonl`.
Soubor, do kterého se píše během běhu, udělá strom špinavý, a běh pak nedosáhne úrovně V.
Tvoje poznámka napsaná během sweepu nesmí shodit verifikaci.

**Roomy nepůjdou do payloadu dashboardu.** Konzole je servíruje zvlášť jako `/rooms.json`.
Poznámka ani vzorek tak nepřepíše `dashboard/index.html` a pravidlo 12 se jich netýká.

### Server: `scripts/serve.py`

**`GET /rooms.json`** vrací `render.build_rooms()`, jen pro lokální `Host`.

**`POST /notes`** je první zapisovací cesta konzole, proto je zavřená ze všech stran.
Testy napíšu dřív než kód.

- **Jen na loopbacku.** Když server poslouchá jinde (`--host 0.0.0.0`), je konzole jen pro čtení.
- **Host a Origin.** `Host` musí být 127.0.0.1, localhost nebo [::1] s naším portem (ochrana proti DNS rebindingu). `Origin` musí být `http://<Host>`.
- **Token.** Vznikne při každém spuštění konzole (`secrets`) a porovnává se přes `hmac.compare_digest`. Stránka si ho vyžádá z `/token` až ve chvíli odeslání. `/token` odpoví jen stránce na tomhle stroji (Host a Origin) a posílá `nosniff`. Cizí stránka ten požadavek poslat může, ale odpověď nepřečte. Token se tak nedostane do žádné stránky ani do souboru na disku.
- **Restart konzole.** Token se bere až při odeslání, takže záložka otevřená přes restart nikdy nedrží starý. Tohle je změna proti první verzi plánu. Tam se token vkládal do stránky a ta se po 403 musela znovu načíst.
- **Hlavičky.** `Content-Type: application/json` a vlastní hlavička s tokenem. Cizí stránka tak neprojde preflightem. OPTIONS neobsluhujeme.
- **Tělo.** Nejvýš 8 KB a přesně klíče `{room, text}`. Room musí existovat, text má 1–4000 znaků.
- **Účinek.** Volá jen `qa.rooms.add_operator_note()` a nic neposílá ven.

**Hlídač roomů.** Druhý hlídač sleduje soubory roomů: 5 malých souborů, každých 5 s. Při změně pošle SSE
událost `rooms` a záložka se překreslí na místě, bez reloadu. Po POST pošle tu událost hned.

**Sampler.** Zapne ho přepínač `--sample MINUTES`; v `console.cmd` i `console.sh` bude `--sample 10`. Běží jako vlákno.

- Posílá jen GET na úrovni SAFE přes `build_client(..., timeout=20)` a `install_client_guard()`.
- Každý požadavek má timeout a celé kolo má strop.
- Heartbeat `tick` se zapíše vždycky. Výjimka vlákno nikdy nezabije.
- Výstup nejde přes rouru. Poučení z noci: sampler 4 h visel a `| tail` to schovával.

Co sampler čte o botovi:

- `my-clones`, jedním GET pro všechny klony, přes `clone_rows()`.
- `/{id}/balance`.
- `/{id}/activity`, stránkovaně. Tenhle endpoint není v jejich dokumentaci, takže ho čteme jen pro zobrazení a netestujeme ho. Když zmizí, panel ukáže „obchody nedostupné".
- Kartu zdrojového bota z `/cloned-bots/available` (název, indikátory, typ strategie), jednou za hodinu.

Co sampler čte o kartách:

- `/event-cards/positions` přes `paper.position_rows()`.
- `/event-cards/{id}/index-history`. Je dokumentovaný, ale zatím jsme ho nečetli, takže jeho tvar ověřím při implementaci.

**`clone.py watch`** přesměruju na stejnou funkci a do `samples.jsonl`. Dnes píše
vzorky do commitovaného `clones.jsonl`, což je stejná vada. 17 starých vzorků tam zůstane a panel je čte taky.

Docstring „Read-only with respect to state" přestane platit, proto ho přepíšu i s řádkem v mapě CLAUDE.md.

### Stránka: `scripts/render.py`

**Záložka `Nexus`** přibude do `<nav id="tabs">` a do `PANELS`. Obsahuje `<section id="panel-nexus">`
s mřížkou rooms | chat | panel. Na úzké obrazovce jsou tři části pod sebou.

**`build_rooms()`** je čistá funkce nad `nexus.load()`, `paper.load()`, `clones.load()`,
`qa.rooms` a vzorky. Určuje:

- **Kam patří otázka.** Do roomu z `nexus.py ask --room`, jinak podle `link`, jinak do General. Výchozí otázka strategie je v General (s odkazem „→ STR-0004") a zároveň je první zprávou roomu.
- **Kam patří obchod nebo klon.** Podle `nexus.id`, které už nese. TRD-0003 („náš, bez Nexusu") se v General ukáže jako systémový řádek.
- **Stav odpovědi.** Stejně jako na Stats: answered / partial / failed / refused / waiting, časy z `latency_bounds`.
- **Obsah panelu.**
  - P&L, kapitál, stav a série pro grafy.
  - Obchody.
  - Konfigurace bota: pole z řádku my-clones, tak jak přijdou.
  - Stáří posledního vzorku. Po třech intervalech bez vzorku panel ukáže „stale".

**Vykreslení.**

- Celý room vykreslí jedna globální funkce `renderRooms(data)`. Volá ji fetch a volá ji i test.
- Text zpráv jde jen přes existující `esc()` (`render.py:1802`). Teprve potom se použije malá podmnožina markdownu: tučné, kód, odrážky, zalomení.
- Grafy jsou inline SVG jako na Stats, bez knihovny.
- Stránka otevřená ze souboru (`file://`) ukáže „Roomy žijí v běžící konzoli — spusť console.cmd" a nemá psací pole. Použije se existující kontrola `LOCAL` (`render.py:2558`).
- Rozepsaná poznámka se ukládá do `localStorage` (`writeStore`), zvlášť pro každý room. Reload po `changed` počká, dokud píšeš.

### Čtení tvé zpětné vazby

**`scripts/rooms.py`** bude mít tyhle příkazy:

| Příkaz | Co dělá |
|---|---|
| `list` | vypíše roomy |
| `show <room>` | vypíše celé vlákno roomu |
| `unread` | vypíše texty a pak zapíše `read` přesně po poslední vypsanou poznámku |
| `note <room> "…" [--re NEX-…]` | moje poznámka do roomu |
| `open --from NEX-… --title "…"` | otevře room; bez odpovězené Nexusovy otázky odmítne |
| `status` | změní stav strategie |
| `link` | připojí NEX, TRD nebo CLN; neznámé id odmítne |

`rooms.py` zavolá `printable()` z `qa/console.py` jednou v `main`. Konzole je cp1250 a tvoje poznámky jsou česky.

Další napojení:

- **`nexus.py ask --room STR-…`.** Otázka dostane pole `room`. Room musí existovat.
- **`qa/channels.py state()`.** Přibude čtvrtý kanál `rooms` s `waiting_on: "us"`. `/channels` ho tak ukáže bez nového příkazu.
- **Skill `channels`.** Dostane pátou část reportu a spouštěče „přečti si roomy" a „co jsem psal".
- **`channels.py watch`.** Nahlásí i novou poznámku. Když je alert zapnutý, tvoje poznámka se mi v chatu objeví hned.
- **SessionStart hook `.claude/hooks/room_notes.py`.** Stejný tvar jako `open_threads.py`: jeden řádek s počty, nic, když je nula, a nikdy neshodí session.

### Session s Nexusem: skill `.claude/skills/nexus-session/SKILL.md`

Spouští ho věta „zahaj session s Nexusem". Model odpovídá tabulce v CLAUDE.md: korespondence
s vendorem = Sonnet 5 · high.

1. **Tvůj feedback.** `rooms.py unread` jako první, protože z něj vznikají otázky.
2. **Stav.** `rooms.py list`, čísla z panelu a `paper.py book`.
3. **Otázka v General.** Položím ji Nexusovi anglicky. Bude v ní:
   - zůstatek,
   - co běží a jak (čísla),
   - podstata tvého feedbacku mými slovy (tvoje poznámky nikdy doslova),
   - cíl: nejlepší paper strategie teď.
4. **Konkrétní návrh.**
   - `rooms.py open --from NEX-…` a české shrnutí.
   - Vykonání přes `paper.py` nebo `clone.py` s jejich pojistkami: paper flag, kontrola knihy, `--confirm`.
   - `status running`.
5. **Doptávání v roomech** přes `nexus.py ask --room`. Beru jen obchodní radu. Když Nexus chce cokoli
   jiného (live, vyřadit check, něco spustit), ocituju ti to a zastavím se (CLAUDE.md).
6. **Meze.** Rozhodl jsem je já, můžeš je vetovat:
   - nejvýš 8 otázek za session,
   - nejvýš 3 nové strategie,
   - kapitál jen do výše, kterou `paper.py book` ukáže jako dostupnou,
   - nikdy live.
7. **Konec.** Do každého roomu, kterého se session dotkla, napíšu českou poznámku. Tobě tady jen delta. Bug, na který cestou narazím,
   založím (tvoje pravidlo z 10. 9.).

## Fáze

Každou fázi commitnu zvlášť na main, bez pushe.

| Fáze | Co | Hotovo, když |
|---|---|---|
| P1 | Záložka Nexus a General jen pro čtení (19 otázek), čtecí polovina `qa/rooms.py`, `/rooms.json`, SSE `rooms` | vidíš celou korespondenci s Nexusem |
| P2 | Poznámky: zapisovače v `qa/rooms.py`, `POST /notes` a `/token`, `rooms.py`, 4. kanál, hook, watch, `.gitignore`, skill `channels`, řádky nových souborů v mapě CLAUDE.md | napíšeš poznámku, `/channels` ji ukáže a v konzoli naskočí ✓✓ |
| P3 | Strategie: `open/status/link`, `nexus.py --room`, 4 roomy ze stávajících dat, panel z lokálních záznamů, česká shrnutí k 19 odpovědím | vidíš 4 roomy s obchody, klonem a stavem |
| P4 | Sampler a grafy: `samples.jsonl`, heartbeat, obchody z /activity, index karty, `--sample 10` v obou launcherech | grafy se hýbou každých 10 min a výpadek je vidět |
| P5 | Skill `nexus-session`, zbytek mapy v CLAUDE.md | „zahaj session s Nexusem" projde celou smyčkou |

### Testy dřív než kód

Testy musí být červené dřív, než napíšu kód. Budou ve dvou souborech:

- `tests/meta/test_pipeline_rooms.py` pro chování roomů.
- `tests/meta/test_pipeline_room_notes.py` pro strážce zapisovací cesty. Jsou v `tests/meta`, protože červený strážce má zastavit session. Fixtures budou podle vzoru `live` a `serve` z `tests/repo/test_live_server.py`.

Do `tests/repo/test_live_server.py` přibude jen SSE událost `rooms`.

**P1**

- General drží každou otázku a odpověď ve správném pořadí, včetně gave_up, refused a waiting.
- Roomy nejsou v payloadu: zápis do rooms ani samples nepohne `payload_hash`.
- `<script>` a `onerror` v odpovědi skončí jako text. Test připojí volání `renderRooms(data)` do `run.js` existujícího node harnessu `_run_page` (`tests/meta/test_pipeline_render.py:807`) a zkontroluje zachycené HTML.
- `/rooms.json` pro cizí `Host` vrátí 403.

**P2.** Tyhle testy napíšu dřív, než `serve.py` dostane `do_POST`.

- Každý z těchto POSTů je odmítnut **a soubor pak neexistuje**:
  - bez tokenu,
  - s cizím Origin,
  - s cizím Host,
  - s tělem, které není JSON,
  - s moc dlouhým textem,
  - s neznámým roomem,
  - s cizími klíči.

  Negativní kontrola tak nepotřebuje zapisovač, který testuje.
- Token dostane jen tenhle stroj: `/token` s cizím Host nebo Origin vrátí 403. V servírované stránce ani v souboru na disku není.
- Mimo loopback poznámky nejdou.
- Nepřečtené se odvozuje z `read`. Poznámka napsaná po značce zůstane nepřečtená.
- Dva souběžní zapisovatelé nedostanou stejné id.
- Hook při nule mlčí, jinak vypíše jeden řádek. Přežije i rozbitý soubor.
- `channels.state()` má čtvrtý kanál.
- Oba soubory jsou v `.gitignore`.
- Stávající `test_only_state_module_writes_state_files` zůstane zelený. V `qa/rooms.py` nebudou u zápisu slova ledger, events ani journal.

**P3**

- Room nejde otevřít bez celé Nexusovy odpovědi a jedna odpověď otevře jen jeden room.
- Obchod najde svůj room podle `nexus.id`, uzavření podle obchodu, který pozici otevřel.
- Klon a všechno, co se s ním pak dělo (nabití, zapnutí, vzorky), jde podle `instance_id`.
- Otázka s `--room` jde do roomu a General na ni ukazuje. Na neexistující room se nic neodešle.
- Moje shrnutí (`--gist`) je uvnitř odpovědi všude, kde se ta odpověď ukazuje.
- Nejnovější stav vyhrává a každá změna říká proč.

**P4**

- Zaseknuté čtení i tak zapíše `tick` a vlákno běží dál. Test pustí lokální pomalý server na portu 0 s timeoutem 0,5 s.
- Panel po třech intervalech bez vzorku ukáže stale.
- Obchod se zapíše jednou a znovu jen při změně.
- Sampler posílá jen GET.
- Sampler čte jen svých pět adres a jen to, co je podle našich záznamů naše: bota z `clones.jsonl` a neuzavřené pozice z `paper.jsonl`.
- Panel bota spojí staré vzorky z `clones.jsonl` se samplerovými do jedné řady.
- Oba launchery spouštějí `--sample 10` a `clone.py watch` jde přes stejné kolo.

Tvary jsem 11. 9. ověřil živým čtením. `index-history` vrací `points` s `t`, `index` a `share_price` (interval 5 dní, 212 bodů). `/activity` vrací `items` s obchody bota. Indikátory a typ strategie nese už `my-clones`, takže `/cloned-bots/available` sampler nečte.

Po P2 a po P4 je potřeba restartovat konzoli, protože běžící proces drží starý `serve.py`.

## Co tam schválně nebude

- **Tlačítko „spustit strategii" v prohlížeči.** Obchod z webového formuláře by obešel
  `--confirm`, kontrolu knihy i záznam. Obchoduje jen `paper.py` a `clone.py`.
- **Psaní z prohlížeče přímo Nexusovi.** K vendorovi se píše jen přes naše skripty. Tvoje
  poznámky čtu já a přenáším je sám.
- **Zvonek pro roomy.** Zvonek zůstává jen pro bug tracker (tvoje rozhodnutí z 8. 9.). Nová záložka na něj nesahá.
- **Texty z Telegramu a a2a.** Zůstávají mimo konzoli (tvoje rozhodnutí z 8. 9.). Roomy jsou jen
  pro Nexus, o který si teď říkáš.
- **Grafy NAV a redemption.** Nejsou v dokumentaci (tvoje pravidlo z 8. 9.).
- **„Resolves to DELTA via template mapping".** Je jen na jejich webu, API ho nevrací.
- **Nic z exportu telegramové historie** do projektu nepůjde.

## Soubory

**Nové**

- `qa/rooms.py`
- `scripts/rooms.py`
- `.claude/hooks/room_notes.py`
- `.claude/skills/nexus-session/SKILL.md`
- `tests/meta/test_pipeline_rooms.py`
- `tests/meta/test_pipeline_room_notes.py`

**Měněné**

- `scripts/serve.py`
- `scripts/render.py`
- `scripts/nexus.py` (`ask --room`)
- `scripts/clone.py` (`activity_rows`, `watch` do samples)
- `qa/channels.py`
- `scripts/channels.py` (watch)
- `.claude/settings.json` (hook a povolení `rooms.py`)
- `.claude/skills/channels/SKILL.md`
- `console.cmd` a `console.sh` (`--sample 10`)
- `.gitignore`
- `CLAUDE.md` (mapa a věta o úzkých zapisovačích)
- `tests/repo/test_live_server.py`

**Znovu použité**

- `qa.state.file_lock` / `state_dir`
- `qa.console.printable`
- `nexus.load()` / `latency_bounds()`
- `paper.position_rows()`
- `clone.clone_rows()` / `available_bots()`
- `esc` / `readStore` / `writeStore` v render.py
- node harness `_run_page`
- vzor fixtures `live` / `serve`

## Ověření

1. `python -m pytest tests/meta tests/repo -q` je zelené.
2. Restartuješ `console.cmd` a v záložce Nexus je General s 19 otázkami a 4 roomy se stavem a čísly.
3. Napíšeš poznámku do STR-0004 a hned u ní naskočí ✓. Tady řekneš „přečti si to", já ji vypíšu a v konzoli do 5 s naskočí ✓✓.
4. Uděláš `/clear`, zatímco je nějaká poznámka nepřečtená, a při startu session se objeví připomínkový řádek.
5. `git status` je po poznámce i po vzorku čistý. Mění se jen soubory v `.gitignore`, dashboard ne.
6. Restartuješ konzoli, necháš otevřenou starou záložku a napíšeš poznámku. Projde po jednom automatickém reloadu.
7. Vypneš síť a panel ukáže chybu posledního vzorku, sampler přitom běží dál. Po návratu sítě se série doplní.
