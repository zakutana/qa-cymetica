"""data.json for the mock: what the Supply Analyzer would hold with the other sources, read once, all real.

Collector Crypt: Streamflow's public dashboard, read by hand on 2026-11-02 (it needs a browser), and the monthly tranche from the
project's tokenomics as Bitrue quotes it. Lombard and the finished schedules: DefiLlama. The coins only DropsTab has: its next
unlock, since its page does not carry a whole schedule, so they get no 12-month figure here.
"""
import json
import re
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROWS = Path(r"C:\Users\adamz\AppData\Local\Temp\claude\C--Users-adamz-Documents-Projects-cymetica-qa-agent-qa-cymetica\9d358676-ea13-4114-85c2-d14c885102d8\scratchpad")
na = json.loads((ROWS / "sa_na.json").read_text(encoding="utf-8"))
ds = json.loads((ROWS / "ds_rows.json").read_text(encoding="utf-8"))
slug_of = {o["sym"]: o["slug"] for o in na}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
cl = httpx.Client(timeout=30, follow_redirects=True, headers=H)
now = time.time()
out = {"read": "2 Nov 2026", "sources": {}, "finished": {}, "dropstab": {}}

out["sources"]["collector-crypt"] = {
    "source": "Streamflow", "pct": 39.2, "new_tokens_12m": 346.8e6, "month_tokens": 44.6e6, "kinds": ["vesting"],
    "next": {"ts": 1795910400, "tokens": 44.59e6, "recipients": [{"who": "Team", "tokens": 32.87e6}, {"who": "Advisors", "tokens": 6.79e6}, {"who": "Seed", "tokens": 4.93e6}]},
    "until": "July 2027"}

d = cl.get("https://defillama-datasets.llama.fi/emissions/lombard").json()
ahead, month, tranches = 0.0, 0.0, []
for s in d["documentedData"]["data"]:
    pts = s.get("data") or []
    before = [p for p in pts if p["timestamp"] <= now]
    after = [p for p in pts if p["timestamp"] <= now + 365 * 86400]
    m1 = [p for p in pts if p["timestamp"] <= now + 30 * 86400]
    if before and after:
        add = after[-1]["unlocked"] - before[-1]["unlocked"]
        ahead += add
        got = m1[-1]["unlocked"] - before[-1]["unlocked"]
        month += got
        if got > 0:
            tranches.append({"who": s.get("label"), "tokens": got})
circ = 397e6
sa = json.loads((ROWS / "sa_batch.json").read_text(encoding="utf-8"))
for r in sa["items"]:
    if (r.get("token") or {}).get("slug") == "lombard" and r.get("circulating"):
        circ = r["circulating"]
out["sources"]["lombard"] = {"source": "DeFiLlama", "pct": round(100 * ahead / circ, 1), "new_tokens_12m": ahead, "month_tokens": month, "kinds": ["vesting"],
                             "next": {"ts": int(now + 30 * 86400), "tokens": month, "recipients": tranches}, "until": "September 2029"}

for o in na:
    if not o["llama"] or o["slug"] == "lombard":
        continue
    d = cl.get(f"https://defillama-datasets.llama.fi/emissions/{o['llama']}").json()
    last = 0
    for s in (d.get("documentedData") or {}).get("data") or []:
        for p in s.get("data") or []:
            last = max(last, p.get("timestamp") or 0)
    if last and last <= now:
        out["finished"][o["slug"]] = time.strftime("%B %Y", time.gmtime(last))

for r in ds:
    if not (r.get("ds") or {}).get("exists") or not r["ds"].get("same") or r["llama"]:
        continue
    resp = cl.get(f"https://dropstab.com/coins/{r['gecko']}/vesting")
    pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.S).group(1))["props"]["pageProps"]
    u = (pp.get("unlocks") or [None])[0]
    out["dropstab"][slug_of[r["sym"]]] = {"gecko": r["gecko"], "next": u and {"ts": int(u["date"] / 1000), "tokens": u.get("tokens"), "who": u.get("sale"), "type": u.get("unlockType")}}
    time.sleep(0.3)
(HERE / "data.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print({k: (len(v) if isinstance(v, dict) else v) for k, v in out.items()}, out["sources"]["lombard"]["pct"], list(out["finished"].items())[:4], list(out["dropstab"].items())[:2])
