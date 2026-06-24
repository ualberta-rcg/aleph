"""brainlm fMRI embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom BrainLM server (vandijklab ViT-MAE, GPU).
1280-dim latent embeddings from 424-ROI fMRI time-series, via the domain /v1/science/embed
endpoint (also aliased at /v1/embeddings). Non-text (fMRI array).

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/brainlm/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/brainlm/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "brainlm")
EXP_DIM = 1280
N_ROIS = 424
N_TP = 200
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout, headers=_HEADERS)
    try: return r, r.json()
    except Exception: return r, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


class _LCG:
    def __init__(self, s): self.s = s & 0x7FFFFFFF
    def nxt(self):
        self.s = (1103515245*self.s + 12345) & 0x7FFFFFFF
        return round(((self.s % 2000)/1000.0) - 1.0, 4)


def rand_fmri(seed, rois=N_ROIS, tp=N_TP):
    rng = _LCG(seed)
    return [[rng.nxt() for _ in range(tp)] for _ in range(rois)]


def _vec(d):
    data = d.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0].get("embedding", [])
    e = d.get("embeddings")
    if isinstance(e, list) and e:
        if isinstance(e[0], list):
            return e[0] if len(e) == 1 else [x for p in e for x in p]
        return list(e)
    return []


def wake_dim():
    fmri = rand_fmri(1)
    for attempt in range(72):
        r, d = embed({"fmri": fmri})
        if r.status_code == 200:
            v = _vec(d); n = len(v)
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE + dim", "timed out")


def checks():
    r, d = embed({"fmri": rand_fmri(2)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")

    _, d1 = embed({"fmri": rand_fmri(10)}); _, d2 = embed({"fmri": rand_fmri(20)})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.99999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f} (noise fMRI ~identical)")

    fmri = rand_fmri(30); _, d1 = embed({"fmri": fmri}); _, d2 = embed({"fmri": fmri})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")

    r, d = embed({"fmri": rand_fmri(40)})
    record("PASS" if r.status_code == 200 and d.get("model") == "brainlm" else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")

    r, _ = embed({})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")

    r, d = embed({"fmri": rand_fmri(50)}); v = _vec(d)
    norm = math.sqrt(sum(x*x for x in v)) if v else 0
    record("PASS" if 0.1 < norm < 1e6 else "FAIL", r.status_code, "embedding norm", f"L2={norm:.4f}")

    required = {"data", "model"}
    r, d = embed({"fmri": rand_fmri(60)})
    present = set(d.keys()) & required
    record("PASS" if r.status_code == 200 and present == required else "FAIL",
           r.status_code, "response fields", f"present={sorted(present)} required={sorted(required)}")

    r = httpx.get(f"{G}/v1/models", timeout=30, headers=_HEADERS)
    try: mlist = r.json().get("data", [])
    except Exception: mlist = []
    found = any(m.get("id","").startswith(MODEL.split("-")[0]) for m in mlist) if mlist else False
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "models list reachable", f"found={found} n_models={len(mlist)}")

    r, d = embed({"fmri": rand_fmri(70)})
    data = d.get("data", [])
    ok = (r.status_code == 200 and isinstance(data, list) and len(data) > 0
          and isinstance(data[0], dict) and "embedding" in data[0] and "index" in data[0])
    record("PASS" if ok else "FAIL", r.status_code, "OpenAI format structure", f"has_data={bool(data)} keys={list(data[0].keys()) if data else []}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    wake_dim(); checks()
    raise SystemExit(summary())
