"""/usage: the Dynamic plan card takes a signed-in cookie session as signed in (2026-10-22).

Seen in the operator's signed-in browser on https://cymetica.com/usage, 2026-10-22 ~18:30 UTC: the usage card
on the same page drew the account's live plan (Max 5x, session and week), while the Dynamic plan card
(`#nxd-body`) read "... smallest BRRR buy $0.01 / Log in to see your forecast and switch." In that page
`window.getAuthToken()` was empty, and `fetch('/api/v1/nexus/dynamic', {credentials: 'same-origin'})` answered
200 with the account's forecast: the server knew the session, the card never asked it.

Why, read anonymously from what the page serves (the page and its scripts are the same for everyone): the
card's inline script decides "signed out" with `if (!tok()) { ...'Log in to see your forecast and switch.'...;
return; }`, where `tok()` is `window.getAuthToken()` -- a read of bearer tokens kept in localStorage /
sessionStorage -- and it returns before /api/v1/nexus/dynamic is asked. auth.js removes those stored tokens
whenever the `et_session` cookie is present, and the page's own head script says so ("Audit #20: the
credential is an httpOnly cookie, so getAuthToken() is null for a perfectly valid session"). The usage card
beside it (nexus-usage.js) asks the server with the cookie and treats a 401 as signed out.

**The rule.** The script that draws the card must not reach its signed-out view on a bearer-token read
alone: a gate that tests only a token (`getAuthToken()`, a helper that returns it, or a variable holding it)
and, when there is none, leaves without asking /api/v1/nexus/dynamic and without consulting the session
(`hasSession`, `hasSessionCookie`, `et_session`, `document.cookie`, `authManager`, `isAuthenticated`, a 401)
is the defect. The same for the positive form: the endpoint asked only inside `if (<token>)`. A compound
condition counts too, when a missing token reaches the signed-out view without the session being read
(`!tok() || !plan`, `!tok() && !plan`); and a helper or a branch consults the session only in its code --
what a helper returns, never a comment (B04, deep pass 2026-10-25).

VERDICTS. failed: such a gate exists in a script that draws the card. passed: no such gate, and the script
asks the endpoint -- whether the gate went, learned the session, asks the server anyway, or the token
helper (the card's or the page's `getAuthToken`) falls back to the session. inconclusive: the page or the
card (`#nxd-body`) is gone; no script names both the card and the endpoint; any same-origin script the page
loads could not be read (it may redefine the helper or draw the card); a gate's branch never closes; a
helper that answers '' for a session (still falsy under `!`); a token ternary that chooses between asking and
a sign-in text, which this check does not read as a gate.

NOT asserted: what the card shows a visitor who really is signed out; a fix that would put a bearer token
back into storage for cookie sessions (their own Audit #20 moved away from that); the card's buttons. The
forecast read with our key (GET /api/v1/nexus/dynamic) is recorded beside the verdict and does not decide it;
without a key it is recorded as not read, and the check still runs.
SAFE: anonymous GETs of the page and the scripts it loads, one GET of the endpoint with our key.
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

import httpx
import pytest

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PAGE = "/usage"
CARD = "nxd-body"
ENDPOINT = "/api/v1/nexus/dynamic"
ENDPOINT_MARK = "nexus/dynamic"
MAX_SCRIPTS = 40

SESSION = re.compile(r"hasSession|et_session|document\.cookie|authManager|isAuthenticated|\b401\b")
SIGN_IN = re.compile(r"\b(?:log|sign)[\s-]?in\b", re.I)
EMPTY_FOR_SESSION = re.compile(r"\?\s*(?:''|\"\"|``)\s*:")
OPEN, CLOSE = "([{", ")]}"


# ------------------------------------------------------------------ reading JS without running it

def _mask(js: str, comments_only: bool = False) -> str:
    """The script with the inside of every string, template, regex literal and comment blanked, index for
    index, so braces, parentheses and semicolons can be counted without being fooled by text.

    `comments_only`: blank the comments and keep every string and regex literal -- the code as it runs,
    still index for index. A session word in a comment is not a session consult, and `getCookie(
    'et_session')` is one (B04, deep pass 2026-10-25)."""
    out, i, n, prev = list(js), 0, len(js), ""

    def blank(a: int, b: int, text: bool = True) -> None:
        if text and comments_only:
            return
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = js[i]
        if c in "'\"`":
            j = i + 1
            while j < n and js[j] != c:
                j += 2 if js[j] == "\\" else 1
            blank(i + 1, j)
            i, prev = j + 1, c
            continue
        if c == "/" and js.startswith("//", i):
            j = js.find("\n", i)
            j = n if j < 0 else j
            blank(i, j, text=False)
            i = j
            continue
        if c == "/" and js.startswith("/*", i):
            j = js.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j, text=False)
            i = j
            continue
        if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^"):
            j, in_class = i + 1, False
            while j < n and js[j] != "\n":
                ch = js[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    break
                j += 1
            blank(i + 1, j)
            i, prev = j + 1, "/"
            continue
        if not c.isspace():
            prev = c
        i += 1
    return "".join(out)


def _match(m: str, start: int) -> int | None:
    """Index of the bracket closing the one at `start` in masked text, or None if it never closes."""
    depth = 0
    for k in range(start, len(m)):
        if m[k] in OPEN:
            depth += 1
        elif m[k] in CLOSE:
            depth -= 1
            if depth == 0:
                return k
    return None


def _statement_end(m: str, start: int) -> int | None:
    """End of one statement from `start`: the first `;` at depth 0, or where an enclosing bracket closes."""
    depth = 0
    for k in range(start, len(m)):
        if m[k] in OPEN:
            depth += 1
        elif m[k] in CLOSE:
            depth -= 1
            if depth < 0:
                return k
        elif m[k] == ";" and depth == 0:
            return k + 1
    return None


def _skip_ws(m: str, k: int) -> int:
    while k < len(m) and m[k].isspace():
        k += 1
    return k


def _body(m: str, k: int) -> tuple[int, int] | None:
    """(start, end) of a `{...}` block or a single statement beginning at or after k, in masked text."""
    k = _skip_ws(m, k)
    if k < len(m) and m[k] == "{":
        end = _match(m, k)
        return None if end is None else (k + 1, end)
    end = _statement_end(m, k)
    return None if end is None else (k, end)


def _split_top(text: str, masked: str, op: str) -> list[tuple[str, str]]:
    """`text` cut at every `op` (`||` or `&&`) outside brackets, found on its mask: (text, mask) pieces."""
    pieces, depth, start, k = [], 0, 0, 0
    while k < len(masked):
        if masked[k] in OPEN:
            depth += 1
        elif masked[k] in CLOSE:
            depth -= 1
        elif depth == 0 and masked.startswith(op, k):
            pieces.append((text[start:k], masked[start:k]))
            start = k = k + len(op)
            continue
        k += 1
    pieces.append((text[start:], masked[start:]))
    return pieces


def _top_level_return(m: str) -> bool:
    depth = 0
    for k, ch in enumerate(m):
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
        elif depth == 0 and m.startswith("return", k) and (k == 0 or not (m[k - 1].isalnum() or m[k - 1] in "_$")):
            return True
    return False


def _functions(js: str, m: str) -> dict[str, tuple[int, int, bool]]:
    """Every named function in the script: its body span, and whether it takes no arguments
    (`function f(`, `var f = function`, arrows)."""
    found: dict[str, tuple[int, int, bool]] = {}
    arrow = r"(?:\bvar|\blet|\bconst)\s+([\w$]+)\s*=\s*(?:async\s*)?\("
    patterns = (r"\bfunction\s+([\w$]+)\s*\(",
                r"(?:\bvar|\blet|\bconst)\s+([\w$]+)\s*=\s*(?:async\s+)?function\b[^(]*\(",
                arrow)
    for pattern in patterns:
        for f in re.finditer(pattern, m):
            params_end = _match(m, f.end() - 1)
            if params_end is None:
                continue
            after = _skip_ws(m, params_end + 1)
            if pattern == arrow:                              # an arrow needs its =>
                if not m.startswith("=>", after):
                    continue
                after += 2
            span = _body(m, after)
            if span and f.group(1) not in found:
                found[f.group(1)] = (span[0], span[1], not m[f.end():params_end].strip())
    return found


def _returns_a_token(js: str, m: str, span: tuple[int, int], calls: str) -> bool:
    """Whether a function body returns a token read: a call of `calls`, or a local variable holding one."""
    body_m = m[span[0]:span[1]]
    local = set(re.findall(r"(?:\bvar|\blet|\bconst|[,;{(])\s*([\w$]+)\s*=\s*(?:" + calls + r")\s*\(\s*\)", body_m))
    for r in re.finditer(r"(?<![\w$.])return\b", body_m):
        end = _statement_end(body_m, r.end())
        statement = body_m[r.end():end or len(body_m)]
        if re.search(r"(?:" + calls + r")\s*\(\s*\)", statement):
            return True
        if any(re.search(r"(?<![\w$.])" + re.escape(v) + r"(?![\w$])", statement) for v in local):
            return True
    return False


def _session_kind(code: str, masked: str) -> str | None:
    """Whether a token reader's ANSWER depends on the session, read from what it returns, not from the
    words its body holds (B04, deep pass 2026-10-25: a comment or a log line naming et_session made the
    defect's own helper "mixed", and the check passed). `code` is the body with its comments blanked,
    `masked` the same body fully masked, index for index. The code read: every `return` statement, the
    condition of every `if` whose branch returns, and the value of a local any of those reads. "mixed"
    when a session consult is in it, "ambiguous" when it answers '' for one, None when it has none."""
    returning, read = [], []
    for r in re.finditer(r"(?<![\w$.])return\b", masked):
        end = _statement_end(masked, r.end())
        returning.append(code[r.end():end or len(masked)])
    for g in re.finditer(r"\bif\s*\(", masked):
        close = _match(masked, g.end() - 1)
        branch = None if close is None else _body(masked, close + 1)
        if branch and re.search(r"(?<![\w$.])return\b", masked[branch[0]:branch[1]]):
            returning.append(code[g.end():close])
    for v in re.finditer(r"(?:\bvar|\blet|\bconst|[,;{(])\s*([\w$]+)\s*=(?![=>])", masked):
        if any(re.search(r"(?<![\w$.])" + re.escape(v.group(1)) + r"(?![\w$])", piece) for piece in returning):
            end = _statement_end(masked, v.end())
            read.append(code[v.end():end or len(masked)])
    said = "\n".join(returning + read)
    if not SESSION.search(said):
        return None
    return "ambiguous" if EMPTY_FOR_SESSION.search(said) else "mixed"


def _token_helper_kind(page_js: str) -> str:
    """How the page's own window.getAuthToken answers: "token" (stored bearer tokens only), "mixed" (it
    consults the session too), "ambiguous" (it answers '' for a session). No definition read: "token" --
    the platform's name for a read of the stored token."""
    m, code = _mask(page_js), _mask(page_js, comments_only=True)
    kinds = []
    for d in re.finditer(r"getAuthToken\s*=\s*(?:window\.getAuthToken\s*\|\|\s*)?function\s*[\w$]*\s*\(|"
                         r"\bfunction\s+getAuthToken\s*\(", m):
        params_end = _match(m, d.end() - 1)
        span = None if params_end is None else _body(m, params_end + 1)
        if not span:
            continue
        kind = _session_kind(code[span[0]:span[1]], m[span[0]:span[1]])
        if kind:
            kinds.append(kind)
    return "ambiguous" if "ambiguous" in kinds else "mixed" if kinds else "token"


