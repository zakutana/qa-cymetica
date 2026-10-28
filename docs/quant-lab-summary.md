# Quant Lab: souhrn všeho, co víme (stav 2026-10-28)

Vlož celé do nového okna chatu. Je psané tak, aby šlo číst bez znalosti dřívější konverzace. Co je moje zjištění a co jejich tvrzení, je řečeno
u každé věci: **[jejich]** = tvrzení Cymetica/Nexuse (neověřeno nezávisle), **[viděli jsme]** = přečteno na jejich stránce nebo v API, **[náš závěr]** = úsudek.

## 1. Co Quant Lab je

Oddělení firmy v Build a Company (cymetica.com/company/app, stránka experimentů /company/app/experiments). Hledá, které obchodní pravidlo
s jakým nastavením by vydělávalo, přehráním minulosti na paperu, bez peněz. Navrhl ho Nexus (REPLY-0216, MSG-0248). Náš Build it Better
request na něj je ET-32976. Pro plán Pro a vyšší, hledání nespotřebuje jednotky plánu **[jejich]**. Naše firma: company 14 "BJ Ironstar Capital".
Nezaměňovat s **naší laboratoří** (naše skripty, "lab Wave 2 …" boti): to je jiná věc než jejich Quant Lab.

## 2. Slovník (tohle je to, co bylo nejvíc zmatené)

- **Bot / agent** = to, co obchoduje. Karty na /perpetual/agents jsou boti; když jednu naklonuješ, tvoje kopie je na /my-agents.
- **Model (algoritmus)** = položka katalogu /adm (20). Je to **obchodní pravidlo se vzorcem a čísly**, ne jazykový model. 10 biomimetických:
  HELIX, PRION, ENZYME, SYNAPSE, CORTEX, TELOMERE, IMMUNE, CIRCADIAN, MITOSIS, CRISPR; 10 pravděpodobnostních: RUPTURE, ORACLE, VERDICT,
  SIGNAL, MIRAGE, ANCHOR, DRIFT, RECOIL, ENDGAME, FLUX. Placené: PRION 9,99 $, SYNAPSE 14,99 $, TELOMERE 14,99 $. Bot nese až 5 modelů.
  Příklad: HELIX = long, když je MACD histogram nad 0 a EMA 9 nad EMA 21 **[jejich, z kódu pravidla]**.
- **Skill** = položka /skills-n-tools (29: indikátory, datové zdroje, filtry…). Bot má 3 primární + 3 sekundární sloty. Skill není model
  (MACD Crossover je skill). Quant Lab skilly neprohledává.
- **Backtested Strategy bot** (na /perpetual/agents: StockBot Blue/Red, CryptoBull Blue/Red, Hybrid 2 Blue/Red, RSI Mean Reversion, Trend Following SMA,
  Bollinger Breakout, MACD Momentum): výsledek na kartě je **modelovaný** (pravidla přehraná na minulých cenách), žádné skutečné obchody.
- **Agent se záznamem** (Sync Master, Delta Hunter, Sent Surfer, Stat Oracle, Corr Catcher): skutečné sázky na jejich perpetual trzích. Nemají backtest
  pravidlo, proto je hledání neprohledává.
- **Paper** = fake peníze v reálném čase; **live** = vlastní peníze; **backtest** = přehrání minulosti.
- **Tvůj klon na záložce Strategy [viděli jsme]:** "DECIDES ON": DELTA (Delta Hunter), "inherited · species rule"; HELIX "MACD + EMA momentum, abstains
  without a signal"; CORR "prior-epoch momentum, baseline". Text: "The source template's strategy is backtest-scope only, so live entries resolve to
  DELTA (Delta Hunter) via direction mapping." Nasazené modely a skilly: 0.

## 3. Dvě různé věci, které se pletou

