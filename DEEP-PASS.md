# Deep pass — 2026-09-10

Běh `deep-pass 2026-09-10`, start na commitu `481958e`, preregistrace
**PRE-0080**, běh **run-20260910T164705Z-b56d1d3**, level V.
62 commitů k pushnutí, strom čistý.

## Co se stalo

**36 nálezů, 30 potvrzených, 30 opravených, 0 odložených na tebe.**

| odkud | nálezů | potvrzeno | zamítnuto | menšinových |
|---|---|---|---|---|
| audit kontraktů (3 auditoři, 55 funkcí) | 24 | 24 | 0 | 0 |
| code review xhigh (přes 5 850 řádků zdroje) | 9 | 3 | 4 | 2 |
| krok 1 — vlastní údržba | 2 | 2 | — | — |
| krok 1b — prořez | 1 | 1 | — | — |

Triáž: tři čtenáři, 34 nálezů, **31 jednomyslných**. Triáda zamítla 4 nálezy
a všechny čtyři byly z **mé recenze**, ani jeden z auditu. Auditoři čtou
tvrzení proti kontraktu, který si test sám napsal; já jsem četl kód a
domýšlel dopad, který nikam nedosáhne.

Konec: 583 prošlo, 5 selhalo, 4 neprůkazné. Dvě selhání byla nesložený ledger
a fold je vyřešil. Tři jsou nálezy na jejich straně.

## Opraveno

**Strážce pouštěl na MUTATE nástroj, o kterém nic neví.** `_check_rpc` odmítal
`trade` a `provision` a pak vypadl z funkce — takže MCP nástroj, který není v
žádném seznamu v `components.yaml`, byl na jediné úrovni, která umí utrácet,
**povolen s plnými argumenty**. Na SAFE se odmítá jménem, na PROBE se nutí
prázdné argumenty. Po každém jejich releasu je to běžný stav, ne výjimka:
publikují 62 nástrojů a jeden dnes ráno změnili. `trade_event_card` sám v
žádném seznamu není, takže odebrání jeho brány by ho z odmítnutého udělalo
povolený.

**Podlaha u peněz četla, že příznak existuje, ne který to je.** Přejmenování
`required_flags` u `agents.clone` z `[paper]` na `[confirm]` nechalo všechny
tři strážce zelené a MUTATE POST s `confirm: true` bez `paper` prošel — a
absenci `paper` řeší jejich schéma proti `simulation_mode`, který je na tomhle
účtu False.

**Obě kontroly nad tím, co odchází vendorovi, četly text skriptu, ne zprávu.**
Kontrola, že už jim neposíláme odkaz do našeho privátního repa, grepovala
zdroj `submit.py`; poskládat ten řádek z proměnné a odkaz odejde znovu se
zelenou kontrolou. A `identity_kind`, který rozhoduje, kterou ze dvou vět o
otisku jim pošleme, neměl test vůbec.

**Nexus kanál měřil stopky, které se restartují.** `waited_seconds` se počítá
od vstupu do polling smyčky, a `nexus.py answer` do ní vstoupí znovu — takže
otázka položená v 10:00, vzdaná v 10:15 a vyzvednutá v 11:00 se zapsala jako
„0 sekund". Kontrola pak hlásila, že kanál drží slíbených 1–5 minut. Po
opravě, měřeno od otázky: **tři z pěti nedopověděly vůbec, zbylé 1527 s,
552 s a 535 s proti jejich vlastnímu stropu 300 s.**

**A extraktor nástrojů v Nexusových odpovědích neviděl nic.** Vyžadoval slovo
„MCP" před zpětnými uvozovkami a ve dvou ze tří zaznamenaných odpovědí našel
nula nástrojů. Po rozšíření vidí 8 místo 3.

**Kniha uvolňovala kapitál, který nevidí.** `book()` tiše přeskočil přijatou
objednávku, jejíž pozici jejich endpoint nevrátil — komentář u toho řádku
říkal „stojí za povšimnutí" a nevšímalo si toho nic. Peníze se vrátily do
hotovosti a `affordable()` by je povolil utratit znovu.

