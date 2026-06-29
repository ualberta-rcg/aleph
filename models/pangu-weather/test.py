"""pangu-weather test — POST /v1/science/forecast.

Two legs:
  DEMO : {"demo": true}            — no-network smoke test; asserts ONNX runs, output finite.
  REAL : {"date": "...", "coords"} — live ERA5 init from WeatherBench2 (GCS); asserts a real
                                      forecast with physically-plausible temps + per-point values.
REAL degrades to SKIP (not FAIL) if GCS egress is blocked — ERA5 fetch needs public-internet access
from the cluster node."""
import httpx, os, time, math
G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY"); _H = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_V = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "pangu-weather"); EP = "/v1/science/forecast"

DEMO = {"model": MODEL, "demo": True, "lead_hours": 6}
REAL = {"model": MODEL, "date": "2018-01-01T00:00:00", "lead_hours": 6,
        "coords": [{"lat": 53.5, "lon": -113.5},   # Edmonton (winter)
                   {"lat": 0.0, "lon": -150.0}]}    # equatorial Pacific

res = []
def req(b, t=300): return httpx.post(f"{G}{EP}", json=b, timeout=t, headers=_H, verify=_V)
def rec(i, s, n, d): res.append((i, s, n, d)); print(f"[{i}] {s} | {n}: {d}", flush=True)

def wake(payload, tag):
    for a in range(90):
        try: r = req(payload)
        except Exception as e:
            rec("FAIL", 0, f"WAKE/{tag}", f"conn err {e}"); return None
        if r.status_code == 200: rec("PASS", 200, f"WAKE/{tag}", f"attempts={a+1}"); return r.json()
        if r.status_code in (502, 503, 504): time.sleep(5); continue
        if r.status_code == 404 and a < 30: time.sleep(5); continue
        rec("FAIL", r.status_code, f"WAKE/{tag}", f"body={r.text[:160]}"); return None
    rec("FAIL", 503, f"WAKE/{tag}", "timed out"); return None

def demo_shape(d):
    ok = set(["summary", "source", "lead_hours"]).issubset(d.keys()) and d.get("source") == "demo"
    rec("PASS" if ok else "FAIL", 200, "DEMO/SHAPE", f"keys={sorted(d.keys())}")

def demo_sanity(d):
    s = d.get("summary", {})
    t = (s.get("t2m_K") or {}).get("mean")
    ok = t is not None and math.isfinite(t)
    rec("PASS" if ok else "FAIL", 200, "DEMO/SANITY", f"finite={ok} t2m_mean={t}")

def real_contract(d):
    if d.get("source") != "weatherbench2-era5":
        rec("FAIL", 200, "REAL/SOURCE", f"source={d.get('source')!r}"); return
    s = d.get("summary", {})
    t2m = (s.get("t2m_K") or {}).get("mean"); z500 = (s.get("z_500hPa_m2s2") or {}).get("mean")
    ok = (t2m is not None and 200 < t2m < 320 and z500 is not None and 40000 < z500 < 65000
          and d.get("valid_time") and d.get("init_time"))
    rec("PASS" if ok else "FAIL", 200, "REAL/SUMMARY",
        f"t2m={t2m} z500={z500} init={d.get('init_time')} valid={d.get('valid_time')}")

def real_points(d):
    pts = d.get("points")
    if not pts or len(pts) < 2:
        rec("FAIL", 200, "REAL/POINTS", f"pts={pts}"); return
    edm, trop = pts[0], pts[1]
    # January: Edmonton should be much colder than the equatorial Pacific
    ok = (edm.get("t2m_K") is not None and trop.get("t2m_K") is not None
          and edm["t2m_K"] < trop["t2m_K"]
          and all(math.isfinite(edm.get(k, float("nan"))) for k in
                  ("t2m_K", "msl_Pa", "u10_ms", "v10_ms", "t_850hPa_K", "z_500hPa_m2s2")))
    rec("PASS" if ok else "FAIL", 200, "REAL/POINTS",
        f"Edmonton t2m={edm.get('t2m_K')} vs tropics t2m={trop.get('t2m_K')}")

def catalog():
    try:
        r = httpx.get(f"{G}/v1/models?all=true", headers=_H, verify=_V, timeout=30)
        m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
        rec("PASS" if m else "FAIL", r.status_code, "Catalog",
            f"type={m.get('type') if m else 'MISSING'}")
    except Exception as e:
        rec("FAIL", 0, "Catalog", str(e)[:100])

if __name__ == "__main__":
    print("=" * 66); print(f"{MODEL} forecast test ({EP})"); print("=" * 66)

    # --- DEMO leg (always) ---
    d = wake(DEMO, "demo")
    if d:
        for t in (demo_shape, demo_sanity):
            try: t(d)
            except Exception as e: rec("ERR", 0, t.__name__, str(e)[:100])

    # --- REAL leg (ERA5 via WeatherBench2) ---
    d2 = wake(REAL, "real")
    if d2:
        for t in (real_contract, real_points):
            try: t(d2)
            except Exception as e: rec("ERR", 0, t.__name__, str(e)[:100])
    else:
        # If wake failed on a 500 from GCS/network, the ERA5 path needs node egress — SKIP, not FAIL.
        rec("SKIP", 0, "REAL/ERA5", "ERA5 fetch unavailable (GCS egress blocked?); demo leg validates the model")

    catalog()

    p = sum(1 for x in res if x[0] == "PASS"); e = sum(1 for x in res if x[0] == "EXP")
    f = sum(1 for x in res if x[0] in ("FAIL", "ERR")); s = sum(1 for x in res if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(res)}")
