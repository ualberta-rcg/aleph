"""bge-small (bge-small-en-v1.5) embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a TEI/CPU embedder — 384-dim English embeddings.
Covers WAKE/dim, batch, model-echo, usage, distinctness, encoding_format (float+base64),
truncation (>512 tokens, safe for this small model), guardrails, catalog.

Run:  cat models/bge-small/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, json, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "bge-small")
EXP_DIM = 384
MAX_INPUT = 512
results = []


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout)


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
    if isinstance(e, list):
        return len(e)
    if isinstance(e, str):  # base64 float32
        return len(base64.b64decode(e)) // 4
    return 0


def _cos(a, b):
    import math
    da = math.sqrt(sum(x * x for x in a)); db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0

T1 = "Machine learning models learn patterns from data."
T2 = "The weather forecast predicts rain tomorrow."
T3 = "Photosynthesis converts sunlight into chemical energy."

# ── 1. WAKE (retry through cold-start 503) + dim ──────────────────────────────
def wake_dim():
    for attempt in range(72):
        r, d = embed({"model": MODEL, "input": T1})
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
    r, d = embed({"model": MODEL, "input": [T1, T2, T3]})
    data = d.get("data", [])
    dims = [_dim(x) for x in data]
    ok = r.status_code == 200 and len(data) == 3 and all(n == EXP_DIM for n in dims)
    record("PASS" if ok else "FAIL", r.status_code, "batch x3", f"got={len(data)} dims={dims}")

def model_echo():
    r, d = embed({"model": MODEL, "input": T1})
    record("PASS" if r.status_code == 200 and d.get("model") else "FAIL", r.status_code,
           "model echo", f"model={d.get('model')!r}")

def usage():
    r, d = embed({"model": MODEL, "input": T1})
    u = d.get("usage", {})
    record("PASS" if r.status_code == 200 and u.get("prompt_tokens", 0) > 0 else "FAIL",
           r.status_code, "usage", f"prompt={u.get('prompt_tokens')} total={u.get('total_tokens')}")

def distinct():
    r, d = embed({"model": MODEL, "input": [T1, T2]})
    data = d.get("data", [])
    if r.status_code == 200 and len(data) == 2:
        sim = _cos(data[0]["embedding"], data[1]["embedding"])
        record("PASS" if sim < 0.99 else "FAIL", r.status_code, "distinctness (cos<0.99)", f"cos={sim:.4f}")
    else:
        record("FAIL", r.status_code, "distinctness", f"got={len(data)}")

def encoding_float():
    r, d = embed({"model": MODEL, "input": T1, "encoding_format": "float"})
    n = _dim(d["data"][0]) if r.status_code == 200 else 0
    record("PASS" if r.status_code == 200 and n == EXP_DIM else "FAIL", r.status_code,
           "encoding_format=float", f"dim={n}")

def encoding_base64():
    r, d = embed({"model": MODEL, "input": T1, "encoding_format": "base64"})
    if r.status_code != 200:
        record("EXP", r.status_code, "encoding_format=base64", f"unsupported? body={r.text[:60]}")
        return
    e = d["data"][0].get("embedding")
    n = _dim(d["data"][0]); ok = isinstance(e, str) and n == EXP_DIM
    record("PASS" if ok else "EXP", r.status_code, "encoding_format=base64", f"dim={n} decoded={isinstance(e,str)}")

def truncation():
    long_text = "science research data " * 200   # >512 tokens
    r, d = embed({"model": MODEL, "input": long_text})
    n = _dim(d["data"][0]) if (r.status_code == 200 and d.get("data")) else 0
    record("PASS" if r.status_code == 200 and n == EXP_DIM else "EXP", r.status_code,
           "truncation (>512 tokens)", f"dim={n} body={r.text[:50]!r}")

def guard_chat_rejected():
    r = req("POST", "/v1/chat/completions",
            {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    record("EXP" if 400 <= r.status_code < 500 else "FAIL", r.status_code,
           "Guard: chat on embed-only", "(expect 4xx rejection)")

def guard_badmodel():
    r = req("POST", "/v1/embeddings", {"model": "fake-xyz", "input": T1})
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
print("=" * 66, flush=True); print(f"{MODEL} embedding gateway test", flush=True)
print("=" * 66, flush=True)
for t in [wake_dim, batch, model_echo, usage, distinct, encoding_float, encoding_base64,
          truncation, guard_chat_rejected, guard_badmodel, catalog]:
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
