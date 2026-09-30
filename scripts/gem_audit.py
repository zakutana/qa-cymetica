"""The Gem Screener audit, run on demand: tick, brief, report.

The operator asked (2026-09-30) for the app to be walked through as a degen who
means to lean on its numbers in the next altseason -- every place that looks
wrong or that they would be afraid to trust -- and for the whole process to be
repeatable whenever it is wanted. The judgements live in `qa/gemaudit.py`, the
parts that will not change are held by `tests/rest/test_gem_screener_*.py`, and
this is the procedure that reads everything and says what moved:

    python scripts/gem_audit.py tick      read the page's snapshot, the picks, and
                                          CoinGecko / DefiLlama / DexScreener; write
                                          the report; print what moved since last time
    python scripts/gem_audit.py brief     one screen: how old the last tick is, what moved
    python scripts/gem_audit.py report    the last tick's tables (markdown)

A department in the repository's sense: a skill (`.claude/skills/gem-audit`), this
script, its diary `state/gem_audit.jsonl` and its report `state/gem_audit/
report.json`, which /lab lists without a line added anywhere else.

Read-only. Cymetica is read through a guarded anonymous client, the three sources
through `build_source_client`, which carries the same guard and none of their
credentials. Nothing is sent, filed or written outside `state/gem_audit*`: a
finding becomes a check and a report the way every other one does, by the sweep.
A source that does not answer leaves its section out and says so; it is never read
as agreement (rule 8).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import gemaudit as g  # noqa: E402
from qa.client import build_client, build_source_client, install_client_guard  # noqa: E402
from qa.config import identities  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

NAME = "gem_audit"
TITLE = "Gem Screener audit"
STALE_AFTER_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dir() -> Path:
    from qa.state import state_dir

    return state_dir() / NAME


def diary_path() -> Path:
    from qa.state import state_dir

    return state_dir() / f"{NAME}.jsonl"


def _write_text(target: Path, text: str) -> None:
    """Whole or not at all, whoever else is reading it (the /lab page reads
    report.json while a tick may be writing it)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            tmp.replace(target)
            return
        except PermissionError:
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05)


def load_diary() -> list[dict]:
    try:
        lines = diary_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def append_diary(row: dict) -> None:
    from qa.state import file_lock

    target = diary_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# -- reading ------------------------------------------------------------------

