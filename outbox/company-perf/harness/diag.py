"""What the office's frame is made of, on the weak machine: high, with one part of the scene taken away at a time (the
sky, the rooms' lamps, everything transparent, the sun's shadow, the post chain, the fill lights). Not a change to
make: a measure of where a frame's GPU time goes, so the levels cut what costs.
  python diag.py <after variant> [scenario] [diag,...]"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent
S = HERE.parent
variant = sys.argv[1]
scen = sys.argv[2] if len(sys.argv) > 2 else "visit"
diags = sys.argv[3].split(",") if len(sys.argv) > 3 else ["nosky", "nolamps", "noglass", "noshadow", "nopost", "nofill"]
res = S / "results"; res.mkdir(exist_ok=True)
for d in diags:
    out = res / f"diag_{d}-{scen}-weak.json"
    cmd = [sys.executable, str(HERE / "perf.py"), "--rec", str(S / "rec"), "--variant", variant, "--scenario", scen,
           "--machine", "weak", "--cpu", "3", "--runs", "1", "--q", "high", "--diag", d, "--out", str(out)]
    t = time.time()
    print(f"== {d} {scen}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-800:] if r.returncode else "", f"({time.time() - t:.0f} s)", flush=True)
