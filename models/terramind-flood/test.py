"""terramind-flood multi-sensor flood detection gateway test.

Classification battery for IBM/ESA TerraMind-base-Flood (GPU, demo mode).
Sentinel-2 (12 bands) + Sentinel-1 RTC (2 bands) + DEM (1 band), 4 time steps, 256x256.
Endpoint: /v1/science/classify. Returns flood_mask, flood_prob, flood_area_pct.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/terramind-flood/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/terramind-flood/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, math, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "terramind-flood")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def classify(body, timeout=300):
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/classify", json=body, timeout=timeout, headers=_HEADERS)
    try: return r, r.json()
    except Exception: return r, {}


def wake():
    for attempt in range(90):
        r, d = classify({"demo": True})
        if r.status_code == 200:
            ok = "flood_mask" in d
            record("PASS" if ok else "FAIL", 200, "WAKE + demo", f"attempts={attempt+1} has_mask={ok}")
            return ok
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + demo", f"body={r.text[:120]}"); return False
    record("FAIL", 0, "WAKE + demo", "timed out"); return False


def checks():
    r, d = classify({"demo": True})
    mask = d.get("flood_mask", [])
    ok = r.status_code == 200 and isinstance(mask, list) and len(mask) > 0 and isinstance(mask[0], list)
    record("PASS" if ok else "FAIL", r.status_code, "demo flood_mask shape", f"H={len(mask)} W={len(mask[0]) if mask else 0}")

    r, d = classify({"demo": True})
    prob = d.get("flood_prob", [])
    ok = r.status_code == 200 and isinstance(prob, list) and len(prob) > 0
    vals = [x for row in (prob[:2] if prob else []) for x in (row[:3] if isinstance(row, list) else [])]
    record("PASS" if ok and all(0 <= v <= 1 for v in vals) else "FAIL",
           r.status_code, "flood_prob range [0,1]", f"sample={vals[:4]}")

    r, d = classify({"demo": True})
    pct = d.get("flood_area_pct")
    ok = r.status_code == 200 and isinstance(pct, (int, float)) and 0 <= pct <= 100
    record("PASS" if ok else "FAIL", r.status_code, "flood_area_pct valid", f"pct={pct}")

    r, d = classify({"demo": True})
    record("PASS" if r.status_code == 200 and d.get("model") == "terramind-flood" else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    r, d = classify({"demo": True})
    record("PASS" if r.status_code == 200 and d.get("demo") == True else "FAIL",
           r.status_code, "demo flag echoed", f"demo={d.get('demo')!r}")

    r1, d1 = classify({"demo": True}); r2, d2 = classify({"demo": True})
    m1, m2 = d1.get("flood_mask", []), d2.get("flood_mask", [])
    record("PASS" if m1 == m2 else "FAIL", 200, "demo deterministic", f"masks_equal={m1 == m2}")

    required = {"flood_mask", "flood_prob", "flood_area_pct", "model"}
    r, d = classify({"demo": True})
    present = set(d.keys()) & required
    record("PASS" if r.status_code == 200 and present == required else "FAIL",
           r.status_code, "response fields", f"present={sorted(present)} required={sorted(required)}")

    r = httpx.get(f"{G}/v1/models", timeout=30, headers=_HEADERS)
    try: mlist = r.json().get("data", [])
    except Exception: mlist = []
    found = any(m.get("id","").startswith(MODEL.split("-")[0]) for m in mlist) if mlist else False
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "models list reachable", f"found={found} n_models={len(mlist)}")

    r, d = classify({"demo": True})
    mask = d.get("flood_mask", [])
    if mask and mask[0]:
        unique = set(v for row in mask for v in row)
        ok = unique <= {0, 1}
        record("PASS" if ok else "FAIL", r.status_code, "mask values binary", f"unique={unique}")
    else:
        record("FAIL", r.status_code, "mask values binary", "empty mask")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    if wake(): checks()
    raise SystemExit(summary())
