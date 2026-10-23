"""Where the main thread's time went in a .cpuprofile: self time by function (file:line), and by file, and the
inclusive time of the functions asked for.  python profsum.py <profile> [t0_ms t1_ms] [--incl name,name]"""
import json, sys
from collections import defaultdict
from pathlib import Path

P = json.loads(Path(sys.argv[1]).read_text())
args = sys.argv[2:]
incl_names = []
if "--incl" in args:
    i = args.index("--incl"); incl_names = args[i + 1].split(","); args = args[:i] + args[i + 2:]
t0 = float(args[0]) if len(args) > 0 else None
t1 = float(args[1]) if len(args) > 1 else None
nodes = {n["id"]: n for n in P["nodes"]}
parent = {}
for n in P["nodes"]:
    for c in n.get("children", []):
        parent[c] = n["id"]
# sample times (µs from startTime)
t = P["startTime"]
self_us = defaultdict(float)
times = []
for sid, dt in zip(P["samples"], P["timeDeltas"]):
    t += dt
    times.append((sid, t, dt))
start = P["startTime"]
for i, (sid, ts, dt) in enumerate(times):
    nxt = times[i + 1][2] if i + 1 < len(times) else 0
    rel = (ts - start) / 1000
    if t0 is not None and rel < t0:
        continue
    if t1 is not None and rel > t1:
        continue
    self_us[sid] += nxt


def name(n):
    cf = n["callFrame"]
    u = cf["url"].split("/")[-1].split("?")[0] or "(native)"
    return f"{cf['functionName'] or '(anon)'} {u}:{cf['lineNumber'] + 1}"


by_fn, by_file = defaultdict(float), defaultdict(float)
for sid, us in self_us.items():
    n = nodes[sid]
    by_fn[name(n)] += us
    u = n["callFrame"]["url"].split("/")[-1].split("?")[0] or n["callFrame"]["functionName"] or "(native)"
    by_file[u] += us
tot = sum(self_us.values()) / 1000
print(f"total sampled {tot:.0f} ms")
print("\n-- by file")
for k, v in sorted(by_file.items(), key=lambda x: -x[1])[:14]:
    print(f"{v / 1000:8.0f} ms  {k}")
print("\n-- by function (self)")
for k, v in sorted(by_fn.items(), key=lambda x: -x[1])[:40]:
    print(f"{v / 1000:8.0f} ms  {k}")
if incl_names:
    print("\n-- inclusive")
    inc = defaultdict(float)
    for sid, us in self_us.items():
        seen = set(); x = sid
        while x is not None:
            fn = nodes[x]["callFrame"]["functionName"]
            if fn in incl_names and fn not in seen:
                inc[fn] += us; seen.add(fn)
            x = parent.get(x)
    for k in incl_names:
        print(f"{inc[k] / 1000:8.0f} ms  {k}")
