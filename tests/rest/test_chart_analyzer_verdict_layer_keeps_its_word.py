"""Chart Analyzer's verdict layer says what it does (ET-29001, verified 2026-10-04).

Build it Better ET-29001 ("top expert", 13 points) shipped on 2026-10-04 07:25 UTC: a
READY TO POP / READY TO DUMP / NO EDGE verdict with a calibrated probability, its 95%
range, the base rate and the number of past cases; structures drawn by rule; a public
ledger of the page's own calls; and the new fields documented. Verified line by line the
same morning (outbox/chart-analyzer-verification.md). Four places where the platform
does not do what its own documents say, one check each:

1. THE SCHEMA. Cymetica's answer: "verdict, structures[], setups[], indicators,
   weekly_signal on GET /api/v1/chart-analyzer/analyze, plus /study/expert and /calls,
   in /openapi-public.json". Seen: the 200 schema of /analyze lists none of them and says
   `additionalProperties: false`; /calls and /study/expert answer with a schema of `{}`.
   ASSERTS: every top-level key of a live answer is listed in that endpoint's 200 schema,
   with a type the schema allows. `additionalProperties: true` alone does not pass: the
   request asked for the fields to be documented, not tolerated.

2. THE LEDGER. /calls: "recorded when made (closed candles only)"; its own `rule`: "once
   per chart, timeframe and closed candle". Seen: `sym:BTC/USDT|1h|1792972800`, made
   2026-10-04 06:21:46 UTC on a candle that opens 2026-10-26 00:00 UTC, at a close of
   229.263278. ASSERTS: every open or scored call's candle closed (candle_time plus one
   bar; 1M to the 1st of the next month) at or before `made_at`. A call they mark with
   any other status (void, withdrawn) is not judged: that is a fix. Reads /calls only, so
   the check itself never adds a call.

3. THE RANGE. llms.txt: `range` is "the 95% range of that probability". Seen: in 26 usable
   calibration bins of /study/expert the calibrated probability lies outside its own
   `ci95` (5d up bin 9: 43.07%, range 59.54-68.12%), and the page prints them side by
   side under "The numbers" (SOL 5d: "43.1% calibrated ... range 49% to 56%").
   ASSERTS: in every usable bin, and on the `up`/`down` sides of sampled 5d answers, the
   probability is inside the range given with it (to the 4 decimals both are published
   at). Either fix passes: a range computed for the pooled value, or no pooling. 5d is
   sampled because it never carries a label (its held-out record failed), so reading it
   writes nothing to their ledger.

4. DEX-POOL COINS. llms.txt, Chart Analyzer section: "a DEX-pool coin gets the drawings
   and setups but no verdict (`coverage_note`)". Seen: Gem Screener coins read from their
   DEX pool get READY TO POP / READY TO DUMP on 1h (SKY, XVS), and the ledger records them
   as `contract:` calls. ASSERTS: while llms.txt still says so, a DEX-pool answer
   (`verdict.coverage` asset_not_covered) whose own up/down figures qualify for a label
   under the published rule (5 points over the base rate, range above it, 300+ cases --
   computed here, never read from `rule_label`) carries NO EDGE. If the sentence is gone,
   INCONCLUSIVE: a withdrawn promise is theirs to announce, not ours to bank. No
   qualifying answer in the sample is INCONCLUSIVE, not a pass.
   SIDE EFFECT, stated: GET /analyze records every POP/DUMP it serves into the public
   ledger. This check stops at the first qualifying answer and reads at most
   MAX_DEX_READS coins, so one run adds at most one call.

NOT asserted: whether the labels are right, whether the study's numbers are true (they
cannot be recomputed without their candles; the published counts do follow from their
own tables), or anything about the page's layout.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_research_backtest_runs_match_their_documentation import (
    _declared_types, _is_json_type, _json_type_of)

ANALYZE = "/api/v1/chart-analyzer/analyze"
CALLS = "/api/v1/chart-analyzer/calls"
EXPERT = "/api/v1/chart-analyzer/study/expert"
BATCH = "/api/v1/chart-analyzer/batch/gem-screener"
OPENAPI = "/openapi-public.json"
LLMS = "/llms.txt"

CLAIM_SCHEMA = "chart-analyzer-verdict-fields-are-in-its-openapi-schema"
CLAIM_LEDGER = "chart-analyzer-calls-are-on-closed-candles"
CLAIM_RANGE = "chart-analyzer-probability-lies-inside-its-range"
CLAIM_DEX = "chart-analyzer-dex-pool-coin-gets-no-verdict-as-documented"

TF_SECONDS = {"1h": 3600, "4h": 14400, "1d": 86400, "5d": 5 * 86400,
              "1w": 7 * 86400, "2w": 14 * 86400}
JUDGED_STATUSES = frozenset({"open", "scored"})
# Published at four decimals: a probability on the edge of its range may round 0.00005
# either way.
EDGE = 0.0001
# The verdict rule, as /study/expert `verdict_rule` and every answer's `verdict.rule`
# state it (read 2026-10-04): gap 0.05, min_cases 300, the 95% range above the base rate.
GAP, MIN_CASES = 0.05, 300
RANGE_SYMBOLS = ("SOL", "BTC", "ETH")
MAX_DEX_READS = 14
MAX_DEX_READABLE = 8


def _get(client, url, **params):
    try:
        return client.get(url, params=params or None, timeout=90.0)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{url} could not be read: {type(exc).__name__}")


def _json(response, what: str):
    if response.status_code != 200:
        raise Inconclusive(f"{what} answered HTTP {response.status_code}; a failed read is not an empty one")
    try:
        return response.json()
    except ValueError:
        raise Inconclusive(f"{what} answered 200 with a body that is not JSON")


# --- 1. the schema ---------------------------------------------------------------------

def _resolve(node, openapi: dict, depth: int = 0):
    if not isinstance(node, dict) or depth > 6:
        return node if isinstance(node, dict) else {}
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        target = openapi
        for part in ref[2:].split("/"):
            target = target.get(part) if isinstance(target, dict) else None
        return _resolve(target, openapi, depth + 1)
    return node


def schema_properties(schema, openapi: dict, depth: int = 0) -> dict:
    """Every property a response schema lists, through `$ref` and `allOf`."""
    node = _resolve(schema, openapi)
    props = dict(node.get("properties") or {}) if isinstance(node, dict) else {}
    for part in (node.get("allOf") or []) if isinstance(node, dict) and depth < 6 else []:
        props.update(schema_properties(part, openapi, depth + 1))
    return props


def response_schema(openapi: dict, path: str) -> dict:
    get = (((openapi.get("paths") or {}).get(path) or {}).get("get") or {})
    return ((((get.get("responses") or {}).get("200") or {}).get("content") or {})
            .get("application/json") or {}).get("schema") or {}


def undocumented(answer: dict, schema, openapi: dict) -> tuple[list[dict], list[dict]]:
    """(keys of a live answer its 200 schema does not list, keys it lists with a type
    the live value does not have). `additionalProperties` is not read: tolerated is
    not documented."""
    props = schema_properties(schema, openapi)
    missing, mistyped = [], []
    for key in sorted(answer):
        if key not in props:
            missing.append({"key": key, "answered": _json_type_of(answer[key])})
            continue
        types = _declared_types(_resolve(props[key], openapi), openapi)
        if types is not None and not any(_is_json_type(answer[key], t) for t in types):
            mistyped.append({"key": key, "answered": _json_type_of(answer[key]),
                             "schema_allows": sorted(types)})
    return missing, mistyped


@qa(component="rest.chart_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_SCHEMA)
def test_the_verdict_fields_are_listed_in_the_openapi_schema(rest_anon):
    """Every top-level key of a live /analyze, /calls and /study/expert answer is listed
    in that endpoint's 200 schema in /openapi-public.json, with a type it allows."""
    openapi = _json(_get(rest_anon, OPENAPI), OPENAPI)
    if not isinstance(openapi, dict) or not isinstance(openapi.get("paths"), dict):
        raise Inconclusive(f"{OPENAPI} has no paths to read")
    # 1M never carries a label ("The study does not cover 1M candles"), so this read
    # adds nothing to their ledger.
    reads = {
        ANALYZE: _json(_get(rest_anon, ANALYZE, symbol="BTC", timeframe="1M",
                            closed_only="true"), f"{ANALYZE}?symbol=BTC&timeframe=1M"),
        CALLS: _json(_get(rest_anon, CALLS, limit=5), CALLS),
        EXPERT: _json(_get(rest_anon, EXPERT, timeframe="1d"), f"{EXPERT}?timeframe=1d"),
    }
    per_path, problems = {}, []
    for path, answer in reads.items():
        if not isinstance(answer, dict):
            raise Inconclusive(f"{path} answered something that is not an object")
        if path not in openapi["paths"]:
            raise Inconclusive(f"{OPENAPI} does not list {path} at all")
        missing, mistyped = undocumented(answer, response_schema(openapi, path), openapi)
        schema = response_schema(openapi, path)
        per_path[path] = {"answered": sorted(answer), "missing": [m["key"] for m in missing],
                          "mistyped": mistyped,
                          "schema_listed": sorted(schema_properties(schema, openapi)),
                          "additionalProperties": _resolve(schema, openapi).get("additionalProperties")}
        if missing:
            problems.append(f"GET {path} answers {len(missing)} top-level key(s) its 200 schema does "
                            f"not list: {', '.join(m['key'] for m in missing)}"
                            + (f" (the schema lists {len(per_path[path]['schema_listed'])} and says "
                               f"additionalProperties: false)"
                               if per_path[path]["additionalProperties"] is False else
                               " (the schema is empty)" if not per_path[path]["schema_listed"] else ""))
        if mistyped:
            problems.append(f"GET {path} answers {', '.join(m['key'] + ' as ' + m['answered'] for m in mistyped)}"
                            f", which its schema types otherwise")
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                "every top-level key of /analyze, /calls and /study/expert is listed in its 200 schema"),
        left={path: v["missing"] + [m["key"] for m in v["mistyped"]] for path, v in per_path.items()},
        right={path: [] for path in per_path},
        population=per_path,
        sources={"schema": OPENAPI, "analyze": f"{ANALYZE}?symbol=BTC&timeframe=1M&closed_only=true",
                 "calls": f"{CALLS}?limit=5", "expert": f"{EXPERT}?timeframe=1d"},
        claim_id=CLAIM_SCHEMA))


