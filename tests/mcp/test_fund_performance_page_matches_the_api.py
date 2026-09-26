"""The fund leaderboard a visitor reads is the one their API returns.

Cymetica asked outside QA, second in its list (REPLY-0030): "Fund Launcher and
the fund pages -- every number a visitor sees. Does it reconcile with the
API?" The page is /fund-performance, "All funds, ranked -- Every fund on this
page, best return first", one row per fund: name, sleeve, status, index,
return. The API is `list_funds` on their MCP, the roster their advisor
connector hands an agent: symbol, name, sleeve, status, `index_price_usd`,
`return_since_inception_pct`.

**What was seen when this was written** (2026-09-25): 27 rows and 27 funds,
every one matching -- same names, same sleeves and statuses, index and return
equal to the cent and the hundredth. This check exists so that stays true: it
is their priority, and a leaderboard that drifts from its API misleads the
one reader it is for.

**Anchored on the markup** (`tr` > `td.rk`, `td.fund`, `td.sleeve`, `span.st`,
the two `td.num` in order), never on prose.

**Tolerances**, because the page is rendered on a request and the API read a
moment apart: index within 1 % or a cent (the page prints two decimals, so a
0.0103 index reads $0.01), return within 0.5 points. Beyond those it fails:
a different number is a different number. Order is checked as "best return
first", the page's own sentence; a fund without a return sorts last.

GETs and read-only MCP tools only.
"""

from __future__ import annotations

import html
import re
import time

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PAGE = "https://cymetica.com/fund-performance"
INDEX_REL = 0.01
INDEX_ABS = 0.01
RETURN_PTS = 0.5
SETTLE_S = 20.0

ROW = re.compile(r"<tr[^>]*>\s*<td class=\"rk\">(\d+)</td>(.*?)</tr>", re.S)
# The fund cell with or without a link: FTA Fund -- Stocks has no profile and
# its row carries no ids, so the numbers are read as the row's two td.num
# cells in order (index, then return), not by id.
NAME = re.compile(r"<td class=\"fund\">(.*?)</td>", re.S)
SLEEVE = re.compile(r"<td class=\"sleeve\">(.*?)<span", re.S)
STATUS = re.compile(r"<span class=\"st [^\"]*\">(.*?)</span>", re.S)
# `td.num` and, since their ET-27387, `td.num.idx` for the index cell.
NUMS = re.compile(r"<td class=\"num(?: idx)?\"[^>]*>(.*?)</td>", re.S)
FIGURE = re.compile(r"([+\-−]?[\d,]*\.?\d+)")


def _num(text):
    found = FIGURE.search(re.sub(r"<[^>]+>", " ", str(text)))
    return float(found.group(1).replace(",", "").replace("−", "-")) if found else None


def rows_of(page: str) -> list[dict]:
    """Every leaderboard row, in page order."""
    out = []
    for rank, cells in ROW.findall(page or ""):
        name, sleeve, status = NAME.search(cells), SLEEVE.search(cells), STATUS.search(cells)
        nums = NUMS.findall(cells)
        index = nums[0] if len(nums) > 0 else None
        ret = nums[1] if len(nums) > 1 and "%" in nums[1] else None
        if not name:
            continue
        out.append({"rank": int(rank),
                    "name": html.unescape(re.sub(r"<[^>]+>", "", name.group(1))).strip(),
                    "sleeve": html.unescape(sleeve.group(1)).strip() if sleeve else None,
                    "status": status.group(1).strip() if status else None,
                    "index": _num(index) if index else None,
                    "return": _num(ret) if ret else None})
    return out


def disagreements(rows: list[dict], funds: list[dict]) -> list[str]:
    """What the page says that the API does not, one line each."""
    api = {f.get("name"): f for f in funds}
    out = []
    for row in rows:
        f = api.get(row["name"])
        if f is None:
            out.append(f"{row['name']!r} is on the page and not in list_funds")
            continue
        if row["sleeve"] != f.get("sleeve") or row["status"] != f.get("status"):
            out.append(f"{row['name']!r}: page {row['sleeve']}/{row['status']}, "
                       f"API {f.get('sleeve')}/{f.get('status')}")
        price = f.get("index_price_usd")
        priced = isinstance(price, (int, float))
        # A figure on one side only is a disagreement, the way the return is
        # judged below: a page showing $1.23 over an API null passed
        # (deep pass 2026-09-25, A08).
        if (row["index"] is None) != (not priced):
            out.append(f"{row['name']!r}: page index "
                       f"{'none' if row['index'] is None else '$' + str(row['index'])}, "
                       f"API {price}")
        elif row["index"] is not None and priced:
            if abs(row["index"] - round(price, 2)) > max(INDEX_ABS, INDEX_REL * abs(price)):
                out.append(f"{row['name']!r}: page index ${row['index']}, API {price}")
        ret = f.get("return_since_inception_pct")
        if (row["return"] is None) != (ret is None) or (
                ret is not None and abs(row["return"] - ret) > RETURN_PTS):
            out.append(f"{row['name']!r}: page return {row['return']}%, API {ret}%")
    for name in sorted(set(api) - {r["name"] for r in rows}):
        out.append(f"{name!r} is in list_funds and not on the page")
    order = [r["return"] if r["return"] is not None else float("-inf") for r in rows]
    if any(a < b for a, b in zip(order, order[1:])):
        out.append("the table is not in best-return-first order")
    return out


def _body(answer):
    if isinstance(answer, dict) and isinstance(answer.get("result"), dict):
        return answer["result"]
    return answer if isinstance(answer, dict) else {}


def _read(mcp_anon):
    page = mcp_anon.http.get(PAGE)
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    rows = rows_of(page.text)
    if not rows:
        raise Inconclusive(f"no leaderboard row could be read on {PAGE}; the "
                           f"markup moved, which is ours to follow")
    try:
        funds = _body(mcp_anon.call("list_funds", {"limit": 100})).get("funds") or []
    except McpError as exc:
        raise Inconclusive(f"list_funds failed: {exc}")
    if not funds:
        raise Inconclusive("list_funds returned no funds; a failed read is not an empty one")
    return rows, funds


def _who(line: str) -> str:
    return line.split(":", 1)[0] if line.startswith("'") else line


@qa(component="mcp.fund_research", tier=SafetyTier.SAFE, surface="mcp")
def test_the_fund_leaderboard_page_matches_list_funds(mcp_anon):
    """Every row of /fund-performance against list_funds, twice when they differ.

    The page and the API are read a moment apart, and on 2026-09-25 that was
    enough for ten stock funds to differ by up to 0.65 points during US hours
    and agree twenty seconds later. So a disagreement is read again after
    SETTLE_S, and only a fund that disagrees in both reads counts.
    """
    rows, funds = _read(mcp_anon)
    wrong = disagreements(rows, funds)
    if wrong:
        time.sleep(SETTLE_S)
        rows, funds = _read(mcp_anon)
        again = disagreements(rows, funds)
        first = {_who(w) for w in wrong}
        wrong = [w for w in again if _who(w) in first]
    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=("; ".join(wrong[:6]) + (f" (+{len(wrong) - 6} more)" if len(wrong) > 6 else "")
                if wrong else
                f"all {len(rows)} rows of {PAGE} match list_funds: names, sleeves, "
                f"statuses, index and return, best return first"),
        left={"rows": len(rows), "funds": len(funds), "disagreements": len(wrong)},
        right={"disagreements": 0},
        population={"page": [r["name"] for r in rows]},
        sources={"page": PAGE, "api": "MCP list_funds"}))
