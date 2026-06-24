"""geneformer single-cell embedding gateway test.

Embedding (Template C) battery for a custom Geneformer server (NIH NCI, CPU).
Cell-level embeddings from single-cell gene expression (gene names + expression), via the domain
/v1/science/embed endpoint. Non-text (gene-expression) → does NOT expose OpenAI /v1/embeddings.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/geneformer/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/geneformer/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "geneformer")
EXP_DIM = 768  # geneformer-v2-104M hidden dim (V1-10M was 256); verified live 2026-06-20
results = []

# A handful of real gene symbols + expression values for a synthetic cell.
GENES = ["TP53", "BRCA1", "EGFR", "MYC", "CD4", "CD8A", "IL6", "TNF", "GAPDH", "ACTB",
         "FOXP3", "CD19", "CD3D", "CD3E", "IL2", "IFNG", "PRF1", "GZMB", "NCAM1", "MS4A1"]


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout, headers=_HEADERS)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


def cell(seed):
    # geneformer takes pre-tokenized gene_ids (int token IDs ranked by expression); the docstring's
    # {genes, expression} is aspirational. Use small ints (real embedding, biologically arbitrary).
    rng = seed & 0x7FFFFFFF
    ids = []
    for _ in range(len(GENES)):
        rng = (1103515245 * rng + 12345) & 0x7FFFFFFF
        ids.append((rng % 2000) + 1)  # token IDs in [1,2000]
    return {"gene_ids": ids}


def _vec(d):
    e = d.get("embeddings")
    if isinstance(e, list) and e:
        return e[0] if isinstance(e[0], list) else list(e)
    return []


def wake_dim():
    for attempt in range(72):
        r, d = embed(cell(1))
        if r is not None and r.status_code == 200:
            v = _vec(d); n = len(v)
            record("PASS" if n and n == d.get("embedding_dim", n) else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={n} embedding_dim={d.get('embedding_dim')}")
            return n
        if r is None or r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return 0
    record("FAIL", 0, "WAKE + dim", "timed out"); return 0


def checks(dim):
    r, d = embed(cell(2)); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == dim and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")
    _, d1 = embed(cell(10)); _, d2 = embed(cell(20))
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f}")
    b = cell(30); _, d1 = embed(b); _, d2 = embed(b)
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")
    r, d = embed(cell(40))
    record("PASS" if r.status_code == 200 and d.get("model") == "geneformer" else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")
    r, _ = embed({})
    record("PASS" if r is not None and 400 <= r.status_code < 600 else "FAIL",
           r.status_code if r else 0, "malformed handled", f"status={r.status_code if r else 'err'}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    dim = wake_dim()
    if dim: checks(dim)
    raise SystemExit(summary())
