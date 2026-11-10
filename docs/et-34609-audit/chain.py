"""Read-only JSON-RPC reads of Robinhood Chain (4663): eth_getLogs / eth_getBlockByNumber only. Nothing is signed or sent."""
import json
import time
import urllib.request

RPC = "https://rpc.mainnet.chain.robinhood.com"
READS = {"eth_chainId", "eth_blockNumber", "eth_getLogs", "eth_getBlockByNumber", "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getBalance", "eth_getCode", "eth_call"}


def rpc(method, params):
    assert method in READS, method
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"content-type": "application/json", "user-agent": "qa-cymetica audit (read-only)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            if "error" in d:
                raise RuntimeError(d["error"])
            return d["result"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def logs(address, frm, to, step=20000):
    out = []
    a = frm
    while a <= to:
        b = min(a + step - 1, to)
        try:
            out += rpc("eth_getLogs", [{"address": address, "fromBlock": hex(a), "toBlock": hex(b)}])
            a = b + 1
        except Exception as e:  # noqa: BLE001
            if step <= 500:
                raise
            step //= 4
            print("  narrowing to", step, str(e)[:120])
    return out


if __name__ == "__main__":
    import sys
    head = int(rpc("eth_blockNumber", []), 16)
    blk = rpc("eth_getBlockByNumber", [hex(head), False])
    old = rpc("eth_getBlockByNumber", [hex(head - 10000), False])
    print("head", head, "ts", int(blk["timestamp"], 16), "block time", (int(blk["timestamp"], 16) - int(old["timestamp"], 16)) / 10000)
    if len(sys.argv) > 2:
        ls = logs(sys.argv[1], int(sys.argv[2]), head)
        json.dump(ls, open(sys.argv[3], "w"))
        from collections import Counter
        print(len(ls), Counter(l["topics"][0] for l in ls))
        print(json.dumps(ls[0], indent=0))
