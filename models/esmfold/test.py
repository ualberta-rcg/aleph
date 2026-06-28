"""esmfold structure test — POST /v1/structure {sequence} -> {pdb, plddt}.

Folds an amino-acid sequence to a 3D structure. Sanity: pdb non-empty + starts with ATOM/HEADER,
plddt in [0,100].
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=esmfold python3 models/esmfold/test.py
"""
import httpx, os, time, math

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "esmfold")
ENDPOINT = "/v1/structure"

# A real small protein sequence (ubiquitin N-terminus fragment, 30 aa).
SEQ = "MQIFVKTLTGKTITLEVEPSDTIENVKAK"
PAYLOAD = {"model": MODEL, "sequence": SEQ}
results = []


def req(body, timeout=200):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + fold", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + fold", f"unexpected body={r.text[:90]}"); return None
    record("FAIL", 503, "WAKE + fold", "timed out waiting for warm model"); return None


def shape(d):
    ok = {"pdb", "plddt"} <= set(d)
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())}")


def sanity(d):
    pdb = d.get("pdb", ""); plddt = d.get("plddt")
    ok = (isinstance(pdb, str) and len(pdb) > 100 and "ATOM" in pdb[:3000]  # real coordinate PDB
          and isinstance(plddt, (int, float)) and 0 <= plddt <= 100)
    record("PASS" if ok else "FAIL", 200, "SANITY", f"pdb_len={len(pdb)} plddt={plddt}")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} structure test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, model_echo, catalog):
            try:
                t(d) if t is not catalog else t()
            except Exception as e:
                record("ERR", 0, t.__name__, str(e)[:120])
    else:
        catalog()
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
