"""Record every GET the live /company app makes, signed out, once per entry path; nothing but GETs leaves.
Each response is saved under rec/http/<host>/<path>[__<query>] with its status and content type, for offline replay.
Usage: rec_live.py <rec dir>"""
import asyncio, hashlib, json, sys
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

REC = Path(sys.argv[1])
HTTP = REC / "http"
LOG = []


def key_for(url: str) -> Path:
    # (a short name: Windows refuses paths over 260 characters, and a font's URL alone is 120)
    u = urlsplit(url)
    return HTTP / u.netloc / hashlib.sha1((u.path + "?" + u.query).encode()).hexdigest()[:16]


async def handler(route):
    req = route.request
    if req.method != "GET":
        LOG.append({"abort": req.method, "url": req.url})
        return await route.abort()
    try:
        resp = await route.fetch()
    except Exception as e:  # noqa: BLE001
        LOG.append({"fail": str(e)[:200], "url": req.url})
        return await route.abort()
    body = await resp.body()
    k = key_for(req.url)
    k.parent.mkdir(parents=True, exist_ok=True)
    k.with_name(k.name + ".body").write_bytes(body)
    meta = {"url": req.url, "status": resp.status, "ct": resp.headers.get("content-type", ""), "len": len(body),
            "type": req.resource_type}
    k.with_name(k.name + ".meta").write_text(json.dumps(meta))
    LOG.append(meta)
    await route.fulfill(response=resp, body=body)


async def main():
    HTTP.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--enable-unsafe-webgpu", "--use-angle=d3d11"])
        ctx = await b.new_context(viewport={"width": 1536, "height": 730}, device_scale_factor=1.25)
        await ctx.route("**/*", handler)
        await ctx.route_web_socket("**/*", lambda ws: ws.close())
        for path in ["/company/app", "/company/app#universe", "/company/app?visit=14", "/company/app/builder"]:
            pg = await ctx.new_page()
            LOG.append({"page": path})
            await pg.goto("https://cymetica.com" + path, wait_until="load", timeout=60000)
            await pg.wait_for_timeout(20000)
            LOG.append({"page_end": path, "url_now": pg.url})
            await pg.close()
        await b.close()
    (REC / "log.json").write_text(json.dumps(LOG, indent=1))
    hosts = {}
    for m in LOG:
        if "len" in m:
            h = urlsplit(m["url"]).netloc
            hosts[h] = hosts.get(h, 0) + m["len"]
    print("aborted:", [m for m in LOG if "abort" in m][:20])
    print("failed:", [m for m in LOG if "fail" in m][:20])
    print("bytes by host:", hosts)
    print("pages:", [m for m in LOG if "page_end" in m])


asyncio.run(main())
