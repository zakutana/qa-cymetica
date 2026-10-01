"""Chart Analyzer's score is the average of the patterns it says it counted.

THE CONTRACT. Every answer of `GET /api/v1/chart-analyzer/analyze` carries its
own rule (read 2026-10-01): "The score is the average success rate of the
patterns confirmed in the last 10 candles, placed on a scale where the most
bearish pattern is 1, the base rate ... is 50 and the most bullish pattern is
100." The same answer lists every pattern it found with its `success_rate`
and `counted_in_score`, and states the average it placed on that scale as
`chart_rate` (its `scale` maps the rates of 1, 50 and 100).

WHAT WAS SEEN (2026-10-01, the laboratory's bug hunt): AAVE on avalanche, 1d.
Three patterns marked `counted_in_score: true` -- "20-bar breakout on volume"
(0.4836) and "Bearish engulfing after a rise" (0.4694) at 4 and at 8 bars ago.
`chart_rate` 0.4765 is the average of the two pattern TYPES; the average of
the three counted patterns is 0.4741, which is 56 on their scale against the
57 served. The Gem Screener batch lists the same three as `counted_patterns`.

WHAT IT ASSERTS. For each sampled coin, `chart_rate` equals the average
`success_rate` of the patterns the same answer marks `counted_in_score`, to
the four decimals both are published at. It does not decide which side is
right: counting a repeated pattern once (and marking it counted once) passes,
and so does counting every confirmation -- the defect is that the answer says
one and computes the other.

THE SAMPLE. One read of the Gem Screener batch (1d): its scored rows whose
`counted_patterns` name a pattern twice -- where the two readings differ --
first, then the other scored rows, until SAMPLE coins have a readable answer.
Fewer than MIN_JUDGED is inconclusive: a failed read is not an agreeing one.

SAFE: GETs only, no key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

BATCH = "/api/v1/chart-analyzer/batch/gem-screener"
ANALYZE = "/api/v1/chart-analyzer/analyze"
TIMEFRAME = "1d"
SAMPLE = 6
MIN_JUDGED = 3
# Both figures are published to four decimals; an average of four-decimal
# rates, itself rounded to four, can differ from the exact one by 0.00005.
TOLERANCE = 0.0002
CLAIM = "chart-analyzer-score-averages-what-it-counts"


def _json(response, what: str):
    if response.status_code != 200:
        raise Inconclusive(f"{what} answered HTTP {response.status_code}; "
                           f"a failed read is not an empty one")
    try:
        return response.json()
    except ValueError:
        raise Inconclusive(f"{what} answered 200 with a body that is not JSON")


def candidates(items) -> list[dict]:
    """Scored rows with a contract and a chain, those whose counted patterns
    name one pattern twice first, each group in the order served."""
    scored = [row for row in items or () if isinstance(row, dict)
              and row.get("status") == "scored"
              and (row.get("input") or {}).get("contract")
              and (row.get("input") or {}).get("chain")]

    def repeats(row: dict) -> bool:
        names = [str(name) for name in row.get("counted_patterns") or ()]
        return len(names) != len(set(names))
    return ([row for row in scored if repeats(row)]
            + [row for row in scored if not repeats(row)])


def averaged(body: dict):
    """(chart_rate, the average success_rate of the patterns marked counted,
    the counted patterns), or None when the answer cannot be read that way --
    no chart_rate, no pattern marked counted, or a counted one with no rate."""
    rate = body.get("chart_rate") if isinstance(body, dict) else None
    patterns = body.get("patterns") if isinstance(body, dict) else None
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) \
            or not isinstance(patterns, list):
        return None
    counted = [p for p in patterns
               if isinstance(p, dict) and p.get("counted_in_score") is True]
    rates = [p.get("success_rate") for p in counted]
    if not counted or not all(isinstance(r, (int, float)) and not isinstance(r, bool)
                              for r in rates):
        return None
    return float(rate), sum(rates) / len(rates), counted


@qa(component="rest.chart_analyzer", tier=SafetyTier.SAFE, surface="rest",
    claim=CLAIM)
def test_a_score_averages_the_patterns_its_answer_marks_counted(rest_anon):
    """Each sampled answer's chart_rate is the average of what it marks counted."""
    batch = _json(rest_anon.get(BATCH, params={"timeframe": TIMEFRAME},
                                timeout=60.0), BATCH)
    rows = candidates((batch or {}).get("items") if isinstance(batch, dict) else None)
    if not rows:
        raise Inconclusive(f"{BATCH} listed no scored coin with a contract and "
                           f"a chain, so nothing could be sampled")

    judged, disagree, unread = [], [], []
    for row in rows:
        if len(judged) >= SAMPLE:
            break
        coin = row["input"]
        params = {"contract": coin["contract"], "chain": coin["chain"],
                  "timeframe": TIMEFRAME}
        response = rest_anon.get(ANALYZE, params=params, timeout=60.0)
        label = f"{row.get('symbol') or coin['contract'][:10]} on {coin['chain']}"
        if response.status_code != 200:
            unread.append(f"{label}: HTTP {response.status_code}")
            continue
        try:
            read = averaged(response.json())
        except ValueError:
            unread.append(f"{label}: not JSON")
            continue
        if read is None:
            unread.append(f"{label}: no chart_rate or no rated pattern marked counted")
            continue
        served, average, counted = read
        entry = {"coin": label, "contract": coin["contract"], "chain": coin["chain"],
                 "chart_rate": served, "average_of_counted": round(average, 4),
                 "counted": [(p.get("key"), p.get("bars_ago"), p.get("success_rate"))
                             for p in counted]}
        judged.append(entry)
        if abs(served - average) > TOLERANCE:
            disagree.append(entry)

    if len(judged) < MIN_JUDGED:
        raise Inconclusive(f"{len(judged)} coin(s) gave a readable answer; "
                           f"{MIN_JUDGED} are needed. Unread: {unread[:6]}")
    said = lambda rows_: "; ".join(
        f"{e['coin']}: chart_rate {e['chart_rate']} against {e['average_of_counted']} "
        f"over the {len(e['counted'])} patterns marked counted_in_score "
        f"({', '.join(f'{k} {b} bars ago' for k, b, _ in e['counted'])})"
        for e in rows_)
    if disagree:
        verdict = "failed"
        reason = (f"{len(disagree)} of {len(judged)} sampled answers state a "
                  f"chart_rate that is not the average success_rate of the "
                  f"patterns the same answer marks counted_in_score, while its "
                  f"rule says the score averages the patterns confirmed in the "
                  f"last 10 candles: {said(disagree)}")
    else:
        verdict = "passed"
        reason = (f"each of {len(judged)} sampled answers states a chart_rate "
                  f"equal to the average of the patterns it marks counted_in_score")
    conclude(Measurement(
        verdict=verdict, reason=reason[:1800],
        left={"judged": len(judged), "disagree": len(disagree)},
        right={"disagree": 0},
        population={"judged": judged, "unread": unread,
                    "batch_scored": len(rows)},
        sources={"batch": f"{BATCH}?timeframe={TIMEFRAME}",
                 "answer": f"{ANALYZE}?contract=&chain=&timeframe={TIMEFRAME}",
                 "rule": "the `rule` field of every analyze answer"},
        claim_id=CLAIM))
