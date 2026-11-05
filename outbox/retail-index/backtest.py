"""The back-test of retail index v5 (or, with --v6, the social index v6) against the rules in RESULT.md, one table, and
the same checks on every baseline.

    python -I outbox/retail-index/backtest.py [--json] [--v6 [--v6b]]

No network: it reads `data/weekly.csv` (and `data/social_weekly.csv` for v6). Same table in, same bytes out (the last
line is a digest of every number, so an A/A run is one comparison). Nothing here is fitted. `--v6b` adds the variant
written down beside v6 (social + turnover + premia); RESULT.md says to show it only if v6 fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from qa import retailindex as R  # noqa: E402
from qa.paths import atomic_write  # noqa: E402

DATA = HERE / "data"
SEGMENTS = {"all": (None, None), "2018-2023": (None, R.ordinal("2023-12-31")), "2024-now": (R.ordinal("2024-01-01"), None)}


def mask(series, weeks, lo, hi):
    return [v if (lo is None or w >= lo) and (hi is None or w <= hi) else None for v, w in zip(series, weeks)]


def cell(r):
    if r["status"] == "not scorable":
        return "n/s"
    return f"{r['value']:.0f}{'P' if r['status'] == 'pass' else 'F'}{'*' if r['thin'] else ''}"


def verdict(rows):
    scored = [r for r in rows if r["status"] != "not scorable"]
    return None if not scored else all(r["status"] == "pass" for r in scored)


def r1(x):
    return None if x is None else round(x, 4)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="also write data/backtest.json (data/backtest_v6.json with --v6)")
    ap.add_argument("--v6", action="store_true", help="score the social index v6 instead of v5")
    ap.add_argument("--v6b", action="store_true", help="with --v6: also the social + turnover + premia variant")
    args = ap.parse_args(argv)

    table = R.read_table((DATA / "weekly.csv").read_text(encoding="utf-8"))
    fams = R.FAMILIES
    if args.v6:
        table = R.merge_social(table, (DATA / "social_weekly.csv").read_text(encoding="utf-8"))
        fams = R.SOCIAL_FAMILIES
    features = [c for cols in fams.values() for c, _ in cols]
    weeks = table["week"]
    n = len(weeks)
    res = R.compute_index(table, families=fams if args.v6 else None)
    ours = "v6 (ours)" if args.v6 else "v5 (ours)"
    sets = {
        ours: (res["index"], res["nfam"]),
        ours.replace(" (ours)", " 4w (post-hoc)"): (R.moving_mean(res["index"]), res["nfam"]),
        "Cymetica v4": (table["cy_v4"], None),
        "Cymetica v3": (table["cy_v3"], None),
        "Fear & Greed": (table["fng"], None),
        "BTC price pct": (R.trailing_percentile(table["btc"]), None),
        "Funding pct": (R.trailing_percentile(table["fund"]), None),
    }
    if args.v6:
        v5 = R.compute_index(table)
        sets["v5 (earlier)"] = (v5["index"], v5["nfam"])
        sets["Wikipedia only"] = (res["families"]["attention"], None)
        if args.v6b:
            b = R.compute_index(table, families=R.V6B_FAMILIES)
            sets["v6b (+turnover, premia)"] = (b["index"], b["nfam"])
    alt, btc = table["alt_level"], table["btc"]
    out: dict = {"weeks": n, "scored": sum(v is not None for v in res["index"])}
    lines: list[str] = []

    def say(s=""):
        lines.append(s)

    # ---- B1 / B2 ------------------------------------------------------------------------------
    say("B1 top windows (highest week in date +/- 6 weeks, needs >= 70) and B2 low windows (lowest week, needs <= 35)")
    say("   P pass, F fail, * only two families behind it, n/s not scorable")
    head = "".join(f"{d[:7]:>9}" for d in R.TOP_DATES) + " |" + "".join(f"{d[:7]:>9}" for d in R.LOW_DATES)
    say(f"{'':14}{head}   B1    B2")
    out["b1b2"] = {}
    for name, (s, nf) in sets.items():
        tops = R.check_windows(s, weeks, nf, R.TOP_DATES, "top")
        lows = R.check_windows(s, weeks, nf, R.LOW_DATES, "low")
        out["b1b2"][name] = {"tops": tops, "lows": lows}
        v1, v2 = verdict(tops), verdict(lows)
        extra = ""
        if args.v6:
            v75 = verdict(R.check_windows(s, weeks, nf, R.TOP_DATES, "top", top_min=75.0))
            out["b1b2"][name]["b1_75"] = v75
            extra = f"   B1' {'-' if v75 is None else ('PASS' if v75 else 'FAIL')}"
        say(f"{name:14}" + "".join(f"{cell(r):>9}" for r in tops) + " |" + "".join(f"{cell(r):>9}" for r in lows)
            + f"   {'-' if v1 is None else ('PASS' if v1 else 'FAIL'):4}  {'-' if v2 is None else ('PASS' if v2 else 'FAIL'):4}" + extra)
    if args.v6:
        say("   B1' = the same top windows asked for 75 instead of 70 (the v6 bar)")
    say()

    # ---- B3 price proxy -------------------------------------------------------------------------
    say("B3 |Spearman| with the BTC weekly close, 2018-01 to now (needs <= 0.40); and B9 share of scored weeks at 75+ (needs <= 10%), longest run")
    start = R.ordinal("2018-01-01")
    out["b3"], out["b9"] = {}, {}
    for name, (s, _nf) in sets.items():
        m = mask(s, weeks, start, None)
        rho = R.spearman(m, btc)
        share, longest = R.top_zone_share(s)
        out["b3"][name], out["b9"][name] = r1(rho), {"share": r1(share), "longest": longest}
        say(f"  {name:14} rho {('%+.2f' % rho) if rho is not None else '  -':>6}  {'' if rho is None else ('PASS' if abs(rho) <= R.SPEARMAN_MAX else 'FAIL'):4}"
            f"   at 75+: {('%.1f%%' % (100 * share)) if share is not None else '-':>6}, run {longest:2d} wk  "
            f"{'' if share is None else ('PASS' if share <= R.SHARE_MAX and longest <= 26 else 'FAIL')}")
    say()

    # ---- B4 robustness --------------------------------------------------------------------------
    say(f"B4 robustness of {ours.split()[0]}: leave one family out (latest reading moves by <= 15; B1/B2 verdict unchanged), leave one cycle out")
    base_top = verdict(out["b1b2"][ours]["tops"])
    base_low = verdict(out["b1b2"][ours]["lows"])
    now_base = res["index"][-1]
    out["b4"] = {"family": {}, "cycle": {}, "latest": r1(now_base)}
    for fam in fams:
        r = R.compute_index(table, drop_family=fam, families=fams if args.v6 else None)
        t = verdict(R.check_windows(r["index"], weeks, r["nfam"], R.TOP_DATES, "top"))
        lo = verdict(R.check_windows(r["index"], weeks, r["nfam"], R.LOW_DATES, "low"))
        d = None if r["index"][-1] is None or now_base is None else r["index"][-1] - now_base
        out["b4"]["family"][fam] = {"latest": r1(r["index"][-1]), "delta": r1(d), "b1": t, "b2": lo}
        flag = "ok" if d is not None and abs(d) <= R.LEAVE_MAX and t == base_top and lo == base_low else "MOVES"
        say(f"  without {fam:9} latest {('%.1f' % r['index'][-1]) if r['index'][-1] is not None else '-':>5}  (delta {('%+.1f' % d) if d is not None else '-':>5})"
            f"  B1 {t}  B2 {lo}  {flag}")
    cycles = {"to 2018": (None, R.ordinal("2018-12-31")), "2019-2022": (R.ordinal("2019-01-01"), R.ordinal("2022-12-31")),
              "2023 on": (R.ordinal("2023-01-01"), None)}
    all_dates = [("top", d) for d in R.TOP_DATES] + [("low", d) for d in R.LOW_DATES]
    for cname, (lo, hi) in cycles.items():
        def inside(day, lo=lo, hi=hi):
            return (lo is None or day >= lo) and (hi is None or day <= hi)

        t2 = {k: v[:] for k, v in table.items()}
        for k in features:
            for i, w in enumerate(weeks):
                if inside(w):
                    t2[k][i] = None
        r = R.compute_index(t2, families=fams if args.v6 else None)
        changed = []
        for kind, d in all_dates:
            if inside(R.ordinal(d)):
                continue
            a = R.check_windows(res["index"], weeks, res["nfam"], (d,), kind)[0]["status"]
            b = R.check_windows(r["index"], weeks, r["nfam"], (d,), kind)[0]["status"]
            if a != b:
                changed.append(f"{d[:7]} {a}->{b}")
        out["b4"]["cycle"][cname] = changed
        say(f"  without the {cname:10} cycle's data: verdicts of the other windows that change: {changed or 'none'}")
    say()

    # ---- B5 forward -----------------------------------------------------------------------------
    say("B5 forward return, weeks at 75+ minus all other weeks (95% block-bootstrap interval), alt basket and BTC, 13 and 26 weeks")
    out["b5"] = {}
    for name, (s, _nf) in sets.items():
        row = {}
        for seg, (lo, hi) in SEGMENTS.items():
            flags = [None if v is None else v >= R.SATURATED for v in mask(s, weeks, lo, hi)]
            for tag, lvl in (("alt", alt), ("btc", btc)):
                for h in (13, 26):
                    fw = [R.forward_return(lvl, i, h) for i in range(n)]
                    b = R.block_bootstrap_diff(flags, fw)
                    row[f"{seg}|{tag}{h}"] = None if b is None else {k: r1(v) if isinstance(v, float) else v for k, v in b.items()}
        out["b5"][name] = row
        parts = []
        for seg in SEGMENTS:
            b = row[f"{seg}|alt13"]
            parts.append(f"{seg}: " + ("-" if not b or b["diff"] is None else f"{100 * b['diff']:+.0f}% [{100 * b['lo']:+.0f},{100 * b['hi']:+.0f}] n={b['flagged']}"))
        say(f"  {name:14} alt 13w  " + " | ".join(parts))
    say()

    # ---- B6 episodes ----------------------------------------------------------------------------
    say("B6 saturated runs (75+) followed within 26 weeks by an alt fall of >= 30% from the running high; Awake events followed by +50%")
    out["b6"] = {}
    out["base"] = {}
    for seg, (lo, hi) in SEGMENTS.items():
        lo_i = next((i for i, w in enumerate(weeks) if lo is None or w >= lo), 0)
        hi_i = max((i for i, w in enumerate(weeks) if hi is None or w <= hi), default=n - 1)
        out["base"][seg] = {k: r1(v) if isinstance(v, float) else v for k, v in R.base_rates(alt, lo_i, hi_i).items()}
    say("  base rate (ANY week): " + " | ".join(
        f"{seg}: fall {100 * b['fall']:.0f}%, rise {100 * b['rise']:.0f}% over {b['weeks']} wk" for seg, b in out["base"].items()))
    for name, (s, _nf) in sets.items():
        row = {}
        for seg, (lo, hi) in SEGMENTS.items():
            m = mask(s, weeks, lo, hi)
            so, ao = R.saturated_outcomes(m, alt), R.awake_outcomes(m, alt)
            row[seg] = {"sat_runs": len(so["runs"]), "sat_fell": r1(so["share"]), "awake_events": len(ao["events"]), "awake_rose": r1(ao["share"])}
        out["b6"][name] = row
        say(f"  {name:14} " + " | ".join(
            f"{seg}: sat {row[seg]['sat_runs']} runs {('-' if row[seg]['sat_fell'] is None else '%.0f%%' % (100 * row[seg]['sat_fell']))}, "
            f"awake {row[seg]['awake_events']} ev {('-' if row[seg]['awake_rose'] is None else '%.0f%%' % (100 * row[seg]['awake_rose']))}" for seg in SEGMENTS))
    say()

    # ---- B8 permutation and the extended events ------------------------------------------------------
    centers = [R.ordinal(d) for d in R.TOP_DATES] + [R.ordinal(d) for d in R.LOW_DATES]
    kinds = ["top"] * len(R.TOP_DATES) + ["low"] * len(R.LOW_DATES)
    zz = R.zigzag(alt)
    ext_c = [weeks[i] for i, _k in zz]
    ext_k = ["top" if k == "top" else "low" for _i, k in zz]
    say(f"B8 event capture (dated windows: share that pass) and its permutation p (2000 block shuffles); extended events = {len(zz)} alt-basket turning points "
        f"({sum(k == 'top' for k in ext_k)} tops, {sum(k == 'low' for k in ext_k)} bottoms), all and 2024-now")
    out["b8"] = {}
    tops_pos = [i for i, k in zz if k == "top"]
    first_alt = next(i for i, v in enumerate(alt) if v is not None)

    def precision(s):
        """POST-HOC, not in RESULT.md: of the 75+ runs that start with the alt basket in existence, the share that has a
        confirmed alt-basket top from its start to 6 weeks after its end."""
        runs = [(a, b) for a, b in R.runs_at_or_above(s, R.SATURATED) if a >= first_alt]
        return (sum(any(a <= t <= b + 6 for t in tops_pos) for a, b in runs) / len(runs) if runs else None), len(runs)

    for name, (s, nf) in sets.items():
        cap, tot = R.capture(s, weeks, nf, centers, kinds)
        p = R.permutation_p(s, weeks, nf, centers, kinds)
        ecap, etot = R.capture(s, weeks, nf, ext_c, ext_k)
        late = [(c, k) for c, k in zip(ext_c, ext_k) if c >= SEGMENTS["2024-now"][0]]
        lcap, ltot = R.capture(s, weeks, nf, [c for c, _ in late], [k for _, k in late])
        prec, nruns = precision(s)
        out["b8"][name] = {"dated": r1(cap), "dated_n": tot, "p": r1(p), "extended": r1(ecap), "extended_n": etot, "late": r1(lcap), "late_n": ltot,
                           "precision_posthoc": r1(prec), "runs": nruns}
        f = lambda v: "-" if v is None else f"{100 * v:.0f}%"  # noqa: E731
        say(f"  {name:14} dated {f(cap)} of {tot}  p={('-' if p is None else '%.3f' % p)}   extended {f(ecap)} of {etot}   2024-now {f(lcap)} of {ltot}"
            f"   | post-hoc: {nruns} runs at 75+, {f(prec)} contain a top")
    say()

    # ---- the reading now ------------------------------------------------------------------------
    say("Now (latest week " + R.iso(weeks[-1]) + "): " + ", ".join(
        f"{name} {('%.0f' % s[-1]) if s[-1] is not None else '-'}" for name, (s, _nf) in sets.items())
        + f"; {ours.split()[0]} zone {R.zone(res['index'][-1])}, families {res['nfam'][-1]}")
    out["now"] = {name: r1(s[-1]) for name, (s, _nf) in sets.items()}

    if args.v6:
        # ---- the peak signal, the rule written before the first run ---------------------------------
        say()
        say("Peak signal (hot in the last 13 weeks, 4-week mean 15 under its 26-week high; once per 26 weeks): tops caught within 8 weeks,"
            " signed delay in weeks, false alarms")
        out["peak"] = {}
        for name in (ours, "Cymetica v3", "Cymetica v4"):
            s = sets[name][0]
            sig = R.peak_signals(s)
            sc = R.score_signals(sig, weeks, R.TOP_DATES, tops_pos)
            out["peak"][name] = {"signals": [R.iso(weeks[i]) for i in sig], "caught": sc["caught"], "false_alarms": sc["false_alarms"],
                                 "tops": sc["tops"]}
            cells = "  ".join(f"{t['date'][:7]} " + ("miss" if not t["caught"] else f"{t['delay']:+d}w") for t in sc["tops"])
            say(f"  {name:14} {sc['caught']} of {len(R.TOP_DATES)} caught  [{cells}]  signals {sc['signals']}, false alarms {sc['false_alarms']}")
        say("  v6 signal weeks: " + ", ".join(out["peak"][ours]["signals"]))

        # ---- the done-when, line by line ---------------------------------------------------------------
        say()
        say("Done-when for v6, from the numbers above:")
        mine = out["b1b2"][ours]
        hit75 = verdict(R.check_windows(res["index"], weeks, res["nfam"], R.TOP_DATES, "top", top_min=75.0))
        share, longest = R.top_zone_share(res["index"])
        b8 = out["b8"][ours]
        lines_ = [
            ("B1' every scorable top window holds a week at 75+", hit75),
            ("B2 every scorable low window holds a week at 35-", verdict(mine["lows"])),
            ("B3 |rho| with BTC at most 0.40", out["b3"][ours] is not None and abs(out["b3"][ours]) <= R.SPEARMAN_MAX),
            ("B9 at most 10% of weeks at 75+, no run over 26", share is not None and share <= R.SHARE_MAX and longest <= 26),
            ("B8 permutation p at most 0.05", b8["p"] is not None and b8["p"] <= 0.05),
            ("75+ runs that contain a confirmed top: at least 75%", b8["precision_posthoc"] is not None and b8["precision_posthoc"] >= 0.75),
        ]
        out["done_when"] = {k: v for k, v in lines_}
        for k, v in lines_:
            say(f"  [{'x' if v else ' '}] {k}")

    body = json.dumps(out, sort_keys=True, indent=1)
    digest = hashlib.sha256(body.encode()).hexdigest()[:16]
    say(f"digest {digest}")
    print("\n".join(lines))
    if args.json:
        atomic_write(DATA / ("backtest_v6.json" if args.v6 else "backtest.json"), body + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