# --- 2. the ledger ---------------------------------------------------------------------

def closes_at(candle_time, timeframe):
    """When the candle that opens at `candle_time` closes, or None for a timeframe this
    check does not know. 1M closes on the 1st of the next month (UTC)."""
    if not isinstance(candle_time, (int, float)) or isinstance(candle_time, bool):
        return None
    if timeframe in TF_SECONDS:
        return int(candle_time) + TF_SECONDS[timeframe]
    if timeframe == "1M":
        opened = datetime.fromtimestamp(int(candle_time), timezone.utc)
        year, month = (opened.year + 1, 1) if opened.month == 12 else (opened.year, opened.month + 1)
        return calendar.timegm((year, month, 1, 0, 0, 0))
    return None


def _epoch(stamp):
    if not isinstance(stamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return int(parsed.timestamp())


def not_on_a_closed_candle(calls) -> tuple[list[dict], list[dict], list[dict]]:
    """(judged, made before their candle closed, unreadable) over the open and scored
    calls. Any other status is theirs (void, withdrawn) and is not judged."""
    judged, bad, unread = [], [], []
    for call in calls or ():
        if not isinstance(call, dict) or call.get("status") not in JUDGED_STATUSES:
            continue
        made, closed = _epoch(call.get("made_at")), closes_at(call.get("candle_time"), call.get("timeframe"))
        row = {k: call.get(k) for k in ("id", "who", "timeframe", "made_at", "candle_time", "close",
                                        "verdict", "probability", "status")}
        if made is None or closed is None:
            unread.append(row)
            continue
        row["candle_closes_at"] = datetime.fromtimestamp(closed, timezone.utc).isoformat()
        row["made_before_close_s"] = closed - made
        judged.append(row)
        if closed > made:
            bad.append(row)
    return judged, bad, unread


@qa(component="rest.chart_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_LEDGER)
def test_every_recorded_call_is_on_a_closed_candle(rest_anon):
    """Every open or scored call in /calls was made after the candle it names closed."""
    ledger = _json(_get(rest_anon, CALLS, limit=1000), CALLS)
    calls = ledger.get("calls") if isinstance(ledger, dict) else None
    if not isinstance(calls, list):
        raise Inconclusive(f"{CALLS} carries no `calls` list")
    judged, bad, unread = not_on_a_closed_candle(calls)
    if not judged:
        raise Inconclusive(f"{CALLS} lists {len(calls)} call(s), none open or scored with a readable "
                           f"made_at, candle_time and timeframe")
    context = {}
    for row in bad[:2]:
        who = str(row.get("who") or "")
        if not who.startswith("sym:"):
            continue
        base = who[4:].split("/")[0]
        # The pair's own monthly candles: 1M never carries a label, so nothing is recorded.
        response = _get(rest_anon, ANALYZE, symbol=base, timeframe="1M", include_candles="true",
                        closed_only="true")
        if response.status_code != 200:
            continue
        try:
            served = response.json() or {}
        except ValueError:
            continue
        candles = [c for c in (served.get("candles") or []) if isinstance(c, list) and len(c) >= 5]
        if candles:
            context[who] = {"monthly_candles": len(candles),
                            "first": datetime.fromtimestamp(candles[0][0], timezone.utc).date().isoformat(),
                            "lowest_low": min(c[3] for c in candles),
                            "highest_high": max(c[2] for c in candles)}
    said = lambda r: (f"{r['id']} ({r['verdict']}, close {r['close']}) was made {r['made_at']} on a candle "
                      f"that opens {datetime.fromtimestamp(r['candle_time'], timezone.utc).isoformat()} and "
                      f"closes {r['candle_closes_at']}"
                      + (f"; the same API's {r['who'][4:]} monthly candles since "
                         f"{context[r['who']]['first']} range {context[r['who']]['lowest_low']:g} to "
                         f"{context[r['who']]['highest_high']:g}" if r.get("who") in context else ""))
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} of {len(judged)} open or scored calls in the public ledger were recorded "
                f"before the candle they name had closed: " + "; ".join(said(r) for r in bad[:3])
                if bad else
                f"all {len(judged)} open or scored calls were recorded after their candle closed"),
        left={"calls_before_their_candle_closed": len(bad)},
        right={"calls_before_their_candle_closed": 0},
        population={"bad": bad, "unread": unread, "judged": len(judged), "context": context,
                    "summary": ledger.get("summary"), "rule": ledger.get("rule")},
        sources={"ledger": f"{CALLS}?limit=1000",
                 "context": f"{ANALYZE}?symbol=<pair>&timeframe=1M&include_candles=true&closed_only=true"},
        claim_id=CLAIM_LEDGER))


