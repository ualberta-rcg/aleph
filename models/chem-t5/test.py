"""chem-t5 test — POST /v1/science/generate {task, input}.

Multitask chemistry T5: caption (SMILES→text), forward_synthesis (reaction→product),
retrosynthesis (product→reaction). Sanity: non-empty `output`.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=chem-t5 python3 models/chem-t5/test.py
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "chem-t5")
ENDPOINT = "/v1/science/generate"
results = []


def gen(task, inp, timeout=200):
    return httpx.post(f"{G}{ENDPOINT}", json={"model": MODEL, "task": task, "input": inp},
                      timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = gen("caption", "CC(=O)OC1=CC=CC=C1C(=O)O")  # aspirin
        if r.status_code == 200:
            record("PASS", 200, "WAKE + caption", f"attempts={attempt+1}"); return
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + caption", f"unexpected body={r.text[:120]}"); return
    record("FAIL", 503, "WAKE + caption", "timed out waiting for warm model")


def _check(task, inp, label):
    r = gen(task, inp)
    d = r.json() if r.status_code == 200 else {}
    out = d.get("output", "")
    ok = r.status_code == 200 and isinstance(out, str) and len(out.strip()) > 0
    record("PASS" if ok else "FAIL", r.status_code, label, f"output={str(out)[:60]!r}")


def caption(): _check("caption", "CC(=O)OC1=CC=CC=C1C(=O)O", "caption (aspirin SMILES→text)")
def fwd_syn(): _check("forward_synthesis", "CCO.CC(=O)O>>", "forward_synthesis (reaction→product)")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} generate test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    for t in (wake, caption, fwd_syn, catalog):
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:120])
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
