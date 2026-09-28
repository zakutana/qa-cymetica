"""Every route their feature pages name is in the schema agents are told to import.

`/openapi-public.json` is the document llms.txt and the agent card send an
outside agent to. The operator, 2026-09-24, kept in NEXT.md: *"vydávají
stránky a do dokumentace je nedávají"* -- they ship pages, and what the pages
call does not reach the docs. Three pages named that day, each for a surface
found that way:

  * `/h2h` -- head-to-head matchups, then in no document at all
    (test_head_to_head_surface_is_undocumented, now published);
  * `/<username>`, our own creator page -- the creator dashboard;
  * `/backtest/api` -- their Backtest API page, the one public page that
    names `run-backtest`, which REPLY-0049 (2026-09-23) called "missing from
    openapi-public.json -- that's a discoverability bug on our side".

**What was seen when this was written** (2026-09-28): the creator page calls
`POST /api/v1/creator/channel-posts`, `POST /api/v1/creator/radar-channel-posts`
and `PATCH /api/v1/creator/links/{slug}`; /backtest/api documents seven
`/api/v1/backtest/bots/{slug}/...` routes, run-backtest among them, and
`/api/v1/backtest/clone` -- none of them in /openapi-public.json (251 paths).
Every route /h2h names is published.

**The claim:** every `/api/v1/...` these pages name -- in their own HTML and
in any script only they load -- is a path of `/openapi-public.json`, and where
the page states the method, the spec publishes that method on it.

How it differs from its siblings: test_public_page_reads_are_documented crawls
every page the home page links and judges only what answers an anonymous GET
with 200 JSON; this reads three named pages and judges every route on them,
writes and authenticated reads included, and calls none of them.

**Reading a route** (memory extract-from-text-anchor-on-markup): a path is
characters no tag can contribute -- no `<`, `>`, quote, backtick, space, `?`
or `#` -- so a `<code>` or `<span>` beside it is a boundary, never part of it;
the method is read off what stands beside it, across whole tags only. A
`{slot}`, a JS `${slot}`, an escaped `&lt;slot&gt;` and an id concatenated in
(`'/links/' + slug`) are slots. A literal ending in `/` with nothing joined to
it, or ending `/*`, names a family: published when some published path
strictly extends it. A method is compared only where the page states one
(`<span class="method">`, `POST /api/...`, a fetch's own `method:`); a bare
fetch is not read as a GET. Every stated method agreed with the spec on the
day this was written, so that branch had not yet fired.

**Out of scope, deliberately:** what the home page names as well -- the push
plumbing every page carries -- is the site's chrome, not the feature's; and
a script the home page loads too is not fetched. A home-page route that is
undocumented is its sibling's to judge.

INCONCLUSIVE, never a gap (rule 8): the document unread, not JSON or empty;
the home page unread, so chrome cannot be told from the feature; a page or
its own script unread; a page naming no route at all -- its calls may have
moved. A gap on a page that was read fails even when another was not.

SAFE: GETs of three pages, the home page, one script and one document.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_creator_links_lists_every_tracked_link import CREATOR

SPEC = "/openapi-public.json"
HOME = "/"
# The page, and the surface it was named for (NEXT.md, 2026-09-23).
PAGES = {"/h2h": "head-to-head", f"/{CREATOR}": "creator",
         "/backtest/api": "run-backtest"}
HTML = {"Accept": "text/html"}
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

# One segment as a page writes it: a `{slot}` or JS `${slot}`, an escaped
# `&lt;slot&gt;`, or a word. None of the three can hold `<` or `>`.
SEGMENT = (r"(?:\$?\{[^{}/\s<>'\"`]*\}|&lt;[A-Za-z_][\w-]*&gt;"
           r"|[A-Za-z0-9_\-.~*]+)")
ROUTE = re.compile(r"/api/v1((?:/" + SEGMENT + r")*)(/?)")
# `'/api/v1/x/' + id` and `'/api/v1/x/' + id + '/posted'`, right after the
# literal that ends in `/`.
CONCAT = re.compile(r"""['"`]\s*\+\s*([\w$.\[\]]+(?:\([\w$.]*\))?)"""
                    r"""(?:\s*\+\s*(['"`])(/[\w\-/.]*)\2)?""")
# The method a page states: the word, then only whitespace, whole tags, a
# quote or the host between it and the path.
STATED = re.compile(r"\b(" + "|".join(METHODS) + r")\b(?:\s|<[^<>]*>|['\"])*"
                    r"(?:https?://[\w.-]+)?$")
