"""ligandmpnn design test — POST /v1/design {pdb, num_sequences, model_type}.

Designs amino-acid sequences for a protein backbone (crambin/1CRN from test_protein.pdb). Sanity:
sequences non-empty, each is uppercase amino-acid letters, returncode 0.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=ligandmpnn python3 models/ligandmpnn/test.py
"""
import httpx, os, time, re

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "ligandmpnn")
ENDPOINT = "/v1/design"
_HERE = os.path.dirname(os.path.abspath(__file__))
PDB = open(os.path.join(_HERE, "test_protein.pdb")).read()  # crambin (1CRN) backbone
PAYLOAD = {"model": MODEL, "pdb": PDB, "num_sequences": 2, "temperature": 0.1, "model_type": "protein_mpnn"}
_AA = set("ACDEFGHIKLMNPQRSTVWY")
results = []


def req(body, timeout=300):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + design", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + design", f"unexpected body={r.text[:160]}"); return None
    record("FAIL", 503, "WAKE + design", "timed out waiting for warm model"); return None


def shape(d):
    ok = isinstance(d.get("sequences"), list) and d.get("returncode") == 0
    record("PASS" if ok else "FAIL", 200, "SHAPE",
           f"returncode={d.get('returncode')} n_seqs={len(d.get('sequences') or [])}")


def sanity(d):
    seqs = d.get("sequences") or []
    ok = len(seqs) >= 1 and all(set(s.get("sequence", "")) <= _AA and len(s.get("sequence", "")) > 0
                                for s in seqs)
    rec = seqs[0]["sequence"][:30] if seqs else ""
    record("PASS" if ok else "FAIL", 200, "SANITY", f"n_seqs={len(seqs)} first_seq[:30]={rec!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} design test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, catalog):
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
