"""Gateway test battery for genmol NIM.

Run inside the gateway pod:
  cat models/genmol/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "genmol")

ENDPOINT = "/v1/biology/nvidia/genmol/generate"
# Aspirin SMILES as seed
PAYLOAD = {
    "model": MODEL,
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "num_molecules": 3,
    "temperature": 1.0,
    "noise": 1.0,
    "step_size": 1,
    "scoring": "QED",
    "unique": False
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


def _molecules(d):
    for key in ("molecules", "smiles", "generated_smiles", "sequences", "output"):
        v = d.get(key)
        if isinstance(v, list):
            return v
    return []


def _first_smiles(mols):
    if not mols:
        return ""
    first = mols[0]
    if isinstance(first, dict):
        return first.get("smiles") or ""
    if isinstance(first, str):
        return first
    return ""


def shape():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SHAPE", f"body={r.text[:120]}"); return
    mols = _molecules(r.json())
    ok = len(mols) > 0
    record("PASS" if ok else "FAIL", r.status_code, "SHAPE",
           f"generated={len(mols)}")


def sanity():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SANITY", f"body={r.text[:120]}"); return
    first = _first_smiles(_molecules(r.json()))
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