def _asks(text: str, masked: str, api_vars: set[str], askers: set[str]) -> bool:
    """Whether this stretch of code requests the Dynamic endpoint, itself or through a function that does."""
    if re.search(r"fetch\s*\(\s*['\"`][^'\"`]*" + re.escape(ENDPOINT_MARK), text):
        return True
    if any(re.search(r"fetch\s*\(\s*" + re.escape(v) + r"\b", masked) for v in api_vars):
        return True
    return any(re.search(r"(?<![\w$.])" + re.escape(a) + r"\s*\(", masked)
               and not re.search(r"\bfunction\s+" + re.escape(a) + r"\s*\(", masked) for a in askers)


def _sign_in_text(text: str) -> str | None:
    for s in re.finditer(r"'([^'\n]*)'|\"([^\"\n]*)\"", text):
        words = re.sub(r"<[^>]+>", " ", s.group(1) or s.group(2) or "")
        if SIGN_IN.search(words):
            return " ".join(unescape(words).split())
    return None


def card_facts(js: str, page_js: str) -> dict | None:
    """What one script that draws the Dynamic card decides about signed-in, read from its code; None when
    the script does not draw the card (it must name both #nxd-body and the endpoint)."""
    # Its code: comments blanked, strings kept, index for index with the mask. A session word, a request
    # or a condition written in a comment is not in the script that runs (B04, deep pass 2026-10-25).
    js = _mask(js, comments_only=True)
    if CARD not in js or ENDPOINT_MARK not in js:
        return None
    m = _mask(js)
    functions = _functions(js, m)
    api_vars = set(re.findall(r"([\w$]+)\s*=\s*['\"`][^'\"`]*" + re.escape(ENDPOINT_MARK), js))

    askers: set[str] = set()
    for _ in range(6):                                   # a function that calls an asker asks too
        grown = {name for name, (a, b, _n) in functions.items()
                 if _asks(js[a:b], m[a:b], api_vars, askers - {name})}
        if grown == askers:
            break
        askers = grown

    # A token reader: a function of no arguments that returns the stored token (getAuthToken, or a reader
    # built on it). Its kind: "token" if what it returns consults no session, "mixed" if it does,
    # "ambiguous" if it answers '' for a session; a reader on a reader inherits.
    helper = _token_helper_kind(page_js)
    kinds: dict[str, str] = {}
    for _ in range(3):
        for name, (a, b, no_args) in functions.items():
            others = [r for r in kinds if r != name]
            calls = "|".join([r"(?:window\.)?getAuthToken"] + [re.escape(r) for r in others])
            if not no_args or not _returns_a_token(js, m, (a, b), calls):
                continue
            inherited = ([helper] if re.search(r"getAuthToken\s*\(", js[a:b]) else []) + [
                kinds[r] for r in others if re.search(r"(?<![\w$.])" + re.escape(r) + r"\s*\(", m[a:b])]
            kinds[name] = (_session_kind(js[a:b], m[a:b])
                           or ("ambiguous" if "ambiguous" in inherited
                               else "mixed" if "mixed" in inherited else "token"))
    readers = dict(kinds)
    calls_of = "|".join([r"(?:window\.)?getAuthToken"] + [re.escape(r) for r in readers])
    variables = {v.group(1): (helper if "getAuthToken" in v.group(2) else readers[v.group(2)])
                 for v in re.finditer(r"(?:\bvar|\blet|\bconst|[,;{(])\s*([\w$]+)\s*=\s*((?:window\.)?getAuthToken|"
                                      + "|".join([re.escape(r) for r in readers] or ["(?!x)x"])
                                      + r")\s*\(\s*\)\s*(?=[;,)\n])", m)}

    def kind_of(expr: str) -> str | None:
        e = expr
        while e.startswith("(") and _match(e, 0) == len(e) - 1:
            e = e[1:-1]
        call = re.fullmatch(r"(?:window\.)?(" + calls_of + r")\(\)", e)
        if call:
            name = call.group(1).replace("window.", "")
            return helper if name == "getAuthToken" else readers.get(name)
        return variables.get(e)

    facts = {"gates": [], "failing": [], "unclosed": [], "ambiguous": [], "readers": readers,
             "token_helper": helper, "asks": bool(askers) or _asks(js, m, api_vars, set()),
             "sign_in": _sign_in_text(js)}

    def stretch(span):
        return js[span[0]:span[1]], m[span[0]:span[1]]

    def gate_role(text: str, masked: str) -> str | None:
        """How an `if` condition tests a token: "negated" (its branch is reached when there is none),
        "positive" (its else is), None (it is no token gate, or the session decides with it), or why it
        cannot be read. A compound condition is judged by its operands (B04, deep pass 2026-10-25:
        `!tok() || !plan` was never judged). With no token, an OR holding `!tok()` is true whatever else
        it holds, and an AND holding `tok()` is false; an AND holding `!tok()`, or an OR holding `tok()`,
        is decided by the other operands too, so a session read among them makes it no token-only gate."""
        disjuncts = _split_top(text, masked, "||")
        groups = [_split_top(t, mk, "&&") for t, mk in disjuncts]
        terms = []
        for t, _mk in (piece for group in groups for piece in group):
            t = re.sub(r"\s+", "", t)
            neg = t.startswith("!") and not t.startswith("!=")
            terms.append((t, neg, kind_of(t[1:] if neg else t)))
        tokens = [(neg, kind) for _t, neg, kind in terms if kind is not None]
        if not tokens or any(kind == "mixed" for _neg, kind in tokens):
            return None
        if any(kind == "ambiguous" for _neg, kind in tokens):
            return "a helper that answers '' for a session"
        either = len(disjuncts) > 1
        if either and any(len(group) > 1 for group in groups):
            return "|| and && side by side around a token read"
        session = any(kind is None and SESSION.search(t) for t, _neg, kind in terms)
        if any(neg for neg, _kind in tokens):
            return "negated" if either or not session else None
        return "positive" if not either or not session else None

    for g in re.finditer(r"\bif\s*\(", m):
        close = _match(m, g.end() - 1)
        if close is None:
            continue
        condition = re.sub(r"\s+", "", js[g.end():close])
        role = gate_role(js[g.end():close], m[g.end():close])
        if role is None:
            continue
        facts["gates"].append(condition)
        if role not in ("negated", "positive"):
            facts["ambiguous"].append(f"if ({condition}): {role}")
            continue
        negated = role == "negated"
        then = _body(m, close + 1)
        if then is None:
            facts["unclosed"].append(f"if ({condition})")
            continue
        other = None
        braced = then[0] > 0 and m[then[0] - 1] == "{"
        k = _skip_ws(m, then[1] + (1 if braced else 0))
        if m.startswith("else", k) and not (m[k + 4:k + 5].isalnum() or m[k + 4:k + 5] in "_$"):
            other = _body(m, k + 4)
            if other is None:
                facts["unclosed"].append(f"if ({condition}) ... else")
                continue
        then_text, then_mask = stretch(then)
        if negated:
            out_text, out_mask = then_text, then_mask
            leaves = _top_level_return(then_mask) or other is not None
            if leaves and not SESSION.search(out_text) and not _asks(out_text, out_mask, api_vars, askers):
                facts["failing"].append({"condition": condition,
                                         "branch": " ".join(out_text.split())[:400]})
        else:
            if not _asks(then_text, then_mask, api_vars, askers):
                continue
            out_text, out_mask = stretch(other) if other else ("", "")
            if not SESSION.search(out_text) and not _asks(out_text, out_mask, api_vars, askers):
                facts["failing"].append({"condition": condition,
                                         "branch": (" ".join(out_text.split())[:400]
                                                    or "(no else: without a token nothing is asked)")})

    # A token tested in a ternary that picks between asking and a sign-in text: not a gate read here.
    for t in re.finditer(r"(?<![\w$.])(!?\s*(?:(?:window\.)?(?:" + calls_of + r")\s*\(\s*\)|"
                         + "|".join([re.escape(v) for v in variables] or ["(?!x)x"]) + r"))\s*\?(?![.?])", m):
        expr = re.sub(r"\s+", "", t.group(1)).lstrip("!")
        if kind_of(expr) not in ("token", "ambiguous"):
            continue
        end = _statement_end(m, t.end())
        seg_text, seg_mask = js[t.end():end or len(js)], m[t.end():end or len(js)]
        if SIGN_IN.search(seg_text) or _asks(seg_text, seg_mask, api_vars, askers):
            facts["ambiguous"].append(f"{t.group(1).strip()} ? ...: a token ternary decides")
    return facts


