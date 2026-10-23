"""Run perf.py over the scenarios and machines, one after another, each result to its own JSON.
  python matrix.py <variant dir> <label> [--q high|medium|low|auto] [--machines weak,fast] [--warm] [scenarios...]"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent
S = HERE.parent
args = sys.argv[1:]
variant, label, rest = args[0], args[1], args[2:]
q, machines, warm = None, ["weak", "fast"], False
scen = []
i = 0
while i < len(rest):
    if rest[i] == "--q":
        q = rest[i + 1]; i += 2; continue
    if rest[i] == "--machines":
        machines = rest[i + 1].split(","); i += 2; continue
    if rest[i] == "--warm":
        warm = True; i += 1; continue
    scen.append(rest[i]); i += 1
scen = scen or ["start", "universe", "visit", "ours"]
res = S / "results"; res.mkdir(exist_ok=True)
plan = []
for sc in scen:
    for m in machines:
        plan.append((sc, m, False, 2 if m == "weak" else 1))
        if warm and m == "weak":
            plan.append((sc, m, True, 1))
for sc, mach, w, runs in plan:
    out = res / f"{label}-{sc}-{mach}{'-warm' if w else ''}.json"
    cmd = [sys.executable, str(HERE / "perf.py"), "--rec", str(S / "rec"), "--variant", variant, "--scenario", sc,
           "--machine", mach, "--cpu", "3", "--runs", str(runs), "--out", str(out)] + (["--warm"] if w else []) + (["--q", q] if q else [])
    t = time.time()
    print(f"== {label} {sc} {mach}{' warm' if w else ''} x{runs}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-1500:] if r.returncode else "", f"({time.time() - t:.0f} s)", flush=True)
