"""Everything measured, before and after side by side in time: for each place, the live page (before) and the changed
one at each level run one after another on the weak machine, then on the strong one, so that what else the computer
was doing that hour falls on both alike. One run after another, nothing else at once.
  python batch.py <results dir> [places...]"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent
S = HERE.parent
PY = sys.executable
R = Path(sys.argv[1]); R.mkdir(parents=True, exist_ok=True)
places = sys.argv[2:] or ["start", "universe", "visit", "ours"]


def run(label, variant, sc, machine, runs, q=None):
    out = R / f"{label}-{sc}-{machine}.json"
    cmd = [PY, str(HERE / "perf.py"), "--rec", str(S / "rec"), "--variant", str(S / variant), "--scenario", sc,
           "--machine", machine, "--cpu", "3", "--runs", str(runs), "--out", str(out)] + (["--q", q] if q else [])
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"== {label} {sc} {machine} x{runs} ({time.time() - t:.0f} s)" + (" FAILED " + r.stderr[-600:] if r.returncode else ""), flush=True)


for sc in places:
    run("base", "base", sc, "weak", 2)
    run("low", "opt", sc, "weak", 2, "low")
    run("medium", "opt", sc, "weak", 2, "medium")
    run("high", "opt", sc, "weak", 1, "high")
    if sc in ("start", "ours"):
        run("auto", "opt", sc, "weak", 1, "auto")
    run("base", "base", sc, "fast", 1)
    run("high", "opt", sc, "fast", 1, "high")
    if sc in ("start", "ours"):
        run("auto", "opt", sc, "fast", 1, "auto")