# Or the fetch() the literal opens, with `method:` in its own options object.
FETCH = re.compile(r"fetch\(\s*['\"`]$")
OPTIONS = re.compile(r"""['"`]?\s*,\s*\{[^{}]*?\bmethod\s*:\s*['"](\w+)['"]""")
SCRIPT = re.compile(r'<script[^>]+src="(/static/js/[^"?#]+)')


def _slot(segment: str) -> str:
    """`${a}`, `{a}` and `&lt;a&gt;` all read `{a}`."""
    name = re.sub(r"^\$?\{|\}$|^&lt;|&gt;$", "", segment)
    return "{" + name + "}"


def _normal(segment: str) -> str:
    if segment.startswith(("{", "${", "&lt;")):
        return _slot(segment)
    return segment


def routes_named(text: str) -> dict[str, set[str]]:
    """Each route the text names, with the methods it states for it.

    A family -- a literal ending in `/` and joined to nothing, or `/*` -- is
    kept with its trailing `/`.
    """
    found: dict[str, set[str]] = {}
    text = text or ""
    for hit in ROUTE.finditer(text):
        parts = [_normal(s) for s in hit.group(1).split("/")[1:]]
        if parts and parts[-1] != "*":
            parts[-1] = parts[-1].rstrip(".")
        end = hit.end()
        family = bool(hit.group(2)) or (parts and parts[-1] == "*")
        if parts and parts[-1] == "*":
            parts = parts[:-1]
        if hit.group(2):
            joined = CONCAT.match(text, end)
            if joined:
                names = re.findall(r"[A-Za-z_$][\w$]*", joined.group(1))
                parts.append("{" + (names[-1] if names else "x") + "}")
                if joined.group(3):
                    parts += [s for s in joined.group(3).split("/") if s]
                family, end = False, joined.end()
        parts = [p for p in parts if p]
        if not parts:
            continue
        path = "/api/v1/" + "/".join(parts) + ("/" if family else "")
        methods = found.setdefault(path, set())
        before = text[max(0, hit.start() - 160):hit.start()]
        said = STATED.search(before)
        if said:
            methods.add(said.group(1))
        elif FETCH.search(before):
            options = OPTIONS.match(text, end)
            if options and options.group(1).upper() in METHODS:
                methods.add(options.group(1).upper())
    return found


def _is_slot(segment: str) -> bool:
    return segment.startswith("{")


def _fits(ours: list[str], theirs: list[str], published: list[list[str]]) -> bool:
    """Segment by segment: our slot stands only where theirs does; their slot
    takes a concrete segment unless they publish that very literal at that
    position under the same prefix -- then it is that route, not a value
    (the reason test_nexus_routes_exist gives, A06 of 2026-09-21)."""
    for at, (mine, slot) in enumerate(zip(ours, theirs)):
        if _is_slot(slot):
            if _is_slot(mine):
                continue
            siblings = {t[at] for t in published if len(t) > at
                        and t[:at] == theirs[:at] and not _is_slot(t[at])}
            if mine in siblings:
                return False
        elif mine != slot:
            return False
    return True


def _methods_of(path: str, spec_paths: dict) -> set[str] | None:
    """The methods published on every template the route fits, or None when
    none fits. A family fits a template that strictly extends it."""
    family = path.endswith("/")
    ours = path.strip("/").split("/")
    published = [t.strip("/").split("/") for t in spec_paths]
    methods, fitted = set(), False
    for template, theirs in zip(spec_paths, published):
        if family:
            fit = len(theirs) > len(ours) and _fits(ours, theirs[:len(ours)], published)
        else:
            fit = len(theirs) == len(ours) and _fits(ours, theirs, published)
        if fit:
            fitted = True
            methods |= {m.upper() for m in (spec_paths[template] or {})
                        if isinstance(m, str) and m.upper() in METHODS}
    return methods if fitted else None


def _covered(path: str, others: list[str]) -> bool:
    """A concrete example of a route the same list names as a template --
    `bots/your-bot-slug/run-backtest` beside `bots/{slug}/run-backtest` --
    is that route, said once."""
    ours = path.strip("/").split("/")
    for other in others:
        theirs = other.strip("/").split("/")
        if other != path and len(theirs) == len(ours) and any(map(_is_slot, theirs)) \
                and all(t == o or (_is_slot(t) and not _is_slot(o))
                        for t, o in zip(theirs, ours)):
            return True
    return False


