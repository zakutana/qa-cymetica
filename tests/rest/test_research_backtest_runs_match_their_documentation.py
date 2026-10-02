"""The Backtest Rally runs say what their documentation says (2026-10-03).

THE CONTRACT. `GET /api/v1/research-backtest/runs/{run_id}` is documented in
/openapi-public.json as "Full stored run document (index fields + per-basket
detail)", with the properties run_id, label, created_at, algo_model, themes,
n_baskets, hold_days, mean_basket_gain_pct, mean_vs_btc_pct, hit_rate_pct and
baskets. And a run is listed by `GET /api/v1/research-backtest/runs` with the
themes it was run on.

WHAT WAS SEEN (2026-10-03, the laboratory's bug hunt on /backtest-rally). The
stored run answers run_id, label, created_at, `parameters`, `summary` and `rows`.
`baskets`, `algo_model`, `themes`, `n_baskets`, `hold_days` and the three index
figures are not at the top level (the figures sit under `summary`, the rest under
`parameters`), so a client written from the schema reads nothing. The schema
requires only run_id and allows extra properties, so it still "validates".
Second: a run whose `parameters.theme` is "defi tokens" is listed with
`themes: []` (run best-params-macd-gated-20260624T200425), so
`?theme=defi%20tokens` does not find it.

WHAT IT ASSERTS. (1) Every property the schema lists for a stored run is present
at the top level of the newest stored run. (2) A run whose parameters name a
theme (anything but "all") is listed with a non-empty `themes`.

NOT asserted: which side changes -- the schema may be brought to the answer or
the answer to the schema -- or what the headline figures should mean (before or
after costs).

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

RUNS = "/api/v1/research-backtest/runs"
SCHEMA_PATH = "/api/v1/research-backtest/runs/{run_id}"
OPENAPI = "/openapi-public.json"
MAX_RUNS = 10


def _json(response, what: str):
    if response.status_code != 200:
        raise Inconclusive(f"{what} answered HTTP {response.status_code}; a failed read is not an empty one")
    try:
        return response.json()
    except ValueError:
        raise Inconclusive(f"{what} answered 200 with a body that is not JSON")


def _get(client, url):
    try:
        return client.get(url)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{url} could not be read: {type(exc).__name__}")


def documented_properties(openapi: dict) -> list[str]:
    """The properties the schema lists for a stored run, in the order it lists them."""
    get = (((openapi.get("paths") or {}).get(SCHEMA_PATH) or {}).get("get") or {})
    schema = ((((get.get("responses") or {}).get("200") or {}).get("content") or {})
              .get("application/json") or {}).get("schema") or {}
    return list((schema.get("properties") or {}).keys())


@qa(component="rest.research_backtest", tier=SafetyTier.SAFE, surface="rest")
def test_a_stored_run_carries_the_fields_its_schema_lists(rest_anon):
    """Every property /openapi-public.json lists for GET /runs/{run_id} is at the top
    level of the newest stored run."""
    listed = documented_properties(_json(_get(rest_anon, OPENAPI), OPENAPI))
    if not listed:
        raise Inconclusive(f"{OPENAPI} lists no properties for GET {SCHEMA_PATH}: nothing to hold the answer to")
    runs = (_json(_get(rest_anon, RUNS), RUNS) or {}).get("runs")
    if not isinstance(runs, list) or not runs or not runs[0].get("run_id"):
        raise Inconclusive(f"{RUNS} lists no stored run to read")
    run_id = runs[0]["run_id"]
    run = _json(_get(rest_anon, f"{RUNS}/{run_id}"), f"{RUNS}/{run_id}")
    if not isinstance(run, dict):
        raise Inconclusive(f"{RUNS}/{run_id} answered something that is not an object")
    missing = [name for name in listed if name not in run]
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{RUNS}/{{run_id}} for {run_id} lacks {len(missing)} of the {len(listed)} properties its "
                f"schema lists: {', '.join(missing)}; it answers {', '.join(sorted(run))}"
                if missing else
                f"all {len(listed)} documented properties are present on {run_id}"),
        left={"documented_but_absent": missing},
        right={"documented_but_absent": []},
        population={"documented": listed, "answered": sorted(run), "run_id": run_id},
        sources={"schema": OPENAPI, "run": f"{RUNS}/{run_id}"}))


@qa(component="rest.research_backtest", tier=SafetyTier.SAFE, surface="rest")
def test_a_run_on_a_theme_is_listed_with_that_theme(rest_anon):
    """A stored run whose parameters name a theme appears in the list under it."""
    runs = (_json(_get(rest_anon, RUNS), RUNS) or {}).get("runs")
    if not isinstance(runs, list) or not runs:
        raise Inconclusive(f"{RUNS} lists no stored run to read")
    judged, unlisted = [], []
    for row in runs[:MAX_RUNS]:
        run_id = row.get("run_id")
        if not run_id:
            continue
        run = _json(_get(rest_anon, f"{RUNS}/{run_id}"), f"{RUNS}/{run_id}")
        theme = str(((run.get("parameters") or {}).get("theme")) or "").strip().lower()
        if theme in ("", "all"):
            continue
        judged.append({"run_id": run_id, "theme": theme, "listed_themes": row.get("themes")})
        if not row.get("themes"):
            unlisted.append(judged[-1])
    if not judged:
        raise Inconclusive(f"none of the {len(runs)} stored run(s) is on a named theme, so none can be judged")
    conclude(Measurement(
        verdict="failed" if unlisted else "passed",
        reason=(f"{len(unlisted)} of {len(judged)} runs on a named theme are listed with no theme: "
                + "; ".join(f"{u['run_id']} (parameters.theme {u['theme']!r}, listed themes {u['listed_themes']!r})"
                            for u in unlisted[:3])
                if unlisted else
                f"all {len(judged)} runs on a named theme are listed under it"),
        left={"runs_listed_without_their_theme": len(unlisted)},
        right={"runs_listed_without_their_theme": 0},
        population={"judged": judged},
        sources={"list": RUNS}))
