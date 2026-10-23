"""Copy one recorded response body out of the recording, by its URL.  python recget.py <rec> <url> <out file>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from perf import key_for  # noqa: E402

rec, url, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
k = key_for(rec, url)
body = k.with_name(k.name + ".body")
out.write_bytes(body.read_bytes())
print(out, out.stat().st_size)
