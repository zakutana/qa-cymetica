"""Bundle the live snapshots into data.js, so the mockup opens from disk (file:// cannot fetch).

snapshot/public-14.json    GET /api/v1/traffic/public?days=14     anonymous
snapshot/public-30.json    GET /api/v1/traffic/public?days=30     anonymous (the Apps tab compares its 30 days with it)
snapshot/activity-14.json  GET /api/v1/traffic/activity?days=14   anonymous
snapshot/mine-14.json      GET /api/v1/traffic/mine?days=14       the operator's session
snapshot/app-usage.json    GET /api/v1/app-usage                  anonymous, 30 days

All read on 2026-10-26 after Cymetica's /traffic fixes. Every figure the mockup draws comes from these files; the
page computes sums and shares from them, never types a number of its own.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

here = Path(__file__).resolve().parent
files = {"public": "public-14.json", "public30": "public-30.json", "activity": "activity-14.json",
         "mine": "mine-14.json", "apps": "app-usage.json"}
snap = {key: json.loads((here / "snapshot" / name).read_text(encoding="utf-8")) for key, name in files.items()}
read = datetime.fromtimestamp((here / "snapshot" / files["apps"]).stat().st_mtime, timezone.utc)
snap["apps"]["_read"] = read.strftime("%Y-%m-%d %H:%M UTC")
(here / "data.js").write_text("window.SNAP = " + json.dumps(snap, ensure_ascii=False) + ";\n", encoding="utf-8")
print("data.js", sum(len(json.dumps(v)) for v in snap.values()), "bytes of snapshot")
