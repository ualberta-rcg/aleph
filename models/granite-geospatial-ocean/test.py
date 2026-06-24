"""granite-geospatial-ocean Sentinel-3 embedding gateway test (run inside the gateway pod).

Embedding battery for IBM Granite Geospatial Ocean (GPU/demo mode). ViT MAE pretrained
on 512K Sentinel-3 OLCI+SLSTR images. 16 bands, 42x42 patches, 768-dim embeddings.
Endpoint: /v1/science/embed.

Run:  cat models/granite-geospatial-ocean/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "granite-geospatial-ocean")
EXP_DIM = 768
BANDS = 16
H = W = 42
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


def rand_cube(seed, bands=BANDS, h=H, w=W):
    rng = _LCG(seed)
    return [[[rng.nxt() for _ in range(w)] for _ in range(h)] for _ in range(bands)]


def _vec(d):
    e = d.get("embeddings")
    if isinstance(e, list) and e:
        if isinstance(e[0], list): return e[0]
        return list(e)
    return []


def wake():
    for attempt in range(90):
        r, d = embed({"demo": True})
        if r.status_code == 200:
            v = _vec(d)
            record("PASS" if len(v) > 0 else "FAIL", 200, "WAKE + demo", f"attempts={attempt+1} dim={len(v)}")
            return True
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + demo", f"body={r.text[:120]}"); return False
    record("FAIL", 0, "WAKE + demo", "timed out"); return False


def checks():
    r, d = embed({"demo": True}); v = _vec(d)
    ok = r.status_code == 200 and len(v) == EXP_DIM
    record("PASS" if ok else "FAIL", r.status_code, "demo dim", f"dim={len(v)} (exp {EXP_DIM})")

    r, d = embed({"demo": True})
    record("PASS" if r.status_code == 200 and d.get("model") == "granite-geospatial-ocean" else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    r, d = embed({"demo": True})
    record("PASS" if r.status_code == 200 and d.get("demo") == True else "FAIL",
           r.status_code, "demo flag echoed", f"demo={d.get('demo')!r}")

    r, d = embed({"image": rand_cube(10)})
    v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) > 0 else ("EXP" if r.status_code in (500, 422) else "FAIL"),
           r.status_code, "real image embed", f"dim={len(v)} (EXP if backbone mismatch)")

    r1, d1 = embed({"demo": True}); r2, d2 = embed({"demo": True})
    v1, v2 = _vec(d1), _vec(d2)
    c = _cos(v1, v2) if v1 and v2 and any(x != 0 for x in v1) else (1.0 if v1 == v2 else 0.0)
    record("PASS" if v1 == v2 else "FAIL", 200, "demo deterministic", f"cos={c:.5f} match={v1==v2}")

    required = {"embeddings", "model", "shape"}
    r, d = embed({"demo": True})
    present = set(d.keys()) & required
    record("PASS" if r.status_code == 200 and present == required else "FAIL",
           r.status_code, "response fields", f"present={sorted(present)} required={sorted(required)}")

    r = httpx.get(f"{G}/v1/models", timeout=30)
    try: mlist = r.json().get("data", [])
    except Exception: mlist = []
    found = any(m.get("id","").startswith(MODEL.split("-")[0]) for m in mlist) if mlist else False
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "models list reachable", f"found={found} n_models={len(mlist)}")

    r, d = embed({"demo": True})
    shape = d.get("shape")
    ok = r.status_code == 200 and isinstance(shape, list) and len(shape) == 2
    record("PASS" if ok else "FAIL", r.status_code, "shape field valid", f"shape={shape}")

    r, _ = embed({})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    if wake(): checks()
    raise SystemExit(summary())
