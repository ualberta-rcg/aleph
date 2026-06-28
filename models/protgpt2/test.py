"""protgpt2 custom generation test.

ProtGPT2 (nferruz/ProtGPT2, ~1.5B) generates novel protein sequences (amino-acid strings)
from scratch or a partial prompt. Custom (non-OpenAI) endpoint POST /v1/completions.
NOT a chat model: no tools / vision / meta / anthropic battery. Wake retries 503.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> MODEL=protgpt2 python3 models/protgpt2/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/protgpt2/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=protgpt2 python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "protgpt2")
results = []
AA = set("ACDEFGHIKLMNPQRSTVWY*X")


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def gen(body):
    r = req("POST", "/v1/completions", body)
    try:
        d = r.json()
    except Exception:
        d = {}
    return r, d


def _seqs(d):
    if isinstance(d.get("sequences"), list):
        return d["sequences"]
    if isinstance(d.get("choices"), list):
        return [c.get("text", "") for c in d["choices"]]
    if isinstance(d.get("sequence"), str):
        return [d["sequence"]]
    return []


def wake():
    body = {"model": MODEL, "prompt": "M", "max_tokens": 100, "temperature": 0.7, "num_sequences": 1}
    for attempt in range(90):
        r, d = gen(body)
        if r.status_code == 200:
            seqs = _seqs(d)
            record("PASS", 200, "WAKE + generate", f"attempts={attempt+1} keys={sorted(d.keys())} seqs={len(seqs)}")
            return d
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + generate", f"body={r.text[:120]}")
        return None
    record("FAIL", 503, "WAKE + generate", "timed out")
    return None


def basic():
    r, d = gen({"model": MODEL, "prompt": "M", "max_tokens": 120, "temperature": 0.7, "num_sequences": 1})
    seqs = _seqs(d)
    sample = str(seqs[0]) if seqs else ""
    aa_frac = (sum(ch in AA for ch in sample) / len(sample)) if sample else 0
    record("PASS" if r.status_code == 200 and seqs else "FAIL", r.status_code,
           "generate protein", f"len={len(sample)} aa_frac={aa_frac:.2f} {sample[:40]!r}")


def continue_prompt():
    r, d = gen({"model": MODEL, "prompt": "MKLV", "max_tokens": 80, "temperature": 0.7, "num_sequences": 1})
    seqs = _seqs(d)
    sample = str(seqs[0]) if seqs else ""
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "continue from prompt", f"starts_mk={str(sample).startswith('MKLV') or 'MKLV' in str(d)} {sample[:40]!r}")


def num_sequences():
    r, d = gen({"model": MODEL, "prompt": "M", "max_tokens": 80, "temperature": 1.0, "num_sequences": 3})
    seqs = _seqs(d)
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "num_sequences=3", f"returned={len(seqs)}")


def temperature():
    r_lo, _ = gen({"model": MODEL, "prompt": "M", "temperature": 0.2, "max_tokens": 80, "num_sequences": 1})
    r_hi, _ = gen({"model": MODEL, "prompt": "M", "temperature": 1.5, "max_tokens": 80, "num_sequences": 1})
    record("PASS" if r_lo.status_code == 200 and r_hi.status_code == 200 else "FAIL",
           r_lo.status_code, "temperature 0.2 / 1.5", f"lo={r_lo.status_code} hi={r_hi.status_code}")


def health():
    r = req("GET", "/health")
    record("PASS" if r.status_code == 200 else "EXP", r.status_code, "health", r.text[:40])


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", timeout=30, headers=_HEADERS, verify=_VERIFY)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    record("PASS", r.status_code, "Catalog entry", f"type={m.get('type')} domain={m.get('domain')}")


print("=" * 66, flush=True)
print(f"{MODEL} custom generation test", flush=True)
print("=" * 66, flush=True)
for t in [wake, basic, continue_prompt, num_sequences, temperature, health, catalog]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
e = sum(1 for x in results if x[0] == "EXP")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err of {len(results)}", flush=True)
