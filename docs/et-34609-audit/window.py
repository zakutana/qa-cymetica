"""All CurveBuy / CurveSell logs of chain 4663 for the radar's window, read-only, saved to window_logs.json.
python window.py <from_block> <to_block>"""
import json
import sys
from chain import rpc

BUY = "0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455"
SELL = "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df"

frm, to = int(sys.argv[1]), int(sys.argv[2])
out, a, step = [], frm, 5000
while a <= to:
    b = min(a + step - 1, to)
    try:
        got = rpc("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "topics": [[BUY, SELL]]}])
        out += got
        a = b + 1
        if len(got) < 2000 and step < 20000:
            step *= 2
    except Exception as e:  # noqa: BLE001
        if step <= 250:
            raise
        step //= 4
        print("narrow", step, str(e)[:100], flush=True)
json.dump(out, open("window_logs.json", "w"))
print("logs", len(out), "curves", len({l["address"] for l in out}), "blocks", frm, to)
