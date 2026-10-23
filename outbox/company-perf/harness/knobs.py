"""What each setting costs on the weak machine: the office (visit) and the Universe at high, then high with one setting
of low, one at a time, then low whole. One run each (their spread is the A/A of the base runs).
  python knobs.py <after variant> [scenario]"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent
S = HERE.parent
variant = sys.argv[1]
scen = sys.argv[2] if len(sys.argv) > 2 else "visit"
KNOBS = [("high", None), ("samples0", '{"samples":0}'), ("mirror0", '{"mirror":0}'), ("shadow1s", '{"shadow":1024,"shadowMs":1000}'),
         ("bloomq", '{"bloomDiv":2}'), ("pr1", '{"pr":1}'), ("idle30", '{"idleMs":33}')]
res = S / "results"; res.mkdir(exist_ok=True)
for name, setting in KNOBS:
    out = res / f"knob_{name}-{scen}-weak.json"
    cmd = [sys.executable, str(HERE / "perf.py"), "--rec", str(S / "rec"), "--variant", variant, "--scenario", scen,
           "--machine", "weak", "--cpu", "3", "--runs", "1", "--q", "high", "--out", str(out)] + (["--set", setting] if setting else [])
    t = time.time()
    print(f"== {name} {scen}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-800:] if r.returncode else "", f"({time.time() - t:.0f} s)", flush=True)
