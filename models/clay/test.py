"""clay geospatial embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom Clay MAE server (Clay Foundation large, CPU).
CLS embeddings of any-band satellite image patches, via the domain /v1/science/embed endpoint.
Non-text (pixels+waves input) → does NOT expose OpenAI /v1/embeddings.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/clay/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/clay/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "clay")
EXP_DIM = 1024
BANDS = 4
H = W = 32
WAVES = [0.49, 0.56, 0.665, 0.84]
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)
    try: return r, r.json()
    except Exception: return r, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


class _LCG:
    def __init__(self, s): self.s = s & 0x7FFFFFFF
    def nxt(self):
        self.s = (1103515245*self.s + 12345) & 0x7FFFFFFF
        return round(((self.s % 3000)/1000.0), 3)


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
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return 0
    record("FAIL", 0, "WAKE + dim", "timed out"); return 0


def checks(dim):
    r, d = embed({"pixels": rand_cube(2), "waves": WAVES}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == dim and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")

    _, d1 = embed({"pixels": rand_cube(10), "waves": WAVES}); _, d2 = embed({"pixels": rand_cube(20), "waves": WAVES})
    e1, e2 = _vec(d1), _vec(d2)
    c = _cos(e1, e2) if e1 and e2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f}")

    cube = rand_cube(30); _, d1 = embed({"pixels": cube, "waves": WAVES}); _, d2 = embed({"pixels": cube, "waves": WAVES})
    e1, e2 = _vec(d1), _vec(d2); c = _cos(e1, e2) if e1 and e2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")

    r, d = embed({"pixels": rand_cube(40), "waves": WAVES})
    record("PASS" if r.status_code == 200 and d.get("model") == MODEL else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")

    r, _ = embed({})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")

    r, d = embed({"pixels": rand_cube(50), "waves": WAVES}); v = _vec(d)
    norm = math.sqrt(sum(x*x for x in v)) if v else 0
    record("PASS" if 0.1 < norm < 1e6 else "FAIL", r.status_code, "embedding norm", f"L2={norm:.4f}")

    required = {"embeddings", "model"}
    r, d = embed({"pixels": rand_cube(60), "waves": WAVES})
    present = set(d.keys()) & required
    record("PASS" if r.status_code == 200 and present == required else "FAIL",
           r.status_code, "response fields", f"present={sorted(present)} required={sorted(required)}")

    r = httpx.get(f"{G}/v1/models", timeout=30, headers=_HEADERS, verify=_VERIFY)
    try: mlist = r.json().get("data", [])
    except Exception: mlist = []
    found = any(m.get("id","").startswith(MODEL.split("-")[0]) for m in mlist) if mlist else False
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "models list reachable", f"found={found} n_models={len(mlist)}")

    r, d = embed({"pixels": rand_cube(80), "waves": WAVES, "gsd": 10.0, "lat": 45.0, "lon": -73.5, "time": "2024-06-15"})
    v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == dim else "FAIL",
           r.status_code, "metadata pass (lat/lon/time)", f"dim={len(v)}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    dim = wake_dim()
    if dim: checks(dim)
    raise SystemExit(summary())
