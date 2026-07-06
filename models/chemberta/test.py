"""chemberta (chemberta-125m) SMILES-embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom transformers server (ChemBERTa, CPU).
768-dim mean-pooled embeddings of chemical SMILES strings.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/chemberta/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/chemberta/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "chemberta-125m")
EXP_DIM = 768
MAX_INPUT = 512
results = []

S1 = "CC(=O)Oc1ccccc1C(=O)O"          # aspirin
S2 = "CC(C)CC1NC(=O)C(N)CCC(=O)O"     # a peptide-ish
S3 = "c1ccccc1"                        # benzene


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body):
    r = req("POST", "/v1/embeddings", body)
    try:
        return r, r.json()
    except Exception:
        return r, {}


def _dim(item):
    e = item.get("embedding")
    return len(e) if isinstance(e, list) else 0


def _cos(a, b):
    import math
    da = math.sqrt(sum(x * x for x in a)); db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0

# ── 1. WAKE (retry through cold-start 503) + dim ──────────────────────────────
def wake_dim():
    for attempt in range(72):
        r, d = embed({"model": MODEL, "input": S1})
        if r.status_code == 200:
            n = _dim(d["data"][0])
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE + dim",
                   f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + dim", "timed out waiting for warm model")

def batch():
    r, d = embed({"model": MODEL, "input": [S1, S2, S3]})
    data = d.get("data", [])
    dims = [_dim(x) for x in data]
    ok = r.status_code == 200 and len(data) == 3 and all(n == EXP_DIM for n in dims)
    record("PASS" if ok else "FAIL", r.status_code, "batch x3", f"got={len(data)} dims={dims}")

def model_echo():
    r, d = embed({"model": MODEL, "input": S1})
    record("PASS" if r.status_code == 200 and d.get("model") else "FAIL", r.status_code,
           "model echo", f"model={d.get('model')!r}")

def usage():
    r, d = embed({"model": MODEL, "input": S1})
    u = d.get("usage", {})
    record("PASS" if r.status_code == 200 and u.get("prompt_tokens", 0) > 0 else "FAIL",
           r.status_code, "usage", f"prompt={u.get('prompt_tokens')} total={u.get('total_tokens')}")

def distinct():
    r, d = embed({"model": MODEL, "input": [S1, S3]})
    data = d.get("data", [])
    if r.status_code == 200 and len(data) == 2:
        sim = _cos(data[0]["embedding"], data[1]["embedding"])
        record("PASS" if sim < 0.99 else "FAIL", r.status_code, "distinctness (cos<0.99)", f"cos={sim:.4f}")
    else:
        record("FAIL", r.status_code, "distinctness", f"got={len(data)}")

def encoding_float():
    r, d = embed({"model": MODEL, "input": S1, "encoding_format": "float"})
    n = _dim(d["data"][0]) if r.status_code == 200 else 0
    record("PASS" if r.status_code == 200 and n == EXP_DIM else "FAIL", r.status_code,
           "encoding_format=float", f"dim={n}")

def truncation():
    long_smiles = "CCO" * 400   # >512 tokens
    r, d = embed({"model": MODEL, "input": long_smiles})
    n = _dim(d["data"][0]) if (r.status_code == 200 and d.get("data")) else 0
    record("PASS" if r.status_code == 200 and n == EXP_DIM else "EXP", r.status_code,
           "truncation (>512 tokens)", f"dim={n} body={r.text[:50]!r}")

def guard_chat_rejected():
    r = req("POST", "/v1/chat/completions",
            {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    record("EXP" if 400 <= r.status_code < 500 else "FAIL", r.status_code,
           "Guard: chat on embed-only", "(expect 4xx rejection)")

def guard_badmodel():
    r = req("POST", "/v1/embeddings", {"model": "fake-xyz", "input": S1})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code,
           "Guard: unknown model", str(r.text)[:60])

def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x.get("id") == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", f"{MODEL} not found"); return
    t = m.get("type"); ctx = m.get("context_window")
    record("PASS" if t == "embedding" and ctx == MAX_INPUT else "FAIL", r.status_code,
           "Catalog entry", f"type={t} ctx={ctx}")

# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True); print(f"{MODEL} SMILES-embedding gateway test", flush=True)
print("=" * 66, flush=True)
for t in [wake_dim, batch, model_echo, usage, distinct, encoding_float, truncation,
          guard_chat_rejected, guard_badmodel, catalog]:
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
