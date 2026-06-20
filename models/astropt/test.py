"""astropt galaxy-image embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom AstroPT server (UniverseTBD, GPU).
Outputs PATCH-level latent embeddings [N, 512] (2D, not a single vector), via the domain
/v1/science/embed endpoint. Non-text (galaxy image) → does NOT expose OpenAI /v1/embeddings.

Run:  cat models/astropt/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "astropt")
EMB_DIM = 768  # real-image output is a 1D 768-dim vector (docstring's [N,512] is wrong; demo returns [16,512])
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
        return round((self.s % 1000)/1000.0, 4)


def rand_img(seed, h=64, w=64):
    rng = _LCG(seed)
    return [[[rng.nxt() for _ in range(3)] for _ in range(w)] for _ in range(h)]


def _vec(d):
    """Return the flat embedding vector. Real path = 1D 768 floats; demo = 2D [16,512] (flatten)."""
    e = d.get("embeddings")
    if isinstance(e, list) and e:
        if isinstance(e[0], list):
            return [x for patch in e for x in patch]
        return list(e)
    return []


def wake():
    for attempt in range(90):  # first v2 boot builds venv (~5 min)
        r, d = embed({"image": rand_img(1)})
        if r.status_code == 200:
            v = _vec(d)
            ok = len(v) == EMB_DIM
            record("PASS" if ok else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={len(v)} (exp {EMB_DIM})")
            return ok
        if r.status_code in (503, 502, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return False
    record("FAIL", 0, "WAKE + dim", "timed out"); return False


def checks():
    # non-zero
    r, d = embed({"image": rand_img(2)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == EMB_DIM and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"len={len(v)} zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")
    # distinct
    _, d1 = embed({"image": rand_img(10)}); _, d2 = embed({"image": rand_img(20)})
    v1, v2 = _vec(d1), _vec(d2)
    c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f}")
    # deterministic
    img = rand_img(30); _, d1 = embed({"image": img}); _, d2 = embed({"image": img})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")
    # echo
    r, d = embed({"image": rand_img(40)})
    record("PASS" if r.status_code == 200 and d.get("model") == "astropt-095m" else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")
    # demo (returns 2D [16,512] → flattened 8192; just check demo flag + non-empty)
    r, d = embed({"demo": True}); v = _vec(d)
    record("PASS" if r.status_code == 200 and d.get("demo") and v else "FAIL",
           r.status_code, "demo path", f"demo={d.get('demo')} flatlen={len(v)}")
    # malformed
    r, _ = embed({})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    if wake(): checks()
    raise SystemExit(summary())