# --- 3. the range ----------------------------------------------------------------------

def _inside(value, rng) -> bool | None:
    if (not isinstance(value, (int, float)) or isinstance(value, bool) or not isinstance(rng, list)
            or len(rng) != 2 or not all(isinstance(x, (int, float)) for x in rng)):
        return None
    return rng[0] - EDGE <= value <= rng[1] + EDGE


def outside_their_range(expert: dict) -> tuple[list[dict], list[dict]]:
    """(judged, outside) over every usable calibration bin of /study/expert: a usable bin
    is one whose calibrated probability the verdict shows."""
    judged, outside = [], []
    for tf, block in ((expert or {}).get("timeframes") or {}).items():
        calibration = (block or {}).get("calibration") if isinstance(block, dict) else None
        # The block also carries base_up, base_down, n and range beside the two tables.
        for side in ("up", "down"):
            rows = calibration.get(side) if isinstance(calibration, dict) else None
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict) or row.get("usable") is not True:
                    continue
                inside = _inside(row.get("calibrated"), row.get("ci95"))
                if inside is None:
                    continue
                entry = {"timeframe": tf, "side": side, "bin": row.get("bin"), "n": row.get("n"),
                         "calibrated": row.get("calibrated"), "ci95": row.get("ci95"),
                         "bin_rate": row.get("rate")}
                judged.append(entry)
                if not inside:
                    outside.append(entry)
    return judged, outside


