"""One authenticated GET of our own office (company 14), through the pipeline's own client, saved for offline replay
(perf.py's "ours" place). Nothing is sent but this read; the key never leaves the client and is not written anywhere.
  python rec_office.py <rec dir>/auth"""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]   # outbox/company-perf/harness -> the repository
sys.path.insert(0, str(REPO))
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
load_dotenv()
install_client_guard()
client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=60.0)
token = CURRENT_TIER.set(SafetyTier.SAFE)
try:
    for name, url in [("office", "https://cymetica.com/api/v1/company/office"),
                      ("me", "https://cymetica.com/auth/me")]:
        r = client.get(url)
        print(name, r.status_code, len(r.content))
        (out / f"{name}.json").write_bytes(r.content)
        (out / f"{name}.status").write_text(str(r.status_code))
finally:
    CURRENT_TIER.reset(token)
    client.close()
o = json.loads((out / "office.json").read_text(encoding="utf-8"))
print("office keys", sorted(o.keys())[:40] if isinstance(o, dict) else type(o))
