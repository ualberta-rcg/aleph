"""bge-reranker-v2-m3 rerank gateway test (run inside the gateway pod).

Standard rerank (Template C) battery — the reference harness for reranker dirs.
The gateway exposes a Cohere/Jina-style `/v1/rerank` and translates it to the TEI
native `/rerank`. Covers:
  - WAKE/basic: {query, documents} -> sorted results with relevance scores.
  - top_n respected, scores descending + in [0,1], correct doc ranked #1 (relevance).
  - return_documents, model-echo.
  - Guardrails: chat on a rerank-only model -> 4xx; unknown model -> 404;
    catalog entry reports type=reranker.

Run:  cat models/bge-reranker-v2-m3/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "bge-reranker-v2-m3")
results = []

DOCS = [
    "Paris is the capital of France.",                 # index 0 — irrelevant
    "Deep learning is a subset of machine learning.",  # index 1 — relevant
    "I had pizza for lunch.",                          # index 2 — irrelevant
]


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def rerank(body):
    r = req("POST", "/v1/rerank", body)
    try:
        return r, r.json()
    except Exception:
        return r, {}

# ── 1. WAKE (retry through cold-start 503) + basic rerank ─────────────────────
def wake_basic():
    body = {"model": MODEL, "query": "What is deep learning?", "documents": DOCS}
    for attempt in range(72):
        r, d = rerank(body)
        if r.status_code == 200:
            res = d.get("results", [])
            ok = len(res) == len(DOCS) and "relevance_score" in res[0]
            record("PASS" if ok else "FAIL", 200, "WAKE + basic rerank",
                   f"attempts={attempt+1} n={len(res)} top_idx={res[0].get('index')}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + basic rerank", f"body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + basic rerank", "timed out waiting for warm model")

# ── Rerank feature battery ────────────────────────────────────────────────────
def top_n():
    r, d = rerank({"model": MODEL, "query": "deep learning", "documents": DOCS, "top_n": 2})
    res = d.get("results", [])
    record("PASS" if r.status_code == 200 and len(res) == 2 else "FAIL", r.status_code,
           "top_n=2", f"got={len(res)}")

def ordering():
    r, d = rerank({"model": MODEL, "query": "deep learning", "documents": DOCS})
    res = d.get("results", [])
    scores = [x.get("relevance_score", 0) for x in res]
    desc = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
    record("PASS" if r.status_code == 200 and desc else "FAIL", r.status_code,
           "scores descending", f"scores={[round(s,3) for s in scores]}")

def score_range():
    r, d = rerank({"model": MODEL, "query": "deep learning", "documents": DOCS})
    res = d.get("results", [])
    ok = r.status_code == 200 and all(0.0 <= x.get("relevance_score", -1) <= 1.0 for x in res)
    record("PASS" if ok else "FAIL", r.status_code, "scores in [0,1]",
           f"scores={[round(x.get('relevance_score',-1),3) for x in res]}")

def relevance():
    r, d = rerank({"model": MODEL, "query": "What is deep learning?", "documents": DOCS})
    res = d.get("results", [])
    top = res[0].get("index") if res else None
    record("PASS" if r.status_code == 200 and top == 1 else "FAIL", r.status_code,
           "relevance (top=deep-learning doc)", f"top_idx={top}")

def model_echo():
    r, d = rerank({"model": MODEL, "query": "q", "documents": ["a"]})
    record("PASS" if r.status_code == 200 and d.get("model") else "FAIL", r.status_code,
           "model echo", f"model={d.get('model')!r}")

def return_documents():
    r, d = rerank({"model": MODEL, "query": "deep learning", "documents": DOCS,
                   "return_documents": True})
    res = d.get("results", [])
    has_doc = bool(res and res[0].get("document"))
    record("PASS" if r.status_code == 200 and has_doc else "FAIL", r.status_code,
           "return_documents=true", f"sample={str(res[0].get('document'))[:40]!r}")

# ── Guardrails ────────────────────────────────────────────────────────────────
def guard_chat_rejected():
    r = req("POST", "/v1/chat/completions",
            {"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    # Gateway returns 404 (chat) / 424 (embed) for type-mismatch — any 4xx is a valid rejection.
    record("EXP" if 400 <= r.status_code < 500 else "FAIL", r.status_code,
           "Guard: chat on rerank-only", f"(expect 4xx rejection)")

def guard_embed_rejected():
    r = req("POST", "/v1/embeddings", {"model": MODEL, "input": "hi"})
    record("EXP" if 400 <= r.status_code < 500 else "FAIL", r.status_code,
           "Guard: embed on rerank-only", f"(expect 4xx rejection)")

def guard_badmodel():
    r = req("POST", "/v1/rerank", {"model": "fake-xyz", "query": "q", "documents": ["a"]})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code,
           "Guard: unknown model", str(r.text)[:60])

def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x.get("id") == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    t = m.get("type")
    record("PASS" if t in ("reranker", "rerank") else "FAIL", r.status_code,
           "Catalog entry", f"type={t} ctx={m.get('context_window')}")

# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True); print(f"{MODEL} rerank gateway test", flush=True)
print("=" * 66, flush=True)
for t in [wake_basic, top_n, ordering, score_range, relevance, model_echo,
          return_documents, guard_chat_rejected, guard_embed_rejected, guard_badmodel, catalog]:
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