def read_everything() -> tuple[dict, dict]:
    """(inputs, errors). Inputs: snapshot, picks, coins, sources. Errors name
    what could not be read; the snapshot is the one thing without which there is
    no audit."""
    errors: dict[str, str] = {}
    registry = EndpointRegistry.load()
    anon = identities()["anon"]
    cymetica = build_client(anon, registry, timeout=90.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    inputs: dict = {"sources": {}}
    try:
        page = cymetica.get(g.APP_PAGE, headers={"Accept": "text/html"})
        if page.status_code != 200:
            raise SystemExit(f"{g.APP_PAGE} answered HTTP {page.status_code}: no snapshot, no audit")
        inputs["snapshot"] = g.parse_snapshot(page.text)

        listed = cymetica.get(g.PICKS)
        picks = (listed.json() or {}).get("picks") if listed.status_code == 200 else None
        if not picks:
            errors["picks"] = f"{g.PICKS} answered HTTP {listed.status_code} or no picks"
        else:
            inputs["picks"], inputs["coins"] = picks, {}
            for pick in picks:
                symbol = pick.get("symbol")
                one = cymetica.get(g.COIN.format(symbol=symbol))
                try:
                    body = one.json() if one.status_code == 200 else None
                except ValueError:
                    body = None
                if isinstance(body, dict):
                    inputs["coins"][symbol] = body
                else:
                    errors[f"coin {symbol}"] = f"HTTP {one.status_code}"
    finally:
        CURRENT_TIER.reset(token)
        cymetica.close()

    snap = inputs["snapshot"]
    source = build_source_client(timeout=90.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        universe = list((snap.get("altseason") or {}).get("alt50") or [])
        ids = [a.get("gecko_id") for a in snap["apps"]] + universe
        try:
            rows = g.fetch_coingecko(source.get, ids)
            inputs["sources"]["coingecko"] = rows
            inputs["sources"]["altseason_universe"] = [r for r in rows if r.get("id") in set(universe)]
        except (g.SourceUnavailable, Exception) as exc:  # noqa: BLE001
            errors["coingecko"] = str(exc)[:200]
        try:
            inputs["sources"]["llama"] = g.fetch_llama_revenue(source.get)
        except (g.SourceUnavailable, Exception) as exc:  # noqa: BLE001
            errors["defillama"] = str(exc)[:200]
        try:
            inputs["sources"]["dexscreener"] = g.fetch_dexscreener(source.get, g.pair_addresses(snap))
        except (g.SourceUnavailable, Exception) as exc:  # noqa: BLE001
            errors["dexscreener"] = str(exc)[:200]
    finally:
        CURRENT_TIER.reset(token)
        source.close()
    return inputs, errors


# -- the diary row: a few flat numbers, for "what moved" ------------------------

def metrics_of(report: dict) -> dict:
    src = report.get("sources") or {}
    picks = [p for p in report.get("picks") or [] if "what" not in p]
    alt = report.get("altseason") or {}
    bt = report.get("backtest") or {}
    cov = report.get("coverage") or {}

    def col(name, key):
        return (src.get(name) or {}).get(key)

    return {
        "snapshot_age_h": report.get("snapshot_age_h"),
        "supply_median": col("supply_vs_coingecko", "median"),
        "supply_over_tail": col("supply_vs_coingecko", "over_tail"),
        "price_median": col("price_vs_coingecko", "median"),
        "revenue_median": col("revenue_vs_defillama", "median"),
        "revenue_over_tail": col("revenue_vs_defillama", "over_tail"),
        "liquidity_median": col("pool_liquidity_vs_dexscreener", "median"),
        "liquidity_over_tail": col("pool_liquidity_vs_dexscreener", "over_tail"),
        "formula_breaches": len((report.get("upside_formula") or {}).get("breaches") or []),
        "identity_breaches": (len(report["pick_identity"]) if "pick_identity" in report else None),
        "picks": len(picks),
        "picks_buyable_on_chain": sum(1 for p in picks if p.get("buyable_on_chain")),
        "picks_with_exit_flag": sum(1 for p in picks if p.get("exit_flags")),
        "picks_negative_after_emissions": sum(1 for p in picks if (p.get("earnings_after_emissions_30d") or 0) < 0),
        "picks_young": sum(1 for p in picks if p.get("young")),
        "upside_rows_at_cap": (report.get("upside") or {}).get("at_cap"),
        "supply_older_than_24h": (report.get("freshness") or {}).get("supply_older_than_24h"),
        "level_range_over_two": cov.get("level_range_over_two"),
        "hot_themes": (report.get("themes") or {}).get("hot_now"),
        "altseason_cycle": alt.get("cycle_index"),
        "breadth_latest": alt.get("breadth_latest_week"),
        "breadth_shown_4w_mean": alt.get("breadth_4w_mean_shown"),
        "pegged_in_universe": len(alt.get("pegged_like_in_universe") or []) if "pegged_like_in_universe" in alt else None,
        "backtest": bt.get("verdict"),
        "live_picks_tracked": bt.get("live_picks_tracked"),
    }


def moved(before: dict | None, after: dict) -> list[str]:
    """Lines for the keys whose value changed since the last tick."""
    if not before:
        return ["first tick: nothing to compare with"]
    lines = []
    for key, now in after.items():
        was = before.get(key)
        if was == now:
            continue
        if isinstance(was, (int, float)) and isinstance(now, (int, float)):
            lines.append(f"{key}: {was:g} -> {now:g}")
        else:
            lines.append(f"{key}: {was} -> {now}")
    return lines or ["nothing moved"]


# -- commands -----------------------------------------------------------------

def tick() -> int:
    install_client_guard()
    inputs, errors = read_everything()
    snap = inputs["snapshot"]
    report = g.build_report(snap, sources=inputs["sources"], picks_api=inputs.get("picks"),
                            coins_api=inputs.get("coins"))
    report["errors"] = errors
    metrics = metrics_of(report)
    diary = load_diary()
    before = (diary[-1].get("metrics") if diary else None)
    at = _now().isoformat(timespec="seconds")

    lines = g.report_lines(report)
    if errors:
        lines.append("not read: " + ", ".join(sorted(errors)))
    _write_text(_dir() / "report.json", json.dumps({"title": TITLE, "at": at, "lines": lines},
                                                   ensure_ascii=False, indent=1))
    _write_text(_dir() / "latest.json", json.dumps(report, ensure_ascii=False, indent=1, default=str))
    _write_text(_dir() / "latest.md", g.render_markdown(report))
    append_diary({"type": "tick", "at": at, "snapshot_generated_at": snap.get("generated_at"),
                  "metrics": metrics, "errors": sorted(errors)})

    print(f"{TITLE}, {at}  (snapshot {report['snapshot_age_h']} h old)")
    for line in lines:
        print(f"  {line}")
    print("moved since the last tick:")
    for line in moved(before, metrics):
        print(f"  {line}")
    print(f"tables: {_dir() / 'latest.md'}")
    return 0


def brief() -> int:
    diary = load_diary()
    if not diary:
        print("Gem Screener audit: never run. `python scripts/gem_audit.py tick`")
        return 0
    last = diary[-1]
    try:
        days = (_now() - datetime.fromisoformat(last["at"])).total_seconds() / 86400.0
    except (KeyError, ValueError):
        days = None
    age = "unknown age" if days is None else f"{days:.1f} days ago"
    due = "  (due: `python scripts/gem_audit.py tick`)" if days is None or days >= STALE_AFTER_DAYS else ""
    print(f"Gem Screener audit: last tick {age}{due}")
    before = diary[-2].get("metrics") if len(diary) > 1 else None
    for line in moved(before, last.get("metrics") or {}):
        print(f"  {line}")
    if last.get("errors"):
        print("  not read last time: " + ", ".join(last["errors"]))
    return 0


def report() -> int:
    target = _dir() / "latest.md"
    try:
        print(target.read_text(encoding="utf-8"))
    except OSError:
        print("no report yet: `python scripts/gem_audit.py tick`")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The Gem Screener audit, on demand.")
    parser.add_argument("command", choices=("tick", "brief", "report"))
    args = parser.parse_args(argv)
    return {"tick": tick, "brief": brief, "report": report}[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