def judge(cards: list, unread: list[str]) -> tuple[str | None, str]:
    """(verdict, why): "failed", "passed", or None for inconclusive."""
    cards = [c for c in cards if c]
    if unread:
        return None, (f"{len(unread)} script(s) /usage loads could not be read ({unread[:3]}); one may "
                      f"redefine the token helper or draw the card")
    if not cards:
        return None, f"no script /usage loads draws #{CARD} from {ENDPOINT}"
    failing = [g for c in cards for g in c["failing"]]
    if failing:
        g = failing[0]
        return "failed", (f"the Dynamic plan card decides signed-out from a bearer token alone: if ({g['condition']}) "
                          f"leaves without asking {ENDPOINT} or the session")
    unclosed = [u for c in cards for u in c["unclosed"]]
    if unclosed:
        return None, f"a token gate whose branch could not be read to its end: {unclosed[0]}"
    ambiguous = [a for c in cards for a in c["ambiguous"]]
    if ambiguous:
        return None, f"the card tests a token in a way this check cannot decide: {ambiguous[0]}"
    if not any(c["asks"] for c in cards):
        return None, f"the card's script names {ENDPOINT} but never requests it"
    return "passed", (f"no token-only gate: the card asks {ENDPOINT} or the session before it calls a "
                      f"visitor signed out")


