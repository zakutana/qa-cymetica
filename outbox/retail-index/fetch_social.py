"""Read the social sources for retail index v6 and write `data/social_weekly.csv`.

    python -I outbox/retail-index/fetch_social.py [--refresh] [--only SUB]

Wikimedia pageviews (CC0) and the Arctic Shift archive of Reddit submissions, as anonymous GETs through
`build_source_client`. The archive times out on long ranges and serves about 1.5 thousand rows a second, so a Reddit member
is sampled (RESULT.md, amendment 1): one request per day, on the Tuesday and the Friday of each week. A day that times out is
asked again in later passes. Answers are written to `cache/reddit/<sub>.json` as they come, so a stopped run resumes where it
stopped and a finished one reads only the new days. Past days do not change, so `--refresh` reads Wikimedia again and keeps
the Reddit cache (`--only SUB --refresh` empties that one subreddit). A source that does not answer is named and its column stays empty.
Rules: RESULT.md, the v6 section.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from qa import retailindex as R  # noqa: E402
from qa.client import build_source_client  # noqa: E402
from qa.paths import atomic_write  # noqa: E402
from qa.safety import CURRENT_TIER, SafetyTier  # noqa: E402

CACHE = HERE / "cache"
DATA = HERE / "data"
FIRST_WEEK = R.ordinal("2015-08-03")
READ_FROM = R.ordinal("2015-01-01")
WIKI = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{title}/daily/{a}/{b}"
ARCTIC = "https://arctic-shift.photon-reddit.com/api"
# Wikimedia's robot policy refuses a User-Agent with no contact (a URL or an address); the repo is that contact.
UA = {"User-Agent": "qa-cymetica-retail-index/1.0 (https://github.com/zakutana/qa-cymetica; public research read, GET only)"}
PAUSE = 1.5


class SourceError(Exception):
    pass


class Slow(SourceError):
    """The archive answered 'Timeout. Maybe slow down a bit'."""


def get(client, url, params=None, tries=3):
    last = "no answer"
    for i in range(tries):
        try:
            r = client.get(url, params=params, headers=UA)
        except Exception as exc:  # noqa: BLE001 - named in the run's output, never swallowed
            last = type(exc).__name__
            time.sleep(3 * (i + 1))
            continue
        if r.status_code == 200:
            try:
                body = r.json()
            except ValueError:
                raise SourceError(f"{url}: a body that is not JSON")
            if isinstance(body, dict) and body.get("error"):
                raise Slow(str(body["error"])[:80])
            return body
        last = f"HTTP {r.status_code}"
        if r.status_code == 422 and "Timeout" in r.text:
            raise Slow(r.text[:80])
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (i + 1))
            continue
        break
    raise SourceError(f"{url}: {last}")


# ---- Wikimedia -----------------------------------------------------------------------------

def read_wiki(client, title, last_day):
    a, b = "2015070100", R.date.fromordinal(last_day).strftime("%Y%m%d") + "00"
    return get(client, WIKI.format(title=title, a=a, b=b)).get("items") or []


# ---- Reddit --------------------------------------------------------------------------------

def sub_start(client, sub):
    for attempt in range(8):
        try:
            d = get(client, f"{ARCTIC}/subreddits/search", params={"subreddit": sub, "limit": 1, "fields": "created_utc"})
            break
        except Slow:
            time.sleep(15 * (attempt + 1))
    else:
        raise SourceError(f"{sub}: the archive never answered the question when it was created")
    rows = d.get("data") or []
    if not rows:
        raise SourceError(f"{sub}: no such subreddit in the archive")
    return max(READ_FROM, R.ordinal_of_epoch(rows[0]["created_utc"]))


sample_days = R.sample_days


def read_reddit(client, sub, end, refresh=False):
    """Submissions on each sampled Prague day for `sub` before day `end`, one day per request. Returns the cache dict:
    `days` {iso: count}, `done` the sampled days already answered (a day with no submissions answers with no row, so
    zero is recorded here, not guessed), `next` a legacy cover from the first chunked read: every day before it is done.
    A day the archive times out on is asked again in later passes; one that never answers stays unread."""
    path = CACHE / "reddit" / f"{sub}.json"
    state = {"start": None, "next": None, "days": {}, "done": []}
    if path.exists() and not refresh:
        state = json.loads(path.read_text(encoding="utf-8"))
        state.setdefault("done", [])
    if state["start"] is None:
        state["start"] = R.iso(sub_start(client, sub))
        state["next"] = state["start"]
    first = R.ordinal(state["start"])
    cover = R.ordinal(state["next"])
    done = {R.ordinal(k) for k in state["done"]}
    todo = [d for d in sample_days(first, end) if d >= cover and d not in done]
    for attempt in range(6):
        failed = []
        for n, d in enumerate(todo, 1):
            try:
                rows = get(client, f"{ARCTIC}/posts/search/aggregate",
                           params={"subreddit": sub, "aggregate": "created_utc", "frequency": "day",
                                   "after": R.iso(d), "before": R.iso(d + 1)}, tries=1)
            except SourceError:   # a timeout (Slow) or a dropped connection: this day is asked again in the next pass
                failed.append(d)
                time.sleep(1)
                continue
            state["days"][R.iso(d)] = sum(int(r["count"]) for r in rows.get("data") or [])
            state["done"].append(R.iso(d))
            if n % 25 == 0:
                atomic_write(path, json.dumps(state))
                print(f"  {sub}: {n} of {len(todo)} days this pass, at {R.iso(d)}", flush=True)
            time.sleep(PAUSE)
        atomic_write(path, json.dumps(state))
        if not failed:
            break
        todo = failed
        print(f"  {sub}: {len(failed)} days timed out, pass {attempt + 1} of 6", flush=True)
        time.sleep(20 * (attempt + 1))
    state["unread"] = [R.iso(d) for d in todo] if failed else []
    atomic_write(path, json.dumps(state))
    if state["unread"]:
        raise SourceError(f"{sub}: {len(state['unread'])} sampled days never answered")
    return state


# ---- the weekly table ------------------------------------------------------------------------

WIKI_TITLES = {"wiki_bitcoin": "Bitcoin", "wiki_cryptocurrency": "Cryptocurrency", "wiki_ethereum": "Ethereum",
               "wiki_dogecoin": "Dogecoin"}
SUBS = {"rd_cc": "CryptoCurrency", "rd_btc": "Bitcoin", "rd_eth": "ethtrader",
        "rd_cms": "CryptoMoonShots", "rd_ssb": "SatoshiStreetBets", "rd_alt": "altcoin"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true", help="read Wikimedia again; with --only, empty that subreddit's cache")
    ap.add_argument("--only", help="read this one subreddit only (a name from SUBS)")
    args = ap.parse_args(argv)

    today = datetime.now(timezone.utc).date().toordinal()
    last_monday = R.monday_on_or_before(today)
    weeks = R.week_grid(FIRST_WEEK, last_monday)
    client = build_source_client(timeout=90.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    daily: dict[str, dict] = {}
    covered: dict[str, tuple] = {}
    errors: dict[str, str] = {}
    try:
        for col, title in WIKI_TITLES.items():
            if args.only and args.only != "wiki":
                break
            path = CACHE / f"{col}.json"
            try:
                if path.exists() and not args.refresh:
                    items = json.loads(path.read_text(encoding="utf-8"))
                else:
                    items = read_wiki(client, title, last_monday - 1)
                    atomic_write(path, json.dumps(items))
                daily[col] = R.parse_wikimedia(items)
                print("read", col, len(daily[col]), "days", flush=True)
            except SourceError as exc:
                errors[col] = str(exc)[:160]
                print("NOT READ", col, errors[col], flush=True)
        for col, sub in SUBS.items():
            if args.only and args.only not in (sub, col):
                continue   # `--only wiki` matches no subreddit: Wikimedia alone
            try:
                state = read_reddit(client, sub, last_monday, refresh=bool(args.only and args.refresh))
            except SourceError as exc:
                errors[col] = str(exc)[:160]
                print("NOT READ", col, errors[col], flush=True)
                state = json.loads((CACHE / "reddit" / f"{sub}.json").read_text(encoding="utf-8")) if (CACHE / "reddit" / f"{sub}.json").exists() else None
                if state is None:
                    continue
            first, cover = R.ordinal(state["start"]), R.ordinal(state["next"])
            done = {R.ordinal(k) for k in state.get("done", [])}
            days = {R.ordinal(k): v for k, v in state["days"].items()}
            daily[col] = {d: days.get(d, 0) for d in sample_days(first, last_monday) if d < cover or d in done}
            covered[col] = {"start": state["start"], "sampled_days_read": len(daily[col]),
                            "sampled_days_unread": len(sample_days(first, last_monday)) - len(daily[col])}
    finally:
        CURRENT_TIER.reset(token)
        client.close()

    cols = list(WIKI_TITLES) + list(SUBS)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["week"] + cols)
    need = {c: (2 if c in SUBS else 6) for c in cols}   # a Reddit week needs both its sampled days, Wikipedia six of seven
    for W in weeks:
        w.writerow([R.iso(W)] + ["" if daily.get(c) is None or R.week_sum(daily[c], W, need[c]) is None
                                 else f"{R.week_sum(daily[c], W, need[c]):.8g}" for c in cols])
    atomic_write(DATA / "social_weekly.csv", out.getvalue())
    log = {"as_of": R.iso(today), "last_week": R.iso(last_monday), "not_read": errors, "reddit_covered": covered,
           "note": "Reddit is sampled on the Tuesday and the Friday of each week (RESULT.md, amendment 1), times 3.5; its days are "
                   "Prague days (the archive buckets in local time): up to 2 h off a UTC day."}
    atomic_write(DATA / "social_sources.json", json.dumps(log, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(weeks)} weeks to {DATA / 'social_weekly.csv'}; not read: {sorted(errors) or 'nothing'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