**Kontrola paper zůstatku procházela jako `passed`, když selhalo čtení
pozic.** `(x or 0)` proměnilo chybějící klíč na nulu, `0 - 39 = -39` vyhodilo
obchod z posuzované množiny a zbyla prázdná — verdikt „každý nákup odečetl
svou hodnotu", zatímco se nepohnulo nic. Pravidlo 8 obráceně, na řádku, který
by překlopil #87 na VERIFIED FIXED.

**Jediný skript, který maže, bral selhané čtení jako prázdné.** Záznam běhu
zachycený v půli zápisu se rozparsuje na `{}`, mine všechny důvody k zachování
a smaže se. A `cited_run_ids` hledalo jen klíč `run_id`, takže běh jmenovaný v
*textu důvodu* withdraw eventu — důkaz pro retrakci u #83 — by se za pět dní
stal obětí.

**Čtyři render kontroly testovaly řetězec místo chování.** Číslo „opravených
bugů" sčítalo přechody, takže 19 přechodů přes 16 nálezů se zobrazilo jako 19.
Odměny se nikdy neporovnaly s jejich vlastním číslem. Harness JS testu
podstrkoval prázdný seznam řádků, takže se komparátor řazení nikdy nespustil.
A tabulka modelů se porovnávala dvěma parsery, z nichž ani jeden se nedíval na
stránku.

**Devět dalších kontrol nemohlo zčervenat pro stav, který samy jmenují** —
včetně tří, které tenhle pass dnes napsal a auditor je posoudil stejně tvrdě
jako zbytek. Správně.

## Prořezáno

* **Paměti.** Jedna retirovaná: `correspondence-arrives-only-through-the-bounty-api`.
  Její první věta — „jejich bug tracker je jediný příchozí kanál" — přestala
  platit 8. září. Rozdíl my-reports / a2a-inbox, kvůli kterému vznikla, drží
  `qa/channels.py` a mapa v CLAUDE.md. Její vlastní varování znělo, že paměť
  může být v době napsání přesná a přesto instalovat špatný model; stala se
  tím. Sloučeno nic — prošel jsem 30 popisů a žádné dva se nepřekrývají tak,
  aby jedno vstřebalo druhé.
* **Mechanismy.** `never_fired --zeros` šlo z 5 na 4. Všechny čtyři jsou
  zkoušené testem, takže žádný není rozbitý; k odstranění nešel ani jeden.
* **Testy.** `tests/meta` narostlo 254 → 260. Šest nových: tři pro cp1250
  konzoli (`test_pipeline_console.py`, nový soubor — zvažoval jsem přidat je
  do `test_pipeline_adapters.py`, kde žije `bounty._printable`, ale ten testuje
  *transkódování textu*, ne rekonfiguraci streamu, a spojit je by znamenalo
  jeden soubor o dvou nesouvisejících strategiích), a tři přibyly rozšířením
  existujících kontrol v guard, book a channels souborech.

## Minority report

Dva nálezy dostaly jeden hlas ze tří. Nejsou zahozené, protože nejdůležitější
nález 7. září našla přesně jedna cesta.

* **R07 — `_positions` čte 200 s neočekávaným obalem jako nula pozic.**
  `(response.json() or {}).get("positions") or []` vrátí prázdno pro tělo
  tvaru `{"result": {"positions": [...]}}` — a `buy()` ve stejném souboru
  `payload["result"]` rozbaluje. Dva čtenáři to zamítli, protože všech 41
  zachycených odpovědí má tvar `{count, positions}`. To je fakt o dnešních
  datech, ne o té funkci.
* **A06 — `test_cloning_a_bot_needs_its_paper_flag_too` netestuje
  `agents.clone`.** Docstring říká „**obě** klonovací cesty". Dva čtenáři to
  zamítli, protože smazání pravidla chytí jiná kontrola; jediná mutace, která
  projde — přejmenování příznaku — je A05, a ta je opravená.

## Změněná pravidla

**Retirace paměti se značí v řádku, ne smazáním řádku.**