# ------------------------------------------------------------------ the page

class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.srcs: list[str] = []
        self.inline: list[str] = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "script":
            if a.get("src"):
                self.srcs.append(a["src"])
            else:
                self._in_script = True
                self.inline.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.inline[-1] += data


def _text(client, path: str) -> str | None:
    try:
        r = get_patiently(client, path)
    except (httpx.HTTPError, Inconclusive):
        return None
    return r.text if r.status_code == 200 else None


# auth.js, read 2026-10-22: `(hasSessionCookie() ...)&&["accessToken","access_token","auth_token",...].forEach(
# function(e){localStorage.removeItem(e),...})` -- with the session cookie present, the stored tokens go.
CLEARS = re.compile(r"(?:hasSessionCookie|et_session)[\s\S]{0,300}?\[\s*['\"](?:accessToken|access_token|auth_token)['\"]"
                    r"[\s\S]{0,200}?removeItem")


def _server_reading(request) -> dict:
    """GET /api/v1/nexus/dynamic with our key: what the card would show this account. Recorded only."""
    try:
        client = request.getfixturevalue("rest_trusted")
    except pytest.skip.Exception:
        return {"status_with_our_key": "not read (no trusted key configured)"}
    out: dict = {}
    try:
        answer = client.get(ENDPOINT)
        out["status_with_our_key"] = answer.status_code
        body = answer.json() if answer.status_code == 200 else {}
        out["forecast_with_fee_usd"] = (body.get("forecast") or {}).get("with_fee_usd")
        out["subscription"] = body.get("subscription")
    except Exception as exc:  # noqa: BLE001 - recorded, never a verdict
        out["status_with_our_key"] = f"not read ({type(exc).__name__})"
    return out


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest")
def test_the_dynamic_plan_card_takes_a_cookie_session_as_signed_in(rest_anon, request):
    """No gate in the Dynamic card's script reaches 'signed out' on a bearer-token read alone."""
    try:
        page = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{PAGE} could not be read: {type(exc).__name__}")
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    html = _Page()
    html.feed(page.text)
    if CARD not in html.ids:
        raise Inconclusive(f"{PAGE} no longer has the Dynamic plan card (#{CARD})")
    srcs = [s for s in html.srcs if s.startswith("/") and not s.startswith("//")][:MAX_SCRIPTS]
    bodies = {s: _text(rest_anon, s) for s in srcs}
    unread = sorted(s for s, b in bodies.items() if b is None)
    scripts = [(f"inline script {k + 1} of {len(html.inline)}", js) for k, js in enumerate(html.inline)]
    scripts += [(s, b) for s, b in bodies.items() if b is not None]
    page_js = "\n;\n".join(js for _, js in scripts)
    cards = []
    for label, js in scripts:
        facts = card_facts(js, page_js)
        if facts is not None:
            cards.append({**facts, "script": label})
    verdict, why = judge(cards, unread)

    server = _server_reading(request)

    gate = next((g for c in cards for g in c["failing"]), None)
    card = next((c for c in cards if c["failing"]), cards[0] if cards else {})
    population = {
        "card_script": card.get("script"),
        "gate": f"if ({gate['condition']})" if gate else None,
        "signed_out_branch": gate["branch"] if gate else None,
        "sign_in_text": card.get("sign_in"),
        "token_readers": card.get("readers"),
        "page_getAuthToken": card.get("token_helper"),
        "stored_tokens_cleared_when_et_session_present": bool(any(CLEARS.search(js) for _, js in scripts)),
        "scripts_read": len(scripts), "scripts_unread": unread,
        "page_date": page.headers.get("date"),
        **{f"endpoint_{k}": v for k, v in server.items()},
    }
    if verdict is None:
        raise Inconclusive(why)
    failed = verdict == "failed"
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{why}. On /usage the card's {card.get('script')} runs if ({gate['condition']}) "
                f"{{ ...{card.get('sign_in')!r}...; return; }} before it requests {ENDPOINT}; the token is "
                f"window.getAuthToken(), stored bearer tokens, which a cookie session does not have, so a "
                f"signed-in visitor is told to log in while GET {ENDPOINT} answers this account "
                f"HTTP {server.get('status_with_our_key')} with forecast with_fee_usd "
                f"{server.get('forecast_with_fee_usd')!r}"
                if failed else why),
        left={"token_only_gates": len([g for c in cards for g in c["failing"]])},
        right={"token_only_gates": 0},
        population=population,
        sources={"page": f"{PAGE} (#{CARD} and the inline script naming {ENDPOINT})",
                 "scripts": srcs, "endpoint": f"{ENDPOINT} (our key, recorded only)"}))
