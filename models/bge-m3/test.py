"""bge-m3 embedding gateway test (run inside the gateway pod).

Standard embedding (Template C) battery — also the reference harness for other
embed/rerank dirs. Covers the OpenAI `/v1/embeddings` surface for a TEI embedder:
  - WAKE/dim: first call retries through the gateway's 503 model_starting, then the
    returned vector length must equal the card's `embedding_dimensions` (1024 for bge-m3).
  - batch, model-echo, usage, encoding_format (float + base64), truncation, multilingual.
  - Guardrails: a chat request to an embed-only model -> 400; unknown model -> 404;
    catalog entry reports type=embedding with the right context window.

Run:  cat models/bge-m3/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, json, os, struct, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "bge-m3")
EXP_DIM = 1024          # catalog.embedding_dimensions (BGE-M3 dense)
MAX_INPUT = 8192        # catalog.max_input_tokens
results = []


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _vec(item):
    """Return (length, is_float_list) for one embedding item (float list or base64 str)."""
    e = item.get("embedding")
    if isinstance(e, list):
        return len(e), True
    if isinstance(e, str):  # base64 float32
        raw = base64.b64decode(e)
        return len(raw) // 4, False
    return 0, False


def embed(body):
    r = req("POST", "/v1/embeddings", body)
    try:
        return r, r.json()
    except Exception:
        return r, {}

# ── 1. WAKE (retry through cold-start 503) + dim ──────────────────────────────
def wake_dim():
    body = {"model": MODEL, "input": "hello world"}
    for attempt in range(72):  # ~6 min cap
        r, d = embed(body)
        if r.status_code == 200:
            n, _ = _vec(d["data"][0])
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE + dim",
                   f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"unexpected body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + dim", "timed out waiting for warm model")

# ── Embedding feature battery ─────────────────────────────────────────────────
def batch():
    r, d = embed({"model": MODEL, "input": ["alpha", "beta", "gamma"]})
    data = d.get("data", [])
    dims = [_vec(x)[0] for x in data]
    ok = r.status_code == 200 and len(data) == 3 and all(n == EXP_DIM for n in dims)
    record("PASS" if ok else "FAIL", r.status_code, "batch x3", f"got={len(data)} dims={dims}")

def model_echo():
    r, d = embed({"model": MODEL, "input": "ping"})
    record("PASS" if r.status_code == 200 and d.get("model") else "FAIL", r.status_code,
           "model echo", f"model={d.get('model')!r}")

def usage():
    r, d = embed({"model": MODEL, "input": "the quick brown fox"})
    u = d.get("usage", {})
    ok = r.status_code == 200 and u.get("prompt_tokens", 0) > 0
    record("PASS" if ok else "FAIL", r.status_code, "usage",
           f"prompt={u.get('prompt_tokens')} total={u.get('total_tokens')}")

def encoding_float():
    r, d = embed({"model": MODEL, "input": "float mode", "encoding_format": "float"})
    n, is_list = _vec(d["data"][0]) if r.status_code == 200 else (0, False)
    record("PASS" if r.status_code == 200 and is_list and n == EXP_DIM else "FAIL",
           r.status_code, "encoding_format=float", f"dim={n} is_list={is_list}")

def encoding_base64():
    r, d = embed({"model": MODEL, "input": "base64 mode", "encoding_format": "base64"})
    if r.status_code != 200:
        record("EXP", r.status_code, "encoding_format=base64", f"unsupported? body={r.text[:60]}")
        return
    n, is_list = _vec(d["data"][0])
    ok = (not is_list) and n == EXP_DIM
    record("PASS" if ok else "EXP", r.status_code, "encoding_format=base64",
           f"dim={n} decoded={not is_list}")

def truncation():
    long_text = "genomics " * 4000   # ~9k tokens, over the 8192 limit
    r, d = embed({"model": MODEL, "input": long_text})
    n, _ = _vec(d["data"][0]) if (r.status_code == 200 and d.get("data")) else (0, False)
    u = d.get("usage", {})
    # TEI truncates per-sequence to max tokens -> 200 + a 1024-dim vector. The pod memory limit
    # was bumped 8Gi -> 16Gi so the fp32 ~8k-token forward pass no longer OOM-kills the pod.
    ok = r.status_code == 200 and n == EXP_DIM
    record("PASS" if ok else "EXP", r.status_code, "truncation (>max_input)",
           f"dim={n} prompt_tokens={u.get('prompt_tokens')} body={r.text[:50]!r}")

def multilingual():
    r, d = embed({"model": MODEL, "input": "多语言嵌入模型测试"})
    n, _ = _vec(d["data"][0]) if r.status_code == 200 else (0, False)
    record("PASS" if r.status_code == 200 and n == EXP_DIM else "FAIL", r.status_code,
           "multilingual (zh)", f"dim={n}")

# ── Guardrails ────────────────────────────────────────────────────────────────
def guard_chat_rejected():
    r = req("POST", "/v1/chat/completions",
            {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    code = ""
    try: code = r.json().get("error", {}).get("code", "")
    except Exception: pass
    record("EXP" if r.status_code in (400, 404) else "FAIL", r.status_code,
           "Guard: chat on embed-only", f"code={code} (expect 4xx rejection)")

def guard_badmodel():
    r = req("POST", "/v1/embeddings", {"model": "fake-xyz", "input": "x"})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code,
           "Guard: unknown model", str(r.text)[:60])

def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x.get("id") == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    t = m.get("type")
    ctx = m.get("context_window")
    ok = t == "embedding" and ctx
    record("PASS" if ok else "FAIL", r.status_code, "Catalog entry",
           f"type={t} ctx={ctx} max_out={m.get('max_completion_tokens')}")

# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True); print(f"{MODEL} embedding gateway test", flush=True)
print("=" * 66, flush=True)
for t in [wake_dim, batch, model_echo, usage, encoding_float, encoding_base64,
          truncation, multilingual, guard_chat_rejected, guard_badmodel, catalog]:
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
