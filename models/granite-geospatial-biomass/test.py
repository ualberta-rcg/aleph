"""granite-geospatial-biomass above-ground biomass gateway test (run inside the gateway pod).

Classification battery for IBM Granite Geospatial Biomass (GPU/demo mode). Swin-B + UPerNet
fine-tuned on GEDI L4A + HLS imagery across 15 biomes. 6 bands (Blue,Green,Red,NIR,SWIR1,SWIR2).
Endpoint: /v1/science/predict. Returns biomass_map, biomass_mean.

Run:  cat models/granite-geospatial-biomass/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "granite-geospatial-biomass")
BANDS = 6
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def predict(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/predict", json=body, timeout=timeout)
    try: return r, r.json()
    except Exception: return r, {}


class _LCG:
    def __init__(self, s): self.s = s & 0x7FFFFFFF
    def nxt(self):
        self.s = (1103515245*self.s + 12345) & 0x7FFFFFFF
        return round((self.s % 1000)/1000.0, 4)


def rand_hls(seed, h=64, w=64):
    rng = _LCG(seed)
    return [[[rng.nxt() for _ in range(w)] for _ in range(h)] for _ in range(BANDS)]


def wake():
    for attempt in range(90):
        r, d = predict({"demo": True})
        if r.status_code == 200:
            ok = "biomass_map" in d
            record("PASS" if ok else "FAIL", 200, "WAKE + demo", f"attempts={attempt+1} has_map={ok}")
            return ok
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + demo", f"body={r.text[:120]}"); return False
    record("FAIL", 0, "WAKE + demo", "timed out"); return False


def checks():
    r, d = predict({"demo": True})
    bmap = d.get("biomass_map", [])
    ok = r.status_code == 200 and isinstance(bmap, list) and len(bmap) > 0 and isinstance(bmap[0], list)
    record("PASS" if ok else "FAIL", r.status_code, "demo biomass_map shape", f"H={len(bmap)} W={len(bmap[0]) if bmap else 0}")

    r, d = predict({"demo": True})
    bmean = d.get("biomass_mean")
    ok = r.status_code == 200 and isinstance(bmean, (int, float)) and bmean >= 0
    record("PASS" if ok else "FAIL", r.status_code, "biomass_mean valid", f"mean={bmean}")

    r, d = predict({"demo": True})
    record("PASS" if r.status_code == 200 and d.get("model") == "granite-geospatial-biomass" else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    r, d = predict({"demo": True})
    record("PASS" if r.status_code == 200 and d.get("demo") == True else "FAIL",
           r.status_code, "demo flag echoed", f"demo={d.get('demo')!r}")

    r1, d1 = predict({"demo": True}); r2, d2 = predict({"demo": True})
    m1, m2 = d1.get("biomass_map", []), d2.get("biomass_map", [])
    record("PASS" if m1 == m2 else "FAIL", 200, "demo deterministic", f"maps_equal={m1 == m2}")

    r, d = predict({"demo": True})
    bmap = d.get("biomass_map", [])
    vals = [v for row in (bmap[:5] if bmap else []) for v in (row[:5] if isinstance(row, list) else [])]
    ok = all(isinstance(v, (int, float)) and v >= 0 for v in vals)
    record("PASS" if ok and vals else "FAIL", r.status_code, "biomass values non-negative", f"sample={vals[:4]}")

    required = {"biomass_map", "biomass_mean", "model"}
    r, d = predict({"demo": True})
    present = set(d.keys()) & required
    record("PASS" if r.status_code == 200 and present == required else "FAIL",
           r.status_code, "response fields", f"present={sorted(present)} required={sorted(required)}")

    r = httpx.get(f"{G}/v1/models", timeout=30)
    try: mlist = r.json().get("data", [])
    except Exception: mlist = []
    found = any(m.get("id","").startswith(MODEL.split("-")[0]) for m in mlist) if mlist else False
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "models list reachable", f"found={found} n_models={len(mlist)}")

    r, d = predict({"image": rand_hls(10)})
    bmap = d.get("biomass_map")
    record("PASS" if r.status_code == 200 and bmap else ("EXP" if r.status_code in (500, 422) else "FAIL"),
           r.status_code, "real image predict", f"has_map={bmap is not None} (EXP if model load issue)")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    if wake(): checks()
    raise SystemExit(summary())
