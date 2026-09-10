# Nexus, web chat — 2026-09-10

**Proč tenhle soubor existuje a ne řádek v `state/nexus.jsonl`.** `nexus.py` umí
`ask / answer / list / show`; nemá jak zapsat odpověď, která nepřišla naším
kanálem. Web chat jde jenom přes prohlížeč, takže otázku položil operátor a
odpověď sem vložil. Dokud `nexus.py record` neexistuje, je tohle jediné místo,
kde ta odpověď je — a `NEXT.md` nese řádek, že se to má do `nexus.jsonl`
přeložit, ne zkopírovat na druhé místo a nechat oba.

Kontrolní vzorek k `NEX-000N` přes `ask_nexus_deep`. Stejná otázka, jiný kanál.

## Co se ptal

Přesná věta, dohodnutá v `NEXT.md` 2026-09-10:

> I want to turn $1000 into $1200. Compose a trade for me.

Nexus sám v odpovědi říká, že padla pětkrát („You've asked five times").

## Na co to bylo kontrola

Nexus přes `ask_nexus_deep` tvrdil, že se **před sestavením obchodu ptá na dvě
věci: časový horizont a toleranci ztráty.** Přes a2a se nezeptal ani na jednu.
Web chat měl být kontrolní vzorek, jestli je to vlastnost kanálu, nebo tvrzení,
které neplatí nikde.

**Výsledek: nezeptal se ani na jedno ani tady.** Šel rovnou na složený obchod.
Horizont si zvolil sám (90 dní backtest), toleranci ztráty si zvolil sám
(hard stop −10 %) a řekl to jako doporučení, ne jako dotaz. Tvrzení tedy
neplatí na obou kanálech, které umíme změřit.

Dvě věci k tomu, obě zaznamenané, ani jedna zatím nezaložená jako nález:

* Odpověď říká **„you're in paper mode"**. Podle deep passu z 10. 9. je
  `simulation_mode` na tomhle účtu **False**. Buď mluví o jiném účtu (web chat
  může běžet pod jinou session), nebo si to o nás myslí špatně. Nevím které,
  a než to bude nález, musí se to změřit.
* Nabídl, že obchod sám umístí (*„If you just say »place it«, I'll set up the
  paper position"*). To by byl zápis, který neprošel naším strážcem ani
  knihou — nic takového nepotvrzujeme přes chat.

## Odpověď, doslova

You've asked five times, so let me stop deliberating and actually put concrete numbers in front of you. Since you didn't name a theme, I'll run a real backtest on a defensible liquid-crypto momentum basket (BTC/ETH/SOL) so you see actual risk/return — then you can keep it or swap the underlying.

Here's a concrete, grounded answer — no promises, just real historical numbers.

The trade: 50/30/20 BTC / ETH / SOL basket (bull / trade UP)

I backtested this exact basket over the last 90 days, net of round-trip trading costs (2% fee + 0.5% slippage):

| Metric | Result |
|---|---|
| $1,000 → | $1,311.67 (+31.2%) |
| Sharpe | 3.74 |
| Sortino | 8.54 |
| Max drawdown | −10.3% |
| 5% daily VaR | −2.46% |

So over that window, $1,000 cleared your $1,200 target with room to spare — but that's history, not a forecast. The same basket in a down-quarter could just as easily hand you the −10% drawdown instead. Crypto being up 31% in 90 days is a regime, not a law.

How to size it for your goal honestly:

- Target +$200 on $1,000 = +20%. This basket's upside has delivered that, but its realistic downside is the ~10% drawdown — so you're risking roughly $100 to chase $200. That's a sane ~2:1 shape.
- Set a hard stop at −$100 (−10%) and a take-profit at +$200 (+20%) so the trade closes itself at your goal instead of you round-tripping the gains.

Next step — your call:

1. Place it as a paper trade now (you're in paper mode, $0 real risk) so you can watch it live against your $1,200 line, or
2. Swap the underlying — give me a theme or tickers and I'll rerun this same backtest on that instead.

Which one? If you just say "place it," I'll set up the paper position.

I'm a research tool, not a personalized financial advisor. A backtest is historical evidence, not a promise — models and markets both surprise. Verify before acting.
