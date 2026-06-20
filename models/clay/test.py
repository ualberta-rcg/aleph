"""clay geospatial embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom Clay MAE server (Clay Foundation large, CPU).
CLS embeddings of any-band satellite image patches, via the domain /v1/science/embed endpoint.
Non-text (pixels+waves input) → does NOT expose OpenAI /v1/embeddings.

Run:  cat models/clay/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "clay")
# Clay large encoder CLS dim; confirmed from the response `embedding_dim` if it differs.
EXP_DIM = 1024
BANDS = 4  # synthetic B/G/R/NIR
H = W = 32
WAVES = [0.49, 0.56, 0.665, 0.84]  # µm
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout)
    try: return r, r.json()
    except Exception: return r, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


class _LCG:
    def __init__(self, s): self.s = s & 0x7FFFFFFF
    def nxt(self):
        self.s = (1103515245*self.s + 12345) & 0x7FFFFFFF
        return round(((self.s % 3000)/1000.0), 3)  # 0-3 reflectance-ish


def rand_cube(seed, bands=BANDS, h=H, w=W):
    rng = _LCG(seed)
    return [[[rng.nxt() for _ in range(w)] for _ in range(h)] for _ in range(bands)]


def _vec(d): return d.get("embeddings") or d.get("cls_embedding") or []


def wake_dim():
    cube = rand_cube(1)
    for attempt in range(72):
        r, d = embed({"pixels": cube, "waves": WAVES, "gsd": 10.0})
        if r.status_code == 200:
            n = len(_vec(d)); rd = d.get("embedding_dim", n)
            record("PASS" if n and n == rd else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={n} embedding_dim={rd}")
            return n
        if r.status_code in (503, 502, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return 0
    record("FAIL", 0, "WAKE + dim", "timed out"); return 0


def checks(dim):
    # non-zero
    r, d = embed({"pixels": rand_cube(2), "waves": WAVES}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == dim and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")
    # distinct
    _, d1 = embed({"pixels": rand_cube(10), "waves": WAVES}); _, d2 = embed({"pixels": rand_cube(20), "waves": WAVES})
    e1, e2 = _vec(d1), _vec(d2)
    c = _cos(e1, e2) if e1 and e2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f}")
    # deterministic
    cube = rand_cube(30); _, d1 = embed({"pixels": cube, "waves": WAVES}); _, d2 = embed({"pixels": cube, "waves": WAVES})
    e1, e2 = _vec(d1), _vec(d2); c = _cos(e1, e2) if e1 and e2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")
    # echo
    r, d = embed({"pixels": rand_cube(40), "waves": WAVES})
    record("PASS" if r.status_code == 200 and d.get("model") == MODEL else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")
    # malformed
    r, _ = embed({})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    dim = wake_dim()
    if dim: checks(dim)
    raise SystemExit(summary())
