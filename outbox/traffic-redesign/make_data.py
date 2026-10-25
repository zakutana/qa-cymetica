"""Bundle the three live snapshots into data.js, so the mockup opens from disk (file:// cannot fetch).

snapshot/public-14.json    GET /api/v1/traffic/public?days=14     2026-10-25T23:17Z, anonymous
snapshot/activity-14.json  GET /api/v1/traffic/activity?days=14   2026-10-25T23:17Z, anonymous
snapshot/mine-14.json      GET /api/v1/traffic/mine?days=14       2026-10-25T23:34Z, the operator's session

Every figure the mockup draws comes from these files; the page computes sums and shares from them, never types
a number of its own.
"""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
snap = {name: json.loads((here / "snapshot" / f"{name}-14.json").read_text(encoding="utf-8"))
        for name in ("public", "activity", "mine")}
(here / "data.js").write_text("window.SNAP = " + json.dumps(snap, ensure_ascii=False) + ";\n", encoding="utf-8")
print("data.js", sum(len(json.dumps(v)) for v in snap.values()), "bytes of snapshot")
