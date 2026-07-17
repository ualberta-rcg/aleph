"""Gateway test battery for openfold-3 NIM.

Run inside the gateway pod:
  cat models/openfold-3/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "openfold-3")

ENDPOINT = "/v1/biology/openfold/openfold3/predict"
# Short insulin A-chain-like sequence for a quick smoke test
SEQUENCE = "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
MSA_CSV = f"key,sequence\n-1,{SEQUENCE}"
PAYLOAD = {
    "model": MODEL,
    "inputs": [
        {
            "input_id": "test",
            "molecules": [
                {
                    "type": "protein",
                    "id": "A",
                    "sequence": SEQUENCE,
                    "msa": {
                        "main_db": {
                            "csv": {
                                "alignment": MSA_CSV,
                                "format": "csv"
                            }
                        }
                    }
                }
            ]
        }
    ],
    "diffusion_samples": 1,
    "output_format": "cif"
}
results = []


def req(method, path, body=None, timeout=600):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _structures(d):
    out = d.get("outputs", [])
    if not out:
        return []
    return out[0].get("structures_with_scores", [])


def wake():
    for attempt in range(72):
        r = req("POST", ENDPOINT, PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + predict", f"attempts={attempt+1}")
            return
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + predict", f"body={r.text[:120]}")
        return
    record("FAIL", 503, "WAKE + predict", "timed out waiting for warm model")


def shape():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SHAPE", f"body={r.text[:120]}"); return
    structs = _structures(r.json())
    ok = isinstance(structs, list) and len(structs) > 0
    record("PASS" if ok else "FAIL", r.status_code, "SHAPE",
           f"structures={len(structs)}")


def sanity():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SANITY", f"body={r.text[:120]}"); return
    structs = _structures(r.json())
    struct = structs[0] if structs else {}
    txt = struct.get("structure", "")
    conf = struct.get("confidence_score")
    ok = isinstance(txt, str) and txt.startswith("data_") and \
         isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0
    record("PASS" if ok else "FAIL", r.status_code, "SANITY",
           f"conf={conf} format={'cif' if ok else 'unknown'}")


def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    record("PASS", r.status_code, "Catalog entry", f"type={m.get('type')} endpoint={m.get('endpoint')}")


BATTERY = [wake, shape, sanity, catalog]

if __name__ == "__main__":
    print("=" * 66, flush=True)
    print(f"{MODEL} science test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    for t in BATTERY:
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:120])
    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
