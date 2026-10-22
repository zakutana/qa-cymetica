# Airdrop Farmer

Design and working test version of Airdrop Farmer (`cymetica.com/airdrop-farmer`). **Read [SPEC.md](SPEC.md)**: what to build, why, every part and every number.

![Farms](pictures/1-farms.jpg)

## Run it

Download this folder and open `mock.html` in a browser, or serve it:

```
python -m http.server 8796
```

then open http://localhost:8796/mock.html. Everything runs on test data in the browser; nothing is sent anywhere.

Try: type an amount (the best split fills in), drag a slider (the pillar and the estimate follow; past your balance it takes from the weakest farms), press START FARMING, then on Live farms set 1 day = 1 s in the test bar and watch the pillars grow; HARVEST when a farm lights up.

`mock.html?shot=1&tab=farms`, `&tab=live`, `&tab=logo`, `&modal=1`: the frozen states in `pictures/`.

## Files

- `mock.html` the page and its styles
- `farm-core.js` farms, maths, plan, start, harvest, stop, the 6-month clock
- `farm-ui.js` views: the field, the list, the confirmation, Live farms, controls
- `pictures/` the target, 1440 px
- `spec.txt` the short Build it Better text