def undocumented(named: dict[str, set[str]], spec_paths: dict) -> list[str]:
    """What the spec lacks, one line each: `METHOD /path` for a route whose
    path is missing (method when stated), and `METHOD /path (path published,
    method not)` for one whose stated method is."""
    missing_paths = [p for p in named if _methods_of(p, spec_paths) is None]
    out = []
    for path in sorted(named):
        stated = sorted(named[path])
        published = _methods_of(path, spec_paths)
        if published is None:
            if not _covered(path, missing_paths):
                out.append(f"{'/'.join(stated)} {path}" if stated else path)
        elif stated and set(stated) - published:
            out.append(f"{'/'.join(sorted(set(stated) - published))} {path} "
                       f"(path published, method not)")
    return out


def _get(client, path, **kw):
    """One GET, or None when their server did not answer in time."""
    import httpx

    try:
        return client.get(path, **kw)
    except httpx.TimeoutException:
        return None


def _script_path(src: str) -> str:
    return src.split("?", 1)[0]


@qa(component="discovery.openapi", tier=SafetyTier.SAFE, surface="rest")
def test_every_route_a_feature_page_names_is_in_the_public_openapi(rest_anon):
    """Three named pages and their own scripts, against /openapi-public.json."""
    spec = _get(rest_anon, SPEC)
    if spec is None or spec.status_code != 200:
        raise Inconclusive(f"{SPEC} answered "
                           f"{'nothing in time' if spec is None else spec.status_code}"
                           f"; a failed read is not a document that omits a route")
    try:
        spec_paths = (spec.json() or {}).get("paths") or {}
    except (ValueError, AttributeError):
        raise Inconclusive(f"{SPEC} answered 200 with a body that is not a JSON object")
    if not isinstance(spec_paths, dict) or not spec_paths:
        raise Inconclusive(f"{SPEC} publishes no paths, so nothing can be missing from it")

    home = _get(rest_anon, HOME, headers=HTML)
    if home is None or home.status_code != 200:
        raise Inconclusive("the home page could not be read, so the chrome every "
                           "page carries cannot be told from what a page adds")
    chrome = set(routes_named(home.text))
    sitewide = {_script_path(s) for s in SCRIPT.findall(home.text)}

    on: dict[str, dict[str, set[str]]] = {}
    unread, silent = [], []
    for page in PAGES:
        answer = _get(rest_anon, page, headers=HTML)
        if answer is None or answer.status_code != 200:
            unread.append(f"{page} ({'timed out' if answer is None else answer.status_code})")
            continue
        texts = [answer.text]
        for src in sorted({_script_path(s) for s in SCRIPT.findall(answer.text)} - sitewide):
            script = _get(rest_anon, src)
            if script is None or script.status_code != 200:
                unread.append(f"{src} ({'timed out' if script is None else script.status_code})")
            else:
                texts.append(script.text)
        named: dict[str, set[str]] = {}
        for text in texts:
            for path, methods in routes_named(text).items():
                if path not in chrome:
                    named.setdefault(path, set()).update(methods)
        if named:
            on[page] = named
        else:
            silent.append(page)

    every: dict[str, set[str]] = {}
    for named in on.values():
        for path, methods in named.items():
            every.setdefault(path, set()).update(methods)
    missing = undocumented(every, spec_paths)
    where = {line: sorted(page for page, named in on.items()
                          if line.split(" (")[0].split(" ")[-1] in named)
             for line in missing}
    if not missing and (unread or silent):
        raise Inconclusive(
            f"every route read is published, but {len(unread)} read(s) failed "
            f"({', '.join(unread) or 'none'}) and {len(silent)} page(s) named no "
            f"route at all ({', '.join(silent) or 'none'}) -- a pass needs all three")
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} route(s) that {', '.join(sorted(on))} name are not "
                f"in {SPEC} ({len(spec_paths)} paths): " + "; ".join(missing)
                if missing else
                f"every one of the {len(every)} route(s) {', '.join(sorted(on))} "
                f"name is in {SPEC}"),
        left=missing, right=[],
        population={"pages": {page: sorted(named) for page, named in on.items()},
                    "where": where, "chrome": sorted(chrome), "unread": unread,
                    "silent": silent, "published_paths": len(spec_paths)},
        sources={"spec": SPEC, "pages": PAGES,
                 "contract": "llms.txt and the agent card send outside agents to "
                             "/openapi-public.json; REPLY-0049 called a route "
                             "missing from it a discoverability bug"}))
