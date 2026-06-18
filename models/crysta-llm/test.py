"""crysta-llm custom generation test (run inside the gateway pod).

CrystaLLM (c-bone/CrystaLLM-pi_base, ~25M) generates crystal structures in CIF format
from a chemical formula. Custom (non-OpenAI) endpoint POST /v1/science/generate.
NOT a chat model: no tools / vision / meta / anthropic battery. Wake retries 503.

Run:  cat models/crysta-llm/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=crysta-llm python3 -
"""
import httpx, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "crysta-llm")
results = []


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def gen(body):
    r = req("POST", "/v1/science/generate", body)
    try:
        d = r.json()
    except Exception:
        d = {}
    return r, d


def wake():
    body = {"model": MODEL, "formula": "NaCl", "max_new_tokens": 300, "num_samples": 1, "temperature": 1.0}
    for attempt in range(90):
        r, d = gen(body)
        if r.status_code == 200:
            rec = d.get("record", "")
            record("PASS", 200, "WAKE + generate NaCl", f"attempts={attempt+1} keys={sorted(d.keys())} rec_len={len(str(rec))}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + generate NaCl", f"body={r.text[:120]}")
        return
    record("FAIL", 503, "WAKE + generate NaCl", "timed out")


def basic():
    r, d = gen({"model": MODEL, "formula": "LiFePO4", "max_new_tokens": 400, "num_samples": 1})
    rec = str(d.get("record", d.get("structures", "")))
    has_cif = ("data_" in rec) or ("cell" in rec.lower()) or ("_atom" in rec)
    record("PASS" if r.status_code == 200 and rec else "FAIL", r.status_code,
           "generate LiFePO4", f"len={len(rec)} cif-like={has_cif} {rec[:50]!r}")


def temperature():
    r_lo, _ = gen({"model": MODEL, "formula": "NaCl", "temperature": 0.2, "max_new_tokens": 200, "num_samples": 1})
    r_hi, _ = gen({"model": MODEL, "formula": "NaCl", "temperature": 1.5, "max_new_tokens": 200, "num_samples": 1})
    record("PASS" if r_lo.status_code == 200 and r_hi.status_code == 200 else "FAIL",
           r_lo.status_code, "temperature 0.2 / 1.5", f"lo={r_lo.status_code} hi={r_hi.status_code}")


def num_samples():
    r, d = gen({"model": MODEL, "formula": "MgO", "max_new_tokens": 200, "num_samples": 3})
    rec = d.get("record", "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "num_samples=3", f"keys={sorted(d.keys())} rec_len={len(str(rec))}")


def health():
    r = req("GET", "/health")
    record("PASS" if r.status_code == 200 else "EXP", r.status_code, "health", r.text[:40])


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    record("PASS", r.status_code, "Catalog entry", f"type={m.get('type')} domain={m.get('domain')}")


print("=" * 66, flush=True)
print(f"{MODEL} custom generation test", flush=True)
print("=" * 66, flush=True)
for t in [wake, basic, temperature, num_samples, health, catalog]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
e = sum(1 for x in results if x[0] == "EXP")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err of {len(results)}", flush=True)
