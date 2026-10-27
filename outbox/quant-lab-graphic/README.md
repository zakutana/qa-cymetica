# The Quant Lab graphic (experiments page)

Asked for by the operator on 2026-10-27 after Nexus explained the Quant Lab in ET-33054 ("it is a hit and a massive moat,
show it so a degen sees what is going on"). One looping picture of the lab's search, in Nexus's own words cut to a few:

1. **Try everything**: every bot model x every market (a cloud of strategies, all looking great on past data).
2. **Blind test**: data the search never saw, against a bar that rises with every try (most fall, the few that clear it turn green).
3. **Paper only**: the survivors trade fake money and draw their own equity lines.
4. **You decide**: the desk puts the best in front of you with three ways to take it (a paper seat at a table, a live copy made
   paused and unfunded, a small stake); you tap one. "Nothing trades until you approve."
Along the foot a strip fills with one cell per combination tried: the lab remembers every one.

Every number comes from one small simulation (`QL` in index.html) and the page says so in its corner: *Illustration,
simulated numbers*. They are not the lab's real results; the real ones are what the experiments page itself shows.

Open: `python -m http.server 8798 --bind 127.0.0.1 --directory outbox/quant-lab-graphic` (the `quant-lab-graphic` entry in
`.claude/launch.json`), then http://127.0.0.1:8798/. Tests: `python -m pytest outbox/quant-lab-graphic/tests -o addopts="" -p no:cacheprovider`.

Next, if it is liked: put it at the top of our mock's experiments page (outbox/company-live/experiments.html, above the
cards, collapsible) and describe it in the Quant Lab request for Cymetica. Desktop first; a phone layout is not drawn yet.
