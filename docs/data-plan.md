# Data ven z gitu, a revize deep passu — plán schválený 12. 9. 2026

Schválen po tvé otázce *„neni lepsi zalozit nejakou databazi pro ty vsechny
data? … ten data managment by mel byt taky spickovy, ale nevim jestli je pro to
github idealni"*.

## Co jsi rozhodl a co to škrtlo

- **Testy:** historické výsledky nezajímají — záznamem o historii jsou samy
  testy. Žádná oblast „testování" v revizi se nestaví.
- **Vývoj:** jestli TDD funguje a nemá díry, patří do deep passu. Žádná oblast
  „vývoj" se nestaví.
- **Laboratoř:** historie se vede dál, jak je. Beze změny.
- **Deep pass:** občas revizi, jestli běží optimálně.
- **Data:** ať se nekupí gigabajty, co nikdo nepoužije.

## Co bylo naměřeno 12. 9.

| | |
|---|---|
| sledovaný strom v gitu | **229 MB**, 1 843 souborů |
| z toho evidence | 167 MB (1 178 souborů: 570 `row`, 380 `promised`, 216 `their-words`, 12 `trade`) |
| z toho záznamy běhů | 44 MB |
| z toho kód a vše ostatní | **16,5 MB** |
| pack, který drží GitHub | 61 MB |
| přírůstek **po** dnešním prořezu | 182 MB v 8:19 → 229 MB v 16:03 |

Prořez řeší disk, ne git. A git nikdy nezapomíná: strom z 11. 9. měl 508 MB a
už je na GitHubu.

## Proč to jde bez ztráty

`verify.py` slibuje vendorovi, že evidence je *„retained … and provided on
request"*, a jeho vlastní docstring dodává, že repozitář je privátní, takže
stahování z GitHubu nikdy nebyla nabídka. **Git je naše volba úložiště, ne
součást slibu.** Obsah captures navíc nečte nic — pipeline pracuje s jejich id;
jediná výjimka je `qa/surface.py`, a ta sahá na posledních pár hodin.

Hash **je** důkaz neporušenosti, protože evidence je adresovaná obsahem. Manifest
v gitu tedy dokazuje, co jsme měli, i bez těla.

## Co se schválně nedělá

- **Databáze** — držela by stejné bajty; problém nebyl kolik, ale kde a jak
  dlouho. Přidala by závislost na dostupnosti k záznamu, jehož cena je, že se dá
  ověřit z commitu.
- **Git LFS** — free tier 1 GB a roste taky navždy; klon bez LFS dostane místo
  souborů ukazatele a tváří se zdravě.
- **Přepis historie** — rozbil by preregistrace i commity, které verdikty
  vendorovi citovaly. 61 MB minulosti je zaplacených; zastavuje se růst.

## Fáze

Každá: testy napřed (červené), pak kód, commit na `main`, bez pushe.

| # | Co | Hotovo, když | Stav |
|---|---|---|---|
| D1 | Manifest `audits/evidence-manifest.jsonl`: hash, bajty, `call_key`, důvod, archiv. Píše se tam, kde dnes `keep.py track` přidává do gitu | manifest pokrývá všech 1 178 držených captures; nový strážce běží **vedle** dvou stávajících gitových, ne místo nich — sledovanost padá až v D3, a strážce uvolněný dřív než jeho náhrada je okno, kde nehlídá nic | **hotovo `8f842524`** — 1 178 řádků, 228 kB za 167 MB těl (730:1) |
| D2 | `keep.py archive --month YYYY-MM`: zabalí těla do `archive/`, **ověří hash každého** a teprve pak je pustí z gitu | archiv se rozbalí a hashe sedí; `git rm --cached` až po ověření | **hotovo `ac1e2fba`** — 167 MB → 10,1 MB (16,5:1), 1 178 ověřeno, 0 vadných; a hned první běh odmítl pustit cokoli, protože id není sha256 souboru |
| D3 | Odpojení: `evidence/` ven ze sledovaných cest, `keep.py track` už těla nepřidává | strom spadne ze 229 MB na ~62 MB; oba strážce **povýšené**, ne uvolněné | **hotovo `ecbe511e`** — strom 229 → **63,8 MB**, 1 843 → 673 souborů, v `evidence/` nula |
| R1 | `scripts/review.py`: okno (`all`/`30d`/`last`/ISO), oblast deep pass nad `deep_pass_process.passes()` | pět tvarů okna projde; `last` bez checkpointu vypíše řádek o mezeře, ne tiché `all`; `condition()` nad **všemi** passy | **hotovo `ce4e21bd`** — a čtení nad ostrým repem nezmění ani bajt, což hlídá test |
| R2 | Oblast laboratoř, `checkpoint --area`, skill `ohlednuti`, krok 11 deep passu | DNA strážce se **nemusel měnit** — hlídka zůstává v kroku 11, škrtla se oblast vývoje z revize, ne čtení hlídky z passu | **hotovo `b5d798f6`** |

## Jedna vada, co se opraví po cestě

`patrol` sčítá okno s nekonečnem: `records_by_part()` nemá spodní mez, takže
`runs` je celoživotní počet přičtený k sedmidennímu. Past v opravě: pustit okno
i do záznamů znamená ztratit `last`, a čtrnáctidenní varování „tahle součást nic
nedělá" zmlkne přesně na součástech, kvůli kterým existuje. Dva průchody nad
jedním čtením: okno počítá `runs`, celá historie drží `last`.

## Kam archiv

Lokálně do `archive/`, mimo git. Kam se kopíruje dál je volba účtu a je tvoje;
default je, že leží lokálně a manifest je v gitu, takže i po ztrátě disku přesně
víme, co chybí a co si znovu vyžádat.

## Ověření

1. `pytest tests/meta tests/repo` zelené po každé fázi.
2. **Nejdůležitější:** po D2 rozbalit archiv do tempu a ověřit hash každého
   souboru proti jeho jménu. Teprve to opravňuje D3.
3. Po D3 `git count-objects -vH` a velikost stromu; den práce znovu změřit —
   přírůstek má být ~1 MB, ne 47.
4. Každý capture v keep-setu je buď na disku, nebo v archivu. Žádný jen
   v manifestu.
5. Součást s jediným záznamem starým 60 dní, okno 30 dní → `runs == 0`, ale
   `idle_days ≈ 60` a varování stále svítí.