1. **Hledání (Hero-agent search)**: hledá nová pravidla; to je popis níže.
2. **Smyčka ladění klonu ("Auto-optimize")**: existující klon denně dostane malou změnu nastavení, ověří se na neviděných datech, nasadí se, příští den se
   změří, při ztrátě se vrátí **[jejich, REPLY 25. 10.]**. Je to stejný motor jako u fondu Tuatara (viz /fund-optimizations). Štítek "Auto-optimize ready" je na
   /my-agents, jen přihlášený, u vlastních klonů s jedním z 10 biomimetických modelů; tlačítko (Pro) spouští plné hledání. Na /perpetual/agents není.
3. **Sekce "Bots" v labu**: zkouší tvůj paper bot nebo paper klon Backtested Strategy bota na jeho skutečných paper obchodech proti tvému pravidlu
   (minimum obchodů, minimální výnos, maximální pokles, několik oken po sobě). Při neúspěchu může lab navrhnout jednu změnu. Live boty dovnitř nejdou.

## 4. Jak hledání funguje, krok za krokem [jejich /how-it-fits, 28. 10.]

1. 16 pravidel: 10 biomimetických z /adm + 6 pravidel Backtested Strategy botů (stockbull_blue, stockbear_red, cryptobull_blue, cryptobull_red,
   hybrid2_blue, hybrid2_red). Neprohledává: skilly, 10 pravděpodobnostních modelů (RUPTURE, ENDGAME, ANCHOR…), tvoje boty, agenty typu Sync Master.
2. Každý krypto trh s aspoň 1 200 hodinovými svíčkami (~50 dní). Naše první běhy: 12 trhů (DOT, LINK, AVAX, SOL, ATOM…).
3. Ke každé dvojici pravidlo × trh až 27 nastavení: stop-loss × take-profit × vstupní práh (přísnější / stejný / volnější). Starší běhy měly jen 9 (SL × TP).
   1 728 zkoušek = 16 × 12 × 9 **[náš výpočet]**.
4. Vybere nejlepší na dřívějších 60 % historie, přeskočí 24 hodin, pak ověří vybrané na pozdější části, kterou nikdy neviděl (held-back).
5. Výhra jen když výsledek přeskočí laťku, která roste s počtem zkoušených kombinací (kvůli štěstí). Nejlepší kandidáti na dřívějších datech vypadají skvěle,
   na zadržených většinou propadnou.
6. Co přeskočí, "se spustí jako paper bot". **Ale viz bod 5.**

## 5. Nejdůležitější zjištění: výherce neobchoduje to pravidlo, které vyhrálo [jejich REPLY-0236, ET-33133]

- Výhra `stockbull_blue` nespustí **žádného** bota (to pravidlo není nasaditelný model).
- Výhra volného modelu (HELIX…) spustí klon CryptoBull; jeho živé vstupy řídí "direction mapping", tedy Delta Hunter. Vítězný SL/TP se použije jen jako pauza celého
  bota, ne u pozice.
- Model nasazený z /adm mění backtesty a hledání, **nikdy živý obchod** (platforma ho značí jako "backtest only").
- Most z labu k obchodujícímu botovi **není postavený**; sledovaný build bez data, napíšou při dokončení. Prázdný bot už živě umí indikátorová pravidla na
  hodinových svíčkách; chybí spojení.
- [náš závěr] Lab dnes **hlásí, co by se v minulosti osvědčilo**, ale skutečného bota se stejným pravidlem nevyrobí. Test a obchodování nejsou totéž.

## 6. Skutečný běh [viděli jsme + jejich příklad v /how-it-fits sekce 6]

Hledání č. 3 z 27. 10.: `stockbull_blue` na DOT, 9 nastavení na 29. 7.–21. 9., nejlepší SL 3 / TP 30 = **+29,60 %**. Zadrženo 22. 9.–27. 10.: **−3,09 %** na 59 obchodech,
laťka 9,97 % (z = 4,0213 pro 1 728 kombinací). Verdikt: prohrál, jako všech 5 nejlepších (helix DOT −1,94 %, stockbull_blue LINK −12,30 %, AVAX −6,87 %, SOL −10,01 %).
**Žádný bot nevznikl.** Jiný výherce nebyl ukázán. Reálný výsledek (kolikrát lab nějakého výherce našel) nevíme.