def _distance(entry) -> float:
    lo, hi = entry["ci95"]
    return max(lo - entry["calibrated"], entry["calibrated"] - hi)


@qa(component="rest.chart_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_RANGE)
def test_a_probability_lies_inside_the_range_shown_with_it(rest_anon):
    """In every usable calibration bin, and on the up/down sides of sampled answers, the
    calibrated probability is inside the 95% range given with it."""
    expert = _json(_get(rest_anon, EXPERT), EXPERT)
    judged, outside = outside_their_range(expert if isinstance(expert, dict) else {})
    if not judged:
        raise Inconclusive(f"{EXPERT} has no usable calibration bin with a probability and a range")
    live, live_outside, unread = [], [], []
    for symbol in RANGE_SYMBOLS:
        response = _get(rest_anon, ANALYZE, symbol=symbol, timeframe="5d", closed_only="true")
        if response.status_code != 200:
            unread.append(f"{symbol}: HTTP {response.status_code}")
            continue
        try:
            verdict = (response.json() or {}).get("verdict") or {}
        except ValueError:
            unread.append(f"{symbol}: not JSON")
            continue
        for side in ("up", "down"):
            said = verdict.get(side) or {}
            inside = _inside(said.get("calibrated"), said.get("range"))
            if inside is None:
                continue
            entry = {"symbol": symbol, "timeframe": "5d", "side": side, "calibrated": said.get("calibrated"),
                     "range": said.get("range"), "cases": said.get("cases"), "bin": said.get("bin"),
                     "label": verdict.get("label")}
            live.append(entry)
            if not inside:
                live_outside.append(entry)
    worst = sorted(outside, key=_distance, reverse=True)[:3]
    usable_by_tf = {}
    for entry in outside:
        usable_by_tf[entry["timeframe"]] = usable_by_tf.get(entry["timeframe"], 0) + 1
    failed = bool(outside or live_outside)
    if not failed and not live:
        # The live answers are half the contract (the user-visible defect was SOL 5d's range):
        # with none of them read -- unreadable, or read with no calibrated/range to judge,
        # which a renamed field would also produce (deep pass 2026-10-08, T06, 3/3) -- a
        # clean study says nothing about them.
        raise Inconclusive(f"no live 5d side could be judged ({'; '.join(unread) or 'answers carry no calibrated/range'}); "
                           f"the study bins alone are not the whole claim")
    conclude(Measurement(
        verdict="failed" if failed else "passed",
        reason=(f"{len(outside)} of {len(judged)} usable calibration bins in /study/expert give a calibrated "
                f"probability outside their own 95% range (by timeframe: "
                f"{', '.join(f'{k} {v}' for k, v in sorted(usable_by_tf.items()))}); widest: "
                + "; ".join(f"{e['timeframe']} {e['side']} bin {e['bin']} ({e['n']} cases): calibrated "
                            f"{e['calibrated']}, ci95 {e['ci95'][0]}-{e['ci95'][1]}" for e in worst)
                + (f". Live 5d answers, {len(live_outside)} of {len(live)} sides: "
                   + "; ".join(f"{e['symbol']} {e['side']} {e['calibrated']} with range "
                               f"{e['range'][0]}-{e['range'][1]}" for e in live_outside[:3])
                   if live_outside else "")
                if failed else
                f"all {len(judged)} usable bins and {len(live)} live sides give a probability inside its range"),
        left={"bins_outside": len(outside), "live_sides_outside": len(live_outside)},
        right={"bins_outside": 0, "live_sides_outside": 0},
        population={"outside": outside, "bins_judged": len(judged), "live": live, "unread": unread},
        sources={"study": EXPERT, "answers": f"{ANALYZE}?symbol=<SOL|BTC|ETH>&timeframe=5d&closed_only=true"},
        claim_id=CLAIM_RANGE))


# --- 4. DEX-pool coins -----------------------------------------------------------------

def dex_promise(llms_text: str) -> str | None:
    """The sentence in llms.txt's `## Chart Analyzer` section that says a DEX-pool coin
    gets no verdict, or None. Anchored on the markdown heading; read from the text."""
    if not isinstance(llms_text, str):
        return None
    match = re.search(r"^## Chart Analyzer\s*$(.*?)(?=^## |\Z)", llms_text, flags=re.M | re.S)
    if not match:
        return None
    section = " ".join(match.group(1).split())
    for sentence in re.split(r"(?<=[.;])\s+", section):
        if re.search(r"DEX[- ]pool coin", sentence, flags=re.I) and re.search(r"\bno verdict\b", sentence, flags=re.I):
            return sentence.strip()
    return None


def label_candidate(verdict: dict) -> str | None:
    """The label the published rule gives on this answer's own up/down figures (5 points
    over the base rate, the 95% range above it, 300+ cases), or None. Both sides
    qualifying is "both". Never read from `rule_label`."""
    found = []
    for side, label in (("up", "READY TO POP"), ("down", "READY TO DUMP")):
        said = (verdict or {}).get(side) or {}
        p, base, rng, cases = said.get("calibrated"), said.get("base_rate"), said.get("range"), said.get("cases")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (p, base, cases)):
            continue
        if not isinstance(rng, list) or len(rng) != 2 or not isinstance(rng[0], (int, float)):
            continue
        if p - base >= GAP - 1e-9 and rng[0] > base and cases >= MIN_CASES:
            found.append(label)
    return None if not found else found[0] if len(found) == 1 else "both"


