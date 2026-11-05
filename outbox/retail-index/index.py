"""Compute retail index v5 from `data/weekly.csv` and write `data/index.csv`.

    python -I outbox/retail-index/index.py [--last N]

No network. Same table in, same bytes out. Rules: RESULT.md; the functions are `qa/retailindex.py`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from qa import retailindex as R  # noqa: E402
from qa.paths import atomic_write  # noqa: E402

DATA = HERE / "data"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--last", type=int, default=8, help="how many of the latest weeks to print")
    args = ap.parse_args(argv)
    table = R.read_table((DATA / "weekly.csv").read_text(encoding="utf-8"))
    result = R.compute_index(table)
    atomic_write(DATA / "index.csv", R.index_csv(table, result))
    n = len(table["week"])
    scored = sum(v is not None for v in result["index"])
    print(f"index v5: {scored} of {n} weeks scored, first {R.iso(table['week'][next(i for i, v in enumerate(result['index']) if v is not None)])}")
    print("week        index  families  zone        " + "  ".join(f"{f:>8}" for f in R.FAMILIES))
    for i in range(n - args.last, n):
        v = result["index"][i]
        fam = "  ".join(f"{result['families'][f][i]:8.1f}" if result["families"][f][i] is not None else "       -" for f in R.FAMILIES)
        print(f"{R.iso(table['week'][i])}  {('%5.1f' % v) if v is not None else '    -'}  {result['nfam'][i]:8d}  {(R.zone(v) or '-'):10}  {fam}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
