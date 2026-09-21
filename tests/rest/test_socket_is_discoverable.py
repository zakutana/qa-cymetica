"""A live channel an agent cannot find is a channel built for browsers.

The whole pitch of this platform is that an agent discovers it: llms.txt for
a reader, openapi-public.json for a caller, mcp.json for a tool user. A
websocket advertised only in the HTML of a page is outside all three, and the
agent that was supposed to use it never learns it exists.

Measured 2026-09-20: `wss://cymetica.com/ws/build-it-better` appears in the
HTML of https://cymetica.com/build-it-better/api and in none of the three
machine-readable documents. It is live -- it accepts a connection with no
credential and greets with `{"type": "hello", "channel":
"build-it-better"}` -- so this is a document gap and not a dead link.

It is the same shape as the one they fixed the same afternoon: the Build it
Better REST routes were in mcp.json and in no OpenAPI document, and once told,
they put all six in openapi-public.json within the hour. This check is the
standing version of that conversation.

WHAT IT ASSERTS. Only presence: a socket URL found in a page, and the
documents in which that same channel is or is not named. The search over each
document is exhaustive -- the whole body, as bytes -- so "not named" is a
complete reading of that document rather than an inference. A page with no
socket at all is nothing to say, and an unreadable document is Inconclusive,
never an absence (rule 8).

"The same channel" is the same host and path, a trailing slash aside, named
either absolutely or as the bare path relative to the server the document is
served from -- which is how an OpenAPI `paths` key and most of llms.txt name
things. A longer path (`/ws/build-it-better-v2`, `/ws/build-it-better/admin`)
or the same path on another host is not it.

SAFE. Four GETs and no websocket: opening one would take this outside the
transport that classifies every other call we make, and that is a decision
about the safety model rather than a line in a check.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

# Pages that advertise a live channel to a reader.
PAGES = ("/build-it-better/api", "/build-it-better")

# Everything a machine reads to learn what this platform serves.
DOCUMENTS = ("/llms.txt", "/.well-known/mcp.json", "/openapi-public.json")

SOCKET = re.compile(r"wss?://[A-Za-z0-9.-]+/ws/[A-Za-z0-9/_-]+")


def sockets_in(text: str) -> set[str]:
    """Every websocket URL a body names, trailing punctuation removed.

    llms.txt writes them inside backticks and the HTML inside quotes, so the
    captured tail is stripped rather than trusted -- an earlier check in this
    repository nearly sent the vendor a field name that a `<code>` tag had
    glued to it.
    """
    return {m.group(0).rstrip("`'\"),.") for m in SOCKET.finditer(text or "")}


# What may follow a path that is the whole path: one optional slash, then
# anything that cannot continue it. A full stop ends a sentence, not a path.
_ENDS = r"/?(?![A-Za-z0-9_~/-])"


def names_socket(body: str, url: str, server_host: str | None) -> bool:
    """Does this document name the channel at `url`?

    Until the deep pass of 2026-09-21 (A12) the page's absolute URL had to be
    a substring of the body, so a page writing the URL with a trailing slash,
    or a document naming `/ws/build-it-better` relative to its own server,
    read as a channel named nowhere -- and that sentence goes to them.
    """
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    if not path:
        return False
    if re.search(r"\b[A-Za-z][A-Za-z0-9+.-]*://" + re.escape(parts.netloc)
                 + re.escape(path) + _ENDS, body or ""):
        return True
    # A bare path names a channel on the server the document came from, and
    # on no other: a socket on another host is not named by it.
    if not server_host or parts.hostname != server_host:
        return False
    return re.search(r"(?<![A-Za-z0-9._~/:-])" + re.escape(path) + _ENDS,
                     body or "") is not None


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_socket_a_page_advertises_is_named_where_a_machine_reads(rest_anon):
    """Every live channel on a page is findable in at least one document."""
    advertised: dict[str, str] = {}
    for path in PAGES:
        page = rest_anon.get(path)
        if page.status_code != 200:
            continue
        for url in sockets_in(page.text):
            # One channel, however many slashes a page ends it with.
            advertised.setdefault(url.rstrip("/"), path)
    if not advertised:
        raise Inconclusive(
            f"no page of {', '.join(PAGES)} names a websocket, so there is no "
            f"advertised channel whose discoverability could be read")

    # Every document is fetched through this client, so its server is the
    # client's host.
    base = getattr(rest_anon, "base_url", None)
    server_host = getattr(base, "host", None) or None
    documented: dict[str, list[str]] = {}
    for path in DOCUMENTS:
        doc = rest_anon.get(path)
        if doc.status_code != 200:
            raise Inconclusive(
                f"{path} answered HTTP {doc.status_code}; a document we could "
                f"not read is not a document that omits something")
        body = doc.text or ""
        for url in advertised:
            if names_socket(body, url, server_host):
                documented.setdefault(url, []).append(path)

    hidden = sorted(url for url in advertised if url not in documented)
    conclude(Measurement(
        verdict="failed" if hidden else "passed",
        reason=(
            # "advertised", not "live". This check opens no socket -- its own
            # docstring says so in those words -- and the failure sentence
            # goes on their tracker, where "live" is a claim about their
            # server that no branch here measured. A stale wss URL left in a
            # page that the documents correctly omit would have been filed as
            # a channel they serve and do not.
            f"{len(hidden)} channel(s) are advertised to a reader on their "
            f"own pages and named in none of {', '.join(DOCUMENTS)}: "
            + "; ".join(f"{url} (on {advertised[url]})" for url in hidden)
            if hidden else
            f"all {len(advertised)} advertised channel(s) are named in a "
            f"machine-readable document: "
            + "; ".join(f"{url} in {', '.join(where)}"
                        for url, where in sorted(documented.items()))),
        left={"advertised": sorted(advertised), "undocumented": hidden},
        right={"undocumented": []},
        sources={"pages": list(PAGES), "documents": list(DOCUMENTS)}))
