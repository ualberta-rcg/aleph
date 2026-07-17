"""Gateway test battery for molmim NIM.

Run inside the gateway pod:
  cat models/molmim/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "molmim")

ENDPOINT = "/v1/biology/nvidia/molmim/generate"
# Aspirin SMILES as seed
PAYLOAD = {
    "model": MODEL,
    "smi": "CC(=O)Oc1ccccc1C(=O)O",
    "num_molecules": 3,
    "algorithm": "CMA-ES",
    "property_name": "QED",
    "minimize": False,
    "particles": 5,
    "iterations": 1,
    "min_similarity": 0.3,
    "scaled_radius": 1.0
}
results = []


def req(method, path, body=None, timeout=600):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req("POST", ENDPOINT, PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + generate", f"attempts={attempt+1}")
            return
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + generate", f"body={r.text[:120]}")
        return
    record("FAIL", 503, "WAKE + generate", "timed out waiting for warm model")


def _smiles_list(d):
    # Response shape is not fully documented; try common keys.
    for key in ("generated_smiles", "smiles", "molecules", "sequences", "output"):
        v = d.get(key)
        if isinstance(v, list):
            return v
    return []


def shape():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SHAPE", f"body={r.text[:120]}"); return
    smiles = _smiles_list(r.json())
    ok = len(smiles) > 0
    record("PASS" if ok else "FAIL", r.status_code, "SHAPE",
           f"generated={len(smiles)}")


def sanity():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SANITY", f"body={r.text[:120]}"); return
    smiles = _smiles_list(r.json())
    first = smiles[0] if smiles else ""
    ok = isinstance(first, str) and len(first) > 0
    record("PASS" if ok else "FAIL", r.status_code, "SANITY",
           f"first_smiles_len={len(first) if ok else 0}")


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
