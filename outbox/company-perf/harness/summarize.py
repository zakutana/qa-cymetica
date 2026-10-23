"""One table from the results: per scenario and machine, each label's mean over its runs (and each run's spread).
  python summarize.py <results dir> [labels...]"""
import json, statistics, sys
from pathlib import Path

R = Path(sys.argv[1])
want = sys.argv[2:]
rows = {}
for f in sorted(R.glob("*.json")):
    label, rest = f.stem.split("-", 1)
    if want and label not in want:
        continue
    for r in json.loads(f.read_text()):
        key = (r["scenario"], r["machine"] + ("-warm" if r.get("warm") else ""))
        rows.setdefault(key, {}).setdefault(label, []).append(r)


def m(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "-"
    s = statistics.mean(vals)
    return f"{s:.0f}" + (f"±{(max(vals) - min(vals)) / 2:.0f}" if len(vals) > 1 else "")


def ph(r, p, k):
    return (r["phases"].get(p) or {}).get(k)


COLS = [("boot ms", lambda r: r.get("boot_ms")), ("1st 3D ms", lambda r: r.get("first_draw_ms")), ("load LT ms", lambda r: ph(r, "load", "lt_sum")),
        ("load LT max", lambda r: ph(r, "load", "lt_max")),
        ("idle fps", lambda r: ph(r, "idle", "draw_fps")), ("idle gpu%", lambda r: ph(r, "idle", "gpu_busy")),
        ("idle LT ms", lambda r: ph(r, "idle", "lt_sum")),
        ("drag fps", lambda r: ph(r, "drag", "draw_fps")), ("drag p95", lambda r: ph(r, "drag", "draw_p95")),
        ("drag >50", lambda r: ph(r, "drag", "over50")),
        ("uvopen ms", lambda r: ph(r, "uvopen", "ms")), ("uvdrag fps", lambda r: ph(r, "uvdrag", "draw_fps")),
        ("uvdrag p95", lambda r: ph(r, "uvdrag", "draw_p95")),
        ("devices", lambda r: r["gpu"]["devices"]), ("pipes", lambda r: r["gpu"]["pipelinesSync"] + r["gpu"]["pipelinesAsync"]),
        ("tex MB", lambda r: r["gpu"]["texPeakMB"]), ("bytes KB", lambda r: r.get("bytes", 0) / 1024)]
for key in sorted(rows):
    print(f"\n### {key[0]} · {key[1]}")
    labels = list(rows[key])
    cols = [c for c in COLS if any(c[1](r) is not None for lab in labels for r in rows[key][lab])]
    print("| | " + " | ".join(c[0] for c in cols) + " |")
    print("|---|" + "---|" * len(cols))
    for lab in labels:
        rs = rows[key][lab]
        q = rs[0].get("q") or ""
        print(f"| {lab}{(' ' + q) if q else ''} (n={len(rs)}) | " + " | ".join(m([c[1](r) for r in rs]) for c in cols) + " |")