@qa(component="rest.chart_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_DEX)
def test_a_dex_pool_coin_gets_no_verdict_while_llms_txt_says_so(rest_anon):
    """While llms.txt says a DEX-pool coin gets no verdict, a DEX-pool answer whose own
    figures qualify under the rule carries NO EDGE."""
    llms = _get(rest_anon, LLMS)
    if llms.status_code != 200:
        raise Inconclusive(f"{LLMS} answered HTTP {llms.status_code}")
    promise = dex_promise(llms.text)
    if promise is None:
        raise Inconclusive(f"{LLMS}'s Chart Analyzer section no longer says a DEX-pool coin gets no verdict; "
                           f"whether that withdraws the promise is theirs to say, not ours to bank")
    batch = _json(_get(rest_anon, BATCH, timeframe="1d"), f"{BATCH}?timeframe=1d")
    coins = [row["input"] for row in (batch.get("items") or []) if isinstance(row, dict)
             and row.get("status") == "scored" and isinstance(row.get("input"), dict)
             and row["input"].get("contract") and row["input"].get("chain")]
    if not coins:
        raise Inconclusive(f"{BATCH} lists no scored coin with a contract and a chain")
    readable, unread, found = [], [], None
    for coin in coins[:MAX_DEX_READS]:
        if len(readable) >= MAX_DEX_READABLE or found:
            break
        response = _get(rest_anon, ANALYZE, contract=coin["contract"], chain=coin["chain"],
                        timeframe="1h", closed_only="true")
        if response.status_code != 200:
            unread.append(f"{coin['contract'][:12]} on {coin['chain']}: HTTP {response.status_code}")
            continue
        try:
            body = response.json() or {}
        except ValueError:
            unread.append(f"{coin['contract'][:12]} on {coin['chain']}: not JSON")
            continue
        verdict = body.get("verdict") or {}
        if verdict.get("coverage") != "asset_not_covered":
            unread.append(f"{coin['contract'][:12]}: coverage {verdict.get('coverage')!r}, not a DEX-pool answer")
            continue
        entry = {"symbol": body.get("symbol"), "contract": coin["contract"], "chain": coin["chain"],
                 "timeframe": body.get("timeframe"), "as_of": body.get("as_of"),
                 "last_candle": body.get("last_candle"), "label": verdict.get("label"),
                 "label_present": "label" in verdict,
                 "rule_label": verdict.get("rule_label"), "probability": verdict.get("probability"),
                 "base_rate": verdict.get("base_rate"), "cases": verdict.get("cases"),
                 "coverage_note": verdict.get("coverage_note"), "source": body.get("source"),
                 "candidate": label_candidate(verdict)}
        readable.append(entry)
        if entry["candidate"]:
            found = entry
    ledger = _get(rest_anon, CALLS, limit=1000)
    recorded = []
    if ledger.status_code == 200:
        recorded = [{k: c.get(k) for k in ("who", "timeframe", "made_at", "verdict", "probability")}
                    for c in (ledger.json() or {}).get("calls") or []
                    if isinstance(c, dict) and str(c.get("who") or "").startswith("contract:")]
    if found is None:
        raise Inconclusive(f"none of {len(readable)} DEX-pool answers on 1h had figures that qualify for a "
                           f"label, so whether one would be labelled was not observed (unread: {unread[:4]})")
    if found["label"] is None and not found["label_present"]:
        raise Inconclusive("the DEX-pool answer carries no `label` field at all: a renamed field is not "
                           "the absence of a verdict")
    # The promise is "no verdict": NO EDGE, or an explicit null, holds it; any other label breaks it.
    labelled = found["label"] not in (None, "NO EDGE")
    conclude(Measurement(
        verdict="failed" if labelled else "passed",
        reason=(f"{found['symbol']} ({found['contract']} on {found['chain']}), read from its DEX pool on "
                f"{found['timeframe']}: verdict {found['label']} at {found['probability']} against a base rate of "
                f"{found['base_rate']} on {found['cases']} cases, with coverage_note \"{found['coverage_note']}\"; "
                f"llms.txt says: \"{promise}\". The public ledger holds {len(recorded)} call(s) on DEX-pool "
                f"coins (`contract:` rows)"
                if labelled else
                f"{found['symbol']} on {found['chain']}: its figures qualify for {found['candidate']} and the "
                f"answer gives {found['label'] or 'no verdict'}, as llms.txt says"),
        left={"dex_answer_labelled": found["label"]},
        right={"dex_answer_labelled": "NO EDGE"},
        population={"judged": found, "readable": readable, "unread": unread, "promise": promise,
                    "ledger_contract_calls": recorded},
        sources={"promise": f"{LLMS} (## Chart Analyzer)", "coins": f"{BATCH}?timeframe=1d",
                 "answer": f"{ANALYZE}?contract=&chain=&timeframe=1h&closed_only=true",
                 "ledger": f"{CALLS}?limit=1000"},
        claim_id=CLAIM_DEX))
