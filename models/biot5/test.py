"""biot5 test — POST /v1/science/generate {task, input}.

BioT5 cross-modal T5: mol2text (SMILES→description) + text2mol (description→SMILES). Sanity:
non-empty text output. Tests both directions.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=biot5 python3 models/biot5/test.py
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "biot5")
ENDPOINT = "/v1/science/generate"
results = []


def gen(task, inp, timeout=200):
    body = {"model": MODEL, "task": task, "input": inp}
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    # wake on mol2text (aspirin SMILES -> text)
    for attempt in range(72):
        r = gen("mol2text", "CC(=O)OC1=CC=CC=C1C(=O)O")
        if r.status_code == 200:
            record("PASS", 200, "WAKE + mol2text", f"attempts={attempt+1}"); return
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + mol2text", f"unexpected body={r.text[:120]}"); return
    record("FAIL", 503, "WAKE + mol2text", "timed out waiting for warm model")


def mol2text():
    r = gen("mol2text", "CC(=O)OC1=CC=CC=C1C(=O)O")  # aspirin
    d = r.json() if r.status_code == 200 else {}
    out = d.get("generated") or d.get("output") or d.get("text") or ""
    ok = r.status_code == 200 and len(str(out).strip()) > 5
    record("PASS" if ok else "FAIL", r.status_code, "mol2text (SMILES→text)", f"out[:60]={str(out)[:60]!r}")


def text2mol():
    r = gen("text2mol", "The molecule is a common analgesic drug known as aspirin.", timeout=250)
    d = r.json() if r.status_code == 200 else {}
    smi = d.get("smiles") or d.get("selfies") or ""
    ok = r.status_code == 200 and isinstance(smi, str) and len(smi) > 5
    record("PASS" if ok else "FAIL", r.status_code, "text2mol (text→SMILES)", f"smiles={str(smi)[:50]!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} generate test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    for t in (wake, mol2text, text2mol, catalog):
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:120])
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