## 7. Co lab neumí a co se opravilo (nápady a schvalování)

- Lab posílal majiteli karty "IDEA" ke schválení (approval ids 19 až 23). Schválení u idea karet jen zaznamená rozhodnutí. **ET-33080:** vstupní práh **postaven a živý**
  (mřížka 27, hledání ~2,5× delší, výherce se změněným vstupem se jen nahlásí); signal weights a AI confidence **nejdou tak, jak jsme žádali** (modely nemají váhy ani
  číslo jistoty; velký build); replay pro arbitráž, DEX a funding je střední build (nepostaveno); placené modely jsou cenové rozhodnutí majitele (náš závěr: zatím ne).
- **ET-33125** (naše výtka, že lab žádal nemožné) **[jejich]** vyřešeno: lab předem kontroluje proveditelnost, karta má řádek "Exists today / Needs a small, medium, large
  build / Not possible", stránka má blok "What the lab can tune today" (API: can_tune, cannot_tune, what_changed), při změně schopností přijde jedna zpráva do chatu.
  Pět čekajících karet zmizelo (v /company/mine je 0 approvalů).
- **Bug (náš, MSG-0270/0271):** Command (Manager) neumí přečíst čekající approvaly, ačkoli jsou čitelné přes `GET /api/v1/company/mine` (pole `approvals` s `details`). Odpověď zatím není.

## 8. Fond Tuatara: /fund-optimizations (jiná věc, ale stejná metoda) [viděli jsme]

Veřejný deník ladění algoritmů hedge fondu Tuatara (názvy pod kódy P-…). 41 hledání: 53 % lepších na neviděných datech, průměr +1,01 pp na obchod; "post-training"
průměr −0,42 pp; z 401 živých změn se 19 použilo a 12 vrátilo po ztrátovém dni, očekávaný směr se trefil v 51 %. [náš závěr] Efekt je malý a blízko hodu mincí; věta
"masivní moat" zatím nemá oporu v číslech.

## 9. Co jsme postavili my

- `outbox/quant-lab-graphic/` (http://127.0.0.1:8798/): animovaná grafika kroků hledání. **Pozor:** sloupec "Paper only" ukazuje přeživší jako paper boty, což podle bodu 5 dnes
  neplatí; je to ke změně. První sloupec už říká "16 model rules × every crypto market".
- Stránka `/quest` (outbox/quest): krok 2B přepsán z "Breed a Hero Agent" na "Find a Hero Agent. The Quant Lab tests strategies on past data."

## 10. Otevřené otázky (pro debatu)

1. Kdy bude postaven most lab → bot, a bude výherce obchodovat vítězné pravidlo?
2. Kolik hledání už proběhlo, kolik výherců našlo, kolik z nich prošlo i paperem? (Žádný jsme neviděli.)
3. Co přesně dělá každé z 16 pravidel (HELIX známe; ostatní jen z tabulky v /how-it-fits, kterou jsme nečetli celou).
4. Kolik paper klonů smí běžet najednou, a co lab stojí (jednotky, čas jednoho hledání; plný běh je ~2,5× delší s prahem)?
5. Má cenu naše úsilí, když fond sám má jen mizivý efekt? (náš názor: jako experiment ano, jako "moat" zatím ne.)
6. Jak otestovat, že lab fakticky nenalezl nic (jestli je chyba v metodě, v datech, nebo v laťce).

## 11. Kde jsou záznamy

Korespondence: REPLY-0233 (Season 0), REPLY-0234 (ET-33125), REPLY-0235 (/how-it-fits), REPLY-0236 (příklad, ET-33133); naše zprávy MSG-0277 (feasibility), MSG-0278 (mapa), MSG-0281 (příklad).
Příkaz: `python scripts/correspond.py show <id>`. Poznámky o Quant Labu v repu: outbox/find-profitable-bot/README.md.
