"""The forward log: this week's reading of the frozen rules, appended once, and what the earlier readings turned into.

    python -I outbox/retail-index/tick.py            read the sources again, append the latest week if it is new
    python -I outbox/retail-index/tick.py --read     no network: print every logged week with what the alt basket and BTC did next

The operator starts it (nothing here runs by itself). A row carries the sha256 of `qa/retailindex.py`: if the rules are
edited the hash changes, so a moved rule can not pass for the frozen one. The log is `state/retail_index/forward.jsonl`,
append-only, a few hundred bytes a week.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from qa import retailindex as R  # noqa: E402
from qa.paths import state_dir  # noqa: E402

DATA = HERE / "data"


def log_path() -> Path:
    return state_dir() / "retail_index" / "forward.jsonl"


def rows() -> list[dict]:
    try:
        lines = log_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def read_back(table, result):
    weeks, alt, btc = table["week"], table["alt_level"], table["btc"]
    at = {R.iso(w): i for i, w in enumerate(weeks)}
    print("logged week   index  zone       families  alt +13w  alt +26w  BTC +13w  BTC +26w")
    for r in rows():
        i = at.get(r["week"])
        cells = []
        for lvl in (alt, btc):
            for h in (13, 26):
                v = R.forward_return(lvl, i, h) if i is not None else None
                cells.append("   later " if v is None else f"{100 * v:+8.0f}%")
        print(f"{r['week']}  {r['index']:5.1f}  {r['zone']:9}  {r['nfam']:8d}  " + " ".join(cells))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--read", action="store_true", help="no network: read the log back against the table")
    ap.add_argument("--no-fetch", action="store_true", help="log from the table already on disk, without reading the sources")
    args = ap.parse_args(argv)
    if not args.read and not args.no_fetch:
        code = subprocess.call([sys.executable, "-I", str(HERE / "fetch.py"), "--refresh"])
        if code not in (0, 1):
            print("fetch failed outright, nothing logged", file=sys.stderr)
            return code
    table = R.read_table((DATA / "weekly.csv").read_text(encoding="utf-8"))
    result = R.compute_index(table)
    if args.read:
        read_back(table, result)
        return 0
    i = len(table["week"]) - 1
    if result["index"][i] is None:
        print("the latest week has no scored index (too few families): nothing logged")
        return 1
    week = R.iso(table["week"][i])
    if any(r["week"] == week for r in rows()):
        print(f"{week} is already in the log; index {result['index'][i]:.1f} ({R.zone(result['index'][i])})")
        return 0
    ma4 = R.moving_mean(result["index"])[i]
    row = {"week": week, "index": round(result["index"][i], 2), "zone": R.zone(result["index"][i]), "nfam": result["nfam"][i],
           "index_4w": None if ma4 is None else round(ma4, 2),
           "families": {f: (None if result["families"][f][i] is None else round(result["families"][f][i], 2)) for f in R.FAMILIES},
           "cymetica_v4": table["cy_v4"][i], "cymetica_v3": table["cy_v3"][i],
           # the baselines the back-test compared it with, so the next 13 and 26 weeks score all of them on new data
           "baselines": {"funding_pct": R.trailing_percentile(table["fund"])[i], "fear_greed": table["fng"][i],
                         "btc_price_pct": R.trailing_percentile(table["btc"])[i]},
           "code_sha256": hashlib.sha256((REPO / "qa" / "retailindex.py").read_bytes()).hexdigest()[:16]}
    p = log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"logged {week}: index {row['index']} ({row['zone']}), {row['nfam']} families; Cymetica v4 {row['cymetica_v4']}, v3 {row['cymetica_v3']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
