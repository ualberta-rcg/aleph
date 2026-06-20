"""satmae satellite-image embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom MAE server (MVRL SatMAE ViT-Large, CPU).
1024-dim [CLS] embeddings of RGB satellite image patches, via the domain /v1/science/embed
endpoint. Non-text (image input) → does NOT expose OpenAI /v1/embeddings.

Run:  cat models/satmae/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "satmae")
EXP_DIM = 1024
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout)
    try:
        return r, r.json()
    except Exception:
        return r, {}


def _cos(a, b):
    da = math.sqrt(sum(x * x for x in a)); db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0


class _LCG:
    def __init__(self, seed): self.s = seed & 0x7FFFFFFF
    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s % 256  # 0-255 RGB


def rand_img(seed, h=96, w=96):
    rng = _LCG(seed)
    return [[[rng.next() for _ in range(3)] for _ in range(w)] for _ in range(h)]


def _dim(d):
    e = d.get("embeddings") or d.get("cls_embedding") or []
    return len(e) if isinstance(e, list) else 0


def _vec(d):
    return d.get("embeddings") or d.get("cls_embedding") or []


def wake_dim():
    img = rand_img(1)
    for attempt in range(72):
        r, d = embed({"image": img})
        if r.status_code == 200:
            n = _dim(d)
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code in (503, 502, 404):
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE + dim", "timed out")


def nonzero():
    r, d = embed({"image": rand_img(2)})
    v = _vec(d)
    ok = r.status_code == 200 and len(v) == EXP_DIM and not all(x == 0 for x in v)
    record("PASS" if ok else "FAIL", r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")


def distinct():
    _, d1 = embed({"image": rand_img(10)})
    _, d2 = embed({"image": rand_img(20)})
    e1, e2 = _vec(d1), _vec(d2)
    if not e1 or not e2:
        record("FAIL", 0, "distinctness", "missing"); return
    c = _cos(e1, e2)
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(img_a,img_b)={c:.5f}")


def deterministic():
    img = rand_img(30)
    _, d1 = embed({"image": img}); _, d2 = embed({"image": img})
    e1, e2 = _vec(d1), _vec(d2)
    if not e1 or not e2:
        record("FAIL", 0, "deterministic", "missing"); return
    c = _cos(e1, e2)
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(img,img)={c:.5f}")


def model_echo():
    r, d = embed({"image": rand_img(40)})
    ok = r.status_code == 200 and d.get("model") == MODEL
    record("PASS" if ok else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")


def malformed():
    r, _ = embed({})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    wake_dim(); nonzero(); distinct(); deterministic(); model_echo(); malformed()
    raise SystemExit(summary())