Krok 1b předepisoval retirovat paměť smazáním jejího řádku z `MEMORY.md`
(`rm` unattended pass nesmí). Provedl jsem to a `tests/repo` zčervenalo:
nezalinkovaný soubor se hlásí jako ten, o kterém nikdo neví — což je červená
v kroku 6, kterou krok 9 řeší revertem celé noci. Ani jedna půlka nebyla
špatně: nezalinkovaný soubor je opravdu neviditelný a záznam opravdu musí
přežít, protože ten adresář je mimo git a `MEMORY.md` je jeho jediná historie.
Chyběl způsob, jak říct, co z toho se stalo.

Řádek teď zůstává a nese `RETIRED YYYY-MM-DD: důvod`.

**Byl to třetí návrh.** Dva poziční šly ke třem čtenářům první a každý byl
shozen dřív, než přistál — pokaždé ze stejného důvodu: nadpis `## Retired`
musí být na konci souboru a na konec souboru se připisuje řádek nové paměti.
První pokus nadpis spolkl každý připsaný řádek. Druhý to opravil požadavkem na
datum, dokud jeden čtenář nenašel, že vlastní jednořádkový popisek paměti může
datem začínat — a v reálném `MEMORY.md` takový řádek už byl.

Hlasy nad druhou verzí: **ne, ne, ano** — projde. Verze, která je
zacommitovaná, poziční parsování ruší úplně, tedy zavírá i tu zbytkovou mezeru,
kterou pojmenoval nesouhlasící čtenář *a* označil ji jako jedinou zbývající i
jeden ze souhlasících. Je přísnější než to, co bylo odhlasováno, ve směru,
kterým ukazovaly oba nesouhlasy. **Tvoje veto je otevřené.**

## Čeká na tebe

* **Nexus jim nefunguje, a teď to máme změřené jejich vlastním číslem.** Tři
  z pěti posledních hlubokých dotazů nedopověděly. Zbylé trvaly 25 minut, 9 a
  9 minut proti jejich publikovaným 1–5. Verifikace `fail` odešly na #85, #86
  a #87 — a u #85 a #86 to jsou **opravy záznamu**, protože dřívější verdikt
  spočítala kontrola, která tu vadu neviděla. Stojí za zprávu na Telegram, ale
  formulace je tvoje.
* **Nový nález, nezaložený.** Nexus říká agentovi, ať zavolá MCP nástroj
  `update_bot_settings`, který jejich server neservíruje. Deep pass nezakládá
  reporty — to je na sweepu, který je tvůj.
* **Jeden z triage agentů nechal v repu odkládací soubor** (`memories_old.py`)
  navzdory instrukci pracovat ve vlastním tempu. Odstraněno. Kdyby se to
  opakovalo, je to důvod tu instrukci zpřísnit, ne ji opakovat.

## Týden

Neproběhl. Poslední byl 2026-09-09, tedy před jedním dnem; je splatný po
sedmi. `retrospective.done` zůstává false.

## Co mě to naučilo

**Nálezy z auditu obstály, nálezy z mé recenze ze dvou třetin ne.** Čtyři
zamítnuté byly všechny moje. Rozdíl není v pečlivosti: auditor drží tvrzení
proti kontraktu, který si ten test **sám napsal**, takže jeho nález má vestavěný
protějšek. Já jsem četl kód a domýšlel si, kam ten dopad dosáhne — a třikrát ze
čtyř nedosáhl nikam (`asked_at_from` nečte nic kromě testu, souhrn v
`prune_runs` se tiskne *před* mazací smyčkou, `bounty.py` píše `at` vždy).

**Dvakrát mě heredoc připravil o zpětné lomítko a pokaždé to vypadalo jako
chyba v logice.** `\b` v regexu dorazilo jako znak backspace; grep ho vykreslil
neviditelně a testy padaly na něčem, co v souboru vypadalo správně. CLAUDE.md
to říká, a říká to právě kvůli tomuhle.

**A jednou jsem `git checkout` použil na soubor, jehož opravy nebyly
zacommitované** — vrátil se celý, ne jen mutace. Mutační test se dělá na
zacommitovaném souboru, jinak je to nerozlišitelné od úklidu.
