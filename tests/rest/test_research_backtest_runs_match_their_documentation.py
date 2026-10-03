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
at the top level of the newest stored run, and its value is of a type the schema
allows for that property. A key that answers null is "present" and still reads
nothing, so null fails unless the schema says that property may be null
(`"type": ["number", "null"]`, `nullable`, or a `null` alternative of `anyOf`).
A property whose schema declares no type this check can read (no `type`, a
`$ref` it cannot follow, an alternative with none) is held to presence only.
(2) A run whose parameters name a theme (anything but "all") is listed under
THAT theme: its own `parameters.theme`, lower-cased and trimmed, is among the
listed `themes`, lower-cased and trimmed. A listing with some other theme, or
with the right theme missing, fails; so does an empty or null `themes`.

NOT asserted: which side changes -- the schema may be brought to the answer or
the answer to the schema -- or what the headline figures should mean (before or
after costs). Nor the type of the items inside `baskets` or `themes`, nor
`required`, nor that `GET /runs?theme=<theme>` finds the run (the filter is not
queried; the listed `themes` it would read are what is judged). A run, a listed
row, `parameters` or `parameters.theme` that is not the shape it should be makes
the check inconclusive, not failed.

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


_SCALAR = {"string": str, "boolean": bool, "array": list, "object": dict, "null": type(None)}
_KNOWN_TYPES = frozenset(_SCALAR) | {"integer", "number"}


def _declared_types(prop, openapi: dict, depth: int = 0) -> frozenset[str] | None:
    """The JSON types one property's schema allows, or None when it declares none this
    check can read. None is conservative: a missing `type`, a `$ref` it cannot follow,
    a type name it does not know, or ONE unreadable `anyOf`/`oneOf` alternative (which
    could be anything) makes nothing asserted about the value. `nullable: true` and a
    `null` type or alternative each allow null."""
    if not isinstance(prop, dict) or depth > 5:
        return None
    types: set[str] = set()
    declared = prop.get("type")
    if isinstance(declared, str):
        types.add(declared)
    elif isinstance(declared, list):
        types.update(t for t in declared if isinstance(t, str))
    ref = prop.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        node = openapi
        for part in ref[2:].split("/"):
            node = node.get(part) if isinstance(node, dict) else None
        followed = _declared_types(node, openapi, depth + 1)
        if followed is None:
            return None
        types |= followed
    for key in ("anyOf", "oneOf"):
        for alternative in prop.get(key) or []:
            alt = _declared_types(alternative, openapi, depth + 1)
            if alt is None:
                return None
            types |= alt
    if not types or not types <= _KNOWN_TYPES:
        return None
    if prop.get("nullable") is True:
        types.add("null")
    return frozenset(types)


def documented_properties(openapi: dict) -> dict[str, frozenset[str] | None]:
    """The properties the schema lists for a stored run, in the order it lists them,
    each with the JSON types the schema allows for it (None: no type this check can
    read, so only its presence is held to the schema)."""
    get = (((openapi.get("paths") or {}).get(SCHEMA_PATH) or {}).get("get") or {})
    schema = ((((get.get("responses") or {}).get("200") or {}).get("content") or {})
              .get("application/json") or {}).get("schema") or {}
    return {name: _declared_types(prop, openapi)
            for name, prop in (schema.get("properties") or {}).items()}


def _is_json_type(value, name: str) -> bool:
    if name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _SCALAR[name])


