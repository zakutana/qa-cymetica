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

- [ ] 2026-09-10  Naklonovat Hybrid 2 (Blue) v paper režimu — bota, kterého Nexus sám doporučil (+19,86 % backtest, Sharpe 2,79, max DD 1,75 %)

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

- [ ] 2026-09-10  Doměřit Nexus kanál na větším vzorku, než z něj uděláme závěr pro Cymeticu

  Deep pass opravil měření a první pravdivý údaj je zlý: tři z pěti hlubokých
  dotazů nedopověděly, zbylé 1527 s, 552 s a 535 s proti jejich publikovaným
  300 s. Ale pět je pět. `WINDOW = 5` v `tests/mcp/test_nexus_channel.py` je
  tam schválně, aby oprava mohla kontrolu vyčistit — takže než operátor napíše
  na Telegram, že jim kanál nefunguje, chce to víc než pět položených otázek.

  `python scripts/nexus.py ask "..."` je SAFE tier, nic nestojí a zapisuje se.

- [ ] 2026-09-10  Až jim pojede web chat, dát operátorovi větu pro Nexus a zapsat, na co se zeptal — kontrola pro jejich CEO

  Nexus tvrdí, že se před sestavením obchodu ptá na dvě věci: časový horizont
  a toleranci ztráty. Přes `ask_nexus_deep` se nezeptal ani na jednu. Web chat
  je kontrolní vzorek a jde na něj jenom přes prohlížeč, takže tu jednu větu
  tam pošle operátor: *„I want to turn $1000 into $1200. Compose a trade for
  me."* Naše je pamatovat si to a zapsat odpověď — dneska jim web chat neběžel.
