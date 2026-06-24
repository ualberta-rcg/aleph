"""croma cross-modal satellite embedding gateway test (run inside the gateway pod).

Embedding battery for CROMA (antofuller/CROMA, GPU). Dual-encoder ViT producing
GAP-pooled embeddings from SAR (Sentinel-1) and/or optical (Sentinel-2) imagery.
Endpoint: /v1/embeddings. Returns OpenAI-format {data:[{embedding,...}]}.

Run:  cat models/croma/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "croma")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/embeddings", json=body, timeout=timeout)
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


def rand_sar(seed, h=120, w=120):
    rng = _LCG(seed)
    return [[[rng.nxt() for _ in range(w)] for _ in range(h)] for _ in range(2)]


def rand_optical(seed, h=120, w=120):
    rng = _LCG(seed + 9999)
    return [[[rng.nxt() for _ in range(w)] for _ in range(h)] for _ in range(12)]


def _flatten(lst):
    out = []
    for x in lst:
        if isinstance(x, list): out.extend(_flatten(x))
        else: out.append(x)
    return out


def _vec(d):
    data = d.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return _flatten(data[0].get("embedding", []))
    e = d.get("embeddings")
    if isinstance(e, list) and e:
        return _flatten(e)
    return []


def wake():
    sar = rand_sar(1); opt = rand_optical(1)
    for attempt in range(90):
        r, d = embed({"sar_images": sar, "optical_images": opt})
        if r.status_code == 200:
            v = _vec(d)
            record("PASS" if len(v) > 0 else "FAIL", 200, "WAKE + embed", f"attempts={attempt+1} dim={len(v)}")
            return len(v)
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + embed", f"body={r.text[:120]}"); return 0
    record("FAIL", 0, "WAKE + embed", "timed out"); return 0


def checks(dim):
    r, d = embed({"sar_images": rand_sar(2), "optical_images": rand_optical(2)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == dim and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")

    _, d1 = embed({"sar_images": rand_sar(10), "optical_images": rand_optical(10)})
    _, d2 = embed({"sar_images": rand_sar(20), "optical_images": rand_optical(20)})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f}")

    sar, opt = rand_sar(30), rand_optical(30)
    _, d1 = embed({"sar_images": sar, "optical_images": opt})
    _, d2 = embed({"sar_images": sar, "optical_images": opt})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")

    r, d = embed({"sar_images": rand_sar(40), "optical_images": rand_optical(40)})
    record("PASS" if r.status_code == 200 and d.get("model") == "croma" else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    r, d = embed({"sar_images": rand_sar(50)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) > 0 else ("EXP" if r.status_code in (400, 500) else "FAIL"),
           r.status_code, "SAR-only modality", f"dim={len(v)}")

    r, d = embed({"optical_images": rand_optical(60)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) > 0 else ("EXP" if r.status_code in (400, 500) else "FAIL"),
           r.status_code, "optical-only modality", f"dim={len(v)}")

    r, d = embed({"sar_images": rand_sar(70), "optical_images": rand_optical(70)}); v = _vec(d)
    norm = math.sqrt(sum(x*x for x in v)) if v else 0
    record("PASS" if 0.1 < norm < 1e6 else "FAIL", r.status_code, "embedding norm", f"L2={norm:.4f}")

    required = {"data", "model"}
    r, d = embed({"sar_images": rand_sar(80), "optical_images": rand_optical(80)})
    present = set(d.keys()) & required
    record("PASS" if r.status_code == 200 and present == required else "FAIL",
           r.status_code, "response fields", f"present={sorted(present)} required={sorted(required)}")

    r = httpx.get(f"{G}/v1/models", timeout=30)
    try: mlist = r.json().get("data", [])
    except Exception: mlist = []
    found = any(m.get("id","").startswith(MODEL.split("-")[0]) for m in mlist) if mlist else False
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "models list reachable", f"found={found} n_models={len(mlist)}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    dim = wake()
    if dim: checks(dim)
    raise SystemExit(summary())