def _json_type_of(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return {str: "string", list: "array", dict: "object"}.get(type(value), type(value).__name__)


@qa(component="rest.research_backtest", tier=SafetyTier.SAFE, surface="rest")
def test_a_stored_run_carries_the_fields_its_schema_lists(rest_anon):
    """Every property /openapi-public.json lists for GET /runs/{run_id} is at the top
    level of the newest stored run, with a value of a type the schema allows (null
    only where the schema allows null)."""
    documented = documented_properties(_json(_get(rest_anon, OPENAPI), OPENAPI))
    if not documented:
        raise Inconclusive(f"{OPENAPI} lists no properties for GET {SCHEMA_PATH}: nothing to hold the answer to")
    listed = list(documented)
    runs = (_json(_get(rest_anon, RUNS), RUNS) or {}).get("runs")
    if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict) or not runs[0].get("run_id"):
        raise Inconclusive(f"{RUNS} lists no stored run to read")
    run_id = runs[0]["run_id"]
    run = _json(_get(rest_anon, f"{RUNS}/{run_id}"), f"{RUNS}/{run_id}")
    if not isinstance(run, dict):
        raise Inconclusive(f"{RUNS}/{run_id} answered something that is not an object")
    missing = [name for name in listed if name not in run]
    # Present is not read: `baskets: null, themes: null` has every key and gives a client
    # written from the schema nothing (deep pass 2026-10-04, T14).
    mistyped = [{"property": name, "answered": _json_type_of(run[name]),
                 "schema_allows": sorted(types)}
                for name, types in documented.items()
                if name in run and types is not None
                and not any(_is_json_type(run[name], t) for t in types)]
    problems = []
    if missing:
        problems.append(f"lacks {len(missing)} of the {len(listed)} properties its schema lists: "
                        f"{', '.join(missing)}")
    if mistyped:
        problems.append(f"answers {len(mistyped)} property(ies) with a value its schema does not allow: "
                        + ", ".join(f"{m['property']} is {m['answered']} (schema: {'/'.join(m['schema_allows'])})"
                                    for m in mistyped))
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=(f"{RUNS}/{{run_id}} for {run_id} " + "; and ".join(problems)
                + f"; it answers {', '.join(sorted(run))}"
                if problems else
                f"all {len(listed)} documented properties are present on {run_id}, each of a type its "
                f"schema allows"),
        left={"documented_but_absent": missing,
              "documented_but_null_or_mistyped": [m["property"] for m in mistyped]},
        right={"documented_but_absent": [], "documented_but_null_or_mistyped": []},
        population={"documented": listed, "answered": sorted(run), "run_id": run_id,
                    "mistyped": mistyped},
        sources={"schema": OPENAPI, "run": f"{RUNS}/{run_id}"}))


@qa(component="rest.research_backtest", tier=SafetyTier.SAFE, surface="rest")
def test_a_run_on_a_theme_is_listed_with_that_theme(rest_anon):
    """A stored run whose parameters name a theme appears in the list under THAT theme:
    its own `parameters.theme` (lower-cased, trimmed) is among the listed `themes`."""
    runs = (_json(_get(rest_anon, RUNS), RUNS) or {}).get("runs")
    if not isinstance(runs, list) or not runs:
        raise Inconclusive(f"{RUNS} lists no stored run to read")
    judged, unlisted = [], []
    for row in runs[:MAX_RUNS]:
        # Not an object is a read we cannot judge, never an AttributeError (R07/T13, deep
        # pass 2026-10-04).
        if not isinstance(row, dict):
            raise Inconclusive(f"{RUNS} lists a stored run that is a {type(row).__name__}, not an object")
        run_id = row.get("run_id")
        if not run_id:
            continue
        run = _json(_get(rest_anon, f"{RUNS}/{run_id}"), f"{RUNS}/{run_id}")
        if not isinstance(run, dict):
            raise Inconclusive(f"{RUNS}/{run_id} answered something that is not an object")
        parameters = run.get("parameters")
        if parameters is not None and not isinstance(parameters, dict):
            raise Inconclusive(f"{RUNS}/{run_id} has `parameters` that is a {type(parameters).__name__}, "
                               f"not an object")
        named = (parameters or {}).get("theme")
        if named is not None and not isinstance(named, str):
            raise Inconclusive(f"{RUNS}/{run_id} has `parameters.theme` that is a {type(named).__name__}, "
                               f"not a string")
        theme = (named or "").strip().lower()
        if theme in ("", "all"):
            continue
        shown = row.get("themes")
        shown_themes = ({t.strip().lower() for t in shown if isinstance(t, str)}
                        if isinstance(shown, list) else set())
        judged.append({"run_id": run_id, "theme": theme, "listed_themes": shown})
        if theme not in shown_themes:
            unlisted.append(judged[-1])
    if not judged:
        raise Inconclusive(f"none of the {len(runs)} stored run(s) is on a named theme, so none can be judged")
    conclude(Measurement(
        verdict="failed" if unlisted else "passed",
        reason=(f"{len(unlisted)} of {len(judged)} runs on a named theme are not listed under it: "
                + "; ".join(f"{u['run_id']} (parameters.theme {u['theme']!r}, listed themes {u['listed_themes']!r})"
                            for u in unlisted[:3])
                if unlisted else
                f"all {len(judged)} runs on a named theme are listed under it"),
        left={"runs_listed_without_their_theme": len(unlisted)},
        right={"runs_listed_without_their_theme": 0},
        population={"judged": judged},
        sources={"list": RUNS}))
